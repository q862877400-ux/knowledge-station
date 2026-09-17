# -*- coding: utf-8 -*-
"""**在 uvicorn 下**验证引擎（§10.84）——补上"进程内 ASGI 量具"覆盖不到的那一层。

## 为什么要它
§10.73–§10.83 的所有 before/after 都来自 `httpx.ASGITransport`（**进程内**调用）：
没有真 socket、没有 uvicorn 的并发限制、`FileResponse` 的流式读出也没真的过一遍。
**真机端到端**要等业主重启两个门（DSH 宿主 + 引擎），而那之前我们能自己做的是：
**另起一个独立引擎实例**（⚠ 不是替换在跑的那个），跑一遍只有真 server 才能暴露的东西。

## 安全边界（硬约束）
- 监听 `127.0.0.1` + **随机空闲端口**；`KS_DATA_DIR` 指向**临时目录** ⇒ 不碰生产库、不占引擎端口。
- **绝不** kill 既有引擎/DSH 宿主：只 kill本脚本自己 spawn 的子进程。
- 只读：只写自己的临时目录。

## 检查项
1. `/health` 200 且在**三态**之内、耗时小（廉价路径没偷偷加载模型）；
2. **并发重活时轻请求不受影响**（真 socket + 真线程池）：N 条 `/ingest/preview` 在飞时，
   `/health` 的 p95 仍应是毫秒级；
3. `FileResponse` 真流式：`/documents/{id}/file` 的**字节数 == 磁盘文件大小**、内容 sha256 一致
   （`def` 化 + 热重载都没把它弄坏）；
4. 转型后的 body 契约：坏 JSON ⇒ **422**（`POST /api/v1/bookmarks`）。
   （SSE 那一条没做：它要种一套合规评审数据，属 `tests/test_compliance.py` 的覆盖，
   本脚本不重复造——**如实说明**，不假装验过。）

用法：`.venv\\Scripts\\python.exe scripts\\verify-engine-uvicorn.py [--heavy 12] [--json]`
退出码 0 = 全过。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: 真入口 `python -m src.core.main` 之前会**预热流程图 OCR**（后台线程加载 RapidOCR，
#: 冷启动约 60s）——那会让本脚本的计时被 CPU 抢占污染。所以这里用**与 `run()` 等价的启动器**：
#: 同样 `bind_random()`（随机端口 + 一次性 token）+ `create_app(token)` + 真 uvicorn，
#: 只去掉预热。⚠ 这是刻意的差异，写在明面上。
_LAUNCHER = (
    "import uvicorn;"
    "from src.core.api.server import bind_random, create_app;"
    "port, token = bind_random();"
    "print(f'PORT={port}', flush=True);"
    "print(f'TOKEN={token}', flush=True);"
    "uvicorn.run(create_app(token), host='127.0.0.1', port=port, log_level='warning')"
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _req(url: str, method: str = "GET", body: bytes | None = None, hdr: dict | None = None,
         timeout: float = 30.0):
    r = urllib.request.Request(url, data=body, method=method,
                               headers={**(hdr or {}), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _wait_ready(base: str, timeout: float = 40.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            st, _ = _req(f"{base}/api/v1/health", timeout=2)
            if st == 200:
                return True
        except Exception:
            time.sleep(0.3)
    return False


def _make_pdf(path: Path, pages: int = 12) -> Path:
    import fitz
    doc = fitz.open()
    body = "本标准规定了动火作业的分级、审批、监护与作业后检查要求。"
    for i in range(pages):
        page = doc.new_page()
        y = 72.0
        for ln in range(28):
            page.insert_text((56, y), f"{i + 1}-{ln + 1} {body}", fontname="china-s",
                             fontsize=10.5)
            y += 24.0
    doc.save(str(path))
    doc.close()
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heavy", type=int, default=12, help="并发重活条数")
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="ks_uvicorn_"))
    env = {**os.environ, "KS_DATA_DIR": str(tmp), "PYTHONIOENCODING": "utf-8"}
    log = (tmp / "uvicorn.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-c", _LAUNCHER], cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        errors="replace", bufsize=1)
    port = token = None
    results: list[tuple[str, bool, str]] = []
    try:
        t0 = time.time()
        while time.time() - t0 < 45:
            line = proc.stdout.readline()
            if not line:
                break
            log.write(line)
            if line.startswith("PORT="):
                port = int(line.strip().split("=", 1)[1])
            elif line.startswith("TOKEN="):
                token = line.strip().split("=", 1)[1]
            if port and token:
                break
        if not (port and token):
            log.close()
            print("引擎没起来（没读到 PORT/TOKEN）；日志尾部：")
            print("\n".join((tmp / "uvicorn.log").read_text(encoding="utf-8",
                                                           errors="replace").splitlines()[-20:]))
            return 2
        # 之后把子进程剩余输出**持续抽干**，别让管道写满把引擎卡住
        import threading
        threading.Thread(target=lambda: [log.write(ln) for ln in proc.stdout],
                         daemon=True).start()
        base = f"http://127.0.0.1:{port}"
        HDR = {"Authorization": f"Bearer {token}"}
        if not _wait_ready(base):
            print("引擎起来了但 /health 不响应；日志尾部：")
            print("\n".join((tmp / "uvicorn.log").read_text(encoding="utf-8",
                                                           errors="replace").splitlines()[-20:]))
            return 2

        # 0) 种一行 doc_meta（指向真 PDF），供 FileResponse 检查
        pdf = _make_pdf(tmp / "verify.pdf", args.pages)
        import sqlite3
        conn = sqlite3.connect(str(tmp / "database" / "knowledge.db"))
        conn.execute("INSERT OR REPLACE INTO doc_meta (doc_id, standard_no, standard_name,"
                     " short_code, current_revision_id, domain_tags, file_path, file_hash)"
                     " VALUES ('doc_uv','GB UV-2025','uvicorn 验证','UV','r1','[]',?, 'h')",
                     (str(pdf),))
        conn.commit()
        conn.close()

        # 1) /health 廉价三态 + 耗时
        t0 = time.perf_counter()
        st, raw = _req(f"{base}/api/v1/health", timeout=10)
        dt = time.perf_counter() - t0
        body = json.loads(raw or b"{}")
        ok1 = (st == 200 and body.get("vector_engine") in ("ok", "offline", "unknown")
               and dt < 1.0)
        results.append(("/health 廉价三态且 <1s", ok1,
                        f"status={st} vector_engine={body.get('vector_engine')} {dt:.4f}s"))

        # 2) 并发重活时轻请求不受影响（真 socket）
        r = _req(f"{base}/api/v1/documents/doc_uv/file", hdr=HDR, timeout=20)
        file_bytes = r[1]
        ok3 = (r[0] == 200 and len(file_bytes) == pdf.stat().st_size
               and hashlib.sha256(file_bytes).hexdigest()
               == hashlib.sha256(pdf.read_bytes()).hexdigest())
        results.append(("FileResponse 字节数/sha256 与磁盘一致", ok3,
                        f"HTTP={r[0]} {len(file_bytes)}B vs {pdf.stat().st_size}B"))

        payload = json.dumps({"path": str(pdf)}).encode()
        lat: list[float] = []

        def _light() -> float:
            t = time.perf_counter()
            _req(f"{base}/api/v1/health", timeout=20)
            return time.perf_counter() - t

        with ThreadPoolExecutor(max_workers=args.heavy + 4) as pool:
            heavy = [pool.submit(_req, f"{base}/api/v1/ingest/preview", "POST", payload, HDR, 120)
                     for _ in range(args.heavy)]
            time.sleep(0.05)                      # 让重活先进去
            light = [pool.submit(_light) for _ in range(8)]
            lat = sorted(f.result() for f in light)
            heavy_codes = [h.result()[0] for h in heavy]
        p95 = lat[min(len(lat) - 1, int(len(lat) * 0.95))] if lat else 0.0
        ok2 = p95 < 0.5 and all(c == 200 for c in heavy_codes)
        results.append((f"{args.heavy} 条重活在飞时 /health 仍毫秒级", ok2,
                        f"p95={p95:.4f}s max={lat[-1] if lat else 0:.4f}s "
                        f"heavy_http={sorted(set(heavy_codes))}"))

        # 3) 坏 JSON ⇒ 422（转型后的 body 契约）
        st4, _ = _req(f"{base}/api/v1/bookmarks", "POST", b"{not json", HDR)
        results.append(("坏 JSON ⇒ 422（body 走签名后的契约）", st4 == 422, f"HTTP={st4}"))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()

    failed = [r for r in results if not r[1]]
    if args.json:
        print(json.dumps([{"check": n, "ok": ok, "detail": d} for n, ok, d in results],
                         ensure_ascii=False, indent=1))
    else:
        for n, ok, d in results:
            print(f"{'PASS' if ok else 'FAIL'}  {n} — {d}")
        print(f"\n== verify-engine-uvicorn {len(results) - len(failed)}/{len(results)} "
              f"{'PASS' if not failed else 'FAIL'} ==（临时目录 {tmp}，端口 {port}）")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
