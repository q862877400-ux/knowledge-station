# -*- coding: utf-8 -*-
"""批次配置（单一所有者）：让 watchdog / driver 知道**当前该跑哪一批**。

为什么要单独一个文件：`watchdog.ps1` 原先把语料清单**硬编码**在脚本里，
每换一批都得手工改脚本——无人值守推进时这就是断点（改漏一次就白跑一批）。
现改为读 `evolve/current_batch.json`，换批只需 `next_batch.py` + 本文件更新。

路径一律存**相对 var/ocr-loop 的 POSIX 形式**（`evolve/work_batch2.json`），
由消费者各自拼根——避免"绝对路径里带空格/中文被 PowerShell 拆参"的老问题
（实测：`-ArgumentList` 传含空格路径会被拆成多参）。

`KS_CORPUS_LIST` 环境变量优先（临时实验用），否则读本文件，再否则回退首批。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = HERE / "evolve"
CURRENT = EV / "current_batch.json"
DEFAULT_LIST = "evolve/fresh_corpus_work.json"


def _rel(p: str) -> str:
    """把任意写法归一成「相对 var/ocr-loop 的 POSIX 相对路径」。"""
    s = (p or "").strip().replace("\\", "/")
    if not s:
        return DEFAULT_LIST
    q = Path(s)
    if q.is_absolute():
        try:
            return q.resolve().relative_to(HERE).as_posix()
        except ValueError:
            return s
    for pref in ("var/ocr-loop/", "./"):
        if s.startswith(pref):
            return s[len(pref):]
    return s


def current() -> dict:
    """当前批次配置：`{list, log, err, batch, ts}`（值均为相对 var/ocr-loop）。"""
    if CURRENT.exists():
        try:
            obj = json.loads(CURRENT.read_text(encoding="utf-8"))
            if obj.get("list"):
                obj["list"] = _rel(obj["list"])
                return obj
        except Exception:  # noqa: BLE001
            pass
    env = (os.environ.get("KS_CORPUS_LIST") or "").strip()
    lst = _rel(env) if env else DEFAULT_LIST
    base = Path(lst).stem
    return {"list": lst, "log": f"vlm_{base}.log", "err": f"vlm_{base}.err",
            "batch": 1, "ts": ""}


def set_current(list_rel: str, batch: int,
                log: str = "", err: str = "") -> dict:
    lst = _rel(list_rel)
    base = Path(lst).stem
    obj = {"list": lst, "log": log or f"vlm_{base}.log",
           "err": err or f"vlm_{base}.err", "batch": int(batch),
           "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    CURRENT.write_text(json.dumps(obj, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    return obj


def main() -> None:
    a = sys.argv[1:]
    if not a or a[0] == "show":
        print(json.dumps(current(), ensure_ascii=False, indent=1))
        return
    if a[0] == "set":
        # set <list> <batch> [log] [err]
        if len(a) < 3:
            print("用法：batch_config.py set <list> <batch> [log] [err]")
            sys.exit(2)
        obj = set_current(a[1], int(a[2]),
                          a[3] if len(a) > 3 else "",
                          a[4] if len(a) > 4 else "")
        print(f"当前批次 → #{obj['batch']} {obj['list']}（日志 {obj['log']}）")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
