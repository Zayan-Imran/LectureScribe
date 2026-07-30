# LectureScribe

LectureScribe is a Python desktop application scaffold for realtime lecture transcription on Windows. The future application will use OpenAI's Realtime Transcription API, but this initial version intentionally focuses on the desktop shell only.

## Current scope

This initial project includes:

- Python 3.12 project metadata
- PySide6 desktop UI
- sounddevice-based microphone and WASAPI loopback device discovery
- 24 kHz mono PCM16 capture plumbing for realtime transcription
- OpenAI SDK realtime transcription client using `gpt-live-transcribe`
- Ruff and Black configuration
- Centralized logging setup
- A polished main window with lecture transcription controls

The following are intentionally **not implemented** yet:

- Export persistence beyond a placeholder UI action
- Transcript post-processing, speaker labels, timestamps, or confidence scores

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) recommended for dependency management

## Getting started

Install dependencies:

```bash
uv sync
```

Run the app:

```bash
uv run lecturescribe
```

Alternatively, run the module directly:

```bash
uv run python -m lecturescribe
```

## Development

Format code:

```bash
uv run black src
```

Lint code:

```bash
uv run ruff check src
```

## Architecture

```text
src/lecturescribe/
├── __init__.py       Package metadata
├── __main__.py       Application entrypoint
├── app.py            QApplication bootstrap and runtime setup
├── logging_config.py Centralized logging configuration
├── audio/           sounddevice discovery and PCM16 capture
├── transcription/   OpenAI Realtime client and session coordinator
└── ui/
    ├── __init__.py
    └── main_window.py Main PySide6 window and UI state
```

The application is organized so audio capture, realtime transcription, and UI concerns remain separated while future export workflows can be added without coupling them to the UI bootstrap.


## Runtime notes

LectureScribe expects `OPENAI_API_KEY` in the environment before starting a realtime transcription session. The app streams 16-bit PCM audio at 24 kHz mono to match the realtime transcription session configuration. On Windows, the System Audio option lists WASAPI loopback-capable output devices when available.
