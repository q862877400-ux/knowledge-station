"""定向复现：`POST /api/v1/ingest/bulk/{batch_id}/resume` 会不会把整个引擎卡死。

## 为什么单独写这一支

全量探针（`07-runtime-probe.py`）跑出：第 106 条 `resume` 用了 12 秒返回 500，
**之后所有请求（含 `/api/v1/health`）连续 70 条全部超时**。

`/health` 是门禁里实测「12 条重活在飞时仍毫秒级」的那个廉价探针。
它都超时 ⇒ 引擎整体不响应了。

**一次不算数。** 本脚本做定向复现，并记录「卡死前后」的对照：

1. 起引擎 → `/health` 记一次基线
2. 调 `resume`（用一个**故意不存在**的批次号）
3. 立刻再调 `/health`
4. 再调一条无关的便宜接口（`GET /api/v1/update/subscriptions`）
5. 如果 `/health` 也超时 ⇒ 记录「该请求让引擎整体不响应」

**只记录，不判断该不该修。**
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "survey" / "data"
SEED = ROOT / "tests" / "fixtures" / "seed" / "knowledge-seed.db"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = Path(sys.executable)


def call(port: int, token: str, method: str, path: str, body=None,
         timeout: float = 10.0) -> dict:
    url = f"http://127.0.0.1:{port}{path}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    rec = {"method": method, "path": path}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            rec.update(status=resp.status, ms=round((time.time() - t0) * 1000, 1),
                       bytes=len(raw))
    except urllib.error.HTTPError as exc:
        rec.update(status=exc.code, ms=round((time.time() - t0) * 1000, 1))
        try:
            exc.read()
        except Exception:                       # noqa: BLE001
            rec["body_read_failed"] = True
    except Exception as exc:                    # noqa: BLE001
        rec.update(status=None, ms=round((time.time() - t0) * 1000, 1),
                   exception=f"{type(exc).__name__}: {str(exc)[:60]}")
    return rec


def prepare(tmp: Path) -> Path:
    """临时数据目录 + 种子库副本 + 清掉孤儿影子表（否则 init_schema 撞名）。"""
    data_dir = tmp / "data"
    (data_dir / "database").mkdir(parents=True)
    db = data_dir / "database" / "knowledge.db"
    shutil.copy2(SEED, db)
    conn = sqlite3.connect(str(db))
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'")]
        tset = set(tables)
        suffixes = ("_data", "_idx", "_content", "_docsize", "_config",
                    "_chunks", "_info", "_rowids", "_vector_chunks00",
                    "_metadatachunks00", "_metadatatext00")
        for name in tables:
            base = None
            for sfx in suffixes:
                if name.endswith(sfx):
                    base = name[: -len(sfx)]
                    break
            if base is None or base in tset:
                continue
            if conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] != 0:
                continue
            conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        conn.commit()
    finally:
        conn.close()
    (tmp / "models").mkdir()
    return data_dir


def main() -> int:
    if not SEED.exists():
        print(f"✘ 种子库不存在：{SEED}", file=sys.stderr)
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="ks_rep_"))
    data_dir = prepare(tmp)
    env = dict(os.environ)
    env["KS_DATA_DIR"] = str(data_dir)
    env["KS_MODELS_DIR"] = str(tmp / "models")
    env["PYTHONIOENCODING"] = "utf-8"
    for k in ("KS_REAL_DB", "RUN_LIVE"):
        env.pop(k, None)

    proc = subprocess.Popen([str(PY), "-m", "src.core.main"], cwd=str(ROOT), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace",
                            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    port = token = None
    try:
        t0 = time.time()
        while time.time() - t0 < 120:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            line = line.strip()
            if line.startswith("KNOWLEDGE_STATION_PORT="):
                port = int(line.split("=", 1)[1])
            elif line.startswith("KNOWLEDGE_STATION_TOKEN="):
                token = line.split("=", 1)[1]
            if port and token:
                break
        if not (port and token):
            print("✘ 没拿到端口/令牌", file=sys.stderr)
            return 1
        time.sleep(2)
        print(f"引擎 PID={proc.pid} 端口={port}")

        steps = []
        # 启动一个后台线程把 stderr 全收下来（引擎的异常只会打在 stderr，
        # 不收集就永远不知道 `resume` 到底抛了什么）
        import threading
        err_buf: list[str] = []

        def _drain() -> None:
            try:
                for ln in proc.stderr:            # type: ignore[union-attr]
                    err_buf.append(ln)
            except Exception:                     # noqa: BLE001
                pass

        threading.Thread(target=_drain, daemon=True).start()

        steps.append(("基线 /health", call(port, token, "GET", "/api/v1/health")))
        steps.append(("基线 无关接口",
                      call(port, token, "GET", "/api/v1/update/subscriptions")))
        # 用一个**拼出来的**不存在批次号（避免发字面 `{batch_id}`）
        steps.append(("resume 不存在的批次",
                      call(port, token, "POST",
                           "/api/v1/ingest/bulk/probe-nonexistent/resume", {})))
        steps.append(("之后 /health（10 秒超时）",
                      call(port, token, "GET", "/api/v1/health", timeout=10)))
        steps.append(("之后 无关接口（10 秒超时）",
                      call(port, token, "GET", "/api/v1/update/subscriptions",
                           timeout=10)))
        steps.append(("再等 20 秒后 /health",
                      (time.sleep(20), call(port, token, "GET", "/api/v1/health",
                                            timeout=10))[1]))

        print()
        for label, r in steps:
            st = r.get("status") if r.get("status") is not None else "无响应"
            print(f"  {label:28} status={st!s:8} {r.get('ms')}ms "
                  f"{r.get('exception') or ''}")

        # ⚠ 第一版写成 `steps[3].get(...)` —— steps 的元素是 `(label, rec)` 元组，
        #   直接 .get 会 AttributeError，导致 JSON 根本没落盘。改成 `[1]`。
        after_ok = steps[3][1].get("status") is not None
        payload = {
            "generated_by": "scripts/survey/08-repro-resume-hang.py",
            "question": ("`POST /api/v1/ingest/bulk/{batch_id}/resume` 用不存在的批次号调用后，"
                         "引擎是否还响应？"),
            "isolation": "临时数据目录 + 种子库副本；绝不碰 var/data",
            "verdict": ("引擎仍响应" if after_ok else "**引擎整体不响应**（含 /health）"),
            "steps": [{"label": lbl, **r} for lbl, r in steps],
            "engine_stderr_tail": "".join(err_buf)[-3000:],
        }
        DATA.mkdir(parents=True, exist_ok=True)
        out = DATA / "repro_resume_hang.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n结论：{payload['verdict']}")
        print(f"→ {out.relative_to(ROOT)}")
        return 0
    finally:
        if proc.poll() is None:
            try:
                proc.send_signal(signal.CTRL_BREAK_EVENT
                                 if hasattr(signal, "CTRL_BREAK_EVENT") else signal.SIGTERM)
            except Exception:                   # noqa: BLE001
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        # 引擎可能留了子进程/线程，日志里记一下
        err = ""
        try:
            if proc.stderr:
                err = proc.stderr.read()[:3000]
        except Exception:                       # noqa: BLE001
            pass
        if err.strip():
            print("\n引擎 stderr（末尾 3000 字）：")
            print(err)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
