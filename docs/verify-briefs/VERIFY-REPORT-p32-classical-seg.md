# 独立复核报告：P3.2 古籍/文言切分评估（批次 `p32-classical-seg`）

* 复核者：verifier-p32（独立复核者，非作者）
* 日期：2026-10-09
* 被验冻结 tag：`verify-freeze-p32-classical-seg` = `7c92405c27194b33fb9ef29578c2571e8ac95752`
* 主仓：`D:/AI/work space/zcode`（复核时 master HEAD = `fb11af7`，tag 在其历史中）
* 提取树：`D:/AI/verify-trees/p32`（`git worktree add D:/AI/verify-trees/p32 verify-freeze-p32-classical-seg`）
* 语料（**只在主仓，只读引用**）：`D:/AI/work space/zcode/var/fixtures/general-corpus/sanguo.txt`
* 解释器：`D:/AI/work space/zcode/.venv/Scripts/python.exe`（Python 3.12.14）
* **结论：放行（无阻塞）**；附 5 条非阻塞发现（§F）。

---

## 0. 提取树首尾取证（本仓"边改边验=双向污染"，故只读引用语料、一切变异在提取树里做）

**首（复核开始时，`D:/AI/verify-trees/p32`）：**

```
$ git rev-parse HEAD
7c92405c27194b33fb9ef29578c2571e8ac95752
$ git status --short
(空)
```

**尾（复核结束、两处变异已还原后）：**

```
$ git rev-parse HEAD
7c92405c27194b33fb9ef29578c2571e8ac95752
$ git status --short
(空)
$ tr -d '\r' < scripts/measure-classical-chinese-segmentation.py | sha256sum
a8baac472ba29b17fb071b05da94a93064849b0fc23f60fec76720ebfc60e465
```

> ⚠ 提取树检出的是 **CRLF**（Windows git autocrlf）；作者文档里记的 SHA256 `a8baac47…` 是 **LF** 版本的哈希。
> 我把提取树文件 `tr -d '\r'` 后复算 = `a8baac47…`，与文档**逐位一致**（作者工作副本是 LF）。**这不是差异**。

### 0.1 冻结事实复核（我机械重算，全部与主代理一致）

| 项 | 主代理给的 | 我实测 | 结论 |
|---|---|---|---|
| tag → commit | `7c92405` | `7c92405c27194b33fb9ef29578c2571e8ac95752` | ✅ |
| `rev-list --count 111e270^..<tag>` | 4 | 4 | ✅ |
| 其中别进程提交 | `e4edb82` gov-qa | `e4edb82`（4 文件中 3 个 `tools/gov-qa/*`） | ✅ 与本批无关 |
| 本批自己的提交 | 3 条 | `111e270` / `1e46f30` / `7c92405` | ✅ |
| 没碰生产代码 | `git diff --stat 111e270^..<tag> -- src/ plugin/` 空 | **空** | ✅ |

本批**实际改动面**（`git diff --name-only 111e270^..<tag>`）：

```
docs/CHANNEL-COVERAGE-PLAN.md
docs/DEVELOPMENT-HISTORY.md
docs/NEXT-DEV-PLAN-2026-09-28.md
docs/RETRIEVAL-LONG-RANGE-PLAN.md
docs/research/classical-chinese-segmentation-evidence.md
docs/research/cross-language-retrieval-evidence.md
scripts/measure-classical-chinese-segmentation.py
tests/test_classical_segmentation_ruler.py
tools/gov-qa/adapters/nat_cnipa.py          ← 属 e4edb82（别进程），非本批
tools/gov-qa/adapters/nat_mot.py            ← 同上
tools/gov-qa/adapters/nat_tax.py            ← 同上
tools/gov-qa/recon/audit-coverage.py        ← 同上
```

⇒ **本批只动 `scripts/*.py`、`tests/*.py`、`docs/*.md`**，与主代理陈述一致。

---

## A. 独立重算尺子读数（**我自己跑，不信文档**）

命令（提取树里跑，语料从主仓只读引用；`PYTHONPATH` 指向提取树以解析 `src/`）：

```
cd D:/AI/verify-trees/p32
D:/AI/work space/zcode/.venv/Scripts/python.exe \
  scripts/measure-classical-chinese-segmentation.py \
  "D:/AI/work space/zcode/var/fixtures/general-corpus/sanguo.txt"
```

结果 `exit=0`，输出 `/tmp/p32_run1.txt`（3 次运行见下）。**逐格核对文档 §三**：

### A.1 语料与现状
| 项 | 文档 §二 | 我实测 | 结论 |
|---|---|---|---|
| 字符数 | 641,312 | `641,312 字符` | ✅ |
| 段数 | 712 | `→ 712 段` | ✅ |

### A.2 三种口径的词表 / 单字占比
| 口径 | 文档词表 | 我实测 | 文档单字占比 | 我实测 | 结论 |
|---|---|---|---|---|---|
| A 现状 | 60,022 | **60,022** | 30.3%（122,148/403,481） | **30.3%（122,148/403,481）** | ✅ |
| B 字级 | 4,839 | **4,839** | 81.3%（484,892/596,278） | **81.3%（484,892/596,278）** | ✅ |
| C 领域词典 | 57,786 | **57,786** | 20.1%（79,181/393,579） | **20.1%（79,181/393,579）** | ✅ |
| 逐字同法复算 | 30.2%（122,148/404,316） | **30.2%（122,148/404,316）** | — | — | ✅ |

> 计划里那个 30.2% **复现成立**（分母口径 = 前 800 段拼串分词；逐段分词是 30.3%）。文档把两个口径都印出来，**没有含糊**。

### A.3 检索命中率（1,200 条查询）
| 口径 | 文档 @5/@20/MRR/空 | 我实测 @5/@20/MRR/空 | 结论 |
|---|---|---|---|
| A 现状 | 30.8% / 47.4% / 0.210 / **15** | **30.8% / 47.4% / 0.210 / 15** | ✅ |
| A+ | 34.3% / 54.2% / 0.232 / 0 | **34.3% / 54.2% / 0.232 / 0** | ✅ |
| B 字级 | 40.2% / **72.2%** / 0.270 / 0 | **40.2% / 72.2% / 0.270 / 0** | ✅ |
| B' 对照 | 39.8% / 71.2% / 0.261 / 0 | **39.8% / 71.2% / 0.261 / 0** | ✅ |
| C 领域词典 | **42.3%** / 65.7% / **0.286** / **15** | **42.3% / 65.7% / 0.286 / 15** | ✅ |

按 n 拆开（文档 §三·③ 第二张表）：n=2 / n=3 / n=4 各格**逐格一致**（含 A 空查询 7+7+1=15、C 同为 7+7+1=15）。
文档把 B' 从 n 拆表里略去（全表里有），**不是漏报**，是有意只列四口径。

### A.4 繁简轴（§三·④）
七组异形词（關公/雲長/張飛/軍馬/糧草/商議/曹賊）简体栏 **A/B/C 三栏全 0**：✅ 我实测全 0。
同形对照（旌旗 A 繁=47 / A 简=47；次日 208/208）**繁栏与简栏逐格相同**：✅（B 简栏 52/299 不同，文档已解释为字级口径本身更宽，非错误）。

### A.5 可复跑性
连跑 3 次（第 3 次 `2>&1` 合并捕获）。剔除耗时行（`建表 Xs`）后：

```
$ sed -E 's/建表 [0-9.]+s/建表 Xs/g' run1.txt > c1 ; sed ... run2.txt > c2
$ diff c1 c2 && echo "(no diff)"
(no diff)
$ md5sum c1 c2
c527a5553cadc9e23cb79fd13091a1c9  c1
c527a5553cadc9e23cb79fd13091a1c9  c2
```

⇒ **两次剔除耗时行后逐字节相同成立**（我实测 md5 `c527a555…`）。
> ⚠ **非阻塞发现 #1**：文档 §二 与开发史 §10.208 记的 md5 是 `6855a287…`，**与我的口径对不上**（我试了"替换/删除耗时子串、合并 stderr、CRLF→LF"四种剔除法都得不到该值）。**可复跑性结论本身成立**，但文档里那个**具体 hash 值不可复现** ⇒ 建议重算或删去具体值，只留"两次逐字节相同"。

---

## B. 判据有没有牙（改到判据的批次必须证明"那条测试真的在跑" + 断言没被放宽）

### B.1 原样件
```
$ PYTHONPATH=D:/AI/verify-trees/p32 <venv>/python.exe -m pytest tests/test_classical_segmentation_ruler.py -v
test_char_seg_gives_one_token_per_cjk_char ............................. PASSED
test_char_level_requires_relaxing_the_single_char_drop ................. PASSED
test_no_drop_expr_differs_from_production_only_by_the_single_char_rule . PASSED
test_single_ratio_counts_occurrences_not_documents ..................... PASSED
test_ngram_counts_segments_not_occurrences ............................. PASSED
============================== 5 passed in 1.13s ==============================
```
✅ **5 passed**。测试依赖可用（`src.core.text_utils` 正常导入、jieba 可用），**确实在跑**。
`pyproject.toml` `testpaths=["tests"]` ⇒ 该文件会被 `-Full` 的 pytest 收集（⚠ 属注册在案的"抬高 pytest 总账"事项，见 §F#4）。

### B.2 变异 1：`single_ratio` 把 `cnt` 改回 `doc`
（提取树内改 `SELECT term, cnt FROM v_{tbl}` → `SELECT term, doc FROM v_{tbl}`）
```
FAILED tests/test_classical_segmentation_ruler.py::test_single_ratio_counts_occurrences_not_documents
E       assert 3 == 5
=========================== 1 failed, 4 passed in 1.21s ===========================
```
✅ **变红，且只红预期的那一条**。文档 §八 声称"1 failed / 4 passed"**属实**。

### B.3 变异 2：`char_and_expr` 也丢单字（`if has_cjk(ch)` → `if has_cjk(ch) and len(ch) > 1`）
```
FAILED tests/test_classical_segmentation_ruler.py::test_char_level_requires_relaxing_the_single_char_drop
E       assert '' == '"陳" "留"'
=========================== 1 failed, 4 passed in 1.01s ===========================
```
✅ **变红，且只红预期的那一条**。文档声称**属实**。

### B.4 还原
两处变异均已在提取树内还原；`git status --short` 空、`git diff --stat` 空；脚本 LF-SHA256 回到 `a8baac47…`；复跑测试回到 **5 passed**。
⚠ 我**没有**同时跑 `scripts/run-gates.ps1`（遵守"变异与门禁并发 ⇒ 假红"的禁令，锁文件退出码 3）。

---

## C. 声称与实现是否一致（本批最容易出错的地方）

### C.1 "词典与考卷不相交" + `load_userdict` 调用位置
* **调用位置（关键）**：`main()` 里 `import jieba; jieba.load_userdict(dict_terms)` 在**第 302–303 行**；而 A/B 两口径的建表与 `single_ratio` 在**第 266–269 行**、`probe`（复现 30.2% 的那次分词）在**第 277–278 行**。
  ⇒ **A/B 及 30.2% 复算都在 `load_userdict` 之前完成**，**没有被 C 的词典污染**。✅ **不是实质错误**。
* **来源不重叠（段级）**：`cut = int(len(rows)*0.5)`，`rows` 712 段 ⇒ `cut=356`；`train=rows[:356]`、`test=rows[356:]`。我实测 `set(range(356)) & set(range(356,712)) = set()` ⇒ **两来源段索引完全不重叠**。✅
* ⚠ **非阻塞发现 #2（措辞不精确）**：文档 §二 / 计划 §二乙写"**词典与考卷不相交**"，**字面上不成立**。我机械求交：`dict_terms(5000) ∩ queries(1200) = 269 条`（≈22%，样例 `一刀斬/一彪軍/一軍/三軍/不知其…`）—— 因为同一串词在前半段（进词典）与后半段（进考卷）**都出现过**。
  **机制本身没错**：词典**只由前半段挖出**、查询词**只由后半段挖出**，属标准留出法（train/test），**没有把测试集答案注入词典** ⇒ "C 的收益构造上不可能来自把答案塞进词典"**成立**。但"不相交"这个词**应改成"词典来源与考卷来源段级不相交（留出法）"**，否则读者按字面理解会以为 0 交集。

### C.2 "字级查询不能复用 `fts_match_expr`"
我独立实测：
```
segment_for_fts('陳留') = ['陳', '留']
fts_match_expr('陳留', latin_prefix=False) = ''        ← 被清空
segment_for_fts('黃巾') = ['黃', '巾']
fts_match_expr('黃巾', latin_prefix=False) = ''        ← 被清空
fts_match_expr('關公', latin_prefix=False) = '"關公"'  ← jieba 认得的词正常
char_and_expr('陳留') = '"陳" "留"'
no_drop_expr('陳留')  = '"陳" OR "留"'
```
机制**属实**：`fts_match_expr`（`src/core/text_utils.py:1526`）有 `if len(tok) > 1` 丢弃单字符词；字级索引下把查询清空 ⇒ **"选字级就必须同时改 `fts_match_expr`"这条代价是真的**。✅

### C.3 "绝对值是送分题"
查询词来自 `kept = [g for g in picked if g in joined]`（`joined = "\n".join(rows)`）⇒ 查询词**必是语料原文的子串**；目标段 `tgt = {i for i,seg in enumerate(rows) if q in seg}` 也在原文里定。⇒ **确系"从原文抄的"送分题**，文档 §三/§七 明确警告"不能当产品效果"。✅ **如实**。

### C.4 文档有没有超出证据的断言
逐条查（任务点名的三类）：
* **把"送分题"数字当产品效果**：**没有**。§三·③ ⚠、§七、计划块都写明"只能横向比"。
* **把自挖 n-gram 词典说成"正经词典"**：**没有**。§三·② 明写"机械自挖的 n-gram，不是人编的词典"，举例 `德曰/笑曰/有一` 不是词；§五·3 要求将来用"有出处的人编/权威古籍词典"。
* **把"一部语料"说成通用结论**：**没有**。§七、§四·2 明写"一部明代小说，不是生产库""量的是通用性质，不是产量指标"。
⇒ **未发现超出证据的断言**。文档在"诚实边界"上做得比一般批次更严。

---

## D. 判定与理由是否站得住

作者拍板"**不改生产口径**"，三条理由：

| 理由 | 我的独立判断 | 依据 |
|---|---|---|
| ① 主因是繁简不是切分 | **被读数支持**（机制性，非统计性） | 七组异形词 A/B/C 三栏全 0（我实测）；字级也一样 0，因为简体字在繁體原文里**根本不存在** ⇒ 换任何切分口径都救不了。**结构性成立**。⚠ 但样本仅 **7 组高频词**，是"机制证明"而非"比例估计"——文档**没有**把它当比例，措辞得当。 |
| ② 只有一部语料 | **被事实支持** | 712 段、一部明代小说；"换资料类型就跑一遍"是本仓 P3.3 自立的规矩（`RETRIEVAL-LONG-RANGE-PLAN` 3.3 行）。一部不足以支撑**索引口径**级变更。**合理**。 |
| ③ 代价与收益不匹配 | **基本支持** | A+ 改的是**全库生效**的 `fts_match_expr`，且对法规语料的副作用**本轮未量**（§五/§九 自认）—— 属实。B 要改两处口径 + 重建索引 —— 属实（⚠ "522k" 这个具体数**我未独立复算**，采信作者/既有文档）。C 需正经词典 —— 属实。 |

### D.1 "单字占比不能当判据"这条纠偏 —— **独立判断：成立，且是本批最有价值的一条**
我实测：B 单字占比 **81.3%（最高）**却拿 **@5 第二（40.2%）、@20 第一（72.2%）**；C 单字占比 **20.1%（最低）**拿 **@5 第一（42.3%）、MRR 第一（0.286）**。三条换法**没有一条**的单字占比与命中率单调同向 ⇒ **"降单字占比"不能当目标**，单看占比会得出**相反结论**。**这条纠偏被读数支持，方向正确。**

### D.2 ⚠ 非阻塞发现 #3（措辞可疑）
§四·3（及 §10.208）有一句："B … 而且'把单字占比推到 81.3%'本身就是把'词'这个单位取消掉，**与'按字找'的立论相反**。"
—— B 恰恰**就是**"按字找"，说它"与按字找相反"**读不通**，疑为笔误（应是"与'按**词**找'的立论相反"，或指"与 P3.2 原判据想降占比的方向相反"）。**不影响结论**（③ 的主证据是"重建索引 + 改两处口径"的代价），但**建议改准**，否则读者会绕。

---

## E. 回归（本批是否可能引起那两个门禁红）

主代理给的 `-Quick` 读数：**3/5，exit=1** —— tsc ✗、mypy ✅（153 文件）、verify:commands ✅ 22/22、pssa-guard ✅、smoke ✗。我**未重跑门禁**（锁 + 时间），做**静态判断 + 最小面核对**：

| 红 | 位置 | 是否本批改动面 | 判断 |
|---|---|---|---|
| tsc ✗ | `plugin/client/KsKnowledgePage.tsx:77`：15 个 `Icon*OutlineRegular` 从 `@deepseek-ai/dsh-client-ui-primitives` 导入，其中若干未导出 | **否** —— `plugin/` 在本批 `git diff --stat 111e270^..<tag> -- plugin/` 为**空**；本批未动任何 `.tsx/.ts/package.json/tsconfig` | **依赖/导出漂移**，与本批无关 |
| smoke ✗（两次跑红点不同） | `plugin/scripts/smoke-lifecycle.mjs`（D5/D6 `calls=-1`）、`plugin/scripts/smoke-chatmode.mjs`（172/174 并发写 EPERM） | **否** —— smoke 脚本在 `plugin/scripts/`，本批未碰 | **并发假红**：`scripts/run-gates.ps1:23-25` 自己写明"并发跑会制造假红（`smoke-chatmode` 实测两次 172/173 都发生在与全量…）"，且**两次红点不同**正是竞态特征 |

⇒ **两个红都不在本批改动面内**。本批只动 `scripts/*.py`、`tests/*.py`、`docs/*.md`，**不能**解释 tsc 的依赖导出缺失，也**不能**解释 smoke 的并发 EPERM。**判断成立**。

---

## F. 非阻塞发现清单（本仓惯例：复核的非阻塞发现会被逐条就地更正）

1. **文档里可复跑的 md5 `6855a287…` 与我复现的口径对不上**（我实测 clean 输出 md5 `c527a555…`，两次一致）。可复跑**结论**成立，**具体 hash** 不可复现 ⇒ 重算或删去具体值。
   *（对照：脚本 SHA256 `a8baac47…` **可复现**，是 LF 版本哈希，✅ 无问题。）*
2. **"词典与考卷不相交"字面不成立**：`dict_terms ∩ queries = 269/1200`。机制（段级留出法）**正确**，但措辞应改为"词典**来源**与考卷**来源**不相交"。见 §C.1。
3. **§四·3 一句措辞可疑**："与'按字找'的立论相反"读不通，疑笔误。见 §D.2。
4. **新测试抬高 pytest 总账**：`-Full` 的棘轮"passed 只涨不跌"要求更新基线（`scripts/gates-baseline.json`）。文档 §八 已**登记**"未跑 `-Full -UpdateBaseline`"——**已自知**，只需别忘。
5. **语料不在版本库**（`var/*` 被忽略）⇒ 尺子从冻结提取树**不能单独复现**（`main()` 无参时返回 2）。文档 §九 已**登记**并给出两条处置。本批**不算欠账**（属主代理已知的登记项），但**它确实限制了本报告的"从提取树独立复现"能力**——我是**只读引用主仓那份语料**才复算出来的。

---

## G. 复核者声明（区分"我实测"与"我采信"）

**我实测的**：全部 A 节读数（语料/词表/占比/命中率/繁简/可复跑）、B 节 5 passed + 两处变异各只红一条 + 还原、C.1 段级不重叠 + 269 交集 + `load_userdict` 位置、C.2 三例 `fts_match_expr`、C.3 查询来源、E 节改动面静态核对。
**我采信作者/既有文档的**：`522k` 索引规模；`-Quick` 3/5 各步读数（我未重跑门禁）；`opencc/zhconv` 未安装；`eval/golden/knowledge-snapshot.db` 存在。
**我未做**：未重跑 `run-gates.ps1`（锁 + 时间）；未做法规语料副作用对照（作者亦未做，已在 §五/§九 登记）；未独立复算 `522k`。

---

## 结论

**放行（无阻塞）。** 本批 3 条自提commit 均只动 `scripts/*.py`、`tests/*.py`、`docs/*.md`，未碰生产代码；判据有牙（5 passed，两处变异各只红预期一条）；声称与实现一致（无超证据断言）；"不改生产口径"的三条理由被读数支持，"单字占比不能当判据"这条纠偏独立成立；两个门禁红均在本批改动面外。
附 5 条非阻塞发现（§F），其中 #1（md5 不可复现）与 #2（"不相交"措辞）建议就地更正。
