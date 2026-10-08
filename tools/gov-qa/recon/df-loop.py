"""无人值守循环 · 人民网领导留言板·地方时间流（people-liuyan-df）。

交接配方（2026-10-08 HANDOVER §4.1）：每批 `--limit 30` 采留言板时间流，
睡 65 分钟后重复；游标在 `data/.people-liuyan-df.cursor`（**不会重采**）；
**403 就停（别硬刷）** —— 这里检测到 403 先睡 3 小时再续，连 4 次 403 退出
（重启即可）。去重靠 (source, id)，天然续采。

日志：`recon/df-loop.log`（追加）。
启动（脱离本会话，后台跑）：
    python tools/gov-qa/recon/df-loop.py
停止：直接结束该进程；游标已落盘，下次继续不重采。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LOG = HERE / "df-loop.log"
BATCH = 30
SLEEP_OK = 65 * 60        # 批间歇 ≥1h（HANDOVER 配方）
SLEEP_403 = 3 * 3600      # 403 → 3h 冷却
MAX_CONSEC_403 = 4


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def main() -> int:
    log(f"df-loop 启动（batch={BATCH}, 正常睡 {SLEEP_OK//60}min, "
        f"403 睡 {SLEEP_403//3600}h, 连 {MAX_CONSEC_403} 次 403 退出）")
    consec403 = 0
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    while True:
        p = subprocess.run(
            [sys.executable, str(ROOT / "harvest.py"),
             "--site", "people-liuyan-df", "--limit", str(BATCH)],
            capture_output=True, text=True, cwd=str(ROOT),
            encoding="utf-8", errors="replace", env=env)
        log(f"批结束 exit={p.returncode}")
        for ln in (p.stdout or "").splitlines():
            if ln.strip():
                log("  | " + ln.strip()[:200])
        for ln in (p.stderr or "").splitlines():
            if ln.strip():
                log("  ! " + ln.strip()[:200])
        blob = (p.stdout or "") + (p.stderr or "")
        if "403" in blob:
            consec403 += 1
            log(f"检测到 403（连续第 {consec403} 次）")
            if consec403 >= MAX_CONSEC_403:
                log("连续 4 次 403，退出（宿主重启后 python df-loop.py 续采）")
                return 0
            time.sleep(SLEEP_403)
        else:
            consec403 = 0
            time.sleep(SLEEP_OK)


if __name__ == "__main__":
    sys.exit(main())
