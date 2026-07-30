"""Audio capture and device discovery for LectureScribe."""

from lecturescribe.audio.devices import AudioDevice, AudioSource, list_audio_devices
from lecturescribe.audio.stream import AudioCaptureConfig, AudioCaptureWorker

__all__ = [
    "AudioCaptureConfig",
    "AudioCaptureWorker",
    "AudioDevice",
    "AudioSource",
    "list_audio_devices",
]
