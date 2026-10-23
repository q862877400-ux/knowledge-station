# verification（核验与纠错守卫）

**位置**：`src/core/verification/`
**一句话**：检查「模型说的」有没有证据、「用户改的」有没有改坏。

## 职责

两条互相独立的守卫：

- **分型核验**（`typed_verifier.py` 13.6 KB，T06）：条款号闭包（引用条款号必须 ⊆ 证据集）；data 型数值闭包（数值 + 单位必须原样出现，改写记 `number_tampered`）；rule 型模态强度（弱化拦截 `modality_weakened`、强化记警告、缺失记 `modality_missing`）；legal 型法理要素（例外丢失 `exception_missing`、主体缺失 `subject_missing`）。
- **纠错补丁守卫**（`patch_guard.py`）：用户「乱纠正」的三级响应——`ok` 落库 / `warning` 落库并回警告 / `reject` 拒绝落库；全规则式，零 LLM 消耗。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 分型核验 | `typed_verifier.verify_llm_output(llm_output, evidence_clauses)` | `api/server.py`、`llm/ks_answer.py` |
| 纠错补丁守卫 | `patch_guard.check_patch(original, patched, field_name)` | `api/server.py` 的补丁端点 |
| 不可打印字符率 | `patch_guard.nonprintable_ratio()` | `quality/recognition.py` |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `domain/models`（`MODALITY_STRENGTH` 等） | 同仓 | 模态强度与结果模型（权威常量，本包只读） |
| `knowledge/classifier.extract_modality` | 同仓 | 从条文里取模态词 |
| difflib / re | 标准库 | 相似度与不可打印字符判定 |

## 明确不做什么

- **不做检索、不生成答案**：只判「已有答案与证据是否对得上」。
- **不落库**：`check_patch` 只返回三态，写入由 `api` 与 `storage` 执行。
- **不做质量分级**：条款体检与文档三态裁决在 `quality`。
- **不做合规差距分析**：义务与制度比对在 `compliance`。
- **不自己定义模态强度**：`MODALITY_STRENGTH` 的唯一所有者在 `domain/models.py`，改它要走契约变更。
- **不做「算法口径」核验**：本模块管的是「你写的数是不是条文里那个数」；「你用的是不是规定的方法」本仓不做，也无人做。

## 关键数据

不持有表；只吃传入的答案文本、证据条款与补丁前后文本。

## 改了它会影响谁

- **`api` 的核验与补丁端点**：返回结构进答案、进界面
- **`llm/ks_answer.py`**：核验字段经 `plugin/src/trim.js` 的白名单才到模型眼前
- **`quality/recognition.py`**：直接 import `nonprintable_ratio`


## 规模与覆盖（2026-10-23 实测）

| 项 | 数字 |
|---|---|
| 文件数 | **3** 个 `.py` |
| 行数 | **427** |
| 提到本子系统的测试文件 | **6** 个 |

> 数字口径：`rglob("*.py")` 排除 `__pycache__`；测试覆盖 = 在 `tests/*.py` 里出现过 `src.core.<本子系统>` 的文件数（**只是「提到」，不等于「被测」**）。

## 已知边界（诚实）

- **阈值常量在 `patch_guard.py` 顶部**：相似度下限 0.15、不可打印率上限 0.30、长度 3 倍 / 1/3、中文占比降 30 点；原文短于 12 字时跳过相似度检查（标题类小改）。
- **核验只覆盖「能自证的」错**：数值、模态、例外、主体、条款号。措辞与推理质量不在核验范围内。
- **本模块不出「当前有效期」结论**：现行性来自 `knowledge/legal_status.resolve_status`。
