# TikTok Video Manager — Selenium Edition

Bản này bỏ Playwright/Electron. GUI dùng Tkinter có sẵn trong Python, automation dùng Selenium, video validation dùng ffprobe.

## Đúng theo workflow đã yêu cầu

1. Chọn folder video.
2. Chọn/nhập tài khoản TikTok.
3. Product là tùy chọn.
4. Nhập description.
5. Tick/untick "Hiển thị trên hồ sơ TikTok công khai".
6. Bấm BẮT ĐẦU.
7. Tool mở Seller Center bằng Chrome profile riêng và tự chờ đăng nhập nếu chưa có session.
8. Tự chạy từng batch tối đa 50 video: Thêm → Tải video lên → account → product → Tiếp → chọn nhiều file.
9. Chỉ những video chưa có trong `state.json` mới được đưa vào batch.
10. Chờ TikTok kiểm tra/upload toàn bộ batch.
11. Nếu batch invalid: tìm nút Xóa, ghi log lỗi và dừng batch để tránh thao tác nhầm.
12. Nếu batch hợp lệ: Tiếp theo → Xác nhận → description → public profile → Lưu.

Video được lọc trước khi upload nếu không đúng định dạng, vượt 500 MB, thời lượng dưới 5 giây hoặc trên 10 phút, không đọc được bằng ffprobe, hoặc tỷ lệ không sát 16:9, 1:1 hay 9:16.

Các quy tắc này có thể chỉnh trực tiếp trên khung **Quy tắc video** của giao diện. Giá trị được lưu trong `config.json` dưới `video_rules`; `batch_size` được giới hạn từ 1 đến 50.

`upload_timeout_seconds` quy định thời gian tối đa chờ TikTok tải và xác thực cả batch. Mặc định là 900 giây (15 phút), phù hợp với batch nhiều video.
12. Có Pause / Resume / Stop, progress, log, screenshot lỗi, state để không upload lại file đã thành công.

CAPTCHA/2FA không bị tự động vượt qua; nếu TikTok yêu cầu, hoàn tất trên cửa sổ Chrome và tool sẽ tự tiếp tục.

## Cài đặt Windows

Cần:
- Python 3.10+
- Google Chrome
- ffprobe trong PATH

Kiểm tra:

```bat
python --version
ffprobe -version
```

Cài Selenium:

```bat
install.bat
```

hoặc:

```bat
python -m pip install -r requirements.txt
```

Chạy:

```bat
run.bat
```

hoặc:

```bat
python app.py
```

Selenium 4 dùng Selenium Manager nên thường không cần tự tải chromedriver.

## Lưu ý selector

TikTok Seller Center có thể thay DOM theo tài khoản/phiên bản. File `automation/seller_center.py` dùng nhiều chiến lược locator và không click bừa khi không chắc chắn. Nếu một bước không nhận ra DOM, tool sẽ ghi log và chụp screenshot vào `logs/`.

## Quy trình bắt buộc khi chỉnh sửa code

Các AI agent hoặc developer phải tuân thủ quy trình sau cho mọi thay đổi tính năng:

1. Đọc README này trước khi sửa code.
2. Kiểm tra trạng thái và nội dung hiện tại của các file liên quan; không giả định code đang ở phiên bản cũ hay mới.
3. Xác định đúng module sở hữu hành vi trước khi chỉnh sửa:
	- `app.py`: giao diện, cấu hình và trạng thái phiên.
	- `automation/engine.py`: queue, batch, progress, pause/resume/stop.
	- `automation/seller_center.py`: Selenium workflow và selector TikTok.
	- `automation/validator.py`: lọc video trước upload.
	- `automation/state.py`: chống upload trùng.
	- `automation/browser.py`: Chrome và ChromeDriver.
4. Sau mỗi lần sửa một tính năng, phải chạy test ngay trước khi sửa tính năng khác.
5. Không chỉ kiểm tra compile; phải chạy test phù hợp với hành vi vừa thay đổi.
6. Không dùng thao tác click bừa. Khi selector hoặc DOM không chắc chắn, lưu screenshot vào `logs/` và báo rõ bước lỗi.
7. Không xóa hoặc reset `state.json`, `config.json`, `logs/` hay thay đổi của người dùng nếu chưa được yêu cầu.

### Bộ kiểm tra tối thiểu sau mỗi thay đổi

Chạy kiểm tra cú pháp toàn bộ project:

```powershell
python -m py_compile app.py automation\engine.py automation\seller_center.py automation\browser.py automation\state.py automation\validator.py
```

Kiểm tra cấu hình:

```powershell
python -m json.tool config.json
```

Nếu sửa validator, phải chạy kiểm tra video thực tế:

```powershell
python -c "import json; from pathlib import Path; from automation.validator import inspect_video; c=json.loads(Path('config.json').read_text(encoding='utf-8')); print([(p.name, inspect_video(p, c)[0]) for p in Path(c['folder']).iterdir() if p.is_file()])"
```

Nếu sửa upload batch, phải xác nhận nhiều đường dẫn được gửi trong một lần vào `input[type=file]`, batch không vượt quá 50 video và video đã có trong `state.json` được bỏ qua.

Nếu sửa Selenium selector hoặc workflow, phải kiểm tra bằng screenshot/HTML DOM thực tế tương ứng với bước vừa sửa. Chỉ kết luận thành công sau khi test hành vi đã đạt; compile thành công một mình chưa đủ.

Sau khi hoàn tất, báo rõ: file đã sửa, test đã chạy, kết quả test và những phần chưa thể test trực tiếp trên TikTok.
