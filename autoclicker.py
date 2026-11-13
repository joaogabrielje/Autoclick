import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import pyautogui
import keyboard
import time
import json
import os
import sys
import math
import re
import ctypes
from ctypes import wintypes

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


def config_path():
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA')
        if not appdata:
            raise RuntimeError("Não foi possível localizar a pasta de configurações do Windows (APPDATA).")
        return os.path.join(appdata, 'AutoClicker Pro', 'autoclick_config.json')
    return 'autoclick_config.json'


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t),
    ]


class KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class InputData(ctypes.Union):
    _fields_ = [("mi", MouseInput), ("ki", KeyboardInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("data", InputData)]


def send_mouse_button(button, pressed):
    flags = {
        'left': (0x0002, 0x0004),
        'right': (0x0008, 0x0010),
        'middle': (0x0020, 0x0040),
    }
    if button not in flags:
        raise ValueError(f"Botão de mouse inválido: {button}")
    mouse_input = MouseInput(0, 0, 0, flags[button][0 if pressed else 1], 0, 0)
    event = Input(0, InputData(mi=mouse_input))
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    send_input = user32.SendInput
    send_input.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
    send_input.restype = wintypes.UINT
    if send_input(1, ctypes.byref(event), ctypes.sizeof(Input)) != 1:
        code = ctypes.get_last_error()
        raise OSError(
            f"Windows não aceitou o evento do mouse (erro {code}). "
            "Verifique se o aplicativo de destino está em modo administrador."
        )


class GlobalHotkeys:
    def __init__(self, events):
        self.events = events
        self.ready = threading.Event()
        self.error = None
        self.thread_id = None
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        if not self.ready.wait(3):
            raise RuntimeError("Tempo esgotado ao registrar atalhos globais.")
        if self.error:
            self.thread.join(timeout=3)
            raise RuntimeError(self.error)

    def _listen(self):
        user32 = None
        registered = []
        try:
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            user32.RegisterHotKey.restype = wintypes.BOOL
            user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
            user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
            user32.GetMessageW.restype = ctypes.c_int
            self.thread_id = kernel32.GetCurrentThreadId()
            message = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
            for hotkey_id, virtual_key, name in ((1, 0x75, 'F6'), (2, 0x76, 'F7')):
                if not user32.RegisterHotKey(None, hotkey_id, 0x4000, virtual_key):
                    raise OSError(f"{name} indisponível (erro Windows {ctypes.get_last_error()}); pode estar em uso por outro programa.")
                registered.append(hotkey_id)
            self.ready.set()
            while True:
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == 0:
                    break
                if result == -1:
                    raise OSError(f"Falha ao receber atalhos (erro Windows {ctypes.get_last_error()}).")
                if message.message == 0x0312:
                    self.events.put('start' if message.wParam == 1 else 'stop')
        except Exception as exc:
            self.error = str(exc)
            if self.ready.is_set():
                self.events.put(('error', self.error))
            else:
                self.ready.set()
        finally:
            for hotkey_id in registered:
                user32.UnregisterHotKey(None, hotkey_id)

    def close(self):
        if self.thread.is_alive():
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.PostThreadMessageW.restype = wintypes.BOOL
            if not user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0):
                raise OSError(f"Falha ao liberar atalhos (erro Windows {ctypes.get_last_error()}).")
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("Não foi possível encerrar os atalhos globais.")


class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoClicker Pro")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        self.actions = []
        self.is_running = False
        self.stop_event = threading.Event()
        self.closing = False
        self.current_action_index = 0
        self.hotkey_events = queue.SimpleQueue()
        self.hotkeys = None
        
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.register_hotkeys()
        self.root.after(25, self.process_hotkeys)
        
    def setup_ui(self):
        # Frame superior - Informações
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="AutoClicker Pro", font=("Arial", 14, "bold")).pack()
        ttk.Label(top_frame, text="F6: iniciar | F7: parar (globais) | ESC: fechar quando em foco").pack()
        self.status_var = tk.StringVar(value="Pronto")
        ttk.Label(top_frame, textvariable=self.status_var).pack()
        
        # Frame de ações
        actions_frame = ttk.LabelFrame(self.root, text="Ações Registradas", padding=10)
        actions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar para lista de ações
        scrollbar = ttk.Scrollbar(actions_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.actions_listbox = tk.Listbox(
            actions_frame, 
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
            height=12
        )
        self.actions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.actions_listbox.yview)
        
        # Frame de botões de ação
        action_buttons_frame = ttk.Frame(self.root)
        action_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(action_buttons_frame, text="Adicionar Click", command=self.add_click).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_buttons_frame, text="Adicionar Tecla", command=self.add_key).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_buttons_frame, text="Adicionar Delay", command=self.add_delay).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_buttons_frame, text="Remover Ação", command=self.remove_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_buttons_frame, text="Limpar Tudo", command=self.clear_actions).pack(side=tk.LEFT, padx=5)
        
        # Frame de controle
        control_frame = ttk.LabelFrame(self.root, text="Controle", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="Iniciar (F6)", command=self.start_execution, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Parar (F7)", command=self.stop_execution, width=20).pack(side=tk.LEFT, padx=5)
        
        # Frame de configurações
        config_frame = ttk.LabelFrame(self.root, text="Configurações", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        repeat_frame = ttk.Frame(config_frame)
        repeat_frame.pack(fill=tk.X)
        ttk.Label(repeat_frame, text="Repetições:").pack(side=tk.LEFT, padx=5)
        self.repeat_var = tk.IntVar(value=1)
        self.repeat_spinbox = ttk.Spinbox(repeat_frame, from_=1, to=1000, textvariable=self.repeat_var, width=10)
        self.repeat_spinbox.pack(side=tk.LEFT, padx=5)
        self.repeat_until_stopped_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(repeat_frame, text="Repetir até parar (F7)",
                        variable=self.repeat_until_stopped_var,
                        command=self.update_repeat_controls).pack(side=tk.LEFT, padx=5)

        delay_frame = ttk.Frame(config_frame)
        delay_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(delay_frame, text="Espera entre repetições (ms):").pack(side=tk.LEFT, padx=5)
        self.repeat_delay_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(delay_frame, from_=0, to=60000, textvariable=self.repeat_delay_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Frame inferior - Botões de arquivo
        file_frame = ttk.Frame(self.root)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(file_frame, text="Salvar Configuração", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Carregar Configuração", command=self.load_config).pack(side=tk.LEFT, padx=5)
        
        self.root.bind_all('<Escape>', lambda e: self.exit_app())

    def update_repeat_controls(self):
        self.repeat_spinbox.configure(state='disabled' if self.repeat_until_stopped_var.get() else 'normal')

    def register_hotkeys(self):
        try:
            self.hotkeys = GlobalHotkeys(self.hotkey_events)
        except Exception as exc:
            messagebox.showerror(
                "Erro nos atalhos",
                f"Não foi possível registrar F6 e F7: {exc}\n"
                "Use os botões da janela e verifique as permissões do Windows."
            )

    def unregister_hotkeys(self):
        if self.hotkeys is not None:
            self.hotkeys.close()
            self.hotkeys = None

    def process_hotkeys(self):
        if self.closing:
            return
        while True:
            try:
                command = self.hotkey_events.get_nowait()
            except queue.Empty:
                break
            if command == 'stop':
                self.stop_execution()
            elif command == 'start' and not self.is_running and self.root.grab_current() is None:
                self.start_execution()
            elif isinstance(command, tuple) and command[0] == 'error':
                messagebox.showerror("Erro nos atalhos", command[1])
        self.root.after(25, self.process_hotkeys)

    def add_click(self):
        dialog = ClickDialog(self.root)
        if dialog.result:
            x, y, button, hold, delay, count, interval = dialog.result
            self.actions.append({
                'type': 'click',
                'x': x,
                'y': y,
                'button': button,
                'hold': hold,
                'delay': delay,
                'count': count,
                'interval': interval
            })
            self.update_listbox()
    
    def add_key(self):
        dialog = KeyDialog(self.root)
        if dialog.result:
            key, hold_time, delay = dialog.result
            self.actions.append({
                'type': 'key',
                'key': key,
                'hold': hold_time,
                'delay': delay
            })
            self.update_listbox()
    
    def add_delay(self):
        dialog = DelayDialog(self.root)
        if dialog.result is not None:
            delay = dialog.result
            self.actions.append({
                'type': 'delay',
                'time': delay
            })
            self.update_listbox()
    
    def remove_action(self):
        selection = self.actions_listbox.curselection()
        if selection:
            self.actions.pop(selection[0])
            self.update_listbox()
    
    def clear_actions(self):
        if messagebox.askyesno("Confirmar", "Deseja limpar todas as ações?"):
            self.actions = []
            self.update_listbox()
    
    def update_listbox(self):
        self.actions_listbox.delete(0, tk.END)
        for i, action in enumerate(self.actions):
            if action['type'] == 'click':
                text = (f"{i+1}. Click ({action['x']}, {action['y']}) - {action['button']} - "
                        f"{action.get('count', 1)}x, intervalo: {action.get('interval', 0)}ms - "
                        f"Hold: {action.get('hold', 0)}ms - Delay após: {action['delay']}ms")
            elif action['type'] == 'key':
                text = f"{i+1}. Tecla '{action['key']}' - Hold: {action['hold']}ms - Delay: {action['delay']}ms"
            else:
                text = f"{i+1}. Delay de {action['time']}ms"
            self.actions_listbox.insert(tk.END, text)
    
    def start_execution(self):
        if not self.actions:
            messagebox.showwarning("Aviso", "Adicione ações antes de iniciar!")
            return
        
        if self.is_running:
            messagebox.showinfo("Info", "Já está em execução!")
            return

        if any(action['type'] == 'key' and
               re.search(r'(?<![a-z0-9])f[67](?![a-z0-9])', action['key'], re.IGNORECASE)
               for action in self.actions):
            messagebox.showerror("Erro", "F6 e F7 são reservadas para iniciar e parar. Remova essas teclas das ações.")
            return
        
        try:
            repetitions = None if self.repeat_until_stopped_var.get() else self.repeat_var.get()
            repeat_delay = self.repeat_delay_var.get()
            if (repetitions is not None and repetitions < 1) or not math.isfinite(repeat_delay) or repeat_delay < 0:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Erro", "Informe repetições válidas e um delay não negativo.")
            return

        self.stop_event.clear()
        self.is_running = True
        self.status_var.set("Executando...")
        thread = threading.Thread(target=self.execute_actions, args=(repetitions, repeat_delay, list(self.actions)))
        thread.daemon = True
        thread.start()
    
    def stop_execution(self):
        if self.is_running:
            self.stop_event.set()
            self.status_var.set("Parando...")
    
    def wait_ms(self, milliseconds, check_failsafe=False):
        deadline = time.monotonic() + milliseconds / 1000
        while not self.stop_event.is_set():
            if check_failsafe:
                pyautogui.failSafeCheck()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self.stop_event.wait(min(remaining, 0.05) if check_failsafe else remaining)

    def release_mouse(self, button):
        send_mouse_button(button, False)

    def execute_actions(self, repetitions, repeat_delay, actions):
        error = None
        try:
            rep = 0
            while repetitions is None or rep < repetitions:
                if self.stop_event.is_set():
                    break
                
                for action in actions:
                    if self.stop_event.is_set():
                        break
                    
                    if action['type'] == 'click':
                        hold_ms = action.get('hold', 0)
                        count = action.get('count', 1)
                        interval = action.get('interval', 0)
                        if (isinstance(count, bool) or not isinstance(count, int) or count < 1
                                or isinstance(interval, bool) or not isinstance(interval, (int, float))
                                or not math.isfinite(interval) or interval < 0):
                            raise ValueError("Quantidade ou intervalo de cliques inválido na configuração.")
                        for click_index in range(count):
                            if self.stop_event.is_set():
                                break
                            if hold_ms > 0:
                                pyautogui.moveTo(action['x'], action['y'])
                                pyautogui.failSafeCheck()
                                send_mouse_button(action['button'], True)
                                try:
                                    self.wait_ms(hold_ms, check_failsafe=True)
                                finally:
                                    self.release_mouse(action['button'])
                            else:
                                pyautogui.click(action['x'], action['y'], button=action['button'])
                            if click_index < count - 1 and not self.stop_event.is_set():
                                self.wait_ms(interval, check_failsafe=True)
                        self.wait_ms(action['delay'])
                    
                    elif action['type'] == 'key':
                        hold_ms = action.get('hold', 0)
                        if hold_ms > 0:
                            keyboard.press(action['key'])
                            try:
                                self.wait_ms(hold_ms)
                            finally:
                                keyboard.release(action['key'])
                        else:
                            keyboard.press_and_release(action['key'])
                        self.wait_ms(action['delay'])
                    
                    elif action['type'] == 'delay':
                        self.wait_ms(action['time'])
                
                rep += 1
                if (repetitions is None or rep < repetitions) and not self.stop_event.is_set():
                    self.wait_ms(repeat_delay)
        except Exception as e:
            error = str(e) or type(e).__name__
        self.root.after(0, self.execution_finished, error, self.stop_event.is_set())

    def execution_finished(self, error, stopped):
        self.is_running = False
        if self.closing:
            if error:
                messagebox.showerror("Erro", f"Erro durante execução: {error}")
            self.root.quit()
            return
        if error:
            self.status_var.set("Erro na execução")
            messagebox.showerror("Erro", f"Erro durante execução: {error}")
        elif stopped:
            self.status_var.set("Execução parada")
        else:
            self.status_var.set("Execução concluída")
    
    def save_config(self):
        if not self.actions:
            messagebox.showwarning("Aviso", "Nenhuma ação para salvar!")
            return
        
        try:
            filename = config_path()
            if getattr(sys, 'frozen', False):
                os.makedirs(os.path.dirname(filename), exist_ok=True)
            config = {
                'actions': self.actions,
                'repetitions': self.repeat_var.get(),
                'repeat_until_stopped': self.repeat_until_stopped_var.get(),
                'repeat_delay': self.repeat_delay_var.get()
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Sucesso", f"Configuração salva em {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {str(e)}")
    
    def load_config(self):
        try:
            filename = config_path()
            if not os.path.exists(filename):
                messagebox.showwarning("Aviso", f"Arquivo {filename} não encontrado!")
                return
            
            with open(filename, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            repeat_until_stopped = config.get('repeat_until_stopped', False)
            if not isinstance(repeat_until_stopped, bool):
                raise ValueError("O campo repeat_until_stopped deve ser verdadeiro ou falso.")
            self.actions = config.get('actions', [])
            self.repeat_var.set(config.get('repetitions', 1))
            self.repeat_until_stopped_var.set(repeat_until_stopped)
            self.update_repeat_controls()
            self.repeat_delay_var.set(config.get('repeat_delay', 1.0))
            self.update_listbox()
            messagebox.showinfo("Sucesso", "Configuração carregada!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar: {str(e)}")
    
    def exit_app(self):
        if self.closing:
            return
        self.closing = True
        self.stop_event.set()
        try:
            self.unregister_hotkeys()
        except (OSError, RuntimeError) as exc:
            messagebox.showerror("Erro nos atalhos", str(exc))
        if not self.is_running:
            self.root.quit()


class ClickDialog:
    def __init__(self, parent):
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.title("Adicionar Click")
        self.window.geometry("460x450")
        self.window.resizable(False, False)
        
        # Frame superior com coordenadas
        coords_frame = ttk.LabelFrame(self.window, text="Coordenadas", padding=10)
        coords_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # X e Y em uma linha
        ttk.Label(coords_frame, text="X:").pack(side=tk.LEFT, padx=5)
        self.x_var = tk.StringVar()
        self.x_entry = ttk.Entry(coords_frame, textvariable=self.x_var, font=("Arial", 10), width=12)
        self.x_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(coords_frame, text="Y:").pack(side=tk.LEFT, padx=5)
        self.y_var = tk.StringVar()
        self.y_entry = ttk.Entry(coords_frame, textvariable=self.y_var, font=("Arial", 10), width=12)
        self.y_entry.pack(side=tk.LEFT, padx=5)
        
        # Botões para capturar
        buttons_frame = ttk.Frame(self.window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="📍 Mover Janela", command=self.show_position_selector).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🔄 Posição Atual", command=self.get_current_position).pack(side=tk.LEFT, padx=5)
        
        # Frame com botão do mouse
        ttk.Label(self.window, text="Botão do Mouse:", font=("Arial", 10)).pack(pady=5)
        self.button_var = tk.StringVar(value="left")
        button_combo = ttk.Combobox(self.window, textvariable=self.button_var, values=["left", "right", "middle"], state="readonly", width=30)
        button_combo.pack()
        
        ttk.Label(self.window, text="Segurar botão (ms, 0 = clique rápido):", font=("Arial", 10)).pack(pady=5)
        self.hold_var = tk.DoubleVar(value=0)
        ttk.Spinbox(self.window, from_=0, to=60000, textvariable=self.hold_var, width=30).pack()

        burst_frame = ttk.Frame(self.window)
        burst_frame.pack(pady=5)
        ttk.Label(burst_frame, text="Quantidade de cliques:").grid(row=0, column=0, padx=5)
        ttk.Label(burst_frame, text="Intervalo entre cliques (ms):").grid(row=0, column=1, padx=5)
        self.count_var = tk.IntVar(value=1)
        ttk.Spinbox(burst_frame, from_=1, to=1000000, textvariable=self.count_var, width=14).grid(row=1, column=0, padx=5)
        self.interval_var = tk.DoubleVar(value=50)
        ttk.Spinbox(burst_frame, from_=0, to=60000, textvariable=self.interval_var, width=14).grid(row=1, column=1, padx=5)

        ttk.Label(self.window, text="Delay após todos os cliques (ms):", font=("Arial", 10)).pack(pady=5)
        self.delay_var = tk.DoubleVar(value=1)
        ttk.Spinbox(self.window, from_=0, to=60000, textvariable=self.delay_var, width=30).pack()
        
        # Instruções
        ttk.Label(self.window, text="💡 Clique em 'Mover Janela' e arraste a janela para o local desejado", 
                  font=("Arial", 8), foreground="gray").pack(pady=5)
        
        # Botões OK e Cancelar
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=15)
        
        ttk.Button(button_frame, text="✅ OK", command=self.ok_click).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancelar", command=self.window.destroy).pack(side=tk.LEFT, padx=5)
        
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)
    
    def show_position_selector(self):
        """Mostra uma janela pequena que pode ser movida para selecionar posição"""
        PositionSelector(self)
    
    def get_current_position(self):
        """Obtém a posição atual do mouse"""
        x, y = pyautogui.position()
        self.x_var.set(str(x))
        self.y_var.set(str(y))
        messagebox.showinfo("Posição Atual", f"Posição do mouse: ({x}, {y})")
    
    def ok_click(self):
        try:
            x = int(self.x_var.get())
            y = int(self.y_var.get())
            button = self.button_var.get()
            hold = float(self.hold_var.get())
            delay = float(self.delay_var.get())
            count = self.count_var.get()
            interval = float(self.interval_var.get())
            if not (1 <= count <= 1000000 and
                    all(math.isfinite(value) and 0 <= value <= 60000 for value in (hold, delay, interval))):
                raise ValueError
            self.result = (x, y, button, hold, delay, count, interval)
            self.window.destroy()
        except (ValueError, tk.TclError):
            messagebox.showerror("Erro", "Informe coordenadas inteiras, quantidade de 1 a 1000000 e tempos entre 0 e 60000 ms.", parent=self.window)


class PositionSelector:
    """Janela arrastável para selecionar posição"""
    def __init__(self, click_dialog):
        self.click_dialog = click_dialog
        self.press_x = 0
        self.press_y = 0

        self.selector_window = tk.Toplevel(click_dialog.window)
        self.selector_window.title("Posição")
        self.selector_window.resizable(False, False)
        self.selector_window.transient(click_dialog.window)
        self.selector_window.attributes('-topmost', True)
        self.selector_window.protocol("WM_DELETE_WINDOW", self.close)

        self.target = tk.Canvas(self.selector_window, width=160, height=70,
                                bg="#4CAF50", highlightthickness=0)
        self.target.pack(padx=5, pady=(5, 0))
        self.target.create_line(70, 35, 90, 35, fill="white", width=2)
        self.target.create_line(80, 25, 80, 45, fill="white", width=2)
        self.coords_label = ttk.Label(self.selector_window, text="Posição:")
        self.coords_label.pack(pady=3)
        self.confirm_btn = ttk.Button(self.selector_window, text="Salvar posição",
                                      command=self.confirm_position)
        self.confirm_btn.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.target.bind('<Button-1>', self.on_press)
        self.target.bind('<B1-Motion>', self.on_drag)
        self.selector_window.bind('<Configure>', self.update_position)
        self.selector_window.update_idletasks()
        self.selector_window.grab_set()
        self.update_position()
    
    def on_press(self, event):
        """Inicia arrasto"""
        self.press_x = event.x_root
        self.press_y = event.y_root
        self.start_x = self.selector_window.winfo_x()
        self.start_y = self.selector_window.winfo_y()
    
    def on_drag(self, event):
        """Arrasta a janela"""
        new_x = self.start_x + (event.x_root - self.press_x)
        new_y = self.start_y + (event.y_root - self.press_y)
        self.selector_window.geometry(f"{new_x:+d}{new_y:+d}")
    
    def update_position(self, event=None):
        x = self.target.winfo_rootx() + self.target.winfo_width() // 2
        y = self.target.winfo_rooty() + self.target.winfo_height() // 2
        self.coords_label.config(text=f"Posição: ({x}, {y})")
    
    def confirm_position(self):
        self.selector_window.update_idletasks()
        x = self.target.winfo_rootx() + self.target.winfo_width() // 2
        y = self.target.winfo_rooty() + self.target.winfo_height() // 2
        self.click_dialog.x_var.set(str(x))
        self.click_dialog.y_var.set(str(y))
        self.close()

    def close(self):
        self.selector_window.grab_release()
        self.selector_window.destroy()
        self.click_dialog.window.grab_set()


class KeyDialog:
    def __init__(self, parent):
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.title("Adicionar Tecla")
        self.window.geometry("400x250")
        self.window.resizable(False, False)
        
        ttk.Label(self.window, text="Tecla (ex: 'a', 'enter', 'space'):", font=("Arial", 10)).pack(pady=5)
        self.key_var = tk.StringVar()
        ttk.Entry(self.window, textvariable=self.key_var, font=("Arial", 10)).pack()
        
        ttk.Label(self.window, text="Hold (milisegundos, 0 = rápido):", font=("Arial", 10)).pack(pady=5)
        self.hold_var = tk.DoubleVar(value=0)
        ttk.Spinbox(self.window, from_=0, to=60000, textvariable=self.hold_var).pack()
        
        ttk.Label(self.window, text="Delay após ação (milisegundos, mín 1):", font=("Arial", 10)).pack(pady=5)
        self.delay_var = tk.DoubleVar(value=1)
        ttk.Spinbox(self.window, from_=0, to=60000, textvariable=self.delay_var).pack()
        
        ttk.Label(self.window, text="Exemplos: a, enter, space, shift, ctrl, alt, tab", font=("Arial", 8), foreground="gray").pack(pady=5)
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.ok_click).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.window.destroy).pack(side=tk.LEFT, padx=5)
        
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)
    
    def ok_click(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showerror("Erro", "Informe uma tecla!")
            return
        
        hold = float(self.hold_var.get())
        delay = float(self.delay_var.get())
        self.result = (key, hold, delay)
        self.window.destroy()


class DelayDialog:
    def __init__(self, parent):
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.title("Adicionar Delay")
        self.window.geometry("300x150")
        self.window.resizable(False, False)
        
        ttk.Label(self.window, text="Tempo de espera (ms):", font=("Arial", 10)).pack(pady=20)
        self.delay_var = tk.DoubleVar(value=1)
        ttk.Spinbox(self.window, from_=0, to=300000, textvariable=self.delay_var).pack()
        
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok_click).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.window.destroy).pack(side=tk.LEFT, padx=5)
        
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)
    
    def ok_click(self):
        try:
            delay = float(self.delay_var.get())
            if not math.isfinite(delay) or not 0 <= delay <= 300000:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Erro", "Informe uma espera entre 0 e 300000 ms.", parent=self.window)
            return
        self.result = delay
        self.window.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClickerApp(root)
    root.mainloop()
