# 浏览器截图 + 逐页对比工作流（提示词 / 操作手册）

> 用途：KnowledgeStation 预览**渲染结果** vs **PDF 原画面**逐页成对截图，供 VLM 逐页对比、
> 定位「图片/公式/表格/上下标/带图表格/数学图形/双栏版面」的识别与排版问题。
> 作者（用户）方法论：**原画面是唯一基准**——对比时不能拿「我对 PDF 的 OCR 结果」、
> 也不能拿「渲染出来的原图」当原画面，必须直接把 PDF 页里**嵌入的原始扫描位图**抠出来。
> 预览只截**预览文本窗格 `.fulltext`**（不要截整个浏览器窗口）。

---

## 0. 自动循环硬性要求（每次执行须遵守）
（用户权威要求，固化防遗忘）
1. **根因修复（治本非治标）**：换另一本 / 新导入同类问题不得复发；已有治标补丁必改治本。
2. **逐本循环**：每本持续「截图对比 + 根因修复」直到该本找不到问题 → 换下一本继续同一循环。
3. **停止条件**：连续 5 本都找不出问题、能一次导入就全部完美，才停。
4. **同类登记 + 三振反思**：每次截图对比出的视觉错误**按类别登记**；同一类连续出现 ≥3 次 →
   上升为架构/思路问题做归纳总结（共同根因），禁止被动打补丁、反复重复无用功。
5. **全程自主不打扰**：需新工具自己装、需搜网直接搜，不打扰用户，直到最终循环结束才一次性汇报。

---

## 1. 用到的脚本与工具
| 工具/脚本 | 位置 | 作用 |
|---|---|---|
| 逐页对比脚本 | `D:\AI\work space\zcode\scripts\ks_page_compare.py` | 一键：抠原画面 + 开预览 + 逐页截预览 + 写清单 |
| browser4 浏览器 CLI | `browser4-cli`（或 `C:\Users\Zegel\AppData\Roaming\npm\browser4-cli\bin\browser4-cli-win32-x64.exe`） | 打开预览、点目录、滚动、截图、eval |
| PyMuPDF (fitz) | `.venv` 环境 | 直接从 PDF 页抠嵌入位图（`get_image_info`+`extract_image`） |
| 预览（前端） | `http://127.0.0.1:5173`（vite dev） | 渲染后的条款流 |

---

## 2. 一键逐页对比（推荐，覆盖全部页）
```
python scripts\ks_page_compare.py <doc_id>
```
- `<doc_id>` 从库查：`SELECT doc_id, standard_no FROM doc_meta WHERE standard_no LIKE '%<标准号>%' ORDER BY rowid DESC LIMIT 1`。
- 脚本自动做 4 步（见 §3-§6）：`render_orig`（抠原画面）→ `preview_open`（打开该标准预览）→ `preview_scroll_shot`（逐页滚动+截预览）→ 写 `manifest.json`。
- **输出**：`C:\Users\Zegel\AppData\Local\Temp\pagecmp\`
  - `orig_pN.<ext>` — PDF 页**嵌入的原始扫描位图**（`get_image_info(xrefs=True)` 取面积最大者 + `extract_image`；无嵌入图才回退 `get_pixmap` 渲染）
  - `prev_pN.png` — 预览 `.fulltext` 文本窗格截图（每页滚动到 `.page-break[data-page=N]` 后截）
  - `manifest.json` — 每页 `orig`/`prev` 路径 + 页号（供 VLM 逐页 `read_image` 成对对比）

> 已改：脚本支持 `sys.argv[1]` 传 `doc_id`；`preview_open` 用该文档的 `standard_no`（不再硬编码 24276）打开目录对应文档。

---

## 3. 手动 browser4 前端操作（抽查某一页时用）
按顺序执行（`browser4-cli`）：

**3.1 打开预览**
```
browser4-cli open --headed --fresh http://127.0.0.1:5173
```
**3.2 展开目录抽屉**（点「📚 文件目录」按钮）
```javascript
() => { const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim()==='📚 文件目录'); if (b && !document.querySelector('.toc-drawer')) b.click(); return 'n'; }
```
经 `browser4-cli eval --base64 <b64> --json` 执行（b64 = `[Text.Encoding]::UTF8.GetBytes(js)` 的 base64）。

**3.3 目录搜索框输入标准号**（例如 `1032`）
```javascript
() => { const i = document.querySelector('.toc-drawer input'); const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(i,'1032'); i.dispatchEvent(new Event('input',{bubbles:true})); return 'q'; }
```
**3.4 点击命中条目**（textContent 含标准号）
```javascript
() => { const d = document.querySelector('.toc-drawer'); const h = Array.from(d.querySelectorAll('*')).find(e => (e.textContent.includes('1032') && e.children.length===0)); if (h) h.click(); return h ? 'opened':'none'; }
```
**3.5 等文档渲染**（约 9-10s）后滚动到目标**
- 滚动到某物理页：`.page-break[data-page=N]`（如 5.2.4 → 第 9 页）：
  ```javascript
  () => { const pv=document.querySelector('.fulltext'); const pb=Array.from(pv.querySelectorAll('.page-break')).find(x=>x.dataset.page==='9'); if(pb) pb.scrollIntoView({block:'start'}); return 'p9'; }
  ```
- 滚动到含公式/双栏的元素：`.katex-formula[data-clause]` 或 `.cols`：
  ```javascript
  () => { const pv=document.querySelector('.fulltext'); const el=pv.querySelector('.cols') || Array.from(pv.querySelectorAll('.katex-formula')).find(x=>x.dataset.clause==='12.8.2.2.2'); if(el) el.scrollIntoView({block:'center'}); return el?'ok':'none'; }
  ```
**3.6 截图预览文本窗格（只截 `.fulltext`）**
```
browser4-cli screenshot ".fulltext" -o "%TEMP%\ks_<名>.jpeg"
```
> 注意：browser4 元素截图输出**字节可能是 JPEG**（尽管写 `.png`）——若 `read_image` 报扩展名不符，把扩展名改为 `.jpeg`。

---

## 4. 原画面截图（准确，勿用渲染/OCR）
详见 `render_orig`（`ks_page_compare.py`）：对每页 `page.get_image_info(xrefs=True)` 找**面积最大**的图像 xref → `doc.extract_image(xref)` 写原始字节；无嵌入图才回退 `get_pixmap(dpi=150)`。**不要**用 `get_pixmap` 渲染当原画面、**不要**用 OCR 文本当原画面。

---

## 5. 输出位置汇总
| 内容 | 目录 |
|---|---|
| 逐页成对截图 | `C:\Users\Zegel\AppData\Local\Temp\pagecmp\`（orig_pN / prev_pN / manifest.json） |
| 手动抽查截图 | `C:\Users\Zegel\AppData\Local\Temp\ks_*.jpeg` |
| 问题登记簿 | `D:\AI\work space\zcode\docs\visual-regression-log.md`（按类别登记 + 三振反思） |

---

## 6. VLM 逐页对比
对 `manifest.json` 每页 `read_image("...orig_pN")` + `read_image("...prev_pN")` 成对看。
**判读要点**：
- 原画面 `orig_pN` 为基准（面积图）。
- 预览 `prev_pN` 只含 `.fulltext`；**连续流含相邻页**——以截图内「第 N 页」**页界角标**为锚，别把相邻页的表/图误判为错位；若 `.fulltext` 正中确实出现**不属于该页**的表/图，那才是归位/边界错。
- 逐类核对：**图片（缺/错位）、公式（是否 KaTeX 排版/是否 raw）、表格（内容/归位）、上下标（Aₑ vs A°）、带图表格、数学图形（曲线/chart）、双栏版面（左/右列）**。
- 视觉错误**按类别登记**到 `visual-regression-log.md`；同类 ≥3 次做架构反思。

---

## 7. 常见坑（避免重复）
- **原画面 vs 渲染**：`orig_pN` 必须来自 `get_image_info+extract_image`（不是 `get_pixmap`、不是 OCR）。
- **预览整窗口 vs 窗格**：截图目标是 `.fulltext`（元素），不是整窗口。
- **相邻页**：`.fulltext` 流式含多页，看页界角标。
- **扩展名造假**：browser4 输出常是 JPEG 字节却标 `.png`——按字节改 `.jpeg`。
- **一次一本**：`ks_page_compare` 每跑一次只生成一个 `doc_id` 的对比（改参数重跑换本）。
