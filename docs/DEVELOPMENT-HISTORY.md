# KnowledgeStation 开发历程简史

> 一句话版：**2026-08 从零建成引擎（phase 1~14，14 天）→ 2026-09-05 起 DSH 秽土转生（旧前端退役，插件一体形态）→ 2026-09-12 批 0~10 整改战役收官 + Electron 正式退役。**
> 详细技术现状见 `ENCYCLOPEDIA.md`；本文只讲"怎么走到今天"。

## 一、前史：引擎从零到 phase 14（2026-08-19 ~ 09-02，无 git 时期）

项目在无版本控制状态下从零建成：T00 契约冻结（SSE 顺序/六通道枚举/schema）→ 存储/检索/解析/核验逐层落地 → phase 1~14 全部完成，测试基线从 24 一路只涨不跌到 513。

关键节点：

- **08-22/23**：MVP 跑通（MinerU 解析、六通道检索、首批 dbg 调试脚本今已清剿）；创建 ENCYCLOPEDIA 单入口百科。
- **08-24**：「更新」模块 13 阶段流水线交付（`pipeline/` 目录全记录）；官方法规来源管线（flk + gov.cn）；三个异常（假绿终态/JA3 TLS 指纹拦截/mock 与真机脱节）全部闭环，沉淀"真实站点先于 mock"铁律。
- **08-25**：高亮错位根因终修——span 坐标顶部/底部原点判定，契约修复必须同步迁移存量数据。
- **08-26**：全库语料获取方案立项；write_queue 消费端接线。
- **08-27**：标准状态巡检渠道实测定型（cssn 单渠道覆盖国标 1~6 类）。
- **09-01/02**：排版还原批次（page_breaks/figure_html）；loop2 四层收敛环设计。

## 二、DSH 秽土转生（2026-09-05 ~ 09-11）

引擎与数据全部保留，只换"壳"与"交互通道"：DSH 会话=左栏问答，better-sidebar=右栏工作台。

- **09-05**：P0 桥打通（插件骨架 + 懒 spawn 引擎 + ks_ping/ks_resolve_clause 工具）。
- **09-06**：P1 信任闭环——`ks_answer` 三段式取证答案 + 蓝链点击 → PDF tab 跳页高亮（真机验证）；收藏 tab；设置栏目；每日巡检接线；`/效力报告`。
- **09-08**：API 配置栏目；深度解析通道语义修订（云优先本地兜底）；两轮 verifier 审计整改（18 条 /ks 路由信任栅栏）。
- **09-09/10**：PDF 查看器铺满 + 悬浮目录（四轮推翻后定案）；「查法规模式」经六轮 verify_rollout 迭代后按业主反馈改为斜杠命令 `/forensic` `/bookmarks`。
- **09-11**：R27 入库 Dry-Run 预览红线落地；**凭据命名空间化事故**——裸全局名 `DEEPSEEK_API_KEY` 遮蔽 DSH 凭据层（进程环境快照冻结 + 优先级最高 + 只读 → 模型设置页密钥框被置灰），业主裁决"**不要动系统层**"，修复为 `KS_LLM_API_KEY`；宿主停摆 3.5 小时事故（看门狗裸拉起 12 次全灭——"已经有自动恢复"是自我感觉）。

## 三、整改战役批 0~10（2026-09-12，一天内完成）

verifier 全面审计产出 25 项问题清单 → 5 verifier 编制方案 → verify_select + verify_compare 终裁"止血优先·风险递减"方案：

| 批 | 一句话 | 关键结果 |
|---|---|---|
| 0 | git 安全网 | `git init` 仓库本地身份 + .gitignore 扩容，首提交 tag `baseline-792` |
| 1 | 密钥安全网 | 快照备份纳入 secrets.json 密文；读者排查工具 |
| 2 | 凭据迁移执行 | 注册表 → DPAPI 加密存储搬完删净；两遍式缺陷修复；**遮蔽事故正式关闭** |
| 3 | 引擎守护 | idle 30min + 查法规 keepalive + stale 重拉留档；抓到并发幽灵引擎缺陷 |
| 4+5+6 | SCNET 读链 + 文档漂移同步 + LLM 需求分析 | 注册表三键清零；8 处文档漂移清剿；"档位 C 零内嵌"定稿 |
| 7 | 安全加固 | 崩溃注入测试；OCR 出网审计缺口补齐；KS_BACKUP_DIR |
| 8 | **Electron 退役（业主拍板）** | "以后把 DSH 整个打包成 EXE，本项目不单独打包"→ 删 618+ 文件、卸 644 npm 包、门禁重定义（tsc -p plugin/client），当场清偿 type 债 |
| 9 | 真实巡检 + 种子入库 | tier1 全库 24 本巡检全绿；R27 预览真机 egress:"none" 确证零外发 |
| 10 | 清障收尾 | 46 个调试脚本归档 scripts/archive/；120s 超时契约 + fastembed 冷启动写入文档 |
| — | 收官后 | 异步批量预览（万级）三半边交付；勘误"复活币≠重启键"（8 处修正） |

## 四、冗余清剿战役（2026-09-12，本次）

5 个 verifier（文档/引擎代码/插件前端/脚本工具链/var 数据）并行全库扫描 + 主对话交叉核实：

- **删除**：git 跟踪僵尸约 120 文件（scripts/archive 48、stdscan/fix-candidates/_channel_probe 探针、.browser4-cli 267 文件工具快照移出、watcher.py 不可达死代码、7 个零引用函数、eval 消融产物等）；物理清理 var/ 约 3.1GB（univer-upstream 154MB、browser4-runtime 258MB、wheels_local 2.42GB、50 个 dbg 脚本、test_docs 43.6MB）。
- **抢救**：30+ 份旧文档的独家结论（决策台账/渠道实证/消融结论/契约增量）先并入百科再删原件；DSH_REINCARNATION 154KB 台账压缩为本文。
- **修复**：main.py `_get_ocr` 笔误（OCR 预热从未生效）；测试白名单 2 幽灵条目。
- **关键否决**（verifier 交叉核实价值体现）：`wenjianmulu/` 与 `var/fixtures/测试法.pdf` 是生产库 file_path 指向的**活数据**不删；`eval/golden/` 是活门禁三件最小集不删；`smoke.mjs` 与 engine-guard 不等价（真机 vs 离线）不删；`restore_package.py`/`_stdparse.py` 是活依赖不删。

## 五、全程贯穿的纪律

1. **每个特性/修复/重构必须让 verifier 参与**（业主硬纪律）——本仓库的每次大改动都有多轮审计留痕。
2. **测试基线只涨不跌**：24 → 173 → 312 → … → 513 → 792 → 828 passed + 3 skipped（当日口径；后续演进见 §八）。
3. **诚实标注**：假绿必判 failed；未做的写"明确未做"；能力宣称挂真机证据。
4. **绝不动系统层**：不写注册表、不改全局环境变量、不用 --global git 配置。
5. **数据/代码分离**：运行产物写数据区（%APPDATA%），代码树零运行产物。
6. **派复核前先冻结区间**（2026-09-18 追加；材料平面战役第 3 次复发后硬化的规矩）：
   给 verifier 的任务书要写**冻结的端点**，不是"最近 N 个提交"；派单**之前**做两件事——
   ① `git tag verify-freeze-<批次>` 打在要复核的 HEAD 上（复核期间主检出继续前进也不影响它）；
   ② 用 `git rev-list --count <base>..<frozen>` **数出**提交条数写进任务书（不要凭印象写"8 个提交"）。
   理由：b9/b10/b12 **连续三轮**都出现"任务书说的区间与事实不符"（条数不对、或声称含某提交而实际
   不含——它的代码在父提交里），而主检出在复核期间又前进了若干提交 ⇒ 复核对象的身份**不确定**，
   报告里那句 CONFIRMED 到底确认的是哪份代码就说不清。这是**流程**纪律，不进自动门禁（没人能自动
   判断任务书写得对不对），但它比任何一条断言都便宜。
   **2026-09-18 再补一句（复核 b13 的 INFO-1，当场就撞上了）**：verifier **必须在冻结提交的
   *提取树*上验证**（`git archive <frozen> | tar -x -C <tmp>` 或 `git worktree add`），
   并在报告**首尾各记一次 `git rev-parse HEAD` + `git status --short`**。
   理由：b13 复核期间主检出又被另一个工作流（同一晚的 §10.79）改了 5 个文件，b13 第一次
   在本工作树上普查路由量到 **95 条 async 端点**、与文档写明的 **115** 不符——**差点报出一个假的
   REFUTED**；它改用提取树后逐字复现。**"在同一个目录里边改边验"是双向污染**：施工方污染
   复核对象，复核方的变异也污染施工方的工作树。

---

*历史细节的原始记录存在于 git 提交历史（`git log`）与术前备份 `D:\AI\zcode-backups\`。本文之外**不存在**其他历史档案库（旧文档宣称的 `docs/_deprecated/` 从未存在）。*

## 六、依赖声明修复（2026-09-13，冗余清剿遗留项收尾）

双 verifier 审计（依赖声明 + 端点消费图谱）+ 主对话交叉核实，三项修复：

1. **`.gitignore` 吞生产文件事故**（审计意外发现，最高优先级）：`exports/` 无锚定规则连带忽略 `src/core/exports/` 整目录——**5 个活生产文件**（报表导出/效力报告/Office 回环/反链）从未进过 git，`git log --all` 历史为空。新克隆必 ImportError。修复：锚定 `/exports/` + 抢救入库。
2. **pyproject 依赖缺陷**：删 `python-multipart`（全仓 0 import、120 端点无 multipart 表单）；`httpx` 从 dev 上提 dependencies（生产 3 文件 8 处使用）；新增 `requests`/`urllib3`/`beautifulsoup4`（knowledge/law_source 模块级裸 import，此前仅靠 mineru 传递依赖偶然满足）；新增 vision/proc/wincom 三个 optional extras（守卫内可降级依赖显式化）；`packages.find` 补 include + `src/__init__.py`（此前 find_packages 返回空=零打包）。mypy 的删而复立见下节（同日另一批次把它真正建立了起来）。
3. **端点消费图谱精确化**：替换 §17 "约 55 个零前端调用"粗估（实为把 54 个 TEST-ONLY 误并入）→ 精确四分类 LIVE-PRODUCT 44 / TEST-ONLY 54 / ZERO 22 / SCRIPT-ONLY 0；ZERO 22 条逐条复核均为"未接线"而非废弃残留，统一 KEEP。ENCYCLOPEDIA §10.2 端点表修 4 处漂移（3 条假路径 + 1 条 SSE 误标）。

## 七、mypy 门禁建立 + 图/公式/表图端点接线（2026-09-13，双遗留项清账）

上节两项遗留的当日清账（均在 0f90972 之上，verifier 纪律全程）：

1. **mypy 门禁从无到有（REQUIREMENTS 硬指标 #2 的 Python 半兑现）**：安装 mypy 2.3.1 → `[tool.mypy]` 非 strict 保守口径（check_untyped_defs / no_implicit_optional / warn_redundant_casts；fitz/jieba/mineru 系/curl_cffi/openai SDK 等无 stub 包 ignore_missing_imports）→ 基线 **126 错误分 7 轮清零**（126→95→82→47→10→0，120 文件全绿）。每处 `# type: ignore[code]` 带行内中文理由注释；`mypy>=1.10` 回 pyproject dev extras；`npm run typecheck:py` 脚本入 package.json；旧主计划 v4.3 L2929（该文档已于 2026-09-19 大清洗中移除）注记改"已建立"（`--strict` 愿景降级为非 strict 起步——~612 处未注解面按 warn 只增不减消化，strict 另立里程碑）。
   - **真实缺陷战果**（超越注解噪音）：announce.py `export_announce_xlsx` 用 `Path` 未导入（**每次 Excel 导出必 NameError 的 P1 崩溃**）；server.py 三处 `_p` int→str 循环变量复用 + 死 `_lo/_hi` 块；effect_report 循环变量 `c` 遮蔽 COLOR_ORDER 键；write_queue `int(cur.lastrowid)` 无 None 守卫；figure_redraw `k`（ndarray 核）与去重循环 `k` 同名类型漂移；office_roundtrip 条款并发删除 None 崩溃（加 None 守卫）；bulk 六处 `load_batch` 返回 None 撒谎路径（`_reload` assert 化）；supervisor ChildHandle Protocol 只读属性化。
   - pytest 回归 828+3 不变（annotation-only + assert 守卫，零行为变化）。
2. **图/公式/表图三端点 ZERO→LIVE 接线**：引擎 `/figure/{fig_no}`｜`/formula/{fno}?clause=`｜`/table-image/{page}/{idx}`（2026-09-02 实现完备，旧 App.tsx 退役后无 GUI 消费者）。
   - **host**：`plugin/src/docimage.js` 前缀路由 `/ks/doc-image/*`（经 guardWebServer 统一栅栏；Bearer 只在 host→引擎段；引擎 404 透传=占位隐藏契约；X-Frac-* 三头逐字转发；dpi 72~300 钳制；401 会话轮换重试一次）。`engine.js` 新增 `apiGetBytes`（二进制 GET，不走 text() 腐蚀字节）。
   - **client**：`api.ts` 新增 `fetchDocClauses`（信封 `{code,data:{clauses[]}}` 下钻——E2E 实测修正）与 `fetchDocImage`（同源代理 → objectURL + frac 头）；`KsEvidenceTab` 新增「📄 正文 / 📑 PDF」视图切换；新组件 `KsDocTextView`：content_html **结构白名单消毒**（剥壳上移节点也必被过滤——过滤不变量=「属性过滤只在节点被 pop 时做」；剥 script/on*/外链 src；img.class 必须存活——接线选择器按 class 命中）→ fig-embed / table-embed / katex-formula 占位 effect 拉图接线（404 隐藏/公式回退线性文本），按 page_start 聚合页块导航与 PDF 翻页双向联动。**asset-embed 本批不接线**（124 处只显示 alt 文本——assets 走 sha256 白名单端点，留待后续批次）；table-embed 现网语料 0 生产者（代码层链路已通，数据层待带图表格语料入库）。
   - **验证**：新增 `smoke-docimage.mjs` 24 断言（路径解析/栅栏拒非回环/字节与 X-Frac 保真/404 状态码透传+本地信封/401×2→502/dpi 钳制/apiGetBytes 字节保真）与 `smoke-sanitize.mjs` 13 断言（消毒器回归——P0 级：剥壳上移 img 的 onerror 必被剥、fig/table-embed class 必存活；P1 级：src 直剥无断头属性、javascript: 随壳剥除、script 文本全丢、正文文本保全）入 `npm run smoke`（10→12 段）；**真机 E2E**（真引擎真语料 GB/T 34406）：figure 1 SVG 矢量重绘 2601B、A.1 PNG 44658B、formula 1@3.7 PNG 3007B 带 X-Frac 三头、无图 404、clauses 31 条全带占位（fig A.1/A.2 + 式 1@3.7/2@3.8）。
   - **verifier 两轮**：第一轮 REJECT（消毒器剥壳上移节点漏过滤=P0-1 XSS 绕过；img.class 被白名单剥掉=P0-2 figure/table-image 断头接线）→ 重写过滤不变量 + class 入白名单 + 补 smoke-sanitize 回归 → 第二轮 APPROVE（真机全库 31 文档 3705 条款普查：非白名单标签 0、fig-embed 92/katex 510/asset-embed 124/table-embed 0；E2E 复证 200 PNG+frac 头）。复审清账 7 项同步落实（P2-11 就地 revoke、404 措辞统一、data-ks-src 声称清除、门禁计数 12 段、asset-embed 取舍显式化）。
   - 门禁扩容四件套→**五件套**：pytest 828+3 ｜ smoke 12 段 ｜ verify:commands 15/15 ｜ tsc 0 错 ｜ **mypy 0 错（新）**。消费图谱 LIVE 44→47、ZERO 22→19。

## 八、水印污染根因 + 官方侧边栏迁移 + 审计缺口清账（2026-09-16）

会话起点 `1143 passed + 2 failed`，会话内陆续扩到 **`1214 passed / 3 skipped / 0 failed / 1 xfailed`**（mypy 122 文件 0 错、tsc 0 错、smoke 11 段 PASS、verify:commands 15/15；那 1 条 xfail 见 §八.3 末的"第二个所有者"）。本段提交：`0ecd1af` `28a86da` `9c851e0` `a808dbb` `7caf9b2` `df4dc41` `5d916cc` `aaefeaf` `c21a332` `53cdf81` `390c434` `5c93a46` `e41e0d5` `a07f40c` `c9898a1` `c69d94a` `a3083f5` `ddcae1f` `0cd52e7` `78a0a1f`。

1. **时间炸弹测试（`0ecd1af`）**：`test_update_inspector` 两条红。根因不在代码——测试用**固定** `T0 = 2026-08-24 12:00Z`，而 fixture 用**墙钟** `datetime('now','-30 days')` 回拨，故 `today > T0+23d` 后必然错位。`git stash` 在 HEAD 复现同样两条红 → 判定**先于本次改动既存**。修复：`_make_iso(dt)` 统一 sqlite 格式 + 两处回拨都锚定 `T0`。
2. **引擎四项（`28a86da`）**：
   - **D2 审计红线缺口**：`/ks/answer` 在发起真实云端 LLM 调用时**零持久化**（无 debug_dump、无 record_egress），与其余出网路径不对称 → 补 `_write_ks_answer_dump` + `record_egress`。
   - **`versioning.compare_docs` 的 `removed` 同义反复**：`idx_b` 的 revision id 永不可能出现在 `idx_a` 里，故 `removed` 实际上等于"全部旧条款"。改用 `paired_a` 配对。
   - 未解析引用可观测性；`mineru_cloud` 显式 `api_key` 参数 + 429 退避重试（`_retried_429`，修竞态）。
3. **水印污染——本会话最大发现（`df4dc41` 所有者层修复 / `5d916cc` 回填根因 / `53cdf81` FTS 同步）**：
   - **根因**：`pypdf_backfill.py` 的 OCR 数字回填逐页把整页文本覆盖进 clause `content_text`，**无终止锚点** → 页面页眉、页脚、盗版站点水印随正文一同写进条款正文。**不是**原始 PDF 解析带进来的。
   - **实测规模**：19,981 条 `content_text` 补丁，**100% 出自该回填**；其中 **14,906 条（74.6%）** 携带盗版页脚/页眉；**原文 0 条**。Aspose 水印 12,614 条，**11,841 条落在前 800 字符内**——而 `deepseek_client.py:53` 正是逐字取 `content_text` 进证据提示词（仅过 `weave_meaning_marks`）。
   - **修复两层**：所有者层 `text_utils.strip_watermark_lines` 扩到四类 token 家族（`_RE_WM_TOOL` / `_RE_WM_HEADER` / `_RE_WM_HEADER_TAIL` / `_WM_TOKENS`）+ `pypdf_backfill` 增结构终止锚点（表/图/附录/页眉/水印）+ 长度护栏 `_hi = max(n*3.0, n+400)`；存量层 `scripts/repair_patch_watermarks.py`（默认 dry-run，`--apply` 批量提交 900 行）。
   - **FTS 同步缺口**：回填写库路径改文本后 FTS 未跟随 → `pypdf_backfill` 内补 `_reindex_fts()`（只重索引 FTS，**不动向量**），与写库同事务。
   - **修后实测**：所有者层清掉 14,852/14,904 = **99.7%**；全库长度差 −12…−102，纯水印样本族恰为 −78（纯水印行整行删除，未伤正文）。回归测试防的正是"过删"——首版行尾页眉正则把页码写成可选，立刻被 `应符合 GB/T 10029—2010` 的存活用例抓回。
   - **诚实边界**：污染**是否真的落进过实际出网记录——未观测到**。`debug_dump` 仅 1000 行且全为 egress，窗口 `2026-09-16 00:10:51 ~ 01:00:26`，**早于** 13:51+ 的入库时刻，故"零命中"不具信息量。判定依据是**代码路径必然性**，不是观察。
   - **清洗收尾实测**（2026-09-17 02:57）：`--apply` 跑完 —— **清洗 15,225 条 · FTS 重算 15,225 行**；收尾 dry-run 报"将清洗 **4** 条"。规模口径见 §八.3 的实测（权威口径 `strip_watermark_lines` 在**清洗前快照**上会改动 **15,524** 条；早先记的 14,906 用任何口径都复现不出来，已作废。Aspose 一族的 **12,614** 条精确复现，其中 **12,389** 条落在前 800 字符内 —— 而 `deepseek_client.py:53` 正是先 `weave_meaning_marks` 再**截断 800 字符**进提示词，即这 800 字符**就是**进模型的那一段）。
   - **⚠ 缺口（`78a0a1f` 已修）**：step ② 的行尾页眉判据原先只有"前导页码"一个特征，而**表格末格**恰好也是 `<裸数字> <标准号>`。实测清洗前快照：step ② 命中的 `页码+标准号` 尾共 **2,910** 处，其中 **2,904** 处是**该文档自己的**标准号（确是页眉，删得对），**6** 处引用**别的**标准（真实表格内容，涉 3 个条款）。生产库当时**未受损**（4 条候选都还在），但再跑一次 `--apply` 就会删掉。
     **修法是喂上下文、不是调正则**：`strip_watermark_lines(text, *, own_standard_no=None)` —— 传自家标准号后该族判据只吃**标准号相符**的页眉；`pipeline.build_clause_models`（签名里本就有 `standard_no`）与 `scripts/repair_patch_watermarks.py`（改 JOIN `doc_meta`）都已传。**比较键只取"号 + 年"**（`_std_key`）——这一步是被我自己的验证脚本逼出来的：最初按**整串**比较，于是 `own='GB／T 12041.1-2010'` 与页眉 `'1 GB 12041.1—2010'`（**页眉把 GB/T 印成 GB**）被判成"别人的标准号"而留下，**226 行真页眉漏删**；改用"号 + 年"后 226 → **0**，同时 6 条真误删仍被保住。
     **语料验证**（快照 19,981 条）：**不传**时与旧实现**逐字节相同**（差异 0 行、改动行数 15,524 == 15,524）；**传**上下文后改动行数 15,524 → **15,518 = 恰好少 6 行**，差异行分解 226 → 6 且全是"别人的标准号尾巴（正确保留）"，反查"自家标准号却仍保留" = **0 条**。
     三条**已试并否决**的纯文本启发式（记录以免后人重走）：①"文本自带页眉证据才收口"→ 漏 2,910 处真页眉（它们没有 Aspose 水印）；②"该标准号在文内出现 ≥2 次"→ 条款只覆盖一页时不成立；③"尾巴前必须是句末标点"→ 判据过粗。
     回归用例 `tests/test_watermark_own_standard.py`（37 条，取代原 `test_watermark_tail_known_gap.py` 的 4 条 strict xfail + 4 条护栏 —— **xfail 已全部转为真断言**）：表格末格必存活 / 自家页眉仍必删 / 整行页眉仍必删 / 全角 own 可匹配 / **页眉把 GB/T 印成 GB 仍必删**（钉住那 226 类）/ 同族不同号必保 / 分册号不同必保 / 合法引用存活 / 水印两族照删 / **不传时保持历史行为**（防无痕改变既有调用方）/ `canon_standard_no` 单元 / **端到端接线 3 条 + 1 条 strict xfail**（截获 `clean_clause_text` 断言 `own_standard_no` 真传到；自家页眉在真链路被删；**行内家具片段保留别人的标准**；xfail 钉住切分层那一半）。
     **⚠ 同一判据还有第二个所有者 —— 两处都已接上下文（写端到端用例时才发现，单元测试全绿也漏）**：`pipeline.py:66` 的 `_STD_CODE_FRAG` / `_STD_CODE_LINE`（**家具剥离**）是"页码 + 标准号"判据的另一份实现，两处都改到了：
     - **`build_clause_models` 内的逐行剥离**：该函数签名里就有 `standard_no`，补命名捕获组 + `_frag_key`（只比"号-年"），**行内片段只剥自家标准号**；
     - **切分层 `split_items_into_clauses` 的 ≤80 字剥离**：给切分层加了可选参数 `standard_no`（缺省 None = 历史行为），`run_full_ingest` 与 `dry_run` 的预览路径都传；剥离逻辑收敛为**唯一实现** `_strip_foreign_frag(text, own_key)`，三处调用同一份，不再各写一遍。
     - `_STD_CODE_LINE`（**整行就是一个标准号**）**故意不设条件** —— 整行只是标准号时不存在"表格末格"歧义，且页眉年份未必等于库内 `standard_no`（既有回归用例 `test_build_row_pipeline_furniture_strip` 正是：文档 `GB 30871-2022` 而页眉行 `GB 30871—2025`）。**歧义只在"行内片段"那一侧。**
     - 新增 `_own_key_of()` 守卫：占位符 `"未知标准号"`（dry-run 猜不出标准号时的填充值）**必须挡回 None**，否则它会变成"永不匹配的比较键"＝把家具剥离整体关掉，与历史行为不符。
     - **这也暴露了项目"单一所有者"原则的一处违反**：`text_utils` 注释自称"使 `strip_watermark_lines` 只有一个判据来源"，实际全仓有两份同义判据（水印族 + 家具族）。现已统一到"传标准号消歧"的同一套口径。
     - **独立 verifier 复核结论（在 `78a0a1f` 的 detached worktree 上跑；勿与后续提交混读）**，我据此修正三处表述并新增一条遗留项：
       - **"226 行"应为约 220**：该数出自"整串比较"变体；verifier 自复刻整串比较得 **220** 行。**机制与量级成立，具体数字随变体实现浮动**。
       - **"不传上下文时幂等"必须注明语料**：我先前测的 `0/19,981 非幂等` 是在**清洗后的活库值**上量的；在**清洗前快照**上，不传上下文时**有 4 行**非幂等（正是那 4 条命名补丁：第一遍剥掉 Aspose + 自家页眉后，表格尾巴变成行尾匹配 → 第二遍删掉它）。**这是从父版本继承的性质，不是本次引入**；传上下文后那 4 行永久保住。故 `repair_patch_watermarks.py` **只在走上下文路径时**才是安全的。
       - **早退守卫有一处有界欠删（新增，零语料触达）**：输入 `'正文 www.spc.net.cn 5 GB/T 10029—2010'`（own=`GB/T 28788-2012`）时新实现保留尾巴、父版本删掉它（URL 两版都保留）。**触达 0/19,981**，方向是"宁可留内容"，接受并记录。
       - **新增遗留项（未修，重要）**：**评估/自进化环的 8 处调用点没有传标准号**（`var/ocr-loop/evolve.py:304`、`fidelity_census.py:280`、`probe_quality.py:53`、`verify_batch.py:138`、`probe_spacedrun3.py:31/52`、`probe_coverage_gap.py:83`、`probe_cov_on_lost.py:68`、`probe_wm_reverse.py:68`）—— 仍按历史行为误删，**且现在与入库口径分叉**，违反 `clean_clause_text` docstring 立的"入库与评估同次序同结果"。
       - **休眠风险**：跨前缀族"号+年"假相等（`GB 10769-2025` ≡ `GB/T 10769-2025` ≡ `GBZ …` ≡ `DB11/T …`）。当前语料只有 GBT/GB/GBZ 且无碰撞 → 未触发；**将来入库行标（JT/JG/NB/DL）页眉页会静默删掉外来表格末格**。另 12 条 `doc_meta.standard_no` 带尾缀/无年份（如 `GB 5009.12-2023食品安全国家标准`）**永远匹配不上自家页眉**。
       - **测试诚实度**：32 条用例里 **25 条在"上下文被架空"的实现上也会通过**（非本改动的护栏）；真正钉住设计的是 4×表格末格存活 + 整行外来标准保留 + 同族不同号必保 + 分册号不同必保 + "GB/T 印成 GB 仍必删"。
     另**显式记录一条有意保留的已知限制**：正文里的全角斜杠标准号不被识别（判据自始只认半角斜杠；实测正文尾巴都是半角，放宽会扩大误删面）。
4. **官方侧边栏迁移（`aaefeaf`）**：DSH 0.1.6-alpha.1 的正式扩展模型是 VS Code 式两段注册——`ctx.sidebarRightTabs.register(def)` + `ctx.slots.register({name:'sidebar.right.pane.tab', key:def.id})`，用 `ctx.sidebarRight.openResource(addr,{kind,params})` 打开；`contentId` **就是地址**，同址即同 tab（打开幂等）。据此删除自造桥接三件（`bsContract.ts` / `dsh-better-sidebar.d.ts` / `smoke-bs-contract.mjs`）——第三方包 `dsh-better-sidebar` 在 0.1.6 profile 中已不存在；`dsh.client.inject` 与 peerDependencies 改指 `@deepseek-ai/dsh-client-ui-sidebar-right`。新增 `ksSidebar.ts`（契约类型/常量/tab 定义）、`KsEvidenceHost.tsx`（官方注入 → `KsEvidenceProps`，`meta.ksClick = navigation.revision`）、`ksPrefs.ts`（localStorage 偏好，storage 事件跨窗同步，SSR 安全）；`entry.ts` 改官方探测 + 显式 `console.error` + 事件驱动重试，设置区注册从"侧边栏成功回调"解耦到 `apply()` 顶层；3 处 `ctx.betterSidebar` 调用点 → `onUpdateTitle` / `onOpenEvidence`；`pdfPanel.ts` 的 `WidthCapableStore` → `PanelWidthPort{getWidth,setWidth}`。smoke 段数 12→11，`smoke-client-entry` 36/36（case 3/4/4b 按两段式重写）。
   - **诚实边界**：C 线**未**实现侧边栏自动加宽（记录为可重启项，用户已认可）；运行中的 DSH host 由 tsx 从**更新前**源码启动，故本次迁移需**重启 host** 才生效——重启前的 "registered nothing" 不代表代码错。
5. **D 线：援引弃权（`c21a332`）**：`typed_verifier._describe_unsupported` 产出 `unsupported_context`（三类：`same_standard_not_retrieved` / `outside_evidence_standard` / `unknown`——未知情形**不猜**）；`VerificationResult.unsupported_context` 新字段；SSE `verification` 事件**只增字段**（`evidence→status→delta→verification→done` 顺序不变）；`tests/test_unsupported_context.py` 6 条；契约增量入 `pipeline/03-contract-delta.md` 33 号。**阻断行为不变**——只增可读信息。
6. **Golden Set 门禁自豁免关闭（`7caf9b2`）**：原 `test_golden_gate.py` 在基线缺失时会**自动写入**基线——即门禁可以**自己给自己定基准**，回归从此不可检出（"门禁假装通过"）。改为：基线缺失 → `AssertionError`；首次构建需显式 `KS_BASELINE_BOOTSTRAP=1`；`no_regression` 用例同时断言基线的**键覆盖**（缺键也算回归）。`_baseline_tracked_by_git()` 只用于错误措辞，不再参与判定。
7. **文档漂移同步（`390c434`）**：README 门禁数字改实测、目录图纠正（`pipeline/` 在仓库根，不在 `docs/` 下）、清掉已删除文件的引用；ENCYCLOPEDIA **表数口径**澄清——`CREATE TABLE` 32 + 虚表 2 = **34**，而 `sqlite_master WHERE type='table'` 返回 **45**（FTS5 影子表），故报数**必须同时声明口径**，否则两个数看着像矛盾。
8. **PDF 阅读器默认瀑布式（`9c851e0`）**：证据 tab 的 PDF 视图默认改为**连续瀑布**并加**底部常驻工具栏**（翻页/缩放/页号不再需要回顶）；适配计算抽到新模块 `pdfFit.ts`（+147 行）并配 `smoke-pdf-fit.mjs` 41 断言。同提交把 OCR 循环的代码资产（`var/ocr-loop/` 的 `HANDOFF.md` / `ingest_from_manifest.py` / `ingest_one_probe.py`）纳入版本控制。`a808dbb` 为 `.gitignore` 补 `check_*.py` 探针族（与 `probe_`/`diag_`/`census_` 同族）。
9. **独立复核的两处产出（`a07f40c` `c9898a1` `a3083f5`）**：
   - **端点底数实测重扫**：AST 全量扫 `src/core/api/` 六个模块 = **127 个端点（method × path）/ 113 条唯一路径**（分模块 server.py 77 · routes_update 30 · routes_law 7 · routes_ingest_preview 6 · routes_report 4 · routes_settings 3；另查 `add_api_route`/`add_route`/`mount`/`websocket` 均 0，故装饰器枚举完备；注意**路由处理器多为 `async def`**，只 override `visit_FunctionDef` 的 AST 遍历会几乎全漏）。旧文"**120** 端点"与 47+54+19=120 的占比**对不上 127** → 该四分类降级为"2026-09-13 历史快照、分母须重算"；**但其 ZERO 标签经抽查 8 条无反例**（`/compare`、`/export/citations`、`/laws/check-updates`、office-edit poll/commit、`/documents/{id}/versions`、`/clauses/{id}/backlinks`、`/annotations` CRUD），故是"标签可用、分母要重算"。**方法论警告已写进百科**：host 会把引擎路径重写成语义不同的同源前缀（`/ks/doc-image/{doc}/figure/{no}` → `/api/v1/documents/{doc}/figure/{no}`），**朴素字面匹配会把 4 个确实在用的端点误判成 ZERO**；且**词级匹配会造假反例**（`from __future__ import annotations` 让 `/annotations` 看似在用、`compare_clause_texts` 让 `/compare` 看似在用）——**匹配必须路径级**。
   - **条款号查询归一（`a3083f5`，P2 级修复）**：`clause_repo.resolve_clause` 全程 `clause_number = ?` **原样比较**，查询入口**零归一**；`normalize_clause_number` 只用于入库（`pipeline.py` 7 处）与引用抽取（`classifier.py:171`）。实测生产库 520,504 条里**含全角 0 条**，`'５．２．１'` 直查 **0 行** → 用户/模型写全角时**查不到本该命中的条款**（取证场景 = 漏一条依据）。改为**原样优先 + 归一重试**（纯增量）：先按原样查，只有查不到才用归一形式重查；`表N` fallback 改测归一形式（「表 2」带空格也能进）。**为什么不能无条件归一**：库里真实存在带前导零的条款号，实测 520,504 条中 normalize 与原文不同的**恰好 2 条**（`'06'`/`'08'`），无条件归一会让查 `'06'` 命中 `'6'`。对照实验（旧实现取自 `git show HEAD~1`，跑同一 fixture）：旧命中 3 条 → 新命中 7 条；新增 7 条回归（含 1 条端点级 + 1 条前导零护栏）。
     **⚠ 第一版（`a3083f5`）自称"纯增量"被 verifier 判 REFUTED**，三条反例均已在 `ddcae1f` 处理：
     **(R3，活体必修)** `normalize_clause_number` 的 `int(p)` 对 `p.isdigit()` 为真的 **128 个码点**（上标 `¹²³`、下标 `₀-₉`、`①`）抛 `ValueError`，而第一版把归一放在**任何 SQL 之前**且不兜异常 → 任意这类输入把 `/api/v1/clauses/resolve` 打成 **HTTP 500**（旧实现是 404/200，无需特殊数据即可触发）；**修法**：归一包 `try/except`，失败退回"不归一"。
     **(R1)** 第一版改用 strip 后的形式做首查，旧实现用的是**调用方原样**串 → 库内真有带空白的 `clause_number` 时会漏；**修法**：原样 → 去空白 → 归一，三级依次试。
     **(R2，有意的行为变更，已声明)** `'表2'` 与 `' 表2 '` 现在给同一结果 —— 旧实现本身不一致（无空格时精确命中"名为 表2 的条款"，带空格时掉进"正文引用该表"的兜底）。**这就是"纯增量"说法被推翻的地方**，故不得再自称纯增量。
     **教训**："纯增量"是**需要证明的断言**，不是自评；一个 20 行的改动照样能引入 500。

9. **侧栏「开始」页手动入口（`75c8828`）**：需求是"把 PDF 阅读器的手动入口放到官方侧边栏开始界面的「新建终端」按钮下面"。
   - **先说清扩展点（读 DSH 检出确认，不靠猜）**：侧栏「开始」页 = `ui-sidebar-right` 的 guide tab，body（`GuideBody.tsx`）把**每个已注册 tab 类型贡献的入口胶囊**排成一列；胶囊来自 `SidebarRightTabDefinition.guide?: SidebarRightGuideEntry[]`（契约原文："Entry boxes for the guide page. **Omit to stay off it.**"）；排序 `tab-registry.refresh()` 里 `.sort((l, r) => l.order - r.order)` 是**升序**；点击走 `tab.actions.openTab(entry.kind, {replaceTab:true})`，**不带地址**。实测在用的 order：`ui-sidebar-files`=**10**、`ui-sidebar-terminal`=**20（新建终端）** ⇒ 取 **30** 即落在它下面。
   - **改动**：`ksSidebar.ts` 补 `KsGuideEntry`/`KsIconProps` 最小契约 + `KsTabDefinition.guide`，`ksEvidenceDefinition()` 贡献一条胶囊（`id:'pdf'`, `order:30`, 标题**与 tab 初始标题同源**、说明、图标）；新增 `KsPdfGuideIcon.tsx`（官方 `IconProps`：方形边长 + class，随 `currentColor`；对 ksSidebar 只做 `import type` ⇒ **无运行时循环依赖**）。`KS_GUIDE_ORDER_PDF` 显式导出并注明"跨插件共享排序空间"。
   - **为什么点胶囊能直接用**：官方按 **kind** 打开（无地址）→ `KsEvidenceHost` 把缺失的 `params.url` 映射为 `tab.path = undefined` → `KsEvidenceTab` 走既有 idle 态（左列文件目录）——**这正是"手动入口"**，不需要先有证据链接。
   - **验证**：`smoke-client-entry` **36/36 → 40/40**（新增 4 条：恰好一条胶囊 / `order=30` 且严格大于 files(10) 与 terminal(20) / id 唯一且 title·description·icon 齐备 / **胶囊标题 == tab 标题**）；全 smoke 11 段 PASS；tsc 0 错；bundle 内确认含该注册。
   - **部署与生效**：profile 的 `ks-dsh-plugin` 是仓库 `plugin/` 的 **junction**，实测重建后两侧 `client.js` SHA-256 一致 ⇒ 无需 copy；纯 client 半改动 ⇒ **刷新浏览器页面即生效，不用重启 DSH 宿主**。
   - **⚠ 上线后第一次真机点击就暴露一个 P0：pane 全白（`e6f0d4e` 系列修复）**。用户反馈"按钮有了、点开也开了 bar，但打开之后是空白"。按系统排错走：抓**完整错误**（CDP 接 headless Edge，`Runtime.consoleAPICalled`）拿到两条决定性日志：
     ```
     [console.error] Error: [ks-dsh-plugin] sidebar.right.pane.tab 座位未提供 hooks.tabInfo
     [console.error] slot entry crashed in 'sidebar.right.pane.tab': <同上>
     ```
     **根因**：body 的 `inject` 工厂把**第一个参数当成"框架聚合面"**并断言 `hooks.tabInfo` 存在 —— 而官方契约里 `inject` 工厂的**第一参数是 `sessionId`**（`ui-sidebar-documentpreview/src/client/index.ts:104` 写作 `inject: (sessionId, actions) => …`），其**返回值才是本插件贡献的面**；`useTabInfo` 则来自座位的 `hookContext: TabHookContext`，框架**直接作为组件运行时 prop** 交给 body（官方 `TextPreview.tsx:96`、`GuideBody.tsx:80` 都这样解构）。于是 `hooks.tabInfo` **永远是 undefined** → 迁移时自设的"契约变更守卫"**挂载即抛** → 官方包成 `slot entry crashed` → 空白。
     **修法（规范所有者＝我们的 body 注册 + 适配层，不是官方）**：`inject: (): KsEvidenceHostInjected => ({ openEvidence })`（只贡献自己那一个面），`useTabInfo` 走 props；并把守卫从"抛错"改成"**渲染一句人话**"（抛错恰好造成它本想避免的空白），拆成 `KsEvidenceHost`（只判断，不调 hook）+ `KsEvidenceBody`（无条件 `useTabInfo()`）以满足 hooks 规则。
     **回归护栏（这条闸以前抓不到它，因为 smoke 的假框架从不调用 body 的 inject）**：`smoke-client-entry` 新增一条 —— 用"像真框架那样"的第一个参数调用 body 的 `inject`，断言**不抛**、返回 `openEvidence`、且**不谎称提供 `useTabInfo`**。`smoke-client-entry` **40/40 → 41/41**。
     **真机复证**：修后同样流程 —— 点胶囊 → pane 子树出现 `📑 目录 ▾ 从左侧目录点开任意国标/法规即可阅读`（idle 态如期渲染），且**页面 console 无任何报错**。
   - **顺带记录（未修、与本缺陷无关）**：页面加载时"目录常驻"自动开 tab 的那次调用报 `sidebarRight: no session surface is mounted`（宿主还没挂载会话面），故**开局不会自动开 PDF tab**——手动入口已覆盖该需求，故本次不动它。另全 smoke 串联跑时 `smoke-chatmode` 偶发 1 条 `a session closed by this process is not resurrected from disk` 失败，**单跑 144/144 通过**，属既有的顺序/环境相关抖动。
10. **两处收尾（2026-09-17，承 §八.9 与独立 verifier 报告）**：
   - **删掉"目录常驻"的自动开 tab**：原实现在 `apply()` 里直接 `right.openResource(...)`，而那一刻**会话面还没挂载** → 真机每次都抛 `sidebarRight: no session surface is mounted` 并留一条 `console.warn`。也就是说**它从来没有生效过**（只是每次加载吵一句），而它的用途（"无证据也能进 PDF 阅读器"）现已由**开始页手动入口胶囊**承担；自动开还会把开始页顶掉，与"开始页＝入口"的设计冲突。**若将来确实要"开局常驻 tab"，正确位置是会话面挂载后的回调**，不是 `apply()`。smoke 里两条钉住"自动开"的断言随之改成钉住"**加载时不自动开**"（`client-entry` 41→40 条，全绿）。真机复证：刷新后页面 console **一条 KS 消息都没有**（原来的 warn 消失），点胶囊仍正常渲染 `📑 目录 ▾`。
   - **评估侧与入库侧口径对齐（verifier 点名的 8 处中的 3 个被跟踪文件）**：`var/ocr-loop/evolve.py`（两处）、`fidelity_census.py`、`verify_batch.py` 原先调 `split_items_into_clauses(items)` / `clean_clause_text(...)` **不传标准号**，于是评估与入库**分叉** —— 水印/家具判据里"页码 + 标准号"那一族无法消歧，评估会把**表格末格**（引用别的标准）当页眉删掉，**持续报一个入库里已经不存在的缺陷**（违反 `clean_clause_text` docstring 立的"入库与评估同一次序同结果"）。已按各文件已有的标准号变量（`doc["std_no"]` / `stem` / `d["std_no"]`）补传 `own_standard_no=` 与 `standard_no=`。**特别地 `verify_batch.py:138` 是对"已清洗过的 model 文本"再洗一遍**——不传标准号时那第二遍会把入库刻意保留的表格末格删掉（正是父版本继承来的"不幂等那 4 行"）。另 5 处（`probe_quality.py` 等）**未被 git 跟踪**（scratch 探针），未改。

11. **目录列定位修正（`9257177`）——"从屏幕最右边向左弹出"**：用户反馈"目录是从屏幕最右边向左弹出的，而不是从 sidebar 左边向左弹出"。先按系统排错**量真机再改**（CDP）：目录列是 `position: fixed` 的 portal，实测 `left=1384 / right=1574 = window.innerWidth`、`cssRight=0px` —— 它贴在**视口最右边**。
    **根因**：旧模型把面板钉死在视口右侧，于是用 `right: panelWidth`（面板宽度）反推"面板左缘向左"的位置；而**官方侧栏没有宽度面**（`KsEvidenceHost` 不注入 `panel`）→ `panelWidth = panel?.getWidth() ?? 0` **恒为 0** → `right: 0` = 屏幕最右边。
    **修法**：新增**实测锚点** `tocAnchorRight = window.innerWidth − 容器所在侧栏列的左缘`，由既有测量链同步（`useLayoutEffect` 保证首帧绘制前就位，避免先在最右边闪一帧；`measureNow` 的 ResizeObserver / `window.resize` 负责拖宽·缩放·最大化跟随）；`panelWidth` 只留作未测量时的兜底。
    ⚠ **坑（第一次修完仍是 `cssRight: 0px`）**：不能直接用容器自己的 `getBoundingClientRect().left` —— 官方侧栏把 body 挂进一层**尺寸为 0** 的包裹层（实测 `rightbarCol` 的内层 div 是 0×0，而它自己 709×907），容器宽 0 时它的 `left` 落到视口最右 → 锚点算成 0。故加 `paneLeftEdge()`：**向上取第一个宽度 > 1px 的祖先**的左缘。
    **真机复证**：列从 `[1384, 1574]` 变为 `[676, 866]`，**右缘正好等于侧栏列左缘 866（重叠 0px）**；三点命中测试（上/中/下）均落在列内 ⇒ 绘制在对话区之上且可交互，内容为文件目录树。门禁：tsc 0 错；smoke 11 段全 PASS（pdf-fit 41/41、pdf-panel 29/29、client-entry 40/40…）。

12. **自适应缩放规则回退为「宽度铺满」（2026-09-17）——用户裁定"高度不用管"**：用户反馈"**自适应窗口模式下，PDF 的右边一部分显示不出来**"，并直接给出规则：**"宽度铺满，高度不用管，万一 sidebar 拉得很宽，那你高度再怎么样都不可能匹配得上"**。
    - **根因（旧规则在数学上必然切右边）**：v2（2026-09-09）的规则是 `scale = max(fitWidth, min(fitHeight, fitWidth × 1.25))` —— "高度优先 + 1.25 横向溢出预算"。横向溢出的**充要条件是 `fitHeight > fitWidth`**（即侧栏"高瘦"），此时 `scale` 取 `min(fitHeight, 1.25×fitWidth)`，溢出比例 `= min(fitHeight/fitWidth, 1.25) − 1 ∈ (0, 25%]`：**侧栏 ≲523px 时恒为满额 +25%**，523~648px 之间不足 25% 并递减到 0，**≥648px 不再溢出**（A4、可视高 883 下的精确拐点 `availWidth = 883 × 595.28/841.89 = 624.35` ⇒ paneW 648.35，复现：`var/tmp/fit_calc_v3.mjs`）。这台机器上侧栏默认就是 ~700px 附近、可拖窄，所以症状只在**拖窄 / 目录列顶开**后出现，与用户描述吻合。实测（真实函数，改动前）：侧栏 400 → scale 0.790 → 页宽 470 vs 可视 376 → **右侧切 94px**（= 可视宽的 25% / 页宽的 20%）；侧栏 520 → 1.042 → 620 vs 496 → **切 124px**（同为满额 25%）。
    - **为什么 v2 当年的理由不成立**：v2 的注释写"保证至少 80% 行宽可见"（verifier P1-2, 2026-09-09 立的"必须有上限"）。但**那 80% 是横向的 80%，切掉的是每行的最后 20% 字符**——对"读条文原文"这个用途，**看不全 = 需要左右拖，比看不到高度更糟**；而纵向本来就必须滚动（A4 页高 841pt 在 ~880px 视口里 1:1 也放不下）。用户的原话正是这个判据：**高度永远匹配不上，所以别为它牺牲宽度**。⇒ `fitHeight` 与 1.25 预算一起退休。
    - **改动**：`fitPageScale` 的算式缩成一句 `scale = 可用宽 / 页宽`（再被 `MIN_SCALE`/`MAX_SCALE` 钳制），**高度完全不参与**；`MAX_WIDTH_OVERFLOW` 与 `continuousViewportHeight` 删除（后者本是为"把旧规则人为压回宽度适配"而存在的补丁）。`FitResult.basis` 恒为 `'width'`、`cappedByBudget` 恒为 `false` —— **字段保留但标注为历史**（UI 文案与冒烟按 `basis` 分支），避免"永不可达的分支"被误读成活逻辑。`KsEvidenceTab.tsx` 解除对 `continuousViewportHeight` 的依赖：单页/连续两种翻页模式现在**定标完全相同**。另把 `TASK-pdf-bottom-bar.md` §3 里两条已失效的约束就地标注为"已被 2026-09-17 取代"（保留原文存证），免得那份任务书继续断言旧规则。
    - **验证**：规则是纯函数 ⇒ 先离线把契约钉死。`smoke-pdf-fit` **37/37 PASS**，其中三条是新契约的主断言：① `availHeight` 取 876/200/4000 三值时 `scale` **完全相同**（钉住"高度不参与"）；② `autoFit` 恰好落在可视宽上且**不超过**可视宽；③ `basis === 'width'` 且 `cappedByBudget === false`。published-symbol 清单同步删掉两个已退休导出（否则冒烟会因导入失败而假红）。
    - **真机复证（CDP，headless Edge 9333）**：读取底部常驻栏的缩放滑块百分比。基准态容器 708px → 滑块 **115**（= 684/595.28，恰好宽度铺满）；**临时把 PDF 容器压到 400px** → 容器 424px → 滑块 **65%**，而**旧规则在同一位置会显示 84%**（= 1.25 × 400/595.28，页宽 500px 塞进 400px ⇒ 切 100px）。这就是"新旧规则可分辨"的直接证据：新规则跟随宽度、旧规则必然溢出。恢复宽度 → 回到 **115**（跟随是双向的）。门禁：tsc 0 错；smoke 11 段全 PASS。
    - **诚实边界**：① `MIN_SCALE = 0.5` 是**可读性下限**，故契约不是"永不横向滚动"——阈值 `0.5 × 页宽 + 24` **随页宽变**：A4 纵向（595.28pt）≈ **322px**，而库里那种 ~826pt 的横向国标页 ≈ **437px**。低于阈值时页宽被定在 297.6/413px 而超出可用宽，此时**仍会横向滚动**（容器 `overflow:auto`，滚得动）。取舍同 v2，只是触发点从"任何窄面板"收窄。② 真机 65% 与预测 67% 那 2 个点的差**已定论：是我自己的探针读错了宽度，不是应用缺陷**——容器 **border-box 708px** vs **clientWidth 700px**（差 = 8px 纵向滚动条），而 `fitPageScale` 用的是 **clientWidth**（它已扣掉滚动条）。实测三态：按 clientWidth 预测 114/71/114 **全部等于**滑块，按 border-box 预测 115/72/115 全部偏 1（`var/tmp/probe-scrollbar-gap.mjs`）。③ 未做跨浏览器/跨 DPI 的真机矩阵。

13. **独立 verifier 复核 §八.12 + 两处修复（2026-09-17，同轮）**：按纪律派独立 verifier 复核"宽度铺满"改动，结论：**6 项主张全部 CONFIRMED**（高度确实不参与：真实模块 6 个宽度上 `availHeight>0` 时结果**逐位相同**，2 万次随机差分 `height-sensitive = 0/20000`；右侧不再被切；无死符号；冒烟**未被削弱反而更强**；文档与代码一致；**bundle 可证明就是新规则**——函数体逐字相同、`git hash-object == HEAD:plugin/client.js`、mtime 顺序正确）。它也抓出两件事，都处理了：
    - **⚠ verifier 有一处误报（记下来当方法论）**：它报 `pdfFit.ts:91` 仍写"~300px"（P2）。**实际不复现**——它是在我改到 322px **之前**读的文件（文件 mtime 08:35:45，提交 08:36:44），随后才读 git 状态并把那份**过期的文件内容**当成"已提交状态"一起报出来。核对方式：`git show HEAD:plugin/client/pdfFit.ts` 该行确为 322px。**教训与"报告不是现状"同源：verifier 的报告也是"它读文件那一刻的状态"，跨时序的引用必须回原文件重验。**
    - **P1（真实、且本次改动把它变得更显眼）**：底部缩放滑块 `step={5}` 而 `min=10` —— range input 按规范把 `value` 吸附到 `10+5k`，**滑块（thumb）位置因此与 label / 实际渲染不一致**：`sl.value="80"` 而 `title="缩放 82%"`、canvas 恰好 82%。这把"自适应百分比"这个本功能的核心读数变成了错的。我先独立复现（CDP 机械证明 `var/tmp/probe-slider-snap.mjs`：step=5 写入 82→80、99→100、113→115 全部被吸附；step=1 后这些整数原值保留），再修：新增 `ZOOM_SLIDER_STEP = 1` + `isOnSliderGrid()` 到 `pdfFit.ts`（与 `MANUAL_MIN/MAX_PERCENT` 同处，因为它是**同一条契约**），滑块改用它。**回归护栏可证伪**：先加两条冒烟断言，再把常量临时改成 5 → 断言**如实失败**（37/39、退出码 1），改回 1 → 39/39。真机复证：三态下 `valueMatchesLabel` 全为 true，且 114/71/101 这些**非 5 倍数**的值现在能如实显示（旧 step=5 下 thumb 会停在 115/70/100）。
14. **P0：`单页/连续` 一按就把文档卸掉（2026-09-17 验证途中抓到；**预先存在的缺陷，非本轮改动引入**）**：
    - **现象**：右侧栏从**文件目录**打开任一文档（连续模式，40 块 canvas 正常）后，点一下底部的「**单页**」→ 文档消失、阅读器回到"从左侧目录点开任意国标/法规即可阅读"空态，**切回「连续」也不恢复**（必须重新点目录）。**全程无任何 console 报错**。
    - **先证明"不是我干的"**（否则会误改自己的新代码）：把工作区 stash 回干净 HEAD，`git checkout 7c96120 -- plugin/client/{pdfFit.ts,KsEvidenceTab.tsx}` 重建**改动前**的 bundle，用同一探针复跑 → **完全同样的现象**（切单页后 canvasTotal 0、idle 文案出现）。⇒ 与本轮的宽度规则无关。（副产物：同一次对照里旧规则连续模式读数 **145%/144%** vs 新规则 **114%/115%**，反向印证了宽度铺满确实生效。）
    - **根因（插桩定位，不是猜）**：`KsEvidenceTab` 里 "Re-parse evidence" effect 的依赖数组含 `loadEvidence`，而 `loadEvidence → renderPage → pagingMode`，所以**点「单页」会改变该 effect 的身份依赖 → effect 重跑**；它又**只从 `tab.path`/`tab.meta` 重新解析证据**，而"从文件目录打开"的 tab **没有地址**（`rawPath=null`）→ 解析出 `ev=null` → `evidence.current=null` → `loadEvidence(null)` 进 idle，**连 cleanup 里的 `pdfDoc.destroy()` 一起**把文档销毁。插桩日志是决定性的：`[KSDBG] path-effect RUN {"rawPath":null,"ev":null}` 恰在点「单页」时出现（点击前后各一条）。
    - **修法（规范所有者＝那个 effect 自己）**：它的职责就是"**地址变了才重解析**"，所以依赖数组收窄为 `[tab.path, tab.meta]`，调用改为经 `loadEvidenceRef`（新增；照 `refreshMetaRef` 既有写法）取最新实现 —— 从根上切断与 `pagingMode/zoom/box/dprEpoch` 的意外耦合。顺带核对了全文件：**其余 12 个 effect 没有一个依赖 `loadEvidence` 身份**（4 个 `useCallback` 的 `[loadEvidence]` 依赖只是让子组件重渲染，无害），故只有这一处需要修。
    - **复证**：连续 40 canvas → 点「单页」→ **1 块 canvas、文档仍在、idle 文案不出现** → 点「连续」→ 回到 40 块，**全程无 console.error**。这也补上了 verifier 明确未测的"单页模式真机"一格。
    - **新增可复现回归**（此前只有 `var/tmp/` 里的一次性探针，未入库＝无法防回归）：`plugin/scripts/e2e-sidebar-pdf.mjs`（`npm run e2e:sidebar`），真机驱动并断言 13 条：模式切换不卸载文档（A2/A5 钉住本次 P0）、宽度铺满不变量（B1/B2/B3）、滑块如实反映（C1/C2/C3）、切换期间无报错（D）。**刻意不进 `npm run smoke`**（真机依赖不该塞进离线门禁），且**没有可连的浏览器时打印 SKIP 并以 0 退出**（实测 `KS_E2E_CDP_PORT=9399` → SKIP、exit 0），保持可选。当前 **13/13 PASS**。
    - **诚实边界**：① 该 P0 只在**无地址的 tab**（从文件目录/收藏打开）上触发；带证据链接的 tab 因 `tab.path` 非空会表现为"悄悄重载一次"而非变空 —— **未实测**后者（需要一条真实证据链接，本轮没造）。② 单页模式的 canvas 宽比容器内容宽 **±8px**（= 一个滚动条宽；连续模式是 0px）：实测 `clippedByWrapper: false`、`horizontalOverflow: 0`，即**不裁剪、不溢出**、只是右侧留白差 ≤1.2%，记为观感级观察，未修。③ 根因机理是插桩实测的，但"为什么 `box` 变化（同在该 effect 的身份依赖链上）没有同样卸载文档"这一点**我没有单独证明**；修法不依赖该问题（收窄依赖后任何身份变化都不再触发），故不影响结论。

## 九、外部借鉴调研的落点与边界（2026-09-16）

独立复审了一批开源项目（**实测 15 个上游浅克隆 + 41 份报告、合计 2.43MB**，全部在仓库之外的 `D:\AI\oss-refs\`）的**可借鉴能力**，逐条回本仓库核实，**不采信既有结论**：

- **唯一落地的借鉴**：援引弃权（citation-abstention 思路）→ 上节 D 线 `unsupported_context`。
- **一处先信后被证伪**：既有报告称 `exception` 列"真 0"——实测 **16,115 非空（3.1%）**，赋值点在 `pipeline.py:1370` / `law_text.py:124` / `docx_ingest.py:58`。
- **一处判断降级**：PyMuPDF 是 **AGPL-3.0**（`METADATA: License: GNU AFFERO GPL 3.0`），`src/core/` 内 23 处活 `import fitz`。但它是 pip 依赖、**从未 vendor**；`scripts/make_handoff_zip.py` 的 `EXCLUDE_DIRS` 含 `.venv`；仓库**无 LICENSE**、**无发布/分发流水线** → AGPL 义务由**分发**触发，而本项目不分发。故处置为"**记实 + 立重开触发器**"（将来若打包成 EXE 或对外提供网络服务则重新评估），**不替换 PyMuPDF**——替换要重做整个坐标层并撞 bbox 红线。
- **一处降级为 P3 并推迟**：`page_breaks` 用**行号**编码而补丁会改行数（19,981 条补丁 / 15,852 条改行数），语义确实失真；但其**唯一消费者**只用"行号→页"来放分页标记与插表格，故失真只让标记平移约 1–2 行 = **观感级**，不影响取证准确性。正确修法（改字符偏移 + 移植 eyecite `SpanUpdater`）是契约变更、有真实回归风险，为 P3 收益不划算。**原设计红线仍然有效**：不增删正文行（强加回车会造成证据卡文字断裂）。
- **验证方法纪律**：既有报告中被随机抽检的 9 条结论里，2 条已过时或错误、1 条已在本会话前修好。**报告不是现状**——凡机制性结论必须落到活的调用链上再采信。
- **独立复核报告原本**（两段式：非工程摘要 + 工程结论表 + 诚实边界 + 复现命令）落在仓库之外：
  `D:\AI\oss-refs\reports\INDEPENDENT-REGRADE-2026-09-17.md`。仓库内**故意不存副本**——
  这类调研产物不属于代码树。上节端点消费图谱的修正也是同一轮复核的副产物。

## 十、定位转移：材料平面与通用研究（2026-09-17 起）

业主 2026-09-17 裁定**定位转移**：项目从「通用国标与法律法规本地 AI 知识工作站」转为**通用资料研究 + 交付工具**——法条问答退为**其中一个（最高权威的）数据源**，而不是唯一内容。新增能力要能：参考用户自定义资料（如上传财报做分析）回答问题、**自己去搜集材料**（默认开启）、对材料**做可信度判别**（"不是随便找个什么网络文章就当权威信源"）、经**用户评审**确认资料可用后，才在"已收集 + 用户提供"的资料上做分析或产出（分析报告 / PPT 等）。

**施工纪律（业主同轮定）**：**小步走、多次提交，每步一个快照，出问题能回滚**；先整体备份再动。
- 基线标签 `pre-redirect-20260917`（= `deadcfd`）；实体备份 `D:\AI\backups\zcode-20260917-122049`（9,835 文件 / 2,546 MB，含 `.git`，排除 `.venv`/`node_modules` 等可重建目录）。
- 快照工具 `scripts/snapshot-project.ps1`：建 `step-NN-<名>` 附注标签、打印回滚命令、**有未提交改动会告警**、`-Full` 追加实体拷贝、`-List` 列出全部。回滚 = `git reset --hard step-NN-<名>`。

### 10.1 方案（`a8287f8`，快照 `step-01-plan-v1`）

`docs/MATERIALS-PLANE-PLAN.md` v1。方案里三处**经核实**的关键结论：

1. **业主对"权威性"的举例逼出了一个根本性设计**：业主说"上传公司制度问怎么做，那肯定要遵守制度"。但公司制度的**来源可信度低于国标** ⇒ 权威性**不能是一条线**，必须拆成**两个正交轴**：**轴 A 来源可信度**（T0 法定/官方 · T1 用户自有原件 · T2 权威第三方 · T3 二手转述需≥2 独立来源互证 · T4 不可回溯）决定"**怎么标注、能否承重**"；**轴 B 任务内效力**（本次以什么为准绳，用户声明）决定"**谁说话**"。单轴排序必然错一个：只按可信度排会答非所问（引国标不引唯一有效的公司制度），只按相关性排会把网络帖子与国标同权——**正是业主要避免的那件事**。
2. **法条链必须零改动**：`doc_meta.standard_no TEXT NOT NULL UNIQUE` **结构上就装不下**财报/新闻，这是必须另立"材料平面"（`project`/`material`/`material_chunk`）的根本原因；且 `doc_meta`/`clause_revision`/`source_span` 是取证链承重墙（bbox 契约 §9.3 已踩坑两次）。
3. **可见性从第一天就是需求**：审计证实**同类失败已经发生过一次**——`unsupported_context` 在服务端算出来了、也进了 SSE，却在 `plugin/src/index.js:217-229` 的 `trimVerification` 白名单里被**静默丢弃**，而 `plugin/client/*.tsx` 对核验字段**零引用** ⇒ **算出来但没人看得见**。

### 10.2 步骤 1：撤销残留的"原始文档零外发"禁令（政策层，零代码）

**先查清"不能外发"到底限制了什么**，结果是一处**三份文档自相矛盾**：
- `ENCYCLOPEDIA.md` §16.2 **D1**：**删除"零外发"验收红线（2026-08-23 业主裁决）**；`INTRODUCTION.md:85` 记 D1→D2"外发可审计"；
- **但** 已移除的旧主计划 v4.3 §0.1 第 2 条仍写着 `[MUST NOT] 原始文档零外发 (Data Egress Zero-Trust)`：任何 PDF/合同/图纸**绝对禁止**上传至云端；
- 且**代码按它结构性地锁着**：`dry_run.py:413`「本函数**不接受** `deep_fallback` 参数」+ `:430` 恒 `False`、`preview_jobs.py:13`「零外发是**结构性事实**」、`routes_ingest_preview.py:49-51` 直接拒绝会外发的深度通道。
⇒ 业主的直觉是对的：**一条早该随 D1 一起删的 `[MUST NOT]` 留在了 REQUIREMENTS 里，并且真的在压制深度解析通道。**

**本步只改政策文档（不动代码）**：
- 旧主计划 v4.3 §0.1 第 2 条 → `[MUST NOT] 无留痕外发 (No Unaudited Egress)`：**禁止的从"外发"变成"不留痕的外发"**（= D2）。原文保留在引用块里存证。同时点明"Prompt 只含最小必要片段"是**成本与准确性的工程口径，不再是外发禁令**（送全库既贵又稀释相关性）。
- `ENCYCLOPEDIA.md` §16.2 追加 **D5** 记录该撤销；§1.5 红线 4 补一句交叉引用并注明"**它不是禁止外发，是要求外发留痕**"。

**为什么这一步单独提交**：解开代码锁要改测试（`test_dryrun_batch.py:173` 甚至直接断言批量函数签名里**不许**有 `deep_fallback` 参数——钉的就是那个结构锁本身），属契约变更，按"小步走"拆成独立一步做。
> ⚠ **自我更正**（2026-09-17 独立复核指出）：此处原写"要改**三个**测试文件"，**实际只改了 2 个**（`test_dryrun_batch.py` + `test_preview_jobs.py`）。`test_dryrun_report.py` **不需要也不应该**改——它断言的是"默认 `deep_fallback=False`"，而默认值没变，故继续成立。当时是**预判**而非实测，写成了既成事实。
**诚实边界**：本步**没有任何行为变化**——文档说可以了，代码仍然锁着，这个不一致要等步骤 2 才消除。

### 10.3 步骤 2：解开三处模块锁（代码 + 测试，契约变更）

**关键设计判断**：不能简单"把参数加回来"。读代码发现 2026-09-11 verifier 审计 P0-2 **是故意删掉**这个参数的，原话是"一旦有人改默认值就会**静默外发**，而批量侧**没有任何测试网**"。⇒ 旧修法用**结构禁止**换安全，代价是**永久封死**扫描件在预览里走深度解析。
新口径把它拆开：**默认值保持 `False`（安全性质不变）+ 补上当年缺的那张测试网 + 如实标注**，把"能不能外发"的决定权交还调用方并留痕，而不是由结构禁止。

**改动（4 处源码）**：
- `dry_run.py`：模块 docstring 从"零外发"改为"默认不外发 + 可显式开启 + 如实标注"（并写明改的理由与历史）；`analyze_preview_report` 的 `egress` 由**硬编码 `"none"`** 改为 `"none" if not deep_fallback else "deep_channel"`（**保守高报**：只要本次*允许*深度通道就报，哪怕该文档恰好有文本层根本不需要——宁可高报不可漏报，真实外发以 `egress_audit` 为准）；`preview_batch` **加回** `deep_fallback: bool = False` 并透传，批量总账的 `egress` 同口径。
- `preview_jobs.py`：`create_job(..., deep_fallback: bool = False)`，任务里记下该决定，worker 透传（用 `.get(..., False)` 兼容手工构造的旧任务字典）。
- `routes_ingest_preview.py`：`allow_deep=true` 从 **422 拒绝**改为**真接线**（单文件 / 批量 / 异步任务三处）。API 里**本来就有** `allow_deep` 字段，只是被拒绝——所以改动比预想小。

**测试（2 处替换 + 1 处新增，全部是"更可证伪"而不是放宽）**：
- `test_dryrun_batch.py`：原 `test_batch_preview_batch_has_no_deep_switch`（断言签名里不许有该参数）→ 换成 `test_batch_deep_switch_defaults_off_and_optin_really_wires_through`，断言**①默认值必须是 `False`（替代"结构性禁止"，防静默外发）②显式 `True` 必须真的透传到解析层（防"参数加了却不接线"的假修）③开启了必须如实标注**。原 `test_api_preview_deep_not_supported`（断言 422）→ 换成 `test_api_preview_allow_deep_is_wired_and_reported`（默认 `egress=="none"` + 显式开启 200 且 `egress != "none"`）。
- `test_preview_jobs.py`：**新增** `TestEgressContract` 两条 —— 异步路径默认必须是 `False`、显式 `True` 真的透传且被记进任务。**异步路径此前完全没有外发口径的测试**（这正是 2026-09-11 那句"批量侧没有任何测试网"的同一个洞）。
- 实测：改动后**只有 2 条测试红**（就是钉住旧契约的那两条），**61 条其余全绿**——反证"默认值保持 `False`"这个决定是对的，它让所有既有安全断言继续成立。

**验证**：`pytest` **1216 passed / 3 skipped / 0 failed**（基线 1214 → **1216，只涨不跌**，新增 2 条）；`mypy` 122 files 0 errors；本次未触碰 TS/前端 ⇒ tsc 与 smoke 段不受影响。
**诚实边界**：① 未对**真实云端**做端到端验证——测试全部用 monkeypatch 拦在解析层之前，即"参数确实透传到了解析入口"是实测的，而"云通道真的被调用并留痕"**未实测**（`test_mineru_cloud.py` 已有覆盖，属另一条链）。② `egress` 是**请求级保守口径**而非"本次真的外发了"；要精确答案看 `egress_audit`。③ 前端尚未消费 `egress != none`（可见性需求属 Phase B）。

### 10.4 独立复核 D5 后的收口（F1~F6）

派独立 verifier 复查两个提交，它复现了基线（1216/3 skipped、mypy 0），**确认了 5 项主张**（默认不外发 5/5 路径实测、opt-in 真的到云通道入口、egress 不漏报、新测试经 4 个变异体双向可证伪、文档基本一致），并给出**剩余自设限制清单**。它抓到的缺陷与处置：

- **F4（真实破口，已修）**：`allow_deep` 原为 `bool(body.get("allow_deep") or False)` ⇒ JSON 字符串 `"false"` 是**真值**，"传 false"反而**开启外发**，与"默认安全"直接冲突。我先**写测试看它变红**（实测 `allow_deep='false'` → **200 被接受**）再修：新增 `_parse_allow_deep()` 严格布尔校验，`"true"/"false"/1/0` 一律 422，三处路由统一。
- **F2（潜在默认外发，已修）**：`pipeline.analyze_preview()` 调 `run_parser_isolated(..., force_deep=False)` **不传 `deep_fallback`** ⇒ 吃默认值 **True** ⇒ 扫描件会走云优先深度通道；其 docstring 还写着"不调 MinerU 深度模型"——**把 `force_deep` 误当成深度通道开关**，正是 `dry_run` docstring 亲自点出的那个陷阱。已显式传 `False` + 更正 docstring。**可达性当前为 0**（非测试调用者不存在）⇒ 潜在而非活的 P0。
  > **附带一次"被测试挡住"的记录**：我顺手给该函数返回体加了 `egress: "none"`（想让口径统一），
  > 结果 `test_dry_analyze_preview_contract_frozen` 立刻变红——它**冻结**了这个老接口的键集合。
  > 判断：本函数既已恒不外发，调用方不需要该字段；为"口径好看"去动冻结契约不划算。
  > ⇒ **撤回该字段、只保留实质修复**，并在 docstring 注明"若将来本函数要支持外发，**那时**
  > 再走契约变更流程加字段"。**冻结测试起作用了，就该听它的。**
- **F3（控制面缺标注，已修）**：异步任务 API（`_public_view`）**不外露 `egress`**，而 routes 的 docstring 声称"响应里**始终**带 `egress`"——doc 与 code 不符，且调用方开启外发后拿不到任何标注。已补 `egress` 字段并加断言。
- **F1（P2，本轮最重要，**尚未修**）**：**能力被产品层结构封死**。`plugin/src/ingest.js:251` 明写「只透传白名单字段；`allow_deep` 不暴露（预览零外发是产品性质，不给开关）」，三处白名单（:252-256 单文件 / :289-327 批量 / :583-603 异步任务）**都不转发 `allow_deep`**；`allow_deep` 在整个 `plugin/`（含已构建 `client.js`）**只出现在那一行注释里**，UI 仍承诺"不外发（深度通道已禁用）"（`KsIngestPanel.tsx:19/336`），且 `scripts/dsh-gui-e2e-ingest.ps1:94` 把该文案钉成 E2E 断言。
  ⇒ **D5 想解开的能力，在用户可见的产品上一点没变——只是把锁从引擎搬到了插件桥。** 两个提交都没碰这一层。**这是下一步（步骤 3/产品桥）的全部内容。**
- **F5（陈旧表述，已修引擎侧）**：`server.py:3022`、`deepseek_client.py:3`（"零外发红线"→"Prompt 最小化，成本与准确性口径"）、`fewshot.py:3`（"不做微调（零外发下不可行）"——该理由**当年也不成立**，本地微调本就不需外发；已标注为工程选择而非禁令）、`ENCYCLOPEDIA.md:429`（唯一仍把旧禁令当**当前政策**陈述的文档行）。另**自我更正** §10.2 里"要改三个测试文件"→ 实测只改了 2 个（当时是预判写成了既成事实）。
- **F6（既有 flaky，非本次引入）**：`test_preview_jobs.py:117` 在"相关子集"命令下约一半概率红（`assert 0 >= 1`）。verifier 在**改动前**的提交上复现了同样的抖动 ⇒ 与本次无关，但**任务书建议的正是那条会摇的子集命令**，容易误判。
- **verifier 的诚实披露**：它第一次跑变异体时未设 `KS_MINERU_DEEP=0`，约 10 分钟后被强杀；事后核查**未发生云外发**（云 Key 在 `<KS_DATA_DIR>/secrets.json`，而 pytest 把 `KS_DATA_DIR` 重定向到临时目录 ⇒ 测试环境云通道不可用；测试库与生产库 egress 行数均为 0）。

**本步（步骤 2.5/引擎收口）**：修 F4 + F2 + F3 + F5（引擎侧），新增 1 条 API 严格性测试 + 2 条异步 egress 断言。**F1 留作下一步**（产品桥 + UI 文案 + E2E 断言）。

### 10.5 步骤 3：打通产品桥（F1）+ 修掉给限制站岗的测试 + 修既有 flaky

**这是 D5 真正"能被用到"的一步。** 上一个提交只把引擎做对；独立复核指出**能力在用户可见产品上仍不可达**——锁从引擎搬到了插件桥。

**根因（比"漏改一处"更值得记）**：`plugin/scripts/smoke-ingest.mjs` **主动断言了这个限制**，还把它命名为护栏：
```
check('preview DROPS allow_deep / deep_fallback / unknown keys (zero-egress guard)', …)
check('job start forwards dir/batch_size only (zero-egress guard)', …)
```
⇒ 桥丢弃 `allow_deep` 是**被测试保护的"特性"**，所以引擎侧解开后**没有任何红灯**，缺陷完全隐形。
**教训：清查"自设限制"时必须连测试一起看——限制常常被写成断言，撤掉限制反而会先撞红。**

**改动**：
- `plugin/src/ingest.js` 三处白名单（单文件 :251-261 / 批量 :333-334 / 异步任务 :612-613）改为**转发 `allow_deep`**；桥只做**严格布尔**转发（`body.allow_deep === true`），不替引擎下判断。
- `plugin/client/api.ts`：三个调用函数加 `allowDeep`（**只为真时才发字段**）、`KsIngestPreview.egress` 类型由 `'none' | 'mineru_cloud'` 改正为 `'none' | 'deep_channel'`（原类型与引擎实际返回值不符）、`KsIngestJobView` 补 `egress`、陈旧注释（"恒 true"）改正。
- `plugin/client/KsIngestPanel.tsx`：**新增「允许云深度解析」复选框（默认关闭）**——把"会外发"直接写在标签里；`egress` 的渲染不再打印原始枚举（"外发 deep_channel"读起来像"本次真的发出去了"），改为如实措辞："已允许云深度通道——扫描件会上传云端（本次是否真的上传取决于该文档有无文本层；精确记录见外发审计）"；模块 docstring 与 `:336` 文案同步。
- `plugin/client/KsSettingsSection.tsx`：hint 由"不写库不外发"改为"不写库；默认不外发（可显式开启云深度解析）"。
- `scripts/dsh-gui-e2e-ingest.ps1`：原断言钉的是旧承诺文案（"不写库、不移动文件、不外发"），改为钉**新**口径，并**加一条**断言检查开关存在（`允许云深度解析`）。
- `plugin/scripts/smoke-ingest.mjs`：两条 `zero-egress guard` 断言改为**反向**（`allow_deep` 必须转发；`deep_fallback` 与未知字段必须丢），并**新增一条**"非布尔 `allow_deep` 不得被转发"（桥不放大真值；权威校验在引擎）。**37 → 38 条**。
- **F6 既有 flaky 修掉**：`test_preview_jobs.py` 的 abort 用例原先只等 `status=='running'` 就中断，而 worker 是**先置 running 再处理第 1 件** ⇒ `done` 常为 0 ⇒ `assert done >= 1` 约**一半概率红**（复核在改动前的提交上同样复现，与本次无关）。改为**等"至少完成 1 件"再 abort**——本用例要证的就是"已完成的行被保留"，先有已完成的行是把不确定性消掉，而不是放宽断言。实测**连跑 6 次全绿**。

**门禁**：`pytest` **1217 passed / 3 skipped / 0 failed**；`mypy` 122 files 0 errors；`tsc` 0；`smoke` 11 段全 PASS（**ingest 37 → 38**）；`verify:commands` 15/15。
**诚实边界**：① 新增的 UI 开关与文案**未做真机点击验证**（E2E 脚本已同步断言，但本轮没起 GUI 跑）；② 未对真实云端做端到端验证；③ "允许云深度解析"是**每页面板的临时勾选**，不落盘、不开记忆——刷新即回到"不外发"，这是刻意的（默认安全优先于便利）。

### 10.6 步骤 4：`standard_name` 副本后缀——先归一派生，再修数据（代码半）

方案 §4.1 说这是 Track L"自动入库"的前置项。**先修数据是错的顺序**：查清后发现这些脏名不是从内容里读出来的，而是**入库时从文件名派生**的，且**各调用方各派生各的**——不先归一派生，灌一次库又脏一次。

**清查出四个派生点**（都不干净）：
- `src/core/storage/write_queue_bootstrap.py:31`（watcher 闭环，**未来数据的主要来源**）：`name = path.stem` —— 原始 stem，同时带着标准号前缀与副本后缀 `(1)`；
- `scripts/_stdparse.py:24-27`（`driver_v2` 用）：先算出干净名，**紧接着又用原始 `stem` 覆盖回去**（`name = stem.replace(std_no, "", 1)`）⇒ `(1)` 回来了；而且 `std_no` 是 ASCII `/` 而 stem 是全角 `／`，那次 `replace` **根本不命中**；
- `scripts/std_bulk_import.py:175`：`meta.get("name") or p.stem` —— 两者都可能带后缀；
- 库里已有 **:139 行**（数字随灌库在涨；独立复核时报 135）`standard_name` 形如 `电梯技术条件(1)`。

**新增共享归一派生**（`src/core/text_utils.py`，就在 `canon_standard_no`/`standard_key` 旁边）：
- `strip_duplicate_suffix(name)`：**只吃结尾**的 `(数字)`（半角/全角括号都认）。库内有 **:312 行**合法括号名（`聚丙烯(PP)树脂`、`湿式(非金属类)摩擦材料`、`额定电压1kV(Um=1.2kV)…`）**必须原样保留**——测试逐条钉住；
- `clean_standard_name(raw, *, standard_no=None)`：全角斜杠归一并压空白 → 去结尾副本后缀 → **按"号 + 年"剥开头标准号**（容忍 `GB` vs `GB/T` vs `GBZ` 与各类破折号）。三个调用方改走它。

**过程中被自检抓到的两个错（都已修，值得记）**：
1. **复用了错的判据**：我最初拿 `_RE_STD_KEY` 去取"号 + 年"，但它要求号是 **3~5 位**（那是为"从页眉抽比较键"设计的）⇒ 真实标准号里的 **1 位号**（`GBZ 1-2010`、`GB/T 1.1-2020`）**永远剥不掉**。自检报告直接暴露（`GBZ 1-2010 工业企业设计卫生标准` 原样返回），改为宽松判据后即通过。
2. **作用域越界**：`clean_standard_name` 会顺带把**表意空格 `U+3000` 与全角斜杠**归一，于是 312 行里有 **3 行**也会被"改动"——那不是本次要做的。⇒ **数据回填只允许用 `strip_duplicate_suffix`**（它按定义只动结尾 `(N)`，那 312 行可证明不受影响）；`clean_standard_name` 只用于**入库派生**。这条分工写进了函数注释。

**门禁**：`pytest` **1220 passed / 3 skipped / 0 failed**（1217 → 1220，新增 3 条）；`mypy` 122 files 0 errors。
**诚实边界**：① 本轮**只改代码，还没动库**——那 139 行仍然是脏的（下一步做回填，单独提交、单独快照）；② `derive_standard` 产出的标准号**不带空格**（`GB/T10058-2023`）与 `doc_meta` 的写法不一致，这是**既有**行为（`driver_v2.py:185` 有注释），本次**故意不动**（改它会影响 bulk import 查重），只在测试里钉住；③ `write_queue_bootstrap` 是 watcher 闭环入口，其派生路径**未做端到端真机验证**（要触发 watcher 灌一份 `…(1).pdf`）。

### 10.7 步骤 5：回填已有脏数据（数据半）——并把"只剥一次"的 bug 抓出来

新增 `scripts/fix_standard_name_suffix.py`（**默认 dry-run**，`--apply` 才写）：
- **只**用 `strip_duplicate_suffix`（不做全角/空白归一，避免越界改动那 312 行合法括号名）；
- 写前 `backup.create_snapshot("manual")`（`VACUUM INTO` + 校验和；**手动快照永不被自动清理** ⇒ 随时可回滚）；
- 单事务逐行 `UPDATE` + 每行写一条 `operation_log`（`operation=fix_standard_name_suffix`，detail 记 旧值→新值）；
- **写后复验**：同一判据再跑一次，报告剩余数；
- 幂等（第二次运行报 0）。

**执行结果**：写前快照 `snap_01M2QH8EA6MRVWXHSV5CB31W4S`（checksum `172471a28e22144f…`）；第一次更新 **139 行**，但**写后复验报"仍有 5 行"**——这个看似失败的数字恰恰是自检的价值所在。

**根因：我的 `strip_duplicate_suffix` 一趟只剥一个后缀**。库内真实存在**双重后缀** `…测定方法(1)(1)`：
```
旧: 煤和岩石物理力学性质测定方法 第15部分：岩石膨胀应力测定方法(1)(1)
新: 煤和岩石物理力学性质测定方法 第15部分：岩石膨胀应力测定方法
```
`re.sub` 用锚定 `$` 的模式，引擎扫过之后不再回头 ⇒ 只吃掉最后一个。修法：**循环剥到稳定**（每轮长度严格减小，必然终止），并补测试（`(1)(1)`、`(1)(2)(3)`、`（1）(2)`）。修完再跑 `--apply --no-backup`（**为什么跳过第二次备份**：同一操作 2 分钟前刚取过快照，那张才是"改动前"的回滚点；再复制一份 2.2GB 只是冗余），清掉最后 **5 行**，**写后复验 = 0**。

**独立复验（最强证据）**：把现行库与那张写前快照**逐行对比**（`var/tmp/verify_backfill.py`，两库均 `mode=ro`）：

| 项 | 结果 |
|---|---|
| `standard_name` 变化的行数 | **139**（= 候选数；其中 5 行需要两趟 ⇒ **共去掉 144 个后缀**） |
| 除 `standard_name` 外被改动的列 | **0** |
| 不满足 `strip(旧) == 新` 的 | **0** |
| 变成空名的 | **0** |
| 行数变化（插入/删除） | 0（6417 → 6417） |

> **一处自我更正**：复验脚本里我写的预期是"144 行"，实际报 139 —— **是我算错了**：那 5 行**本来就在 139 个候选里**（首次更新把它们从 `(1)(1)` 变成 `(1)`），不是额外的 5 行。**139 个不同行 / 144 个后缀**才对。脚本的预期值写错不影响结论（另三项都是 0），但记在这里以免以后误读。

**门禁**：`pytest` **1220 passed / 3 skipped / 0 failed**（双重后缀的断言加在**既有**测试函数里，故用例数不变；仍是只涨不跌：本轮起点 1217 → 1220）；`mypy` 122 files 0 errors。
**诚实边界**：① **生产库已被修改**（139 行 `standard_name`）——回滚路径 = 快照 `snap_01M2QH8EA6MRVWXHSV5CB31W4S`，但**恢复动作需停写后替换 db 并重连**（`restore_snapshot` 只返回路径，替换由上层做），我**没有实测回滚流程**；② `file_path` / 磁盘文件名**一律未动**（那些文件确实叫 `…(1).pdf`，改名会牵动路径与查重，超出本步范围）；③ 手动快照**永不被自动清理**，每份约 2.2GB —— 已在 `backups/` 累积 9 份，建议你定期人工清理旧的手动快照（这是**设计如此**，不是 bug）；④ 那 139 行改名后，**引用/检索侧未做回归验证**（标准名只用于展示与匹配，`standard_no` 未动；但"名称参与匹配"的路径未逐一排查）。

### 10.8 Phase A 起步：材料平面建表 + 仓库层（第一步）

**先立"平面"，不碰法条链。** 新增三张**全新**表（`schema.sql`，`CREATE TABLE IF NOT EXISTS` ⇒ 对既有库是纯增量，无需 ALTER）：
- `material_project`：项目（含 `authority_policy` = **轴 B 的项目级效力声明**，JSON）；
- `material`：材料。**轴 A** `source_tier`(T0~T4) + `tier_source`(system/user) + `tier_evidence`(JSON)；
  **轴 B** `task_role`(criterion/reference)；`review_status`(pending/approved/rejected)；
  `lifecycle`(ephemeral/promoted)；`doc_id`（Track L 入法规库后**从材料侧回指**）；
- `material_chunk`：切片 + **字符区间** `char_start/char_end` + `page`（引用要能点回原文位置）。

**为什么另立平面**（写进 schema 注释）：`doc_meta.standard_no TEXT NOT NULL UNIQUE` **结构上装不下**
财报/新闻；且 `doc_meta`/`clause_revision`/`source_span` 是取证链承重墙（bbox 契约 §9.3 踩坑两次）。

新增 `src/core/storage/material_repo.py`（**只碰这三张新表**）：
- 默认值体现两条纪律：新材料 **`pending`**（未经评审不得用）、**自采默认 T3**（网上找来的没证据前不该默认可信；用户自有原件才是 T1）；
- **`approved_materials()` 是硬门**——凡要拿材料去"用"的路径都必须经它，不许自己拼条件过滤；
- `set_tier(..., source='user')` 记录**是谁定的层级**（业主明说"用户可以改"，留痕是为了日后看得懂当时的判断，不是限制）；
- `set_task_role` 独立于 `source_tier`——**两个轴不合并**（公司制度例：来源 T1 低，却是本任务的准则）。

**测试 24 条**（`tests/test_material_repo.py`），其中三条是"纪律级"的：
① **硬门**：`approved_materials()` 恰好只含 approved（pending 与 rejected 都进不去），而管理列表仍看得见它们（否则没法批）；
② **两轴不合并**：`task_role='criterion'` 不影响 `source_tier`（可同时成立）；
③ **与法条链零耦合是行为级证明**：跑一遍材料操作（建材料/切片/评审/改层级/声明效力/升长期/回指 doc_id）前后，
`doc_meta`/`clause_revision`/`source_span` **三张表行数完全不变**——不是靠"我记得没写"。

**过程中暴露并修好一个真实交互**：加入 FK 后，`tests/test_retrieval.py` 的 `seeded_db` fixture 让 **10 个用例在 setup 阶段 ERROR**（`FOREIGN KEY constraint failed`）。根因：该 fixture **逐表 DROP**，而 `sqlite_master` 是**创建顺序**——我按 `material_project → material → material_chunk` 建表，于是先 DROP 被引用者、引用者还在，`foreign_keys=ON` 下直接失败。修法：**DROP 前先 `PRAGMA foreign_keys=OFF`，建完 schema 再打开**（"一次删光所有表"本就与外键顺序无关）。全仓只有这一处用该模式（已 grep 确认）。

**门禁**：`pytest` **1244 passed / 3 skipped / 0 failed**（1220 → 1244，新增 24 条）；`mypy` **123 files** 0 errors（+1 新模块）。
**诚实边界**：① 只有**表 + 仓库层**——**没有解析、没有 API、没有 UI**，所以现在还"用不了"（下一步做材料解析切片）；② 新表对**既有库**要等引擎下次 `init_schema()` 才建出来（本次**未重启引擎验证**）；③ `materials_dir()` 只保证目录在 `data_dir` 下并按项目分目录，**尚未接入收件/复制逻辑**；④ T0~T4 的**判级规则**（域名权威清单等）**尚未实现**，目前层级只能由调用方传入或用户手改。

### 10.9 Phase A 第二步：材料解析与切片

新增 `src/core/ingestion/material_ingest.py`。

**关键判断：不复用条款切分。** 法规入库按**条款号**切成三型知识单元（要逐条取证）；
材料不是条文（财报/公告/帖子/研报），硬套 `split_items_into_clauses` 只会切出碎片且丢上下文。
⇒ 材料按**段落**聚合成块，只保留"能指回原文位置"的最小契约：`char_start/char_end/page`。

- **解析**：PDF 走既有 `run_parser_isolated(..., deep_fallback=False)`（子进程隔离 → 复用成熟路径），
  按 `page_number` 聚合 blocks；DOCX 用 python-docx 取段落、**整体算第 1 页**（docx 没有页概念，
  **不假装有页号**）；TXT/MD 整体第 1 页。**默认不外发**（无文本层就不解析）——与 D5 口径一致。
- **规范全文 + 页区间**：`build_document()` 把各页用 `"\n\n"` 拼成全文并记录每页字符区间，
  **所有块偏移都是对这篇全文的绝对偏移**（这是引用能点回位置的唯一依据）。
- **切片**：逐行累加、超 `max_chars`(900) 先落块；单行本身超限则**硬切**（否则一行几万字的
  材料只出一块，检索粒度退化）；空行只是分隔符。
- **收件**：`ingest_project_dir()` 扫项目目录逐份登记（单份失败不中断整批，沿用批量预览范式）；
  **查重**按 `content_hash`（重复放同一份不产生两份材料）；**自包含存储**——文件在项目目录外
  就复制进来（材料平面要能被独立备份/清理）；**解析不出文本的扫描件仍登记**，只是 `chunk_count=0`
  并在 `tier_reason` 里如实说明（**既不假装可用，也不悄悄丢掉**——两种都会让用户以为"放进去了"）。

**测试 21 条**，核心是那条**保真不变量**：`全文[块.start:块.end].strip() == 块.text`
逐块回验。区间一旦对不上，"引用可点回原文"就是假的——所以这条钉在最前面，
文本/PDF/DOCX 三条路径、硬切与超长行都验。

**门禁**：`pytest` **1265 passed / 3 skipped / 0 failed**（1244 → 1265，新增 21 条）；`mypy` **124 files** 0 errors。
**诚实边界**：① 仍**没有 API / UI / 检索**——文件只能由代码放进去，界面还看不到；② 只支持
PDF/DOCX/TXT/MD，**图片类材料（要走 OCR）未做**；③ PDF 走的是**文本层**路径，扫描件在默认
（不外发）下拿不到内容，需显式 `deep_fallback=True`——**该显式路径未做端到端真机验证**；
④ 切片未做去重/重叠（同段落不会被切两次，但相邻块之间**无重叠**，跨块语义可能被切断，
需检索侧配合）；⑤ 未做**材料全文的检索索引**（下一步）。

### 10.10 Phase A 第三步：已批准材料上的检索 + 可点回原文的引用（**Phase A 验收达成**）

**分词只有一个所有者**：新增 `text_utils.segment_for_fts()`（jieba `cut_for_search` + 空格连接），
把 clause 侧原有的私有 `_seg` 改为**委托**它。理由：`clause_fts` 与新的 `material_fts` 都靠
"先分词、再交给 `tokenize='ascii'` 的 FTS5"这条口径——**只要出现第二份实现，两条检索线早晚分叉**
（分叉的症状是"同一句话在法条里搜得到、在材料里搜不到"，最难查）。

新增 `material_fts`（虚拟表，口径与 `clause_fts` 完全一致）；`add_chunks()` 同步写索引（**单一写路径**）；
新增 `search_materials()`：

- **评审硬门写死在 SQL 里**：`JOIN material … AND review_status='approved'`。即使调用方忘了过滤，
  也**拿不到未批准的材料**——硬门不能靠"调用方记得"（这是 Phase A 验收"未批准不得进入分析"的落点）；
- 返回结构同时给出**两个轴**（`tier_label` + `role_label`），免得读者以为只有一个"可信度"；
- FTS 语法异常**不抛**（无命中优于把提问打成 500），并有测试钉住 `'"('` 这类输入。

**验收测试（方案 §9 的 Phase A 验收原文）**：`放一份 PDF → 评审通过 → 提问 → 引用能点回该 PDF 的位置`
——`test_material_ingest.py::TestPhaseAAcceptance` 把四个部件串起来跑：收件（默认 pending）→
**未批准时搜不到** → 评审通过 → 检索命中（含 `page=1` 与层级标注）→ **用引用区间在重新解析的全文上
取回同一段文本**，并验证 `page_of(char_start) == page`。另有一条：扫描件在默认不外发下
`chunk_count=0`、**即使批准了也搜不到内容**（不是把空内容当依据）。

> **又被自己的验收测试抓到一个真 bug（值得记）**：跨页块的文本原先用 `"\n".join(行)` **重建**，
> 而规范全文的页间分隔是 `"\n\n"` ⇒ 块文本与 `char_start/char_end` **对不上**（`\n\n` 被压成 `\n`）。
> 这**正是"引用点回原文"会失真的地方**，而先前那条"保真不变量"用了 `.strip()` 兜底、
> 且测试数据没让它跨空行，所以没暴露。修法：**块文本一律从原文切片得到**（`emit()` 对 `[start,end)`
> 取子串并收紧区间），不再手工 `join`；同时把那两条不变量断言**收紧为逐字相等**（去掉 `.strip()`），
> 并补一条"跨空行的块必须原样保留分隔符"的用例。

**门禁**：`pytest` **1276 passed / 3 skipped / 0 failed**（1265 → 1276）；`mypy` 124 files 0 errors。
**诚实边界**：① 检索是 **FTS5 关键词命中**，**没有向量/重排**——语义相近但用词不同的材料可能搜不到
（法条侧有六通道，材料侧暂只有一路，这是有意的起步口径）；② **答案生成尚未消费材料**：本步只做到
"检索 + 引用的字段齐备"，把材料喂进答案与产出物（两轴标注、T3 不得单独承重）属 **Phase B**；
③ **无 API / UI**，所以现在仍只能由代码驱动（GUI 的评审界面属后续）；
④ 未做材料检索的**准确率门禁**（法条侧有 Golden Set，材料侧尚无）；⑤ 跨块无重叠 ⇒ 提问命中跨越
块边界的信息时可能只捞到半句。

### 10.11 Phase A 第四步：材料平面 API（让你**真的能碰**）

Phase A 前三步把引擎做通了，但**业主碰不到**——验收句里的"放一份 PDF"与"评审通过"都只能由代码干。
本步把那条链开成端点：新增 `src/core/api/routes_materials.py`（13 个端点）+ 在 `create_app()` 注册。

端点：建项目 / 列项目 / 列参考资料文件夹（inbox）/ **扫描收件** / 列材料（评审视图，含 pending）/
**已批准材料检索** / 单份材料 / **切片分页**（评审必须能读到内容，否则是"盲签"）/ 批准拒绝 /
改层级（轴 A）/ 声明任务效力（轴 B）/ 一次性↔长期 / 删除 / 层级定义。

**两条纪律在端点层重申**（写在模块 docstring 里，防止后来者在 API 层"顺手"另起一套）：
1. `search` **必须**走 `material_repo.search_materials()`——评审硬门写死在那条 SQL 里，
   端点层不得自己拼查询；
2. **枚举校验交给仓库层**（抛 ValueError）→ 端点层统一转 422。判据只有一个所有者。

**测试 15 条**（`tests/test_material_api.py`）。重点不是"每个端点都 200"，而是：
- **硬门在 HTTP 层同样成立**：未批准 → `/search` 查不到；批准后查得到；再改成 rejected → 又查不到；
- **端到端用户闭环**：建项目 → 丢文件 → scan → **读切片确认内容** → 批准 → 检索命中且引用字段齐备；
- 校验严格：非法枚举一律 422（不是当默认值放过）。

> **又被自己的测试抓到一个真 bug**：`/api/v1/materials/tiers` 返回 404——因为 FastAPI **按注册顺序**匹配，
> 而我把 `/api/v1/materials/{material_id}` 注册在它前面，字面量 `tiers` 被 `{material_id}` 捕获了。
> 修法：把字面量路径**移到** `{material_id}` 之前，并在代码里留注释说明顺序约束（`test_tiers_endpoint_lists_all` 钉住）。

**门禁**：`pytest` **1291 passed / 3 skipped / 0 failed**（1276 → 1291）；`mypy` **125 files** 0 errors。
另：`ENCYCLOPEDIA` §10.2 的端点底数（127/113）**又过期了**（+13），已在那处加注"引用底数前必须重扫"。
**诚实边界**：① **还没有 GUI**——端点通了，但界面上仍看不见，材料只能"手动放进文件夹再调 API"；
② **答案生成仍未消费材料**（Phase B）；③ **未对真实引擎做端到端调用**（引擎当前跑的是旧代码，
需重启才会加载新路由与新表——本步只做了 TestClient 级验证）；④ 未做**文件上传端点**：收件仍是
"把文件放进项目文件夹再 scan"（与方案 §9 的"先走放文件夹+扫描，GUI 上传留后"一致）；⑤ 未做分页
之外的排序/筛选（按创建时间倒序）。

### 10.12 Phase B 第一步：把"可信度"从标签变成**可执行规则** + `unsupported_context` 接通上下文

业主的原话是"**要对材料可信度进行判别，而不是随便找个什么网络文章就当权威信源**"。
光给材料贴 T0~T4 标签**不够**——必须有人按标签拒绝/降级，否则标签只是装饰。

**① 两轴权威模型**（`src/core/materials/authority.py`，新）
- `TIER_BEHAVIOUR` 是**承重规则的唯一所有者**：T0/T1/T2 = 可作依据；T3 = **只作线索**，
  **≥2 个独立来源**才可作辅证；T4 = **禁止用于结论**（仍如实列出，标"已知不可用"——
  不假装它不存在）。
- `assemble_evidence()` 按**承重能力分组**（准则 / 可作依据 / 互证辅证 / 仅线索 / 已排除），
  **不是排序**。本模块**刻意不提供"按一个分数排序材料"的函数**：那必然把业主裁定的两个轴
  （来源可信度 × 任务内效力）压成一个，公司制度例必错。
- **独立来源按域名判**：同一站点转载两篇**不算**互证（最常见的假互证，有专门用例钉住）。
- `usable_hits()` 是"要产出结论"的安全入口（准则+依据+辅证），`leads_only` 与 `excluded`
  **不在**里面——并在 docstring 里警告：要展示线索请用完整结构，别用本函数（否则把
  "只能当线索"的东西漏到可见性之外）。
- **测试 17 条**（`tests/test_material_authority.py`）。

> **我自己的测试先红了一次**，红得对：断言写"渲染里要有『参考』"，而该材料的 `task_role`
> **未声明**，诚实标注应是「未声明效力」。**代码是对的，测试是错的**——改成断言 `role_label`
> 本身，并补一条"声明了轴 B 之后渲染出『本任务准则』"的用例。

**② `unsupported_context` 接通（上下文半）**——审计结论是"**算出来但没人看得见**"：
引擎算了、SSE 也发了，却在 `plugin/src/index.js` 的 `trimVerification` 白名单里被**静默丢弃**。
- 把纯函数裁剪层抽成 `plugin/src/trim.js`（**零依赖**）⇒ `plugin/scripts/smoke-trim.mjs` 能调
  **真代码**。抽出来的理由就是可测：原先埋在 `index.js`（顶层 import DSH 包）里，node 只能
  "复刻算法"或"字符串匹配源码"，两者都会漂移。
- 新增 `trimUnsupportedContext()`：**逐字段**透出（clause_number / standard_no / verdict /
  reason），`reason` 单独给 400 字符上限并**显式标 `[已截断]`**。
  **不走**通用 `compact()` 的理由是实测出来的：后者把整条 JSON 化再截 160，
  这条真实 reason 走通用路径后 `len=158`、**中文原因被切断**——正好复现该字段本要修掉的
  "告警不可执行"毛病。**冒烟里用真 `shortList` 做对照**（不是手算）钉住这个差别。
- `ks_answer` 工具描述加**强制披露**指令：`MUST disclose`、两种 verdict 的含义
  （`same_standard_not_retrieved`=检索漏召回，不是编造；`outside_evidence_standard`=越界或可能编造）、
  `Never present such a citation as support`。**只送字段不指示动作 = 把"静默丢弃"换成"静默不理会"。**
- **反回归的机制**（这是本步最值钱的部分）：冒烟**从 `src/core/llm/ks_answer.py` 源码解析**
  引擎的真实 verification 字段集，**逐键探测**是否被转发；将来引擎加字段而桥忘了转发，
  **冒烟立刻红**，不依赖任何人记得。反向也查（白名单里不许有引擎不发的键 = 死转发）。

> **冒烟第一次跑就抓到我一条不成立的论断**：我断言"真实 reason >160 字符所以通用路径必切断"，
> 实测 **94 字符**。让它失效的不是 reason 长度，而是**整条 JSON 化后的长度（201）**——
> 键名+标点就占掉近百字符。断言改成用**真代码**对照 + 断言正确的量，并在注释里写明实测数值。

**③ UI 半**：座位已查明（`cordis_inspect` 查 Slot 树）= **`tool.call.toolview`**，`key='ks_answer'`
（该 key **当前无人占用**）。⚠ 但它 `replaceRisk: shadows-shipped-ui` ⇒ 注册会**顶掉**该工具
调用的默认渲染，**必须整卡自绘**，不是"只加一段"。故**单独一步**做（B-3），不塞进本步。

**门禁**：`pytest` **1308 passed / 3 skipped / 0 failed**（1291 → 1308，+17）；`mypy` 0 errors（125 files）；
`tsc --noEmit` 0；`smoke:trim` **25/25**；`smoke` 全链 12 段；`node --check` 两个宿主模块语法 OK。

**诚实边界**：① 逐主张级 T3 互证（语义聚类）**未做**——当下是**批级**判定，已在代码里注明
（批级互证只把线索升到"辅证"，**不会**升到"可作依据"，故偏保守）；② **答案生成仍未消费材料**
（`assemble_evidence` 已可用，但答案链尚未接它——那是 Phase B 的下一步）；③ UI 半未做（见③）；
④ 引擎仍在跑旧代码，新路由/新表**要重启才生效**；⑤ `knowledge_types_involved`（SSE 专有）仍未转发，
与 UI 展示一并评估。

> **门禁噪声（如实记）**：全量跑出现过 **1 次** `tests/test_deep_server.py` 失败，同文件单独跑
> **8/8 通过**，紧接着的全量跑又全绿 ⇒ 判定为**既有间歇性失败**（该文件用 10s 超时 + 轮询线程，
> 对 CPU 争用敏感；本步只新增测试与独立模块，与它无调用关系，但新增 17 条测试**改变了整轮时序**、
> 可能把它暴露出来）。失败用例名被控制台编码打乱，**未能确证**，故不点名。
> 随后用 `PYTHONIOENCODING=utf-8` **连跑 3 轮全量：1308 passed / 3 skipped / 0 failed ×3** ⇒ 未复现。
> 见 `MATERIALS-PLANE-PLAN.md` §12 待办。

### 10.13 独立复核 Phase A 的结论与收口（verifier 参与，2026-09-17）

独立子代理在**隔离 worktree**（钉在 `b8579f6`，独立 `KS_DATA_DIR`，未改任何受控文件）复核
Phase A 的三次提交，7 项声明全部给出结论。**CONFIRMED**：法条链零改动（静态正则 0 命中 +
行为级 5 张表内容 SHA/DDL 哈希不变）、切片保真（**4000 份模糊文档，0 反例**）、
脏查询打不崩提问（54 个畸形查询全部返回列表）、schema 对既有库**只增不改**
（16 个新对象全为 `material*`，旧表行数与列清单逐项相同、二次初始化幂等）、
分词重构**与生产库 200 行真实语料逐字节一致**。

**被复核推翻/收窄的**：① 我原先在 `material_repo` 的 docstring 里写"`approved_materials()` /
`search_materials()` 是**唯一入口**"——**说过头了**：硬门是**函数内**保证，**不是数据库强制**
（无 view / trigger），且本模块**故意**另有三处不设门的读函数（评审人要读正文才不是盲签）。
已把 docstring 改成**精确边界**并点名那三个函数"任何产出结论的路径都不得使用它们"（缺陷②）。
② 验收测试 docstring 写"逐字验证"而断言用了 `.strip()` ⇒ 断言的量改成**不 strip 的逐字相等**，
并在类 docstring 里写明该验收**读不到**的三件事（无答案链、引用基于重解析文本、页号非独立几何核对）。

**修掉的缺陷**（按严重度）：
1. **MEDIUM — `chunk_text(max_chars<=0)` 死循环**（`material_ingest.py`）。硬切循环里
   `seg_end = min(off + max_chars, line_end)`，`max_chars<=0` 时 `seg_end == off` ⇒ 指针不前进。
   **我自己复现过**（subprocess + 12s 超时：`100→1` 块、`1→10` 块正常，**`0`/`-5` 超时不终止**），
   修复后再跑同一探针：`0`/`-5` 改为 **exit=1 + `ValueError`**。
   修法：新增 **`_require_positive_max_chars()` 作为参数规则的唯一所有者**，两个公开入口都调它
   （关键：`ingest_material_file` 里 `chunk_text(...) if text.strip() else []` 会让**空文本绕过校验**
   ——同一个参数两种命运，校验因此前置到碰文件之前）。**抛错而不夹紧到 1**：静默夹紧会把调用方的
   参数 bug 藏起来。回归测试 9 条（含 bool 也被拒、空文本也拒、合法小值仍能硬切）。
2. **LOW-MEDIUM — `search_materials` 的兜底 `except Exception`** 会把"表没了 / SQL 写错列名"
   伪装成"材料里没有命中"（最坏的一种失真）。按**法条侧同款**（`hybrid_engine` 的 FTS 通道）
   收窄为 `except sqlite3.OperationalError` + `logger.warning`，并加测试：真 SQL 失败**必须留痕**、
   非 sqlite 的编程错误**必须冒出来**。
3. **LOW — 坏参数静默变成"没找到"**：`int(limit)` 原先在 `try` 内，`limit=None` 的 `TypeError`
   被兜底 except 吃掉 → 静默 `[]`。这与本次战役修掉的 `allow_deep="false"` 是**同一类 bug**。
   现 `limit` / `query` 的类型校验前置到 `try` 之外并显式 `TypeError`（非 str query 原先会从
   jieba 深处冒 `AttributeError`，契约很差）。
4. **LOW — `page_of()` docstring 与代码不符**（写"归上一页"，实际返回**最后一页**）。无行为影响
   （切片起点经 `emit()` 收紧到非空白字符，不会落在页间分隔符里）。docstring 改准 + 一条测试钉住
   **代码的真实**行为（免得下一个人照旧 docstring 推行为）。

**未修、已登记为 Phase B 必解**（诚实边界）：`material` 表不存派生全文、无解析器指纹，
而切片区间是**解析结果的坐标** ⇒ 换解析器/开云深度解析会**静默作废所有已存引用**（今天不爆
只是因为重解析当下确定性）。⇒ 已在 `MATERIALS-PLANE-PLAN.md` §12 列为**动答案链之前必须先决策**的项。
另：deferred `knowledge_types_involved`（SSE 专有）与核验 UI 仍待做。

**门禁（收口后）**：`pytest` **1322 passed / 3 skipped / 0 failed**（1308 → 1322，**+14**：
`max_chars` 守卫 9 + 逐字引用/`page_of` 契约 2 + `search_materials` 参数与留痕 3）；
`mypy` 127 files 0 errors；`tsc --noEmit` 0；`smoke` 12 段全过（含新增 `smoke:trim` 25 项）；
死循环探针复跑：`max_chars=0/-5` 由 **TIMEOUT → exit=1 + ValueError**。

### 10.14 Phase B 第二步：材料进答案链——并因此挖出一个**静默失效**的检索缺陷

业主的 Phase B 验收句：**"声明『本项目以公司制度为准』后，答案准绳从国标切到制度；
T3 单独引用被拒"**。本步把这句落到提示词层。

**① 材料作为"另一个平面"进答案**（`ks_answer.py`）
- 新增参数 `params.material_project_id`。**不给就一个字都不变**：`materials_text` 保持 None
  ⇒ system/user prompt 与"没有材料平面之前"**逐字一致**（写成断言，不是"差不多"）。
- 材料**另起一节**（`参考资料（**非法规证据**…）`）追加，`[[m:i]]` 与法条 `[[c:i]]`
  **两套编号空间**、互不越界校验——混用会让材料序号被当成法条序号。
- SYSTEM_PROMPT **追加规则 7~11**（措辞的唯一所有者 = `MATERIAL_SYSTEM_ADDENDUM`）：
  准则**优先于法条且冲突必须显式说明**；"仅作线索"**不得单独支撑结论**（引用须写明
  「单一来源，未经互证」）；"已知不可用"**不得用于结论**；两个平面不得互相冒充。
- **可审计记录** `material_usage`（项目 id / 各组条数 / 可承重编号 / notes）+ `_meta` 留痕。
- **notes 诚实三条**：项目**不存在** ≠ 项目里没命中（两种事实分开报）；取到材料**不**等于
  "结论已依据制度"（那只证明它进了提示词）；**材料载入失败必须说出来**——否则会产出一份
  "看着正常、其实没用上项目制度"的答案（本战役反复打的失真）。
- `[[m:i]]` 越界同样报 `citation_index_out_of_range`（**没给材料却引材料**也报——那是凭想象引用）。

**② 被自己的测试抓到的检索缺陷（本步最值钱的部分）**
新写的答案链测试里，「住宿标准是多少」**没命中**内容含「住宿标准…」的材料。顺这条线查下去，
`search_materials` 把分词结果**裸**传给 FTS5 的 `MATCH`，于是：
- **隐式 AND** ⇒ 自然语言提问基本 0 命中（"是多少"这种词材料里没有）；
- **标点触发语法错误，再被兜底 except 吞成"没有命中"**：实测 `'GB 30871-2022'` →
  `no such column: 2022`；`'5.2.3'` → `fts5: syntax error near "."`。

> ⚠ 值得记一笔：**是 §10.13 那次"把兜底 except 收窄 + 加 warning"把这个缺陷暴露出来的**。
> 原先 `except Exception: return []` 让这两个查询**安静地返回空**，verifier 的"脏查询打不崩"
> 测试也照样通过（那条测试只验"不崩、返回列表"，**不验召回**）。
> 教训：**"不崩"不等于"能用"**——冒烟要能分辨"没有命中"与"根本没查成"。

- **根因是同一个机制写了两份**（法条侧 `hybrid_engine._fts_query()` 早就加引号 + 剥标点 + `OR`，
  材料侧那份是我新写的、更差）。修法**不是再写一份**，而是把口径收敛到唯一所有者：
  新增 `text_utils.fts_match_expr()`（与 `segment_for_fts` 同一个 owner 模块），
  法条侧 `_fts_query` 改为**委托**，材料侧直接调用。
- 迁移**不改行为**：用 15 个输入把新旧输出逐一比对（`TestFtsMatchExprIsTheSingleOwner`）。
- `hybrid_engine._seg` 迁移后**成为死代码，已删除**——它正是 verifier 报的
  "第三份查询侧分词实现（丢掉单字符词，与 `segment_for_fts` 行为不同）"。
  这不是"记一笔"，是**把分叉源去掉**。
- **已知边界（如实钉住，别当 bug 反复"修"）**：`'5.2.3'` 分词只剩单字符 `5`/`2`/`3`，
  构造器按设计丢弃单字符词 ⇒ 空表达式 ⇒ 该查询在 FTS 上**无命中**。法条侧靠"精确条款号通道"
  覆盖这类查询，**材料侧暂无对应通道**（已写进 docstring + 用测试钉住它"安静返回空、不 500"）。

**③ 同一个失败模式，上一层差点再犯一次**
引擎新返回的 `material_usage`，在插件桥 `trimAnswer` 的返回里**没有** ⇒ 又是一次
"算出来没人看得见"（与 `unsupported_context` 同款）。已加进白名单，并把 §10.12 的那道
**反回归机制扩到答案层**：冒烟现在**真的调用 `trimAnswer`**（`index.js` 顶层无 DSH import，
node 可直接 import），拿 `ks_answer.py` 源码解析出的顶层键逐个核对。
- 冒烟第一版**自己红了一次**，且红得对：它用 `^\s*"key":` 抓键，把嵌套 `_meta` 的子键
  （query/intent/…）也当成了顶层字段 ⇒ 误报"这些被丢弃"。改成**按缩进只取顶层键**，
  并补一条"嵌套子键未被误当顶层字段"的断言。

**门禁**：`pytest` **1362 passed / 3 skipped / 0 failed**（1322 → 1362，**+40**：
答案链 37 + 引用编号 3）；`mypy` 127 files 0 errors（**被 mypy 抓到一个真问题**：
新加的编号循环里 `assembled` 字面量因值类型混杂被推成 `dict[str, object]` ⇒ 不可迭代，
加显式注解修掉）；`tsc --noEmit` 0；`smoke` 12 段全过（`smoke:trim` **32/32**）；
`verify:commands` 15/15。

**诚实边界**：① **模型没法发现项目**——插件只暴露 ks_ping/ks_resolve_clause/ks_answer，
没有列项目的工具，所以 `material_project_id` 目前只能由**用户手输 id** 或**宿主绑定**
（后者未做，是下一步：仿"夹内提问"的 chatmode + UI 选择器）。**在宿主绑定做好之前，
这个功能对普通用户其实还不可用**——本步交付的是引擎侧那一层。
② `material_usage` 只**记录**用了什么，不**保证**模型真的按规则 7~11 说话（提示词约束
不是强制执行；要不要加核验是后面的事）。③ 材料侧没有"精确条款号通道"，见上文已知边界。
④ 材料与法条**检索是否共池**仍未定（§11.1），本步只是把两边的 MATCH 口径统一。

### 10.15 Phase B 第三步：`ks_materials`（只读）——让模型能**发现**项目

§10.14 交付后有一个**说不通的断点**：引擎能按 `params.material_project_id` 用材料，
但**模型无从得知项目 id**（插件只暴露 ping/resolve_clause/answer/effect_report，没有列项目的
接口）⇒ "用我上传的财报做分析"这句话在模型那边**接不上**，只能干等用户手抄一个 `prj_…`。
本步补的就是这一步：新增 `plugin/src/materials.js` + 工具 `ks_materials`（接入 `apply()`）。

**三个只读动作**：`projects`（列项目：id/name/authority_policy；便于"按名字找项目"）、
`materials`（列某项目材料：`review_status` + **轴 A 来源层级** + **轴 B 任务效力** +
切片数，并给 approved/pending/rejected 计数）、`inbox`（列参考资料文件夹里**尚未登记**的文件）。

**为什么刻意不暴露 批准/拒绝/扫描（这是纪律，不是省事）**：方案 §6 的评审闸门是**硬门**，
业主要求"**经用户评审确认参考资料可用后**再做分析"。把 `review` 开成模型工具 =
**让模型自己给自己发许可**，闸门立刻形同虚设。故工具**只读**：模型可以告诉用户
"有 2 份还没批准、不会进入结论"，但**不能**代他批准。收件（scan）是写操作，同样留给人/界面。

**措辞纪律**（写进工具描述，防止模型把"看见了"说成"用上了"）：本工具只**看**；
材料**只有**作为 `ks_answer.params.material_project_id` 传下去才参与作答，且**只有
`approved`** 会进提示词。有 pending 时如实提示"尚未评审、不会进入作答"，并说明"是否批准由
**用户**判断（本工具只读，不代批）"。

**顺手做掉的两处"多份实现"**：
- `combineSignals` 从 `index.js` 移到 `engine.js`（它服务于"给引擎调用配超时/取消"，
  而各工具的 HTTP 调用都过 engine.js）。原先它在 index.js 里 ⇒ 任何新工具模块要么
  import index.js **成环**，要么靠**依赖注入**绕——第一版就是这么写的，比放到自然归属地差；
- 新工具**不再自己拼 FTS/取数逻辑**，直接用 engine.js 的 `apiGet`/`originUrl`。

**取数加固（与 ks_answer / ks_effect_report 同款，两道）**：① 信封必须带 `data`
（200 但无 data ⇒ **抛错**，绝不伪装"这个项目没有材料"——那会让模型对用户断言"你还没上传
材料"，一句可能完全错误的话）；② **形状守卫** `expectArray`/`expectObject`：
只查"有没有 data"不够，`data: null` 会被下游 `Array.isArray()` 吃成空列表 ⇒ **同一伪装
从另一条路漏进来**（本步自查时发现并补上）。`project_id` 一律 URL 编码（不拼进路径结构）。

**测试**：`plugin/scripts/smoke-materials-tool.mjs`（**24 项**，注册为 `smoke:materials` 并
并入 `smoke` 链）。用**桩引擎**（本地 http server + 假 manager）而非真引擎：本工具的价值全在
"路径拼对没 / 状态过滤有没有透传 / 异常信封会不会被伪装成空结果"这些**确定性映射**上，
桩能把每个分支都覆盖（真引擎只能覆盖它恰好有的数据），且不依赖引擎是否已重启加载新路由。
覆盖：默认动作、Bearer token、URL 编码、status 透传、两个轴分开透出、**不透出
`raw_path`/`content_hash` 等内部字段**、缺 project_id 报错而不猜、以及四种信封/形状异常。

> 冒烟自己红了两次，**两次都是测试的错、且都红得对**：① 桩响应器用 `status` 同时当
> HTTP 状态与信封字段（信封里本就有 `status:'success'`）⇒ 写出非法状态码；
> ② `data: null` 那条我一开始断言"不抛"并配了个与之矛盾的用例名 —— 顺这个矛盾查下去
> 才发现**形状守卫缺失**这个真问题（见上）。

**门禁**：`smoke` **13 段**全过（新增段 `smoke:materials-tool` **24/24**）；`tsc --noEmit` 0；
`node --check` 三个宿主模块 OK；`verify:commands` 15/15。**本步零 Python 改动**
（`git diff --stat` 可验），故 pytest 基线不变（1362 passed / 3 skipped / 0 failed）。

**诚实边界**：① 这解决了"模型怎么知道项目 id"，**没**解决"用户怎么选项目"——
真正的 GUI 选择器（仿"夹内提问"的 chatmode 绑定 + `KsScopeChip`）**仍未做**，
所以普通用户当前要用材料，仍得先让项目存在、并让模型从名字里认出它；
② 工具只读 ⇒ **审批仍只能走 API**（界面未做，见 §10.11 诚实边界④），
这条在评审 UI 落地前一直是"功能可用、但不好用"；
③ `materials` 动作会连 `pending/rejected` 一起列（列出是**故意的**——否则用户不知道
该批什么），但描述里已明确"未批准不会进入作答"。

### 10.16 Phase B 第四步：用户侧的会话级项目绑定（`/materials`）

§10.15 之后还剩一个说不通的断点：模型能发现项目了，但**没有任何入口让"这一轮用哪个项目"
成为会话级真值**——`material_project_id` 只能由模型每次自传（不可信、会漏传）。本步补上这一点，
做法**照抄既有的"收藏夹内提问"**（同一套 chatmode 机制，不新造体系）：

- `chatmode.js` 新增**第三个维度** `materialProjectId` + `materialProjectName`（显示快照）：
  与 `folderId` 同款语义（非空=绑定 / `null`=解绑 / `undefined`=不动），非空时**蕴含查法规模式**
  （材料只在 `ks_answer` 这条链上参与作答）。CAS 回读校验、合法集合、落盘一并扩到该维度。
- **`index.js` 的 host 强制传参**：与 `folder_id` 并排，`answer_scope` 增加
  `material / material_project_id / material_project_name` 回显（这是"host 是否强制传参"的真值，
  **不是**"材料一定进了提示词"的证明——项目里可能一条已批准材料都没有）。
- **`/materials` 斜杠命令**（用户动作）：`use <prj_id> [项目名]` / `off` / `status`。
  命令**只负责"用哪个项目"**，**不代批**材料——评审是用户的判断（方案 §6 硬门）。
- 新增提示段 `FORENSIC_MATERIALS_PROMPT`：讲清"另加一个证据平面（不是缩小检索范围）"、
  `[[m:i]]` 与 `[[c:i]]` 两套编号、四组承重语义、以及**四种必须如实区分的状态**
  （命中 N 条 / 没有命中 / 项目不存在 / 材料载入失败）。
  ⚠ 与夹范围段的组合是**独立追加**而非 else-if：夹范围是"缩小检索范围"，材料是"另加证据平面"，
  语义不同，两者同开时**如实给两段**。

> **最容易踩的坑，专门钉住**：把收藏夹 id（`bmf_…`）当项目 id 传给 `/materials use`。
> 若静默通过，结果是"**开着但永不生效**"——用户会以为材料已经参与作答了。故 `setMode`
> 对 `materialProjectId` **校验前缀并抛错**，错误信息里同时给出 `prj_` 与 `bmf_` 的区别
> 并指向 `ks_materials`（测试与真实命令派发各有一条断言钉住）。

**测试**：`smoke-chatmode`（144 → **173** 项）、`verify-commands-real`（**15 → 22** 项，
用**真实 CommandRuntime** 派发 `/materials use|off|status`、断言会话级 store 与提示段）、
`smoke-materials-tool`（24 → **32** 项，新增"**host 是否真的把绑定写进请求体**"一节：
未绑定时请求体里**连键都不能有**、已绑定时强制写入、**模型自传值被 host 覆盖**、
夹范围仍照旧强制（回归护栏）、`answer_scope` 回显如实）。

**门禁**：`smoke` **13 段**全过；`verify:commands` **22/22**；`e2e:sidebar` 13/13；
`tsc --noEmit` 0；`node --check` 全 OK。**本步零 Python 改动**，pytest 基线不变。

> **冒烟红了 4 次，全是测试自己的错、且每次红得都对**：① 我新增的一段里调了
> `__resetChatModeForTests()` 并覆盖状态文件，把脚本**后面**依赖的"子会话继承"状态清掉了
> （3 条断言被连坐）；② 一条"关掉材料范围后夹范围还在"的断言，因为上一步已经把夹范围关掉了，
> 是**假前提**；③ 老脚本把"2 条命令""4 个字段"写死了 12 遍，加维度时 14 条一起红——
> 已改成 `ALL_OFF` 基座 + `mode({...})` 覆盖，以后加维度只改一处；
> ④ 长中文串里又混进了会**提前终止字符串**的 `'`（与 §10.13 同一类手误）。

**诚实边界**：① **没有 GUI**——绑定的入口是斜杠命令，不是界面选择器（下一步）；
② 命令**不代批**材料，所以批准仍只能走 API（评审界面仍未做）；
③ 宿主绑定只回答"用哪个项目"，**不证明**该项目里真有可承重材料（真值在引擎的
`material_usage` 与 `notes`）。

### 10.17 独立复核 step-12/13 的收口：一个"功能其实是死的"+ 两个设计漏洞

独立子代理（隔离 worktree `var/tmp/verify_b2`，钉在 `5e1cd13`，未改受控文件）
复核 step-12/13，7 项声明里 **6 项 CONFIRMED、4 项 PARTLY、0 项被整体推翻**。
它对**每一步都做了真实复现**（下表引用的实测数字都来自它）。收口如下。

**① MEDIUM —— `sanitizeParams` 静默丢弃 `material_project_id`：整个功能在插件层是死的。**
`plugin/src/index.js` 的 `sanitizeParams`（把模型参数过白名单后才进请求体）**没有**
`material_project_id`，而它自己的注释就写着"unknown keys are silently dropped"；
与此同时工具 schema **向模型承诺**了这个参数。实测
`sanitizeParams({material_project_id:'prj_X'}) === null` ⇒ 在 `5e1cd13` 上，
"材料进答案"这条链**从模型侧根本走不通**，`material_usage` 永远是 null，**且不报错**——
正是本战役反复打的"算出来没人看得见"，只不过这次在**输入端**。
（step-15 的宿主强制绑定绕过了这个白名单，所以用户侧能用；但 schema 与桥互相矛盾。）
- 修：把 `material_project_id` 加进白名单（与 `folder_id` 完全同款：形态校验 + host 强制值覆盖）。
- **反回归**：新增"把工具 schema 当契约、逐个键探测桥是否转发"的冒烟断言
  （外加一条"探针必须覆盖全部 schema 键"的防假绿断言）。这类缺陷从此会红。

**② MEDIUM —— T4 被声明为准则时会**压过国标**（轴 A 的绝对禁令被轴 B 重置）。**
`authority.py` 原先**先判** `task_role=='criterion'`，于是 `source_tier='T4'` +
`task_role='criterion'` 落进 `criteria`（渲染为「本任务准则」），进 `usable_hits()`，
**不进** `excluded` —— 而提示词规则 8 说"本任务准则**优先于法条**"。
实测：`counts {'criteria':1,'excluded':0}`、`usable_hits==1`、渲染里只有「本任务准则」、
**「已知不可用」那节根本不出现**。等于一篇匿名内容农场的帖子能压过国标。
- 修：**T4 优先于轴 B**（写进模块表头，作为不可被覆盖的绝对规则）。T4 一律进 `excluded`，
  且**保留用户的声明痕迹**：`criterion_blocked_by_tier=True` + 行内标注
  「⛔你声明它为准绳，但来源不可回溯（T4），**未按准则承重**」+ notes 说明。
  **不是悄悄推翻用户的声明，而是不承重 + 说清楚**。T3 当准则的正常用法有专门测试保证不被误伤。

**③ MEDIUM —— "≥2 个独立来源互证"是**不可证伪**的（假互证）。**
`_source_identity` 在无域名/URL 时退到 `material:<id>`，而**生产代码从不设置 domain/url**
（唯一的写入方 `ingest_material_file` 两个都不传）⇒ 兜底等于"任意两份材料都算两个独立来源"。
实测：同一篇文章的两份副本被报成「二手转述 2 条获 **2 个独立来源**互证」；
而 `A.COM` 与 `a.com`、`www.a.com` 与 `a.com`、`news.a.com` 与 `blog.a.com` 都被算作不同来源。
- 修（**两处**，且都是被新测试当场抓出来的）：
  1. **身份未知 ⇒ 不能互证**（`_source_identity` 返回 `None`；`None` 不进互证集合）——
     宁可保守为"仅线索"，也不要报一个不可证伪的"多源互证"；notes 会说明"身份未知者不能互证"。
  2. **一律**过域名归一（去 scheme/userinfo/端口/路径/前导 `www.`）：第一版我写成
     "含 `://` 才归一"，于是 `www.a.com` 原样返回、三种写法仍算三个来源 —— **我自己的测试当场红了**。
  3. 互证**逐条**判定而非整批提升：身份未知那条不能搭上别人的互证（同样被自己的测试抓住）。
- **诚实局限**：这不是 eTLD+1（需公共后缀表，未引入），`news.a.com` 与 `blog.a.com` 仍算两个域名。

**④ LOW —— 引用标记的两处漏检。**
(a) 旧正则 `\d+` **匹配不到负数** ⇒ `[[m:-1]]`/`[[c:-1]]` 既不算标记、也永远不被越界校验抓到
（`i < 0` 那条分支是**死代码**）；(b) **只扫 `derivation`**，于是把越界标记写在 `conclusion`
里时 `warnings == []` —— 而 SYSTEM_PROMPT 规则 1 恰恰要求"每条结论后紧跟引用标记"，
**最该被检查的位置反而没查**。
- 修：正则改 `-?\d+`（共用一个 `_MARK_NUM`），且**两个字段都扫**；三条测试钉住。

**⑤ LOW —— 冒烟自身的脆弱点（会让门禁在不同检出上给不同结论）。**
(a) 键名正则 `([a-z_]+)` 漏掉含数字/大写的键（复核用 scratch 镜像验证：新增
`vb2field`/`materialCount2` 这类未转发字段时冒烟**仍 32/32 PASS**，是瞎的）；
(b) 本仓库 `core.autocrlf=true`，**全新 clone 是 CRLF**，而冒烟用 `}\n` 找字典结尾 ⇒
CRLF 下 `indexOf` 返回 **-1**，块被**静默**扩到文件末尾，键集失真（LF 工作树上却全绿）。
- 修：键名正则放宽为 `[A-Za-z_][A-Za-z0-9_]*`；解析改为**吃文本的纯函数 + 内部自我归一换行**，
  并**新增两条 CRLF 自检**（"键解析对 CRLF 免疫"+"块边界在 CRLF 下也找得到"）。
  ⚠ 这两条自检**第一版就红了**——因为我只归一了"读取"，没归一"解析"；这正说明这类
  自检值得留着（它把静默失效变成会红的检查）。

**⑥ 其余确认项（不修，记录以备忘）**：无 scope 提示词与旧实现**逐字一致**（756 用例矩阵 0 差异）；
评审硬门在答案链上成立（运行时探针：只调 `get_project` + `search_materials`，从不碰
`list_materials`/`get_material`/`material_chunks`）；`fts_match_expr` 迁移**5528 个输入 0 差异**；
OR 化未开洞（77 个畸形查询无崩溃、无越权、无跨项目）；`chunk_text` 守卫 + `search_materials`
收窄异常均如实成立；测试非空转（注入式回归分别打红 2~10 条）。

**门禁**：`pytest` **1373 passed / 3 skipped / 0 failed**（1362 → 1373，**+11**：T4 优先 3 +
互证可证伪 4 + 两轴行为护栏 1 + 引用标记 3）；`mypy` 127 files 0 errors；
`tsc --noEmit` 0；`smoke` 13 段全过（`smoke:trim` **34/34**、`smoke:materials-tool` **34/34**）；
`verify:commands` **22/22**；`e2e:sidebar` 13/13。

> **关于"pytest 1362 还是 1361"**（复核 C11 提出的口径问题，如实记录）：
> **干净检出**跑出来是 **1361 passed / 4 skipped**，比我在**实时工作树**里报的 1362/3
> 少一条通过、多一条跳过。差的正是 `tests/test_pipeline.py::test_real_middle_json_integration`：
> 它的 `skipif` 判的是一个**相对路径**的 MinerU 产物
> （`var/mineru_cli_out/GB30871-2022识别版/…_middle.json`），而该文件是**未受控的运行产物**，
> 只在我的工作树里存在；复核把该文件拷进 worktree 后它立刻变成 11 passed / 0 skipped。
> ⇒ **两个数字都对**，只是口径不同；写进文档的数字今后要注明**是在哪种检出上取的**。

### 10.18 Phase B 第五步：`/ks/materials/*` 同源路由（界面用的材料读写通道）

界面要能**评审材料**，但 client 半边**拿不到引擎 Bearer token**（token 只在 host↔引擎之间），
所以必须由 host 做同源代理——与 `/ks/report/*`、`/ks/ingest/*` 同款。本步交付这一层。

**9 条路由**（全部 `kind:'exact'` 字面路径）：`projects`（GET 列 / POST 建）、`list`
（某项目材料，**含未批准**——否则没法批）、`inbox`（尚未登记的文件）、`scan`、
`review`（**核心**）、`tier`（轴 A）、`role`（轴 B）、`chunks`（切片分页，评审要读正文）、
`tiers`（层定义）。

**与 `ks_materials`（模型工具）的分工，写进模块头注**：
`ks_materials` 是**只读**的（模型不能批准——那等于让模型自己发许可）；
本模块**可写**，因为它的调用者是**用户界面**，而评审正是**用户的判断**（方案 §6 硬门）。

> **评审决定只收 `approved` / `rejected`**，`pending`/`auto`/`APPROVED`/`approve`/空
> **一律 400 且不打扰引擎**（冒烟逐个钉住）。`pending` 是"还没评"，**不是可以"评成"的状态**；
> 不设白名单的话，"自动通过"就能从界面这条缝里漏进来，硬门形同虚设。

> ⚠ **一步之遥踩中的字段名不匹配**（本步最值钱的检查）：对界面的契约我用 `decision`
> （语义明确、且不会与响应信封里的 `status:"success"` 混淆），但**引擎侧收的是 `status`**
> （`routes_materials.py` 的 `materials_review` 读 `body["status"]`）。
> 我最初直接把 `{decision}` 发过去 ⇒ 引擎会对**每一次**审批回 422，界面表现为"批准失败"。
> 上线前逐个核对了**每个端点的引擎侧键名**（projects 的 name/note/authority_policy、
> tier 的 tier/source、role 的 role、scan 的 origin、chunks 的 offset/limit 全部吻合），
> 只有 review 这一处不吻合。现在 host 侧**显式翻译** `decision → status`，并留了注释与两条
> 断言（"翻译成 status"+"**不发** decision 字段"）防止有人"顺手改回直接透传"。

**顺手消掉一处多份实现**：`jsonResponse` / `errorBody` / `readJsonBody` 在 **6 个模块**里
各有一份私有拷贝，且 `BODY_CAP` 有 **3 个不同取值**（4096 / 16384 / 65536）。
一次性合并风险大于收益（每个 cap 都是当场选的），故本步：
新增 `route_util.js` 作为**新代码的唯一来源**（`readJsonBody(req, cap)` 显式传 cap，
不藏模块常量），并把**最接近的一份**（`report.js`：同 cap、helpers 逐字相同）切了过去，
使这里不是一个"只有一个用户的假共享模块"。
**其余 5 个模块仍带私有拷贝，未合并**——这是**登记在案的遗留**，不是遗漏。

**测试**：`smoke-materials-routes.mjs`（**37 项**，注册为 `smoke:materials-routes` 并并入链）。
做法：给假 `ctx.webServer.register` 收下 `{kind,path,handler}` 后**直接调 handler**（配假
req/res），引擎侧用**本地桩 HTTP 服务** ⇒ URL/query/body 的构造走的是**真 `apiGet`/`apiPost`**，
不是复刻。覆盖：注册面、方法守卫（5 组 405）、必填参数缺失 **400 且 engineCalls=0**、
评审白名单 5 个非法值、轴 A 改动**默认留痕 `source:user`**、未知 query 键不透传、
引擎 422→400（**原样带出引擎错误信息**）/5xx→502/不可达→503（不抛到框架）。

**门禁**：`smoke` **14 段**全过（新增段 37/37）；`verify:commands` 22/22；`tsc --noEmit` 0；
`node --check` 四个模块 OK。**本步零 Python 改动**（`git diff --name-only` 可验），
故 pytest 基线不变（1373 passed / 3 skipped / 0 failed）。

**诚实边界**：① **界面还没做**——本步只交付"界面能调用的通道"，`KsMaterialsPanel` 是下一步；
② 没有"撤回为待评审"的入口（引擎允许三态，界面契约只开 approved/rejected）；
③ 材料路由不带任何缓存，每个请求现拉引擎（与效力报告同款：宁可慢，不要"看出了旧状态"
就批准了）；④ 生产引擎仍跑旧代码，`/api/v1/materials/*` 要**重启引擎**才在真机上通
——本步全部验证都在桩引擎与离线 handler 层完成。

### 10.19 Phase B 第六步：`KsMaterialsPanel`——**评审闸门终于有了用户界面**

§10.18 把通道打通了，但批准仍然只能调 API。方案 §6 把评审定为**硬门**
（`review_status != 'approved'` 的材料不得进入检索/分析/产出物），
在本步之前那个硬门**装了却没有钥匙**。本步补上钥匙。

**落位选择**：放进**设置里的折叠类目**（`KsCategory title="参考资料"`），**紧挨「效力报告」**。
理由是刻意的——两者都是"库内东西的管理台"，而**评审与选项目同处一地**，
硬门才不会被分到两处而形同虚设。（沿用已有形态，不新开侧栏 tab 类型。）

**面板只做用户能做的事（三条纪律，写进文件头注）**：
1. **逐份决定**：没有"全部通过"、没有"自动批准"——每份材料各自 批准/拒绝；
2. **两个轴分开摆**：`轴 A 来源可信度`（T0~T4，业主明说用户可改）与
   `轴 B 任务内效力`（criterion=本任务准则 / reference）**并排显示、各自独立设置**
   ——合成一个"可信度"就必然错一个（公司制度例）。层级下拉的选项**从引擎取**
   （`/ks/materials/tiers`），前端不抄一份措辞；用户改过的行标注"（你改的）"（`tier_source==='user'`）。
3. **评审前能读到正文**：每行可展开切片（`/ks/materials/chunks`）——
   没有正文就没法评审，那是盲签。解析不出文本的材料会明说"没有正文就无法评审"。

另外面板会**主动提示 T4+准则**这一违规组合（我在 §10.17 把 T4 定为不可被轴 B 覆盖）：
行内红字说明"它不会按准则承重，要承重请先改成可回溯的来源层级"——
把引擎侧的新纪律**在界面上也说出来**，而不是让用户自己撞。

**懒加载门**与效力报告同款：`visible=false` 时挂载但**零请求**，展开才开始拉。

**顺手加了一条"构建产物与源码同步"的冒烟**（这一条抓到了我自己的错）：
`plugin/client.js` 是**提交进仓库的构建产物**，改了 `.tsx` 却忘了 `npm run build:client`
是典型的静默失效——源码"看起来做了"、GUI 里什么都没有，而 `tsc` 全绿（它只看源码）。
新增断言：把产物里的 `\uXXXX` **解码后**再找面板的标记串。
> ⚠ 这条断言**第一版是假红**：我直接 `bundle.includes('评审是硬门')`，而 esbuild 默认
> `charset:'ascii'`，中文在产物里是转义序列 ⇒ 中文标记全找不到，而 ASCII 标记
> （`ks/materials/list`）却找得到，看起来像"面板没打进去"，实则只是编码。
> 解码后再找就对了。**这类"看起来是 A、其实是 B"的假红也值得记一笔**。

**门禁**：`smoke` **14 段**全过（`smoke:client-entry` 41 → **46**）；`e2e:sidebar` 13/13；
`verify:commands` 22/22；`tsc --noEmit` 0；`npm run build:client` 成功（1,254,536 bytes）。
**本步零 Python 改动**，pytest 基线不变（1373 passed / 3 skipped / 0 failed）。

**诚实边界**：
① **没有验证过真机 GUI**——本步验证到"打包产物含面板、类型全绿、既有 e2e 不回归"这一层；
**面板在浏览器里的实际渲染与交互未做端到端验证**（要看效果需**刷新 GUI**：
client 插件改动只有在 `pnpm run dev:web` 同时在跑时才会免刷新热更）。
② 批准/拒绝的是**材料级**判断，面板不提供"按切片批准"；
③ 没有"撤回为待评审"的入口（引擎允许三态，界面契约只开 approved/rejected）；
④ 生产引擎仍跑旧代码 ⇒ 面板现在点开会在"引擎返回 404/502"上失败，**要重启引擎**才在真机可用。

### 10.20 Phase B 第七步：**一稿多发不算多源互证**（近重复检测）

§10.17 把"独立来源"从"任意两份材料"收紧到"**域名互异且身份已知**"。但域名这一层挡不住
**同一篇通稿被两个站点转载**——独立复核当时就是这么测出假互证的。本步补上**内容**这一层。

**新增 `src/core/materials/dedup.py`**：
- `normalize_text`：NFKC（全角→半角）+ 大小写折叠 + **去空白与标点**（转载最常见的差异
  就是标点与断行）；
- `similarity`：归一化后的**字符 5-gram Jaccard**（选字符 n-gram 而非词 n-gram，
  因为中文没有空格分词、且转载常改断行）；短文本（< 3n）退化为"相等则 1"；
- `group_by_content`：按内容近似做**并查集连通分量**（不用贪心：近似关系不传递，
  贪心结果会依赖遍历顺序，连通分量才是可复现的定义）；
- `independent_source_count`：在**域名**上做连通分量（节点=域名，边=承载近似内容），
  返回独立来源数与合并分组。

**接进 `authority.assemble_evidence`**：互证判据从"域名数 ≥2"改成
**"独立来源数 ≥2"**（内容近似的域名先合并）。note 里如实说明谁与谁被并了。

> **一个逻辑 bug 被我自己当场抓住**：`independent_source_count` 第一版我按
> "**内容分组的个数**"计数——那会把"同一家媒体的两篇**不同**文章"算成两个来源。
> 正确的图是**域名图**，不是内容图。测试 `test_same_domain_two_articles_is_ONE_source` 钉住。

> **另一个缺口也是测试抓的**：合并说明原先只在**互证成立**时输出，于是
> "**为什么这两个域名不算两个来源**"在最该解释的时候（互证被合并挡下）反而没有解释。
> 现在两条路径都说明——用户看到两个域名时最容易误以为已经有互证了。

**诚实边界（写进模块头注，别把它当查重/辟谣工具）**：
- 阈值 0.8 是**启发式**，判的是"**文字是否几乎一样**"，**不是**"事实是否相同"；
- 把通稿**大改**后重发，本模块**抓不到**（有专门测试钉住这个边界）；
- 只用于**降级**（合并来源、收紧互证），**绝不**用于"自动批准"或"自动判定造假"——
  判据存疑时默认动作永远是**更保守**（少给一个互证）。
- 短文本（归一化后 < 15 字）退化为"相等即同一来源"：两个独立媒体**碰巧写出同一句
  短话**会被合并。方向是保守的（少给互证），且已在 docstring 写明。

**测试**：`tests/test_material_dedup.py` **28 条** + `test_material_authority.py` 新增
4 条（同一篇两个域名 / 只改标点的转载 / 同一家媒体两篇 / 转载对 + 真第二来源）。

> **我自己的两处期望又错了**（改断言而不是改代码，因为代码是对的）：
> ① "改一个词相似度 > 0.9" —— 实测 **0.857**；改成断言"仍在阈值之上"（那才是要保证的性质）。
> ② "阈值 0.5 松 / 0.999 严" —— 实测那对文本对 0.5 就已经是 False；改成**性质断言**
> （以实测相似度为界，两侧行为相反）。**拍脑袋的数值期望是测试里最常见的假红来源。**

**门禁**：`pytest` **1405 passed / 3 skipped / 0 failed**（1373 → 1405，**+32**）；
`mypy` **128 files** 0 errors；其余门禁不受影响（本步只动 Python）。

### 10.21 **P0 修复：畸形 JSON 会永久挂住请求**（独立复核在步骤 17/18 上抓到的）

独立复核在 §10.18/§10.19 的提交上做**中途报告**（P0/HIGH），内容是我引进的**真 bug**：

`plugin/src/route_util.js` 的 `readJsonBody` 在 `end` 回调里先 `done = true`，
再把解析异常交给一个"**见 `done` 就 return**"的出口 ⇒ **promise 永不 settle**。
后果：**畸形 JSON 的请求永久挂住**——9 条材料路由**加上既有路由 `/ks/report/export`**
一起被打挂（客户端只能超时，且 handler 与连接被永久占住、面板的 `busy` 永不清空）。
`materials_routes.js` 的 `readBodyOr400` 与 `report.js` 的 `catch { 400 }` 在这条路上**都是死代码**。

- **根因是我"顺手改进"**：基线 `report.js` 的同一处在 catch 里是**裸 `reject(err)`**，
  我把它改道经过一个会自行判重入的 helper —— 那个 helper 眼里"已经结束了"，于是静默什么都不做。
- **修法**：`readJsonBody` 改为**只有一个出口** `settle(fn, arg)`（先判重入再置位），
  "置了位又走另一条路"这种顺序错误在**结构上**不可能再发生。
- **为什么我的冒烟没抓到（复核明确指出）**：`smoke-materials-routes.mjs` 的 `invoke()`
  只会 `JSON.stringify`，**畸形 body 那条路零覆盖**；那条"空 body → 400"的断言是真的，
  但它测的是**空**body（走 `{}` 分支），与畸形 JSON 是两条路。
- **补的覆盖（并且当场验证非空转）**：给 `invoke()` 加 `rawBody`（不过 stringify），
  对 5 条写路由 + 非 JSON 文本各断言"**有响应（400）且不打扰引擎**"，
  并用 **`Promise.race` + 1.5s 超时**把"挂死"变成**一条会红的断言**（而不是把冒烟本身挂住）。
  > **非空转是实测的**：我把修复临时换回有 bug 的版本（忠实复现：`resolve` 直调、
  > 只有 catch 走那个出口），冒烟立刻 **6/43 FAILED，detail 全是 `status=HANG`**；
  > 换回修复版后 43/43 PASS（文件哈希前后一致，已核对）。**这条覆盖以后抓得住同类回归。**

**门禁**：`smoke` **14 段**全过（`smoke:materials-routes` 37 → **43**）；本步零 Python 改动。

### 10.22 **Phase C 起步：自采入口**（`materials/collect.py`）

业主的 Phase C 要求是两句话：**"能自己搜集材料"** + **"采集材料必须经用户判断或系统评审"**。
合起来意味着自采**不能**是绕开评审的旁路——收集到的每一条都必须落到**同一扇门**
（`review_status='pending'`）后面。本步交付那个**唯一入口**。

**四条结构性约束（不是靠调用方自觉）**：
1. **永远 pending**：本模块**没有**任何能设置评审状态的通道。这条有**AST 级**断言守着
   （禁止 `set_review` 调用、禁止 `review_status`/`review`/`approved` 关键字实参、
   禁止签名里出现 review 参数），并且**那个检测器自己也有自测**（在故意违规的片段上必须报，
   在"注释里提到这些词"的正当代码上必须不报）——否则这条纪律可能是空转的。
2. **默认一次性**：`lifecycle='ephemeral'`（业主裁定"其它资料默认当前任务一次性，
   用户可提名长期参考"）。升为长期是**用户**的动作，不在采集路径上。
3. **来源必须交代**：`url` → `domain` 落列；**没有出处就是"身份未知"**，
   而 §10.17 已把"身份未知者不能参与互证"定为绝对规则 ⇒ 采来的东西默认只是**线索**。
4. **判重**：正文完全相同 → **不新建**（返回既有材料并标 `duplicate=True`）；
   内容**近似**（`dedup`）→ **仍然登记**，但记 `near_duplicate_of` 并在 `tier_reason` 里
   提示"疑似与已有材料同稿"。
   > 为什么不直接把近似件丢掉：丢掉了评审人就永远看不到"疑似同稿"这个事实，
   > 而"要不要采信"是**人**的判断——我们只负责把事实摆出来。

**Track L 的入口**：复用 `knowledge.auto_tag` 的既有标准号判据（**不新写第二份正则**——
本战役已经因为"同一机制两份实现"栽过多次），认出疑似标准正文时只记录意图
（`tier_evidence['track_l'] = {standard_no, year, status:'pending_review'}`）
并在 `tier_reason` 里写明"批准后才会自动入库为法条"。
**真正的入库是评审通过之后的事**——有断言守着"本调用**没有**写 `doc_meta`"。

**测试**：`tests/test_material_collect.py` **26 条**。

> **两条测试自身的错，都被"只在全量跑时红"或"被自己的注释绊倒"暴露**：
> ① 结构化约束那条**第一版搜源码文本**，于是被模块 docstring 里正当提到的
> `review_status` 弄成假红 → 改成 **AST**（并把检测器抽出来自测）。
> ② Track L 那条断言 `doc_meta` 为空 —— 那是**全局**条件，套件里别的测试已经写过
> `doc_meta`，于是**单跑绿、全量红** → 改成断言**前后差值**。要测的性质是
> "**这次调用**没写 doc_meta"，不是"整个库是空的"。

**诚实边界**：
- 本模块**不抓网**：抓取（含 SSRF/外发纪律）在调用方；这里只做登记与判据。
- 文本候选的 `content_hash` 是**正文**的哈希（网页没有"源文件"）⇒ 同一网页两次抓取
  若正文有个别变动会被当成两份（判重只在完全相同或近似时合并）。
- 近似判重是**启发式**（阈值 0.8，判"文字是否几乎一样"），只用于**标注给人看**，
  不做任何自动决定。
- **Phase C 只到这里**：还没有"谁去抓"（采集器/工具接线）、没有 Track L 的
  **评审后自动入库**、没有采集预算与频率上限（方案 §11.4 仍未定）。

**门禁**：`pytest` **1431 passed / 3 skipped / 0 failed**（1405 → 1431，**+26**）；
`mypy` **129 files** 0 errors。

### 10.23 Phase C 第二步：**Track L 的决策**（采到的标准要不要 / 怎么进法条库）

§10.22 把 `tier_evidence['track_l']` 记下了，但**没有任何东西会去用它**。本步补上决策：
库内已有 ⇒ 只回指；库内没有 ⇒ 需要入库。**入库本身仍不做**（下一步复用既有 ingest 管线）。

**三道门（顺序即优先级，写在一处以免别处再判一次）**：
1. 材料必须存在；
2. **必须已批准** —— 评审硬门**没有例外**。这是最要紧的一条：若能绕开评审把东西塞进
   `doc_meta`，整个闸门就废了。有专门断言（pending **与** rejected 都得 `blocked`）；
3. 必须带 `track_l` 意图（没认出是标准的普通资料 ⇒ `skip`）。

**动作只有四个**（`ACTIONS` 常量是唯一定义）：`skip` / `blocked` / `link` / `import`。
`apply_link` 是**唯一会写的操作**，且只写材料平面的 `material.doc_id`（法条链零改动）；
`import` 分支**什么都不写**并如实回报"还没入库"——有断言守着"本调用没写 `doc_meta`"
（用前后差值，不用"库是空的"那种全局断言）。

**标准号比较键**：新增 `text_utils.standard_no_key()`。**先查了真库再定规则**——
实测生产库 `doc_meta.standard_no` 是 **`GB 10146-2015`**（带空格带连字符，6417 行里 6400 行含空格），
而 `knowledge.auto_tag` 抽出来的却是 **`GB10146-2015`**（去空格去斜杠）——不归一就永远比不上。
规则保守：NFKC + 大写 + 去空白 + 去 `/` + 统一各种连字符；**保留年份与部分号**
（实测库里 `GB 10769-2010` 与 `GB 10769-2025` **同时存在**，是两部文件）。
既有的几处就地归一**没有合并**（`_hier_from_no` 取前缀、`short_code` 去连字符、
`ccs_fetcher._seed_key` 给种子表），各有用语义，已在 docstring 里逐一点明。

**测试**：`tests/test_material_track_l.py` **23 条**。

> **又是"测试自己错"的三次，而且都很有代表性**：
> ① 我按记忆写了 `upsert_document` —— 真名是 `insert_document(conn, doc)` 且需要
> `file_path`/`file_hash`（NOT NULL）⇒ 补齐占位值；
> ② `doc_meta.standard_no` 是 **UNIQUE**，而 `db` fixture 在**同一个文件内共用一套库**，
> 于是第二个测试重复种同一条标准就 `UNIQUE constraint failed` ⇒ 把种数据的 helper 改成**幂等**；
> ③ 承 ②，那条"库内没有 ⇒ import"的用例**永远走成 link**（前面的测试已经把该标准种进去了）
> ⇒ 标准号参数化，import 用**没有任何测试种过**的号。
> 教训：**共用测试库 + UNIQUE 约束**会让"按顺序发生的副作用"决定断言结果，
> 这类测试必须自己保证前置状态，而不是假设"库里本来没有"。

**诚实边界**：
- 判"库内有没有"是 `standard_no_key` 的**Exact 匹配**（含年份/部分号），
  **不做**跨版本、勘误、替代关系的关联（那是 `short_code` 与 `superseded_by` 的事）。
- 采集件正文来自网页 ⇒ **不是官方原件**；即使将来入库，`legal_status`/`legal_hierarchy`
  等判据仍应由既有管线的规则给，**本模块不代它决定**。
- **入库（写 `doc_meta`）仍未实现**——这是 Track L 剩下的一半，必须复用既有 ingest 管线。

**门禁**：`pytest` **1454 passed / 3 skipped / 0 failed**（1431 → 1454，**+23**）；
`mypy` **130 files** 0 errors；本步只动 Python，插件侧门禁不受影响。

### 10.24 Phase C 第三步：**Track L 入库**（采到的标准真的进法条库了）

§10.23 只会"决定"，不会"入库"。本步补上另一半：走**既有** `law_text.ingest_law_text`
（切分/分型/建边/事务/查重全在那里），成功后再从材料侧 `link_doc` 回指。

**没有重写第二份切分逻辑**（这是本步的关键决定）：`ingest_law_text` 把 `doc_type`
**写死成 `法律法规`**，而生产库 6417 行 `doc_meta` **全是 `standard`**（6130 GB/T + 287 GB）。
本可以照着它的结构再写一份"标准版"，但那正是本战役反复栽的坑。于是把它
**参数化**（`doc_type` / `short_code` / `source_marker` / `source_url`，全部关键字参数、
默认值保持原行为向后兼容），Track L 传 `doc_type="standard"` +
`legal_hierarchy=_hier_from_no(...)`（复用既有前缀判据）+ `source_url`（**溯源要落库**）。

**单一入口 `reconcile(material_id)`**：按决策分派（`link`→回指 / `import`→入库 / 其余什么都不做），
返回体恒有 `imported`/`linked` 两个布尔 ⇒ "没做任何事"与"做了但没成功"**看得出来**。
调用方（评审后的钩子）不必自己判该走哪条——那会分叉。

> **两条"测试自己错"，都是被既有测试或真实数据抓出来的**：
> ① 我的标准正文夹具只写了**单级**章标题（`1 范围`），而 GB 切分器要的是**两级**（`3.1`）
>    ⇒ 入库返回 `error: 未识别到任何'第X条'条文`。**是夹具不真实，不是代码错**。
>    顺手把这条**真限制**钉成一条测试（只有单级标题的网页正文切不出来 ⇒ 必须**如实报错**，
>    不能造出一部空标准）。
> ② 更值钱的一条：Track L 入库测试是**第一处往法条链写东西的材料测试**，于是
>    `tests/test_quality_rules.py::test_qh_02_quality_issues_endpoint_shape`
>    （断言"质量问题的条款恰好 5 条"——一个**全局**假设）当场变红：它数到了 8。
>    **这是我污染了会话级共享库**，不是它的错 ⇒ 新增 `law_docs` fixture，
>    用**既有的** `clause_repo.delete_document`（它自己会清 `clause_fts`/`clause_vec`
>    孤儿行）在测后删干净。

**已知边界（钉住，别当 bug 反复"修"）**：
- **Track L 今天只认标准**：`track_l` 意图来自 `collect.looks_like_standard`，而复用的是
  `auto_tag` 的**标准号正则** ⇒ 没有标准号的**法规正文**（`民法典` 那种 `第X条`）认不出来，
  `plan_import` 返回 `skip`。`law_text.split_law_text` 已有法规切分能力，缺的只是
  "认出这是法规"——留给后续一步（有测试 `test_collected_LAW_text_is_out_of_scope_today` 钉住）。
- **落库的 `standard_no` 写法与库内既有行不一致**：新增行用 `auto_tag` 归一形
  `GB88888-2088`（无空格），库内既有 6417 行是 `GB 10146-2015`（带空格）。
  判重/比较走 `standard_no_key`，**不受影响**，但拼写不统一。需要一个 canonicalizer，
  而它必须正确处理 `DB11/T 1234` 这类**前缀带数字**的号段（一行正则会把 `DB11/T` 变成
  `DB 11/T`，比不统一更糟）⇒ **没有**糊一个上去，登记为待办。

**门禁**：`pytest` **1462 passed / 3 skipped / 0 failed**（1454 → 1462，**+8**）；
`mypy` **130 files** 0 errors。

### 10.25 收口独立复核 step-17/18：一个 MEDIUM + 四个 LOW + 两处**覆盖缺口**

复核（隔离 worktree，钉 `a6e91c2`）给出 8 项结论：**C1/C2/C7/C8 CONFIRMED**、
C3/C5/C6 **PARTLY**、C4 **REFUTED**（就是 §10.21 那个 P0，已修）。本步收口余下各条。

**MEDIUM —— 轴 B 在界面上**永远无法撤销**（面板上那个选项装了用不了）。**
面板的「未声明效力」按 `api.ts` 的类型（`'criterion'|'reference'|null`）发 `{role: null}`，
引擎与仓库本来就支持 `None`（"null=撤销"），**但我的主机路由要求"非空字符串"** ⇒ 每次 400，
界面显示"操作失败"。修：键**必须在**（缺键 = 调用方没说要设什么 → 400），
值允许 `null`（撤销）或非空字符串；空串按"写错了"拒绝（含混的值不猜）。

**LOW —— `tier` 每次改级都把原判级说明**擦成空**（真实的数据丢失）。**
引擎的 `set_tier(..., reason=...)` 会**把 `tier_reason` 写成**传入的 reason，
而我的路由只发 `{tier, source}` ⇒ 原来那句"系统判据：域名可回溯"变成 `None`，
界面上"判级说明"那行随之消失、轴 A 的审计链断掉。修：路由转发 `reason`（缺省发 `null`，
**显式**而不是漏字段），界面带上变更说明（`用户改级：T1 → T2`）。

**LOW —— 收件箱读取失败被**静默渲染成「未登记 0 个文件」**，而代码注释却写着"但要**说**"。**
那与"文件夹确实是空的"长得一模一样，用户会以为文件没放对。修：如实报错，
并说明"这个计数不可信——不是没有文件，是没读到"。

**LOW —— `run()` 的过期闭包**每建一个项目白发一次请求**。**
`run` 捕获 `projectId`，而「新建项目」在 `run` 内部才 `setProjectId(新 id)`（尚未提交）
⇒ 刷新用的是旧 id，发出 `GET /ks/materials/list?project_id=`（空 id，主机 400）。
修：把要刷新的 id 作为**显式参数**传入，新建时传 `null`（新项目必然没有材料）。

**INFO —— 打包脚本的注释是假的**：产物走的是 **automatic JSX runtime**
（`react/jsx-runtime` 的 `_jsx`），不是 classic `React.createElement`——
`client/tsconfig.json` 的 `"jsx": "react-jsx"` 覆盖了 `build-client.mjs` 的 API 选项。
已把注释改成事实，免得下一个人照着错前提写代码。

**INFO —— 超限请求体变成"连接被重置"而不是 400**：`readJsonBody` 在读超 `cap` 时调
`req.destroy()`，于是调用方随后写的 400 **送不到客户端**（`chatmode.js` 里也有同样的告诫）。
改成 `req.resume()`（读掉但不用），连接保住、400 能发出去。

**两处复核指出的**覆盖缺口**（都是"改了也全绿"的盲区）**：
1. **冒烟从不发引擎的字段名 `status`** ⇒ 一个 `.status` 兜底（`decision ?? status`）
   能把评审白名单整个绕过去而冒烟仍全绿。补：`{status:'approved'}` 必须**仍然 400**；
   同时给 `{status:'pending', decision:'approved'}` 断言"以 `decision` 为准、不给 `status` 留缝"。
2. **"产物与源码同步"那组只证明"产物里有字符串"** ⇒ 抓不到"源码里把面板**删了**"
   （源码不再挂载、产物是旧的）与"忘了重新构建"。补：**源码级断言**
   （`KsSettingsSection.tsx` 里真的 `import` 并挂载了 `<KsMaterialsPanel`、真的有
   「参考资料」类目），并**当场验证非空转**——把挂载那一行删掉，冒烟立刻 **48/49 FAIL**。

**门禁**：`smoke` **14 段**全过（`smoke:materials-routes` 43 → **50**、
`smoke:client-entry` 46 → **49**）；`verify:commands` 22/22；`e2e:sidebar` 13/13；
`tsc --noEmit` 0；`pytest` **1462 passed / 3 skipped / 0 failed**（本步零 Python 改动，复跑确认）。

**仍未做（复核也确认了）**：**真机 GUI 端到端**没验过（复核只能在
`renderToStaticMarkup` + 它自写的 hook runtime 里跑，不是 React scheduler 证据）；
**引擎仍需重启**（复核实测：那些路由在活进程里 404，与"不存在的路由"同形 ⇒
`routes_materials` 根本没加载；磁盘上的文件比进程启动时间新 30 分钟）。
复核给的两条后续建议已记：**GUI 验证前先钉住产物身份**（活动 GUI 读的是主检出的
`client.js`，可能不是你要验的那个提交），以及**轴 A 的 reason 值得改成必填**
（Phase C 的"强制评审"叙事会正好踩在"用户覆盖系统判级"这个点上）。
### 10.26 Phase C 第四步：**网页采集器**（"能自己搜集材料"的后半句）+ 一个"读不了的正文"缺陷

**做了什么**：新增 `src/core/materials/harvest.py`。§10.22 有自采入口、§10.23/§10.24 有
Track L 的决策与入库，但**没有任何东西真的去抓**——"能自己搜集材料"当时只是半句话。
`collect_url(project_id, url, ...)` 现在真的取回一个 URL 并交给 `collect_text` 登记。

**三条纪律，全部复用既有所有者**（这一段的价值主要在这里，不在代码量）：
1. **SSRF** 走 `update.announce.is_private_url`（那个模块的 docstring 已写明"用户拍板严格版、
   **无豁免开关**"）。本模块**不提供**任何"允许内网"参数——那等于给严格版开后门。
   有一条**结构性**测试钉住签名里不许出现 `allow`/`private`/`local`/`unsafe` 这类词，
   另一条钉住"只调用那个所有者、自己不实现地址判断"（源码里不许出现 `socket.`/`ipaddress`）。
2. **抓取**走 `update.channels.base.default_transport()`（curl_cffi 浏览器指纹 / httpx 兜底），
   契约 `fetch(url, timeout=…) -> (status, body)`。**不自造 HTTP 客户端**。
   测试用注入 transport（`Fake`/`Boom`/`Spy`）跑通路，**不依赖真网络**；
   要打本地站点时才用 `monkeypatch` 换掉判据函数——**生产代码里没有开关**。
3. **HTML→文本**走新的**页面级规范实现** `text_utils.html_to_text`（见下）。

**硬门没有被采集松动**：抓回来的东西一律 `pending` / `origin='collected'` /
`lifecycle='ephemeral'` / 来源留痕（`url` + `domain`），且**未批准就检索不到**（测试钉住
`search_materials` 返回空）。`collect_text` 的"永远 pending"结构性约束原样生效——
本模块连设置评审状态的通道都没有。

**顺带把"HTML→文本"的第四份实现拦住了**：同一算法此前在**三处**各有一份
（`server._html_to_text`、`ks_answer._html_to_text_compact`、
`quality.clause_health.clause_health_html_to_text`），而 `clause_health` 自己的 docstring
就写着"**逐字符等价于** `server.py` 的原 `_html_to_text`"——那是承认了的重复。
采集器需要**页面级**转换（不是小片段、也不是表格），与其再写第四份，不如把规范实现放进
`text_utils`。**没有**顺手改那三处的调用点（各自 `limit` 与语义是当场选的，改动面大于收益）
——登记为待办。
与 `clause_health_html_to_text` 的关系在 docstring 里**精确**写明并被测试**双向**钉住：
同一 `limit` 下、**不含 `script`/`style`** 的输入逐字符等价（**该测试当时的 6 组样本**：表格 / 实体 / 空 /
`None` / 裸 `<td>`）；含 `script`/`style` 时**本函数丢掉它们的内容**而旧的那份不会——
这是**有意的改进**（页面里的 JS/CSS 被当成正文塞进材料，是采集最脏的来源），
并有一条测试专门把这条差异钉死，免得后人发现"不等价"后当成 bug 改回去。

**本步挖出并修掉一个缺陷（测试红了才暴露）：PDF 头被当成正文登记。**
现象：`collect_url` 对 `Content-Type: application/pdf` 的响应返回 `collected=True`，
`%PDF-1.7` 连同乱码被 `html_to_text` 原样留下、**登记成一条材料**。
根因**不在采集器**：**传输层把响应统一收敛成 `str`**（`CurlCffiTransport.fetch` 先试
`resp.json()`，失败取 `resp.text`），**Content-Type 在那一层就丢了**。所以"这是不是 PDF"
**无法**靠响应头判断，只能靠**开头字节**。
修法：新增判据 `text_utils.looks_like_binary`（去前导空白后以已知容器签名开头——
`%PDF-` / `PK\x03\x04`（docx/xlsx/odt）/ `\x89PNG` / JPEG / `\x7fELF` / OLE2 / PostScript——
或前 4096 字符内含 NUL），在**两处**调用（**同一实现**，不新写第二份）：
① `collect_text`（**唯一的采集门**，拒收并抛 `ValueError`）；② `harvest.collect_url`
（它才知道自己刚抓过一个 URL，给得出"响应不是文本"这个具体理由）。
**为什么挡在唯一那扇门上**：登记进去的东西**直接进评审队列**，而"读不了的正文"要等到
分析时才暴露——那时它可能**已经被批准了**。这也**比空材料更坏**：空材料一眼看得出有问题，
这个看起来"有内容"。
诚实边界写进 docstring：这是**启发式**、只认**开头**、认不出**没有签名**的二进制、
正文**中间**提到签名的会漏——**宁可漏也不误伤**（判据挡在唯一的门上，误判=丢材料）；
完整判断要 magic 库（未立项）。
测试：2 条在 `test_text_utils.py`（认全 + **少误伤**——⚠ 更正：原写「零误伤」**不成立**，见 §10.29 的 LOW；含"签名在中间不算"与"NUL 只在开头
4096 内才算"）、**2 条**在 `test_material_collect.py`（门自己拒收且**不碰 `doc_meta`**
——Track L 只在批准后入库；另一条钉住"签名在正文**中间**不算"，即不许误杀）。

**门禁（本步）**：`pytest` **1492 passed / 3 skipped / 0 failed**（**主检出**；上一步 1462 ⇒ **+30**，
基线**只涨**）。⚠ **更正**（见 §10.29）：**干净工作树**跑出来是 **1491 passed / 4 skipped**
——总数同为 1495，差的 1 条是 `test_pipeline.py::test_real_middle_json_integration` 的
`skipif` 依赖被 `.gitignore` 忽略、**只在主检出存在**的 `var/mineru_cli_out/…_middle.json`，
属**环境依赖**而非缺陷。⇒ 引用 pytest 数字必须注明是哪棵树。；`mypy src` **131 files / 0 errors**（上一步 130；新增 `harvest.py`）。
本步**零 JS 改动**，故 `smoke` / `verify:commands` / `e2e:sidebar` / `tsc --noEmit` 未复跑
（数字同上一步：冒烟 14 段全过、22/22、13/13、0）。

**诚实边界（本步明确未做）**：
- **没有接线**：`collect_url` 目前是**库级能力**——没有 API 路由、也没有模型工具。
  今天的产品里**没有人能触发它**（`routes_materials.py` 的 14 个端点里没有采集；
  `ks_materials` 是只读的）。⇒ 下一步（C-5）才是接线。
- **不是爬虫**：不排队、不重试、不递归跟链接、**不限速**、不做 robots/ToS 判断。
  **采集预算与频率上限仍未定**（方案 §11.4），所以刻意**不提供批量入口**——要批量，先定预算。
- **不解析附件**：PDF/docx 交给文档解析管线（`ingestion.material_ingest`，走 MinerU 子进程），
  采集器只收网页正文。
- **标题是粗的**：`<title>` 正则 + `html_to_text`，不解析 DOM、不做正文抽取（readability）。
- **继承** `is_private_url` 的已知局限（DNS rebinding 的 TOCTOU 窗口不设防），**不声称更强**。
- 正文超 `MAX_TEXT_CHARS`(200_000) 会**显式**截断（返回值带 `truncated`、`tier_reason` 写明）。
### 10.27 Phase C 第五步（接线一）：采集终于**可达**——并且四条契约被写死在代码里

**做了什么**：§10.26 的 `collect_url` 是**库级能力**（没有路由、没有工具 ⇒ 产品里没人能
触发它）。本步把它接成端点：引擎 `POST /api/v1/materials/projects/{pid}/collect` +
主机同源路由 `POST /ks/materials/collect?project_id=`。**仍是单条**（理由见契约 3）。

**四条契约（都不是"顺手写的"，每条都对应一次踩坑）**：

1. **采集者不得自 claim 可信度**：两个端点都**拒绝** `source_tier`（引擎 422 / 主机 400），
   而不是"悄悄丢掉那个字段"。理由是本战役已经在 `sanitizeParams` 上栽过同款——字段被吞、
   功能全死、**没有人报错**；静默忽略还会让调用方**以为自己设上了**。
   轴 A 的起点因此是**系统判据**（采集默认 T3），要改只能由**用户**走 `/ks/materials/tier`。
   测试钉住三点：端点是 422/400、消息里点出 `source_tier`、**且一份材料都没留**。
2. **"抓取失败"不是错误码**：SSRF 拒绝 / HTTP 404 / 非文本 / 空正文一律 **HTTP 200 +
   `collected:false` + 原因**（与 `scan` 的"逐条结果"同款）。理由：调用方**要把原因显示给
   人看**（"为什么这条没进来"），而错误码把它变成一个没有内容可展示的失败。
   有一条**不打桩**的用例走真实 `announce.is_private_url`（回环地址必被拒）⇒ 在**没有网络**
   的机器上也成立。
3. **只有单条，没有批量**：方案 §11.4 的采集预算/频率上限**还没定**，所以刻意不提供数组
   入口。判据是**行为**（不是"源码里有没有某个词"）：`{"urls": [...]}` ⇒ 422 且**一份都不采**。
   将来要加批量，必须先定预算——这条会变红，逼着那个决定被显式做出来。
4. **端点声明成 `def` 而不是 `async def`**（本文件其它端点是 async；**有先例**：
   `server.data_quality_issues` 也是 `def`）：这个端点会做**最长 15 秒的同步网络抓取**，
   而 uvicorn 是**单事件循环**——`async def` 里做同步 I/O 会把**整个引擎**卡住（期间别的
   请求一起等）。Starlette 对非 async 端点是丢进线程池跑的，所以"慢"只慢这一个请求。
   代价如实写进注释：线程池每个工作线程会拿一条自己的 SQLite 连接（本仓库是线程局部连接），
   所以并发采集时连接数上界 = 线程池大小（默认 40），不是无界。
   顺带发现 `materials_scan` 同样做同步重活却声明成 `async def`——**登记为待办**，本步不动它。

**端到端用例（评审硬门在 HTTP 层没有被采集松动）**：
`采集 → 待评审 → 检索不到 → 批准 → 检索到`，且断言 `origin='collected'`、`lifecycle='ephemeral'`、
`source_tier='T3'`（**系统给的**，不是调用方声称的）、`url`/`domain` 留痕、页面标题被取到、
**页面里的 JS 没有进正文**；另一条用例断言 PDF 那条缺陷在**路由层**也挡住了。

**顺带消掉一个门禁噪声（本步实测踩到）**：`smoke-chatmode` 里等 sweep 用的是**固定 80ms**，
而 sweep 是 **fire-and-forget**（`chatmode.js` 故意不 await）。机器有负载时 80ms 不够，
于是本步第一次跑 `npm run smoke` 报 **chatmode 172/173**（单独跑 173/173 全绿）。
改成**轮询到超时**（语义不变：sweep 没跑起来仍然红），并做了**变异实验**证明非空转
——把 `chatmode.js` 里那行 `sweepStaleArtifacts()` 注释掉，冒烟立刻 **FAIL 172/173**
且失败断言正是同一条 `the corrupt load path reaches the artifact sweep`（与观察到的
数字与断言一致）。这也把"未确证"的旧条目（§12 第 1 条）里的同类噪声往前推了一步。

**门禁（本步）**：`pytest` **1499 passed / 3 skipped / 0 failed**（上一步 1492 ⇒ **+7**，
全部是采集端点的用例）；`mypy src` **131 files / 0 errors**；`npm run smoke` **14 段全过**
（`smoke:materials-routes` 50 → **59**）；`verify:commands` **22/22**；`tsc --noEmit` **0**。
（`client.js` 未改：本步只动主机侧模块与 Python；主机入口是 `src/index.js` 源码，不是产物。）

**诚实边界（本步明确未做）**：
- **模型侧还没有采集工具**：这一层是**同源 HTTP 路由**（`/ks/materials/collect`），当时的调用者只有冒烟脚本与 C-6 的模型工具——⚠ **更正**（复核 step-26~30 指出）：全仓**没有任何 GUI 代码**调用它，写成「界面能走的路」是**过度声称**。
  模型要能"自己搜集材料"，还需要一个模型工具 + 提示段（**下一步**）——在那之前，
  模型仍然只能**看到**材料（只读的 `ks_materials`），不能自己抓。
- **引擎需要重启才加载新路由**：活进程里的材料路由仍是 404（§10.25 已记，本步不重启——
  插件纪律：绝不死掉不是自己拉起的实例）。⇒ 端到端"真机 GUI 点一遍"仍待做。
- 不解析 PDF/附件；不排队、不重试、不递归、**不限速**、不做 robots/ToS 判断；
  "这不是文本"仍是**启发式**（§10.26）。
### 10.28 Phase C 第六步：**模型能自己搜集材料了**（`ks_collect`）+ 独立复核 step-25 的结论

**做了什么**：新增模型工具 **`ks_collect`**（`plugin/src/collect.js`），接在 `apply()` 里。
至此"AI 自己搜集材料"这条链在**模型侧**通了：模型用自己的检索找到原始出处 → `ks_collect`
登记 → 用户评审 →（批准后）material 才可能进结论。

**为什么与 `ks_materials` 分成两个工具**（不是往只读工具里塞一个 action）：
`ks_materials` 的纪律是**只读**（评审不能开给模型——那等于让模型自己发许可）。
把"写"混进去会让"这个工具到底会不会改东西"变成要逐 action 判断的问题，复核者也难一眼看出
边界。⇒ **读一个工具、写一个工具，名字即权限**；`smoke-effect-tool` 里有一条断言点名
六个工具都在册（防"模块写好了但忘了注册"——那种漏在自己的模块冒烟里**抓不到**，
因为那个冒烟是直接 import 模块的）。

**四条写进代码的契约**（与 C-5 的路由同源，且更严）：
1. **目标项目不猜**：会话绑定（`/materials use`）优先；模型显式给 `project_id` 且与绑定
   **不一致时报错**（不偷偷换项目——"材料进了别的项目"是静默失真）；两者都没有 → 报错并
   指路（`ks_materials` 查项目 / 请用户绑定）。以上失败都**不打扰引擎**。
2. **不发 `source_tier`**（连试都不试；schema 里也没有这个键）：采集者不得自 claim 可信度。
3. **不假装成功**：信封缺 `data` / 404 / 没有 `collected` 字段 → **抛**（不得说成"已经采到了"
   或"没采到"）；`collected:false` 则如实回报 `reason` + 明确"**没有**登记成材料、不要算作
   已获取的证据"（这是**结果**不是异常，模型应换来源）。
4. 回执一律带"**待评审 / T3=仅线索 / 不得单独支撑结论 / 本工具不能代批**"，并把
   `review_status` 原样带出；内部字段（`content_hash`/`raw_path`）不外泄。

**新增的一条：会话级刹车（暂定）**。引擎端点只收单条，但模型可以**反复调用** ⇒
"没有批量入口"在模型侧其实等于"可以无限次单条"。方案 §11.4 的采集预算**尚未定案**，
所以给了一个**宽松但有界**的暂定值（`MAX_COLLECT_PER_SESSION = 20`）：回执带
"本会话已采/上限"（让节奏看得见），超出则**响亮报错**并明确"由用户决定是否继续"，
并**显式禁止**"已经采够了 / 没有更多资料"这两种错误读法。
⚠ 这是**暂定值，不是产品决定**——业主定案后改一行即可（已写进 §11.4 待决）。

**提示段**：`FORENSIC_MATERIALS_PROMPT` 增第 7 条（自采），三条必须照说：
采到的是仅线索、登记后是 pending 不会进结论、模型不能批准也不能声明层级；
并明确"证据不足时宁可如实说，不要用线索硬撑"。

**门禁（本步）**：`smoke` **15 段全过**（新增 `smoke:collect` **32/32**；
`smoke:effect-tool` 63 → **65**）；`verify:commands` **22/22**；`tsc --noEmit` **0**；
`pytest` **1499/3/0**（本步零 Python 改动，复跑确认）；`mypy` 131/0（同上）。

**独立复核 step-25 的结论（2026-09-17，`var/tmp/verify-b4-artifacts/VERIFY-REPORT.md`）**：
A/C/H/I + B 的实质 **CONFIRMED**；D/E/G **PARTLY**；F **REFUTED**。8 组变异实验里
M1/M1b/M2/M4/M5/M6 **RED**（测试非空转），两条 **GREEN**（空转守卫）。
**11 条发现，按严重度排**（全部**尚未修**，就是下一步的施工单）：

- **[HIGH] SSRF 闸门不覆盖重定向**：默认传输跟随 302，实测真的向 `169.254.169.254`
  发起连接，而 `is_private_url` 全程只调用 1 次。作者只声明了 DNS rebinding 的 TOCTOU。
- **[HIGH] 自闭合 `<script src="a.js"/>` 会过杀整页正文**（一路吃到后面的 `</script>`），
  harvest 随后报"页面没有可提取的正文"⇒ **丢材料 + 归因误导**。
- **[MEDIUM] "不是网页正文"照样登记**：真传输下 11 条样本 9 条被登记（JS / CSS /
  JSON 字符串标量 / JSON 解析失败体 / UTF-16），而拒收原因串还写着"不解析 PDF/**JSON**"。
- **[MEDIUM] 未闭合 `<script>`/`<style>` 的 JS/CSS 真的进材料**（正是本步声称修掉的"最脏来源"）。
- **[MEDIUM] `looks_like_binary` 的 PNG/JPEG/OLE2 签名在真实路径上是死代码**（`errors='replace'`
  把非 ASCII 首字节变成 U+FFFD），而测试 `f("\x89PNG…") is True` 钉的是传输层产生不了的字符串
  ——**假信心**（那条断言本身不假，但它测的不是生产路径）。
- **[MEDIUM] `test_it_delegates_to_the_ssrf_owner` 是可绕过的空转守卫**
  （只断言源码里出现字符串），变异 M7 通过；而 §10.26 却称它"钉住不自造地址判断"。
- **[LOW]** "零误伤"不成立（`%PDF-` 开头的讲解文、PostScript 源码、含 NUL 的 CSV 会被拒）；
  script/style 的**大小写敏感性**无测试钉子（M3 GREEN）；§10.26 有三处计数/措辞不准
  （"5 组样本"实为 6 组；"1 条在 test_material_collect"实为 2 条；pytest 数字随未跟踪产物浮动，
  干净工作树是 1491/4）。
- **[INFO]** harvest 判的是 `html_to_text` **转换后**的文本、`collect_text` 判的是**原始 body**
  （同一实现、不同输入形态）；复核期间主检出已前进到 C-5，故上述缺陷**现在都在一条可达路径
  后面**（复核者未复核 C-5/C-6 本身）。

⇒ **下一步施工单（step-28 起）**：先修两个 HIGH（重定向 SSRF；自闭合/未闭合 script），
再修 MEDIUM（给传输层一个"带响应头的取回"契约，让 Content-Type 与**真实字节**的 magic
都能判；把 `looks_like_binary` 的叙述与测试改成不制造假信心；把空转守卫改成行为断言），
最后修 LOW（措辞与钉子）。**顺序按"静默失效 + 安全"优先**，不按发现列表顺序。
### 10.29 收口独立复核 step-25 的两个 HIGH（+ 三条诚实性修正）——施工单第 1 批

复核的 11 条发现按"**静默失效 + 安全**优先"排序施工。本步只做**两个 HIGH**与随它们一起
暴露的诚实性问题；MEDIUM（Content-Type/真实字节）与 LOW（措辞）留下一批。

**① [HIGH] 重定向绕过 SSRF 闸门——已修（安全）**
复核实测：默认传输**跟随 302**，一个公网 URL 用 `Location: http://169.254.169.254/…`
就能让引擎**真的向云元数据端点发起连接**，而 `is_private_url` 全程只被调用一次。
根因是**闸门只在"发起前"判了原始 URL**，而那一跳之后去哪由 HTTP 栈自己决定。
修法（三处，各司其职）：
- `update.channels.base`：给两个 transport 一个**显式** `allow_redirects` 参数
  （curl_cffi 是 `allow_redirects`、httpx 是 `follow_redirects`——**只有那个模块知道**
  两家名字不同，所以对外统一成一个名字；**默认 True = 既有行为不变**，公告扫描照旧跟随）；
- `harvest._fetch_without_redirects()`：抓取时**显式关掉跟随**。关掉之后，"重定向"变成
  一个**可见的结果**（3xx），由调用方决定；**不接受 `**kw` 的替身**会在这里抛错 ⇒
  这是**故意**的 fail-closed（宁可抓不到，也不在"可能已跟随"的情况下登记材料）；
- 3xx 的处理：只对**同主机**的 http→https 升级**自动重试一次**（`_https_upgrade`；
  主机没变 ⇒ `is_private_url` 结论不变 ⇒ 不可能被引向内网），其余 3xx **如实拒绝**，
  原因串写清"不跟随"的理由并要求给**最终地址**。留痕用**实际抓到的**地址
  （升级后就是 https 那个），并在 `tier_reason` 里注明"同主机 http→https 升级后取到"。
**证据**：本地 302 站点的 `Location` 指向 `169.254.169.254`；真传输拿到的状态就是 **302**
（跟随了的话不可能是 302），`allow_redirects=False` 这条 kwarg 是**承重**的——
变异实验（把它改回 True）令 `test_contract_forwards_allow_redirects_false` **变红**。

**② [HIGH] 自闭合 `<script src="a.js"/>` 吃掉整页正文——已修（静默丢材料）**
旧实现是一句 `re.sub(r"<(script|style)\b[^>]*>.*?</\1>", …)`，两种**真实页面**形态都错：
自闭合标签会从它一路吃到**后面第一个** `</script>`（实测可见正文被吃光 ⇒ 采集器随后报
"没有可提取的正文" ⇒ **丢材料 + 归因误导**）；未闭合 `<script>` 则**匹配不上** ⇒ JS/CSS
被当正文**留进材料**（正是本步上一版声称修掉的"最脏来源"）。
修法：抽出 `_strip_script_style()`，逐个标签定位——**自闭合**（属性以 `/` 结尾）只丢标签
本身；**未闭合**按 HTML 规则把其后整段丢掉（浏览器不渲染它）；闭合标签用 `</script\s*>`
**本身**定位，脚本字符串里的 `</p>` 骗不过它；大小写用 IGNORECASE（并**补了钉子**，
复核的 M3 变异体原先 GREEN 说明这块零覆盖）。
**证据**：变异实验（换回旧正则）令 4/7 条边角用例**变红**。

**③ [MEDIUM] 空转守卫——已换成行为断言**
复核的 M7 变异体证明 `test_it_delegates_to_the_ssrf_owner`（只断言源码里出现字符串
`_announce.is_private_url`、且没有 `ipaddress`/`socket.`）**可以绕过**。现在改成两条
**行为**断言：判据**被调用且只被调用一次**（列出实参），以及**判据的结论真的决定结果**
（换成"一律拒绝"的替身 ⇒ 连公网地址也不抓、`fetch` 一次都不被调用）；那条源码级检查
保留但**降级并写明它的边界**（"一个把逻辑藏到别的模块再 import 进来的写法能绕过它"）。
**证据**：变异实验（把判据调用摘掉）令这两条**变红**。

**④ [MEDIUM→已修] `html_to_text` 与 `clause_health` 的"精确关系"写错了**
复核指出等价性**不止一条例外**：大写 `</TD>`/`</TR>` 两边并不等价
（本函数 `'甲 | 乙'` vs 旧 `'甲乙'`），而 docstring 只声明了 script/style 一条。
已改成**精确**措辞（两条有意差异，各有一条测试钉住），并加一句"除此之外**不许**再有
第三处差异——发现第三处就说明两边开始分叉"。

**⑤ [LOW→已修] 两种"空正文"混为一谈**
现在分开报：取回就是空的 ⇒ "响应为空"；取回来了但 HTML→文本之后为空 ⇒
"原文非空，但 HTML→文本后为空（可能是只有标签/脚本/样式的页面）"。
两条测试分别钉住"不同故障给不同原因串"（合并成一句会把排查方向带偏）。

**⑥ 门禁数字的分歧已查清**：复核在**干净工作树**跑出 `1491 passed / 4 skipped`，
作者在主检出跑 `1492/3` —— 总数同为 1495，差的 1 条是
`test_pipeline.py::test_real_middle_json_integration`（`skipif` 依赖被 `.gitignore`
忽略、**只在主检出存在**的 `var/mineru_cli_out/…_middle.json`）。⇒ **不是造假，是环境依赖**；
本节起凡引用 pytest 数字都注明工作树（主检出 1518/3）。

**⑦ 事故（自伤，如实记录）**：本步做变异实验时，对**尚未提交**的 `harvest.py` 跑了
`git checkout -- src/core/materials/harvest.py`（想还原变异），结果把这批改动**整份冲掉**。
按同一批编辑重建、复跑（45 passed）后继续。**教训已写进纪律**：变异实验只对**已提交**
的代码跑；必须对工作区文件做实验时，先用 `Copy-Item` 备份（后来的 M7' 就是这样做的，
并用逐字节比对确认还原）。

**仍未做（下一批，按严重度）**：
- [MEDIUM] **Content-Type 与真实字节都拿不到** ⇒ JS/CSS/JSON 接口这类"不是网页正文"的
  响应照样登记；`looks_like_binary` 的 `\x89PNG`/`\xff\xd8\xff`/`\xd0\xcf\x11\xe0`
  在真实路径上是**死代码**（`errors='replace'` 把非 ASCII 首字节变成 U+FFFD），
  而 `tests/test_text_utils.py` 里那条 `f("\x89PNG…") is True` 钉的是传输层产生不了的
  字符串——**断言本身不假，但它测的不是生产路径**（假信心）。
  计划：给传输层一个"带响应头的取回"（一次请求同时给出 headers/text/bytes，
  **不新增 HTTP 客户端**），采集侧据此做 Content-Type 白名单 + **真实字节**的 magic。
- [LOW] `looks_like_binary` 的"零误伤"不成立（`%PDF-` 开头的讲解文、PostScript 源码、
  含 NUL 的 CSV 会被拒）——要把误伤面写进 docstring 而不是声称"零误伤"。
- [LOW] §10.26 的三处计数/措辞（"5 组样本"实为 6 组；"1 条在 test_material_collect"实为 2 条；
  pytest 数字未注明工作树）。

**门禁（本步）**：`pytest` **1518 passed / 3 skipped / 0 failed**（主检出；上一步 1499 ⇒
**+19**，全部在 `test_material_harvest.py`：26 → 45）；`mypy src` **131 files / 0 errors**。
本步**零 JS 改动**，故 JS 门禁未复跑（数字同上一步：冒烟 15 段全过、`verify:commands` 22/22、
`tsc` 0）。两个 HIGH 的修复都用**变异实验**证明非空转（M1 重定向 kwarg、M2 剥离实现、
M7' 判据调用），且**实验后逐字节确认文件已还原**。
### 10.30 收口复核第二批：Content-Type 与**真实字节**（+ 把"零误伤"改成写实）

**做了什么**：给传输层一个**带响应头的取回**，采集侧据此把"这是不是网页正文"的判据
从"猜文本"换成"看事实"。

**① `fetch_page` 契约（`update.channels.base`，两个 transport + 代理版各一份）**
`fetch_page(url, timeout=…, allow_redirects=False) -> (status, headers, text, raw)`。
⚠ 这**不是**第二个 HTTP 客户端：与 `fetch` **同一次请求、同一个 session**，只是把响应上
本来就有的两个字段多暴露出来（`fetch` 只回 `(status, body)`——Content-Type 与真实字节
都在那一层丢了）。三个实现（curl_cffi / httpx / 代理版）契约一致，`fetch` 的老调用方
（公告扫描等）**一行没动**。

**② 采集侧两条新判据（`harvest`）**
- **Content-Type 白名单**：只收 `text/html`、`application/xhtml+xml`、`text/plain`、
  `application/xml`、`text/xml`。**不收**脚本/样式（`text/css`、`*javascript`）、接口
  （`application/json`）、附件（`application/pdf`、`image/*`、`application/zip`）。
  为什么是**白名单**：黑名单永远漏——复核实测 11 条样本里 **9 条**能溜过去。
  服务端**没给** Content-Type 时放行，但 `tier_reason` 里**如实写明"服务端未给"**
  （不是假装检查过）。
- **真实字节的 magic**（`text_utils.looks_like_binary_bytes`）：PNG/JPEG/ELF/OLE2 这些
  **非 UTF-8 首字节**在 `resp.text` 里早被 `errors='replace'` 换成 U+FFFD，
  **文本路径永远认不出**（复核的 REFUTED 那条）。现在按 `resp.content` 判 ⇒
  "Content-Type 撒谎说自己是 html"的 PNG/PDF 也挡得住（有测试与变异实验）。
- Content-Type **记进 `tier_reason`**（`Content-Type: text/html`）：判据**可见 = 可审计**，
  评审人能自己复核白名单判得对不对。

**③ 契约变成**严格**的：没有 `fetch_page` 的 transport ⇒ 抓不了（如实报错）**
不退回 `fetch` 继续登记。理由：退回去就意味着"**在拿不到 Content-Type 与真实字节的情况下**
把材料送进评审队列"——正是这条 MEDIUM 本身，不能因为"换了个传输层"就悄悄复活。
代价：测试替身必须实现 `fetch_page`（本步统一成 `page_transport()` 一个包装，
顺带在那里断言 `allow_redirects is False`——把上一批的契约也一起钉住）。

**④ `looks_like_binary` 的"零误伤"改成**写实**（复核的 LOW）**
docstring 现在写明：文本路径上真正有效的只有 **ASCII 签名 + NUL**（PNG/JPEG 那几条是
死分支，由字节函数兑现）；并**列出已知误伤**——以 `%PDF-` 开头的**讲解文**、`%!PS` 的
**PostScript 源码**、前 4096 字符含 NUL 的 **CSV** 都会被拒收（= 丢材料）。
取舍写明：采集路径上"把二进制当正文"比"拒掉几篇讲文件格式的文章"更坏，所以宁可误伤，
但**不再声称零误伤**，而且把这三条钉成测试（以后要放宽判据，得先改那些断言）。

**⑤ §10.26 的三处计数/措辞已就地更正**（复核的 LOW）："5 组样本"→6 组；
"1 条在 `test_material_collect.py`"→**2 条**（另一条钉"签名在正文**中间**不算"）；
pytest 数字**注明是哪棵树**——干净工作树是 **1491/4**、主检出是 1492/3，差的 1 条是
`test_pipeline.py::test_real_middle_json_integration` 的 `skipif` 依赖被 `.gitignore`
忽略、只在主检出存在的 `var/mineru_cli_out/…_middle.json`（**环境依赖，不是缺陷**）。

**变异实验（三条新判据都非空转，且实验后逐字节确认还原）**：
关掉 Content-Type 白名单 ⇒ **9 failed**；关掉字节 magic ⇒ **3 failed**；
把"缺 `fetch_page`"改回静默降级 ⇒ **1 failed**。
（本步的变异实验**不再用 `git checkout --`**——上一批的事故写在 §10.29 第 ⑦ 条；
这里用 `Copy-Item` 备份 + 收尾 `bytes` 比对，全部逐字节相同。）

**门禁（本步）**：`pytest` **1533 passed / 3 skipped / 0 failed**（主检出；上一步 1518 ⇒
**+15**：`test_material_harvest` 45→57、`test_material_api` 22→23、`test_text_utils` 新增 3 条判据用例）；
`mypy src` **131 files / 0 errors**。JS 侧只改了 `ks_collect` 的**描述**（原来那句
"引擎认不出 JS/CSS/JSON"现在**不成立**了——判据已加强，描述必须跟着改，
否则模型会照着过期前提行事）：冒烟 `smoke:collect` 32/32、`smoke:materials-tool` 34/34。

**诚实边界（仍然成立）**：
- 白名单是**人工列举**的；新类型要**显式**加（漏了就拒收，属"宁可拒"方向）。
- "只看开头"的签名判据认不出**没有签名**的二进制；完整判断要 magic 库（未立项）。
- **Content-Type 撒谎**且**无签名**的组合仍会溜过去（例如伪装成 text/html 的 JSON 接口）。
- 本次仍**没做真联网**：真实公网页面的 gzip 传输、`charset=gbk/gb2312` 中文站点、
  TLS 指纹路径都未验（复核也点出过）⇒ 乱码材料的风险面**未被排除**，只是没证据说它坏。

### 10.31 自查发现（环境相关，**未修**）：httpx 回退传输在本机整体失效

做 §10.29 的变异实验时顺手探了两个真实传输的重定向策略，**顺带发现**一条与本次改动无关、
但后果不小的既有问题：`HttpxTransport`（curl_cffi 不可用时的**回退**）在本机对**任意 URL**
都会抛 `httpx.InvalidURL: Invalid port: ':1]'`。

- **根因不在我们的代码**：本机环境变量 `NO_PROXY=localhost,127.0.0.1,::1,[::1]` 含**带方括号的
  IPv6** 项，`httpx 0.28.1` 解析它时按 `:` 切分而炸（`':1]'` 就是这么来的）。
- **实测证据**：`httpx.get('https://example.com/')` → `InvalidURL`；同一请求加
  `trust_env=False` → **200**。
- **影响面**：本机 curl_cffi 可用 ⇒ `default_transport()` 走 curl_cffi，**生产路径不受影响**；
  但一旦回退到 httpx，公告扫描与材料采集会**整体失败**，而报错信息**不指向** NO_PROXY
  （排查会走弯路）。
- **为什么不顺手修**：`trust_env=False` 能换来"可用"，但会**放弃 env 代理**——那是策略决定，
  不是 bug 修复。已记入方案 §12 已知未决第 8 条，**待业主拍板**（或清洗 NO_PROXY，
  或在失败时给出可诊断提示）。

**顺带得到两条对自己改动的证据**（同一探针）：
- `CurlCffiTransport.fetch_page(..., allow_redirects=False)` 对本地 302 → **302**（不跟随）；
- **默认（跟随）** → `curl: (28) Operation timed out`：**真的向 `169.254.169.254` 发起了连接**
  ——这就是复核报那条 HIGH 的现场复现，也说明 §10.29 的修法确实掐断了它。
- `HttpxTransport` 那条分支**在本机无法这样验证**（它连基本请求都失败，见上）⇒ §10.30 里
  "两个传输都验过"**不成立**，实测只验了 curl_cffi。这是**新的覆盖缺口**，如实登记
  （不假装 httpx 分支也被测过）；`allow_redirects → follow_redirects` 的翻译目前只有
  **代码可读性**上的保证，没有运行时证据。

**门禁**：本步**零代码改动**（只加文档），故未复跑测试；数字同上一步（主检出 1533/3/0）。

### 10.32 修掉自己登记的待办：`materials_scan` 也改回 `def`（慢端点不许占事件循环）

**背景**：写 C-5 的 `collect` 端点时发现同一文件里两种写法并排——`collect` 是 `def`
（15 秒同步抓取，靠 Starlette 的线程池），而 **`materials_scan` 是 `async def`**，
可它做的是**更重**的同步活（逐个 PDF 跑 MinerU 子进程，**分钟级**）。当时写明"超出本步
范围、登记为待办"。本步把它收掉：**一行改动**（`async def` → `def`）+ 一条**结构性**测试。

**为什么这不是小事**：uvicorn 是**单事件循环**，`async def` 端点里的同步 I/O 会把
**整个引擎**卡住——扫描期间连 GUI 的"列项目"都要一起等，用户看到的是"程序死了"。
改成 `def` 后 Starlette 把它丢进线程池，"慢"只慢那一个请求。

**新测试防的是回退**：`TestSlowEndpointsAreDeclaredSync` 用
`asyncio.iscoroutinefunction(route.endpoint)` 断言 `scan` 与 `collect` **都不是**协程函数
——将来谁把它改回 `async def` 会立刻红。**变异实验**（把 `scan` 改回 `async def`）：
该参数化用例里 scan 那一半**变红**、collect 那一半仍绿（正是预期的精确性），
还原后**逐字节确认**与原文件相同。

**顺带更新的注释**：`collect` 那段原来写着"`materials_scan` 同类问题、登记为待办"，
现在改成"已在本步一并改成 `def`"，并把"**凡是做同步重活的端点都该是 `def`**"写进
`scan` 的 docstring（对下一个读者是提示，不只是记录）。

**门禁（本步）**：`pytest` **1535 passed / 3 skipped / 0 failed**（主检出；上一步 1533 ⇒ **+2**
= 新测试的两个参数化用例）；`mypy src` **131 files / 0 errors**。本步**零 JS 改动**。

### 10.33 接上一条"**其实是死的**"的功能：批准 → Track L 自动入库（+ 让用户看得见）

**本步发现的缺陷（自己找的，不是复核报的）**：`track_l.reconcile()` / `import_to_library()`
**没有任何生产调用方**——`materials_review`（唯一的"批准"入口）批准完就返回了。
于是 §10.24 记的"Track L 入库已完成"、方案 §12 的 C-3，在**产品里是死的**：
用户批准一份采到的国标，它能被**当作材料**检索到，但**永远不会**进法条库
（`doc_meta`）⇒ 法条链、`ks_resolve_clause`、效力报告都看不到它。
而业主裁定 J5 写的是"**采到库内没有的法规标准 → 评审通过后自动入库**"。

**怎么查出来的**：做 C-8 的法规识别前先问"现在这条链谁触发？"⇒
`git grep reconcile|track_l` 里除了 `track_l.py` 自己与文档，**没有任何 src/plugin 调用点**。
（这与 §10.17 抓到的"`sanitizeParams` 静默丢掉参数 ⇒ 整条材料链是死的"是**同一类**缺陷：
**模块全绿、测试全过、产品里没人调用**。）

**修法（接线 + 可见）**：
1. `materials_review` 在**批准成功之后**调 `track_l.reconcile(material_id)`，结果放进
   **`data.track_l`**（不是响应顶层——主机侧 `mapProbe` 只转发 `body.data`，
   顶层字段会被**静默丢掉**，那正是"算了但看不见"的老坑）；
2. **只有 `approved` 触发**：`rejected`/`pending` 连 `track_l` 键都不出现
   （"没决策"与"决策=skip"必须能区分，有测试钉住）；
3. Track L 抛错**不改写评审结果**（批准是用户对**材料**的判断，入库是它的**后果**），
   但异常被翻成 `action='error'` + 原因如实回传——**绝不静默**；
   有测试用 monkeypatch 让 `reconcile` 抛错，断言"评审仍是 approved"且"错误在响应里"；
4. `materials_review` 同时改成 **`def`**（入库要写库、可能秒级；并入 §10.32 那条
   "慢端点必须是 `def`"的结构性测试）；
5. **界面看得见**（方案 §7）：面板批准后的回执现在带 Track L 的结果
   （`已自动入库为法条` / `库内已有，已回指` / `未识别，未动法条库` / `⚠ 未完成：原因`），
   `client/api.ts` 的 `KsMaterial` 增 `doc_id` 与 `track_l` 两个可选字段，
   `client.js` 已重建，冒烟加了一条"产物里含该文案"的钉子（50/50）。
   理由：批准一份采到的标准会**自动写进法条库**——那是批准的**副作用**，
   静默通过等于用户不知道自己的库里多了东西。

**顺带被自己的测试抓到的第二个缺陷（已修）**：第一版实现先读 `get_material()` 再跑 Track L，
于是**回指写进库了、返回体里 `doc_id` 还是 null**（界面会显示"没关联"）。
现在 Track L 之后**重读**一行再回传（注释写明为什么必须重读）。
**这条正是"端到端断言"的价值**：只断言 `action='import'` 的实现会全绿，
而用户看到的却是"没关联"。

**门禁（本步）**：`pytest` **1540 passed / 3 skipped / 0 failed**（主检出；上一步 1535 ⇒ **+5**：
4 条 Track L 触发用例 + 1 条 review 入同步端点清单）；`mypy src` **131 files / 0 errors**；
`smoke` **15 段全过**（`materials-routes` 59 → **60**、`client-entry` 49 → **50**）；
`verify:commands` 22/22；`tsc --noEmit` 0。

**诚实边界**：
- 入库是**自动**的（业主裁定如此），但它**只发生在用户点"批准"之后**；且材料来自网页、
  **不是官方原件**——`legal_hierarchy` 等判据仍由既有管线给，本步没有替它决定。
- 生产库现状（只读实测）：`doc_meta` **6417 行全是 `standard`**，`legal_hierarchy` 只有
  `GB`/`GB/T` 两种值 ⇒ **法规库今天是空的**，所以"采到一部法规入库"会是**第一次**有法规行。
  这条链的其它环节（法规树、效力层级）因此**没有被真实数据验证过**（只被单测覆盖）。
- 仍然**没有**法规正文的识别（`looks_like_standard` 只认标准号）⇒ 今天能自动入库的只有
  **带标准号的正文**；法规（`第X条` 形态）会被 `skip`。这是下一步（C-8 ①）。
- Track L 的失败**不回滚**、也没有重试队列：失败只在当次响应里报出（要重试就再评一次）。

### 10.34 法规正文识别（Track L 终于覆盖法规）+ 复核 step-26~step-30 的施工单

**做了什么**：`collect.looks_like_law()` 补上 C-3 留下的那句"走不通"——此前
`looks_like_standard` 复用 `auto_tag` 的**标准号正则**，法规没有号 ⇒ **永远认不出来**
（`track_l.import_to_library` 自己的 docstring 就写着"当前实际只会走标准那一支"）。
现在：

- **识别**（`collect.looks_like_law`，两条信号，都要真有"第X条"）：
  ① 标题是法规形态（`《…》` 或以 `LAW_NAME_SUFFIXES` 结尾）**且**条数 ≥ 3；
  ② 条数 ≥ 10（采网页常丢标题）。条数由 `ingestion.law_text.split_law_text` 数
  ——**第X条切分的唯一所有者**，本函数不新写第二份正则。
- **优先级**：**有标准号就走标准那一支**（标准号判据更精确；带标准号的文本不该被当法规入库）。
- **身份**：`text_utils.law_name_key`（NFKC + 去空白 + 去书名号），
  ⚠ **保留修正年份**——法规靠名称里的年份区分版本，去掉括号会把"库里有 2014 版"
  当成"这部法已经有了"，于是**把 2021 修正版指到旧版上**（引用到过时法条，P1 最坏的后果）。
  跨版本关联是 `doc_meta.short_code` 的事。
- **库内查重**（`track_l.find_existing_law`）：主判据是 `standard_no`（既有法规管线就是
  **用名称当号**：`law_source.ingest._ingest(standard_no=standard_no or d.title)`）；
  `standard_name` 只在**法规类**文档上兜底——**不**拿它去匹配 `doc_type='standard'` 的行，
  否则标准名与法规名偶合时会把该入库的法规**静默跳过**。
- **入库**：法规走 `ingest_law_text(..., doc_type='法律法规', short_code=None)`，
  `standard_no` 传法规名；**层级由 `_law_hierarchy` 保守推断**——只有
  "以 `法`/`法典` 结尾 ⇒ 法律（狭义）"与"含司法解释字样 ⇒ 司法解释"两条安全规则，
  其余（`条例`/`办法`/`规定`：国务院的？省人大的？部门规章？**要看发行机关，采网页拿不到**）
  一律 **`未定`**，并把这句"层级是我们推断的"写进材料的判级说明（评审人看得到）。

**被自己的测试抓到的两处错（都已修 + 钉住）**：
1. `中华人民共和国民法典` **不以"法"结尾**（结尾是"典"）⇒ 第一版**取不到法规名**，
   `is_law=False`（中国最重要的一部法律认不出来）。已把 `法典` 单列进后缀表。
2. `_law_hierarchy` 用 `endswith("法")` 会把 **`安全生产违法行为行政处罚办法`** 判成
   **"法律"**——一个**写进法规库的错误位阶**（`办法` 是规章）。已排除 `办法/方法/做法`。
   这条正是"保守推断"存在的理由：宁可写 `未定`，也不猜。

**改了一条旧测试（并说明为什么必须改）**：`test_collected_LAW_text_is_out_of_scope_today`
原来**钉住"法规走不通"**（C-3 的已知边界）。本步把它换成
`test_collected_LAW_text_is_now_recognized_and_imported`——**旧断言如果不改，它会变成
一条阻止修复的假门**（修复一落地它就红）。新测试断言：识别（`doc_kind='law'` + 名称）、
未批准仍 `blocked`、入库后 `doc_meta` 里 `doc_type='法律法规'`/`standard_no=名称`/
`legal_hierarchy='法律'`、`find_existing_law` 找得到、**再评一次退化为 `link` 不造第二部**。

**⚠ 独立复核 step-26~step-30 的结论（2026-09-17，`var/tmp/verify-b5-artifacts/`）**：
A/C/D②/E/I **PARTLY**；B/D①/F/G/H/J **CONFIRMED**（含 10 个自做变异体 9 RED / 1 GREEN，
以及真 uvicorn 下的并发测量：`collect` 睡 2.0s 时 `tiers` **0.004s** 返回，
而 async 对照组挡住 **1.188s**——§10.29 那条"慢端点必须是 def"的立论被**实测证实**）。
**三个 MEDIUM 与若干 LOW 是下一步的施工单**（按"静默失效 + 安全"优先）：

- **[MEDIUM] `ks_collect` 对"`data` 里没有 `collected` 字段"不抛**，返回 `collected:false`
  ——与 §10.28 写明的"抛"**相反**，且会把"引擎信封形状变了/版本不匹配"**谎报成"没采到"**
  （引擎那边可能**已经登记了** pending 材料）。更糟的是**我的冒烟把相反行为钉住了**
  （复核按文档加抛后 M7 变红）。⇒ 单列信封异常并抛 + 改冒烟。
- **[MEDIUM] 采集端点只挡 `source_tier` 一个拼写**：`sourceTier`/`tier`/`review_status`/
  `origin` 等一律 200 + **静默忽略**——与"响亮拒绝、绝不静默丢弃（`sanitizeParams` 同款坑）"
  的立论直接冲突（硬门未松动，危害是误导调用方）。⇒ 请求体**白名单**校验（未知键 422），
  引擎与主机两层都做。
- **[MEDIUM] `_strip_script_style` 两个方向都留缺口**（21 组边角 5 组异常）：
  **LEAK** `text/html` 下 `<script src="a.js"/>…</script>`（HTML5 里 `/` 不自闭合，
  到 `</script>` 之间**是**脚本内容，我却按 XHTML 当自闭合 ⇒ JS 进正文）；
  **OVERKILL** `<!-- <script> -->`（注释里的脚本标签让我把其后正文**整段吞掉**=丢材料）、
  `</script foo>`（合法结束标签认不出）、正文里字面 `<script>`。⇒ 先剥 HTML 注释、
  结束标签放宽为 `</(script|style)\b[^>]*>`、自闭合判定按 **HTML5 语义**（我们收的是 text/html），
  并**回头改**§10.29 那条按 XHTML 语义写的用例与措辞。
- **[LOW]** `_content_type_of` 只认已小写的 `content-type` 键（传输层会小写，但替身/未来
  传输层传混合大小写就**整道白名单被静默跳过**）；会话上限判断在 `ensureLive()` **之后**
  （超限时仍会拉起引擎）；`harvest.py` 模块头注**过期**（仍称拿不到 Content-Type，
  属**低报自身能力**）；`looks_like_binary` 的 ASCII 清单少列 3 个；上限数值 `20` 无钉子；
  `ks_collect` 对硬塞的 `source_tier` 静默忽略；§10.27"三条契约"vs 正文"四条"、
  §10.26"6 组样本"实为 8 组、§10.26 残留"零误伤"未标更正、§10.27/方案"界面侧已通"
  **过度声称**（全仓**无任何 GUI 调用** `/ks/materials/collect`）。
- **[INFO/未覆盖]** 真公网传输（gzip 实解压、`charset=gbk` 中文站、TLS 指纹）仍未验；
  `HttpxTransport` 因本机 `NO_PROXY` 无法运行时验证（§10.31 的自我更正确认成立）；
  **当前 DSH 会话的工具表里没有 `ks_collect`/`ks_materials`** ⇒ 宿主插件也要重挂载
  （复核点出：作者只登记了"引擎需重启"）——**这是"真机可用"的最后一道门**。

**门禁（本步）**：`pytest` **1546 passed / 3 skipped / 0 failed**（主检出；上一步 1540 ⇒ **+6**：
`test_material_collect` 新增 4 条法规识别用例、`test_material_track_l` 新增 3 条
（法规入库 / 无名拒绝 / 层级保守），并**替换**掉原来那条"钉住走不通"的用例）；
`mypy src` **131 files / 0 errors**。本步**零 JS 改动**。

### 10.35 收口复核 step-26~step-30 的三个 MEDIUM（+ 一批 LOW/INFO）

**① [MEDIUM] `ks_collect` 把"信封形状不认识"谎报成"没采到"——已修**
复核实测与文档**相反**：`data` 里没有 `collected` 字段时，实现回 `collected:false`
（文档 §10.28 写的是"抛"）。为什么必须抛：形状不认识时引擎**可能已经登记了**一条 pending
材料，而回 `false` 会让模型对用户说"没采到"——**一句可能是假的话**（P1 准确性）。
现在 `data.collected === undefined`（或 data 不是对象）**单列信封异常并抛**；
"合法的抓取失败"（`collected:false` + reason）仍如实回报。
⚠ 更值得记的是：**我的冒烟原来把相反行为钉住了**（复核按文档加抛后 M7 变红）——
已把那条断言改成"必须抛"，并**另加**一条"合法失败不抛"（两者必须同时成立才叫对）。

**② [MEDIUM] 采集端点只挡 `source_tier` 一个拼写——已修（白名单）**
复核实测：`sourceTier`/`tier`/`review_status`/`origin`/`lifecycle`… 一律 **200 + 静默忽略**，
与"响亮拒绝、绝不静默丢弃（`sanitizeParams` 同款坑）"的立论直接冲突
（硬门未松动，危害是**误导调用方**：它以为自己设上了）。
现在**引擎与主机两层都做请求体白名单**：只收 `url/title/note/published_at`，
未知键 422/400 并**列出**未知键名（`source_tier` 保留更具体的那句话）。
白名单比黑名单可靠：以后新增字段必须**显式**加。测试 +7（参数化 7 个键）。

**③ [MEDIUM] `_strip_script_style` 两个方向都留缺口——已修（并按 HTML5 定语义）**
复核 21 组边角里 5 组异常，两类：
- **LEAK**：`text/html` 下 `<script src="a.js"/>` 的 `/` **不表示自闭合**（HTML5），
  到 `</script>` 之间**是**脚本内容，而我按 XHTML 当自闭合 ⇒ **JS 进了正文**。
- **OVERKILL**：`<!-- <script> -->`（注释里的标签不是标签 ⇒ 其后正文被**整段吞掉**）、
  `</script foo>`（浏览器接受的结束标签，第一版认不出 ⇒ 同样吞掉）、
  属性值里的字面 `<script>`（`title='<script>'`）。
修法三条：**先剥 HTML 注释**；**结束标签放宽**为 `</(script|style)\b[^>]*>`；
**自闭合按 HTML5**（不特殊处理）。另外给开标签加 `(?<!["'])`，挡"属性值里的字面标签"。
⚠ **两种读法直接冲突**（第一轮复核把 XHTML 读法当成 HIGH、第二轮把 HTML5 读法当成 LEAK）：
本函数选 **HTML5**（浏览器怎么解析，正文就怎么算），代价（XHTML 页面会丢一段正文）
写在 docstring 里并**登记为待办**（按 Content-Type 分流需要把 content-type 传进来）。
⇒ 我把 §10.29 那条按 XHTML 写的用例**改了方向**并写明为什么（不写清就等于埋雷）。
⚠ **本行的更正（2026-09-17，见 §10.39 末）**：原文写"复核的 5 组异常现在**全过**
（16 组探针 0 BAD）"——那是**缩了探针集**的说法。把复核自己的 `probeD.py`
（**21 组**）原样拿回来复跑，实测是 **20 OK / 1 OVERKILL**：剩下那 1 组是
"正文里**未转义**地提到 `<script>` 标签"（`<p>关于 <script> 标签的说明</p>`）——
按 HTML5 它就是**脚本开始**、吞掉后文，**与浏览器一致**，属于本选择已登记的代价，
不是回归。原句容易读成"21 组全过"，故在此改正。

**④ [LOW/INFO] 其余一并收掉**：`_content_type_of` 改成**键名大小写不敏感**
（否则替身/未来传输层传 `Content-Type` 会**整道白名单静默跳过**）；
`ks_collect` 的**会话上限判断前移到 `ensureLive()` 之前**（复核实测超限时仍会把引擎拉起）；
硬塞进 `source_tier` 的调用**响亮拒绝**（不再静默忽略）；
上限数值 `20` 加**钉子**（复核指出改成 1e6 也全绿）；`ProxyCurlTransport.fetch_page`
**显式** pop `allow_redirects`（不再靠"`**kw` 恰好透传"）；`looks_like_binary` 的
ASCII 可达清单**补全为 7 个**（复核实测；原列 4 个）；`harvest.py` 模块头注**过期**
（仍称"拿不到 Content-Type"——**低报自身能力**）已重写。
文档措辞（复核 I 的 6 处）**就地更正**：§10.26"6 组样本"补"该测试当时"、残留的
**「零误伤」**加更正标记、§10.27 标题"三条契约"→**四条**、§10.27/方案 §12 的
**"界面侧已通"→"同源路由已通"**（全仓**没有任何 GUI 调用** `/ks/materials/collect`，
复核 J 查得比作者彻底）。

**复核**（`var/tmp/verify-b5-artifacts/`，工作树已清理）**独立确认的几条**（记下来，
因为它们比作者的自述更强）：B——真 uvicorn 单循环下 `collect` 睡 2.0s 时 `tiers`
**0.004s** 返回，而 async 对照组挡住 **1.188s**（§10.29 的立论被实测证实）；
D①——`allow_redirects=False` 拿到 302（0.00s），改回 True 后 curl(28) 超时 3.02s =
**真的向 `169.254.169.254` 发起连接**；G——自做 **10 个变异体 9 RED / 1 GREEN**，
作者报的 9/3/1/4 failed 全部复现；H——数字逐项一致（工作树 1532/4 与主检出差 1 条，
原因已独立确认）。**仍未覆盖**：真公网传输（gzip/charset/TLS 指纹）、
`HttpxTransport` 的运行时验证（本机 NO_PROXY 使 httpx 整体失效）、
线程池/SQLite 连接上界压测、**宿主插件重挂载**（复核发现**当前 DSH 工具表里没有
`ks_collect`**——引擎重启之外还有这道门）。

**门禁（本步）**：`pytest` **1557 passed / 3 skipped / 0 failed**（主检出）；`mypy src`
**131 files / 0 errors**；`smoke` **15 段全过**（`smoke-collect-tool` 32 → **35**、
`smoke-materials-routes` 60 → **65**）；`verify:commands` 22/22；`tsc --noEmit` 0。
变异实验：`_strip_script_style`（两条线索）、`_content_type_of` 三处修复各用一次变异确认非空转。

**⚠ 变异实验当场抓到"我的修复没有被测到"**：`_content_type_of` 的键名大小写修复
第一次跑变异体是 **GREEN（101 passed）**——**代码修了、测试没跟上**。补了一条
"替身返回 `Content-Type` 大写键 ⇒ 必须仍被白名单拒"的用例后再变异，才变红。
⇒ 记下来：**"改了实现"与"改了实现并被钉住"是两件事**，两者都做完才算收口。

**⚠ 顺手确证了一条长期"无名"的门禁噪声**：全量跑抓到
`tests/test_deep_server.py::test_提交与等待拆分_先投后收` 失败一次——正是方案 §12 第 1 条
记了很久的那条偶发（此前**因控制台编码打乱而不点名**）。现在有了**确切用例名**，
并给出隔离证据（该文件单独跑 8/8、该用例单独跑 3/3，0.28~0.56s）与判断
（时序/GIL 敏感：那个用例把 `ds.time.sleep` patch 成空操作，fake daemon 与主线程抢 GIL）。
**未修**，但已从"无名噪声"变成"有名字的待办"（记入方案 §12 第 1 条）。
另有一条 chatmode 偶发（`a session closed by this process is not resurrected from disk`）
在**串行链**里红过一次、之后单独跑与高负载并发跑都 **3/3 绿**，**未能复现**；
已把 `persisted=…` 打进那条断言的详情，下次红时能一眼分清"写盘失败"与"复活逻辑错"——
**没有**加"失败就重试"来掩盖它。

### 10.36 Phase D 第一步：**研究报告导出**（材料平面终于有了自己的产出物）

**为什么是这一步**：到 §10.35 为止，"参考资料平面"能把材料**收进来、评审、按承重能力分组**，
但**产出物**这一侧只有《问答依据清单》与《审查报告》——都不包含"这一轮用了哪些参考资料、
两个轴是什么、还有哪些没批准"。而业主的原始要求是"经用户评审确认参考资料可用后再做
**分析/产出**（报告、PPT）"。方案 §8 写着：PPT 要**单独立项**（要论证值不值），
**退路是先出 Markdown/HTML**。本步就是那条退路——**零新增依赖**，能立刻交付。

**做了什么**：`src/core/exports/research_report.py` + 引擎 `POST /api/v1/report/research`
+ 主机 `POST /ks/report/research`。报告分六节：研究问题 / 结论（调用方给）/ **依据（按承重
能力分组）** / 已批准参考资料清单 / **尚未批准的材料（如实列出）** / 已知限制。
Markdown 与 HTML **从同一份结构化文档渲染**（不引 markdown 库、不做 MD→HTML 转换），
HTML 侧一律 `html.escape`。落盘到既有 `exports/` 目录（**不外发**）。

**三条纪律**：
1. **分组不另写一份**：依据一节直接用 `materials.authority.assemble_evidence()` +
   `render_evidence()`（承重分组、两个轴、`[[m:i]]` 编号都只有一个所有者）；
   有测试断言"分组标题必须来自 `authority.GROUP_ORDER`"。
2. **引用可核**：结论里的 `[[m:i]]` **逐条校验**——编号不存在 ⇒ `unknown`；
   落在 `leads_only`/`excluded` ⇒ `not_load_bearing`（**引用了不该承重的东西**）。
   两条都进 `warnings`（**绝不静默**）。负数编号也抓（历史缺陷：提示词侧曾漏 `[[m:-1]]`）。
   ⚠ 诚实边界：`[[c:i]]`（法条）在本次导出里**无法校验**（要问答上下文的证据集），
   如实计成 `unchecked_law_refs`；**没给 `query` 就没有依据集可比**，那时会明确说
   "无法校验"，而不是假装查过。
3. **不假装完整**：未批准/已拒绝材料**如实列出**；"没有已批准材料"是一句明说，
   不是一片空白（可见性硬需求 §7）。

**顺带补掉一个真实的覆盖缺口（自查发现）**：`/ks/report/*` 四条路由**此前一条冒烟都没有**
（全仓 `plugin/scripts` 里没有任何文件 import `report.js`）。新增
`smoke-report-routes.mjs`（**19 项**）覆盖：注册面/方法守卫/query 白名单/body 白名单/
二进制回传链（POST 生成 → GET 下载 → xlsx MIME + 中文文件名）/错误映射。
⇒ 这正是"改了实现但没测到"的老毛病，**这次没等复核来指出**。

**顺手修掉一个归因错误**：`route_util.mapProbe` 原先把引擎的 **404**（"项目/材料 id 不存在"）
翻成 **502 `engine_error`**——用户看到"引擎错误"会去查引擎，而真正的原因是他给了个不存在的 id。
现在 **404 原样透传**（带上引擎的原因），与 `docimage` 那条路由的既有约定一致；
新冒烟里有一条专门钉它（"引擎 404 → 同源 404 且带出引擎的原因，不是 502"）。

**门禁（本步）**：`pytest` **1577 passed / 3 skipped / 0 failed**（主检出；上一步 1557 ⇒ **+20**
= 新文件 `tests/test_research_report.py`）；`mypy src` **132 files / 0 errors**（+1 新模块）；
`smoke` **16 段全过**（新增 `smoke:report-routes` **19/19**）；`verify:commands` 22/22；
`tsc --noEmit` 0。
**变异实验**：`_check_citations` 恒返回空 ⇒ **4 条引用用例变红**；`_to_html` 不转义 ⇒
**转义用例变红**（两次都逐字节确认还原）。

**诚实边界**：
- **PPT 仍未做**（方案 §8 要单独立项：新增 `python-pptx`，且本仓有"0 import 就删依赖"的纪律）。
  本步只交付了 Markdown/HTML 这条退路。
- 报告的**结论正文由调用方给**（模型/用户）——引擎不生成结论，只负责"依据、引用校验、
  未批准清单、限制"这些**可核**的部分。这符合"引擎只做可验证的事"的分工。
- **还没有 GUI 入口**（同 `collect` 的现状）：路由已同源可达（脚本/模型工具可调），
  面板上没有按钮；`client` 侧未改（本次`client.js`未重建）。
- 报告是**纯文本/markdown**，不含图表；`.docx` 侧仍未扩到"材料平面"（既有 docx 导出是
  问答依据/审查报告两条，各自用途不同，**没有**顺手合并）。

### 10.37 复核 step-31~34 的**数据污染**缺陷：法规识别误伤（+ 宪法位阶）

复核（`var/tmp/verify-b6-artifacts/`）给了一条比"识别不准"重得多的发现，**端到端实测**：

**[MEDIUM-HIGH] 一篇新闻被认成《安全生产法》，并**挤掉**了真法规**
- 现象：新闻正文首行出现 `《中华人民共和国安全生产法》`（新闻/判决书/合同都这么引法条），
  第一版 `_law_name_of` 会扫"正文首行 120 字里的任意 `《…》`" ⇒ 认成法规
  `law_name='中华人民共和国安全生产法'`；**批准后真的往 `doc_meta` 插了一行**
  （`standard_no=中华人民共和国安全生产法`、`standard_name=新闻标题`、`doc_type=法律法规`）。
  更重的一步：此后采到**真**《安全生产法》全文再批准时，`find_existing_law` 命中那行新闻
  ⇒ 决策是 `link`、`imported=False` ⇒ **真法规全文永远进不了库**（脏数据拦住真数据）。
  合同（《设备采购合同》）、判决书（正文引《合同法》）同理。
- 第一版 docstring 写着"宁可不认，也不要把新闻当法规"——**那句话当时是空话**。
- 修法（现在它真的是判据）：**四条证据齐了才算法规**
  ① 标题是法规名（`_law_name_of` **只看标题**；标题 ≤40 字、**不含句读**、
     候选不得以 `合同/协议/判决书/…` 结尾）；
  ② 条文**从「第一条」开始**（新闻/判决书引的是第三条、第四条）；
  ③ 正文有**立法句式**（`本(法|条例|规定|办法|规则|细则|决定)`）；
  ④ 条数 ≥3；**没有可用标题时**要 ≥10 条且同样满足 ②③。
  另外把 `通知` 从"法规后缀"里**去掉**（`《…通知》` 绝大多数是公告/新闻标题——
  这条是被新用例当场抓出来的：`某部门通知` 曾被当成法规名）。
  版本括注（`（2021年修正）`）**保留**（身份的一部分），`（节选）` 这类非版本括注**去掉**。
- **变异实验**（两次，逐字节还原）：摘掉 ②③ ⇒ **3 条误伤用例变红**；
  把"只看标题"退回"扫正文首行" ⇒ **根因用例变红**（`test_law_name_is_never_taken_from_the_body`）。

**[MEDIUM] 宪法被判成「法律」——已修**
`中华人民共和国宪法` 以"法"结尾 ⇒ 原来返回 `法律` ⇒ `doc_catalog._HIER_TO_TIER` 直映到
**「法律（狭义）」**（那句 `if "宪法" in text` 的兜底**永不生效**，因为层级能直映）。
现在 `_law_hierarchy` **先判宪法** ⇒ 返回 `宪法`（目录里对应「宪法及宪法相关法」这一档）。
测试加了 `宪法` 与 `宪法修正案` 两条。⚠ 我原来只钉了 `办法/方法/做法`——**别的"以法结尾
但不是法律"的写法没想到**，这条是被复核补上的。

**⚠ 复核同时证伪了我 §10.33 的一句断言（如实更正）**：我写过"落库的标准号写法与库内既有行
不统一**不是判据问题**"。复核实测：`auto_tag` 的归一形 **`GB88888-2088`（无空格）**过不了
`doc_catalog._STD_NO_PREFIX` 的 `\b` ⇒ Track L 入的标准被 `classify_document` 归到
**`top='law'`（法规树）**；且 `ingest_law_text` 里 `classify_clause(..., doc_type="法律法规")`
是**写死**的 ⇒ 标准条款的 `knowledge_type` 成了 `legal` 而不是 `rule`。
**⇒ 那句断言是错的**，而且它正好挡住了"该做的归一化"。这两条（拼写归一 + `doc_type` 透传）
以及下面三条已登记为下一步施工单，**本步未修**。

**下一步施工单（复核 step-31~34 的其余发现，按严重度）**：
- [MEDIUM] **Track L 入的标准进错树 + 条款类型判错**（见上，含 `doc_type` 透传与写库拼写归一）。
- [MEDIUM] **网页文本落库即"现行有效 + A 级 + 强制性"**：`clause_repo.insert_document` 的默认值
  （`legal_status='effective'`、`quality_grade='A'`、`standard_type='mandatory'`）会被这条
  新接通的路径直接吃下 ⇒ 未核验的网页文本会被 `ks_answer` 当**现行有效**引用、
  效力报告算 🟢。§10.33 的诚实边界**没有披露这一层默认**（复核补的）。
- [LOW] query 串里的未知键被静默忽略（`?source_tier=T0` → 200，无状态影响）；
  `_strip_script_style` 又两处偏差（无引号属性值 `title=<script>` 吞后文、
  `foo<!--x-->bar` → `foo bar`）；方案 §12 的 **C-11 仍写「未做」**（`4153735` 已收口）；
  §10.35 的"21 组里 5 组全过（16 组探针 0 BAD）"是**缩了探针集**的说法，应写明；
  `application/xhtml+xml` 被白名单接收却按 HTML5 解析，"待办"只写在 docstring 里。
- [LOW] 两个测试缺口：**优先级契约在"真冲突"下无覆盖**（复核 M13 把 `elif` 改成 `if` 全绿）；
  `law_name_key` 的"保留修正年份"没有**直接**断言（复核 M11 变红是别的测试的 UNIQUE 约束连带抓到）。

**门禁（本步）**：`pytest` **1594 passed / 3 skipped / 0 failed**（主检出）；`mypy src`
**133 files / 0 errors**；`smoke` **16 段全过**（`smoke-report-routes` 24/24）；
`verify:commands` 22/22；`tsc --noEmit` 0。

### 10.38 Phase D 第二步：**PPT 导出**（"报告、PPT"里最后那块）+ 一次**提交混装**的自记

**⚠ 先说流程上的自记**：这一段的改动**与 §10.37 的法规修复混在同一个提交里**
（`dc1935d`），而那条提交信息与快照标签（`step-36-law-false-positive-fix`）**只写了法规**。
原因是"PPT 写完 → 复核结论回来 → 直接接着修"而中间没有提交。**代码与测试都在**，
但历史把两件事记在一起了 ⇒ 本节补上 PPT 那半的记录，并把这次混装**写出来**（下次先提交再开新活）。

**立项论证（方案 §8 要求 PPT"单独立项、先论证值不值"——这就是论证）**：
1. **内容模型已经有了**：§10.36 的 `research_report.build_report_blocks()` 产出结构化内容块，
   PPT 只做"块 → 幻灯片"的映射（**不重新组织内容**）⇒ 边际成本是一个薄映射 + 一次落盘，
   **不是**一条新管线；也保证"报告写的和 PPT 写的是同一份内容"。
2. **依赖几乎不新增**：`python-pptx` 是纯 Python 包，其依赖（`lxml`、`Pillow`）在本仓
   已因 `python-docx` 等存在（实测 `lxml 6.1.2`、`PIL 12.3.0`）。⚠ 实测本机 venv 里
   `pptx` **早就在**（1.0.3），但那是**传递依赖**恰好满足——与 `requests/bs4` 那条教训**同型**
   ⇒ 按 `pyproject.toml` 既有惯例**显式声明** `python-pptx>=1.0` 并写明调用文件
   （"0 import 就删依赖"的反面：**有 import 就必须声明**）。
3. **业主明确要过**（原始要求"报告、PPT"），而 §10.36 只交付了 Markdown/HTML（"自行转"）。

**做了什么**：`src/core/exports/slide_export.py`（`build_slides` 纯映射 + `write_slide_deck`
落盘）+ 引擎 `POST /api/v1/report/research/slides` + 主机 `POST /ks/report/research/slides`
（同款白名单转发）+ `pyproject.toml` 声明依赖 + `tests/test_slide_export.py`（**11 条**）
+ 冒烟 +5（`smoke-report-routes` 19 → **24**）。三条纪律写进了模块头注：
**内容只从 `build_report_blocks` 来**；**诚实**（要点 >300 字截断并标 `…`、页数 >30 时
**在 PPT 里**写明"后续见 Markdown 报告"、末页固定写"本机生成未外发 / 两个轴分开看 /
仅线索不得单独支撑结论 / 待评审不进结论"）；**不假装 pptx 可用**（缺依赖抛**可操作**的错误）。
**测试非空转**：`_check_citations` 恒空 ⇒ 4 条引用用例红；`_to_html` 不转义 ⇒ 转义用例红
（§10.36 那批）；本步 PPT 侧的 `build_slides` 用"空页会掉 / 截断带 `…` / 超限写在末页"
三条断言钉住。

**诚实边界**：
- **还没有 GUI 入口**（与 `collect`、Markdown 报告同一现状）：路由同源可达（脚本/模型工具可调）。
- PPT 用的是 python-pptx 的**默认版式**（没有做设计/母版）；要点是**纯文本**（不做富文本、
  不插图、不嵌表格）——要更好看得引入模板（未立项）。
- 300 字/要点、30 页是**硬上限**（写死在常量里，超了会**说明**而不是静默丢）。
- `.docx` 侧仍未扩到材料平面（三条导出用途不同，**没有**顺手合并）。

**门禁（这段）**：`pytest` **1594 passed / 3 skipped / 0 failed**（其中 PPT 侧 +11）；
`mypy src` **133 files / 0 errors**；`smoke` **16 段全过**（`smoke-report-routes` **24/24**）；
`verify:commands` 22/22；`tsc --noEmit` 0。

### 10.39 复核 step-31~34 的 ③④：**采集件进对树、判对型、写诚实元数据**

**为什么这两条是 MEDIUM 而不是"小瑕疵"**：它们都是**新接通的那条路**（§10.33 才把
`track_l` 接到评审批准之后）上的默认值/判据问题，而**默认值不会报错**——
错误会**静默地写进库里**，再被 `ks_answer` 和效力报告当成事实用。两条：

**③ 进错树 + 判错条款类型**（复核实测）
- `doc_catalog._STD_NO_PREFIX` 用 `\b` 收尾：`auto_tag` 抽出来的归一形是**无空格**的
  `GB12321-2021`，而 `GB` 与 `1` **都是词字符** ⇒ `\b` **不成立** ⇒ 标准被归到
  **法规树**（`classify_document` 的 `top='law'`）。`DB11/T 1234-2020`（地方标准）
  同样过不了；`GBZ`（职业卫生）压根**不在白名单**里。
- `ingest_law_text` 里 `classify_clause(..., doc_type="法律法规")` 是**写死**的 ⇒
  Track L 入的**标准**条款拿到 `knowledge_type='legal'`（**标准条款不是法条**）。

**④ 落库即"现行有效 + A 级 + 强制性"**
`clause_repo.insert_document` 的默认是 `legal_status='effective'`、`quality_grade='A'`、
`standard_type='mandatory'`。对**官方原件**（docx/官方法规源）那是合理的；但采集件
**来自网页**，我们并不知道它是否现行、是否清晰、是不是强制 ⇒ 吃默认值的后果是
`ks_answer` 把它当**现行有效**引用、效力报告把它算 **🟢**（真实状态是"**未知**"）。
§10.33 的诚实边界**没有披露这一层默认**（复核补的）。

**做了什么**（4 文件，+173/−11）
1. **修在判据的所有者**：改 `doc_catalog._STD_NO_PREFIX` 的边界为
   `(?=[\s/]|\d)`（后面是空白/斜杠**或数字**），并补 `GBZ`。**没有**改成"把
   `standard_no` 写个空格"——那样只是让**这一条**数据好看，任何未来的无空格写法
   照错（`DB11/T` 就是同一个家族）。
2. `ingest_law_text` 加 `clause_doc_type`（条款分型用哪个 `doc_type`，**不给就跟随
   `doc_type`**），`track_l` 两个分支分别显式传 `"法律法规"` / `"standard"`。
3. 加三个**落库值**参数（`legal_status`/`quality_grade`/`standard_type`），用
   `"__default__"` **哨兵**区分"调用方没给"（沿用既有默认，docx/官方法规源**行为不变**）
   与"调用方要给 `NULL`"（采集路径就是要 `None`）。为什么不用"不传 `None` 就写 `None`"：
   那样会把既有调用方的默认**悄悄改掉**，属于另一条改动。
4. `track_l._collected_doc_meta()` → `{legal_status: None, quality_grade: 'C',
   standard_type: None}`，**两个**入库分支都带上。为什么是 `C` 不是 `B`：`doc_meta`
   的 `quality_grade` 契约里 A 要求清晰度/OCR ≥0.95，采网页没这回事；
   `C` 与既有 `ingestion.bulk` 的骨架行**同口径**。为什么 `standard_type=None`：
   `query/understanding.py` 用 `== 'mandatory'` 加权，`None` 自然**不加权**
   ——正是"不知道就别加权"。
5. 测试 **+16**（`tests/test_material_track_l.py` 33 → **49**）。

**测试非空转（4 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step38.py`
+ `var/tmp/run-mutations-step38.py`
- A（`\b` 退回）⇒ **6 failed**（`TestTreeClassificationOfStandardNumbers` 5 例 +
  落库那条的树断言）；
- B（写死 `"法律法规"`）⇒ **1 failed**（`test_imported_standard_clauses_are_rules_not_legal`）；
- C（**标准**分支去掉 `**_collected_doc_meta()`）⇒ **1 failed**；
- D（**法规**分支同上）⇒ **1 failed**（见下"当场抓到的假绿"）。
四个变异体跑完，三个源文件 sha256 **与变异前逐字节一致**。

**⚠ 当场抓到一次"假绿"，这条方法论值得记**：C 的**第一版**锚点打在**法规分支**上
（`**_collected_doc_meta(),` 在文件里出现两次，脚本只替换第一处），而当时的测试用的
采集件是**标准** ⇒ 变异根本没进被测路径 ⇒ **全绿**。我据此差点把"诚实元数据"记为
"测不到"。修法两条：①锚点改成靠 `status = result.get("status")` **唯一定位标准分支**；
②**这不是脚本 bug 而是测试缺口**——法规分支的元数据**一行断言都没有**（`**_collected_doc_meta(),`
整行删掉不会红）。于是在 `test_collected_LAW_text_is_now_recognized_and_imported`
里补 `legal_status is None / quality_grade == 'C' / standard_type is None` 三条，
D 随即变红。
> 教训：变异体"绿"有两种原因——**修复是空转的**，或者**变异体没打在路径上**。
> 不查清是哪一种就把结论写成前者，是**用方法论给自己的漏洞背书**。

**诚实边界**：
- **两个"未知"的口径是保守的，不是完备的**：`legal_status=None` 让效力报告落 ⚪
  「状态未知/未登记」。它表示"我们没核验"，**不表示**"它已废止"。要真正给出效力，
  得回到官方来源逐条核验（未立项）。
- **`quality_grade='C'` 是"未核验"的代理值**，不是对文本质量的实测评级。
- 层级（`legal_hierarchy`）仍是**名称推断**：`条例`/`办法` 一律 `未定`
  （判位阶要看**发行机关**，采网页拿不到）——**不假装知道**。
- **没有做写库拼写归一**（复核原话里提到的那种）：改的是**判据**，`doc_meta` 里
  仍然存采集时那个写法（`GB12321-2021`）。归一要动的是入库管线的既有契约，
  影响面比这两条 MEDIUM 大（未立项）。
- **GUI 与真机接线仍未验证**（与 §10.36/§10.38 同一现状，两道门：引擎重启、
  宿主插件重挂载）；**本步没有跑真机**。
- 采集预算（§11.4 的 `MAX_COLLECT_PER_SESSION = 20`）仍是**暂定值**。

**门禁（本步）**：`pytest` **1610 passed / 3 skipped / 0 failed**（`test_material_track_l`
33 → **49**）；`mypy src` **133 files / 0 errors**；`smoke` **16 段全过**
（`smoke-report-routes` 24/24、`smoke-collect-tool` 35/35）；
`verify:commands` 22/22；`tsc --noEmit` 0。变异实验 4 个全 RED 且逐字节还原。

**遗留（C-12 ⑤ 的若干 LOW，留给下一步）**：query 串未知键静默忽略
（`?source_tier=T0` → 200）、`_strip_script_style` 的两处非 HTML5-精确边角
（无引号属性值里的 `<script>`、`foo<!--x-->bar` → `foo bar`）、方案 §12 的 C-11
陈旧状态、`application/xhtml+xml` 分流只写在 docstring、两个测试缺口
（优先级契约在**真冲突**下无覆盖、`law_name_key` 保留修正年份无**直接**断言）。
`_strip_script_style` 那两处要精确只能**写一个 HTML 分词器**——本步**没有**做，
它们与本步的"判据归属"问题不同族，登记而不是顺手改。

### 10.40 收口 C-12 的 ⑤（那批 LOW）：一条**真缺陷**、两条测试缺口、两条登记不改、一条有意不改

复核把 ⑤ 归成"若干 LOW"。**逐条走下来不都是 LOW**——按"先实测再定性"（P1 准确性），
其中一条实测是**静默的内容损失**，属于真缺陷；另有**一条复核判定被证据更正**。

**① `_strip_script_style`：无引号属性值里的字面 `<script>`（真缺陷 ⇒ 已修）**
- 复核给的输入：`<p>前</p><p title=<script> 可见甲</p><p>后</p>`。第一版实测输出
  **`'前<p title='`** —— "可见甲"与"后"**整段丢掉**，且**不报错**（`var/tmp/probe-step39-edges.py`）。
- 机理：开标签正则 `(?<!["'])<(script|style)\b[^>]*>` 里的 `(?<!["'])` 只挡**引号**包住的
  属性值；无引号时 `<` 前是 `=`，守卫不成立 ⇒ 把属性值里的字面 `<script>` 当成了真标签。
- **HTML5 到底怎么解析**（判据必须跟浏览器，不能用"我觉得"）：`<` 在**无引号属性值**里
  属于属性值（parse error 但继续），标签在**下一个 `>`** 处结束 ⇒ `<p title=<script`
  是一个完整标签，**"可见甲"是正文**。所以第一版是**丢正文**，不是保守。
- 修法（新守卫 `_inside_unclosed_tag`）：匹配点之前若有一个**未闭合的标签开头**
  （`<` 紧跟字母或 `/`，且其后**没有** `>`），则这次匹配在标签内部、**不是**标签，跳过。
  ⚠ **为什么必须要求"紧跟字母/`/`"**：正文里的裸 `<`（`3 < 5`）后面是空格，
  那不是标签开头；若判据放宽成"有 `<` 就算在标签里"，真 `<script>` 会被当文本
  ⇒ **JS 漏进正文**（本函数要防的方向）。修后实测 `'前 可见甲后'`（与浏览器一致）。
- **非空转（成对的两个变异体）**：E（整条守卫拿掉）⇒ `test_literal_script_in_an_UNQUOTED_attribute…`
  **RED**；F（守卫放宽成"出现过 `<` 就算在标签里"，即上面那个风险方向）⇒ **4 条 RED**
  （含既有的 `test_script_and_style_do_not_become_content`）。跑完 `text_utils.py`
  sha256 **逐字节一致**。E/F 是**故意成对**的：只测 E 会鼓励把守卫放宽，只测 F 会鼓励撤掉它。

**② 两条测试缺口（⇒ 已补）**
- `law_name_key` **保留修正年份**此前**没有任何直接断言**（复核 M11 变红是**别的**用例撞上
  `doc_meta.standard_no` 的 UNIQUE 约束**连带**抓到）。补 `TestLawNameKey` **6 条**：年份进身份、
  同一部的不同写法共享键、空值、以及**行为级**一条——库里只有 `（2014年修正）` 时
  `find_existing_law("…（2021年修正）")` 必须**是 None**（判成"已有"就只会 `link`，
  新版正文永远进不了库、引用指向旧版；与 §10.37 那条"脏数据拦住真数据"同型）。
- "标准赢过法规形态"的断言**加严**：从"`doc_kind == standard`"到"法规字段
  （`law_name`/`clause_count`）**一个都不许漏出来**" + `tier_reason` 里只许出现"标准"那套说法。

**③ 两条登记不改（不丢字，要精确得写分词器）**
- 引号属性值里的字面 `<script>`：`<p title='<script>'>可见</p>` → `前'> 可见后`
  （多出 `'>` 两个字符；缺的是通用剥标签那步的 DOM 感知）；
- `foo<!--x-->bar` → `foo bar`（浏览器渲染成 `foobar`，多一个空格）。
两条都**不丢内容**、**不造内容**，且都在"整体近似解析"的定位内 ⇒ 只登记。
**方案 §12 未决第 9 条**（此前只写在 docstring 里 —— 复核说"待办只写在 docstring"，
这条正是那个抱怨的落点）。

**④ `application/xhtml+xml`：登记，并明确选择"保留接收"（方案 §12 未决第 10 条）
白名单收它、却按 HTML5 解析 ⇒ XHTML 的 `<script src=x/>`（真自闭合）会被当"未闭合"
**吞掉后文**（实测 `<p>前</p><script src="a.js"/><p>后</p>` → `前`）。
选**保留接收**的理由：政府站点的 XHTML/XML 公告真实存在，拒收会**丢资料**；
而这条偏差的方向是**丢内容、不是造内容**（P1 上危险的那一侧没被打开）。
要按 Content-Type 分流得把它传进 `html_to_text`（跨层签名改动）⇒ **未立项**。

**⑤ query 未知键静默忽略：有意不改（并写清为什么）**
复核探到 `?source_tier=T0` → 200（**无状态影响**）。**不改**的理由：
1. 这是 **FastAPI 全引擎 113 个端点**的统一行为，不是材料端点独有的洞；
2. 只在这里加白名单会造出**第二条判据**（"请求校验"这件事会有两个所有者），
   而"一个判据只有一个所有者"是本项目比这更硬的纪律（本战役已因"第二份实现"栽过多次）；
3. 真发生影响的路径（我们的主机层）本来就按白名单**构造** query（`mapProbe`），
   不存在"以为设上了"的调用方。
⇒ 记录为**已知且有意**的行为，而不是把这条 LOW 悄悄丢掉。

**⑥ 一条复核判定被更正：M13 是等价变异体（不是测试缺口）**
复核原文把 M13（`if std…: / elif law…:` 的 `elif` 改 `if`，测试全绿）记成
"优先级契约在**真冲突**下无覆盖"。**证据不支持这个结论**：
`collect_text` 里 `law = {"is_law": False} if std.get("is_standard") else looks_like_law(…)`
这行**守卫**保证"认成标准时 `law` 恒为假" ⇒ 那个 `elif` 在 `std` 为真时**不可达** ⇒
M13 是**等价变异体**（equivalent mutant），本来就不该指望它变红。
**真正承重的是那行守卫**——复核的 M12（删掉守卫）**是 RED**，且
`test_standard_number_wins_over_law_shape` 正是覆盖"标准号 + 法规形态"真冲突的用例。
⇒ 已把这条更正写进本节与方案 §12；
> 教训（与 §10.39 的"假绿"是同一枚硬币的两面）：变异体**绿**可能意味着
> ①修复空转、②变异体没打在路径上、③**变异体与原文语义等价**。
> 三种要分别查清；把③误记成①会凭空长出一条"待办"，把①误记成③则会把漏洞洗白。

**诚实边界**：
- ①修的是**一个具体形态**；`_strip_script_style` 仍是**近似解析**（不是分词器），
  ③那两处偏差**仍然在**，且"引号内 `>` 让标签边界偏差"这类也无法穷举。
- ⑤**是有意不改**，不是"已解决"：将来若全引擎统一加请求校验，材料端点应跟着走，
  而不是各自为政。
- 本轮**没有**跑真机 GUI、**没有**重启活引擎（新路由/新工具仍未上线，两道门见 §10.35 末）。
- 采集预算（§11.4 `MAX_COLLECT_PER_SESSION = 20`）仍是**暂定值**。

**门禁（本步）**：`pytest` **1618 passed / 3 skipped / 0 failed**（+8：`TestLawNameKey` 6 +
`test_material_harvest` 2）；`mypy src` **133 files / 0 errors**；`smoke` **16 段全过**；
`verify:commands` 22/22；`tsc --noEmit` 0。变异实验 E/F 全 RED 且逐字节还原；
复核探针 `probeD.py`（21 组）复跑 **20 OK / 1 OVERKILL**（剩的那组见 §10.35 的更正）。

### 10.41 Phase D-3（上半）：**自采入口进界面**——"自己搜集材料"终于有用户可达的入口

**为什么是这一步**：业主的原始要求里有一条是"**自己搜集材料**"。C-4 写了采集器、
C-5 开了同源路由、C-6 给了模型工具 `ks_collect`——**但面板上没有任何入口**
（D-3 自己记的"未做"）。于是这条能力到今天为止只对**模型**可达：
用户想说"去把这个网址收进来"得靠模型自己决定调工具。**用户手动采一条**没有路。

**做了什么**（4 文件）
1. `plugin/client/api.ts`：新增 `collectMaterialUrl()` + `KsCollectOutcome`。
   **不提供** `source_tier` 入参（连试都不试），body 只构造主机白名单里的四个键的**子集**。
2. `plugin/client/KsMaterialsPanel.tsx`：在"参考资料文件夹"那块下面加**自采一条**
   （网址 + 可选备注 + 按钮），并加了**第三条反馈通道 `warn`**（琥珀色）。
3. `plugin/scripts/smoke-collect-ui.mjs`（**新**，14 条）：**替身 fetch** 抓请求、四种响应形状逐一喂回。
4. `plugin/scripts/smoke-client-entry.mjs`：+6 条产物标记（50 → **56**）；
   `package.json` 的 `smoke` 链 16 → **17 段**。

**三个刻意设计（都不是随手写的）**
- **不给"可信度"输入框**：轴 A 是**系统判据**（采集默认 T3=仅线索），用户要改只能
  采完之后在材料行上改（`onTier`）。给个下拉框 = 让"自采"变成自评，
  与 `ks_collect` 里那条"采集者不得 self-claim 可信度"的纪律直接冲突。
- **"没采到"走琥珀色 `warn`，不是红字**：引擎**刻意**用 `HTTP 200 + collected:false + reason`
  表达它（原因要给人看）。塞进 `error` 会把"网址抓不到"与"引擎/网络挂了"混成同一种红；
  塞进 `notice`（灰）又太弱。于是面板多一条通道——**这是引擎三态语义的必然结果**，
  不是"颜色好看"。
- **一次一条、只收网页正文**：没有批量（方案 §11.4 预算未定），文案里写明
  "PDF / 图片 / 压缩包请下载后放进文件夹"（不然用户会以为按钮失败）。

**为什么要写一条新的冒烟（而不是只加字符串断言）**
`smoke-client-entry` 只能证明"产物里有某句文案"——它**抓不到请求契约漂移**：
`project_id` 挪进 body（主机读 query ⇒ 400）、多发 `source_tier`（主机**响亮拒绝**）、
把 `collected:false` 当异常抛、坏信封不抛。这几个正是本战役栽过的坑
（`sanitizeParams` 吞字段 ⇒ 功能全死无人报错），所以用**替身 fetch 把真实请求截下来验**：
路径/方法/头/body 键、URL 原样透传、成功形状、`collected:false` **正常返回**且原因与
HTTP 状态都在、缺 `collected` **抛**、`data` 缺失 **抛**、HTTP 502 **抛并带出引擎 message**。

**测试非空转（3 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step40.py`
- G：body 里多发 `source_tier` ⇒ **3 条红**（含"绝不发 source_tier"那条）；
- H：去掉"缺 `collected` 就抛"的守卫 ⇒ **1 条红**；
- I：把 `collected:false` 当异常抛 ⇒ **2 条红**。
三个跑完 `api.ts` **逐字节一致**。

**诚实边界**：
- **真机点击未验证**（本轮没有在浏览器里点过）。而且**今天点下去很可能 404**：
  活的引擎实例（pid 32564，起于 09-17 19:14）**早于**材料路由那次提交
  （复核实测 `/openapi.json` 113 条路径里**0 条** materials）⇒ 要真机可用需
  **两道门**：**引擎重启**（加载材料路由）+ **宿主插件重挂载**（`ks_collect` 才会进工具表）。
  **本步没有重启引擎**（业主的实例，不擅自动）。
- 界面**不能代批**（没有"批准"快捷键接在自采上）：采完必须走下方逐份评审。
- 采集预算 `MAX_COLLECT_PER_SESSION = 20` 仍是**暂定值**（方案 §11.4）；
  界面上的自采**不受**该会话上限约束（那条刹车在模型工具侧）——**如实记下这个不对称**，
  它是"预算未定案"的直接后果。
- **下半（研究报告 / PPT 的界面入口）仍未做**：路由同源可达，面板上还没有按钮。

**门禁（本步）**：`pytest` **1618 passed / 3 skipped / 0 failed**（Python 侧**一字未改**，
与 §10.39 同值）；`mypy src` **133 files / 0 errors**；`smoke` **17 段全过**
（`client-entry` 50 → **56**、`collect-ui` 14/14 新增）；`verify:commands` 22/22；
`tsc --noEmit` 0。变异实验 G/H/I 全 RED 且逐字节还原。

### 10.42 Phase D-3b：**研究报告 / PPT 进界面**——"经用户评审后产出"那句话的最后一米

**为什么是这一步**：业主的原始要求是"经**用户评审**确认参考资料可用后再做分析/产出
（**报告、PPT**）"。§10.36/§10.38 把两条产出路由做通了，但它们到今天只有
**脚本/模型**可达——D-3 记的"面板上没有按钮"。这一步补上按钮与**如实显示**。

**做了什么**（4 文件）
1. `plugin/client/api.ts`：`exportResearchReport()` / `exportResearchSlides()` +
   `KsResearchReport` / `KsSlideDeck` / `KsReportCounts`，共用一个
   `reportBody()`（把界面入参翻成主机白名单认识的那几个键）。
2. `plugin/client/KsMaterialsPanel.tsx`：底部加**产出**一块——研究问题（可选）、
   结论（可选，可用 `[[m:i]]`）、两个按钮、以及生成后的
   **计数 / 引用核验数 / 落盘路径 / 引用警告 / 可展开的 Markdown**。
3. `plugin/scripts/smoke-report-ui.mjs`（**新**，15 条）：替身 fetch 验请求与四种响应。
4. `smoke-client-entry.mjs`：+7 条（56 → **63**，含"两个按钮**接了 handler**"的源码断言）；
   `package.json` 的 `smoke` 链 17 → **18 段**。

**⚠ 这条接线上最容易"错得很安静"的一点，值得单独记**：产出路由与材料路由的
**参数位置不同**——材料路由 `project_id` 在 **query**（`pickQuery`），产出路由在 **body**
（`plugin/src/report.js` 从 body 取，缺了就 400）。**两条路由是不同时间写的**，
照抄前一条就必然 400。冒烟因此把"路径里**不许**出现 `project_id`"钉成断言
（变异体 J：挪到 query ⇒ 3 条红）。同款还有两条：
`dry_run` 写成字符串会让主机 `=== true` **永远判假**（界面以为在预览、其实落了盘，变异体 L）；
空串照发会把"我没写结论"与"我要一份空结论"混起来（变异体 K）。

**为什么界面上必须显示那四样**
- **计数**（已批准/待评审/已拒绝）：报告把"尚未批准的材料（**不会进入任何结论**）"
  单列一节——界面不显示计数，用户就看不见"硬门真的生效了"。
- **引用核验数 + 警告**：`[[m:i]]` 对不上、或落在仅线索/不可用上，引擎**列出来而
  不改掉**（这是 §10.36 定的纪律）。界面不显示等于用户以为引用都成立。
- **落盘路径**：产物在**本机**、不外发；用户得知道文件在哪。
- **"报告与 PPT 是同一份内容"**这句话：两条路由共用 `build_report_blocks`，
  但用户看不出来——不写就会有"是不是两套东西"的疑虑（而那正是这套设计要避免的）。

**测试非空转（3 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step41.py`
- J：`project_id` 挪进 query ⇒ **3 条红**；
- K：去掉"空串不发"的守卫 ⇒ **1 条红**；
- L：`dry_run` 发成字符串 ⇒ **2 条红**。
三条跑完 `api.ts` **逐字节一致**。

**诚实边界**：
- **真机点击未验证**（与 §10.41 同）：产品里点下去要**两道门**——**引擎重启**
  （加载 `/api/v1/report/research[/slides]`）+ **宿主插件重挂载**。本步没有重启引擎。
- **结论正文仍要人（或模型）写**：这一步只把"已有的结论 + 已批准的参考材料"落成文件，
  **不做**"自动得出结论"。自动成文触及答案链（P1），**未立项**。
- 报告里的 `[[c:i]]`（法规引用）**本次无法逐条核验**——引擎如实计数（`unchecked_law_refs`），
  界面也照实显示"本次无法核验"，**不假装核过**。
- PPT 仍是默认版式 + 纯文本要点；300 字/要点与 30 页是硬上限（超限**写明**在末页）。
- `.docx` 侧仍未扩到材料平面（三条导出用途不同，没有顺手合并）。

**门禁（本步）**：`pytest` **1618 passed / 3 skipped / 0 failed**（Python 侧**一字未改**）；
`mypy src` **133 files / 0 errors**；`smoke` **18 段全过**（`client-entry` 56 → **63**、
`report-ui` **15/15** 新增）；`verify:commands` 22/22；`tsc --noEmit` 0。
变异实验 J/K/L 全 RED 且逐字节还原。

### 10.43 冷启动缺陷：**全新库上 `/api/v1/report/effect` 直接 500**（`no such column: catalog_hidden`）

**怎么发现的（值得记）**：修完 D-3b 之后我没有停在"单测全绿"，而是**起了一个一次性引擎
做真机端到端**（独立 `KS_DATA_DIR` + 随机端口，**只碰那个临时实例**；活引擎 pid 32564
只读探测、session 文件哈希前后一致、探完即杀）。那条端到端把业主的主环走通了：

    建项目 ✓ → 空项目报告如实说"没有已批准的材料" ✓ → **真网络自采** example.com ✓
    （T3/pending/1 切片）→ **未批准检索不到（命中 0）** ✓ → 批准 ✓（track_l=skip，对）
    → **批准后检索到（命中 1）** ✓ → 报告落盘 ✓（counts approved=1，warnings=1）
    → **PPT 8 页** ✓ → 最后一步 `/api/v1/report/effect` → **500**

**缺陷本身**：`schema.sql` 是 `CREATE TABLE IF NOT EXISTS`，而 **`catalog_hidden` 这一列
不在 `schema.sql` 里**——只由 `storage/clause_repo` 的迁移函数添加。而那条迁移此前
**只挂在写路径**（`insert_clauses_in_txn` → `_ensure_content_hash_once`）⇒
**一个还没入库过任何条款的新库，这一列根本不存在**，读者照用：
`exports/effect_report.py:137` 的 `WHERE catalog_hidden = 0` 直接
`sqlite3.OperationalError: no such column`（`api/server.py` 的两个目录端点同理）。
⇒ 新装的库，"效力报告"第一眼就是服务器错误。**独立复核（b7）也复现了同一缺陷**
（它的 INFO ①，探针 `probeG2_latent_500.py`）。
⚠ **本段在 §10.50 被更正**（复核 b8 的 LOW-2 / LOW-6）：原文写的是"三列"，
而 `page_breaks` / `figure_html` **从基线起就在 `schema.sql` 里**（:60 / :87）——
真实缺口**只有 `catalog_hidden` 一列**；写路径迁移的真触发点也是 `insert_clauses_in_txn`
（**不是** `insert_document`）。原文保留在下面这段的措辞里只作对照，**以本更正为准**。

**修法（判据只有一个所有者）**：`clause_repo.ensure_additive_columns()` 作为**追加列
迁移的唯一入口**（纯 ALTER、**不回填**——回填是写路径的事，见该函数 docstring），
在 `create_app()` 里紧跟 `init_schema()` 调一次：与 schema 初始化同一时间点，
**任何请求都晚于它**。没有把三个列抄进 `schema.sql`（那会造出第二份列定义）。

**⚠ 顺带修掉一条**顺序依赖的假绿**（同一缺陷的另一面）**：
`tests/test_effect_report.py::test_eff_09_export_empty_db` **单跑是红的**，
放在文件里跑是绿的——因为它靠**同文件前一条用例**触发了写路径迁移。
`world` 夹具里那句 `ensure_catalog_hidden_column()` （注释写着"与真实运行时一致先迁移"）
正是这种补丁。现在：
- 迁移统一在 `db` 夹具（与 `create_app()` **同一个入口**）；
- `world` 不再自己迁移；
- 新增 `tests/test_api_cold_start.py`（**4 条**，用**自己的一次性数据目录**，
  只走 HTTP）。⚠ 第一版我用会话共享的 `client` 夹具，**全量跑时红**——
  因为 `_isolate_data_dir` 是 **session 级**的，先跑过的入库用例会把列补上，
  于是"未迁移的空库"这个前提不成立（而且 `test_effect_report.py` 的 autouse 夹具
  会拉起 `db`，把要验的启动路径整个遮住 ⇒ 变异体 M 假 GREEN）。
  改成"本用例自己的目录 + 丢掉线程局部连接"之后，**顺序无关**。

**测试非空转（2 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step42.py`
- M：`create_app()` 里去掉 `ensure_additive_columns()` ⇒ `test_api_cold_start` **3 条红**
  （`no such column: catalog_hidden`）；
- N：`db` 夹具里去掉 ⇒ `test_eff_09_export_empty_db` **红**。
  ⚠ 变异体 M 的**第一版锚点带 `\n`**，而 `server.py` 是 **CRLF** 文件 ⇒ 锚点不匹配、
  变异根本没打上，脚本却报"GREEN"（我按 exit code 判读时才发现）。**锚点必须与文件行尾一致**
  ——这条与 §10.39 的"变异体没打在路径上"是同一类坑，再记一次。

**诚实边界**：
- 修的是**启动引导**；`create_app()` 之外如果还有别的入口直接建库（脚本/批处理），
  它们仍走写路径迁移——本步**没有**逐个排查那些入口（写路径本身会迁移，风险低但未穷举）。
- 活引擎（pid 32564）**没有重启**，所以**它上面这个 500 仍然存在**
  （它的作用是"重启后才生效"）；真机验证仍未做。
- 本步只动 schema 引导与测试夹具，**没有**碰答案链。

**门禁（本步）**：`pytest` **1622 passed / 3 skipped / 0 failed**（+4：冷启动 3 + 引导契约 1）；
`mypy src` **133 files / 0 errors**；`smoke` 18 段（本步未改 `plugin/`，与 §10.42 同值）；
`tsc --noEmit` 0。变异实验 M/N 全 RED 且逐字节还原。

**⚠ 下一步的输入（b7 独立复核已回，按严重度排队）**：复核报了 1 个 **HIGH** + 4 个 MEDIUM，
其中 **[HIGH] 采集件在答案链上仍被当"现行有效"**（`clause_repo.py:617` 的
`row["legal_status"] or "effective"` 把 NULL 洗白，`ClauseRevisionModel.legal_status`
是非可选 `str`）——**这条直接证伪了 §10.39 的一句自述**（我那时只钉到 `doc_meta` 那一列，
没有跑到底）。另两条同批：`_inside_unclosed_tag` 在**被上游改写过的字符串**上求值，
新开若干"JS 进正文"的路径；PPT 的"30 页上限"对交付物不成立（实际 31 页）
且尾页"已知限制"是**手写的第二份内容**。**这些都留到下一步逐条处置**（不在本步夹带）。

### 10.44 复核 b7 的 **HIGH**：采集件在**答案链**上仍被当"现行有效"（§10.39 的自述被证伪）

**复核怎么打中的（它的原话值得抄下来）**：§10.39 我写了"这三条（`legal_status=None` /
`quality_grade='C'` / `standard_type=None`）**决定**'未核验的网页文本会不会被当成现行有效'"，
测试 docstring 也这么写。复核没有停在读代码，它**跑了端到端**（真 `ks_answer.answer()`
+ 打桩 LLM）：`D2 fetch_full_clause(...).legal_status='effective'`、
`D3 本采集件入证=True / 提示词效力=effective`，`resolve_clause(...)` 同样。
⇒ **我那句自述是过度声称**：那三处只决定 `doc_meta` 那一列（与效力报告的 ⚪），
**答案链上的洗白发生在另一处**，而那条路径**零测试覆盖**（复核用它自己的变异体 X1
证明了：删掉洗白那一行**没有任何测试变红**）。

**洗白点（一行）**：`storage/clause_repo.fetch_full_clause` 里
`legal_status=row["legal_status"] or "effective"`。
`doc_meta.legal_status` 允许 NULL（Track L 入库的采集件**写的就是** NULL），
而 `ClauseRevisionModel.legal_status` 当时是**非可选 `str`**——于是读取时把 NULL
变回"现行有效"，它随即通过 `ks_answer._is_effective`（`legal_status == "effective"`）
进证据集、进提示词。**效力报告显示 ⚪（未核验），而同一个库里的答案链把它当现行法条**：
两份输出对同一行的判断相反，这是最坏的一种不一致。

**修法（契约级，一次收口）**
1. `domain/models.py`：`ClauseRevisionModel.legal_status: Optional[str] = "effective"`。
   **默认值保持不变**——写入方（`docx_ingest` / `pipeline` / `ingest_law_text` 里构造
   `ClauseRevisionModel(...)` 的三处）都不传该字段，所以**既有入库行为一字未变**；
   变的只是**读取**能如实带回 NULL。
2. `clause_repo.fetch_full_clause`：`row["legal_status"]`（去掉 `or "effective"`）。
3. **读者审计**（`Optional` 之后逐个看，而不是只看 mypy 绿）：
   - `resolve_status(clause.legal_status, …)` —— 三处（`ks_answer._clause_to_evidence`、
     `server.py:1673`、`server.py:2975`）：签名本来就是 `str | None`，None 原样返回；
   - `hybrid_engine` 的时效过滤：`in ("superseded", "withdrawn")`，None **不在**其中
     ⇒ **不会被误删**（未核验 ≠ 已废止，这条边界要保住）；
   - `user_data` / `effect_report` 读的是 `doc_meta`（SQL 层，不受本改动影响）；
   - `understanding` 的排序项与 `standard_type` 无关（那条是另一个 MEDIUM，见下）。
   `mypy`（`Optional` 已生效）**133 files / 0 errors**：没有读者把该字段当字符串拼接。

**后果（这正是我们要的）**：采集件入库后，它的条款**进不了 `ks_answer` 的证据集**
（`_filter_effective` 会剔除并打 warning），效力报告显示 ⚪，两条链的口径**一致**。

**测试（跑到底，三级断言）**：`tests/test_material_track_l.py` 那条
`test_imported_collected_doc_is_marked_unknown_not_effective` 从"只钉 `doc_meta` 一列"
扩成三级——① `doc_meta.legal_status is None`；② `fetch_full_clause(...).legal_status is None`；
③ **行为级**：`_clause_to_evidence(...)["legal_status"] is None`、
`_is_effective(...) is False`、`_filter_effective([ev]) == []`。
docstring 里**写明了它曾被判过度声称**（不删旧话，改掉并说明为什么）。

**测试非空转（2 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step43.py`
- O：把洗白写回去 ⇒ **红**，且失败点正是新断言
  `assert clause.legal_status is None` → `AssertionError: effective`（复核的 X1 从此有主）；
- P：模型退回非可选 `str` ⇒ **红**（pydantic 对 None 报校验错）
  ——证明"契约允许 NULL"本身也是承重的，不只是注释。

**不需要数据迁移（值得说明）**：洗白发生在**读取**，库里存的一直是 NULL ⇒
**既有库不需要修正任何行**，重启即生效。这也是"当初写 `None` 而不是写个哨兵字符串"
的一个回报（复核建议的方案 3 要改数据契约，影响面反而更大）。

**诚实边界**：
- 修完的语义是**"未核验 ⇒ 不得进证据集"**（保守）；**没有**做"进证据集但显式标注未核验"
  ——那要让 `_filter_effective` 从"二值门"变成"带标注的通道"，属于另一个决定，**未立项**。
- 本步**没有**改 `DocumentMetaModel.legal_status: str`（它在 `src/` 里**没有任何构造点**，
  是死模型）——登记而不是顺手改。
- 活引擎仍未重启 ⇒ **它上面两份输出不一致的现状会持续到重启为止**。
- 本步**没有**碰 b7 的其余 MEDIUM（`_inside_unclosed_tag` 的新泄漏路径、PPT 页数/尾页、
  `standard_type` 死项）——它们排在下一步，**不在本步夹带**。

**门禁（本步）**：`pytest` **1622 passed / 3 skipped / 0 failed**（`test_material_track_l`
49 → **55**）；`mypy src` **133 files / 0 errors**；`smoke` 18 段（未改 `plugin/`）；
`verify:commands` 22/22；`tsc --noEmit` 0。变异实验 O/P 全 RED 且逐字节还原。

### 10.45 复核 b7 的 **MEDIUM-1**：`_inside_unclosed_tag` 曾对**被上游改写过的字符串**求值

**复核怎么打中的**：它给 `_inside_unclosed_tag`（§10.40 新加的守卫）做了**归因实验**——
把守卫关掉（v2）与留着（v3）各跑一遍，并用 lxml / `html.parser` 两个独立参照对表。
结论：守卫在**生产路径**上**新开 7 条"JS 进正文"**，而方向**正是它要防的那个**。
其中 4 条的根因是**顺序**：`html_to_text` 里 `clean_eq_tags` / `</td>`→` | ` / `</tr>`→`\n`
这三个替换**跑在 `_strip_script_style` 之前**，而它们**会删掉 `>`** ⇒
原串里**已经闭合**的 `<b` / `<div` 在守卫眼里变成"未闭合的标签开头" ⇒ 误判 ⇒ JS 漏进正文。
例：`<td>a<b</td><script>JS</script>` → 修前 `'aJS'`（浏览器 `'a'`）。

**修法（一行顺序）**：`html_to_text` 里把 `_strip_script_style(html)` 提到**最前**，
之后再做那三个替换。守卫看到的就是**原始**字符串。**没有**去写分词器
（复核的另一个建议是"按 HTML5 的 tag/comment/attribute 三态判定"——那是**新写一个解析器**，
与本项目"要更准得引 HTML 解析器（未立项）"的既有裁决冲突，登记而不做）。

**实测（`var/tmp/probe-step44-order.py`，10 组）**：复核实测的 4 组（31/32/34/35）
全部由"JS 进正文"变成**不含 JS**；反向的 3 组（正常 script、正文裸 `<` 后跟真 script、
表格正常闭合）**仍然把 JS 剥干净**（修顺序不许换来"漏 JS"，所以正反都要跑）。
**仍有 3 组**（36 未闭合注释 / 37 RCDATA `<title>` / 38 未收尾引号属性）需要建模
HTML5 的**词法状态**，属"分词器"范畴 ⇒ 已连同**实测值**登记进方案 §12 未决第 9 条
（方向是"我们多出浏览器不显示的内容"，触发需畸形 HTML）。

**测试非空转（1 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step44.py`
- Q：把顺序换回复核之前那样 ⇒ **红**，失败点正是新增的顺序回归用例
  （`AssertionError: ('<b</td>x<script>var SECRET_JS=3;</script>', 'var SECRET_JS=3;')`）。

**另外补上复核的 LOW-2（守卫要求①零覆盖）**：复核指出我 §10.40 的"反例1"
（`<p>前 3 < 5</p><script>…`）被 `</p>` 收尾 ⇒ **没真正测到**要求①"`<` 后紧跟字母/`/`"。
`test_a_bare_less_than_in_the_text_does_not_disable_the_sweep` 里那条注释现在**说清了盲区**，
并新增的表格形态用例让"删掉要求①"这条变异**有主**（复核的 F1 从 GREEN 变可抓）。

**诚实边界**：
- 修的是**顺序**；`html_to_text` 仍是**近似解析**，§12 未决第 9 条列的三态**仍在**
  （未闭合注释 / RCDATA / 未收尾引号属性）——本条**没有**把它们变好。
- 本步**没有**动 `clause_health_html_to_text`（那一份**不剥 script/style**，
  是既有裁决：它做的是"条款健康度"、不是采集正文），所以两边的**有意差异**仍是两处。
- b7 的其余 MEDIUM（PPT 页数/尾页、`standard_type` 死项）与若干 LOW **不在本步**。

**门禁（本步）**：`pytest` **1623 passed / 3 skipped / 0 failed**（`test_material_harvest`
63 → **64**）；`mypy src` **133 files / 0 errors**；`smoke` 18 段（未改 `plugin/`）；
`verify:commands` 22/22；`tsc --noEmit` 0。变异实验 Q RED 且逐字节还原。

### 10.46 复核 b7 的 MEDIUM-2/3/4：PPT 页数与末页内容、`standard_type` 死项

**MEDIUM-2「30 页硬上限」对交付物不成立**：`build_slides` 给到 30 张**内容页**，
`write_slide_deck` 再加 1 张末页 ⇒ 落盘 **31** 页（`slide_count` 也报 31），
而常量与文档都写 30 —— **过度声称**。而且真报告的 `h2` 数 ≤7 ⇒ 页数上限**生产不可达**，
真正会崩的形态是**每页要点数**（复核实测：60 份已批准材料 ⇒ 单页 **120** 条，
PPT 里必然溢出文本框）。
**修法**：`build_slides` 的内容页上限改成 `MAX_SLIDES - 1`（交付物总页数因此 ≤ `MAX_SLIDES`）；
新增 `MAX_BULLETS_PER_SLIDE = 12` 与 `_paginate()`——超了就**续页**（标题加"（续 N）"），
并且**条数守恒**（续页不丢内容）。为什么放在**模型层**：页数是**可断言的交付物属性**，
测试要能在不装 python-pptx 的路径上验它。

**MEDIUM-3 末页是手写的第二份内容**：那 4 句与报告 §六 分叉（PPT 多 3 句、报告多 2 句）
——与 §10.38 立下的"内容只从 `build_report_blocks` 来"直接冲突。
**修法**：新增 `limits_from_blocks(blocks)`（从报告块里取 `## 六、已知限制` 之后的第一个 `ul`），
末页 = 生成时间 + **报告里的限制** + "与 Markdown 报告同一份内容"。
另外把 PPT 独有的那句"**待评审**材料不会进入任何结论"**搬进报告**的 `limits`
（内容只有一个所有者：要加就加在报告里，PTT 自动跟上）。
取不到那一节时**不编造**，返回一条"报告里没有『已知限制』一节（异常，请核对）"。

**MEDIUM-4 `standard_type` 是死项**：`rank_with_hierarchy` 写
`getattr(c, 'standard_type', 'mandatory') == 'mandatory'`，而 `ClauseRevisionModel`
**根本没有该字段** ⇒ 恒取默认 `'mandatory'` ⇒ 该项对**所有**条款都是 0
——"按强制性排前"**从来没生效过**（复核实测 `std_term=0`）。
**修法**：模型补 `standard_type: Optional[str] = None`，`fetch_full_clause` 从
`doc_meta.standard_type` 填，排序项改成 `getattr(c, 'standard_type', None) == 'mandatory'`
（**未登记 ⇒ 不优先**）。⚠ **这是一处排序行为变化**（以前恒等、现在真的区分）——
如实记下：它恢复的是**本来就这么写**的意图，不是新引入的偏好。

**测试非空转（4 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step45.py`
- R：内容页上限退回 `MAX_SLIDES` ⇒ `test_too_many_slides_is_declared_inside_the_deck` 红；
- S：拿掉 `_paginate` ⇒ 续页用例红；
- T：末页退回手写那 4 句 ⇒ "报告→PPT 逐条包含"红；
- V：`fetch_full_clause` 不填 `standard_type` ⇒ `test_fetch_full_clause_fills_standard_type` 红。
⚠ **另有 U 是等价变异体**（把排序项写回 `getattr(..., 'mandatory')`）⇒ **GREEN，而且应该 GREEN**：
字段存在之后 `getattr` 的默认值**再也没有机会生效**（属性在、值是 `None`）。
这条顺带**证明**了原来的缺陷是"**字段缺失**"而不是"getattr 默认值写错"——
即"绿"的第三种原因（等价变异体）在这里又一次出现，按 §10.40 的三种原因逐条判清。

**诚实边界**：
- 页数/续页解决的是"**一页塞太多**"；PPT 仍用**默认版式**，`MAX_BULLETS_PER_SLIDE = 12`
  是**估计值**（按默认版式文本框高度估的），**没有**做真实的溢出测量（要测量得渲染）。
- 末页"已知限制"现在与报告**逐条一致**，但**顺序/措辞**取决于报告（这是我们要的）。
- `standard_type` 排序**生效后**的真实效果**没有做 A/B 评测**（本步只钉"它在起作用"）。
- `.docx` 侧仍未扩到材料平面（既有边界，未变）。

**门禁（本步）**：`pytest` **1628 passed / 3 skipped / 0 failed**
（`test_slide_export` 11 → **15**、`test_understanding` 13 → **16**、`test_research_report` +0）；
`mypy src` **133 files / 0 errors**；`smoke` 18 段（未改 `plugin/`）；`verify:commands` 22/22；
`tsc --noEmit` 0。变异实验 R/S/T/V 全 RED、U 为等价变异体（并说明为什么），
5 个源文件逐字节还原。

### 10.47 复核 b7 的**其余 LOW**：判据回退、结构化字段与文案不一致、共享映射器的影响面

四条 LOW 逐条处置（都不夹带新功能）：

**① 光杆 `GB` 从标准树回退到法规树**（复核实测）。§10.39 把边界从 `\b` 改成
`(?=[\s/]|\d)` 时漏了一种退化输入：`standard_no` 恰好就是 `GB`（光杆前缀）——
`\b` 在字符串末尾**成立**，所以旧写法当它是标准，新写法不成立 ⇒ 掉进法规树。
**修法**：边界补上 `$` 分支（`(?=[\s/]|\d|$)`），恢复原行为；并把它加进
`TestTreeClassificationOfStandardNumbers` 的参数表（**它有主了**——变异体 W 证明）。

**② 同一段注释里两句话自相矛盾**（`doc_catalog.py`）：那段注释写"保留原有的
'GBX 开头的法规名不该误判'（`GB` 后面跟字母时仍不匹配）"——而**同一版**白名单里
加了 `GBZ`（职业卫生标准），它恰恰是"GB 后面跟字母"。**修法**：措辞改准
（"名单里的前缀后面必须是空白/斜杠/数字或字符串结束"），并写明 `GBZ` 为什么要匹配。

**③ 无 `query` 分支：文案说有引用、结构化字段说是空**（复核实测）。
`citations["material_refs"]` 在"没给 query"那条路上**没被填**，
而 warning 文案里写着"有 N 个 `[[m:i]]` 无法校验" ⇒ **读结构化字段的消费者会得出
相反的结论**（"结论里没有材料引用"）。**修法**：`citations["material_refs"] = still`，
并让测试**同时**断言文案与字段（变异体 X 证明）。

**④ `mapProbe` 的 404 改动是全局的**（复核指出"影响面未披露"）。
那条改动（引擎 404 → 主机 404，原先翻成 502）写在**共享**映射器里，
所以 `materials_routes.js` / `report.js` / `settings.js` 一起变了，而当时的记录只说材料路由。
**修法**：在 `route_util.js` 的 `mapProbe` 头上**写明影响面**（这是有意的全局口径，
"目标不存在"不是"引擎坏了"；若要回到旧行为只能在调用点决定）。**代码未改，只补披露。**

**另外两条 LOW 在 §10.44/§10.45 已经收掉**：`ingest_law_text` docstring 的受益者写错
（docx/官方法规源**不调用**该函数——现在写的是"哨兵护住的是仓外/未来调用方"，
本步一并改）；守卫要求①零覆盖（§10.45）。

**测试非空转（2 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step46.py`
- W：去掉 `$` 那一支 ⇒ 参数化里的 `GB` 那条红（`assert 'law' == 'std'`）；
- X：结构化字段不填 ⇒ LOW-3 的新断言红（`assert [] == [3]`）。

**诚实边界**：
- ①修的是**退化输入**（`standard_no` 只有前缀），真实库里有没有这种行**没有查**
  （本步不去动生产库；判据恢复原行为，属"少改"方向）。
- ④是**披露**而不是行为改动：全局 404 口径**仍然**是全局的。
- b7 报告的其余条目（`_inside_unclosed_tag` 的另三态、`xhtml` 分流、httpx/NO_PROXY 的
  策略决定）状态不变：**三态已登记进方案 §12 未决第 9 条**，后两条仍是**待业主拍板**。

**门禁（本步）**：`pytest` **1629 passed / 3 skipped / 0 failed**
（`test_research_report` +1 断言、`test_material_track_l` 参数表 +1）；
`mypy src` **133 files / 0 errors**；`smoke` **18 段全过**（本步改了 `plugin/src/route_util.js`
的注释 ⇒ 重跑确认）；`verify:commands` 22/22；`tsc --noEmit` 0。
变异实验 W/X 全 RED 且逐字节还原。

### 10.48 Phase B 必解：**材料引用的"锚点稳定性"**（方案 §12 未决第 5 条 —— 决策 + 判据落地）

**问题（复核 2026-09-17 提出，标 LOW-MEDIUM 但后果重）**：`material.content_hash` 是
**源文件字节**的哈希，而 `material_chunk` 的 `char_start/char_end/page` 是**解析结果**的坐标。
两者之间隔着解析器：换 PyMuPDF 版本、换 MinerU backend、开 `deep_fallback` 走云解析，
都可能让同一份 PDF 解析出**不一样的文本** ⇒ 已存区间**悄悄指向别处**，而引用、报告、界面
看起来一切正常。**"看起来很正常的错引用"比报错危险得多**，而且当时**没有任何东西能发现它**。

**决策（我拍的，记理由）**：选**增列**（`material` 增 `derived_text_hash` + `parser_fingerprint`），
**不**落派生全文——落全文要多一倍存储，而"能不能判定"并不需要全文。
⚠ 代价如实说：判据只能**发现**失效，**不能修复**；`mismatch` 之后的重建流程**仍未做**。

**做了什么**（7 文件）
1. `schema.sql`：`material` 增两列（带注释说明它们对应哪条未决）；
2. `material_repo.ensure_additive_columns()`（**老库**补列；纯 ALTER、**不回填**——
   老材料就是"未登记"，那比编一个假指纹诚实），并在 `create_app()` 里与 clause_repo 的
   同一个时间点被调（§10.43 的教训：追加列必须在任何请求之前）；
3. `material_ingest`：`extract_pages_with_provenance()` 返回 `(页文本, 指纹)`
   （`extract_pages` 变成薄包装，**解析逻辑仍只有一份**）；`text_hash()` 是派生全文哈希，
   **委托**给 `clause_repo.content_hash`（不在这里再抄一个 sha256）；
   指纹 = 解析通道 + 库版本（取不到写 `unknown`） + `deep_fallback` + 实测的
   `text_layer_state`/`is_ocr`；
4. `materials/collect.py`：网页材料记 `COLLECT_PARSER_FINGERPRINT`，派生文本哈希
   **复用已有的 `chash`**（网页材料的"派生文本"就是采到的正文）；
5. **新模块 `materials/locator.py`**：三道判据（模块 docstring 逐条写了措辞纪律）；
6. `tests/test_material_locator.py`（**14 条**）+ 引导契约里加上材料表那两列。

**措辞纪律（这一层的核心，写进 docstring 与测试）**：
- 指纹**相同** ⇒ `ok` 的措辞是"**未发现变化**"，**不是**"保证一致"（真正的保证只有重解析比对）；
- 指纹**不同** ⇒ `stale` 是"**需要复算**"，**不是**"已经坏了"；
- 网页材料（没有留存源文件）⇒ 只能 `unavailable`，**不是 ok**；
- 老材料（NULL，2026-09-17 之前）⇒ 只能 `unknown`，**不假装 ok**；
- PDF 的便宜比对**拒绝给 ok**（完整指纹含只有解析后才知道的 `text_layer`/`ocr`）——
  这可能是本步最要紧的一条：**"能便宜判的就判，判不了就说判不了"**。

**测试非空转（4 个变异体，on/off 成对，逐字节还原）**：`var/tmp/mutate-step47.py`
- Y：老材料当 `ok` ⇒ 2 条红；Z：网页材料当 `match` ⇒ 1 条红；
- AA：不比哈希就宣布 `match` ⇒ 1 条红；AB：入库不写 `derived_text_hash` ⇒ 4 条红。

**诚实边界**：
- **判据还没有接进产品**：本步只交付**模块 + 测试**；API/界面/报告里**还没有**那个标记
  （「这份材料的引用锚点未验证/已失效」），也**没有** `mismatch` 之后的重建流程。**下一步**。
- 指纹是**人工列举**的影响因子，不可能穷举（隐藏的环境变量、非确定性 OCR 都不在里面）
  ⇒ 它**只能用来提示"要复算"**，不能当保证——这句话写在 docstring 里。
- 老材料（现有库里的那些）**全是 `unknown`**：这是**故意的**（不知道就说不知道），
  但也意味着**上线后第一眼会看到一批 unknown**——不是回归，是如实。
- `reverify` 是**子进程解析**（PDF 秒级到分钟级）⇒ 它只能是**显式动作**；
  本步**没有**做批量入口（避免有人把它挂进请求路径）。

**门禁（本步）**：`pytest` **1643 passed / 3 skipped / 0 failed**（+14）；
`mypy src` **134 files / 0 errors**（新模块 +1 文件）；`smoke` 18 段（未改 `plugin/`）；
`verify:commands` 22/22；`tsc --noEmit` 0。变异实验 Y/Z/AA/AB 全 RED 且逐字节还原。

### 10.49 把锚点判据**接进产品**：引擎端点 + 主机路由 + 面板标记 + 报告里的 ⚠

**为什么必须紧接着做（§10.48 的判据当时是"死"的）**：上一节只交付了模块与测试——
按本项目自己的标准（§10.33 的 Track L 教训："有实现、没有生产调用方 = 死功能"），
判据不接进任何产品路径就等于**没做**。

**做了什么**
1. **引擎三个端点**：`GET /api/v1/materials/{mid}/locators`（单份，便宜）、
   `GET /api/v1/materials/projects/{pid}/locators`（项目级总览，**一次给全项目状态**——
   界面每行都要画标记，逐行发请求就是请求风暴）、
   `POST /api/v1/materials/{mid}/reverify`（**重解析比对**，声明成 `def`：
   PDF 是子进程解析，与 `scan`/`collect` 同款理由；已加进那条结构性测试的参数表）。
2. **主机三条路由**（`/ks/materials/locators` 用 query 区分两个 id、`/ks/materials/reverify`），
   并进 `KS_MATERIALS_PATHS`（那条"注册了全部 N 条"的断言自动覆盖新路径）。
3. **参考资料面板**：材料行在 `stale`/`unknown` 时显示 ⚠（`ok` **不加噪声**）+
   「复算锚点」按钮（**贵动作，只由用户点**；`no_locators` 时禁用）。
4. **研究报告**：材料清单行带 `⚠锚点需复算` / `⚠锚点未验证`，并**在 warnings 里也出现一次**
   （清单里的标记要逐条读才看得到，而"引用位置可能失效"该被一眼看到）。
   报告只跑**便宜判据**（重解析太贵，不能进报告路径）。

**措辞纪律在前端也守住**（这是本步最容易做错的地方）：界面文案里
「需复算」必须同时说"**不代表已经坏了**"，「未验证」必须同时说"**不等于有问题**"
——两句话都进了 `smoke-client-entry` 的标记断言（少一句就等于把"不确定"说成"有问题"）。

**测试**：`tests/test_material_locator.py`（14）+ `tests/test_material_api.py`
（新增 `TestLocatorEndpoints` 3 条 + 结构性测试参数 +1）+
`tests/test_research_report.py`（新增 `TestAnchorVisibility` 3 条）；
`smoke-materials-routes` 65 → **71**；`smoke-client-entry` 63 → **66**。
⚠ 其中一条 API 用例第一版走 HTTP `collect` 端点 ⇒ 离线时只能 `skip`，而"会跳的断言"
等于没有保证 ⇒ 改成用 `collect_text` 直接造材料（**不抓网**）。

**诚实边界**：
- **真机仍未点过**（两道门不变）：新端点要引擎重启才在活实例上出现。
- **`mismatch` 之后没有重建流程**：本步只让它**看得见**；重建（重解析 + 重建切片）
  与"把锚点状态接进答案链"都**未做**（后者要单独想清楚：材料进证据集走的是材料检索，
  与条款区间不是同一套坐标）。
- 面板只在**选中项目时**拉一次总览：之后新入库的材料要走"重新选一次项目"才会带上标记
  （**没有**做自动失效刷新——登记为已知粗糙点）。
- 报告里的 ⚠ 是**便宜判据**的结论：`unknown` **不等于**有问题（老材料全都会是它）。

**门禁（本步）**：`pytest` **1651 passed / 3 skipped / 0 failed**；`mypy src`
**134 files / 0 errors**；`smoke` **18 段全过**（`materials-routes` **71/71**、
`client-entry` **66/66**）；`verify:commands` 22/22；`tsc --noEmit` 0。

### 10.50 处置复核 b8（step-40~46）：3 个 MEDIUM + 6 个 LOW，以及它**打回我的三句话**

复核 b8 报了 3 个 MEDIUM + 6 个 LOW，并**证伪了我三条自述**。逐条处置如下（先记被证伪的，
因为那是最该写清的部分）。

**① 被证伪：§10.45 说"新增的表格形态用例让『删掉守卫要求①』有主"——实测那条变异全绿**
（复核的 `mutate_b8.py Y1`：**GREEN 64 passed**），而同一个改动**真的**新开 4 条"JS 进正文"
（`a < b<script>` / `a < /b<script>` / `3 < 5<script>` / `a <= b<script>`）。
**差别在于**：我那条用例里 `<script>` 之前有 `</p>` 收尾 ⇒ 守卫的第②条（"其后没有 `>`"）
先不成立，**根本走不到要求①**。**修法**：按复核给的四组输入新增
`test_guard_requirement_one_is_load_bearing`；变异体 Y1 现在**红**。
> 教训：**"有主"必须用变异证明**——否则"加了用例"与"加对了用例"看起来一模一样。

**② 被证伪：§10.43 说 `catalog_hidden`/`page_breaks`/`figure_html` "三列不在 schema.sql"**
——`git log -S` 证明后两列**从基线起就在**（`schema.sql:60` / `:87`），真实缺口**只有一列**
（影响 3 个端点），而这句话在**五处**重复过。**修法**：`server.py` 的引导注释与
`clause_repo.ensure_additive_columns()` 的 docstring 都改成"**只缺 `catalog_hidden` 一列**"，
并注明这是复核的更正；顺带按复核的 LOW-6 更正写路径迁移的**真触发点**
（是 `insert_clauses_in_txn`，不是 `insert_document`/`delete_document`）。
> 复核同时独立确认：**59 个 GET 端点 × 迁移开关两轮 ⇒ 关时恰好 3 个 500、开时 0 个**
> ——修复面完整，但我的描述夸大了。

**③ 被证伪：§10.47 说 `mapProbe` 的 404 改动影响了 `settings.js`**——它**有自己的一份
私有 `mapProbe`**（`settings.js:113`），那份**仍然**是 404→502。**修法**：`route_util.js`
的注释改成"真正共用的是 `materials_routes.js` 与 `report.js`；`settings.js` **不共用**"
并把那份私有实现**登记为同一判据的第二份实现**（只登记不合并：合并要动设置面板的
错误语义，属另一件事）。

**MEDIUM-1（守卫要求①零覆盖）** —— 见上面①。另外复核用 `probeG_req1.py` 证明
**去掉要求①真会漏 JS**，所以这不是"为了覆盖而覆盖"。

**MEDIUM-2：`_paginate` 让页数上限**变成可达** ⇒ 在报告自己的设计范围内丢 47% 的要点，
而我的措辞是"条数守恒（续页不丢内容）"**。复核的输入是"三份清单各填到 `LIST_CAP`"
（**不是畸形输入**）⇒ 609 条要点只放进去 323 条。**修法**：溢出页现在**算出并写明丢了多少条**
（"另有 N 条要点未放入本 PPT（共 M 条，这里放了 K 条）"），并新增用例钉住这句话；
措辞也改成"**续页不丢内容；页数上限触发时会写明丢了多少**"。

**MEDIUM-3：`MAX_BULLETS_PER_SLIDE = 12` 经几何测量就不够**（12 条 × 40 字 ≈ 7.20in >
正文框可用 6.19in ≈ 20 行）——与 b7 的"30 页假上界"**同型**（看起来有上界，其实不是）。
**修法**：**删掉那个常量**，改按**行预算**分页：`MAX_LINES_PER_SLIDE = 18` +
`CHARS_PER_LINE = 40`（`estimate_lines()` 单独抽出来**是为了可断言**——正是复核建议的钉法：
断言"每页估算行数 ≤ 行预算"）。新增两条用例（少量超长要点、条数与行数两种形态）。
⚠ **诚实边界**：这两个数字仍是**估算**（按 python-pptx 默认版式与默认字号），
**没有**做渲染级测量 ⇒ 它是"**减少溢出**"，不是"保证不溢出"。

**LOW-1（SQL `NOT IN` 静默排除 NULL 行）** —— 这条**是功能缺陷**，不是措辞：
`hybrid_engine` 的精确命中与模态召回两条 SQL 用 `legal_status NOT IN ('withdrawn','superseded')`，
而 `NOT IN` 对 NULL 求值是 NULL ⇒ **未核验的条款被静默排除**。
有意思的是这与 §10.44 的修复**方向相反**：上层（`fetch_full_clause`）已如实带出 NULL，
这条 SQL 又把它筛掉了。**修法**：两条 SQL 都改成
`(dm.legal_status IS NULL OR dm.legal_status NOT IN (…))`，
新增 `test_null_legal_status_is_not_silently_excluded`（**含反向断言**：已废止的仍要被排除），
变异体 Y3 **红在新增那条用例上**。

**LOW-4（全角斜杠）** —— 复核在生产库实测有一行 `'GBZ／T'`（U+FF0F）落进了法规树：
兄弟函数（`_hier_from_no` / `_std_type`）都做了全角归一，只有 `_STD_NO_PREFIX` 漏了。
**修法**：边界类补 `\uFF0F`，并把 `'GBZ／T'` 加进参数化用例（变异体 Y2 **红在那一组**）。
> ⚠ **2026-09-18 更正（复核 b9 的 LOW-1，§10.56）——上面这段把影响面写小了约 5879 倍，
> 而且根因写错了。** 实测（只读生产库 6417 行、把三个历史版本各跑一遍）：
> **5879/6417 = 91.6%** 的行 `top` 从法规树翻回标准树，方向**全部** `law → std`，
> 且全库含全角斜杠的行数**正好也是 5879**（全角斜杠在生产库是**常态**，不是"有一行"）。
> 根因不是"两个所有者归一不一致"，而是**上一区间 §10.47 把一般规则 `\b` 换成了枚举类**
> （`\b` 本来是对的：`／` 是非词字符，边界成立）——枚举漏了**一整类**非词分隔符。
> ⇒ 这不是"补一行的装饰性修复"，而是**92% 的标准语料挂在哪棵树**；
> 当小修看，会在后续重构里被轻易回退。§10.56 已把枚举**整个换回一般规则**
> （`(?![A-Za-z])` + NFKC 归一），并补了"枚举 `\b` 接受过的全部边界形态"的用例。

**LOW-5（raw text 族）** —— 复核实测 `iframe`/`xmp`/`noembed`/`noframes`/`noscript`/
`textarea`/`title`/`plaintext` 等的内容**全部**进正文。本步实测 **8/8 泄漏**，
处置成**两类**（不是一把全剥）：
- **收**（浏览器不渲染其内容）：`iframe` / `xmp` / `noembed` / `noframes` / `plaintext`
  （`plaintext` 无结束标签，正好走"找不到闭合就丢尾"那条既有逻辑）；
- **有意保留**（内容**可能有用**）：`noscript`（**我们不执行 JS**，它里面的兜底内容
  恰恰是"我们会看到的"）/ `textarea`（表单默认值）/ `title`（页面标题）。
⇒ 实测从 8/8 泄漏变成 **3/8**，而那 3 条是**决定的**，不是漏的（登记在方案 §12 未决第 9 条）。
变异体 Z2（只留 `script|style`）**红**。

**复核独立确认的三条（比我的自述更强，记下来）**：
1. §10.44 的修复在**真答案链**上成立，且它**补了我没做的反向控制**：同库另一条正常
   `effective` 条款**仍然入证** ⇒ 排除"修成谁都不进"；全仓只有**一处**从 SQL 构造条款模型
   ⇒ **没有第二条洗白路径**。
2. §10.45 的**顺序**修复是硬修复：**915 组语料 + 自写 HTML5 词法参照 + lxml + html.parser**
   三参照对表 ⇒ `new LEAK=0 / old LEAK=52 / 净修 64 / 引入 0`，并有**单调性论证**
   （那三个替换只删 `>` 不增 `>` ⇒ 新顺序的误判集合 ⊆ 旧顺序）。**我只做了 10 组。**
3. §10.43 的真实缺陷面是 **1 列 / 3 端点**，且 `init_schema()` 的 4 个非测试调用点都会
   经 `insert_clauses_in_txn` 自愈、脚本层无 `catalog_hidden` 读者 ⇒ **修复面完整**。

**我自己的流程失误（记下来，因为两次都差点变成"改坏文件"）**：
- 用 PowerShell 的 here-string 往源码里插含**反引号**的注释 ⇒ 反引号被当转义吃掉，
  行被拼坏（`# （etch_full_clause …）`、甚至把 `else` 语句并进注释行）；
- 用 `edit` 时 `old_string` 末尾带 `\n` 而 `new_string` 不带 ⇒ **吞掉换行**，
  把 `def`/`def` 挤成一行（`onToggleChunks`、`test_the_guard_runs_…` 各一次）。
⇒ 两次都靠 **`git checkout -- <file>` 从 HEAD 恢复后重做**（这两个文件当时的未提交改动
只有我先前的意图改动）+ `ast.parse` 校验；**教训**：往代码里写含 `$`/反引号的中文注释
要用 `edit` 工具或 `.py` 文件，别用 PowerShell 字符串；`edit` 的锚点**首尾换行要对齐**。
（另：`git checkout --` 在本仓的纪律是"**别对未提交且有价值的改动用**"——这两次之所以
安全，是因为改动本身要重做，且我先把坏文件备份到了 `var/tmp/`。）

**仍未做（复核指出、本步**不改**的）**：
- **`standard_type` 排序的生产 A/B 评测**：复核只能证"排序真的变了"（旧 `['u','r','m']`
  → 新 `['m','u','r']`）与机制（`is_mandatory` 是第二键），**相关性会不会变坏需要真实评测**
  ——本步**没有**做（不是"忽略"，是**明确留待**）。
  > ⚠ **2026-09-18 更正（复核 b9 的 LOW-4，§10.56）**：上面那两个排序样例是**合成对象**上的
  > 结果。**在区间端点 `f55b5de` 的生产语料上，第三键的区分度是 0**——生产库 `doc_meta` 只有
  > 两个 `(hierarchy, standard_type)` 组合：`GB`/`mandatory`（287 行，rank 6）与
  > `GB/T`/`recommended`（6130 行，rank **99**）⇒ 两档已被**第二键**完全分开，
  > 第三键**没有竞争对象**，"排序真的变了"在生产上并没有发生。
  > 真正让它生效的是**区间外**的 `6eede2e`（把 `GB/T`/`GB/Z` 补进 `HIERARCHY_RANK`，
  > 486,587 条条款此前排在企标之后——那是一条**缺陷修复**，见 §10.51 的只读实测）。
  > ⇒ 措辞纪律：说"某排序项生效了"之前，要先证明**生产语料上它真有区分度**。
- PPT 的**渲染级**溢出测量（现在只有几何估算）。
- §10.45 登记的三态（未闭合注释 / RCDATA / 未收尾引号属性）与 `noscript`/`textarea`/`title`
  的**有意保留**：都是**决定**，不是遗留 bug。

**门禁（本步）**：`pytest` **1657 passed / 3 skipped / 0 failed**（+6：守卫要求① 1、
raw text 族 1、行预算 2、掉条数声明 1、SQL NULL 1、全角斜杠 1，另有若干重写）；
`mypy src` **134 files / 0 errors**；`smoke` **18 段全过**（`materials-routes` 71/71、
`client-entry` 66/66，本步改了 `plugin/src/route_util.js` 的注释 ⇒ 重跑确认）；
`verify:commands` 22/22；`tsc --noEmit` 0。
**变异实验**：Y1 / Y2 / Y3 / Z1 / Z2 **全部 RED 且逐字节还原**（每一条都先用
`Copy-Item` 备份、跑完比对 sha256）。

### 10.51 把复核的"两处未评测"补上：PPT 行预算**钉到真实版式**，`standard_type` 做**只读实测**

复核 b7/b8 都点了同两件事：**PPT 的溢出只有估算**、**`standard_type` 排序从来没有评测**。
这一节把两件事都做成"有证据"，顺带**发现并修掉一个排序缺陷**。

**① PPT：行预算不再只是拍脑袋的常数（用真实版式反算 + 独立断言）**
- 从真实 `Presentation()` 量出：幻灯片 `9144000 × 6858000` EMU（10in × 7.5in），
  正文框是 `add_textbox(0, 1_000_000, slide_width, slide_height - 1_200_000)`
  ⇒ 高 `5658000` EMU = **445.5pt**；不设字号（`size=None`）⇒ 版式默认 **18pt**；
  行高按 1.2 倍 ⇒ 21.6pt/行 ⇒ 容量 **≈20.6 行**，取 **18** 作预算（留一行多余量）。
- 这些数字**进了常量并带注释**（`SLIDE_*_EMU` / `BODY_HEIGHT_PT` / `ASSUMED_FONT_PT` /
  `LINE_HEIGHT_FACTOR`），并新增 `test_line_budget_matches_the_real_slide_geometry`：
  **从真实模板重算**并断言"行预算 × 行高 ≤ 正文框高"、"每行容量 = 框宽/字号"一致
  ——常量与版式**不会各自漂移**。
- `estimate_lines()` 也改成**全角当量**模型（中文 1.0、ASCII 0.5）：一律按字符数会把英文
  清单**高估**（拆得更碎，只是浪费），而它的反面（低估中文）才是危险方向；两条都有断言
  （`test_ascii_bullets_are_cheaper_than_cjk_bullets`）。
- **变异实验**：`CHARS_PER_LINE=100` / `MAX_LINES_PER_SLIDE=25` / `estimate_lines` 退回字符数
  ⇒ **三个变异体全 RED**且逐字节还原。

**② `standard_type` 排序：只读实测（不是"读代码觉得它有用"）**
只读聚合生产库（`mode=ro`，两条 `GROUP BY`，不写库、不做大扫描）：
```
doc_meta.standard_type : recommended 6130 / mandatory 287
按 legal_hierarchy     : GB/T 6130 份（全 recommended） / GB 287 份（全 mandatory）
条款级                 : GB/T 486,587 条（全 recommended） / GB 33,917 条（全 mandatory）
```
**结论（对复核那个问题的正面回答）**：在**当时的代码**下，`standard_type` 这个排序键
**在生产库里等于没作用**——不是因为库小，而是因为两个档被 `rank` 完全分开了
（`GB`=6、`GB/T`=99）⇒ 第三键**没有竞争对象**，既不会变好也不会变坏。
**但同一份数据也暴露出一个真缺陷**：`GB/T` **不在** `HIERARCHY_RANK` 里
（`.get(..., 99)`）⇒ **486,587 条条款**（库里的绝大多数）**排在企标（10）之后**。

**修法（缺陷修复，不是口味）**：`HIERARCHY_RANK` 补 `'GB/T': 6` 与 `'GB/Z': 6`
（三者都是**国家标准**；强制/推荐/指导的区分交给第②键 `is_mandatory` 与第③键
`standard_type` —— 那正是它们存在的意义）。补上之后：
- `GB/T` 回到与 `GB` 同档 ⇒ **第三键第一次真正有区分度**，且方向（GB 在前）与
  实测的"GB 全 mandatory / GB/T 全 recommended"一致 ⇒ **启用它不会引入相关性风险**；
- `hierarchy_label` 用 `<= 5` 判"法律类"，6 不受影响（不会把 GB/T 误标成法律层级）。
新增 `test_rank_with_hierarchy_gbt_is_a_national_standard`（含"法律 > GB/T > 企标"的
顺序断言）；变异体 H1（去掉 `GB/T`/`GB/Z`）**RED** 且逐字节还原。

**诚实边界**：
- ①的几何仍然是**按默认模板 + 默认字号 + 1.2 行高**的估算，**没有渲染级测量**
  （要渲染得引 LibreOffice/真机 PowerPoint，未立项）；它现在钉住的是"**常量与版式一致**"
  与"**不再用条数当代理**"，不是"保证不溢出"。
- ②的评估是**分布统计**（只读），**不是**相关性 A/B：我证明的是"改前无竞争对象、
  改后方向与数据一致"，**没有**用真实问题做人工相关性打分（那需要评测集与标注，
  本仓没有）。若将来 `standard_type` 与 `hierarchy` 不再高度相关（例如同层级里混入
  两种类型），**应重新评估**再决定是否保留这个键。
- 生产库只读聚合用了 `%APPDATA%\KnowledgeStation\database\knowledge.db`（一条 `GROUP BY`），
  **未写库**（`mode=ro`）。

**门禁（本步）**：`pytest` **1661 passed / 3 skipped / 0 failed**（+4：几何一致性、
全角当量、GB/T 位阶、以及一条重写）；`mypy src` **134 files / 0 errors**；
`smoke` 18 段（未改 `plugin/`）；`verify:commands` 22/22；`tsc --noEmit` 0。
变异实验 G1/G2/G3/H1 **全 RED 且逐字节还原**。

### 10.52 收掉方案里两个"仍未定"：**不共池**、评审 UI **留在设置侧栏**

方案 §12 有两条挂着的"未定"，它们其实**已经被实现定型了**，只是没人把决定写下来。
按"需要拍板的就按推荐继续"的口径，这里把决定与**理由**记清（代码即证据）。

**① 材料与法条检索是否共池 ⇒ 不共池，分节并列。**
- 事实：两条检索线各有自己的表与所有者——`clause_fts`（`hybrid_engine` 查法条）与
  `material_fts`（`material_repo` 查材料）；两者**共用同一个分词实现**
  （`text_utils.fts_match_expr`）是为了"同一句话两边搜得到/搜不到要一致"，不是为了合并。
  答案链里材料**另起一节**、编号两套（`[[m:i]]` / `[[c:i]]`），且**不给
  `params.material_project_id` 时提示词逐字不变**（B-5 的回归保证，§10.14）。
- **为什么不合并**：① 两条线的**门**不同（材料有评审硬门 + 两个权威轴；法条是库内已核验）；
  ② 合并就得在同一语料上跑两套规则 ⇒ **两个轴会互相渗漏**（本战役反复强调"轴 A 与轴 B
  不可折叠"）；③ 引用编号混成一套后，用户与模型都分不清"这条是库内法条还是你上传的材料"。
- ⇒ **维持现状**；将来若要共池，先解决上面三条（**新立项**，不是顺手改）。

**② 材料评审 UI 的落位 ⇒ 留在设置侧栏（现状），不进 `conversation.input.dock`。**
- 现状即实现：`KsSettingsSection` 的「参考资料」类目里是 `KsMaterialsPanel`
  （项目 / 收件箱 / 自采 / **逐份评审** / 两个轴 / 产出）。
- **为什么**：① **评审是刻意的、慢的动作**（要读正文、要判断），放进对话流会诱导
  "顺手点通过"——而评审闸门是这功能的立身之本；② 它与「效力报告」相邻，两者都是
  "库内东西的管理台"；③ 对话侧只留**绑定**（`/materials use <prj>`）与产出入口，职责清楚。
- ⇒ **不迁移**；若将来要"对话里快速看材料"，那是**只读**入口，**不是**评审入口。

**诚实边界**：这两条都是**记录既有事实 + 说明理由**，**没有代码改动**；若业主不同意，
改的是 UI 落位（迁移面板）或检索架构（合并两池），两者都不是小改。



### 10.53 真机 GUI 第一次真的点了面板：抓到两个真缺陷，并把"两道门"量化

**背景**：方案 §12 里"真机 GUI 端到端未验证"挂了很久。这次发现本机 **CDP 端口 9333 上有活的
浏览器**（既有 `e2e-sidebar-pdf.mjs` 就是为它写的），于是把材料面板也接进同一个马具。

**先量清楚"真机在跑哪一版"**（这决定了能验证什么）：
- **客户端半是现读现发的**：抓下 DSH 发出去的 `/plugins/??…ks-dsh-plugin/client.js`，
  解码 `\uXXXX` 后与本地产物**逐段比对** ⇒ 除尾部空白外**逐字一致**，
  连 `复算锚点` / `自采一条` / `ks/materials/locators` 都在。
- **宿主半是启动时载入的**：`/ks/materials*` 与 `/ks/report/research*` 一律 **404**，
  而 `/ks/chat-mode`、`/ks/session`、`/ks/inspection/*`、`/ks/announce/*`、`/ks/report/effect`
  正常 ⇒ 活的宿主（pid 37268，**19:06:12** 启动）早于材料提交（**23:19** 起）。
- 引擎（pid 32564，**19:14:53**）同理：活实例 `/openapi.json` 113 条路径、0 条 materials。
⇒ 这就是"代码全绿、真机 404"的全部原因；**不是**构建或接线错。已写进方案未决第 11 条。

**新增真机 e2e**：`plugin/scripts/e2e-materials-panel.mjs`（`npm run e2e:materials`，
与 PDF 那条同款：没浏览器就 SKIP 且退出 0，不进 `npm run smoke`）。9 条断言，其中三条是这轮的重点：
- A3 面板**真的挂进了设置界面**（`设置 → 法规标准知识库 → 参考资料`）且 `console.error` /
  未捕获异常为 **0**——这是该组件**第一次被真实浏览器渲染**（离线冒烟只跑得到纯函数与路由表）。
- B1 硬门文案 `评审是硬门` 在位：这句是"谁批准了才进结论"的**用户可见承诺**。
- C1/C3 **失败必须如实说**：任何 `/ks/materials/*` 失败 ⇒ 界面必须有 `操作失败：…`；
  层级清单失败 ⇒ 必须有 `来源层级清单…没读到`。

**它当场抓出两个真缺陷**（都是"静默降级"族，P1 最不能接受的形状）：
1. `fetchMaterialTiers(...).catch(() => [])` 把"清单没读到"变成"清单就是空的" ⇒ 材料行的
   「轴 A 来源可信度」下拉只剩**当前值一个选项**，用户看到的是"这份材料只有一个层级可选"，
   而真相是"这份清单没取到"。（与 `legal_status` 的 NULL 洗白同族。）
2. **我自己的第一版修复仍然不显示**：我把失败记进局部变量、等 `Promise.all` 的 `await`
   回来再落地——项目列表也失败时 `Promise.all` 先 reject，函数直接跳进 catch，
   "清单没读到"**永远说不出口**（静默只是从一层挪到另一层）。e2e 的 C3 当场把它证伪。
   ⇒ 修法：**两条请求各自结算**，清单自己 `then/catch`、自己落地。
   顺带把"清单没取到时"的下拉**禁用**并给 `title`（留着可点会让"改不了级"看起来像点了没反应）。

**马具本身的一个坑（值得单独记）**：`Page.reload({ ignoreCache: true })` **拦不住**插件
bundle——它是 `import('/plugins/??…&rev=…')` 动态取的，浏览器内存缓存会继续喂**旧产物**，
于是"改了代码却仍在测旧产物" ⇒ 假红（也意味着可能假绿）。
修法：`Network.setCacheDisabled({ cacheDisabled: true })`；已同时补进 PDF 那条 e2e。
诊断过程：本地产物里**有**新文案、页面渲染里**没有** ⇒ 再用 `rev` 变了（旧 rev 404）
这一步定位到缓存，而不是构建。

**变异证据**（都做过、都 byte-identical 还原）：
- **M1**（把 warn 渲染条件 `tierListFailed &&` 改成 `false &&`，重建）：真机 e2e **C3 RED**
  （8/9，exit 1）；⚠ 产物内的字符串断言**仍绿**——因为它只删"渲染"不删"文案"。
  ⇒ 这正好量出**两条闸门的分工**：e2e 管"渲染有没有说"，离线串断言管"文案有没有被删"。
- **M2**（把两条请求各自结算改回 `.catch(() => [] as KsMaterialTierDef[])`，不重建）：
  离线两条源码护栏**同时 RED**（67/69），还原后 **69/69**。

**新增离线护栏 3 条**（`smoke-client-entry.mjs`，66 → 69）：产物含诚实文案、
源码里没有 `fetchMaterialTiers(...).catch(() => [])` 这种写法、清单请求自己落地成败
（用 `\s*` 而不是写死 `\n`——本仓 TSX 是 LF 但同类文件有 CRLF，写死换行会静默匹配不上）。

**顺带一条诚实记录**：串行 `npm run smoke` 里 chatmode 那条老偶发
（`a session closed by this process is not resurrected from disk`）这轮又红一次，
而详情 `persisted=false` **第一次真的分清了**：是**写盘没成功**（锁等待 3s 超时），
不是"复活逻辑错"；单独跑 173/173，紧接着整条链 **EXIT=0**。当时并发跑着两轮真机 e2e
（Edge 渲染 PDF）+ 复核方 pytest。**故意不改**生产侧 `LOCK_WAIT_MS`——为让测试变绿而放松
一把真锁，方向是错的。

**本轮门禁（全绿）**：pytest **1661 passed / 3 skipped**；mypy **134 files / 0 errors**；
`npm run typecheck` **0**；`npm run smoke` **EXIT=0**（client-entry 69/69）；
`verify:commands` **22/22**；`e2e:sidebar` **13/13**；`e2e:materials` **9/9**。

**诚实边界**：happy path（建项目 → 扫描收件 → 批准 → 产出报告/PPT）**仍未在真机走通**，
卡在两道门（宿主 + 引擎都早于本战役）；今天真机验证的是**失败路径的诚实性**与
**面板能不能挂进设置界面**——比"没验证"强，但**不等于功能可用**。另外 `tool.call.toolview`
（核验 UI 半）仍未动：它 `replaceRisk: shadows-shipped-ui`，要画整张卡，必须先能看见。

### 10.54 处置复核 b9（step-47~49）：先修两条"静默报 ok"的洞 + 同步词表

复核 b9 给了 **4 MEDIUM + 6 LOW + 5 INFO**，逐条带实测证据。按小步纪律**分步修**，
本步只收 **MEDIUM-1 + MEDIUM-2 + LOW-6**（都是"锚点判据说谎"这一族），台账写进方案未决第 12 条。

**MEDIUM-1：源文件被删除／被同名替换时 `locator_health` 报 `ok`。**
- 根因：`current_fingerprint_for()` **只看后缀**——它从不 `is_file()`，也从不比
  `material.content_hash`（那个哈希**已经在库里**，是源文件字节的 sha256）。
  于是"用户把更新版 PDF 放回项目目录再扫一次"（**正常操作**）与"材料目录被清理"之后，
  材料照旧显示 `ok`（"未发现变化"），界面与报告的 ⚠ **一个都不出**。
- 这正是本模块立论要防的那一类（"**看起来很正常的错引用比报错危险得多**"），
  而且报告/面板的 ⚠ **全部**依赖这个便宜判据。
- 修法（比"只比字符串"贵一点：每个材料一次**流式** sha256，不起子进程）：
  ① 源文件材料先判 `is_file()`，不在 ⇒ `unknown`（"源文件不在磁盘上…**不是 ok**"）；
  ② 再比 `file_hash(磁盘)` vs `material.content_hash`，不一致 ⇒ **`stale`**，且措辞点明
  "**源文件字节已变**（与入库时记的 content_hash 不一致）⇒ 已存区间是按**旧字节**解析出来的，
  对新文件不再成立"。PDF 也走这一轴：字节变了就是 `stale`，不再停在 `unknown`。
- 诚实代价：`locator_health` 因此**要读一次源文件**，模块 docstring 里"便宜"的说法已改准。
  真嫌贵，正确的优化是**缓存 size/mtime**（已登记），**不是**删掉这条判据。

**MEDIUM-2：`reverify` 把"确定的失效"降级成 `unavailable`（"验不了"）。**
- 判定顺序原先是"先看重解析是否为空 → 再看 recorded"，于是"入库时**有**派生文本、
  现在重解析**一个字都得不到**"（文件被截断／换成扫描件／文本层丢了）回 `unavailable`；
  而 `unavailable` **不是** health 状态 ⇒ 这份材料在界面与报告里**一个标记都没有**。
- 修法：`recorded is not None` 且重解析为空 ⇒ **`mismatch`**，措辞"入库时**有**派生文本，
  而重解析**一个字都得不到** ⇒ 已存区间**必然失效**（不是'验不了'：基准是存在的，对不上）"。

**LOW-6：词表前后不一致。** 模块 docstring 与方案 §12-5 都列着 `no_text`，而代码
**刻意**没有这一档（解析不出文本必然 `chunk_count == 0` ⇒ 落 `no_locators`）；
另外把 `unavailable` 说成"不是 ok"容易让人以为它可能由 `locator_health` 返回（它不会，
它是 `REVERIFY_STATUSES` 的词）。两处都改准，并把"源文件字节"这一轴写进 docstring。

**顺带修掉的两处"替后端下结论"的界面/报告措辞**（MEDIUM-1 的直接后果）：
- 面板原先写死"**解析器身份变了**，已存区间**可能**失效"——`stale` 现在有**两个**成因，
  写死等于替后端下结论，且"可能"把"字节已变"这条**确定**失效说轻了。改成
  **照抄后端的 `why`**（总览接口的 `attention` 里本来就带着），界面不再自己解释 status；
  同时保留"**不代表已经坏了**"这句偏差纪律。
- 报告的同一条 warning 同理：不再只说"解析器身份变了"，改为"解析器身份变了，或**源文件字节已变**"。
- ⚠ 这两处改动**当场被两条既有闸门抓住**（`test_research_report` 钉的"可能失效"、
  `smoke-client-entry` 钉的"不代表已经坏了"）——**闸门在按设计工作**。
  报告那条断言改成钉"**不代表已经坏了**"（被钉住的**语义**是"不许升级成'已经坏了'"，
  而不是某一句原文），改动理由写在测试里。

**变异证据（全部逐字节还原，sha256 `ec5d2f42…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| V4 | 源文件存在性检查改成"永远匹配" | `test_deleted_source_file_is_not_ok` **RED**（复核 b9 报的同一个 V4 在修前是 **GREEN 17 passed** = 零覆盖） |
| V6 | 去掉"字节不一致 ⇒ stale"那一支 | 换文件两条（txt + PDF）**RED** |
| V7 | MEDIUM-2 退回"无条件 unavailable" | `test_text_then_blank_reparse_is_a_mismatch` **RED** |
| V8 | 字节比对改成恒 `False`（判据坏向另一侧） | **反向对照** `test_unchanged_source_still_ok` **RED** |

V8 是特意加的：没有反向对照，"不是 ok"的三条断言可能只是"**永远不是 ok**"。

**顺带修掉一个"假绿"的既有测试**：`test_pdf_cheap_check_refuses_to_claim_ok` 的 fixture
一直用一个**不存在的** `x.pdf` 路径——本步加了存在性检查后它会先落进"源文件不在"那条分支，
**测试还是绿的，却不再测它宣称的"PDF 前缀比对拒绝给 ok"**。已改成写一个真文件。
（这正是我反复栽的那类"测试测的不是它宣称的东西"。）

**门禁**：pytest **1667 passed / 3 skipped**（新增 6 条）；mypy **134 files / 0 errors**；
`npm run typecheck` **0**；`npm run smoke` **EXIT=0**（client-entry 69/69）；e2e 两条照旧。

**诚实边界**：本步**没有**动 MEDIUM-3（PPT 渲染级溢出）、MEDIUM-4（`xmp`/`plaintext`
是可见文字）、LOW-1~5、INFO-3~5——台账在方案未决第 12 条，下一步按严重度继续。
另：`locator_health` 现在会读源文件，**项目总览**在有几十份大 PDF 时会变慢；
本步选择"准确优先"，把 size/mtime 缓存登记为待办而不是先优化。


### 10.55 处置复核 b9（第二步）：PPT 渲染级丢字、以及我自己收编错了两个标签

承接 §10.54（台账在方案未决第 12 条），本步收 **MEDIUM-3 + MEDIUM-4**。

**MEDIUM-3：PPT 的"行预算"偏乐观 ⇒ 渲染器**静默裁字**（不是丢条数）。**
- 复核做了我明确说"仍未做"的**渲染级**测量（LibreOffice → PDF → PyMuPDF 逐行 bbox）：
  18 条 × 40 字被判"18 行一页"（真排 2 行/条）⇒ PDF 里只剩 **440/720 字（丢 39%）**；
  39 字 ⇒ 429/702；**38 字 ⇒ 684/684 完整**；9 条 × 78 字 ⇒ 丢 118。
- 两个根因，**各占一半**：
  ① 每行容量写的是 `720pt / 18pt = 40`——拿的是**整张幻灯片宽**，而文本框左右各有
  0.1in 内边距，真正能用的是 **705.6pt ⇒ 39.2em**（注释还把 40 说成"偏保守"，**实测相反**）；
  ② `estimate_lines()` 估算时**根本没算**渲染时才加上的 `· ` 前缀（`write_slide_deck` 里
  `f"· {bullet}"`），等于每条都多算一格。
- 修法：新增 `BODY_WIDTH_EMU/PT`（可用宽，由几何测试从**真实 `text_frame.margin_*`** 重算并钉住）
  与 `BULLET_PREFIX`；`estimate_lines` 改成**逐行模拟换行**（首行先扣前缀），
  比较用**整数**（容量 ×10）以免浮点在 39.2em 这个临界点上抖。`MAX_LINES_PER_SLIDE=18`
  不动（容量 20.63 行，仍是保守的 87%）。
- **渲染级复测**（复用复核的链路，跑**主检出**的代码，`var/tmp/probe-step54-render.py`）：
  判据从"第 2 页剩几个字"改成**整份 PPT 的字数守恒**（修好后超出的要点是**续页**，不是被裁）：
  | 输入 | 修复前 | 修复后 |
  |---|---|---|
  | 18 × 40 字 | 440/720（丢 280） | **720/720**，2 个正文页 [360, 360] |
  | 18 × 39 字 | 429/702（丢 273） | **702/702**，2 页 [351, 351] |
  | 18 × 38 字 | 684/684 | **684/684**，**1 页**（不多拆） |
  | 9 × 78 字 | 584/702（丢 118） | **702/702**，2 页 [468, 234] |
- 诚实边界：字数守恒是**本机默认版式 + LibreOffice 字体回退**下的实测；原理性结论
  （CJK 1em、内边距、前缀占位）与字体无关，但**阈值要在业主的模板/WPS/PowerPoint 下重测**。
  英文按"任意断行"估算 ⇒ 比真实渲染**多**算几行，方向安全（多续页，不裁字）。

**MEDIUM-4：我自己把两个"浏览器会显示"的标签当成"不渲染"收掉了。**
- §10.50 处理 b8 的 LOW-5 时，把 `iframe` / `xmp` / `noembed` / `noframes` / `plaintext`
  一起收进"内容不进正文"，依据是一句**没验证过**的注释。复核 b9 用 Edge headless 的
  `innerText`（用户真能看到的字）裁决：`iframe`/`noembed`/`noframes` **确实不显示**，
  而 **`xmp` 显示**（原样字面文本）、**`plaintext` 显示**（其后全部当可见文本）
  ⇒ 收掉它们是**删可见正文**，方向与本函数定位（"页面上看到什么就是正文"）**相反**，
  而且这个删除是**本战役引入**的（修前这两个的内容是保留的）。
- 修法：`_CONTENT_HIDDEN_TAGS` 只留 `script|style|iframe|noembed|noframes`；
  注释里把**两条不同判据分开写**（"浏览器不显示且不要" vs "浏览器不显示但我们要"）
  ——上一版把它们混成一条，正是 `xmp`/`plaintext` 混进来的原因。
- 既有用例 `test_raw_text_families_that_browsers_do_not_render_are_stripped` 钉的是**旧行为**，
  已改成成对断言：三个不显示的**必须剥掉**、两个会显示的**必须留下**、
  三个有意保留的**仍要留下**。

**变异证据（全部逐字节还原，`slide_export.py` sha256 `4253a0b9…` / `text_utils.py` `236df3f4…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| M3a | 容量退回"整张宽/字号"（=40） | 临界点用例 RED（39 字被判 1 行）；⚠ 续页用例**仍绿**——只算前缀就够救 40 字那种输入 |
| M3b | 估算时不算 `· ` 前缀 | 临界点用例 RED |
| M3c | **两处一起退回 = 真正修复前** | 临界点 RED **+ 续页用例 RED**，"38 字不多拆"的反向对照**仍绿** |
| M4 | 把 `xmp`/`plaintext` 重新收进去 | 可见文字用例 RED |

M3a/M3b 是**单点**变异：各自只让"临界点"那条红，说明修复的两半**各自都不够**、
合起来才救下"会被裁字"的输入；M3c（组合）才让"必须续页"那条红——这就是该用例的价值边界，
记录在案以免有人以为它能单独挡住单点退化。

**门禁**：pytest **1670 passed / 3 skipped**（新增 3 条）；mypy **134 files / 0 errors**；
`npm run smoke` **EXIT=0**；渲染级探针 **render-conservation PASS**。

**仍然开着**（方案未决第 12 条）：LOW-1（记录少报 5879 倍）、LOW-2（边界仍枚举）、
LOW-3（NULL 排最前）、LOW-4（第三键零区分度）、LOW-5（端点索引）、INFO-3/4/5。


### 10.56 处置复核 b9（第三步）：把"一般规则被换成枚举"这类缺陷连根收掉，并更正三处记录

承接 §10.54/§10.55，本步收 **LOW-1 + LOW-2 + LOW-3 + LOW-4 + LOW-5**（都是 LOW，
但其中两条是**真缺陷**、不是措辞问题）。

**LOW-3（真缺陷）：`ORDER BY dm.legal_status` 把"未核验"排到最前 ⇒ 通道内权重给反了。**
- 同一条 SQL 上两个方向相反的修复叠在一起：`NOT IN (…)` 对 NULL 求值是 NULL ⇒ 未核验条款曾被
  **静默排除**（b8 的 LOW，已把他们**放进来**）；而 SQLite 的 `ORDER BY x` **把 NULL 排最前**，
  `rank` 又直接决定 `CHANNEL_WEIGHTS/(RRF_K+rank+1)` ⇒ 刚被放进来的未核验条款拿到
  **通道内最好的名次**——方向与 §10.44 的"未核验不得承重"**相反**。
- 修法：`ORDER BY (dm.legal_status IS NULL), dm.legal_status`（未核验沉底，已知状态的按名排）。
- ⚠ 顺带发现**另一个**同类问题并**登记不改**：模态通道（通道 D）**根本没有 ORDER BY**
  ⇒ 它的 `rank` 顺序取决于 SQLite 的返回次序（未定义、可能不稳定）⇒ 同一查询的权重分配
  **不可复现**。修它要定"通道内该怎么排"，会动到检索结果分布 ⇒ 单独一步，不夹带。

**LOW-2（潜性缺陷）+ LOW-1（记录错误）：判据整条换回一般规则。**
- 事实（**只读生产库 6417 行、三个历史版本各跑一遍**，`var/tmp/probe-step55-prod-matrix.py`）：
  | 版本 | 判据 | 相对上一版翻转 |
  |---|---|---|
  | A 最初 | `\b` | — |
  | B0 §10.47 | `(?=[\s/]\|\d\|$)` | **A→B0 = 5879 行 = 91.6%**，方向**全部** `std → law`（见下方更正） |
  | B §10.50 | 再把 `／` 加进枚举 | **B0→B = 5879 行 = 91.6%**，方向**全部** `law → std` |
  | C 本步 | `(?![A-Za-z])` + NFKC | **B→C = 0 行**、**A→C = 0 行**、反向翻转 **0** |
  > ⚠ **2026-09-18 更正（复核 b10 的 LOW-2，§10.65）**：上面 B0 那一格原写 **"A→B0 = 0 行"**，
  > **错了**——那是把 **`A→B`**（`\b` 与"枚举含 `／`"之间）的结果填到了 `A→B0` 这一格上。
  > 我当时的探针**根本没算 `A→B0`**（它打印的是 `A→B = 0`，因为 `\b` 与"枚举含 `／`"对这批行
  > 判定相同）。**正确值：A→B0 = 5879 行，方向全部 `std → law`**
  > （`\b` 对 `GBZ／T` 是成立的：`／` 是非词字符；换成枚举又把 `／` 漏了 ⇒ 这 5879 行掉进法规树）。
  > 这个格子**恰好抵消了本节要立的结论**（"根因 = 上一区间 `\b`→枚举的回归"）：
  > 写成 0 行，读者会以为那次改写**没有影响**。⇒ 两处都记：**A→B0 = 5879（std→law）**、
  > **B0→B = 5879（law→std）**，中间的 `A→B = 0` 只说明"最终修回来了"，**不是**"没坏过"。
  > 复核 b10 用**原文重跑**独立确认了这一点。
  即：复核说的 **5879/6417 = 91.6% 独立确认**，而且全库含全角斜杠的行数**正好也是 5879**
  ——全角斜杠在生产库是**常态**，不是"有一行"。根因是**上一区间把一般规则 `\b` 换成枚举类**
  引入的回归（`\b` 本来是对的），**不是**"两个所有者归一不一致"。
- 修法：`_STD_NO_PREFIX` 换成 `(?![A-Za-z])`（**一般规则**：前缀后面只要不是字母就算标准号）
  + 判定前做 **NFKC 归一**（全角字母 `ＧＢ`、全角斜杠 `／`、分数斜杠 `⁄` 一起解决，
  不必再枚举全角形态；与兄弟函数 `_hier_from_no`/`_std_type` 同款）。名单顺序改成**长前缀在前**。
  新增 `_is_standard_no()`（判据单独可断言）。
- ⚠ **诚实边界**：C 在生产库上**一行都没变**（B 与 C 完全一致）——`-`/`—`/全角字母那几类
  当前 0 行，所以这一步**今天没有实际影响**，它关的是**这一整类的复发风险**。
- 新增 `tests/test_doc_catalog_std_no.py`（20 条）：把"**A 版 `\b` 接受过的全部边界形态**"
  枚举成用例（半角连字符、破折号、全角空格、全角字母、无空格接数字、光杆 `GB`…），
  外加"不许一起放松"的反向组（`GBX`/`DBX`/法规名/空串）与"`classify_document` 必须走这条判据"
  的接线断言。这样"一般规则被换成枚举"**必然**留下证据——LOW-1 的教训正是"枚举漏一整类"。

**LOW-4（记录错误）：`standard_type` 的"排序真的变了"在生产上并没发生。**
  复核指出：区间端点 `f55b5de` 上生产库只有两个 `(hierarchy, standard_type)` 组合
  （`GB`/`mandatory`=287 行 rank 6、`GB/T`/`recommended`=6130 行 rank 99）⇒ 两档已被第二键
  完全分开，**第三键零区分度**，那两个"变了的排序样例"只是**合成对象**上的结果。
  已在 §10.50 的对应段落加更正块：真正生效的是**区间外**的 `6eede2e`（把 `GB/T`/`GB/Z`
  补进 `HIERARCHY_RANK`，那是一条**缺陷修复**，见 §10.51 的只读实测）。

**LOW-1（记录错误）：§10.50 把"全角斜杠"的影响面写小了约 5879 倍、根因也写错。**
  已在 §10.50 那段加更正块（实测数字 + 根因 = 上一区间 `\b`→枚举的回归 + "当小修会被回退"的提醒）。

**LOW-5（文档）：引擎模块 docstring 的端点索引缺 4 条**（`tiers` 早就漏了，
本步新增的 `locators`×2 与 `reverify` 也没列）。已补全（现列 18 条 = 18 个 `@app.*` 装饰器），
并在索引上加一句"新增端点时必须同时补这里，或直接数一遍装饰器"。

**变异证据（全部逐字节还原，`hybrid_engine.py` sha256 `266b259d…` / `doc_catalog.py` `72d6454b…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| L1 | 排序退回 `ORDER BY dm.legal_status` | `test_unverified_clause_does_not_outrank_an_effective_one` **RED** |
| L2 | 判据退回**枚举类**（并去掉 NFKC） | 边界形态普查 **4 failed / 16 passed**（正是那几类丢掉的形态） |

**门禁**：pytest **1691 passed / 3 skipped**（新增 21 条）；mypy **134 files / 0 errors**；
`npm run smoke` **EXIT=0**；生产库探针只读，未改一行数据。

**b9 台账现状**（方案未决第 12 条）：4 MEDIUM **全收**；LOW-1/2/3/4/5/6 **全收**；
剩 INFO-3（健康度异常被吞成 unknown ⇒ 多报一条 ⚠）、INFO-4（报告 ⚠ 不覆盖"依据"节）、
INFO-5（`no_locators` 两种成因文案未区分）——三条都是"更精确"而非"说谎"，登记待办。


### 10.57 收掉 b9 的两条 INFO，并修掉它们的**同族**缺陷（"结论没拿到"不许装成材料的结论）

b9 台账里剩下的是 INFO 级，但其中 INFO-3 是**真**的诚实问题（不是措辞）：本步收 INFO-3 + INFO-5，
并顺带发现/修掉 INFO-3 的**同型**缺陷（同一个错误的第二处，b9 没提到）。

**INFO-3（真问题）：判据抛异常被写成"这份材料未验证"。**
- 旧写法：`_attach_locator_status` 的 `except` 里写死 `_locator_status = "unknown"` ⇒ 报告上出现
  "⚠锚点**未验证**（不等于有问题）"——读者会去怀疑**材料**，而真相是**我们的判据跑挂了**。
- 修法：新增取值 `health_error`（**明确不是**健康状态：`locator_health` 永远不会返回它，
  与 `unavailable` 之于 `reverify` 同理），
  报告里给独立标记 `⚠锚点健康度算不出来` + 独立 warning（"这是**工具缺陷**，不是这些材料有问题"），
  并**断言它不再出现在"未经验证"那一条里**。

**同族缺陷（b9 未提，本步自查发现）：项目总览会让一份材料毁掉整份总览。**
- `project_locator_summary()` 逐份调 `locator_health()` 时**没有**保护 ⇒ 一份材料抛异常，
  整个端点 500；而面板对总览失败是 `.catch(()=>{})`（"不该挡住材料列表"）⇒ 用户看到一份
  **一个 ⚠ 都没有**的材料列表，读起来像"全都健康"。**这与 INFO-3 是同一个错误**：
  "结论没拿到"被渲染成"没有结论要报"。
- 修法：单份 try/except ⇒ 那一份标 `health_error` 进 `statuses`/`counts`/`attention`（带 `why`），
  其余照常给结论；`note` 里也写明"`health_error` 不是健康状态"。
  面板加**独立分支**（红色 `role="alert"`）——不加这一支，那种材料在界面上仍然**没有标记**。
  ⚠ 这一步**被类型系统拦了一次**：`KsLocatorHealth['status']` 的 union 里没有 `health_error`，
  `tsc` 直接报"两个类型没有重叠" ⇒ 扩 union 才过。**这是好事**：类型把一个"会被静默忽略"的
  取值变成了编译期错误（注释里写明了为什么它必须在这个 union 里）。

**INFO-5：`no_locators` 的两种成因不再共用一句话。**
- ① 压根没有派生文本（扫描件没开 OCR / 入库早于该列）；② 有派生文本但**切块没产出**。
  判据用入库时记的 `derived_text_hash`（有它 ⇒ 当时确实产出过文本），两句话分开写。

**变异证据（逐字节还原，`locator.py` sha256 `9f1e890a…` / `research_report.py` `a59bc4fc…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| N1 | 报告的异常分支退回 `unknown` | `test_health_crash_is_not_reported_as_unverified` **RED** |
| N2 | `no_locators` 两种成因退回同一句 | 两条成因断言 **RED** |
| N3 | 总览去掉单份保护 | `test_one_crashing_material_does_not_kill_the_whole_overview` **RED** |

⚠ **N2 两次返工，两次教训都记下来**（都属"变异本身没打中"）：
① 第一版把整段字面量换成 `""  # 注释` ⇒ 把后面的字符串拼接注释掉了，**文件解析不了**
（收集期 error），而且还原断言因为标记重复而失败、文件一度停在坏状态——**已从 pristine 快照
byte-identical 还原**（并加了 `ast.parse` 自查）；
② 第二版只改了括号里的补充说明，而"没有派生文本 / 有派生文本但切块没产出"在**前一行的字面量**里
⇒ 测试**照旧全绿**。那次 GREEN **不是**"闸门空转"，是**我瞄错了目标**——第三版把锚点改成整个
表达式才 RED。⇒ 纪律：变异红了要说清"红在哪条断言"，**绿了更要说清**"是闸门空还是我没打中"。

**门禁**：pytest **1694 passed / 3 skipped**（新增 3 条）；mypy **134 files / 0 errors**；
`npm run typecheck` **0**；`npm run smoke` **EXIT=0**（client-entry 69→**71**）；
`verify:commands` **22/22**；`e2e:materials` **9/9**。

**b9 台账现状**（方案未决第 12 条）：4 MEDIUM、LOW-1~6、INFO-3、INFO-5 **全部收口**；
剩 INFO-4（报告 ⚠ 不覆盖「依据」节——要动 `authority.render_evidence` 这第二个所有者，**新立项**）
与 INFO-6（模态通道没有 ORDER BY ⇒ 通道内顺序未定义，要先定"通道内该怎么排"）。


### 10.58 收掉 INFO-6：通道内"名次未定义"⇒ 权重不可复现（并把同族第二处一起钉住）

b9 台账里 INFO-6 是 step-55 顺手发现的：**模态通道（D）那条 SQL 完全没有 `ORDER BY`**。
本步收它，并发现**同族第二处**（通道 E），一并钉住。

**问题（为什么这不是"少了句 ORDER BY"的小事）**
`rank` 直接决定 `CHANNEL_WEIGHTS / (RRF_K + rank + 1)`。而**没有 `ORDER BY` 的 SELECT
返回次序是未定义的**——实践中它由访问路径/rowid 决定，所以"今天看起来稳定"只是**巧合**：
换规划器、加索引、VACUUM、甚至数据插入次序变了都可能让同一个查询给出**不同的权重分配**。
后果是双重的：① 答案**不可复现**（同一问题两次检索可能给出不同排序）；
② 这条行为**没法断言**（未定义的东西写不出稳定的期望值）。

**修法（与通道 A 的口径一致）**
- 通道 D（模态）：`ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id`
  ——未核验（NULL）沉底、已知状态按名排、最后用 id 兜底保证**全序**（同状态多行也确定）。
- 通道 E（法理要素，**同族、自查发现**）：`ORDER BY clause_revision_id`。
  ⚠ **诚实边界**：E **没有** JOIN `doc_meta`，所以这里只能给"**确定性**"，
  **给不了**"未核验沉底"那条偏好——要那条得改查询形状（加 JOIN），属更大的改动，
  已登记为待办，**不**在这一步夹带。

**测试（行为侧证据，且刻意让"不写 ORDER BY"排错）**
- 模态：**先插入未核验那一份**（自然/rowid 次序会把它排前）⇒ 只有真的写了排序且未核验沉底，
  已核验那份才会在前；顺带断言"同一查询两次给出同一序列"。
  ⚠ 用例里写明**判别力边界**：这条依赖 SQLite 的访问路径，规划器若改成从 `doc_meta` 驱动
  可能出现**假绿** ⇒ 真正的护栏是"语句里现在就写着 ORDER BY"。
- 法理要素：按 **id 倒序**插入（先 `c992` 再 `c991`）⇒ 真按 id 排序时返回顺序必然与插入顺序
  **相反**；不写 ORDER BY 会给插入顺序 ⇒ 红。

**变异证据（逐字节还原，`hybrid_engine.py` sha256 `333a4803…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| O1 | 去掉通道 D 的 ORDER BY | `test_modality_channel_ranks_verified_before_unverified` **RED** |
| O2 | 去掉通道 E 的 ORDER BY | `test_legal_element_channel_order_is_deterministic` **RED** |

⚠ 本步的变异驱动**新增了 `ast.parse` 自查**（step-56 那次把文件改成语法错误的教训）：
变异施加后先确认文件仍能解析，再跑用例——避免"红在收集期 error"被误读成"断言有效"。

**门禁**：pytest **1696 passed / 3 skipped**（新增 2 条）；mypy **134 files / 0 errors**
（本步只动 Python 与测试，未动客户端 ⇒ 无需重建产物、smoke 与 tsc 不受影响）。

**b9 台账现状**（方案未决第 12 条）：4 MEDIUM、LOW-1~6、INFO-3、INFO-5、INFO-6 **全部收口**；
只剩 INFO-4（报告 ⚠ 不覆盖「依据」节——要动 `authority.render_evidence` 这第二个所有者，
**新立项**）+ 本条新登记的待办（通道 E 的"未核验沉底"要加 JOIN）。


### 10.59 收 b10 的 MEDIUM-2：我自己把"很便宜"的判据改成了会读盘，端点却还留在 `async def`

承接 §10.54（给锚点判据加了"源文件字节"这一轴），本条是那一步的**副作用**——复核 b10 抓到的：

**问题**：`project_locator_summary()` 现在对**每份材料**流式 `sha256` 一次源文件（§10.54 加的
"源文件字节"轴），却被 `async def` 端点同步调用。uvicorn 是**单事件循环** ⇒ 几十份 PDF 的
磁盘读会把**整个引擎**卡住（期间别的请求一起等，GUI 看起来"死掉"）。
更刺眼的是：**同一个文件里的 `reverify` 恰恰为这个理由声明成了 `def`**，而它旁边这两条留在了
`async def`；两处"很便宜（PRAGMA + 比字符串）"的说明也没跟着改（`routes_materials.py` 与
`locator.py` 各一处）。⇒ 典型的"改了判据的代价，忘了改调用方的假设"。

**修法**：
- 两个端点（项目级总览、单份健康度）`async def` → **`def`**（Starlette 丢线程池）；
- 两处 docstring 改准：明确"**不是零 I/O**：每份材料一次流式 sha256，几十份 PDF 就是一次真实
  磁盘读"，并指向那条结构性判据；
- **闸门**：把两条路径加进 `TestSlowEndpointsAreDeclaredSync` 的参数化表
  （它原本已覆盖 `scan`/`collect`/`review`/`reverify`）——**这是 b10 这条 MEDIUM 的一半价值**：
  该类存在的理由就是"做同步重活的端点必须是 `def`"，而新端点漏了进表。

**变异证据（逐字节还原，`routes_materials.py` sha256 `5295629b…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| P1 | 项目级总览退回 `async def` | `test_declared_sync[.../projects/{project_id}/locators]` **RED**（另一条仍绿 ⇒ 参数化是精确的） |
| P2 | 单份健康度退回 `async def` | `test_declared_sync[.../{material_id}/locators]` **RED** |

**门禁**：pytest **1698 passed / 3 skipped**（参数化新增 2 例）；mypy **134 files / 0 errors**；
`npm run smoke` **EXIT=0**（本步未动客户端）。

**⚠ 仍开着的 b10 缺陷（台账已进方案未决第 13 条）**：
- **MEDIUM（PPT 宽度模型，比本条更严重）**：`_ems_x10` 用 `ord(ch) > 0x2E7F` 判全宽 ⇒
  General Punctuation（U+2000–U+206F：`——` `""` `''` `…`）整块被当 **0.5em**，而渲染实测是
  **1.000em** ⇒ 含这些标点的要点被**低估行数**、渲染时**裁字**：合成输入丢 42%，
  **产品路径**（18 份真实材料 → 报告 → pptx → PDF）丢 **98/252 汉字 = 39%**。
  **变异 G1（把这类标点改对）22 条用例全绿 ⇒ 这一类零覆盖。**
  另：本机字体下 `字`=1.020em、前缀 `· `=0.605em，**两处偏差恰好抵消**才让 38/39 临界点看起来对
  ——换字体就会漂（这条要写进 PPT 的诚实边界）。
- **LOW（`xmp`/`plaintext` 残余）**：移出隐藏列表后，它们**内部**的字面 `<script>`/`<style>`
  仍被整串剥掉，而浏览器 `innerText` **会显示**这些字符 ⇒ 仍丢可见正文（零覆盖）。
- **LOW（记录）**：§10.56 的表把 `A→B0` 写成"0 行"，实为 **5879 行 `std→law`**——我的探针
  根本没算 `A→B0`（它打印的是 `A→B`）。这个格子恰好把该节要立的"根因 = 上一区间 `\b`→枚举的
  回归"**抵消掉**了，须改。
- **LOW（措辞）**：`raw_path` 有、文件在磁盘、`content_hash=NULL` 时，`locator_health` 的
  `why` 说"源文件不在磁盘上"（文件明明在那儿）。当前不可达（两个入库口都写 `content_hash`），
  但那是公开 API 的合法状态，且恢复建议误导。
- **零闸门两条**：G3（删掉引擎 docstring 的端点索引 4 行 ⇒ 42 passed 全绿）、
  G4（面板把 `why` 退回写死 `''` ⇒ client-entry 69/69 绿）。
- **流程（第二次复发）**：复核期间主检出又前进了（1 个提交 + 两批未提交改动），b9 的 INFO-1
  同型。⇒ 规矩要硬化：**派复核前先冻结主检出**（或把区间端点写进每条命令，并要求复核方
  在报告里对比"开始/结束的 HEAD"）。

**另记 b10 独立确认的事实**（对"能不能真机用"很关键）：**生产库里根本没有 `material*` 表**
（45 张表里一张都没有）——材料建表那次提交在 `2026-09-17 19:33`，而活引擎 `19:14:53` 就起来了，
**早 18 分钟**。⇒ 材料平面**从未在真机跑过**（不只是路由 404）：引擎重启时
`init_schema()` 会把这些表建出来，所以"两道门"重启后仍然可用，但**第一次真机运行是未经检验的**，
第一次跑要有人看着（这也是 MEDIUM-1/2 的真实误报率与成本**现在测不出来**的原因）。


### 10.60 收 b10 的 MEDIUM-1：歧义宽度标点被当半角 ⇒ 产品路径**静默裁字**（39%）

**问题（b10 用渲染级证据报的）**：`_ems_x10` 只按 `ord(ch) > 0x2E7F` 分档 ⇒
General Punctuation（U+2000–206F：`——` `“”` `‘’` `…`）整块被当 **0.5 em**，
而它们是**中文排版里的全宽标点** ⇒ **低估行数** ⇒ 渲染器把多出来的部分**裁掉**。
b10 在**产品路径**上复现：18 份真实材料（标题含 `——`）→ 报告 → pptx → PDF，
只剩 **154/252 汉字（丢 39%）**；合成输入丢 42%。
更糟的是它证明这一类**零覆盖**：变异 G1（把这类标点改对）**22 条用例全绿**。

**我自己先量了一遍，结果与报告不完全一致——这很关键**（`var/tmp/probe-step59-charwidth.py`）：
本机纯标点行量到 `—` **0.921**、`“` **0.434**、`…` **0.706**、`’` **0.265** em，
而 b10 在 **CJK 上下文**里量到 **1.000**。两者都真实：**歧义宽度字符的实测宽度随上下文/字体漂**
（中文字体里排全宽）。⇒ 取值规则不是"精密测量"，而是**取宽的那个**：
高估行数 ⇒ 多续一页 ⇒ 超限会**写明丢了多少条**（可见、可处置）；
低估 ⇒ **静默裁字**（不可见）。P1 下前者可接受，后者不可接受。

**修法**：`_ems_x10` 加一档 `_WIDE_PUNCT = "—‘’“”…"`（**取宽**，注释里写明"这是保守取值、
不是精密测量"以及两种实测量值）；**实测接近半角的不收**（`–` 0.514、`·` 0.252、`±` 0.514、
`°` 0.338）——把它们也当全宽会把"38 字一行"这个**渲染实测钉住的临界点**改错、白多拆页。

**验证**：
- 单测：`—`×39 ⇒ 2 行（修前 1 行）、×38 ⇒ 1 行（边界与汉字同款）；整组每个字符都钉 38/39；
  混排 `字`×37+`——` ⇒ 2 行（修前 1 行 ⇒ **正是被裁字的那种要点**）；
  **反向对照**：`字`×38 仍 1 行、`–`×38 仍 1 行（不许把半角的也收进来）。
- **渲染级产品路径验收**（`var/tmp/probe-step59-render.py`，等价 b10 的复现形状）：
  18 条 × （37 汉字 + `——`）= 期望 666 字 ⇒ PDF 全篇提取 **666 字，完整**，
  2 个正文页各 333 字 ⇒ **续页而不是裁字**。
- 变异 **Q1**（去掉 `_WIDE_PUNCT` 那一档）⇒ 新用例 **RED**（1 failed / 23 passed），
  逐字节还原后 24 passed。

**门禁**：pytest **1700 passed / 3 skipped**（新增 2 条）；mypy **134 files / 0 errors**；
`npm run smoke` **EXIT=0**（本步未动客户端）。

**⚠ 诚实边界（PPT 宽度模型的两处已知偏差，b10 指出、本步登记不改）**：
① 本机字体下 `字` = **1.020 em**、前缀 `· ` = **0.605 em**（不是模型里的 1.0/1.0）——
两处偏差**恰好部分抵消**才让 38/39 临界点看起来对；**换模板/字体（业主的 WPS/PowerPoint）
必须重测**。② `NARROW_CHAR_WEIGHT=0.5` 对 ASCII 实测 0.578 是**偏保守**（高估行数）方向，保留。

---

### 10.60 附：复核 b11（step-56，`aa735b1`）的结论与本步一并登记

b11 **四条声称全部 CONFIRMED、零 REFUTED**，且它用**父/子对照**做的证据比我的自述更强：
父树（`5b8cb04`）上 `_locator_status=unknown` + 报告出「⚠锚点未验证」+ warning 说"未经验证"
（= 把工具崩溃说成材料未验证）；子树换成 `health_error` + 「工具缺陷」warning、双向通道都有标记；
总览那条父树**端点 500**、子树 200 且好材料结论不变；面板分支它**自建了 jsdom 真实渲染用例**，
把条件改 false 后标记**从 DOM 消失**（⇒ 该分支承重）；`tsc` 拦 union 缺项也独立重做成功。

**它新报的 5 条 LOW + 1 条 INFO（全部登记，待下一步修）**：
- **b11-LOW-3（最有价值，属"闸门空"）**：离线护栏对**交付产物**只查"文案在场"——
  变异 M4 只改 `plugin/client.js`（让条件永不成立、tsx 不动）⇒ **`npm run smoke` 71/71 全绿**，
  而交付界面上那个标记**再也不会出现**。⇒ 要断言**产物里的条件**，或把渲染用例收进 smoke。
- **b11-LOW-4**：union 非穷尽（M5b：加一个没人渲染的成员 ⇒ `tsc` **GREEN 0**）⇒ 将来加状态
  忘了加分支不会编译报错。⇒ 加 `never` 型穷尽性断言。
- **b11-LOW-1**：`_locator_why` **只写不读**（全仓 2 处写、0 处读）⇒ 报告从不把失败原因说出来，
  而面板会说 ⇒ 两通道不对称（建议拼进 `health_error` 的 warning）。
- **b11-LOW-2**：warning 作用域不对称（`_unknown` 只扫 approved，`_health_error` 扫三态）
  ⇒ 待评审的会崩材料会报警、待评审的真 unknown 不报。
- **b11-LOW-5**：`no_locators` 的"没有派生文本"把**第三种成因**（入库早于该列）说进主句
  （括号里点了替代因，未下错结论）——仅措辞。
- **b11-INFO-1（非本提交引入）**：`anchorNote` 是**死状态**（声明 + 2 处写、0 处读）
  ⇒ `locator.py` 的 `note`（含本步新增文案）从不进 UI；好在面板那条红分支独立承载同样信息。

**b11 的两条方法性提醒（我采纳）**：
① 我记录的"逐字节还原 sha256"是 **git blob（LF）哈希**（本检出工作树是 CRLF ⇒ 工作树哈希不同，
如 `58547b1a…`）——记录里要注明，否则后代复算会对不上；
② 它用 `KS_E2E_NO_RELOAD=1` 跑 e2e 时面板**未发任何 `/ks/materials` 请求** ⇒ C1/C2 **空过**，
强度不及我那次 ⇒ 提醒：**e2e 的"通过"要同时报它实际发了哪些请求**（我已把它写进脚本的诊断输出，
但"空过"这件事要在结论里说）。


### 10.61 收 b11 的 LOW-3：离线 UI 护栏原来是**空闸门**（只查"文案在场"）

**问题（复核 b11 用变异证明的）**：`smoke-client-entry.mjs` 对**交付产物**只断言"那句文案还在"。
于是有一个**假绿**形状——**只改产物**（把分支条件改成永不成立），`.tsx` 一个字节不动：
文案还在 ⇒ 断言全绿（b11 实测 **71/71 GREEN**），而**交付到界面上的那个标记再也不会出现**。
反向也一样：改了 `.tsx` 忘了重新构建 ⇒ 产物是旧的 ⇒ 也全绿。
两种都是"门禁说没事、用户看不到东西"——而这一节本来就是为了防"改 .tsx 忘了 build 是静默失效"。

**修法（两条，都是结构性的）**：
1. `build-client.mjs` 加 `KS_CLIENT_OUT` 覆盖（默认仍是 `plugin/client.js`）——
   让冒烟能**从源码现构建一份到临时文件**，而**不覆盖**被跟踪的产物。
2. `smoke-client-entry.mjs` 加一节"**产物 ↔ 源码一致性**"：对 5 个关键标记
   （三条 ⚠ 分支的**条件** `status === "stale"|"unknown"|"health_error"` +
   `health_error` 的提示文案 + "不代表已经坏了"），在**两份产物**里各查一遍并断言一致：
   · 交付的 `client.js` 必须有（那才是发出去的东西）；· 现构建的那份也必须有（源码真的这么写）；
   · 两者**必须一致**（不一致 = 产物陈旧或被改过）。
   断言从 71 条涨到 **81 条**。

**变异证据（两种假绿形状各一次，均逐字节还原）**：
| 变异 | 内容 | 修前 | 修后 |
|---|---|---|---|
| **R1**（= b11 的 M4） | **只改产物** `client.js`：`=== "health_error"` → `=== "__never__"`，tsx 不动 | b11 实测 **GREEN 71/71** | **RED**：`交付产物里有health_error 分支的条件` FAIL + 同步断言 FAIL（`现构建含=true 交付产物含=false`），exit 1 |
| **R2** | **只改源码** 把 `status === 'stale'` 改成 `status === 'stale_'`，**不重建** | GREEN（产物仍是旧的） | **RED**：同步断言 FAIL（`现构建含=false 交付产物含=true`）——⚠ 且**只有**这一条断言响，正好证明同步机制在独立承重 |

还原后 `client.js` / `KsMaterialsPanel.tsx` 均 **byte-identical**，冒烟回到 **81/81**。

**⚠ 诚实边界（写进冒烟注释与台账，不假装关掉）**：这仍是**字符串级**检查。它能挡
①"删掉/改掉条件"②"忘了重建"，**挡不住**③"条件后面偷偷加 `&& false`"——那种要**渲染级**用例
（b11 用 **jsdom + 真组件 + 真 api.ts + 打桩 fetch** 建过一份，`render-b11.mjs` 在
`var/tmp/verify-b11-artifacts/`，**不在仓里**）。收编它需要先决定**依赖策略**
（本仓 `plugin/` 没有 jsdom；`react-dom` 只在**根** `node_modules` 里有）——
属"要不要为门禁引入新依赖"的决策，**留给业主**，不在这步私自装依赖。

**门禁**：pytest **1700 passed / 3 skipped**、mypy（本步未动 Python，上一步 134/0 不变）、
`npm run typecheck` **0**、`npm run smoke` **EXIT=0**（client-entry **71 → 81**）。
⚠ 本步**没有**重新构建 `client.js`（改的是构建脚本的"输出到哪"，默认路径与产物内容都不变）
⇒ 工作区只动了两个 `scripts/*.mjs`，`git status` 可证。


### 10.62 收 b11 的 LOW-4：状态取值域增长了，界面却不会报错（改成编译期穷尽）

**问题（复核 b11 的变异 M5b 证明的）**：锚点标记过去是**三串 `status === 'x' && <p/>`**。
后端的状态取值域**已经长过两次**（`unknown` → 加 `no_locators` → 加 `health_error`），
而**新增一个取值却忘了加分支时什么都不会报**：那一类材料在界面上**一个标记都没有**，
读起来像"全都健康"。b11 往 union 里加一个没人渲染的成员 ⇒ **`tsc` 仍 GREEN 0**。

**修法**：把标记收成**唯一出口** `AnchorMark`：`switch` + `default: return assertNever(status)`。
`assertNever(status: never)` 让"union 里多出一个没人处理的成员"变成**类型不匹配** ⇒
`npm run typecheck` **直接红**（不是运行时静默）。
`undefined` / `ok` / `no_locators` 三个 case 明确返回 `null`（不加噪声），
`stale` / `unknown` / `health_error` 各自一块（理由**照抄后端 `why`**，界面不解释 status）。

**变异证据（全部逐字节还原）**：
| 变异 | 内容 | 修前 | 修后 |
|---|---|---|---|
| **M5b**（= b11 的 LOW-4） | 往 `KsLocatorHealth['status']` 加一个**没人渲染**的成员 | `tsc` **GREEN 0** | **RED**：`TS2345: Argument of type '"future_status"' is not assignable to parameter of type 'never'`（KsMaterialsPanel.tsx:153），exit 2 |
| **R1**（step-60 的闸门在重构后仍有效） | **只改产物**：`case "health_error":` → `case "__never__":` | — | 冒烟 **RED**（"交付产物里有 case" + 同步断言双红，exit 1） |
| **R2** | **只改源码**：`case 'stale':` → `'stale_x'`，**不重建** | — | 冒烟 **RED**（只有同步断言响：`现构建含=false 交付产物含=true`） |

**顺带处理的重构涟漪（不藏）**：
- `client.js`（**被跟踪的产物**）随源码重建 —— 这本来就是"改 .tsx 必须重建"的纪律；
- step-60 那节的**关键标记换成 switch 的 case**（`case "stale":` 等），源码侧断言从
  `status === 'health_error'` 改成 `case 'health_error':`，并**新增一条**"源码里有穷尽性断言"
  （`assertNever(` + `default: return assertNever(`）⇒ 断言 **81 → 82**。

**门禁**：pytest **1700 passed / 3 skipped**、`npm run typecheck` **0**、
`npm run smoke` **EXIT=0**（client-entry **82/82**）。

**仍未做（b11 台账）**：LOW-1（`_locator_why` 只写不读 ⇒ 报告从不把失败原因说出来，面板会说）、
LOW-2（warning 作用域不对称：`_unknown` 只扫 approved、`_health_error` 扫三态）、
LOW-5（`no_locators` 把"入库早于该列"说进主句）、INFO-1（`anchorNote` 死状态）
——以及 b10 的 LOW-1/2/3 与 G3/G4。


### 10.63 收 b11 的 LOW-1/LOW-2/LOW-5 与 b10 的 LOW-3：报告与面板"说同一件事"的四条对齐

四条都是**同一句判据在两处说法不一致**（报告 vs 面板 vs 事实），本步一起对齐。

**b11-LOW-1（`_locator_why` 只写不读）**：`_attach_locator_status` 会把异常原因写进
`_locator_why`，但报告**从来不读它**（全仓 2 处写、0 处读）⇒ 面板会把异常说出来、报告不说，
两个通道不对称。修法：`health_error` 那条 warning **带上原因**（去重、最多列 3 条，
超出打 `…`），并加测试断言 warning 里含异常文本。

**b11-LOW-2（warning 作用域不对称）**：`_unknown` 只扫**已批准**、`_health_error` 扫**三态**。
这不是 bug 而是**故意的**——只有已批准才承重，待评审的"未经验证"不影响结论；
而"判据崩溃"是**我们自己的**失败，无论评审状态都该被看见。
⇒ **保留行为、把理由写在代码里、并在 warning 文本里明写"含待评审/已拒绝的在内"**，
不让读者去猜这条为什么比上一条宽。

**b11-LOW-5（`no_locators` 主句越权）**："入库时**没有派生文本**" 是把**记录**说成了**事实**
（第三种成因是"入库早于该列，那时有文本也不会记"）。修法：主句改成"没有派生文本**记录**"，
两种可能都放进括号。

**b10-LOW-3（`content_hash` 为空时 `why` 说谎）**：`raw_path` 有、文件**在磁盘上**、
但 `content_hash` 为空时，旧写法与"文件不在"**共用同一句**"源文件不在磁盘上"
⇒ 文件明明在那儿，读者会去翻目录，而恢复建议（"把源文件放回原位"）对它**完全没用**。
修法：把两种"判不了"分开——① 文件不在（原话保留）；② 文件在、但没登记字节哈希
（新话：说清"判不出有没有被换过"、**不是 ok**、恢复要重新入库或走 reverify）。
两种都仍是 `unknown`（**不假装 ok**）。

**变异证据（逐字节还原，`research_report.py` `d81a5238…` / `locator.py` `dd4561cc…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| **S1b** | 把 `_detail`（原因拼接）改成恒空 | `test_health_crash_is_not_reported_as_unverified` **RED** |
| **S2** | 把 `content_hash` 那条分支改成 `if False` | `test_missing_content_hash_is_not_a_missing_file` **RED** |

⚠ **S1 第一版是"没打中的变异"，如实记**：我把 `_detail = ""` 改成 `_detail = ""  # 注释` ——
**只加了个注释**，行为分毫未变 ⇒ 测试当然 GREEN。这不是"闸门空"，是**我瞄错了目标**
（与 §10.57 的 N2 同型，本仓已第三次）。⇒ 纪律再强调一次：**变异 GREEN 时必须先问
"我改的东西真的会改变行为吗"**，再说闸门的事。

**门禁**：pytest **1701 passed / 3 skipped**（新增 1 条用例 + 2 条断言）；mypy **134 files / 0 errors**；
本步未动客户端（`client.js`/TSX/smoke 均未改）⇒ `tsc` 与 smoke 不受影响。

**b11/b10 台账现状**：b11 的 LOW-1/2/3/4/5 与 b10 的 MEDIUM-1/2、LOW-3 已收（§10.59/§10.60/§10.61/§10.62/本条）；
**仍开着**：b10-LOW-1（`xmp`/`plaintext` 内部字面 `<script>` 仍被剥）、b10-LOW-2（§10.56 表 `A→B0`
记成"0 行"实为 5879 行）、b10-G3/G4（两处零闸门）、b11-INFO-1（`anchorNote` 死状态）、
INFO-4（报告 ⚠ 不覆盖「依据」节 ⇒ 新立项）、通道 E 的"未核验沉底"（要加 JOIN）。


### 10.64 收 b10 的 LOW-1：raw text 元素里的字面 `<script>` 是**文字**，不是标签（我们仍在删可见正文）

**问题**：§10.55 把 `xmp`/`plaintext` 从"内容不进正文"的名单里移出（它们是**可见文字**），
但 `_strip_script_style` **在那之前**就把 script/style 整串剥掉了 ⇒
`<xmp><script>var x=1;</script></xmp>` 里那段**字面文本**照样被删 ⇒ **仍在丢可见正文**。
复核 b10 实测：浏览器 `innerText` 对这段是**会显示**的（`xmp` 原样字面显示）——
也就是说我上一轮只改了"名单"，没改"谁先动手"。
⇒ 教训一句话：**修"某个元素的内容要不要留"时，必须检查在这之前有没有别的步骤已经把它删了。**

**修法**：新增 `_inside_raw_text(s, at)`——判 `at` 是否落在 **raw text / RCDATA** 元素内部
（`xmp` / `plaintext` / `textarea` / `title`）；`plaintext` 永不闭合（其后全是 raw text）。
`_strip_script_style` 的循环里，匹配点落在其中就**跳过**（与既有的第 4 条"未闭合标签内部"
同款做法）。`textarea`/`title` 一并收：它们的内容是**我们有意保留**的（表单默认值/页面标题），
在里面剥 script 同样是在删我们决定要留的字。
⚠ 诚实登记：这个判据每遇一个 script/style 匹配就回扫一遍前缀（O(n·k)）；页面上 script/style
通常个位数 ⇒ 可接受；真要快得写**单遍状态机**（未立项）。

**测试（成对，方向两边都钉）**：
- **正向**：`<xmp><script>var LEAK=1;</script>可见甲</xmp>` ⇒ `var LEAK=1;` **必须在**
  （浏览器会显示它），且前后正文都在；`<plaintext>` 与 `<textarea>` 变体同理。
- **反向对照**：元素**外面**的 `<script>`/`<style>` 仍必须被剥（含**未闭合**的真 script）
  ——没有这一条，"raw text 里跳过"就可能被写成"到处都跳过"，等于把守卫反过来。

**变异证据（逐字节还原，`text_utils.py` sha256 `d388d2f0…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| **T1** | 把 `_inside_raw_text(...)` 从跳过条件里去掉 | 正向用例 **RED**，**反向对照仍绿**（1 failed / 1 passed）⇒ 判别力精确 |

**门禁**：pytest **1703 passed / 3 skipped**（新增 2 条）；mypy **134 files / 0 errors**；
本步只动 `text_utils.py` 与测试 ⇒ `tsc`/smoke 不受影响。

**台账现状**：b10 只剩 **LOW-2**（§10.56 的表把 `A→B0` 记成"0 行"，实为 5879 行）与
**G3/G4**（两处零闸门）；b11 只剩 **INFO-1**（`anchorNote` 死状态）。
再往后是 INFO-4（报告 ⚠ 不覆盖「依据」节 ⇒ 新立项）与通道 E 的"未核验沉底"（要加 JOIN）。


### 10.65 收尾：两处**零闸门**补上、一处记录改错、以及"后端的说明从没上过屏"

前四位复核报的缺陷到这一步基本清完；本条收 b10 的 **G3/G4**、**LOW-2** 与 b11 的 **INFO-1**。

**b10-G3（端点索引零闸门）**：§10.56 补全了 `routes_materials.py` docstring 的端点索引，
但**没有闸门**——b10 实测把补上的 4 行删掉，测试套件**全绿**（42 passed）。
而那份索引就是这一层的"地图"（下一轮接线/复核照它找端点）。
⇒ 新增 `TestEndpointIndexMatchesReality`：从 docstring 里抽出 `(方法, 路径)` 集合，
与 `app.routes` 里真实注册的 `/api/v1/materials*` **逐条相等**；
⚠ 占位名要归一（索引写简写 `{pid}`/`{mid}`，代码是 `{project_id}`/`{material_id}` ⇒ 统一成 `{}`）。
不等时把"只在索引里/只在路由里"两边都打出来，便于定位。

**b10-G4（面板 `why` 接线零闸门）**：把面板里 `attention → why` 的映射退回写死 `why: ''`，
冒烟仍全绿 ⇒ 界面上再也说不出"为什么需要复算"。⇒ 冒烟新增两条**钉接线本身**的断言
（`for (const a of s.attention)` + `why[a.material_id] = a.why`），不是钉某句文案。

**b11-INFO-1（`anchorNote` 是死状态）**：面板把后端 `locator.py` 的 `note` 存进状态却**从不渲染**
（2 处写、0 处读）⇒ 后端那句"`unknown` 包含哪几类、`health_error` 不是健康状态"的解释
**从来没上过屏**——而它正是"别把不知道当成没问题"那件事的说明。
⇒ 现在渲染出来（选了项目、拿到总览之后显示），并加断言钉"不是只存不读"。

**b10-LOW-2（记录改错）**：§10.56 的表把 `A→B0` 写成 **"0 行"**，那是把 **`A→B`** 的结果
填错了格子（我的探针**根本没算 `A→B0`**）。**正确值：A→B0 = 5879 行，方向全部 `std → law`**
（`\b` 对 `GBZ／T` 成立，换成枚举又漏了 `／` ⇒ 这 5879 行掉进法规树）。
这个格子**恰好抵消了该节要立的结论**（"根因 = 上一区间 `\b`→枚举的回归"）——
写成 0 行，读者会以为那次改写**没有影响**。已在表下加更正块（两处都记：A→B0 = 5879 `std→law`、
B0→B = 5879 `law→std`；中间的 `A→B = 0` 只说明"最终修回来了"，**不是**"没坏过"）。

**变异证据（逐字节还原，`KsMaterialsPanel.tsx` 还原后哈希一致）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| **U1**（G4 形状） | 删掉 `attention → why` 的映射 | 冒烟 **RED**（只红在新断言那一条） |
| **U2**（INFO-1 形状） | 把 `anchorNote` 的渲染条件改成 `false &&` | 冒烟 **RED**（同上） |

**门禁**：pytest **1704 passed / 3 skipped**（新增 1 条）；mypy **134 files / 0 errors**；
`npm run typecheck` **0**；`npm run smoke` **EXIT=0**（client-entry **82 → 84**）。
`client.js` 随 TSX 重建（被跟踪产物）。

**台账现状**：**b10 的四条与 b11 的五条 + INFO-1 全部收口**。**只剩**：
INFO-4（报告 ⚠ 不覆盖「依据」节 —— 要动 `authority.render_evidence` 这**第二个所有者** ⇒ 新立项）
与通道 E 的"未核验沉底"（要给它加 JOIN `doc_meta`）。
其余都是**需要业主拍板**的事（两道门重启 / B-3 / `NO_PROXY` / 采集预算 / 是否引入 jsdom）。


### 10.66 收尾第二项：通道 E 补齐"未核验沉底"（此前只能给确定性，给不了偏好）

**背景**：§10.58 给通道 E（法理要素召回）补了 `ORDER BY clause_revision_id`（**确定性**），
但当时如实登记了一条边界——**E 没有 JOIN `doc_meta`，所以给不了"未核验沉底"那条偏好**。
本步把它补齐：`LEFT JOIN doc_meta dm ON dm.doc_id = cr.doc_id`，
排序口径与通道 A/D **完全对齐**：`(dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id`。

**为什么是 `LEFT JOIN` 而不是 `JOIN`（这一条比排序本身更重要）**：
本项目**已经栽过两次**"未核验条款被静默排除"——§10.44/§10.49 那次是 `NOT IN (…)` 对 NULL
求值为 NULL；这一次若用**内连接**，缺 `doc_meta` 行的条款会在**更前面**被丢掉，
**症状一模一样**（行少了、没人报错、答案悄悄变窄）。
`LEFT JOIN` 保证**绝不因为元数据缺行而丢条款**；缺行时 `dm.legal_status` 为 NULL
⇒ 正好落进"未核验"那一档并**沉底**，语义也对。

**测试（构造让"不写 ORDER BY"与"只按 id"都排错）**：
**先插入未核验那份、且它的 id 更小**（`c990` < `c991`）⇒ 自然顺序与"按 id"顺序都把未核验排前；
只有真的"状态优先、再 id"排，已核验的 `c991` 才会在前。

**变异证据（逐字节还原，`hybrid_engine.py` sha256 `c28d9be5…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| **V1** | 排序退回 `ORDER BY cr.clause_revision_id`（丢掉状态偏好） | 新用例 **RED**，而"确定性"那条**仍绿**（1 failed / 2 passed）⇒ 判别力精确 |
| **V2** | 去掉 `LEFT JOIN`（只留 ORDER BY 里的 `dm.`） | **`sqlite3.OperationalError`** ⇒ 3 条红 ⇒ 证明那个 JOIN 是这条排序的**前提** |

**门禁**：pytest **1705 passed / 3 skipped**（新增 1 条）；mypy **134 files / 0 errors**；
本步只动检索层与测试 ⇒ `tsc`/smoke 不受影响。

**台账**：通道 E 这一项**收口**。方案 §12 里"我自己能推进"的只剩 **INFO-4**——
报告里的 ⚠ 只覆盖**材料清单**、不覆盖「**三、依据**」节（引用真正出现的地方）；
它要动 `authority.render_evidence`（**第二个所有者**），已按"**新立项**"登记，**不夹带**。
其余全部是**需要业主拍板**的事（两道门重启 / B-3 / `NO_PROXY` / 采集预算 / 是否引入 jsdom）。



### 10.67 收 b11 的 INFO-4（"改准理由"那一半）：把"标记在哪一节"说清楚，并把增强写成可执行的立项

复核 b11 的 INFO-4 指出：`_attach_locator_status` 的 docstring 写"报告要能**引用前校验**"，
但实际标出来的位置是**材料清单行**（`_material_line`），而**真正的引用在「三、依据」节**——
那一节由 `materials/authority.py::render_evidence()` 渲染，**这一层不碰它**。
b11 的措辞也留了余地："建议把那句理由改准，**或**把 `_locator_status` 接进 `render_evidence()`"。

本步做**前者**（改准），并把后者写成**可执行的立项**：

**改准**：docstring 现在明说"**本函数只保证'材料清单里看得见'，不保证'引用点上看得见'**"，
并指出要放到引用点上得让 `render_evidence` 认识锚点状态（跨所有者）。
顺带把"**便宜**判据"改成"不重解析但**会读一次源文件**"（§10.54 之后它已经不是零 I/O 了，
这句与 §10.59 的端点声明同源）。

**为什么增强不当场做（理由写进台账）**：查了 `render_evidence` 的实现——它的 `line()`
**本来就有行内状态标记**（`⛔你声明它为准绳…未按准则承重`），所以"加一个锚点标记"在
**职责上是通的**、改动也不大（把报告已经算好的 status map 传进去、查表）。
**但**它的输出**同时喂给答案链的提示词** ⇒ 加标记会**改变提示词字节**，而本项目有一条硬保证：
**不给 `params.material_project_id` 时提示词逐字不变**（B-5 的回归保证）。
⇒ 这是"跨所有者 + 动提示词"的事，必须连带那条保证的测试一起设计（空 map / 未绑定必须零变化），
**属新立项，不夹带**。验收方式一并写明：真机报告里「三、依据」的引用行上要能看到 ⚠。

**门禁**：`tests/test_research_report.py` **24 条**通过；mypy **134 files / 0 errors**。
本步是**纯记录/文档修正**（无行为变化）⇒ **不新增测试，也不假装有闸门**。
⚠ 诚实边界：本步**没有**写"边界测试"去钉"依据节目前没有 ⚠"——那种断言很容易变成**空洞的**
（它钉的是"今天还没做"，不是任何契约），而本项目最近几轮反复抓的正是这类断言。
真正的护栏是立项里的**验收条件**（真机报告里看到标记）。



### 10.68 收 b11 的 LOW-3 后半句：把渲染用例**零依赖**地收进仓（不再只到字符串级）

b11 的 LOW-3 说：离线护栏对**交付产物**只做"文案在场"检查，建议"断言产物里的条件，
**或把我那份渲染用例收进 smoke**"。前者在 §10.61/§10.62 做了（产物↔源码一致 + 编译期穷尽），
但它仍**只是字符串级**：条件在、文案在，**渲染出来是空**也照样全绿。
b11 那份用 **jsdom**（本仓 `plugin/` 没装 ⇒ 要引依赖，属业主决策）。

**本步用零依赖的等价做法把它真正做出来**：`react-dom/server` 的 `renderToStaticMarkup`
（**静态渲染不需要 DOM**），react/react-dom 用**仓库根** `node_modules` 里已有的 18.3.1；
面板把 `AnchorMark` 导出，冒烟用 esbuild 把 TSX 打成 Node 可 import 的 ESM 后**真渲染**它。

**新增 `plugin/scripts/smoke-anchor-mark.mjs`（15 条断言，已进 `npm run smoke` 链，18 → 19 段）**：
- `undefined` / `ok` / `no_locators` ⇒ **渲染成空**（不加噪声，这是刻意的）；
- `stale` ⇒ 「引用锚点需复算」+ **后端 why 原样** + "不代表已经坏了"；
- `unknown` ⇒ 「引用锚点未验证」+ why + "不等于有问题"；
- `health_error` ⇒ 「锚点健康度算不出来」+ **`role="alert"`** + why + "工具缺陷/不代表材料有问题"；
- **`why` 缺失时仍要渲染标记**（只换成"后端未给原因"）——不能因为没原因就不报。

⚠ 两个踩过的坑（都写进脚本注释）：
① 临时产物**必须落在 `plugin/` 里**（不是 `%TEMP%`）：bundle 里 `import 'react'` 是 **external**，
Node 要沿**它自己的路径**往上找 `node_modules`，放 TEMP 树上直接 `ERR_MODULE_NOT_FOUND`（第一版就是这样）；
② **根 `node_modules` 缺 react/react-dom 时明确 FAIL**（附可操作的修法），**不做静默 SKIP**
——门禁缺依赖应当是可见的，而不是悄悄消失（这正是 b11 抓的那类"闸门空"）。

**变异证据（这一条是本步最有价值的部分）**：
| 变异 | 内容 | 渲染级冒烟 | 字符串级冒烟 |
|---|---|---|---|
| **W1** | 把 `const why = props.why \|\| '（后端未给原因）'` 改成**界面自己编一句原因**（JSX 文案一字未动） | **11/15 RED**（4 条"why 必须原样"红，exit 1） | **84/84 全绿** |

⇒ 这是"渲染级闸门带来新东西"的**实测证明**：同一处行为退化，字符串级**看不见**，渲染级看得见。
（也正是 b11-LOW-3 的实质：文案在场 ≠ 界面对。）逐字节还原（`KsMaterialsPanel.tsx` 哈希一致）。

**门禁**：pytest **1705 passed / 3 skipped**；mypy **134 files / 0 errors**；`npm run typecheck` **0**；
`npm run smoke` **EXIT=0（19 段）**。`client.js` 重建后与被跟踪产物**逐字节相同**
（加一个 `export` 不改变 CJS 包裹体的发射结果）⇒ 产物↔源码一致那条闸门仍然绿。

**诚实边界**：这条冒烟覆盖的是**标记组件本身**（逐档渲染），**不是**整块面板的端到端渲染
（那还要 DOM/事件/effect ⇒ 才需要 jsdom 或浏览器；真机那条路已由 `e2e:materials` 覆盖到
"面板挂载 + 不炸 + 失败如实说"）。两句话都写进脚本头注，免得后人以为它替掉了 jsdom 方案的**全部**价值。



### 10.69 收 INFO-4 **真身**：锚点标记上到"引用行"，而且**不动提示词一个字节**

§10.67 我把 INFO-4 的增强登记为"需要立项"，理由是"`render_evidence` 的输出同时喂给提示词
⇒ 加标记会改提示词字节，而 B-5 有'未绑定时提示词逐字不变'的硬保证"。
**本轮复查代码后发现那个理由不成立**：`render_evidence` 有**两个调用方**——
`ks_answer.py:683`（答案链提示词）与 `research_report.py:262`（报告的「三、依据」节）。
⇒ 只要**让调用方自己决定**（可选参数 + 只有报告传），提示词那条路径**一个字节都不变**。
**我把"功能"与"提示词风险"当成一件事了，其实解耦就行。**

**改法（三处，都很小）**：
1. `locator.STATUS_MARKS`：三个短标记（`⚠锚点需复算` / `⚠锚点未验证` / `⚠锚点健康度算不出来`）
   的**唯一所有者**（放这儿因为它是状态词表的定义处）。`ok`/`no_locators` **故意不在**里面。
   报告的材料行（`_material_line`）与证据行（`render_evidence`）**都从它取**
   ——顺手消掉了"两处各写一份、慢慢漂开"的隐患（同一次 INFO-4 的另一半）。
2. `authority.render_evidence(assembled, locator_status=None)`：传了 map 才给引用行加标记。
3. `research_report` 传 map（它本来就为每份材料算好了 `_locator_status`）。

**验收（INFO-4 当初写下的条件就是这条）**：报告「三、依据」的引用行
（`- [[m:0]] …#mat_…`）上**看得到** `⚠锚点未验证`；而**清单行**上也仍然有（不是"挪过去"）。

**P1 保证被机械钉住**（比功能本身重要）：`test_without_the_map_the_rendering_is_unchanged`
断言"不传 map 时渲染里**一个'锚点'都不许出现**"，并且"传 map 的结果 = 不传的结果 + 那一段标记"
（逐字替换回来必须相等）⇒ 只要"谁要标记谁传 map"，B-5 那条保证**不靠人记得**。

**变异证据（逐字节还原，`research_report.py` `256d880d…` / `authority.py` `c7b81ab4…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| **X1** | 报告**不**传 map（等于"没接线"） | 验收用例 **RED**（另 2 条仍绿）⇒ 接线真承重 |
| **X2** | 渲染器**忽略** map | 2 条 **RED**（含"传了 map 必须有标记"） |

**门禁**：pytest **1708 passed / 3 skipped**（新增 3 条）；mypy **134 files / 0 errors**；
`npm run smoke` **EXIT=0（19 段）**。本步未动客户端。

⇒ **复核 b9/b10/b11 报的全部条目现在都收口了**（含这条原以为要立项的 INFO-4）。
方案 §12 的"已知未决"里，只剩**需要业主拍板**的运行/产品决策，以及
"业主模板/WPS 下的 PPT 渲染阈值重测"这类**只能在您环境里做**的事。



### 10.70 收 b12 的 MEDIUM-1：我上一轮**把守卫打开了**（真脚本漏进材料正文）——回归修复

复核 b12 判定 step-63 的 raw text 改动 **PARTLY**：正向修法**对**（真浏览器 CDP ground truth 证实
`xmp`/`plaintext` 里的字面 script 是**可见文字**，该留），**但 `_inside_raw_text` 太朴素，
两种形状下把守卫打开了**——而且这两种在**修前不漏、现在漏**，是**本步引入的回归**：

| 形状 | 现象 | 浏览器裁决 |
|---|---|---|
| ① 属性值里的 `<xmp>` | `<p title="<xmp>">前</p><script>var ATTR=1;</script><p>后</p>` ⇒ 我们输出含 `var ATTR=1;` | 那个 `<xmp>` 只是 `title` 的**值** ⇒ 后面是**真脚本**（`scriptEls=1`） |
| ② raw text 元素不嵌套 | `<textarea><xmp></textarea><script>var NEST=2;</script>` ⇒ 输出含 `var NEST=2;` | `<textarea>` 一直吃到 `</textarea>`，中间 `<xmp>` 是**文字** ⇒ 后面是**真脚本** |

**根因（两条，正好对应我第一版代码的两个疏忽）**：
① 回扫时**没检查候选边界自己是不是真标签**（属性值里的 `<xmp>` 也会被算成"进入 xmp"）；
② 开始标签**无条件覆盖** `open_tag` ⇒ `<textarea>` 里的 `<xmp>` 把状态改成 `xmp`，
于是 `</textarea>` 关不掉它（raw text 元素**不能嵌套**，先开的那个一直管到自己那个结束标签）。

**修法（各一行）**：
① 每个候选边界先过 `_inside_unclosed_tag(s, 0, m.start())`（与函数里第 4 条**同一套判据**，
   不为这件事再写第二个"这算不算标签"的判断）；
② 只有 `open_tag is None` 时开始标签才生效（已在 raw text 里 ⇒ 那个开始标签是**文字**）。

**测试（补上复核指出的零覆盖形状，成对）**：
`test_raw_text_guard_is_not_opened_by_attribute_values_or_nesting` —— 两种形状**都不许**泄漏，
并附**正向对照**（`<xmp><script>var KEEP=1;</script></xmp>` 的 `KEEP=1` **必须留着**），
免得"为堵上面两个把正路堵死"。

**变异证据（逐字节还原，`text_utils.py` sha256 `e89a18f9…`）**：
| 变异 | 内容 | 结果 |
|---|---|---|
| **Y1** | 去掉属性值判据（`if _inside_unclosed_tag(...): continue`） | 该用例 **RED** |
| **Y2** | 开始标签恢复无条件覆盖（`elif open_tag is None` → `elif True`） | 该用例 **RED** |

**门禁**：pytest **1709 passed / 3 skipped**（新增 1 条）；mypy **134 files / 0 errors**。

**⚠ 教训（写下来，因为这是本战役第 N 次"修一个方向、开另一个方向"）**：
我加 `_inside_raw_text` 时只想着"别删可见正文"，**没有回头问"这个新判据会不会让别的东西漏进来"**。
凡是**在守卫上加例外**的改动，都必须**同时给出反向用例**——本步的 Y1/Y2 就是这么补的。
同一轮 b12 还报了 **MEDIUM-2**（报告两条端点仍是 `async def` 却逐份 sha256 源文件，
与 §10.59 同族、只是上次没审计调用方），**登记待修**（见方案未决第 12 条的 b12 台账）。


## §10.71 产出物那两条端点改 `def` —— 并把"审计调用方"从口头纪律做成工具（复核 b12 的 MEDIUM-2）

**一句话**：b12 报的 MEDIUM-2 修了（不是只修它报的两条，而是把它所在的**整个文件**六条端点
一次收口），并且这次**真的把全部端点扫了一遍**——扫的工具进了仓库
（`scripts/audit-async-endpoints.py`），它**独立复现**了复核的结论，还给出 74 条同族候选
（下一步的工作清单）。

### 1. 缺陷：同一个洞，第二次被发现

uvicorn 是**单事件循环**。`async def` 端点里做同步重活（读盘、哈希、渲染、落盘）会**卡住整个引擎**
——GUI 看起来"死掉"。判据是 `iscoroutinefunction(endpoint)`。

- §10.59（复核 b10 的 MEDIUM-2）修了 **2 条**：`/materials/projects/{pid}/locators`、
  `/materials/{mid}/locators`——因为 §10.54 给锚点健康度加了"源文件字节"那一轴，
  它会**流式 sha256 每份源文件**。
- §10.71（复核 b12 的 MEDIUM-2）发现**产出物那一侧**还有两条同族的：
  `POST /report/research`、`POST /report/research/slides` —— 内容块组装会经
  `research_report._attach_locator_status` → `locator.locator_health` → `file_hash`
  **逐份 sha256 材料源文件**（复核实测 3 份材料 = 3 次读盘），再叠加 Markdown/HTML/pptx 落盘。

**根因不是"漏了一条"，而是"从来没有人把全部端点扫过一遍"**：每次靠复核撞见一条修一条，
就永远有下一条。所以这一步除了修，还要把"扫一遍"变成可重跑的东西。

### 2. 改了什么

**`src/core/api/routes_report.py`：六条端点全部 `def`**（不是只改报出来的两条）。
同一个文件里另外四条（`/report/effect`、`/effect/docs`、`/effect/color`、`/effect/export`）
是**同族**：秒级 SQL 聚合 + openpyxl 落盘。只修两条等于把"下次再报"留给下一次。

`/effect/export` 的改法带一个**语义变化**，必须钉住：它原先写成 `async def`
**只为了 `await request.json()`**（`except Exception: body = {}`）。现在把 body 写进函数签名
（`body: dict | None = None`）——FastAPI 在派发进线程池**之前**就把 body 解析好。代价：

| | 改前 | 改后 |
|---|---|---|
| 没有 body | 200（空 body） | 200（`None` → `{}`） |
| 合法 JSON | 200 | 200 |
| **非法 JSON** | 200（被 `except` 吞成空 body，**照常出文件**） | **422**（FastAPI 直接拒） |

这是**有意的收紧**（fail-closed，与库里其它端点同口径）。这条端点此前**一个 HTTP 测试都没有**
（只有模块级 `export_effect_report_xlsx()` 的用例），所以补了一组
`tests/test_effect_report.py::TestExportEndpointBody`（3 条：无 body / 合法 body / 非法 JSON→422）。

### 3. 新闸门：逐条 + **文件级** + 反向断言

`tests/test_material_api.py::TestSlowEndpointsAreDeclaredSync` 里加了两层：

1. **逐条**：把报出来的两条加进 `parametrize` 白名单（沿用原样式）。
2. **文件级**（新）：`routes_report.py` 注册的端点**一个都不许是 `async def`**。
   理由写在测试里：白名单挡不住**将来新加**的端点，文件级判据挡得住；这个文件里的每一件事
   （聚合 / 落盘 / 哈希）都是同步重活，往里加端点**默认就该是 `def`**。
3. **反向断言**：`assert len(seen) >= 6` —— 路由一条都没扫到时"全绿"是**假绿**
   （b12 的 `e2e:materials` C2 就是这么空过的）。

### 4. 审计工具：把"扫一遍"做成可重跑的（`scripts/audit-async-endpoints.py`）

判据两层，都只看静态代码：

- **T1**：`async def` 但**整个函数体里一个 `await` 都没有** ⇒ 永远不会让出控制权，纯属惯性。
- **T2**：有 `await`，但**可达路径上**有阻塞标记（文件 I/O / 哈希 / 子进程 / openpyxl / pptx /
  网络 / sleep / 遍历 / 大事务）——与 `/effect/export` 原来的形状一模一样。

**这个工具自己先栽了三次，三次都修了（都是"审计的盲区正好盖住它要抓的东西"）**：

| 症状 | 原因 | 修法 |
|---|---|---|
| `/report/effect/export` 在审计里**完全隐形** | 端点写成 `from src.core.exports import effect_report`（**函数体内** import），模块 globals 里没有这个名字 ⇒ 丢进 unresolved | 解析**函数体内的 import**（`_local_aliases`） |
| `/report/research` 仍是"仅轻标记" | `from src.core.exports import research_report as rrep` 里的 **`research_report` 是子模块**，`getattr(pkg, name)` **拿不到**（`from pkg import x` 能成是靠 import 系统的回退） | 子模块回退：`importlib.import_module(f"{pkg}.{name}")` |
| 同上，还不亮 | 两个原因叠加：① 链太长被 `depth_max=3` 截断（`locator_health` 在 depth 4、`source_bytes_match` 5、`file_hash` 6）；② **标记表只认 `sha256`/`hashlib` 字面量**，而项目自己的哈希入口叫 `file_hash`（字面量在 `material_ingest.py` 里） | 深度 3 → 7；并把项目自己的哈希入口名 `file_hash` / `_sha256_file` 加进 hashing 标记（深度 5 时两个原因各占一半，单改深度不亮） |

**它独立复现了复核的结论**（这是这一步最有价值的一行证据）：把 `routes_report.py` 还原到 HEAD
再跑，审计自己点出

```
  /api/v1/report/research         awaits=0 heavy=file-io,hashing,pdf/ocr
  /api/v1/report/research/slides  awaits=0 heavy=file-io,hashing,office/render,pdf/ocr
  /api/v1/report/effect/export    awaits=1 heavy=office/render
```

——**没看过复核报告**，纯粹从源码调用链推出来的。

| 指标 | 修前 | 修后 |
|---|---|---|
| `async def` 端点 | 140 | **134** |
| T1（无 `await`） | 89 | **84** |
| T1 **且**有重阻塞标记（"必然卡 + 真做重活"） | 36 | **34** |
| T2（有 `await` + 重标记） | 41 | **40** |

### 5. 下一步（step-72）的工作清单已经现成

审计剩下 **34 条 T1+重** 与 **40 条 T2+重**，按严重度排在最前面的几类：

- **PDF 渲染/读盘**（最重）：`/documents/{doc_id}/figure/{fig_no}`、`/formula/{fno}`、
  `/table-image/{page}/{idx}`、`/tree`、`/assets/{fname}` —— PyMuPDF 渲染一张图就是秒级，
  现在全在事件循环里；`/documents/{doc_id}/file`（发 PDF 字节）也在其中。
- **落盘/导出**：`/export/obligations/{list_id}`、`/export/review/{task_id}`、
  `/egress/audit/export`、`/update/report/{batch_id}`、`/update/report-xlsx/{batch_id}`、
  `/snapshots/{snapshot_id}/restore`（含 sha256）。
- **扫描/采集**：`/ingest/preview*`（同步跑解析！）、`/ingest/bulk/{batch_id}/resume`、
  `/vision/locate`、`/aliases/extract`。
- **`bulk-db` 一族**（最弱的一档标记：短事务本身不算重活，但 `BEGIN IMMEDIATE` 在写竞争下
  最长可等到 `busy_timeout=60s`）——需要**逐条实测**再决定，不要照单全改。

**不要照单全改**：`/chat/completions`、`/compliance/review/{task_id}/execute` 这类
`async def` 是**有理由的**（流式/后台任务），改错了会把 SSE 弄坏。下一步的做法与这一步一样：
**先量（改前卡多久）→ 再改 → 再量**，一条一提交或一小批一提交。

### 6. 证据

- **门禁**：`pytest` **1715 passed / 3 skipped / 0 failed**（1709 → +6：3 条 body 契约 +
  2 条逐条白名单 + 1 条文件级）；`mypy` **134 files / 0 errors**；`tsc --noEmit` 0；
  `smoke` **EXIT=0（19 段脚本全过）**；`verify:commands` **22/22**。
- **变异（全部按预期变红，还原字节一致）**：
  - **Z1** `/report/research` 改回 `async def` ⇒ 逐条闸门红（指名该路径）；
  - **Z2** `/report/effect/export` 改回 `async def` ⇒ **只有文件级闸门**红（逐条白名单里没它
    ——这正是"白名单挡不住新端点"的实证）；
  - **Z3** 把文件级闸门的模块筛改成不存在的名字（人为"空过"）⇒ **反向断言**红（`只扫到 0 条`）；
  - **Z4** 把 export 端点**忠实**还原成旧的 `async` + `await request.json()` 形状 ⇒
    `test_malformed_json_is_422_not_silently_empty` 红（证明这条契约测试不是装饰）。
  - Z4 第一次做得不干净（插了 `Request` 注解却没导入，红的原因是另一回事），**重做**成忠实还原。
- **审计**：`scripts/audit-async-endpoints.py`（只读、临时 KS_DATA_DIR、~2.4s 跑完）。

### 7. 诚实边界（必须一起读）

1. **真机上这次修复还没生效**：DSH 宿主（pid 37268，09-17 19:06 启动）与引擎
   （pid 32564，19:14 启动）**都早于**这些提交，跑的是旧代码。要等业主重启两个门才生效——
   与材料平面本身同一个待办。
2. **审计是启发式的，不是证明**：它只看"**I/O 形状**"的重活。**纯 CPU / 纯 SQL 聚合看不见**
   ——`/report/effect` 这类"秒级同步聚合"在审计里是 `heavy=-`（它照样在 T1 里，但"重"这一栏
   不亮）。深度上限（7）也会截断长链；`unresolved` 名字 **2690 处**（跨模块实例方法等，
   已把纯局部变量排除）；轻标记 `fs-copy` 单独出现**不算重活**（`get_db_connection()` 里就有
   一个 `mkdir`，会传染到任何碰库的助手）。**扫不到 ≠ 没有。**
3. **两条 `async` 可能是对的**：`/chat/completions` 之类**不能**盲改（见 §5 末）。
4. **`e2e:materials` 的 C2 仍是空过**（真机路由 404、那轮只发了 2 条 404 请求），
   `e2e:sidebar` 也只测了宿主侧——两条端点的 `def` 化**没有**经过真机浏览器验证。
5. 本步**零前端改动**（`plugin/` 一个字节没动）。


## §10.72 收口复核 b12 的 LOW/INFO —— 一条假绿（C2）、一条真检测（anchorNote）、一处穷尽性缺口（复算按钮）

**一句话**：b12 剩下的 7 条 LOW/INFO 全部落地；其中三条不是"改注释"而是**真护栏**：
C2 从"没数据也 PASS"改成 `INCONCLUSIVE`（真机实测已生效）、`anchorNote` 那条改为**渲染级**判据
（原先放宽后**丢了真检测**，是我自己变异 AA5 抓出来的）、"要不要禁用复算按钮"收进**穷尽函数**。
另外把连续三轮复发的流程问题写成了纪律。

⚠ **编号对照（避免后代对不上号）**：本节按**我台账**的编号写；复核报告的编号括号里标注——
报告 `LOW-4b` = 本台账 `b12-LOW-3`；报告 `LOW-3` = 台账 `b12-LOW-4`；
报告 `LOW-4` = 台账 `b12-LOW-5`；报告 `LOW-5` = 台账 `b12-流程`。

### 1. b12-LOW-1（报告 LOW-1）：那两条"钉字符串"的断言 —— 放宽之后**丢了真检测**，最后走渲染级

原先：
```js
/why\[a\.material_id\] = a\.why/.test(panel)
/\{anchorNote !== '' &&/.test(panel)
```
复核的 M10/M11 证明：**语义等价**的重写（`String(a.why || '')`、`Boolean(anchorNote)`）会让它们
**假红**——假红的门禁会被训练成"忽略它"。但**放宽成结构级**之后我自己变异一次（**AA5**：
把条件改成 `{false && (<p>{anchorNote}</p>)}`）发现：源码里**照样"读"到 `anchorNote`**
（内层 `<p>{anchorNote}</p>` 还在）⇒ 结构级断言**看不见**这种永不上屏的改法。

**结论不是二选一，而是拆成两层**：
- `why` 映射（AA4 验过）：结构级 = "真的遍历 `s.attention` 且赋值右侧取自 `a.why`"。
  写死 `''` ⇒ **RED** ✅；`String(a.why || '')` 这类等价重写 ⇒ 绿 ✅（假红消掉）。
- `anchorNote`：**抽成一个能单独渲染的组件** `AnchorNoteLine`，判据变成
  · 调用点（结构级）：`<AnchorNoteLine note={anchorNote} />` —— AA6 断开调用 ⇒ RED ✅；
  · 行为（**渲染级**）：`note=''`/缺省 ⇒ 什么都不出；`note='后端原文'` ⇒ **原样**出现。
    AA5（让组件永远 `return null`）⇒ RED ✅。
  这就是 b11 建议"收编渲染用例"的**零依赖版本**（`react-dom/server`，不装 jsdom），
  和 `AnchorMark` 同一套路。顺带把那个脆弱的 JSX 条件**从源码里消掉了**——
  没有条件可被改成 `false &&`。

### 2. b12-LOW-3（报告 LOW-4b）：穷尽性管不到的**第二个判断点**

`KsMaterialsPanel.tsx` 里"要不要禁用『复算锚点』"原先是调用点直接比较状态名。
`assertNever` 只保护 `AnchorMark` 的那个 `switch` ⇒ 后端**新增状态**且它**也该**禁用时，
那一处**一声不响**（今天不是 bug：按设计只有 `no_locators` 禁用）。

修法：抽出**穷尽函数** `statusDisablesReverify(status)`（自己的 `switch` + `assertNever`），
调用点改用它。判据：没有区间可复算 ⇒ 禁用；其余都能点（`stale` 正是要点它的时候）。
护栏：
- 行为级逐档（`smoke-anchor-mark.mjs` 真调用）：`no_locators ⇒ true`，其余五档 ⇒ `false`；
- 调用点结构级（`smoke-client-entry.mjs`）：`statusDisablesReverify(` 必须在，且面板源码里
  **不许再出现**状态名的相等比较；
- 穷尽性由 `tsc` 保证（往 union 加成员 ⇒ `default` 分支不再是 `never` ⇒ typecheck 红）。

变异 **AA1**（调用点写回直接比较）⇒ 调用点判据 RED；**AA2**（去掉 `export`）⇒ 导出判据 RED；
**AA3**（把 `stale` 判成禁用）⇒ 行为判据 RED。三条互为补位（少了任一条都有洞）。

### 3. b12-INFO-1（报告 INFO-1）：`e2e:materials` 的 **C2 是假绿** —— 已改成三态

C2 原先是 `succeeded.length === 0 || state.optionCount > 1 || honest` ——
**一条成功请求都没有时它照样 PASS**。实机就是这个形状：那轮只发了 2 条 `/ks/materials` 请求、
**两条都是 404**、2xx **0 条**，C2 依然绿（"接线验过了"的假象）。

修法：脚本引入第三个状态 **`INCONCLUSIVE`**（判据前提没满足，既不是 PASS 也不是 FAIL），
C2 在"0 条 2xx"时报它，**单独计数并打印**，绝不被"全绿"的总结尾吞掉。

**真机实测（本步当场跑的）**：
```
INCONCLUSIVE  C2 成功的项目列表请求确实喂进了下拉框 — 2xx 0 条（无法验证：一条成功的项目列表请求都没有）
⚠ 1 条 INCONCLUSIVE（**没验证过**，不是通过）：C2
== e2e-materials-panel PASS (8/8 + 1 INCONCLUSIVE) ==
```
改前同一台机器上是 `PASS 9/9`。

⚠ **诚实边界**：C2 的 **FAIL 分支没在真机验过**（真机路由还是 404，没有 2xx 可走）；
不过那一支的表达式与改前**逐字相同**（`optionCount > 1 || honest`），本步只改了"0 条 2xx"这一支。
"有 2xx 但库里确实没有项目"与"接线坏了"仍然分不开（要读响应体数条数）——**登记为下一步**，
不在这里假装解决。

### 4. 其余三条（注释/文档，不是护栏但会误导人）

| 台账编号 | 报告编号 | 问题 | 处置 |
|---|---|---|---|
| b12-LOW-4 | LOW-3 | `test_slide_export.py` 里"39 放不下"的**理由**与渲染实测不符（渲染器对纯破折号行做标点压缩，`—`×39 实测**只占 1 行**） | 注释改成"**模型≠渲染**：模型取宽（38 放得下、39 放不下），渲染可能更省行 ⇒ 方向**安全**（多续页不裁字）"；断言仍钉**模型**（可复现），不再暗示"渲染必然 2 行" |
| b12-LOW-5 | LOW-4 | `hybrid_engine.py` 只写"未核验沉底"，**没写**"因此已废止/已替代排在未核验之前" | 在**通道 A**（口径的唯一所有者）补取舍说明：字符串序 `effective < superseded < withdrawn < NULL`；与"未核验不得承重"不冲突（那是"能不能承重"，不在排序里）；要改是**新口径**、需业主拍板。另记 D/E 有 `cr.clause_revision_id` 兜底成**全序**、**A 没有**（复核 b12 的 INFO），D/E 只指向 A 不再各写一份 |
| b12-LOW-2 | LOW-2 | 仍有 **23 条**"文案在场"型断言 | **不清算**（它们本来就有用：措辞纪律 + 产物新鲜度），但把**边界**写进 `smoke-client-entry.mjs` 的注释：挡得住"删掉这句字"，挡不住"字还在、渲染不出来"；行为级那一半由 `smoke-anchor-mark.mjs` 与"产物↔源码一致"承担 |

另修：`_inside_raw_text` 的**名单边界**（报告 INFO-2）——docstring 原来列四个元素，读起来像
"这就是完整的 raw text 名单"；现在写明 `iframe`/`noembed`/`noframes` 由 `_CONTENT_HIDDEN_TAGS`
那条路径整块剥掉（浏览器不渲染其回退内容 ⇒ 今天无害），**要动得两边一起看**。

### 5. b12-流程（报告 LOW-5）：把"派复核前冻结区间"写成纪律

b9/b10/b12 **连续三轮**都出现"任务书说的区间与事实不符"（条数不对、或声称含某提交而实际不含
——它的代码在父提交里），同时主检出在复核期间又前进了若干提交。已写进
`docs/DEVELOPMENT-HISTORY.md` §五 **第 6 条**：派单前 ① `git tag verify-freeze-<批次>` 打在要复核的
HEAD 上；② 用 `git rev-list --count <base>..<frozen>` **数出**条数写进任务书。
**这是流程纪律、不进自动门禁**（没人能自动判断任务书写得对不对），但它比任何断言都便宜。

### 6. 证据

- **门禁**：`pytest` **1715 passed / 3 skipped / 0 failed**；`mypy` **134 files / 0 errors**；
  `tsc --noEmit` **0**；`smoke` **EXIT=0（19 段脚本全过）**——其中 `client-entry` **84 → 85**、
  `anchor-mark` **15 → 26**；`verify:commands` **22/22**；`e2e:materials` 真机 **8/8 + 1 INCONCLUSIVE**。
- **变异 AA1–AA6 全部按预期变红、还原字节一致**（JS/TS 侧变异每条都**重新构建产物**再跑冒烟）。
  ⚠ **AA2/AA3 第一次是我瞄歪了**：我写了 `npm run smoke:anchor-mark`，而 `plugin/package.json`
  **没有**这个脚本名（它只在 `smoke` 链里）⇒ npm 报 `Missing script` 也让 `rc=1`，
  "看起来红了"。判据是**红的原因对不对**，不是"红没红"——已改成直接 `node <path>` 并复跑全部。
- `plugin/client.js` 已按修好的源码重建（**1,280,556 bytes**）并一起提交
  （它是被跟踪的**交付产物**，冒烟会同时查产物与源码）。

### 7. 诚实边界

1. **真机仍是旧进程**：DSH 宿主（pid 37268，09-17 19:06）与引擎（pid 32564，19:14）都早于本批提交
   ⇒ 这一批（含 §10.71 的端点 `def` 化）**都还没生效**，要等业主重启两个门。
2. **C2 的 FAIL 分支未在真机验过**（见 §3）。
3. **`INCONCLUSIVE` 不影响退出码**：它靠"单独计数 + 打印"可见，不靠失败——这是**有意的**
   （前提没满足不该判失败），代价是"全绿"的总结行旁边必须看那行 ⚠。
4. 本步改动面广但每条都小：**零 Python 行为改动**（只有注释与 docstring），
   Python 侧门禁数字与 §10.71 完全一致（1715/134）。


## §10.73 造一把"引擎被堵多久"的尺，并用它做完第一批（`ingest/preview` 六条）——顺带量出一条审计看不见的缺陷

**一句话**：§10.71 的审计只能给**候选清单**，答不了"**卡多久**"，也证明不了改动真的让出了事件
循环。这一步先造量具（`scripts/measure-endpoint-blocking.py`），再用它把入库预览那一族六条端点
从 `async def` 改成 `def`：**事件循环空档 0.468s → 0.032s**（请求耗时不变）。量具跑第一趟就抓到
一条静态审计**完全看不见**的问题（`/health` 每次调用触发一次 6.6s 阻塞式模型拉取）。

### 1. 为什么需要一把尺（而不是继续靠推断）

`audit-async-endpoints.py` 是**静态**判据：它说"这条端点做同步重活"，但它
① 排不了优先级（读个目录 vs 解析一本 300 页 PDF 都是"重"），② 给不出"改完真的好了吗"的证据
——`async def` 改成 `def` 只是**声明**，Starlette 到底有没有把它丢进线程池，**得量**。
复核 b10/b12 都是靠"变异 + 实测"定的性；这把尺把那种做法固定成可重跑的东西。

**机制**：`httpx.ASGITransport` 让被测 app 与调用方**跑在同一个事件循环**里；同时开一个心跳
协程（每 5ms 醒一次，记录两次唤醒之间的间隔）。于是
- 端点是 `async def` ⇒ 同步重活在**调用方任务里**执行，心跳**排不上调度**
  ⇒ `max_gap ≈ 该请求耗时`；
- 端点是 `def` ⇒ anyio 丢**线程池**，心跳照跳 ⇒ `max_gap` 掉回**心跳分辨率**。
两条端点的**请求耗时一样**——所以它量的是"**谁被占住**"，不是"谁慢"。

用法：`.venv\Scripts\python.exe scripts\measure-endpoint-blocking.py --case ingest_preview [--pages N] [--json]`
（只建**临时** `KS_DATA_DIR` 的 app 与自己生成的 PDF，不碰真库、不碰生产模型缓存。）

### 2. 第一批：`routes_ingest_preview.py` 六条端点 → `def`

选它的理由：本文件自己写着"**单本预览在负载下实测可达 135s**"，而它是 `async def` ⇒
**最坏情况下整个引擎静默死两分钟**（GUI 看起来"卡死"，所有请求一起等）。改法是机械的
（六条都**没有 `await`**），风险最低、收益最高。

| 用例（本机单次实测） | 改前 | 改后 |
|---|---|---|
| `POST /ingest/preview`（12 页 PDF）**请求耗时** | 0.4736s | 0.4605s（**活照干**） |
| ↑ **事件循环最大空档** | **0.4679s**（≈整条请求） | **0.0320s** |
| ↑ 心跳样本数 | 9 | 34（心跳一直在跳） |
| ↑ 空闲基线 / 中位 | 0.0141s / 0.0001s | 0.0191s / 0.0155s |
| `GET /ingest/preview/inbox` 最大空档 | 0.0094s | 0.0199s（两者都在噪声底） |

**怎么读**：改后的 0.032s **不该**读成"还堵了 32ms"——同一次运行的**空闲基线是 0.019s**、
中位 0.016s，也就是**已经回到量具的分辨率**（心跳 5ms + 线程/调度抖动）。改前那个 0.468s
则是货真价实的"整条请求期间引擎对所有人都是死的"。

### 3. 闸门（含"闸门不能空过"的反向断言）

`tests/test_material_api.py::TestSlowEndpointsAreDeclaredSync` 的文件级那条从"写死
`routes_report`"**泛化成参数化**：`[(routes_report, 6), (routes_ingest_preview, 6)]`
（`seen >= min_routes` 的反向断言逐模块保留）。

变异（全 RED、还原字节一致）：**AB1** 把 `ingest_preview` 改回 `async def` ⇒ 指名该路径；
**AB2** 把模块名筛成不存在的 ⇒ 反向断言红（`只扫到 0 条端点`）；
**AB3** **只**把最便宜的那条（`job_status`）改回 `async` ⇒ **照样红**（证明它管全六条，
不是只管第一条）。

### 4. 量具自己也要有闸门（否则它的数字有一天会集体变假绿）

`tests/test_measure_harness.py`（3 条，~1.6s，**不依赖真引擎**）：造两条端点，
`async def + time.sleep(0.3)` 与 `def + time.sleep(0.3)`，断言
① 前者 `max_gap ≥ 0.21s`（量得出"堵"）；② 后者 `max_gap < 0.15s` 且样本数 ≥ 5（量得出"没堵"，
且**心跳真的在跳**）；③ 两者**耗时同量级**而空档差 3 倍以上（证明量的是"谁被占住"）。

**为什么这条最要紧**：§10.73 之后每一个"改后掉回噪声底"都出自这把尺。量具没有闸门的话，
它坏掉那天所有 after 数字都会变成**假绿**——而且是**最难发现**的一种：数字看起来完全合理，
只是永远是 0。变异 **AC1**（心跳刚建起来就被 `stop`，即"永远报 0"）⇒ 红在①；
**AC2**（心跳间隔粗到 5s，即"分不开"）⇒ 红在②。

### 5. 量具跑第一趟就抓到一条审计看不见的缺陷（登记，未修）

```
case=health  HTTP=200
  请求耗时 : 6.7918s
  事件循环最大空档 : 6.7912s   ⇒ 至少堵了 6.7862s     （第二次跑 6.66s，可复现）
stderr: Fetching 5 files: 100%|██████████| 5/5 [00:05<00:00, 1.08s/it]
```

链路：`GET /api/v1/health`（**`async def`**）→ `embedder.is_available()` → `_get_model()`
→ `fastembed.TextEmbedding(...)` ⇒ **一次 6.6s 的阻塞式取模型**，全程占着事件循环。

**静态审计为什么漏了**：标记表认的是 `requests.` / `httpx.` / `urlopen` 这类**裸网络调用**，
而这里的外发藏在 `fastembed`/`huggingface_hub` 内部——**"扫不到 ≠ 没有"**的又一例。

**两条真实缺陷（必须分开说）**：
1. **`/health` 是 `async def` 却做 6.6s 级重活** ⇒ 每次健康检查把引擎堵住
   （GUI 健康板/`ks_ping` 都会打它）。这条与第一批同族，改 `def` 即可。
2. **`_get_model()` 只缓存成功、失败不缓存**（`_load_error` 记了却不再用）⇒
   一次加载失败后**每次调用都重试**。**诚实的量化边界**：本机 6.6s 出现在
   **空缓存**（临时 `KS_DATA_DIR` ⇒ 真去下载 5 个文件）；真机 `models_dir` **已有**
   `models--Qdrant--bge-small-zh-v1.5` ⇒ 稳态不会下载。所以"**离线机器上每次 `/health`
   都重试一次网络加载**"是**推断**（推理链：一次尝试在空缓存下耗时 6.6s + 失败不缓存），
   **不是本机测得的数字**——要测得在一台 DNS 被黑洞的机器上跑。修法（负缓存 + 冷却窗口，
   而不是永久拉黑）是**设计决定**，留给下一步。

### 6. 改完的**连带核查**（`def` 把"事件循环串行"换成"线程池并发"）

| 共享状态 | 核查结论 |
|---|---|
| `preview_jobs`（任务表 + worker 线程） | ✅ **已有 `threading.Lock`**（`_jobs_lock`，本来就是线程模型）⇒ 并发安全 |
| `dry_run` 的临时目录 `dryrun/tmp/<hash16>/`（按**源文件哈希**命名 ⇒ 同一文件共享） | ⚠ **登记**：默认路径（`allow_deep=false`）只**写**不读回（结果经 IPC 队列返回），且同一哈希的输入**逐字节相同** ⇒ 没查出可证明的损害；只有显式 `allow_deep=true` 时深通道的落地目录会被**读回**（layout/images）⇒ 同一文件并发时理论上有**撕裂读**。且这种并发**改动前就存在**（jobs worker 线程 vs 同步请求），本步只是把它变宽（两次点击）。修法（按哈希加锁，保留"每文件一个目录"的磁盘上界）留给下一步，**不在本步假装解决** |
| `sqlite` 连接 | ✅ 线程局部连接（`_local`）+ `check_same_thread=False` ⇒ 每个工作线程各一条 |

### 7. 证据

- **门禁**：`pytest` **1719 passed / 3 skipped / 0 failed**（1715 → +4：文件级参数化 +1、
  量具自测 +3）；`mypy` **134 files / 0 errors**；`tsc --noEmit` 0；`smoke` **EXIT=0（19 段）**；
  `verify:commands` **22/22**。
- **变异 AB1–AB3 / AC1–AC2 全部按预期变红、还原字节一致**。
- `src/core/api/routes_ingest_preview.py` 的 diff：**6 行增 6 行删**（只有 `async` 一词），
  无其他改动。

### 8. 诚实边界

1. **量的是"事件循环被占住多久"，不是端到端延迟**：ASGITransport 是**进程内**调用，
   没有真 socket、没有 uvicorn 的并发限制；所以这些数字**不能**当作"用户等待时间"。
2. **单次实测、本机**：没做方差研究（心跳本身有 5ms 分辨率与调度抖动，改后那 0.032s
   就落在噪声里）。跨机器/跨负载的复现留给需要时再跑。
3. `blocked_s_lower_bound` 是**下界**（心跳只在两次唤醒之间采样）⇒ 读成"**至少**堵了这么久"。
4. **真机还没生效**：两个门（DSH 宿主 pid 37268 / 引擎 pid 32564）仍跑旧代码，要业主重启。
5. 本步**零前端改动**；`smoke`/`tsc` 数字与 §10.72 完全一致。

### 9. 下一步（按这把尺继续）

1. **`/health` + `embedder`**（§5）：端点改 `def`；负缓存 + 冷却窗口（设计决定，要写清
   "失败多久后允许重试"）；并给 `/health` 加一条"**不许触发全量模型加载**"的判据
   （健康检查应当是**廉价**的——今天是"加载一个模型来判断它能不能加载"）。
2. **PDF 渲染/读盘族**（审计里最重的一档）：`/documents/{doc_id}/figure|formula|table-image|tree|assets`
   ——先用这把尺量出每条的真实空档（**改前**），再决定改动顺序；这些端点返回的是**图片/字节**，
   要顺带确认 `def` 下 `Response`/`FileResponse` 的语义没变。
3. **落盘/导出族**：`/export/obligations|review`、`/egress/audit/export`、`/update/report[-xlsx]`、
   `/snapshots/{id}/restore`。
4. **`dry_run` 同一文件的并发**（§6 登记项）。
5. **`bulk-db` 一族**逐条实测再决定；`/chat/completions` 那类有理由的 `async` **不动**。


## §10.74 让健康检查回到"廉价"：`/health` 6.79s → 0.0064s；失败的加载不再无限重试 —— 并把一句我自己写错的注释当场改掉

**一句话**：§10.73 的量具抓到的两条缺陷都修了——(1) `/health` 不再"**加载一个模型来判断它能不能
加载**"（`embedder.health()` 廉价三态），实测请求 **6.7918s → 0.0064s**、事件循环空档
**6.7912s → 0.006s**；(2) 加载失败**进 60s 冷却窗口**，不再每次调用重试。顺带：我写在注释里的
"`import mineru` 首次导入要几秒"**是错的**（实测 0.000s），量完就改掉了——这条比修好本身更值得记。

### 1. 缺陷（§10.73 量具抓的，静态审计看不见）

```
GET /api/v1/health  →  embedder.is_available()  →  _get_model()  →  fastembed.TextEmbedding(...)
```
- 这条链**每次调用**都走一遍：`TextEmbedding(...)` 首次要下载/装载模型。量具实测空缓存下
  **6.79s，且全程占着事件循环**（`/health` 当时是 `async def`）⇒ 每次健康检查把引擎堵 6.8 秒。
- `_load_error` **只记不缓存**（记了却从不参与判断）⇒ 一次失败之后**每次调用都重试**。
  离线机器上，这意味着**每次 `/health`、每次检索**都付一次网络超时。
- 静态审计漏它的原因：标记表认的是裸网络调用（`requests.`/`httpx.`/`urlopen`），而这里的外发
  藏在 `fastembed`/`huggingface_hub` 内部——**"扫不到 ≠ 没有"**又一例（已登记）。

### 2. 修法（两条纪律写进 `embedder` 的模块 docstring）

**① 廉价路径不许触发加载。** 新增三态判据 `health()`：

| 取值 | 含义 | 依据 |
|---|---|---|
| `ok` | 本进程**真的加载成功过** | `_model is not None`（**唯一**能证明"能用"的证据） |
| `offline` | **最近一次**加载尝试失败 | `_load_error is not None`（`offline_reason()` 给原因） |
| `unknown` | 本进程**还没试过** | 其余情况——如实说"没验证"，**绝不为了猜去加载** |

改用它的三处：`GET /api/v1/health`、`GET /api/v1/diagnostics/health-board`（`engines.vector`）、
以及 `hybrid_engine` 检索 debug 块（那里原来是"一次失败之后**每次检索**都再重试一次加载"）。
`is_available()` **保留原语义**（会真的加载）——向量通道 `if "vec" in channels and
embedder.is_available()`、入库时的 `embed_batch` 这些**真要拿模型**的路径继续用它。

**② 失败进冷却窗口。** `RETRY_COOLDOWN_S = 60.0`：失败后记住 `_error_at`，窗口内
`_get_model()` **直接复用上次失败**（不重试），窗口过去后允许再试一次——**瞬时故障一分钟内自愈，
不永久拉黑向量引擎**；成功时清掉 `_load_error`。另加一个测试缝 `_import_text_embedding()`，
让单测不必真装 fastembed、更不必连网。

### 3. 实测（同一把尺，同一条用例）

| `case=health` | 改前 | 改后 |
|---|---|---|
| 请求耗时 | **6.7918s** | **0.0064s** |
| 事件循环最大空档 | **6.7912s** | **0.006s**（空闲基线 0.0149s ⇒ 已在噪声底） |

### 4. ⚠ 当场纠正一句我自己写错的话（"先量再吹"）

我最初给 `health_board → def` 写的理由是"`mineru_available()` 是 `import mineru`，**首次导入几秒**"。
量了之后：

- `import mineru` 实测 **0.000s**（它是 **CLI 包**，不是重依赖库）——**那句话是错的**；
- `health_board` 总耗时实测 **0.017s**（本机、空测试库）；
- 30 万行表上一条 `COUNT(*)` ≈ **1.1ms**（代理测量）⇒ 七条约 **7ms** 量级。

⇒ `health_board` **从来不是严重阻塞**。改 `def` 的判据降级为**结构性纪律**（"同步 I/O 不该写在
`async def` 里"），而不是"这里很慢"；三处注释（端点 docstring / 闸门条目 / 量具用例）
**全部按实测改写**，并明确写"**别夸大收益**"。留这条记录是因为：**差点把一次测不出来收益的改动
写成战果**——量具的价值不只是证明"改好了"，也包括证明"**没你想的那么好**"。

### 5. 闸门与变异

`tests/test_embedder_health.py`（**11 条**，~0.6s，判据全是**行为级**，不是"源码里有那个词"）：
- `TestHealthIsCheap`：没试过 ⇒ `unknown` **且替身没被调用**；加载成功过 ⇒ `ok`；失败过 ⇒
  `offline` + 原因含原文；
- `TestFailureCooldown`：窗口内三次 `is_available()` ⇒ 加载替身**只被调用 1 次**；
  把 `_error_at` 拨回窗口外 ⇒ 再试一次（**不永久拉黑**）；先失败后成功 ⇒ `_load_error` 被清掉、
  `health()` 变 `ok`；
- `TestHealthEndpointsDoNotLoad`：`/health` 与 `/diagnostics/health-board` **都不许触发加载**
  （替身被调用即失败）+ 两条端点的取值必须在三态之内。

`/api/v1/diagnostics/health-board` 进 `TestSlowEndpointsAreDeclaredSync` 的逐条表（它现在是 `def`）。

变异（全 RED、还原字节一致）：**AE1** 让 `health()` 退回 `"ok" if is_available() else "offline"`
⇒ "不许加载"红；**AE2** 删掉冷却窗口 ⇒ "窗口内重试了 **3 次**"红（正是那个洞的形状）；
**AE3** 只把 `/health` 退回 `is_available()`（共享函数没动）⇒ HTTP 层那条红；
**AE4** 健康看板改回 `async def` ⇒ 同步闸门红。

消费方同步（"`unknown` 是新取值，别让界面把它当布尔用"）：`plugin/src/index.js` 的 `ks_ping`
工具描述、`plugin/README.md`、`docs/ENCYCLOPEDIA.md` 都写明三态与"**不做加载测试**"。

### 6. 证据

- **门禁**：`pytest` **1731 passed / 3 skipped / 0 failed**（1719 → +12）；`mypy` **134 / 0**；
  `tsc --noEmit` 0；`smoke` **EXIT=0（19 段）**；`node --check plugin/src/index.js` 通过；
  `verify:commands` **22/22**。
- 变异 AE1–AE4 全 RED。
- 量具：`--case health`（前后对照见 §3）、新增 `--case health_board`。

### 7. 诚实边界

1. **6.79s 是"空缓存"下的数字**（临时 `KS_DATA_DIR` ⇒ 真去下载 5 个文件）。真机 `models_dir`
   **已有** `models--Qdrant--bge-small-zh-v1.5` ⇒ 改前在真机上的代价是**装载**（秒级量级但**未测**）
   而不是下载。**修法本身与缓存状态无关**（健康路径再也不加载了），所以结论不受影响；
   但**不要**把这句读成"生产 `/health` 曾经 6.79s"。
2. "离线机器上每次调用都重试一次网络超时"：**重试行为**已被单测证明（AE2 的"3 次"），
   但**超时的代价**是在本机测不出来的（要一台 DNS 被黑洞的机器）。
3. `unknown` 是**新增取值**：仓内消费方只有字符串插值/透传（已核对），但**任何外部脚本**若把
   `vector_engine == "ok"` 当唯一真值，会看到 `unknown`；这是**有意的**（没验证就说没验证）。
4. **`/health` 仍是 `async def`**，且**没有**进同步闸门——这是刻意的：修法是"**别在这里加载**"，
   而不是"把加载挪到线程池"。它剩下的活是 `SELECT 1`（µs 级）。
5. **真机仍是旧进程**（DSH 宿主 pid 37268 / 引擎 pid 32564，09-17 启动）⇒ 本批要业主重启才生效。


## §10.75 PDF 渲染/读盘族去阻塞化（5 条）+ 把"候选清单不是待办清单"写成结论

**一句话**：审计里最重的一档（PyMuPDF 逐页取字、截图渲染、middle.json 读回、资产 glob）5 条端点
改 `def`：`/figure/1` 实测**事件循环空档 0.232s → 0.036s**（请求耗时不变）。同时**判定并留下**
一条不改的（`/documents/{doc_id}/file`），把"为什么它可以不改"写进代码——因为审计的候选清单
**不是**待办清单。

### 1. 先读代码再动手（这一步有一半价值在"不改"）

| 端点 | 读代码的结论 | 处置 |
|---|---|---|
| `/documents/{doc_id}/figure/{fig_no}` | `middle_geo.load`（读 JSON）+ 逐页 `get_text("dict")` 找题注 + `get_pixmap(clip, dpi)` 出 PNG，还有 `try_redraw` 的矢量重绘（含 OCR）路径 | **改 `def`** |
| `/documents/{doc_id}/formula/{fno}` | middle.json 公式块定位 + `get_pixmap` 截图 | **改 `def`** |
| `/documents/{doc_id}/table-image/{page_no}/{tbl_idx}` | middle.json 表格 bbox + `get_pixmap` | **改 `def`** |
| `/documents/{doc_id}/tree` | 库内条款 + 无书签时用 fitz 扫**文本层**猜章标题 | **改 `def`** |
| `/documents/{doc_id}/assets/{fname}` | 校验 + `glob("**/images/…")` + `middle_geo.load` 取比例头 + `FileResponse` | **改 `def`** |
| `/documents/{doc_id}/file` | **只做一次查询 + `FileResponse`**：字节由 Starlette 用 anyio 流式读出，**本来就不占事件循环** | **不改**（并把理由写进 docstring） |

⚠ `/file` 当初进候选是因为调用链上出现过 `fs-copy` **轻标记**（`get_db_connection()` 里就有
`mkdir`，会传染到任何碰库的助手）。这一条留在这里的意义：**审计给的是"值得看一眼"的清单，
最终每条都要落到"改"或"不改 + 为什么"**。

### 2. 量具加了"带种子数据"的能力，然后量

`scripts/measure-endpoint-blocking.py` 新增：用例可带 `setup` 钩子（在**量之前**跑完，不计入
被测端点的空档）+ `document_figure` 用例——造一份"**题注在最后一页**"的密排 PDF（150 页 × 28 行）
+ 种一行 `doc_meta`，于是走**真路径**：`middle_geo.load` 返回 None → `locate_figure` 逐页扫 →
命中 → `get_pixmap` 出 PNG（HTTP 200）。

| `--case document_figure --pages 150` | 改前（`async def`） | 改后（`def`） |
|---|---|---|
| 请求耗时 | 0.2324s | 0.2324s（**活照干**） |
| 事件循环最大空档 | **0.2321s**（≈整条请求） | **0.036s**（空闲基线 0.0066s ⇒ 已在噪声底） |
| 心跳样本数 | 5 | 15（心跳一直在跳） |

**诚实边界（写在这里，别让这个数字被读大了）**：这是**合成 PDF**（文字密排、无插图、无矢量
流程图）⇒ 它量的是"逐页取字 + 一次截图"的下界；真机文档更重（真扫描件、以及 `try_redraw`
的 **OCR** 路径——本条用例没有触发它）。所以 0.232s 是**下界**，真实代价通常更高。

### 3. 闸门与变异

`TestSlowEndpointsAreDeclaredSync` 逐条表加 5 条（figure / formula / table-image / tree / assets），
并在**同一个注释块里**写明 `/file` 为什么**不在**表里。

变异（全 RED、还原字节一致）：**AF1** `/figure` 改回 `async def` ⇒ 指名该路径；
**AF2** `/tree` 改回 ⇒ 红（证明覆盖不是只有第一条）；**AF3** `/assets` 改回 ⇒ 红。

### 4. 证据

`pytest` **1736 passed / 3 skipped / 0 failed**（1731 → +5）；`mypy` **134 / 0**；`tsc` 0；
`smoke` **EXIT=0（19 段）**；`verify:commands` **22/22**。`src/core/api/server.py` 的改动
= 5 个 `async` 一词 + 1 段 docstring。

### 5. 诚实边界

1. 合成 PDF（见 §2）；真机重启后才生效（两个门仍是旧进程）。
2. **HTTP 层覆盖不均**：`/figure` 由量具真跑（200 + PNG）；`/assets`、`/tree` 有仓内测试
   （`test_assets_endpoint.py` / `test_phase4.py`）；**`/formula` 与 `/table-image` 没有 HTTP 测试**
   ——它们现在走线程池、返回的也是 `Response`/`FileResponse`（与已验的 `/figure` 同形），
   但**未逐条验过**，登记为下一次补测。
3. 本步**零前端改动**。

### 6. 下一步（继续按族推进，先量再改）

1. **落盘/导出族**：`/export/obligations/{list_id}`、`/export/review/{task_id}`、
   `/egress/audit/export`、`/update/report/{batch_id}`、`/update/report-xlsx/{batch_id}`、
   `/snapshots/{snapshot_id}/restore`。
2. **`dry_run` 同一文件的并发**（§10.73 §6 登记项）：按哈希加锁。
3. **给 `/formula`、`/table-image` 补 HTTP 测试**。
4. **审计标记表补"库内部网络/重活"族**（§10.74 §5 的盲区：`fastembed`/`huggingface_hub` 这类
   藏在库里的外发，`requests.`/`httpx.` 那套标记扫不到）。


## §10.76 落盘/导出族去阻塞化（7 条）——并如实记下"这一族**没测出大收益**"

**一句话**：docx / xlsx / JSON 落盘与快照恢复 7 条端点改 `def`（含一条原先只为
`await request.json()` 而写成 `async def` 的）。**但这一族没测出大收益**：唯一能把量铺满的
`/egress/audit/export` 实测只有 **0.030s**（它读的 `debug_dump` 有 1000 行保留上限），其余几条
要有**生产规模**的更新批次 / 义务清单 / 2.2GB 库快照才有意义。所以本步的判据是**结构性**的
（同步落盘不该放事件循环里），不是战果。

### 1. 改了什么

| 端点 | 重活 | 处置 |
|---|---|---|
| `POST /api/v1/export/obligations/{list_id}` | python-docx 生成 + 落盘 | `def` |
| `POST /api/v1/export/review/{task_id}` | python-docx 报告 + 落盘 | `def` |
| `POST /api/v1/export/citations` | **原为 `async def` 只为 `await request.json()`**，随后 docx 落盘 | `def` + **body 改走签名**（⚠ **措辞更正**见下：改前**坏 JSON/没有 body 都是 500**，不是"吞成空 body"） |
| `GET /api/v1/egress/audit/export` | 查审计行 + 写 JSON | `def` |
| `POST /api/v1/snapshots/{snapshot_id}/restore` | 读快照包 + sha256 + 落库 | `def` |
| `POST /api/v1/update/report/{batch_id}` | python-docx 生成 + 落盘 | `def` |
| `POST /api/v1/update/report-xlsx/{batch_id}` | openpyxl 生成 + 落盘 | `def` |

### 2. 量到的（以及**没**量到的）

量具新增 `egress_audit_export` 用例：把 `debug_dump` 的审计行**铺到保留上限 1000 行**
（`trigger_type in ('user_export','egress')`），再量。

| `--case egress_audit_export`（1000 行） | 改前 | 改后 |
|---|---|---|
| 请求耗时 | 0.0305s | 0.0338s |
| 事件循环最大空档 | 0.0301s | 0.0164s（空闲基线 0.0198s ⇒ 噪声底） |

⇒ **这条本来就不大**（30ms 量级、上限就有界）。**另外 6 条未测**，原因写在闸门注释里：
要有生产规模的批次/清单/2.2GB 库快照才有意义，量具跑**临时空库只会给出假小的数字**——
那比不量更坏。它们按**结构性**判据进表（同族的 office/render + sha256 已在
§10.71/§10.73/§10.74 实测过：一次 docx/xlsx 落盘 + 逐份 sha256 是**秒级**那一类）。

### 3. 闸门与变异

逐条表 +7（并写明"这一族基本没测出大收益"）。变异全 RED、还原字节一致：
**AG1** `/export/obligations` 改回 `async def`；**AG2** `/snapshots/{id}/restore` 改回；
**AG3** `/update/report-xlsx` 改回（**另一个文件** ⇒ 跨模块也管）；
**AG4** `/export/citations` 改回。

另补 **HTTP 层契约测试**：`tests/test_phase7.py::test_export_citations_body_contract`
——这条端点此前**没有 HTTP 测试**，而本步改了它取 body 的方式，必须钉住：
无 body ⇒ 200；有证据 ⇒ 200 且 `docx` 非空；**非法 JSON ⇒ 422**（有意的收紧）。

### 4. 证据

`pytest` **1744 passed / 3 skipped / 0 failed**（1736 → +8：7 条闸门 + 1 条契约测试）；
`mypy` **134 / 0**；`tsc` 0；`smoke` **EXIT=0（19 段）**；`verify:commands` **22/22**。

### 5. 诚实边界

1. 6 条**未测**（见 §2）；真机重启后才生效。
2. `/export/citations` 的 422 是**行为变化**：此前非法 JSON 会被当成空 body 照常出结果。
   与 §10.71 的 `/report/effect/export` 一致（fail-closed），且如今有测试钉住。
3. 本步**零前端改动**。

### 6. 下一步

① `dry_run` 同一文件的并发按哈希加锁（§10.73 §6 登记项）；② 补 `/formula`、`/table-image`
的 HTTP 测试；③ 审计标记表补"库内部网络/重活"族（`fastembed`/`huggingface_hub` 盲区）；
④ 派一次独立复核 **b13**（按 §五第 6 条纪律：**先冻结区间**再写任务书）。


## §10.77 `dry_run` 同文件并发加锁 + 渲染端点补 HTTP 契约（两件小事，一次收口）

**一句话**：① 把 §10.73 登记的连带风险修掉——`dryrun` 临时目录按**源文件哈希**命名 ⇒ 同一文件的
并发预览会写同一个目录，现在按哈希**分片加锁**（同文件串行、不同文件照常并行）；
② 把 §10.75 登记的缺口补上——`/formula` 与 `/table-image` 此前**一条 HTTP 测试都没有**，
现在两条**都有确定性 happy path**（真造 middle.json ⇒ 200 + PNG + 比例头）。

### 1. `dry_run` 同文件并发（§10.73 §6 登记的项）

风险回顾：临时目录 `dryrun/tmp/<sha256[:16]>/` 按**源文件内容**命名 ⇒ 同一文件的两个并发预览
写同一个目录；**显式**走深通道（`deep_fallback=true`）时那个落地目录还会被**读回**
（`layout.json` + `images/`）⇒ 理论上有撕裂读。默认路径（`deep_fallback=false`）只写不读、
且同一哈希的输入**逐字节相同** ⇒ 查不出可证明的损害；而这个并发**改动前就存在**
（jobs 的 worker 线程 vs 同步请求），§10.73 把预览端点改成 `def` 后变宽（两次点击即可）。

修法：**按哈希分片加锁**（64 把，`_parse_lock(tmp_dir)`），只包住 `run_parser_isolated` 那一段。

| 设计选择 | 为什么不是别的 |
|---|---|
| **分片**（固定 64 把）而不是"每个目录一把" | 后者要为进程见过的**每个文件**留锁对象，万级批量预览就是万级条目（无界）；分片表内存有界 |
| 分片而不是**全局一把** | 全局锁会把**不同文件**的预览也串起来（批量预览与手动预览互相等）——拿吞吐换安全 |

**测试是行为级的**（`tests/test_dry_run_concurrency.py`，真开两个线程 + 替身解析器记并发峰值）：
同一文件 ⇒ 峰值必须是 **1**；不同文件（且分片不同，测试里用 sha256 挑出来）⇒ 峰值必须是 **2**。
变异 **AH1**（去掉锁）⇒ 前者红；**AH2**（改成全局一把锁）⇒ 后者红——两条互为反向断言。

⚠ 过程中踩到两个"我以为在测、其实没测到"的坑，都写进注释留给后代：
① 替身最初打在 `dry_run.run_parser_isolated` 上，而实际调用点是**函数内**
`from ...parser_worker import run_parser_isolated` ⇒ 那个名字**根本不存在**（实测 `calls=0`）；
② 用假 PDF 字节（`b"%PDF-1.4" + 填充`）过不了体检里的 fitz 解析，第一步就抛 ⇒ 必须造**真 PDF**。

### 2. 渲染端点补 HTTP 契约（§10.75 登记的缺口）

`tests/test_doc_render_api.py`（9 条）：种一行 `doc_meta` + 真 PDF + **最小可用的 middle.json**
（schema 简单：`pdf_info[].page_size` + `para_blocks[].{type,bbox}`，放在
`parse_out/<doc_id>/**/*_middle.json`）。

| 端点 | happy path（**确定性**） | 失败契约 |
|---|---|---|
| `/table-image/{page}/{idx}` | ✅ 200 + `image/png` + PNG 魔数 + `X-Frac-X0/W/H` 三个还原头 | 无产物 ⇒ `table_geo_not_found`；序号越界 ⇒ `table_not_found`；未知文档 ⇒ `doc_not_found` |
| `/formula/{fno}?clause=X` | ✅ 200 + PNG（`interline_equation` 块按全局序命中 fno=1） | 未知文档 ⇒ `doc_not_found`；条款不存在 ⇒ `clause_not_found`；序号不存在 ⇒ `formula_not_found`；**缺 `clause` ⇒ 422** |

⚠ 写之前我以为 `/formula` 只能钉失败契约（"造不出稳定命中"），实测**能命中** ⇒ 就按成功钉。
这条记下来是因为：**"只能测失败路径"这个判断本身也要验**，否则会永久少一块覆盖。

变异 **AI1**（`/table-image` 永远走"没表格"分支）⇒ 成功那条红；**AI2**（按号定位改成查不存在的号）
⇒ 公式成功那条红；**AI3**（`clause` 加默认值，必填变可选）⇒ 422 那条红。

### 3. 证据

`pytest` **1755 passed / 3 skipped / 0 failed**（1744 → +11：并发 2 + 渲染契约 9）；
`mypy` **134 / 0**；`tsc` 0；`smoke` **EXIT=0（19 段）**；`verify:commands` **22/22**。
变异 AH1/AH2/AI1/AI2/AI3 全部按预期变红、还原字节一致。

### 4. 诚实边界

1. 分片锁是**进程内**的：多进程（真机只有一个引擎进程）或多实例并发预览同一文件仍不受保护；
   仓内没有第二个写者（预览端点只在本进程的线程池里跑）。
2. `/formula` 的成功路径依赖 middle.json 里存在按序的公式块；**识别版 PDF 的编号锚回退路径未测**。
3. 真机仍是旧进程，需重启后生效。
4. 本步**零前端改动**。


## §10.78 给审计补上"库内部重活"这一族（并修掉它的假阳性）——顺带重新盘点

**一句话**：审计的标记表原先只认**裸调用**（`requests.`/`httpx.`/`open(`），于是"每次调用都去
加载一个模型"这种最贵的活**完全扫不到**（§10.74 那个 `/health` 6.79s 就是这么漏掉的）。
补了 `model-load` / `ml-runtime` 两族标记；补的过程中又发现标记会**被注释骗到**（我自己在
`health()` 的 docstring 里写了"原先调 `is_available()`"⇒ `/health` 被误判），于是把判据改成
**只看代码**（删 docstring 与注释）。

### 1. 两处改动（都在 `scripts/audit-async-endpoints.py`）

1. **补标记族**：`model-load`（`fastembed`/`TextEmbedding`/`huggingface_hub`/`snapshot_download`/
   `sentence_transformers`/`CrossEncoder`/`reranker.`/`_get_model`/`is_available(`）与
   `ml-runtime`（`torch.`/`transformers.`/`whisper`/`jieba.`/`onnxruntime`）。
   理由写在注释里：**判据是名字**——项目自己与常见库的加载入口。
2. **只看代码**（`_code_only`）：`ast.unparse` 天然丢注释，docstring 手动摘掉。
   **假阳性实证**：改之前 `/health` 被新标记判成"要加载模型"，而它恰恰是 §10.74 **修好之后   不加载**的那一条——它命中的是 docstring 里那句话。**注释不是行为**，判据得先自己去掉。

### 2. 重新盘点（step-71 之后累计 25 条端点已转 `def`）

| 指标 | §10.71 测的基线 | 现在 | 变化 |
|---|---|---|---|
| `async def` 端点 | 140 | **115** | −25（report 6 + ingest/preview 6 + documents 5 + 诊断 1 + 落盘/导出 7） |
| T1（函数体里没有 `await`） | 89 | **66** | −23 |
| **T1 且带重标记**（"必然卡 + 真做重活"） | 36 | **16** | −20 |
| T2（有 `await` + 重标记） | 41 | **41** | 未动（本批还没碰 T2） |

**剩下的 T1+重 16 条**（下一步的清单）：其中 **13 条只有 `bulk-db`**（单行删除/更新走
`write_transaction`：正常情况是**毫秒级**，只有写锁竞争时 `BEGIN IMMEDIATE` 才可能等到
`busy_timeout=60s`）；另外 3 条是 `/clauses/office-edit/poll`（file-io+hashing）、
`/update/announce-export`（office/render）、`/clauses/patches/{patch_id}`（ml-runtime+model-load）。

**新标记命中的 12 条**（`model-load`/`ml-runtime`）：`/ks/answer`、`/chat/completions`、
`/batch/qa`、`/aliases/extract`、`/vision/locate`、`/compliance/review/{id}/execute`、
`/compliance/obligations`、`/compliance/gap-analysis`、`/clauses/patches`×2、
`/clauses/office-edit/commit`、`/ingest/bulk/{id}/resume`——这些**基本都该慢**（调模型/LLM），
它们的问题不是"不该慢"，而是"**慢的时候谁在等**"（多数已有 `def` 或走后台任务，下一步逐条判）。

### 3. 取舍：`bulk-db` 一族为什么**不**照单全改

单行 `DELETE`/`UPDATE` 的同步写事务正常是**毫秒级**，把 13 条全改成 `def` 的收益接近于零；
而它真正危险的那一面（写锁竞争最长等 60s）**和是否 `def` 无关**——`def` 只保证"等的时候不冻结
事件循环"。所以这一族的正确做法是：**先量一条代表的争用代价**（下一步），再决定是否值得动。
本步**没有**顺手全改：照单全改会让闸门表变成"什么都往里塞"，那就失去筛选意义了。

### 4. 证据

`scripts/audit-async-endpoints.py` 重跑（只读、临时 `KS_DATA_DIR`、约 3s）；
`/health` 的假阳性已消失（13 → 12 条命中）。
⚠ **收益更正**（独立复核 b13 的 LOW-2）：本节原先只写了 `/health` 那一条，把 `_code_only()`
的收益**写小了**——复核逐条比对标记集合，实测它一共改了 **7 行**：
`/health` 的 `model-load` + **5 处 `pdf/ocr`** + **1 处 `hashing`**（都不只是"假阳性"，
而是**真把注释里的词当成了代码行为**）。`unresolved` 两种跑法都是 2045（自洽）。
本步**零产品代码改动**（只改审计工具），
所以门禁数字与 §10.77 一致：`pytest` **1755 / 3 skipped**、`mypy` **134 / 0**、`tsc` 0、
`smoke` EXIT=0（19 段）、`verify:commands` 22/22。

### 5. 诚实边界

1. 标记仍是**启发式**：按名字匹配，且深度上限 7 会截断长链；`unresolved` **2045** 处
   （"扫不到 ≠ 没有"）。
2. 新标记族会**多报**（凡调用链上出现过 `is_available(`/`_get_model` 的端点都会亮），
   所以它只用于**排序**，实测仍是唯一裁决。
3. 本步只做"看得更准"，**没有**改变任何端点行为。


## §10.79 T2 批次：25 条"只 await 一下 body 就在做重活"的端点改 `def` —— 并加了一条**能自己发现同类**的通则闸门

**一句话**：把"`async def` 里唯一的 `await` 只是 `request.json()`，读完 body 全是同步重活"的
**25 条**端点（LLM 调用 / 抽别名 / 快照落盘 / 包导入导出 / 网络探测 / 重算向量 …）一次收口，
body 改走函数签名；并且这次**没有**再抄一份 24 行白名单，而是加了一条**通则闸门**
（`test_async_endpoints_that_only_read_body_are_not_heavy`）——它用审计的标记族扫整个 API 面，
**将来谁再写一条同族端点会自动红**。

> ⚠ **计数更正**（独立复核 b14 的 LOW-1，2026-09-18）：本节原先写"**24 条**（20 条 T2 + 4 条
> 闸门抓出来的）"，**两个数字都错**。按 `git show d43d14f -- src/core/api/` 逐个数
> `async def` → `def`：**实际转了 25 条** = 20 条 T2 + **5** 条闸门抓出来的
> （原文那个 bullet 自己就列了 **5** 个路径，只是前面的数字写成 4——**同一行里自相矛盾**）。
> 下面的正文已按实测改正；"24"这个数字的来历是**新增测试条数**（23 条逐条参数 + 1 条通则）
> 与**转换条数**被我混为一谈，见 §6 与 §8。

### 1. 先说分类：43 条"只读 body"，为什么只改 25 条

全库 `async def` 里"唯一的 await 是读 body"的有 **43 条**。按 §10.78 定的取舍：
**只改"带重标记且不只是 `bulk-db`"的那些**（单行写事务是毫秒级，全改的收益≈0 且会把闸门表塞成
"什么都进"）。最终改 **25 条**（20 条 T2 + 5 条在这次核对中**被闸门抓出来的**）：

- **T2（40 条里的 20 条）**：`clauses/patches`(POST)｜`compliance/obligations`｜`gap-analysis`｜
  `aliases/extract`｜`ks/answer`｜`documents/{old}/migrate-patches`｜`clauses/{id}/office-edit`｜
  `office-edit/commit`｜`batch/qa`｜`vision/locate`｜`snapshots`(POST)｜`announce-sources`(POST/PUT)｜
  `discover/classify`｜`ingest/bulk`｜`ingest/bulk/{id}/resume`｜`data/package/export`｜
  `data/package/import`｜`settings/api-config`(PUT)｜`settings/api-config/test`
- **闸门抓出来的 5 条**（我按路径找候选时漏掉的**同路径兄弟/纯 T1**）：
  `settings/api-config`(**GET** 要读凭据文件)｜`announce-sources`(**GET** 要读配置)｜
  `clauses/office-edit/poll`(读会话文件 + 比哈希)｜`update/announce-export`(openpyxl)｜
  `clauses/patches/{patch_id}`(DELETE ⇒ `_reindex_clause_indexes` **重算 FTS + 向量**)
  —— 最后这条尤其值得记：审计的 `ml-runtime/model-load` 标记**不是误报**。


**没改的**（都写清了理由）：23 条**只有 `bulk-db`** 的（毫秒级写事务，§10.78 的取舍）、
`/chat/completions`（真异步：`anyio.to_thread` + 流式）、`/laws/*` 5 条（用 `asyncio.to_thread`
包同步活——**正确写法**，本次特意留着当范本）、`/compliance/review/{id}/execute`（SSE，见 §3）。

### 2. 怎么改的（不靠手抄，也不靠"改完再说"）

- 写了个**干跑**转换器（`var/tmp/convert-t2-batch.py`，脚手架区）：先打印**每一处要动的两行**
  （43 条里筛出 20 条），我逐条看过才 `--apply`；每步都做 `ast.parse` 语法自检。
- 转换后发现**多数原本有 `try/except` 包着读 body** ⇒ 留了个"永远不抛"的死 `try`。
  第二个脚本（`collapse-dead-try.py`）只收**纯死**的那种四行形状（收了 8 处），
  **不碰**"try 里还有别的行"的（例如 `vision_locate` 那个 `try` 还护着 `rect = body.get(...)`）——
  收那种等于顺手改行为。
- **语义变化（有意）**：坏 body 一律变成 **FastAPI 直接 422**。
  ⚠ **措辞更正**（独立复核 b13 的 LOW-1）：本节原先写"从'被 `except` 吞成空 body'（或 500）
  变成 422"——**只对了一半**。这 25 条里**有 `try/except` 的那些**改前确实是"吞成空 body"（200）；
  **没有的**（例如 §10.76 的 `/export/citations`）改前是**未捕获异常 → 500**，连"没有 body"也是 500。
  所以正确说法是：**改前两种形状（200-空 body / 500），改后一律 422**。方向不变，
  事实以复核实测为准（它三种输入各发了一次）。
  与 §10.71/§10.76 同口径。`routes_settings.api_config_put` 原来那句自定义 422
  （"body 必须为 JSON"）随之删掉（它已成死代码）——全库无测试钉那句话（已 grep 确认）。
- **mypy 抓到 2 处**（转型带来的真实收紧）：`announce.add_source(body.get("name"), ...)`
  ——`body` 从 `Any` 变成 `dict | None` ⇒ `Any | None` 传给 `str` 形参。修法是**保留宽松传参** +
  `# type: ignore[arg-type]` 并写清理由：**缺参/非字符串的校验在 `add_source` 内部做**
  （`_validate_source_payload` → 422/UPD-3008），先猜会把"缺 name"变成 `""`，那是**改行为**。

### 3. 通则闸门（本步最有价值的产出）

```
async def  +  唯一的 await 只是读 body  +  可达路径上有"重"标记（且不只是 bulk-db）
⇒ 必须是 def（白名单只有一条，且必须写理由）
```
它 import 审计脚本的标记族（含 §10.78 新加的 `model-load`/`ml-runtime`）在**整个 API 面**上跑，
所以**不用维护白名单**。白名单目前**只有一条**：
`/api/v1/compliance/review/{task_id}/execute` —— **SSE**：外层虽然只 `await request.json()`，
但重活在**嵌套的 `async def event_stream()`** 里；把外层改 `def` 解决不了任何事。
**这是一条新登记的缺陷**：要治得把那个生成器改成**同步生成器**（Starlette 会用线程池迭代它），
属于需要单独验 SSE 行为的改动 —— 留给下一步。

变异证明它真的承重：**AJ5** 把 `aliases/extract` 还原成完整旧形状（`async def` + `await
request.json()`），**只跑通则那条** ⇒ RED（指名该端点）。AJ1–AJ4 分别还原 3 个不同文件的端点
⇒ 逐条表 RED。

### 4. 量到的

`POST /api/v1/snapshots`（造快照 = 读库 + sha256 + 落盘），量具新增 `snapshot_create` 用例
（种 2 万条条款把临时库撑到 MB 级）：

| | 改前 | 改后 |
|---|---|---|
| 请求耗时 | 0.0324s | 0.0343s |
| 事件循环最大空档 | 0.0266s | 0.0158s（空闲基线 0.0065s） |

⚠ **本机量的是"小库"**：真机库 **2.2GB**，那条路是**秒级**——这个用例给的是**下界**。
本批其余端点的收益同理（LLM 调用/向量重算/包导入导出在真机上都是秒级）。

### 5. 终盘（累计）

| 指标 | §10.71 基线 | 现在 |
|---|---|---|
| `async def` 端点 | 140 | **90** |
| T1（函数体无 `await`） | 89 | **61** |
| **T1 且重** | 36 | **13**（**全部**只剩 `bulk-db`，按取舍故意不转） |
| T2（有 `await` + 重） | 41 | **21**（19 纯 bulk-db + `/execute` SSE + 1） |

### 6. 证据

`pytest` **1779 passed / 3 skipped / 0 failed**（1755 → **+24** = 23 条逐条参数
+ 1 条通则闸门）；`mypy` **134 / 0**；`tsc` 0；`smoke` EXIT=0（19 段）；
`verify:commands` 22/22。变异 AJ1–AJ5 全 RED、还原字节一致。转换器干跑记录与审计 JSON 在
`var/tmp/`（脚手架区）。

⚠ **"+24"与"转 25 条"不矛盾，别再把它们混起来**（b14 的 LOW-1 就是这么来的）：
逐条参数表只加了 **23** 条，因为 `settings/api-config`(GET) 与 `announce-sources`(GET)
这两个**兄弟方法**的**路径**已经在表里了（`/settings/api-config`、`/update/announce-sources`
各只有**一行**参数），所以 25 条转换只产生 23 行参数；再加通则那条 = 24 条新测试。

⚠ **更进一步：那 2 条兄弟方法当时其实"没被表验到"**（b14 的 LOW-2）：`test_declared_sync`
原先只看 `routes[0]`（同一路径有多个方法时只有第一个 Route 对象被断言）⇒ 若只把 GET 那条改回
`async def`，表仍然 GREEN。**§10.85 已改成遍历该路径上的全部 Route 对象**（并配了变异）。


### 7. 诚实边界

1. `/execute`（SSE）**没修**（见 §3），已登记；这是本批唯一"知道有问题但故意留着"的。
2. 23 条纯 `bulk-db` 的也**没转**（§10.78 的取舍），它们**不在**通则闸门的判据里
   （闸门把 `bulk-db` 排除），所以不会造成"闸门一直红"的噪声。
   ⚠ **这句已过时**（独立复核 b15 的 LOW-1，2026-09-18）：`bulk-db` 的排除**只在 §10.79 那一版**
   成立——**§10.83 起"不再排除"并把那一族 32 条全部转成 `def`**，§10.86 起"重标记"更不再是闸门
   的必要条件。保留这句是为了不改写历史章节，但读者请以 **§10.83 / §10.86** 为准。
3. 量的是小库（§4）；真机重启后才生效。
4. 本步**零前端改动**。


## §10.80 SSE 那条：把"没有 await 的异步生成器"修掉，并加第二条通则闸门

**一句话**：`/api/v1/compliance/review/{task_id}/execute` 原先外层 `async def`（唯一 await 是读
body）、内层 `async def event_stream()` **一个 `await` 都没有** ⇒ 它**逐点调 LLM** 的评审
（几十秒到几分钟）**全程在事件循环里跑**，把整个引擎冻住。改成"外层 `def` + **同步生成器**"
（`StreamingResponse` 对非异步可迭代对象会 `iterate_in_threadpool`），并补了一条
**零假阳性的通则闸门**让这个形状以后自动红。

### 1. 为什么前面所有判据都看不见它

| 判据 | 为什么漏 |
|---|---|
| T1（`async def` 且**函数体**无 await） | 外层**有** await（`request.json()`）⇒ 不算 T1 |
| 通则之一（唯一 await 是读 body + 带重标记） | 它**命中**了！但当时把它当"SSE 例外"**白名单**了（§10.79） |
| `bulk-db`/`model-load` 标记 | 命中，但标记只影响"要不要看一眼" |

真正的洞在**嵌套生成器**里：`StreamingResponse` 对**异步**可迭代对象是 `async for` 直接迭代
（starlette 1.6 `stream_response`），所以"没有 await 的 async 生成器"每次 `yield` 都占着事件循环。
**§10.79 的白名单只是把症状登记了，没有治它**——这一步治了，并把白名单**清空**。

### 2. 改法（两行 + 一段理由）

```python
def execute_review(task_id: str, body: dict | None = None):   # 外层：def + 签名取 body
    ...
    def event_stream():                                        # 内层：**同步**生成器
        for item in run_review(task_id, confirmed):
            yield _sse("point_verdict", item)
```
`StreamingResponse(event_stream(), ...)`：starlette 1.6 的 `__init__` 里就一句
`if isinstance(content, AsyncIterable): ... else: self.body_iterator = iterate_in_threadpool(content)`
⇒ 同步生成器**逐条在线程池里产出**，事件循环全程空闲；SSE 的**事件顺序与分帧逐字不变**
（`tests/test_compliance.py::test_review_api_sse` 断言 `events[0]=="point_verdict"`、
`events[-2]=="report_ready"`、`events[-1]=="done"` ⇒ 55 passed）。

### 3. 新闸门：通则之二（AST，零假阳性）

```python
# 端点里嵌套的 async def 生成器（体内含 yield）若整段没有 Await ⇒ 红
```
理由：**异步生成器**逐条产出，没有 await 就等于**每条都在事件循环里**；而 `StreamingResponse`
对同步生成器会用线程池 ⇒ 这种形状**应当写成 `def` 生成器**。
它不像"重标记"那样是启发式：**有 await 的异步生成器完全不受影响**，所以**没有白名单**。

变异：**AK2**（把内层生成器改回 `async def`）⇒ 通则之二红（指名 `event_stream()`）；
**AK1**（外层改回 `async def`）⇒ 逐条表红（我复核了那句失败消息确实是
`做同步重活，必须是 def` 那条断言，不是"路由不存在"）。

### 4. 证据

`pytest` **1781 passed / 3 skipped / 0 failed**（1779 → +2：SSE 逐条 + 通则之二）；
`mypy` **134 / 0**；`tsc` 0；`smoke` EXIT=0（19 段）；`verify:commands` 22/22。
变异 AK1/AK2 全 RED、还原字节一致。

### 5. 诚实边界

1. 量具**没有**为这条端点造 before/after 数字（它要跑真 LLM 逐点评审才慢）——本步的证据是
   **结构性的**（AST 判据 + SSE 测试的语义等价），不是时长实测。这是本步唯一"没量"的地方，
   写在这里而不是含糊过去。
2. 同步生成器在**线程池**里迭代 ⇒ 它现在也要吃 §10.81 要处理的那口池子的额度（见下一条）。
3. 真机重启后才生效。


## §10.81 处理复核 b13 的发现：线程池容量有界（MEDIUM-1）+ 三处措辞更正 + 流程纪律加一条

**一句话**：b13 报的 8 条声称**全部 CONFIRMED**，但它找出一个**我自己没写的 MEDIUM**：
去阻塞化把一批长活搬进了 anyio 那口**默认 40 令牌、且全仓无闸门**的共享线程池 ⇒
**40 个 MinerU 子进程/40 份渲染可以同时来**（这是改动前不存在的形态）。本步给它**显式收个上限**，
并把三处"理由写错"的地方按实测更正。

### 1. MEDIUM-1：线程池必须显式有界（`THREADPOOL_TOKENS = 16`）

b13 的实测（进程内 ASGI，受害者是**真实产品 `def` 端点** `/ingest/preview/inbox`）：

| 在飞的慢 `def` 请求 | 受害者耗时 |
|---|---|
| 0 | 0.0105s |
| 39 | 0.0014s（**不受影响**） |
| **40** | **0.6595s** |
| 45 | 0.6702s |
| （对照）`async def` 受害者 | 0.0007s 不受影响 |

机制：`def` 端点在 **anyio 默认线程池**（40 令牌）里跑；池满后**开始排队**。
**关键不是延迟而是形态**：改前这些活在事件循环里**天然串行（并发度 1）**，改后允许 **40 条同时跑**
——`ingest/preview` 的最坏情况是"40 个解析子进程同时启动"，那是内存/CPU 的风暴。
而 §10.73 §6 的"连带核查"表只核查了锁/sqlite/临时目录，**漏了线程池容量**（这一栏现已补上）。

修法：
```python
THREADPOOL_TOKENS = 16          # anyio 默认 40 → 显式收窄
def bound_threadpool_once():    # 幂等；anyio 的 limiter 是 RunVar ⇒ 只能在事件循环里设
    ...
```
挂在**已有的 HTTP 中间件**里（每请求一次、幂等、跑在循环内）——而不是 `create_app()`（同步上下文）
也不是 lifespan（`httpx.ASGITransport` **默认不跑 lifespan**，挂那里会让量具与真实路径行为不一致）。

**取 16 的理由**：单用户桌面场景同时发起的重活很少超过个位数；16 既掐掉"40 子进程"的风暴，
又给**文件流式读取**（`FileResponse` 也吃这口池子）留了余量。
**取舍（诚实登记）**：池子更小 ⇒ "若干条长解析在飞时加载 PDF"会排队。要同时治好两头，得给
**最长的那几条**（`ingest/preview*`、`bulk`、PDF 渲染）挂**专用** `CapacityLimiter`、
留一条"文件流"专用位——那是**下一步**（见 §5），不在本步假装解决。

闸门 `tests/test_threadpool_bound.py`（3 条，**确定性、不计时**）：
收窄函数真的把 limiter 设成常量（循环内读回来核对）、常量 ≤ 40 且 ≠ 40（"收窄成 40 = 没收窄"）、
**每个请求都会走一次收窄**（拿替身记录调用 ⇒ 挡"有人把中间件那行删了"）。

### 2. 三处措辞更正（b13 的 LOW-1/LOW-2/LOW-3）

| 编号 | 我原来写的 | 实测（b13） | 更正 |
|---|---|---|---|
| **LOW-1** | §10.76：`/export/citations` 改前"非法 JSON 被 `except` **吞成空 body** 照常 200" | **错**：这条**从来没有** `except` ⇒ 改前**坏 JSON 与"没有 body"都是未捕获异常 → 500**（三种输入实测） | 改 `server.py` docstring、`test_phase7.py` docstring、§10.76 表格、§10.79 的"语义变化"段、台账第 22 条：**正确说法是"改前两种形状（200-空 body / 500），改后一律 422"** |
| **LOW-2** | §10.78：`_code_only()` 的收益 = `/health` 那一条假阳性 | 写**小**了：逐条比对标记集合，它一共改了 **7 行**（`/health` 的 `model-load` + **5 处 `pdf/ocr`** + **1 处 `hashing`**）——那些是**真把注释里的词当成了代码行为** | §10.78 §4 已按实测改写 |
| **LOW-3** | 量具 `document_figure` 报 `pages` | **假数据**：`ctx` 里根本没有 `pages` 键 ⇒ 永远回落 150 页，于是 `--pages 12` 与 `--pages 150` 生成**逐字节相同**的 PDF，而输出照抄 CLI 参数报页数 | 修：`ctx["pages"]` 补上 + 输出改成 **`pages(参数)` 与 `pages(实际)` 两个都报**（实际页数用 fitz 数）；实测 `--pages 12` → 12 页/91549B、`--pages 60` → 60 页/489214B |

### 3. 流程纪律加一条（b13 的 INFO-1，当场就撞上了）

b13 复核期间**主检出又被另一个工作流（同一晚的 §10.79）改了 5 个文件**；它第一次在本工作树上
普查路由量到 **95 条 async 端点**、与文档写明的 **115** 不符——**差点报出一个假的 REFUTED**，
改用 `git archive` 提取 pristine 提交后才逐字复现。
⇒ 已写进 §五第 6 条：**verifier 必须在冻结提交的提取树上验证**，报告**首尾各记一次
`git rev-parse HEAD` + `git status --short`**。理由一句话：**"在同一个目录里边改边验"是双向污染**。

### 4. 顺带修掉 b13 的 INFO-4（既有问题，但它违反本项目自己的纪律）

`tests/test_golden_gate.py` 直接在**仓库内**的 `eval/golden/knowledge-snapshot.db` 上开库，
而 `get_db_connection()` 会对库跑 `PRAGMA journal_mode=WAL`（**那是写**）⇒ 留下 `-shm`/`-wal`，
**违反纪律 5「代码树零运行产物」**。修：跑前**拷到临时目录**，并在收尾 `set_db_override(None)`
（复核同一点时发现：那个覆盖是**模块级全局**，不复位会**泄给后面的测试**，让它们读到快照库）。
已验证：跑完 `eval/golden/` 里只剩三个原有文件、无 `-wal/-shm`。

### 5. b13 的判定与我下一步

**8 条声称全部 CONFIRMED**（含 §10.78 盘点表逐字复现、**C2 假绿的 before/after 同机当场跑出**、
16 条变异全红在预期断言且**字节级还原**：提取树 432 文件 0 不一致）。它自己列的 honest boundaries
（真机未重启、6.79s 用 0.8s 替身复现机制、pristine 树 1754 passed/4 skipped 而文档 1755/3——
差异在"跳过哪一条"、0 failed 一致）**我全部接受，不改口径**。

**下一步**：① 给最长的几条挂**专用** `CapacityLimiter`（留出文件流专用位，见 §1 的取舍）；
② 真机重启后端到端复验（需业主）；③ b13 未覆盖的：`/formula` 识别版回退、C2 的 FAIL 分支、
uvicorn 下 `FileResponse` 语义、`dry_run` 真实撕裂读。

### 6. 证据

`pytest` **1784 passed / 3 skipped / 0 failed**（1781 → +3：线程池三条）；`mypy` **134 / 0**；
`tsc` 0；`smoke` EXIT=0（19 段）；`verify:commands` 22/22；
`eval/golden/` 跑后无 `-wal/-shm`（新增验证）。


## §10.82 重活专用闸门：让长活排队时**不占线程**，给文件流留出位子

**一句话**：§10.81 那把"线程池 16"治住了 40 子进程的风暴，但把**长活**和**文件流式读取**
（`FileResponse` 也吃同一口池子）放进同一个队——16 条长解析在飞时，加载一份 PDF 就得排队
（最长可能等到一条 135s 的预览跑完）。这一步把两类活**分开**：重活最多 **4** 条，
其余 12 个线程留给文件流与廉价 DB；**排队发生在中间件里的 `await`（异步等，不占线程）**。

### 1. 做法（一处路径表 + 中间件几行）

```python
HEAVY_TOKENS = 4
HEAVY_PREFIXES = (...)     # ingest/preview、ingest/bulk、documents/、materials/、
                           # report/、export/、snapshots、ks/answer、batch/qa、
                           # compliance/review、vision/locate、aliases/extract、
                           # data/package/、update/report
HEAVY_SKIP = ("/api/v1/ingest/preview/inbox",)   # 廉价 listing：**闸门自己不许造排队**
```
中间件里：命中重活路径 ⇒ `await limiter.acquire()` → `call_next` → `finally: release()`。
limiter 按 **loop** 缓存（anyio 的 limiter 绑后端/循环；测试里一个进程会开很多循环）。

**为什么"异步等"是要点**：等的时候**不占线程池额度**，所以"排队"本身不再挤占文件流的位子
——这正是 §10.81 §1 登记的取舍的另一半。

### 2. 闸门（4 条，其中一条是**行为级**）

| 判据 | 挡的是什么 |
|---|---|
| 路径表覆盖那些被量出秒级的端点 | 表被改窄（漏掉一族） |
| 轻活路径**不动**闸门 | 误把轻活也关进去 |
| 重活路径**确实** acquire/release | 中间件那几行被顺手删掉（**最容易的坏法**） |
| **12 条并发重活的峰值 == `HEAVY_TOKENS`** | 令牌数被改大（接线全对但闸门等于没有）；这条用替身替换 `/ingest/preview` 真正调用的函数、真发 12 条并发请求 |
| `HEAVY_TOKENS < THREADPOOL_TOKENS` | "留位"这件事被抹掉 |

变异：**AL1** 让 `is_heavy_path` 永远 False ⇒ 4 条同时红（含行为级）；
**AL2** 把 `HEAVY_TOKENS` 抬到 16 ⇒ "必须小于线程池上限"红。

⚠ 写这条行为级用例时踩了一个**骗过接线断言**的坑：我第一版写 `create_app("t")` 而请求头用的是
`test-token-123` ⇒ 12 条全部 **401**、替身一次没被调用（峰值 0）。**401 也会经过中间件**，
所以"接线断言"照样绿，只有行为级那条才把它抓出来。已写进测试注释。

### 3. 一个**未被复现的偶发失败**（如实记）

本步跑全量门禁时，`npm --prefix plugin run smoke` **EXIT=1**；但我那条命令只记了退出码、
**没留输出**（我的取证失误）。随后**连续三次重跑全部 EXIT=0**，11 段汇总行全 PASS。
本步 diff 只有 `src/core/api/server.py` 与两个测试文件（**零前端改动**），所以无法归因于本步。
⇒ 按"假绿/偶发"惯例登记：**未复现、未归因**；教训是**冒烟失败时必须抓输出**，
只读 `$LASTEXITCODE` 等于把证据丢掉（下次遇到要能指出是哪一段、哪条断言）。

### 4. 证据

`pytest` **1789 passed / 3 skipped / 0 failed**（1784 → +5：闸门 4 条 + 廉价例外 1 条——
其中行为级那条真的造了 12 条并发）；`mypy` **134 / 0**；`tsc` 0；
`smoke` **EXIT=0（19 段，连跑 3 次）**；`verify:commands` 22/22。变异 AL1/AL2 全 RED。

### 5. 诚实边界

1. 闸门是**进程内**的：多实例/多进程不共享（真机只有一个引擎进程）。
2. `HEAVY_TOKENS=4` 是**取值判断**（单用户桌面场景重活通常 1–2 条），不是量出来的最优值；
   真机并发行为仍待重启后端到端观察。
3. 量具**没有**为这条做"受害者延迟"曲线（b13 那套 39/40 条的实验我没重做）；
   本步的证据是**行为级并发峰值**（峰值恰好 4）与接线，不是延迟数字。
4. 真机重启后才生效。


## §10.83 `bulk-db` 一族：**先量了争用代价，再全部转 `def`** —— 并把通则收成"单一条规则"

**一句话**：§10.78 当时决定"`bulk-db` 一族先别照单全改、量一条代表的争用代价再定"。本步量了：
**无争用 0.0013s（可忽略），但另一个写者持锁 0.5s 时，这个 `async` 端点把事件循环堵了 0.5489s**
——而 `busy_timeout = 60s`，所以真机上"批量入库持锁"期间点一下删除，**整个引擎可以静默死几十秒**。
于是把剩下 **32 条**（T1 无 body 19 条 + T2 只读 body 13 条）全部转 `def`，
并把通则**加强成单一条规则**（含 T1、含 `bulk-db`）——现在 `async` 且带重标记的端点**只剩 1 条**：
`/chat/completions`（真异步：流式 + `anyio.to_thread`）。

### 1. 取证（`var/tmp/probe-write-lock.py`，只碰临时库）

用例：`DELETE /api/v1/projects/{pid}/clauses/{rev}`（`bulk-db` 家族的典型形状），
另一个连接 `BEGIN IMMEDIATE` 持写锁 0.5s。

| 用例 | HTTP | 请求耗时 | 事件循环空档 | 空闲基线 |
|---|---|---|---|---|
| A 无争用 | 200 | 0.0013s | **0.0011s** | 0.0160s |
| B 争用（另一写者持锁 0.5s） | 200 | 0.5492s | **0.5489s** | 0.0119s |

⇒ 结论清楚了：**常见情况确实可忽略（§10.78 的判断没错），但尾风险是"锁等多久就堵多久"**，
上限是 `busy_timeout=60000ms`。转换成本为零（同样的两行）⇒ **该转**。

### 2. 转换（自动选取 + 干跑，不再手抄名单）

`var/tmp/convert-remaining.py` 的选择规则 = **两条通则的并集**，直接跑审计模块：
```
async def  ∧  带"重"标记（非 fs-copy）  ∧  （函数体没有 await ∨ 唯一 await 是读 body）
```
干跑打印 **32 条**（`server.py` 22 + `routes_update.py` 10；两种形状都有），我逐条看过才 `--apply`；
每步 `ast.parse` 自检；改完再跑一次"残留 `request` 引用"检查（**0 处**——这一点很要紧：
把这些端点的 `request: Request` 参数换成 `body: dict | None = None` 时，若函数体里还有别处用
`request`，就会 `NameError`）。

### 3. 通则加强：从"body-only"到"**从不真正让出控制权**"

`test_async_endpoints_that_only_read_body_are_not_heavy` 现在的判据：
**`async def` ∧（没有 `await` ∨ `await` 全是读 body）∧ 带重标记（`fs-copy` 除外，`bulk-db` **不再**排除）**
⇒ 必须是 `def`。并且加了**反向断言** `scanned >= 40`（枚举坏掉时"全绿"没有意义）。
白名单 `_BODY_ONLY_ASYNC_ALLOWLIST` **目前是空集**——这本身是个好信号：该转的都转了。

变异（全 RED、逐字节还原）：**AM1** 把无 body 的 `del_bookmark` 改回 `async def`；
**AM2** 把有 body 的 `add_bookmark` 还原成 `async def + await request.json()`；
**AM3** 把另一个文件里的 `subscriptions_put` 改回 `async def`。

### 4. 终盘（累计，从 §10.71 的基线起）

| 指标 | §10.71 基线 | 现在 |
|---|---|---|
| `async def` 端点 | 140 | **57** |
| T1（函数体无 `await`） | 89 | **48**（**全部零重标记**：廉价 DB 读 / `FileResponse`） |
| **T1 且重** | 36 | **0** |
| **T2+重** | 41 | **1**（`/chat/completions`，真异步） |
| `async` 且带重标记 | — | **1** |

剩下的 56 条 `async` 端点**全部不带重标记**（`/health`、`/documents`、`/clauses/resolve`、
`/documents/{id}/file`…）⇒ 它们是"查一下、返回"，留在事件循环里是对的。

### 5. 证据

`pytest` **1789 passed / 3 skipped / 0 failed**；`mypy` **134 / 0**；`tsc` 0；
`smoke` EXIT=0（19 段）；`verify:commands` 22/22。变异 AM1–AM3 全 RED。
审计重跑（`var/tmp/audit-after-83.json`）：`async` 57 / T1 48 / **T1+重 0** / T2+重 1。

### 6. 诚实边界

1. 争用是**人为制造**的（另一连接持锁）；真机上"批量入库持锁"的**实际时长未测**，
   但上限由 `busy_timeout=60s` 界定。
2. 转换**让进程内并发写成为可能**（改前事件循环把它们串行化了）：两条写请求现在可以在两个
   工作线程里同时进 DB，一条等锁。WAL + `busy_timeout` 正是为此准备的，但**真机并发写行为未测**。
3. 这 32 条里**没有一条**做了"改前/改后空档"的逐条实测（做的是那一条代表 + 结构性判据）；
   它们的收益只在**争用**时体现，无争用时本来就 1ms。
4. 真机重启后才生效。


## §10.84 真 uvicorn 下的引擎验证：进程内量具覆盖不到的那一层（4/4 PASS）

**一句话**：§10.73–§10.83 的 before/after 全部来自 `httpx.ASGITransport`（**进程内**调用）——
没有真 socket、没有 uvicorn 的并发限制、`FileResponse` 也没真流过一次。真机端到端要等业主重启
两个门，在那之前能自己做的是：**另起一个独立引擎实例**（绝不碰在跑的那个），
验那些**只有真 server 才能暴露**的东西。4 项全过。

### 1. 安全边界（硬约束，写进脚本 docstring）

- 只监听 `127.0.0.1` + **随机空闲端口**；`KS_DATA_DIR` 指向**临时目录** ⇒ 不碰生产库、不占引擎端口；
- **绝不** kill 既有引擎 / DSH 宿主：只 kill 本脚本自己 spawn 的子进程（`finally` 里 `terminate`）；
- 只读：只写自己的临时目录。

⚠ **与真入口的刻意差异**：不用 `python -m src.core.main`（它会**预热流程图 OCR**，后台线程加载
RapidOCR、冷启动约 60s，会污染计时），改用等价启动器：同样 `bind_random()`（随机端口 + 一次性 token）
+ `create_app(token)` + 真 uvicorn，只去掉预热。差异写在脚本里，不藏着。

### 2. 结果（2026-09-18 复跑，`--heavy 12`）

| 检查项 | 结果 | 实测 |
|---|---|---|
| `/health` 廉价三态且 <1s | ✅ | `status=200 vector_engine=unknown 0.0014s`（没在健康检查里加载模型） |
| `FileResponse` 字节数/sha256 与磁盘一致 | ✅ | `HTTP=200 85483B vs 85483B`（`def` 化 + 中间件改造都没把它弄坏） |
| 12 条重活在飞时 `/health` 仍毫秒级 | ✅ | `p95=0.0500s max=0.0500s heavy_http=[200]` |
| 坏 JSON ⇒ 422（body 走签名后的契约） | ✅ | `HTTP=422` |

### 3. 诚实边界

1. **SSE 那条没做**：要种一整套合规评审数据，属 `tests/test_compliance.py` 的覆盖，本脚本不重复造
   ——**如实说明，不假装验过**。
2. **这仍不是"真机端到端"**：是同一台机器上的**另一个**进程 + 真 socket；业主重启后才是。
3. 重活用**合成的 12 页 PDF**，真机文档更重 ⇒ `p95=0.05s` 只说明"轻请求没被拖到秒级"，
   不是真机负载下的上界。
4. ⚠ **本条是"迟记"**：脚本在 step-83 那个窗口就写好并用过（当时是它给出的 4/4），
   但**既没提交进仓库、也没写章节**，脚本 docstring 里还引用了不存在的"§10.84"。
   本步补上：脚本入库 + 本节 + 台账第 30 条。**这是流程失误**（工具与结论必须同批落盘），
   记在这里而不是悄悄补掉。


## §10.85 处理复核 b14 的发现：闸门对流式不生效（MEDIUM-1）、判据能被注释骗（MEDIUM-2）+ 4 条 LOW

**一句话**：独立复核 b14（冻结在 `verify-freeze-b14` = `0efbcd0`）判 **2 MEDIUM + 4 LOW**，
并自己做了 16 个变异、逐字节还原。两条 MEDIUM 都是"**自称已消除的形状换个入口回来**"：
① 重活闸门**对流式响应完全不生效**（`BaseHTTPMiddleware.call_next` 在 `http.response.start`
就返回 ⇒ 令牌在响应体开流前被放掉；实测 12 条并发非流式峰值 **4**、流式峰值 **12**，
等量工作下受害者放大 **×477–483**）；② 通则闸门的"只读 body"判据读的是**源码文本** ⇒
**一句含 `await ` 的 docstring/注释就能静默豁免整个端点**。本步把两条都收口，并顺手修掉 4 条 LOW。

### 1. MEDIUM-1：闸门改成**纯 ASGI** 中间件

`@app.middleware("http")` 走 `BaseHTTPMiddleware`，`call_next` 只等到 `http.response.start`；
于是中间件 `finally: release()` 在**响应体开流之前**执行——对 `/compliance/review/{id}/execute`
（逐点 LLM 的 SSE）与 `/ks/answer` 这类**流式重活**，闸门等于不存在。

修法：`class _HeavyGateMiddleware`（**纯 ASGI**，`await self.app(scope, receive, send)`）——
纯 ASGI 的 `await self.app(...)` 会**一直等到响应体发完**（router 内部
`await response(scope, receive, send)`），`finally` 的释放时机因此正确；**另加**一条更早的
精确释放：在 `http.response.body` 且 `more_body=False` 时释放（用 `released` 标志保证**只放一次**）。
中间件栈：`_HeavyGateMiddleware → BaseHTTPMiddleware(auth) → CORSMiddleware`。

**为什么这条不改判据、只改中间件**：流式端点"真的会 await"（`/chat/completions` 的
`await anyio.to_thread.run_sync(...)`），所以它不是"从不 yield"那一族；它的问题是**令牌持有时间**
——那只能由中间件治。两者的分工写在 `never_yields()` 的 docstring 里。

### 2. MEDIUM-2：两条通则的判据从"读文本"改成 **AST**

判据原先写在测试里：`awaits = [ln for ln in src.splitlines() if "await " in ln]`。
复核的对照实验：同一形状、只改 docstring/注释文本 ⇒ 闸门 GREEN（N3/N4 两个变异）。
而审计脚本的 `_code_only()` **早就**为同一课修过（"注释不是行为"）——**闸门自己没吃这一课**。

修法：把两条判据搬进 `scripts/audit-async-endpoints.py`，都用 AST 实现：
`never_yields(src)`（数 `Await` 节点；每个都必须是 `xxx.json()`/`xxx.body()`）
与 `nested_async_gen_without_await(src)`（`AsyncFunctionDef` + 含 `Yield` 且无 `Await`）。

⚠ **一处必须写清的范围判断**：`never_yields` 数的是**整段源码里**的 `Await`，**包含嵌套函数**。
这不是漏网，是**有意**：`/api/v1/chat/completions` 外层唯一的 `await` 只是读 body，而它的嵌套
`async def event_stream()` 里有 `await anyio.to_thread.run_sync(...)` ⇒ 这条请求在**流式迭代**
期间**真会**让出事件循环；只数外层会把它误判成"从不 yield"（AST 版第一稿正是这样，一跑就红）。
真正"从不 yield"的坏形状（外层读 body + 嵌套**同步**生成器/纯同步体）**没有任何非读-body 的
`await`**，照样命中。这个取舍写在函数 docstring 里。

### 3. 四条 LOW + 两条 INFO

| 编号 | 一句话 | 处置 |
|---|---|---|
| b14-LOW-1 | §10.79 的数量词与 diff 不符："24 条 / 4 条"实为 **25 条 / 5 条**（`git show d43d14f` 正则计数：删 `async def` **25** 个；§1 标题写"4 条"却**列了 5 条**） | ✅ §10.79 正文/标题/§6 按实测改写 + 加"计数更正"块；台账第 25 条同步 |
| b14-LOW-2 | `test_declared_sync` 按**路径**取 `routes[0]` ⇒ 同路径**兄弟方法**逃逸（b14 的 S1 变异：`PUT /settings/api-config` 还原成 `async def` ⇒ 该表 **GREEN**，只被通则兜住） | ✅ 表改成 **`(路径, 方法)`** 参数（45 条路径 → 48 条参数）；断言按方法选 Route 并要求唯一匹配 |
| b14-LOW-3 | `announce_export` **双 docstring**（只有第一个是 `__doc__`，第二个是死字符串） | ✅ 合并成一条；并加**全库**结构判据 `test_没有函数叠着两个_docstring`（扫 `src/**/*.py`） |
| b14-LOW-4 | `_heavy_limiters` 按 `id(loop)` 缓存：id 复用极频繁（实测 200 循环 → **5 个不同 id**），硬拆丢令牌后新循环会拿到**陈旧 limiter** 永久排队 | ✅ 键改成**弱引用的循环对象**（`weakref.WeakKeyDictionary`）+ 判据（跑完的循环不许留在缓存里） |
| b14-INFO-1 | `test_重活闸门真的把并发卡在_HEAVY_TOKENS` 的 docstring 写"真发 **10** 条"，代码是 `HEAVY_TOKENS * 3` = **12** 条 | ✅ docstring 改成"`HEAVY_TOKENS * 3` 条"，并补上"这条看不见流式"的说明 |
| b14-INFO-4 | 闸门的行为级判据**只覆盖非流式**，对 MEDIUM-1 天然不可见；建议给流式补一条行为级判据 | ✅ 新增 `test_流式响应的令牌要等响应体发完才放`（**假 ASGI app 直接驱动中间件**：分 3 块发 body，`more_body=True` 期间必须**仍持有**、最后一块才归零、且**恰好释放一次**） |
| b14-INFO-5 | 两条 MEDIUM 在冻结提交之后的 `252d5a6` 上依然存在 | ✅ 本步正是收口（`server.py` 中间件 + `tests/test_material_api.py` 判据） |
| b14-INFO-2 | LOW-3 的修复把 `"pages"` 放进 `ctx` 后，量具的 `snapshot_create` 用例也吃 `--pages`（默认 12 下行为不变，非回归） | 📝 已知的连带影响，不改（默认值不变） |
| b14-INFO-3 | 文档 `1789/3` 与复核 `1788/4` 总数一致（1792），差异是本地少下一个 reranker 模型 | 📝 接受，不改口径（b13 已登记同款） |

### 4. 变异与取证（全 RED 且命中**预期断言**，逐字节还原）

`var/tmp/mutate-step85.py`（M1–M6）：

| 变异 | 改了什么 | 红在哪条判据上 |
|---|---|---|
| **M1** | `never_yields` 顶部加 `if "await" in src: return False`（= 退回"读文本"的老判据） | `test_两条通则的判据走_AST_不会被注释骗`：**注释里出现 await 就把判据骗了** |
| **M2** | `_send` 去掉 `and not message.get("more_body")`（= 响应体没发完就放令牌，`BaseHTTPMiddleware` 的效果） | `test_流式响应的令牌要等响应体发完才放`：**流式期间令牌必须一直被持有** |
| **M3** | 外层 `finally` 无条件 `release()`（= 同一个请求放两次） | 同上：**闸门被撑大** |
| **M4** | 缓存键两处一起退回 `id(loop)` + 普通 dict（只改 getter 会造出一个新 bug ⇒ RED 但"红在别处"，第一稿踩到后就改成两处一起） | `test_闸门缓存不会把死循环留在字典里` |
| **M5** | `POST /update/announce-sources` 改回 `async def + await request.json()` | `test_declared_sync`：**POST /api/v1/update/announce-sources** |
| **M6** | `announce_export` 再叠一个 docstring | `test_没有函数叠着两个_docstring` |

**LOW-2 的取证**（`var/tmp/low2-forensics.py`，打完 M5 后逐字节还原）：同一条路径上的 Route 顺序是
`[GET(def), POST(ASYNC)]` ⇒ **旧断言（路径 + `routes[0]`）GREEN（放行）**，
**新断言（按方法选）RED（抓住）**。这就是 b14 那条 LOW 的形状。

### 5. 证据

⚠ **快照标签的编号对应**：本步的提交同时承担 §10.84 与 §10.85（§10.84 那份 uvicorn 验证
此前没有自己的提交），而 `scripts/snapshot-project.ps1` 是"最大 `step-NN` + 1" ⇒
这一步的快照标签是 **`step-84-b14-findings-closed`**（指向 **`423985a`**）。
**标签号比章节号小 1**，不是漏做快照。
⚠ **哈希更正**（独立复核 b15 的 LOW-2）：这里原写 `ec5cfc2`——那是**同一内容的更早一笔**
（打完标签后我又补了这几行说明并 amend 成 `423985a`，`ec5cfc2` 成了**游离提交**）。
标签实际指向 `423985a`，已按 `git cat-file -p step-84-b14-findings-closed` 更正。

`pytest` **1798 passed / 3 skipped / 0 failed**（1792 → 1801 收集：**+9**，精确分解 =
**3 条新的逐条参数**（多方法路径拆成 `GET/POST`、`PUT/DELETE`、`GET/PUT`）+ **2 条新的测试函数**
（`tests/test_material_api.py`）+ **4 条新的 `TestHeavyGate` 用例**（`tests/test_threadpool_bound.py`）；
⚠ 这个分解按复核 b15 的 INFO-5 更正过——原先写的"6 条新测试 + 3 条参数"与 `git show` 的
**7 个新 `def test_`** 对不上，收集数（+9）则一直是对的）；
`mypy` **134 / 0**；`tsc` 0；`smoke` **EXIT=0（19 段）**；`verify:commands` **22/22**；
真 uvicorn 验证 **4/4**（§10.84，本步复跑）。审计重跑（`var/tmp/audit-after-85.json`）：
终盘与 §10.83 一致——`async` **57** / T1 **48** / **T1+重 0** / **T2+重 1**（`/chat/completions`），
说明本步只动中间件与判据，**没有碰端点的 async 形状**。

### 6. 诚实边界

1. **两条改动都在服务端 ⇒ 真机重启（DSH 宿主 + 引擎）后才生效**；重启前的"端到端"都还是进程内。
2. §10.79 那笔提交（`d43d14f`）的 **commit message 里"24 条"改不了**（历史不动），
   只能在文档里更正——所以"25"这个正确数字出现在 §10.79 正文、本节与台账里。
3. 流式那条判据是**直接驱动中间件**（假 ASGI app），**不是**一条真 SSE 端点的端到端行为级用例；
   真 SSE 现场要业主重启 + 真 LLM，属未覆盖项。
4. M2 的变异是"早放令牌"的**等价形状**，不是真的把中间件换回 `BaseHTTPMiddleware`
   （换回去要动整个装配，且中间件栈里还有 auth 的 `BaseHTTPMiddleware`）。
5. `never_yields` 的"整段源码含嵌套"是**有意**取舍（§2 已写清）；代价是"外层同步重活 +
   嵌套 async 生成器真的在 await"这种混血形状仍会豁免——**这一族由中间件的令牌持有治，不由判据治**。
6. b14 未覆盖项照旧：§10.79 §4 的两行量具数字、§10.81 LOW-2 的"7 行"、真机并发写行为、
   `/formula` 识别版回退、C2 的 FAIL 分支、`dry_run` 真实撕裂读。


## §10.86 处理复核 b15：把判据从"看标记"换成"看有没有 await" —— 一次性消掉"零 await 占着事件循环"这一整类

**一句话**：独立复核 b15（冻结在 `verify-freeze-b15` = `423985a`）**19 条声称里 0 条 REFUTED**
（2 条 PARTLY），新发现 **1 MEDIUM + 3 LOW + 5 INFO**。那条 MEDIUM 是这一个系列里第**四**次
同型漏网："`async def` + **零 await** + 真同步重活"，因为通则的第三个合取项要求"带重标记"，
而 b15 实测的两条端点**一条标记都命不中**（裸 `DELETE FROM`、`CREATE INDEX`）——它们仍在
事件循环里**等库写锁 0.65–0.70s**（上限 `busy_timeout=60s`）。本步**不再给标记表打补丁**，
而是把判据换成结构性的那一句：

> **`async def` 端点若"零有效 await"（没有 `await`，或所有 `await` 都只是读 body）⇒ 必须 `def`。**

一次性转 **51 条**（48 条 T1 + 3 条只读 body），终盘 **`async` 57 → 6**，且**6 条全部有真
`await`**（1 条 LLM 流式 + 5 条 `asyncio.to_thread`）——盲区随判据一起消失，而不是等下一次复核
再撞见一条。

### 1. MEDIUM-1：为什么不再给标记表打补丁

标记表已经漏过**四次**（b12 的 MEDIUM-2、§10.71、§10.79，以及本次 b15）——每次都"复核撞见一条、
补一条"。根因是**它在问一个问不出答案的问题**："这段代码重不重？"（静态上不可判）。
而"**有没有一个真会让出控制权的 `await`**"是**可判的结构事实**：没有 ⇒ 这条端点从进到出都占着
事件循环，无论它干的是 1ms 的读还是 60s 的锁等。**把必要条件换成充分条件**，这一类就没了。

**before/after（我自己量的，独立于 b15；`var/tmp/probe-t1-lock-gap.py`）**：
另一条连接 `BEGIN IMMEDIATE` 持写锁 0.6s，心跳线程量事件循环最大空档。

| 端点 | before 空档 | after 空档 | 说明 |
|---|---|---|---|
| `DELETE /api/v1/materials/{id}` | **0.651 / 0.668 / 0.656s** | **0.019 / 0.016 / 0.017s** | b15 点名的那条（裸 `DELETE FROM`，标记命不中） |
| `GET /api/v1/laws/catalog`（首次） | **0.704s** | **0.016s** | b15 点名的另一条（`ensure_catalog_schema` 的 DDL） |
| 对照：`DELETE /projects/{p}/clauses/{c}`（§10.83 已转 `def`） | 0.021 / 0.016 / 0.016s | 0.016 / 0.016 / 0.016s | 同一把锁、同一时长：**空档本来就应该在噪声底** |

⚠ **请求耗时不变**（0.64–0.67s）：等锁的时间**还在**，只是从"堵住整个引擎"挪到了"那个工作线程
在等"。这一点必须说清——修的**不是**"用户不用等"，而是"**别人不用陪着等**"。

**代价也要量**（`var/tmp/probe-t1-latency-cost.py`，同一份顺序请求在两棵树上各跑 25 次、
前 5 次热身避开线程冷启动）：`def` 端点每次多一趟线程跳转 ⇒

| 端点 | before p50 | after p50 |
|---|---|---|
| `GET /health` | 0.26ms | **0.36ms** |
| `GET /documents` | 0.26ms | **0.41ms** |
| `GET /clauses/resolve?...` | 0.34ms | **0.47ms** |
| `GET /materials/tiers` | 0.34ms | **0.44ms** |

⇒ 每次廉价请求 **+0.1–0.13ms**（P5 性能最低优先，换的是"整类 0.65–0.70s 冻结"不再可能出现）。
⚠ 新起进程的**第一次**请求还要额外付一次线程创建（§10.84 的 uvicorn 验证里 `/health`
首测 **0.0164s**，而进程内热身后的 p50 是 0.36ms）——那不是稳态成本。

**转换与终盘**：
```
async 端点  57 → 6        T1（零 await）  48 → 0
T1+重标记   0 → 0         6 条剩下的：/chat/completions（LLM 流式）
                          + /laws/search、/laws/ingest、/laws/check-updates、
                            /laws/catalog/refresh、/laws/verify（`asyncio.to_thread` 范本）
```
转换用一个**自动选取 + 干跑**的脚本（`var/tmp/convert-t1-batch.py`）：判据 = 审计模块的
`awaits_like(src) == 0`；干跑逐条打印 (文件, 函数, 路径, 方法) 我看过才 `--apply`；
只做**一处单点替换**（`    async def <name>(` → `    def <name>(`），每步 `ast.parse`，收尾逐条
复核"已不是 `AsyncDef`"。那 3 条"只读 body"的（`/compare`、`/documents/impact`、`/discover/search`）
按 §10.79/§10.83 同款手改：body 走签名、坏 JSON 由 FastAPI 直接 **422**。

### 2. 判据本体也修了两处（b15 的 INFO-1 / INFO-3）

- **`awaits_like()` 必须把 `async for` / `async with` 算成"会让出控制权"**（INFO-1）：
  它们编译成 `await __anext__` / `__aenter__`，但 AST 里**没有 `Await` 节点**——只数 `Await`
  会把"只写了 `async for` 的 async 端点"判成该改 `def`，而那种代码改成 `def` **根本不成立**。
  现在判据是 `Await | AsyncFor | AsyncWith`。
- **解析失败 ⇒ 判红（fail-closed）**（INFO-3）：`never_yields` 原先在 `SyntaxError` 下
  `return False`（= "会 yield" = 放行）。两个现有调用点都先 `dedent` 所以没实际逃逸，但那是
  **静默 fail-open**：将来谁把 `inspect.getsource()` 直接喂进去，全部缩进端点一起被放行。
  现在两个函数都**自己 dedent**，且解析失败时 `never_yields → True`、`awaits_like → None`
  （调用方判红）。配了单测（含"缩进源码"与"坏源码"两种形状）。

### 3. 三条 LOW + 五条 INFO 的处置

| 编号 | 一句话 | 处置 |
|---|---|---|
| b15-LOW-1 | §10.79 §7 第 2 条仍写"闸门把 `bulk-db` 排除"，与 §10.83 起的事实相反（现在时陈述，会误导） | ✅ 就地加**过时标注**并指向 §10.83/§10.86（**不改写历史章节**，只钉"以谁为准"） |
| b15-LOW-2 | §10.85 §5 写快照标签指向 `ec5cfc2`，实际是 `423985a`（`ec5cfc2` 是 amend 前的**游离提交**） | ✅ 按 `git cat-file -p <tag>` 更正哈希 + 写清来历 |
| b15-LOW-3 | `GET /snapshots`、`GET /clauses/patches` 当时"表里没有 + 通则不红"⇒ **没有任何闸门** | ✅ **已被本步的结构性判据覆盖**（两条都是零 await ⇒ 一并转 `def`）；测试与文档里的"故意留 async"表述同步改掉 |
| b15-INFO-1 | `never_yields` 对 `async for` 漏判（方向保守） | ✅ 见 §2：新增 `awaits_like()` 把三类语法都算上；`never_yields` 的保守性在 docstring 里写明 |
| b15-INFO-2 | 对"助手包装读 body"会误判 False（保守） | 📝 docstring 写明"名字比语义强"，两处偏差都是保守方向 |
| b15-INFO-3 | 非 dedent 源码上静默 fail-open | ✅ 见 §2（两个函数内 dedent + fail-closed + 单测） |
| b15-INFO-4 | `verify-engine-uvicorn.py` 临时目录从不清理；`_free_port()` 死代码 | ✅ 删死代码；临时目录**默认删除**、`--keep-tmp` 才留（打印路径） |
| b15-INFO-5 | §10.85 §5 的"+9 = 6 条新测试 + 3 参数"分解与 `git show` 的 7 个新 `def test_` 不符 | ✅ 按实测分解改写（3 参数 + 2 函数 + 4 `TestHeavyGate`）；收集数 +9 本来就对 |
| b15-B3 | uvicorn 脚本的"刻意差异"是 **PARTLY**：真入口还做 `start_write_worker()` / `engine.session.json` / `stop_write_worker()`，第一版三件都没做 | ✅ 启动器**改成逐字调 `run()`**（只去掉 OCR 预热），连握手前缀都改成真的 `KNOWLEDGE_STATION_PORT=/TOKEN=` |

### 4. 我自查出来的一个缺陷（等 b15 报告时发现的）：嵌套作用域

`nested_async_gen_without_await()` 原先用 `ast.walk(node)` 数 `yield`/`await` ⇒ **把嵌套函数里的
也算到外层头上**，实测两个反例（`var/tmp/evidence-1086-scope.py`）：

| 形状 | 旧实现 | 新实现 | 性质 |
|---|---|---|---|
| `async def helper()` 里嵌**同步**生成器 `def inner(): yield 1` | `['helper']` | `[]` | **假阳性**（`helper` 根本不是生成器） |
| 真 async 生成器，唯一的 `await` 写在嵌套 async 函数里 | `[]` | `['stream']` | **假阴性**（判据放行 = 闸门静默失效） |

修法：新增 `_own_scope_nodes()`（跳过嵌套 `FunctionDef`/`AsyncFunctionDef`/`Lambda`），
`yield`/`await` 只数**该函数自己作用域**里的。配了单测钉住这三个形状（含"自己有 await ⇒ 不红"）。

### 5. 顺手关掉一条登记项：§10.81 LOW-2 的"7 行"

b14 把"`_code_only()` 实测改了 7 行"标为**未验证**。本步在 `fdfce3b`（§10.78）的提取树里
用两种跑法逐端点比标记集合（`var/tmp/verify-1078-code-only.py`，比的是 `audit_endpoint()` 的
完整可达路径，不是端点自身源码）：**差异 = 7 处**，按标记分 `{model-load: 1, pdf/ocr: 5,
hashing: 1}` ——与 b13 的原话**逐字吻合**。⇒ 该登记项关闭。

### 6. 变异（全 RED 且命中**预期断言**，逐字节还原）

`var/tmp/mutate-step86.py`：

| 变异 | 改了什么 | 红在哪条判据上 |
|---|---|---|
| **N1** | `DELETE /materials/{id}` 改回 `async def`（= b15 的 MEDIUM-1 原形状） | `test_T1_零await的async端点必须是def` + 通则（指名该路径） |
| **N2** | `GET /laws/catalog` 改回 `async def` | 同上 |
| **N3** | `/compare` 改回 `async def + await request.json()`（"只读 body"形状） | `test_async_endpoints_that_only_read_body_are_not_heavy` |
| **N4** | `awaits_like()` 只看 `Await`（丢掉 `AsyncFor`/`AsyncWith`） | 单测：`async for` 样本被判成"零 await" |
| **N5** | `never_yields()` 的 `SyntaxError` 分支改回 `return False` | 单测：坏源码被判成"会 yield"（fail-open） |
| **N6** | `_own_scope_nodes()` 改回 `ast.walk`（嵌套作用域缺陷复现） | `test_嵌套生成器判据只数自己作用域` |

### 7. 证据

⚠ **本步的快照标签是 `step-85-no-await-async-gone`**（指向本步提交）：标签号仍比章节号小 1
——原因与 §10.85 §5 写的是同一个（`scripts/snapshot-project.ps1` 按"已有最大 `step-NN` + 1"
递增，而 §10.84 与 §10.85 共用了一笔提交）。**不是漏做快照**，也不是编号写错。

`pytest` **1801 passed / 3 skipped / 0 failed**（1801 → 1804 收集：**+3 条新测试**，都是判据本体
与作用域的边界样本）；`mypy` **134 / 0**；`tsc` 0；`smoke` EXIT=0（19 段）；
`verify:commands` 22/22；真 uvicorn 验证 **4/4**（第二版启动器，逐字调 `run()`）。
审计重跑（`var/tmp/audit-after-86.json`）：`async` **6** / T1 **0** / T1+重 **0** / T2+重 **1**。
转换清单与干跑记录在 `var/tmp/convert-t1-batch.py`；锁争用 before/after 探针在
`var/tmp/probe-t1-lock-gap.py`（before 树 = `git archive verify-freeze-b15` 的提取树）。

### 8. 诚实边界

1. **真机重启（DSH 宿主 + 引擎）后才生效**；asgi 量具里的数字不是端到端。
2. **请求耗时没有变快**（等锁还是要等 0.65s）：修的是"**别人不被陪着堵**"。若要让那个用户也
   不等，得改数据模型（乐观写/队列），不在本步范围。
3. **新增 51 条 `def` 端点会多占线程池令牌**（每个请求一次线程跳转）：进程内实测每次
   **+0.1–0.13ms**（见 §1 的表），`THREADPOOL_TOKENS=16` 里恒有 ≥12 个位子留给它们
   （重活最多 4）；**没有在真机负载下量过**高并发时的排队，这是**取舍**而非测量结论
   （P5 性能最低优先）。
4. **`asyncio.to_thread` 那 5 条用的是 asyncio 的默认执行器**（`loop.run_in_executor(None, …)`），
   **与我们那把 `THREADPOOL_TOKENS=16` 的 anyio 池不是同一个池** ⇒ 它们的并发**不受** 16 约束。
   它们做的是网络/入库（I/O 密集，风险低于 MinerU 那类子进程风暴），且这个写法是 §10.79 特意
   留下的"范本"，本步**没动**。⇒ **登记为未决**：要么把它们也收敛成 `def`（进有界池），
   要么显式给那条路加闸门。
5. `awaits_like`/`never_yields` 都是**语法层**判据：把 await 藏进助手函数
   （`await read_json(request)`）仍会被判成"会 yield"（INFO-2，保守方向，未修）。
6. b15 未覆盖项照旧（真机端到端、真 SSE + 真 LLM、`/formula` 识别版回退、C2 的 FAIL 分支、
   `dry_run` 真实撕裂读、§10.79 §4 的两行量具数字）。


## §10.87 处理复核 b16：**"async 必须显式申报"**（判据静态上判不准就改要申报）＋ 并发 DDL 竞态修复

**一句话**：独立复核 b16（冻结在 `verify-freeze-b16` = `0873225`）**7 CONFIRMED / 4 PARTLY /
0 REFUTED**。最有价值的一条 PARTLY 是 **D4**：§10.86 声称"把必要条件换成充分条件，这一类就没了"
——**这个强度不成立**。b16 构造出两条**静态判据不可能判准**的形状，各实测冻结事件循环
**0.650s**：① 唯一的 `await` 是 `await _read_json(request)`（助手内部才读 body）；
② 外层只读 body、嵌套 `async def` 里有真 await 但**从不被迭代**。本步的处置**不再是再打一层补丁**
（那是第 5 次），而是**把举证责任反过来**：

> **`async def` 是例外**：每条 async 端点都必须在 `_ASYNC_ENDPOINTS` 名单里**写明理由**，
> 任何新形状（H1/H3/以及将来没想到的）**默认红**。

外加修掉 b16 的 3 条新发现：**并发 DDL 竞态**（本步引入的新可达路径，已修 + 有闸门）、
uvicorn 脚本"删了却说已删"的**假事实**、`get_document_file` 的过时 docstring；并给
`THREADPOOL_TOKENS` 补上"它已是 §10.86 收益的前提"的注。

### 1. D4：为什么放弃"静态判准"，改成"必须申报"

b16 的量具（它自己造的端点 + 真 app + 事件循环空档）：

| 形状 | 旧判据判定 | 实测空档 |
|---|---|---|
| **H1** 唯一 await 是 `await _read_json(request)`（助手内部才读 body）+ 0.65s 同步重活 | `never_yields=False`（**放行**） | **0.6501s** |
| **H3** 外层唯一 await 是读 body；嵌套 `async def stream()` 有真 await 但**从不迭代** | `never_yields=False`（**放行**） | **0.6501s** |
| H2 真流式（嵌套生成器里有真 await） | `False`（放行，**不允许误伤**） | 0.0202s ✅ |
| H4 只有 `async for` | `never_yields=True`（**被判红——误伤**，见下） | 0.0000s ✅ |
| H5 真流式形状，但嵌套生成器的唯一 await 是读 body | `True`（红，**判红是对的**） | 0.6501s |

⚠ **H4 那一行更正**（独立复核 b17 的 E3，**REFUTED**）：`never_yields` 数的是 `Await` **节点**，
而 `async for` 编译成 `await __anext__`、AST 里**没有** `Await` ⇒ `never_yields(H4) = True`。
所以名单的第三关（当时写成"`never_yields` 必须为 False"）对"只有 `async for`"的**合法**端点
**误红，而且名单不可满足**（那种端点永远进不来）。§10.88 已把第二关换成
`effective_real_await()`（`async for/with/yield` 算挂起点 + 内联嵌套助手），并配了六形状单测。
（本节原先把 H4 写成 "False（放行）" —— 那是**转抄 b16 表格时的错**，与代码和仓库自己的断言
都冲突；**这行以 §10.88 为准**。）

根因写进 `never_yields` docstring：**"源码里存在一个非读-body 的 await" ≠ "执行路径上存在"**。
要判准就得做**过程间 + 可达性**分析（还要判"这个生成器会不会被迭代"），**静态上做不到**。

⇒ 所以闸门换成 **`test_async端点必须在显式名单里`**（`tests/test_material_api.py`）：
1. 每条 `async def` 端点都必须在 `_ASYNC_ENDPOINTS`（**路径 → 理由**）里，否则红；
2. 名单里的理由**不许为空**；
3. 名单里的每条还要过**第二关**：`never_yields(src)` 必须是 `False`（真的有一个非读-body 的
   await）——否则"为什么必须 async"答不上来；
4. **名单腐烂也要红**：写在名单里但已经不是 async 的路径 ⇒ 红。

现在的名单（**6 条**，每条都写了理由）：`/chat/completions`（SSE + `anyio.to_thread.run_sync`）、
`/laws/search`、`/laws/ingest`、`/laws/check-updates`、`/laws/catalog/refresh`、`/laws/verify`
（这 5 条是 §10.79 特意留下的 `await asyncio.to_thread(...)` 范本）。
§10.86 的 T1 判据（`awaits_like==0 ⇒ 必须 def`）**保留**——它给最常见的形状一个更直白的失败信息。

⚠ **诚实**：这**不是**"静态判据更强了"，而是**放弃静态判准**（把"证明你无害"换成"申报 + 写理由"）。
代价是将来新增 async 端点要过一道人工理由；收益是 H1/H3 这类**未知形状**也进不来。

### 2. b16-INFO-3：并发 DDL 竞态（本步**引入**的新可达路径，已修 + 有闸门）

`GET /api/v1/laws/catalog` → `query_catalog()` → `ensure_catalog_schema()`：`PRAGMA table_info`
看到缺列 → `ALTER TABLE ADD COLUMN` 是**读-改-写竞态**。改前那条端点在事件循环里**串行**执行，
**走不到**这个竞态；§10.86 把它变成 `def` 之后，16 个工作线程可以同时进来。

**自测（`var/tmp/probe-ddl-race.py`，旧版表缺 `category` 列 + 32 线程并发）**：

| 树 | 抛异常 |
|---|---|
| `verify-freeze-b16`（修复前） | **21–31 / 32**（`OperationalError: duplicate column name: category`；多次跑 23/29/31 都有） |
| 本步（三层修复后） | **0 / 32**，**连跑 28+ 次全 0** |

⚠ **"21–31/32" 不是稳定属性**（独立复核 b17 的 E4）：b17 自己测 12 轮得 **16–28/32**，且
**不压 GIL 时旧代码也会出现 0/32**（它测到 `[1,24,3,4,0,31]`）⇒ 准确说法是
"**旧代码会偶发竞态，压 GIL 时 21–31/32；不压时 0–31 都可能**"。修复后 b17 测 **896 次调用 0 异常**。

修法（三层，**第一版只做了 ① + ②**）：
- ⓪ **只读快路径**：这条函数被 `query_catalog()` **每个请求**调用，稳态下什么都不用做
  ⇒ 先用 `PRAGMA table_info` + `PRAGMA index_list`（**都是读**）确认"表/列/索引都齐"就直接返回。
  ⚠ **第一版没做这一步，是个自己引入的问题**：`ensure_catalog_schema()` 被包进
  `write_transaction()` 之后，**每次翻法规目录都要先拿写锁**——一条纯读端点的延迟被绑到
  "当前有没有别的写者"上（`busy_timeout=60s`）。快路径把稳态拉回纯读；`_catalog_schema_current()`
  检查 **6 个**前提（表存在 + 两列 + 三条索引），任何一个不满足才走迁移路径
  （b17 的 INFO：这里原写"5 个前提"，数错了）。
  闸门：`test_稳态下ensure_catalog_schema不拿写锁`（另一个连接持写锁 + 本连接 `busy_timeout=300ms`
  ⇒ 若它走写路径就会 `database is locked`，确定性判据）。
- ① 需要迁移时，整个迁移收进 `write_transaction()`（`BEGIN IMMEDIATE`）⇒ 同一时刻只有一个写者
  做读-改-写；
- ② 仍对 `duplicate column name` 幂等兜底（迁移本来就该容忍"别人已经补上了"）。

**两层修法各自都够**（这算是意外的收获）：把 ① 单独撤掉（留兜底）⇒ 探针 **0/32**；
把 ② 单独撤掉（留事务）⇒ **0/32**；**两层都撤** ⇒ **21–25/32**。所以这条修复是**纵深防御**，
而变异实验必须**同时**撤掉两层才复现（`var/tmp/debug-n8b.py` 记录了三档对照）。

⚠ 另一个量具教训：`test_并发ensure…` 第一版**测不出**两层都撤的变异——32 条线程被 GIL 串行化到
"第一条已经迁完、其余走只读快路径"。加 `sys.setswitchinterval(1e-6)` 逼出交错之后，
同一变异稳定 RED（29/23/24 条异常）。**"并发测试"不等于"测出了并发"**，这条记进 §10.87 §6 的纪律。

`conn` 显式传入或已在事务里时不再套一层（SQLite 不支持嵌套 `BEGIN`）。
**闸门**：`tests/test_law_catalog.py::test_并发ensure_catalog_schema在缺列旧表上不抛异常`
（32 线程 + 回读最终列，确定性、不计时）+ `::test_稳态下ensure_catalog_schema不拿写锁`。

⚠ **一次未能归因的残留**：修复后第一次跑出现过 **1/32 异常**，但我的探针当时只打印前 3 条、
又被 `Select-Object -Last 2` 截断，**异常原文丢了**（取证失误）。随后 **28 次连跑全 0**。
按惯例登记为**未归因**，不写成"彻底 0"。

### 3. b16-LOW-2：uvicorn 脚本"删了却说已删"

`shutil.rmtree(tmp, ignore_errors=True)` 在 Windows 上因 SQLite `-wal/-shm` 句柄延迟释放，
**只删掉一部分就返回**（留下 `database/`），而脚本接着打印"临时目录 …（已删除）"——
**主动报告假事实，比不删更糟**。现在：`rmtree` 后**回读目录是否真的没了**、不行就重试 5 次
（每次 0.3s），仍不行就**如实打印"删除失败"**（并说明多半是 `-wal/-shm` 句柄）。

### 4. b16-LOW-1：`get_document_file` 的过时 docstring

它已被 §10.86 转成 `def`，docstring 却还写着"⚠ **故意保持 `async def`**（§10.75）…判定'这条
不用改'"——**以现在时陈述、与相邻一行的 `def` 直接矛盾**。改成过去时 + 写清 §10.86 的判据变更，
并附上 b16 的行为证据（2.5MB / 18MB / **72MB** PDF 字节与 sha256 全对、非 PDF 仍 404）。

### 5. b16-INFO-2：`THREADPOOL_TOKENS` 的地位变了

§10.86 把那 51 条廉价端点也搬进了这口池（全库 141 条同步端点共享它）⇒ **"池子有界"从一条性能
纪律变成了 §10.86 收益的前提**：把它调大（尤其调回 anyio 默认 40）等于**同时取消 §10.86 的收益**
（"在事件循环里等锁"会换成"在无界池里并发等锁"）。这条注已写在 `THREADPOOL_TOKENS` 定义处，
并把"`asyncio.to_thread` 不在**这口**池里"一并写明。

### 6. b16-D8：`_code_only()` 的"7 处"——**口径不同，两个数都对**

b16 复现不出"7 处"（它得到 44/13 或 38/12）。本步把**口径**写明并两个都量了
（`var/tmp/verify-1078-code-only.py`，`fdfce3b` 提取树）：

| 口径 | 定义 | 结果 |
|---|---|---|
| **A 端点级**（b13 与 §10.85 用的那个） | 每个 **async 端点**的**可达路径标记集合**（`audit_endpoint()['markers']`）在"删注释"前后的差 | **7 处** = `{model-load:1, pdf/ocr:5, hashing:1}` ✅ 与 b13 逐字吻合 |
| **B 函数级** | 可达路径上**每个函数**的 `_markers_in()` 集合差 | **35 处** = `{pdf/ocr:23, model-load:6, hashing:2, network:2, bulk-db:1, ml-runtime:1}` |

⇒ b16 与我的差异来自**口径**（它换了几种公平口径都没落在 A 上），不是数字造假；
**实质**（注释里的词被当成代码行为、造成假阳性）双方都确认。
⚠ **纪律更正**：一条没有**写明口径**的计数**不可复现**——以后凡引用计数，都要写清"数的是什么"
（本条已回填口径 A 的定义；b15/b16 的报告也都点名了这一点）。
⚠ 另一条相关的取证失误：我的探针在 `var/tmp/`（**不进仓库**），复核拿不到源码 ⇒
**引用计数时，探针要么进仓库、要么在文档里写清算法**。

### 7. 变异（全 RED 且命中**预期断言**，逐字节还原）

`var/tmp/mutate-step87.py`：

| 变异 | 改了什么 | 红在哪条判据上 |
|---|---|---|
| **N7** | `/laws/verify` 去掉真 await（`await asyncio.to_thread(verify_law, bbbs)` → `verify_law(bbbs)`） | 名单第二关：它**答不上来"为什么必须 async"** |
| **N8** | `ensure_catalog_schema` 退回"裸 PRAGMA + ALTER"（去掉 `write_transaction` 与兜底） | 新并发闸门（32 线程复现 31/32 异常） |
| **N9** | uvicorn 脚本退回 `rmtree(ignore_errors=True)` 且照打"（已删除）" | 见 §8 的证据：真跑一次后目录仍在而打印说已删 |
| **N10** | 名单里加一条**已经不存在**的路径（名单腐烂） | `test_async端点必须在显式名单里` |
| **N11** | 把一个**不在名单**里的端点改回 `async def`（H1 形状） | 同上（指名该路径） |

### 8. 证据

`pytest` **1804 passed / 3 skipped / 0 failed**（收集 1807；1804 → 1807 = **+3**：名单闸门
`test_async端点必须在显式名单里` + 并发 DDL 闸门 `test_并发ensure_catalog_schema在缺列旧表上不抛异常`
+ 稳态快路径闸门 `test_稳态下ensure_catalog_schema不拿写锁`）；
`mypy` **134 / 0**；`tsc` 0；`smoke` EXIT=0（19 段）；
`verify:commands` 22/22；真 uvicorn 验证 **4/4**（并**首次验证"临时目录真的被删掉"这条声明**：
连跑两次，`%TEMP%` 里的 `ks_uvicorn_*` 计数 before=10 / after=10，两次都打印"（已删除）"
——声明与事实一致）。
审计重跑：`async` **6** / T1 **0** / T2+重 **1**；6 条全在名单里。

⚠ **本步的快照标签是 `step-86-async-must-declare`**（标签号比章节号小 1，原因见 §10.85 §5）。

### 9. 诚实边界

1. **H1/H3 我修的是"闸门"，不是"判据"**：`never_yields` 仍然会把这两种形状判成"会 yield"
   （docstring 已如实写清它是**诊断量**）。它们现在进不来，是因为**不在名单里**——
   **如果一个新 async 端点被写进名单、理由写得漂亮、但其实是 H1/H3 形状，闸门拦不住**
   （拦不住）。这是"显式申报"模型的固有代价。
   ⚠ **更正**（b17 的 MEDIUM-3）：原写"**只有**人工复核能拦"**说过头了** —— 仓库自带的
   `scripts/measure-endpoint-blocking.py`（心跳量事件循环空档）对同一条 H1 形状实测
   **max_gap=0.6504s**（空闲基线 0.0136s）⇒ **自动化第二层已经存在**，只是还没接到名单上。
   §10.88 把它登记为下一层（并把"理由成不成立"的静态判据换成 `effective_real_await()`，
   能自动抓住 H1/H3 的**构造形状**）。
2. **并发 DDL 的那次 1/32 未归因**（异常原文丢了，随后 28 次全 0）。
3. **`asyncio.to_thread` 的池不对称仍未动**（5 条 `/laws/*` 在 asyncio 默认执行器、不受 16 约束，
   且 `/api/v1/laws/` **不在 `HEAVY_PREFIXES`** 里 ⇒ 也不受 4 令牌闸门约束）：b16 判"不必升级严重度"，
   我接受，登记为下一步（要么换成 `anyio.to_thread.run_sync` 进有界池，要么补进重活表）。
4. **真机重启（DSH 宿主 + 引擎）后才生效**；本步的 DDL 竞态修复在真机上还需要"老库 + 并发首请求"
   才能端到端复现（b16 也只做到函数级）。
5. b16 未覆盖项照旧（真机端到端、真 SSE + 真 LLM、72MB 走的是进程内 ASGITransport、
   `to_thread` 32 线程池未压力实测、smoke 的"19 段"只有 11 个具名小结）。


## §10.88 处理复核 b17：线程池收窄的"按循环"错配（MEDIUM-1）、名单第二关的误红（MEDIUM-2/REFUTED）、"只剩人工"更正（MEDIUM-3）

**一句话**：独立复核 b17（冻结在 `verify-freeze-b17` = `24b40f4`）判 **7 CONFIRMED / 3 PARTLY /
1 REFUTED**，并且**抓到一个真缺陷**：`THREADPOOL_TOKENS` 的收窄用**进程级**幂等标记，而 anyio 的
limiter 是**按事件循环**的 RunVar ⇒ **第二个事件循环起"池子有界"静默失效**（实测 loop#1=16、
loop#2=**40**）。另外它把 §10.87 的名单第二关**证伪**了：对"只有 `async for`"的**合法**端点
**误红且名单不可满足**。本步三件都修，并把它指出的 3 条 LOW/若干 INFO 一并收口。

### 1. MEDIUM-1：收窄的幂等粒度必须是**每个事件循环**

anyio 的 `current_default_thread_limiter()` 是 **RunVar**（按循环），而
`bound_threadpool_once()` 原先用一个**进程级 `_bound_once`** 做幂等 ⇒ 第二次进入新循环时它
直接 `return`，那个循环的 limiter 停在 anyio 默认的 **40**。生产只有一条长驻循环（uvicorn），
所以现网没暴露；但测试/嵌入式多循环、以及"将来换调度方式"都会踩到——而 b14 的 LOW-4 是
**同一族的另一处**（`_get_heavy_limiter()` 当时已按循环缓存，这里没跟上）。

修法：`_bound_loops: weakref.WeakKeyDictionary`（键 = **循环对象**，与 `_get_heavy_limiter()`
同款）；命中才返回，否则**在本循环里再收窄一次**。新闸门
`test_线程池收窄是按事件循环的`（跑两个 `asyncio.run`，每个循环里都断言 `total_tokens == 16`）。

### 2. MEDIUM-2 / E3 REFUTED：名单第二关对"`async for`"误红

`never_yields()` 数的是 `Await` **节点**，而 `async for` 编译成 `await __anext__`、AST 里
**没有** `Await` ⇒ `never_yields` 对"只有 `async for`"的端点返回 **True**。而 §10.87 的名单第二关
写的是"`never_yields` 必须为 False" ⇒ **合法端点被误红，而且永远进不了名单**（分支不可满足）。
b17 还指出 §10.87 §1 的 H4 行（当时写"`False`（放行）"）**与代码、与仓库自己的断言冲突**——
那是我**转抄 b16 表格时的错**，已在 §10.87 §1 就地更正。

修法：第二关换成新判据 **`effective_real_await(src)`**：
1. `async for` / `async with` / `yield` ⇒ **算**挂起点（等待点常在库源码里）；
2. 读 body 的 `await`（`x.json()`/`x.body()`）**不算**；
3. **调用本端点内嵌套的 async 助手 ⇒ 内联进去再看**（b16 的 H1 形状靠这一层判准：助手内部
   只读 body ⇒ 整条链一次都不让出）；
4. 本端点**引用了**的嵌套 async 生成器（真流式 `StreamingResponse(stream())`）**算**；
5. 解析失败 ⇒ **False**（fail-closed ⇒ 名单判红）。
配六形状单测（H1 **False** / H3 **False** / H4 **True** / H2 **True** / `to_thread` **True** /
纯读 body **False** / 坏源码 **False**），并核过现存 6 条名单端点全部 `True`。

### 3. MEDIUM-3：更正"只剩人工这一道"

§10.87 §9 第 1 条写"名单里一条理由写得好、其实是 H1/H3 形状时**只有人工复核能拦**"——**说过头**。
b17 实测：仓库自带的 `scripts/measure-endpoint-blocking.py`（心跳量事件循环空档）对那条 H1 形状
量出 **max_gap=0.6504s**（空闲基线 0.0136s）⇒ **自动化第二层早就存在，只是没接到名单上**。
本步：① 就地更正那句话；② 第 2 节的新判据已能**自动抓住 H1/H3 的构造形状**；
③ 把"量具接名单"登记为下一层（对名单里的端点跑一次空档测量，超阈值即红——需要每条一个能慢下来的
依赖，属单独一步）。

### 4. 三条 LOW + 若干 INFO

| 编号 | 一句话 | 处置 |
|---|---|---|
| b17-LOW-1 | `verify-engine-uvicorn.py::_free_port()` 是**死代码**，且用**未 import** 的 `socket`（一调用就 `NameError`） | ✅ 删掉（并留一行说明） |
| b17-LOW-2 | 只读快路径去掉了旧的**无条件 `commit()`**（悬而未决的隐式事务不再被顺手提交）——未登记的行为变化 | ✅ 写进 `ensure_catalog_schema()` 的 docstring（查过：唯一热路径 `query_catalog()` 是纯读，无依赖方） |
| b17-LOW-3 | `never_yields` 是 **may** 分析 ⇒ `if False: await x` **一行**即可豁免；残余逃逸面比 §10.87 §9 登记的两条更宽 | ✅ 写进 `never_yields` docstring，并说明这正是"名单制 + 量具 + 人工"三层存在的理由 |
| b17-INFO | `test_并发…` 无 join 超时；§10.87 的"21–31/32"不稳定（不压 GIL 时 **0–31 都可能**）；§10.87 §2 "5 个前提"实为 **6**；闸门范围是 `/api/`（框架自带 4 条 async 路由在外） | ✅ 加 `t.join(30)` + 存活断言；§10.87 补"不是稳定属性"；改 6；测试 docstring 写明范围 |

### 5. 变异（全 RED 且命中**预期断言**，逐字节还原）

`var/tmp/mutate-step88.py`：

| 变异 | 改了什么 | 红在哪条判据上 |
|---|---|---|
| **M1** | 收窄函数退回**进程级**幂等（`if _bound_loops: return`，第一个循环置位后第二个循环直接返回） | `test_线程池收窄是按事件循环的`（第二循环停在 40） |
| **M2** | `effective_real_await` 的 `async for/with/yield` 分支改成 `if False` | 六形状单测：**"只有 `async for` 也是真的会让出"** |
| **M3** | 去掉**内联嵌套助手**那一层（`helper = None`） | 六形状单测：**"H1（嵌套助手包装读 body）必须判成'没有真挂起点'"** |

### 6. 证据

`pytest` **1806 passed / 3 skipped / 0 failed**（收集 1809；1804 → 1806 = **+2**：线程池按循环收窄 1 +
名单第二关的六形状判据 1；另有一条既有用例改名并加断言，不计条数）；
`mypy` **134 / 0**；`tsc` 0；`smoke` EXIT=0（19 段）；`verify:commands` 22/22；真 uvicorn 验证 **4/4**。
审计：`async` **6** / T1 **0** / T2+重 **1**，6 条全在名单里且 `effective_real_await` 全 `True`。

⚠ **本步的快照标签是 `step-87-loop-bound-and-list-gate`**（标签号比章节号小 1，原因见 §10.85 §5）。

### 7. 诚实边界

1. **`effective_real_await` 只内联"同一段源码里嵌套的" async 助手**：`await read_json(request)`
   （模块级/跨模块助手）仍算"有挂起点"——**过程间分析不在能力内**。b17 的 LOW-3 也说明
   `may` 分析的逃逸面（`if False: await x`）依旧存在。⇒ 三层（判据 / 量具 / 人工）里，
   **判据永远只是第一道**；"量具接名单"是已登记的下一步。
2. **DDL 竞态的数字不是稳定属性**（b17 实测不压 GIL 时旧代码也能 0/32）：文档已改成"分布 + GIL
   敏感性"，**不要**把"21–31/32"当成可复算的常数。
3. **`asyncio.to_thread` 的池不对称仍未动**（5 条 `/laws/*`；`/api/v1/laws/` 也不在重活前缀表），
   b16/b17 都说不必升级严重度；仍是下一层候选。
4. **真机重启（DSH 宿主 + 引擎）后才生效**；b17 的 E11#4 我们双方都**无法验证**（它没碰在跑引擎）。
5. b17 未覆盖项照旧（真 SSE + 真 LLM、72MB PDF、`to_thread` 32 线程压测、真机老库并发端到端）。


## §10.89 处理复核 b18：**"误红"的那条其实是"正确但硌手"**（拿框架事实收口），+ 口径更正与死代码

**一句话**：独立复核 b18（冻结在 `verify-freeze-b18` = `58c5acb`）判 **4 CONFIRMED / 3 PARTLY**
（F2 的"不会误红"**REFUTED**），新发现 **1 MEDIUM + 3 LOW + 3 INFO**、**无 HIGH**。它的 MEDIUM-1
是一条**真反例**：名单第二关会判红一条**真会让出的流式端点**（嵌套 async 生成器被
**装饰器/模块级注册表**登记 ⇒ 判据的"被引用"检测只看 `Name` 节点，看不见它）。本步**没有放宽判据**，
而是**用框架事实收口**：闸门问的是"**必须** async 吗"，而那条端点的答案是**否**——`def` 端点返回
`StreamingResponse(async_gen())` **一样能真流式**（实测逐字节相同）⇒ 判红的补救（改 `def`）**无害**。
另修两处口径（"严一档"说过头、深度上限未登记）+ 删两个**新死代码**。

### 1. b18-MEDIUM-1：不放宽判据，先证明"补救无害"

b18 的复现：`@register async def stream(): … await asyncio.sleep(0) … yield` +
`return StreamingResponse(REGISTRY[-1]())` ⇒ `effective_real_await=False` ⇒ 挂进 KS app 后闸门红，
但实测 HTTP 200 逐块产出。

**为什么不放宽（两条路都试过）**：
- **放宽**（把 `StreamingResponse` 一律当"有挂起点"）：会让 **H5** 那种"端点体里先跑 0.65s 同步活、
  再返回流"的形状混过去 —— 那正是 b16 证明"判红是对的"的形状。**闸门放行错误方向不可取**。
- **保留并换补救**（本步选择）：闸门问的是"**必须** async 吗"。`def` 端点返回
  `StreamingResponse(async_gen())` 时，Starlette 仍然 `async for` 迭代那个异步可迭代对象 ⇒
  **流式行为与 `async def` 逐字节相同**。自测（`var/tmp/probe-def-streaming.py`）：

  ```
  /def_ep    status=200 chunks=[b'chunk0|chunk1|chunk2|']
  /async_ep  status=200 chunks=[b'chunk0|chunk1|chunk2|']
  ```

  ⇒ 对这条端点，"改 `def`"是**无害**的补救；判红是**正确但硌手**，不是误红。
  **闸门信息也已改成可执行**：offenders 里现在直接写"若它是流式端点：`def` 一样能真流式
  （见 `test_def端点返回StreamingResponse仍然真流式`），所以改 `def` 是无害的补救"。
  **新用例**钉住这个前提（`tests/test_material_api.py::test_def端点返回StreamingResponse仍然真流式`）：
  两种声明方式都 200 且 body 相同。⚠ 它钉的是**框架事实**，框架升级后若它红了，本节的论证要重做。

### 2. 口径更正（b18-LOW-2）：`effective_real_await` **不是**"严一档"

原 docstring 写"比 `never_yields` 严一档"——**不处处成立**：它在 H1/H3 上更**严**（内联嵌套助手），
但在 H5 / `async for` 上更**宽**（`never_yields` 只数 `Await` **节点**，对"只有 `async for`"的合法
端点会误红）。已改成**两个方向都写明**，并逐条列出判据顺序（①–⑤）与三条能力边界
（只内联嵌套助手 / "引用"只看 `Name` 节点 / 深度上限 4 只朝放行截断）。
⚠ 顺带记一条：§10.87 §1 的 **H5 行**（"判红是对的"）说的是**旧第二关**；新判据下 H5 会被**放行**，
而**这是有意的取舍**——判据只回答"必须 async 吗"，"端点体里有没有同步重活"由**审计的 T2+重表**
与**量具**回答（§10.88 §3 已登记"量具接名单"为下一层）。

### 3. 死代码（b18-INFO-2）：同一族**再现**

第 2 节换判据时留下的 `_own_awaits()` / `_scope_suspends()` 成了**无调用点**的死代码——
而 b17 刚刚因为 `_free_port` 死代码提过 LOW。**已删**。教训写在这里：
**"换实现"要和"删旧实现"同一笔提交**（`git diff` 里没人会去看一个不再被 import 的名字）。

### 4. 其余 LOW / INFO（登记与处置）

| 编号 | 一句话 | 处置 |
|---|---|---|
| b18-F1/F3/F4/F5 等 4 条 CONFIRMED | 按循环收窄有鉴别力（重建旧实现得 `[16,40,40]`、40 线程端到端峰值 16、弱引用全回收）；名单四关 + 5 变异全红、名单零漂移；§10.87 四处更正落地；三条 LOW 修复属实 | ✅ 接受（细节见其报告） |
| b18-LOW-1 | pytest pass/skip 拆分差 1（它 **1805/4/0** vs 我 **1806/3/0**）：差的那条是 `test_golden_set.py:31`（本机临时库无 GB 30871 语料），本区间未改该文件 | 📝 环境差，**不改口径**（b15/b16/b17 同款） |
| b18-LOW-3 | `package.json` 的 `typecheck:py` 用 Windows 相对路径 `.venv\\Scripts\\python`（**非本轮改动**） | 📝 已知；本项目是 Windows 单机桌面部署，保留（跨平台不是目标） |
| b18-INFO-1 | 递归深度上限 4 ⇒ **第 5 层起放行**（只朝放行截断，不误红） | ✅ 已写进 docstring 的能力边界 |
| b18-INFO-3 | `plugin/scripts/smoke-chatmode.mjs:613` 的并发断言**偶发失败一次**（`durable=23/24`；紧接单跑 6 次全过、整段 smoke EXIT=0；`plugin/**` 本区间零改动） | 📝 登记为**既有 flake**（与 §10.82 那条 `smoke` EXIT=1 同族），不动；下次动 `plugin/` 时优先查它 |
| b18-F6 | 门禁：mypy 134/0（它用**新缓存目录**排除复用）、tsc 0、smoke EXIT=0（脚本链**恰好 19 段**已复算）、verify:commands 22/22、uvicorn 4/4 + 临时目录真删 | ✅ |

### 5. 变异（RED 且命中**预期断言**，逐字节还原）

`var/tmp/mutate-step89.py`：**M4** —— 把"被引用的嵌套生成器"放宽成"任何嵌套 async 生成器都算"，
用 b18 的反例方向去打**我选择保留的那条严格性** ⇒ `test_名单第二关的判据_effective_real_await`
的 **H3（从不被引用的嵌套 async 生成器）必须判成"没有真挂起点"** 变红。
（本步的两处改动是"文档口径"与"删死代码"，没有可注入的产品行为；**能注入且承重的那一处就是它**。）

### 6. 证据

`pytest` **1807 passed / 3 skipped / 0 failed**（收集 1810；1806 → 1807 = **+1**：
`test_def端点返回StreamingResponse仍然真流式`）；`mypy` **134 / 0**；`tsc` 0；`smoke` EXIT=0（19 段）；
`verify:commands` 22/22；真 uvicorn 验证 **4/4**。审计：`async` **6** / T1 **0** / T2+重 **1**，
6 条全在名单里。

⚠ **本步的快照标签是 `step-88-streaming-premise`**（标签号比章节号小 1，原因见 §10.85 §5）。

### 7. 诚实边界

1. **"判红但不放宽"是一个取舍**：b18 认为误红比漏放更疼；我按"闸门只回答'必须 async 吗'，
   而答案是'否'（`def` 能流式）"保留严格性。**如果将来真出现一条"必须 async 且判据判红"的流式
   端点**（例如它在返回 `StreamingResponse` **之前**还要 `await` 别的东西而判据没看见），
   那才是真误红——届时按 §10.88 §3 的下一层（量具接名单）收口，而不是放宽语法判据。
2. **静态判据的能力边界依旧**：只内联嵌套助手、"引用"只看 `Name`、深度 4、`may` 分析
   （`if False: await x` 一行逃逸，b18 再次实测存在）。
3. **`test_def端点返回StreamingResponse仍然真流式` 钉的是框架事实**（Starlette 1.6 行为）：
   升级框架后它若红，第 1 节的论证需要重做。
4. **`smoke-chatmode.mjs` 的偶发失败未归因**（本区间未动 `plugin/`；只观察到 1 次、随后 6 次全过）。
5. **真机重启（DSH 宿主 + 引擎）后才生效**；本步没有任何行为改动会影响运行中的实例
   （只改审计脚本 + 测试 + 文档）。


## §10.90 处理复核 b19：核心前提被独立证实（G1），4 条 INFO 全收口

**一句话**：独立复核 b19（冻结在 `verify-freeze-b19` = `738dae0`）**收窄范围**只做 G1–G5：
**G1（核心）CONFIRMED** —— 它**自己写了两把尺**，证明"`def` 端点返回 `StreamingResponse`
与 `async def` **行为相同**"这条框架事实，而且**流式期间事件循环真的空出来**；
G2/G4 **PARTLY**（都是文档口径与 1 条环境 skip 差），G3/G5 CONFIRMED；
新发现 **6 条 INFO**（**无 HIGH/MEDIUM**）。本步把 4 条能修的修掉（N1–N4），2 条登记（N5/N6）。

### 1. G1：b19 给"不放宽判据"补上了**独立**证据（这是本步最有价值的部分）

它的两把尺（都不是我的用例）：
- **逐块边界**：`def` 与 `async def` **各发出 6 次 `http.response.body`**、发送时刻差 ≤3ms、
  body 逐字节相同（它还指出 **httpx 会把流合并**成一个 piece ⇒ 客户端侧"逐块"观测不到，
  所以它改在 **ASGI `send()` 边界**取证 —— 与我在 §10.90 §3 的做法一致）；
- **空档对照**：`def` 流式 0.096s 期间事件循环最大空档 **0.0160s ≈ 空闲基线 0.0182s**；
  端点体塞 0.3s 同步活时两者**差一个量级**：`def` **0.0163s**（sleep）/ **0.0322s**（CPU 自旋）
  vs `async def` **0.3013s / 0.3005s**。⇒ "改 `def` 无害"**成立**。
  它还直接问判据：H5（注册表登记）今天判红、加上"出现 `StreamingResponse` 就算"那条放宽后
  被放行 ⇒ 我"不放宽"的**机制理由**也实测成立。

### 2. N1 / N2：两处文档口径

- **N1**：§10.89 §2 判为"不成立"的那句"比 `never_yields` **严一档**"，**只改了审计脚本那一份**，
  同一句还活在 `tests/test_material_api.py` 的名单闸门 docstring 里（而且后半句自相矛盾）。
  ⇒ 已按两方向改写（更严：内联嵌套助手；更宽：`async for`/H5）。
- **N2**：审计 docstring 的交叉引用"见 b17 的 **E3/E6**"**半错** —— E3 对（`async for` 误红/名单
  不可满足），**E6 是 `setswitchinterval`/GIL flaky，与 `async for` 无关**。⇒ 改成只引 E3，
  并把"这句错话当时还留在测试里"一并写在旁边。

### 3. N3：把"真流式"钉成**分块边界**（第一版钉不住）

b19 的 MUT-D：把新用例里的生成器换成**一次性** `Response(同样字节)` ⇒ 第一版用例**仍然绿**
（它只断言"两种声明都 200 + 拼接后的 body 相同"）⇒ 那它钉的其实是"两种声明方式结果一致"，
**不是"流式"**。现在改成**直接调 app（ASGI 层）数 `http.response.body` 且 `more_body=True` 的条数**
（`def` 与 `async def` 都必须 ≥3 块，且**分块序列相同**）。

⚠ **ASGI 直调的两个坑**（本步实测踩到，写进用例注释免得下一个人再踩）：
① Starlette 的 `Response.__call__` 会**并发**跑一个 `listen_for_disconnect(receive)` 任务 ⇒
若 `receive()` 永不返回 `http.disconnect`，任务组**永远不结束**（测试**挂住**，不报错——我第一次
就挂了 300s）；② 但也不能一上来就回 `http.disconnect` ⇒ Starlette 会当成客户端提前断开、
**中止响应**（只发 `http.response.start`，body 一条都没有）。正解：**等最后一块 body 发完**再回
disconnect（用例里的 `done` 事件）。
**反事实 CF1**（`var/tmp/mutate-step90.py`）：同样的采集逻辑打一次性 `Response` ⇒
分块数 **0** ⇒ 强化后的断言**会红** ⇒ b19 的 MUT-D 再也骗不过它。

### 4. N4：给"内联递归深度上限 4"加断言

b19 实测：把上限改成 2，**全量 1810 条零红** ⇒ 那条边界只是文档、没人守。
新增 `test_内联递归的深度上限有断言保护`：**3 层**嵌套助手（每层只读 body）⇒ `False`；
**6 层**同款 ⇒ `True`（按"只朝放行截断"的约定）。⇒ 上限改成任何 <3 的值，第一条就翻 ⇒ 红。

### 5. 登记（N5 / N6）

| 编号 | 一句话 | 处置 |
|---|---|---|
| b19-N5 | **CPU 型**同步活在 `def` 下仍留 **0.032–0.046s** 空档（GIL 抖动），比 `async def` 的 0.30s 好一个量级但**非零** | 📝 这是线程池方案的固有上限（GIL 下 CPU 活仍会抢占），写进 §10.90 边界；**不**改判据（它已经比"整段堵住"好一个量级） |
| b19-N6 | `smoke-chatmode.mjs:613` 的 flake b19 **9 次未复现**（整段 1 + 单跑 8，全 173/173） | 📝 保持 b18 的登记（既不能复现也不能否证） |

### 6. 变异 / 反事实（逐字节还原）

`var/tmp/mutate-step90.py`：**M5** 把内联递归上限 4→2 ⇒ `test_内联递归的深度上限有断言保护`
的"3 层必须判 False"**RED**（命中预期断言）；**CF1** 见 §3（一次性响应 ⇒ 分块数 0 ⇒ 抓得住）。

### 7. 证据

`pytest` **1808 passed / 3 skipped / 0 failed**（收集 1811；1807 → 1808 = **+1**：
`test_内联递归的深度上限有断言保护`；另一条是**强化**既有用例、不计条数）；
`mypy` **134 / 0**；`tsc` 0；`smoke` EXIT=0（19 段）；`verify:commands` 22/22；真 uvicorn **4/4**。

⚠ **本步的快照标签是 `step-89-fix-doc-and-chunk-pin`**（标签号比章节号小 1，原因见 §10.85 §5）。

### 8. 诚实边界

1. **b19 的 G1 与我的用例都在进程内 ASGI**（无真 socket / uvicorn 并发限制）：
   "`def` 流式在**真 uvicorn** 下同样成立"**双方都没有独立取证**（uvicorn 4/4 不测流式）。
2. **"逐块"证明的是 Starlette 逐块 `send()`**，不等于客户端逐块**收到**（httpx 会合并；
   真机上的分块还取决于 TCP/缓冲）。
3. **b19 的"空档"量具受 Windows ~15.6ms 计时器刻度限制**，只能与同次基线比较。
4. **N5 的 GIL 空档（0.032–0.046s）没有在本步复测**（沿用 b19 的数）。
5. b19 那条 pytest 拆分之差（1806/4 vs 1807/3）是 `test_golden_set.py` 的**环境 skip**，
   本机与它的机器口径不同——**该数字是机器特有的口径**，不要在别处当常数引用。


## §10.91 处理复核 b20：我自己写错的一条"坑"（N1）＋ 深度上限只钉住窗口（N2）＋ `.pyc` 变异陷阱（N3）

**一句话**：独立复核 b20（冻结在 `verify-freeze-b20` = `cd25877`，**范围极小**）判
**H1（新用例钉住分块流式）CONFIRMED**、**H3①/② CONFIRMED**、**H4 门禁 CONFIRMED**；
但 **H1 的"ASGI 直调两个坑"是 PARTLY —— 其中"坑①"是我写错的假事实**。它另外实测出
**深度上限只被钉成窗口 {3,4,5}**（不是 4），以及一条**会影响所有后续变异复核的方法学陷阱**
（同尺寸单字节编辑 + CPython `.pyc` 缓存 ⇒ 假红/假绿）。三条都已修/已加固。

### 1. N1：**"不回 `http.disconnect` 会挂住"是假的**（我写进用例注释的事实错）

我在 §10.90 §3 写"若 `receive()` 永不返回 `http.disconnect`，任务组永不结束、**测试挂住**"，
还配了两个坑的解释。b20 用 6 种形状 + **不套 `wait_for` 的原始调用**实测：
**0.0032s 正常返回、3 块齐全**。机制在 starlette 1.6 的
`StreamingResponse.__call__` → `create_collapsing_task_group()`：**任一侧跑完就
`cancel_scope.cancel()`**，流式侧结束会**连带取消**卡在 `listen_for_disconnect` 上的宿主任务。

⚠ 我原先还写错了类名（是 `StreamingResponse.__call__`，不是 `Response.__call__`），而且**那个
listen 分支只在 ASGI `spec_version < 2.4` 下存在**（b20 用 2.4 测时任务组根本没进）。

至于"坑②"（一上来就回 disconnect 会被当成提前断开）**成立但有条件**：只有流式侧随后撞到
checkpoint 才会中止（本用例的 `await asyncio.sleep(0)` 会 ⇒ 实测只有 `http.response.start`、
0 块 body）；生成器与 `send` 都不让出时，立刻回 disconnect 也能把 3 块发完。
⇒ 用例**仍然**用"等最后一块 body 发完再回 disconnect"的写法，理由改成**确定性**（不依赖上述
时序细节），注释已按事实重写。

⚠ 我为什么会写错：**§10.90 那次我真的挂过 300s**，于是把"挂住"归因给了 `receive`——
但真正的原因是我当时的 `receive()` 返回的是**重复的 `http.request`**（不是"永不返回"），
以及更早一版"立刻回 disconnect ⇒ 只发 start、看起来像挂"。**同一次现象被归因给相邻的机制**，
这是本轮最值得记的教训：**测试挂住时，先把 `receive`/`send` 的每一次调用打出来再下结论**。

### 2. N2：深度上限只钉成"窗口 {3,4,5}"，不是 **4**

b20 实测：只钉 3 层/6 层时，上限改成 **3 或 5 也全绿**。已补两条临界断言，把上限**唯一**钉住：

| 上限值 | 用例结果 | 红在哪条 |
|---|---|---|
| 2 | RED | 3 层（`chain(3)` 翻成 True） |
| 3 | RED | 3 层 |
| **4（原值）** | **GREEN** | — |
| 5 | RED | 5 层（`chain(5)` 翻成 False） |
| 6 | RED | 5 层 |

（`var/tmp/probe-depth-window.py`，5 个值各跑一次；⚠ 该探针的"红在哪条"归因第一版**不可靠**
——它用 `msg in out` 匹配，而 pytest 的帧源码会把**整段**断言连同消息一起打出来 ⇒ 五条消息
全都命中；原始输出已核对：cap=5 确实红在"5 层"那条。）

### 3. N3：**同尺寸单字节变异 + `.pyc` 缓存** ⇒ 假红/假绿（方法学，影响所有后续复核）

CPython 的 `.pyc` 校验键是 **(mtime 秒, 文件大小)**；`tests/test_material_api.py` 用
`spec_from_file_location` + `exec_module` 加载 `scripts/audit-async-endpoints.py`
⇒ **同一秒内**把"`depth > 4`"改成"`depth > 5`"这类**同尺寸**编辑会被当成"没变过"、
**复用旧字节码**。b20 的第一版变异因此拿到"`4→3` 假红"，它靠 `PYTHONDONTWRITEBYTECODE=1`
+ 清 `__pycache__` 才拿到干净结论（两版日志都留在它的产物里）。

**本步的加固**：`var/tmp/mutate-step90.py` 的 `run_pytest()` 现在**先删 `scripts/__pycache__`、
再带 `PYTHONDONTWRITEBYTECODE=1` 跑**（加固后 M5 仍 RED、命中预期断言）。
⚠ **纪律**：以后凡是"同尺寸"的字节级变异，必须在变异前后各清一次 `__pycache__`；
否则**假绿会掩盖真变异、假红会掩盖真绿**。这条已写进本轮记录，后续变异脚本按此办。

### 4. 证据

`pytest` **1808 passed / 3 skipped / 0 failed**（收集 1811；与 b20 的 1807/4 收集数相同，
差的那条是已登记的环境 skip）；`mypy` **134 / 0**；`tsc` 0；`smoke` EXIT=0（19 段）；
`verify:commands` 22/22。

⚠ **本步的快照标签是 `step-90-fix-asgi-note-and-depth-pin`**（标签号比章节号小 1，见 §10.85 §5）。
⚠ **2026-09-18 更正（§10.92 发现）：这条标签当时其实"漏打"了**——文档先写了名字，脚本没跑。
§10.92 在核对标签时发现（`git tag --list` 里根本没有 `step-90-*`），**已补打**并指向本节提交
`9b57d4c`（标签附注里写明是补打）。教训与 §10.85 §5 那条同型：**"文档说打了"不等于"真的打了"**，
每次快照后应立刻 `git tag --list 'step-*' | tail` 核一眼。

### 5. 诚实边界

1. b20 的两个"坑"结论限于 **ASGI 直调 + starlette 1.6.0 + spec 2.3**；升框架、或换
   `spec_version ≥ 2.4`（那个 listen 分支不存在）都要重测。
2. 那句被更正的"坑①"**曾写进 §10.90 的公开记录**（本轮已就地更正并说明**我为什么归因错**）；
   若有人引用过 §10.90 那句话，以本节为准。
3. N3 的 `.pyc` 陷阱说明：**我此前几轮的变异（M1–M5）都是同尺寸编辑**——它们的结论
   （RED 且命中预期断言）与本次"清缓存后重跑"一致，但我**没有**把每一轮的缓存状态都回溯核对过；
   可能的残留影响是"某次假红被当成真红"。⇒ 后续变异一律按 §3 的加固跑。
4. 本步仍**没有**真机端到端（需业主重启两道门）。


## §10.92 产品侧：研究报告的第三种形态 Word（`.docx`）——同一份内容块，且失败不留半份产物

**一句话**：方案 §8 明写"报告：`python-docx`（Word）…扩展现有 `exports/` 即可"，而 D-1
（§10.36）只交付了"先出 Markdown/HTML"那条**退路**，D-3b 自己记的缺口就是"`.docx` 侧未扩到
材料平面"。本步把它补上——**第三种形态不是第二套内容**（`build_report_blocks` 仍是唯一内容来源），
并顺手把本步**新引入的那一种失败模式**（docx 渲染失败会在盘上留下两个孤儿文件）堵死。

### 1. 补什么、为什么不新增依赖

| 内容块 | Word 落地 | 依据 |
|---|---|---|
| `h1` / `h2` / `h3` | `add_heading(level=1/2/3)` | 六节标题层级与 MD/HTML 一致，不另设一套层级 |
| `p` | `add_paragraph` | — |
| `pre` | 段落 + `run.font.name = "Consolas"` | 代码块/证据原文在 Word 里也要等宽（对齐才看得清） |
| `ul` | `add_paragraph(style="List Bullet")` | 用**内置**样式，不自造 numbering（自造要写 numbering.xml） |

**零新增依赖**：走的是 `exports/report_export._open_document("research-report")` 那条
`python-docx` 通路——效力报告 Excel、合规审查报告 Word、问答依据清单 Word **三条既有导出**
早就在用（`pyproject.toml` 里 `python-docx>=1.0` 也早就显式声明）。文本渲染里**不**手工设
中文字体（与 `export_review_report_docx` 保持一致：交给 Word 的字体回退与模板；硬设字体名
在没装该字体的机器上会**静默换字**，比不设更难查）。

`dry_run=true` **仍然只回 markdown/html**：`.docx` 只在**落盘**路径产生——docx 是二进制，
塞进 JSON 响应没有意义（响应形状的这一处**故意**不统一，已写进端点 docstring）。

### 2. "先渲染后落盘" —— 本步唯一一处**新引入**的失败模式

原写法（本步第一版）是：

```text
md.write_text(...) → html.write_text(...) → docx.write_bytes(_to_docx(...))   # 错的顺序
```

`.docx` 是三步里**唯一**会因**外部原因**失败的一步（业主自备模板缺内置样式），上面这个顺序
一旦抛异常 ⇒ 接口回 500，而盘上**已经躺着两个孤儿 `.md`/`.html`**。"接口说失败、盘上却有半份
产物"是最难查的一种状态。现在改成**先把 docx 字节渲染出来，再写三个文件**：

```text
docx_bytes = _to_docx(...)   # 先渲染；抛了 ⇒ 一个文件都不落
md.write_text(...); html.write_text(...); docx.write_bytes(docx_bytes)
```

并且把异常**翻成可操作的错误码**（`docx_render_failed`，信息里带模板绝对路径与需要的样式名）
——否则调用方只会看到 FastAPI 那句什么都不说的裸 500。

**为什么不做"静默降级"**（`try: List Bullet / except: 退成普通段落`）：那样会产出一份"看着成功、
其实丢了全部小标题与项目符号"的文件，正是本战役一路在堵的坑（P1 准确性 > P3 体验）。
⇒ 选择**大声失败**。代价也写进边界（§6.3）：这份报告**整个**导出会失败，不会只少 Word 一种形态。

### 3. 取证：模板缺样式时究竟是哪种行为（**实测**，不是推断）

`var/tmp/probe-docx-template.py`（把 `KS_DATA_DIR` 指到临时目录，手工造模板，**不碰**真实
`%APPDATA%`）：把默认模板里 `word/styles.xml` 的 `ListBullet` / `ListBullet2` / `ListBullet3`
三个 `<w:style>` 删掉当模板，然后调 `_to_docx`：

| 模板 | `Document(tpl).styles["List Bullet"]` | `_to_docx(...)` |
|---|---|---|
| 默认（未删） | 找得到 | **正常**出字节（36,671 B，条目文本在正文里、`ListBullet` 样式被引用） |
| 删掉那三个样式 | 抛 `KeyError: "no style with name 'List Bullet'"` | **抛同一个 `KeyError`**（不静默降级） |

⇒ python-docx 是**按样式名查**的，缺样式就是异常；这正是 §2 那个 `except` 要接住的东西
（`tests/test_research_report.py` 里两条新用例各自把短路点与 HTTP 边界钉住）。

内容探针 `var/tmp/probe-docx.py`（8 个块，含 CJK 标点、`[[m:1]]`、代码块）：**37,001 字节**、
`PK` 头、`word/document.xml` 等 6 个 `word/` 条目，**11/11 项全过**
（Heading1/2/3、ListBullet、Consolas、四级文本、列表项、引用标记原样）。

### 4. 改到的每一处（含"哪些地方**必须**跟着改"）

| 位置 | 改了什么 |
|---|---|
| `src/core/exports/research_report.py` | `_to_docx()`、`_docx_template_path()`、先渲染后落盘、`docx_render_failed`；模块 docstring「依赖」一节补第三种形态 |
| `src/core/api/routes_report.py` | 端点 docstring（三形态、`files`=3、`dry_run` 不含 docx）；路由清单第 8 行同步 |
| `tests/test_research_report.py` | 2→3 处断言（`write_` + 端点各一处）+ **4 条新用例**（内容同源、六种块、失败不留半份产物、错误码过 HTTP） |
| `plugin/client/KsMaterialsPanel.tsx` | 按钮文案 `Markdown/HTML` → `Markdown/HTML/Word` + 注释 |
| `plugin/client/api.ts` | `KsResearchReport.files` 注释写清"落盘是三个、顺序固定" |
| `plugin/src/report.js` | 路由注释（主机侧白名单转发**不用改代码**——`files` 是引擎回包，主机只透传） |
| `plugin/scripts/smoke-report-ui.mjs` | fixture 2→3 文件 + 新增一条"三形态都带出"断言（15→**16/16**） |
| `plugin/scripts/smoke-client-entry.mjs` | ⚠ **按钮文案断言**（`生成研究报告（Markdown/HTML）`）——这条**不跟着改就会红**：它按界面文案扫**构建产物**，是"产物↔源码一致"的那道关 |
| `plugin/client.js` | 重新构建（⚠ 构建脚本打印的 `1280561` 是**字符串长度**；落盘/入库的 **UTF-8 字节数 = 1282106**——772 个 CJK 字多占 1545 字节。独立复核 b21 的 LOW 就是拿这两个数对不上：与 b20 的 1282101 相差 **5 字节**，正是文案里多出来的 `/Word`。本节初稿只写了脚本打印的那个数，已更正） |
| 文档 | 本 §10.92、方案 D-1 / D-3b 两处、方案 §12 账本第 38 条 |

⚠ 一处**没改**也值得记：主机路由的白名单转发只认 `project_id`/`title`/`query`/`conclusion_md`/
`limit`/`dry_run` 六个**请求**键，而 `files`/`names` 是**响应**内容 ⇒ 主机侧一行都不用动
（"新形态"没有引入任何新的请求参数）。

### 5. 证据

- `pytest` **1812 passed / 3 skipped / 0 failed**（收集 **1815**）；
- `mypy` **134 / 0**；`tsc` **0**；
- `npm --prefix plugin run smoke` **EXIT=0**（19 段，其中 11 段打印 `== … PASS ==`；
  `report-ui` **16/16**、`client-entry` **85/85**）；
- `npm --prefix plugin run verify:commands` **22/22**；
- `scripts/verify-engine-uvicorn.py` **4/4**（`/health` 三态、FileResponse 字节一致、
  12 条重活在飞时 p95 0.0503s、坏 JSON 422）。

⚠ **收集数 +4 的对账**（避免"数字对不上"）：`HEAD`（本步之前）收集 **1811**，
本步收集 **1815**；差 4 全部来自 `tests/test_research_report.py` 的 **27 → 31**——
2 条是"能生成 Word / 三种渲染器覆盖六种块"，2 条是"失败不留半份产物 / 错误码过 HTTP"。
对账脚本 `var/tmp/collect-head-count.py`（用 `git archive` 抽 `HEAD` 与 `verify-freeze-b20`
各自的树，在两个树里 `pytest --collect-only -q` 各数一次：**1811 / 1811**）。

⚠ **本步的快照标签是 `step-91-docx-third-form`**（标签号比章节号小 1，见 §10.85 §5）。

⚠ **顺带补了一条漏打的快照**：核对标签时发现 `step-90-*` **根本不存在**——§10.91 的文档写了
"快照标签是 `step-90-fix-asgi-note-and-depth-pin`"，但**当时并没有真的跑快照脚本**
（`git tag --points-at 9b57d4c` 当时是空的）。已用 `scripts/snapshot-project.ps1` 补打在
§10.91 的提交 `9b57d4c` 上（附注里写明是补打），§10.91 §4 也**就地更正**了。
这是"我自己的记录与磁盘事实不一致"的第二次同型事故（第一次见 §10.85 §5 的游离提交哈希误记）
⇒ 已把"快照后立刻 `git tag --list 'step-*'` 核一眼"写成纪律。

### 6. 诚实边界

1. **没有真机端到端**：本步全部证据都在**测试夹具 + 内存字节**里。业主重启两道门之前，
   界面上那个按钮**还没跑过本步的代码**（引擎 pid 32564 与 DSH 主机 pid 37268 都早于本步）。
2. **"能生成 Word" ≠ "Word 里排版好看"**：只断言了 zip 结构、`word/document.xml`、样式 id、
   文本与等宽字体。字体回退、行距、分页、中文在**真 Word / WPS** 里的观感**未验**
   （与 PPT 那条边界同型）。
3. **模板契约**：`%APPDATA%/KnowledgeStation/templates/research-report.docx` 若存在，必须保留
   内置样式 `Heading 1/2/3` + `List Bullet`；缺了会**整个报告导出失败**（`docx_render_failed`），
   **不会**只少 Word 一种形态——这是"不静默降级"的**故意**代价（§2）。本机当前**没有**
   `templates/` 目录（=走默认模板），所以这条在真机上**还没被触发过**。
4. `.docx` 只在落盘路径产生 ⇒ `dry_run` 的响应形状**仍然是两种形态**（有意，不是漏改）。
5. **不是原子写入**："先渲染后落盘"只挡住了**渲染**失败；**写盘阶段**失败（磁盘满/权限/
   写第二个文件时断电）仍可能留下不完整的产物集合。已登记，未加固。
6. `files`/`names` 的**顺序**（md, html, docx）是**约定**而不是契约字段；界面按顺序显示。
7. 本步**没有**做 `templates/research-report.docx` 的样板文件（业主想自备版式时得自己放）——
   方案 §8 没要求，先不发明。


## §10.93 收口两个遗留结构洞：`/laws/*` 回到 `def`（`asyncio.to_thread` 全库清零）＋ 重活前缀表补齐

**一句话**：从 §10.85（b16）到 §10.91（b20）每一轮都把同两条写进"下一步"——
「`asyncio.to_thread` 的池不对称」与「`/api/v1/laws/` 不在重活前缀表」。本步把它俩当**一件事**收掉：
5 条 `/laws/*` 从 `async def + await asyncio.to_thread(...)` 改回 `def` ⇒ 回到那口**有界**的池子；
重活前缀表**逐条**补上它们 ⇒ 同时吃重活令牌。副产品：`_ASYNC_ENDPOINTS` 从 **6 条降到 1 条**
（只剩 `/chat/completions`）——"async 是例外"这条纪律第一次真的把例外压到个位数。

### 1. 为什么 `await asyncio.to_thread(...)` 是最容易骗过复核的形状

它**看着**完全正确：真的 `await` 了（审计判据 `effective_real_await()` 也判它 True ⇒
名单第二关过），事件循环**确实**没被冻住（这是 §10.79 那一轮的真实收益）。问题在**界**：

| | 用的池 | 谁在管 |
|---|---|---|
| `def` 端点（Starlette 丢进 anyio） | anyio 默认 limiter | `THREADPOOL_TOKENS = 16`（§10.81/§10.88）+ 重活闸门 4（§10.82） |
| `await anyio.to_thread.run_sync(...)` | 同一口 anyio limiter | 同上 |
| `await asyncio.to_thread(...)` | **asyncio 默认执行器** | **没人管**（`min(32, cpu+4)` 个 worker） |

**实测**（`var/tmp/probe-to-thread-asymmetry.py`：把 anyio 默认 limiter 收到 **2**，
各起 8 条并发跑同一个"睡 0.1s"的活）：

| 写法 | 并发峰值 | 总耗时 |
|---|---|---|
| `anyio.to_thread.run_sync` | **2** | 0.403s |
| `asyncio.to_thread` | **8** | 0.119s |
| 反事实：同一段路改走 anyio | **2** | 0.403s |

⇒ `asyncio.to_thread` **完全绕过**那道令牌数（本机 anyio 默认 worker = 32）。
也就是说：这 5 条端点的"让出事件循环"是**真的**，但"并发有界"是**假的**——
最坏情况下 5 条分钟级的 `/laws/catalog/refresh` 会各占一个池位同时跑。
改回 `def` 之后它们进有界池、并且**同时**吃重活令牌 ⇒ 最坏 4 条。

### 2. 代价（与 §10.86 那 51 条同款，诚实登记）

1. **报错形状变了**：body 由 FastAPI 在派发进线程池**之前**解析 ⇒ 非法 JSON 现在是 FastAPI 自己的
   422，不再是本文件的 `json_error(422, "bad_json", ...)`；空 body 变成 `payload is None`
   ⇒ 走各端点自己的"缺少 xxx"分支（状态码仍是 422）。仓内**无消费者**：`plugin` 里那个
   `bad_json` 是**主机侧**自己的 body 闸，与引擎无关（已 grep 核对）。
2. **排队语义变了**：单条 `/laws/*` 从"默认执行器（32 位）"变成"有界池（16）+ 重活闸门（4）"。
   5 条并发的 `/laws/catalog/refresh` 现在会**排队**（是队列不是报错）——这正是那道界的作用。
3. `GET /laws/catalog` 与 `GET /laws/sources` **故意没进**重活表（一个是本地快读、一个是静态字典），
   否则"开法规目录要排在一条分钟级爬取后面"，就是 §10.82 记的"**闸门自己造排队**"。

### 3. 判据升级：从"看记号"→"看有没有 await"→**"看它用的是哪口池"**

| 层 | 判据 | 位置 |
|---|---|---|
| 通则一 | `async def` 零 await-like ⇒ 必须 `def` | `test_T1_零await的async端点必须是def` |
| 通则二 | `async` 是例外，必须在 `_ASYNC_ENDPOINTS` 写理由且过 `effective_real_await` | `test_async端点必须在显式名单里` |
| **通则三（本步）** | **端点里不许出现 `asyncio.to_thread` / `run_in_executor`** | `test_端点上不许用_asyncio_to_thread` |
| 通则三的**理由**（回归锚） | 令牌=2 时 anyio ≤2、`asyncio.to_thread` ≥4 | `tests/test_threadpool_bound.py::test_asyncio_to_thread_绕过_anyio_闸门` |

⚠ **通则三的判据是 AST**（不是文本扫描）：注释/docstring 里提到这些名字不算（§10.78 那个假阳性
就是注释被当行为），并带 6 个合成正负样本 + 一条**带缩进源码**的样本。
⚠ 那条带缩进的样本是**踩出来的**：`inspect.getsource()` 对闭包内定义的端点（`create_app()`/
`register()` 里的那些）返回**带缩进**的源码，直接 `ast.parse` 就是 `IndentationError`
（本节第一版就这么炸的）。`scripts/audit-async-endpoints.py` 第 187 行早就记过这个坑，
但**新写的判据不会自动继承前人的注释**——所以合成样本里也钉一条。

**顺带修掉一个失效的哨兵**：两条通则原先用"扫到 ≥4/≥5 条 async 端点"当**防假绿**的反向断言，
async 只剩 1 条之后这种魔数就没意义了（1 条也能"扫过"）。现在改成
`扫到的 async 集合 == set(_ASYNC_ENDPOINTS)`——比魔数更贴事实，也不会随端点增减而失效。

### 4. 顺带发现并修掉一条**既存**的顺序依赖假绿（与本步改动无关）

`tests/test_law_catalog.py::test_refresh_full_crawl_dedup_and_result` 断言
`out["by_category"] == {法律T1:250, 行政法规T1:30, 法律解释T1:2}`，但 `by_category` 是
**全表**分组计数（`catalog.py` 那句 `SELECT category, COUNT(*) … GROUP BY category`），
而 conftest 的库是**会话级共享**的 ⇒ 只要在它前面跑过 `tests/test_law_source_api.py`
（它会往 `law_catalog` 里留下一行 `API测试`），这条就**红**；全量跑（字母序 `law_catalog` 在前）
却**绿**。

**取证**（`var/tmp/probe-preexisting-pollution.py`：在 **`HEAD` 的干净树**里跑同样两个文件）：

| 顺序 | 结果 |
|---|---|
| `test_law_source_api.py` → `test_law_catalog.py` | **1 failed** |
| 倒序 | 22 passed |

⇒ 与本节改动**无关**，`HEAD` 上就复现。修法照**该文件自己开头写的纪律**（第 8–9 行：
"涉及全局计数的断言一律用「基线 + 本次增量」"）：改成与基线相减的**增量字典**相等。
这是本步的第二条教训：**全量绿 ≠ 每个子集都绿**（这条只有在按非字母序挑文件跑时才会露出来）。

### 4.5 顺带修掉第二条既存的**时序假红**：`test_deep_server` 的"残留 daemon"

同一次全量跑里还有一条红：`tests/test_deep_server.py::test_提交与等待拆分_先投后收`
——这条**方案"已知未决 §1"早就登记过**（"全量跑里红过一次、单跑 8/8 绿，时序/GIL 敏感"），
但一直没人定位到具体机制。本步把它读明白了：

`_fake_daemon()` 在**循环里**每次调 `ds._job_dir()`，而 `_job_dir()` 是**现读环境变量**
`KS_DEEP_JOBS_DIR`；本文件每个用例靠 `monkeypatch.setenv` 拿自己的目录。于是：
上一用例 `stop.set()` 之后、线程真正退出之前，monkeypatch 可能已经把环境变量切给了**下一个用例**
⇒ 这个"残留 daemon"会去动**别人的**任务目录。`fail=True` 那个更狠（它给下一个用例的任务写
`.error.json` ⇒ 那个用例的 `deep_server_wait` 返回 `None` ⇒ 断言红）。窗口只有几十微秒，
所以表现为"几千条用例里偶发红一次"。

**修法**（不放松任何断言）：① `_fake_daemon` 启动时就把目录**捕获一次**，此后只认自己那个；
② 三处调用方 `stop.set()` 之后 `t.join(2.0)`，把窗口关死。
**验证**：整文件 8/8 绿；连跑 **20 次整文件 0 红**（`var/tmp/repro-deep-server-flake.py`）。

### 4.6 顺带修掉第三条既存假绿：`test_ks_answer` 硬编码仓库路径（**复核 b21 的 MEDIUM**）

`tests/test_ks_answer.py:18` 原写 `sys.path.insert(0, r"D:\AI\work space\zcode")`。这会
把**工作区**顶到 `sys.path[0]` ⇒ 在 `git archive` 抽出的冻结树里**单文件跑**时，
`src` / `src.core.llm.ks_answer` 全部从**工作区**加载——用例**绿在对另一棵树的测试上**，
输出只有一句 `27 passed`。**我自己复现过**（`var/tmp/probe-ksanswer-syspath.py`：抽 `HEAD` 的树，
用小 pytest 插件打印模块来源）：

| | `src.core.llm.ks_answer.__file__` |
|---|---|
| 修前（树里跑） | `D:\AI\work space\zcode\src\core\llm\ks_answer.py`（**工作区**） |
| 修后（树里跑） | `<提取树>\src\core\llm\ks_answer.py` |

修法：`ROOT = Path(__file__).resolve().parent.parent`（与 `tests/test_golden_gate.py` 同款），
并把"这里曾经硬编码过"写进该文件 docstring。
⚠ 这条是**复核纪律的元缺陷**：它让"在冻结树里独立复核"这件事本身失真。

### 5. 证据

- 探针：`var/tmp/probe-to-thread-asymmetry.py`（上表）；`var/tmp/probe-preexisting-pollution.py`（上表）；
  `var/tmp/probe-ksanswer-syspath.py`（§4.6 的来源对照）；`var/tmp/repro-deep-server-flake.py`（§4.5 的 20 连跑）。
- `pytest` **1820 passed / 3 skipped / 0 failed**（收集 **1823** = 上一步 1815 + 本步 3 条新用例 **+5 个
  `test_declared_sync` 参数**；⚠ 我第一版把通过数写成 1822——那次全量跑里有 **1 条红**
  （就是 §4.5 那条残留 daemon 假红），修掉之后才是 1820/0 failed；复核实测 1823 也纠正了我
  漏算参数化 5 条的错）；其中 async 集合与名单一致的断言、`test_declared_sync` 表 **48 → 53** 行。
- `mypy` **134 / 0**；`tsc` **0**；`smoke` **EXIT=0**（19 段，11 段打印 `== … PASS ==`）；
  `verify:commands` **22/22**；`scripts/verify-engine-uvicorn.py` **4/4**。
- `plugin/client.js` 重新构建后 **字节不变**（构建脚本的假"bytes"输出已修：现在同时打印
  `1282106 bytes (1280561 chars)`，见 §10.92 §4 的更正）。

⚠ **本步的快照标签是 `step-92-laws-def-and-heavy-table`**（标签号比章节号小 1，见 §10.85 §5）。

### 6. 附：处理复核 b21（区间 `verify-freeze-b20`..`verify-freeze-b21`，6 条**全部 CONFIRMED**）

复核报告 `var/tmp/verify-b21-artifacts/VERIFY-REPORT.md`（500 行 + 原始日志）。
它**自己写变异**证明：把"先渲染后落盘"改回旧顺序 ⇒ 唯一守卫
（`tests/test_research_report.py` 的 `assert list(tmp_path.iterdir()) == []`）红、盘上恰好 **2 个孤儿**；
同尺寸变异 `h2→h4`（docx 里静默丢二级标题）⇒ 两条用例红；用真缺样式模板走全路径 ⇒
`docx_render_failed` + 导出目录 0 文件；`git hash-object` 校验变异复原；
自制收集数 **1815 = 1811 + 4**（与该文件 27→31 算术吻合）。它判**"本区间可以信"**。

它的两条 finding 与 2 条 INFO（**均已收口或已记录**）：

| 编号 | 一句话 | 处理 |
|---|---|---|
| **b21-MEDIUM** | `tests/test_ks_answer.py` 硬编码仓库路径 ⇒ 冻结树里单跑时**从工作区加载 `src`**，"27 passed"是绿在对工作区的测试上（**非本区间引入**，baseline 起就有） | ✅ §4.6 修（`__file__` 反推树根）+ 我自己复现过来源对照 |
| b21-LOW | §10.92 §4 记 `client.js` = 1280561 "字节"，而 git blob 是 1282106（差 1545） | ✅ 真相是构建脚本把**字符数**当字节数打印（`out.length`）：改成同时打印两者；§10.92 §4 就地更正（与 b20 的 1282101 差 **5 字节** = 多出的 `/Word`） |
| b21-INFO-1 | `git archive` 在 `core.autocrlf` 下导出 **CRLF**、工作区是 LF（同文件 30015 vs 29506 B）⇒ **别拿工作区文件当提取树备份** | 📝 已登记（复核纪律） |
| b21-INFO-2 | 复核期间工作区被"本会话之外的写者"改了 7 个文件 | 📝 **那个写者就是我**（同一时间我在做 §10.93）；HEAD 未动、冻结区间完好。⇒ 纪律：**冻结标签是"只读"的，但工作区不是**；复核方只看提取树是对的 |
| b21-INFO-3 | 4 条 skip 逐条列出（作者 3 条）⇒ 机器口径差（本机多一条 reranker 模型未下载的 skip） | 📝 接受（收集数与 0 failed 一致） |

### 7. 诚实边界

1. **判据是源码级的**：它挡得住"在端点里直接写 `asyncio.to_thread`"，挡不住"封装进一个被调用的
   助手模块"。**扫不到 ≠ 没有**——所以 offenders 文案直接给出两条替代写法，而不是只说"别用"。
2. **没有真机端到端**：这 5 条的真实网络耗时（秒级/分钟级）**本步没有实测**；把它们放进重活表用的是
   **结构性**判据（同族网络/长跑活已在 §10.71–§10.80 被量过）。要拿到真数字得等业主重启后跑真机。
3. 唯一剩下的 async 端点 `/chat/completions`（SSE）**不在**重活表里，**故意**：它占线程的时间是
   "逐块取 LLM 输出"的毫秒级，不吃线程的分钟级长跑；哪天真在本进程里跑同步重活，通则一/通则二/
   通则三会先红。⚠ 但它**没有**一条"measured"证据说明它不吃线程——这是**结构性判断**。
4. `anyio.to_thread.run_sync` 仍是**允许**的写法（它进同一口有界池）——判据禁的是"换池"，不是"用线程"。
5. 本步**没有**做 §10.85 起就一直挂着的另一项「量具（`measure-endpoint-blocking.py`）接名单当第二层」：
   本步的判据是**静态**的（AST）。量具那条要按端点造种子数据，否则会变成"请求早早失败⇒空档≈0⇒假绿"，
   反而引入**假覆盖**——留在下一步（要么给出真正可测的用例，要么明确写成"名单里哪些端点不可量、为什么"）。
6. **三条"顺带修掉的既存问题"都不是本步主题**，各自的守卫强度不一样（如实说）：
   · §4 顺序依赖假绿：修后**两个文件顺序都跑过**（各 22 passed）⇒ 有直接证据；
   · §4.5 残留 daemon：**原始红没复现出来**（40 次单跑 + 20 次整文件跑 0 红），机制是**读代码**推的
     （`_job_dir()` 现读 env + 线程在循环里调用），修法把那个窗口关死了 ⇒ 结论是"修法与机制自洽"，
     **不等于**"已证明那就是历史那次红的成因"；
   · §4.6 硬编码路径：有**来源对照**（修前工作区 / 修后提取树）⇒ 直接证据，且这正是复核方报的 MEDIUM。
7. b21 的 INFO-1（`core.autocrlf` 下提取树是 **CRLF**、工作区是 LF ⇒ 别拿工作区文件当提取树备份）
   **只记在本节**，没有写进任何复核模板 ⇒ 下一轮复核方仍可能踩到。已登记。


## §10.94 量具接名单（第二层）——**尺子抓出并修掉**了 `/chat/completions` 冷启动冻引擎 6.79s

**一句话**：§10.85（b17）起每一轮都写"把量具接到名单上当第二层"，本步做完了；而它**第一次
跑就抓出一个真缺陷**：唯一剩下的 async 端点 `/api/v1/chat/completions` 在**启动后第一次提问**
会把整个事件循环占住 **6.79s**（fastembed 下载/加载模型 ≈5.2s + jieba 建词典 ≈0.33s，两件都发生在
`async def` 端点体里）。修法是"进循环体之前先在线程里预热"，首次请求的**耗时不变**（下载照做，
8.14s），但空档 **6.79s → 0.056s**（引擎不再被冻住）。

### 1. 为什么这条"第二层"现在做得成、以前做不成

以前名单里有 **6 条** async 端点，其中 5 条是网络/数据库活、要按端点造种子数据才量得出来，
一条条铺开就是"为了量而造一整套 fixture"。§10.93 把那 5 条改回 `def` 之后名单只剩 1 条，
于是"接名单"变成一个**可完成**的动作。做法（`tests/test_material_api.py`）：

1. `_MEASURED_ASYNC`（**量过**）与 `_NOT_MEASURABLE_ASYNC`（**写明为什么量不了**）两张表
   必须**恰好覆盖** `_ASYNC_ENDPOINTS`、两两不交、理由非空 —— 名单新增一条就红，
   逼作者**做决定**而不是默认放过（"点名一条、其余放过"比不做更坏：那是假覆盖）。
2. 对量过的那条**真的量**：`scripts/measure-endpoint-blocking.py` 的心跳 + `ASGITransport`。
   两个"工作"都是**自己塞进去的定值**，不依赖机器性能、不联网：
   · 假 LLM 流每块在**线程**里阻塞 `0.3s ×3`（`stream_chat_completion` 被 monkeypatch）；
   · 假 fastembed `__init__` 阻塞 `1.0s`（`embedder._import_text_embedding` 这个
     **模块 docstring 里写明的"唯一缝"**）。
   断言两条**同时**成立：耗时 ≥ `1.0 + 0.9×0.8`（**活真的干了**，否则"空档小"毫无意义）
   + 最大空档 < `0.5s`。

### 2. 尺子量出来的缺陷（**改前**，`var/tmp/probe-chat-blocking.py`）

同一个进程连量三次（每次的"活"都是 3×0.3s 的假 LLM 分块）：

| 第几次 | 端点耗时 | **事件循环最大空档** | 心跳样本 |
|---|---|---|---|
| 第 1 次（冷） | 7.70s | **6.79s** | 82 |
| 第 2 次 | 0.91s | 0.020s | 83 |
| 第 3 次 | 0.91s | 0.019s | 83 |

⇒ 不是"每请求都慢"，而是**一次性初始化放错了位置**：`def` 端点（`/ks/answer` 等）天生跑在
线程池里，所以它们冷启动只是"这条请求慢"；这条 `async def` 端点把同样的活放在**事件循环**里
⇒ 启动后第一次提问期间**连 `/health` 都不响应**（正是本战役从 §10.71 起一直在治的那一类）。
顺带量到：检索本身（热态、空库）单独调用只要 **0.006s**，所以那 6.79s 里几乎全是模型与词典。

### 3. 修法：**进循环体之前，在线程里把两件一次性初始化付掉**

`server.py` 新增 `warm_retrieval_stack()`（幂等，返回"做过几次加载尝试"给探针断言），
端点在解析完 body、**任何检索/分词之前**插一行：

```python
await anyio.to_thread.run_sync(warm_retrieval_stack)
```

- 幂等：`embedder.health() == "ok"` 就**不进** `_get_model()`；jieba 自己认 `dt.initialized`
  ⇒ 热态代价只有**一次线程跳**（实测 0.1–0.15ms，§10.87 那个数字）。
- 失败**绝不影响请求**：`is_available()` 自己吞异常并进 60s 冷却（返回 False），jieba 那条也包起来。
- **为什么不在 lifespan 里预热**：① `httpx.ASGITransport` 不跑 lifespan（量具与真实路径会不一致，
  §10.81 踩过）；② 离线机器上启动会卡一次下载超时；③ `/health` 必须廉价，启动变慢会牵动
  插件侧就绪握手。

**改后**同一个探针（同进程）：

| 第几次 | 端点耗时 | **最大空档** |
|---|---|---|
| 第 1 次（冷） | 8.14s | **0.056s** |
| 第 2 次 | 0.91s | 0.017s |
| 第 3 次 | 0.91s | 0.016s |

（首请求 8.14s > 改前 7.70s 是**做同一件事**的正常抖动——下载 5 个模型文件；差别只在
**这 8 秒里引擎是活的**：544 个心跳样本 vs 改前 82 个。）

### 4. 判据承重：两个反事实都做了（字节级变异 + 逐字节复原，前后 sha256 相同）

| 变异 | 结果 |
|---|---|
| ① 删掉 `await anyio.to_thread.run_sync(warm_retrieval_stack)` | 红在 `< max(1.0, 0.3)/2` 那条上，`max_gap_s = **1.3382s**`（`duration 2.25s` = 1.0s 假加载 + 0.9s 假 LLM） |
| ② 把 `part = await anyio.to_thread.run_sync(_next_chunk)` 改成 `part = _next_chunk()` | 红在同一条上，`max_gap_s = **0.6011s** |

变异脚本：`var/tmp/mutate-step94.py`、`var/tmp/mutate-step94-streaming.py`（都打印
`before/after sha256` 并断言相等）。

### 5. 证据

- `pytest` **1821 passed / 3 skipped / 0 failed**（收集 **1824** = §10.93 的 1823 + 本步 1 条）；
  `mypy` **134 / 0**；`tsc` **0**；`smoke` **EXIT=0**（19 段，11 段打印 `== … PASS ==`）；
  `verify:commands` **22/22**；`verify-engine-uvicorn` **4/4**；
- 探针 `var/tmp/probe-chat-blocking.py`（上表，改前/改后各一次）；两个变异（上表）；
- 相关测试文件（chat 一族 7 个 + material_api + threadpool）**184 passed**。

⚠ **本步的快照标签是 `step-93-chat-warmup-and-measured-allowlist`**（标签号比章节号小 1，见 §10.85 §5）。

### 6. 诚实边界

1. 修的是**一次性初始化**（模型/词典），**不是**"检索不在循环里"：热态检索仍在事件循环里跑，
   空库实测 **≈14ms**（端点耗时 0.91s 减去假 LLM 的 0.9s）。**真实大库上没量过**——那里
   FTS + 向量检索可能到百毫秒级。⇒ 若真机量出来偏大，正确修法是把**整段检索**挪进线程
   （拆 `_prepare` 供 `run_sync` 用），那是独立一步，本步没做。
2. 这条用例是**计时**判据（阈值 0.5s，两个慢点是自塞的 1.0s/0.3s）⇒ 机器极卡时理论上可能偶发红；
   处置是**调大常数**，不是放松断言。与 `tests/test_measure_harness.py` 同款余量。
3. 离线机器上：预热会在线程里付一次网络超时（之后 60s 冷却窗口内不再付）——
   **离线场景没实测过**（本机是联网的）。
4. `/chat/completions` 仍然**不在**重活前缀表里（§10.93 §7.3 的判断：它占线程的时间是逐块取数的
   毫秒级）；本步多出来的那次线程跳同样不吃重活令牌。
5. 本步**没有**真机端到端：所有数字都来自进程内 `ASGITransport` + 假 LLM/假 fastembed。
   真机上的 fastembed 可能是**本地已缓存**版本（不会下载 5.2s），那时冷启动成本更低——
   但这不影响"加载发生在循环里"这个结论（假替身正是为了把这一步**定值化**）。


## §10.96 自动成文落地（D-5a）：结论**草稿**端点——零新提示词，且**更正了我上一节的形态取舍**

**一句话**：§10.95 把"自动成文"立项了，业主答"按你的推荐继续"；本步按推荐做完 **D-5a**：
`POST /api/v1/report/research/draft`（引擎）+ `/ks/report/research/draft`（主机白名单转发）+
客户端 api 函数。草稿基于**已批准材料**、带 `unapproved_draft` 标记、引用逐条校验，
**不落盘、不进报告**（是否采用由用户逐次显式决定）。

### 1. ⚠ 先更正我自己：§10.95 的"形态 A 被否掉"是**读漏了**

§10.95 §3 把"复用取证链"当作形态 A 并否掉，理由是"答案链引的是**法条** `[[c:i]]`，
报告校验器核不了材料 —— 那样拼出来的结论每条引用都'本次无法核验'"。**这个理由不成立**：

`ks_answer.answer(query, params={"material_project_id": pid})` **本来就有**材料范围那条路——
① 取**已批准**材料（评审硬门同一条）、② 把材料**另起一节**渲染进提示词
（`[[m:i]]` 编号由 `authority.render_evidence` 分配）、③ 在 `material_usage` 里回
**`usable_indices`**，注释原文就写着"**产出物按它拼引用**"。我上一节只看了 `/ks/answer`
的**法条**那一半就下了结论。

⇒ 落到实现上的正确形态是 **形态 C：复用取证链的**提示词**，但只喂材料**：

```python
assembled = authority.assemble_evidence(project_id, query, limit=limit)
if not authority.usable_hits(assembled):        # 没有可承重材料
    return 空草稿 + "没有起草" + llm_called=False   # ⚠ **一次 LLM 都不调**
materials_text = authority.render_evidence(assembled)
messages = ka.build_messages(query, [], "default", materials_text)   # ← 既有提示词，零新增
raw = ka._collect_stream(ka._stream_llm(messages))                   # ← 既有传输 + 既有测试缝
draft = ka.parse_llm_answer(raw, 0, counts["total"])["conclusion"]
citations, warnings = check_conclusion_citations(draft, assembled)   # ← 与报告同一个判据
```

**两处关键设计**（都不是"顺手"）：

1. **一次检索、一次装配**：提示词里的 `[[m:i]]` 编号与校验用的编号**必须来自同一个
   `assembled`**。若"先调链、再重新检索一遍来校验"，两次检索的命中顺序可能不同 ⇒ 编号漂移 ⇒
   把**合法引用误判成"引用了不存在的材料"**。用例
   `test_提示词里材料另起一节且编号与校验同一套` 钉住这条不变量。
2. **把"引用判据 + 警告措辞"抽成唯一所有者**：`research_report.check_conclusion_citations()`
   （从 `build_report_blocks` 里抽出来），报告与草稿**共用**。不抽的话，同一段文字会在两处
   得到不同的警告——那是本项目一路在堵的分叉。

### 2. 落地清单

| 位置 | 内容 |
|---|---|
| `src/core/exports/research_draft.py`（新） | `draft_conclusion()`：装配 → 守卫 → 提示词 → LLM → 解析 → 引用校验；`DRAFT_STATUS`/`DRAFT_DISCLAIMER` |
| `src/core/exports/research_report.py` | 抽出 `check_conclusion_citations()`（**唯一判据 + 唯一措辞**），`build_report_blocks` 改为调它 |
| `src/core/api/routes_report.py` | `POST /report/research/draft`（**`def`** ⇒ 同步 LLM 调用走线程池 + 吃重活令牌）；422/404/500 与 `/report/research` 同款 |
| `plugin/src/report.js` | `/ks/report/research/draft` 白名单转发（只认 `project_id`/`query`/`limit`；超时 120s） |
| `plugin/client/api.ts` | `exportResearchDraft()` + `KsResearchDraft`（**snake_case 与引擎逐字一致**——`ksJson` 只透传不做命名转换） |
| `tests/test_research_draft.py`（新） | 13 条：没材料不调模型 / 空输出不是成功 / 项目不存在 / LLM 不可用 / 正常路径 / 同源不变量 / 越界与"仅线索"引用 / 端点 422·404·200·500 |
| 冒烟 | `smoke-report-routes` **33/33**（新增 8 条：路径、白名单、缺 query 不打扰引擎、405、`llm_called=false` 原样透传、500 不伪装）；`smoke-report-ui` **21/21**（新增 5 条） |
| `tests/test_material_api.py` | `test_declared_sync` 表 +1 行（`/report/research/draft` 必须 `def`） |
| 文档 | 本节 + `docs/AUTO-DRAFT-PLAN.md`（更正形态取舍、§4.1–§4.3 按实现重写、§8/§9 记"业主已答按推荐"）+ 方案 D-3b / D-5a / 账本第 42 条 |

### 3. 证据

- `pytest` **1835 passed / 3 skipped / 0 failed**（收集 **1838** = §10.95 的 1824 + 本步 13 条
  新用例 + 1 个 `test_declared_sync` 参数）；
  ⚠ **skip 数与机器相关**（§10.98 补注）：本机 **3** 条，复核 b25 的机器 **4** 条——差的那条是
  `tests/test_golden_set.py:31`（"真实库无 GB 30871"），**本机有该数据所以它真的跑了**。
  ⇒ 门禁数字一律同时报"收集数 + passed + skipped + failed"，**别只看 passed**；
- `mypy` **135 / 0**（⚠ 文件数从 134 涨到 135——本步新增 `research_draft.py`；
  **不变量是"0 错误"**，不是那个数）；`tsc` **0**；
- `smoke` **EXIT=0**（19 段，11 段打印 `== … PASS ==`；其中 `report-ui` **21/21**、
  `report-routes` **33/33**）；`verify:commands` **22/22**；`verify-engine-uvicorn` **4/4**；
- 相关文件合跑：`test_research_draft.py` + `test_research_report.py` + `test_answer_materials.py`
  **84 passed**；`test_declared_sync` 表 **54** 行（新增 `/report/research/draft`）。

⚠ **本步的快照标签是 `step-95-research-draft`**（标签号比章节号小 1，见 §10.85 §5）。

### 4. 诚实边界

1. **"草稿"不等于"正确"**：引用校验只证明"引用的材料真实且可承重"，**不**证明"这句话确实由
   那条材料支持"（语义级核验需要逐句蕴含判定——不在本步）。
2. **没有评测集**：本步的验收全是**结构性判据**（路径、标记、守卫、失败矩阵），
   **不谈**草稿质量。
3. **提示词注入风险登记在案**（§10.95 §5 那一行）：材料正文是外部文本、原样进提示词，
   本步**没有**做内容隔离或注入检测。
4. 默认**不带**法条链（`evidence=[]`）⇒ 提示词里"证据条款："一节是空的；这是决策点②的
   推荐取法，要改就是一次 `build_messages` 的入参。
5. **没有真机**：全部证据来自 `TestClient`/进程内 + 假 LLM（`_stream_llm` monkeypatch）。
   真机上一次真实起草的**质量**必须由业主看过才算数。


## §10.97 自动成文 D-5b：面板接线——「起草结论（草稿）」+ **绝不自动填**

**一句话**：§10.96 把结论草稿做成了端点，本步把它接到面板上，并**用判据钉住三条最容易被
"顺手做掉"的纪律**：① 草稿必须显眼标明**未批准**；② **绝不自动填进结论框**——只有用户点
「用这段填进结论框」才写；③ 引擎"一次模型都没调"（没有可承重材料）要按**没起草**如实说，
不是失败。

### 1. 为什么这三条必须**用判据**钉，而不是"写代码时注意"

"自动填"是最自然、也最危险的实现：起草回来了，`setConclusionMd(draft.draft_md)` 一行就完事，
用户看到结论框里已经有字、直接点"生成研究报告" ⇒ **系统起草的内容以用户的批准姿态进了报告**。
那一行代码在评审时"看起来很方便"，在 P1 口径上却是把**用户的批准动作偷走**。

所以本步把判据放在两处：

| 判据 | 位置 | 挡的是什么 |
|---|---|---|
| `onDraftConclusion` 的**源码切片**里不许出现 `setConclusionMd`（切成那个 useCallback 的 body 再看） | `scripts/smoke-draft-ui.mjs` | "响应回来顺手填一下" |
| `setConclusionMd(` 在面板里**恰好两处**：结论框自己的 `onChange` + 「用这段」按钮 | 同上 | 多出第三处（第二个自动填入口） |
| `canApplyDraft(draft)`：没起草过 / `llm_called === false` / 空草稿 ⇒ **false** | 面板导出的**纯函数**，冒烟真的调用它（5 档） | "空草稿也允许填"⇒ 用户点一下发现什么都没变 |
| 三处文案存在（「未批准草稿」「不得作为依据」「用这段填进结论框」）+ `role="status"` | 同上 + `smoke-client-entry` 扫**构建产物** | 文案被删/产物没重建 |

⚠ 源码切片判据是**行为代理**（不是真渲染）：本仓 `plugin/` 没装 jsdom，而这条判据要问的是
"**在这个回调里**有没有写状态"，源码切片正好能回答；真渲染那条留给 `smoke-anchor-mark.mjs`
那种静态渲染（它证明的是"条件成立时渲染出什么"）。两者互补，**都留在链上**。

> ⚠⚠ **2026-09-18 就地更正（§10.99）：上面这套"源码切片 + 计数"判据被复核 b26 判为
> H1 REFUTED——它能被一个别名绕过并让门禁全绿，而"自动填"真的发生。**
> 结论不再是"两者互补"，而是"**字符串级判据钉的是写法、不是性质**"。
> §10.99 已把它换成三层（纯函数语义 / `useReducer` 封闭动作集 / 到达路径窄判据），
> 并如实登记了"藏在切片之外的伪造动作"这一**残余**。读本节时请以 §10.99 为准。

### 2. 落地的界面行为

- 产出区新增按钮**「起草结论（草稿）」**：`researchQuery` 为空时**不发请求**，直接提示
  "起草结论要先填「研究问题」"（草稿必须知道要回答什么——引擎侧也是 422）。
- 草稿块（`role="status"`，虚线边框）：**未批准草稿**标题 + 「不得作为依据」+
  只读草稿正文 + **警告原样列出**（引用不成立 / 仅线索 / 模型没产出结论段）+
  「用这段填进结论框」（`canApplyDraft` 为 true 才可点）。
- `llm_called === false` ⇒ **单独分支**："没有可承重的已批准材料，引擎**没有起草**（一次模型都没调）"
  ——不显示成错误、也不显示成"生成了一份空草稿"。

### 3. 证据

- 新冒烟 `smoke-draft-ui.mjs`（**19/19**）：`canApplyDraft` 5 档 + 源码切片 3 条 + 文案 5 条；
- `smoke-client-entry.mjs` **89/89**（+4：按钮与三句纪律文案，扫的是**构建产物** `client.js`
  1287342 字节 / 1285797 字符）；
- `smoke` 链 **EXIT=0**（**20 段**，12 段打印 `== … PASS ==`；⚠ 上一步是 19 段/11 段，
  本步新增一段 —— 段落数是**链的事实**，不是"数字好看"）；
- `tsc` **0**；`pytest` **1835 passed / 3 skipped / 0 failed**（收集 1838——本步只改 `plugin/`，
  用例数不变）；`mypy` **135 / 0**；
- `verify:commands` 22/22；`verify-engine-uvicorn` 4/4。

⚠ **本步的快照标签是 `step-96-draft-panel`**（标签号比章节号小 1，见 §10.85 §5）。

### 4. 诚实边界

1. **没有真机**：面板的行为判据是**源码切片 + 纯函数**（无 jsdom、无真渲染整个面板）。
   "点一下按钮真的把草稿填进去了"这件事**没有被自动化验证**——它由 `canApplyDraft` 与那一处
   `onClick` 的组合**推**出来，最终要业主在界面上点一次才算数。
2. **草稿进了结论框之后就不再被标记**：用户点「用这段」⇒ 结论框里就是普通文本，
   报告里也不会写"这段来自草稿"。这是决策点③（"允许写进报告，但逐次显式确认"）的
   **已知代价**：显式确认被记录在"用户点了那一下"，而**产物里没有痕迹**。
   若要产物带痕迹（例如报告里加一句"结论含系统草稿"），那需要改报告的内容块 —— **本步没做**。
3. 面板仍未显示 `counts`/`notes`（引擎回了，界面只显示警告）——不是本步的判据，登记。
4. 全链的**计时/依赖**前提与上一步相同：无真机、无真 LLM（冒烟里一律替身）。


## §10.98 处理复核 b25：材料装配失败的**裸 500** + 一条**噪声警告** + 补"只装配一次"的门禁

**一句话**：独立复核 b25（冻结在 `verify-freeze-b25` = `2860939`，§10.96 那一步）判
**H1–H5 CONFIRMED、H7 CONFIRMED、H6 PARTLY**，总评"**本区间可以信**"；它另外报了
**2 条 MEDIUM + 3 条 LOW + 1 条 INFO**。本步把其中**能立刻修的 3 条**修掉（各带变异证据），
1 条改文档口径，其余登记。

### 1. 复核确认了什么（挑三条最值钱的）

- **H1（P1 性质）**：只有"仅线索"材料时，计数替身 `_stream_llm` **0 次调用**；
  对照臂（有可承重材料时）**1 次**；删掉守卫反事实 ⇒ 我的用例红在**预期断言**上，
  且它的探针显示替身**真被调到**、模型编出了结论（`draft_md='y'`）⇒
  "**没有可承重材料就一次模型都不调**"这条性质**双向**被证实。
- **H2（同源不变量）**：`draft_conclusion` 全函数**只有一次** `assemble_evidence`（计数器实测 = 1）；
  引用"仅线索"的 `[[m:1]]` ⇒ `not_load_bearing == [{"index":1,"group":"leads_only"}]`；
  它还**自己造了反事实**：让"第二次装配"造成编号平移一格 ⇒ 同一段**合法**草稿被翻成
  "不得承重" ⇒ 我"两次检索会编号漂移"的论证**不是纯理论的**。
- **H4**：失败矩阵**每条真触发**（422×4 / 404 / 500 `llm_unavailable` / 空输出 / 200），
  并加了一条我没想到的证据：**目录快照**证明草稿**零新增文件**（对照 `/report/research` 落 3 份）
  ⇒ "不落盘"这条有**分辨力**。

### 2. 修掉的三条（各带字节级变异）

| 编号 | 问题 | 修法 | 变异证据 |
|---|---|---|---|
| **b25-MEDIUM-1** | `research_draft.py` 的 `assemble_evidence` **不在 try 里**（报告的同一处也不在）⇒ 库损坏/锁死时异常**穿过**路由层那两个 `except`（只接 `ValueError`/`KnowledgeStationError`）变成**裸 500**：用户只看到 "Internal Server Error"，真原因只在日志里 | 新增**一个入口** `research_report.assemble_evidence_or_raise()`（**两处调用点都改走它**）：`ValueError` 照原样放行（路由层靠它翻 404），其余异常一律翻成 `KnowledgeStationError(code="materials_load_failed")` + 可操作信息 | M1：把它改回"不接异常" ⇒ 用例红，异常是 `RuntimeError: 数据库被锁死（模拟）`（正是"裸 500"的形状） |
| **b25-LOW-2** | 取证链提示词**无条件**要求 `[[c:i]]` 标记，而草稿**故意不喂法条** ⇒ 真模型（会照提示词写 `[[c:i]]`）在**正常路径**上就吃一条 `llm_json_no_citation_marker` **噪声**；噪声的坏处是"以后用户不信真警告" | **滤掉不适用的那条、换成准确的那条**：草稿里**出现** `[[c:i]]` 时明说"本次起草**没有喂法条证据**，这些编号无从核验（本次只逐条核材料引用）" —— 不是"少报"，是把同一条换成说得通的措辞 | M2：把过滤改回"全收" ⇒ 用例红在噪声断言上（输出里两条同时出现） |
| **b25-LOW-3** | 支撑 H2 的"**只装配一次**"**没有任何用例守着**（复核方是用 monkeypatch 计数器才钉住的） | 新用例 `test_只装配一次`：计数器断言 `== 1`，并同时断言"校验用的编号就是那一次的编号" | M3：让 `draft_conclusion` 装配两次 ⇒ 用例红在 `calls["n"] == 1`（实测 2） |

顺带把"法条编号"的**正则**也收进唯一所有者：`research_report.clause_refs()`
（原先 `_RE_CLAUSE_REF` 在报告里私有，草稿要用就得**再写一份正则**——那正是本项目一路在堵的分叉）。

### 3. 改口径的一条（b25-MEDIUM-2）：那次失误**归因过轻**

b25 指出 §10.96 §1 只承认"我漏读了答案链的材料范围"，没说**架构差异**——而那才是选**形态 C**
的隐藏理由。补上（同时写进 `docs/AUTO-DRAFT-PLAN.md` §3）：

1. **答案链的材料路是"fail-open + 披露"**：材料装载失败时它 `except` 住、把错误记进
   `material_usage["error"]` 与 `notes`，然后**照样调模型**（提示词里没有材料节，
   但**有**法条证据）⇒ 产出一份"没用到项目材料、但披露了"的答案。
   **草稿不能这么做**：用户要的就是"基于我的材料起一稿" ⇒ 本步的选择是
   **没材料就不调模型 / 装配失败就报可操作错误**（与答案链**故意**不同）。
2. 答案链一次给的是**三段式整份答案**（依据区/推导区/结论区）且默认带法条证据；
   报告要的只是"结论"一段 ⇒ 直接照搬形状也不对。

⇒ 所以正确形态是"**复用提示词与传输，但自己拿守卫**"，而不是"直接调 `answer()`"。
这条不是措辞问题：它决定了**错误路径**的语义（本步的 MEDIUM-1 修法正是它的落地）。

### 4. 登记（本步不改）

- **b25-INFO-1**：`HEAVY_PREFIXES` 里的 `/api/v1/report/` 前缀让两条**廉价 GET**
  （`/report/effect`、`/report/effect/docs`）也吃重活令牌——既有口径，非本步引入。
- **b25-INFO-2**：主机路由对 `limit` **原样透传、不做类型校验**（引擎会 422）。
  保留：主机侧只做"白名单 + 缺键守卫"，类型判据的**唯一所有者**在引擎。
- **b25-H6 的数字差**：复核机 **1834 passed / 4 skipped**，本机 **1835 / 3**——
  收集数（1838）与 **0 failed** 一致；差的那条 skip 是 `tests/test_golden_set.py:31`
  （"真实库无 GB 30871"）——**本机有该数据所以它真的跑了**。⇒ 以后门禁一律同时报
  "收集数 + passed + skipped + failed"，并**注明 skip 与机器相关**（本步已在 §10.96 补注）。
- 复核方**未跑** `verify-engine-uvicorn`（它自己说明时间盒 + 与本区间产物无交集）；
  本机该门禁 **4/4** 通过。

### 5. 证据

- 三个变异脚本 `var/tmp/mutate-step98.py`（M1/M2/M3 全部 RED 且**红在预期断言**上，
  三处均**逐字节复原**，脚本自己打印前后 sha256）；
- `pytest`（全量见下）+ `tests/test_research_draft.py` **17 passed**（13 → 17：新增
  "只装配一次" / "装配失败报错误码" / "项目不存在仍放行" / "噪声警告换成准确的那条"）。

⚠ **本步的快照标签与 §10.99 共用 `step-97-b25-and-b26-findings`**（标签号比章节号小 1，见 §10.85 §5）。
⚠ **为什么两步共用一个提交/标签**：§10.98 的全量门禁刚跑完，复核 b26 的报告就到了——而两步改的
**文档文件是同一批**（`DEVELOPMENT-HISTORY.md` / `MATERIALS-PLANE-PLAN.md` / `AUTO-DRAFT-PLAN.md`），
按文件拆两个提交会把同一步的文档劈成两半。⇒ 合成一个提交，但**两节各自记录、复核 b27 一并覆盖**。

### 6. 诚实边界

1. **MEDIUM-1 的修法没有"真触发"到生产代码路径之外**：变更是"加一层类型翻译"，
   证据是变异 + 单测；**没有**制造真实的"库锁死"去做端到端。
2. **`materials_load_failed` 是新错误码**：主机侧（`/ks/report/research/draft`）按 5xx 一律转
   502 `engine_error`（与缺 pptx / LLM 不可用同款）——**界面看到的是 502**，不是那个码；
   要把它变成可操作文案得改主机映射，本步**没做**（登记）。
3. **噪声警告的"真模型形状"是推断的**：我用"结论里带 `[[c:0]]`"复现了取证链那条警告，
   但**没有**用真模型跑过一次（无 Key / 不在本机跑真 LLM 的纪律）。
4. b25 报的 `H2 反事实③`（编号漂移会造成误判）**是复核方构造的**，不是生产可达路径；
   生产不可达靠的是"只装配一次"，现在有用例守着（LOW-3 已修）。


## §10.99 处理复核 b26：**"绝不自动填"那条护栏是假的**（H1 REFUTED）——三层重做 + 两条 MEDIUM

**一句话**：独立复核 b26（冻结在 `verify-freeze-b26` = `435c629`，§10.97 那一步）判
**H1 REFUTED**——我用两条**字符串级**判据守"绝不自动填"，它**构造出了绕过**（把 setter 赋给一个
声明在切片之外的别名，再在起草响应里调用）⇒ 整条冒烟 **19/19 全绿**，而"自动填"**真的发生了**。
它同时报 **H3 PARTLY**（产物陈旧检测缺位：23 条文案断言只读交付件）与两条 MEDIUM/LOW。
本步把这些**能修的修掉、能收窄的收窄**，剩下的残余**如实登记**。

### 1. b26 判了什么（挑最要紧的三条）

| 判定 | 事实 |
|---|---|
| **H1 REFUTED（HIGH，F1）** | 两条判据合起来**可被绕过**：别名声明在切片**之外** + 在起草响应里调用 ⇒ 冒烟全绿、`setConclusionMd` 真被调用。它还把"变异 A/B 能红"与"绕过能绿"**都**跑了出来 ⇒ 证明判据钉的是**写法**而不是**性质** |
| **H3 PARTLY（MEDIUM，F2）** | 三句话**确实**在产物里（CJK 是 `\uXXXX` 转义，须先解码再 grep）；但**反事实方向相反**：改源码**不重建** ⇒ `smoke-client-entry` **89/89 全绿**，重建后才红 ⇒ 那 23 条只查交付件，**产物陈旧检测缺位**（check 名里的"已重新构建"是夸大） |
| **F3（MEDIUM）** | 「用这段填进结论框」是**无确认、无撤销的覆盖写**：不看结论框是否已有用户手写内容 ⇒ 一键**静默丢掉**用户自己写的字且不可恢复 |

另外它确认了 H2（`canApplyDraft` 唯一判据、方向正确）、H4（"没起草"走 `setNotice` 而非 `setError`、
无正文无按钮 ⇒ 不是空草稿）、H5（门禁数字基本复现；pytest 差的那条是环境 skip，见 §10.98 §4）、
H6（产物是真构建：**行尾归一化后逐字节相同**）。

### 2. F1 修法：**三层**（语义 / 类型 / 窄写法），每层都有实测

| 层 | 做什么 | 绕过尝试的结果 |
|---|---|---|
| **① 语义层**（可被真的调用） | 面板的状态转移抽成四个导出纯函数：`draftArrived`（**函数体里就没有**给 `conclusionMd` 赋值的分支）、`requestApplyDraft`、`confirmApplyDraft`、`cancelApplyDraft`、`userTypedConclusion`。冒烟**真的调用**它们断言结果 | 把 `draftArrived` 改成自动填 ⇒ 冒烟 **3/49 红在预期断言**（`after.conclusionMd !== USER` 等 3 条），逐字节复原。⚠ **数字更正**（复核 b27 实测）：本节原写"2/38 红"，基线**写错了**（本节开工时 `smoke-draft-ui` 是 **19/19**，不是 38），红的也是 **3** 条不是 2 条（第 3 条是 `draftReducer`——它也走 `draftArrived`） |
| **② 类型层** | 面板改用 `useReducer(draftReducer, emptyDraftFlow)`，动作集**封闭**（`DraftAction` 五种）⇒ 想直接写一个状态对象**编译不过** | 变异 A（别名 + 对象字面量，b26 原写成法）⇒ **tsc RED**：`error TS2353: Object literal may only specify known properties…` |
| **③ 窄写法判据** | 到达路径（`onDraftConclusion` 切片）**只许**出现 `arrived` 动作；不许出现 `confirmApply`/`requestApply`/`typed`/`conclusionMd` | 变异 B（在到达路径伪造 `confirmApply`）⇒ 冒烟 **RED**；变异 C（别名 + 伪造动作，全在切片内）⇒ 冒烟也 RED（动作名在切片里可见） |

⚠ **残余（如实登记，别当它守住了）**：**变异 D**——把伪造动作藏进一个**声明在切片之外**的辅助函数
（到达路径只出现一个"无辜的名字"）⇒ **tsc 与冒烟两边都绿**。
⚠ **边界更正（复核 b27 的 HIGH-1，本轮改宽）**：b27 又实测出一种**同性质、但位置不同**的绕过——
组件内 `useEffect(..., [flow.draft])`：**挂载即自动填**（用户一个按钮都没点过，名字完全无辜），
同样 **smoke 49/49 + tsc 0 全绿**。所以残余不是"一个藏在别处的辅助函数"，而是：
**任何声明在切片之外、运行期能触达 `dispatch` 的路径**（模块级助手 / `useEffect` / 订阅 / 别名）。
也就是说：**没有人能自动证明"用户真的点过那一下"**。要真防住它需要 **jsdom**（本仓未装 ⇒ 需决策）
或真机 E2E。三层护栏的定位是"**把绕过从'任意写法'收窄到'运行期藏在别处的路径'**"，
不是"证明了界面守规矩"。

### 3. 另外两条修法

- **F3（一键静默覆盖）**：`requestApplyDraft` 在结论框**非空**时**只进入"待确认覆盖"、不写**；
  `confirmApplyDraft` 才是唯一写入路径；`cancelApplyDraft` 一个字都不动。UI 多出
  「确认覆盖 / 取消（保留我写的）」两个按钮（按钮文案也会变成「…（将覆盖现有内容）」）。
  冒烟逐条真调用断言（含"取消后他写的字一个都不丢"）。
- **F2（产物陈旧）**：`smoke-client-entry` 在原有 5 条"关键标记"之外，增加一条
  **整份产物 ↔ 从源码现构建逐字符一致**（行尾归一化）——这才是"改了 `client/` 忘了
  `build:client`"的那条真判据；并把那 23 条文案断言的 check 名改成
  "交付产物 client.js 含…（**新鲜度见本节末尾的"整份一致"**）"，不再暗示它们管新鲜度。
  ⚠ 顺带抓出**两个坑**（都实测）：
  ① esbuild 会把**相对 `absWorkingDir`** 的模块路径写进产物注释（`// client/entry.ts` vs
  `// plugin/client/entry.ts`）⇒ 同一份源码在不同 **cwd** 下产出**不同字节**的产物，
  害得"整份一致"**假红**；修法是 `build-client.mjs` 显式 `absWorkingDir: root`（产物与调用方 cwd 无关）；
  ② 在 Node 脚本里用 `execFileSync('npx', …)` **必须 `shell: true`**（Windows 下 `npx` 是 `npx.cmd`）：
  不加时直接 ENOENT、**stdout/stderr 全空**，于是"三种绕过看起来 tsc 全红"——那是**环境假红**，
  不是类型错误（本轮实测踩过）。
- **F4/F5（LOW）**：判据②（数 `setConclusionMd(` 次数）**整体换掉**（见上面的第②③层）；
  到达路径的切片**结束锚点**从"字面 deps 数组"改成"下一个 handler 的开头"
  （给该回调加依赖不再让它断——而"加依赖"正是修 F1 的第一步）。
- **F6/F7（INFO）**：草稿填入后失去标记（报告侧只收 `conclusionMd`，无 provenance）；
  "唯一判据"实为两层（渲染层 + 启用层），渲染层无自动化断言 ⇒ 均**登记**。

### 4. ⚠ 我自己在本步中间犯的一个错（记下来）

我用一个变异脚本做"复原"时写了 `git checkout -- plugin/client/KsMaterialsPanel.tsx` ——
那条命令把**尚未提交的正当改动**（本步的面板状态机）**一起丢掉**了（工作区从 HEAD 恢复），
于是不得不**重做**那 7 处改动（`var/tmp/redo-panel-step99.mjs`）。
⇒ 纪律：**变异脚本复原一律用"读进内存 → 写回"**；`git checkout -- <file>` 只许用在
"该文件的改动已经提交、或本来就是构建产物"的场合。已写进本轮记录。

### 5. 证据

- 绕过尝试脚本 `var/tmp/bypass-check-step99.mjs`（A/B/C/D 四条，逐条打印 tsc 与冒烟结果，
  末尾断言**逐字节复原**）；M1 的独立验证 `var/tmp/mutate-m1-check.mjs`（**3/49** 红在预期断言
  ——本节原写 "2/38"，复核 b27 的 MEDIUM-2 实测更正）；
- `smoke-draft-ui` **49/49**（**19 → 49**：新增 reducer/动作/到达路径窄判据；本节原写 "38 → 49"，
  38 这个基线**不存在过** —— b27 实测 b26 时它是 19/19，台账 `MATERIALS-PLANE-PLAN` 里写的 19/19 是对的）；
  `smoke-client-entry` **90/90**（+1：整份一致）；
- `pytest` **1839 passed / 3 skipped / 0 failed**（收集 **1842** = §10.98 的 1838 + 本步新增 4 条
  草稿用例）；`mypy` **135 / 0**；`tsc` **0**；`smoke` **EXIT=0**（20 段，12 段打印 PASS）；
  `verify:commands` **22/22**；`verify-engine-uvicorn` **4/4**。

⚠ **本步的快照标签与 §10.98 共用 `step-97-b25-and-b26-findings`**（标签号比章节号小 1，见 §10.85 §5；
共用一个提交的理由见 §10.98 末尾那段）。

### 6. 诚实边界

1. **三层护栏挡不住"藏在别处的伪造动作"**（变异 D 实测两边全绿）⇒ "绝不自动填"在**离线门禁**上
   只能做到"绕过很难看"，**不能做到"证明没有"**。真防需要 jsdom（新依赖 ⇒ 决策）或真机 E2E。
2. `useReducer` 那层靠 **tsc**：`tsc` 是本仓门禁的一部分，但**只在** `npx tsc -p plugin/client/tsconfig.json`
   这条路径上跑（它用的是 **DSH 检出**里的 typescript）⇒ 若那条门禁被跳过，第②层就不存在。
3. b26 的两条方法论提醒（提取树是 **CRLF**；PowerShell 的 `cd` **不移动 .NET 的 CurrentDirectory**）
   仍**只记在本节**，没有写进复核模板（上一轮同样的欠账，见 §10.93 §7.7）。
4. 本步**没有**真机、没有浏览器、没有 jsdom ⇒ F1 的残余、F6/F7 都只能在真机上由人眼确认。


## §10.95 自动成文（系统起草结论）**立项论证**——只出文档，不动代码

**一句话**：方案 Phase D 末尾一直挂着"**自动成文**（由系统得出结论）未立项（触及答案链，P1）"。
本步按 §10.38（PPT 那次的流程：先论证值不值、单独立项）把它论证清楚，产出
**`docs/AUTO-DRAFT-PLAN.md`**，**不写任何生产代码**，把三个决策点留给业主。

### 1. 论证的结论

**推荐做，但只做"草稿"形态**：系统基于**已批准材料**起草一段结论，带 `unapproved_draft` 标记与
**逐条引用校验**回给用户，**由用户显式确认**才进结论框；**绝不**自动落盘成报告、
**不动**答案链（`ks_answer`）的提示词与口径。**不建议**"全自动成文"。

### 2. 论证里最值得记的两件事

1. **除了"写"这一步，其余每一步都已经有唯一所有者了**——检索已批准材料（
   `assemble_evidence`）、只取可承重组（`usable_hits`，它的 docstring 原文就是
   *"给'要产出结论'的调用方用的安全入口"*）、渲染带 `[[m:i]]` 与出处的证据文本
   （`render_evidence`）、**结论引用的唯一判据**（`research_report._check_citations`）。
   ⇒ 本立项要补的只是"写"，而且**只能复用**这些所有者。这也让设计变得很短。
2. **"复用法条链当草稿"（形态 A）看起来最省事，其实是错的**：答案链引的是**法条**（`[[c:i]]`），
   而报告的校验器只能核**材料**（`[[m:i]]`）⇒ 那样拼出来的结论里**每条引用都是"本次无法核验"**，
   报告会如实写"未核验"，用户却容易读成"系统已经核过了"。⇒ 推荐**形态 B（材料链起草）**。

### 3. 三个决策点（留给业主）

1. 做不做；2. 默认是否把法条链一并带上（我推荐**不**，需要时由用户在面板上显式选）；
3. 草稿能否写进报告（我推荐**允许但逐次显式确认**，不做"以后都自动填"的开关）。

### 4. 证据与诚实边界

- **本步没有运行时改动**：`git diff` 只有 `docs/AUTO-DRAFT-PLAN.md` + 两处文档登记
  （方案 Phase D 与账本），**没有**碰 `src/`、`tests/`、`plugin/`。
- 文档里的每条"现状"都是**读代码**得到的（owner 名字、docstring 原文、评审硬门位置），
  不是推断；但**提示词的实际输出质量没有任何证据**——那要有评测集，本立项明确写了
  "验收全是结构性判据，不谈质量"。
- ⚠ 一句必须说清的：引用校验只能证明"**引用的材料真实且可承重**"，
  **不能**证明"**这句话确实由那条材料支持**"。语义级核验（逐句蕴含）**不**在本立项里。
- 本步**没有**真机、没有 LLM 调用、没有新依赖。



## §10.100 用户四条真机报障 + 复核 b27 收口（真机 CDP 首次成为**眼睛**）

业主原话（2026-09-18 08:4x，重启后的真机）：

> 装 jsdom（或走真机 E2E）这都啥意思啊 / 目录悬浮窗关不掉了，进入这个对话会自动打开，
> 就算没有开 sidebar / 之前你让我看 PPT 和 word 观感，但是设置里的导入只接受 PDF，还有 html 呢 /
> 法律法规的目录被搞坏了 · 目录的最后一级显示个计数 · 点开目录只感觉里面密密麻麻的字，
> 二级目录三级目录和文件名长得都一样

### 1. 先拿到"眼睛"：真机 CDP（这一步是本轮所有结论的前提）

之前所有 UI 判断都是**读代码**得出的。本轮发现**远程调试端口已经是开的**
（`127.0.0.1:9333`，Edge/HeadlessChrome，target=`http://127.0.0.1:3080/`），
于是写了 `var/tmp/cdp.mjs`（`eval` / `evalfile` / `shot` / `reload`，支持 `--gesture`
= CDP `Runtime.evaluate{userGesture:true}`），用它**截图 + 探 DOM**。

⚠ 踩到的坑（两条都写进脚本注释了）：
- `Invoke-WebRequest` 打 GUI 是 **401**（`?token=` 换 cookie 的机制，token 只在
  `dsh web` 启动时打印、进程内存里）；**CDP 走的是你已登录的那个浏览器**，所以不用 token。
- PowerShell 里 `browser4-cli ... | Select-Object -First 12` 会**提前掐断**上游进程
  （JVM 起一半）——长跑命令必须重定向到文件再读尾部。

### 2. 四条报障逐条定位与修复

**① 目录浮层"自动打开 + 关不掉 + 没开 sidebar 还浮着" —— 真机复现，两半原因都在浮层自己身上**

复现链（截图 `var/tmp/gui-04.png` → `gui-05.png`）：开右侧栏 → 点开始页「PDF 查看器」胶囊
→ **浮层自己出现**（没点过 📑）→ 收右侧栏 → **浮层仍浮在对话上**，而它**没有关闭按钮**。
根因两条：

1. `showLeftCol` 旧判据是 `leftMode !== 'toc' || (tocOpen && docHasToc)`，而"无证据直开 tab"
   会把 `leftMode` 默认成 `files` ⇒ **tab 一挂上浮层就出现**（"进入这个对话会自动打开"）。
2. 浮层是 `document.body` 的 portal（必须脱离侧栏 overflow 裁剪）⇒ 侧栏收起时它
   **不跟着消失**；而它的 ◀ 收起按钮当年在 `load.status === 'idle'` 时**刻意不渲染**
   （理由："目录列是唯一入口"）⇒ 唯一关闭入口恰好在"没打开文档"时消失 = **关不掉**。
   真机还测出官方收起右侧栏的做法是 `visibility:hidden` + **把整列停到视口右缘之外**
   （容器仍是 708×869、`left = 1575 > innerWidth = 1574`）⇒ "宽度>0 即在屏上"的判据会漏掉，
   而且那次收起**没有等到重新测量**（锚点 `right` 停在收起前的 708px）⇒ 几何判据会过期。

修法（都在**唯一所有者** `KsEvidenceTab` 里）：
- `showLeftCol = tocOpen && visible && paneOnScreen`：**只有用户显式打开才显示**；
  再叠官方 `visible`（主判据，契约字段，变了就重渲染）与几何 `paneOnScreen`（第二层，
  防"停在屏外"，由既有测量链 `syncTocAnchor` 同一处刷新）。
- 展开/收起各收成**唯一出口** `openLeftCol()` / `closeLeftCol()`（展开时"当前模式没东西可点
  就落文件目录"的判断只留一份；`loadEvidence` 里那段自动设模式的代码**删除**）。
- ◀ 收起按钮**无条件渲染**；空屏改由面板区一个显式的「📑 打开文件目录」按钮接手
  （这才是"idle 时不许收起"那个旧理由的正当替代）。
- 真机复验：`gui-07`（不再自开 + 空态按钮）→ `gui-08`（显式点开后 ◀ 在场）→
  `gui-09`（**收右侧栏后浮层消失**）。

**② 文件目录"密密麻麻、二级三级和文件名长得一样、没有计数" —— 客户端就能修，不动引擎**

`KsFilesTab` 改：新增 `countDocs()`（递归计数，**导出以便离线测**）并**逐级显示计数**
（L1/L2/L3 同名右侧徽章 + L4 胶囊旁的计数）；四级视觉各自区分（L1 色条+底色 12.5/700、
L2 12/600、L3 11.5/400+左侧树线、L4 蓝色胶囊、文档叶 = mono 标准号徽章 + 常规字重名称 +
meta 换行）；L4 名字 `nowrap+ellipsis`（190px 列宽里换行会把一颗胶囊劈成两行）。
真机复验：`gui-10`（每级计数）→ `gui-11`（L3）→ `gui-12`（L4 胶囊 + 叶节点）。
⚠ **"计数的数据源"是既有 `fetchCategories`**（一次下发整棵树）⇒ 不加端点、不改引擎。

**③ "设置里的导入只接受 PDF，还有 html 呢" —— 真实缺口是"产物拿不到手"，不是"导入"**

先分诊：`入库预览`（`plugin/src/ingest.js`）只收 `.pdf` **是刻意的**——那是**法规入库**闸门
（要页码/锚点定位原文）；而报告/PPT/Word 是**交付物**，本来就不该走入库。用户缺的是
**能打开看**。修法（纯客户端 + 复用引擎既有端点）：
- `api.ts` 新增 `fetchExportBlob(name)`：走引擎**早就有的** `GET /api/v1/export/download?name=…`
  ——"名字必须落在 exports 目录内"这条防穿越纪律**由引擎一家所有**（`base not in target.parents`），
  客户端直连引擎（同 `fetchPdf` 的跨源 + Bearer 通路）⇒ **不新增宿主路由、不要重启**。
- 面板新增 `Deliverables` 按钮组：`.html/.md` → 「👁 打开」（新标签渲染）；`.docx/.pptx` →
  「⬇ 下载」（浏览器渲染不了 Word/PPT），并把**保存目录**显示出来 + 「📋 复制目录」。
- ⚠ **真机抓到本人写的一个真 bug**：原先 `await fetchExportBlob()` 之后才 `window.open(blobUrl)`
  ⇒ 实测**新标签根本不出现**（`window.open` 返回 null = 被弹窗拦截；引擎冷启动实测可达 8s，
  瞬时激活早过期）。改成**在用户手势的同步段先 `window.open('about:blank')` 占位**，
  拿到字节后 `location.replace(blobUrl)`；被拦时**退化成下载并显示原因**（绝不静默无反应）。
- 真机证据：`gui-16`（报告生成后三形态按钮 + 保存目录）→ 点 `.html` ⇒ 新标签
  （target 列表出现 `blob:` URL）→ `var/tmp/report-html.png` 与正文文本
  （"四、已批准参考资料清单 / 五、尚未批准的材料 / 六、已知限制"），
  且引擎端点**在页面上下文实测**：`200 / text/html / 1622B`，越权名 `../secrets.json` ⇒ **403**。

**④ "法律法规的目录被搞坏了" —— 只读探针给出的事实，本轮**不下结论式修复****

只读库探针（`var/tmp/probe-law-tree*.py`，`mode=ro` + 复用 `classify_document`）：
`doc_meta` 共 6415 行，其中**非标准号（法规树）只有 7 行**，且这 7 行**全部**
`doc_type='standard'` / `legal_hierarchy='GB'` / `effective_from` 为空 ⇒ `_law_tier` 落到
"未定级"、`_law_domain_doc` 落"未细分" ⇒ 法规树读起来就是
`法律法规 → 未定级 → <部门> → 未细分 → 7 条文` 这种"三层占位桶"。
另有 `law_catalog` 表 **29764 行**（法规库），但**客户端没有任何 UI 读它**（grep 无引用）。
⚠ 本步**没有**去改分类规则：把《北京市消防条例》这类名字按后缀猜成"行政法规"是**法律错误**
（地方性法规），而 `P1 准确性` 高于"看着整齐"；`doc_type='standard'`/`legal_hierarchy='GB'`
是**数据**问题（写入侧），不是展示层能修的。⇒ 本轮只把**展示**修好（计数 + 层级），
把分类与"法规库没有入口"两件事**登记为待业主裁定**（见 §6 待裁定）。

### 3. 复核 b27 的六条新发现（本轮一并收口）

| # | 级别 | 处置 |
|---|---|---|
| 1 | HIGH | **残余边界写宽**：三层护栏只覆盖"纯函数 + 切片内写法"，实测 `useEffect(..., [flow.draft])` 挂载即自动填也是 **smoke 49/49 + tsc 0 全绿**。已把残余登记改写成"**任何声明在切片之外、运行期能触达 dispatch 的路径**（模块级助手 / useEffect / 订阅 / 别名）"，并写明**只有 jsdom 或真机 E2E 能挡** |
| 2 | MEDIUM | **§10.99 的数字错**：`draft-ui` 实测 **19 → 49**（不是"38 → 49"），自动填变异 **3/49 红**（不是"2/38"）。已在 §10.99 两处逐字更正（台账里的 19/19 本来是对的） |
| 3 | MEDIUM | **"整份一致"在 junction/symlink `node_modules` 下假红**：`absWorkingDir: root` 只保证"同树内与 cwd 无关"；junction 树里交付件写的是 `// node_modules/pdfjs-dist/…`、现构建写的是长相对路径。已在 `smoke-client-entry.mjs` 的失败详情里**提示先分辨**"是不是 junction 树"，并在本节记录（**不**加豁免开关——那会放走真漂移） |
| 4 | LOW | **报告侧新入口没有门禁**：改回直调仍 17 passed 全绿。已补 `TestEvidenceAssemblyGate`（3 条），并**做了变异检查**：改回直调 ⇒ 该 3 条中 2 条 RED、文件 sha256 逐字节复原 |
| 5 | LOW | **"法条正则唯一所有者"说得过满**：报告/草稿确实收敛到 `clause_refs()`，但答案链另有独立的 `_CITE_MARK`（严格性不同）。已在 `clause_refs` 的 docstring 里限定为"**产出侧**两条路径的所有者" |
| 6 | INFO | 语义层只保证**纯函数**行为；"面板用的就是它"只有字符串判据 ⇒ 已写进 `smoke-catalog-ui.mjs` 文件头（"能证明什么/不能证明什么"） |

### 4. 本轮新增/改动的门禁

- `plugin/scripts/smoke-catalog-ui.mjs`（新，**26/26**）：`countDocs` 的**行为级**用例（叶子/空/
  递归/占位桶）+ `deliverableKind`/`folderOf` 行为级 + 浮层"三重约束/唯一出口/收起按钮无条件"
  的**写法级**判据 + "新标签必须在 await 之前占位"的结构判据。已接进 `npm run smoke`
  （链由 20 段变 **21 段**，打印 `== … PASS ==` 的 13 段）。
- `plugin/scripts/smoke-report-ui.mjs`：+6 条（**28/28**）——`fetchExportBlob` 的路径逐字、
  名字 URL-encode、Bearer、403/404 如实抛、401 重取会话再试。
- `tests/test_research_report.py`：+3 条（**34 passed**）——报告侧装配失败翻码 / `ValueError` 放行 /
  落盘路径只装配一次；**变异已证承重**（改回直调 ⇒ 3 条中 2 条 RED、sha256 逐字节复原）。
- 本轮全门禁：`pytest` **1842 passed / 3 skipped / 0 failed**（收集 **1845** = §10.99 的 1842 + 本节 3）、
  `mypy` **135/0**、`tsc` **0**、`smoke` **EXIT=0**、`verify:commands` **22/22**、
  `verify-engine-uvicorn` **4/4**。
  ⚠ 已知 flake（**预先存在，非本轮引入**）：`smoke-chatmode` 在串行链里偶发 1 条红
  （本轮 2 次链跑 = 1 红 1 绿，单独跑 173/173 绿）。红的那条详情里带 `persisted=false`
  ⇒ 是**写盘没成功**（锁竞争）而不是"复活逻辑错"——这个诊断字段正是本仓早前一轮为它加的。

### 5. 诚实边界（本轮**没**做到的）

1. **真机验证是本轮的主要证据，但它不是自动门禁**：`var/tmp/cdp.mjs` 是排错用的"眼睛"，
   没进 `npm run smoke`（要一台开着远程调试的浏览器）。仓库里既有的
   `plugin/scripts/e2e-sidebar-pdf.mjs` / `e2e-materials-panel.mjs` 才是那个位置，
   但它们的探针还是 **better-sidebar 时代**的写法（`COL` 选择器拿 `document.body.children`
   里的第一个含"📚 文件目录"的元素——实测会命中 `#root`；本轮临时脚本用
   `[style*=fixed] + /共 \d+ 部/` 才是准的）⇒ **待修**。
2. **Word/PPT 只能"下载一份"**：浏览器渲染不了。"用系统默认程序一键打开"要新增宿主路由
   （`explorer /select`）⇒ **要重启宿主**，本轮没做（面板文案已如实写明）。
3. **没装 jsdom**：本轮结论是**不装**——四条报障里三条是"浮层/裁剪/观感"，而 jsdom
   **没有真排版**，恰好测不到；真机 E2E 的工具**仓库里已经有**，缺的只是"用带远程调试的
   浏览器打开 GUI"这一步（本轮实测**已经是开的**）。
4. **测试用数据**：本轮为了验交付物按钮，建了一个参考资料项目
   `自测-交付物按钮（可删）`（`prj_01M2S04BJN7E5R4SKY6917A22Q`）+ 一份**未评审**材料
   `自测材料.md`（**没有**批准它——批准是业主的硬门），并在 exports 目录留下两份自测报告。
   面板没有"删除项目"入口 ⇒ **请业主决定**：留着（改个材料再用）或告诉我删。
5. **没动引擎/宿主**：本轮所有改动都是 `plugin/client/**` + `plugin/scripts/**` + `tests/**` +
   文档 ⇒ 客户端 `build:client` 后**刷新页面即生效**（真机已验）；
   ⚠ 宿主（pid 17160 @07:52）与引擎（pid 29908 @07:52）**早于** §10.96/§10.97 的提交
   ⇒ 面板上的「起草结论（草稿）」那条链路**当前不在线**，要重启两个门才可用。

### 6. 待业主裁定（本轮**刻意没做**的）

1. **法规树的分类**（报障④的"被搞坏了"）：法规树 7 行全部落 `未定级/未细分`，因为它们的
   `doc_type='standard'` 且 `legal_hierarchy='GB'`（写入侧给的默认值，不是法规位阶）。
   要不要按"名称后缀"补一层位阶推断（法→法律、条例→行政法规/地方性法规、部令→部门规章）？
   **我倾向不做或只做最保守的一档**：按名字猜位阶会出法律错误（如《北京市消防条例》是
   **地方性法规**，不是行政法规），而准确性优先。请你裁定。
2. **`law_catalog`（29764 行法规库）没有入口**：客户端 grep 不到任何读 `/api/v1/laws/catalog`
   的代码 ⇒ 查法规模式用的是**检索**，不是**浏览**。要不要在文件目录里加一个"法规库"分支？
   （那是新产品面，不是修 bug。）
3. **测试数据**：`自测-交付物按钮（可删）`（`prj_01M2S04BJN7E5R4SKY6917A22Q`）+ 一份未评审材料
   `自测材料.md`，exports 里两份自测报告。面板没有"删项目"入口 ⇒ 留着复用，还是我删？
4. **Word/PPT 的"一键打开"**：现在只能"下载一份 / 复制目录自己去开"。要"用系统默认程序打开"
   得加宿主路由（`explorer /select`）⇒ **要重启宿主**。做不做？
5. **jsdom**：本轮结论是**不装**（见 §5-3）。如果你更想要"离线也能测界面行为"，
   那就装 jsdom 当 devDependency——但请知悉它**测不到排版/裁剪/浮层**这类本轮的主要问题。
6. **真机 E2E 脚本要修**：`plugin/scripts/e2e-sidebar-pdf.mjs` 的探针还是 better-sidebar 时代的
   （`COL` 会命中 `#root`）。要不要我把它按本轮验证过的选择器（`[style*=fixed]` + `/共 \d+ 部/`
   + `[data-sidebar-right-guide-entry=...]`）重写一遍，让它能当"每次改 UI 都跑一遍"的正式门禁？

## §10.101 渠道探针：未探 103 → 29，并把「⚪ 未探」拆成两种处境（§11.0 R6a/R6b）——附我自己的两次锚点翻车

分工：**进度真源**在 `docs/CHANNEL-COVERAGE-PLAN.md`（§6 的 R6a/R6b 两条），本节只记结论、
门禁与**诚实边界**。

### 1. 做了什么

1. **判据扩容**（`src/core/update/channel_probe.py`）：期望值从"单一文本锚点"变成**可叠加**的
   `expect` + **新增 `min_links`**（HTML 链接数下限），任一不满足即不算通过；
   **429 从 `down` 改判 `suspicious/rate_limited`**（限流≠死了）。
   来源是实测：应急部频道页 HTTP 200 / **471 字节 / 0 链接**，标题却是好的；批量实测又发现
   **12 条**同形态（人社部 / 工信部 / 浙江人大 / 浙江政府 / 国家标准委 / 电子工业标准协会…）。
   ⚠ 其中 **11 条今天仍判 🟡**；第 12 条 `ch:mee` 是 JSP 报表页、本来就没有 `<a>`，
   改用手工实测的文本锚点后是 🟢（**判据要贴对象，不能一刀切**）。
2. **覆盖率**：103 条未探里 96 条有具体 URL，给 **70 条**配上**实测**目标（每条带 evidence：
   时间/出口/字节/链接数/title 原文），目标表 **28 → 102 条**（台账口径变化见下面 2.5）。
3. **我方通路**（internal）补 4 条手工目标（`ndls`/`ttbz`/`ccs_fetcher`/`mee`）：method 与 body
   **抄适配器里实测跑通的那一版**——第一次探 `ndls` 我用 GET 得到 404，正是 R3 记过的
   "method 不传就静默变 GET"。
4. **可见性**：`GET /api/v1/channels` 每条加 `has_probe_target`（按探针表算，不往库里塞第二份真相）；
   面板对"按设计无探针"的灰行标**（无探针）**；状态报告第四节拆成「已配未探」与「按设计无探针」。
5. **还掉 R5c 的欠账**：删 `inspector.CHAIN`（与 `routing._FALLBACK` 重复的字面量），
   `inspector._FALLBACK_CHAIN` 改为向新增的 `routing.fallback_chain()` 取**同一个 tuple 对象**；
   新用例用 `is` 钉住——以后谁再抄一份都会红。

### 2. 门禁（只涨不跌）

pytest **1935 passed / 3 skipped / 0 failed**（1922 → +13：探针 11 + API 1 + 降级链 1）、
mypy **138/0**、tsc **0**、smoke **EXIT=0**（22 段；`catalog-ui` 43 → **46**）。

### 2.5 覆盖率数字与它的"时点"（容易被误读，单独写清）

真机落库：**ok 22 / suspicious 1 / down 5 / unknown 103** → **ok 77 / suspicious 11 / down 14 / unknown 29**；
随后我把当时 `down` 的 14 条**用同样的目标复探第二轮**（查"红是不是抖出来的"）：
**13 条两轮错误码逐条一致**（404/403/412/SSL/ConnectionError/202），只有 1 条翻转
（`cfsa` 证书校验时好时坏 ⇒ 瞬时）⇒ 最终 **ok 78 / suspicious 11 / down 13 / unknown 29**。
这也是台账 `consecutive_failures` 第一次拿到真实数据（那 13 条 = 2）。
⚠ 台账是**活的**：任何"数字"都必须带时点读（本节数字 = 2026-09-18 18:2x）。

### 3. 我自己的两次翻车（都留档，因为它们是同一类错）

- **第一次**：批量脚本把 `<title>` 做了**实体解码 + 空白折叠**再当锚点 ⇒
  `全部文件&nbsp;&nbsp;广东省人民政府门户网站` 被写成 `全部文件 广东省人民政府门户网站`，
  正文里根本没有这个串 ⇒ **3 条广东渠道被误判 `probe_no_anchor`**。
- **第二次**（同一天、换了形式）：`ch:mee` 的锚点我**从 URL 抄**了 `xmlname=1520238134405`，
  同样不在正文里 ⇒ 判 `suspicious`。
- **同一条纪律**：**锚点只能来自正文，且必须是逐字子串**。已做成可执行的工具
  `scripts/channel-anchor-measure.py`（取候选后先自检"在正文里逐字存在"，再输出可粘贴的目标；
  `--repair [错误码]` 可批量重走被标该错误的渠道）。

### 4. 诚实边界

1. **面板上的「（无探针）」现在看不到，且原因在"宿主"而不是"引擎"**（本条的措辞在收尾时按实测改正过）：
   面板要经**宿主路由** `/ks/channels*` 才能拿到数据，而宿主插件代码 `plugin/src/channels.js`
   是今天才加的——宿主进程启动时还没有它 ⇒ 面板现在拿到的是**宿主**的 404，引擎**根本没被问到**。
   所以要的是**重启宿主**（客户端的 `build:client` 那半已重建，刷新页面即生效，不依赖重启）。
   引擎是**按需懒启动**的：实测此刻**没有活着的引擎**（session 文件指向 pid 30836 @18:17:07，
   进程已不在；端口 2036 无监听）⇒ 宿主重启后它 spawn 出来的会是**当前代码**的引擎，字段自然就有。
   ⚠ 唯一会翻车的情形：重启时若恰好有一个**旧引擎**活着，宿主会**复用**它（会话里的 `reused`）——
   那时才会出现"宿主重启了但字段还是没有"，需要再重启引擎。
   （字段缺失时面板不显示标记：不报错、不误导。）
2. **29 条 ⚪ 是"按设计无探针"，不是"漏了"**：24 条 tool（代码仓库/工具，实测里两条就是
   GitHub **429 限流**——把限流显示成"渠道不可用"是误导）＋ 5 条 internal
   （两条与已有渠道同一端点、一条是用户自配列表、一条已摘除、一条入口地址实测 404 待重找）。
   它们的"有效性"该用**另一类判据**（链接可达性），本轮**没做**。
3. **`ch:mem_gov` 形态变了**：R5a 时是 471 字节 0 链接的 JS 壳，R6 复测 29285 字节 / 113 链接，
   且栏目页标题改成「制度文件--中华人民共和国应急管理部」⇒ 锚点按当时正文重取（`suspicious → ok`）。
   这是**站点变了**，不是我们修好了什么。
4. **4 条 TLS/连接失败 + 1 条时好时坏的证书问题**（`cfsa`：18:08 量到 200 / 56778 字节，
   18:2x 探针又报 `transport_error`）⇒ 台账的 `consecutive_failures` 会如实累加；
   "不可抓"里有我方客户端指纹的因素（与 R3d 的上海人大同款），不是站点全责。
5. **没动**：`src/core/update/channels/**` 的适配器逻辑一行没改（本轮只动探针/台账/面板/路由常量）；
   引擎与宿主**没重启**（按纪律不擅自动业主的进程），所以引擎侧新东西要重启后才在线。
6. **测试数据**：本轮**没有**新建参考资料项目或材料，也没改任何既有项目/材料。

### 5. 待业主裁定（也可以直接告诉我"按你的推荐做"）

1. **tool 类 24 条的"链接可达性"判据**要不要做？（做了它们才从 ⚪ 变成有意义的状态；
   代价是探针语义要再分一类，且 GitHub 会限流。）
2. **`ch:discover_search` 的入口**要不要花一轮重找？（它是"按分类路径发现新标准"的通路；
   记录里的地址实测 404。今天它的实际影响有限——巡检链上并没有它。）
3. **G28 出网模式**（direct / env-proxy）要不要**落进台账**（现在只写在 evidence 文字里）？
   这件事的价值是让"有效性"三个字在换环境后仍然可解释。

### 6. 真机复验抓到我自己的一处新瑕疵（已修 + 已加闸门）

刷新真机页面（CDP）看到面板底部说明里 `**（无探针）**` **带着星号原样显示**——JSX 不渲染
markdown，这与 R4b 修过的 7 处是同一类问题，而这次是我在 R6b **新写**的。
处置：改为「（无探针）」；`smoke-catalog-ui.mjs` 新增闸门「可见文案里没有 markdown 粗体」
（去掉块注释/整行注释后扫 `**`），并做**变异验证**：拿 `git show e7fb13d:…KsChannelsPanel.tsx`
跑同一段判据 ⇒ 命中 1 行（旧版会红），修复后 0 行。catalog-ui 45 → **46**，
提交 `5a214fc`（快照 `step-113-r6b-caption-gate`）。

⚠ 顺带把"真机复验"这条纪律再说一遍：**离线闸门全绿也挡不住排版/文案类问题**——
本轮唯一被真机抓到的问题，恰好是 46 条离线用例里没有的那一类（这与 §10.100 的结论一致）。

### 7. 独立复核 b28 的发现与处置（6 条声明 5 成立、1 条"措辞比证据强"）

**两条真问题**（都在"我声明得比证据强"这一类，报告 `var/tmp/VERIFY-b28.md`）：

1. **`expect=""` 是假绿口子**：`_classify(200, "", "")` ⇒ `('ok', None)`（`"" in body` **恒真**，
   空正文也判"可抓"）。不是本次新引入（R6 前同款），但我说"没有假绿口子"经不起宽读。
2. **目标形状不受校验**：把 target 写成**字符串**能静默过表，随后 `probe_channel` 抛
   `AttributeError`；`expect=123` 抛 `TypeError` ⇒ "探针不抛异常"当时只对**恰好写对**的目标成立。

**处置**：`load_targets` 改为**逐字段校验**（`_validate_target`：对象 / `url` 必须 http /
`method` ∈ {get,post} / `expect` 非空字符串或**省略** / `min_links` ≥1 整数 / `form`·`json`·`headers`
必须是对象），空 `expect` **读表即拒**；`probe_channel` 的 docstring 改成明说**契约前提**
（未经校验的裸 dict 不保证不抛）。用例 34 → **44**（新增 10：9 种坏形状 + 1 条把"为什么必须拒"
钉成证据——`_classify(200, "", "")` 确实返回 `ok`）。pytest **1945 passed / 3 skipped / 0 failed**、
mypy **138/0**。

**另外三处"这次改动让别处变旧"**（复核抓的，都已修）：
- `docs/research/channels/internal-inventory.md:19` 因删 `inspector.CHAIN` 变成错的 ⇒ 加
  2026-09-18 更新块（原文保留：它是 R1 当时的记录），顺带注明同段 `web` 已被 R5c 摘除；
- `routes_channels.py` docstring 还写"只探配了目标的渠道（**28 条**）" ⇒ 改为"数量随目标表变
  （R3 时 28 条，R6 后 102 条）"；
- 事故文档：`pending-incident.json` 处理完已被重命名为 `resolved-incident-<ts>.json`（复核实测）
  ⇒ 文档注明；"stderr 被覆盖"措辞改为"**被复用而丢弃**"（机制可证、"当时确实写过内容"不可观测）。

**一条它判 `UNVERIFIABLE` 的**：我说的"复探两轮 13/14 逐条同码"没法从库复核——`record_probe`
是**覆盖写**，首轮错误码已不在库里 ⇒ 已在 ledger 写明这个对照只能在那两个 `var/tmp` 输出文件里核。

⚠ 结论（写给下一轮）：**"判据实现正确"与"判据的输入被校验"是两件事**——本轮前一半做对了，
后一半靠复核才发现。以后凡"我把某个契约写进 docstring"（如"探针不抛异常"），
都要同时回答**"这个契约对什么输入成立"**。

⚠ **流程缺陷自记（与上面同一提交）**：全量首跑出现 **1 failed**，同一提交重跑 **1945 passed**
⇒ 是**既有 flake**；但我**没抓到是哪一条**——因为我把 pytest 输出用 `Select-Object -Last 2`
截掉了。已改成整份落盘（`var/tmp/pytest-full-captured.txt`），下次复现就能点名。
**"知道有 flake 却叫不出名字"本身就是欠账，记在这里而不是含糊过去。**

## §10.102 复核 b28 的第二轮：从"会抛异常"换到"不抛但会误分类"——又抓到四条（§11.0 R6b）

第二轮复核（报告 `var/tmp/VERIFY-b28-fix.md`）把攻击面换了：不再问"能不能让它抛异常"，
而是问"**能不能让配置错误伪装成渠道故障**"。于是又抓到四条（第一条那轮修的是会抛的那类）：

| 发现 | 后果 | 处置（提交 `4512e97`） |
|---|---|---|
| `url` 用 `startswith("http")` | `"http"`/`"httpfoo"` 过表 ⇒ `down/transport_error`；合法大写 `HTTP://` 反被拒 | 改 `urlsplit` 判 scheme+netloc（大小写不敏感） |
| `headers` 只校验"是对象" | 值给 list/dict ⇒ 同样记成 `down` | 必须 `str→str`、名不含 `:`/换行、值不含换行（顺手堵头注入） |
| `json` 只允许 dict | 顶层数组的 POST 体被误拒 | 允许 dict 或 list |
| `json.dumps` 在 `try` 之外 | 怪响应体会**从 probe_channel 逃出去** | 移进 `try` ⇒ `down/bad_body`；"不抛"契约补第二条前提 |
| 两处消费端仍按旧读法 | "有目标但只探连通性"会被写成"还没实测/欠账" | 状态报告改**三分**；面板表尾补第三种 ⚪ |
| docstring 与代码不符（`no_probe_target`） | 读文档的人会以为没配目标也写库 | 改成与代码一致：跳过、不写库、只在 `without_target` |
| 复核建议：**校验未知键**比"拒 null"更值 | `expext` 拼错过去是静默忽略 | 采纳：`_TARGET_KEYS` 白名单，未知键读表即拒；`expect:null` 保持合法（不是假绿） |

**闸门第二次抓到同一个我**：新写的面板文案里又出现 markdown 粗体，R6b 加的那条闸门**当场红**
（46 项 1 红并报出行号），去掉后 46/46。**一条闸门连续两次有效**，这就是它值钱的地方。

**门禁**：pytest **1959 passed / 3 skipped / 0 failed**（1945 → +14）、mypy **138/0**、tsc **0**、
smoke 链 **EXIT=0**（14 段全 PASS，chatmode 173/173）。

### 关于那两条"flake"：本轮终于有更准的说法

- `smoke-chatmode` 失败**两次**，都发生在**与全量 pytest 并发**时（172/173）；
  单独跑 **4 次全绿**（含整条 smoke 链 EXIT=0）。
- 先前那次 pytest `1 failed` 也出现在与**复核员的另一次全量**并发时。
⇒ 收紧为：**与"同时跑多份重活"相关**（机制推测是文件锁/时序敏感；样本 2 失败 vs 4 成功，
**因果未证实**）。**操作纪律：门禁一次只跑一个。** 并发跑门禁是在给自己制造假红——
这条以前只当"偶发"，现在有了"什么时候会偶发"的说法。

## §10.103 复核 b28 的第三轮：攻击面换成"过表之后真请求会不会炸"——抓到一个真反例（§11.0 R6b）

第三轮（报告 `var/tmp/VERIFY-b28-fix2.md`）跑了**真 transport**（还起了本机临时 HTTP server），
不问"会不会抛"，而问"会不会在真机上变成 `down`"。抓到：

1. **NEW-A（唯一真反例）**：header **值**含非 ASCII 就过表 → 真请求 `UnicodeEncodeError: 'latin-1'`
   （`{"X":"中文值"}`）或 `UnicodeDecodeError`（`{"X":"a\x85b"}`）⇒ 记成 `down/transport_error`
   —— 与上一轮 N3 要消灭的是**同一类错**（配置错伪装成渠道挂了），只是从"类型"换成了"编码"。
   处置：值加 `value.isascii()`。**对照实测**：`\t`/`\x0b`/`\x01`/`\x7f` 都**发得出去、200**
   ⇒ 只禁 CR/LF + 要求 ASCII，**不动** C0 的既有宽松度（收紧要收在"真会炸"的地方）。
2. **NEW-B**：`http://:80/`、`http://e.com:99999/`、`http://e.com:port/` 过表 → `down`。
   处置：`parts.hostname` 非空 + `try: parts.port`；另补 **6 个合法 URL 回归**（大写 scheme /
   userinfo / 中文域名 / 带端口 / 回环 / 查询串）钉住"不误伤"。
3. 两处 doc 小口（报告第四节标题仍写"还没实测"；`routes_channels.py` 与 `api.ts` 的注释仍只列两种处境）
   + 一条既存脚注（报告脚本传相对路径时 `relative_to` 抛错、产物已写出但退出码非 0）都已修。
4. `expect: null` 该不该关：复核员**两轮都判"不该"**（结果是 `unknown/no_anchor_configured`，
   明确"未判定"，不是假绿）⇒ 采纳，并写明理由。

**它顺带给出的独立证据**（这类"它自己动手验过"的东西最值）：三分口径它在**隔离临时库**里端到端验过；
`json` 数组体它用**本机 server** 证明真发出去了；`REGISTRY-STATUS.md` 与它对真库的再生结果
**除时间戳外逐行相同**（证明快照是脚本生成而非手改）。

**门禁（按新纪律 §5 第 8 条单独跑，不并发）**：smoke 链 EXIT=0、pytest **1970 passed / 3 skipped / 0 failed**、
mypy 138/0、tsc 0。

⚠ 三轮复核的模式值得记下来：**第一轮问"会不会抛"、第二轮问"会不会误分类"、第三轮问"真机会不会炸"**。
同一段代码，三个问题问出三类缺陷；**"我声明它不抛"这种契约，只回答第一类问题**。
⚠ **过程自记（我的错，第二次）**：这次提交**又**因为多行 `-m` 里的引号/分号被 git 当成 pathspec 而失败
（§10.99 附近那次是引号、这次是多行）——同一个坑两次。**纪律：提交消息一律写文件、用 `-F`。**
⚠ **同一次操作里的第二个坑**：我把 `git commit …; git tag step-116-…` 写成一条命令，而那个 commit
因上面的原因失败了、`git tag` 却照样执行 ⇒ 快照标签落到了**上一个提交**（`1b4a54c`）。
已核对并重打到 `5a923fd`（`git rev-parse` 两个值都验过）。**纪律补充：`git commit` 与 `git tag`
不要写在同一行**——commit 失败时 tag 不会跟着失败，于是"快照指向哪"就悄悄错了。
（`step-111` 那次也是同类：快照落到旧提交。）

## §10.104 收官复核：R6 探针「可收口」——三件边角收掉，一条边界**明写不追**（§11.0 R6b）

第四轮（报告 `var/tmp/VERIFY-b28-fix3.md`）的判定是**可收口**，并留了三件边角：

1. `http://e.com:0/` 过表 ⇒ **必然** down（`urlsplit().port` 对 0 不抛；0 是 IANA 保留端口，
   没有服务器能监听）⇒ 拒掉。**同时保留**空端口 `http://e.com:/` 合法——复核用 curl 实测它按默认
   80 连，所以"端口为空"与"端口非法"必须分开处理（这条已写进 docstring）。
2. host 混入空格 / `%zz` / 内部 tab 仍会过表 → down：**刻意不追**（要 host 字符集/IDNA 校验），
   写进 `_validate_target` 的「已知边界」段。**宁可写明边界，也不假装已解决**。
3. `REGISTRY-STATUS.md` 自称"自动生成，勿手改"却没随生成器再生（差 2 行）⇒ 重新生成。
   ⚠ 这是"产物陈旧"这一类问题：改了生成器/标题，就要**同步再生产物**，否则仓库里两份口径。

**复核自己的取证（最值钱的部分）**：NEW-A **无误伤**（`\xff`/`\x80`/`\xe9` 线上也一律
`UnicodeDecodeError` ⇒ `isascii()` 没拒掉任何能用的值）；隔离临时库 e2e 三处境与注释逐条对得上
（`false/NULL`、`true+no_anchor_configured`、`true+NULL`）；相对路径 EXIT=0；`__str__` 抛异常不逃逸；
**真库全程未被改动**（131/78/11/13/29，`max(last_try_at)` 仍是复探那次）。

**门禁**：smoke 链 EXIT=0、pytest **1973 passed / 3 skipped / 0 failed**、mypy 138/0、tsc 0。

⚠ 四轮复核的模式（值得下一轮照抄）：**①"会不会抛" → ②"会不会误分类" → ③"真机会不会炸"
→ ④"边界与产物是否也有话说"**。同一段代码四问四类缺陷；我一开始只在 docstring 里声明"不抛"，
那只回答了第一问。**"这个模块很稳"这种判断，必须由别人换着问法来证。**

## §10.105 R6c-1：五类能力表补齐（68/131→131/131）+ 链快照当场抓到我自己的规则错误（§11.0）

### 1. 补齐（63 条缺口）
按"能不能查"切成四组：A 法规族 18（**17 空** + 1 条 `["发布"]`）、B 标准族 20（**全空**）、
C 其它/聚合 7（**全空**）、D 工具类 18（规则判"不参与五类"）。A/B/C 派**三个子代理逐条判**
（只读调研文档 + 适配器代码 + 探针表，各自写盘，父代理只读摘要）⇒ 这正是 §5 反上下文压缩纪律
想要的样子：**重活在子代理，父代理只吃结论**。
产物 `src/core/update/channel_answers.json`（131 条，每条带 `basis`/`confidence`/`source`）
+ `channel_answers.py` + `scripts/answers-matrix.py` + 13 条用例。

**B 组的发现值得单独记**：`std-cn.md §7` 本来就是**机读附录**（38 条，每条带 `answers`），
那 18 条"缺声明"其实**R1 早就写了 `"answers": []`**——缺的不是调研，是**搬运**。
⇒ 教训：**"台账里某个字段是空的"不等于"这个信息没人查过"**，先看调研文档有没有机读附录。

### 2. 我自己被自己的工具抓到（本步最值钱的部分）
我第一版 `ledger_chain` 的规则是"台账 `wiring='wired'` 且 `enabled=1` 的都进兜底链"。
写完 `scripts/chain-snapshot.py` 一跑：**9/9 个样例号的链都变**——`wired` 里混着 5 条
**前缀专用**渠道（`dbba`/`hbba`/`mee`/`ndls`/`ttbz`），泛查链从 2 条变 7 条。
两处都错：① 每号最多 7 次请求（预算/耗时）；② `dbba` 只答 DB 号，拿它试 ISO 是白跑。
⇒ 规则改成"**成员资格是显式名单**，台账只做硬过滤与报告"，并把
**"wired ≠ 兜底成员"**与**循环问题**（`wiring` 本是反查 routing 得到的）写进 docstring。
**这一步没有改巡检行为**——快照工具的全部价值就在这：**让"接入后会怎样"在动手前就看得见**。
现在真库快照：过滤后 = 今天的链（0/9 变化），5 条候选**列出来**而不是被悄悄提升。

### 3. 一条 flake 终于点名（前几轮的欠账）
全量首跑 **1999 passed + 1 failed**、二跑 **2000 passed / 3 skipped / 0 failed**、
mypy **140/0**。那条失败是
`tests/test_answer_materials.py::TestAnswerIntegration::test_scoped_answer_injects_materials_and_records_usage`
（`assert None == {"output_dir": "…/out9"}`），**单独跑通过**、二跑通过 ⇒ 频率约 1/3，
与本轮改动无关（文件顺序上它在新增测试**之前**）。
⚠ 前几轮我说过"知道有 flake 却叫不出名字"——今天**名字与现象钉住了**（但"是不是同一条"无法证实）。
**不顺手改**：那是另一条线，要单独的根因分析（且它自己会给出证据）。

### §10.105 补：复核 b29 抓到的两处（一处是"承诺没实现"）

6 条声明 **5 成立 / 1 措辞比证据强**（报告 `var/tmp/VERIFY-b29.md`）：

1. **引错证据行**：`channel_answers.json` 里 `seed:law-cn:浙江省人大` 的 `basis` 写"附录同条
   answers=["发布"]"——附录里 `浙江省人大` 是 `[]`、`浙江省人大-首页` 才是 `["发布"]`。
   **取值本身站得住**（§6 散文有实测），错的是引用 ⇒ 已改引 §6 并在生成脚本里加覆盖，
   **重生成不会退回旧错**。
2. **docstring 承诺没实现**（这条比笔误严重）：`ledger_chain.py` 写"名单里有、代码里没有的名字
   会被报出来"，但 `known` 是**死参数**（`_ = known`）、`missing_in_code` 只看台账行
   ⇒ 显式名单里的 `nope_x` **静默留在链里**。改成 **fail-closed**（没有适配器就不进链）
   + 新增 `roster_missing_in_code` **点名**，并加用例钉住。
   ⇒ 教训：**"我在 docstring 里写了"不等于"代码做了"**——这次是复核员拿一个不存在的名单成员试出来的。

它顺带纠正我两处口径（已改文档）：**C 组 7 条里有 1 条是聚合入口、不是 tool**；
**B 组那句"缺的不是调研是搬运"要加"主要"**（20 条里 18 条命中机读附录，另 2 条确属新调研）。
它的保留意见也记下了：附录行**没有 id**（靠 name 匹配，脆弱）；**R1 那 68 条的 basis 是弱的**
（只写"未逐条复核"）——已写进 JSON 的 note，不当作"已核"。

⚠ 流程自记（第三次同一类错）：我在 `docs/CHANNEL-COVERAGE-PLAN.md` 里写 `answers: []` 引号时
又用了 **ASCII 双引号套在双引号字符串里**，`python -c` 与 `Add-Content` 各炸了一次；
还有一次把 `**` 写进 Python 函数名（`def test_..._也**不**过滤`）导致收集失败。
**纪律：中文散文里的引号一律用「」，代码标识符里不出现 markdown 记号。**

## §10.106 R6c-2a：**先量再决定**——量出来的结论推翻了原计划（真问题是标准号写全角斜杠）

**要拍板的点**：要不要把 `ndls` 这类前缀专用渠道提升为泛查兜底成员。我推荐"先不提升、先量"，
本轮就是那次量——**结论是这个杠杆用错了**，而且发现的问题比原问题更值钱。

**量法**（刻意可复现、不挑样本）：真库 `doc_meta` → 取**走泛查兜底**的号 → 按 `doc_id` **等距抽样 12 个**
→ 每个号跑 `official_gb` / `govcn` / `ndls`。第一轮：今天两棒只答上 **1/12**，`ndls` 额外 0，
但 **`ndls` 对其中 11 个全部报错**。⚠ 这一步的结果**本身不足以支持任何结论**（样本几乎全是同一种写法）
——于是去查写法，这是本轮的关键动作。

**普查（6417 条标准）**：**5879 条（92%）的标准号写的是全角斜杠 `／`（U+FF0F）**，
是**唯一**的系统性异常字符（另 11 条是法规名混进了标准表，属另一条线）。

**根因**：`norm_no()` 只剥半角 `/` ⇒
`norm_no('GB／T 17098-1997')='GB／T17098-1997'` vs `norm_no('GB/T 17098-1997')='GBT17098-1997'`
——**永不相等**，`pick_row_by_norm` 这类"按归一号挑行"的匹配**全线失手**。

**决定性 A/B**（同一批号，两种写法各跑一遍）：原样全角 **任一命中 0/6，ndls 报错 6**；
换成半角 **任一命中 5/6，ndls 报错 0**。

**处置**：`norm_no` 字符类收进全角斜杠（一行）+ `TestNormNoFullWidth`（两种写法归一相等、
**全角目标能命中半角行**）。门禁：pytest **2018/3/0**、mypy **140/0**。

**为什么值得单列一节**：这次"先量"省下的不是时间，是**一条错路**——若按原计划把 5 条渠道提升进泛查链，
每号多打 5 次请求，而在一个 92% 的号写错格式的库里，**这些请求全都打在错的查询串上**。
⇒ 教训：**在"加资源"之前，先确认现有资源是不是被浪费了**。
（配套登记：查询侧用规范形、5879 行存量是否归一、入库侧防新增、11 条法规名混表。）

### §10.106 补：复核 b30 更正了我的机制，并顺出一个真 bug（ndls 全角号发不出请求）

**复核结论：6 条声明 5 成立 + 1 部分成立**（报告 `var/tmp/VERIFY-b30.md`）。它把我的**机制说错**指了出来：

- 对的方向：`official_gb.py:50-51` 确实把**原始号**放进 URL（实测 `searchText=GB%EF%BC%8FT+…`）；
- **我说错的地方**：`ndls` 的 6/6「报错」**不是"站点查不到"**，而是 `ndls.py:89` 把原始号拼进
  **Referer**、HTTP 头按 latin-1 编码 ⇒ **请求发出之前**就抛 `UnicodeEncodeError`。
  两者原因完全不同，现场都只表现为"每个号都失败"。
- 它还给了**反例**：`std_samr_hb.py:58` 用 `norm_no()` 查的就是规范形 ⇒ 我"适配器都用原始写法"
  这句**不成立**；待办①必须**按渠道拆**（点名的 7 条 + 一个已归一的正面例子）。

**顺着它把真 bug 修了**：Referer 关键词改用 `quote(...)`（同仓 `hbba.py:89` 已有正确写法），
加 2 条离线用例（发出前不炸、Referer 纯 ASCII 且 `%EF%BC%8F`/`%20` 转义）。
**修后同一批号复测**：原样全角 **0/6 → 5/6 命中**、`ndls` 报错 **6 → 0**；半角仍 5/6。

⇒ **两个"一行修复"（`norm_no` + ndls 头）把这类号从"全灭"变成"5/6"**。
剩下 `official_gb` 那类（原始号进 URL 查询串）仍 0/6 —— 那才是待办①真正要做的。
**这条经验值得记**：复核员说"你机制说错了"时，别只改措辞——**顺着正确机制去看，往往就有一个真 bug**。

## §10.107 R6c-2b：查询侧统一半角规范形——**原样全角 0/6 → 5/6**（§11.0）

**做了什么**（纯代码、可回滚）：新增 `query_no()`（只换字符形状：`／`→`/`、`－`→`-`，**保留空格**
——cssn/mee 实测"带空格完整号"才排第一），落到 **6 个查询点**：`official_gb` / `hbba`（`dbba` 继承）
/ `ttzb` / `cssn` / `mee` / `govcn_announce`；`std_samr_hb` 不用改（本来就查规范形）。
8 条守卫用例逐渠道断言"**送出去的请求里没有全角斜杠**"（比"改了哪一行"更防回归）。

**真机复测**（同一批号同一脚本）：原样全角 **任一命中 0/6 → 5/6**、`official_gb` **0/6 → 5/6**；
半角写法 5/6 不变。⇒ 三处修复（`norm_no`、`ndls` 非法头、查询点规范形）合起来把"全灭"变"5/6"，
剩下 1 条是格式本身不成号的 `GBZ／T`。

### 诚实发现：这是"同一根因的另一层"，不是新问题
`text_utils.clean_standard_name`（2026-09-17）**早就修过全角→半角**，docstring 还明确写着
"库内 `standard_name` 是从**文件名派生**的，各调用方各派生各的（`write_queue_bootstrap` /
`scripts/_stdparse.derive_standard` / `std_bulk_import`）⇒ **修数据前先把派生归一，否则灌一次库又脏一次**"。
⇒ 我是在**更外一层**（标准号与查询串）重新撞上同一类根因。
**教训写进纪律：动手前先搜"这一层有没有人修过"**——不然会把"别人修过的同一类问题"当成新发现。

### 登记不做（各有理由）
1. **入库侧防新增**：派生路径不止一处、影响 35k 行 ⇒ 单独一轮 + 复核；而且查询侧修好后，
   存量全角写法**已不影响命中**（只剩展示形态）。
2. **存量 5879 行是否归一**：数据变更，**要业主点头**。
3. **`norm_no` 与 `canon_standard_no` 自称"同口径"但实测不一致**（`—`/`－` 上不同）
   ⇒ 登记为"重复所有者"（与 R5c 的 `inspector.CHAIN` 同类）。

⚠ **过程自记（本步踩的坑）**：我用脚本批量插入行内注释时，两次把注释插进**多行调用**里，
`mypy` 当场报语法错——而 `pytest` 给出的下游报错很迷惑（"这些渠道在 routing 链里被引用、
但适配表里查不到"）。**批量改动后先跑 mypy，再跑用例**：顺序反了会先看到误导性失败。

## §10.108 复核 b31 + 存量全角回填执行：三处修复、一次自捉、一次落库（§11.0）

### 1. b31 抓到的三类（4 成立 + 2 部分成立）
1. **两处漏网**——我"送出去的请求里没有全角"的声明**不成立**：`ndls` 的 **JSON 搜索体** `keyword`
   仍是原始全角（**可达渠道**，routing 会把 AQ/GB 送过去）、`web_fallback` 的 `q` 同（已不在链里）。
   两处都改用 `query_no`，补 2 条用例。
2. **一个我没提的真失配**：`norm_no` **不折连字符**（`—`/`–`/`－`/`─`），而 `query_no` 与
   `canon_standard_no` 都折 ⇒ **只有匹配侧漏了**，表现是静默的"查得到但匹配不上"。
   ⇒ 对齐折同一组 + 用例（断言与 `canon_standard_no` 一致）。
3. **两处措辞比证据强**（接受）：我引用的 A/B 脚本证明不了前后对比（修好后两路请求被折成同一串），
   真正的 before/after 是**复核员的变异测试**；"原样 0/6"对 `ndls` 不成立且无 artifact
   ⇒ 以其换批 12 号的 **0/12 → 12/12** 为准。

### 2. 存量全角斜杠回填（已落库）
计划 **11758 处**、跳过 **2 处**（同一标准的两个文件——跳过即"不制造重复"）；
写库后**逐条对账**：形状替换不纯净 **0**、**归一语义被改 0**（`norm_no(old)==norm_no(new)` 全 11758 条成立）、
库里与新值不一致 **0**、剩余全角**正好那 2 处**、`integrity_check` **ok**；
清单 `var/backup/r6c2c-normalize-slash-20260918-210550.json` 可精确回滚。

### 3. ⚠ 我自己抓到并更正的一处错（记下来，因为它比"没犯错"更有信息量）
清单里 `db_after` 与 `db_before` **完全相同**——因为我在事务提交后**立即**取库指纹，
而当时改动还在 **WAL** 里、**主库文件一个字节都没变**。也就是说：
**"留了指纹"不等于"指纹有用"**。脚本已修（先 `PRAGMA wal_checkpoint(TRUNCATE)` 再关连接、
最后取 stat），清单里补了 `db_after_checkpoint`（sha256 `5a775938a3d4…`）与 `correction_note`（**不掩盖**）。
讽刺的是：这条正是复核员收尾时提醒的那件事（"可回滚不能只是口头承诺"）——**我自己先撞上了**。
⇒ 由此得到一条可复用的检查：**凡"写前/写后指纹"，都要确认取的时刻在数据真正落盘之后**
（SQLite 是 WAL 模式时尤其如此）。

## §10.109 R6c-3「这一号该问谁」可调用化 —— 真机量出 **GB/T 从未进 ndls**（§11.0）

### 1. 交付
`src/core/update/channels/question_router.py`：`channels_for`（五类 → 候选渠道，**按链的顺序**）、
`route_report`（每类多给一个**原因**：`ok`/`no_capability`/`off_chain`/`all_down`）、
`unanswerable_classes`（调用方据此写 `unanswerable`，**不是** `not_found`）。
用例 `tests/test_question_router.py` **20 条**（设计稿验收 5 条全覆盖，第 5 条改为**独立复算**）；
人用脚本 `scripts/question-route.py`（只读，支持 `--sample N` / `--json`）。**不改巡检行为**（只读层）。

### 2. 交付时做的两个判断（都写进了 docstring）
- "候选为空"**必须分开记原因**：`no_capability`/`off_chain` 是结构性缺口，`all_down` 是"今天全挂"。
  设计稿只说"记 unanswerable"——合成一个理由会让业主以为"查过了"；
- **不在本模块滤 `enabled=0`/`wiring=broken`**：那是"链"的职责（`ledger_chain` 已在做）。
  两处都滤 = 两个所有者；R6c-4 换链源后由链负责。

### 3. ⚠ 我自己踩的三个坑（都是用例/真机当场抓的）
- 把**标准号写成第一个位置参数**（`channels_for("HJ …")`）⇒ 原报错只说"不是五类之一：'H'"，
  看不出是位置错。已改提示（"单类怎么写 / 标准号放第二个位置参数"）+ 补用例；
- "已知缺口"用例里我把原因断言成 `off_chain`，**实际是 `all_down`**——被用例当场纠正
  （`off_chain` 是"链上没人能答"，`all_down` 是"能答的那根今天死了"）；
- `--sample` 第一版查 `documents` 表（真名 `doc_meta`）且用了可写连接 ⇒ 已改真名 + `mode=ro`。
  顺带确认 `doc_meta.standard_no` 是 **UNIQUE**（这正是回填"撞车即跳过"的原因）。

### 4. 真机量到的三件事（本步最有价值的产出）
1. **链只有 2–3 根棒**，且五类今天都有候选——**只是因为 `official_gb` 声明了全部五类**；
   `mee`（HJ）只声明"发布" ⇒ **`official_gb` 一判死，HJ 的"修订/编号核验"就没有候选**
   （已用**记录型用例**钉住：链一加宽它就红，逼人有意改）；
2. **9 条渠道声明了能力、却没有任何号能路由到它**（全部 `wiring=unwired`；其中 5 条 `state=ok`）
   ——R6c-4"要不要把专用渠道提升进链"的真实输入；
3. ⚠ **GB/T 从来没被送进 ndls**：真库 6417 个号里 **6129 个（95.5%）是 `GB/T`**，
   而前缀正则 `^GB\s?\d{4,5}\b` **不匹配 `GB/T`** ⇒ 它们只走（official_gb, govcn）。
   真机实测 ndls **答得出来**（`GB/T 38496-2020` → 现行、发布 2020-03-06、实施 2020-10-01、
   名称"消毒剂安全性毒理学评价程序和方法"）⇒ **下一步 R6c-3b** 单独修（含
   "`select_chain` 是第 7 个读原始号的站点"：`GB／T 14308-2010` 那条全角行今天匹配不上 GB 规则）。

## §10.110 复核 b32 把我"入库侧不用改"**证伪**了 —— 收口 + 加固 + 修那一行坏号（§11.0）

### 1. b32 的结论（声明 1/2/3 成立，4/6 部分成立，**5 不成立**）
- 存量回填本身**数据正确、可逆、无漏改多改**（它逐条独立复算，还自己复算了 WAL 机制
  ⇒ 我那处"提交后指纹不变"的自我更正成立）；
- ⚠ **它证伪了我的结论"没有活的派生路径产出全角"**：
  `write_queue_bootstrap._ingest_doc` 用 `path.stem`（`auto_tag("")` 恒 None），
  实测写出 `standard_no='GB／T 10058-2023 电梯技术条件(1)'`；
  `var/ocr-loop/ingest_from_manifest.py` + manifest（**8205/8484 条带全角**，
  **约 2322 条 PDF 尚未入库**），`split_std` 漏了 `GBZ／T` ⇒ 号被压成裸 `GBZ／T`，
  **真库现存那一行就是它的指纹**（已经写过脏号）；
  我的"日期论证"也不成立：`created_at >= 2026-09-17` 的行数 = **0** ⇒ "0 条新增"是**没数据**，
  不是**没脏数据**；
- **4.4 有盲区且实测制造了重复**：判重是 apply 前快照，看不见"两行归一到同一个尚不存在目标"，
  真脚本在一次性库上写出重复 `('GB/T33332003', 2)` 还报 integrity ok（`short_code` 只有非唯一索引）；
- 附带：Ctrl-C 不回滚（`write_transaction` 写的 `except Exception`）、`conn2.close()` 关掉共享连接、
  回填在 `event_log`/`updated_at` 上**零痕迹**、无 CAS/rowcount 校验；用例挡不住上述任何一类。

### 2. 处置（R6c-2d）
**存储形第一次有主**：`text_utils.store_standard_no`（1:1 折 `／`/`－`，不动空格/大小写/年份）
+ 收口在**写边界** `clause_repo.insert_document`（三列都折——因为 `short_code` 是从 `standard_no`
派生的，`pipeline:2169`/`docx_ingest:66`/`track_l:306`，逐个调用方折必然漏），
另两个裸写入口（`bulk.py` INSERT、`auto_tag` UPDATE）过同一个 helper（入口清单写在代码旁）。
**`write_transaction` 改 `except BaseException`**——修的是**每个写者**的 Ctrl-C 语义，不只我的脚本。
**回填脚本加固**：计划内自撞判重 + 清单无重复断言 + CAS/rowcount（对不上整批回滚）+ 不再关共享连接
+ 一条汇总 `event_log`（刻意不 bump `updated_at`）。加固后对真库 dry-run 仍是**计划 0 处、跳过 2 处**。

### 3. R6c-2e：修那一行坏号
`'GBZ/T'` → **`'GBZ/T 160.27-2004'`**、`short_code` → `'GBZ/T160.272004'`、
名去掉开头的号 → `'工作场所空气有毒物质测定硼及其化合物'`；dry-run 修 1 跳 2（两条法规行**故意不动**），
写后 integrity ok、清单可精确回滚、指纹 `5a775938a3d4…` → `97f1dcb70e80…`。

### 4. 诚实边界
① **已执行的那次回填在 `event_log` 里仍然零痕迹**（我没补写追溯行——事后补的行容易被误读成"当时记了"）；
② **2322 条待入库全角仍在**（收口后它们进库会变半角，但"跑不跑这个循环"是业主的操作决定，我不替他跑）；
③ ⚠ **行为变化（有意）**：折形状后"同一标准的第二份文件"会撞 `standard_no` UNIQUE ⇒
**报错而非静默写第二行**——跑 OCR 循环的人要知道这条。

## §10.111 R6c-3b：兜底链**量完再改**（`ndls` 插到 `govcn` 前）+ 第 7 个读原始号的站点（§11.0）

### 1. 量出来的结论推翻了我原来的判断
R6c-3 时我认定"6129 个 `GB/T` 从不进 `ndls` = 覆盖缺口，应把 `GB/T` 补进前缀路由"。
**先量，判断就变了**：
- **量 1（12 个真库 `GB/T` 号 A/B）**：`official_gb` 12/12、`ndls` 12/12，两者都给状态
  ⇒ 在 `GB/T` 上这**不是"能不能答"的缺口**，差别在**字段**（`official_gb` 无废止日期/代替链，
  给的是 HTML 表里第一个日期；`ndls` 给实施日期 + 废止日期 + 代替）。且 `ndls` 默认发**两次**请求
  ⇒ **不把它提到 `official_gb` 前**（谁在前不改变"能不能答"，却让 6129 个号请求数翻倍）。
- **量 2（按前缀分层 10 个号）**：`official_gb` 4/10、**`govcn` 1/10**（唯一命中是**法规**行）、
  `ndls` **6/10**；`govcn` 还最慢（未命中时 7.1s，`ndls` 1.2s）。
  真例：`GBZ 37-2024`、`GBZ/T 160.27-2004` 都是 `official_gb` miss 而 `ndls` 命中。
  ⇒ **`govcn` 排第二棒 = 在标准号上白打一次请求**。

### 2. 改动
`_FALLBACK` 改为 `(official_gb, ndls, govcn)`（`govcn` 不删：它是今天唯一命中法规名行的那根）；
`select_chain` 用存储形折半角匹配（**第 7 个读原始号的站点**）；新增 `first_route()` 作为"前缀首选"的唯一来源。

### 3. 两条记录型用例**如约变红**，被我有意改写
`test_已知缺口_official_gb判死时_HJ会丢两类`（R6c-3 钉的单点故障）现断言"缺口已被补掉"；
`test_专用渠道在候选里而不在链里[ch:ndls]` 里 `ndls` **毕业**成链上成员，参数换成 `dbba`/`hbba`，
并另加一条正面钉住毕业。

### 4. ⚠ 我自己抓到并更正的两处
- **措辞比证据强**：我原说"全角 `GB／T 14308-2010` 掉了国标→状态权威的首选"——**错**：
  半角的 `GB/T …` 同样不匹配任何 GB 规则，两种写法本来都走泛查兜底。**有真实差别的是
  "前缀规则里带斜杠"的号**（`T／ZSA …` 匹配不上 `^T/\b` ⇒ 丢掉团体标准专门渠道）。
  docstring/用例按准确说法改了。
- **量完才发现的假差异**：`chain-snapshot.py` 靠"`select_chain(no)[0]` 不在兜底名单里"反推前缀首选，
  `ndls` 进名单后把 3 个样例误报"⚠ 链会变"；改成向路由要（`first_route`）后 9 个样例全部"不变"。

**诚实边界**：本轮**没有**跑真实巡检批次端到端；"哪根棒能答"的证据是 A/B 实测 + 台账探针。

## §10.112 R6c-3c：`official_gb` 把**发布**日期当**实施**日期存了（P1 准确性，最常用的那根棒）

**发现路径**：R6c-3b 的 A/B 看到 `official_gb` 与 `ndls` 的日期差几个月（`GB/T 38496-2020`：
2020-03-06 vs 2020-10-01）⇒ 抓原始 HTML 逐格看：`GB 18218-2018` 行是
`td[7]='2018-11-19'`（发布）、`td[8]='2019-03-01'`（实施），而适配器取 `dates[0]` ⇒ **存的是发布**。

**证据**：12 个真库 `GB/T` 号交叉验证 —— `dates[-1]`（第 2 格）与 `ndls` 实施日期（a205）
**12/12 一致**；`dates[0]` 只在"发布==实施"的 **2** 个号上一致。
且**只有这一根错**：`ndls`/`cssn` 都是 `impl or pub`、`hbba` 取 `actDate`、`std_samr_hb` 取 `ACT_DATE`、
`mee` 按"实施时间"列取。

**影响面**：`effective_date` → `inspector.py:372 latest_info` → `update_change_event.latest_info_json`
→ 面板/报告里的日期；而 `official_gb` 是 `GB/T` 的首选棒 ⇒ 大多数变更事件的日期受影响。

**修法**：`_impl_date(dates)` 取第 2 格（只有一格时如实取用）；取 `[1]` 而非 `[-1]`，因为列**追加**
比**重排**常见。⚠ 一条老用例把 bug 钉住了：`test_official_gb_parses_real_openstd_html` 断言
`effective_date == "2022-03-15"`（发布），而它**上面两行的 fixture 注释**写着列序是"发布日期 | 实施日期"
——**注释对、断言错**。已改断言 + 把证据写进注释，并补 4 条 `_impl_date` 单测。

**登记同类可疑（未修）**：`ttzb.py` 用 `datePublished` 填 `effective_date`（也是发布语义），
但 `T/` 类号今天库里没有、且我还没核 ttzb 响应里有没有实施日期字段 ⇒ 列待办。

**诚实边界**：只修**解析**；已写进历史事件的旧日期**没有**回填（那是另一件事）。

## §10.113 复核 b33：收口"结果"成立，但**我做过头与做漏了各一处**（§11.0 R6c-3d）

b33 把全部 tracked 文件的写者逐条判完（121 文件 / 语句级 24 处 / `CREATE TRIGGER`=0）：
**没有第三条能把全角 `／` 写进那三列的活路径**（声明 1 的结果、2、3、4、5、6 全部成立）。
但它抓到三件，都已修：

1. ⚠ **最高风险：我给"名称"列折了连字符——那不是换形状，是改文字。**
   真库 **5 行**标准名拿全角 `－` 当中文连接号（`丙烯腈－丁二烯－苯乙烯（ABS）…`、`蒸馏－硝酸钍容量法`…），
   折了以后同一标准再入库会写成半角、新旧行名字不一致且无提示。
   ⇒ 拆成 `store_standard_no`（号：折 `／` 与 `－`）与 `store_standard_name`（名：**只折 `／`**），
   `clause_repo` 改为"列 → 折法"映射，`bulk.py` 名列同步。用例钉住那 5 行的写法必须保留。
2. ⚠ **次高：写边界折了、查重边界没折** ⇒ 全角重复件从"静默多一行"变成 `run_full_ingest` 里
   **未捕获的 IntegrityError**（我自己改出来的不对称）。⇒ 6 处 `WHERE standard_no=?` 一律折后再查。
3. **措辞被证伪**："写这三列的**全部入口**"——实际至少 4 个写者不在清单里
   （`fix_standard_name_suffix.py`、两个 bench 脚本、外加我新写的 repair 脚本），
   而"入口清单"正是 b32 找到漏口的办法。⇒ 改成"已知入口 + 明确列出不在收口路径上的那几个"，
   并加用例断言源码里不许再出现"全部入口"。
4. 顺带更正数字：待入库全角条目它独立复算 **2282–2283**（我写的"约 2322"是 basename 代理口径，差 ~1.7%）。

**诚实边界**：这三处是**按复核意见改的**，改完**还没经独立复核**；b33 与我都没有跑端到端（没造 PDF 跑整条管线）。

## §10.114 R6c-5：能力表审计（子代理 b35）+ **模拟排序发现"照做会变坏"**（§11.0）

b35 把 18 条 `ch:*` 适配器的 **56 条五类声明逐条对代码核完**：
`supported 25 / partial 31 / not_supported 0 / cannot_tell 0`。要点：
- **废止日期只有 3 条真拿到**（`ndls` a206、`hbba`/`dbba` fzDate），其余 8 条只有状态串或**标题关键词**；
- **`编号核验` 18 条全 partial**（无一条做"写法是否规范"的判定）；
- 抓到 **3 处"docstring 写了、代码没写"**（`hbba`/`dbba` 的 `reviseStdCodes`、`ttzb` 的 `abolishDate`、
  `mohurd` 的"详情含发布时间"）——本仓那条老教训的又一例；
- **唯一漏声明**：`ch:flk_client` 的 `编号核验`（`flk_client.py:73-81` 解析 `bbbs`）；
- **最弱一例**：`ch:govcn` 的「现行性」三条 branch 全是**猜**，而设计稿曾把它当"权威对照源"⇒ 口径冲突，登记；
- 它**独立复现了 R6c-3e 的动机**：`ChannelResult` 只有一个日期槽 ⇒ 6 条渠道"发布日期无处安放"。

⚠ **本轮最值钱的一步是"先模拟"**：原打算"同一类里 supported 排在 partial 前"。先在内存里模拟
（12 号 × 5 类）：**20 格变化**，其中 **8 格把 `发布` 类搞坏**——
`废止` 的 `official_gb(partial)→ndls(supported)` 是对的，但 `发布` 里 `ndls` 被压到 `govcn` 之后
（因为 b35 给 `official_gb` 的 `发布` 判 supported，**而它产出的是实施日期**）。
⇒ 定下顺序：`answers_detail` 先只当**证据**落库、不参与排序；**先做 R6c-3e（补 `published_date`）**，
再重新模拟确认只有 `废止` 那一类翻，然后才启用 verdict 排序。
**教训**：把"能力有/无"当排序键之前，先问"它给的是不是这一类**要的那个**东西"——
"有日期"与"有这一类要的日期"不是一回事。

## §10.115 复核 b34 抓到两个真问题：预算把最后一棒截掉、ttzb 错标已确认（§11.0 R6c-3e/3f）

b34 复核 R6c-3b/3c/3d：**A（排序方向）/A（台账相等）/A（UX）/B（第 2 格=实施）/C（名称折法）/
E（清单诚实度）成立**（它自抽 7 个号复核：`official_gb` 5/5、`ndls` 5/5、`govcn` 0/5）；
**三条不成立，都是我的问题**：

1. ⚠ **我改出来的潜伏回归**：链长变 4 后 **`MAX_ATTEMPTS=3` 把最后一棒截掉**——
   `mee`/`dbba`/`hbba`/`ttbz` 四族的 `govcn` **永远探不到**（旧链 probed=[mee,official_gb,govcn]，
   新链 [mee,official_gb,**ndls**]）。真库链长今天全 3 ⇒ 0 行受影响，但库里一出现 HJ/DB/行标就少一根棒。
2. ⚠ **`ttzb` 的错标是"已确认"**：真实响应 `T/CECS 2350-2026` 发布 2026-06-12 vs 实施 2026-12-01
   （**差 6 个月**），而 `implementDate` **本来就在**白名单里。
3. **F**：链序用例第一句断言的是**自己文件里的 `TRAIL` 字面量** ⇒ 永真。
4. **D**：收口侧 `WHERE standard_no=?` 是 **5 处**（我写"6 处"是数错），另有 2 处未折等值读。
5. B-残留（**设计差异，不是错标**）：废止号上 `official_gb` 报实施日、`ndls` 报废止日
   （GB 11121-2006：2007-01-01 vs 2026-07-01）——这正是"废止类该问 ndls"的依据。

**R6c-3e/3f 处置**：
- 新增 `ChannelResult.published_date`，6 条渠道各自落位（`official_gb` 第 1 格 / `ndls` a101 /
  `cssn` a101 / `std_samr_hb` ISSUE_DATE / `laws_db` gbrq / `ttzb` datePublished；`hbba`/`dbba`
  的 `issueDate` 也一并命名解析），`inspector` 记进 `latest_info`；
  ⚠ `_pub_date` 在只有一格时返回 `None`——**不许把唯一那格当发布**；
- `ttzb`：`effective_date ← implementDate`、`published_date ← datePublished`（抽 `_pick_dates` 便于单测）；
- `govcn_announce` 同类修（`hit['date']` 是成文日期 ⇒ 落发布槽，实施**如实留空**），两条 fixture 期望随之改；
- **预算截断修掉**：`max(MAX_ATTEMPTS, len(可用链))`，短链行为不变；**做了变异测试**——
  改回旧写法那条四棒用例当场红（`[1,1,1,0]`）；
- 收掉剩余两处等值读（`resolve_clause`、`ocr-loop/vlm_ocr.py`）+ 修掉那条永真断言；
- 数字更正：收口侧 **5 处**。

## §10.116 复核 b39 抓到 R6c-4d 的**生产恢复档**：欠账随崩溃静默消失（§11.0 R6c-4e）

**复核结论：4 条声明 2 成立、2 部分成立**（报告 `var/tmp/VERIFY-b39.md` + `var/tmp/b39-verify/`）。
它把我这一步的护栏在生产恢复路径上的**失效**实测出来了，还抓到一处文档过时话。两条都改了。

**它抓到的真问题（声明 2）**：`_commit_outcome` 是**第 5 个**写断点的地方，它只推进队列、
**不带欠账**；而欠账当时只在内存里累积、只在暂停/终态才落盘。于是"号已提交 → 进程被杀
（status 留 `running`）→ `pause_batch` → `resume_batch`"这条**生产恢复**路径上：已提交的号
**不再入队**、内存清单也没了 ⇒ 批次照报 **done**，结构性欠账**静默消失**。
（b39 用同构对照证明 `error_trail` 也一样，且这是**既有**缺陷、非本步引入。）

**修法**：事件行是**持久**凭据（`latest_info_json.classes_unanswerable` 就在里面）⇒ 新增
`_debt_from_events(batch_id)`，在终态裁决**之前**把库里的欠账并进内存清单（恢复到时记
`classes_debt_recovered`）。只认 `classes_unanswerable`（结构性），**不认** `classes_unanswered`
（含 `not_probed`＝"这次没轮到问"）；读库失败**不抛**，退回内存口径并出声
（`classes_debt_unreadable`——"读不到"≠"没有欠账"）。

**用例与变异**：`test_提交后被杀_欠账从事件行收回`——真跑一批 → 把断点改写成"崩溃后
`pause_batch` 手上那份（无欠账）" → `resume_batch` 必须仍 `failed`；让 `_debt_from_events`
直接返回 `[]` ⇒ 该用例当场红（**实测复现 b39 的 `done`**）。

**它抓到的第二件事（声明 4）**：R6c-4c 段那句"这条终态恒等式还没接…done/四色口径一字未改"
被 R6c-4d 证伪后**原样留着**（我只追加了更正段）⇒ 按上一提交 `beae0fd` 立下的"**改在原处**"
惯例划掉并指向更正处。**教训**：只追加、不划掉，等于在文档里留一句假话；
同一形状的问题被复核员抓到第二次，说明"改在原处"要当**硬规矩**，不是偏好。

**登记未修**：`error_trail` 的同形状缺口（未判定号在"提交后被杀"档上同样会丢）——它属于
"四色恒等式"那条更老的守则，单独一步 + 自己的复核。

门禁：`pytest -q` 2125 passed / 3 skipped / 0 failed；`mypy` 142 文件 0 错。
快照 `step-137-r6c4e-debt-from-events`（`dddff8c`）。

## §10.117 R6c-7：`废止` 类的日期是**错标**的——真机 3 个废止号 3 行错（§11.0，P1 准确性）

**怎么发现的**：不是专门去找的。给 R6c-6 的"红/黄号补探"定价时，我问了一句
"补到了什么，值这 +19.4% 的请求吗"——答案是**今天记的那个日期本来就是错的**。

**错在哪**：`class_outcomes.conclusion_for('废止', r)` 在 `legal_status == 'withdrawn'` 时
把 `r.effective_date` 当废止日期带出去。可那个槽的语义**是实施日期**（`base.py` 自己写的），
而把 `effective_date` 填上的渠道里，**8 条判 partial 的渠道填的都是自己的关键日期**：
`official_gb` 取的是**实施日期列**、`cssn` 是"实施 or 发布"、`std_samr_hb` 是 ACT_DATE、
`laws_db` 是 sxrq/gbrq、`govcn` 是 pubtime、`ttbz` 是 datePublished、`web` 是第一个日期。

**真机一手实测**（3 个真废止号 × 2 渠道 = 5 行，**3 行错**）：

| 号 | 渠道 | 改前吐出的"废止日期" | 真相 |
|---|---|---|---|
| GB 16663-1996 | `official_gb` | 1997-07-01 ✗ | 实施日期（真废止 2026-09-01） |
| GB 1219-2008 | `ndls`（降级档） | 1986-05-01 ✗ | **站点没有 a206**，回落 impl_date |
| GB 11121-2006 | `official_gb` | 2007-01-01 ✗ | 实施日期（真值 2026-07-01） |

⚠ **最关键的一条教训**：错的**不只是**判 `partial` 的渠道——`ndls` 判的是 `supported`，
它自己的降级路径（详情缺 a206）**一样会拿 impl_date 冒充**。
⇒ 我原本以为可以"按能力判定兜住"（partial 才可能错），**这个修法不成立**；
只有让"渠道到底有没有解析出废止日期"成为**结果里的一等事实**才兜得住。
这和 R6c-3e 给 `published_date` 开槽是**同一个形状**：一个日期槽装两种日期，早晚出事。

**改法**：`ChannelResult` 新槽 `withdrawn_date`（`ndls` 从 a206、`hbba`/`dbba` 从 fzDate），
`conclusion_for('废止')` **只认这个槽**，`latest_info` 一并落它。
`ndls` 的 `effective_date` 因此回到"恒为实施日期"（信息没丢：两个日期都在事件里，
而且 `doc_meta.withdrawn_date` 与插件侧一直是这么分的——是**结果类缺这个一等字段**）。
⚠ 降级档 `withdrawn_date=None` 是"**不知道**"，不是"拿实施日期顶上"。

**变异测试（两处都当场红）**：`conclusion_for` 改回读 `effective_date` ⇒ class_outcomes 用例红；
`ndls` 改回 `wd or impl` ⇒ adapter 用例红。
**旧断言改在原处**：`test_废止_现行也是结论_非废止时无废止日期` 原来喂 `effective_date` 并期望
它变成废止日期——**那正好把被修掉的错标钉成了契约**（这类"测试在替 bug 站岗"的用例，
比没有测试更危险）。

**诚实边界**：库里 355 条事件里 **0 条**带 `classes` 键（R6c-4c 之后还没跑过巡检）
⇒ **今天没有已写坏的行走数据**，这是抢在下一次巡检之前落的护栏（与 R6c-4d 同形）。
本步只做到"**不再记错**"；红号要拿到**正确**的废止日期，仍需 R6c-6 定价的那步
（只对红/黄号补探 `ndls`）。

门禁：`pytest -q` 2128 passed / 3 skipped / 0 failed；`mypy` 142 文件 0 错。
快照 `step-138-r6c7-withdrawn-date`（`aa5e910`）。

## §10.118 R6d：渠道台账的**人工增删与复核**（目标②的后半，引擎侧）

**缺口**：台账此前**只能读**（列表 + 详情 + 立刻探一遍）。仓储层其实早就有
`upsert_channel`/`set_enabled`/`delete_channel`（种子导入在用），缺的是**给人用的写入口**。

**落了四个端点**：`POST /channels`（新增，id 可省 ⇒ `user:<slug>-<8位>`；`wiring` 默认 `user`、
`verification` 默认 `unverified`——**人工录入 ≠ 已核实**）、`PATCH /channels/{id}`（复核编辑
描述性字段）、`POST /channels/{id}/enabled`（启停不删：历史健康度是证据）、
`DELETE /channels/{id}`（痕迹带**删除前整行快照**）。

**两条不变量（都做了变异测试，且都不是"顺手加的"）**

1. **人工写不了运行期健康度**。`state`/`last_*`/`consecutive_failures` 一律 **422 出声拒绝**
   并指路探针。⚠ 为什么不靠 `overwrite_health=False` 的**静默丢弃**：静默丢弃会让人以为写成功了，
   而面板上那条"上次成功"会被错读成**真探过**——**那就是凭空造证据**。
   同理，未知字段名也 422（拼错就静默丢，是同一类事故的另一个入口）。
2. **人工改动一律留痕**。`channel/created|updated|enabled|deleted` 写进 `event_log`
   （`actor=user` + 改前/改后 JSON 快照），**与改动同一个事务**。
   留痕写在**仓储层**而不是路由层：路由不是唯一入口（脚本、将来的 CLI、测试都调仓储），
   而"人工改了台账却没痕迹"在审查场景里不可接受。
   删除时 `before_state` 里留着删除前整行 ⇒ **删得掉条目，删不掉证据**。

**测试逼出来的真 bug**：`update_channel.category` 是 **NOT NULL**，而人工新增说不出
"这属于哪一类" ⇒ 原先直接把 `sqlite3.IntegrityError` 冒到面板（用户看到的是一个 500）。
现在默认值落在**仓储层**（缺 `category` ⇒ `normalize_category(category_raw)` ⇒ `other`）——
**schema 不变量归所有者**，任何调用方都不该绕过它；"没分类"本身是一个正常状态。

**变异检查的做法值得记**：`var/tmp/r6dmut.py` 是一个 pytest 插件，运行时把
`channel_repo._audit` 换成 no-op，**不改仓库任何文件** ⇒ 四条依赖留痕的用例当场红，
去掉 `-p r6dmut` 全绿。（前几轮我改仓库文件再改回来做变异，这次的写法更干净，后面沿用。）

**仍未做（下一步）**：宿主插件代理（`plugin/src/channels.js` 现在只有列表 + 探测两条）
与**面板上的增删复核界面**。⚠ 宿主插件是**进程启动时静态 import** 的 ⇒
面板侧改动要等 DSH 宿主重启才生效，所以单独一轮做，别和引擎侧混提交——
**别把"引擎有了"说成"界面有了"**。

门禁：`pytest -q` 2136 passed / 3 skipped / 0 failed；`mypy` 142 文件 0 错。
快照 `step-139-r6d-channel-write-api`（`64c1597`）。

## §10.119 R6e：把"五类结论"显示出来——数据早就记了，界面一直没读

**这是一个"投入看不见"的典型**：引擎从 R6c-4c 起，每条变更事件的 `latest_info.classes`
里就记着"五类（发布/修订/废止/现行性/编号核验）各自答没答、是哪根渠道答的、答得全不全"，
R6c-7 又把它修准了——**但面板从头到尾没读过它**（批次收尾只归组 `change_type`）。
换句话说：前面几轮的准确性投入，业主在界面上**一点都看不到**。

**这一步做的**（宿主侧 + 客户端 + 离线用例）：
- 一次拉取、两份归组（`by_type` + `by_class`），收尾落进状态文件，并在宿主日志打一行
  `五类结论 发布 n/N · …（未答主因：…）`；
- 综览多一行 `五类结论：发布 n/N · 修订 … （未答主因：渠道无此字段 k / 未轮到问 m）`；
- 状态文件的 `by_class` 走白名单清洗（旧文件 ⇒ `null`）；启动自愈与 `by_type` **共用同一次拉取**；
- 新增 `plugin/scripts/smoke-class-summary.mjs`（9 条断言），`smoke` 链 22 → 23 段。

**三个口径（这一段是这轮的真正内容）**：
1. `classes` 键**不存在** ⇒ 计 `unreadable`、**不进分母**。那是"这批没记五类"（R6c-4c 之前的事件、
   引擎读台账失败降级），与"记了但没答出来"是两回事；UI 上单列"另有 N 条未记五类"；
2. 某类**缺项** ⇒ 记 `absent`，**不许**冒充 `not_probed`（"没轮到问"是另一回事）；
3. 分母**只数有记录的条数**——否则"发布 3/500"这种数字看着很吓人，其实什么都没说明。
   这一条与仓库里既有的那条教训同源（`wiring` 与 `state` 分开报、否则覆盖率虚高）：
   **分母的语义错，比数字错更危险**。

**诚实边界**：宿主插件是进程启动时静态 import ⇒ 这一行**要等 DSH 宿主重启才出现**。
所以验证只能是离线的：tsc 0 错、新 smoke 9/9、全量 smoke 23/23、verify:commands 22/22。
**我在真机上还没看到过它**；重启后第一件事应该是核一眼这一行 + 渠道面板。
（渠道的"人工增删复核"按钮同样是"引擎侧已落、界面侧未做"。）

## §10.120 R6f：渠道人工维护接到界面上——smoke 在这步抓到两个真问题

引擎侧 R6d 已落四个写口，这一步补宿主代理（`plugin/src/channels.js`）与界面
（`KsChannelsPanel` 的"＋新增渠道"与行内"停用/改备注/删除"）。真正值得记的是**它抓到的两件事**：

**① 同一个 path 注册两次会互相覆盖。** 路由表按 path 去重、**后注册覆盖先注册**。
我第一版把"列表（GET）"与"新增（POST）"拆成两次 `register` ⇒ `GET /ks/channels`
**静默消失**——现场表现是"渠道页面突然空了"，而且**没有任何报错**。
一个 path 只能有一个 handler，内部按方法分派才是这张注册表的正确用法。
（smoke 的第一条断言就是"注册了几条路由"，它是被这条断言拦下的。）

**② ⚠⚠ 宿主侧"白名单筛字段"是错的——它与 R6d 明令禁止的失败模式一模一样。**
我原先按"界面不发明字段"的纪律，在宿主侧**丢掉**名单外的键，包括 `state`/`last_ok_at`
这类健康度字段。后果：引擎那句 loud 422（"这些是探针产出的字段，人工不能写"）**永远发不出来**，
界面拿到的是一个成功的 200 —— **用户以为写进去了**。这正是 R6d 花力气防的那件事，只是换了一层。
⇒ 改成 **判据归引擎**（它才是 `_WRITABLE`/`HEALTH_FIELDS` 的所有者）：宿主把 body **照转**，
让引擎出声拒绝；宿主自己只留"形状（JSON 对象）与方法"的把关。同理 `enabled` 类型也由引擎判。
**教训（值得单独记一行）**：*"缩小透传面"的直觉在写口上会把 loud 错误变成 silent 成功——
凡是"拒绝"的判据，只能有一个所有者，而且必须是能说清原因的那一层。*

**③ 既有守卫替我挡了一次。** `catalog-ui` 那条"可见文案里不许出现 markdown 粗体"当场拦下我新写的
`**人工录入 ≠ 已核实**`——JSX 不渲染 `**`，用户看到的是星号。这条 R4b/R6b 的教训被固化成守卫，
这次不用我事后发现。

**诚实边界**：与 §10.119 同——宿主插件是启动时静态 import，界面要等 **DSH 宿主重启**才出现；
本步验证全为离线：tsc 0 错、`npm run smoke` 23 段全过（含 channels-routes 26/26）、
`npm run verify:commands` 22/22。

## §10.121 R6g：把"覆盖率"量出来——顺带发现**只有 3 条渠道能用于今天的号**

目标里一直挂着"覆盖率未量化"这个缺口（R1 登记的）。这轮把它量了，**拆成四层**，
因为混着看就是 R1 的 G5/G6 那种虚高：

| 层 | 含义 | 数量 |
|---|---|---|
| L1 台账在册 | 我们知道它存在 | **131** |
| L2 有适配器代码 | 我们写了代码去抓它 | **13** |
| L3 有探针目标 | 我们真的会去敲它 | **102** |
| L4 **链上可达** | **巡检真的会用到它** | **3** |

**最重要的发现**：真库 6417 个号的 `select_chain` 并集**只有 3 条**
（`ndls`/`official_gb`/`govcn`，而且每个号都是这三条）⇒ **有适配器但今天一个真号都到不了它的有 10 条**
（`cssn`/`dbba`/`hbba`/`laws_db`/`mee`/`mem_gov`/`mohurd`/`std_samr_hb`/`ttzb`/`web`）。
反向是干净的：链上出现的都有适配器。

**为什么**（不是"适配器写错了"）：库里只有 `GB/T`(6130) 与 `GB`(287) 两个号段，
而 `first_route()` 的前缀规则对 `GB/T` 不命中（R6c-6 已量）⇒ 全库退化成兜底链；
那 10 条适配器对应的号段（HJ / T- / 法规 / 建工）**库里一个号都没有**。
它们是"为将来号段准备的"，但**今天一条都用不上**——而这在台账里被"已接线 7 条"的措辞掩盖了。

**"注册 ≠ 能力"的量化版**：L3(102) ≫ L2(13)——**能体检的渠道远多于能使用的渠道**；
体检只证明"站活着"，不代表"我们有解析器能从它拿结论"。
台账交叉印证：`seed_only` 113 条里已有 65 条 `ok`、13 条 `down`、11 条 `suspicious`（被探过），
而 `wired` 只有 **7** 条。

**五类覆盖**：6417 号 × 5 类里，**无候选的号数 = 0**（与 R6c-4d 独立吻合）；
中位候选数 2–3；声明能答某一类的渠道有 26–64 条，但**在链上的只有 2–3 条**。
⇒ "渠道覆盖尽可能全"在这张表上的含义**不是"再写适配器"**，而是
**让已登记/已适配的渠道按号段真正进链**——即 R6c-4 的"台账驱动链"。

**三条可执行结论**：① 台账驱动链（把"号段→可用渠道"从硬编码前缀变成台账里可维护的事实，
并把那 10 条按号段接回来）；② 对 `GB/T` 号段唯一能立刻提精度的是 R6c-6 定的"按类补探"；
③ **需要业主拍板**：库里没有 HJ/团标/地标号段的料——若行业面涉及，应先扩号段（那 10 条立刻有用）；
若只做 GB/GB/T，则应在台账里如实标注"为未来号段保留"，别让"已接线 7 条"给人覆盖率假象。

⚠ 边界：本轮只量了"**链**能不能到"（静态路由），**没有**量"渠道实际能不能答"（要真机请求）；
别把这两件事混起来读。

---

## §10.122 全项目大清洗（业主指令）：临时数据 / 旧文档 / 死代码 / 旧备份

业主原话：把项目清洗一遍，死代码、老文档、旧版本该删就删；**做之前把现状备份 ZIP，只保留一个最新的**；
文档只描述当下的，**不要出现"老版本需求留着"**（上一轮我据旧主计划 R 编号画愿景树，把老界面当成了今天的能力）。

**先备份**：`D:\AI\zcode-backups\zcode-clean-20260919-0212.zip`（827.2 MB / 43095 条目），
排除 `.venv / node_modules / .git / __pycache__ / .mypy_cache / .pytest_cache / .mimosa / .browser4-cli`。
备份目录里另外 3 份 9/13 的旧备份（2 个 `.bundle` + 1 个 `.zip`）按指令删除，**只留这一份**。

**删了什么**

| 类别 | 对象 | 量 |
|---|---|---|
| 临时数据 | `var/tmp/`（**每个独立验证者 b10–b42 都把自己的整份工作树副本解压在这里**）+ var 下诊断输出/小产物 + 4 类缓存 | **释放 2738 MB**（3127 → 389 MB） |
| 旧文档 | `REQUIREMENTS-v4.3.md`（旧主计划：Win11 单 exe 形态已不存在，且含 **2026-09-17 已被业主撤销**的 `[MUST NOT] 原始文档零外发`）、`INCIDENT-20260905-boot-failure.md`（0 引用）、`LLM_REQUIREMENTS_AND_SMALL_MODEL_FEASIBILITY.md`（0 引用） | 3 份 |
| 死代码 | vulture 报 6 处 → **真死代码只有 3 个没用的 import**（`pipeline.py:1357` `_pua_sep`、`office_roundtrip.py:81` `ElementTree`、`fewshot.py:14` `Counter`） | 3 行 |

**留了什么，为什么**

- `REALTIME_VALIDITY_VERIFY_RESEARCH.md`：**代码里 3 处引用它**当权威映射来源（`law_source/verify.py`、`catalog.py`）；
- `WSL2_VLM_BACKEND_DECISION.md`：活跃 OCR 工作流的决策记录；
- `LAW_SOURCE_PLAN` / `STD_STATUS_CHANNELS` / `CHANNEL_PROBE_REPORT`：ENCYCLOPEDIA §6/§9 明写「保留原文件」作工程证据；
- `DEVELOPMENT-HISTORY.md`：项目记忆（被 33 处引用）——**业主 2026-09-19 明确决定保留，不再列为删除候选**；
- `var/ocr-loop/`：**是活的**——`vlm_ocr.py` 最后修改 **2026-09-18 22:06**，约 50 个被跟踪 `.py` + `fixed_classes.json`；
  `.gitignore` 特意放行并写明理由：丢了会「**再次静默丢内容**」。故未动其数据目录。

**我造成并修好的一个错（教训）**：清 `var/` 时把 `var/mineru_cli_out/` 删了，而 `tests/test_pipeline.py:219`
用 `skipif` 依赖其中的 `GB30871-2022识别版_middle.json`（README:83 也写明"测试依赖"）——
**那会让一个测试从"运行"静默变成"跳过"（掉覆盖）**。已从备份 ZIP 逐路径恢复并验证存在。
⇒ **纪律：清 `var/` 之前必须先查代码里对它的 `skipif`／路径依赖。**

**发现一个真 bug（本轮未修，登记）**：`src/core/update/inspector.py:437-443` 的
「至少一个渠道给出确定性『查无』⇒ 判 `judged / gray / not_found`，与 hard-fail 严格区分」这一段
**永远执行不到**——上面 428 行已无条件 `return ProbeOutcome(kind="failed", …)`。
即**「查无此号」被错报成「失败」**。删掉这段等于把错误固化，故**保留原样并登记**，等业主定是否修。

**vulture 的 2 处误报（不能删）**：`office_roundtrip.py:131` 的 `lparam` 是 **Win32 回调签名必需参数**（ctypes 传两个参数）；
`ks_answer.py:220` 的 `retrieval_meta` 是 docstring 里明确「只影响 confidence_reasons、不改 tier 主体」的**刻意保留参数**。

**引用修复**：被删文档共 **13 处引用**（README×2 / INTRODUCTION / ENCYCLOPEDIA×4 / MATERIALS-PLANE-PLAN×2 /
DEVELOPMENT-HISTORY×3 / `research/plan-vs-reality.md`），全部改指向当下文档（`docs/VISION-TREE.md` 等）；
用脚本做**字面替换 + 「恰好命中一次」断言**，改完复核**残留 0**。顺手删掉 `scripts/make_handoff_zip.py` 里
**写死的旧基线数字**（"828 passed"）——它违反项目自己的规矩（INTRODUCTION §八：不重复维护写死的基线）。

**门禁（清洗后，全部零回退）**：pytest **2136 passed / 3 skipped**（与清洗前一致）· mypy **142 文件 0 错** ·
tsc exit 0 · plugin smoke 全链 PASS · verify:commands **22/22** · verify-engine-uvicorn **4/4**。

⚠ 边界：本轮删的是"**确证无引用**"的东西；`DEVELOPMENT-HISTORY` 与 `var/ocr-loop` 属**有意保留**（记忆与活工作流），
不是漏删。inspect 那个 bug 只是**登记**，未改代码。

## §10.123 交互重设计（业主指定，抄 WeKnora 的思路）+ 两次被叫停的过度延伸

业主原话（依次）：`/platform/knowledge-bases` 我很喜欢**你抄过来**，作为胶囊下拉里的「知识库管理」，
默认俩文件夹就是我们的**法律法规和标准**，用户可自建（如**公司制度**）；`/platform/agents` 的**结构思路**也可以抄
——不是要搞 agents，而是"制度修订/检查清单/合同审计这些功能**各自留一个设置窗口**，而不是全塞进设置按钮里"。

产出 **`docs/INTERACTION-DESIGN.md`**（八节，全部一手核实宿主契约与 WeKnora 源码）：
一问一屏 / 知识库入口 + 知识库管理二级页 / 能力页（一功能一卡一窗）/
「知识库管理」里的目录·标签·筛选·搜索 / 边界。**本轮全程只做设计，未动一行实现代码。**

### 两次过度延伸（都得业主叫停，记录以示边界感）

1. **把"升为一级 tab"当方案**：查证宿主 `ui-sidebar-right/contract/slots.ts` 后不成立——
   `sidebar.right.pane.tab` 是 `kind:'keyed'`，tab 是**按地址打开的记录**（`openResource`/`openTab`），
   注释写明"加一个类型是注册，不是改这里"。⇒ 我改口为「**定义成可按地址打开的 tab 类型**」，
   从回答/工具回执/命令一步直达。**业主当时没提，是我自己查证后自己改的。**
2. **把比方当成需求**（更严重）：业主说 WeKnora 那个 KB 详情页"**感觉是我们那个 PDF 浏览器旁边的目录的详细版**"，
   我**当成了要实现的目标**，把该节写成"查看器左列的列头升级"——**等于要去改业主明确要保留的东西**。
   业主随即叫停：「**我们的原件查看窗口 + 目录的形式还是要保留的，现在说的只是知识库管理的界面这样搞**」。
   ⇒ 已整节改正：查看器本体 + 左列三模式 + PDF 旁边那份本书目录**全部保留原样**；
   设计只落在**知识库管理界面**内。**教训：业主的比喻是在描述"像什么"，不是在下需求。**

### 业主一句定调，解掉了设计里最危险的一处

> 「**法规标准的几级目录应该是对应知识库文件夹的不同层文件夹名字**」

原设计里"知识库文件夹"是一个**新容器**，我正担心它会和既有两套集合（收藏夹 `bmf_`、材料项目 `prj_`）
变成**第四个重叠容器**。业主这句把它定死：**不存在"另一套层级"**——
`doc_catalog` 产出的分类路径**就是**文件夹路径，文件夹名**就是**分类节点名。
⇒ 自带两棵树是**视图**（无 id、禁改禁删），用户自建（如公司制度）是**真容器**（与两棵树平级、可建改删）。
⇒ **两棵树都从 `GET /documents/categories` 派生**，并写进硬约束：**不许另建 `kb_folders` 表描述层级**，
否则就有两套分类法，必然出现"树里在 P16、文件夹里在 P15"。

### 独立验证者 b44：6/8 成立，抓到**两处真错**

- **错1（法规树层数）**：我把法规树写成「L2 效力等级 → L3 领域 → 文档叶、**法规无 L4**」。
  一手复核 `doc_catalog.py:265-276`：注释写「法规树（三级体系）：效力层级 → **法律部门** → **业务领域** → 文档」，
  返回 `level3=dept`（法律部门 A~G）、`level4=domains[0]` 或 `"未细分"`；
  `server.py:933-937` 对**两棵树恒定输出四层**。⇒ **法规也有 L4**。
- **错2（改名处数）**：「PDF 查看器」我写"两处"，实为 **6 处**
  （`ksSidebar.ts:180` / `entry.ts:118` / `KsEvidenceTab.tsx:782,1445,1711,1777`，另 `:1056` 是注释）。

**根因值得记下来（本轮最有用的一条）**：错1 的根因**不是读错代码**，而是
**我抄了 `server.py:898` 的 docstring**（它自己就与代码不符），**把存量文档的错抄进了新文档**。
> 📌 **纪律：写"代码事实"时以代码为准，docstring 只当线索；docstring 与代码冲突时，冲突本身就是一条要登记的缺陷。**

⇒ 顺带**新登记一处存量缺陷**：`src/core/update/inspector.py:428` 无条件 return 使 `:437-443` 的
「查无」判定永不执行（§10.122 已登记）；本轮又添 `server.py:898` 的 docstring 与代码不符。
两处都**只登记、未改**，等业主定。

### 门禁

**纯文档改动，零代码触碰**（`git status` 全程只显示 `docs/INTERACTION-DESIGN.md`），
六道门禁不受影响，**本轮未重跑**——不声称"跑过"，只声称"**未触碰被测面**"。

⚠ 边界仍照旧：材料平面**未在真机跑过一次**（生产库无 `material*` 表）；渠道台账的人工维护路由在**真派发器**下 404
（`KS_CHANNELS_ITEM_PREFIX` 多尾斜杠，未修）；panel 侧写 UI 需**重启宿主**才可见；`doc_meta.withdrawn_date` 无数据通路。

## §10.124 交互原型：先做一个可点的 HTML 再动项目文件（业主提议）

业主原话：「**你用 HTML 给我先把你做的前端模拟展示一下**，里面的数据都用假数据或者占位符，
不用接入真的数据库或者建立真的什么逻辑关系，我就想体验好了再改项目文件，**这样会更省时间还是额外浪费精力？**」

**答：省时间，而且这轮尤其省。** 理由不是"原型好看"，而是**前两次都是在设计文字上被叫停的**
（"升为一级 tab"不成立；§10.123 那次把比方当需求、整节写错方向）。那两次往返的成本高于做一个 HTML。
真正的落地成本不在 HTML，而在**动宿主契约的 3 个 slot + 那个 128 KB 的 `KsEvidenceTab` + 六道门禁**——
一次性的重活，不该在做错方向时付。

**但它不能验证什么，也一并写清**：假数据验不出「6417 条真实数据下手感对不对」「筛选器是否真有用」
「宿主集成会不会崩」。⇒ 它验的是**形态 / 措辞 / 信息层级**，不是**契合度**。

**产出**：`docs/mockups/knowledge-ui-mockup.html`（43.7 KB 单文件、零依赖、全假数据、可直接打开）。
四个视图对应设计四节：① 知识库管理（自带两棵树 + 我建的卡片）② 知识库详情（目录+筛选+标签弹层+列表/卡片）
③ 原件查看器（**标注"保留原样"**，见 §10.123）④ 能力页（一功能一卡一窗，点开真出设置窗）。

**⚠ 数据层刻意与真实实现同构**：假数据是「扁平文档行 + 层级路径」→ 组树 → **判谓词后剪枝空枝**，
与 `KsFilesTab` 那段管线同构。这样业主在原型里看到的筛选行为，就是落地后的行为。
CCS 分类号/区间名**取自 `doc_catalog.py` 的真实全表**（非我编造），例如 `P15/19 工程抗震、工程防火、人防工程`。

**自查（不是门禁）**：抽出 `<script>` 跑 `node --check` **exit 0**；`<div>` 开闭 **110/110** 配平。
⚠ 这三条只证明"页面不自崩"，**不证明任何产品判断**。

⚠ 边界：原型是**一次性产物**，不会复用进项目（落地是 DSH 客户端的 React/TSX，不是这份 HTML）。
业主定稿后可整目录删除。**本轮仍未动一行实现代码。**

## §10.125 收藏→标签 / 批量操作 / 检索语法；原型改成「仿真 DSH 窗口 + 双配色」

业主一次给了十几条追加（在 §10.124 之后），并明确「**你的 UI 设计要和 DSH 保持相同风格，并且有深色浅色两套配色**」。
原型 `docs/mockups/knowledge-ui-mockup.html` 已按全部条目重做。

### 最划算的发现：「收藏 → 标签」**底账已经是标签的形状**（一手核实）

不需要新建标签系统。现有收藏夹在数据层**就是标签**：

| 现成的东西 | 位置 | 它就是 |
|---|---|---|
| `user_bookmark_folder(folder_id, folder_name UNIQUE)` | `schema.sql:170-175` | **标签**（名字唯一＝标签名唯一） |
| `user_doc_bookmark(doc_id, folder_id)` | `schema.sql:158-166` | 文档 ↔ 标签 |
| `user_bookmark(clause_key, folder_id)` | `schema.sql:147-155` | 条款 ↔ 标签 |
| `user_data.folder_scope(folder_id)` → `{doc_ids, clause_keys}` | `user_data.py:262-282` | **标签覆盖的文档集** |
| `ks_answer.py` 按 `folder_id` 过滤（`:645-648`、`:754`） | 引擎 | **「在标签下提问」已是引擎能力** |

⇒ 业主说的「搜索的时候可以选择在这个标签下面进行对话」**不是新能力**，是把既有「夹内提问」改名接出来。

**但一处硬约束挡着多标签**：`user_doc_bookmark` 有 **`UNIQUE(doc_id)`**（`schema.sql:165`）
——今天**一个文档只能属于一个夹**。业主的例子（一条标准既「公司相关」又「动火作业」）要求多标签，
⇒ **必须去掉这个 UNIQUE**（真迁移，单独一轮 + 脚本 + 老库兼容）。

**改名面（实测）**：`收藏` 在 plugin **145 处 / 9 文件**、src **100 处 / 13 文件**；
`bookmark-folders` 路由 `server.py` 39 处、`api.ts` 33 处。
⇒ 取舍：**内部表名/路由名先不动，只改用户看得见的词**（收益低、风险高的物理改名留到确有需要）。
这是**有意识的取舍，不是漏做**。

### 「搜内容」与 `+` / `-`：**今天是"包含"而不是"屏蔽"**（重要事实）

`src/core/text_utils.py:1374-1402` 的 `fts_match_expr()` 是 FTS5 MATCH 表达式的**唯一构造器**，
它现在：分词（jieba）→ **每词加引号**（裸 `-` 会被 FTS5 当语法，实测 `GB 30871-2022` → `no such column: 2022`，
且这类错**会被兜底 except 吞成"没有命中"**）→ 用 **`OR`** 连接。
⇒ **推论**：今天输入 `安全+半导体-冶金`，"冶金"**会作为正词被 OR 进去**——**是包含，不是屏蔽**。
业主想要的行为**今天不成立**，是真改动。改法只改这一处（唯一构造器），产出 `(正词组) NOT (屏蔽词组)`。
⚠ **两个坑**：① `-` 也是标准号的一部分 ⇒ 约定"`-` 后紧跟数字不算运算符"；
② **只有 `-词` 没有正词**时 FTS5 的 `NOT` **缺左操作数**（非法） ⇒ 策略待定，**先记下来，不假装不存在**。

**「搜内容」纯前端做不到**：标题/标准号可以在已下发的树上筛，但**正文检索必须打引擎**（FTS5 + jieba）
⇒ 需要一个**返回命中 `doc_id` 集合**的端点，前端拿它剪目录树。**这是一条真后端活**，与「零后端改动的四轴」性质不同。

### 其余条目（已写进设计文档 §八）

知识库页**去掉搜索框**（只留「＋ 新建文件夹」）· 自建夹与自带两棵树**平级**、加在后面 ·
详情屏加勾选/全选/**悬浮批量条**（已选 X 项 / 取消选择 / 批量打标签 / 移动到目录 / 批量删除）·
每行常驻**「＋标签」**· 行上补**发布/生效/废止**三日期 ·
**删掉"自动打的领域标签当筛选轴"**（业主明确不喜欢；⚠ 引擎的 `auto_tag.py`/`ccs_fetcher` **不动**，
`domain_tags` 仍被效力报告/义务/差距分析读着，只是不再当界面筛选轴）。

### 配色与风格：**照抄宿主真实 token，不是我自己调的颜色**

自查 `packages/client/ui-theme/src/styles/design-platform.css` 与 `ui-dockkit/.../dockkit.module.css`：
- 胶囊几何逐条照抄：`.tab` 高 **28px**、`border-radius:**12px**、`padding: 0 10px`、`min-width:80px`，
  条 `.tabStrip` `height:28px; gap:4px; padding:10px 6px 0 10px`；
  **活动胶囊 = 实心填充 `--dsw-alias-markdown-tag`，其余是裸文字**（注释原话）；
- 浅色在 `body`、深色在 `body[data-ds-dark-theme]`（**与宿主同构**），关键值如
  `markdown-tag` 浅 `rgb(241,243,245)` / 深 `rgb(44,44,46)`，`brand-primary` 浅近黑 / 深近白（所以主按钮是反色的）。

**原型自查（不是门禁）**：抽 `<script>` 跑 `node --check` **exit 0**；
`<div>` 开闭 **79/79**、`<script>`/`<style>` 各 1/1；
写了个小脚本对账 CSS 变量：**62 个定义 / 50 个引用，拼错的 0 个**（拼错的 token 会静默失效成"没有颜色"）。
⚠ 三条都只证明"页面不自崩"，**不证明任何产品判断**。

⚠ 边界：**我没有在浏览器里渲染过它**（只做了语法与 token 对账）——真机像素请业主打开确认。
本轮**仍未动一行实现代码**。

## §10.126 UI 真落地：开始页那张卡改成「知识库 + ▾」二级目录（真插件、真宿主机制）

业主先给了右侧栏的**真机截图**，指出我一直在错的地方建原型：
> 「图片是右侧边栏点开后的界面，下面那个 PDF 查看器变成知识库，然后又下拉菜单，菜单里是刚刚说的东西」
> 「你能不能把 DSH 的前端文件复制一份，然后直接按照真实落地的方式做 UI，只做 UI，后端接口留着不写。
>  这样就**百分百是最终视觉效果**」
> （我此前只交了 HTML 仿真，业主判为不合格："啥呀这是"。）

⇒ 本轮**不再做 HTML 仿真，直接改真插件**：`plugin/client/*`。因为"100% 最终视觉效果"只有一条路——
跑在真宿主里。

### 三处关键机制（全部一手，含官方文档依据）

1. **开始页那张卡是"槽位"，provider 可自己画。**
   官方 `ui-sidebar-right/README.zh.md:101` 原话：「开始页按当前生效的**定义 id** 渲染
   `sidebar.right.tab.guide.entry`… **provider 可按自己的定义 id 注册自定义卡片**；未注册时使用
   默认图标与标题按钮。侧栏负责宽度和排列，**自定义组件负责内部结构和交互**。」
   ⇒ 「新建终端」右边的 ▾ 就是这么来的（`ui-sidebar-terminal/src/client/TerminalGuide.tsx` +
   `index.ts:62` 的 `key: id`）。**照它做**，而不是自己发明。
2. **宿主 `Button`/`Menu`/`IconChevronDownOutline14` 是我们能 require 的。**
   官方 `docs/subsystems/client-modules.zh.md`：`external` 只管 "**non-baseline** module specifiers"；
   baseline 是 `packages/client/web/src/seed.ts` 里那 9 个（注释原话 "the **ONLY** entities the shell
   shares into the frozen module table"），`@deepseek-ai/dsh-client-ui-primitives` 在其中。
   ⇒ **下拉就是宿主那个 Menu**，风格同源而非我抄像素。
   ⚠ 但 `plugin/node_modules/@deepseek-ai/` 里**没有**它 ⇒ 直接 import 会让 `tsc` 红；
   故加 `ksHostPrimitives.d.ts` 用 `declare module` 自持类型（运行时是真货）——
   与 `ksSidebar.ts` 对 sidebar 契约"只声明我们调用的最小面"同一手法。
3. **样式只能运行时注入**：我们的 esbuild（`build-client.mjs`）**没有 CSS loader**，
   import `.css` 会产出**第二个文件**、而宿主只加载 `client.js` ⇒ 样式永远不生效。
   ⇒ `ksGuideStyles.ts` 运行时注入 `<style>`；颜色全走**宿主活 token**（`var(--dsw-alias-*)`，
   深浅色自动跟随）；卡片几何逐条抄 `TerminalGuide.module.css`（radius 24px / min-height 56px /
   padding 14px 20px / ▾ 宽 44px）。

### 改了什么

| 文件 | 事 |
|---|---|
| `KsKnowledgeGuide.tsx`（新） | 开始页那张卡：「知识库」+ ▾（知识库管理/文件导入/效力报告/渠道台账/打开 PDF 查看器） |
| `KsKnowledgePage.tsx`（新） | 知识库页 body：自带两棵树（层级名用 `doc_catalog` 的权威 CCS 表）+ 自建夹 |
| `KsKnowledgeGuideIcon.tsx`、`ksGuideStyles.ts`、`ksHostPrimitives.d.ts`（新） | 图标 / 注入样式 / 宿主 primitives 的最小面声明 |
| `ksSidebar.ts` | 新增 `ks-knowledge` 类型（`KS_KB_*`）、`actions.openTab`、guide 卡与 tab 标题**解耦** |
| `entry.ts` | 注册第二类型 + 第二 body + **guide 卡片槽位**（key 用**定义 id**，与 terminal 同法） |
| `scripts/smoke-client-entry.mjs` | 见下 |

**PDF 阅读器没删**：从"开始页一张卡"变成"知识库入口下的一个去处"（菜单最后一项），
符合业主"原件查看窗口 + 目录保留"的要求。

### 门禁抓到的两处**真缺陷**（不是门禁碍事）

1. **smoke 的 external 清单与真实构建不一致**：主构建 external `@deepseek-ai/*` 全量，
   smoke 只 external `['react','react-dom']`。它以前没暴露，因为我们对宿主模块一直只做**类型**导入
   （会被擦除）。⇒ 按它**已有的 pdfjs 桩做法**补 primitives 桩（同一理由：测的是 `apply()` 接线，不是渲染）。
2. **5 条断言写死了旧不变量**（"有且仅有一个类型"、"卡片标题必须等于 tab 标题"）。
   **没有放宽，而是重写成更强的**：类型断言 → **有序完整集合**；标题 → **各自钉死字面量**
   （任一侧误改都红，且"哪侧错"从输出一眼可辨）；并**给新类型补 4 条断言**
   （地址只认自己 / `canOpen` 拒外来 / 单例 / 不贡献第二个卡片）——否则门禁对新类型**是空的**。

### 门禁（全部零回退）

`tsc -p plugin/client` **0 错** · `npm run smoke` 全链 PASS（`client-entry` **94/94**，原有 90 条 +
新类型 4 条）· `verify:commands` **22/22** · `verify-engine-uvicorn` **4/4** ·
`mypy` **142 文件 0 错** · `pytest` **2136 passed / 3 skipped**（与基线一致）。

### ⚠ 边界（必须照实说）

- **要看到它得重启 DSH 宿主**：官方文档明写「生产环境的图完全不含 HMR 行；module host 自身从不监视文件」，
  插件 bundle 的 rev 只在**启动时组合**。重启会结束当前会话，故这一步留给业主定
  （或开 `pnpm run dev:web` 走 HMR，但不确定它是否同端口，不敢拿业主正在用的 GUI 赌）。
- **知识库页是纯 UI**：页首黄条写明「数据是占位，后端接口未接」，`＋ 新建文件夹` 是 **disabled**，
  导入/效力报告/渠道台账三项是**诚实的占位页**（真入口、空内容）。**一个引擎接口都没调。**
- **我没有在浏览器里渲染过它**（门禁证明的是接线与产物一致，不是像素）。

---

## §10.127 业主反馈「多了个浏览器按钮」→ 查证是官方新增；**但顺出一个我们自己的真 bug（开始页 order 撞号）**

### 业主的话

> 「有知识库了，但是多了个浏览器按钮」

（这句同时证明：§10.126 的卡片**在业主的真机上确实渲染出来了**。）

### 一、「浏览器」卡**不是我们造成的**

查 alpha.2 出货包 `packages/client/ui-sidebar-browser/`：

- `src/client/index.ts`：「Register the Browser type, **localized guide entry**, body, and title」；
- `src/client/definition.tsx`：`BROWSER_KIND = 'browser'`、
  `BROWSER_ID = '@deepseek-ai/dsh-client-ui-sidebar-browser'`、**`multiple: true`**、
  **`priority: 'builtin'`**、`guide: [{ id: 'new', order: 30, icon: IconGlobeOutline14 }]`。

⇒ 它是**官方新类型自带的应用内浏览器**：`openTab('browser', { params: { url? } })`，
**接受公网与 loopback 的 HTTP(S)**、**拒本地文件**（把本地文件让给 Document Preview）、自带 iframe 历史。
`ERRATA-alpha.2.md` §B1/§B6 早已登记过它 —— **只是业主先在自己的侧栏里遇见，比读到文档早**。

### 二、但它的 `order: 30` **和我们撞号了** —— 这是我们的 bug

`plugin/client/ksSidebar.ts` 的 `KS_GUIDE_ORDER_PDF` **原本也是 30**。而开始页按 `order` 升序排
（`tab-registry.refresh()`：`.sort((l, r) => l.order - r.order)`），**同号 ⇒ 先后只由注册顺序
（即 bundle 顺序）决定**。也就是说：**「知识库」与「浏览器」两张卡谁在上面是偶然的**，
一次无关的装配顺序变化就会让它翻转 —— 而 `Array.prototype.sort` 在 V8 里是**稳定的**，
所以它看起来"总是那样"，**更难被发现**。

⚠ 最值得记的是：我们当初写这个值时留的注释就是
「⚠ 这个值是**跨插件共享的排序空间**，上游新增条目时可能需要重排」——
**这句话在 alpha.2 应验了，而且是撞号（最坏的一种），不是简单的插队。**
"我当时想到了" 不等于 "我做了防护"：那条注释没有变成任何可执行的检查。

**修法**：`30 → 25` —— 夹在「新建终端」(20) 与「浏览器」(30) 之间，既保留原需求
（我们的入口在终端下面），又**不与任何出货条目同号**，先后变成**确定的**。
实测出货占号：`ui-sidebar-files` **10** / `ui-sidebar-terminal` **20** / `ui-sidebar-browser` **30**。
`plugin/scripts/smoke-client-entry.mjs` 的断言同步**收紧**（不是放宽）：
`order === 25 && > 20 && < 30`。

并把规矩写进 `docs/research/dsh-official/REALIGN.md` §六：**每次升级 DSH 都要跑**

```powershell
git grep -n "order:" <new-ref> -- packages/client/ui-sidebar-*
```

### 三、同批更正两处**我自己写错过的**边界（不留假话在手册里）

`REALIGN.md` §六是"下次升级照着做"的手册，里面两句话**已经被证伪**，本轮一并改掉：

| 原话（错） | 现在（对） | 证据 |
|---|---|---|
| 「重建后**必须重启 DSH 宿主**（生产模式无 watcher）」 | **插件改动是热重载的**；只有 bootstrap / 静态装配库 / shell 要重建页面 | `@deepseek-ai/dsh-client-hmr` 自 alpha.1 即在 `packages/bundle/web-app/cordis.patch.yml`（alpha.1 :166-167 / alpha.2 :167-168）；alpha.2 新增 `### Live graph reconciliation`（SSE、逐插件 `entry.refresh()`、CSS 在旧 disposer 排空后重注） |
| 「顺手该做的：……**补 `peerDependencies`**」 | **不要补**（我们不补就是对的） | alpha.2 把 Desktop 那条校验**有意移除**：「does not recursively check peer versions, duplicate packages, linked packages, or ancestor dependency resolution」 |

⇒ 这两条都属"我说过、后来被证伪"，按本仓纪律**必须留下痕迹**（`ERRATA` §I/§D5 有完整证据链），
不能悄悄删掉。

### 四、把"那句注释"变成**升级时真会跑的一步**（并当场证伪过它）

根因不是"我选了 30"，而是**那句警告只是注释**：没有任何东西会在升级后去核它。
所以把它加进 `scripts/dsh-docs-delta.ps1`（升级时本来就跑的那个只读脚本）**第 7 节**：
扫出全部出货 guide 条目的 order，与本仓 `plugin/client/ksSidebar.ts` 的
`KS_GUIDE_ORDER_PDF`（**从源码读，不另抄一份**）比对，撞号打 ⛔。

写这个检查时**我自己先错了两次**，都记下来（都属于"检查装成通过"这一类）：

| 错误 | 后果 | 修法 |
|---|---|---|
| 把两次 `-match` 串进一个 `-and` 条件再读 `$Matches` | `$Matches` 只剩**最后一次**匹配的组号 ⇒ 取到的是 order 而不是路径 | 拆开顺序 match |
| 用 pathspec `'packages/client/*/src/client'` | git 的 wildmatch 里 `*` **不跨 `/`**，**一个文件都匹配不到** ⇒ 输出"出货占用："**空集**，脚本却报 `✅ 未与任何出货条目同号` | 改成全扫 `packages/client` + 自己按 `/src/client/` 过滤 |

第二条尤其值得记：**它把"什么都没查到"渲染成了"检查通过"**。现在脚本遇到扫描结果为 0 会明确说
「很可能是**检查本身坏了**（不是"没有"）」，不当作通过。

**然后真的证伪了一次**：临时把我们源码里的值改回 30，脚本如期打印
`⛔ **撞号**：出货条目也占 30`；改回 25 后 `✅ 未与任何出货条目同号（出货占用：10, 20, 30）`。
（改完立刻 `git checkout --` 还原，已确认源码是 25。）
—— **一个从不报警的检查等于没有**，所以这一步不能省。

### 门禁（本轮改动：1 个脚本 + 2 个源文件 + 3 篇文档）

`tsc -p plugin/client` **0 错** · `client-entry` smoke **94/94** · `npm run smoke` 全链 PASS ·
`verify:commands` **22/22** —— **零回归**。
`plugin/client.js` 重建后 sha256 前缀 `C1CF7946DAC4DAC1`（1348327 字节；改前 `14BB55F7DABCC970`）
—— 与改前的字节数相同、但**哈希不同**，符合"仅 `30`→`25` 一位数字"的预期。
`dsh-docs-delta.ps1` 全流程重跑成功，其它节未受影响。

### ⚠ 边界

- **我仍未在浏览器里渲染过**：顺序修复的正确性依据是"官方 `order` 升序 + 我们已独占 25"这条
  **读码得出的事实**，不是我看了一眼真机。业主刷新/重开侧栏后应能看到「知识库」在「新建终端」下方、
  「浏览器」上方 —— **若位置仍不对，那是我的推断错了，请告诉我**。
- 本节只证明**排除了一个随机性**，**不证明**卡片视觉与官方逐像素一致。

---

## §10.128 独立复核**打回了我两处说法**（其中一处是我自己写的"更强"站不住）

按纪律对 §10.127 派了独立复核子代理（它自己读码、自己实跑、还独立重建了一次产物）。
结论：**7 条里 4 条 CONFIRMED、3 条 PARTLY**，而 PARTLY 的那三条里有两处是我的**说法**问题，不是实现问题：

### 一、我说 smoke 断言「收紧（不是放宽）／更强」—— **形式上错的**

旧断言 `order === 30 && > 20 && > 10` 接受集合 `{30}`；新断言 `order === 25 && > 20 && < 30`
接受 `{25}`。**两者都是单点集且不相交**，谁都不蕴含谁 ⇒ **不构成"更强"**。
实质上的改进是"**更贴题**"：新增了 `order < 30`（压在新增的浏览器下面）这个**真约束**，
去掉了 `> 10` 这个**空洞**约束（任何 ≥10 的值都满足它，它从来没排掉过什么）。
⇒ 措辞已改；后续不再用"更强/收紧"描述**换了目标值**的断言。

### 二、第 7 节「撞号打 ⛔」—— 它**当时 `exit 0`**，是提示而不是门禁

这是复核里最实的一击：**一个不会失败的检查挡不住任何东西**。我明明刚写过
"一个从不报警的检查等于没有"，却在同一条里造了个"报警但退出码 0"的东西。
⇒ 已改：撞号 / 空扫 / 读不到我们的值 ⇒ **退出码 1**；并在结尾明确写
"**退出码 0 只表示第 7 节没发现问题**，前面各节的 ⛔ 仍是提示"（免得把 0 当全绿）。
另外它的扫描面从 `packages/client` 放宽到 **`packages` 全树**（复核是用全库
`git grep 'guide: \['` 才确认"确实没有第四条"的），并排掉 `.spec/.test`。
**改完两个方向都实测过**：正常 ⇒ `exit 0`；临时改回 30 ⇒ ⛔ + `exit 1`；还原后源码是 25。

### 三、我说的"先后变成确定的"要加限定

脚本只能扫**出货树**；真正的排序空间还包括**本插件的 25** 与 profile 里**第三方插件**贡献的条目。
⇒ "未与出货条目同号"**只覆盖出货树**，不构成"全局无冲突"的证明。已写进脚本注释与 `ERRATA` §K。

### 复核**证实**的部分（可以当真）

- `plugin/client.js` 与"从当前源码现构建"**逐字节相同**（复核自己拷了一份带真实 `node_modules`
  的 `plugin/` 到 %TEMP% 重建，sha256 两边都是 `C1CF7946…`）—— 它没信我们的门禁，而是重建了一遍；
- `tab-registry.ts:402-407` 的 `.sort((l, r) => l.order - r.order)` **升序且无并列打破规则**；
  同一文件 `candidates()` 是**有** `|| left.order - right.order` 的 ⇒ 说明作者在别处想到了并列，
  这里没有。**并列时保持注册顺序**是 `Array.prototype.sort` 稳定性给的（ES2019+），
  **不是这段代码声明的保证**；
- 出货树里**确实只有三条** guide 条目（10 / 20 / 30），全库扫过，没有第四条。

---

## §10.129 业主问「官方文档存记忆干完了吗」—— **没有**；本轮把它干完了（171/171 逐字核对）

### 一、先查事实，不凭记忆答

`hindsight_diagnose` 给库名，再直连 `GET /v1/default/banks/coding-agent::zcode/documents` 枚举：
**27 份**文档里与 DSH 官方文档有关的只有 —— 1 份导航（`dsh`）+ 8 份摘要分片 +
**2 篇逐字原文（都是手抄）**+ 若干更正件。⇒ **171 篇英文正本里 169 篇未入**。

我此前把这个状态记成"内容层全部覆盖、原文层 2/167"，**听起来像完成了**。
业主问的是"干完了吗"，正确答案是**没有**：分片是**二次加工**，而业主当初的原话是
「**不仅要存入记忆，还要按照人家文档的结构把原文存进去**」——**原文层才是他要的那件事**。

### 二、当时卡住的两条理由，只否掉了"手抄"

① 子代理不能写记忆；② 手抄 2.6% 失真。**这两条都只说明"别手抄、别派子代理抄"**，
并不意味着"做不到"。读插件自己的 dist 找到了它用的写入协议（**不是猜的**）：

```
POST http://127.0.0.1:8888/v1/default/banks/<bank>/memories
{ items: [{ content, context, document_id, tags, strategy, observation_scopes }], async: true }
```

⇒ 于是写了 `scripts/ingest-dsh-docs-into-memory.mjs`：**内容从磁盘按字节读**，
既不经过子代理、也不经过我的上下文 ⇒ **结构上不可能抄错**。

### 三、结果：171/171 **逐字一致**（不是"长度一致"这种必要条件）

- 幂等：先比长度，一致就跳过（重跑显示"要灌 0 篇"）；
- `update_mode` 默认 `replace` ⇒ 那 2 篇手抄件**用原 id 原地覆盖**，**不留两份同文**
  （库里文档数 27 → 196，与"167 新增 + 1 替换"的账**对得上**）；
- 对账从"比长度"升级成 **`GET /documents/<id>` 取回 `original_text` 算 sha256 与磁盘比对**：
  **171/171 逐字一致，异常 0 篇**。账本 `docs/research/dsh-official/INGEST-LEDGER.md`（每篇带源 sha256）。

**手抄确实错了两篇，而且长度就能看出来**（这是"手抄不可信"最硬的证据）：
`AGENTS.md` 手抄 10,828 / 磁盘 10,761（**多 67 字符**）；`web-styling.md` 手抄 4,778 / 磁盘 5,088（**少 310 字符**）。

### 四、过程里我自己错了一次（**凭记忆写 id**）

覆盖表里我把 `docs/AGENTS.md` 的目标 id 凭记忆写成 `dsh-docs-agents-md-the-documentation-standard`，
而库里真 id 是 `dsh-docs-agents-md-**agents-md-**the-documentation-standard`（`agents-md-` 重复）。
后果：**"原地覆盖"静默变成"新增一份"** —— 库里会同时留手抄版和字节版**两份同文**。
是干跑输出里"该覆盖的只列出一篇"暴露了它。⇒ 现在凡涉及 id **一律从库里逐字读**，
并把这次教训写进脚本注释与 `REALIGN.md` §五。

### 五、⚠ 边界（别把这次的成果说大）

- **没入的语料**：`.agents/notes/` 决策记录 **2056 篇 / 约 14.3 MB**（分片 G 只触及与客户端 UI
  有关的部分）、`docs/**/*.zh.md` 中文译本约 158 篇。业主这次批的是"171 篇英文正本"，**就只做了这个**。
- **逐字一致证明的是"库里存的正文 = 磁盘那份"**，**不证明**服务端抽取出的事实条数/质量正确，
  也不证明检索时一定能召回。
- **8 份摘要分片没有被这次取代**：它们是"导航 + 提炼"层（带 file:line），原文层是"引用"层，
  两层职责不同；但分片是按 alpha.1/alpha.2 视角写的，**逐字引用一律以原文条目/磁盘为准**。
- **我没在浏览器/UI 里验证任何东西**——本轮与 UI 无关。

### 六、导航件 `dsh` 的更新（业主批准的范围，只做了这一条）

`dsh` 是"该用什么/哪里有坑"的导航件，但它是按**原文不在库里**写的。现在给它**加**了两节：
开头一节讲**原文层 vs 提炼层**（171 条 `dsh-docs-*` / 账本 / 脚本 / 那 2 篇手抄件已被字节级覆盖 /
`.agents/notes/` 与 `.zh.md` **仍未入**），末尾一节列**对本条自身的更正**（167→171；
§2.5「布局仅内存」作废 + 新权威；§七「分片 D/F/G/H 尚未回流」已不成立；
peerDependencies 与"必须重启宿主"两条的撤回）。

⚠ **旧正文必须字节保持**：那 8,267 字符是我**亲读第一手结论**，手工重打=又抄一次。
所以写了 `scripts/update-dsh-navigation-entry.mjs`：GET 回 `original_text` → **原样拼**新节 →
POST 写回（`document_id: 'dsh'`，`update_mode` 默认 `replace`）→ **校验旧正文仍是新正文的子串**。
结果 8,267 → **10,672 字符**，`长度一致=true　旧正文逐字仍在=true`，op `completed`。带看门标记，可重跑。

（写这个脚本时我又踩了个同类的坑：模板字符串里漏转义一个反引号 ⇒ 语法错误。**"抄写类"错误的重犯率
确实高**——这正好又印证了"别手抄、用字节读"这条纪律。）

### 七、⚠ 入库带来一个**新的运行限制**：问得太宽的 `reflect` 会 500

入库后试一个**又宽又多问**的 `reflect`（"原文在不在库里/多少篇/该查哪里 + 布局是否仅内存"）：

```
reflect 500 {"detail":"LLM output exceeded token limits (openai/deepseek-flash, scope=reflect).
             Input may need to be split into smaller chunks."}
```

**先分清是不是"reflect 坏了"**：换一个**窄**问题（"DSH 侧栏的布局在刷新后会怎样？"）⇒ **正常且质量很高**，
它自己就召回了刚加的更正（"布局仅内存"作废、权威换成 `2026-09-14-sidebar-layout-provider-recovery.md`）。
⇒ 结论：**reflect 仍然可用；失败的是"一次问太多"** —— 语料从 27 份涨到 196 份（含 2.9 MB 原文）后，
宽问题的**合成输出**更容易超上限。

- 这是**入库的副作用**（我造成的），不是 Hindsight 坏了；写在这里以免以后误判。
- 用法上的应对：**把大问题拆成几个窄问题**（官方报错原文也是这个建议）。
- ⚠ **不确定的部分**：我没有证据证明"就是入库导致的"（也可能是这条查询本身要求输出太多），
  故只说"观察到这个限制"，不说因果已定。

---

## §10.130 知识库页按业主 13 条真落地 + 清两处官方违规（并记我自己犯的两个错）

业主已在 §10.126 之后给了 13 条追加要求（原话见 §10.125/§10.129 的那段引述），
本轮把它们**落进真插件**（仍是纯 UI，后端未接）。逐条对照表写进了
`docs/INTERACTION-DESIGN.md` §〇（**那节是"现在真跑着的是什么"，以代码为准**）。

### 一、页面结构（三段式 + 页内二级 tab）

「文件 / 标签」二级 tab；顶部只有一个「＋ 新建」（下拉：新建文件夹占位 / 导入文件跳真入口）；
文件视图 = **目录轨 | 文件列表 | 详情**；标签视图 = 标签行（计数 + 覆盖哪些文件夹 + 在此标签下提问）
+ 检索语法输入（当场回显解析结果）。

**交互是真的**：勾选/全选/批量动作（批量打标签、移动到目录、批量删除）/行内加标签
都作用在 React 状态上，所以业主可以直接点着体验（他要的就是"体验好了再改项目文件"）。
但数据是页面内占位常量，**一个引擎接口都没调**，页首黄条写在界面上。

### 二、检索语法（本页唯一的真逻辑，抽成独立模块）

`plugin/client/ksSearchSyntax.ts`：`+` = 并且、`-` 前缀 = 屏蔽。两个坑都处理了：
- **标准号里本来就有 `-`**：`GB 30871-2022` 若被当成"屏蔽 2022"就会**静默搜不到**。
  ⇒ 规则：`-` **只在前面不是数字时**才是屏蔽符（`半导体-冶金` 前是「体」⇒ 屏蔽；
  `30871-2022` 前是「1」⇒ 留词里）。冒烟有 10 个用例逐例钉住，其中包括这一条。
- **全角符号**（`＋－　`）先归一化 —— 本仓有过全角号导致请求发不出去的真事故（§10.106）。

### 三、清掉两处官方违规（都是"写错不报错、只在真机静默发作"类）

| 处 | 问题 | 修法 |
|---|---|---|
| `entry.ts` 结尾 | `export default { apply, inject }` —— 官方 `postmortem/0001` 根因 #1：cordis Loader 的 `unwrapExports` **优先取 `.default`**，会把**整个命名空间丢掉**（`inject`/`name` 消失），插件在不含注入服务的 fiber 里跑，第一个 `ctx.xxx` 就抛 "cannot get property … without inject"；而**单元测试全绿**（它们绕过真实 Loader）。我们那个对象恰好带了 `inject` 所以没炸，但仍然丢命名空间，等于**把事故推迟**。 | 删掉那一行（官方修法），并在原处留注释说明**别再加回来**；冒烟加断言钉住 |
| `ksGuideStyles.ts` | 3 处 `1px solid var(--dsw-alias-border-*)` —— 官方硬规定中性边框统一 **0.5px**；另外我给 `.ks-batch` 写成"中性边框 + elevation 阴影"，而官方明令 **"Never pair a `--dsw-alias-border-*` border with an lv/elevation shadow"**（描边由阴影自己画，颜色用 `--dsw-elevation-stroke-color`） | 全改 0.5px；`.ks-batch` 改成官方写法（`border:0` + stroke 变量 + `box-shadow:var(--dsw-elevation-prominent)`） |

⚠ 顺带核了 token 名：`--dsw-elevation-panel|prominent|soft` **都存在**（定义在
`ui-theme/src/styles/gradient-shadow-text.css:29-33`），但 `--dsw-elevation-*` 在
`design-platform.css` 里**一个都没有** —— 我一开始就是在那个文件里 grep 的，差点得出"这 token 不存在"的错结论。
**这类"名字写错不报错、只是静默没样式"的地方，必须去定义处核，不能靠 grep 一个文件没找到就下结论。**

### 四、顺手修掉两个真 bug（都在我自己的代码里）

1. `ksHostPrimitives.d.ts` 把 Button 的 `variant` 声明成 `'secondary' | 'text'` —— 宿主**没有这两档**
   （官方 `Button.tsx` 是 `primary|ghost|outline|toolbar`）。写成别的**不会构建失败**
   （external，esbuild 不校验命名导出），只是 `css[variant]` 取到 `undefined` ⇒ **静默没有填充**。
   现按源码改成 4 档，并补 `Checkbox`/`Tag`/`Pill`/`Input` 的**精确 props**（都是我逐个读源码抄的）。
   冒烟加一条：我们 11 处 `variant=` 用法必须全在那 4 档里。
2. 知识库页原版用 `node.name` 当展开状态的键，而「宪法与行政法」在两棵法律分支下**重名**
   ⇒ 点一个会把另一个一起展开、文档还会挂到错误分支。改成**全路径 key**。
   （这正是官方那句 "Localized display text is never an identity" 的现场版。）

### 五、冒烟 94 → 122（+28 条），并**两个方向都验**

新增：无 default 导出；Button variant 只在官方 4 档；无 1px 中性边框；无"边框+阴影"非法配对；
检索语法 10 例；13 条需求在场（删任一条即红）。
**证伪测试**：把 `export default` 加回去 ⇒ 该条 FAIL、`120/122`、**退出码 1** ✓。

### 六、⚠ 我自己在这一轮犯的错（两个，都记下来）

1. **`git checkout -- <file>` 吃掉了我未提交的故意改动**。
   做上面的证伪测试时我用它还原 `entry.ts`，但**那个文件的修改还没提交**
   ⇒ `checkout` 恢复到**已提交**版本，把我刚做的"删 default 导出"一起删了。
   教训：`git checkout --` 只能用于"丢弃不想要的改动"，**不能用来还原一次临时证伪**；
   要么先提交，要么手工反向编辑。已重做并核对产物字节数一致（`1376102`）。
2. **同一个错误犯了三次：在模板字符串里写反引号**（`ksGuideStyles.ts` 的 CSS 就是模板字符串）。
   第一次是 `update-dsh-navigation-entry.mjs`，第二次是 `ksGuideStyles.ts` 的注释，第三次是同一文件的另一条注释。
   三次都是 `tsc`/Node 语法错误挡下的（**这点算运气好**：若是运行时才炸就麻烦了）。
   ⇒ 结论：在"字符串里再嵌字符串"的地方，**别用反引号做排版**，用「」或引号。

### 七、⚠ 边界：**我仍然没有在浏览器里渲染过这一页**

我试了三条路，都不通或不划算，如实记下来免得以后重复投入：

1. **冒烟**：证明的是"接线正确 + 产物与源码一致"，**不是像素**（jsdom 本仓未装，
   收编它要先决定依赖策略 —— 这条边界 §10.99 就写过了）。
2. **从正在用的 GUI 取服务端 bundle 比对**：`http://127.0.0.1:3080/plugins/ks-dsh-plugin/client.js`
   与 `/plugin/...` 都是 **404**；取首页根路径返回 **401（要鉴权）** ⇒ 非侵入式取不到。
3. **装浏览器自动化（`browser4-cli`）**：需要全局 CLI + JVM 后端（约 200 MB，首次构建 1–3 分钟）。
   为一个**占位 UI** 装这套，属于业主明确叫停过两次的"过度延伸"，**不做**。

⇒ **像素级结论只能由业主在真机上看**（他本来就说了"我就想体验好了再改项目文件"）。
我能给的是：产物已重建、门禁全绿、`tsc` 0 错，以及一份"哪条需求落在哪段代码"的对照表。

### 八、"深浅两套配色"的真实状态：新 UI 已达标，**老面板有 115 行写死颜色**

业主明确要过「**深色浅色两套配色**」。查证结果分两半，别混为一谈：

- **新 UI（`ksGuideStyles.ts` + `KsKnowledgePage.tsx`）已达标，且是"结构性达标"**：
  只用宿主原语 + 活的 `--dsw-alias-*` token，**一个写死色值都没有**。
  机制一手核实：`ui-theme/src/styles/design-platform.css` 里 alias token 恰好两套 ——
  `body {…}`（浅色，:156）与 `body[data-ds-dark-theme] {…}`（深色，:253）
  ⇒ **主题一换，token 自己变**，我**不该也不需**写两套色值（写了反而会与宿主主题打架）。
- **老面板还有 115 行写死颜色**（逐文件基线，2026-09-19 实测）：

| 文件 | 行数 | | 文件 | 行数 |
|---|---|---|---|---|
| `KsSettingsSection.tsx` | 48 | | `KsMaterialsPanel.tsx` | 5 |
| `KsIngestPanel.tsx` | 22 | | `KsScopeChip.tsx` | 5 |
| `KsReportPanel.tsx` | 16 | | `KsBookmarksTab.tsx` | 3 |
| `KsEvidenceTab.tsx` | 12 | | `KsChannelsPanel.tsx` | 3 |
| `KsFilesTab.tsx` | 1 | | **合计** | **115** |

#### 为什么这一轮**不改**它们（写清楚，免得后人以为忘了）

1. 约 130 处**颜色出现**里，只有 ~20 处能从文件自身推出 token
   （那些文件里已有 `var(--dsw-alias-X, #字面)` 的回退声明）；**其余 ~110 处需要语义判断**
   （哪个是危险红 `#c0392b`、哪个是警告黄 `#b8860b`/`#9a6700`/`#d99000`、哪个是成功绿 `#2e7d32`）。
2. 其中还有 `#c0392b55` / `#b8860b55` / `#88888855` / `#2e7d3255` 这种**带 alpha 的 8 位色**：
   换成 token 会**丢掉透明度**（没有"33% 危险红"的 token），盲改会让半透明边框变实心
   —— 那是**把深色改得更糟**。
3. 这些面板**本来就在交互重设计里等着被重建**（`docs/INTERACTION-DESIGN.md`：能力页/导入页/报告页
   都在"重新做"的清单里）；现在花力气改它们的配色，大概率是**给要拆的墙刷漆**。
4. 最要紧：**我看不到像素**。改错了不会有任何门禁报警，业主也不在旁边。

⇒ 所以这一轮只做**棘轮（ratchet）**：`client-entry` 冒烟里新增一条断言，
**每个文件的写死颜色行数不许超过上面的基线（只许减）**。新增文件默认基线 0
（即新代码**一律不准**引入写死颜色）。**两个方向都实测过**：临时加一个含 `#ff0000` 的新文件
⇒ 该条 FAIL（`ZZTempProbe.tsx: 0 → 1`）、`122/123`、**退出码 1**；删掉后回到 `123/123`、退出码 0。

⇒ 结论：**"两套配色"在新 UI 上是真的；在老面板上是"已知且被冻结的债务"**，
等那些面板重建时一并清掉（棘轮保证它不会先长大）。

---

## §10.131 业主追问「这俩问题解决了吗」—— ① 查到了真根因并修好；② zh 全量 + 决策记录 10 篇已入（并更正我记错的规模）

### ① `reflect` 500：**根因是输出上限 4096，不是"问得太多"**

我上一轮只做到"观察 + 绕法（把问题拆窄）"，**没查根因**。这轮查到了，而且它**不是**我猜的那样：

从服务自己的 `GET /openapi.json` 读到 `ReflectRequest`：
- **`max_tokens`，默认 4096**，描述原文 "**Maximum tokens for the response**"；
- 插件工具 `hindsight_reflect(query)` **只暴露 `query`** ⇒ 永远吃默认值。

⇒ 所以当**回答**超过 4096 token 时，服务端**选择报错而不是截断**。报错里那句
"Input may need to be split into smaller chunks" **是误导** —— 问题不在输入。

**决定性实测**：把此前 500 的那个宽查询，用 `max_tokens: 8192` 直连重打 ⇒ **成功，47 秒**，
而且答案质量很高（它自己指出"171 篇中仅 2 篇有逐字原文"这条**已过时**、应以"已完成"为准）。

**做成可复用的脚本** `scripts/hindsight-reflect.mjs`：可指定 `--max-tokens`、`--budget`、
`--tags`（按标签域圈定范围）。它还在 500 时**直接印出"这是输出上限撞了"**，
免得下次又被那句"拆小输入"带偏。

### ② `.zh.md` 与 `.agents/notes/`：**先更正规模，再动手**

我此前记的规模**两个都不对**（都是从分片转述里抄的，没实测）：

| 语料 | 我记的 | **实测（alpha.2，`git ls-files`）** |
|---|---|---|
| `docs/**/*.zh.md` | ~158 篇 | **166 篇 / 2.7 MB** |
| `.agents/notes/*.md`（非 zh） | 2056 篇 / 14.3 MB | **1105 篇 / 7.6 MB** |

**做了什么**（脚本已泛化：新增 `--root` / `--match` / `--id-prefix` / `--tag`，
账本与状态文件**按语料分开**，不再互相覆盖）：

| 语料 | 结果 | 标签域 | 账本 |
|---|---|---|---|
| `docs/**/*.zh.md` 中文译本 | **166/166 逐字一致，异常 0** | `dsh-official-docs-zh` | `INGEST-LEDGER-docs-zh.md` |
| 分片 G 依赖的 10 篇客户端/UI 决策记录 | **10/10 逐字一致，异常 0** | `dsh-notes-client-ui` | `INGEST-LEDGER-notes-client-ui.md` |

库里文档总数 **196 → 372**。**并验证了"按域检索"真的可用**：
`node scripts/hindsight-reflect.mjs --tags dsh-official-docs-zh "客户端插件的加载模型…"`
⇒ 它从 `client-modules.zh.md` 等**中文译本**里取原文作答并列出依据。
（这一点很要紧：中英两份同文如果不分域，会互相稀释召回。）

**没做的事（写明理由，不是忘了）**：`.agents/notes/` 其余 **1095 篇 / 7.6 MB 未入**。
理由是**召回质量**而非成本：决策记录是 **DSH 内部工程决策**，大部分与 KnowledgeStation 无关，
全量入库会把我们的检索**淹没在 DSH 内部细节里**。现在它是**一条命令**（`--root .agents/notes`
+ `--tag dsh-notes`，约 30 分钟后台），且因为带独立标签域，**随时可圈进来、也可排除掉**。
⇒ 需要"为什么这么设计"时再灌，或先灌某个子目录。

### ③ 泛化脚本时我自己又犯一个错（护栏当场逮住）

把"排除 `.zh.md`"的逻辑留在了**遍历函数**里，而新的过滤归 `--match` 正则管
⇒ `--match '\.zh\.md$'` **永远扫不到东西**、一篇都选不中。
**幸好"空集即报错、绝不当成通过"那条护栏是前一轮加的**，它直接打印
「一篇都没扫到 —— 这几乎肯定是**扫描本身坏了**，不是"没有文档"」并退出 1。
否则这次就会安静地"灌 0 篇还报成功"——正是我一直在批的那种失败模式。
（另有一个小坑：`.gitignore` 里 `$` 在 CRLF 下不匹配 `\r` 前的位置，替换静默没生效，加 `\r?` 才成。）

---

## §10.132 关掉"我从没渲染过这一页"：**渲染级**冒烟（真 jsdom + 真 React + 真事件）

§10.130 第七节记着三条"验不了"的路。这轮找到第四条，而且**不用给业主加任何依赖**：
`jsdom` 与 `react`/`react-dom` **已经躺在 DSH 检出里**
（本机实测 `deepseek-harness/node_modules/jsdom` v29.1.1、
`packages/client/web/node_modules/react{,-dom}` v18.3.1）⇒ 用 `--harness` 指过去即可。

### 新增 `plugin/scripts/smoke-kb-page-render.mjs`（13 条，已接进 `npm run smoke`）

真 DOM、真 React、真事件，断言的是**行为**而不是字符串：
真渲染出内容 · 运行时样式被注入 · 勾选框数 = 文档数 + 1 · 每行都有常驻「＋标签」·
点全选 ⇒ 批量条出现且显示「已选 4 项」· 批量条五项俱全 · **点批量删除真的把行删到 0** ·
切自建夹列表跟着换 · 详情含三个日期且是**真值**（`2025-01-06` 这种，不是破折号）·
标签视图跨文件夹 · **检索语法当场回显** · 本页没有搜索框。

这补齐了 `smoke-client-entry.mjs` 里自己承认的缺口：
「这仍是**字符串级**检查…挡不住"条件后面偷偷加 `&& false`"——那种要**渲染级**用例。」

### 写它时踩的两个坑（都属"看起来该work的东西不work"）

1. **两个 React 副本** ⇒ `Invalid hook call` + `Cannot read properties of null (reading 'useState')`。
   成因有两处：只用 `nodePaths` 解析可能落到不同路径；而且我为了拿 `act`
   去 import 了 `react-dom/test-utils`，**那一下就把第二份 react/react-dom 引进来了**。
   修法：**alias 把 react/react-dom 钉成绝对路径的唯一一份**，并且**完全不用 `act`**
   （`createRoot` 的更新本来就会刷到 DOM，给一个 tick 即可，代价是每次交互后 `await flush()`）。
2. **受控 input 直接赋 `.value` 不触发 `onChange`**：React 的 value tracker 判定"没变化"。
   表现是"检索语法没解析出来"。修法：走**原生 setter**
   （`HTMLInputElement.prototype.value` 的 descriptor.set）再 dispatch `input`。
   —— 这正是测试库内部一直在做的那件事。

### 缺件时**报错退出，不静默跳过**

这套用例依赖 DSH 检出存在。缺 `jsdom`/`react`/`react-dom` 时它**以退出码 1 明确报红**
并告诉你怎么办（`--harness` / `KS_HARNESS_DIR`），**不打印"SKIPPED"然后报通过** ——
理由与本仓其它护栏一致：**"没跑" 不能渲染成 "通过"**。

### 证伪测试

把详情里的「废止日期」临时改成「作废日期」⇒ 该条 FAIL、`12/13`、**退出码 1**；
改回 ⇒ `13/13`、退出码 0，且 `git diff --stat` 只有预期文件。
（⚠ 这次**没有**再用 `git checkout --` 还原 —— §10.130 第六节那个教训。）

### ⚠ 边界（别把它读成"像素已验证"）

- 宿主 `ui-primitives` 在用例里是**按源码形状写的桩**（Button/Checkbox/Tag/Pill/Input/Menu，
  形状逐个读过宿主源码）⇒ 验的是**我们这一页的组装与行为**，不是宿主组件内部实现。
- 样式只验"注入了"，验不了"长什么样"。
- **依赖检出存在**（`--harness`）：换机器要指对路径，否则这套会红（这是有意的）。
- **仍然没在真浏览器里看过**：GUI 要鉴权（401）、浏览器自动化那套 200 MB 属于过度延伸。
  ⇒ 观感/像素仍只能由业主定。
