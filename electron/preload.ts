import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('engine', {
  getInfo: () => ipcRenderer.invoke('engine:info'),
});
