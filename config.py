from __future__ import annotations

import os
import sys
from pathlib import Path


def get_resource_base_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    return Path(".")


def get_writable_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(".")


def resource_path(*parts: str) -> Path:
    return RESOURCE_DIR.joinpath(*parts)


def writable_path(*parts: str) -> Path:
    return WRITABLE_DIR.joinpath(*parts)


def relative_path(*parts: str) -> Path:
    return resource_path(*parts)


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


RESOURCE_DIR = get_resource_base_dir()
WRITABLE_DIR = get_writable_base_dir()
BASE_DIR = RESOURCE_DIR

ENV_PATH = writable_path(".env")
AUDIO_DIR = writable_path("recordings")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_ENV = _read_env_file(ENV_PATH)


def get_config(name: str, default: str = "") -> str:
    return os.getenv(name) or _ENV.get(name) or default


HOTKEY = get_config("HOTKEY", "ctrl+alt+f1")
RECORD_SECONDS = int(get_config("RECORD_SECONDS", "5"))
SAMPLE_RATE = int(get_config("SAMPLE_RATE", "16000"))

LLM_PROVIDER = get_config("LLM_PROVIDER", "spark").lower()
STT_PROVIDER = get_config("STT_PROVIDER", "mock").lower()
TTS_PROVIDER = get_config("TTS_PROVIDER", "pyttsx3").lower()

OPENAI_API_KEY = get_config("OPENAI_API_KEY")
OPENAI_MODEL = get_config("OPENAI_MODEL", "gpt-4o-mini")
