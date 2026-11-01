# 渠道库接线方案

> 调查对象：`update_channel` 表 286 行、其中 `wiring='seed_only'` 262 行。
> 数据来源：只读打开 `var/data/database/knowledge.db`（`mode=ro`）+ 读代码 + grep，未跑引擎、未跑门禁、未跑 pytest、未抓任何外网。
> 生成日期：2026-10-25。台账会变（渠道在增），引用前请重跑 §七 的命令。

---

## 〇、一句话结论（先看这个）

**262 条 `seed_only` 里，一条也进不了巡检链 —— 不是配置问题，是 id 形状问题。**

`ledger_chain` 只认 `channel_id = "ch:<适配器名>"` 这一种形状（判据见 `_name_candidates`，源码 `src/core/update/channels/ledger_chain.py`：「`ch:ndls` ⇒ `{ndls}`；`seed:law-cn:xxx`/`tool:xxx` 这类没有适配器名 ⇒ 空集」）。
262 条的 id 实际是三种形状：`ch:<类别>:<ULID>`（149 条）、`seed:<文件>:<中文名>`（95 条）、`tool:<名>`（18 条）——**没有一条取得出适配器名**。

⇒ 把 `wiring` 从 `seed_only` 改成 `wired`，**行为上什么都不变**：`wiring` 这个字段在链里只做两件事（挡 `broken`、报候选），它从来不是"能答"的证据。真正的门槛是「代码里有这个适配器名」+「台账 id 是 `ch:<那个名>`」。

顺带一条同源缺陷（不是本次任务但属于同一根因）：今天 13 条 `wired` 里有 **6 条** id 是 `ch:law:01M4DJF8…` / `ch:std_hb:01M4DJF8…`，名字同样取不出适配器（按 `ledger_chain_report` 里 `missing_in_code` 的判据**手工复算**会点名这 6 条；未 import 模块、未跑引擎）。这 6 条里 5 条标着 `verified`、1 条 `unverified`，但巡检永远不会问它们。

**这条结论改变了方案形态**：接线不是"补 URL / 补锚点"，而是"**每接一批，同时把台账 id 改写成 `ch:<新适配器名>`**"。少了后半步，代码写得再对也是零。

---

## 一、接线的最小条件

### 1.1 三层门槛（都能从代码里读出来，不用猜）

**第一层 · 代码里有适配器**（`src/core/update/channels/__init__.py`）

- 一个 `ChannelAdapter` 子类，`name = "<渠道名>"`，实现 `probe(self, standard_no: str, standard_name: str = "") -> ChannelResult`（`base.py` 的 `class ChannelAdapter(ABC)`，`probe` 是 `@abstractmethod`，接口注释写「接口冻结」）。
- 在 `ADAPTER_CLASSES` 里登记：`"<名>":  <类>`。新渠道默认走 `_safe_import("<模块名>", "<类名>")`。
- `_safe_import` 的语义（源码注释：「容错导入子代理正在实现的渠道（未完成/语法错不阻塞整体启动，记 warn）」）：**吞掉任何异常、返回 `None`、只打一条 `ks.upd` WARN**。
- 这个名字会不会被当成"代码里存在"，取决于 `_adapter_names()`：「`{getattr(cls, "name", None) or key for key, cls in ADAPTER_CLASSES.items() if cls}`」——**`None` 被 `if cls` 过滤掉**。⇒ 模块导入失败 = 名字从 `known` 里消失 = fail-closed（不进链），但**不报错、不红门禁**，只在日志里一条 WARN。这是"配了个不存在的渠道"伪装成"链短了一截"的入口。

**第二层 · 台账 id 对得上**（`ledger_chain.py`）

- `_channel_id_of(name)` = `f"ch:{name}"`；`_name_candidates(cid)` 只在 `cid.startswith("ch:")` 时返回 `{cid[3:]}`，否则返回空集。
- `ledger_fallback_chain` 的过滤式：`name in in_code and ((row := by_id.get(_channel_id_of(name))) is None or not _is_excluded(row))`。
- `_is_excluded` 只认两条：`enabled=0`（人工停用）、`wiring='broken'`（已知失效）。**`state` 不过滤**（模块 docstring 写明理由：按一次探针就把渠道踢出链会让链随探针抖动）。

**第三层 · 巡检真的会问它**（`routing.py`）

- 泛查兜底链是 `_FALLBACK = ("official_gb", "ndls", "govcn")` 三个字面量。
- 前缀首选在 `_PREFIX_ROUTE`（7 条正则 → `ndls`/`ttbz`/`mee`/`dbba`/`hbba`）。
- 台账 `segments_json` 只能**加尾巴**（`_segment_channels`，且「只加路由链里没有的」）。
- ⇒ 一个适配器写好了、台账 id 也对上了，如果名字既不在 `_FALLBACK`、也不在任何 `_PREFIX_ROUTE`、又没有号段声明，它依然**一个号都不会被问到**。`segments_report()["unreachable_no_segments"]` 就是这份欠账清单（R6g 记录的"13 条适配器只有 3 条在链上"就是这个）。

**汇总成一句可执行的话**：一条渠道要变成真能回答的 `wired`，**必须**同时具备 ① `ADAPTER_CLASSES` 里一个非 `None` 的类、② 台账行 `channel_id = "ch:<该类.name>"` 且 `enabled=1`、`wiring != 'broken'`、③ 该名字出现在 `_FALLBACK` / `_PREFIX_ROUTE` / 台账 `segments_json` 三者之一。

### 1.2 `probe_url` / `probe_expect` 是干什么用的？为空会怎样？

**答：这两列今天没有任何代码在读。** 为空对巡检、对探针、对接线**都无影响**。

- 它们只出现在两个"字段白名单"里：`channel_repo.py` 的 `_DESCRIPTIVE`（种子可写）与 `src/core/api/routes_channels.py` 里允许经 HTTP 写的那串字段名。
- 全仓递归 grep `probe_url|probe_expect`，除上面两处白名单、`channel_probe.py` 里一个**同名的局部 dict 键** `no_probe_url`、以及两条用例断言外，**没有任何读取点**。
- 真正的探针目标在**另一个文件**：`src/core/update/channel_probe.py` 的 `PROBES_PATH = Path(__file__).resolve().parent / "channel_probes.json"`，由 `load_targets()` 逐字段校验后喂给 `probe_channel(channel_id, target)`。
- 目标字段是 `url / method / json / form / headers / expect / min_links / evidence / note`（`_TARGET_KEYS`）。**`expect` 为空串是明确禁止的**（注释：「`"" in body_text` 恒真 ⇒ 连空正文都会被判 `ok`（假绿）」）；要"只探连通性"就省略 `expect`，结果是 `unknown/no_anchor_configured`。同理只给 `url`、不给任何期望 ⇒ `unknown`，不算通过。

**所以为空会怎样：什么都不会发生。** 真正会影响的是"这条渠道有没有进 `channel_probes.json`"——没进 = 探针根本不探它（`probe_channels` 的注释：「没配目标的渠道会被跳过……只是出现在返回值的 `without_target` 里」）。

实测（见 §七 命令）：`channel_probes.json` 今天有 **102 个目标**，全部落在台账里；其中 89 个是 `seed_only`。

### 1.3 `segments_json` 是什么？为空影响什么？

- 语义：**"这条渠道管哪些标准号段"**，JSON 字符串数组，如 `["HJ", "GB 50"]`（`check_segments` 的报错文案就是这个例子）。
- 写路径：`upsert_channel` 里调 `check_segments`，形状不合法**出声拒绝**（`ValueError`），理由是「一个拼错的号段会永不命中……那正是'配置错伪装成渠道故障'」。
- 读路径：`parse_segments` **容错，坏值返回空元组、绝不抛**（读路径不该因为一行脏数据炸巡检）。两者分工是刻意的。
- 作用点只有一处：`chain_for_number` → `_segment_channels`，把命中本号号段的渠道**追加到链尾**（不动链首顺序；已被排除的、代码里没有的不加）。
- 为空的影响：**不加尾巴**。对 262 条来说，"为空"甚至不是瓶颈——就算填了号段也没用，因为 `_segment_channels` 同样要 `name in in_code`，而它们的名字取不出来（§〇）。

实测：`segments_json` **0/286 非空**。

### 1.4 `channel_test_case` 表谁来写、什么时候写？

- 写者一：`src/core/update/channel_test.py` 的 `set_test_case(channel_id, sample_url, expect_no, note)`，经 HTTP `POST /api/v1/channels/{channel_id}/test-case`（`src/core/api/routes_channels.py`）。**人工**动作——业主/维护者给某条渠道配"一个已知文件"（样本链接 + 期望标准号）。
- 写者二：同文件的 `_record(channel_id, result, detail)`，由 `run_channel_test` 调用，经 `POST /api/v1/channels/{channel_id}/test` 触发。**成功失败都落痕**（模块 docstring：「结果**永远落库**……不留痕就等于没测过」）。
- 语义：模块 docstring 引业主原话——「成功把某个你知道的文件从新渠道下载或者识别下来了，那就说明这个渠道是成功的」。它答的是比探针更强的一句："真东西拿不拿得到、**认不认得出**"。
- 实现纪律：拉取走可注入 `fetcher`（默认 `urllib` 标准库 GET，10s 超时）；识别口径是本模块的 `STANDARD_NO_RE`（「找到的第一个号」）；改样本会**清掉旧样本的留痕**（`ON CONFLICT ... last_result=NULL`），因为"改样本 = 重新起跑"。
- 实测：**0 行**。⇒ 286 条里没有任何一条被这套"已知文件验收"验过一遍。

### 1.5 台账三列的真实口径（`channel_repo.py` 的模块 docstring 是权威）

| 列 | 回答的问题 | 谁写 | 值域 |
|---|---|---|---|
| `wiring` | **我们的适配器能不能解析它** | 人工/种子（描述性字段） | `wired / unwired / broken / user / seed_only` |
| `verification` | 研究期**一次性**实测，这个站当时好不好使 | 调研文档导入 | `verified / unverified / broken` |
| `state` | 运行期探针实测 | `record_probe()`（**源码里的唯一写者**） | `unknown / ok / suspicious / down` |

模块 docstring 明写：「**注册 ≠ 能力**」；「`verification`（研究期一次性实测）≠ `state`（运行期探针）」；「**种子导入不得覆盖运行期健康度**」（`_DESCRIPTIVE` 里没有 `state/last_*/consecutive_failures`，且 `upsert_channel(overwrite_health=False)` 会把它们从 payload 里 pop 掉）。

**但今天这张表里的 `state` 有一半不是探针写的（实测，不是推论）**：`record_probe` 的 SQL 注释明写「`last_try_at` **任何状态都推进**（含 unknown）」⇒ 凡走过探针的行，`last_try_at` 必非空。实测：

| 指标 | 值 |
|---|---|
| `last_try_at` 非空的行 | **102** / 286 |
| `last_ok_at` 非空的行 | 78 / 286 |
| `channel_probes.json` 的目标数 | **102**（完全吻合） |

⇒ **只有那 102 行（80 ok / 16 suspicious / 6 down）的 `state` 是运行期实测**；剩下 **184 行**（79 ok / 23 suspicious / 53 down / 29 unknown）的 `state` 不是探针结果，是别的路径写进来的（递归 grep 全源码，写 `state` 的只有 `channel_repo.py` 里 `record_probe` 那一处 `UPDATE update_channel SET state=?`；种子的 `_DESCRIPTIVE` 也不含 `state`）。**作者未查到**（没查 `event_log`、没查一次性迁移脚本）。
**⇒ 面板上"286 条里 159 条 ok"这个数字，有 79 条是导入值、不是实测。做任何按 `state` 的排序决策前必须先知道这一点。**

---

## 二、262 个 seed_only 分组（表）

分组是**互斥**的，判据全部来自 URL 主机 + 路径与 `ADAPTER_CLASSES` 的对照（命令见 §七）。

| 组 | 判据 | 条数 | 其中"已有校准探针且 ok+语义期望"（可直接开写解析器） |
|---|---|---|---|
| **A 有现成 KS 适配器** | URL 的 host+路径落在某个已接适配器的**同一栏目** | **19** | 8 |
| **B gov-qa 有、KS 没有** | `tools/gov-qa/adapters/` 里能找到**同栏目**的适配器 | **0** | 0 |
| **C 按站点族可批量接** | 同一套平台/URL 语法覆盖 ≥2 条，一个参数化适配器可吃 | **35** | 16 |
| **D 逐站新写** | 找不到任何现成适配器、也不成族 | **184** | 42 |
| **T 非发布源（工具）** | `category='tool'`：定义就是"可抄思路，**不是**发布源" | **24** | 0 |
| 合计 | | **262** | **66** |

> **最后那一列的读法**（很要紧）：它统计的是"`channel_probes.json` 里有目标 **且** `state=ok` **且** 配了 `expect`/`min_links`"。
> 这个组合的含义是"**页面形态已被真机确认、内容真的发出来了、不是 JS 空壳**"——所以这批写解析器不用先探。
> 反过来，**没有这一个组合的 196 条不代表坏**：其中 173 条压根没有探针目标（探针不探它们），它们的 `state` 还是导入值（见 §1.5），**不能用它判断好坏**。

**另一个独立轴：`verification`（研究期一次性实测，与 `state` 无关）**

| `verification` | seed_only 条数 | 接线时怎么用 |
|---|---|---|
| `verified` | 154 | 研究期验过 ⇒ 直接写适配器，风险低（但仍要自己跑一遍，见 §四） |
| `broken` | 66 | 研究期验出坏的 ⇒ **先重探**，可能已修好或改版 |
| `unverified` | 42 | 没验过 ⇒ **必须先探**，别直接写适配器 |

（对照：全 286 行是 `verified` 159 / `broken` 66 / `unverified` 61；差额 5 条 `verified` 落在已 `wired` 的行上。`docs/GOVQA-UNWIRED-CHANNELS.md` 里记的 154/66/53 是把 11 条 `unwired` 的 `internal` 也算进了"没接线"口径，两者不矛盾。）

### A 组 19 条明细（这一批的正确动作不是写代码，而是**去重**）

| 已接适配器 | 条数 | 落在该适配器站点/栏目的 seed_only |
|---|---|---|
| `laws_db` | 4 | 国家法律法规数据库-检索列表API / 详情 / 枚举字典 / 首页聚合（`flk.npc.gov.cn/law-search/*`） |
| `mem_gov` | 3 | 应急管理部-法律法规 / 应急管理部标准 / 应急管理部-AQ行业标准公告 |
| `mee` | 3 | 生态环境部-法规标准 / 生态环境部标准 / 生态环境部-标准发布 |
| `official_gb` | 2 | 国家标准全文公开系统 / (index)（`openstd.samr.gov.cn/bzgk/std*`） |
| `hbba` | 2 | 行业标准信息公共服务平台 / 公告计划（`hbba.sacinfo.org.cn/stdList`、`/snList`） |
| `ttzb` | 2 | 全国团体标准信息平台 / 首页 |
| `dbba` | 1 | 地方标准信息公共服务平台（`dbba.sacinfo.org.cn/stdList`） |
| `mohurd` | 1 | 住建部-工程建设标准文告（该站另有 3 条已 `wired` 的 `ch:law:…` 行） |
| `std_samr_hb` | 1 | 全国标准信息公共服务平台-行业标准（`std.samr.gov.cn/hb`） |

这 19 条与已 `wired` 的 13 条是**同一批站点被重复登记了两次**（一次作为 `ch:<适配器名>`，一次作为 `ch:<类别>:<ULID>` 种子）。它们需要的不是新适配器，而是：把台账 id 合并到 `ch:<已存在的适配器名>` 上（或直接删掉重复行）。**注意 `laws_db` 那 4 条里只有"检索列表API"是适配器真正打的端点（`/law-search/search/list`）**，其余 3 条是同服务的兄弟端点（详情/字典/聚合），适配器不调它们——严格说这 3 条属于"同服务不同端点"，接的意义是补能力而不是修 id。

### C 组 35 条的四个子族

| 子族 | 条数 | 依据 | 已有校准探针(ok+语义期望) |
|---|---|---|---|
| C1 `std.samr.gov.cn` 其他子栏目 | 14 | 全站同一平台，子栏目 `/gb`、`/db`、`/noc/nocGB\|HB\|DB\|TB\|CMR`、`/org`、`/tb`、`/gj`、`/gw`；KS 现有 `std_samr_hb` 只打了 `/hb` 一个 | 6 |
| C2 `*.sacinfo.org.cn` 其他子系统 | 3 | `std.sacinfo.org.cn/PCNoc/queryAll`、`tc.sacinfo.org.cn`、`org.sacinfo.org.cn/tcrm/…`；与 `hbba`/`dbba` 同平台但**子系统不同** | 0 |
| C3 `col/col<数字>/index.html` CMS | 8 | 浙江（zj.gov.cn 4、sft.zj.gov.cn 1）、江苏市监、山东市监、广电总局，URL 语法完全同形 | 5（另 1 条 `ok` 但没配语义期望、2 条 `suspicious`） |
| C4 同站扩栏目（已有适配器但栏目不同） | 10 | www.gov.cn 4、mem.gov.cn 1、mohurd.gov.cn 3、mee.gov.cn 1、www.gov.cn 标准查询 1 | 5 |

C1 的批量依据不是猜的：仓库里已有三处实测记录同一个平台的**同构子接口**——`docs/CHANNEL-COVERAGE-PLAN.md`「国标公告发现 `GET std.samr.gov.cn/noc/search/nocGBPage`（实测 total=542…）」与「团标 `GET std.samr.gov.cn/tb/search/tbPage`（total=7906…）」；`docs/research/cross-plane-jump-assessment.md`「`std.samr.gov.cn/gb/search/gbAdvancedSearchPage` | JSON 通、**无验证码**」；再加上代码里 `std_samr_hb` 打的 `/hb/search/hbPage`。⇒ 四个子栏目同一套"`<子栏目>/search/<子栏目>Page`"JSON 接口，一个参数化基类能覆盖。

### D 组 184 条的难度分布（这一组不是"一堆散站"，而是"34 个站 × 多点"）

- distinct host **131 个**；
- 其中 **34 个 host 各占 ≥2 条，共 87 条** —— 这部分可以按"一站一适配器、覆盖多点"来做，不是逐条；
- `std_db`（各省地方标准）**36 条**，是 36 个**互不相同**的遗留系统（`LawQueryServlet` / `.aspx` / `.jsp` / `findLocalStandard.do` / `:8090`、`:8012` 之类 IP+端口），**没有共用平台**；
- 已有校准探针且 ok+语义期望 **42 条**（这批"页面形态已知、内容真有"）；
- 剩下 **142 条**既没校准探针也没族归属——需要先探、再写。

### T 组 24 条 —— 建议**不接**

`category='tool'`，`channel_repo.py` 的类别注释写着 `"tool",       # 工具与 Skill（可抄思路，不是发布源）`。它们没有"渠道"属性：URL 是 `github.com`（17 条）、`npmjs.com`（2 条）、`clawhub.ai`（1 条），另有 4 条 URL 就是 `(not found)` / `(ambiguous…)` / `(no single canonical repo found)`。把它们列在渠道台账里本身是分类错误——它们该在"参考工具"清单里，不该参与 `wiring` 统计。

---

## 三、站点族覆盖表（核心）

### 3.1 gov-qa 的共用引擎 —— **对 262 条的覆盖是 0**

先给汇总数字（命令见 §七）：`tools/gov-qa/adapters/` 有 **371 个 .py**，其中非 `_` 开头 **356 个**；`ADAPTERS` 字典 **355 条**登记；**272 个适配器用到某个共用引擎**，84 个独立。

| 引擎文件 | 覆盖 gov-qa 适配器数 | 覆盖 KS 渠道数 | 是否已被 KS 用过 |
|---|---|---|---|
| `_igi_common.py` | 111 | **0** | 否 |
| `_gd_hdjlpt_common.py` | 47 | **0** | 否 |
| `_hunan_hd_common.py` | 33 | **0** | 否 |
| `_jact_common.py` | 32 | **0** | 否 |
| `_sczwfw_common.py` | 21 | **0** | 否 |
| `_zj_mhww_common.py` | 11 | **0** | 否 |
| `_sd_jact.py` | 7 | **0** | 否 |
| `_liuyan_common.py` | 4 | **0** | 否 |
| `_post_list_common.py` | 4 | **0** | 否 |
| `_jpaas_jact_common.py` | 2 | **0** | 否 |
| `_jpaas_jact_html_common.py` | 2 | **0** | 否 |
| `_sd_jact_gw.py` | 2 | **0** | 否 |
| `_was5_common.py` | **0（无任何适配器 import 它）** | 0 | 否 |
| `_igi_multi.py` | **0（无任何适配器 import 它）** | 0 | 否 |

**"覆盖 KS 渠道数 = 0" 不是抽样，是两次独立核对的结果：**

1. **URL 标记核对**（对 262 条的全部 URL 做正则）：`/IGI/`、`/jact/`、`/was5/`、`liuyan.people.com.cn`、`hdjlpt`、`jpaas`、`sczwfw`、`mhww`、`12345`、`mailbox|szxx|ldxx|letter`、`hdjl` —— **命中数全部为 0**。
2. **内容口径核对**（对 371 个适配器 .py 全文 grep `flfg|zcfg|zhengce|bzgk|bzgg|fggb|dfxfg|gongbao|zhengcelibrary`）：**No matches found**。抽查交集站点的实际列表 URL 全是互动栏目：`nea.gov.cn/hudong/liuyan.htm`、`moa.gov.cn/bzxxlyhf/xfwy/…`（部长信箱留言回复）、`cma.gov.cn/wmhd/gzly/`、`forestry.gov.cn/hdly.jhtml`、`amr.gd.gov.cn/hdjlpt`、`beijing.gov.cn/hudong/hdjl/…`。

⇒ **gov-qa 那 355 个适配器整体是"政民互动/留言/12345"语料，262 条整体是"法规/标准发布"栏目。两个语料不重叠。** 题目预设的"IGI/jact/WAS5 一个引擎覆盖几十个城市站点 ⇒ 也能批量接 KS 渠道"这条路，**对 262 条不成立**。

同域名但不同栏目（不能复用解析器，只能复用传输/反爬经验）的 50 条顺带记一下：`github.com` 17、`mem.gov.cn` 4、`mee.gov.cn` 4、`mohurd.gov.cn` 4、`beijing.gov.cn` 4、`gdpc.gov.cn` 4、`nea.gov.cn` 3、`forestry.gov.cn` 3、`npc.gov.cn` 2、`moa.gov.cn` 2、`cma.gov.cn` 2、`amr.gd.gov.cn` 1。其中唯一"内容沾边"的是 `rd-*` 族（9 省人大·**法规草案征求意见**，`_common` 文件是 `rd_common.py`）——KS 的 `gdpc.gov.cn` / `npc.gov.cn` 种子是**已发布法规**栏目，不是草案征集，仍然不同栏目。

### 3.2 KS 侧真正的站点族（按覆盖条数排）

| 站点族 | KS 渠道数 | 现有引擎/适配器文件 | 是否已被 KS 用过 | 可批量性 |
|---|---|---|---|---|
| `std.samr.gov.cn` 全国标准信息公共服务平台 | **15** | `src/core/update/channels/std_samr_hb.py` | **部分**：只打了 `/hb/search/hbPage`（1 条）| **高**：`<子栏目>/search/<子栏目>Page` 同构，已有 3 处实测记录 |
| 各省地方标准遗留系统 | **36** | 无 | 否 | **无**：36 个互不相同的系统 |
| 开源工具仓库 | 20 | 无 | — | **不该接**（非发布源；`category='tool'` 共 24 条，另 4 条 URL 是 `(not found)` 之类、没有主机） |
| `col/col<数字>/index.html` CMS | **8** | 无 | 否 | **中（不确定）**：URL 同形，但跨 4 个主体 |
| `*.sacinfo.org.cn` 标准平台族 | **6** | `hbba.py` / `dbba.py`（共用基类 `_SacinfoQueryAdapter`） | **是**（2 条） | **中**：同平台、子系统不同 |
| 其他 `samr.gov.cn` / `sac.gov.cn` 站点 | 6 | 无（`www.samr.gov.cn` 4 条、`www.sac.gov.cn` 2 条） | 否 | 低：栏目各异 |
| `flk.npc.gov.cn` 国家法律法规数据库 | 5 | `laws_db.py` | **是** | 高（已接，属去重） |
| `www.gov.cn` 中国政府网 | 5 | `govcn_announce.py`（只查 `sousuo.www.gov.cn/search-gov/data` JSON，**不抓 www.gov.cn 页面**） | **否**（页面栏目未接） | 低（4 个不同栏目） |
| `www.mem.gov.cn` 应急管理部 | 4 | `mem_gov.py` | **是** | 中（扩栏目） |
| `www.mee.gov.cn` 生态环境部 | 4 | `mee.py` | **是** | 中（扩栏目） |
| `www.mohurd.gov.cn` 住建部 | 4 | `mohurd.py` | **是**（只 `/gongkai/zc`） | 中（`/gongkai/fdzdgknr/bzgg` 是另一栏目） |
| `openstd.samr.gov.cn` 国标全文公开 | 2 | `official_gb.py` | **是** | 高（去重） |
| `www.ttbz.org.cn` 团体标准平台 | 2 | `ttzb.py` | **是** | 高（去重） |
| 其余（一站点一条） | 145 | — | — | 逐站 |
| **合计** | **262** | | | |

**说明"是否已被 KS 用过"的判据**：拿 `ADAPTER_CLASSES` 里 13 个类的源码里出现的 URL 主机+路径，与台账 URL 做前缀比对。13 个适配器实际打的端点只有这些：`openstd.samr.gov.cn/bzgk/std/std_list`、`flk.npc.gov.cn/law-search/search/list` 与 `/detail?id=`、`sousuo.www.gov.cn/search-gov/data`、`www.mem.gov.cn/fw/flfgbz/bz/bzgg/`、`std.samr.gov.cn/hb/search/hbPage`、`hbba|dbba.sacinfo.org.cn/stdQueryList`、`ndls.cnis.ac.cn/api/standard/list`、`www.mohurd.gov.cn/gongkai/zc/wgk/`、`www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/`、`www.mee.gov.cn/ywgz/fgbz/bz/` 与 `datacenter.mee.gov.cn/websjzx/report!list.action`、`www.cssn.net.cn/api/standards/list`、`www.bing.com/search`（`web`，已从链上摘除）。

**注意一个容易误判的点**：`std_samr_hb` 用的是 `std.samr.gov.cn`，`std.samr.gov.cn` 上那 15 条里 14 条**没被覆盖**——不是"这个平台接过了"就等于"这个平台的子栏目都接了"。

---

## 四、单条验证路径

### 4.1 A 组（走 KS 适配器）—— 一条 1~8 秒，代码 5 行

**路径一（不写代码、走已有 API，最快）**

```powershell
# 只探一条，不落库
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/channels/probe `
  -ContentType 'application/json' -Body '{"ids":["ch:std_samr_hb"],"persist":false}'
```

- 端点：`POST /api/v1/channels/probe`（`routes_channels.py` → `cp.probe_channels(ids, persist)`）。
- 目标来自 `src/core/update/channel_probes.json`；**没配目标的渠道不会被探**，只会出现在 `without_target` 里。
- 判据（`_classify`，集中在一处）：`state` 取值 + `error_code`。`ok` 要求"HTTP 200 **且** 命中 `expect` 文本锚点 **且** `<a>` 数 ≥ `min_links`"三者同时满足；只配 `url` 不配任何期望 ⇒ `unknown/no_anchor_configured`（**如实说没做语义判定，不算通过**）。`403/412 → down/blocked_by_waf`、`429 → suspicious/rate_limited`（限流不算死）、`404/410 → down/endpoint_gone`、`5xx → down/server_error`；**HTTP 200 但正文 `code>=400` 或含"系统异常/不支持/失败/错误" 也是 `down/api_error`**。
- 时间：`PROBE_TIMEOUT_S = 20.0` 是单次上界。

**路径二（验"我们的适配器真能解析"，这才是接线的验收口径）**

```powershell
@'
from src.core.update.channels.std_samr_hb import StdSamrHbAdapter
# 不传 transport ⇒ default_transport()：优先 curl_cffi 模拟浏览器 TLS 指纹
# （base.py 模块注释：ANOM-002 gov 三站点 JA3 级 WAF 掐 Python 握手）；
# curl_cffi 不可导入时回退 httpx 并打一条 WARN。要指定就传 HttpxTransport()。
r = StdSamrHbAdapter().probe("AQ 3028-2008")
print(r.found, r.latest_version, r.legal_status, r.effective_date, r.evidence_url)
'@ | python -
```

- 调用：`<Adapter>(transport=<...>).probe(standard_no, standard_name="")`（接口冻结，`@abstractmethod`）。
- 依赖很轻：`base.py` 只 import 标准库 + `src.core.exceptions`，这条路径**不碰库、不起引擎**。
- 判据三件齐：`found is True`；`latest_version` 非空（适配器解析出了号）；`legal_status in LEGAL_STATUSES`。再加 `raw["http"] == 200`。
- **反面样板（别重复）**：`web` / `govcn` 两根兜底棒曾经"在链上但只解 mock 的 dict" ⇒ 真实 HTML 下**恒 miss**。所以判据不能只看 `found`，要看"喂真响应时能不能取出字段"。
- 时间：单条 = 1 次 GET（`ndls` 要 2 次：搜索 + 详情）。`DEFAULT_TIMEOUT_S = 30.0` 是上界；`routing.py` 的实测注释给了两个真实参考：`ndls` 1.2s、`govcn` 未命中时见过 7.1s。`std_samr_hb` 另有 `PAUSE_S = 1.0` 的调用间限速。⇒ **一条按 1~8 秒估，30 条约 1~3 分钟。**

### 4.2 B 组（走 gov-qa 适配器）—— 秒级，但**对 262 条的覆盖是 0**

保留路径写法，供将来真的要接"互动/留言"类渠道时用：

```powershell
@'
import sys; sys.path.insert(0, "tools/gov-qa")
import adapters, httpx
mod = adapters.load("nat-nea")           # key 来自 ADAPTERS 字典
client = httpx.Client(timeout=30, follow_redirects=True, verify=False)
rows = mod.harvest(client.get, limit=1)  # 契约：harvest(fetch, *, limit=None) -> list[dict]
print(len(rows), list(rows[0])[:8] if rows else None)
'@ | python -
```

- 载入：`adapters.load(key)` → 模块（延迟导入）。
- 调用契约：`harvest(fetch, *, limit=None) -> list[dict]`；`fetch` 是可注入的 `httpx.Client.get` 形状（`fetch(url, **kw)`）。
- 判据：`len(rows) >= 1` 且行里有该适配器的字段（`title/url/asked_at` 等，各适配器字段名不同）。
- 时间：IGI 类 1~3 次请求，秒级（`_igi_common.harvest_igi` 是分页循环，`limit` 卡住就停）。
- **但这条路修不了 262 条里的任何一条**（§3.1 的两次核对）。

### 4.3 接完一条之后还差什么（别漏）

1. `channel_probes.json` 加目标（`url` + `expect` 或 `min_links`，`expect` 必须是**实测看到过**的字符串）。否则探针不探它，`state` 永远是上一轮的值。
2. `POST /api/v1/channels/{id}/test-case` 配"已知文件"（`sample_url` + `expect_no`），再 `POST /api/v1/channels/{id}/test` 跑一遍 —— 这是唯一能回答"真东西拿不拿得到、认不认得出"的判据。今天 0 行，等于 286 条**一条都没过这道验收**。
3. 台账 id 必须是 `ch:<适配器名>`，`enabled=1`，`wiring != 'broken'`。
4. 名字要进 `routing._FALLBACK` / `_PREFIX_ROUTE` / 台账 `segments_json` 之一，否则"接好了但一个号都问不到"。

---

## 五、建议执行顺序

排序原则：**一批能吃多少条 / 风险多大**。风险的三档是现成的：`verification` + `state` + 有没有校准探针。

### 批次 0 · 先修 id 形状（不做，后面全白做）

- 内容：把 262 条的 `channel_id` 从 `ch:<类别>:<ULID>` / `seed:<文件>:<中文名>` 改成 `ch:<适配器名>` 的**规则**定下来（哪个字段承载"原调研名"——建议留在 `note`/`source_file`，别丢）。同时修掉 6 条 `ch:law:…` / `ch:std_hb:…` 的 `wired` 假状态。
- 成本：纯数据迁移 + 一条用例。
- 不做这一批的后果：A/C/D 任何一批接完，台账上仍是 `seed_only`，巡检仍不问它。

### 批次 1 · A 组 19 条（去重，0 行新代码）

- 一个能吃 19 条，风险≈0（站点已被适配器覆盖），动作是合并/删除重复登记。
- 顺带收益：台账从"286 条 = 13 条能干活"的假象里纠正过来。

### 批次 2 · C1 + C3 + C4 = 32 条（收益最大的一批）

- **先 C1（14 条）**：一个参数化适配器吃 `std.samr.gov.cn` 全部子栏目，加上已有 `/hb` 共 15 条 —— 这是**单一适配器覆盖条数最多**的一族，且有 3 处实测记录背书（`nocGBPage`、`tbPage`、`gbAdvancedSearchPage`）。其中 6 条已有校准探针、`state=ok`，14 条里 13 条 `ok`、1 条（`nocTB`）研究期就验出是坏的。
- **再 C3（8 条）**：`col/col<数字>` CMS。5 条 `ok` 且带语义期望（浙江 3 条：`col1229836653` / `col1229577560` / `sft.zj.gov.cn` 的 `col1229247318`；江苏市监 `col78963`；山东市监 `col76510`），另 1 条 `ok` 但没配语义期望（广电总局 `col2081`），2 条 `suspicious` 且是**同一个 URL 的重复登记**（`zj.gov.cn/col/col1229019364`）。**先拿两条对比 HTML 的 `<meta generator>`/静态资源路径确认是不是同一套 CMS**——是，则 1 个适配器吃 8 条；不是，则退回 3~4 个薄适配器。
- **最后 C4（10 条）**：同站扩栏目（mem 1 / mohurd 3 / mee 1 / gov.cn 4 + 标准查询 1），本质是给已有适配器加分支，5 条已有校准探针。gov.cn 那 5 条 `govcn` 适配器帮不上（它只查搜索 API），要新写页面抓取。
- **C2 的 3 条本批不做**：`*.sacinfo.org.cn` 的另外三个子系统接口形状未核（§六 #2），3 条里 2 条 `suspicious`、0 条可开写 —— 投入产出比最差，留到 C1/C3/C4 做完再单独评估。

### 批次 3 · D 组里 42 条"已校准可开写"

- 判据最硬的一批：`channel_probes.json` 里有目标、实测 `state=ok`、且带 `expect`/`min_links`（即"页面形态确认过、内容真的发出来了，不是 JS 空壳"）。
- 风险：中（要写解析器，但不用先探）。建议按"同 host ≥2 条"打包（34 个 host 占 87 条，其中落在本池的会进一步合并成 10 来个适配器）。

### 批次 4 · D 组剩余 142 条（含 36 条各省地标）

- **注意：这批的第一步不是写代码、也不是"看台账 `state` 挑 ok 的"** —— 这 142 条**都没有探针目标**，它们的 `state` 是导入值（§1.5），拿它排序会把 79 条"看起来 ok 但从未探过"的混进来。第一步是**给它们配探针目标**（`channel_probes.json` 加 `url` + `expect`/`min_links`，`expect` 必须是实测看到过的字符串），跑一遍 `POST /api/v1/channels/probe` 拿到真 `state`，再决定写不写。
- 其中 36 条地方标准是 36 个互不相同的遗留系统（`LawQueryServlet` / `.aspx` / `.jsp` / `findLocalStandard.do` / IP:端口）。整个 `category='std_db'` 的 42 条里，台账 `verification` 是 **broken 26 / verified 12 / unverified 4**（这是台账列，不是我判的）——这 36 条是它的主体。
- 建议：**先确认是否已被 `dbba.sacinfo.org.cn`（地方标准信息公共服务平台）覆盖**。若已覆盖，这批应当像 A 组一样**去重而不是新写**；只有"dbba 没有的省份/栏目"才值得单独写。这一步没做之前，别按 36 条排期。
- 风险：高（逐站，且无族可借）。

### 批次 5 · T 组 24 条 —— 建议**不做**

- 非发布源，接进来会让"渠道数"继续虚高。正确动作是从 `update_channel` 迁出到"参考工具"清单，或至少 `enabled=0` 且不计入 `wiring` 统计。

### 一句话建议

**先做批次 0 + 1（数据，0 代码，19 条）→ 批次 2 的 C1（1 个适配器吃 14 条）→ 批次 3 的 42 条。** 不要从 D 组的 36 条地方标准开始：条数看着多，却是 36 份独立工作，而 `std_db` 那 42 条在台账里本来就有 26 条标着 `broken`。

---

## 六、不确定的地方

| # | 不确定的事 | 依据 / 为什么没定 |
|---|---|---|
| 1 | `col/col<数字>/index.html` 的 8 条**是不是同一套 CMS** | URL 语法完全同形（`/col/col<数字>/index.html`），但分属浙江（5）、江苏市监、山东市监、广电总局（1）四个主体；其中浙江 3 条 + 江苏 + 山东 = 5 条探针 `ok` 且带锚点、浙江 2 条 `suspicious`。**判法**：取两条 HTML 的 `<meta name="generator">` 或静态资源路径对比即可定；本次是只读边界（不抓网），未做。 |
| 2 | C2 的 3 个 sacinfo 子系统能否复用 `_SacinfoQueryAdapter` | `hbba`/`dbba` 打的是 `POST /stdQueryList` 表单；`std.sacinfo.org.cn/PCNoc/queryAll`、`tc.sacinfo.org.cn`、`org.sacinfo.org.cn/tcrm/…` 是三个不同子系统。同域名 ≠ 同接口。3 条里 2 条 `suspicious`、1 条 `ok`。**未核实接口形状。** |
| 3 | 184 行的 `state` **是谁写的、什么时候写的** | 已经确定"**不是** `record_probe` 写的"（`last_try_at` 全为 NULL，而 `record_probe` 任何状态都推进它；递归 grep 全源码，写 `state` 的只有那一处）。**但写入者未查到**——没查 `event_log`、没查一次性迁移/回填脚本、没查 git 历史。这 184 行里 79 条是 `ok`、53 条是 `down`，"79 条 ok"目前没有实测支撑。 |
| 4 | 36 条各省地方标准是否与 `dbba.sacinfo.org.cn` **重复** | `dbba` 是"地方标准信息公共服务平台"，已接；那 36 条是各省自建系统。二者内容是否有交集、交集多大，**未核**。若有交集，批次 4 的规模会显著缩小。 |
| 5 | `_was5_common.py` / `_igi_multi.py` 为什么没人 import | 全仓 grep `_was5_common` / `_igi_multi` 在 `tools/gov-qa/adapters/*.py` 里除自身外**零引用**。可能是历史遗留、也可能是动态 import，**未追 git 记录**。 |
| 6 | `WIRING` 元组里的 `user` 值 | 库里 **0 行**，代码里 `_new_user_channel_id` 生成 `user:<hash>` 形状。是设计预留还是从未启用，**未查**。 |
| 7 | `probe_url` / `probe_expect` 两列的历史用途 | 现状态是"可写、不可读"（只在两处字段白名单里）。是否曾经被读过、什么时候废掉的，**未查 git 记录**。本报告只断言"今天没有代码读它们"。 |
| 8 | `channel_repo.upsert_channel` docstring 的 id 约定与数据不符 | docstring 写 `seed:<源文件>:<序号>`，实际是 `seed:<文件名>:<中文名>`。是文档落后还是数据违规，**未查**。 |
| 9 | 262 条里"报名但不属于渠道"的边界 | 我只按 `category='tool'` 判出 24 条非发布源。另有若干条是**站点首页**而非栏目（如 `https://sft.sh.gov.cn/`、`https://www.cnis.ac.cn/`），接首页的价值低，但"首页算不算渠道"没有明确定义，**未逐条判**。 |
| 10 | A 组 19 条里"同服务不同端点"的算不算已覆盖 | `laws_db` 那 4 条中只有 1 条是适配器真正打的端点；另外 3 条（详情/枚举字典/首页聚合）是兄弟端点。我把 4 条都算进 A，口径是"同一服务、同一适配器所在站点"，**这个口径是我定的，不是代码里写死的**。 |

---

## 七、复算命令（全部只读）

```powershell
# 前置：UTF-8 输出（否则中文名会乱码）
$OutputEncoding=[Console]::OutputEncoding=[Text.Encoding]::UTF8; $env:PYTHONIOENCODING='utf-8'
```

**① 总账 / wiring × channel_id 形状**

```powershell
@'
import sqlite3
c=sqlite3.connect("file:var/data/database/knowledge.db?mode=ro",uri=True)
for r in c.execute("select wiring,count(*) from update_channel group by 1 order by 2 desc"): print(r)
print("-- seed_only 的 id 形状 --")
import collections
q=("select channel_id from update_channel where wiring='seed_only'")
def shape(cid):
    if cid.startswith("tool:"): return "tool:<名>"
    if cid.startswith("seed:"): return "seed:<文件>:<名>"
    if cid.count(":")>=2: return "ch:<类别>:<ULID>"
    return "ch:<名>"
for k,v in collections.Counter(shape(r[0]) for r in c.execute(q)).items(): print(k,v)
'@ | python -
```

**② 262 条里有几条能取到 ADAPTER_CLASSES 里的名字**（§〇 的结论由这条命令支撑）

```powershell
@'
import sqlite3
AD={"official_gb","web","govcn","laws_db","mem_gov","std_samr_hb","hbba","dbba","ndls","mohurd","ttzb","mee","cssn"}
c=sqlite3.connect("file:var/data/database/knowledge.db?mode=ro",uri=True)
n=sum(1 for (cid,) in c.execute("select channel_id from update_channel where wiring='seed_only'")
      if cid.startswith("ch:") and cid[3:] in AD)
print("seed_only 能对上适配器名:",n,"/262")
n=sum(1 for (cid,) in c.execute("select channel_id from update_channel where wiring='wired'")
      if cid.startswith("ch:") and cid[3:] in AD)
print("wired 能对上适配器名:",n,"/13")
'@ | python -
```

**③ 探针目标覆盖率（`channel_probes.json` vs 台账）**

```powershell
@'
import json,sqlite3,collections
t=json.load(open("src/core/update/channel_probes.json",encoding="utf-8"))["targets"]
c=sqlite3.connect("file:var/data/database/knowledge.db?mode=ro",uri=True)
rows={r[0]:(r[1],r[2]) for r in c.execute("select channel_id,wiring,state from update_channel")}
print("targets:",len(t)," 全落在台账:",set(t)<=set(rows))
cnt=collections.Counter((rows[k][0],rows[k][1]) for k in t)
for k,v in sorted(cnt.items()): print(k,v)
ready=sum(1 for k in t if rows[k][1]=="ok" and
          ((t[k] or {}).get("expect") or int((t[k] or {}).get("min_links") or 0)>0))
print("ok + 带语义期望:",ready)
'@ | python -
```

**④ 三列空值核对**

```powershell
@'
import sqlite3
c=sqlite3.connect("file:var/data/database/knowledge.db?mode=ro",uri=True)
for col in ("probe_url","probe_expect","segments_json"):
    print(col,"非空:",c.execute(f"select count(*) from update_channel where {col} is not null and {col}<>''").fetchone()[0],"/286")
print("channel_test_case 行数:",c.execute("select count(*) from channel_test_case").fetchone()[0])
'@ | python -
```

**⑤ gov-qa 引擎覆盖数**

```powershell
@'
import os,re,collections
base="tools/gov-qa/adapters"
files=[f for f in os.listdir(base) if f.endswith(".py") and not f.startswith("_")]
engines=[f for f in os.listdir(base) if f.endswith(".py") and f.startswith("_") and f!="__init__.py"]
use=collections.defaultdict(list)
for f in files:
    txt=open(os.path.join(base,f),encoding="utf-8",errors="replace").read()
    for e in engines:
        if re.search(r'\b'+re.escape(e[:-3])+r'\b',txt): use[e[:-3]].append(f)
print("非_适配器:",len(files))
for e in sorted(engines,key=lambda x:-len(use[x[:-3]])): print(f'{e:32s}{len(use[e[:-3]])}')
'@ | python -
```

**⑥ gov-qa 里有没有法规/标准栏目（B 组是否为 0 的判据）**

用 grep 工具，路径 `tools/gov-qa/adapters`，include `*.py`，模式：

```
flfg|zcfg|zhengce|bzgk|bzgg|fggb|dfxfg|gongbao|zhengcelibrary
```

⇒ 本次结果：**No matches found**。

**⑦ KS 侧站点族条数**

```powershell
@'
import sqlite3,urllib.parse,collections
c=sqlite3.connect("file:var/data/database/knowledge.db?mode=ro",uri=True)
def h(u):
    try:return (urllib.parse.urlsplit(u).hostname or "").lower()
    except Exception:return ""
rows=list(c.execute("select url from update_channel where wiring='seed_only'"))
cnt=collections.Counter(h(r[0]) for r in rows)
for x,n in cnt.most_common(15): print(n,x)
print("distinct host:",len(cnt))
'@ | python -
```

**⑧ `state` 是不是真探针写的（§1.5 的结论由这条命令支撑）**

```powershell
@'
import sqlite3
c=sqlite3.connect("file:var/data/database/knowledge.db?mode=ro",uri=True)
for row in c.execute("""select state,
        case when last_try_at is null then 'last_try_at NULL' else 'last_try_at 有值' end k,
        count(*) from update_channel group by 1,2 order by 1,2"""): print(row)
print("有 last_try_at 的行:",c.execute("select count(*) from update_channel where last_try_at is not null").fetchone()[0])
print("last_ok_at 非空:",c.execute("select count(*) from update_channel where last_ok_at is not null").fetchone()[0])
'@ | python -
```

判据来自 `channel_repo.record_probe` 的 SQL 注释：「`last_try_at` **任何状态都推进**（含 unknown）」。`last_try_at` 为 NULL ⇒ 这条行从没走过探针。

**⑨ `verification` 分布**

```powershell
@'
import sqlite3
c=sqlite3.connect("file:var/data/database/knowledge.db?mode=ro",uri=True)
for w in ("seed_only",None):
    q="select verification,count(*) from update_channel"+(" where wiring='seed_only'" if w else "")+" group by 1"
    print(w or "全部", c.execute(q).fetchall())
print("std_db:",c.execute("select verification,count(*) from update_channel where wiring='seed_only' and category='std_db' group by 1").fetchall())
'@ | python -
```

---

*本方案由只读调查生成：未改任何文件（本文件除外）、未跑引擎/门禁/pytest、未抓外网。所有数字来自 `var/data/database/knowledge.db`（只读）、`src/core/update/channel_probes.json`、以及 `grep`；未 import 引擎模块，`ledger_chain` 的判据是手工复算。*
