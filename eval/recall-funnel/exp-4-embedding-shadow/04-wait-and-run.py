"""E4 · 步骤 4：**守候并自动出结论** —— 等 `clause_vec_qwen` 齐了就跑 A/B + 判决。

**为什么需要它**：全量重算约 50 分钟，而目标轮次触发得比它快得多
（实测轮次间隔只推进约 40 秒的算力）⇒ 若靠"每轮看一眼"，轮次会在重算完成前用光。
E1 那轮已经用过这个办法（`exp-1-contextual/07-wait-and-run.py`），本轮照做：
把"等齐 → 跑对照 → 出判决"串成一条后台链，**与轮次解耦**。

守候条件（两个都满足才算写完）：
 1. `clause_vec_qwen` 行数 ≥ 目标（= `clause_vec` 的行数）；
 2. 行数**连续两次读数不变**（间隔 60 秒）。

跑完把结果与判决写进同一个日志；轮次只需读日志，不必阻塞。

用法（后台）：
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\04-wait-and-run.py
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


def count(table: str, where: str = "") -> int:
    """⚠ 读 `vec0` 表**必须**加载 sqlite-vec 扩展（本会话已踩过四次）。"""
    sys.path.insert(0, str(ROOT))
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    try:
        load_vec_extension(c)
        return c.execute(f"SELECT COUNT(*) FROM {table} {where}").fetchone()[0]
    finally:
        c.close()


def main() -> int:
    # ⚠ 目标**不能**取 `clause_vec` 的行数（522,021）——
    #   实验表的来源是"正文非空"的条文（521,978），拿 522,021 当门槛会**永远等不到**。
    #   这是本脚本第一版的 bug，已修（留痕）。
    target = count("clause_revision", "WHERE trim(coalesce(content_text,'')) <> ''")
    print(f"[wait] 目标 = {target} 行（= 正文非空的条文数；**不是** clause_vec 的 "
          f"{count('clause_vec')} 行）", flush=True)
    prev = -1
    while True:
        n = count("clause_vec_qwen")
        print(f"[wait] {time.strftime('%H:%M:%S')}  {n} / {target}", flush=True)
        if n >= target and n == prev:
            print("[wait] 行数已稳定 ⇒ 认为写完了", flush=True)
            break
        prev = n
        time.sleep(60)

    time.sleep(30)
    for step in ("02-ab-eval.py", "03-verdict-e4.py"):
        print(f"[run] ===== {step} =====", flush=True)
        r = subprocess.run([str(PY), "-u", str(HERE / step)], cwd=str(ROOT))
        print(f"[run] {step} 退出码 = {r.returncode}", flush=True)
    print("[run] 全链完成", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
