"""OpenAI Realtime transcription client isolated from the UI."""

from __future__ import annotations

import asyncio
import base64
import logging
import queue
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

REALTIME_TRANSCRIPTION_MODEL = "gpt-live-transcribe"
REALTIME_INPUT_SAMPLE_RATE = 24_000


class TranscriptEventType(StrEnum):
    """Transcript event kinds emitted to the application."""

    PARTIAL = "partial"
    FINAL = "final"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class TranscriptEvent:
    """A transcript update emitted by the realtime client."""

    type: TranscriptEventType
    text: str
    item_id: str | None = None


TranscriptHandler = Callable[[TranscriptEvent], None]
ErrorHandler = Callable[[Exception], None]


class RealtimeTranscriptionClient:
    """Stream PCM16 audio to an OpenAI Realtime transcription session."""

    def __init__(
        self,
        on_transcript: TranscriptHandler,
        on_error: ErrorHandler,
    ) -> None:
        self._on_transcript = on_transcript
        self._on_error = on_error
        self._audio_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=128)

    def submit_audio(self, chunk: bytes) -> None:
        """Queue a PCM16 audio chunk for transmission."""
        try:
            self._audio_queue.put_nowait(chunk)
        except queue.Full:
            logger.warning("Dropping audio chunk because realtime queue is full")

    def request_stop(self) -> None:
        """Ask the running client to finish the current turn and stop."""
        try:
            self._audio_queue.put_nowait(None)
        except queue.Full:
            logger.warning("Realtime queue was full while stopping; waiting to enqueue stop marker")
            self._audio_queue.put(None)

    async def run(self) -> None:
        """Connect to OpenAI Realtime and process transcript events."""
        client = AsyncOpenAI()
        try:
            async with client.realtime.connect(model=REALTIME_TRANSCRIPTION_MODEL) as connection:
                await connection.session.update(session=_session_config())
                sender = asyncio.create_task(self._send_audio(connection))
                receiver = asyncio.create_task(self._receive_events(connection))

                done, pending = await asyncio.wait(
                    {sender, receiver},
                    return_when=asyncio.FIRST_EXCEPTION,
                )
                for task in done:
                    task.result()
                for task in pending:
                    task.cancel()
        except Exception as exc:
            logger.exception("Realtime transcription failed")
            self._on_error(exc)

    async def _send_audio(self, connection: object) -> None:
        sent_audio = False
        while True:
            chunk = await asyncio.to_thread(self._audio_queue.get)
            if chunk is None:
                if sent_audio:
                    await connection.send({"type": "input_audio_buffer.commit"})
                return

            await connection.send(
                {
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(chunk).decode("utf-8"),
                }
            )
            sent_audio = True

    async def _receive_events(self, connection: object) -> None:
        async for event in connection:
            event_type = getattr(event, "type", "")
            if event_type == "conversation.item.input_audio_transcription.delta":
                self._on_transcript(
                    TranscriptEvent(
                        type=TranscriptEventType.PARTIAL,
                        text=str(getattr(event, "delta", "")),
                        item_id=getattr(event, "item_id", None),
                    )
                )
            elif event_type == "conversation.item.input_audio_transcription.completed":
                self._on_transcript(
                    TranscriptEvent(
                        type=TranscriptEventType.FINAL,
                        text=str(getattr(event, "transcript", "")),
                        item_id=getattr(event, "item_id", None),
                    )
                )
            elif event_type == "error":
                error = getattr(event, "error", None)
                message = getattr(error, "message", "Realtime API returned an error")
                self._on_transcript(TranscriptEvent(type=TranscriptEventType.ERROR, text=str(message)))


def _session_config() -> dict[str, object]:
    return {
        "type": "transcription",
        "audio": {
            "input": {
                "format": {
                    "type": "audio/pcm",
                    "rate": REALTIME_INPUT_SAMPLE_RATE,
                },
                "transcription": {
                    "model": REALTIME_TRANSCRIPTION_MODEL,
                    "delay": "low",
                },
                "turn_detection": None,
            }
        },
    }
