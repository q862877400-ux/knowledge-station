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
2. **测试基线只涨不跌**：24 → 173 → 312 → … → 513 → 792 → 828 passed + 3 skipped（当前）。
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
