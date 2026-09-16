# OCR 循环 · 配套子项目契约（CONTRACT）

> 立约日：2026-09-16 ｜ 状态：**已暂停，可续跑**
> 位置：`var/ocr-loop/`（**独立配套子项目**，不属于主项目 `src/` 代码）
> 关联：`REPORT-2026-09-16.md`（成果与故障率）· `HANDOFF.md`（全部教训与技术细节）

---

## 0. 为什么单独立契约

这条循环**改了主项目的知识库内容**（产出 OCR 产物），却**不是主项目的代码**。
把它塞进 `src/` 会污染产品边界；完全不管又会让"换机器即丢防御"重演
（历史上 `var/` 被整目录忽略，7 项修复曾只存在于本机）。

故：**它是配套子项目**——有自己的入口、自己的台账、自己的门禁，
与主项目之间**只通过下面这份契约交互**。

---

## 1. 边界（谁是谁）

| | 主项目（KnowledgeStation） | 本配套子项目 |
|---|---|---|
| 代码位置 | `src/`、`tests/` | `var/ocr-loop/` |
| 职责 | 解析/清洗/入库/检索；**拥有清洗链与判据的所有者层** | **获取 OCR 产物**（把 PDF 变成可入库产物） |
| 可否写库 | ✅ 入库是它的职责 | ❌ **绝不写库**（只读连接） |
| 版本控制 | 已跟踪 | **只跟踪资产**（探针/诊断脚本留在本机，见 `.gitignore`） |

**唯一的共享真相是磁盘上的产物目录**，不是内存状态、不是数据库。

---

## 2. 输入契约（本子项目消费什么）

| 输入 | 位置 / 口径 | 说明 |
|---|---|---|
| 语料 | `D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)` | 递归 `*.pdf`：**35,243 个文件 ＝ 31,710 个归一 stem（不同标准）** |
| 库（只读） | `src.core.config.get_settings().db_path`，以 `file:...?mode=ro` 打开 | 仅用于排除"库内已用"（`doc_meta.file_path`） |
| 产物根 | `vlm_ocr.parse_out()`（KnowledgeStation 的 `parse_out`） | 落位口径见 §3 |
| VLM 云凭据 | `keys_pool()` 提供的多账号 key | **云优先**；云不通才走本地 VLM |

---

## 3. 输出契约（本子项目产出什么、放哪）

**产物落位（必须与主项目解析口径逐字一致）**：

```
parse_out / _land_key(doc_id or std_no)
```

`_land_key` 是**单一所有者**（`vlm_ocr._land_key` ≡ `artifact_index._land_key`），
消毒规则：保留字母数字与 `-._`，其余替换为 `_`，截断 80 字符。

> ⚠ 改 `_land_key` 必须**两处同步**，否则新语料产物定位失效（历史教训）。

**台账（运行态，不进版本控制）**：

| 文件 | 作用 |
|---|---|
| `vlm_ocr_state.json` | 逐部状态（`ok`/`failed`/`pending-local`/`needs-human`/`skipped-oversize`）+ `pdf`/`pages`/`channel`/`msg`/`fatal` |
| `vlm_ocr_log.jsonl` | **append-only 权威账本**（`recover_state` 由它回补 state） |
| `evolve/carry_over.jsonl` | 携带台账（某部被带进下批几次） |
| `evolve/instrument_fixes.jsonl` | 修复/测量/结案台账（**决策留痕**） |
| `fixed_classes.json` | 类登记 + `gate_exempt`（**已跟踪**） |
| `evolve/work_batchN.json` | 每批清单（历史批 paths ＝ 候选排除依据） |

---

## 4. 不变量（契约核心，破坏任一条都会静默丢内容）

1. **绝不写库**：DB 连接恒为 `mode=ro`。
2. **VLM-only**：`KS_VLM_ONLY=1`；主项目 pipeline 不参与本循环。
3. **一个归一 stem 只保留一个代表**（`next_batch.candidates()`）。
   曾因"撞键整组丢弃"导致 **约 3,228 个标准永不被 OCR**。
4. **`state` 是整体读改写**（`commit_rec`：`state[k]=rec; save_json(...)`）。
   → **worker 活着时外部改 `vlm_ocr_state.json` 无效**（会被内存副本整份覆盖）；
   修复必须做在**持有 state 的进程里**，且改代码后**必须重启对应进程**。
5. **`needs-human` 只用于真终态**：本地 VLM 能力边界 / 源 PDF 丢失。
   云超时属**瞬态**，必须可复归（否则每次降级窗口都留永久缺口）。
6. **判据必须与其所有者层同源口径**：判据报缺陷而所有者层（`src/core/text_utils` 等）
   按设计不改的，就是**永久误报**（曾致闸门误停 1h50m）。
7. **单实例**：`vlm_ocr` 有单实例闸门；driver 与 watchdog 通过
   `batch_advance.owner` 心跳仲裁，**禁止双 worker**（会重复烧云额度）。

---

## 5. 通道（成果如何交给主项目入库）★

**推荐通道：产物目录 + 一份 manifest**。主项目**不需要理解本子项目内部状态**，
只需读 manifest 与产物目录：

```
evolve/ingest_manifest.json     ← 由本子项目导出（可重生成、幂等）
{
  "built_at": "...",
  "source": "var/ocr-loop",
  "denominator": {"pdf_files": 35243, "distinct_stems": 31710},
  "items": [
    {"std_no": "GB 150-2011 压力容器",
     "product_dir": "C:\\...\\parse_out\\GB_150-2011_压力容器",
     "status": "ok",
     "pages": 341,
     "nonempty": true}
  ],
  "excluded": {"holdout": 28, "oversize": 35, "note": "..."}
}
```

**"没问题"的判据（入库前过滤，建议）**：
`status == "ok"` **且** 产物目录存在且非空 **且** 该部在最近一轮基线里**未命中达线类**。
必须显式排除/标注：巨型跳过 35 部（用户决定不做）、留出集 28 部（locked、本就不参与）、
以及 `unknown` 后端那一小部分（口径见 HANDOFF §10.27）。

**去重**：入库前按 `doc_meta.file_path` 排除库内已用（当前 260 条）。

**通道实现状态**：**待实现** `export_manifest.py`（约 50 行：读 state + 校验目录非空 → 写 manifest）。
在它实现前，主项目可临时直接用 `vlm_ocr_state.json` 里 `status=="ok"` 的条目 + §3 的落位口径。

---

## 6. 如何续跑（暂停后恢复）

```powershell
# 1) 拉起 driver（它会自动等当前批 → 取基线 → 无达线类则取下一批）
& .\.venv\Scripts\python.exe -X utf8 var/ocr-loop/batch_advance.py --size 500 --max-batches 20

# 2) watchdog（可选，每 5 分钟巡检；**它不会重启 driver**，driver 死了只接管拉 worker）
pwsh -NoProfile -File var\ocr-loop\watchdog_loop.ps1
```

**改代码后必须重启对应进程**（否则内存副本仍是旧逻辑）：

```powershell
# driver 是「trampoline(.venv python) → 真实解释器(uv python)」两层，按 owner 心跳里的 pid 找真实那个
taskkill /T /F /PID <trampoline_pid>
```

**停循环**：杀掉 `batch_advance.py` 与 `vlm_ocr.py` 两组进程即可（state 与清单都在，可续跑）。

**当前续跑点**：批次 #18（`work_batch18.json`，暂停时 31/517）；候选池 **23,316**。

---

## 7. 门禁（本子项目的自测）

```powershell
# 8 个 instrument 套件（当前靠手工跑；见下方"待接门禁"）
foreach ($f in 'test_candidate_rep','test_state_carryover','test_gate_exempt',
               'test_driver_liveness','test_single_instance','test_cloud_stage_timeout',
               'test_table_probe','test_dot_leader_judge') {
  & .\.venv\Scripts\python.exe "var\ocr-loop\$f.py" }
```

**待接门禁**：主项目 `pyproject.toml` 是 `testpaths = ["tests"]`，**不会收集本目录**，
故这些不变量目前**无自动化护栏**。建议加薄包装 `tests/test_ocr_loop_invariants.py`
（subprocess 跑套件、断言退出码 0），**只接零外部依赖的 3 个**：
`test_candidate_rep`（用假语料段）、`test_gate_exempt`、`test_dot_leader_judge`
（其余会遍历 35k 文件或碰真实锁文件，进主门禁会变慢/不稳）。

---

## 8. 已知限制（不隐藏）

- 云降级窗口两类：**快速失败型**（`failed` 快涨）与**挂起型**（计数几乎不动，
  易误读成死锁；判据＝进程存活且 `failed` 不涨）。两者都无需人工干预。
- `CLOUD_TIMEOUT_S=240` 是否偏长**未定论**，需**健康期延迟分布**才能调。
- 闸门达线阈值**按类名**统计，而正文/表格缺陷记成不同类名 → 跨上下文分散的形态
  **不会达线**（可能的漏检面，已记台账，未改）。
- `toc-ingested-as-clauses` 为**有意保留的固有歧义**类（二歧检索表步号/评价分值与
  目录行同形）；达线时按 `HANDOFF §10.29` 四步手册处置。
- 有意排除（标准级）**63 个**：留出集 28 + 巨型 35。
