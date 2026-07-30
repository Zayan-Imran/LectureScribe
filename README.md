# LectureScribe

LectureScribe is an Electron laptop app for live lecture transcription. It can listen to your microphone for in-room lectures or capture system audio from a selected screen/window for lecture streams playing on your computer.

## Features

- Microphone or system-audio capture mode.
- OpenAI Realtime transcription session using `gpt-live-transcribe`.
- Live partial transcript display plus completed transcript turns.
- Lecture context, keyword hints, language hints, and latency/accuracy controls.
- Copy and `.txt` download actions for your notes.

## Requirements

- Node.js 20+.
- An OpenAI API key with Realtime API access.
- Operating-system permission for microphone and/or screen audio capture.

## Run locally

```bash
npm install
OPENAI_API_KEY=sk-... npm start
```

For system-audio capture, choose **System audio / lecture stream**, pick the screen/window where the lecture is playing, and grant capture permission if your OS asks.

## Notes

The app creates an ephemeral Realtime client secret in the Electron main process so the renderer never sees your long-lived OpenAI API key. The renderer connects to the Realtime WebRTC endpoint, sends the selected audio track, and listens for `conversation.item.input_audio_transcription.delta` and `conversation.item.input_audio_transcription.completed` events.
