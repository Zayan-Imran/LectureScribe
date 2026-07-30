const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('lectureScribe', {
  listSystemSources: () => ipcRenderer.invoke('audio:list-system-sources'),
  microphoneStatus: () => ipcRenderer.invoke('permissions:microphone-status'),
  createRealtimeToken: (options) => ipcRenderer.invoke('openai:create-realtime-token', options)
});
