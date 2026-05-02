from __future__ import annotations

from config import LLM_PROVIDER
from spark_client import call_spark


class ChatSkill:
    def run(self, text: str) -> str:
        if LLM_PROVIDER == "mock":
            return _mock_reply(text)

        return call_chat(text)


def call_chat(query: str) -> str:
    system_prompt = "你是一个自然口语化的中文语音助手。回答要简短，控制在1到3句话。"

    try:
        response = call_spark(
            query,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=512,
        )
        print("[chat] Spark 调用成功: True")
        print(f"[chat] 返回内容: {response}")

        if not response:
            raise RuntimeError("Spark 返回空内容")

        return response
    except Exception as exc:
        fallback = _mock_reply(query)
        print(f"[chat] Spark 调用成功: False, error={exc}")
        print(f"[chat] 返回内容: {fallback}")
        return fallback


def _mock_reply(query: str) -> str:
    return f"这是 mock 大模型回复：我收到了「{query}」。"
