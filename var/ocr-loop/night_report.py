# -*- coding: utf-8 -*-
"""夜间运行报告（吸收《夜间全自主运行指南》第八章，2026-09-15 立）。

目标：**早上五分钟能读完**，且每条结论都带数值（不带数值的结论等于没写）。
章节照指南第八章：运行时段 / 侦察结果 / 修复结果 / verifier 小节 /
扩样进度 / 系统状态 / 待人工清单 / 建议下一步。

用法：
  python var/ocr-loop/night_report.py               # 写 evolve/NIGHT_REPORT.md 并打印
  python var/ocr-loop/night_report.py --window 8    # 指定横比窗口
  python var/ocr-loop/night_report.py --quiet       # 只写文件不打印

只读：本工具不写库、不动 parse_out、不调云、不改任何轮次结果。
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVOLVE = HERE / "evolve"
ROUNDS = EVOLVE / "rounds"
OUT = EVOLVE / "NIGHT_REPORT.md"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _load(p: Path, default=None):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return out


def _rounds_present() -> list[int]:
    return sorted(int(p.name.split("-")[1]) for p in ROUNDS.glob("round-*")
                  if (p / "docs").is_dir() and any((p / "docs").glob("*.json")))


# --------------------------------------------------------------- 章节
def sec_window() -> list[str]:
    st = _load(EVOLVE / "state.json", {}) or {}
    instr = _jsonl(EVOLVE / "instrument.jsonl")
    rnds = _rounds_present()
    lines = ["## 1. 运行时段", ""]
    lines.append(f"- 当前轮：**#{st.get('round', '?')}** · 游标 {st.get('cursor', '?')}"
                 f" · 阶段 {st.get('phase', '?')}")
    if rnds:
        lines.append(f"- 已有结果的轮次：{len(rnds)} 个（#{rnds[0]} … #{rnds[-1]}）")
    if instr:
        first, last = instr[0], instr[-1]
        lines.append(f"- 仪器记录 {len(instr)} 条 · 最新 {last.get('ts', '?')}")
        dets = {x.get("detector") for x in instr}
        owners = {x.get("owner") for x in instr}
        lines.append(f"- 检测器哈希：{len(dets)} 个不同值"
                     f"{'（**变过**——跨轮比较须只看哈希相同的轮）' if len(dets) > 1 else '（稳定）'}")
        lines.append(f"- 所有者哈希：{len(owners)} 个不同值"
                     f"（修复会让它变，属预期）")
        _ = first
    lines.append("")
    return lines


def sec_scout() -> list[str]:
    sc = _load(EVOLVE / "scout.json")
    work = _load(EVOLVE / "fresh_corpus_work.json")
    lines = ["## 2. 侦察结果", ""]
    if not sc:
        lines += ["- ⚠ 尚无 `scout.json`——先跑：`scout.py scout --vlm-only`", ""]
        return lines
    # **过期检测**（必须显式说明）：换了语料/改了判据之后，旧 scout 数字不再代表
    # 现状；不标出来就会拿过拟合的旧结论继续做修复决策。
    stale = []
    sc_ts = str(sc.get("ts") or "")
    if work and str(work.get("built_at") or "") > sc_ts:
        stale.append(f"语料在 {work.get('built_at')} 重建过（新工作集 "
                     f"{work.get('n', 0)} 部），晚于本次侦察 {sc_ts}")
    if stale:
        lines += ["- ⚠ **本侦察已过期，不足以支撑修复决策**："]
        lines += [f"  - {s}" for s in stale]
        lines += ["  - 处置：重跑 `scout.py scout --vlm-only` 后再决定修哪个类", ""]
    lines.append(f"- 侦察时间 {sc_ts or '?'} · 评估 {sc.get('docs_evaluated', 0)} 部"
                 f"（pipeline 跳过 {sc.get('skipped_pipeline', 0)}）"
                 f" · 留出集 {sc.get('holdout_n', 0)} 部")
    # **批量进行中读数会误导**（2026-09-15 实测教训）：语料未跑完时，尚无产物的
    # 文档会被 `artifact_index.resolve` 兜底成「重读 PDF 文本层」，于是
    #   ① 账面出现"文本层重提 N 部"，看着像 VLM 覆盖不足；
    #   ② 更糟：PDF 文本层缺字形（PUA）会被当成"管线缺陷"报出来——
    #      实测 pua-residue 报 2 部，批量跑完后归零（VLM 像素 OCR 取回真字）。
    # 故把来源构成显式打出来，看到 textlayer/GAP 非零就该先问"这批跑完了吗"。
    kinds = sc.get("source_kinds") or {}
    if kinds:
        tl = sum(v for k, v in kinds.items() if "textlayer" in k)
        gap = sum(v for k, v in kinds.items()
                  if k.endswith("|unknown") or k.endswith("|?"))
        vm = sum(v for k, v in kinds.items()
                 if any(b in k for b in ("hybrid", "vlm", "vlm-engine")))
        lines.append(f"- 样本来源：VLM 产物 {vm} · 文本层重提 {tl} · 无产物 {gap}")
        if tl or gap:
            lines.append("  - ⚠ **该批可能尚未跑完**：无产物的文档会被兜底成"
                         "「重读 PDF 文本层」，其缺陷（含 PDF 自身缺字形 PUA）"
                         "会被误报成管线缺陷。取基线前请确认 "
                         "`vlm_ocr.py --status` 已无待处理。")
    lines.append(f"- 命中总计 {sc.get('total_hits', 0)} · "
                 f"前三类占比 **{sc.get('top3_share', 0):.1%}**")
    ranked = sorted((sc.get("classes") or {}).items(),
                    key=lambda kv: -kv[1].get("docs", 0))
    if ranked:
        lines += ["", "| 类 | 命中部数 | 占比 | 层 |", "|---|---:|---:|---|"]
        for c, v in ranked[:10]:
            lines.append(f"| `{c}` | {v.get('docs', 0)} | "
                         f"{v.get('share', 0):.1%} | {v.get('strata', [])} |")
    over = sc.get("over_line") or []
    lines += ["", f"- **达线类**（≥3 部）：{over or '（无）'}"]
    if sc.get("catastrophic"):
        lines.append(f"- ⚠ 灾难性文档 {len(sc['catastrophic'])} 部（单本 >20 类，已排除统计）")
    if sc.get("layer0_only"):
        lines.append(f"- ⚠ 仅老标准层出现的类：{sc['layer0_only']}（不参与全局修复决策）")
    lines.append("")
    return lines


def sec_fixes() -> list[str]:
    fixes = _jsonl(EVOLVE / "fixes.jsonl")
    led = _load(HERE / "fixed_classes.json", {}) or {}
    lines = ["## 3. 修复结果", ""]
    lines.append(f"- 修复记录 **{len(fixes)}** 次 · 台账登记 {len(led)} 类")
    if led:
        lines += ["", "| 类 | 日期 | 处置 |", "|---|---|---|"]
        for c, e in sorted(led.items()):
            commit = str(e.get("commit", ""))[:60]
            mark = "（不驱动修复）" if any(m in commit for m in ("不修", "已知限制")) else ""
            lines.append(f"| `{c}` | {e.get('date', '?')} | {commit}{mark} |")
    if fixes:
        last = fixes[-1]
        lines += ["", f"- 最近一次：轮 #{last.get('round')} · `{last.get('cls')}` · "
                      f"{last.get('commit', '')[:50]}"]
    lines.append("")
    return lines


def sec_verifier() -> list[str]:
    """verifier / arbiter 小节（指南要求报告必须含）。"""
    arb = EVOLVE / "arbiter"
    lines = ["## 4. verifier / arbiter 小节", ""]
    if not arb.exists():
        lines += ["- 尚无仲裁记录——同类达 3 次尝试时用："
                  "`evolve.py arbiter plan --class <类>`", ""]
        return lines
    batches = sorted([p for p in arb.glob("arb-*") if p.is_dir()])
    decs = _jsonl(arb / "decisions.jsonl")
    lines.append(f"- 仲裁批次 **{len(batches)}** 个 · 已落决策 {len(decs)} 条")
    for b in batches:
        man = _load(b / "manifest.json", {}) or {}
        sc = _load(b / "scores.json")
        n_top2 = len((sc or {}).get("top2") or [])
        n_invalid = len((sc or {}).get("invalid") or [])
        forced = "（≥3 次强制仲裁）" if man.get("forced_by_attempts") else ""
        lines.append(f"  - `{b.name}` 类 `{man.get('cls', '?')}`{forced}"
                     f"：方案 {n_top2 + n_invalid} 份，有效进前二 {n_top2}，"
                     f"判无效 {n_invalid}")
    if decs:
        last = decs[-1]
        lines.append(f"- 最近决策：类 `{last.get('cls')}` 胜者 "
                     f"`{Path(str(last.get('winner'))).name}`")
    lines += ["", "- 复核（指南第九条）：`arbiter check --base-round N --cur-round M`"
                  " —— 新冒类 >3 或某类上升 >20% 判失败并回滚", ""]
    return lines


def sec_expansion() -> list[str]:
    """扩样进度：VLM 批量覆盖。"""
    lines = ["## 5. 扩样进度（VLM 语料面）", ""]
    state = _load(HERE / "vlm_ocr_state.json", {}) or {}
    ok = sum(1 for v in state.values()
             if v.get("status") in ("ok", "textlayer"))
    lines.append(f"- 已完成 VLM 化（记账）**{ok}** 部")
    work = _load(EVOLVE / "fresh_corpus_work.json")
    if work:
        lines.append(f"- 工作集 `fresh_corpus_work.json`：{work.get('n', 0)} 部"
                     f"（{work.get('built_at', '?')[:10]} 按用户指令换**全新语料**防过拟合）")
    quota = _load(HERE / "vlm_cloud_quota.json", {}) or {}
    day = time.strftime("%Y-%m-%d")
    lines.append(f"- 今日云文件用量 {quota.get(day, 0)}"
                 f"（上限 {__import__('os').environ.get('KW_DAILY_CLOUD_FILES', '5000')}）")
    log = HERE / "vlm_fresh.log"
    if log.exists():
        last = [x for x in log.read_text(encoding="utf-8",
                                         errors="replace").splitlines() if x.strip()]
        if last:
            lines.append(f"- 批量日志尾：`{last[-1][:70]}`")
    lines.append("")
    return lines


def _proc_alive(pat: str) -> list[int]:
    """匹配命令行的进程 pid（与 watchdog 同判据：进程存活，不看文件 mtime）。"""
    try:
        ps = ("Get-CimInstance Win32_Process -Filter "
              "\"Name='python.exe' OR Name='pythonw.exe'\" | "
              f"Where-Object {{ $_.CommandLine -like '*{pat}*' }} | "
              "Select-Object -ExpandProperty ProcessId")
        r = subprocess.run(["pwsh", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=30)
        return [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    except Exception:  # noqa: BLE001
        return []


def sec_system() -> list[str]:
    lines = ["## 6. 系统状态", ""]
    batch = _proc_alive("vlm_ocr.py")
    lines.append(f"- VLM 批量进程：{'存活 pid=' + ','.join(map(str, batch)) if batch else '**不在运行**'}")
    wd = HERE / "watchdog.log"
    if wd.exists():
        tail = [x for x in wd.read_text(encoding="utf-8",
                                        errors="replace").splitlines() if x.strip()]
        if tail:
            lines.append(f"- 看门狗最近：`{tail[-1][:80]}`")
        else:
            lines.append("- 看门狗日志为空（**守护可能没在跑**——进程死了没人拉起）")
    else:
        lines.append("- ⚠ 无 `watchdog.log`：守护从未运行过")
    sent = EVOLVE / "db_sentinel.jsonl"
    n = len(_jsonl(sent))
    lines.append(f"- DB 哨兵记录 {n} 条（不落库核验：一变即停轮）")
    lines.append(f"- 检测器哈希 `{_detector_hash()}`")
    lines.append("")
    return lines


def _detector_hash() -> str:
    try:
        import sweep as SW
        return SW.detector_hash()
    except Exception:  # noqa: BLE001
        return "（取不到）"


def sec_manual() -> list[str]:
    """待人工清单：登记为已知限制/不修、以及仲裁失败的类。"""
    lines = ["## 7. 待人工清单", ""]
    led = _load(HERE / "fixed_classes.json", {}) or {}
    rows = [(c, str(e.get("commit", ""))) for c, e in led.items()
            if any(m in str(e.get("commit", "")) for m in ("不修", "已知限制"))]
    if not rows:
        lines.append("- （空）")
    for c, why in sorted(rows):
        lines.append(f"- `{c}`：{why[:80]}")
    decs = _jsonl(EVOLVE / "arbiter" / "decisions.jsonl")
    _ = decs
    lines.append("")
    return lines


def sec_next() -> list[str]:
    lines = ["## 8. 建议下一步", ""]
    rnds = _rounds_present()
    sc = _load(EVOLVE / "scout.json")
    work = _load(EVOLVE / "fresh_corpus_work.json")
    steps: list[str] = []
    scout_stale = bool(sc and work
                       and str(work.get("built_at") or "") > str(sc.get("ts") or ""))
    if not sc or scout_stale:
        steps.append("重跑侦察拿**当前语料**的地图：`scout.py scout --vlm-only` "
                     "→ `scout.py decide`（旧 scout 已过期，不可据以修类）")
    elif sc.get("over_line"):
        c = sc["over_line"][0]
        steps.append(f"修头部达线类 `{c}`（≥3 部）；先 "
                     f"`evolve.py evidence --round {rnds[-1] if rnds else 1} "
                     f"--class {c}` 取证，判「仪器误报 vs 管线真缺陷」后再动所有者层")
        steps.append(f"修完用留出集判定：`scout.py verify --class {c}`"
                     f"（下降 ≥30% 才算通过）")
    else:
        steps.append("无达线类 → 按指南扩样（当前语料面尚未铺开）")
    if len(rnds) >= 5:
        steps.append("五轮横比：`evolve.py compare --window 5`")
    steps.append("语料跑完一批即换**全新文档**（防过拟合）："
                 "`build_fresh_corpus.py` → `vlm_ocr.py --corpus-list …`")
    for i, s in enumerate(steps, 1):
        lines.append(f"{i}. {s}")
    lines.append("")
    return lines


def build(window: int = 5) -> str:
    _ = window
    head = [
        "# 夜间运行报告",
        "",
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "> 全自主夜间运行的晨读版：**五分钟读完**，每条结论都带数值。",
        "> 本报告只读生成，不改任何轮次结果。",
        "",
    ]
    body = (sec_window() + sec_scout() + sec_fixes() + sec_verifier()
            + sec_expansion() + sec_system() + sec_manual() + sec_next())
    return "\n".join(head + body)


def main() -> None:
    args = sys.argv[1:]
    w = int(args[args.index("--window") + 1]) if "--window" in args else 5
    md = build(w)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md, encoding="utf-8")
    if "--quiet" not in args:
        print(md)
    print(f"\n→ 已写 {OUT}")


if __name__ == "__main__":
    main()
