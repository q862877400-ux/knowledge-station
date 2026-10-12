# Implementation Plan: 接上更新通道系统的三个断点

**Branch**: `011-channel-system-wiring` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-channel-system-wiring/spec.md`

## Summary

三件事，**全部是"把已建成但没接线的能力接上"**，不新建能力：

1. **自动巡检**：照 `law_refresh` 既有先例，在 `server.run()` 启动调度线程；
   并补上"建批后执行"（现状 `tick()` 只建批不跑）。
2. **补 CCS**：`law_text.ingest_law_text()` 补查 CCS 写 `domain_tags`
   （判据唯一所有者 = `ccs_fetcher`，与 `pipeline.py` 同一处）。
3. **下载前弹框**：巡检判定 `new_version` 时走审批门，同意才调
   `govcn_announce.archive_pdf()`。

## Technical Context

**Language/Version**: Python 3.12（引擎侧）+ JavaScript ESM（宿主插件侧，仅第 ③ 条要动）

**Primary Dependencies**: 无新增。复用 `threading` / `ccs_fetcher` / `ccs_store` /
`govcn_announce.archive_pdf` / 既有审批门 `tools/pre-execute`

**Storage**: SQLite（`bulk_import_batch` / `update_change_event` / `doc_meta` / `doc_ccs_state`）

**Testing**: pytest（根 `tests/`）

**Target Platform**: Windows（引擎 + DSH 宿主）

**Constraints**:
- **不新增依赖**（本仓纪律：能复用就复用）
- **不碰 `NOT-DOING` 红线**：第 20 条禁止自动下载 ⇒ 第 ③ 条必须弹框
- 一次只跑一个门禁（锁文件）

**Scale/Scope**: 调度器 1 个线程 / CCS 回填 380 篇 / 下载走审批门

## Constitution Check

| 原则 | 本特性怎么满足 |
|---|---|
| **I 说人话** | 汇报说"引擎会自己定期去查标准有没有新版"、"从网上入的标准现在也能在目录里看到"、"要下载前会问你要不要"；不说线程/字段/适配器 |
| **II 从事实出发** | ⚠ **本特性推翻了我自己前几轮的两个说法**：① 我说"要放宽 `ks_collect` 白名单才能收 PDF" —— 错，`archive_pdf` 早有 `%PDF` 校验；② 我说"抓的进材料库不是标准库" —— 错，`web_ingest` 走 `ingest_law_text` 直接进 `doc_meta`。**根因是我没先找现成的** |
| **III 证据优于断言** | 每个数字挂复算命令；SC-009 要求变异自验 |
| **IV 一个事实一个归属层** | 核实报告落 `docs/research/CHANNEL-SYSTEM-AUDIT-2026-10-12.md`；实现写本 spec |
| **V 假绿判 failed** | 变异自验（把 `start()` 换成 `pass`、把 CCS 调用删掉、把弹框改成直接下载 —— 各自必须变红） |
| **VI 门禁为准** | `-Full` N/N · exit=0 |
| **VII 不撞车** | ⚠ **实测另一条线（spec 009 UI）今天有 6 个提交** ⇒ 写前先确认它已收工；只动 `src/core/update/` + `src/core/ingestion/law_text.py` + `server.py` |

**结论**：无违规。

## Project Structure

### Documentation (this feature)

```text
specs/011-channel-system-wiring/
├── spec.md      # 已完成
├── plan.md      # 本文件
└── tasks.md     # 下一步
```

### Source Code

```text
src/core/update/
└── scheduler_runner.py          # 新增：调度线程（照 law_refresh 先例）
                                 #   含"建批后执行"——补 tick() 只建不跑的缺口

src/core/api/server.py           # 改：run() 里启动调度线程 + 关停

src/core/ingestion/law_text.py   # 改：补 CCS（复用 ccs_fetcher，判据唯一所有者）

src/core/knowledge/ccs_backfill.py  # 复用（已有回填入口，给 380 篇补）

src/core/update/download_gate.py    # 新增：下载前的审批门（服务端）
                                    #   复用 govcn_announce.archive_pdf

plugin/src/inspection.js            # 改：把"可下载"暴露给宿主审批门（第 ③ 条宿主侧）

tests/
└── test_channel_system_wiring.py   # 新增：三组判据 + 变异自验
```

**Structure Decision**：调度线程**新开一个文件**（`scheduler_runner.py`）而不是改
`scheduler.py` —— 理由与 `law_refresh.py` 头注写的一样：`scheduler.py` 的**编排逻辑是对的**，
只是没被启动；把"线程生命周期"与"编排语义"分开，改动面最小、回退最干净。

## 判据设计（**先定判据，再写实现**）

### 第 ① 条：调度接线

| # | 断言 | 牙在哪 |
|---|---|---|
| **A1** | `server.run()` 的 AST 里有**真的 Call** `start_update_scheduler()` | 只 import 不调用 ⇒ 红（照 `test_law_catalog_refresh` 的 AST 判据先例） |
| **A2** | `start()` 幂等：连调两次只有一个线程 | 不判重 ⇒ 起两个线程 ⇒ 红 |
| **A3** | 到期建批**且执行**（批状态离开 `pending`） | 只建不跑 ⇒ 红（这正是现状缺口） |
| **A4** | 未到期不建批 | 不判时间 ⇒ 每拍都建 ⇒ 红 |
| **A5** | `schedule_days=0` ⇒ 关闭 | 忽略 0 ⇒ 关了还跑 ⇒ 红 |

### 第 ② 条：CCS

| # | 断言 | 牙在哪 |
|---|---|---|
| **B1** | `ingest_law_text` 入库后 `domain_tags` 含 `CCS:` | 不查 CCS ⇒ 红 |
| **B2** | CCS 查不到 ⇒ **入库仍成功**（降级不阻塞） | 查不到就抛 ⇒ 红 |
| **B3** | `classify_document()` 不落「其他标准」 | 补了 CCS 但仍落兜底 ⇒ 红 |
| **B4** | 判据**同一所有者**：不出现第二份 CCS 解析 | 另写一份正则 ⇒ 红（结构判据） |

### 第 ③ 条：下载前弹框

| # | 断言 | 牙在哪 |
|---|---|---|
| **C1** | 判定 `new_version` 后 **`archived_pdf_path` 仍为空**（没自动下载） | 自动下载 ⇒ 红 |
| **C2** | 审批门返回 `kind:'ask'`，问句含"来源 + 形态" | 不问就下 ⇒ 红 |
| **C3** | 同意 ⇒ 调 `archive_pdf`；拒绝 ⇒ 不调 | 拒绝也下 ⇒ 红 |
| **C4** | 非 PDF（返回 HTML）⇒ **拒收** | 不校验魔数 ⇒ 红 |

### 变异自验（SC-009）

| 变异 | 必须变红 |
|---|---|
| 把 `start_update_scheduler()` 调用换成 `pass` | A1 |
| 去掉 `tick()` 后的执行步骤 | A3 |
| 删掉 `law_text` 里的 CCS 调用 | B1 |
| 让 CCS 查不到时抛异常 | B2 |
| 把审批门改成直接下载 | C1 + C2 |
| 去掉 `%PDF` 校验 | C4 |

## 实施顺序

**按业主要求的 ①②③ 顺序**（先接自动巡检，再补 CCS，最后接下载）。

1. **T001** `scheduler_runner.py`：线程 + 建批后执行
2. **T002** `server.py` 接启动/关停 + AST 判据
3. **T003** 判据 A1–A5 + 变异
4. **T004** `law_text.py` 补 CCS（复用 `ccs_fetcher`）
5. **T005** 回填入口（380 篇 `web://`）
6. **T006** 判据 B1–B4 + 变异
7. **T007** 下载审批门（服务端 + 宿主侧）
8. **T008** 判据 C1–C4 + 变异
9. **T009** 门禁 `-Full`
10. **T010** 小提交 + 快照

## Complexity Tracking

无违规项。

## 风险与回退

| 风险 | 缓解 |
|---|---|
| 调度线程自动建批会**自动进日预算池** | `update.schedule_days` 默认 7 天；可设 0 关闭；**沿用既有配置语义，不新增开关** |
| CCS 查询拖慢入库 | `ccs_fetcher` 有超时 + 三级链 + 失败降级；`pipeline.py` 已是这个模式 |
| 自动巡检撞上另一条线的写入 | 写前确认对方收工；只动 `src/core/update/` + `law_text.py` + `server.py` |
| 弹框在无人值守时挂住 | 视为"不下载"（不猜意图），不阻塞巡检主流程 |
| 改了 `server.run()` 影响启动 | AST 判据 + 启动冒烟；线程失败**不阻塞引擎启动**（照 `law_refresh` 的 try/except） |
