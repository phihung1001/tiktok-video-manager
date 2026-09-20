"""Opt-in local Chrome tests: no TikTok, saved profiles, videos or publishing."""
import os
from pathlib import Path
import unittest

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service

from automation.confirm_form import CONFIRM_POINTER_SAFE
from automation.seller_center import SellerCenter


@unittest.skipUnless(os.environ.get('RUN_CONFIRM_BROWSER_TESTS') == '1', 'Opt-in local Chrome test')
class ConfirmationBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1280,900')
        options.add_argument('--no-first-run')
        service = Service(executable_path=os.environ['TEST_CHROMEDRIVER']) if os.environ.get('TEST_CHROMEDRIVER') else Service()
        cls.driver = webdriver.Chrome(service=service, options=options)
        cls.addClassCleanup(cls.driver.quit)
        cls.driver.set_page_load_timeout(15)
        # Fail once at setup if this environment cannot load a Chrome tab.
        cls.driver.get((Path(__file__).parent / 'fixtures' / 'confirmation.html').resolve().as_uri())

    def setUp(self):
        self.events = []
        self.seller = SellerCenter(self.driver, self.events.append, lambda: None)

    def setup_page(self, **options):
        self.driver.execute_script('window.setup(arguments[0]);', options)

    def test_native_shadow_click_then_delayed_shadow_description(self):
        self.setup_page(transitionDelay=150, editorDelay=200)
        self.seller.click_confirm(timeout=4)
        self.seller.fill_description('Mô tả tiếng Việt 🎬', timeout=2)
        result = self.driver.execute_script('return [confirmClicks, editor.value, inputEvents, document.querySelector("main textarea").value];')
        self.assertEqual(result, [1, 'Mô tả tiếng Việt 🎬', 1, 'Do not edit'])

    def test_changed_component_version_inside_nested_shadow_root(self):
        self.setup_page(version='ks-button-9-9-9', nested=True)
        self.seller.click_confirm(timeout=3)
        self.seller.fill_description('text')
        self.assertEqual(self.driver.execute_script('return confirmClicks;'), 1)

    def test_regular_button_and_contenteditable_editor(self):
        self.setup_page(nativeButton=True, contentEditable=True)
        self.seller.click_confirm(timeout=3)
        self.seller.fill_description('Nội dung')
        self.assertEqual(self.driver.execute_script('return editor.textContent;'), 'Nội dung')

    def test_disabled_host_is_respected_then_clicked_when_enabled(self):
        self.setup_page(hostDisabled=True)
        self.assertIsNone(self.seller._confirm_form_snapshot()['confirm'])
        self.driver.execute_script('setTimeout(() => confirmHost.removeAttribute("disabled"), 250);')
        self.seller.click_confirm(timeout=3)
        self.assertEqual(self.driver.execute_script('return confirmClicks;'), 1)

    def test_disabled_inner_button_not_clicked(self):
        self.setup_page(buttonDisabled=True)
        self.assertIsNone(self.seller._confirm_form_snapshot()['confirm'])
        with self.assertRaisesRegex(TimeoutException, 'Chưa nhấn được đúng nút Xác nhận'):
            self.seller.click_confirm(timeout=.3)
        self.assertEqual(self.driver.execute_script('return confirmClicks;'), 0)

    def test_no_transition_does_not_accept_background_form_or_repeat_click(self):
        self.setup_page(noTransition=True, backgroundForm=True)
        with self.assertRaisesRegex(TimeoutException, 'Đã nhấn Xác nhận nhưng chưa chuyển'):
            self.seller.click_confirm(timeout=.4)
        self.assertEqual(self.driver.execute_script('return [confirmClicks, editor.value];'), [1, ''])

    def test_two_visible_confirmations_are_not_guessed(self):
        self.setup_page(duplicate=True)
        snapshot = self.seller._confirm_form_snapshot()
        self.assertEqual(snapshot['confirmCount'], 2)
        self.assertIsNone(snapshot['confirm'])

    def test_display_contents_wrapper_does_not_hide_editor(self):
        self.setup_page(lightEditor=True)
        self.driver.execute_script('document.querySelector("test-editor").style.display = "contents";')
        self.seller.click_confirm(timeout=3)
        self.seller.fill_description('text')
        self.assertEqual(self.driver.execute_script('return editor.value;'), 'text')

    def test_unrelated_overlay_is_not_clicked_through(self):
        self.setup_page()
        self.driver.execute_script('''
            window.overlayClicks = 0;
            const overlay = document.createElement('main');
            overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;background:white';
            overlay.onclick = () => overlayClicks++;
            document.body.append(overlay);
        ''')
        button = self.seller._confirm_form_snapshot()['confirm']
        self.assertFalse(self.driver.execute_script(CONFIRM_POINTER_SAFE, button))
        with self.assertRaisesRegex(TimeoutException, 'Chưa nhấn được đúng nút Xác nhận'):
            self.seller.click_confirm(timeout=.3)
        self.assertEqual(self.driver.execute_script('return [confirmClicks, overlayClicks];'), [0, 0])

    def test_inner_shadow_overlay_is_not_clicked_through(self):
        self.setup_page()
        button = self.seller._confirm_form_snapshot()['confirm']
        self.driver.execute_script('''
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;background:white';
            confirmHost.shadowRoot.append(overlay);
        ''')
        self.assertFalse(self.driver.execute_script(CONFIRM_POINTER_SAFE, button))

    def test_host_becoming_disabled_blocks_pointer_fallback(self):
        self.setup_page()
        button = self.seller._confirm_form_snapshot()['confirm']
        self.driver.execute_script('confirmHost.setAttribute("aria-disabled", "true");')
        self.assertFalse(self.driver.execute_script(CONFIRM_POINTER_SAFE, button))

    def test_role_button_host_is_not_counted_twice(self):
        self.setup_page()
        self.driver.execute_script('confirmHost.setAttribute("role", "button");')
        self.assertEqual(self.seller._confirm_form_snapshot()['confirmCount'], 1)
        self.seller.click_confirm(timeout=3)
        self.assertEqual(self.driver.execute_script('return confirmClicks;'), 1)


if __name__ == '__main__':
    unittest.main()
