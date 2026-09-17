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









