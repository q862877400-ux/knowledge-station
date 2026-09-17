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
- **但** `REQUIREMENTS-v4.3.md` §0.1 第 2 条仍写着 `[MUST NOT] 原始文档零外发 (Data Egress Zero-Trust)`：任何 PDF/合同/图纸**绝对禁止**上传至云端；
- 且**代码按它结构性地锁着**：`dry_run.py:413`「本函数**不接受** `deep_fallback` 参数」+ `:430` 恒 `False`、`preview_jobs.py:13`「零外发是**结构性事实**」、`routes_ingest_preview.py:49-51` 直接拒绝会外发的深度通道。
⇒ 业主的直觉是对的：**一条早该随 D1 一起删的 `[MUST NOT]` 留在了 REQUIREMENTS 里，并且真的在压制深度解析通道。**

**本步只改政策文档（不动代码）**：
- `REQUIREMENTS-v4.3.md` §0.1 第 2 条 → `[MUST NOT] 无留痕外发 (No Unaudited Egress)`：**禁止的从"外发"变成"不留痕的外发"**（= D2）。原文保留在引用块里存证。同时点明"Prompt 只含最小必要片段"是**成本与准确性的工程口径，不再是外发禁令**（送全库既贵又稀释相关性）。
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
  | B0 §10.47 | `(?=[\s/]\|\d\|$)` | **A→B0 = 0 行** |
  | B §10.50 | 再把 `／` 加进枚举 | **B0→B = 5879 行 = 91.6%**，方向**全部** `law → std` |
  | C 本步 | `(?![A-Za-z])` + NFKC | **B→C = 0 行**、**A→C = 0 行**、反向翻转 **0** |
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

