from __future__ import annotations

import re
import threading
import time

from tts import TTS


class TimerSkill:
    def run(self, text: str, duration_seconds: int | None = None) -> str:
        seconds = duration_seconds if duration_seconds is not None else self._parse_seconds(text)
        message = self._normalize_message(text)

        thread = threading.Thread(
            target=self._countdown,
            args=(seconds, message),
            daemon=True,
        )
        thread.start()

        return f"已启动 {seconds} 秒倒计时。"

    def _parse_seconds(self, text: str) -> int:
        minute_match = re.search(r"(\d+)\s*(分钟|分|minute|minutes|min)", text, re.I)
        second_match = re.search(r"(\d+)\s*(秒|second|seconds|sec)", text, re.I)

        seconds = 0
        if minute_match:
            seconds += int(minute_match.group(1)) * 60
        if second_match:
            seconds += int(second_match.group(1))

        return seconds or 60

    def _normalize_message(self, message: str | None) -> str | None:
        if not message:
            return None

        message = message.strip()
        if self._is_pure_time_message(message):
            return None

        return message

    def _is_pure_time_message(self, message: str) -> bool:
        time_pattern = (
            r"(?:半\s*(?:小时|钟头|分钟|分|秒)|"
            r"(?:\d+|[零〇一二两三四五六七八九十百千万]+)\s*"
            r"(?:小时|钟头|分钟|分|秒|hour|hours|minute|minutes|min|second|seconds|sec))"
        )
        remaining = re.sub(time_pattern, "", message, flags=re.I)
        remaining = re.sub(
            r"(?:之后|以后|后|倒计时|倒数|到数|计时|timer)",
            "",
            remaining,
            flags=re.I,
        )
        remaining = remaining.strip(" ，,。.!！?？；;：:")
        return not remaining

    def _countdown(self, seconds: int, message: str | None = None) -> None:
        time.sleep(seconds)
        print(f"\n倒计时结束: {seconds} 秒")

        spoken_text = message or "倒计时结束"
        try:
            TTS().speak(spoken_text)
        except Exception as exc:
            print(f"[timer] 语音播报失败: {exc}")
