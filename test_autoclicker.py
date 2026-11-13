import json
import os
import queue
import threading
import time
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import autoclicker


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.app = autoclicker.AutoClickerApp.__new__(autoclicker.AutoClickerApp)
        self.app.stop_event = threading.Event()
        self.app.root = Mock()
        self.app.actions = []
        self.app.repeat_var = Mock()
        self.app.repeat_var.get.return_value = 1
        self.app.repeat_until_stopped_var = Mock()
        self.app.repeat_until_stopped_var.get.return_value = True
        self.app.update_repeat_controls = Mock()
        self.app.repeat_delay_var = Mock()
        self.app.repeat_delay_var.get.return_value = 1
        self.click = {'type': 'click', 'x': 100, 'y': 200, 'button': 'right', 'delay': 1}

    def test_quick_click_without_hold_field(self):
        with patch.object(autoclicker.pyautogui, 'click') as click:
            self.app.execute_actions(1, 0, [self.click])
        click.assert_called_once_with(100, 200, button='right')
        self.assertEqual(autoclicker.pyautogui.PAUSE, 0)
        self.assertEqual(self.app.root.after.call_args.args[2:], (None, False))

    def test_hold_press_wait_release_and_delay(self):
        action = dict(self.click, hold=25, delay=7)
        events = []
        with patch.object(autoclicker.pyautogui, 'moveTo') as move, \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'), \
             patch.object(autoclicker, 'send_mouse_button', side_effect=lambda button, pressed: events.append('down' if pressed else 'up')) as send, \
             patch.object(self.app, 'wait_ms', side_effect=lambda ms, **k: events.append((ms, k))):
            self.app.execute_actions(1, 0, [action])
        move.assert_called_once_with(100, 200)
        self.assertEqual(send.call_args_list, [unittest.mock.call('right', True), unittest.mock.call('right', False)])
        self.assertEqual(events, ['down', (25, {'check_failsafe': True}), 'up', (7, {})])

    def test_stop_interrupts_hold_and_releases_button(self):
        pressed = threading.Event()
        action = dict(self.click, hold=5000)
        with patch.object(autoclicker.pyautogui, 'moveTo'), \
             patch.object(autoclicker, 'send_mouse_button', side_effect=lambda button, down: pressed.set() if down else None) as send, \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'):
            thread = threading.Thread(target=self.app.execute_actions, args=(1, 0, [action]))
            thread.start()
            self.assertTrue(pressed.wait(1))
            self.app.stop_event.set()
            thread.join(1)
            self.assertFalse(thread.is_alive())
        self.assertEqual(send.call_args_list, [unittest.mock.call('right', True), unittest.mock.call('right', False)])
        self.assertEqual(self.app.root.after.call_args.args[2:], (None, True))

    def test_failsafe_releases_mouse_even_at_corner(self):
        action = dict(self.click, hold=1000)
        with patch.object(autoclicker.pyautogui, 'moveTo'), \
             patch.object(autoclicker.pyautogui, 'failSafeCheck', side_effect=[None, autoclicker.pyautogui.FailSafeException('corner')]), \
             patch.object(autoclicker, 'send_mouse_button') as send:
            self.app.execute_actions(1, 0, [action])
        self.assertEqual(send.call_args_list, [unittest.mock.call('right', True), unittest.mock.call('right', False)])
        self.assertEqual(self.app.root.after.call_args.args[2], 'corner')

    def test_sendinput_error_is_reported(self):
        action = dict(self.click, hold=1000)
        with patch.object(autoclicker.pyautogui, 'moveTo'), \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'), \
             patch.object(autoclicker, 'send_mouse_button', side_effect=OSError('envio bloqueado')):
            self.app.execute_actions(1, 0, [action])
        self.assertEqual(self.app.root.after.call_args.args[2], 'envio bloqueado')

    def test_sendinput_uses_correct_button_flags(self):
        import ctypes
        expected = {'left': (2, 4), 'right': (8, 16), 'middle': (32, 64)}
        api = Mock()
        api.SendInput.return_value = 1
        with patch.object(autoclicker.ctypes, 'WinDLL', return_value=api):
            for button, flags in expected.items():
                for pressed, flag in zip((True, False), flags):
                    autoclicker.send_mouse_button(button, pressed)
                    args = api.SendInput.call_args.args
                    event = ctypes.cast(args[1], ctypes.POINTER(autoclicker.Input)).contents
                    self.assertEqual((event.type, event.data.mi.dwFlags), (0, flag))
                    self.assertEqual(args[2], ctypes.sizeof(autoclicker.Input))

    def test_hold_is_saved_and_loaded(self):
        self.app.actions = [dict(self.click, hold=1500)]
        saved = {}
        def capture(file, mode, encoding=None):
            from io import StringIO
            stream = StringIO()
            original_close = stream.close
            def close():
                saved['json'] = stream.getvalue()
                original_close()
            stream.close = close
            return stream
        with patch('builtins.open', side_effect=capture), patch.object(autoclicker.messagebox, 'showinfo'):
            self.app.save_config()
        config = json.loads(saved['json'])
        self.assertEqual(config['actions'][0]['hold'], 1500)
        self.assertTrue(config['repeat_until_stopped'])
        from unittest.mock import mock_open
        with patch('builtins.open', mock_open(read_data=saved['json'])), \
             patch.object(autoclicker.os.path, 'exists', return_value=True), \
             patch.object(autoclicker.messagebox, 'showinfo'), \
             patch.object(self.app, 'update_listbox'):
            self.app.load_config()
        self.assertEqual(self.app.actions[0]['hold'], 1500)
        self.app.repeat_until_stopped_var.set.assert_called_once_with(True)

    def test_installed_config_uses_appdata(self):
        import tempfile
        from pathlib import Path
        self.app.actions = [dict(self.click, hold=1500)]
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {'APPDATA': directory}), \
             patch.object(autoclicker.sys, 'frozen', True, create=True), \
             patch.object(autoclicker.messagebox, 'showinfo'), \
             patch.object(self.app, 'update_listbox'):
            self.app.save_config()
            path = Path(directory) / 'AutoClicker Pro' / 'autoclick_config.json'
            self.assertTrue(path.is_file())
            self.app.actions = []
            self.app.load_config()
            self.assertEqual(self.app.actions[0]['hold'], 1500)

    def test_old_config_defaults_to_finite_repetitions(self):
        from unittest.mock import mock_open
        config = json.dumps({'actions': [self.click], 'repetitions': 3})
        with patch('builtins.open', mock_open(read_data=config)), \
             patch.object(autoclicker.os.path, 'exists', return_value=True), \
             patch.object(autoclicker.messagebox, 'showinfo'), \
             patch.object(self.app, 'update_listbox'):
            self.app.load_config()
        self.app.repeat_until_stopped_var.set.assert_called_once_with(False)
        self.app.repeat_var.set.assert_called_once_with(3)

    def test_burst_after_hold_repeats_in_correct_order(self):
        actions = [
            dict(self.click, hold=1100, delay=4000),
            dict(self.click, hold=0, delay=3000, count=3, interval=20),
        ]
        events = []
        with patch.object(autoclicker.pyautogui, 'moveTo'), \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'), \
             patch.object(autoclicker, 'send_mouse_button', side_effect=lambda b, pressed: events.append('down' if pressed else 'up')), \
             patch.object(autoclicker.pyautogui, 'click', side_effect=lambda *a, **k: events.append('click')), \
             patch.object(self.app, 'wait_ms', side_effect=lambda ms, **k: events.append(ms)):
            self.app.execute_actions(2, 100, actions)
        cycle = ['down', 1100, 'up', 4000, 'click', 20, 'click', 20, 'click', 3000]
        self.assertEqual(events, cycle + [100] + cycle)

    def test_stop_during_burst_interval_prevents_further_clicks(self):
        interval_started = threading.Event()
        action = dict(self.click, count=10, interval=5000)
        real_wait = self.app.wait_ms
        def wait(ms, **kwargs):
            if ms == 5000:
                interval_started.set()
            real_wait(ms, **kwargs)
        with patch.object(autoclicker.pyautogui, 'click') as click, \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'), \
             patch.object(self.app, 'wait_ms', side_effect=wait):
            thread = threading.Thread(target=self.app.execute_actions, args=(1, 0, [action]))
            thread.start()
            self.assertTrue(interval_started.wait(1))
            self.app.stop_event.set()
            thread.join(1)
            self.assertFalse(thread.is_alive())
        self.assertEqual(click.call_count, 1)

    def test_invalid_burst_reports_error(self):
        with patch.object(autoclicker.pyautogui, 'click') as click:
            self.app.execute_actions(1, 0, [dict(self.click, count=0)])
        click.assert_not_called()
        self.assertIn('inválido', self.app.root.after.call_args.args[2])

    def test_burst_config_round_trip(self):
        from unittest.mock import mock_open
        action = dict(self.click, count=12, interval=35)
        self.app.actions = [action]
        stream = mock_open()
        with patch('builtins.open', stream), patch.object(autoclicker.messagebox, 'showinfo'):
            self.app.save_config()
        saved = ''.join(call.args[0] for call in stream().write.call_args_list)
        self.assertEqual(json.loads(saved)['actions'][0], action)
        with patch('builtins.open', mock_open(read_data=saved)), \
             patch.object(autoclicker.os.path, 'exists', return_value=True), \
             patch.object(autoclicker.messagebox, 'showinfo'), \
             patch.object(self.app, 'update_listbox'):
            self.app.load_config()
        self.assertEqual(self.app.actions[0], action)

    def test_sequence_order_and_continuous_repetition(self):
        actions = [
            dict(self.click, hold=2000, delay=1000),
            dict(self.click, hold=0, delay=0, x=300),
            {'type': 'delay', 'time': 2500},
        ]
        events = []
        def wait(ms, **kwargs):
            events.append(('wait', ms))
            if events.count(('wait', 3000)) == 2:
                self.app.stop_event.set()
        with patch.object(autoclicker.pyautogui, 'moveTo', side_effect=lambda *a: events.append(('move', *a))), \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'), \
             patch.object(autoclicker, 'send_mouse_button', side_effect=lambda b, pressed: events.append(('mouse', pressed))), \
             patch.object(autoclicker.pyautogui, 'click', side_effect=lambda x, y, button: events.append(('click', x, y))), \
             patch.object(self.app, 'wait_ms', side_effect=wait):
            self.app.execute_actions(None, 3000, actions)
        cycle = [('move', 100, 200), ('mouse', True), ('wait', 2000), ('mouse', False),
                 ('wait', 1000), ('click', 300, 200), ('wait', 0), ('wait', 2500), ('wait', 3000)]
        self.assertEqual(events, cycle * 2)
        self.assertEqual(self.app.root.after.call_args.args[2:], (None, True))

    def test_stop_during_wait_prevents_next_action(self):
        entered_wait = threading.Event()
        actions = [dict(self.click, delay=0), {'type': 'delay', 'time': 5000}, dict(self.click, x=300)]
        real_wait = self.app.wait_ms
        def wait(ms, **kwargs):
            if ms == 5000:
                entered_wait.set()
            real_wait(ms, **kwargs)
        with patch.object(autoclicker.pyautogui, 'click') as click, \
             patch.object(self.app, 'wait_ms', side_effect=wait):
            thread = threading.Thread(target=self.app.execute_actions, args=(None, 0, actions))
            thread.start()
            self.assertTrue(entered_wait.wait(1))
            self.app.stop_event.set()
            thread.join(1)
            self.assertFalse(thread.is_alive())
        click.assert_called_once_with(100, 200, button='right')

    def test_configured_delays_and_repetition_are_applied(self):
        actions = [dict(self.click, hold=0, delay=1)]
        with patch.object(autoclicker.pyautogui, 'click'), \
             patch.object(self.app, 'wait_ms') as wait:
            self.app.execute_actions(3, 10, actions)
        self.assertEqual([call.args[0] for call in wait.call_args_list], [1, 10, 1, 10, 1])

    def test_real_click_path_has_no_100ms_pause(self):
        with patch.object(autoclicker.pyautogui, 'failSafeCheck'), \
             patch.object(autoclicker.pyautogui, '_mouseMoveDrag'), \
             patch.object(autoclicker.pyautogui.platformModule, '_click'):
            start = time.perf_counter()
            self.app.execute_actions(5, 1, [self.click])
            elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.3)

    def test_longer_delay_takes_longer(self):
        with patch.object(autoclicker.pyautogui, 'click'):
            start = time.perf_counter()
            self.app.execute_actions(3, 0, [dict(self.click, delay=1)])
            fast = time.perf_counter() - start
            start = time.perf_counter()
            self.app.execute_actions(3, 0, [dict(self.click, delay=80)])
            slow = time.perf_counter() - start
        self.assertGreater(slow - fast, 0.15)


class DialogTests(unittest.TestCase):
    def test_position_selector_save_and_cancel_restore_dialog(self):
        root = tk.Tk()
        root.geometry('350x200+100+100')
        root.update()
        dialog_window = tk.Toplevel(root)
        dialog_window.update()
        dialog_window.grab_set()
        dialog = SimpleNamespace(window=dialog_window, x_var=tk.StringVar(root), y_var=tk.StringVar(root))
        try:
            selector = autoclicker.PositionSelector(dialog)
            selector.selector_window.geometry('+250+180')
            root.update()
            self.assertTrue(selector.confirm_btn.winfo_ismapped())
            expected_x = selector.target.winfo_rootx() + selector.target.winfo_width() // 2
            expected_y = selector.target.winfo_rooty() + selector.target.winfo_height() // 2
            self.assertEqual(selector.coords_label.cget('text'), f'Posição: ({expected_x}, {expected_y})')
            selector.confirm_btn.invoke()
            self.assertEqual((dialog.x_var.get(), dialog.y_var.get()), (str(expected_x), str(expected_y)))
            self.assertEqual(dialog_window.grab_current(), dialog_window)

            selector = autoclicker.PositionSelector(dialog)
            selector.close()
            self.assertEqual((dialog.x_var.get(), dialog.y_var.get()), (str(expected_x), str(expected_y)))
            self.assertEqual(dialog_window.grab_current(), dialog_window)
        finally:
            root.destroy()

    def test_burst_fields_are_saved_from_dialog(self):
        root = tk.Tk()
        root.geometry('200x100+100+100')
        root.update()
        def fill_dialog():
            window = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            coordinate_frame = window.winfo_children()[0]
            entries = [w for w in coordinate_frame.winfo_children() if w.winfo_class() == 'TEntry']
            entries[0].insert(0, '100')
            entries[1].insert(0, '200')
            burst_frame = next(w for w in window.winfo_children()
                               if len([c for c in w.winfo_children() if c.winfo_class() == 'TSpinbox']) == 2)
            boxes = [w for w in burst_frame.winfo_children() if w.winfo_class() == 'TSpinbox']
            for box, value in zip(boxes, ('10', '25')):
                box.delete(0, tk.END)
                box.insert(0, value)
            ok = window.winfo_children()[-1].winfo_children()[0]
            ok.invoke()
        root.after(500, fill_dialog)
        root.after(3000, lambda: [w.destroy() for w in root.winfo_children() if isinstance(w, tk.Toplevel)])
        try:
            dialog = autoclicker.ClickDialog(root)
            self.assertEqual(dialog.result, (100, 200, 'left', 0, 1, 10, 25))
        finally:
            root.destroy()

    def test_repeat_checkbox_disables_count_and_restores_it(self):
        root = tk.Tk()
        root.withdraw()
        with patch.object(autoclicker, 'GlobalHotkeys'):
            app = autoclicker.AutoClickerApp(root)
            try:
                app.repeat_var.set(4)
                app.repeat_until_stopped_var.set(True)
                app.update_repeat_controls()
                self.assertEqual(str(app.repeat_spinbox.cget('state')), 'disabled')
                app.repeat_until_stopped_var.set(False)
                app.update_repeat_controls()
                self.assertEqual(str(app.repeat_spinbox.cget('state')), 'normal')
                self.assertEqual(app.repeat_var.get(), 4)
            finally:
                app.exit_app()
                root.destroy()

    def test_continuous_sequence_stops_via_hotkey_queue(self):
        root = tk.Tk()
        root.withdraw()
        with patch.object(autoclicker, 'GlobalHotkeys'), \
             patch.object(autoclicker.pyautogui, 'moveTo'), \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'), \
             patch.object(autoclicker, 'send_mouse_button') as send, \
             patch.object(autoclicker.pyautogui, 'click') as click:
            app = autoclicker.AutoClickerApp(root)
            app.repeat_until_stopped_var.set(True)
            app.update_repeat_controls()
            app.repeat_delay_var.set(25)
            app.actions = [
                {'type': 'click', 'x': 100, 'y': 200, 'button': 'left', 'hold': 25, 'delay': 25},
                {'type': 'click', 'x': 300, 'y': 400, 'button': 'left', 'hold': 0, 'delay': 0},
            ]
            root.after(100, lambda: app.hotkey_events.put('start'))
            root.after(400, lambda: app.hotkey_events.put('stop'))
            root.after(650, root.quit)
            try:
                root.mainloop()
                self.assertFalse(app.is_running)
                self.assertEqual(app.status_var.get(), 'Execução parada')
                self.assertGreaterEqual(click.call_count, 2)
                self.assertIn(send.call_count, (2 * click.call_count, 2 * (click.call_count + 1)))
                self.assertEqual(send.call_count % 2, 0)
                self.assertEqual(send.call_args_list[-1], unittest.mock.call('left', False))
            finally:
                app.exit_app()
                root.destroy()
    def test_click_dialog_accepts_hold(self):
        root = tk.Tk()
        root.withdraw()
        def fill_dialog():
            window = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            coordinate_frame = window.winfo_children()[0]
            entries = [w for w in coordinate_frame.winfo_children() if w.winfo_class() == 'TEntry']
            entries[0].insert(0, '100')
            entries[1].insert(0, '200')
            spinboxes = [w for w in window.winfo_children() if w.winfo_class() == 'TSpinbox']
            spinboxes[0].delete(0, tk.END)
            spinboxes[0].insert(0, '2500')
            button_frame = window.winfo_children()[-1]
            button_frame.winfo_children()[0].invoke()
        root.after(100, fill_dialog)
        root.after(3000, lambda: [w.destroy() for w in root.winfo_children() if isinstance(w, tk.Toplevel)])
        try:
            dialog = autoclicker.ClickDialog(root)
            self.assertEqual(dialog.result, (100, 200, 'left', 2500, 1, 1, 50))
        finally:
            root.destroy()

    def test_running_hold_stops_from_gui_and_releases(self):
        root = tk.Tk()
        root.withdraw()
        with patch.object(autoclicker, 'GlobalHotkeys'), \
             patch.object(autoclicker.pyautogui, 'moveTo') as move, \
             patch.object(autoclicker, 'send_mouse_button') as send, \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'):
            app = autoclicker.AutoClickerApp(root)
            app.actions = [{'type': 'click', 'x': 100, 'y': 200, 'button': 'left', 'hold': 5000, 'delay': 1}]
            root.after(100, app.start_execution)
            root.after(250, app.stop_execution)
            root.after(500, root.quit)
            try:
                root.mainloop()
                self.assertFalse(app.is_running)
                move.assert_called_once_with(100, 200)
                self.assertEqual(send.call_args_list, [unittest.mock.call('left', True), unittest.mock.call('left', False)])
            finally:
                app.exit_app()
                root.destroy()

    def test_hotkey_queue_respects_dialog_and_stops_running(self):
        app = autoclicker.AutoClickerApp.__new__(autoclicker.AutoClickerApp)
        app.root = Mock()
        app.hotkey_events = queue.SimpleQueue()
        app.closing = False
        app.is_running = False
        app.start_execution = Mock()
        app.stop_execution = Mock()
        app.root.grab_current.return_value = object()
        app.hotkey_events.put('start')
        app.hotkey_events.put('stop')
        app.process_hotkeys()
        app.start_execution.assert_not_called()
        app.stop_execution.assert_called_once()
        app.root.grab_current.return_value = None
        app.hotkey_events.put('start')
        app.process_hotkeys()
        app.start_execution.assert_called_once()

    def test_failed_registration_reports_error(self):
        app = autoclicker.AutoClickerApp.__new__(autoclicker.AutoClickerApp)
        app.hotkey_events = queue.SimpleQueue()
        app.hotkeys = None
        with patch.object(autoclicker, 'GlobalHotkeys', side_effect=OSError('bloqueado')), \
             patch.object(autoclicker.messagebox, 'showerror') as error:
            app.register_hotkeys()
        self.assertIn('bloqueado', error.call_args.args[1])
        self.assertIsNone(app.hotkeys)

    def test_reserved_keys_cannot_be_automated(self):
        app = autoclicker.AutoClickerApp.__new__(autoclicker.AutoClickerApp)
        app.actions = [{'type': 'key', 'key': 'ctrl+F7'}]
        app.is_running = False
        with patch.object(autoclicker.messagebox, 'showerror') as error:
            app.start_execution()
        self.assertIn('reservadas', error.call_args.args[1])
        self.assertFalse(app.is_running)


@unittest.skipUnless(os.environ.get('AUTOCLICKER_TEST_REAL_MOUSE') == '1', 'Requer controle do mouse e uma área de trabalho visível')
class RealMouseTests(unittest.TestCase):
    def test_mouse_hold_reaches_tk_target(self):
        root = tk.Tk()
        root.geometry('250x160+100+100')
        root.attributes('-topmost', True)
        target = tk.Label(root, text='Teste de clique', bg='lightblue')
        target.pack(fill=tk.BOTH, expand=True)
        events = []
        target.bind('<ButtonPress-1>', lambda event: events.append(('down', time.monotonic())))
        target.bind('<ButtonRelease-1>', lambda event: events.append(('up', time.monotonic())))
        button_state = []
        app = autoclicker.AutoClickerApp.__new__(autoclicker.AutoClickerApp)
        app.root = root
        app.stop_event = threading.Event()
        app.is_running = True
        app.closing = False
        app.status_var = Mock()
        root.update()
        original_position = autoclicker.pyautogui.position()
        x = target.winfo_rootx() + target.winfo_width() // 2
        y = target.winfo_rooty() + target.winfo_height() // 2
        action = {'type': 'click', 'x': x, 'y': y, 'button': 'left', 'hold': 400, 'delay': 1}
        worker = None
        def start():
            nonlocal worker
            worker = threading.Thread(target=app.execute_actions, args=(1, 0, [action]))
            worker.start()
        root.after(200, start)
        root.after(400, lambda: button_state.append(bool(autoclicker.ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)))
        root.after(3000, root.quit)
        root.after(900, root.quit)
        try:
            with patch.object(autoclicker.messagebox, 'showinfo', side_effect=lambda *a: root.after(100, root.quit)), \
                 patch.object(autoclicker.messagebox, 'showerror', side_effect=lambda *a: root.after(100, root.quit)):
                root.mainloop()
            self.assertIsNotNone(worker)
            worker.join(1)
            self.assertFalse(worker.is_alive())
            self.assertEqual([event[0] for event in events], ['down', 'up'])
            self.assertGreaterEqual(events[1][1] - events[0][1], 0.35)
            self.assertEqual(button_state, [True])
        finally:
            app.stop_event.set()
            if worker is not None:
                worker.join(1)
            root.destroy()
            autoclicker.pyautogui.moveTo(*original_position)


@unittest.skipUnless(os.environ.get('AUTOCLICKER_TEST_REAL_HOTKEYS') == '1', 'Requer teclado e área de trabalho visível')
class RealHotkeyTests(unittest.TestCase):
    def test_conflict_reported_and_hotkeys_released(self):
        first = autoclicker.GlobalHotkeys(queue.SimpleQueue())
        try:
            with self.assertRaisesRegex(RuntimeError, 'F6 indisponível'):
                autoclicker.GlobalHotkeys(queue.SimpleQueue())
        finally:
            first.close()
        second = autoclicker.GlobalHotkeys(queue.SimpleQueue())
        second.close()

    def test_hotkeys_with_another_window_focused(self):
        root = tk.Tk()
        root.geometry('350x250+50+50')
        app = autoclicker.AutoClickerApp(root)
        app.actions = [{'type': 'click', 'x': 100, 'y': 200, 'button': 'left', 'hold': 5000, 'delay': 1}]
        target = tk.Toplevel(root)
        target.title('Janela de destino')
        target.geometry('250x150+500+100')
        tk.Entry(target).pack()
        results = []

        def send_f6():
            target.focus_force()
            results.append(('target_focused', root.focus_get() == target))
            threading.Thread(target=lambda: autoclicker.keyboard.send('f6'), daemon=True).start()

        def send_f7():
            results.append(('started', app.is_running))
            focused = root.focus_get()
            results.append(('still_focused', focused is not None and focused.winfo_toplevel() == target))
            threading.Thread(target=lambda: autoclicker.keyboard.send('f7'), daemon=True).start()

        def finish():
            results.append(('stopped', not app.is_running))
            root.quit()

        with patch.object(autoclicker.pyautogui, 'moveTo'), \
             patch.object(autoclicker.pyautogui, 'failSafeCheck'), \
             patch.object(autoclicker, 'send_mouse_button') as send:
            root.after(300, send_f6)
            root.after(1000, send_f7)
            root.after(1600, finish)
            try:
                root.mainloop()
                self.assertEqual(results, [('target_focused', True), ('started', True), ('still_focused', True), ('stopped', True)])
                self.assertEqual(send.call_args_list, [unittest.mock.call('left', True), unittest.mock.call('left', False)])
            finally:
                app.exit_app()
                target.destroy()
                root.destroy()


if __name__ == '__main__':
    unittest.main()
