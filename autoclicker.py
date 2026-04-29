import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import psutil

# Tenta importar pynput e pyautogui
try:
    import pynput.mouse as pmouse
    import pynput.keyboard as pkeyboard
    import pyautogui
    LIBS_OK = True
except ImportError:
    LIBS_OK = False

# ── Tentativa de importar win32
try:
    import win32gui
    import win32process
    WIN32_OK = True
except ImportError:
    WIN32_OK = False



#  Helpers


def get_open_windows():
    """Retorna lista de (hwnd, titulo, pid, nome_processo)."""
    if not WIN32_OK:
        return []
    windows = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    windows.append((hwnd, title, pid, proc.name()))
                except Exception:
                    windows.append((hwnd, title, 0, ""))

    win32gui.EnumWindows(callback, None)
    return windows


def get_foreground_hwnd():
    if WIN32_OK:
        return win32gui.GetForegroundWindow()
    return None



#  AutoClicker engine


class AutoClickerEngine:
    def __init__(self):
        self.running = False
        self._thread = None

    #  Conversores 

    def _parse_interval(self, horas, minutos, segundos, milissegundos):
        return (int(horas) * 3600 + int(minutos) * 60 +
                int(segundos) + int(milissegundos) / 1000)

    def _parse_key(self, key_str):
        """Converte string para objeto pynput Key ou KeyCode."""
        special = {
            "space": pkeyboard.Key.space,
            "enter": pkeyboard.Key.enter,
            "tab": pkeyboard.Key.tab,
            "esc": pkeyboard.Key.esc,
            "shift": pkeyboard.Key.shift,
            "ctrl": pkeyboard.Key.ctrl,
            "alt": pkeyboard.Key.alt,
            "backspace": pkeyboard.Key.backspace,
            "delete": pkeyboard.Key.delete,
            "up": pkeyboard.Key.up,
            "down": pkeyboard.Key.down,
            "left": pkeyboard.Key.left,
            "right": pkeyboard.Key.right,
            "f1": pkeyboard.Key.f1, "f2": pkeyboard.Key.f2,
            "f3": pkeyboard.Key.f3, "f4": pkeyboard.Key.f4,
            "f5": pkeyboard.Key.f5, "f6": pkeyboard.Key.f6,
            "f7": pkeyboard.Key.f7, "f8": pkeyboard.Key.f8,
            "f9": pkeyboard.Key.f9, "f10": pkeyboard.Key.f10,
            "f11": pkeyboard.Key.f11, "f12": pkeyboard.Key.f12,
        }
        k = key_str.strip().lower()
        return special.get(k, pkeyboard.KeyCode.from_char(k))

    #  Loop principal 

    def _loop(self, action, interval, target_hwnd, repeat, repeat_count, callback_status):
        mouse_ctrl = pmouse.Controller() if LIBS_OK else None
        kb_ctrl    = pkeyboard.Controller() if LIBS_OK else None

        count = 0
        while self.running:
            # Verificação de janela alvo
            if target_hwnd is not None:
                fg = get_foreground_hwnd()
                if fg != target_hwnd:
                    time.sleep(0.05)
                    continue

            # Executa ação
            try:
                atype = action["type"]
                if atype == "mouse_left":
                    mouse_ctrl.click(pmouse.Button.left)
                elif atype == "mouse_right":
                    mouse_ctrl.click(pmouse.Button.right)
                elif atype == "mouse_middle":
                    mouse_ctrl.click(pmouse.Button.middle)
                elif atype == "key":
                    key = self._parse_key(action["key"])
                    kb_ctrl.press(key)
                    kb_ctrl.release(key)
                elif atype == "scroll_up":
                    mouse_ctrl.scroll(0, 3)
                elif atype == "scroll_down":
                    mouse_ctrl.scroll(0, -3)
            except Exception as e:
                callback_status(f"Erro: {e}")
                self.running = False
                break

            count += 1
            callback_status(f"Cliques: {count}")

            if repeat and count >= repeat_count:
                self.running = False
                callback_status(f"Concluído — {count} cliques")
                break

            time.sleep(interval)

    def start(self, action, interval, target_hwnd, repeat, repeat_count, callback_status):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._loop,
            args=(action, interval, target_hwnd, repeat, repeat_count, callback_status),
            daemon=True
        )
        self._thread.start()

    def stop(self):
        self.running = False


#  Interface gráfica

class App(tk.Tk):
    COLORS = {
        "bg":       "#0f0f13",
        "panel":    "#17171f",
        "border":   "#2a2a3a",
        "accent":   "#6c63ff",
        "accent2":  "#ff6584",
        "green":    "#43d9a0",
        "text":     "#e8e8f0",
        "subtext":  "#8888aa",
        "entry_bg": "#1e1e2e",
    }

    def __init__(self):
        super().__init__()
        self.engine = AutoClickerEngine()
        self.hotkey_listener = None

        self.title("AutoClicker Pro")
        self.resizable(False, False)
        self.configure(bg=self.COLORS["bg"])

        self._build_ui()
        self._refresh_windows()
        self._setup_hotkey()

        # Aviso se libs faltando
        if not LIBS_OK:
            messagebox.showwarning(
                "Dependências",
                "Instale pynput e pyautogui:\n\npip install pynput pyautogui"
            )
        if not WIN32_OK:
            messagebox.showwarning(
                "Dependências",
                "Para filtrar por aba instale pywin32:\n\npip install pywin32"
            )

    #  Construção da UI 

    def _build_ui(self):
        C = self.COLORS
        pad = dict(padx=18, pady=8)

        # Título
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill="x", padx=18, pady=(18, 4))
        tk.Label(header, text="⚡ AutoClicker Pro", font=("Consolas", 20, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(side="left")
        self.lbl_status = tk.Label(header, text="● Parado", font=("Consolas", 11),
                                   bg=C["bg"], fg=C["accent2"])
        self.lbl_status.pack(side="right")

        sep = tk.Frame(self, bg=C["border"], height=1)
        sep.pack(fill="x", padx=18, pady=4)

        #  Ação 
        self._section("AÇÃO")
        action_frame = self._panel()

        tk.Label(action_frame, text="Tipo:", bg=C["panel"], fg=C["subtext"],
                 font=("Consolas", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=6)

        self.action_var = tk.StringVar(value="mouse_left")
        actions = [
            ("mouse_left",   "🖱  Clique Esquerdo"),
            ("mouse_right",  "🖱  Clique Direito"),
            ("mouse_middle", "🖱  Clique do Meio"),
            ("scroll_up",    "↑  Scroll Up"),
            ("scroll_down",  "↓  Scroll Down"),
            ("key",          "⌨  Tecla do Teclado"),
        ]
        self.action_combo = ttk.Combobox(
            action_frame, textvariable=self.action_var,
            values=[a[1] for a in actions], state="readonly", width=24,
            font=("Consolas", 10)
        )
        self._style_combo()
        self.action_labels = {a[1]: a[0] for a in actions}
        self.action_combo.current(0)
        self.action_combo.grid(row=0, column=1, padx=10, pady=6)
        self.action_combo.bind("<<ComboboxSelected>>", self._on_action_change)

        tk.Label(action_frame, text="Tecla:", bg=C["panel"], fg=C["subtext"],
                 font=("Consolas", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=4)
        self.key_entry = tk.Entry(action_frame, bg=C["entry_bg"], fg=C["text"],
                                  font=("Consolas", 11), width=10,
                                  insertbackground=C["accent"],
                                  relief="flat", bd=4)
        self.key_entry.insert(0, "f")
        self.key_entry.grid(row=1, column=1, sticky="w", padx=10, pady=4)
        self.key_row = (action_frame, 1)
        self._on_action_change()

        #  Intervalo 
        self._section("INTERVALO")
        iv = self._panel()

        labels = ["Horas", "Min", "Seg", "ms"]
        defaults = ["0", "0", "1", "0"]
        self.iv_vars = []
        for i, (lbl, val) in enumerate(zip(labels, defaults)):
            tk.Label(iv, text=lbl, bg=C["panel"], fg=C["subtext"],
                     font=("Consolas", 9)).grid(row=0, column=i*2, padx=(10,2))
            v = tk.StringVar(value=val)
            self.iv_vars.append(v)
            e = tk.Entry(iv, textvariable=v, width=5, bg=C["entry_bg"],
                         fg=C["text"], font=("Consolas", 11),
                         insertbackground=C["accent"], relief="flat", bd=4)
            e.grid(row=0, column=i*2+1, padx=(0, 6), pady=8)

        #  Repetição 
        self._section("REPETIÇÃO")
        rep = self._panel()

        self.repeat_var = tk.StringVar(value="infinito")
        tk.Radiobutton(rep, text="Infinito", variable=self.repeat_var,
                       value="infinito", bg=C["panel"], fg=C["text"],
                       selectcolor=C["accent"], activebackground=C["panel"],
                       font=("Consolas", 10), command=self._on_repeat_change
                       ).grid(row=0, column=0, padx=10, pady=6, sticky="w")
        tk.Radiobutton(rep, text="Repetir", variable=self.repeat_var,
                       value="repetir", bg=C["panel"], fg=C["text"],
                       selectcolor=C["accent"], activebackground=C["panel"],
                       font=("Consolas", 10), command=self._on_repeat_change
                       ).grid(row=0, column=1, padx=4, pady=6, sticky="w")
        self.repeat_count_var = tk.StringVar(value="10")
        self.repeat_entry = tk.Entry(rep, textvariable=self.repeat_count_var,
                                     width=7, bg=C["entry_bg"], fg=C["text"],
                                     font=("Consolas", 11),
                                     insertbackground=C["accent"],
                                     relief="flat", bd=4, state="disabled")
        self.repeat_entry.grid(row=0, column=2, padx=4)
        tk.Label(rep, text="vezes", bg=C["panel"], fg=C["subtext"],
                 font=("Consolas", 10)).grid(row=0, column=3, padx=(0,10))

        #  Janela alvo 
        self._section("JANELA ALVO")
        wf = self._panel()

        self.window_mode = tk.StringVar(value="todas")
        tk.Radiobutton(wf, text="Todas as janelas", variable=self.window_mode,
                       value="todas", bg=C["panel"], fg=C["text"],
                       selectcolor=C["accent"], activebackground=C["panel"],
                       font=("Consolas", 10), command=self._on_window_mode
                       ).grid(row=0, column=0, columnspan=2, padx=10, pady=(8,2), sticky="w")
        tk.Radiobutton(wf, text="Janela específica:", variable=self.window_mode,
                       value="especifica", bg=C["panel"], fg=C["text"],
                       selectcolor=C["accent"], activebackground=C["panel"],
                       font=("Consolas", 10), command=self._on_window_mode
                       ).grid(row=1, column=0, padx=10, pady=2, sticky="w")

        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(wf, textvariable=self.window_var,
                                         state="disabled", width=36,
                                         font=("Consolas", 9))
        self.window_combo.grid(row=2, column=0, columnspan=2, padx=10, pady=(2,8), sticky="w")

        btn_refresh = tk.Button(wf, text="↻ Atualizar", bg=C["border"], fg=C["text"],
                                font=("Consolas", 9), relief="flat", cursor="hand2",
                                command=self._refresh_windows)
        btn_refresh.grid(row=2, column=2, padx=6)

        # Contador
        self.lbl_count = tk.Label(self, text="Cliques: 0",
                                  bg=C["bg"], fg=C["subtext"],
                                  font=("Consolas", 10))
        self.lbl_count.pack(pady=(4, 2))

        # Hotkey info
        tk.Label(self, text="Hotkey: F6 = Iniciar/Parar",
                 bg=C["bg"], fg=C["subtext"], font=("Consolas", 9)).pack()

        # Botões
        btn_frame = tk.Frame(self, bg=C["bg"])
        btn_frame.pack(pady=14)

        self.btn_start = tk.Button(
            btn_frame, text="▶  INICIAR", width=14,
            bg=C["accent"], fg="white", font=("Consolas", 12, "bold"),
            relief="flat", cursor="hand2", bd=0,
            activebackground="#8b84ff", activeforeground="white",
            command=self.toggle
        )
        self.btn_start.pack(side="left", padx=8, ipady=8)

        tk.Button(
            btn_frame, text="✕  PARAR", width=12,
            bg=C["accent2"], fg="white", font=("Consolas", 12, "bold"),
            relief="flat", cursor="hand2", bd=0,
            activebackground="#ff85a0", activeforeground="white",
            command=self.stop
        ).pack(side="left", padx=8, ipady=8)

    def _section(self, title):
        C = self.COLORS
        tk.Label(self, text=title, bg=self.COLORS["bg"], fg=self.COLORS["subtext"],
                 font=("Consolas", 8, "bold")).pack(anchor="w", padx=20, pady=(10, 0))

    def _panel(self):
        C = self.COLORS
        f = tk.Frame(self, bg=C["panel"], bd=0, highlightthickness=1,
                     highlightbackground=C["border"])
        f.pack(fill="x", padx=18, pady=2)
        return f

    def _style_combo(self):
        style = ttk.Style()
        C = self.COLORS
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=C["entry_bg"],
                        background=C["entry_bg"],
                        foreground=C["text"],
                        selectbackground=C["accent"],
                        selectforeground="white",
                        bordercolor=C["border"],
                        arrowcolor=C["accent"])

    #  Eventos UI 

    def _on_action_change(self, *_):
        label = self.action_combo.get()
        key = self.action_labels.get(label, "mouse_left")
        self.action_var.set(key)
        state = "normal" if key == "key" else "disabled"
        self.key_entry.config(state=state)

    def _on_repeat_change(self):
        state = "normal" if self.repeat_var.get() == "repetir" else "disabled"
        self.repeat_entry.config(state=state)

    def _on_window_mode(self):
        state = "readonly" if self.window_mode.get() == "especifica" else "disabled"
        self.window_combo.config(state=state)

    def _refresh_windows(self):
        wins = get_open_windows()
        self._window_map = {f"[{pid}] {title[:60]}": hwnd
                            for hwnd, title, pid, _ in wins}
        self.window_combo["values"] = list(self._window_map.keys())
        if self._window_map:
            self.window_combo.current(0)

    #  Hotkey 

    def _setup_hotkey(self):
        if not LIBS_OK:
            return
        def on_press(key):
            if key == pkeyboard.Key.f6:
                self.after(0, self.toggle)
        self.hotkey_listener = pkeyboard.Listener(on_press=on_press)
        self.hotkey_listener.daemon = True
        self.hotkey_listener.start()

    #  Controles

    def _get_action(self):
        atype = self.action_var.get()
        if atype == "key":
            return {"type": "key", "key": self.key_entry.get() or "f"}
        return {"type": atype}

    def _get_interval(self):
        try:
            h, m, s, ms = [int(v.get()) for v in self.iv_vars]
            total = h * 3600 + m * 60 + s + ms / 1000
            return max(0.01, total)
        except ValueError:
            return 1.0

    def _get_target_hwnd(self):
        if self.window_mode.get() == "especifica":
            key = self.window_var.get()
            return self._window_map.get(key)
        return None

    def _status_cb(self, msg):
        self.after(0, lambda: self.lbl_count.config(text=msg))

    def toggle(self):
        if self.engine.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if not LIBS_OK:
            messagebox.showerror("Erro", "Instale pynput e pyautogui primeiro.")
            return
        action   = self._get_action()
        interval = self._get_interval()
        hwnd     = self._get_target_hwnd()
        repeat   = self.repeat_var.get() == "repetir"
        try:
            count = int(self.repeat_count_var.get())
        except ValueError:
            count = 10

        self.engine.start(action, interval, hwnd, repeat, count, self._status_cb)
        self.lbl_status.config(text="● Rodando", fg=self.COLORS["green"])
        self.btn_start.config(text="⏸  PAUSAR")

    def stop(self):
        self.engine.stop()
        self.lbl_status.config(text="● Parado", fg=self.COLORS["accent2"])
        self.btn_start.config(text="▶  INICIAR")

    def destroy(self):
        self.stop()
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        super().destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
