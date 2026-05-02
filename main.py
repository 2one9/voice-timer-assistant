from __future__ import annotations

import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import scrolledtext

import pystray
from PIL import Image, ImageDraw
from pynput import keyboard

from audio_recorder import AudioRecorder
from intent_router import IntentRouter
from speech_to_text import SpeechToText
from tts import TTS


alt_pressed = False
backtick_pressed = False
recording = False
listening_enabled = True

recorder = AudioRecorder()
state_lock = threading.Lock()
stop_event = threading.Event()
show_log_event = threading.Event()
tray_icon: pystray.Icon | None = None
keyboard_listener: keyboard.Listener | None = None
log_window: LogWindow | None = None


class LogWindow:
    def __init__(self) -> None:
        self.queue: queue.Queue[str] = queue.Queue()
        self.root = tk.Tk()
        self.root.title("语音助手日志")
        self.root.geometry("760x420")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self.text = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Microsoft YaHei UI", 10),
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        self.root.withdraw()

    def write(self, text: str) -> None:
        self.queue.put(text)

    def poll(self) -> None:
        while True:
            try:
                text = self.queue.get_nowait()
            except queue.Empty:
                break

            self.text.configure(state=tk.NORMAL)
            self.text.insert(tk.END, text)
            self.text.see(tk.END)
            self.text.configure(state=tk.DISABLED)

        self.root.update_idletasks()
        self.root.update()

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))

    def hide(self) -> None:
        self.root.withdraw()

    def destroy(self) -> None:
        self.root.destroy()


class TeeOutput:
    def __init__(self, original) -> None:
        self.original = original

    def write(self, text: str) -> int:
        if self.original is not None:
            self.original.write(text)
            self.original.flush()

        if log_window is not None:
            log_window.write(text)

        return len(text)

    def flush(self) -> None:
        if self.original is not None:
            self.original.flush()


def handle_audio_file(audio_path) -> None:
    stt = SpeechToText()
    router = IntentRouter()
    tts = TTS()

    text = stt.transcribe(audio_path)
    print(f"识别文本: {text}")

    result = router.handle(text)
    print(f"助手回复: {result}")

    tts.speak(result)


def is_alt_key(key) -> bool:
    return key in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}


def is_backtick_key(key) -> bool:
    return getattr(key, "char", None) == "`"


def on_press(key) -> None:
    global alt_pressed, backtick_pressed, recording

    with state_lock:
        if not listening_enabled:
            return

        if is_alt_key(key):
            if not alt_pressed:
                print("[hotkey] Alt 按下")
            alt_pressed = True
            return

        if is_backtick_key(key):
            if backtick_pressed:
                return

            backtick_pressed = True
            print("[hotkey] ` 按下")

            if alt_pressed and not recording:
                print("[hotkey] 开始录音")
                recorder.start_recording()
                recording = True


def on_release(key) -> None:
    global alt_pressed, backtick_pressed, recording

    audio_path = None

    with state_lock:
        if is_backtick_key(key):
            backtick_pressed = False

            if listening_enabled:
                print("[hotkey] ` 松开")

            if recording:
                print("[hotkey] 停止录音")
                audio_path = recorder.stop_recording()
                recording = False

        if is_alt_key(key):
            if alt_pressed and listening_enabled:
                print("[hotkey] Alt 松开")
            alt_pressed = False

    if audio_path is not None:
        threading.Thread(target=handle_audio_file, args=(audio_path,), daemon=True).start()


def create_tray_image() -> Image.Image:
    image = Image.new("RGB", (64, 64), "#1f2937")
    draw = ImageDraw.Draw(image)
    draw.ellipse((18, 8, 46, 36), fill="#38bdf8")
    draw.rounded_rectangle((26, 32, 38, 48), radius=4, fill="#38bdf8")
    draw.rectangle((20, 48, 44, 54), fill="#e5e7eb")
    return image


def toggle_listening(icon: pystray.Icon, item) -> None:
    global listening_enabled, alt_pressed, backtick_pressed

    with state_lock:
        listening_enabled = not listening_enabled
        alt_pressed = False
        backtick_pressed = False
        status = "开启" if listening_enabled else "关闭"
        print(f"[tray] 监听已{status}")

    icon.update_menu()


def listening_menu_text(item) -> str:
    return "关闭监听" if listening_enabled else "开启监听"


def request_show_log_window(icon: pystray.Icon, item) -> None:
    show_log_event.set()


def exit_app(icon: pystray.Icon, item) -> None:
    global recording

    print("[tray] 退出")
    stop_event.set()

    with state_lock:
        if recording:
            print("[hotkey] 停止录音")
            recorder.stop_recording()
            recording = False

    if keyboard_listener is not None:
        keyboard_listener.stop()

    icon.stop()


def run_tray() -> None:
    global tray_icon

    menu = pystray.Menu(
        pystray.MenuItem(listening_menu_text, toggle_listening),
        pystray.MenuItem("显示日志窗口", request_show_log_window),
        pystray.MenuItem("退出", exit_app),
    )
    tray_icon = pystray.Icon(
        "voice_timer",
        create_tray_image(),
        "Voice Timer Assistant",
        menu,
    )
    tray_icon.run()


def main() -> None:
    global keyboard_listener, log_window

    log_window = LogWindow()
    sys.stdout = TeeOutput(sys.stdout)
    sys.stderr = TeeOutput(sys.stderr)

    print("Voice Timer Assistant 已启动")
    print("按住 Alt + ` 开始录音，松开 ` 停止录音")

    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    keyboard_listener.start()

    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

    try:
        while not stop_event.is_set():
            if show_log_event.is_set():
                show_log_event.clear()
                log_window.show()

            log_window.poll()
            time.sleep(0.05)
    except KeyboardInterrupt:
        stop_event.set()
        if tray_icon is not None:
            tray_icon.stop()
        if keyboard_listener is not None:
            keyboard_listener.stop()
        print("\n已退出")
    finally:
        log_window.destroy()


if __name__ == "__main__":
    main()
