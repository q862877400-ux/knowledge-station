# -*- coding: utf-8 -*-
r"""`vlm_ocr` 单实例闸门的行为测试（不烧云额度：故意让批次"无事可做"）。

**为什么专门测它**（2026-09-15 实测代价）：`commit_rec` 是
`state[key] = rec; save_json(STATE, state)`——**整体读改写、无跨进程锁**。
两个 `vlm_ocr` 并发跑同一批时，后写者用自己启动时的旧快照覆盖已落盘记录：
完成记录被抹掉（重启后重复提交、重复烧云额度），实测批次 3 还出现
**双方都卡在 8/500、日志数分钟不动、CPU 30 秒只涨 0.7 秒**的僵局。
当时 driver 每 20 秒重拉一次就是双实例的来源（根因已在 driver 侧用
`START_GRACE_S` 修掉）。本闸门是第二道防线，必须能证明它真的挡住。

判据（三条都要成立）：
  1. 无锁时能拿到锁，且写出正确 payload；
  2. 锁被**活进程**持有时，新实例**正常退出**（退出码 0，不是异常）；
  3. 锁的持有者**已死**时，新实例**接管**（不能永久堵死——被杀/崩溃是常态）。

跑法：`& .\.venv\Scripts\python.exe -X utf8 var\ocr-loop\test_single_instance.py`
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
LOCK = HERE / "vlm_ocr.lock"
saved = LOCK.read_text(encoding="utf-8") if LOCK.exists() else None

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


def run_vlm(tag: str, lock_wait: int = 0) -> tuple[int, str]:
    """跑一个 vlm_ocr 子进程（清单合法但 **0 部目标** → 不烧额度）。

    清单必须是**合法 JSON**：用一个不存在的路径会让 `targets_from_corpus_list`
    之前就抛异常退出（实测踩过），那样测的是"启动失败"而不是闸门。

    `lock_wait=0`：闸门抢不到锁时**不等待**、立刻退出——测试要的是快速判定。
    生产默认 900 秒（`vlm_ocr.LOCK_WAIT_S`）：driver 每 20 秒重拉一次，闸门若
    立刻退出，driver 的 5 次机会会在 100 秒内耗尽而误报"反复中断→待人工"。
    """
    probe = HERE / "evolve" / "_si_empty_probe.json"
    probe.write_text(json.dumps({"n": 0, "paths": []}, ensure_ascii=False),
                     encoding="utf-8")
    p = subprocess.run(
        [PY, "-X", "utf8", "var/ocr-loop/vlm_ocr.py",
         "--corpus-list", str(probe), "--lock-wait", str(lock_wait),
         "--docs", "1", "--channel", "auto", "--parallel", "1"],
        # **必须显式 `encoding="utf-8"`**（2026-09-16 实测缺陷）：
        # `text=True` 在 Windows 上默认用**区域编码**（本机 cp936/GBK）解码，
        # 而子进程输出是 UTF-8 中文（闸门原因等）→ 读取线程抛
        # `UnicodeDecodeError: 'gbk' codec can't decode byte 0xad`，
        # **捕获到的输出变成空的**，于是 3 项断言全部误报失败。
        # 症状极易被读成"单实例闸门坏了"，实际是**测试夹具的编码 bug**。
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT), timeout=180)
    txt = (p.stdout or "") + (p.stderr or "")
    (HERE / f"_si_{tag}.log").write_text(txt, encoding="utf-8")
    probe.unlink(missing_ok=True)
    return p.returncode, txt


try:
    print("=== 1) 锁的持有者已死（陈旧锁）→ 新实例必须接管，不能永久堵死 ===")
    LOCK.write_text(json.dumps({"pid": 999999, "ts_unix": 0,
                                "corpus": "dead-holder"}), encoding="utf-8")
    rc, txt = run_vlm("stale")
    check("陈旧锁 → 退出码 0", rc, 0)
    check("陈旧锁 → 报出陈旧并接管", "陈旧锁" in txt and "接管" in txt, True)

    print("\n=== 2) 锁被**本进程**（活 pid）持有 → 新实例必须让位 ===")
    LOCK.write_text(json.dumps({"pid": __import__("os").getpid(),
                                "ts_unix": time.time(),
                                "corpus": "probe-holder"}), encoding="utf-8")
    rc, txt = run_vlm("blocked")
    check("活锁 → 正常退出（退出码 0）", rc, 0)
    check("活锁 → 打印闸门原因", "单实例闸门" in txt and "已有 vlm_ocr 在跑" in txt, True)
    check("活锁 → 未进入批处理", "=== VLM OCR" not in txt, True)
    # 锁不能被让位者清掉（否则第二个也会放行）
    kept = json.loads(LOCK.read_text(encoding="utf-8"))
    check("让位者不清锁", kept.get("corpus"), "probe-holder")

    print("\n=== 3) 无锁 → 能拿到锁并正常跑完 ===")
    LOCK.unlink(missing_ok=True)
    rc, txt = run_vlm("free")
    check("无锁 → 退出码 0", rc, 0)
    check("无锁 → 进入批处理", "=== VLM OCR" in txt, True)
finally:
    if saved is not None:
        LOCK.write_text(saved, encoding="utf-8")
    else:
        LOCK.unlink(missing_ok=True)
    for f in HERE.glob("_si_*.log"):
        f.unlink(missing_ok=True)
    for f in HERE.glob("_si_*.err"):
        f.unlink(missing_ok=True)

print()
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
