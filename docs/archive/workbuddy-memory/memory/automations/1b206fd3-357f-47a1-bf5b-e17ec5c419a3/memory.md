# 自动续接链执行记忆（1b206fd3-357f-47a1-bf5b-e17ec5c419a3）

> 只记高层执行摘要，不放正文/交付物。详细交接见 `../AUTO-CHAIN-HANDOFF.md`。

## 第 1 轮 — 2026-10-09 00:34

- **做了什么**：NEXT-DEV-PLAN 序 1「甲」—— 给 `scripts/run-gates.ps1` 的棘轮接线补单测。
- **产物**：新增 `tests/test_run_gates_ratchet_wiring.py`（7 条）；改
  `scripts/verify-pssa-command-layer.ps1`、`scripts/pssa-guard.ps1`、
  `docs/RETRIEVAL-LONG-RANGE-PLAN.md`、`docs/NEXT-DEV-PLAN-2026-09-28.md`。
- **提交/快照**：`c281288` / `step-317-ratchet-wiring-test`。
- **关键读数**：8 处判定点逐处变异 **8/8 全红**；相关测试 48 passed；
  实测更正 —— `pssa-guard` 只抓得住"7 个读取点全改回"那一种（任意一处单独改回 0 命中）。
- **门禁**：`-Quick` 3/5。tsc 与 smoke 红，红点均不在本批改动面（环境依赖漂移 /
  未提交的禁碰件 announce.py）。
- **遗留**：新测试未进棘轮基线（未跑 `-Full -UpdateBaseline`）；独立复核未派（必验类别）。
- **下一轮第一动作**：冻结 `c281288` 派独立复核，放行后开「乙」（P0.4b 排序键）。

## 第 2 轮 — 2026-10-09 00:44

- **做了什么**：① 派独立复核「甲」（必验类别）并**放行**；② 「乙」P0.4b 排序键**诊断 + 拍板：不改**。
- **产物**：`docs/verify-briefs/VERIFY-REPORT-ratchet-1.md`（新增，字节级搬运）；
  就地更正 `tests/test_run_gates_ratchet_wiring.py` 的 docstring 错话；
  改 `docs/NEXT-DEV-PLAN-2026-09-28.md`、`docs/RETRIEVAL-LONG-RANGE-PLAN.md`、`docs/DEVELOPMENT-HISTORY.md`（10.205）。
- **提交/快照**：`ec70128` / `step-318-ratchet-1-verify`。
- **关键读数**：复核三条自报结论全部复现（逐处 8/8 各 5 红 / 原样件 7 passed / PSSA 0-0-1），
  4 类良性改动全绿。**两条非阻塞发现**：红因实为"计数 8→7"（逐处循环无独立判别力）；
  docstring 的 fail-closed 说法**实测相反**（`$baseTotal` 改名 ⇒ 7 passed，是 fail-open）。
  乙 真库实测：doc 级 8,963/16/4/NULL 0；候选面 663,613，第一档占 99.99759% ⇒ 排序 = 灌库序。
- **门禁**：`-Quick` 3/5（mypy / verify:commands / pssa-guard 绿；tsc、smoke 红，均不在本批改动面）。
- **遗留**：新测试未进棘轮基线；测试的 fail-open 缺口未补；乙的 P2 第一项诊断未开工。
- **下一轮第一动作**：补锚点存在性前置断言（fail-open → fail-closed）并派复核，再开 P2 第一项诊断。

## 第 3 轮 — 2026-10-09 01:05

- **做了什么**：补「甲」的 fail-open 缺口（判据 3'：三个锚点必须各自出现在至少一行代码里，缺一即报）
  + 派独立复核（必验类别）并**放行**；顺带做了 P2 诊断·第 0 刀（只读量"有没有可用的相关性列"）。
- **产物**：`tests/test_run_gates_ratchet_wiring.py`（+76/−2，3 条新测试）；
  `docs/verify-briefs/VERIFY-REPORT-ratchet-2.md`（新增，字节级搬运 md5 `62fb5aec…`）；
  改 `NEXT-DEV-PLAN-2026-09-28.md` / `RETRIEVAL-LONG-RANGE-PLAN.md` / `DEVELOPMENT-HISTORY.md`（10.206）/
  `CHANNEL-COVERAGE-PLAN.md`（R9）。
- **提交/快照**：`7992f9d`（tests）+ `1832242`（docs）；快照 `step-319-ratchet-1-anchor-guard` /
  `step-320-ratchet-2-verify-docs`；冻结 tag `verify-freeze-ratchet-2`（区间 1 提交）。
- **关键读数**：原样件 **10 passed**；`$baseTotal` 全文改名 ⇒ **4 failed / 6 passed**（改前照绿）⇒ fail-closed 成立；
  复核独立复现全部三条自报，4 类良性改动零误伤，8 处逐处改回仍 8/8 全红。
  两条非阻塞发现：① 只删锚点赋值行 ⇒ 零报（残余）；② 红因细化（检测函数层面 7/8 处有独立信号）。
- **门禁**：`-Quick` 跑到第 5 步 smoke 前**被外部杀**（~2 分 1 秒、锁泄漏）；前 4 步 = tsc ✗（已知环境漂移）/
  mypy ✅ / verify:commands ✅（22/22）/ pssa-guard ✅。smoke 单独重跑：**红点又变了** ⇒
  `smoke-effect-tool.mjs`（引擎 60s 未就绪，`OpenCV bindings requires "numpy"`，而 venv 里 numpy/cv2 都在）。
- **P2 第 0 刀**：A 最坏面上 `legal_status` 是单值；有分辨力的列全是"类型/质量/时效"属性，
  **没有现成相关性列**。新事实：`clause_revision.title` 几乎是空列（663,634 行只有 43 行非空，且是图题注）。
- **遗留**：`-Full -UpdateBaseline` 本机跑不完（⇒ 基线仍 2530）；锚点赋值点断言登记未修；
  P2 收益未量。
- **下一轮第一动作**：按 NEXT-DEV-PLAN §三序 4 开 P2 诊断（量候选列对名次的收益，先量收益再改法）。

## 第 4 轮 — 2026-10-09 01:28

- **做了什么**：P2 诊断·第 1 刀 —— 量"候选列当筛子有没有收益"（第 0 刀只答了"有没有相关性列"，
  那是另一个问题）。只读 `mode=ro`、不改生产代码、不写库。
- **产物**：`eval/recall-funnel/exp-9-col-prior/`（`measure.py` / `result.json` /
  `VERDICT-候选列当筛子没有收益.md`）；归属层 `DEVELOPMENT-HISTORY §10.207` /
  `RETRIEVAL-LONG-RANGE-PLAN` P2 段 / `NEXT-DEV-PLAN` §二乙后 + §一更正 / `CHANNEL-COVERAGE-PLAN` R10。
- **提交/快照**：`db5c074` / `step-321-p2-col-prior` / 冻结 tag `verify-freeze-e9-col-prior`（区间 1 提交）。
- **关键读数**：参考空间 663,634 行、headline 120 条 ⇒ 去重金标条款 64 个。
  最好单列 `content_len_bucket` r95=0.608 ⇒ 1.645×；最好两列（样本内 oracle）0.329 ⇒ 3.044×；
  随机基线 0.95；**门槛 Top1000 需 4.32× / Top100 43.2× / Top20 216.1×**
  ⇒ **连 oracle 上界都没到最低门槛 ⇒ 这 14 列都不改**。
  新事实：`is_suspicious=1` 与 `type_confidence=0.5` 全库逐行同步（291,905 行）⇒ 同一个信号。
- **门禁**：`-Quick` **3/5（退出码 1，本轮跑完了）** —— tsc ✗ / mypy ✅ / verify:commands ✅ 22/22 /
  pssa-guard ✅ / smoke ✗（`smoke-materials-rows.mjs:121`）。两红均不在本批改动面。
- **遗留**：独立复核**已派未收**（批次 e9-col-prior，提取树 `D:/AI/verify-trees/e9`）；
  `-Full -UpdateBaseline` 仍未跑；锚点赋值点断言仍登记未修；P2"候选深度"那条线未量。
- **下一轮第一动作**：先收 e9-col-prior 的独立复核（收到就落 `docs/verify-briefs/` + 追加归属文档；
  没收到就继续挂 ② 段，不重派、不改数）。

## 第 4 轮续 — 2026-10-09 01:45（独立复核收口）

- **做了什么**：收第 4 轮派出的独立复核（批次 e9-col-prior）——**通过（无阻塞）**，并按"打回就地更正留痕"处置。
- **产物**：`docs/verify-briefs/VERIFY-REPORT-e9-col-prior.md`（⚠ **按复核者消息转录，非字节级搬运** ——
  复核者未按约定落盘到 `D:/AI/verify-trees/VERIFY-REPORT-e9-col-prior.md`，该目录实测为空）；
  `VERDICT` 就地更正 3 处 + 新增"五之二、独立复核"节；`DEVELOPMENT-HISTORY §10.207` /
  `RETRIEVAL-LONG-RANGE-PLAN` P2 段同步。
- **提交/快照**：`6e70e9f` / `step-322-p2-col-prior-verify`。
- **关键读数**：复核独立重算三项逐位一致（0.608051 / 0.734232 / 加权 0.910524）；`result.json`
  重跑字节级相同（md5 `1fb10761…`）；变异（贪心顺序反转）⇒ 三列 r95 全变（判据有牙）。
  **四条非阻塞发现**：① "8 列 ≥91%" 应为 **9 列**（≤1.10× 是 10 列）；② 随机基线 4,104 → **4,106**；
  ③ `effective_year` 89,082 行 NULL 未交代归桶；④ 去重不在 r95 路径上（登记防误用点）。①②③ 已更正。
- **流程教训**：派复核时"报告落盘路径"只放在事后追加的消息里 ⇒ 复核者没照做；
  下轮派复核要在**任务书正文**里写。另：`git commit -- <pathspec>` 对**未跟踪新文件**会报
  `did not match any file(s) known to git` ⇒ 新文件先 `git add`（只加自己的）再带 pathspec 提交。
- **下一轮第一动作**：按 `NEXT-DEV-PLAN §三序 7` 开 **P3.2 古籍/文言切分评估**
  （无前置；判据 = 中文单字占比（现 30.2%）与检索命中率）。⚠ 不要再收 e9 复核、不要重跑 E9。

## 第 5 轮 — 2026-10-09 02:05

- **做了什么**：**P3.2 古籍/文言切分评估**（`NEXT-DEV-PLAN §三序 7`）—— 三条换法都比现状好，
  但**判据不够格开工 ⇒ 拍板不改生产口径**；并**查清古籍的主因是繁简**（简体提问 0 命中）。
  全程只读、不写库、不改生产代码。
- **产物**：`scripts/measure-classical-chinese-segmentation.py`（399 行，新尺子）+
  `docs/research/classical-chinese-segmentation-evidence.md`（十节）+ `tests/test_classical_segmentation_ruler.py`（5 条）。
  归属层：`DEVELOPMENT-HISTORY §10.208` / `RETRIEVAL-LONG-RANGE-PLAN` P3.2 行 + "P3.2 评估"块 /
  `NEXT-DEV-PLAN` §一 P3 行 + §三序 7 + 新块 / `cross-language-retrieval-evidence.md` 两处就地追加 /
  `CHANNEL-COVERAGE-PLAN` R11。
- **提交/快照**：`111e270` + `1e46f30` + `7c92405`（本批 3 条；区间 4 条含别人的 gov-qa `e4edb82`）；
  快照 `step-323-classical-seg` / `step-324-classical-seg-tests` / `step-325-classical-seg-final`；
  冻结 tag `verify-freeze-p32-classical-seg` = `7c92405`。
- **关键读数**：语料 641,312 字符 → 712 段（繁體）；1,200 条查询（词典前半段挖、查询词后半段挖，互不相交）。
  recall@5：A 现状 **30.8%** → A+（索引不动）**34.3%** / B 字级 **40.2%** / C 领域词典 **42.3%**；
  单字占比 A **30.3%**（另按 cross-language 同法复算 **30.2%**，计划那行复现成立）/ B 81.3% / C 20.1%；
  **繁简轴：七组异形词简体栏 A/B/C 三栏全 0**（同形对照逐格相同）。
  可复跑：连跑两次剔除耗时行后**逐字节相同**。
- **判据自验**：原样件 5 passed；两处变异（`cnt`→`doc`、字级查询也丢单字）**各被抓**；
  变异后按 SHA256 逐字节还原（`a8baac47…`）。
- **门禁**：`-Quick` 跑了两次，**两次都 3/5 · exit=1** —— tsc ✗（已知环境漂移）/ mypy ✅ 153 文件 /
  verify:commands ✅ 22/22 / pssa-guard ✅ / smoke ✗（**两次红点不同**：`smoke-lifecycle.mjs` D5/D6 calls=-1
  → `smoke-chatmode.mjs` 172/174 并发写 EPERM）。两红均不在本批改动面。
- **遗留**：独立复核**已派未收**（批次 `p32-classical-seg`，task id `agent-c9ba9e656b864043`，
  报告约定落 `D:/AI/verify-trees/VERIFY-REPORT-p32-classical-seg.md`，**路径已写进任务书正文**）；
  `-Full -UpdateBaseline` 仍未跑（总账 2530，本轮又 +5）；锚点赋值点断言仍登记未修；
  **新登记两条**：① 繁简归一（需业主定，本仓无 opencc/zhconv）；② 尺子的语料不在库里（`var/*` 被忽略）
  ⇒ 从冻结提取树不能单独复现。
- **流程新坑**：`snapshot-project.ps1` 把标签打在"当时的 HEAD"上，别的进程（gov-qa 每 3 小时提交）
  会在中间插进来 ⇒ 本轮 `step-325` 原本落在**别人的** `fb11af7` 上，已手工重建到 `7c92405`。
  另：`git rev-parse <附注标签>` 给的是**标签对象** SHA，要 `^{commit}` 才是提交。
- **下一轮第一动作**：**先收 `p32-classical-seg` 的独立复核**（收到就落 `docs/verify-briefs/` + 追加归属文档；
  没收到就继续挂 ② 段，**不重派、不改数**）。放行后开 `§三序 4` 的 P2 后半段（查询改写/语料内统计关系）
  或 `§三序 6` P4 检索分类闸。⚠ `§三序 5` 要业主点头，别自己开。

## 第 6 轮 — 2026-10-09 03:45

- **做了什么**：**E4 第二轮验证**（任务书硬约束点名"需要显卡的照常跑"）。
  A 臂 = 提问侧成本/延迟/显存；B 臂 = 查询侧指令前缀 A/B。全程只读真库、不写向量、生产代码零改动。
- **开工先纠了一处过时状态**：交接单 ② 段原写"p32 复核已派未收"，实测**已收已处置**（提交 `d73b13b`，
  02:37，晚于交接单 02:23 的写入）⇒ 就地更正，未重派、未重跑。
- **产物**：`eval/recall-funnel/exp-4b-embedding-round2/`（13 文件 / 173 KB：stop-loss + 5 脚本 + 6 结果 + README）。
  归属层：`DEVELOPMENT-HISTORY §10.209` / 总纲 P2 段后新块 / NEXT-DEV-PLAN §一+§二乙后 /
  `CHANNEL-COVERAGE-PLAN` R12 / `exp-4 README §九`。
- **提交/快照**：`07c6a50` + `95cfcfb`；快照 `step-327-e4b-round2`（= `95cfcfb`）；
  冻结 tag `verify-freeze-e4b-round2` = `95cfcfb`（区间 **2** 提交，全是我的，`src/`+`plugin/` 零改动）。
- **关键读数**：A 臂 —— bge-small(CPU) 1.38 ms → Qwen3-0.6B(GPU fp16) **32.02 ms**（p90 34.74），
  冷启动 5154.3 ms、峰值显存 **1164 MiB**，〔抽样 30 条〕CPU fp32 72.88 ms；
  参照真库扫描 **1074.7 ms（663,634 行）** ⇒ 嵌入占 **2.98%** ⇒ **成本不构成拦路虎**。
  B 臂 —— Vector@1000（120 条）**0.6833 → 0.8417（+15.84pt）**，簇级 CI **[+9.43, +22.73]**、p=0.0000、
  **翻进 19 / 翻出 0**；全量 171 条 +14.03pt；仪器对照 0/171 与 0 处差异 ⇒ **有可分辨收益**。
  **两处就地更正**：真库已是 663,634 条（"52 万行"过期）；606 ms vs 812.3 ms 差 35% 归因不了。
  **补一处登记缺口**：E4 第一轮 +32.50pt 从没登记进总纲/开发史。
- **门禁**：`-Quick` **3/5 · exit=1** —— tsc ✗（已知环境漂移）/ mypy ✅ / verify:commands ✅ 22/22 /
  pssa-guard ✅ / smoke ✗（**红点又变了**：`smoke-channels-routes.mjs:162`）。两红不在改动面；
  棘轮本跑未生效 ⇒ 不许记基线。
- **遗留**：独立复核**已派未收**（批次 `e4b-round2`，task id `agent-8517671e521f49a7`，
  报告约定 `D:/AI/verify-trees/VERIFY-REPORT-e4b-round2.md`，**已写进任务书正文**）；
  `-Full -UpdateBaseline` 仍未跑（⚠ 本轮没新增 `tests/` 用例 ⇒ 总账没再涨）；
  E4 剩下三项（1024 维 / BGE-M3 / 清洗后金标重跑）登记未排期；把前缀接进生产链属行为改动。
- **新坑**：跑长任务时把输出管到 `tail` ⇒ **进度被缓冲、看不到任何输出**（下轮别接 tail，落日志文件）。
  看门狗「改 DB 不生效」那条结论**至少不总成立**（本轮槽位过期 33 分钟仍被触发）⇒ 登记待观察。
- **下一轮第一动作**：先看 `D:/AI/verify-trees/VERIFY-REPORT-e4b-round2.md` 有没有落盘
  （收到就落 `docs/verify-briefs/` + 追加归属文档；没收到就继续挂，**不重派、不改数**），
  **不要等它**（复核要重跑 11 分钟）；然后三选一：E4 剩下三项 / `§三序 6` P4 检索分类闸 /
  `§三序 4` P2 后半段（⚠ 开 P2 前先对齐"表示 vs 排序"这个前提）。
  ⚠ 不要重跑 E4 第二轮 / E9 / P3.2；`§三序 5` 要业主点头。

## 复核收口（`e4b-round2`）—— 2026-10-09 04:19–04:34

- `verifier-e4b` 回报 **放行（无阻塞）**；报告**字节级**搬进 `docs/verify-briefs/VERIFY-REPORT-e4b-round2.md`
  （两边 sha256 `b2c8fa95…` 一致，20,062 B）。
- **5 条非阻塞发现就地更正**（提交 `63da757`，**读数未动**）：F1 阈值改从 `stop-loss.json` 抽边界
  （`verdict.json` 除 attribution 外逐字节不变）；F2 副本两读数分行列出处；F3 归因文案 815.1→**实测 812.3 ms**；
  F4 冷启动波动加注；F5 主终点 Δ 两种写法加注（精确值 **+15.83pt**）。`stop-loss.json` sha `67aa10f2…` **未变**。
- **归属层**（提交 `d245b22`）：开发史 §10.209 / 总纲 E4 块 / NEXT-DEV-PLAN E4 块 三处追加"复核放行"。
- **门禁** `-Quick` = **3/5 · exit=1**（tsc ✗ 已知漂移 / mypy ✅ / verify:commands ✅ 22/22 / pssa-guard ✅ /
  smoke ✗ —— ⚠ **红点第 3 次换位置**：本轮 `scripts/smoke-kb-pad-pixels.mjs`，且耗时 717 s 超预算）。
  两红不在 `eval/`+`docs/` 改动面。棘轮未生效 ⇒ 不许记基线。
- **验证一条约定有效**：把"报告落盘路径**写进任务书正文**" ⇒ 复核者这次**真落盘了**（第 4/5 轮的教训已解决）。
- ② 段第 0 条由"已派未收" ⇒ **已收已处置**。
- **下一轮第一动作**：本任务无遗留复核 ⇒ 直接从候选里开新活：E4 剩下三项（1024 维 / BGE-M3 /
  清洗后金标重跑）/ `§三序 6` P4 检索分类闸 / `§三序 4` P2 后半段（⚠ 先对齐"表示 vs 排序"前提）。

## 第 7 轮 — 2026-10-09 09:56

- **做了什么**：**E4 第三刀：同模型升维（512 → 1024 维）**（唯一变量 = 输出维度；同一个 Qwen3-0.6B；
  两臂都不加指令前缀；语料刻意冻结在 `exp-4` 副本的 521,978 条）。只读真库、生产代码零改动、零网络（HF 离线）。
- **产物**：`eval/recall-funnel/exp-4c-embedding-1024/`（5 脚本 + 5 结果 + README + stop-loss 两份）。
  归属层：`DEVELOPMENT-HISTORY §10.210` / 总纲 E4 第三轮块 / `NEXT-DEV-PLAN` §一+E4 块 /
  `CHANNEL-COVERAGE-PLAN` R13 / `exp-4 README §九`。
- **提交/快照**：`4b9e3e5`（19 文件 / +1401 −4，全在 `eval/` + `docs/`）；快照 `step-330-e4c-1024`（=`4b9e3e5`）；
  冻结 tag `verify-freeze-e4c-1024`=`4b9e3e5`（区间 **1** 提交）。
- **关键读数**：吞吐探针 batch16 **195.9 条/s** ⇒ 全库实测 **45.9 分钟**（189 条/s）。
  主终点 Vector@1000（主结果 120 条）0.6833 → **0.7000（+1.67pt）**，簇级 CI **[-5.08, +8.55]**、**p=0.7284**、
  翻进 8 / 翻出 6；全量 171 **+0.00pt**；**@20/@100/生产上限口径全降**（−0.58 ~ −1.66pt）；
  代价 KNN@1000 p50 **787.2 → 1296.4 ms = 1.647×**。
  仪器对照全过（两表 521,978=521,978、双向 EXCEPT 0/0、d512 臂逐条复现第一轮 ctx 臂 0/171、FTS 0 处差异）。
  ⇒ **判决"放弃升维"**（低于半条分辨率线 4pt）⇒ 向量路的杠杆是**换模型/指令前缀**，不是把同模型维度用满。
- **本轮自己写的一处缺陷（已修+登记）**：`22-cluster-ci.py` 的 `p=2*min(le0,ge0)` 在 Δ≈0 时会 >1（首跑 1.079）
  ⇒ 改 `min(1.0,…)`；同一公式在 `exp-4b/13-cluster-ci.py` 里也有（那次未暴露）——已冻结文件**不改**，只登记。
- **门禁**：`-Quick` **3/5 · exit=1**（tsc ✗ 已知漂移 / mypy ✅ / verify:commands ✅ 22/22 /
  pssa-guard ✅ / smoke ✗ `smoke-lifecycle.mjs` D5/D6 calls=-1）。两红不在改动面；棘轮未生效 ⇒ 不许记基线。
- **新坑**：① **shell `nohup ... &` 起的进程会被杀**（Bash 工具调用一结束就死）⇒ 长任务必须用
  工具的 `run_in_background=true` + `TaskOutput`（并用 `filter` 少取输出）；② **本机当前无外网**
  （HF 代理 502）⇒ 加载模型的脚本必须 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`；**BGE-M3 现在做不了**。
- **遗留**：独立复核**已派未收**（批次 `e4c-1024`，agent id `agent-b1b8f072019344dc`，
  报告约定 `D:/AI/verify-trees/VERIFY-REPORT-e4c-1024.md`，路径已写进任务书正文）；
  `-Full -UpdateBaseline` 仍未跑（本轮未新增 `tests/` 用例 ⇒ 总账没涨）。
- **下一轮第一动作**：先看 `D:/AI/verify-trees/VERIFY-REPORT-e4c-1024.md` 有没有落盘
  （收到就落 `docs/verify-briefs/` + 三处归属文档追加"复核放行"；没收到就继续挂，**不重派、不改数**），
  **不要等它**；然后从候选里开新活（⚠ BGE-M3 因无网络不可选；`§三序 5` 要业主点头）。

## 复核收口（`e4c-1024`）—— 2026-10-09 11:16–11:40

- `general-purpose-1` 回报 **放行（PASS，8 项全过）**；报告**字节级**搬进 `docs/verify-briefs/VERIFY-REPORT-e4c-1024.md`
  （12,401 B / 137 行，两边 sha256 `89e06fa2…` 一致）。
- **复核独立实测**：冻结哈希 `2e4139b7…` 与 freeze.txt 逐字符一致 + mtime 早于全部结果；
  `22` 连跑两次 `cd5fac79…` 逐字节相同且与冻结版 IDENTICAL、`23` 与冻结版 IDENTICAL；
  **判据有牙**（三个变异把 `decision` 打到另三档 ⇒ 非恒判"放弃"，变异已还原）；
  仪器对照独立复现（两表 521,978×2、集合法双向 EXCEPT 0/0、`d512` 逐条复现 round1 `ctx` 臂）；
  真库 663,634、mtime 2026-10-08 18:55 ⇒ 未触碰；作者那处自我更正**属实**（未截断 p 复算 1.079→1.0 吻合）。
- **4 条非阻塞发现**：**F1** `23-verdict.py` 分档读聚合 `delta_pp` 不从两臂重算 ⇒ **已就地补自洽硬校验**
  （`abs((d1024−d512)×100 − delta_pp) ≤ 0.02pp`，不自洽即抛错；**原样件 `verdict.json` sha256 不变** `5410412f…`；
  变异自验：单侧改 `d512.rank@1000`=0.3 ⇒ exit=1 精确报错）；
  **F2 ★ 冻结哈希对 EOL 敏感**（`stop-loss.json` 是 LF、结果文件是 CRLF，提取树 fresh checkout 变 CRLF）
  ⇒ **跨批次通用坑**，正确核法 `git show <tag>:<path> | sha256sum`；`.gitattributes` 固定 `-text` 属仓级改动需业主点头；
  **F3** `NOT EXISTS` 在 vec0 虚表上极慢（复核改用集合法）；**F4** 真库"未动"只有行数+mtime 证据。F2–F4 登记不改。
- **提交/快照**：`a69b9a2`（6 文件 / +196 −1）；快照 `step-331-e4c-1024-verify`（=`a69b9a2`，`^{commit}` 已核）。
  归属层三处（开发史 §10.210 / 总纲 E4 第三轮块 / NEXT-DEV-PLAN 第三轮块）追加"复核放行"；
  `exp-4c README` 新增 §九（复核与更正表）。
- **清理**：复核提取树 `D:/AI/verify-trees/e4c`（476 MB）已 `worktree remove --force` + `prune`；
  复核旁证（日志/冻结备份）**保留**在原地。
- **② 段第 0 条**由"已派未收" ⇒ **已收已处置**。**本任务当前没有待收的复核。**
- **下一轮第一动作**：本任务无遗留复核 ⇒ 直接开新活，**推荐 `§三序 6` P4 检索分类闸**
  （E4 三刀已把表示层量到收口，它是剩下候选里唯一不依赖新语料、不依赖外网的一件）。

> ⚠ 第 8–10 轮（P4 可行性实测 / 考卷线 T016-T017 / 修总纲 P0·0.7）**未写进本记忆文件**，
> 记录在 `.workbuddy-ai/memory/2026-10-09.md` 与 `AUTO-CHAIN-HANDOFF.md`（下同，本文件从第 11 轮起恢复登记）。

## 第 11 轮 — 2026-10-09 14:02

- **做了什么**：**总纲 P0·0.10「长条款的尾巴没进向量」的只读量化**（审计 A2；只读真库、生产代码零改动、零网络）。
- **★ 成因更正**：总纲只写一道截断，实测**两道** —— 代码层 `content_text[:512]`（512 **字符**）+
  模型 `model_max_length=512` **token**；拆账后**代码上限只占 21.2%、模型窗口 78.8%**
  ⇒ **"去掉 `[:512]`"不是修法**。
- **关键读数**：>512 字 **13,666 = 2.0593%**；尾巴独有词 97.534% 的长条款有 ≥1 个（去重 117,654）；
  尾巴不进向量的字符 = 全库正文 **9.63%**。**★ 影响面 = 考卷结构上看不见**：171 条 gold 最长 **270 字**、
  **0 条 >512 字**；探针证明机制（FTS 尾巴 75% / 向量尾巴 25%，中位名次 21 vs 2）。
- **判决**：**本轮不改 schema**（考卷测不出收益 / 修法是切子块多向量 / 尾巴已被 FTS 覆盖 /
  向量路问答边际价值已量出很小）；**要修先得有"长条款 gold"考卷 = P1 第四刀，需业主点头**。
- **产物**：`eval/recall-funnel/exp-12-long-clause-tail/`（README + 尺子 + 探针 + 3 份 json）
  + `tests/test_long_clause_tail_ruler.py`（5 条）；归属层：总纲 0.10 行 + `0.10-量化` 行、
  开发史 §10.217、NEXT-DEV-PLAN 第 11 轮块、CHANNEL-COVERAGE R16、recall-funnel README §5.8。
- **提交/快照/冻结**：`98aeb52` / `step-339-p010-long-tail-quant` / `verify-freeze-p010-long-tail`（窗口 1 提交）。
- **门禁**：`-Quick` **3/5 · exit=1**（tsc + smoke 红，均不在改动面）；`-Quick` 不含 pytest 棘轮 ⇒ 不许记基线。
- **遗留**：独立复核**已收、已处置、已闭环**（见下）；`-Full -UpdateBaseline` 仍未跑（总账 +7）。
- **下一轮第一动作**：**没有挂着的复核要等** ⇒ 直接开工选活，首选 `§三序 4` 的 P2 后半段
  （查询改写 / 语料内统计关系）。

### 第 11 轮·复核闭环（同轮内）

- **结论**：**PASS，无 P0**；**1 P1 + 4 P2 全部处置完**；复核者同轮内主动 `SendMessage` 回 `main`。
- **报告**：字节级归档 `docs/verify-briefs/VERIFY-REPORT-p010-long-tail.md`，两边 sha256 = `f51d4826…`。
- **处置**：P1 = 余弦组**盘上无脚本** ⇒ 补 `cos-verify.py`/`.json`；
  P2-1 = `MODEL_WINDOW` 无钉子 ⇒ 补 2 条测试（变异 512→256 ⇒ 2 failed，原样件 7 passed）；
  P2-2 = `gain+residual` 差 2 ⇒ README 加前置说明；P2-3 = `result.json` 哈希口径错 ⇒ 更正为 `03d0a12e…`；
  P2-4 = 判决理由②措辞 ⇒ 澄清。**未再派第二复核者**（自检代替，理由写进提交信息）。
- **提交/快照**：`27fcfa3`（9 文件 / +493 −9）/ `step-340-p010-long-tail-verifyfix` → `27fcfa3`。
- **★ 新踩坑**：`snapshot-project.ps1` **自动加 `step-NN-` 前缀** ⇒ `-Label` **只传短名**，
  否则标签会变成 `step-340-step-340-xxx`（且连跑两次生成两个错名标签）。

## 第 12 轮 — 2026-10-09 14:40

- **做了什么**：**`NEXT-DEV-PLAN §三序 4` 的 P2 后半段·第一刀 —— 查询侧改写 A/B/C/D**
  （`exp-13-query-rewrite`；**只改查询串**：索引不动、模型不换、生产代码零改动、只读真库 `mode=ro`）。
- **四臂读数（headline 120 条；向量路；主终点 `Vector@1000`）**：
  `A0_raw` 30.00% / 中位名次 **4,322**（= exp-8 基准）；
  `B1_bge_instruction`（BGE 官方中文指令前缀）**34.17%**（**+4.17pt**，5 进 0 出，p=0.0625，中位名次 2,195）；
  `C1_domain_prefix`（**自造**领域前缀）23.33%（**−6.67pt**，1 进 9 出，**p=0.0215** 显著负效果，中位名次 12,244）；
  `D1_prf_expand`（**语料内 PRF**）**36.67%**（+6.67pt，11 进 3 出，p=0.0574，但 `Vector@20` 9.17%→7.50%）。
  **FTS@1000**：A0 12.5%（与 exp-8 逐格相同）/ D1 23.33%。**仪器对照 = 与 exp-8 逐条 0 处不同**（120/120）。
- **判决（按预注册阈值机械算）**：**三条全不改**（都没到"推广"线 `Δ≥+8.18pt 且 p<0.05`）。可带走的结论：
  ① "自造领域前缀"**被证伪且显著变差** ⇒ 与"只缝合不发明"（宪法原则 VI）同向；
  ② BGE 官方指令前缀是**唯一全阈值同向**的一臂（三阈值全涨、中位名次腰斩、**零索引代价**），
     但 +4.17pt **不够格单独接生产** ⇒ 记**观察**档，供与 **E4**（Qwen3 上 +15.84pt）合并评估；
  ③ 语料内 PRF **把够得着的范围推远却把最前面的名次弄差**，根因 = 伪相关集本身不含正确答案
     ⇒ 与 `exp-6`（放大上限没用）互相印证。
- **★ 一处就地更正（错话 + 更正，留痕）**：首跑用"等价但更快"的算式 `-(‖M‖²−2M·q+‖q‖²)`
  ⇒ **3/120 条名次差 ±1**（float32 并列，最近非零距离差 6e-8~6e-7 ≈ 1 ULP）⇒ 换回 `exp-8` 的
  **同一算式** `np.linalg.norm(M-qe, axis=1)` ⇒ **0 处不同**（代价 0.87 s/问）。
  ⇒ **通用教训：名次这种"并列敏感"的量上，"等价公式"不等价。**
- **判据/可复跑**：`tests/test_query_rewrite_ruler.py` **15 passed**，**5 处变异全被抓**
  （`var/tmp/exp-13-mutate.py`，还原后 `run.py` sha256 = `486e8311…` 逐字节一致）；
  换算式后**连跑两次** `result.json`（`9f585fa3…`）/ `per-query.jsonl`（`9755942b…`）**逐字节相同**。
- **产物/归属层**：`eval/recall-funnel/exp-13-query-rewrite/`（stop-loss + 尺子 + 2 份 json + README 主文档）
  + `tests/test_query_rewrite_ruler.py`；开发史 §10.219、总纲 P2 段「第 2 刀」块、NEXT-DEV-PLAN 第 12 轮块、
  CHANNEL-COVERAGE R17、recall-funnel README §5.9。
- **提交/快照/冻结**：`090ee7a`（11 文件 / +1102 −0）；快照 `step-341-p2-query-rewrite` → `090ee7a`（`^{commit}` 已核）；
  冻结 `verify-freeze-exp13-query-rewrite` → `090ee7a`（窗口 `27fcfa3..090ee7a` = 2 提交，含 gov-qa 的 `cf6c797`，已说明）。
- **门禁** `-Quick` **3/5 · exit=1**（tsc + smoke 红，均不在本批改动面；`-Quick` 不含 pytest 棘轮 ⇒ 不许记基线）。
- **遗留**：独立复核**已派未收**（agent `general-purpose-1`，报告落 `D:/AI/verify-trees/VERIFY-REPORT-exp13-query-rewrite.md`，
  **收工时已核不在** ⇒ 继续挂，**不重派、不改数**）；`-Full -UpdateBaseline` 仍未跑（总账会涨到约 2552）；
  P2 **融合层那一刀未做**（本批只测向量路，`fused@20` 仍未测）。
- **下一轮第一动作**：**先看复核报告在不在**（先看收件箱 —— 复核者可能同轮内 `SendMessage` 回 `main`）；
  之后选一件：首选 `§三序 6` P4 检索分类闸（**先探 Jev 可达性**，仍被 451 挡）、
  或 **E4 ① BGE-M3**（**外网已恢复，现在做得了**，代价大要按后台跑编排）、或 **P2 融合层**（测 `fused@20`）。

### 第 12 轮·复核闭环（同轮内收到 → 已闭环）

- **结论 = PASS（无 P0）**；四条主干（读数逐格 / 仪器对照独立复算 0 处 / 可复跑逐字节 /
  float32 更正恰好 3 条 i=23/78/162）**全部独立复现**。报告字节级归档
  `docs/verify-briefs/VERIFY-REPORT-exp13-query-rewrite.md`（`37d06e48…`）。
- **2 P1 已处置**：① **判据盲区**（`hit_rate` 边界 `<=`→`<`、`flip_counts` 方向对调 `b,c`→`c,b`
  各 15 passed 逃逸）⇒ 补 2 条用例（15→**17 条**）+ 完整变异组 7 处对**最终** `run.py`(`e0c24b10`) 重放
  ⇒ 全抓；② **口径混用措辞**（"用户看得见的前 20" 与"不测 `fused@20`"冲突）⇒ 六处全改"**向量路**前 20"。
- **2 P2**：`stop-loss.json` 的 `registered_at` 与 mtime 不符 ⇒ **登记不改**；
  `run.py` 哈希易误读 ⇒ §六 澄清（`486e8311…` = 变异当时备份、`e0c24b10…` = 提交版）。
- **提交/快照**：`caffb46`（8 文件 / +303 −14）；快照 `step-342-p2-query-rewrite-verify` → `caffb46`。
  归属层：开发史 §10.219 追加 + 新增 §10.220；总纲 P2 段；NEXT-DEV-PLAN 第 12 轮块；
  CHANNEL-COVERAGE R17；recall-funnel README §5.9；exp-13 README §六/§八。
- **清理**：提取树 `D:/AI/verify-trees/exp13` 已删。⚠ 复核回复轮不重跑门禁（改动面 = docs+tests）。
- **本任务当前没有挂着的复核要等** ⇒ 下一轮**直接开工选活**。

## 第 13 轮 — 2026-10-09 15:34

- **做了什么**：**`NEXT-DEV-PLAN §三序 4` 的 P2 后半段·第二刀（融合层）** —— 把第 12 轮（`exp-13`）
  的三条**查询侧改写**接进**完整六路融合**（生产函数 `search_with_details`），量**用户实际看到的 `fused@20`**
  （`exp-13` §五 明写"只测向量路、不测 `fused@20`"）。只读真库 `mode=ro`、生产代码零改动
  （改写只在实验脚本里 monkeypatch `embedder.embed_query` + `hybrid_engine._fts_query`）。
- **开工先探（排除两个候选）**：**Jev 仍 HTTP 451**（P4 检索分类闸做不了）；
  **HF 直连 502**（`hf-mirror.com` 200）⇒ **BGE-M3 不选**（一轮跑不完 + 进程无法跨轮存活）。
- **读数（headline 120；库 663,634 条）**：`A0_raw` fused@20 **8.33%** / 中位名次 9 / **池中位 40**；
  `B1_bge_instruction` **9.17%**（**+0.84pt**、进 1 出 0、p=1.0）⇒ 观察档；
  `C1_domain_prefix` **5.00%**（**−3.33pt**、进 0 出 4）⇒ 放弃；
  `D1_prf_expand` **7.50%**（**−0.83pt**、进 1 出 2）⇒ 放弃。
  **判决：三条全不改**（与 exp-13 同向且更彻底 —— **D1 在融合层也是负的**，补上了 exp-13 不敢下的断言）。
- **★ 两条结构读数（比 Δ 更值得记）**：① **`fused@1000` == `fused@100`（四臂都是）、池中位只有 40**
  ⇒ **用户永远看不到第 41 条以后** ⇒ `exp-8` 的"候选深度 +21.7pt"**在当前生产限量下到不了用户面前**；
  ② 融合的前 20（8.33%）**比只用向量路**（exp-13 的 `Vector@20` 9.17%）**还低 1 条**
  （⚠ 时点不同 ⇒ 作者自标"只登记为观察、不构成结论"）。
- **★★ 预注册的仪器对照【失效】，已就地更正并留痕**：预注册"A0 必须与 `funnel-per-query.jsonl` 逐条一致"
  **实测失配 6/120**；归因 = 那份文件是 **2026-10-06** 的产物、真库**已长大**
  （同批提问的 **FTS 候选池全线上涨**，i=166 **54,359 → 68,475**）
  ⇒ **通用教训：仪器对照的参照物必须是"同期重跑"，不能是历史产物**。
  处置 = 换成**同期**替代对照 `determinism.py`/`determinism.json`（三条全过：120 条 A0 跑两遍 0/120、
  与台账 0/120、20 条"装钩子 vs 不装钩子" 0/20）。
- **判据自验**：`tests/test_fused_rewrite_ruler.py` **10 条**、**8 处变异全被抓**；
  ⚠ **M4 首轮曾逃逸**（边界用例断言的是比率、被变异的是翻转侧阈值）⇒ 补用例后被抓（9 → 10 条），
  **本批自己写的缺陷、已就地更正留痕**。
- **★ 断点续跑是必需的**：单次融合调用里 **sqlite-vec 的 KNN 占 ~0.96 s**（暴力扫 663,634 行）
  ⇒ 120 条 × 4 臂 ≈ **8 分钟**、**超过工具后台任务 timeout 上限（600 s）**
  ⇒ 逐 `(i, arm)` **append + fsync** 落 `runs.jsonl`，聚合另走 `--aggregate`（实测 471 s，中途被杀一次靠续跑接完）。
- **产物/归属层**：`eval/recall-funnel/exp-14-fused-rewrite/`（stop-loss + run.py + determinism.py/json +
  runs.jsonl + result.json + per-query.jsonl + README 主文档）+ `tests/test_fused_rewrite_ruler.py`；
  开发史 §10.221、总纲 P2 段「第 3 刀」、NEXT-DEV-PLAN 第 13 轮块、CHANNEL-COVERAGE R18、recall-funnel README §5.10。
- **提交/快照/冻结**：`da27368`（14 文件 / +1745 −0，全在 `eval/`+`docs/`+`tests/`，`src/`/`plugin/` 零改动）；
  快照 `step-343-exp14-fused-rewrite` → `da27368`（`^{commit}` 已核）；
  冻结 `verify-freeze-exp14-fused-rewrite` → `da27368`（窗口 `caffb46..da27368` = 2 提交，含 gov-qa 的 `935bc31`）。
- **门禁** `-Quick` **3/5 · exit=1**（tsc ✗ 已知环境漂移 / mypy ✅ 153 文件 / verify:commands ✅ 22/22 /
  pssa-guard ✅ / smoke ✗ `scripts/smoke-lifecycle.mjs` `FAIL D5`）；两红均不在本批改动面；
  `-Quick` 不含 pytest 棘轮 ⇒ 不许记基线。⚠ 门禁与变异**没有并发**（门禁跑完才派复核）。
- **★ 新踩坑**：**PowerShell 工具本轮两次零回显**（快照与门禁都只返回 exit code、零输出，但实际都跑了）
  ⇒ **别靠它的输出判断成败**；另 `git for-each-ref --format='%(objectname:short)'` 给的是**标签对象** SHA，
  核标签要用 `^{commit}`。
- **遗留**：独立复核**已派未收**（agent `general-purpose-1`，task `agent-588de746c9934778`，
  报告约定 `D:/AI/verify-trees/VERIFY-REPORT-exp14-fused-rewrite.md`，路径已写进任务书正文；
  **被点名重点查"仪器对照失效的归因站不站得住"**）；`-Full -UpdateBaseline` 仍未跑（总账约 2564）。
- **下一轮第一动作**：**先看收件箱 + 报告在不在**（收到就字节级搬进 `docs/verify-briefs/` + 三处归属文档追加
  "复核放行"；没收到就继续挂，**不重派、不改数**）；之后选一件：
  **量"深读候选怎么筛进那 40 条池子"**（本批留下的最明确下一步）/ E4 ① BGE-M3（**走 hf-mirror + 必须先可续跑**）/
  积压 / A1 序 3 复核收尾。⚠ 不要重跑 exp-13 / exp-14 / E4 前几轮 / E9 / P3.2；`§三序 5` 要业主点头。

---

## 第 14 轮（2026-10-09 16:05–16:15）—— 复核回复轮：收下 exp-14 独立复核并逐条处置

- **判定 = PASS（无 P0）**；报告**字节级**归档 `docs/verify-briefs/VERIFY-REPORT-exp14-fused-rewrite.md`
  （sha256 `619cfff6ddbcedda48eabf72a3b122002e35ed22a34c14a23ef38372c692cf56`、13,108 B，两边逐字节相同）。
- **P1（已更正留痕，9 处）**：第 13 轮"模态 0 触发 ⇒ 池子就 40 ⇒ 用户永远看不到第 41 条"是**超出证据的全称断言**
  —— 本批 **5/120 题**（i=142/153/155/163/167）触发模态通道 ⇒ 池达 1000；池深 min 32 / p50 40 / max 1000；
  且与 `exp-7-rrm` 已登记事实（池均值 1,668.7、最大 169,645）矛盾 ⇒ 降级为"115/120 题池 ≈ 40，5/120 题池达 1000"。
- **P2-1（已补牙）**：副终点补 3 条用例（10→13 条）+ 3 处变异（M9/M10/M11）全被抓（11/11）。
- **P2-2（登记不修）**：`registered_at(15:42:00)` 晚于 mtime(15:36:43)；**就地改会毁掉"跑前落盘"证据**
  ⇒ 保留文件不动，改在 README §五.1 留痕；流程改进 = `registered_at` 用 `date` 取实钟。
- **提交** `2a0c394`（8 文件 / +379 −24；`src`/`plugin` 零改动）；**快照** `step-345-exp14-verify-close` → `2a0c394`；
  **门禁** `-Quick` **3/5 · exit=1**（tsc ✗ 环境漂移 / mypy ✅ / verify:commands ✅ / pssa-guard ✅ / smoke ✗ `FAIL D5 + D6`）。
- **★ 本轮【无挂着的复核】** ⇒ 下一轮可直接开新事。
- **新坑 3 条**：`git tag -l` 字典序（找最新标签用 `for-each-ref --sort=-creatordate`）；
  写全称句前先 grep 既存登记；上报的副终点也要有判据。
- **下一轮第一动作**：无挂着复核 ⇒ 选一件开工：**量"深读候选怎么筛进那 ~40 条池子"**（最明确下一步）/
  E4 ① BGE-M3（走 hf-mirror + 必须先可续跑）/ 积压 / A1 序 3 复核收尾。
  ⚠ 不要重跑 exp-13 / exp-14 / E4 前几轮 / E9 / P3.2；`§三序 5` 要业主点头。


## 第 15 轮（2026-10-09 16:20–16:40）—— P2 后半段·第三刀：池深 × 融合方式（`exp-15-pool-depth-fusion`）

- **做了什么**：把 `exp-6`（只放大每路取数）与 `exp-7`（只换融合公式）的**交互**补上 —— 7 格二维对照
  （池深 20/100/1000 × 加权 RRF `k`=60/200/1000 / RRM / 按文档去重），终点 `fused@20`（headline 120）。
  只读真库、零网络、`src`/`plugin` **零改动**；融合/排序/统计**复用** `exp-7-rrm/run.py`（只把它的模块级 `K` 参数化）。
- **判决：整格都不动** —— 最好两格 `P100_rrf60` / `P1000_rrf60` 只有 **+1.67pt**（p=0.5 / 0.625，低于观察线 +2pt）；
  变平衰减（`k`=200/1000）**反而 0 / −1.66pt**；**RRM 与「按文档去重」两臂与生产逐条完全相同（翻进 0 / 翻出 0）**。
- **★ 真正的收获是一条结构读数**：池子里有 gold 的比例能从 **12.50%（池中位 40）**拉到 **35.00%（池中位 1,930）**，
  但前 20 只从 **8.33% → 10.00%** ⇒ **卡住用户的不是「池子太小」，是「排不到前面」**；
  那 42 条里 gold 最好深读名次 ≤20 的有 14 条、生产只捞到 10 条 ⇒ 看见了也排不上。
  ⇒ **「限量的方式」这条路收口**；`exp-8` 的「+21.7pt 到 Top1000」**只存在于 oracle 里**；
  P2 剩余杠杆只剩**表示层（E4：换模型 +32.50pt / 指令前缀 +15.84pt）+ P1 第四刀（需业主点头）**。
- **代价**（真库 663,634 行）：向量 KNN `k=20` p50 **717.5 ms** → `k=1000` **1108.9 ms**（×1.55，+391 ms/问）。
- **仪器对照**改用**同期重跑**（不再拿历史产物）：`A0_prod` vs 生产函数 = **120/120 逐条一致**；真库 mtime 未变。
- **判据**：`tests/test_pool_depth_ruler.py` **17 条**；`var/tmp/exp-15-mutate.py` **12 处变异全被抓、还原逐字节一致**。
- **提交** `cc42d9f`（14 文件 / **+1,604 −0**）；冻结 tag `verify-freeze-exp15-pool-depth-fusion` → `cc42d9f`（窗口 `cc042eb..cc42d9f` = 1 提交）；
  快照 `step-347-exp15-pool-depth` → `cc42d9f`（`^{commit}` 已核 = HEAD）；**门禁 `-Quick` = 3/5 · exit=1 · 46 s**
  （`tsc` exit=2 已知环境漂移 / `smoke` `FAIL D5 + D6`；**都不在改动面**）。
- **归属层 6 处**：exp-15 README / 开发史 **§10.224** / 总纲 **P2·第 4 刀** / NEXT-DEV-PLAN **第 15 轮块** /
  渠道线 **R19** / recall-funnel README **§5.11**。
- **新踩的两个坑**：① **别人的未提交件不许卷进自己的提交**（`DEVELOPMENT-HISTORY.md` 里有别人未提交的 §10.223 行
  ⇒ 用 `git show HEAD:<path>` + `git hash-object -w` + `git update-index --cacheinfo` 只暂存自己那一行，
  再 `git commit` 不带 pathspec；提交后 `git show HEAD:… | grep -c 10.223` = **0**）；
  ② **门禁 exit=3 = 别的会话在跑**（等 `%TEMP%\ks-gates.lock` 消失后重跑，不是失败）。
- **本轮派了 1 条独立复核**（报告落盘路径写进任务书正文）
  ⇒ **下一轮第一动作 = 收这条复核并逐条处置 P1/P2**。
- **下一轮候选（收完复核后）**：「换模型 + 指令前缀」接生产的**方案 + 可续跑重建脚本**（属行为改动，不许顺手改生产）/
  E4 ① BGE-M3（走 hf-mirror + 必须先可续跑）/ 积压（棘轮记账、T023/T032/T033①/T036、P3.2 三件、B3 T015、E1 查 tsc）/ A1 序 3 复核收尾。
  ⚠ 不要重跑 E4 前三轮 / E9 / P3.2 / exp-11 / exp-12 / exp-13 / exp-14 / exp-15；`§三序 5` 要业主点头。

---

## 第 15 轮复核回复轮（2026-10-09 16:44–16:57）—— 收 exp-15 复核，2 条 P1 + 1 条 P2 全部处置

- **复核总判定 = PASS（无 P0）**（7 臂逐格复现 / oracle 三数一致 / 仪器对照 14/14 / 唯一变量成立 /
  复核自写 10 处变异 10/10 被抓 / 预注册早于提交 ~10 min）。
- **★ P1-1（必改）：`@100` 是 `@20` 的复制** —— 初版台账只存「top-20 名单里的名次」，聚合却拿它算
  `@100`/`@1000`（台账里**已经存着**的 `hit@100` **从未被读取**）⇒ `fused@100 ≡ fused@20`，
  而 `stop-loss.json` 明列 `fused@100` 为副终点 ⇒ **上报的是假读数**。
  **修法（不重跑 —— 复核明确认可「聚合改读 `hit@100`」）**：`run.py` 新增 `arm_rank()`（兼容新/旧台账）
  + `ledger_depths()`；聚合按 `arm_r20`/`arm_r100`/`arm_r1000` **分别**取数；
  **没测的深度上报 `null`（不许报 0%）**；台账写入改为分别存 `rank20`/`rank100`/`rank1000`。
  **真 @100 = 11.67 / 14.17 / 15.00 / 15.83 / 13.33 / 12.50 / 10.00%**
  —— 与复核独立复算逐个相同，**又用复核者自己的 `recompute_exp15.py` 对当前产物复算一遍仍逐个相同**。
  **★ 未变部分**：`@20`/判决/`pool_median`/`by_subset`/`oracle`/仪器对照/Δ/翻进翻出/`p` **全部逐位未变**；
  `result.json` 改动行只有 `fused_top100`/`fused_top1000` + 2 个元字段；`runs.jsonl`、`per-query.jsonl` **逐字节未变**。
  **★ 顺带修掉我自己引入的次生缺陷**：曾把 `fused_hit_n`/`fused_median_rank` 从 @20 口径改到 `rank1000` 口径
  （**静默换定义**）⇒ 已改回 @20 口径（现与冻结版逐位一致）。
- **P1-2（必改）：「与生产逐条完全相同」超出证据** —— 0 进 0 出只证**命中状态**相同；复核实算 top-20 **名单**：
  RRM 臂抽样 14 条里 **5 条不同**（i=84 gold 名次 1→7）、文档去重臂 **7 条不同**
  ⇒ **6 处文档全部改为「命中状态（`@20`）逐条相同」并留痕**。
  ⚠ 仪器对照那句「120/120 逐条一致」**不改**（真的逐元素比了名单）。
- **P2-1：3 处错链 §10.223 → §10.224**（RETRIEVAL / CHANNEL R19 / exp-15 README）。
- **附带（复核指出）**：README §5.2 分桶表头「≤100/≤1000」读起来像累计、实为**互斥分桶**（14+11+16+1=42）
  ⇒ 改为 `20<x≤100`/`100<x≤1000` + 补注累计值（≤100 = 25、≤1000 = 41）。
- **判据 17 → 21 条**；**变异 12 → 17 处全部被抓（17/17）、`run.py` 逐字节还原一致**；`pytest` **21 passed**。
- **提交** `43f4a6a`（10 文件）；冻结 tag `verify-freeze-exp15-p1fix` → `43f4a6a`
  （窗口 `cc42d9f..43f4a6a` = 3 提交，`14bc75a` exp-16 与 `a713dea` gov-qa **无关、非夹带**）；
  快照 `step-351-exp15-p1fix` → `43f4a6a`；**门禁 `-Quick` = 3/5 · exit=1**（`tsc` exit=2、`smoke` D5/D6，都不在改动面）。
- **复核报告归档**：`docs/verify-briefs/VERIFY-REPORT-exp15-pool-depth-fusion.md`
  （`9688b5cfca3c2a7660637da3a8b21555fa2b16f8179e444b4f0f6ef8936ecf12`、11,207 B，两边同哈希）。
- **★ 本轮没有派新复核**（复核回复轮按本仓既例 §10.216/§10.218/§10.220/§10.222 **处置完即收工**，
  且本次修法正是复核者本人开的处方）。
- **★ 新登记两条可复用教训**：① **副终点读数：名次字段必须按深度分别存**（只存一个 top-20 名次会让
  `@100`/`@1000` 恒等于 `@20` 而上报看不出来；**没测的深度上报 `null`，不许报 0%**）；
  ② **"翻进 0 / 翻出 0" 只证明命中状态逐条相同，不证明名单相同** ⇒ 别写全称句。
- **下一轮第一动作**：**没有挂着复核** ⇒ 从 ① 「换模型 + 指令前缀」接生产的**方案 + 可续跑重建脚本**
  （属行为改动，不许顺手改生产）/ ② E4 ① BGE-M3（走 hf-mirror、必须先可续跑）/
  ③ 积压（棘轮记账、T023/T032/T033①/T036、P3.2 三件、B3 T015、E1 查 tsc）/ ④ A1 序 3 复核收尾 里选一件。
