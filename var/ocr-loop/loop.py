"""循环自治运行器 + 断链恢复（2026-09-15 立）。

把「循环推进」与「模型回合」解耦：循环在后台作业里自己跑、自己持久化、
自己重试；模型回合（或整个会话）断掉都不影响它继续导入下一部标准。会话
恢复时读 next_action() 输出的 RESUME.md 即可接手。

用法：
  python var/ocr-loop/loop.py --rounds 8            # 跑 8 轮
  python var/ocr-loop/loop.py --minutes 90          # 跑 90 分钟
  python var/ocr-loop/loop.py --status              # 只打印当前状态并刷新 RESUME.md

容错（断链恢复的具体机制）：
- 每轮结束写 loop_state.json（原子替换）→ 进程被杀也已知进度
- 单轮异常不终止循环：记 ledger.error + 继续下一部（连续 3 次异常才停，防系统性故障空转）
- 超时/网络类瞬时错误：退避后重试 1 次（云通道偶发慢，实测 10238 出现过）
- tried/ledger/next_pick/probe 缓存全部落盘 → 重跑不会重复导入已完成文档
"""
from __future__ import annotations

import io
import json
import sys
import time
import traceback
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 原地改，勿包新 wrapper
VARDIR = Path(__file__).resolve().parent
ROOT = VARDIR.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(VARDIR))

import round as R  # noqa: E402

STATE = VARDIR / "loop_state.json"
RETRYABLE = ("timeout", "Timeout", "连接", "Connection", "SSL", "HTTP", "云解析")


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "rounds_done": 0,
            "ok": 0, "error": 0, "consecutive_errors": 0,
            "last_stem": None, "last_status": None, "stopped_reason": None}


def save_state(s: dict) -> None:
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STATE)


def ledger_tail(n: int = 5) -> list[dict]:
    p = VARDIR / "ledger.jsonl"
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()[-n:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def one_round(state: dict) -> bool:
    """跑一轮；返回 True=成功。异常向上抛由调用方记 error。"""
    import pick_next
    pick_next.main()
    pk = R.pick()
    r = R.ingest(pk)
    st = r.get("status")
    msg = (r.get("message") or "")
    # 瞬时错误：退避后重试一次
    if st not in ("ok", "duplicate") and any(k in msg for k in RETRYABLE):
        print(f"[retry] 瞬时错误，60s 后重试一次: {msg[:80]}")
        time.sleep(60)
        r = R.ingest(pk)
        st = r.get("status")
        msg = (r.get("message") or "")
    if st not in ("ok", "duplicate"):
        R.record(pk, r, None)
        R.mark_tried(pk, note=f"ingest:{msg[:60]}")
        state["error"] += 1
        state["last_stem"], state["last_status"] = pk["stem"], st
        return False
    did = r.get("doc_id") or R.doc_id_of(pk["stem"])
    q = R.qc(did)
    R.record(pk, r, q)
    R.mark_tried(pk)
    state["ok"] += 1
    state["last_stem"], state["last_status"] = pk["stem"], "ok"
    print(f"[round ok] {pk['stem'][:46]} | clauses={q.get('clauses')} "
          f"low={q['conf_dist'].get('low(<0.85)')}")
    return True


def main() -> None:
    args = sys.argv[1:]
    if "--status" in args:
        import report
        report.main()
        return
    rounds = 6
    minutes = 60.0
    if "--rounds" in args:
        rounds = int(args[args.index("--rounds") + 1])
    if "--minutes" in args:
        minutes = float(args[args.index("--minutes") + 1])

    state = load_state()
    deadline = time.monotonic() + minutes * 60
    print(f"[loop] 起跑 rounds={rounds} minutes={minutes} "
          f"已累计 rounds_done={state['rounds_done']}")

    for i in range(rounds):
        if time.monotonic() > deadline:
            state["stopped_reason"] = "minutes_budget"
            break
        if state["consecutive_errors"] >= 3:
            state["stopped_reason"] = "3_consecutive_errors"
            print("[loop] 连续 3 次异常，停下（防系统性故障空转）")
            break
        try:
            ok = one_round(state)
            state["consecutive_errors"] = 0 if ok else state["consecutive_errors"] + 1
        except Exception as e:  # noqa: BLE001 — 单轮异常不终止循环
            state["consecutive_errors"] += 1
            state["error"] += 1
            print(f"[loop] 轮次异常（继续下一部）: {type(e).__name__}: {e}")
            with open(VARDIR / "ledger.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "stem": state.get("last_stem"), "status": "exception",
                    "message": f"{type(e).__name__}: {str(e)[:160]}",
                    "qc": None, "classes": {},
                    "trace": traceback.format_exc()[-600:],
                }, ensure_ascii=False) + "\n")
        state["rounds_done"] += 1
        save_state(state)
        try:
            import report
            report.main(quiet=True)
        except Exception:
            pass

    save_state(state)
    print(f"[loop] 结束：{json.dumps({k: state[k] for k in ('rounds_done','ok','error','stopped_reason')}, ensure_ascii=False)}")
    try:
        import report
        report.main()
    except Exception:
        pass


if __name__ == "__main__":
    main()
