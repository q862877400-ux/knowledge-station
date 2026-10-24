"""检查第 7 步（运行时层）：**真启动引擎，把每条端点都调一遍**。

## 为什么必须有这一步

前面十步全是**静态**的：看代码写了什么。但业主问的是「了解透彻了吗」——
**静态检查验不了「跑起来会怎样」**。这是本检查最大的一道缺口，本脚本补它。

## 安全边界（硬约束）

| 约束 | 做法 |
|---|---|
| **绝不碰生产数据** | `KS_DATA_DIR` 指向**临时目录**，里面是随仓种子库的副本（13 MB） |
| **绝不碰生产模型** | `KS_MODELS_DIR` 也指向临时目录 ⇒ 模型不可用就降级，不下载 |
| **不落任何持久产物** | 临时目录用完即删；只把**探测结果**写进 `docs/survey/data/` |
| **每条请求有超时** | 单条 12 秒；整体有上限 |
| **引擎一定是被我们启动的** | 记 PID，结束时只杀这个 PID |

## 记录什么（只记录，不判断）

每条端点：方法、路径、请求体、**真实状态码**、耗时、响应体是否合法 JSON、
响应顶层键、错误码（如果有）。

## 口径

- 用**空 body**（`{}`）发请求 ⇒ `422`/`400` 是**正常结果**（说明它要必填字段），
  不是失败；
- 会触发云模型调用的端点（问答类）在无密钥时会失败 ⇒ 如实记成失败；
- **不判断「该返回什么」**，只记「实际返回了什么」。
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
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

#: 单条请求超时（秒）。有的端点会等云模型 ⇒ 12 秒后放弃并记 timeout。
REQ_TIMEOUT_S = 12
#: 引擎启动等待上限（秒）。
BOOT_TIMEOUT_S = 120

#: 这些路径**可能真的改数据**。虽然用的是临时库，仍单独标记出来，
#: 让下一棒知道「这些端点跑过会写库」。
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def free_port() -> int:
    """要一个空闲端口（只为探活，引擎自己会绑随机端口）。"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def wait_port(port: int, proc: subprocess.Popen, timeout: int) -> bool:
    """等端口能连上（进程还活着为前提）。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def call(port: int, token: str, method: str, path: str,
         body: dict | None = None) -> dict:
    """发一条请求，返回记录（不抛异常，失败也记）。"""
    url = f"http://127.0.0.1:{port}{path}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    rec: dict = {"method": method, "path": path,
                 "body_sent": body if body is not None else None}
    try:
        with urllib.request.urlopen(req, timeout=REQ_TIMEOUT_S) as resp:
            raw = resp.read()
            rec["status"] = resp.status
            rec["ms"] = round((time.time() - t0) * 1000, 1)
            rec["bytes"] = len(raw)
            try:
                payload = json.loads(raw.decode("utf-8", "replace"))
                rec["json"] = True
                if isinstance(payload, dict):
                    rec["top_keys"] = sorted(payload.keys())[:8]
                    if isinstance(payload.get("error"), dict):
                        rec["error_code"] = payload["error"].get("code")
                    elif "code" in payload:
                        rec["error_code"] = payload.get("code")
                else:
                    rec["top_keys"] = []
            except json.JSONDecodeError:
                rec["json"] = False
                rec["snippet"] = raw[:120].decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        # ⚠ 读错误体**也可能超时**（实测踩到）：`exc.read()` 在套接字超时时抛
        #   `TimeoutError`，而那时已经在 except 分支里，外层那个
        #   `except (TimeoutError, socket.timeout)` **接不住**（Python 不会
        #   在同一 try 的其它 except 里再捕获新异常）。
        #   ⇒ 单独兜住，把它记成「拿到了状态码但没读到响应体」。
        rec["status"] = exc.code
        try:
            raw = exc.read()
        except Exception as exc2:                  # noqa: BLE001 - 失败要具名
            rec["ms"] = round((time.time() - t0) * 1000, 1)
            rec["body_read_failed"] = f"{type(exc2).__name__}: {str(exc2)[:80]}"
            return rec
        rec["ms"] = round((time.time() - t0) * 1000, 1)
        rec["bytes"] = len(raw)
        try:
            payload = json.loads(raw.decode("utf-8", "replace"))
            rec["json"] = True
            if isinstance(payload, dict):
                rec["top_keys"] = sorted(payload.keys())[:8]
                if isinstance(payload.get("error"), dict):
                    rec["error_code"] = payload["error"].get("code")
                elif "code" in payload:
                    rec["error_code"] = payload.get("code")
                if isinstance(payload.get("detail"), list):
                    rec["validation_errors"] = len(payload["detail"])
        except json.JSONDecodeError:
            rec["json"] = False
            rec["snippet"] = raw[:120].decode("utf-8", "replace")
    except (TimeoutError, socket.timeout):
        rec["status"] = None
        rec["ms"] = round((time.time() - t0) * 1000, 1)
        rec["timeout"] = True
    except Exception as exc:                      # noqa: BLE001 - 失败要具名
        rec["status"] = None
        rec["ms"] = round((time.time() - t0) * 1000, 1)
        rec["exception"] = f"{type(exc).__name__}: {exc}"[:160]
    return rec


def main() -> int:
    if not SEED.exists():
        print(f"✘ 种子库不存在：{SEED}", file=sys.stderr)
        return 1
    routes_doc = json.loads((DATA / "endpoints.json").read_text(encoding="utf-8"))
    routes = routes_doc["backend"]
    print(f"要探的端点：{len(routes)} 条")

    tmp = Path(tempfile.mkdtemp(prefix="ks_probe_"))
    data_dir = tmp / "data"
    (data_dir / "database").mkdir(parents=True)
    db_copy = data_dir / "database" / "knowledge.db"
    shutil.copy2(SEED, db_copy)

    # ⚠ **实测发现（2026-10-24，只记录不修）**：种子库里有 vec0 的 **6 张影子表**
    #   （`clause_vec_chunks` / `_info` / `_metadatachunks00` / `_metadatatext00` /
    #   `_rowids` / `_vector_chunks00`，都是普通表、0 行），但**没有 `clause_vec`
    #   这个虚拟表本身**。
    #   ⇒ 引擎启动时 `init_schema()` 执行 `CREATE VIRTUAL TABLE clause_vec`，
    #     vec0 建影子表撞名 ⇒ `StorageError: 初始化 schema 失败:
    #     Could not create '_info' shadow table: table "clause_vec_info" already exists`
    #   ⇒ **种子库不能用来启动引擎**，只能像测试那样直接读 SQLite。
    #
    #   `make-seed-db.py` 的注释（L25 / L209）本意是「vec 影子表不建、由虚拟表自动生成」，
    #   但影子表还是被带进来了 —— 这是**记录**，不是判断该不该修。
    #
    #   本探针只为了让引擎能起来：在**临时副本**上删掉这 6 张空影子表，
    #   让 `init_schema()` 自己重建（重建后是空向量表，不影响端点行为探测）。
    import sqlite3 as _sq
    conn = _sq.connect(str(db_copy))
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'")]
        tset = set(tables)
        # 影子表的后缀（fts5 与 vec0 各一族）
        suffixes = ("_data", "_idx", "_content", "_docsize", "_config",
                    "_chunks", "_info", "_rowids", "_vector_chunks00",
                    "_metadatachunks00", "_metadatatext00")
        dropped = []
        for name in tables:
            base = None
            for sfx in suffixes:
                if name.endswith(sfx):
                    base = name[: -len(sfx)]
                    break
            if base is None or base in tset:
                # 基表在 ⇒ 这是真虚拟表的影子表，留着（init_schema 的 IF NOT EXISTS 会跳过）
                continue
            # **两道守卫，防止误删**：
            #   ① 基表不存在（说明虚拟表本身没被带进来 ⇒ init_schema 会重建它）
            #   ② 该影子表**0 行**（`app_config` 这类真表有数据，第①条对它成立但第②条挡住它）
            n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            if n != 0:
                continue
            conn.execute(f'DROP TABLE IF EXISTS "{name}"')
            dropped.append(name)
        conn.commit()
        if dropped:
            print(f"  临时副本上删掉 {len(dropped)} 张孤儿影子表"
                  "（基虚拟表不在 + 0 行，否则 init_schema 撞名）")
            print(f"    删的是：{', '.join(sorted(dropped))}")
    finally:
        conn.close()
    models_dir = tmp / "models"
    models_dir.mkdir()
    print(f"临时数据目录：{tmp}")
    print(f"  库里是种子库副本（{SEED.stat().st_size / 1048576:.1f} MB），"
          "**不碰 var/data**")

    env = dict(os.environ)
    env["KS_DATA_DIR"] = str(data_dir)
    env["KS_MODELS_DIR"] = str(models_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    for k in ("KS_REAL_DB", "RUN_LIVE"):
        env.pop(k, None)

    proc = subprocess.Popen(
        [str(PY), "-m", "src.core.main"],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    print(f"引擎 PID={proc.pid}，等端口…")

    port = token = None
    t0 = time.time()
    try:
        while time.time() - t0 < BOOT_TIMEOUT_S:
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
            err = proc.stderr.read()[:2000] if proc.stderr else ""
            print(f"✘ 没拿到端口/令牌。进程退出码={proc.poll()}\n{err}",
                  file=sys.stderr)
            return 1
        print(f"  端口={port}  令牌=***{token[-4:]}")
        if not wait_port(port, proc, 60):
            print("✘ 端口连不上", file=sys.stderr)
            return 1
        print("  端口已开")

        # 健康检查（不需令牌）
        health = call(port, token, "GET", "/api/v1/health")
        print(f"  /health → {health.get('status')} "
              f"{health.get('ms')}ms keys={health.get('top_keys')}")

        results = []
        for i, r in enumerate(routes, 1):
            method = r["method"]
            path = r["path"]
            # 路径里的 {x} 用占位值替代；占位值故意选不存在的 id
            real = path
            for ph in ("{channel_id}", "{doc_id}", "{clause_id}", "{folder_id}",
                       "{item_id}", "{id}", "{bookmark_id}", "{snapshot_id}",
                       "{version_id}", "{package_id}", "{dump_id}"):
                real = real.replace(ph, "probe-nonexistent")
            body = {} if method in WRITE_METHODS else None
            rec = call(port, token, method, real, body)
            rec.update({"declared_path": path, "probe_path": real,
                        "handler": r.get("handler"), "file": r.get("file"),
                        "lineno": r.get("lineno"),
                        "is_write_method": method in WRITE_METHODS})
            results.append(rec)
            if i % 25 == 0:
                print(f"  已探 {i}/{len(routes)}")

        # 汇总
        by_status: dict[str, int] = {}
        for r in results:
            k = str(r.get("status") if r.get("status") is not None
                    else ("timeout" if r.get("timeout") else "exception"))
            by_status[k] = by_status.get(k, 0) + 1
        print("\n状态码分布：", json.dumps(by_status, ensure_ascii=False))

        payload = {
            "generated_by": "scripts/survey/07-runtime-probe.py",
            "engine": {"module": "src.core.main", "port": port,
                       "token_last4": token[-4:], "pid": proc.pid},
            "isolation": {
                "KS_DATA_DIR": "临时目录（种子库副本，13 MB）",
                "KS_MODELS_DIR": "临时空目录（模型不可用 ⇒ 降级）",
                "note": "**绝不碰 var/data**；临时目录用完即删",
            },
            "caliber": (
                "每条端点用**空 body**（`{}`）探测；"
                "`422`/`400` 是**正常结果**（说明它要必填字段），不是失败。"
                "会触发云模型的端点在没有密钥时会失败 —— 如实记录。"
                "**只记实际返回了什么，不判断该返回什么。**"
                "路径里的 `{xxx}` 占位符统一替换成 `probe-nonexistent`。"
            ),
            "timeout_s": REQ_TIMEOUT_S,
            "counts": {"routes_probed": len(results), "by_status": by_status},
            "health": health,
            "results": results,
        }
        DATA.mkdir(parents=True, exist_ok=True)
        out = DATA / "runtime_probe.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"\n→ {out.relative_to(ROOT)}")
        return 0
    finally:
        # 只杀我们启动的那个 PID
        if proc.poll() is None:
            try:
                proc.send_signal(signal.CTRL_BREAK_EVENT
                                 if hasattr(signal, "CTRL_BREAK_EVENT") else signal.SIGTERM)
            except Exception:                     # noqa: BLE001
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"已清理临时目录（引擎退出码={proc.returncode}）")


if __name__ == "__main__":
    sys.exit(main())
