# 回收区 `var/_trash-2026-10-11/`

> **这不是垃圾堆，是"只移不删"纪律的产物。** 里面每一件都**还在盘上、随时可搬回**。
> **删除前 MUST 先确认没有正在跑的复核/采集在用它们**（本仓为此丢过原始证据，见 §四）。

**建它的人**：2026-10-11 全仓整理（业主令「把没用的文件归在一起，我给它放起来」）。
**它的上游纪律**：`var/README.md` §三、`docs/naming-convention.md` §八。

---

## 一、为什么移到这里（判据，逐类可核）

| 类 | 判据 | 数量 |
|---|---|---|
| `root-tmp/` | 仓库根的一次性探针 / commit 消息草稿（并行自动化产出）。`.gitignore:44` 的 `.tmp-*` 已盖住 ⇒ **本来就不入库**；实测**已停写**（无进程、无提交） | 233 |
| `eval-expdb/` | 三个实验库**副本**。**目录自带的 `.gitignore` 就写着"可重建"**（`01/02/03` 脚本可重跑）⇒ 它们**不是唯一证据** | 3 库 / 9 文件 |
| `var-tmp/` | `var/tmp/` 里的一次性产物（Chrome 调试 profile、pytest 回溯树、真库副本、各轮备份…） | 15 项 |
| `recon-ln8890/` | 顶层 `recon/` 的 32 个 JS —— 采集线 JS 逆向产物（未跟踪、未被忽略） | 32 |

**合计**：**15.13 GB / 9,548 文件**（移动后实测）。

---

## 二、移的每一项是什么（可核对）

### `root-tmp/`（233 个，0.67 MB）
`.tmp-*` 一族。**8 个被文档提到**，但**都不是可点链接**：
- 5 个是 `VERIFY-REPORT-govqa-data-forensics.md` 里的**原件路径叙述**（"取证脚本为 `.tmp-forensics.py`…"）
  —— 该报告已**字节级归档**进 `docs/verify-briefs/`，原件在不在**不影响报告的完整性**；
- 2 个是 `specs/001/.../top-level-inventory.md` 的**分类举例**；
- 1 个是 `DEVELOPMENT-HISTORY.md` 的叙述。

### `eval-expdb/`（11.8 GB）
| 文件 | 大小 | 为什么可移 |
|---|---|---|
| `exp-4-embedding-shadow/exp.db` | 5.45 GB | 目录 `.gitignore` 写「可重建」；`01-embed-qwen.py` 等可重跑 |
| `exp-1-contextual/exp.db` | 4.06 GB | 同上；`.gitignore` 原文：「**真库副本 2.2 GB + 新向量表 1.1 GB；它们是可重建的运行产物（01/02/03 三个脚本可重跑）**」 |
| `exp-3-query-side/exp.db` | 2.28 GB | 同上；`.gitignore` 写「与 exp-1-contextual 同一纪律」 |

⚠ **它们的结论没有丢**：每个目录里的 `ab-result.json` / `verdict.json` / `README.md` 等**都在版本控制里**，
移走的只是**能重算出来的中间库**。

### `var-tmp/`（15 项，3.7 GB）
`path-audit`（Chrome 调试 profile + 探针，413 MB / 5,886 文件）、`r18`（第 18 轮 pytest 回溯，157 MB）、
`ingest-trial`（真库副本试跑，2.96 GB）、`exp-17`（98.9 MB）、`ui-shots`（41.5 MB）、
`r17` / `r19` / `round8-bak` / `round10-bak` / `ratchet-probe` / `verify-pssa-command-layer` /
`pre-check` / `tutorial` / `lawrefbook` / `ingest-full`。

⚠ **`ui-shots/` 有一处要注意**：`docs/KB-FOLDER-PLAN.md` 与 `docs/HANDOVER-2026-09-23.md` 提到过它的截图路径。
那两处是**历史记录里的路径**（不是活引用），且 `HANDOVER-2026-09-23` 本身已归档。
**若要重新看图**，搬回 `var/tmp/ui-shots/` 即可。

### `recon-ln8890/`（32 个 JS，4.63 MB）
采集线逆向出的 `ln8890/` 前端 JS。**未跟踪、未被 `.gitignore` 盖住** ⇒ 它一直在 `git status` 里当噪声。
它是 `tools/gov-qa` 那条线的取证产物；那条线的活件在 `tools/gov-qa/recon/`，**这里这份是顶层的历史副本**。

---

## 三、怎么搬回去

**同盘移动，瞬时、可逆**。例：

```powershell
# 搬回一个 var/tmp 产物
Move-Item "var\_trash-2026-10-11\var-tmp\ui-shots" "var\tmp\ui-shots"

# 搬回根目录探针
Move-Item "var\_trash-2026-10-11\root-tmp\*" "."
```

---

## 四、真要删之前（MUST）

1. **确认没有正在跑的复核/采集在用**（本仓实测教训：批准清掉 30 棵陈旧副本时，
   把某轮复核**正在用的"改前对照树"**一起删了 ⇒ 那份原始 JSON 证据**永久丢失**）。
2. **确认 `eval/` 那三个库真的不需要复现**（要复现就跑 `01`/`02`/`03` 重算，不便宜）。
3. 确认后 `Remove-Item -Recurse -Force`。
4. **拿不准的搬回原位**，不要删。

---

## 五、同批**没有**动的东西（以及为什么）

| 没动 | 为什么 |
|---|---|
| `wenjianmulu/` | 🔴 **活数据**：生产库 `doc_meta.file_path` 指向这里的 PDF，删了知识库**证据链就断**（见 `docs/ENCYCLOPEDIA.md`） |
| `var/fixtures/` | 🔴 测试依赖的活数据（290 MB） |
| `eval/golden/` | 🔴 门禁三件最小集 |
| `var/ocr-loop/` | 🔴 部分受版本控制（53 个文件），移了就没安全网 |
| `pelican-bike.html` | ⚠ **别人的未提交件**，`docs/README.md` 明写 **MUST NOT 动** |
| `plugin/src/*.bak-20260927-*` | ⚠ 别人的回滚点（两两重复） |
| `tools/gov-qa/**` | 🔴 并行自动化的活件 |
| `var/_trash-2026-10-05/` | 已有回收区（18.9 GB）；**动它要先走 §四 第 1 步** |
| `docs/trash-2026-10-05/` | 只剩一个 `.gitkeep` 的空目录（受控）；`docs/README.md` 有 2 处历史叙述 |
