from __future__ import annotations

import json
import re
from typing import Any

from skills.chat import ChatSkill
from skills.timer import TimerSkill
from spark_client import call_spark


DEFAULT_TIMER_SECONDS = 60

CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

CHINESE_UNITS = {
    "十": 10,
    "百": 100,
    "千": 1000,
    "万": 10000,
}


class IntentRouter:
    def __init__(self) -> None:
        self.timer = TimerSkill()
        self.chat = ChatSkill()

    def handle(self, text: str) -> str:
        intent = self.classify(text)

        if intent["intent"] == "timer":
            return self.timer.run(
                intent["message"] or text,
                duration_seconds=intent["duration_seconds"],
            )

        return self.chat.run(intent["query"] or text)

    def classify(self, text: str) -> dict[str, Any]:
        print(f"[intent_router] 输入文本: {text}")

        try:
            intent = self._classify_with_spark(text)
        except Exception as exc:
            print(f"[intent_router] Spark 调用失败，fallback 本地规则: {exc}")
            intent = self._classify_locally(text)

        if intent["intent"] == "timer":
            if intent.get("_duration_parsed_locally"):
                duration_seconds = intent.get("duration_seconds")
            else:
                duration_seconds = self._parse_duration_seconds(text)
                if duration_seconds is None:
                    duration_seconds = intent.get("duration_seconds")

            if not isinstance(duration_seconds, int) or duration_seconds <= 0:
                print(
                    "[intent_router] 时间解析失败，"
                    f"fallback 到默认值: {DEFAULT_TIMER_SECONDS}"
                )
                duration_seconds = DEFAULT_TIMER_SECONDS

            raw_message = intent.get("message") or text
            cleaned_message = clean_timer_message(raw_message)
            print(f"[intent_router] 清洗前 message: {raw_message}")
            print(f"[intent_router] 清洗后 message: {cleaned_message}")

            intent["duration_seconds"] = duration_seconds
            intent["message"] = cleaned_message
            intent["query"] = None
        else:
            intent["intent"] = "chat"
            intent["duration_seconds"] = None
            intent["message"] = intent.get("message")
            intent["query"] = intent.get("query") or text

        print(
            "[intent_router] 最终结果: "
            f"intent={intent['intent']}, duration_seconds={intent['duration_seconds']}"
        )
        intent.pop("_duration_parsed_locally", None)
        return intent

    def _classify_with_spark(self, text: str) -> dict[str, Any]:
        prompt = f"""
你是语音助手的意图识别器。

请根据用户输入判断 intent：
- 包含“计时 / 倒数 / 提醒 / 几秒后 / 几分钟后”等倒计时或提醒含义，intent 为 "timer"
- 其他 intent 为 "chat"

你必须只输出 JSON，不要解释，不要 Markdown，不要多余文字。
JSON 格式必须完全符合：
{{
  "intent": "timer" 或 "chat",
  "duration_seconds": 秒数或 null,
  "message": "提醒内容，可为空字符串",
  "query": "原始问题，chat 时填写，timer 时可为 null"
}}

用户输入：{text}
""".strip()

        raw = call_spark(prompt, temperature=0.1, max_tokens=512)
        print(f"[intent_router] Spark 原始返回: {raw}")

        data = _load_json_object(raw)
        intent = data.get("intent")
        if intent not in {"timer", "chat"}:
            raise ValueError(f"Spark 返回了未知 intent: {intent}")

        return {
            "intent": intent,
            "duration_seconds": data.get("duration_seconds"),
            "message": data.get("message"),
            "query": data.get("query") or text,
        }

    def _classify_locally(self, text: str) -> dict[str, Any]:
        normalized = text.lower()
        duration_seconds = self._parse_duration_seconds(text)
        timer_keywords = [
            "timer",
            "计时",
            "倒计时",
            "倒数",
            "到数",
            "提醒",
            "叫我",
            "告诉我",
            "秒后",
            "分钟后",
            "分后",
            "小时后",
        ]
        is_timer = any(keyword in normalized for keyword in timer_keywords)
        is_timer = is_timer or duration_seconds is not None

        return {
            "intent": "timer" if is_timer else "chat",
            "duration_seconds": duration_seconds if is_timer else None,
            "message": text if is_timer else None,
            "query": None if is_timer else text,
            "_duration_parsed_locally": True,
        }

    def _parse_duration_seconds(self, text: str) -> int | None:
        total_seconds = 0
        matched_parts: list[str] = []

        half_pattern = re.compile(r"半\s*(?P<unit>小时|钟头|分钟|分|秒)")
        for match in half_pattern.finditer(text):
            unit = match.group("unit")
            seconds = _unit_to_seconds(unit) // 2
            total_seconds += seconds
            matched_parts.append(match.group(0))
            print(
                "[intent_router] 解析半单位时间: "
                f"part={match.group(0)}, seconds={seconds}"
            )

        pattern = re.compile(
            r"(?P<number>\d+|[零〇一二两三四五六七八九十百千万]+)\s*"
            r"(?P<unit>小时|钟头|分钟|分|秒|hour|hours|minute|minutes|min|second|seconds|sec)",
            re.I,
        )

        for match in pattern.finditer(text):
            raw_number = match.group("number")
            unit = match.group("unit").lower()
            number = self._parse_number(raw_number)
            print(
                "[intent_router] 解析时间片段: "
                f"raw_number={raw_number}, number={number}, unit={unit}"
            )

            if number is None:
                continue

            total_seconds += number * _unit_to_seconds(unit)
            matched_parts.append(match.group(0))

        if matched_parts:
            print(f"[intent_router] 命中的时间片段: {matched_parts}")
        else:
            print("[intent_router] 未命中明确时间片段")

        return total_seconds if total_seconds > 0 else None

    def _parse_number(self, raw: str) -> int | None:
        if raw.isdigit():
            return int(raw)

        result = 0
        section = 0
        number = 0

        for char in raw:
            if char in CHINESE_DIGITS:
                number = CHINESE_DIGITS[char]
                continue

            unit = CHINESE_UNITS.get(char)
            if unit is None:
                print(f"[intent_router] 不支持的中文数字字符: {char}")
                return None

            if unit == 10000:
                section = (section + number) * unit
                result += section
                section = 0
            else:
                section += (number or 1) * unit
            number = 0

        return result + section + number


def clean_timer_message(message: str | None) -> str:
    if not message:
        return ""

    cleaned = message.strip()
    cleaned = re.sub(r"[，,。.!！?？；;：:]+$", "", cleaned)

    time_pattern = (
        r"(?:半\s*(?:小时|钟头|分钟|分|秒)|"
        r"(?:\d+|[零〇一二两三四五六七八九十百千万]+)\s*"
        r"(?:小时|钟头|分钟|分|秒|hour|hours|minute|minutes|min|second|seconds|sec))"
    )
    cleaned = re.sub(time_pattern, "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*(?:之后|以后|后)\s*", "", cleaned)
    cleaned = re.sub(r"(?:请|帮我|麻烦你|给我|为我|替我)", "", cleaned)
    cleaned = re.sub(r"(?:提醒我|提醒一下我|提醒|叫我|告诉我|通知我)", "", cleaned)
    cleaned = re.sub(r"(?:倒计时|倒数|到数|计时|timer)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = cleaned.strip(" ，,。.!！?？；;：:")

    if is_pure_time_message(cleaned):
        return ""

    return cleaned


def is_pure_time_message(message: str | None) -> bool:
    if not message:
        return True

    text = message.strip()
    if not text:
        return True

    time_pattern = (
        r"(?:半\s*(?:小时|钟头|分钟|分|秒)|"
        r"(?:\d+|[零〇一二两三四五六七八九十百千万]+)\s*"
        r"(?:小时|钟头|分钟|分|秒|hour|hours|minute|minutes|min|second|seconds|sec))"
    )
    text = re.sub(time_pattern, "", text, flags=re.I)
    text = re.sub(r"(?:之后|以后|后|倒计时|倒数|到数|计时|timer)", "", text, flags=re.I)
    text = text.strip(" ，,。.!！?？；;：:")
    return not text


def _unit_to_seconds(unit: str) -> int:
    if unit in {"小时", "钟头", "hour", "hours"}:
        return 3600
    if unit in {"分钟", "分", "minute", "minutes", "min"}:
        return 60
    if unit in {"秒", "second", "seconds", "sec"}:
        return 1
    raise ValueError(f"不支持的时间单位: {unit}")


def _load_json_object(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise
        return json.loads(match.group(0))
