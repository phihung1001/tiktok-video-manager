# TikTok Video Manager

Tool Windows tự động upload video lên TikTok Seller Center bằng Selenium.

## 1. Tính năng hiện tại

- Chọn thư mục video và chạy theo batch tối đa 50 file.
- Kiểm tra định dạng, dung lượng, thời lượng và tỷ lệ khung hình bằng `ffprobe`.
- Hỗ trợ pause, resume và stop.
- Tự chờ người dùng xử lý đăng nhập, 2FA hoặc CAPTCHA trên Chrome.
- Lưu trạng thái upload để tránh upload lại video đã thành công.
- Chụp screenshot khi batch gặp lỗi và hiển thị trực tiếp trên giao diện.
- Xóa screenshot/log cũ khi bắt đầu phiên mới.
- Hỗ trợ theme sáng/tối và tiếng Việt/English.

## 2. Yêu cầu chạy

- Windows 10/11.
- Python 3.10 trở lên khi chạy từ mã nguồn.
- Google Chrome.
- `ffprobe` trong `PATH`, hoặc được đóng gói cùng installer.
- Kết nối Internet khi Selenium Manager cần tải driver và khi kiểm tra license.

## 3. Cài đặt từ mã nguồn

```powershell
python -m pip install -r requirements.txt
python app.py
```

Kiểm tra cú pháp và test:

```powershell
python -m py_compile app.py automation\*.py
python -m unittest discover -s tests -v
```

## 4. Dữ liệu người dùng

Từ phiên bản mới, dữ liệu không còn ghi cạnh file `.exe`. Tool sử dụng:

```text
%APPDATA%\TikTokVideoManager\
├── config.json
├── state.json
├── state.json.bak
├── logs\
└── browser-profile\
```

Ở lần chạy đầu tiên, `config.json` và `state.json` cũ cạnh project sẽ được sao chép vào vùng dữ liệu mới; file cũ không bị xóa.

`browser-profile` chứa session Chrome của người dùng. Không chia sẻ thư mục này vì có thể chứa session đăng nhập Seller Center.

## 5. Quy trình upload

1. Chọn thư mục video.
2. Nhập tài khoản TikTok và thông tin upload.
3. Chọn quy tắc video, batch size và timeout.
4. Bấm **Bắt đầu phiên**.
5. Hoàn tất login/2FA/CAPTCHA trên Chrome nếu được yêu cầu.
6. Tool kiểm tra video, bỏ qua video không hợp lệ và upload theo batch.
7. Khi TikTok báo lỗi hoặc DOM không xác định, tool dừng batch để tránh thao tác nhầm.

## 6. State và chống upload trùng

State sử dụng các trạng thái:

- `success`: upload đã xác nhận thành công.
- `uploading`: tool đã bắt đầu batch nhưng chưa có kết quả cuối.
- `unknown`: phiên trước kết thúc giữa chừng, không biết TikTok đã nhận video hay chưa.
- `new`: chưa có lịch sử upload.

File `uploading` hoặc `unknown` được bỏ qua ở phiên sau để tránh upload trùng. Người vận hành cần kiểm tra trên Seller Center trước khi xử lý lại.

State được ghi bằng file tạm và thay thế nguyên tử; bản trước được giữ ở `state.json.bak`.

## 7. License cho bản thương mại

Client đã có hợp đồng API license dạng:

```text
POST {license_server_url}/v1/licenses/validate
Content-Type: application/json

{
  "license_key": "...",
  "device_id": "..."
}
```

Server cần trả về:

```json
{
  "valid": true,
  "payload": {
    "license_id": "LIC-001",
    "expires_at": 1893456000
  },
  "signature": "base64-ed25519-signature"
}
```

Chữ ký phải là Ed25519 trên JSON canonical của `payload`. Public key chỉ được nhúng vào bản build thương mại, không lấy từ response của server.

Thiết lập trong `config.json` của bản thương mại:

```json
{
  "license_server_url": "https://license.example.com",
  "license_key": "CUSTOMER-LICENSE-KEY",
  "license_public_key": "BASE64-ED25519-PUBLIC-KEY"
}
```

Khi `license_server_url` chưa cấu hình, bản development không khóa license. Trước khi phát hành cần cấu hình endpoint, public key và giao diện kích hoạt license cho khách hàng.

## 8. Đóng gói bản thương mại

```powershell
pyinstaller MyTool.spec
```

`MyTool.spec` đã tắt console để khách hàng không thấy cửa sổ dòng lệnh. Trước khi phát hành cần bổ sung:

- Icon và thông tin version.
- Installer Windows.
- Bộ cài `ffprobe` hoặc cơ chế kiểm tra dependency rõ ràng.
- Endpoint license production và public key production.
- Kiểm tra smoke test trên máy Windows sạch.

## 9. Kiểm tra trước mỗi release

```powershell
python -m py_compile app.py automation\*.py
python -m unittest discover -s tests -v
python -m json.tool config.json
```

Ngoài test tự động, cần kiểm tra trên Seller Center thật:

- Login mới và login đã có session.
- 1 video và nhiều video trong một batch.
- Video invalid và batch invalid.
- Pause/resume/stop.
- Chrome đóng đột ngột hoặc mất mạng.
- State `uploading`/`unknown` sau khi khởi động lại.
- Screenshot lỗi hiển thị và phóng to được.
- Chạy trên Windows user không có quyền ghi vào thư mục cài đặt.

## 10. Giới hạn và lưu ý

TikTok có thể thay đổi DOM hoặc quy trình Seller Center. Selector phải được kiểm tra lại khi TikTok cập nhật. Tool không tự vượt CAPTCHA/2FA và không nên dùng click cưỡng chế khi chưa xác định đúng phần tử.

Không ghi mật khẩu vào config hoặc log. Khi hỗ trợ khách hàng, chỉ gửi screenshot và báo cáo lỗi cần thiết; không gửi `browser-profile`.
