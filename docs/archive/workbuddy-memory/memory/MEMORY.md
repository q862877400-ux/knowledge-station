# 项目长期记忆（KnowledgeStation / D:\AI\work space\zcode）

> 只记**跨会话仍成立**的**环境陷阱 / 方法论 / 禁碰**；状态与读数在 `output/GOAL.md`（每轮必读），过程细节在 `AUTO-CHAIN-HANDOFF.md` 与各 exp README。
> ⚠ `tools/gov-qa/**` 由**另一个自动化**（每 3 小时一轮、直接提交 master）推进 ⇒ 本文件"禁碰"清单**对它不适用**。
> 瘦身史：2026-10-09 第 18 轮（19.3→14 KB）｜2026-10-10 第 19 轮（23.8→约 14 KB）。

## 一、环境事实（实测；机器状态会变 ⇒ 引用旧读数前先复核）

- **长任务姿势**：`run_in_background=true` 有 **2 分钟硬上限** ⇒ 门禁**用前台、不传 `timeout`**（前台超时自动转后台且不杀；给了 600 s 到点连进程一起杀）。`nohup ... &` 的子进程在 Bash 调用结束时会被杀。
- **`spawnSync` 只要 stdin 是 pipe（默认）就恒 `EBUSY`**（连跑 20/20；两个 node 版本、沙箱内外一样）⇒ 显式 `stdio: ['ignore','pipe','pipe']`（⚠ `stdin:'ignore'` 简写不管用）。async `spawn` 正常；`timeout` 本身是好的。⚠ 同一棵树不同时刻表现不同。
- **★★★ 门禁的模型 seed 判据**（`feed371`）：`KS_MODELS_DIR` 指向 `%TEMP%\ks-gates-models`；旧判据**只看"目录在不在"** ⇒ 一次被强杀/拷一半的跑留下**空骨架**（实测 12 KB、0 onnx；真缓存 91 MB）⇒ **永不重 seed** ⇒ fastembed 退避 9s+27s≈36s ⇒ 吃光 `INGEST_BUDGET_S`(45s) ⇒ `test_announce_ingest` `tried=1`（期望 2）⇒ **`-Full` 恒红，被误读成"公告组件真缺陷、修点在禁碰区"**。**已修**：判据改"递归找 `*.onnx`"+ seed 前清空骨架。**教训：看到"恒红且修点在禁碰区"，先查它依赖的环境有没有真的备好。**
- **★★★ 门禁 pytest 必须带 `--basetemp`**（`1d065b6`）：不带时 pytest 用**共享**的 `%TEMP%\pytest-of-Zegel`，启动时把上轮残留**整目录搬走**（实测 **2248** 文件）⇒ 撞**沙箱删除守卫**（阈值 50）⇒ 收尾被打断：**stdout 汇总行没打、退出码非 0，而 junit 里 `failed=0 errors=0`** ⇒ **假红**。判据：带 `-X faulthandler` 复跑 ⇒ **没有回溯**（不是崩溃）+ 日志停在 `[100%]` 点阵、无汇总行。**修后 9/9 · exit=0**。⚠ `dangerouslyDisableSandbox` **靠不住**（后台任务里试两次都没生效）⇒ 用环境侧解法。⚠ 同类症状**只在 pytest 那一步**（`-Quick` 不跑 pytest）。
- **起 Word/WPS COM 会把宿主进程打死**（SEH 级，`try/except` 抓不住；不可用时抛 `0x800706BA` 直接杀进程）⇒ **调 COM 前先做廉价前置闸**。
- **网络/GPU/解释器**：外网状态会变 ⇒ 跑联网脚本前先探一次。GPU = RTX 4080 SUPER 16,376 MiB（跑实验前先 `nvidia-smi`，常被本地大模型占）。**托管 Python 跑不了 `src.core.*`**（无 `pydantic`）⇒ 用 `.venv/Scripts/python.exe`。**DSH 插件 peer 检查会真拦安装**（只查 `@deepseek-ai/dsh*` 前缀、`includePrerelease:true`）⇒ 声明了就必须跟 runtime 对齐。
- **Jev（TypeSafe System One）本机不可用 —— 地域封锁**：`api.typesafe.ai` **HTTP 451** ⇒ 依赖 Jev 的都做不了（P4 分类闸、合规哨兵隐性层已退化成纯词表）。复跑用 `eval/recall-funnel/exp-10-p4-feasibility/probe-jev-region.py`。
- **真库**：`%APPDATA%\KnowledgeStation\database\knowledge.db`，只读 `uri=True&mode=ro`；读 `clause_vec` 前先 `load_vec_extension`（或 `funnel.ro_conn`）。2026-10-09 规模 `clause_vec` = `clause_revision` = **663,634** 行。⚠ **库在 C 盘（93% 满，只剩 ~70 GB）** ⇒ 大动作前先 `df -h /c`；目录共 20 GB（库 5.6 GB + `backup/` 14 GB，含 2 份冗余）。⚠ 大事务把 WAL 顶到 GB 级（实测 4,065 MB）⇒ 完事 `PRAGMA wal_checkpoint(TRUNCATE)`（0.4 s）。⚠ 普通表存 BLOB 向量比 vec0 占得多（2.6 vs 1.3 GB）；vec0 上**不要用 `NOT EXISTS` 做集合差**（>45 s）⇒ 取 id 到 Python 集合再对称差。
- **`tests/conftest.py` 两个 autouse fixture 让"依赖真实模型"的用例永远 SKIP（假绿）**：`_rerank_offline_for_tests` + `_isolate_data_dir`。要用真模型必须 `monkeypatch.setattr(reranker,"get_settings",lambda:_RealModelsDir)` 并清 `_model`/`_load_error`；**写这类用例前先 `-rs` 确认它真在跑。**
- **判"文件变没变"先看 `git status`/`git diff`，别用裸 `sha256sum`**（`core.autocrlf=true`：工作区 CRLF、`git show <tag>:<path>` 是 LF ⇒ 裸哈希必假红）。核冻结哈希用 `git show <tag>:<path> | sha256sum`；⚠ 变异后还原一律 `write_bytes(backup.read_bytes())`。
- **`benchmark-v2.jsonl` 的 `flag_detail.same_def_docs` 是活计数** ⇒ 重跑不保证逐字节相同；核改动面一律逐行 `json.loads` 递归比 key。

## 二、门禁与红点（现状读数见 `output/GOAL.md` 第二/三节）

- **调用姿势**：`pwsh -File scripts/run-gates.ps1 -Quick|-Full` **只能从 PowerShell 工具调**；一次只跑一个（**退出码 3 = 有人在跑，不是失败**，锁在 `%TEMP%\ks-gates.lock`）。⚠ **红的跑不许 `-UpdateBaseline`**（脚本注释自己写着"红的跑也会改写基线"）。
- **★★★ `var/tmp` 产物"不见了"先查 `var/_trash-*/`**：2026-10-05 那次是**移到** `var/_trash-2026-10-05/var-tmp-rest/`（1473 文件）**不是真删** ⇒ 还原 6 个产物一次修掉 5 failed + 3 skip。
- **★★★ 种子里的"未来日期"是【日期炸弹】**：`legal_status.resolve_status()` 是**惰性翻转**（`upcoming` + 实施日期已到 ⇒ `effective`）⇒ 到点用例前提失效。**种子日期一律用未来**（`test_ks_answer.py` 已改 `2027-10-01`）。
- **★★ sqlite-vec（0.1.9）范围下推**（探针 `specs/003-vec-scope-pushdown/probes/probe-mechanism.py`）：失效条件 = **"范围里的条款只有【一部分】有向量"** ⇒ 旧写法（在 `clause_revision_id` 这个 **TEXT PRIMARY KEY** 上过滤）返回 `[]`，**与表大小无关**；全都有向量则正常（真库今天常态）⇒ **不是当前故障，是潜在脆弱点**。**修法**（`d07a32c`+`25e17e7`）：`clause_vec` 加 **`doc_id`** 列，过滤走 `doc_id IN (SELECT value FROM json_each(?))` —— **只有这一种写法能下推**；字面量 `IN (?,?)` 与 `OR` **会返回范围外的行**（比不修更糟）。⚠ `ALTER TABLE … RENAME` 对 `vec0` **不连带改影子表** ⇒ 必须"普通表中转 → DROP → 重建 → 回灌"；`PRAGMA table_info` 对 `vec0` **不报声明类型** ⇒ 形状断言只能靠 DDL 文本 + `pk` 标志。
- **★★ Windows 上多线程同时 `open()` 同一个【还不存在的】文件会 `PermissionError(13)`**（并发 CreateFile 撞车，不是"被锁"）⇒ 要有界重试。
- **门禁基线里的节点名要和真名逐字一致**（曾把 `test_reranker_real_model_reorders` 写成 `test_rerank_...` ⇒ 白名单里是幽灵、`test_gate_baseline_whitelist` 恒红）。
- **红点排查法**：`tsc` 红 = 自己漏改（改图标名没跟 `ksHostPrimitives.d.ts`）；`smoke` 红 = spawnSync EBUSY / `ui-render-shot.mjs` 跑完不退出 / chatmode 锁 EPERM；`pytest` 红 = `docx_to_pdf_com` 起 Word COM；真宿主 e2e 红 = DSH peer 区间过期 ⇒ **别再写"已知环境漂移"**。
- **`ui-render-shot.mjs` 的「开菜单」场景（`kb-filemenu`/`kb-dirmenu`）跑完不退出**：`_getActiveRequests()===[FSReqCallback]`、**CPU 恒 0（不是死循环）**，根因未查明；已加文件末尾显式 flush + exit。⇒ 判"冒烟卡住没有"**别看日志**（跑完才打印），**看 CPU 涨没涨 / 产物 mtime 推没推进**。

## 三、检索线现状（改这一线前必读；全读数见各 exp README）

- **重排在【生产里是显式关闭】**（`server.py` 主问答与 `local_vision.py` 都写 `rerank=False`）⇒ 要开启必须先改这两处 + 走必验。`reranker.rerank` 契约 = 返回**与 texts 一一对应、未排序**的分数。**已知缺陷 D2（未修、已登记）**：`_protect_exception_clauses` 在真实调用形态下**恒不生效**（`kept` 长度已等于 `top_k`）⇒ 它是"把重排接进生产"的前置条件。
- **四条改进路线的收益上限都已量出（别再当杠杆）**：重排器 +1.67pt（exp-11）｜查询侧改写最好 +4.17pt(向量)/+0.84pt(融合)（exp-13/14）｜融合算子 RRM 逐条不变（exp-7）｜池深×融合方式最好 +1.67pt（exp-15）。**池深不是瓶颈**（池 40→1,930 只把前 20 命中 8.33%→10.00%）⇒ **P2 剩余杠杆只剩【候选本身的名次质量】= 表示层（E4）+ P1 第四刀（重建评测集，需业主点头）**。⚠ 融合池通常 ≈40 条**但不是硬顶**（5/120 题因模态通道达 1000；`exp-7-rrm` 池均值 1,668.7）⇒ 别把中位数写成"上限"。
- **E4（换嵌入模型）是唯一已量出大收益的方向**：bge-small → Qwen3-Embedding-0.6B **+32.50pt**，加 BGE 中文指令前缀再 +15.84pt；升维 512→1024 只 +1.67pt ⇒ 放弃。**成本不是拦路虎**（占向量路扫描 2.98%、显存 1,164 MiB），但属**行为改动**须走必验。**BGE-M3 未做**（要下模型走 hf-mirror；**必须先设计成可续跑**）。
- **★★ fp16 批不变性**：同一批 64 条换一种分批 ⇒ 只 16/64 逐字节相同（`maxdiff 8.4e-4`）⇒ 拿"逐字节相同"当嵌入口径判据时必须**复刻对方的分批**。
- **★★ `embedder.embed_query` 被【两处】调用**：查询侧 `hybrid_engine.py:310` + **条文侧** `clause_repo.py:426` ⇒ **查询指令前缀只能做在调用点，不能做在 `embed_query` 内部**（否则两套口径混进一张表且无读数可见）。
- **`exp-17/rebuild-shadow.py` = 可复用的"可续跑重建"骨架**（影子库 + `rowid` 游标 + 库内 checkpoint 同事务 + 口径守卫硬失败）；换 `--model-id`/`--out-dim` 就能重算全库。
- **有些性质【运行期测不出来】**：只在"两次提交之间被强杀"才出错的时序性质 ⇒ 只能静态钉住代码结构；"不改行数只改取样集合"的过滤条件 ⇒ **必须比集合本身**，不能只比行数。

## 四、复核机制（派/收）

- **`TaskOutput` 对"队友型"后台任务【不阻塞】** ⇒ 派给 `Agent` 的复核**默认按"下一轮收"编排**；★ 复核者**收工时会主动 `SendMessage` 回 `main`** ⇒ **等收件箱**。队友型后台 Agent 收工后团队就散 ⇒ **要复核"修复批次"只能另起新 agent**。**★ 复核报告落盘路径必须写进任务书正文**。
- **★★ 写"永远 / 硬限制 / 0 触发"这类【全称句】前，先 grep 本仓既存登记**；**上报的副终点也要有判据**。
- **★★ 自我更正必须 grep 全仓**：第 18 轮我把"向量范围下推失效条件"改对，改了 4 处文档，**漏了 6 处代码/测试/注释**，被独立复核逐处点出 ⇒ 改完**立刻** `grep -rn "<被推翻的原话片段>"`（含**代码注释与测试 docstring**）。
- **★★ `grep ... | head -40` 会截断 ⇒ 漏看文件**：改 `clause_vec` schema 时漏了 `tests/test_storage.py`（直接 `INSERT clause_vec` 不带 `doc_id` ⇒ junit 抓出 `Expected text for TEXT metadata column doc_id, received NULL`）⇒ **改共享 schema/接口前先 `grep -rl` 拿文件清单（不带 head），再逐文件看**。
- **★★★ 判"是不是 flake"必须【取率】，不许取单次**：`smoke-materials-rows.mjs` 的「行 0」我**四次单跑都过**就下了"单跑必过"的结论 —— 取率后（各 10 次）直接 **8/10**、被 node 父进程 spawn **5/10** ⇒ **20–50% 的真 flake**（`0.8^4≈41%`）；**同一次试验里我据此下的 `stdio` A/B 结论也是错的**（那次 PASS 是噪声，随后连跑 3/3 全挂）。**真因** = 脚本里 **3 处定死的 `setTimeout(30/30/20)`** ⇒ 改成**等条件**（`waitFor`+`settle`）、断言一字未动 ⇒ 修后 **20/20**。⇒ **规矩：凡"有时过有时不过"，先跑 N≥10 取率；单次 PASS/FAIL 都不算证据。**
- **★ 仪器对照的参照物必须是"同期重跑"，不能是历史产物**（活库会长，历史名次不可复现）。
- **★★ 副终点读数：名次字段必须【按深度分别存】**（只存一个「top-20 名单里的名次」时 `@100`/`@1000` 会**恒等于** `@20`）⇒ `rank20`/`rank100`/`rank1000` 分别取；**没测的深度一律上报 `null`，不许报 0%。**
- **★ 上报数的【定义】不许顺手换**（改定义要当"改读数"对待）；**"翻进 0 / 翻出 0"只证明【命中状态】相同，不证明【名单】相同** ⇒ 名单级结论必须真去比 top-20 名单。**★ 复核者会附带挑【表述】问题** ⇒ 表头/口径句也要自查；**预注册文件的时间戳取实钟**（`date`），不一致**别就地改那个文件**（会毁 mtime 证据）。

## 五、提交 / 快照 / 调度（细则见 `output/GOAL.md` §五/§七）

- `git commit -F <消息文件>`；`git add` 只加自己的文件；**归属层清单只列本提交真的包含的文件**。⚠ **别人的提交会【夹带】你的未提交件** ⇒ 改完尽快提交，写清单前先 `git status --short` 核。**★ 与别人的未提交行同处一个文件时**（典型 `docs/DEVELOPMENT-HISTORY.md`）：`git show HEAD:<path>` 建 blob → `git hash-object -w` → `git update-index --cacheinfo 100644,<blob>,<path>` **只暂存自己那一行** → `git commit -F <msg>`（**不带 pathspec**）。**已验证可用。**
- 快照 `& .\scripts\snapshot-project.ps1 -Label <短名>`；找最新 tag 用 `git for-each-ref --sort=-creatordate`（`git tag -l` 是字典序）。⚠ **PowerShell 工具常零回显** ⇒ 别靠输出判断成败（Tee 到文件再读）。
- **★★ 调度 = Stop hook + `output/GOAL.md`（2026-10-10 换挡）**：⚠ 业主已删光 13 条自动化任务 ⇒ 旧口径（`recurring`/`scheduledAt`/自链）**全废**。⚠ 项目级 `.codebuddy/settings.json` 已**停用**（与全局 hook 重复 ⇒ 计数器翻倍）⇒ **不许重建、不许新增 hook**。⚠ 逐轮判据 `check-full-green.sh` **比【代码面】（`src/ tests/ plugin/ scripts/`）而非 HEAD**（gov-qa 一直提交 `tools/gov-qa/**` ⇒ 比 HEAD 会**永远"不新鲜"**），且**只用 ASCII 匹配**。⚠ **Stop hook 是【终止型】**。**看门狗已退役** ⇒ 别再启动。

## 六、禁碰 / 不重走

- **禁碰** `tools/gov-qa/**`（另一自动化每 3 小时直接提交 master）；**禁碰**公告更新组件（`src/core/update/announce.py` / `web_ingest.py` / `discover.py`、`routes_update.py` 的 `announce-*`、`plugin/src/announce.js`、`KsSettingsSection.tsx` 的"公告发现"）。
- **不要重跑**：E4 前三轮 / E9 / P3.2 / exp-11~15。**`§三序 5`「P1 第四刀：重建评测集」要新测试语料 ⇒ 等业主点头**。**`docs/NOT-DOING.md` 第 22 条**：不许再提"三字滑窗"。长文档搬运一律**脚本化**；**打回的说法就地更正并留痕**。

## 七、`/goal` 命令（2026-10-09 只读核查本地 CLI）

- 斜杠命令：`GoalService.set()` → `registerGoalHook()`（**Stop 钩子**）+ `persistMeta()`。**★ 模型设不了**（grep `set_goal`/`setGoal` 零命中）⇒ 只有业主能设。**⚠ 语义 = 终止型** ⇒ 与"每小时一轮、永远跑"的自动化**互补、不是替换**。
