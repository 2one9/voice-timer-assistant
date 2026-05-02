from __future__ import annotations

from config import TTS_PROVIDER


class TTS:
    def speak(self, text: str) -> None:
        if TTS_PROVIDER == "pyttsx3":
            try:
                import pyttsx3

                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
                return
            except Exception as exc:
                print(f"TTS 播报不可用，已改为文字输出: {exc}")

        print(text)
