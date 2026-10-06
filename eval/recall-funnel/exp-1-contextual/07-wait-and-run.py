"""E1 步骤 7：**守候并自动出结论** —— 等 `clause_vec_ctx` 齐了就跑 A/B + 判决。

为什么要有它：全库算向量约 100 分钟。与其每隔一会儿人工看一眼（容易看成"没动"），
不如把"等齐 → 跑 04 → 跑 06"串成一条链跑在后台，条件满足前不碰任何东西。

守候条件（两个都要满足，避免在向量还在写的时候就开始比）：
 1. `clause_vec_ctx` 行数 ≥ 目标（默认 521,978 = `retrieval_text_ctx` 的行数）；
 2. 行数**连续两次读数不变**（间隔 60 秒）⇒ 写完了。

用法（后台）：
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\07-wait-and-run.py
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXP = HERE / "exp.db"
PY = ROOT / ".venv" / "Scripts" / "python.exe"


def count() -> int:
    """读一次行数。⚠ 必须加载 sqlite-vec 扩展，否则读 `vec0` 虚拟表会报 no such module: vec0
    （第一次写这个函数时漏了，守候进程刚起来就崩了 —— 留痕）。"""
    sys.path.insert(0, str(ROOT))
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    try:
        load_vec_extension(c)
        return c.execute("SELECT COUNT(*) FROM clause_vec_ctx").fetchone()[0]
    finally:
        c.close()


def _target() -> int:
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    try:
        return c.execute("SELECT COUNT(*) FROM retrieval_text_ctx").fetchone()[0]
    finally:
        c.close()


def main() -> int:
    target = _target()
    print(f"[wait] 目标 = {target} 行（= retrieval_text_ctx 的行数）", flush=True)

    prev = -1
    while True:
        n = count()
        print(f"[wait] {time.strftime('%H:%M:%S')}  {n} / {target}", flush=True)
        if n >= target and n == prev:
            print("[wait] 行数已稳定 ⇒ 认为写完了", flush=True)
            break
        prev = n
        time.sleep(60)

    time.sleep(30)          # 让最后一个事务落干净
    for step in ("04-ab-eval.py", "06-verdict.py"):
        print(f"[run] ===== {step} =====", flush=True)
        r = subprocess.run([str(PY), "-u", str(HERE / step)], cwd=str(ROOT))
        print(f"[run] {step} 退出码 = {r.returncode}", flush=True)
    print("[run] 全链完成", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
