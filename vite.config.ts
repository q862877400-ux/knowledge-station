import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';

// web 模式引擎发现（2026-08-29）：dev server 把引擎 session（随机端口+token，
// 由引擎进程写 %APPDATA%/KnowledgeStation/engine.session.json）以只读方式
// 暴露给同机前端 —— 引擎重启后前端刷新页面即可自动换绑，无需 URL 参数。
// 仅 dev；Electron 生产走 preload getInfo，不走此路径。vite 与引擎都只绑
// 127.0.0.1，token 的暴露面与引擎本体一致（本机环回），不扩大攻击面。
// 注意：configureServer 是 plugin hook，不是 server.ServerOptions 字段
// （历史坑：写在 server: {} 里被 vite 静默忽略，端点永远 404）。
function engineSessionPlugin(): Plugin {
  return {
    name: 'knowledge-station:engine-session',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url !== '/__engine_session') return next();
        const p = path.join(process.env.APPDATA || '', 'KnowledgeStation', 'engine.session.json');
        try {
          const txt = fs.readFileSync(p, 'utf-8');
          JSON.parse(txt); // 守卫：半写文件不外发
          res.setHeader('Content-Type', 'application/json');
          res.setHeader('Cache-Control', 'no-store');
          res.end(txt);
        } catch {
          res.statusCode = 404;
          res.setHeader('Content-Type', 'application/json');
          res.end('{}');
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), engineSessionPlugin()],
  base: './',
  build: { outDir: 'dist' },
  server: {
    host: '127.0.0.1',
    // 仓库内的 SQLite 快照/测试库会被引擎或测试进程锁住，vite 文件监听撞 EBUSY 直接崩——
    // 排除数据类目录（var/eval/wenjianmulu 用户文档目录）与 .db/.sqlite 文件
    // （历史坑：eval/golden/knowledge-snapshot.db、wenjianmulu/*.pdf 锁死 dev server）
    watch: { ignored: ['**/eval/**', '**/var/**', '**/wenjianmulu/**', '**/node_modules/**', '**/*.db', '**/*.sqlite', '**/*.zstd'] },
  },
});
