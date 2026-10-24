# 为什么"约定了契约"还是会变乱

> 业主 2026-10-24 问：「我记得这个项目开发的时候是约定了契约的，怎么还是会变乱」
>
> 这份文件用**本仓的实测证据**回答。结论先说：
> **契约不是没定，是"定了但没有机器盯着"**。文档里的约定靠人记得，人记不住。
>
> 每一条都带文件位置与实测数字。

---

## 一、本仓确实有契约（不是没有）

| 契约 | 在哪 | 管什么 |
|---|---|---|
| 契约台账 | `pipeline/03-contract-delta.md` | 改 schema 前必须先写一条 |
| 命名规范 | `docs/naming-convention.md`（v2，2026-10-05 定案） | 文件/目录怎么命名、什么算"历史"该归档 |
| 项目宪章 | `.specify/memory/constitution.md` | 7 条原则（自 AGENTS.md 提取） |
| 检索质量契约 | `eval/baseline.json` | 4 指标回退 ≤2pp、`modality_intercept_rate` 硬底线 0.9 |
| 门禁纪律 | `AGENTS.md` | 一条命令、以退出码为准、基线只涨不跌 |

**这些契约都是真的、都写下来了、有的还很严**（`eval/baseline.json` 是全项目最强约束：
基线缺失 = 硬失败）。

---

## 二、那为什么还是变乱了 —— 六个可实测的原因

### 原因 1：契约只覆盖"命名"，**不覆盖"同一功能只许一份实现"**

`docs/naming-convention.md` 管的是**文件名/目录名**（连字符不用下划线、标准文档全大写、
分类靠目录不靠前缀）。它**一个字都没提"同一个功能不许两个实现"**。

⇒ 后果实测：`src/core` 里有 **13 组跨文件同函数体**（α-等价，改个变量名就完全相同），
其中 `_xlsx_header_style` 三处逐字相同、`_checksum`/`_file_sha256` 两处逐字相同。
**它们不违反任何一条既有契约**，所以没有任何东西会拦它们。

### 原因 2：门禁 12 步全在验"跑得通"，**没有一步量"是不是只有一个口径"**

`scripts/run-gates.ps1` 的 12 步是：tsc / mypy / verify:commands / pssa-guard / smoke(44套)
/ pytest(3,117条) / 引擎门禁 / verify-tools-real / 真宿主 e2e / gov-qa 三条。

**它们全部回答"功能还在不在"，没有一个回答"同一个东西是不是只有一份"。**

⇒ 这就是为什么 13 组重复能活到今天：**没有一道门禁在看这件事**。
（这也是我这次先造尺子的原因 —— 没有读数就直接动手，"改好了"无法证明。）

### 原因 3：同一事实写在三处，改一处另两处腐烂

实测找到 **9 组互相矛盾的数字/说法**（详见 `03-docs-specs-scripts.md` §三），典型：

| 冲突 | 一处说 | 另一处说 | 实测 |
|---|---|---|---|
| 表数量 | `schema.sql` 冻结 **38 张** | 统一化尺子量到 **44 张** | **44** |
| 语料规模 | **6,797 篇 / 522,021 条** | **8,983 篇 / 663,634 条** | 后者 |
| 子系统数 | `docs/README.md` **19 个** | `wiki/architecture.md` **16 个** | **16** |
| 工具数 | `docs/README.md` **4 个** | `wiki/architecture.md` **6 个** | **6** |
| 「接手先读哪一份」 | `wiki/` 说是我 | `HANDOVER` 说是我 | `ENCYCLOPEDIA` 也说是我 |

**根因**：这些数字**没有单一归属**。文档 A 说了、文档 B 抄了一份，然后 A 更新了、B 没跟。
`AGENTS.md` 明明写了「一个事实一个归属层」，但**没有任何机器检查"是不是抄了两份"**。

### 原因 4：契约本身会过期，而且**过期了没人知道**

实测两例：

| 契约原文 | 事实 |
|---|---|
| `specs/001-project-consolidation/rename-map.md`：「`wenjianmulu/` **未跟踪（不在版本控制里）**」 | `git ls-files wenjianmulu` 返回 **2 条**（两个 PDF 都受控） |
| `docs/README.md`：「`pipeline/03` 有 **79 处引用**」 | 实测 **31 处** |

**根因**：契约是**文档**，它的正确性靠**人下次读它时核对**。
而没人会去核对一份"看起来已经定案"的契约。

### 原因 5：契约写的是"该怎么做"，**没写"做不到时谁会发现"**

`AGENTS.md` 明令：**代码里不许写死绝对路径**（便携硬约束，业主 2026-10-17 亲定）。
但我实测到 **12 处写死旧工作区路径** `D:/AI/work space/zcode`：

```
plugin/scripts/smoke-kb-page-render.mjs:2629
plugin/scripts/verify-commands-real.mjs:34
plugin/scripts/verify-tools-real.mjs:101（注释）
…共 12 处
```

**逐处核实后的精确分类（13 处，不是 12 处）**：

| 类别 | 处数 | 位置 | 严重度 |
|---|---|---|---|
| **真运行依赖**（会真去读旧路径） | **2** | `plugin/scripts/smoke-kb-page-render.mjs:2629`<br>`plugin/scripts/verify-commands-real.mjs:34` | 🔴 假绿 |
| **脚本里写死 `REPO` 常量** | 3 | `scripts/fix-dsh-icon-names.py:15`<br>`scripts/map-dsh-icons.py:13`<br>`scripts/pick-domain-terms.py:48`<br>（都是 `REPO = Path(r"D:\AI\work space\zcode")`） | 🟠 只在旧路径下能跑 |
| **测试里写死** | 3 | `tests/test_jev_cn_baseline.py:21`（未跟踪文件）<br>`tests/test_rag_gate_not_adopted.py:46`<br>`tests/test_change_signal.py:175`（注释） | 🟡 |
| **注释/文档串**（允许，讲历史） | 4 | `audit-hardcoded-paths.py:41`、`engine.js:39` 等 | ✅ 不算违规 |

**最要命的一处**：`smoke-kb-page-render.mjs:2629`
```js
const guideSrc = readFileSync('D:/AI/work space/zcode/plugin/client/KsKnowledgeGuide.tsx', 'utf8')
```
它**读的是旧工作区的文件，不是本仓的**。现在能过，只是因为：
- 旧目录 `D:\AI\work space\zcode` **还在磁盘上**（实测存在）；
- 那份文件与当前仓的 sha256 **完全相同**（`67AE7732…`）。

⇒ **这是假绿**：它验的是外部旧副本，不是被测的这棵树。
一旦旧目录被删（或换台机器、或 `git worktree` 提取树里跑），这条**当场崩**。

**而没有任何门禁检测"有没有写死路径"** —— 协议写了，执行没落地。

### 原因 6：契约的"修订流程"没有机械闭环

`pipeline/03-contract-delta.md` 要求"改 schema 前先写一条"。
但**没有任何东西检查"改了 schema 却没写 delta"**。
它内部引用的 `pipeline/02-architecture-contract.md` **根本不存在**（断链），
说明连台账自己都在腐烂。

---

## 三、一句话总结

> **契约是"约束人的文字"，判据是"约束机器的数字"。
> 只有前者 ⇒ 靠人记得 ⇒ 人记不住 ⇒ 一定烂。**

本仓的情况是：**契约写得比大多数项目都细，但 12 步门禁里没有一步在读契约。**

---

## 四、所以我这次做了什么（对应上面六条）

| 原因 | 我做的 |
|---|---|
| 1 契约不管重复实现 | 造了统一化尺子（5 指标），把"重复"变成读数；⑤ 从 **13 组降到 8 组** |
| 2 门禁不看一致性 | 尺子已可一条命令出全部读数、exit code 即判据，**待接进门禁**（见 §五） |
| 3 同一事实写多处 | 给三份"接手入口"定了序；`wiki/architecture.md` 与 `docs/README.md` 的数字全部对齐到实测 |
| 4 契约过期没人知道 | 全部数字标上**口径**（工作树 vs HEAD）、补"最后更新"、过期处就地更正并留痕 |
| 5 契约没写"谁会发现" | 发现 12 处写死路径并登记（**尚未修**，见 §五） |
| 6 修订没闭环 | 加了 `docs/uniformity/baseline.json`（天花板只降不升 + `_下调记录`），把"约定"变成"棘轮" |

---

## 五、还没做的（照实登记）

| 事项 | 状态 | 为什么值得做 |
|---|---|---|
| **把尺子接进 `run-gates.ps1`** | **未做** | 现在尺子要人记得跑；接进门禁才有强制力。这是"契约变判据"的最后一公里 |
| **修那 12 处写死路径** | **未做** | 其中 `smoke-kb-page-render.mjs:2629` 是**假绿**（读外部旧副本） |
| **删/隔离旧工作区 `D:\AI\work space\zcode`** | **未做** | 它现在是假绿的"支撑"。要业主决定（可能还有别的东西在用） |
| 把"同一功能只许一份实现"写进 `naming-convention.md` | 未做 | 契约目前完全不管这件事 |
| 契约过期检测机制 | 未做 | 现在靠人；可考虑把关键数字做成生成物（机器可核） |

---

## 六、给业主的一句话

**约定没问题，缺的是"约定之后有人盯着"。**

我这次造的那把尺子就是把"盯着"变成机器的事 ——
但它现在还**没接进门禁**，所以严格说：**统一化目前的约束力来自我的自觉，不是来自系统。**

要让它真正不变乱，下一步是**把尺子接进 `run-gates.ps1`**，
让"重复变多"和"测试变少"一样**当场红**。

（这件事本身不大 —— 在 `run-gates.ps1` 里加一个 `Add-Step`，跑 `check-repo-uniformity.py`。
代价是每次门禁多约 10 秒。）

---

## 七、附：我试写"自动检测写死路径"的检测器，**失败了**（留证）

想把它做成判据（`scripts/audit-hardcoded-paths2.py`），扫全仓报 **198 处**。
抽样一看，**绝大多数是误报**：

| 被误报的东西 | 为什么 |
|---|---|
| `[[m:\s*(-?\d+` | 正则里的 `m:` 被当成盘符 |
| `\tag\{[^` | LaTeX 的 `\tag{` |
| `'2009\ue01103'` | 转义序列里的反斜杠 |
| `PK\x03\x04` | ZIP 签名 |

**根因**：`[A-Za-z]:[\\/]` 这个模式对"任意单字母 + 冒号"都成立，
而代码里到处是正则、LaTeX、转义序列。

**处置：删掉那个脚本，不接进门禁。** 理由：
- 一个误报率 >90% 的判据，要么被无视，要么逼所有人写 `noqa` —— 两种都比没有更坏；
- 按纪律「同一个启发式连续修补 ≥3 次看起来对了就停下」，**这次第 1 次就停下**。

**改用"精确串匹配"**（`D:/AI/work space` / `D:\AI\work space`），一次就得到上表那 13 处，
零误报。**通用检测器需要真校准（AST 级判断"这是路径字面量吗"），明确未做。**

⇒ 这条本身就是「原因 5」的又一个例证：**写契约容易，写守契约的判据难；
判据写歪了比没有更糟。**

---

## 十、补：`src/core` 三个最大文件读完后的**直接证据**（2026-10-24）

`09-big-files.md` 把 `pipeline.py`（2,443 行）、`text_utils.py`（2,162 行）、
`inspector.py`（937 行）逐行读完，找到 **8 组「同一件事两个实现」**。
**其中第 1 条是代码注释自己承认的** —— 这比任何推测都硬。

| # | 同一件事 | 两份实现 | 后果 |
|---|---|---|---|
| **1** | **「页码 + 标准号」页眉判据** | `pipeline._STD_CODE_FRAG/_frag_key/_strip_foreign_frag`<br>`text_utils._RE_WM_HEADER/_match_key/strip_watermark_lines` | **`pipeline.py` 的注释原话：`⚠ 这两个判据是「页码 + 标准号」的**第二份实现**（第一份在 text_utils 的水印族）`**。两边口径已不同：pipeline 允许 `\d{1,6}` 号与任意 1–4 大写字母前缀，text_utils 要求 `\d{3,5}` 号 + 前缀白名单 ⇒ **一边认得的页眉另一边会漏** |
| 2 | 图例判据 | `_is_figure_legend`（块级，条目只认数字） | `strip_figure_legend_segment`（文本级，含字母型、要求两个破折号）⇒ 单破折号/字母型条目两边判定不一致 |
| 3 | HTML → 纯文本 | `text_utils.html_to_text`（声明为规范实现） | 另有 `server._html_to_text`、`ks_answer._html_to_text_compact`、`clause_health_html_to_text`。**`text_utils` 的 docstring 原话：`此前同一算法在**三处**各有一份…**没有**顺手改那三处的调用点…登记为待办`** —— 登记了，没人做 |
| 4 | 标准号归一/比较键 | `text_utils` 4 个 | 另有 `channels/base.norm_no`、`ccs_fetcher._seed_key`、`clause_repo._standard_body`、`pipeline._hier_from_no`、`_frag_key`。各 docstring 都写「口径不同」，但**没有任何判据能证明它们在同一输入上不矛盾**。`norm_no` 注释记着一次真失配：`GB/T－17098` 与 `GB/T-17098` 归一出永不相等 |
| 5 | **完整入库流程** | `pipeline.run_full_ingest`（12 步） | `law_text.ingest_law_text`（自建 model / 自建边 / 自写 doc 行 / 自查 CCS）。**`law_text.py` 注释原话：`pipeline.py 的 resolve_edges 一直有这道闸，这里漏了 ⇒ 两条入库路径行为不一致`** |
| 6 | app_config 读写 | `inspector.get_config` / `set_config` | `announce.py`、`discover.py`、`subscriptions.py` **各自直接写 SQL**（工具函数存在，3 个兄弟模块绕过它） |
| 7 | 同文件近重复 | `text_utils._match_key`（有人用） | `text_utils._match_std`（**全仓 0 调用**） |
| 8 | ✅ **做对了的那一例** | `clause_repo._seg` | → `from src.core.text_utils import segment_for_fts`，注释写「保留这个私有名只是为了不动既有调用点；**实现只有一份**」 |

### 顺带查出的死代码与不可达代码（实测 `grep`）

| 类别 | 位置 | 证据 |
|---|---|---|
| 真死 | `inspector._utcnow` | `grep '_utcnow'` 全仓 **1 处，就是 def 行本身** |
| 真死 | `text_utils._match_std` | `grep '_match_std'` 全仓 **1 处，就是 def 行本身** |
| **不可达** | `inspector._probe_number` L444–454 | 前面 L435–443 是**无条件 return**，后面永远执行不到 |
| **不可达** | `pipeline._extract_vector_table_items` L1820–1821 | `is_ocr` 恒为 `False`（`mineru_adapter` 里硬编码后原样带出） |
| 未使用 import | `inspector.py` 3 个 | `UPD_CAPTCHA_BLOCKED`、`CHANGE_TYPES`、`LEGAL_STATUSES`（AST 剥 docstring 后 0 引用） |
| 过时注释 | 7 处 | 注释里写的行号已漂移 |

### **6 个**超过 100 行的函数（我第一版写「5 个」，漏了 `_cell_html`）

| 文件 | 函数 | 行数 |
|---|---|---|
| `pipeline.py` | `run_full_ingest` | **397** |
| `pipeline.py` | `split_items_into_clauses` | **367** |
| `pipeline.py` | `build_clause_models` | **201** |
| `inspector.py` | `run_batch` | **172** |
| `inspector.py` | `_probe_number` | **121** |
| `pipeline.py` | `_cell_html` | **116** |

（`load_middle_items` 刚好 100 行，计入则 7 个。）

**⚠ `text_utils.py` 一个超长函数都没有**（最长 91 行）—— 它的问题是**职责过多**
（前一半 OCR 清洗、后一半塞了标准号比较键 + FTS 分词 + 采集侧 HTML→文本 + 二进制嗅探），
**不是函数过长**。⇒ 「拆函数」对这个文件是错的药，该拆的是**模块**。

### 会丢数据的隐患（静态推断，未跑真入库对账）

`reingest` **先删旧文档（独立事务）再写新文档** ⇒ 新事务失败 / 进程被杀
就是「旧已删、新没进」，而**目录归属快照只在内存里**。

另：`total_clauses` 报的是 `n_normal - n_pre`，而实际入库是
`n_normal + n_pre + n_附录` ⇒ **算术可疑**。⚠ 这两条都是**静态结论，未验证**。

### 过时注释 7 处（全部带 git 年龄，最长 42 天）

`pipeline.py` 有 **3 处行号已漂移的自引用**（注释写 `:658-661`，实际在 **709-712**；
注释写 `2021/2037/2096`，实际在 **2244/2260/2401**）；
`inspector.py` 的模块 docstring 还写着链是 `official_gb→govcn`，
而**同一文件 L523 自己写着**实际是 `official_gb→ndls→govcn`（36 天）；
`text_utils.html_to_text` 的「三处待办」**37 天未动，仍 4 份实现并存**。

⇒ 这 7 处本身就是「契约腐烂」的微观证据：**注释写了"以后改"，然后没人改，注释还留在那儿骗下一个人。**

### 这节对「契约为什么会烂」的意义

上面 8 组里，**有 3 组的代码注释自己写着「这是第二份实现」/「三处各有一份」/「这里漏了」**。

⇒ **写代码的人知道有重复，甚至写下来提醒后人，但没有任何机器检查会因此变红。**
这就是「原因 1 + 原因 2」的活标本：契约不管重复，门禁不看重复，
于是「知道」和「修掉」之间那条路**从来没被打通**。
