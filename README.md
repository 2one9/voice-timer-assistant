# Voice Timer Assistant

A small Windows-friendly Python voice assistant with push-to-talk recording, iFlytek speech transcription, Spark intent routing, timer reminders, chat replies, text-to-speech, a tray menu, and an optional log window.

## Features

- Push-to-talk hotkey: hold `Alt + `` to record, release `` ` `` to stop.
- Speech-to-text via iFlytek recording file transcription API.
- Intent routing via iFlytek Spark Ultra-32K.
- Timer skill with Chinese duration parsing, reminder message cleanup, and voice announcement when the timer ends.
- Chat skill powered by Spark, with mock fallback.
- System tray menu:
  - Enable/disable keyboard listening
  - Show log window
  - Exit
- Optional tkinter log window that mirrors `print` output.
- PyInstaller-aware paths:
  - `.env` is read from the executable directory after packaging.
  - `recordings/` is written next to the executable after packaging.

## Project Structure

```text
main.py              # tray, keyboard listener, push-to-talk flow, log window
config.py            # config, .env loading, resource/writable paths
audio_recorder.py    # microphone recording
speech_to_text.py    # iFlytek recording file transcription
intent_router.py     # Spark intent routing and timer duration parsing
spark_client.py      # Spark WebSocket client
tts.py               # text-to-speech
skills/
  chat.py            # chat reply skill
  timer.py           # timer skill
```

## Install

Python 3.10+ is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Some audio or tray dependencies may require a normal desktop session. Running over a headless shell is not recommended.

## Configuration

Copy the example file:

```bash
copy .env.example .env
```

Fill in your iFlytek credentials:

```env
LLM_PROVIDER=spark
STT_PROVIDER=xfyun
TTS_PROVIDER=pyttsx3
RECORD_SECONDS=5
SAMPLE_RATE=16000

XFYUN_APPID=
XFYUN_SECRET_KEY=

XFYUN_SPARK_APPID=
XFYUN_SPARK_API_KEY=
XFYUN_SPARK_API_SECRET=
XFYUN_SPARK_MODEL=spark-ultra-32k
```

Use mock chat replies by setting:

```env
LLM_PROVIDER=mock
```

Do not commit `.env`. Use `.env.example` for public configuration templates.

## Run

```bash
python main.py
```

The app starts in the system tray. Hold `Alt + `` to record and release `` ` `` to stop. Right-click the tray icon to enable or disable listening, show the log window, or exit.

Example timer phrases:

```text
5秒后提醒我喝水
一分钟后提醒我休息
倒数5秒
计时十秒
```

Example chat phrase:

```text
你好，介绍一下你自己
```

## Build With PyInstaller

Install PyInstaller if needed:

```bash
pip install pyinstaller
```

Build a windowed tray app:

```bash
pyinstaller --noconsole --onefile --name VoiceTimer main.py
```

After packaging, put `.env` next to the generated executable:

```text
dist/
  VoiceTimer.exe
  .env
```

Runtime recordings will be saved next to the executable:

```text
dist/
  recordings/
```

## Verification

Check syntax before committing:

```bash
python -m compileall .
```

## Notes

- `.env`, `recordings/`, `build/`, `dist/`, and Python cache files are ignored by Git.
- API calls automatically fall back where possible so the app does not crash on temporary service failures.
