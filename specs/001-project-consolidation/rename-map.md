# 新旧名称对应表（T007）

**Feature**: 001-project-consolidation | **Date**: 2026-10-05
**依据**: [contracts/naming-convention.md](./contracts/naming-convention.md) v2 §二

**范围**：**只改文档文件名里的下划线**。按 v2 §一，**代码文件一律不改**——
那 327 个 `snake_case.py` 是 PEP8 的正确写法，改了会断 import 且违反语言约定。

**实测全仓 track 文件里，真违规只有 6 个。**

---

## 一、要改的（6 个）

| # | 现名 | 新名 | 理由 | 受影响引用 |
|---:|---|---|---|---|
| 1 | `docs/CHANNEL_PROBE_REPORT.md` | `../../docs/archive/research-process/CHANNEL-PROBE-REPORT.md` | 下划线下划线 → 连字符 | **6** |
| 2 | `docs/LAW_SOURCE_PLAN.md` | `docs/LAW-SOURCE-PLAN.md` | 同上 | **20**（含 11 处代码注释） |
| 3 | `docs/REALTIME_VALIDITY_VERIFY_RESEARCH.md` | `../../docs/archive/research-process/REALTIME-VALIDITY-VERIFY-RESEARCH.md` | 同上 | **6** |
| 4 | `docs/STD_STATUS_CHANNELS.md` | `../../docs/archive/research-process/STD-STATUS-CHANNELS.md` | 同上 | **7** |
| 5 | `docs/WSL2_VLM_BACKEND_DECISION.md` | `../../docs/archive/research-process/WSL2-VLM-BACKEND-DECISION.md` | 同上 | **3** |
| 6 | `tests/fixtures/rental_contract.md` | `tests/fixtures/rental-contract.md` | 同上 | **1**（仅本规范文档提到，未在代码里引用） |

## 二、明确不改的（附理由，不许静默跳过）

| 对象 | 为什么不改 |
|---|---|
| `src/**/*.py`（含 327 个带下划线的） | **PEP8 snake_case 是正确写法**；改名会断 import。v2 §一 |
| `plugin/src/materials_routes.js` 等 JS | 跟随同目录既有写法；改名会断 import。v2 §一 |
| `docs/**` 里所有**全大写**的文件名（约 100 个） | 本仓既有的"标准文档全大写"约定；**`AGENTS.md` 按这些名字引用它们，而本特征不许改 `AGENTS.md`**。v2 §三 |
| 所有目录名 | 实测 **0 违规**，已是全小写 kebab |
| `scripts/_stdparse.py` | 前导下划线是 Python 的"私有模块"约定，不是命名不一致 |
| `wenjianmulu/` 及其中文目录 | **未跟踪**（不在版本控制里）；按 v2 §八 属 `var/` 同类的本机产物，不在本项目文件范围 |

## 三、撞车检查（T008）

按 v2 §九 第 6 条，MUST 检查是否有两个不同文件算出同一新名。

**结果：无撞车。** 6 个新名两两不同，且都不与现有任何文件名冲突
（现有文件名里没有 `CHANNEL-PROBE-REPORT.md` / `LAW-SOURCE-PLAN.md` /
`REALTIME-VALIDITY-VERIFY-RESEARCH.md` / `STD-STATUS-CHANNELS.md` /
`WSL2-VLM-BACKEND-DECISION.md` / `rental-contract.md`）。

**例外清单检查**：6 个文件都不需要全大写例外——它们的原名已是全大写，只是分隔符要改。

## 四、受影响引用（改名时 MUST 同步改正）

三类，按 v2 §九 第 3 条：

1. **文档间链接**——含 `README.md`（将在 T031 重写为 wiki 入口）、`docs/DEVELOPMENT-HISTORY.md`、
   `docs/ENCYCLOPEDIA.md`、`docs/INDEX.md`（脚本生成，重跑即可）等
2. **代码里引用的文档路径**——实测 11 处，在 `scripts/fetch_law.py`、`scripts/make_handoff_zip.py`、
   `src/core/api/routes_law.py`、`src/core/knowledge/law_source/*.py`、`src/core/storage/clause_repo.py`、
   `src/core/update/channels/routing.py` 的注释与 docstring 里
3. **门禁断言**——待跑门禁时暴露；若有，同步改

**验证**：改名后 MUST 跑 `python scripts/docs/check-links.py`，**残留为 0**；
再用 `git grep` 搜 6 个旧名，残留为 0。
