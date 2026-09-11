// 引擎连接与 API 封装（随机端口 + token 从 Electron preload 或 env 注入）
export interface EngineInfo { port: string; token: string }

export function engineInfo(): EngineInfo {
  const port = (window as any).engine
    ? '' // 由 preload 异步提供，见 App.tsx
    : (import.meta.env.VITE_ENGINE_PORT ?? '');
  return {
    port: port || localStorage.getItem('engine.port') || '',
    token: (import.meta.env.VITE_ENGINE_TOKEN as string) || localStorage.getItem('engine.token') || '',
  };
}

export function saveEngineInfo(info: EngineInfo) {
  localStorage.setItem('engine.port', info.port);
  localStorage.setItem('engine.token', info.token);
}

export async function apiFetch(port: string, token: string, path: string, init?: RequestInit) {
  const res = await fetch(`http://127.0.0.1:${port}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${token}`,
      ...(init?.body && !(init.body instanceof ArrayBuffer) ? { 'Content-Type': 'application/json' } : {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res;
}

export async function fetchPdf(port: string, token: string, docId: string): Promise<ArrayBuffer | null> {
  try {
    const res = await apiFetch(port, token, `/api/v1/documents/${docId}/file`);
    return await res.arrayBuffer();
  } catch {
    return null; // 法律文本直灌文档无原页
  }
}
