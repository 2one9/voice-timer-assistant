from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any

import requests

from config import ENV_PATH


XFYUN_API_BASE = "https://raasr.xfyun.cn/v2/api"
UPLOAD_URL = f"{XFYUN_API_BASE}/upload"
RESULT_URL = f"{XFYUN_API_BASE}/getResult"

POLL_INTERVAL_SECONDS = 3
MAX_POLL_ATTEMPTS = 60


class SpeechToText:
    def transcribe(self, audio_path: Path) -> str:
        return transcribe_audio(audio_path)


def transcribe_audio(path: str | Path) -> str:
    audio_path = Path(path)

    try:
        app_id, secret_key = _load_xfyun_credentials()
        task_id = _upload_audio(audio_path, app_id, secret_key)
        result_text = _poll_transcription(task_id, app_id, secret_key)

        print(f"[speech_to_text] 转写结果: {result_text}")
        if not result_text:
            raise RuntimeError("讯飞 API 返回了空转写结果")

        return result_text
    except Exception as exc:
        print(f"[speech_to_text] API 失败，fallback 手动输入: {exc}")
        return input("请输入模拟语音识别结果: ").strip()


def _load_xfyun_credentials() -> tuple[str, str]:
    env = _read_env_file(ENV_PATH)
    app_id = env.get("XFYUN_APPID", "")
    secret_key = env.get("XFYUN_SECRET_KEY", "")

    if not app_id or not secret_key:
        raise RuntimeError(".env 缺少 XFYUN_APPID 或 XFYUN_SECRET_KEY")

    return app_id, secret_key


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


def _upload_audio(audio_path: Path, app_id: str, secret_key: str) -> str:
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    file_size = audio_path.stat().st_size
    timestamp = str(int(time.time()))
    params = _signed_params(app_id, secret_key, timestamp)
    params.update(
        {
            "fileName": "temp.wav",
            "fileSize": str(file_size),
            "duration": "200",
        }
    )

    with audio_path.open("rb") as audio_file:
        response = requests.post(
            UPLOAD_URL,
            params=params,
            data=audio_file,
            headers={"Content-Type": "application/octet-stream"},
            timeout=30,
        )

    payload = response.json()
    upload_success = response.ok and str(payload.get("code")) == "000000"
    print(f"[speech_to_text] 上传是否成功: {upload_success}")
    print(f"[speech_to_text] 上传响应: {payload}")

    if not upload_success:
        raise RuntimeError(f"上传失败: {payload}")

    content = payload.get("content") or {}
    task_id = content.get("orderId") or content.get("task_id") or content.get("taskId")
    print(f"[speech_to_text] task_id: {task_id}")

    if not task_id:
        raise RuntimeError(f"上传成功但未返回 task_id/orderId: {payload}")

    return str(task_id)


def _poll_transcription(task_id: str, app_id: str, secret_key: str) -> str:
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        timestamp = str(int(time.time()))
        params = _signed_params(app_id, secret_key, timestamp)
        params["orderId"] = task_id

        response = requests.post(RESULT_URL, data=params, timeout=30)
        payload = response.json()
        code = str(payload.get("code"))
        content = payload.get("content") or {}
        order_info = content.get("orderInfo") or {}
        status = int(order_info.get("status", 0) or 0)

        print(
            "[speech_to_text] 查询转写结果: "
            f"attempt={attempt}, code={code}, status={status}"
        )

        if code != "000000":
            raise RuntimeError(f"查询失败: {payload}")

        if status == 4:
            order_result = content.get("orderResult", "")
            return _extract_text_from_order_result(order_result)

        if status == -1:
            raise RuntimeError(f"转写任务失败: {payload}")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"转写任务超时: task_id={task_id}")


def _signed_params(app_id: str, secret_key: str, timestamp: str) -> dict[str, str]:
    md5_source = (app_id + timestamp).encode("utf-8")
    base_string = hashlib.md5(md5_source).hexdigest()
    signature = hmac.new(
        secret_key.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    signa = base64.b64encode(signature).decode("utf-8")

    return {
        "appId": app_id,
        "ts": timestamp,
        "signa": signa,
    }


def _extract_text_from_order_result(order_result: str | dict[str, Any]) -> str:
    if isinstance(order_result, str):
        data = json.loads(order_result)
    else:
        data = order_result

    pieces: list[str] = []

    for lattice in data.get("lattice", []):
        json_1best = lattice.get("json_1best", {})
        if isinstance(json_1best, str):
            json_1best = json.loads(json_1best)

        pieces.extend(_extract_words(json_1best))

    return "".join(pieces).strip()


def _extract_words(data: dict[str, Any]) -> list[str]:
    words: list[str] = []

    for sentence in data.get("st", {}).get("rt", []):
        for word_segment in sentence.get("ws", []):
            candidates = word_segment.get("cw", [])
            if not candidates:
                continue

            word = candidates[0].get("w", "")
            if word:
                words.append(word)

    return words
