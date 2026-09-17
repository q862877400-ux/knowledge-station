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

用法：`.venv\\Scripts\\python.exe scripts\\verify-engine-uvicorn.py [--heavy 12] [--json] [--keep-tmp]`
退出码 0 = 全过。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

#: ⚠ 本脚本要打印**中文 + `⇒`**；Windows 默认控制台编码是 GBK ⇒ 不重设会在**最后打印结果时**
#: `UnicodeEncodeError` 崩掉（检查其实已经跑完，拿不到结论——§10.86 实测踩到）。所以在最前面
#: 把 stdout/stderr 重设为 UTF-8（替换不可编码字符，绝不因为"打不出来"而丢结果）。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
    except Exception:                                             # pragma: no cover
        pass

ROOT = Path(__file__).resolve().parents[1]

#: 真入口 `python -m src.core.main` = `_warmup_figure_ocr()` + `run()`。预热是**后台线程**加载
#: RapidOCR（冷启动约 60s，会抢 CPU 污染计时），所以这里**只去掉预热**，其余**逐步照抄**：
#: 直接调 `run()`（它自己做 `bind_random()` → `create_app(token)` → `start_write_worker()`
#: → 打 `KNOWLEDGE_STATION_PORT/TOKEN` + 写 `engine.session.json` → `uvicorn.run(...)` →
#: `finally: stop_write_worker()`），连**握手前缀**都用真的。
#:
#: ⚠ **这是第二版**（§10.86 修复核 b15 的 B3）：第一版用自己拼的启动器（只 `bind_random` +
#: `create_app` + `uvicorn.run`），**漏了** `start_write_worker()`（单写者队列消费端）、
#: `engine.session.json`、`stop_write_worker()`，把握手前缀写成 `PORT=`/`TOKEN=`
#: （真入口是 `KNOWLEDGE_STATION_PORT=`/`KNOWLEDGE_STATION_TOKEN=`）⇒ 复核判"刻意差异"为
#: **PARTLY**：它验的并不是真入口的启动路径。现在**逐字调 `run()`**，差异只剩"不预热 OCR"。
_LAUNCHER = "from src.core.api.server import run; run()"

#: 真入口的握手前缀（照抄，别自己发明一个 —— 那样连"握手格式"都没被验到）。
_PORT_PREFIX = "KNOWLEDGE_STATION_PORT="
_TOKEN_PREFIX = "KNOWLEDGE_STATION_TOKEN="


# ⚠ 这里原来有个 `_free_port()`：**死代码**（端口实际由子进程里的 `bind_random()` 决定），
# 而且它用 `socket` 而这个文件**没有** `import socket`（第一版有过，改写启动器时删了 import）
# —— 一旦有人调用它就 `NameError`。§10.88 按独立复核 b17 的 LOW-1 **删掉**。


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
    ap.add_argument("--keep-tmp", action="store_true",
                    help="保留临时目录（默认跑完删掉；它含 knowledge.db / verify.pdf / uvicorn.log）")
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
            if line.startswith(_PORT_PREFIX):
                port = int(line.strip().split("=", 1)[1])
            elif line.startswith(_TOKEN_PREFIX):
                token = line.strip().split("=", 1)[1]
            if port and token:
                break
        if not (port and token):
            log.close()
            print(f"引擎没起来（没读到 {_PORT_PREFIX}/{_TOKEN_PREFIX}）；日志尾部：")
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
        # 临时目录默认删掉（§10.86 修复核 b15 的 INFO-4：第一版跑一次留一个含
        # knowledge.db / verify.pdf / uvicorn.log 的目录，从不清理）。要事后取证就 `--keep-tmp`。
        #
        # ⚠ **第二版仍然没删干净，而且还在打印"（已删除）"—— 这是 b16 的 LOW-2**：
        # Windows 上 SQLite 的 `-wal/-shm` 句柄在子进程退出后可能**延迟释放** ⇒
        # `shutil.rmtree(ignore_errors=True)` 只删掉一部分、**静默留下** `database/`，
        # 而本脚本接着打印"已删除"（**主动报告假事实**，比不删更糟）。
        # 现在：删完**回读**目录是否真的没了；没删掉就**重试几次**，仍不行就**如实打印**，
        # 绝不把失败说成成功。
        if not args.keep_tmp:
            for attempt in range(5):
                shutil.rmtree(tmp, ignore_errors=True)
                if not tmp.exists():
                    break
                time.sleep(0.3)
        tmp_gone = not tmp.exists()

    failed = [r for r in results if not r[1]]
    if args.keep_tmp:
        tmp_note = f"临时目录 {tmp}（--keep-tmp 保留）"
    elif tmp_gone:
        tmp_note = f"临时目录 {tmp}（已删除）"
    else:
        tmp_note = f"临时目录 {tmp}（**删除失败**：多半是 SQLite -wal/-shm 句柄还在，可手动删）"
    if args.json:
        print(json.dumps([{"check": n, "ok": ok, "detail": d} for n, ok, d in results],
                         ensure_ascii=False, indent=1))
    else:
        for n, ok, d in results:
            print(f"{'PASS' if ok else 'FAIL'}  {n} — {d}")
        print(f"\n== verify-engine-uvicorn {len(results) - len(failed)}/{len(results)} "
              f"{'PASS' if not failed else 'FAIL'} ==（{tmp_note}，端口 {port}）")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
