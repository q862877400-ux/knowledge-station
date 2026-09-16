# -*- coding: utf-8 -*-
"""状态持久化：**未到终点的记录必须有唯一消费者**（2026-09-15 立）。

**为什么要专门确认**（实测缺陷，本测试就是它的回归护栏）：

`vlm_ocr_state.json` 里的 `pending-local` / `failed`（"未到终点"）**只存在于它所属
批次的清单里**，而 `batch_advance` 收批后立刻 `next_batch` 换一批**全新、零重叠**的
文档，`vlm_ocr` 也只会被以**当前批清单**拉起 → 上一批的残留**没有任何代码路径会
再消费它**。原实现把这件事靠注释假设成"下一轮必然重做"，现场反例：

- `GB／T 34001-2016`（152 页）、`GB／T 46085-2025`（27 页）在 2026-09-15
  19:46 / 20:13 被重分类为 `pending-local`；
- 批次 4 于 20:19 被宣布"已完成 496/500"、driver 立刻推进批次 5；
- 这两部此后**无人再碰**（批次 5 的清单里没有它们），而当时的会话把它报告成
  "已转 pending-local 的失败项会在下一轮自动重试"。

本测试用**行为断言**钉住三件事：
  ① `_carry_over` 会把全局残留并入下一批清单（唯一消费者）；
  ② 试满 `MAX_CARRY` / 能力边界 / 无源文件 → 转 `needs-human`（显式终点，不静默丢）；
  ③ `_wait_batch` 里**重分类发生在收批判据之前**（原缺陷正是顺序相反：
     先按 `failed` 当终点宣布完成，再把 failed 改成"未到终点"）。
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import batch_advance as B  # noqa: E402

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


TMP = Path(tempfile.mkdtemp(prefix="ks-carry-"))
EV = TMP / "evolve"
EV.mkdir(parents=True, exist_ok=True)
PDFS = TMP / "pdfs"
PDFS.mkdir(parents=True, exist_ok=True)


def mkpdf(stem: str) -> str:
    p = PDFS / f"{stem}.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return str(p)


# 现场复刻：全新一批 2 部 + 上批残留 3 部 + 已跳过/已完成各 1 部 + 无源文件 1 部
NEW = ["GB／T 9001-2016 全新甲", "GB／T 9002-2016 全新乙"]
CARRY = ["GB／T 34001-2016 中国修船质量标准", "GB／T 46085-2025 系留式观光气球通用技术条件"]
LOCALFAIL = "GB／T 16751.1-2023 中医临床诊疗术语"
NOPDF = "GB／T 0000-0000 无源文件旧回填"
OVER = "GB／T 20171-2006 巨型已跳过"
DONE = "GB／T 9999-2016 已完成"

STATE = {
    NEW[0]: {"status": "ok", "channel": "cloud", "pdf": mkpdf(NEW[0])},
    NEW[1]: {"status": None, "channel": None, "pdf": mkpdf(NEW[1])},   # 本批还没跑
    CARRY[0]: {"status": "pending-local", "channel": "cloud", "pdf": mkpdf(CARRY[0])},
    CARRY[1]: {"status": "failed", "channel": "cloud", "pdf": mkpdf(CARRY[1])},
    LOCALFAIL: {"status": "failed", "channel": "local-vlm", "pdf": mkpdf(LOCALFAIL)},
    NOPDF: {"status": "failed", "channel": "cloud"},
    OVER: {"status": "skipped-oversize", "channel": "skipped", "pdf": mkpdf(OVER)},
    DONE: {"status": "ok", "channel": "cloud", "pdf": mkpdf(DONE)},
}

B.HERE = TMP
B.CARRY_LEDGER = EV / "carry_over.jsonl"
TMP.joinpath("vlm_ocr_state.json").write_text(
    json.dumps(STATE, ensure_ascii=False), encoding="utf-8")

BATCH9 = {"n": 3, "paths": [mkpdf(NEW[0]), mkpdf(NEW[1]), mkpdf(DONE)]}
(EV / "work_batch9.json").write_text(json.dumps(BATCH9, ensure_ascii=False),
                                    encoding="utf-8")
CFG = {"list": "evolve/work_batch9.json", "log": "vlm_batch9.log", "batch": 9}

print("=== ① _batch_progress 分桶（完成/失败/待重做/巨型跳过/待人工）===")
done, failed, total, pend, skip, human = B._batch_progress(CFG)
check("总数取自清单", total, 3)
check("已完成 = ok（本批 2 部 ok、1 部还没跑）", done, 2)
check("待重做 = 本批内的 pending-local", pend, 0)
check("待人工 = 0（尚无）", human, 0)
check("巨型跳过 = 0（不在本批）", skip, 0)
check("未跑完：done+… < total（驱动会继续等）",
      done + failed + pend + skip + human < total, True)

print("\n=== ② _carry_over：全局残留并入本批清单（唯一消费者）===")
paths, rep = B._carry_over(list(BATCH9["paths"]))
check("全新 3 部保留", [Path(p).stem for p in paths[:3]],
      [Path(p).stem for p in BATCH9["paths"]])
check("带过来的残留 = 2 部（云超时的那两部）", sorted(rep["carried"]), sorted(CARRY))
check("清单变长 = 3 + 2", len(paths), 5)
check("本地 VLM 失败 → 待人工（能力边界）", LOCALFAIL in rep["retired"], True)
check("无源文件记录 → 待人工（无从重做）", NOPDF in rep["retired"], True)
check("已跳过/已完成不被动", any(k in rep["retired"] for k in (OVER, DONE)), False)
st = json.loads((TMP / "vlm_ocr_state.json").read_text(encoding="utf-8"))
check("state 落盘：本地失败已标 needs-human",
      st[LOCALFAIL]["status"], "needs-human")
check("state 落盘：待重做保持 pending-local（等重跑）",
      st[CARRY[0]]["status"], "pending-local")
check("台账已记 2 行", len((EV / "carry_over.jsonl").read_text(
    encoding="utf-8").strip().splitlines()), 2)

print("\n=== ②' 同一部已在清单里 → 不重复带（防重复烧云额度）===")
p0 = mkpdf(CARRY[0])
paths2, rep2 = B._carry_over([p0], dry_run=True)
check("清单里那部只出现一次", paths2.count(p0), 1)
check("已在清单里的不再 carried", CARRY[0] in rep2["carried"], False)
check("不在清单里的残留照样带（CARRY[1]）", CARRY[1] in rep2["carried"], True)

print(f"\n=== ③ 试满 MAX_CARRY={B.MAX_CARRY} 次 → 转 needs-human（显式终点）===")
for already in range(1, B.MAX_CARRY):
    B.CARRY_LEDGER.write_text(
        "".join(json.dumps({"key": CARRY[0]}, ensure_ascii=False) + "\n"
                for _ in range(already)), encoding="utf-8")
    _, r = B._carry_over([], dry_run=True)
    print(f"     已带 {already} 次：carried={len(r['carried'])} "
          f"retired={len(r['retired'])}")
    if CARRY[0] not in r["carried"]:
        FAIL.append(f"携带次数 {already} 仍应继续携带")
        print(f"  FAIL 已带 {already} 次仍应携带")
B.CARRY_LEDGER.write_text(
    "".join(json.dumps({"key": CARRY[0]}, ensure_ascii=False) + "\n"
            for _ in range(B.MAX_CARRY)), encoding="utf-8")
_, rep3 = B._carry_over([], dry_run=True)
check("试满上限 → 转待人工", CARRY[0] in rep3["retired"], True)
check("试满上限 → 不再携带", CARRY[0] in rep3["carried"], False)

print("\n=== ④ 顺序护栏：重分类必须在收批判据之前（原缺陷是反的）===")
src = (HERE / "batch_advance.py").read_text(encoding="utf-8")
wait = src[src.index("def _wait_batch"):src.index("def _carry_attempts")]
i_req = wait.index("moved = _requeue_cloud_failures")
i_log = wait.index("收批：")
check("_requeue_cloud_failures 在收批日志之前", i_req < i_log, True)
check("收批判据把 pending_local 也算到过终点",
      bool(re.search(r"skipped \+ pending_local >= total", wait)), True)
check("收批日志带残留数字（不写「已完成 N/N」）", "残留" in wait, True)
check("收批日志不再出现「已完成：」旧口径", "已完成：" in wait, False)

print("\n=== ⑤ 下一批构建里必须调用 _carry_over（否则残留照样没人消费）===")
run = src[src.index("def _run("):]
check("_run 里调用 _carry_over", "paths, carry = _carry_over(" in run, True)
check("清单写入 carried_over 字段", '"carried_over": len(carry["carried"])' in run, True)
check("新批日志报「全新 + 残留」", "部上批残留重跑" in run, True)

print("\n=== ⑥ 基线口径：命中数必须带分母缺口（防「评估 496 部 · 命中 0」被读成 500 部零缺陷）===")
check("scout_and_judge 透出 skipped", '"skipped": sc.get("skipped_pipeline", 0)' in src, True)
check("基线路打印未进分母部数", "未进分母" in src, True)

print("\n=== ⑦ needs-human 复归：只有真终态才永不携带 ===")
print("    （缺陷：提 MAX_CARRY 3→8 保护不了已被钉死的 37 部；且外部脚本")
print("      改 state 会被活着的 worker「整体读改写」整份覆盖 → 修复必须在")
print("      _carry_over 这个持有 state 的所有者层做）")
R_OK = "GB／T 7001-2016 复归应成功"
R_LOC = "GB／T 7002-2016 本地VLM能力边界"
R_NOP = "GB／T 7003-2016 无源文件已不在盘上"
R_CAP = "GB／T 7004-2016 复归后撞满硬上限"
GONE = str(PDFS / "gone.pdf")          # 故意不存在
st7 = {
    R_OK: {"status": "needs-human", "channel": "cloud", "pdf": mkpdf(R_OK),
           "msg": "（转待人工）已携带重跑 3 次仍未成功：云侧超时"},
    R_LOC: {"status": "needs-human", "channel": "local-vlm", "pdf": mkpdf(R_LOC)},
    R_NOP: {"status": "needs-human", "channel": "cloud", "pdf": GONE},
    R_CAP: {"status": "needs-human", "channel": "cloud", "pdf": mkpdf(R_CAP)},
}
(TMP / "vlm_ocr_state.json").write_text(json.dumps(st7, ensure_ascii=False),
                                       encoding="utf-8")
_led = [{"key": k} for k in (R_OK, R_LOC, R_NOP) for _ in range(3)]
_led += [{"key": R_CAP}] * B.READMIT_HARD_CAP
B.CARRY_LEDGER.write_text(
    "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in _led),
    encoding="utf-8")

_, rep7 = B._carry_over([])
check("可重试的 needs-human 被复归", R_OK in rep7["readmitted"], True)
check("复归的也进入本批携带清单", R_OK in rep7["carried"], True)
check("本地 VLM 能力边界 → 不复归（真终态）",
      R_LOC in rep7["readmitted"], False)
check("源 PDF 已不在盘上 → 不复归（真终态）",
      R_NOP in rep7["readmitted"], False)
check("撞满复归硬上限 → 不再复归", R_CAP in rep7["readmitted"], False)
check("真终态既不复归也不被携带",
      any(k in rep7["carried"] for k in (R_LOC, R_NOP, R_CAP)), False)
st7b = json.loads((TMP / "vlm_ocr_state.json").read_text(encoding="utf-8"))
check("复归后 state 变 pending-local（真的会重跑）",
      st7b[R_OK]["status"], "pending-local")
check("复归打上 readmitted 标记（供更宽上限用）",
      st7b[R_OK].get("readmitted"), True)
check("真终态 status 保持 needs-human",
      st7b[R_LOC]["status"], "needs-human")

print("\n=== ⑦' 复归后改用更宽上限（否则与 MAX_CARRY 来回抖）===")
B.CARRY_LEDGER.write_text(
    "".join(json.dumps({"key": R_OK}, ensure_ascii=False) + "\n"
            for _ in range(B.MAX_CARRY)), encoding="utf-8")
_, rep8 = B._carry_over([], dry_run=True)
check(f"复归后 attempts={B.MAX_CARRY} 仍携带（不被 MAX_CARRY 拦下）",
      R_OK in rep8["carried"], True)
check(f"复归后 attempts={B.MAX_CARRY} 不被转待人工",
      R_OK in rep8["retired"], False)
B.CARRY_LEDGER.write_text(
    "".join(json.dumps({"key": R_OK}, ensure_ascii=False) + "\n"
            for _ in range(B.READMIT_HARD_CAP)), encoding="utf-8")
_, rep9 = B._carry_over([])          # 非 dry-run：本步要验落盘字段
check(f"复归后撞满硬上限 {B.READMIT_HARD_CAP} → 转待人工（有终点）",
      R_OK in rep9["retired"], True)
st9 = json.loads((TMP / "vlm_ocr_state.json").read_text(encoding="utf-8"))
check("转待人工留结构化 human_reason（不靠解析 msg）",
      st9[R_OK].get("human_reason"), f"已携带重跑 {B.READMIT_HARD_CAP} 次仍未成功")

print("\n=== ⑦'' 复归有配额（防一口气灌进上千部挤掉全新文档）===")
many = {}
for i in range(B.READMIT_QUOTA + 5):
    t = f"GB／T 8{i:03d}-2016 配额压测{i}"
    many[t] = {"status": "needs-human", "channel": "cloud", "pdf": mkpdf(t)}
(TMP / "vlm_ocr_state.json").write_text(json.dumps(many, ensure_ascii=False),
                                       encoding="utf-8")
B.CARRY_LEDGER.write_text("", encoding="utf-8")
_, repQ = B._carry_over([], dry_run=True)
check(f"每批复归恰好不超过配额 {B.READMIT_QUOTA}",
      len(repQ["readmitted"]), B.READMIT_QUOTA)
check("剩余的下批还能继续复归（不是永久丢弃）",
      len(many) - len(repQ["readmitted"]) > 0, True)

shutil.rmtree(TMP, ignore_errors=True)

print()
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
