# 统一化报告（repo-uniformity-ratchet 留档）

> **这份文件做什么**：按 `repo-uniformity-ratchet` skill 的要求，逐轮留档：
> 读数表、裁决、**我自己制造并修掉的回归**。
> skill 原话：「不留回归记录的报告等于把坑留给下一轮。」
>
> **配套文件**：
> - 尺子 `scripts/check-repo-uniformity.py` + `scripts/uniformity-ast-dupes.py`
> - 基线 `docs/uniformity/baseline.json`（天花板 + `_下调记录`）
> - 摸底证据 `docs/uniformity/README.md` / `START-HERE.md`
> - verifier 抽查 `docs/uniformity/05-verifier-findings.md`

**基线提交**：`64f37707` 起 ｜ **最后更新**：2026-10-23

---

## 一、读数演进（每一轮都是实测）

| 轮次 | ① ruff | ② pyscn（信息项） | ③ 缺 docstring | ④ 同名文件 | ⑤ 同函数体 |
|---|---|---|---|---|---|
| 立项（初测） | 6166 | 130 | 2 | **0** | **13** |
| 两档校准后（去 E501 散文豁免 / N802 中文测试名） | **1053** | 132 | 2 | 0 | 13 |
| 第三批（合并 3 组 src/core 重复） | 1052 | 131 | 2 | 0 | **10** |
| 第四批（脚本口径 + ③ 归零） | **1051** | 128 | **0** | 0 | **8** |

**收尾状态**：①②③④⑤ 全部 ≤ 天花板，且**天花板 == 实测值（零松弛）**。
③④ 是「可归零」指标，**已是 0，无存量**。

---

## 二、两条判据校准（先量后定，不是放水）

### `E501` 两档：代码行 88 显示列 / 散文行 120 显示列

**实测依据**：本仓 5,096 条 E501 里 ——
- **4,684 条（91.9%）是中文散文行**（注释/文档串）
- 412 条是真代码行

中文在 88 列下只有 **44 个汉字**，而本仓注释是**承载判断依据**的
（每条都写着"为什么这么做、实测多少"）⇒ 按 88 判会把**判断依据本身**判成违规。

**改成 120 档后散文行仍剩 64 条** ⇒ 判据仍然有效，不是放水。

**⚠ 必须用显示列不能用字符数**：实测 50 个汉字 = 102 列（判超），
50 个字母 = 52 列（不判）。用 `len()` 判宽会让中文注释一改就涨。

### `N802` 退出判据

**实测依据**：492 条里
- **452 条是中文测试名**（`test_隐藏文档被排除`）—— 本仓刻意选择
  （`docs/naming-convention.md`「代码跟随语言」：测试名要说清意图，中文比拼音清楚）
- 19 条是 Windows API mock（`SetValueEx` 等，必须同名才能替换）
- 21 条是刻意的强调写法（`test_unapproved_material_is_BLOCKED`）

⇒ 退出判据，只在 `--report` 打印。

### ② pyscn 行块克隆：降为信息项

它在**每一次纯格式改动下都会涨**（ruff format +194、docstring 折行 +39、改名 +39），
衡量的不是「重复实现」。保留打印、不决定 exit code。

---

## 三、五轮改动与守恒自查

### 第 1 批：`_xlsx_header_style`（3 处 → 1 处）

| 项 | 内容 |
|---|---|
| 原位置 | `exports/effect_report.py` / `update/announce.py` / `update/report.py` |
| 新家 | `exports/xlsx_common.py`（`update` 本来就依赖 `exports`，不引入新环） |
| 为什么合 | 表头底色是**业主定过的口径**；分叉会让三个导出文件表头不一致 |
| 守恒证据 | 用 openpyxl 读回样式**逐属性比对**（bold/字体/字号/fill/前景色/垂直居中），cols=1/3/8 全同；并验「明细行不套样式」这个原行为的另一半 |
| 回归 | 三个导出相关测试 **79 passed** |

### 第 2 批：`_checksum` / `_file_sha256`（2 处 → 1 处）

| 项 | 内容 |
|---|---|
| 原位置 | `storage/backup.py` / `update/data_package.py` |
| 新家 | `src/core/file_digest.py::file_sha256` |
| 为什么必须合 | 这两个指纹**会被互相比较**（"数据包里的库和备份里的库是不是同一份"）。分块口径一分叉，那个判断就给出错误答案。而 `data_package.py` 的 docstring 只写了「与 `backup._checksum` 同一口径」——**注释挡不住将来只改一处** |
| 守恒证据 | 0 / 100 / 65536 / 65537 / 300000 字节五种大小，新旧指纹**逐字节相同** |
| 钉住 | `CHUNK_SIZE=65536` 单独钉住（改它会让所有历史指纹失效，历史指纹存在数据库和快照文件名里） |
| 新增测试 | `tests/test_file_digest.py`（10 条）：已知值、分块边界、**两个调用点是同一个函数对象**（`is` 判等，防有人又各写一份） |
| 回归 | `test_backup.py` + `test_update_package.py` **14 passed** |

### 第 3 批：`_fetch_text` + `_ua`（各 2 处 → 基类 1 处）

| 项 | 内容 |
|---|---|
| 原位置 | `update/channels/mem_gov.py` / `mohurd.py` |
| 新家 | `ChannelAdapter` 基类 |
| 为什么合 | `_fetch_text` 的语义是「异常/非 200/非文本 **一律 None，不抛**」——这是**失败记账**的一部分。两份只要有一份改成抛异常，那条渠道的失败统计口径就和别人不一样 |
| 守恒证据 | 5 种响应（200+text / 404 / 200+bytes / UpdateError / 任意异常）返回值一致；`_ua()` 仍是那个 Chrome 串 |
| 回归 | 渠道相关测试 **214 passed, 1 skipped** |

### 第 4 批：`chunk_text` + `db_stat`（各 2 处 → `scripts/_measure_common.py`）

| 项 | 内容 |
|---|---|
| 原位置 | `measure-classical-chinese-segmentation.py` / `measure-cross-language-fts.py`（chunk_text）；`normalize-standard-no-slash.py` / `repair-missing-standard-no.py`（db_stat） |
| 为什么合（chunk_text） | 两把尺子切法一分叉，**两次测量的读数就不可比**，而这类结论要写进方案文档当依据 |
| 为什么合（db_stat） | 它是**回滚可自证**的唯一依据（复核 b31：「"可回滚"不能只是口头承诺」）。口径分叉，回滚清单没法证明「改的就是这些行、库也没被别的东西动过」 |
| 守恒证据 | `chunk_text` **21 组输入**（3 种 size × 7 种文本，含空串/超长段/CRLF/中文）全一致；四个脚本 `--help` 真跑都能启动；**生产库未被写**（两脚本默认 dry-run，库 mtime 仍是 5 小时前） |

### 第 5 批：③ 归零（2 → 0）

`scripts/docs/gen-doc-index.py` 与 `tests/conftest.py` 补模块 docstring。
后者尤其该有：里面四个夹具各自对应一个踩过的坑（空库 / 种子库 / 线程缓存 / reranker 禁用）。

---

## 四、**我自己制造并修掉的回归**（skill 要求必须留痕）

| # | 回归 | 怎么发现的 | 怎么修的 |
|---|---|---|---|
| 1 | 新文件 `make-seed-db.py` / `xlsx_common.py` / `test_standard_body.py` 引入 7 条 ruff（长行 / import 排序 / 未用 import） | **尺子当场判红**（1058 > 1053） | 逐条改；③ 那条长行拆行 |
| 2 | `report.py` import 排序被我的插入破坏（I001 从 0 变 1） | 尺子判红（1053 > 1052），再逐个文件比对「改前副本」定位 | `ruff --fix` 只修该文件 |
| 3 | `backup.py` / `data_package.py` 里 `hashlib` 变成未使用 import | `ruff --select F401` | `--fix` 清掉 |
| 4 | 脚本批：4 处 import 排序 + 2 处 `get_settings` 因 `_db_stat` 移走而不再使用 | 尺子判红（1057 > 1051） | `ruff --fix`；并**对照改前副本**确认剩余 E501/F541 都是本来就有的 |
| 5 | **`_xlsx_header_style` 批里 `announce.py` 混进另一条线的历史未提交改动**（`SOURCES_MAX` 删除等） | `git show --stat` 显示 +43/−43 而不是 −8 | **不改代码**，在提交说明里如实登记「这不是我写的、我的说明不替它背书」；判断依据是那些改动**有测试守着**（`test_ann_n08_no_source_cap`）且**只存在于工作树**（回退就永久丢失） |
| 6 | **删函数用正则导致灾难性回溯**：`(?:    .*\n)+?    return out\n` 在 19 KB 文件上跑了 **2 分钟没出来** | 后台任务超时、文件未被修改 | 改**逐行扫描**（找 `def` 行 → 向下吃到第一个顶格非空行），瞬时完成 |

**第 6 条最值钱**：它说明「批量改代码的脚本本身要按 `ast` 或行扫描写，
不要用带惰性量词的正则」—— 正则在这类缩进密集的文件上是**指数级**的。

---

## 五、明确判「不统一」的（否定裁决，须登记）

### 剩下 8 组：全部在 `tests/`，**判不合**

`fake_reg` / `store_dir` / `synthetic_parser` / `_install` /
`data_dir` / `_write_pdf` / `QueryValueEx` / `_load`

**理由（实测过的判断，不是偷懒）**：

1. 它们是**测试夹具**，不是产品代码。合并到 `conftest.py` 会让不同测试文件
   **共享同一份夹具定义** ⇒ 改一处影响 N 个测试文件的可读性与独立性。
2. 现在每个测试文件**自带夹具**，看一个文件就知道它造了什么数据 —— 这是测试的
   **可读性优势**，不是缺陷。
3. 体量都极小（4~6 语句），合并省不下多少行，却增加跨文件耦合。

⇒ **验证能力 > 去重收益**（skill 的第一条裁决原则）。

**但它们仍计入基线 8 组** —— 不是"已解决"，是「明确暂缓且继续计入」。
将来若测试夹具真的开始分叉出错（同一夹具两份行为不一致），那时按**实测到的危害**重新裁决。

---

## 六、尺子自身的自证（四条，缺一条就不可信）

| 自证 | 怎么验 | 结果 |
|---|---|---|
| 一条命令出全部读数，exit code 即判据 | `python scripts/check-repo-uniformity.py` | exit 0/1 |
| 每条指标能指回权威源 | 文件头表格逐条列出处（Google Style Guide / pyscn / 本仓 AGENTS.md / naming-convention.md） | — |
| 工具不可用时 **FAIL 不跳过** | `metric_ruff` 抛 `RuntimeError` | 有代码 |
| 读数幂等 | `--repeat-check` 连跑两次 | **PASS**（两次一致） |

**外加一条**：`--selftest` 拿坏样本确认 ③④⑤ 都抓得到负例 —— **PASS**。

**⚠ 尺子抓到了自己人的回归 4 次**（见 §四），说明棘轮是真的在拦，不是装饰。

---

## 七、没做什么（如实登记）

| 事项 | 状态 |
|---|---|
| `tools/gov-qa` 那 32 组同函数体 | **只测量不判红**（另一条线的活跃工作，767 项未跟踪） |
| 标准号归一 10 个名字的收敛 | **未做**（全仓 1,250 处引用 / 147 文件，改动面大，须分批 + 先出对应表） |
| `_answer_confidence` / `_expand_title_clauses` 两处分叉的合并 | **未做**（须先移出 `create_app` 闭包让它可测，再定字段名） |
| 门禁 `xfail` 假红的修复 | **处方已给，未实跑验证**（改门禁要跑 `-Full`） |
| 前端 40 条重复（`api.ts` 的 401 抛错 ×40 等） | **未做**（`plugin/` 侧，本轮只做了 `src/core` + `scripts/`） |
| 冒烟碰不碰真库的 39/44 套 | **未逐套确认**（只验了 5 套，全安全） |

**这些都不算「已解决」**，是明确未做。
