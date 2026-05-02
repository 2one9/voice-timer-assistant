from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime
from pathlib import Path
from time import mktime
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

from config import ENV_PATH


DEFAULT_SPARK_MODEL = "spark-ultra-32k"

MODEL_CONFIG = {
    "spark-ultra-32k": {
        "url": "wss://spark-api.xf-yun.com/v4.0/chat",
        "domain": "4.0Ultra",
    },
    "ultra": {
        "url": "wss://spark-api.xf-yun.com/v4.0/chat",
        "domain": "4.0Ultra",
    },
    "4.0Ultra": {
        "url": "wss://spark-api.xf-yun.com/v4.0/chat",
        "domain": "4.0Ultra",
    },
    "max-32k": {
        "url": "wss://spark-api.xf-yun.com/chat/max-32k",
        "domain": "max-32k",
    },
}


def call_spark(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> str:
    env = _read_env_file(ENV_PATH)
    app_id = env.get("XFYUN_SPARK_APPID", "")
    api_key = env.get("XFYUN_SPARK_API_KEY", "")
    api_secret = env.get("XFYUN_SPARK_API_SECRET", "")
    model = env.get("XFYUN_SPARK_MODEL", DEFAULT_SPARK_MODEL)

    if not app_id or not api_key or not api_secret:
        raise RuntimeError(
            ".env 缺少 XFYUN_SPARK_APPID、XFYUN_SPARK_API_KEY 或 XFYUN_SPARK_API_SECRET"
        )

    model_config = MODEL_CONFIG.get(model, MODEL_CONFIG[DEFAULT_SPARK_MODEL])
    spark_url = model_config["url"]
    domain = model_config["domain"]
    auth_url = _build_auth_url(spark_url, api_key, api_secret)

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    request_body = {
        "header": {
            "app_id": app_id,
            "uid": "voice_timer",
        },
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        },
        "payload": {
            "message": {
                "text": messages,
            }
        },
    }

    import websocket

    ws = websocket.create_connection(auth_url, timeout=30)
    try:
        ws.send(json.dumps(request_body, ensure_ascii=False))
        return _receive_spark_response(ws)
    finally:
        ws.close()


def _build_auth_url(spark_url: str, api_key: str, api_secret: str) -> str:
    parsed_url = urlparse(spark_url)
    host = parsed_url.netloc
    path = parsed_url.path
    date = format_date_time(mktime(datetime.now().timetuple()))

    signature_origin = f"host: {host}\n"
    signature_origin += f"date: {date}\n"
    signature_origin += f"GET {path} HTTP/1.1"

    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
        "utf-8"
    )

    return f"{spark_url}?{urlencode({'authorization': authorization, 'date': date, 'host': host})}"


def _receive_spark_response(ws) -> str:
    chunks: list[str] = []

    while True:
        message = ws.recv()
        data = json.loads(message)
        header = data.get("header", {})
        code = header.get("code", 0)

        if code != 0:
            raise RuntimeError(f"Spark API 返回错误: {data}")

        choices = data.get("payload", {}).get("choices", {})
        for item in choices.get("text", []):
            chunks.append(item.get("content", ""))

        if header.get("status") == 2 or choices.get("status") == 2:
            break

    return "".join(chunks).strip()


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values
