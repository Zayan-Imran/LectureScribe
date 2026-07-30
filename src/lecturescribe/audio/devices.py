"""Audio device discovery built on sounddevice."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import sounddevice as sd


class AudioSource(StrEnum):
    """Supported user-facing audio capture sources."""

    MICROPHONE = "microphone"
    LOOPBACK = "loopback"


@dataclass(frozen=True, slots=True)
class AudioDevice:
    """A normalized audio device descriptor for the UI and capture layer."""

    id: int
    name: str
    source: AudioSource
    hostapi: str
    max_input_channels: int
    default_sample_rate: float
    loopback_output_device_id: int | None = None

    @property
    def display_name(self) -> str:
        """Return a compact label suitable for the device selector."""
        return f"{self.name} — {self.hostapi}"


def list_audio_devices() -> list[AudioDevice]:
    """Return microphones and Windows WASAPI loopback-capable devices."""
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    normalized: list[AudioDevice] = []

    for device_id, raw_device in enumerate(devices):
        device = dict(raw_device)
        hostapi = _hostapi_name(hostapis, device.get("hostapi"))
        input_channels = int(device.get("max_input_channels", 0))
        output_channels = int(device.get("max_output_channels", 0))
        default_sample_rate = float(device.get("default_samplerate", 0.0))
        name = str(device.get("name", f"Device {device_id}"))

        if input_channels > 0:
            source = AudioSource.LOOPBACK if _is_wasapi_loopback_device(name, hostapi) else AudioSource.MICROPHONE
            normalized.append(
                AudioDevice(
                    id=device_id,
                    name=name,
                    source=source,
                    hostapi=hostapi,
                    max_input_channels=input_channels,
                    default_sample_rate=default_sample_rate,
                )
            )

        if _is_wasapi(hostapi) and output_channels > 0 and not _is_wasapi_loopback_device(name, hostapi):
            normalized.append(
                AudioDevice(
                    id=device_id,
                    name=f"{name} (WASAPI loopback)",
                    source=AudioSource.LOOPBACK,
                    hostapi=hostapi,
                    max_input_channels=output_channels,
                    default_sample_rate=default_sample_rate,
                    loopback_output_device_id=device_id,
                )
            )

    return normalized


def _hostapi_name(hostapis: Any, hostapi_index: object) -> str:
    try:
        return str(hostapis[int(hostapi_index)]["name"])
    except (IndexError, TypeError, ValueError, KeyError):
        return "Unknown host API"


def _is_wasapi(hostapi: str) -> bool:
    return "wasapi" in hostapi.casefold()


def _is_wasapi_loopback_device(name: str, hostapi: str) -> bool:
    normalized_name = name.casefold()
    return _is_wasapi(hostapi) and ("loopback" in normalized_name or "what u hear" in normalized_name)
