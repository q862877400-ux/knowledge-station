"""循环状态汇总 + RESUME.md 生成（2026-09-15 立）。

会话/模型断链后，接手者只需读 var/ocr-loop/RESUME.md：
进度到哪、哪些问题类已累计到修复线、下一步跑什么命令。

用法：python var/ocr-loop/report.py
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 原地改，勿包新 wrapper
VARDIR = Path(__file__).resolve().parent
LEDGER = VARDIR / "ledger.jsonl"
STATE = VARDIR / "loop_state.json"
FIXED = VARDIR / "fixed_classes.json"
RESUME = VARDIR / "RESUME.md"

#: 已达修复线的问题类 → 修复记录（修复提交后写入，避免重复触发）
FIX_LINE = 3


def load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def load_fixed() -> dict:
    if FIXED.exists():
        try:
            return json.loads(FIXED.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def summarize() -> dict:
    entries = load_jsonl(LEDGER)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    fixed = load_fixed()

    docs_ok = [e for e in entries if e.get("status") == "ok"]
    docs_err = [e for e in entries if e.get("status") not in ("ok",)]
    # 按 stem 去重（同一文档可能有多条失败 + 一条成功）
    seen: dict[str, dict] = {}
    for e in docs_ok:
        seen[e.get("stem")] = e
    uniq_ok = list(seen.values())

    tally: dict[str, int] = {}
    evid: dict[str, list[str]] = {}
    for e in entries:
        for cls, rec in (e.get("classes") or {}).items():
            tally[cls] = tally.get(cls, 0) + int(rec.get("count") or 0)
            evid.setdefault(cls, [])
            for ev in rec.get("evidence") or []:
                if ev and ev not in evid[cls]:
                    evid[cls].append(ev)

    open_classes = {k: v for k, v in tally.items()
                    if v >= FIX_LINE and k not in fixed}
    low_total = sum(int((e.get("qc") or {}).get("conf_dist", {}).get("low(<0.85)") or 0)
                    for e in uniq_ok)
    clause_total = sum(int((e.get("qc") or {}).get("clauses") or 0) for e in uniq_ok)
    return {"entries": entries, "state": state, "fixed": fixed, "tally": tally,
            "evid": evid, "open_classes": open_classes, "docs_ok": uniq_ok,
            "docs_err": docs_err, "low_total": low_total,
            "clause_total": clause_total}


def write_resume(s: dict) -> None:
    st = s["state"]
    lines = [
        "# OCR 循环 RESUME（断链恢复入口）",
        "",
        f"> 自动生成于 {time.strftime('%Y-%m-%d %H:%M:%S')}。**接手第一步：读本文件，"
        f"第二步执行下方「继续」命令。**",
        "",
        "## 当前进度",
        "",
        f"- 已入库文档（成功）：**{len(s['docs_ok'])}** 部",
        f"- 循环状态：rounds_done={st.get('rounds_done')} ok={st.get('ok')} "
        f"error={st.get('error')} stopped_reason={st.get('stopped_reason')}",
        f"- 最后一部：{st.get('last_stem')}（{st.get('last_status')}）",
        f"- 累计正文条款：{s['clause_total']} 条；低置信(<0.85)：{s['low_total']} 条",
        "",
        "## 继续（断链后照抄执行）",
        "",
        "```powershell",
        "cd 'D:\\AI\\work space\\zcode'",
        "# 1) 看状态（刷新本文件）",
        "& '.\\\\.venv\\\\Scripts\\\\python.exe' -X utf8 var\\\\ocr-loop\\\\report.py",
        "# 2) 续跑循环（后台作业；rounds/minutes 二选一）",
        "& '.\\\\.venv\\\\Scripts\\\\python.exe' -X utf8 var\\\\ocr-loop\\\\loop.py --rounds 8",
        "```",
        "",
        "## 问题类累计（跨文档同类，≥3 触发根因修复）",
        "",
        "| 问题类 | 累计 | 状态 | 证据条款 |",
        "|---|---|---|---|",
    ]
    for cls, n in sorted(s["tally"].items(), key=lambda kv: -kv[1]):
        if cls in s["fixed"]:
            status = f"已修（{s['fixed'][cls].get('date','')}）"
        elif n >= FIX_LINE:
            status = "**达线待修**"
        else:
            status = "累计中"
        ev = "、".join((s["evid"].get(cls) or [])[:6])
        lines.append(f"| {cls} | {n} | {status} | {ev} |")
    if not s["tally"]:
        lines.append("| （暂无） | 0 | — | — |")
    lines += [
        "",
        "## 已修复类（不再重复触发）",
        "",
    ]
    if s["fixed"]:
        for cls, rec in s["fixed"].items():
            lines.append(f"- **{cls}** — {rec.get('date','')} · "
                         f"{rec.get('commit','')} · {rec.get('note','')}")
    else:
        lines.append("- （暂无）")
    lines += [
        "",
        "## 最近 8 条台账",
        "",
        "| 时间 | 文档 | 状态 | 条款 | 低置信 | 命中类 |",
        "|---|---|---|---|---|---|",
    ]
    for e in s["entries"][-8:]:
        qc = e.get("qc") or {}
        cd = qc.get("conf_dist") or {}
        cls = "、".join((e.get("classes") or {}).keys())
        lines.append(f"| {e.get('ts')} | {(e.get('stem') or '')[:34]} | "
                     f"{e.get('status')} | {qc.get('clauses','')} | "
                     f"{cd.get('low(<0.85)','')} | {cls} |")
    lines += [
        "",
        "## 逐轮协议（不变）",
        "",
        "1. `pick_next.py` 选一部未入库的国标（去重三键：全串/号段/号段+年份）",
        "2. `round.py` 走正规 daemon 深度解析管线入库（云优先 → 本地兜底）",
        "3. QC：只统计 `content_type='normal'` 正文条款的 `ocr_confidence` 分布 + 低置信抽样",
        "4. `classify.py` 给低置信条款打问题类标签 → ledger.jsonl",
        "5. 同类跨文档累计 ≥3 → systematic-debugging 根因修复（规范所有者层）+ "
        "回归测试 + 门禁 + 提交，然后写入 fixed_classes.json",
        "",
    ]
    RESUME.write_text("\n".join(lines), encoding="utf-8")


def main(quiet: bool = False) -> None:
    s = summarize()
    write_resume(s)
    if quiet:
        return
    st = s["state"]
    print(f"进度：入库成功 {len(s['docs_ok'])} 部 | rounds_done={st.get('rounds_done')} "
          f"ok={st.get('ok')} error={st.get('error')}")
    print(f"条款 {s['clause_total']} 条 | 低置信 {s['low_total']} 条")
    if s["open_classes"]:
        print("达线待修：")
        for cls, n in sorted(s["open_classes"].items(), key=lambda kv: -kv[1]):
            print(f"  - {cls}: {n} 次 | 证据 {s['evid'].get(cls, [])[:4]}")
    else:
        print("达线待修：无")
    print("累计中：", {k: v for k, v in sorted(s["tally"].items(), key=lambda kv: -kv[1])
                    if k not in s["fixed"] and v < FIX_LINE})
    print(f"已生成 {RESUME}")


if __name__ == "__main__":
    main()
