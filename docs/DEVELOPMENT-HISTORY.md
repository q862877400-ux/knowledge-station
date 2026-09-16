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

---

*历史细节的原始记录存在于 git 提交历史（`git log`）与术前备份 `D:\AI\zcode-backups\`。本文之外**不存在**其他历史档案库（旧文档宣称的 `docs/_deprecated/` 从未存在）。*

## 六、依赖声明修复（2026-09-13，冗余清剿遗留项收尾）

双 verifier 审计（依赖声明 + 端点消费图谱）+ 主对话交叉核实，三项修复：

1. **`.gitignore` 吞生产文件事故**（审计意外发现，最高优先级）：`exports/` 无锚定规则连带忽略 `src/core/exports/` 整目录——**5 个活生产文件**（报表导出/效力报告/Office 回环/反链）从未进过 git，`git log --all` 历史为空。新克隆必 ImportError。修复：锚定 `/exports/` + 抢救入库。
2. **pyproject 依赖缺陷**：删 `python-multipart`（全仓 0 import、120 端点无 multipart 表单）；`httpx` 从 dev 上提 dependencies（生产 3 文件 8 处使用）；新增 `requests`/`urllib3`/`beautifulsoup4`（knowledge/law_source 模块级裸 import，此前仅靠 mineru 传递依赖偶然满足）；新增 vision/proc/wincom 三个 optional extras（守卫内可降级依赖显式化）；`packages.find` 补 include + `src/__init__.py`（此前 find_packages 返回空=零打包）。mypy 的删而复立见下节（同日另一批次把它真正建立了起来）。
3. **端点消费图谱精确化**：替换 §17 "约 55 个零前端调用"粗估（实为把 54 个 TEST-ONLY 误并入）→ 精确四分类 LIVE-PRODUCT 44 / TEST-ONLY 54 / ZERO 22 / SCRIPT-ONLY 0；ZERO 22 条逐条复核均为"未接线"而非废弃残留，统一 KEEP。ENCYCLOPEDIA §10.2 端点表修 4 处漂移（3 条假路径 + 1 条 SSE 误标）。

## 七、mypy 门禁建立 + 图/公式/表图端点接线（2026-09-13，双遗留项清账）

上节两项遗留的当日清账（均在 0f90972 之上，verifier 纪律全程）：

1. **mypy 门禁从无到有（REQUIREMENTS 硬指标 #2 的 Python 半兑现）**：安装 mypy 2.3.1 → `[tool.mypy]` 非 strict 保守口径（check_untyped_defs / no_implicit_optional / warn_redundant_casts；fitz/jieba/mineru 系/curl_cffi/openai SDK 等无 stub 包 ignore_missing_imports）→ 基线 **126 错误分 7 轮清零**（126→95→82→47→10→0，120 文件全绿）。每处 `# type: ignore[code]` 带行内中文理由注释；`mypy>=1.10` 回 pyproject dev extras；`npm run typecheck:py` 脚本入 package.json；REQUIREMENTS-v4.3 L2929 注记改"已建立"（`--strict` 愿景降级为非 strict 起步——~612 处未注解面按 warn 只增不减消化，strict 另立里程碑）。
   - **真实缺陷战果**（超越注解噪音）：announce.py `export_announce_xlsx` 用 `Path` 未导入（**每次 Excel 导出必 NameError 的 P1 崩溃**）；server.py 三处 `_p` int→str 循环变量复用 + 死 `_lo/_hi` 块；effect_report 循环变量 `c` 遮蔽 COLOR_ORDER 键；write_queue `int(cur.lastrowid)` 无 None 守卫；figure_redraw `k`（ndarray 核）与去重循环 `k` 同名类型漂移；office_roundtrip 条款并发删除 None 崩溃（加 None 守卫）；bulk 六处 `load_batch` 返回 None 撒谎路径（`_reload` assert 化）；supervisor ChildHandle Protocol 只读属性化。
   - pytest 回归 828+3 不变（annotation-only + assert 守卫，零行为变化）。
2. **图/公式/表图三端点 ZERO→LIVE 接线**：引擎 `/figure/{fig_no}`｜`/formula/{fno}?clause=`｜`/table-image/{page}/{idx}`（2026-09-02 实现完备，旧 App.tsx 退役后无 GUI 消费者）。
   - **host**：`plugin/src/docimage.js` 前缀路由 `/ks/doc-image/*`（经 guardWebServer 统一栅栏；Bearer 只在 host→引擎段；引擎 404 透传=占位隐藏契约；X-Frac-* 三头逐字转发；dpi 72~300 钳制；401 会话轮换重试一次）。`engine.js` 新增 `apiGetBytes`（二进制 GET，不走 text() 腐蚀字节）。
   - **client**：`api.ts` 新增 `fetchDocClauses`（信封 `{code,data:{clauses[]}}` 下钻——E2E 实测修正）与 `fetchDocImage`（同源代理 → objectURL + frac 头）；`KsEvidenceTab` 新增「📄 正文 / 📑 PDF」视图切换；新组件 `KsDocTextView`：content_html **结构白名单消毒**（剥壳上移节点也必被过滤——过滤不变量=「属性过滤只在节点被 pop 时做」；剥 script/on*/外链 src；img.class 必须存活——接线选择器按 class 命中）→ fig-embed / table-embed / katex-formula 占位 effect 拉图接线（404 隐藏/公式回退线性文本），按 page_start 聚合页块导航与 PDF 翻页双向联动。**asset-embed 本批不接线**（124 处只显示 alt 文本——assets 走 sha256 白名单端点，留待后续批次）；table-embed 现网语料 0 生产者（代码层链路已通，数据层待带图表格语料入库）。
   - **验证**：新增 `smoke-docimage.mjs` 24 断言（路径解析/栅栏拒非回环/字节与 X-Frac 保真/404 状态码透传+本地信封/401×2→502/dpi 钳制/apiGetBytes 字节保真）与 `smoke-sanitize.mjs` 13 断言（消毒器回归——P0 级：剥壳上移 img 的 onerror 必被剥、fig/table-embed class 必存活；P1 级：src 直剥无断头属性、javascript: 随壳剥除、script 文本全丢、正文文本保全）入 `npm run smoke`（10→12 段）；**真机 E2E**（真引擎真语料 GB/T 34406）：figure 1 SVG 矢量重绘 2601B、A.1 PNG 44658B、formula 1@3.7 PNG 3007B 带 X-Frac 三头、无图 404、clauses 31 条全带占位（fig A.1/A.2 + 式 1@3.7/2@3.8）。
   - **verifier 两轮**：第一轮 REJECT（消毒器剥壳上移节点漏过滤=P0-1 XSS 绕过；img.class 被白名单剥掉=P0-2 figure/table-image 断头接线）→ 重写过滤不变量 + class 入白名单 + 补 smoke-sanitize 回归 → 第二轮 APPROVE（真机全库 31 文档 3705 条款普查：非白名单标签 0、fig-embed 92/katex 510/asset-embed 124/table-embed 0；E2E 复证 200 PNG+frac 头）。复审清账 7 项同步落实（P2-11 就地 revoke、404 措辞统一、data-ks-src 声称清除、门禁计数 12 段、asset-embed 取舍显式化）。
   - 门禁扩容四件套→**五件套**：pytest 828+3 ｜ smoke 12 段 ｜ verify:commands 15/15 ｜ tsc 0 错 ｜ **mypy 0 错（新）**。消费图谱 LIVE 44→47、ZERO 22→19。

## 八、水印污染根因 + 官方侧边栏迁移 + 审计缺口清账（2026-09-16）

会话起点 `1143 passed + 2 failed`，会话内陆续扩到 **`1210 passed / 3 skipped / 0 failed / 1 xfailed`**（mypy 122 文件 0 错、tsc 0 错、smoke 11 段 PASS、verify:commands 15/15；那 1 条 xfail 见 §八.3 末的"第二个所有者"）。本段提交：`0ecd1af` `28a86da` `9c851e0` `a808dbb` `7caf9b2` `df4dc41` `5d916cc` `aaefeaf` `c21a332` `53cdf81` `390c434` `5c93a46` `e41e0d5` `a07f40c` `c9898a1` `c69d94a` `a3083f5` `ddcae1f` `0cd52e7` `78a0a1f`。

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
     回归用例 `tests/test_watermark_own_standard.py`（35 条，取代原 `test_watermark_tail_known_gap.py` 的 4 条 strict xfail + 4 条护栏 —— **xfail 已全部转为真断言**）：表格末格必存活 / 自家页眉仍必删 / 整行页眉仍必删 / 全角 own 可匹配 / **页眉把 GB/T 印成 GB 仍必删**（钉住那 226 类）/ 同族不同号必保 / 分册号不同必保 / 合法引用存活 / 水印两族照删 / **不传时保持历史行为**（防无痕改变既有调用方）/ `canon_standard_no` 单元 / **端到端接线**（截获 `clean_clause_text` 断言 `own_standard_no` 真的传到了；以及自家页眉在真链路被删）。
     **⚠ 但只修了一半 —— 同一判据还有第二个所有者（写端到端用例时才发现，单元测试全绿也漏）**：`pipeline.py:66-67` 的 `_STD_CODE_FRAG`（**家具剥离**）是"页码 + 标准号"判据的**另一份实现**，它**在清洗链之前**跑、且**不知道文档自己的标准号**，照样把表格末格当家具切掉。实测：合成页里进入 `clean_clause_text` 的文本**已经是** `'5.2.1 材料要求：…见表 2。\n牵条 优质碳素结构钢'` —— ` 20 GB/T699—2015` 在**上游**就没了，**与文档标准号无关，故本次的上下文修法对它无效**。这也是项目"单一所有者"原则被违反的实例（`text_utils` 注释自称"只有一个判据来源"，实际有两份）。**修它要把 `standard_no` 穿过切分层**（`split_items_into_clauses` 目前拿不到标准号），属另一批工作，**本会话未做**；影响面**尚未量化**（要量化需入库前的切分文本，生产库只剩入库后的 `content_text`）。已用一条 `strict` xfail 钉住（`test_ingest_table_cell_lost_by_furniture_owner`）。
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
