"""16-bit PCM audio capture workers for realtime transcription."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass

import sounddevice as sd

from lecturescribe.audio.devices import AudioDevice

logger = logging.getLogger(__name__)

OPENAI_PCM_SAMPLE_RATE = 24_000
OPENAI_PCM_CHANNELS = 1
OPENAI_PCM_DTYPE = "int16"

AudioChunkHandler = Callable[[bytes], None]
ErrorHandler = Callable[[Exception], None]


@dataclass(frozen=True, slots=True)
class AudioCaptureConfig:
    """Configuration for a PCM16 audio stream."""

    device: AudioDevice
    sample_rate: int = OPENAI_PCM_SAMPLE_RATE
    channels: int = OPENAI_PCM_CHANNELS
    blocksize: int = 2_400


class AudioCaptureWorker:
    """Capture PCM16 audio in a background thread and emit raw byte chunks."""

    def __init__(
        self,
        config: AudioCaptureConfig,
        on_audio: AudioChunkHandler,
        on_error: ErrorHandler,
    ) -> None:
        self._config = config
        self._on_audio = on_audio
        self._on_error = on_error
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=32)
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        """Start capturing audio if not already running."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="AudioCaptureWorker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop capture and wait briefly for the worker to finish."""
        self._stop_event.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        try:
            extra_settings = self._extra_settings()
            device_id = self._config.device.loopback_output_device_id or self._config.device.id
            logger.info("Opening audio device %s", self._config.device.display_name)

            with sd.InputStream(
                samplerate=self._config.sample_rate,
                device=device_id,
                channels=self._config.channels,
                dtype=OPENAI_PCM_DTYPE,
                blocksize=self._config.blocksize,
                callback=self._audio_callback,
                extra_settings=extra_settings,
            ) as stream:
                self._stream = stream
                while not self._stop_event.is_set():
                    try:
                        chunk = self._queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    self._on_audio(chunk)
        except Exception as exc:
            logger.exception("Audio capture failed")
            self._on_error(exc)
        finally:
            self._stream = None

    def _audio_callback(self, indata: object, frames: int, time: object, status: sd.CallbackFlags) -> None:
        del frames, time
        if status:
            logger.warning("Audio callback status: %s", status)

        try:
            self._queue.put_nowait(bytes(indata))
        except queue.Full:
            logger.warning("Dropping audio chunk because the audio queue is full")

    def _extra_settings(self) -> object | None:
        if self._config.device.loopback_output_device_id is None:
            return None
        try:
            return sd.WasapiSettings(loopback=True)
        except AttributeError:
            return None
