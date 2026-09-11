// Electron 主进程骨架（第一阶段）。
// 说明：直接拉起 Python 引擎子进程的代码（含 heartbeat/auto-restart）属于 T09 范围，
// 本阶段引擎连接信息从环境变量 KS_ENGINE_PORT / KS_ENGINE_TOKEN 读取：
//   开发时先启动引擎: .venv\Scripts\python -m src.core.main  (stdout 会打印端口与 token)
//   再以对应环境变量启动 Electron。
import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';

let enginePort = process.env.KS_ENGINE_PORT ?? '';
let engineToken = process.env.KS_ENGINE_TOKEN ?? '';

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) win.loadURL(devUrl);
  else win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
}

ipcMain.handle('engine:info', () => ({ port: enginePort, token: engineToken }));

app.whenReady().then(createWindow);
