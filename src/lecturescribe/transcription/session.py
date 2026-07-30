"""Coordinates audio capture with realtime transcription without UI dependencies."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable

from lecturescribe.audio import AudioCaptureConfig, AudioCaptureWorker, AudioDevice
from lecturescribe.transcription import RealtimeTranscriptionClient, TranscriptEvent

logger = logging.getLogger(__name__)


class TranscriptionSession:
    """Own a capture worker and realtime client for one recording session."""

    def __init__(
        self,
        device: AudioDevice,
        on_transcript: Callable[[TranscriptEvent], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        self._device = device
        self._on_transcript = on_transcript
        self._on_error = on_error
        self._client = RealtimeTranscriptionClient(on_transcript=on_transcript, on_error=on_error)
        self._audio = AudioCaptureWorker(
            AudioCaptureConfig(device=device),
            on_audio=self._client.submit_audio,
            on_error=on_error,
        )
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start networking and audio capture in background threads."""
        logger.info("Starting transcription session for %s", self._device.display_name)
        self._thread = threading.Thread(target=self._run_client, name="RealtimeTranscription", daemon=True)
        self._thread.start()
        self._audio.start()

    def stop(self) -> None:
        """Stop audio capture and request realtime turn completion."""
        logger.info("Stopping transcription session")
        self._audio.stop()
        self._client.request_stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run_client(self) -> None:
        asyncio.run(self._client.run())
