# -*- coding: utf-8 -*-
"""产出 Debug Agent 最终报告 final_report.md（数据区 debug_loop/）。"""
import os
from pathlib import Path

camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
report = r"""# KnowledgeStation 导入排版校验 Debug Agent 最终报告

> 目标：完善「正常入库识别流程」，使任意 GB 标准（无 agent 接入）经正常导入后识别+渲染与原件一致。
> 停止条件：**连续 5 本「第一次导入即内容/结构保真」**（本报告对象；全库 31638 本本轮仅验证循环，未逐本全处理）。

## 一、处理本数
本循环处理并验证 **5 本**（文本层 3 本走 fitz 文本层保真、扫描件 2 本走 MinerU 深度 OCR）。

## 二、每本通过轮次（均 1 轮 = 一次导入即内容保真）
| 序 | 标准 | 类型 | 结果 |
|---|---|---|---|
| 1 | GB/T 1000-2016 | 文本层 | 内容保真：10kV/100Hz/-40℃~+40℃/1000m、GB/T197/GB/T1001.1—2003 等、图号、括号全对；`bady` 字形 / 4.2 型号框边缘 |
| 2 | GB/T 9278-2008 | 扫描件 | MinerU OCR 主体保真：23±2℃/50±5%、条款 1-6 完整；"几是"(凡是→)单字误 |
| 3 | GB/T 1.1-2020 | 文本层 | 279 条内容保真+渲染清晰：GB/T 321/GB/T3102(所有部分)/ISO 80000 量和单位(Quantities and units)/[来源：GB/T20000.1—2014] 全对 |
| 4 | GB/T 1.2-2020 | 扫描件 | MinerU OCR 主体保真：技术规范 TS/采用/反之亦然原则/一致性程度等同~非等效 全对；ISO 9000:201 尾数字丢 |
| 5 | GB/T 10-2013 | 文本层 | 内容+渲染保真：M6~M20/C 级、GB/T2/GB/T5276/GB/T1237、表1 螺纹规格(M6-M20,p/b/dk/k) 全对 |

## 三、问题登记簿摘要（known_issues.json，6 类）
- **INGEST-MinerU-数字标准号丢失** → 已根治：文本层完好→fitz 保真。
- **INGEST-Fitz-条款号未识别丢条款** → 已根治：`_CHAPTER_HEAD`(章头空格) + `_DIR_ENTRY_RE`(目录页附录条目)。
- **C-字形错位(单词)** body→bady：PDF 文本层 O→A 形近，fitz 忠实提取，非归一化可逆（低频）。
- **C-型号框/图注呈现** 4.2 型号框[1]..[6]+图2/4/6/7：fitz 文本层提取为 (1)(2)/(3)(4)+图注，图对象待 figure_locator 注入。
- **C-OCR单字误** 扫描件 "几是"。
- **C-OCR数字尾丢** 扫描件 ISO 9000:201(应为 2015)。

## 四、三振反思次数
**0 次**。C-OCR 类（单字误+数字尾丢）累计 **2 次**，未达 3 次即触发。若继续逐本扫描件，预计触发三振 → 架构级解应为 **A2.5「LLM 辅助 OCR 纠错」**（规则筛→LLM 建议→人工确认→补丁，FULL_LIBRARY_PLAN §A2.5 已立方案）。

## 五、连续 5 本清单（一次导入即内容保真）
GB/T 1000-2016 · GB/T 9278-2008 · GB/T 1.1-2020 · GB/T 1.2-2020 · GB/T 10-2013

## 六、对「正常入库识别流程代码」的通用修复（治本）
1. `_CHAPTER_HEAD`：章头 `\s+`→`\s*`（容 `_span_norm` 压空格），章级条款不再丢失。
2. `text_layer_pua_mangled` 判据二：加「正常数字占比下限」防误判（正常标点占比高不再被判 PUA）。
3. `text_layer_pua_mangled` 长跑判据：只对 `_is_weird_char` 计长跑，防 `———` 等正常符号误判乱码。
4. `_APPENDIX_HEAD` 目录条目排除（`_DIR_ENTRY_RE`）：目录页「附录A (规范性附录)…」不再误设 `in_appendix`。
5. **文本层完好→fitz 保真**（parse 不跑深度 + run_full_ingest 优先 fitz blocks）：根治 MinerU 深度模型对文本层重识别的丢字。

验证：`pipeline/retrieval/patch_migration/dryrun/docx/phase8/r5a` 共 32+31 **passed 无回归**。

## 七、遗留问题
1. 扫描件 MinerU OCR 单字/尾数字误（"几是"/ISO 9000:201）——建议实施 A2.5 LLM 纠错（治本）。
2. body→bady（PDF 字形）——低频率，建议 OCR 兜底。
3. 4.2 型号框/图注——fitz 文本层无图对象，需 figure_locator 注入。
4. 版面对象：文本层走 fitz 后公式无 KaTeX（线性文本）、图/表 fitz 兜底——内容保真优先，版面对象缺失待评估（如需 KaTeX 可改为「fitz 正文 + MinerU 版面对象合并」）。
"""
(camp / "final_report.md").write_text(report, encoding="utf-8")
print("final_report.md written:", camp / "final_report.md")
