const { app, BrowserWindow, desktopCapturer, ipcMain, systemPreferences } = require('electron');
const path = require('node:path');

const REALTIME_SESSION_URL = 'https://api.openai.com/v1/realtime/client_secrets';
const DEFAULT_MODEL = 'gpt-live-transcribe';

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1180,
    height: 820,
    minWidth: 900,
    minHeight: 640,
    title: 'LectureScribe',
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
}

app.whenReady().then(() => {
  ipcMain.handle('audio:list-system-sources', async () => {
    const sources = await desktopCapturer.getSources({ types: ['screen', 'window'] });
    return sources.map((source) => ({ id: source.id, name: source.name }));
  });

  ipcMain.handle('permissions:microphone-status', () => {
    if (process.platform !== 'darwin') {
      return 'not-required';
    }
    return systemPreferences.getMediaAccessStatus('microphone');
  });

  ipcMain.handle('openai:create-realtime-token', async (_event, options = {}) => {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error('Set OPENAI_API_KEY in your environment before starting LectureScribe.');
    }

    const keywords = Array.isArray(options.keywords) ? options.keywords.filter(Boolean) : [];
    const languages = Array.isArray(options.languages) ? options.languages.filter(Boolean) : [];
    const body = {
      session: {
        type: 'transcription',
        audio: {
          input: {
            transcription: {
              model: DEFAULT_MODEL,
              delay: options.delay || 'low'
            },
            turn_detection: {
              type: 'server_vad',
              silence_duration_ms: 900
            }
          }
        }
      }
    };

    if (options.prompt) {
      body.session.audio.input.transcription.prompt = options.prompt;
    }
    if (keywords.length > 0) {
      body.session.audio.input.transcription.keywords = keywords;
    }
    if (languages.length > 0) {
      body.session.audio.input.transcription.languages = languages;
    }

    const response = await fetch(REALTIME_SESSION_URL, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenAI session failed (${response.status}): ${errorText}`);
    }

    const json = await response.json();
    const secret = json.value || json.client_secret?.value;
    if (!secret) {
      throw new Error('OpenAI response did not include an ephemeral client secret.');
    }

    return { clientSecret: secret, model: DEFAULT_MODEL };
  });

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
