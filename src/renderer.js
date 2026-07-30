const REALTIME_WEBRTC_URL = 'https://api.openai.com/v1/realtime/calls';

const state = {
  peerConnection: null,
  dataChannel: null,
  mediaStream: null,
  startedAt: null,
  timerId: null,
  finalTranscript: '',
  partialTranscript: ''
};

const elements = {
  inputMode: document.querySelector('#inputMode'),
  sourcePicker: document.querySelector('#sourcePicker'),
  systemSource: document.querySelector('#systemSource'),
  delay: document.querySelector('#delay'),
  languages: document.querySelector('#languages'),
  prompt: document.querySelector('#prompt'),
  keywords: document.querySelector('#keywords'),
  startButton: document.querySelector('#startButton'),
  stopButton: document.querySelector('#stopButton'),
  copyButton: document.querySelector('#copyButton'),
  downloadButton: document.querySelector('#downloadButton'),
  status: document.querySelector('#status'),
  transcript: document.querySelector('#transcript'),
  timer: document.querySelector('#timer')
};

function setStatus(message) {
  elements.status.textContent = message;
}

function parseList(value) {
  return value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);
}

function renderTranscript() {
  elements.transcript.innerHTML = '';
  elements.transcript.append(document.createTextNode(state.finalTranscript));
  if (state.partialTranscript) {
    const partial = document.createElement('span');
    partial.className = 'partial';
    partial.textContent = state.partialTranscript;
    elements.transcript.append(partial);
  }
  elements.transcript.scrollTop = elements.transcript.scrollHeight;
}

function startTimer() {
  state.startedAt = Date.now();
  state.timerId = setInterval(() => {
    const elapsed = Math.floor((Date.now() - state.startedAt) / 1000);
    const minutes = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const seconds = String(elapsed % 60).padStart(2, '0');
    elements.timer.textContent = `${minutes}:${seconds}`;
  }, 1000);
}

async function refreshSystemSources() {
  const sources = await window.lectureScribe.listSystemSources();
  elements.systemSource.replaceChildren(...sources.map((source) => {
    const option = document.createElement('option');
    option.value = source.id;
    option.textContent = source.name;
    return option;
  }));
}

async function getAudioStream() {
  if (elements.inputMode.value === 'mic') {
    return navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  }

  const sourceId = elements.systemSource.value;
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: {
        chromeMediaSource: 'desktop',
        chromeMediaSourceId: sourceId
      }
    },
    video: {
      mandatory: {
        chromeMediaSource: 'desktop',
        chromeMediaSourceId: sourceId,
        maxWidth: 1,
        maxHeight: 1
      }
    }
  });
  stream.getVideoTracks().forEach((track) => track.stop());
  return stream;
}

function handleRealtimeEvent(event) {
  if (event.type === 'conversation.item.input_audio_transcription.delta') {
    state.partialTranscript += event.delta || '';
    renderTranscript();
    return;
  }

  if (event.type === 'conversation.item.input_audio_transcription.completed') {
    const transcript = event.transcript || state.partialTranscript;
    state.finalTranscript += `${transcript.trim()}\n\n`;
    state.partialTranscript = '';
    renderTranscript();
    return;
  }

  if (event.type === 'error') {
    setStatus(event.error?.message || 'Realtime API error');
  }
}

async function startTranscription() {
  try {
    elements.startButton.disabled = true;
    setStatus('Requesting audio…');

    const [stream, token] = await Promise.all([
      getAudioStream(),
      window.lectureScribe.createRealtimeToken({
        delay: elements.delay.value,
        prompt: elements.prompt.value.trim(),
        keywords: parseList(elements.keywords.value),
        languages: parseList(elements.languages.value)
      })
    ]);

    const peerConnection = new RTCPeerConnection();
    stream.getAudioTracks().forEach((track) => peerConnection.addTrack(track, stream));

    const dataChannel = peerConnection.createDataChannel('oai-events');
    dataChannel.addEventListener('message', (message) => {
      handleRealtimeEvent(JSON.parse(message.data));
    });
    dataChannel.addEventListener('open', () => setStatus(`Listening with ${token.model}`));

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    const sdpResponse = await fetch(REALTIME_WEBRTC_URL, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token.clientSecret}`,
        'Content-Type': 'application/sdp'
      },
      body: offer.sdp
    });

    if (!sdpResponse.ok) {
      throw new Error(`WebRTC connection failed (${sdpResponse.status}): ${await sdpResponse.text()}`);
    }

    await peerConnection.setRemoteDescription({ type: 'answer', sdp: await sdpResponse.text() });

    state.peerConnection = peerConnection;
    state.dataChannel = dataChannel;
    state.mediaStream = stream;
    state.finalTranscript = '';
    state.partialTranscript = '';
    renderTranscript();
    startTimer();
    elements.stopButton.disabled = false;
  } catch (error) {
    stopTranscription();
    setStatus(error.message);
  }
}

function stopTranscription() {
  if (state.timerId) {
    clearInterval(state.timerId);
    state.timerId = null;
  }
  if (state.dataChannel) {
    state.dataChannel.close();
    state.dataChannel = null;
  }
  if (state.peerConnection) {
    state.peerConnection.close();
    state.peerConnection = null;
  }
  if (state.mediaStream) {
    state.mediaStream.getTracks().forEach((track) => track.stop());
    state.mediaStream = null;
  }
  elements.startButton.disabled = false;
  elements.stopButton.disabled = true;
  setStatus('Idle');
}

async function copyTranscript() {
  await navigator.clipboard.writeText(`${state.finalTranscript}${state.partialTranscript}`.trim());
  setStatus('Copied transcript');
}

function downloadTranscript() {
  const blob = new Blob([`${state.finalTranscript}${state.partialTranscript}`.trim()], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `lecture-transcript-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.txt`;
  link.click();
  URL.revokeObjectURL(url);
}

elements.inputMode.addEventListener('change', async () => {
  const systemMode = elements.inputMode.value === 'system';
  elements.sourcePicker.classList.toggle('hidden', !systemMode);
  if (systemMode) {
    await refreshSystemSources();
  }
});
elements.startButton.addEventListener('click', startTranscription);
elements.stopButton.addEventListener('click', stopTranscription);
elements.copyButton.addEventListener('click', copyTranscript);
elements.downloadButton.addEventListener('click', downloadTranscript);

window.addEventListener('beforeunload', stopTranscription);
