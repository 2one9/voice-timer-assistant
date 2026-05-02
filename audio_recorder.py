from __future__ import annotations

import wave
from datetime import datetime
from pathlib import Path

from config import AUDIO_DIR, RECORD_SECONDS, SAMPLE_RATE


class AudioRecorder:
    def __init__(self, audio_dir: Path = AUDIO_DIR) -> None:
        self.audio_dir = audio_dir
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.output_path: Path | None = None
        self.stream = None
        self.frames: list[bytes] = []
        self.recording = False

    def start_recording(self) -> None:
        if self.recording:
            return

        filename = datetime.now().strftime("recording_%Y%m%d_%H%M%S.wav")
        self.output_path = self.audio_dir / filename
        self.frames = []
        self.recording = True

        try:
            import sounddevice as sd

            def callback(indata, frames, time_info, status) -> None:
                if status:
                    print(f"[audio_recorder] 录音状态: {status}")
                self.frames.append(indata.copy().tobytes())

            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                callback=callback,
            )
            self.stream.start()
            print(f"[audio_recorder] 开始录音: {self.output_path}")
        except Exception as exc:
            self.stream = None
            print(f"[audio_recorder] 录音设备不可用，进入 mock 模式: {exc}")

    def stop_recording(self) -> Path:
        if not self.recording:
            raise RuntimeError("当前没有正在进行的录音")

        self.recording = False

        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if self.output_path is None:
            filename = datetime.now().strftime("recording_%Y%m%d_%H%M%S.wav")
            self.output_path = self.audio_dir / filename

        pcm_bytes = b"".join(self.frames)
        if not pcm_bytes:
            pcm_bytes = b"\x00\x00" * SAMPLE_RATE

        self._write_wav(self.output_path, pcm_bytes)
        print(f"[audio_recorder] 停止录音: {self.output_path}")
        return self.output_path

    def record(self) -> Path:
        self.start_recording()

        import time

        time.sleep(RECORD_SECONDS)
        return self.stop_recording()

    def _write_wav(self, path: Path, pcm_bytes: bytes) -> None:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(pcm_bytes)
