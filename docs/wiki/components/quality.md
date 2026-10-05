# quality（质量判定）

**位置**：`src/core/quality/`
**一句话**：判定「这份解析结果坏没坏、坏到什么程度」，并给出三态裁决。

## 职责

**质量规则的唯一所有者**：条款体检 6 标签（`clause_health.py`）、识别与版面度量（`recognition.py`）、分级阈值与裁决（`grading.py` 的 `THRESHOLDS`）、本地识别与云识别的分歧检测（`disagreement.py`）。

接手的是**尚未落库或刚解析出来的结果**（入库预览 Dry-Run 与已入库体检共用同一实现），交付的是可解释的标签、度量与三态裁决。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 条款体检 6 标签 | `clause_health.clause_health()` / `ClauseHealth` | `api/server.py` 的体检端点、`ingestion/dry_run.py`、`llm/ks_answer.py` |
| 体检结果转文本 | `clause_health.clause_health_html_to_text()` | `api/server.py`、`ks_answer` |
| 质量阈值 | `grading.THRESHOLDS` | `ingestion/dry_run.py`、`recognition` |
| 文档三态裁决与分型质量 | `grading.verdict_document()` / `grade_document()` / `typing_quality()` / `legal_element_quality()` / `one_line_summary()` | 入库预览 |
| 文本层 / 版面度量 | `recognition.text_layer_metrics()` / `page_layout_metrics()` / `measure_skew()` / `clause_ocr_confidence()` | `ingestion/pipeline.py`、`dry_run.py` |
| 云二次识别分歧报告 | `disagreement.build_disagreement_report()` / `select_2c_input()` | 阶段 2c 通道 |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `ingestion/mineru_adapter`（`is_weird_char`、`text_layer_pua_mangled`） | 同仓 | 乱码判据——本包**不另造** |
| `verification/patch_guard.nonprintable_ratio()` | 同仓 | 不可打印字符率 |
| PyMuPDF（`fitz`） | 外部库 | `measure_skew` 读页面字符坐标（这一步有磁盘 IO） |

## 明确不做什么

- **不写库、不建表、不移动用户文件**（包 `__init__.py` 明写「只读」）。
- **不做解析**：PDF / Office 解析在 `ingestion`；本包只吃解析好的结果。
- **不重定义乱码判据**：复用 `mineru_adapter`，本包只调用。
- **不自动执行裁决**：`block` 只是「不建议入库」，是否入库由**用户与评审纪律**决定。
- **不改条款原文**：`disagreement` 只出分歧报告，任何替换须**人工裁决**（证据文本不可变）。
- **不自己调云、不做外发登记**：`compare_clause_texts()` 只吃「本地文本 / 云文本」两个入参；云识别调用与 `llm/egress_audit.record_egress()` 由**调用方**做——头注把这条写成不可豁免的红线，但**本文件当前没有 import `egress_audit`**。

## 关键数据

不持有表；只吃解析结果对象（正文、markdown、页面几何、置信度）。

## 改了它会影响谁

- **`ingestion/dry_run.py`**：入库预览的三态裁决
- **`api/server.py`** 的条款体检端点
- **`llm/ks_answer.py`**：正文转文本用的是本包
- **阈值一改，这些调用方同时变**——这正是把规则从路由里抽出来的理由

## 已知边界（诚实）

- **`grading.THRESHOLDS` 是唯一调参点**：改阈值只改这一处，并同步测试 fixture。
- **「纯函数」不等于全程零 IO**：`measure_skew` 要读 PDF 页面；包的设计约束是零 DB、零 parser 依赖、零网络。
- **O2 兜底**：机器打分分布坍缩（>0.95 占比超 95%）时，`disagreement` 的输入集退化为旧 suspects 清单（启发式口径）。
- **替换字符率是独立度量**，不是异常字符率的重复：`is_weird_char` 把 U+FF00–U+FFEF 视为正常，故 U+FFFD 要单独数。
