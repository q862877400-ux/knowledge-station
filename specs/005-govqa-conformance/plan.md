# Implementation Plan: gov-qa 合规收口与目标达成

**Branch**: `005-govqa-conformance` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-govqa-conformance/spec.md`

---

## Summary

把 `tools/gov-qa` 从"能跑的一次性机器"收口成"本仓规范的合格成员 + 目标可验证地达成"。
技术路径：**先建立门禁与判据（否则后面所有修复都无法防回退）→ 再修已实证的静默缺陷
→ 再补 M1 自报总量 → 再推进 M2/M4 → 最后独立复核**。

诊断依据（Lead 独立复现 + 一份独立复核报告）：`../../docs/archive/research-process/GOVQA-DIAGNOSIS-2026-10-10.md`
与 `.tmp-review-spec004.md`。

---

## Technical Context

**Language/Version**: Python 3.12（`.venv/Scripts/python.exe`）+ PowerShell 7（门禁脚本）

**Primary Dependencies**: `httpx`（采集）、`pytest`（测试）、`scikit-learn`（标签 SVM）。
无新增第三方依赖。

**Storage**: JSONL 文件（`tools/gov-qa/data/*.jsonl`，558 个 / 600 MB）+ JSON 状态
（`state/watermarks.json`）+ JSON 登记表（`recon/targets.json`）。

**Testing**: `pytest tools/gov-qa/tests`（58 条）。门禁为
`pwsh -File scripts/run-gates.ps1 -Quick|-Full`。

**Target Platform**: Windows 本机（GBK 控制台是硬约束——机器可读输出必须纯 ASCII）。

**Project Type**: 单项目 CLI 工具 + 侦察脚本集（`tools/gov-qa/`）。

**Constraints**:
- **GBK 控制台**：`print` 中文/emoji 会 `UnicodeEncodeError`（实测 `audit-coverage.py --answers` rc=1）。
  机器可读输出**一律走 `common.ascii_kv`**。
- **`core.autocrlf=true` 且无 `.gitattributes`** ⇒ 编辑源码会改行尾。
  **还原必须用 `git checkout`，不能用 `write_text`**（我在诊断阶段实测踩过）。
- **并发写**：另一 Agent 的 `igi-chunked.py` 仍在跑（实测 07:54 仍在写 `gx-igi-*.jsonl`），
  且**仍在往 master 提交**（实测 08:03 提交 `ee56cd0`）。
- **`.git` 已 2,248 MB**（含 1,953 MB 孤儿对象）。
- **门禁一次只跑一个**（锁文件；退出码 3 = 有人在跑，不是失败）。

**Scale/Scope**: 345 个适配器、558 个数据文件、39.5 万条、888.7 MB。

---

## Constitution Check

*GATE: 必须通过才能进入 Phase 1。*

| 原则 | 本计划如何满足 |
|---|---|
| **I 说人话** | 向业主汇报一律用「能做什么 / 会看到什么 / 代价」表述；本文件与 tasks.md 属设计文档，不受此限 |
| **II 从事实出发，不迎合** | 所有"已修/已验"必须附当次真跑的命令与输出；未做的写"明确未做" |
| **III 证据优于断言** | 每项新判据做变异验证（改坏 ⇒ 必红）；SC-003 要求 4/4 报红 |
| **IV 单一出处** | 标签覆盖率合并为一个函数（现 `health.py` 99.2 vs `label-coverage.py` 100.0 两个出处）；省级名单 31/34 两份需同步判据 |
| **V 自我更正 grep 全仓** | 修交接文档 §11 与 README 两处过时说法时，全仓 grep 同族句子 |
| **VI 门禁即代码** | 本特性的核心就是把 gov-qa 接进 `run-gates.ps1`，消灭"靠人记得跑" |
| **VII 小提交 + 可回退** | 每个 Phase = 小提交；提交消息写「改了什么/为什么/边界」 |

**结论：无违反，无需 Complexity Tracking。**

---

## Project Structure

### Documentation (this feature)

```
specs/005-govqa-conformance/
├── spec.md              # 本特性规格（已写）
├── plan.md              # 本文件
├── tasks.md             # 施工计划（T001…）
├── research.md          # Phase 0 调查结论（诊断 + 复核的实测事实）
├── data-model.md        # 判据与登记表的数据结构
├── quickstart.md        # 怎么跑、怎么验
├── contracts/           # 门禁契约（判据名 / 阈值 / 退出码）
└── checklists/
    └── requirements.md  # 规格质量自检
```

### Source Code (repository root)

```
tools/gov-qa/
├── common.py            # ← 加：统一覆盖率函数、修 human() 兜底
├── health.py            # ← 修：四项判据接真值 + 被测试钉住
├── coverage.py          # ← 修：334/333 口径统一
├── coverage-report.py   # ← 修：--quiet 与 --missing-cities 退出码一致
├── poll.py              # ← 修：水位真读、--quiet 走 ascii_kv、删死代码
├── state.py             # ← 修：锁陈旧检测
├── recon/
│   ├── audit-coverage.py    # ← 修：GBK 崩、跨文件重复 id、ADAPTERS_ERR
│   ├── targets.json         # ← 补：308 个适配器自报总量
│   └── gate-quality.py      # ← 新：四项数据质量判据（唯一数字源）
├── tests/               # ← 补：门禁接入、契约、变异
└── data/                # ← 修：xz-lasa 空答复、内容重复、时间倒置

scripts/
├── run-gates.ps1        # ← 加：gov-qa 测试步骤 + 质量判据步骤
└── gates-baseline.json  # ← 重记：pytest 基线

D:/AI/output/            # ← 纳入版本控制（移到 tools/gov-qa/gate/）
```

---

## Phase 结构（详见 tasks.md）

| Phase | 内容 | 可完成? |
|---|---|---|
| **Phase 0** | 安全前置：停并发写、清死锁、`.gitignore` | ✅ |
| **Phase 1** | 纳入本仓门禁（含堵假绿 + 四项新判据） | ✅ |
| **Phase 2** | 修静默数据缺陷（空答复 / 重复 / 时间倒置 / 截断 / 标签口径） | ✅ |
| **Phase 3** | M1 补齐：308 个适配器自报总量 | ✅ |
| **Phase 4** | M2 存量推进（长周期） | ⚠ 推进 |
| **Phase 5** | M3 标签人工抽检 | ⚠ 需业主 |
| **Phase 6** | M4 覆盖面推进（长周期） | ⚠ 推进 |
| **Phase 7** | 独立复核 + 开发史登记 + 文档更正 | ✅ |

---

## 关键风险与对策

| 风险 | 对策 |
|---|---|
| 改门禁时把本仓主门禁弄红，影响别的线 | gov-qa 步骤**追加**在现有步骤之后；先在 `-Full` 里加，绿了再考虑 `-Quick` |
| 门禁变慢导致没人愿意跑 | SC-004 硬约束：总耗时 ≤ 现状 +60 秒。gov-qa 测试现仅 0.5 秒 |
| 与并发 Agent 冲突 | Phase 0 先停 `igi-chunked.py`；`gx-igi-*.jsonl` 全程不碰；提交前 `git status` 逐文件过归属 |
| 判据写成恒真 | SC-003：每项新判据做变异，4/4 必红 |
| 数据修复不可逆 | 修数据前先 `git commit` 现状；用 `recon/dedup-data.py` 类工具而非手改 |
| 门禁锁冲突（退出码 3） | 识别 3 ≠ 失败，串行重试 |

---

## 验收（对应 spec 的 SC-001…SC-012）

收工时逐条跑、逐条贴输出。**任何一条拿不出当次真跑的输出，就写"未达成"**，
不写"基本完成"。
