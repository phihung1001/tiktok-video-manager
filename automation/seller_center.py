import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException, ElementNotInteractableException,
    StaleElementReferenceException, TimeoutException,
)
from .confirm_form import CONFIRM_FORM_SNAPSHOT, CONFIRM_POINTER_SAFE, SET_DESCRIPTION

FAST_POLL = 0.05

class SellerCenter:
    def __init__(self, driver, emit, wait_control):
        self.driver = driver
        self.emit = emit
        self.wait_control = wait_control
        self.wait = WebDriverWait(driver, 20, poll_frequency=FAST_POLL)

    def _checkpoint(self):
        self.wait_control()

    def open(self, url):
        self.driver.get(url)

    def open_video_manager(self, url):
        self.emit({"type": "info", "message": "Đã đăng nhập. Đang mở trang quản lý video..."})
        self.driver.get(url)
        self.wait_for_video_manager(timeout=30)

    def wait_for_video_manager(self, timeout=20):
        locators = [
            (By.CSS_SELECTOR, 'button[data-testid="creation-page-add-anchor-cxMyKe"]'),
            (By.CSS_SELECTOR, 'button[data-tid="m4b_dropdown_button"]'),
            (By.XPATH, '//button[normalize-space(.)="Thêm"]'),
        ]

        def ready(driver):
            if "/ads-creation/manage-analyze" not in driver.current_url:
                return False
            for locator in locators:
                for element in driver.find_elements(*locator):
                    if element.is_displayed() and element.is_enabled():
                        return True
            return False

        self._checkpoint()
        WebDriverWait(self.driver, timeout, poll_frequency=FAST_POLL).until(ready)

    def ensure_logged_in(self, timeout=300):
        # Chỉ chờ người dùng hoàn tất login/2FA/CAPTCHA nếu TikTok yêu cầu.
        end = time.time() + timeout
        informed = False
        while time.time() < end:
            self._checkpoint()
            body = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            login_markers = ("đăng nhập", "log in", "login")
            seller_markers = ("seller center", "trung tâm nhà bán", "thêm")
            if any(x in body for x in seller_markers) and not (
                "đăng nhập vào tiktok shop" in body or "log in to tiktok shop" in body
            ):
                return
            if not informed:
                self.emit({"type":"info","message":"Nếu Seller Center yêu cầu đăng nhập/2FA/CAPTCHA, hãy hoàn tất trên Chrome. Tool sẽ tự tiếp tục."})
                informed = True
            time.sleep(2)
        raise TimeoutException("Không phát hiện Seller Center đã đăng nhập sau 5 phút.")

    def _visible(self, locators, timeout=15):
        last = None
        for by, value in locators:
            self._checkpoint()
            try:
                return WebDriverWait(self.driver, timeout, poll_frequency=FAST_POLL).until(
                    EC.visibility_of_element_located((by, value))
                )
            except Exception as e:
                last = e
        raise TimeoutException(f"Không tìm thấy phần tử. Locators={locators}") from last

    def _click(self, locators, timeout=15):
        last = None
        for by, value in locators:
            self._checkpoint()
            try:
                el = WebDriverWait(self.driver, timeout, poll_frequency=FAST_POLL).until(
                    EC.element_to_be_clickable((by, value))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try:
                    el.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", el)
                return el
            except Exception as e:
                last = e
        raise TimeoutException(f"Không click được phần tử. Locators={locators}") from last

    @staticmethod
    def _text_exact(text):
        safe = text.replace('"', '\\"')
        return (By.XPATH, f'//*[normalize-space(text())="{safe}"]')

    @staticmethod
    def _text_contains(text):
        safe = text.replace('"', '\\"')
        return (By.XPATH, f'//*[contains(normalize-space(.),"{safe}")]')

    def click_add(self):
        self._click([
            (By.CSS_SELECTOR, 'button[data-testid="creation-page-add-anchor-cxMyKe"]'),
            (By.CSS_SELECTOR, 'button[data-tid="m4b_dropdown_button"]'),
            (By.XPATH, '//button[normalize-space(.)="Thêm"]'),
            (By.XPATH, '//*[@role="button" and normalize-space(.)="Thêm"]'),
            self._text_exact("Thêm"),
        ], timeout=10)

    def click_upload_video(self):
        self._click([
            (By.CSS_SELECTOR, '[role="menuitem"][data-testid="operation-creative-hub-f2GFp9-upload_video"]'),
            (By.CSS_SELECTOR, '[role="menuitem"][data-tid="m4b_dropdown_menu_item"]'),
            self._text_exact("Tải video lên"),
            (By.XPATH, '//*[contains(normalize-space(.),"Tải video lên")]')
        ], timeout=10)
        self.wait_for_upload_drawer(timeout=15)

    def wait_for_upload_drawer(self, timeout=15):
        def ready(driver):
            visible_product_button = any(
                element.is_displayed()
                for element in driver.find_elements(
                    By.CSS_SELECTOR, 'button[data-testid^="upload-drawer-product-link-"]'
                )
            )
            body = driver.find_element(By.TAG_NAME, "body").text
            upload_step_visible = "Bước 1/3" in body
            upload_title_visible = "Tải video lên" in body and (
                "Nội dung sáng tạo" not in body or upload_step_visible
            )
            return visible_product_button or upload_step_visible or upload_title_visible

        self._checkpoint()
        WebDriverWait(self.driver, timeout, poll_frequency=FAST_POLL).until(ready)

    def select_account(self, name):
        normalized = " ".join(name.split())
        locator = (By.XPATH, f'//*[normalize-space(text())="{normalized}" or contains(normalize-space(text()),"{normalized}")]')
        try:
            if WebDriverWait(self.driver, 3, poll_frequency=FAST_POLL).until(
                lambda driver: any(element.is_displayed() for element in driver.find_elements(*locator))
            ):
                return
        except TimeoutException:
            pass

        # Mở combobox/account picker.
        self._click([
            (By.XPATH, '//*[contains(text(),"Tài khoản TikTok")]/following::*[@role="combobox"][1]'),
            (By.CSS_SELECTOR, '[role="combobox"]'),
            (By.XPATH, '//input[contains(@placeholder,"Tài khoản")]')
        ])
        try:
            self._click([self._text_exact(normalized), self._text_contains(normalized)])
        except TimeoutException as error:
            raise TimeoutException(
                f"Không tìm thấy tài khoản TikTok '{normalized}'. Hãy kiểm tra account_name trong config.json."
            ) from error

    def choose_product(self, name):
        if not name:
            return
        try:
            self._click([
                (By.CSS_SELECTOR, 'button[data-testid^="upload-drawer-product-link-"]'),
                (By.XPATH, '//button[@data-tid="m4b_button" and .//span[normalize-space(.)="Chọn sản phẩm"]]'),
                (By.XPATH, '//button[normalize-space(.)="Chọn sản phẩm"]'),
            ], timeout=5)
        except TimeoutException:
            return

        input_locators = [
            (By.CSS_SELECTOR, 'input[placeholder*="sản phẩm" i]'),
            (By.CSS_SELECTOR, 'input[placeholder*="product" i]'),
            (By.CSS_SELECTOR, '[role="combobox"] input'),
        ]
        field = None
        try:
            field = self._visible(input_locators, timeout=5)
            field.clear()
            field.send_keys(name)
        except Exception:
            self.driver.execute_script("document.activeElement?.blur();")
            return

        normalized = " ".join(name.split())

        def find_exact_option(driver):
            candidates = driver.find_elements(
                By.CSS_SELECTOR,
                '[role="option"], [role="menuitem"], li, button'
            )
            for element in candidates:
                if element.is_displayed() and " ".join(element.text.split()) == normalized:
                    return element
            return False

        try:
            option = WebDriverWait(self.driver, 5, poll_frequency=FAST_POLL).until(find_exact_option)
            option.click()
        except Exception:
            # Sản phẩm không tồn tại: giữ trạng thái không chọn sản phẩm.
            try:
                field.send_keys(Keys.ESCAPE)
            except Exception:
                self.driver.execute_script("document.activeElement?.blur();")
            return

    def click_next(self):
        try:
            self._click([
                (By.XPATH, '//button[@data-tid="m4b_button" and normalize-space(.)="Tiếp" and not(@disabled)]'),
                (By.XPATH, '//button[normalize-space(.)="Tiếp" and not(@disabled)]'),
                (By.XPATH, '//*[@role="button" and normalize-space(.)="Tiếp" and not(@aria-disabled="true")]')
            ], timeout=1.5)
        except TimeoutException:
            self._click_custom_button(("Tiếp",), timeout=10)

    def upload_file(self, file_path):
        self.upload_files([file_path])

    def upload_files(self, file_paths):
        self._checkpoint()
        el = WebDriverWait(self.driver, 20, poll_frequency=FAST_POLL).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
        )
        self.driver.execute_script(
            "arguments[0].multiple = true; arguments[0].setAttribute('multiple', '');", el
        )
        el.send_keys("\n".join(str(path) for path in file_paths))

    def has_visible_file_input(self):
        return any(
            element.is_displayed()
            for element in self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
        )

    def _shadow_button_ready(self, labels):
        return bool(self.driver.execute_script(
            r"""
            const labels = arguments[0];
            function scan(root) {
                for (const host of root.querySelectorAll('*')) {
                    const text = (host.innerText || host.textContent || '').replace(/\s+/g, ' ').trim();
                    if (labels.some(label => text === label || text.includes(label))) {
                        const button = host.shadowRoot?.querySelector('button, [role="button"]') ||
                            (host.matches('button, [role="button"]') ? host : null);
                        if (button) {
                            const rect = button.getBoundingClientRect();
                            const disabled = button.disabled === true || button.hasAttribute('disabled') ||
                                button.getAttribute('aria-disabled') === 'true';
                            if (!disabled && rect.width > 0 && rect.height > 0) return true;
                        }
                    }
                    if (host.shadowRoot && scan(host.shadowRoot)) return true;
                }
                return false;
            }
            return scan(document);
            """,
            list(labels)
        ))

    def _click_shadow_button(self, labels, timeout=900):
        self._checkpoint()
        def ready(driver):
            try:
                return self._shadow_button_ready(labels)
            except Exception:
                return False
        WebDriverWait(self.driver, timeout, poll_frequency=FAST_POLL).until(ready)
        clicked = self.driver.execute_script(
            r"""
            const labels = arguments[0];
            function scan(root) {
                for (const host of root.querySelectorAll('*')) {
                    const text = (host.innerText || host.textContent || '').replace(/\s+/g, ' ').trim();
                    if (labels.some(label => text === label || text.includes(label))) {
                        const button = host.shadowRoot?.querySelector('button, [role="button"]') ||
                            (host.matches('button, [role="button"]') ? host : null);
                        if (button && !button.disabled && !button.hasAttribute('disabled') &&
                            button.getAttribute('aria-disabled') !== 'true') {
                            button.scrollIntoView({block: 'center'});
                            button.click();
                            return true;
                        }
                    }
                    if (host.shadowRoot && scan(host.shadowRoot)) return true;
                }
                return false;
            }
            return scan(document);
            """,
            list(labels)
        )
        if not clicked:
            raise TimeoutException(f"Không click được nút {', '.join(labels)} ở trạng thái sẵn sàng.")

    def _click_custom_button(self, labels, timeout=30):
        def click_button(driver):
            for host in driver.find_elements(By.CSS_SELECTOR, 'ks-button-1-1-11'):
                if not host.is_displayed() or ' '.join(host.text.split()) not in labels:
                    continue
                try:
                    button = host.shadow_root.find_element(By.CSS_SELECTOR, 'button')
                    if not button.is_enabled():
                        continue
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", button
                    )
                    button.click()
                    return True
                except Exception:
                    try:
                        host.click()
                        return True
                    except Exception:
                        continue
            return False

        self._checkpoint()
        WebDriverWait(self.driver, timeout, poll_frequency=FAST_POLL).until(click_button)

    def click_next_step(self):
        self._click_custom_button(("Tiếp theo",), timeout=900)

    def wait_upload_result(self, timeout=900):
        end = time.time() + timeout
        errors = ("Không được hỗ trợ bởi TikTok", "Không được hỗ trợ", "không hợp lệ")
        while time.time() < end:
            self._checkpoint()
            body = self.driver.find_element(By.TAG_NAME, "body").text
            if any(x in body for x in errors):
                return "invalid"
            if self._shadow_button_ready(("Xác nhận",)):
                return "confirm"
            if self._shadow_button_ready(("Tiếp theo",)):
                return "next"
            time.sleep(0.25)
        raise TimeoutException("Upload/validation quá thời gian chờ.")

    def delete_invalid_video(self):
        # Ưu tiên aria/title/text có nghĩa xóa. Không click button cuối cùng một cách mù quáng.
        locators = [
            (By.CSS_SELECTOR, 'button[aria-label*="xóa" i]'),
            (By.CSS_SELECTOR, 'button[aria-label*="delete" i]'),
            (By.CSS_SELECTOR, 'button[title*="xóa" i]'),
            (By.CSS_SELECTOR, 'button[title*="delete" i]'),
            (By.XPATH, '//*[@role="button" and (.//*[contains(@class,"trash")] or .//*[contains(@class,"delete")])]'),
            (By.XPATH, '//button[.//*[name()="svg"] and (@aria-label="Xóa" or @aria-label="Delete")]')
        ]
        self._click(locators, timeout=3)
        time.sleep(.5)

        # Nếu có confirm modal.
        for text in ("Xóa", "Delete", "Xác nhận"):
            els = self.driver.find_elements(By.XPATH, f'//button[normalize-space(.)="{text}" and not(@disabled)]')
            visible = [e for e in els if e.is_displayed()]
            if visible:
                try:
                    visible[-1].click()
                    break
                except Exception:
                    pass

    def _confirm_form_snapshot(self):
        snapshot = self.driver.execute_script(CONFIRM_FORM_SNAPSHOT)
        return snapshot if isinstance(snapshot, dict) else {}

    def click_confirm(self, timeout=30):
        """A click is not success: wait for the actual description form as well."""
        clicked = False
        snapshot = {}
        click_error = ""
        started = last_log = time.monotonic()
        self.emit({"type": "info", "message": "Chờ nút Xác nhận và màn hình mô tả..."})

        def ready(driver):
            nonlocal clicked, snapshot, last_log, click_error
            self._checkpoint()
            now = time.monotonic()
            if now - last_log >= 10:
                if clicked:
                    phase = "Chờ chuyển sang màn hình mô tả"
                elif snapshot.get("readyConfirmCount", 0):
                    phase = "Đã thấy nút Xác nhận; chờ click không bị chặn"
                else:
                    phase = "Chờ nút Xác nhận sẵn sàng"
                self.emit({"type": "info", "message": f"{phase} ({now - started:.0f}/{timeout:g}s)"})
                last_log = now
            try:
                snapshot = self._confirm_form_snapshot()
                if snapshot.get("formReady") and snapshot.get("description") is not None:
                    return True
                button = snapshot.get("confirm")
                if not clicked and button is not None:
                    # Native click checks interactability and produces a real pointer event.
                    # Retry only rejected/stale clicks; do not spam an accepted confirmation.
                    try:
                        button.click()
                    except ElementClickInterceptedException:
                        if not driver.execute_script(CONFIRM_POINTER_SAFE, button):
                            raise
                        ActionChains(driver).move_to_element(button).click().perform()
                        self.emit({"type": "info", "message": "Đã click chuột vào nút Xác nhận trong Shadow DOM."})
                    clicked = True
                    self.emit({"type": "info", "message": "Đã nhấn Xác nhận; đang chờ ô mô tả xuất hiện."})
            except (StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException) as error:
                click_error = f"{type(error).__name__}: {(error.msg or str(error)).splitlines()[0]}"[:300]
                return False
            return False

        try:
            WebDriverWait(self.driver, timeout, poll_frequency=0.1).until(ready)
        except TimeoutException as error:
            phase = ("Đã nhấn Xác nhận nhưng chưa chuyển sang màn hình mô tả"
                     if clicked else "Chưa nhấn được đúng nút Xác nhận đang hiển thị")
            details = (f"bước 3/3={snapshot.get('step3Visible')}, "
                       f"nút xác nhận={snapshot.get('confirmCount', 0)}, "
                       f"nút sẵn sàng={snapshot.get('readyConfirmCount', 0)}, "
                       f"ô mô tả={snapshot.get('descriptionCount', 0)}")
            raise TimeoutException(f"{phase} sau {timeout:g}s ({details}). {click_error}") from error
        self.emit({"type": "info", "message": "Đã chuyển sang màn hình mô tả."})

    def fill_description(self, description, timeout=15):
        if not description:
            return

        def fill(driver):
            self._checkpoint()
            try:
                snapshot = self._confirm_form_snapshot()
                field = snapshot.get("description")
                if not snapshot.get("formReady") or field is None:
                    return False
                # Re-discover on each poll: React may replace the editor after transition.
                return driver.execute_script(SET_DESCRIPTION, field, description)
            except StaleElementReferenceException:
                return False

        try:
            WebDriverWait(self.driver, timeout, poll_frequency=0.1).until(fill)
        except TimeoutException as error:
            raise TimeoutException(f"Màn hình mô tả chưa sẵn sàng hoặc chưa nhận nội dung sau {timeout:g}s.") from error

    def set_public_profile(self, enabled):
        text = "Hiển thị trên hồ sơ TikTok công khai"
        labels = self.driver.find_elements(By.XPATH, f'//*[normalize-space(.)="{text}"]')
        for label in labels:
            if not label.is_displayed():
                continue
            # Tìm checkbox trong/near label.
            boxes = label.find_elements(By.XPATH, './/input[@type="checkbox"]')
            if not boxes:
                boxes = label.find_elements(By.XPATH, 'preceding::input[@type="checkbox"][1]')
            if boxes:
                box = boxes[0]
                if box.is_selected() != enabled:
                    self.driver.execute_script("arguments[0].click();", box)
                return
        # Nếu DOM custom, thử checkbox duy nhất trong vùng form.
        boxes = [b for b in self.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]') if b.is_displayed()]
        if len(boxes) == 1 and boxes[0].is_selected() != enabled:
            self.driver.execute_script("arguments[0].click();", boxes[0])

    def close_upload_success_modal(self, timeout=30):
        def click_done(driver):
            for host in driver.find_elements(By.CSS_SELECTOR, 'ks-button-1-1-11'):
                label = " ".join(host.text.split())
                if not host.is_displayed() or not label.startswith("Xong"):
                    continue
                try:
                    button = host.shadow_root.find_element(By.CSS_SELECTOR, 'button')
                    if button.is_enabled() and button.get_attribute("aria-disabled") != "true":
                        button.click()
                        return True
                except Exception:
                    continue

            for button in driver.find_elements(By.XPATH, '//button[starts-with(normalize-space(.), "Xong")]'):
                if button.is_displayed() and button.is_enabled():
                    button.click()
                    return True
            return False

        self._checkpoint()
        WebDriverWait(self.driver, timeout, poll_frequency=FAST_POLL).until(click_done)

    def click_save(self):
        self._click([
            (By.XPATH, '//button[normalize-space(.)="Lưu" and not(@disabled)]'),
            self._text_exact("Lưu")
        ], timeout=30)
        self.close_upload_success_modal(timeout=30)
        time.sleep(3)
        self.wait_for_video_manager(timeout=20)

    def upload_one(self, file_path, account, product, description, public_profile, upload_timeout=900):
        return self.upload_many([file_path], account, product, description, public_profile, upload_timeout)[0]

    def upload_many(self, file_paths, account, product, description, public_profile, upload_timeout=900):
        self.click_add()
        self.click_upload_video()

        if self.has_visible_file_input():
            self.upload_files(file_paths)
            self.click_next()
        else:
            self.select_account(account)
            self.choose_product(product)
            self.click_next()
            self.upload_files(file_paths)

        result = self.wait_upload_result(timeout=upload_timeout)
        if result == "invalid":
            return [("invalid", "TikTok báo batch có video không hợp lệ; batch đã dừng.") for _ in file_paths]

        if result == "next":
            self.click_next_step()
        self.click_confirm(timeout=upload_timeout)
        self.fill_description(description)
        self.set_public_profile(public_profile)
        self.click_save()
        return [("success", "Đã upload và lưu.") for _ in file_paths]
