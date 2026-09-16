# -*- coding: utf-8 -*-
"""收敛循环 v2 编排器 —— 「改一处 → 全库重扫 → 与上一轮对比 → 直到零超线」。

用户订的循环（2026-09-15 原话）：
    每次改完一个 BUG，OCR 的时候都要 OCR 之前识别过的所有内容，
    然后和上一次做对比，看看这次的历史修复是不是对之前所有文档都有用……
    直到一直 OCR 一直不出问题为止。

**关键前提（已实测，probe_reuse.py / reuse_coverage.json）**：
库内 260/260 部文档的解析产物都在 `parse_out/<doc_id>/`（18 部文本层
blocks + 242 部深度 OCR 产物），覆盖率 **100%**。因此「全库重扫」走
`--reuse` 复用缓存 = **零 OCR · 零云额度 · 零 GPU**，把原本「小时级云额度」
一轮压到分钟级——这才让「每改一处就全库重验」在经济上真正成立。

一轮（round）的机械步骤：
  1. 全库复用重导：repair_corpus.py --only all_docs --reuse --reset
  2. 全库扫描：sweep.audit_db()（db 层 = 库里真实内容，唯一权威口径）
  3. 与上一快照 diff（检测器 hash 变化会被标记：防把「仪器变化」当「修复效果」）
  4. 判定：
     - **regressed**：已登记修好的类仍然达线 → 修复没生效 or 复用没覆盖到（最高优先级）
     - **over_line**：达线且从未修过 → 待修类
     - 两者皆空 → ✅ 收敛（用户要的终点）
  5. 落盘 `rounds/<n>.json`、更新 `CONVERGE.md` / `converge_state.json`

用法：
  python var/ocr-loop/converge.py round [--note "改了什么"] [--no-reprocess]
  python var/ocr-loop/converge.py status        # 看当前收敛状态（零副作用）
  python var/ocr-loop/converge.py targets       # 只列该修什么（零副作用）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import sweep  # noqa: E402 —— 复用同一套检测器（绝不另写一份，防仪器漂移）

SWEEPDIR = sweep.SWEEPDIR
LATEST = sweep.LATEST
ROUNDDIR = HERE / "rounds"
STATE = HERE / "converge_state.json"
REPORT = HERE / "CONVERGE.md"
LEDGER = HERE / "fixed_classes.json"
LOCK = HERE / ".converge.lock"
PY = ROOT / ".venv" / "Scripts" / "python.exe"


# ---------------------------------------------------------------- 台账
def fixed_ledger() -> dict:
    if not LEDGER.exists():
        return {}
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def should_be_clean(entry: dict) -> bool:
    """该登记项是否算「真修复」（必须在全库重扫后清空）。

    排除两类别名条目：
      - 「不修」：故意不修（如号尾吞数字：源文本歧义，启发式会误伤合法长号）
      - 「未达线」：累计中、尚未动手的类
    二者出现在台账里只是**登记**，不构成「修复失效」。
    """
    c = str(entry.get("commit", ""))
    return ("不修" not in c) and ("未达线" not in c)


# ---------------------------------------------------------------- 判读
def targets(snap: dict) -> dict:
    """从快照算出本轮该修什么：regressed（修复失效）优先于 over_line（待修）。"""
    s = snap["summary"]
    ledger = fixed_ledger()
    regressed, over_line = [], []
    for cls in s["over_line"]:
        n = s["classes"][cls]["docs"]
        entry = ledger.get(cls)
        if entry and should_be_clean(entry):
            regressed.append({"cls": cls, "docs": n,
                              "commit": str(entry.get("commit", ""))[:70]})
        else:
            over_line.append({"cls": cls, "docs": n,
                              "registered": bool(entry)})
    over_line.sort(key=lambda x: -x["docs"])
    return {"regressed": regressed, "over_line": over_line,
            "next": (regressed or over_line or [None])[0]}


def _load_last_round() -> dict | None:
    if not STATE.exists():
        return None
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _lock_guard() -> int | None:
    """串行护栏：并发入库会撞 doc_meta.standard_no UNIQUE（本会话实测 3 次）。"""
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text(encoding="utf-8").strip().split()[0])
        except Exception:  # noqa: BLE001
            pid = -1
        alive = False
        if pid > 0:
            try:
                os.kill(pid, 0)
                alive = True
            except OSError:
                alive = False
        if alive:
            print(f"❌ 已有收敛轮次在跑（pid={pid}，锁 {LOCK}）——拒绝并发重导。")
            return None
        print(f"⚠ 发现陈旧锁（pid={pid} 已不存在），接管。")
    LOCK.write_text(f"{os.getpid()} {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    encoding="utf-8")
    return os.getpid()


# ---------------------------------------------------------------- 一轮
def _reprocess() -> dict:
    """全库复用重导（零 OCR）。实时透传子进程输出。"""
    cmd = [str(PY), "-X", "utf8", str(HERE / "repair_corpus.py"),
           "--only", "all_docs", "--reuse", "--reset"]
    print(f"[round] 全库复用重导：{' '.join(cmd[2:])}")
    t0 = time.monotonic()
    p = subprocess.run(cmd, cwd=str(ROOT), text=True, encoding="utf-8",
                       errors="replace")
    wall = round(time.monotonic() - t0, 1)
    print(f"[round] 重导结束 rc={p.returncode} 用时 {wall}s")
    # 从 repair_log.jsonl 尾部统计本轮结果
    ok = fail = 0
    log = HERE / "repair_log.jsonl"
    if log.exists():
        lines = log.read_text(encoding="utf-8").splitlines()[-400:]
        for ln in lines:
            try:
                r = json.loads(ln)
            except Exception:  # noqa: BLE001
                continue
            if r.get("ingest_status") in ("ok", "duplicate"):
                ok += 1
            elif r.get("ingest_status"):
                fail += 1
    return {"rc": p.returncode, "wall_s": wall,
            "log_ok_recent": ok, "log_fail_recent": fail}


def _write_report(state: dict) -> None:
    lines = ["# 收敛循环（OCRI 自我进化）状态", "",
             f"更新：{state['ts']} · 轮次 **#{state['round']}** · "
             f"判定：**{'✅ 已收敛' if state['converged'] else '❌ 未收敛'}**", "",
             f"- 全库文档 {state['docs']} · 条款 {state['clauses']} · "
             f"低置信(<0.85) {state['low']}",
             f"- 检测器 `{state['detector']}` · 库指纹 `{state['corpus']}`",
             f"- 复用重导：{state.get('reprocess', {}).get('wall_s', '—')}s "
             f"（rc={state.get('reprocess', {}).get('rc', '—')}）", ""]
    if state["regressed"]:
        lines += ["## ⚠ 修复失效（已登记的类仍达线）", ""]
        for r in state["regressed"]:
            lines.append(f"- `{r['cls']}` 命中 {r['docs']} 部 · 原修复：{r['commit']}")
        lines.append("")
    if state["over_line"]:
        lines += ["## 待修类（达线 ≥3 部）", ""]
        for r in state["over_line"]:
            lines.append(f"- `{r['cls']}` 命中 {r['docs']} 部"
                         + ("（台账已登记但不算真修复）" if r["registered"] else ""))
        lines.append("")
    if not state["regressed"] and not state["over_line"]:
        lines += ["## ✅ 全量扫描零超线", "",
                  "所有类命中文档数均 < 3，且无新增类、无新命中文档 —— "
                  "循环达到用户设定的终点。", ""]
    else:
        nxt = state["next"]
        lines += [f"## 下一处根因修复目标", "",
                  f"`{nxt['cls']}`（命中 {nxt['docs']} 部）", ""]
    hist = state.get("history", [])[-12:]
    if hist:
        lines += ["## 轮次历史", "", "| 轮 | 时间 | 文档 | 条款 | 超线类数 | 判定 |",
                  "|---|---|---|---|---|---|"]
        for h in hist:
            lines.append(f"| #{h['round']} | {h['ts'][5:16]} | {h['docs']} | "
                         f"{h['clauses']} | {h['over_line_n']} | "
                         f"{'✅' if h['converged'] else '❌'} |")
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_round(args: list[str]) -> int:
    note = args[args.index("--note") + 1] if "--note" in args else ""
    if os.getpid() != _lock_guard():
        return 2
    try:
        prev = sweep.load_latest()
        rp = {} if "--no-reprocess" in args else _reprocess()

        snap = sweep.audit_db()
        SWEEPDIR.mkdir(parents=True, exist_ok=True)
        (SWEEPDIR / f"{snap['sweep_id']}-db.json").write_text(
            json.dumps(snap, ensure_ascii=False), encoding="utf-8")
        LATEST.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")

        d = sweep.diff(snap, prev)
        ok, why = sweep.converged(snap, d)
        tg = targets(snap)
        s = snap["summary"]

        st = _load_last_round() or {}
        rnd = int(st.get("round", 0)) + 1
        state = {"round": rnd, "ts": snap["ts"], "note": note,
                 "sweep_id": snap["sweep_id"], "detector": snap["detector"],
                 "corpus": snap["corpus"], "docs": s["docs"],
                 "clauses": s["clauses"], "low": s["low"],
                 "converged": ok, "why": why, "reprocess": rp,
                 "regressed": tg["regressed"], "over_line": tg["over_line"],
                 "next": tg["next"],
                 "diff": {k: d.get(k) for k in
                          ("instrument_changed", "cleared_classes",
                           "changed_classes", "new_classes", "docs", "clauses",
                           "low")},
                 "history": (st.get("history", []) +
                             [{"round": rnd, "ts": snap["ts"], "docs": s["docs"],
                               "clauses": s["clauses"],
                               "over_line_n": len(s["over_line"]),
                               "converged": ok}])}
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                         encoding="utf-8")
        ROUNDDIR.mkdir(parents=True, exist_ok=True)
        (ROUNDDIR / f"round-{rnd:03d}.json").write_text(
            json.dumps({"state": state, "summary": s, "diff": d},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        _write_report(state)

        print(f"\n=== 收敛轮次 #{rnd} ===")
        print(f"文档 {s['docs']} · 条款 {s['clauses']} · 低置信 {s['low']} · "
              f"超线类 {len(s['over_line'])}")
        if d.get("cleared_classes"):
            print(f"本轮清除类：{d['cleared_classes']}")
        if d.get("new_classes"):
            print(f"⚠ 新增类：{d['new_classes']}")
        if d.get("instrument_changed"):
            print("⚠ 检测器集已变——类级变化含仪器影响，勿直接归因修复")
        if tg["regressed"]:
            print("\n⚠ 修复失效（登记的类仍达线）：")
            for r in tg["regressed"]:
                print(f"  {r['cls']:26} {r['docs']} 部 ← {r['commit']}")
        if ok:
            print("\n✅ 已收敛：全量扫描零超线。")
        else:
            nxt = tg["next"]
            print(f"\n❌ 未收敛 —— 下一处修复目标：`{nxt['cls']}`"
                  f"（{nxt['docs']} 部）")
            ids = s["classes"][nxt["cls"]]["doc_ids"]
            for did in ids[:12]:
                print(f"    {snap['docs'][did]['standard_no']:<24} {did}")
        print(f"\n报告：var/ocr-loop/CONVERGE.md · 轮次档：rounds/round-{rnd:03d}.json")
        return 0 if ok else 1
    finally:
        LOCK.unlink(missing_ok=True)


def cmd_status(_args: list[str]) -> int:
    st = _load_last_round()
    if not st:
        print("尚无收敛轮次。先跑：python var/ocr-loop/converge.py round")
        latest = sweep.load_latest()
        if latest:
            s = latest["summary"]
            print(f"\n现存基线快照 {latest['sweep_id']}：文档 {s['docs']} · "
                  f"条款 {s['clauses']} · 超线类 {len(s['over_line'])}")
            print("  超线：" + ", ".join(
                f"{c}({s['classes'][c]['docs']}部)" for c in s["over_line"]))
        return 0
    print(f"轮次 #{st['round']} · {st['ts']} · "
          f"{'✅ 已收敛' if st['converged'] else '❌ 未收敛'}")
    print(f"文档 {st['docs']} · 条款 {st['clauses']} · 低置信 {st['low']}")
    if st["regressed"]:
        print("⚠ 修复失效：" + ", ".join(f"{r['cls']}({r['docs']}部)"
                                          for r in st["regressed"]))
    if st["over_line"]:
        print("待修：" + ", ".join(f"{r['cls']}({r['docs']}部)"
                                   for r in st["over_line"]))
    if st.get("next"):
        print(f"下一目标：{st['next']['cls']}")
    return 0


def cmd_targets(_args: list[str]) -> int:
    latest = sweep.load_latest()
    if not latest:
        print("无快照。请先跑 sweep.py 或 converge.py round")
        return 2
    tg = targets(latest)
    s = latest["summary"]
    print(f"快照 {latest['sweep_id']} · 检测器 {latest['detector']}")
    print(f"超线类 {len(s['over_line'])}：")
    for cls in s["over_line"]:
        print(f"  {cls:26} {s['classes'][cls]['docs']:4} 部 / "
              f"{s['classes'][cls]['clauses']:5} 条")
    if tg["regressed"]:
        print("\n⚠ 修复失效：")
        for r in tg["regressed"]:
            print(f"  {r['cls']:26} {r['docs']} 部 ← {r['commit']}")
    print(f"\n下一目标：{tg['next']['cls'] if tg['next'] else '（无 → 已收敛）'}")
    return 0


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    table = {"round": cmd_round, "status": cmd_status, "targets": cmd_targets}
    if cmd not in table:
        print(__doc__)
        sys.exit(2)
    sys.exit(table[cmd](args))


if __name__ == "__main__":
    main()
