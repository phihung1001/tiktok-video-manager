import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import (
    ElementClickInterceptedException, ElementNotInteractableException,
    StaleElementReferenceException, TimeoutException,
)

from automation.confirm_form import CONFIRM_FORM_SNAPSHOT, CONFIRM_POINTER_SAFE, SET_DESCRIPTION
from automation.seller_center import SellerCenter


class PollWait:
    """Deterministic polling; no real sleep or Chrome for state-machine tests."""
    def __init__(self, driver, timeout, poll_frequency):
        self.driver = driver

    def until(self, predicate):
        for _ in range(8):
            result = predicate(self.driver)
            if result:
                return result
        raise TimeoutException()


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.driver = Mock()
        self.events = []
        self.checkpoint = Mock()
        self.seller = SellerCenter(self.driver, self.events.append, self.checkpoint)
        self.button = Mock()
        self.field = Mock()
        self.wizard = {"confirm": self.button, "step3Visible": True, "confirmCount": 1,
                       "readyConfirmCount": 1, "formReady": False}
        self.form = {"formReady": True, "description": self.field, "step3Visible": False}
        self.wait_patch = patch('automation.seller_center.WebDriverWait', side_effect=PollWait)
        self.wait = self.wait_patch.start()
        self.addCleanup(self.wait_patch.stop)

    def snapshots(self, values):
        values = iter(values)
        current = {}

        def execute(script, *args):
            nonlocal current
            if script == CONFIRM_POINTER_SAFE:
                return False
            self.assertEqual(script, CONFIRM_FORM_SNAPSHOT)
            current = next(values, current)
            return current
        self.driver.execute_script.side_effect = execute

    def test_waits_for_form_after_native_click_and_does_not_click_twice(self):
        self.snapshots([self.wizard, self.wizard, {}, self.form])
        self.seller.click_confirm(timeout=37)
        self.button.click.assert_called_once_with()
        self.assertEqual(self.driver.execute_script.call_count, 4)
        self.wait.assert_called_once_with(self.driver, 37, poll_frequency=0.1)

    def test_disabled_button_is_not_clicked_until_enabled(self):
        self.snapshots([dict(self.wizard, confirm=None, readyConfirmCount=0), self.wizard, self.form])
        self.seller.click_confirm()
        self.button.click.assert_called_once_with()

    def test_rejected_clicks_can_retry_without_js_force_click(self):
        for error in (ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException):
            with self.subTest(error=error.__name__):
                self.button.reset_mock()
                self.button.click.side_effect = [error(), None]
                self.snapshots([self.wizard, self.wizard, self.form])
                self.seller.click_confirm()
                self.assertEqual(self.button.click.call_count, 2)

    def test_click_with_no_transition_times_out_in_confirmation_not_description(self):
        self.snapshots([self.wizard])
        with self.assertRaisesRegex(TimeoutException, 'Đã nhấn Xác nhận nhưng chưa chuyển'):
            self.seller.click_confirm(timeout=2)
        self.button.click.assert_called_once_with()

    def test_verified_shadow_host_uses_pointer_fallback(self):
        self.button.click.side_effect = ElementClickInterceptedException('Own shadow host')
        self.driver.execute_script.side_effect = [self.wizard, True, self.form]
        with patch('automation.seller_center.ActionChains') as actions:
            self.seller.click_confirm()
            actions.return_value.move_to_element.assert_called_once_with(self.button)
            actions.return_value.move_to_element.return_value.click.return_value.perform.assert_called_once_with()

    def test_unrelated_overlay_never_uses_pointer_fallback(self):
        self.button.click.side_effect = ElementClickInterceptedException('Unrelated overlay')
        self.snapshots([self.wizard])
        with patch('automation.seller_center.ActionChains') as actions:
            with self.assertRaisesRegex(TimeoutException, 'Unrelated overlay'):
                self.seller.click_confirm(timeout=1)
            actions.assert_not_called()

    def test_no_button_reports_specific_error(self):
        self.snapshots([dict(self.wizard, confirm=None, readyConfirmCount=0)])
        with self.assertRaisesRegex(TimeoutException, 'Chưa nhấn được đúng nút Xác nhận'):
            self.seller.click_confirm(timeout=1)
        self.button.click.assert_not_called()

    def test_none_dom_result_is_safe(self):
        self.snapshots([None, self.wizard, self.form])
        self.seller.click_confirm()
        self.button.click.assert_called_once_with()

    def test_stop_propagates_without_click(self):
        self.checkpoint.side_effect = RuntimeError('STOP_REQUESTED')
        with self.assertRaisesRegex(RuntimeError, 'STOP_REQUESTED'):
            self.seller.click_confirm()
        self.driver.execute_script.assert_not_called()

    def test_already_open_form_does_not_click_another_confirmation(self):
        self.snapshots([self.form])
        self.seller.click_confirm()
        self.button.click.assert_not_called()

    def test_delayed_editor_is_polled_before_setting_description(self):
        self.driver.execute_script.side_effect = [self.wizard, {}, self.form, True]
        self.seller.fill_description('Mô tả mới')
        self.driver.execute_script.assert_called_with(SET_DESCRIPTION, self.field, 'Mô tả mới')
        self.assertEqual(self.driver.execute_script.call_count, 4)

    def test_replaced_editor_is_rediscovered(self):
        replacement = Mock()
        self.driver.execute_script.side_effect = [self.form, StaleElementReferenceException(),
                                                 dict(self.form, description=replacement), True]
        self.seller.fill_description('Mô tả')
        self.driver.execute_script.assert_called_with(SET_DESCRIPTION, replacement, 'Mô tả')

    def test_description_is_never_filled_while_wizard_visible(self):
        self.snapshots([self.wizard])
        with self.assertRaisesRegex(TimeoutException, 'Màn hình mô tả chưa sẵn sàng'):
            self.seller.fill_description('text', timeout=1)

    def test_empty_description_skips_writing_only(self):
        self.seller.fill_description('')
        self.driver.execute_script.assert_not_called()

    def test_batch_preserves_existing_send_and_next_steps_and_forwards_timeout(self):
        for description in ('Mô tả', ''):
            with self.subTest(description=description):
                seller = SellerCenter(Mock(), Mock(), Mock())
                order = []
                for name in ('click_add', 'click_upload_video', 'select_account', 'choose_product',
                             'click_next', 'upload_files', 'click_next_step', 'click_confirm',
                             'fill_description', 'set_public_profile', 'click_save'):
                    setattr(seller, name, Mock(side_effect=lambda *a, _name=name, **k: order.append(_name)))
                seller.has_visible_file_input = Mock(return_value=False)
                seller.wait_upload_result = Mock(return_value='next')
                paths = [f'video-{i}.mp4' for i in range(10)]
                result = seller.upload_many(paths, 'account', '', description, True, upload_timeout=41)
                seller.upload_files.assert_called_once_with(paths)
                seller.click_confirm.assert_called_once_with(timeout=41)
                self.assertLess(order.index('click_confirm'), order.index('fill_description'))
                self.assertEqual(len(result), 10)

    def test_failed_transition_never_fills_or_saves_batch(self):
        self.seller.click_add = Mock()
        self.seller.click_upload_video = Mock()
        self.seller.has_visible_file_input = Mock(return_value=True)
        self.seller.upload_files = Mock()
        self.seller.click_next = Mock()
        self.seller.wait_upload_result = Mock(return_value='confirm')
        self.seller.fill_description = Mock()
        self.seller.click_save = Mock()
        self.snapshots([self.wizard])
        with self.assertRaises(TimeoutException):
            self.seller.upload_many(['video.mp4'], '', '', 'text', True, upload_timeout=2)
        self.seller.fill_description.assert_not_called()
        self.seller.click_save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
