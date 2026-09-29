# Hindsight 本机部署现状交接说明

> 用途：交给另一个 AI 独立评估。本文只写**实测到的事实**，每条注明取得方式与时间。
> ⚠ **凡本文写"未跑/未测/未验"的，都还没做，不要当结论用。**
> 生成时间：2026-09-30　　采集时的运行版本：**v0.10.0**（官方文档为 v0.10.1，实机旧一版）

---

## 一、一句话现状

**能用的**：写入、精确条款命中、标签过滤、16 个记忆库、11.9 万条事实、MCP 接入正常。
**没用的**：知识页自 2026-09-25 起冻结、11.9 万条事实从未归并成"通则"、**中文关键词检索等于没有**。
**刚改完还没生效**：四条配置已写入 `dsh.env`，**服务未重启**。

---

## 二、运行拓扑（实测）

```
DSH 宿主  node apps/cli/src/bin.ts "web"          PID 21580
 └ 插件   node serve.mjs                         PID 14324
            源码 D:\AI\oss-research-and-deployments\hindsight-ov\dsh-lifecycle\lib\index.js
 └ uv     uv.exe                                 PID 23232
     └ hindsight-api.exe  (API 服务 :8888)
         └ 内嵌 PostgreSQL  :5432  实例 hindsight-embed-dsh
```

| 项 | 值 | 来源 |
|---|---|---|
| 插件名 | `dsh-hindsight-lifecycle` | 其 package.json 自述 |
| 插件职责 | "把本地 Hindsight 记忆守护进程**绑定到 DSH 自身的生命周期**：DSH 启动时拉起，DSH 退出时关闭。**不做后台常驻、不注册计划任务。**" | 同上 |
| 启动判定 | 插件先探 8888 端口；**已在跑就复用、不重启**（注释理由：重启要重连 PG + 重载 ONNX，30~100 秒） | `lib/index.js` L136–138 |
| 进程父子绑定 | 插件给子进程传 `DSH_PARENT_PID`，`serve.mjs` 盯着它，DSH 一消失就自动收摊 | `lib/index.js` L89–91 |
| 所有权守卫 | "不是本进程启动的，一律不动" | `lib/index.js` L113–116 |
| 日志 | `D:\AI\oss-research-and-deployments\hindsight-ov\state\lifecycle.log` | 源码常量 |

⚠ **重要操作约束**（我今天踩过）：
- **重启必须走 DSH 重启**（插件会拉起），**绝不能手工跑 `hindsight-api.exe`**。
  手工跑会绕过 `DSH_PARENT_PID` 绑定 ⇒ 成为孤儿进程，**且会用默认 pg0 实例名而不是 profile 的那个**。
  我 2026-09-29 11:33 就这么干过，结果连到了空的 `hindsight` 实例（0.05 GB），
  看起来"数据全没了"——**数据当时一直好好躺在 5.99 GB 的 `hindsight-embed-dsh` 里**。

---

## 三、数据规模（实测，`/stats` 与 `/banks`）

| 项 | 值 |
|---|---|
| 记忆库总数 | **16** |
| 生产库（`coding-agent::zcode`） | **118,985** 事实 / 3,534 文档 / 5,727,929 边 |
| 事实类型分布 | world 87,079　experience 31,906 |
| 边类型分布 | semantic 3,819,141　temporal 1,761,451　entity 141,218　caused_by 6,119 |
| 最后写入 | 2026-09-29T17:55:37Z（**仍在增长**） |
| 归并（observations） | **0 条**；`last_consolidated_at = null` ⇒ **从未归并过** |
| 知识页 | 9 张（`Initiatives` 文件夹下） |
| 数据库体积 | 5.99 GB（`.pg0\instances\hindsight-embed-dsh\data`） |
| 备份 | `C:\Users\Zegel\.hindsight\backups\pre-config-change-20260930.zip`，10,016,469 行 / 23 表 / 0.52 GB |

⚠ 另有 2 个**探针库**是我 2026-09-29 压测留下的（`probe-import-20` 7,608 事实 / `probe-clean-20` 7,463 事实），
**未清理**，混在生产库里。

---

## 四、当前生效的配置（读 `C:\Users\Zegel\.hindsight\profiles\dsh.env`，45 个生效变量）

### 4.1 LLM 链（failover 模式，3 个成员）

| 位 | 模型 | 端点 | 说明 |
|---|---|---|---|
| 主 | `space-bunny-free` | `opencode.ai/zen/v1` | **限时免费，业主称窗口约至 09-30** |
| 备 1 | `stealth/space-bunny-alpha` | `openrouter.ai/api/v1` | 同源不同代号，**同为限时免费** |
| 备 2 | `deepseek-flash` | `api.deepseek.com/v1` | 已配 `EXTRA_BODY={"thinking":{"type":"disabled"}}`（非思考别名，最便宜形态） |

主成员必须带三个头（文件内注释）：
`HINDSIGHT_API_LLM_DEFAULT_HEADERS={"User-Agent":"opencode","x-opencode-client":"desktop","x-opencode-project":"global"}`
⚠ 原因（文件内注释）："**Zen 免费层对客户端身份敏感：非 CLI UA 会 429 FreeUsageLimitError**"
⇒ **免费层不只是到期问题，它对请求身份也敏感，去掉这三个头就会 429。**

⚠ **成本现状（未测）**：主模型每分钟/每天能吞多少、11.9 万条若走写入路径要多少钱 —— **我没测**。
`llm_requests` 记录只留 1 天（**我已改成 90 天，但未重启，尚未生效**）⇒ **窗口内的历史用量已不可查**。

### 4.2 与官方默认不同的项（逐条对照官方 configuration.mdx）

| 项 | 本机 | 官方默认 | 评价 |
|---|---|---|---|
| `LLM_MODEL` | `space-bunny-free` | `gpt-5-mini` | 有意 |
| `LLM_TIMEOUT` | `300` | `120` | ✅ 对，官方要求"比最慢的还慢" |
| `EMBEDDINGS_PROVIDER` | `onnx` | `local` | ✅ 对，官方定位 onnx 就是"轻量本地 CPU 多语言" |
| `RERANKER_LOCAL_MODEL` | `BAAI/bge-reranker-base` | `ms-marco-MiniLM-L-6-v2` | ✅ 对，**默认两个都是英文模型，我们换成了中文模型** |
| `ENABLE_OBSERVATIONS` | `false`→**`true`(待生效)** | `true` | 🔴 曾被关掉 |

### 4.3 🔴 今天刚写入、**尚未生效**的四条（服务没重启）

| 项 | 从 | 到 | 依据 |
|---|---|---|---|
| `LLM_MAX_RETRIES` | 默认 3 | **0** | 见下"故障复算" |
| `WORKER_ID` | 默认主机名 | **`hindsight-dsh`** | 官方 installation 与 admin-cli 两处专门警告 |
| `LLM_TRACE_RETENTION_DAYS` | 默认 1 | **90** | 免费窗口关了就没账可查 |
| `ENABLE_OBSERVATIONS` | `false` | **`true`** | 11.9 万条从未归并、9 张页冻结 |

### 4.4 **未设、走默认，但对我们不利的项**

| 项 | 默认值 | 问题 |
|---|---|---|
| `TEXT_SEARCH_EXTENSION_NATIVE_LANGUAGE` | `english` | 🔴 **中文关键词检索失效**（见第五节） |
| `REFLECT_LLM_TIMEOUT` | `30` 秒 | ⚠ 免费模型慢，官方明写慢模型要调高（我们只调了全局 300） |
| `OPERATION_RETENTION_DAYS` | `0`（永久） | 作业表只涨不删（现有约 1.2 万行） |
| `DB_POOL_MAX_SIZE` | `100` | 官方说"每次并发召回吃 2-4 条连接" |

---

## 五、🔴 三个硬约束（官方文档已核，不是我的判断）

### 5.1 中文关键词检索**等于没有**

默认走内嵌库自带的分词，官方原文：
> "**对中文/日文/韩文完全没有有用的分词**（这些语言没有空格词界）"
> "pgroonga 与 pg_search 依赖的扩展**不在内嵌库中**……在这个默认单机部署下**两个都开不了**。"

**本机未设任何分词后端** ⇒ 走默认英文分词器，**中文 BM25 那条臂实际不产出可用结果**。
⇒ **要解决只有一条路：换外部 PostgreSQL**（官方 Windows 步骤：`winget install PostgreSQL.PostgreSQL.17` + 编译 pgvector）。
⚠ **但**：`pgroonga`（唯一开箱支持 CJK 的）在官方文档里**只有 Docker 配方，Windows 裸机无步骤**。
本机 winget ✅、VS C++ 生成工具 ✅（`Microsoft Visual Studio\2022\BuildTools`）⇒ 编译扩展这条路是通的。

### 5.2 装不下"效力档"（数据模型层面，改配置无用）

官方 `TransferFact` schema 里 `fact_type` 枚举**只有 `world` / `experience` 两个值**。
**没有地方放"这是 GB 30871-2022 的 5.2.3 条、现行有效、2027-01-01 实施"**。
只能塞进 `context`（自由文本）/ `metadata`（字符串键值）/ `tags`（**用于硬过滤**）。
⚠ 用 tags 硬过滤"现行有效"→ 猜错一条就可能把作废规范当现行引用。

### 5.3 抽取模型有硬门槛：输出须达 **65,000 token**

官方原文："其他模型可能可用，但**必须支持至少 65,000 输出 token** 才能可靠抽取事实"（不够只能去官方开 issue 申请豁免）。
⚠ 官方给出的 15 个"已测模型"里，**可本地跑的开源底模只有 `gpt-oss-20b` 与 `gpt-oss-120b`**（最小 20B）。
⚠ 官方对"抽取用"只点名过 **`gpt-oss-20b`**（"抽取是结构化任务，更小更快的模型表现极好"）。

---

## 六、🔴 故障复算：那 4 个"卡满 3600 秒被取消"的作业

**现象**（2026-09-28 实测日志）：
```
Task exceeded the 3600s wall-clock limit for 'batch_retain'
(stage=llm.openai.retain_extract_facts.attempt=2/4) and was cancelled.
```

**算式**：
```
LLM_TIMEOUT(300s) × (1 + MAX_RETRIES=3) ≈ 1200s/成员 × 3 个链成员 ≈ 3600s
                    ↑ 恰好等于 RETAIN_WALL_TIMEOUT 的 3600s 天花板
```
⇒ **不是模型不行，是超时调大了而重试次数没跟着调小，容错预算吃掉了整个任务预算。**

**官方处方**（configuration.mdx「Retries inside a chain」）：
> "在 failover 链里重试**非末位**成员只会拖慢切换……设 `LLM_MAX_RETRIES=0` 让它快速切换，只给**末位**成员单独预算。"

**已按此改了 `LLM_MAX_RETRIES=0`，未重启。**

---

## 七、已实测的功能结论（2026-09-28/29，20 篇真标准压测）

| 判据 | 结果 |
|---|---|
| 归档导入路能走吗 | ✅ 能。实机端点是 `POST /banks/{id}/document-transfer?on_conflict=replace`（**不是**官方文档写的 `/transfer/import?mode=merge`——实机版本旧一版） |
| 导入花不花钱 | ✅ **0 次 LLM 调用**。7,608 事实 / **140.7 秒** |
| 全量要多久 | 522,021 条外推 **≈ 2.7 小时**（一次性，可后台） |
| 精确条款命中保得住吗 | ✅ 保得住。查"标准号+条款号+正文片段"，**目标条款排第 1** |
| 标签硬过滤有效吗 | ✅ 有效。`tags=["mod:应"] + all_strict` 取回 43 条，**0 条漏过滤** |
| 召回延迟 | ❌ **8–26 秒** |
| 延迟瓶颈在哪 | ✅ **99% 在重排**。关掉后 22.4s → **0.245s（91 倍）** |
| 关重排的代价 | ❌ 目标条款从**第 1 名掉到第 31 名**。关重排后前 5 名全来自同一篇标准（**找对文件、找错条款**） |
| 候选池（100→5） | ⚠ 延迟降 5.1 倍，但**可召回率 7/8 → 5/8**；n=8 太小，定不出阈值 |

⚠ **我自己在 §15 犯过一次错并已收回**：当时说"降候选池 ⇒ 重排打 fewer 分 ⇒ 变快"，
官方 `retrieval.md` 明写**重排预筛上限与检索预算无关**，**机制解释是错的**（延迟数字本身没错）。

---

## 八、⚠ 明确**未做/未测**的（别当结论）

| 事项 | 状态 |
|---|---|
| 四条新配置生效 | ❌ **未重启**，`/version` 仍报 `observations=False` |
| 重启 | ❌ 未做。**必须走 DSH 重启，绝不手工跑 exe**（理由见第二节） |
| 探针库清理 | ❌ 未做（`probe-import-20` / `probe-clean-20`，1.5 万条试验数据混在生产库） |
| uv 旧程序清理 | ❌ 未做（`archive-v0\qFPW5JnKx50Rbwf4`，1.28 GB，已不被使用）。**建议留作回滚保险** |
| 升级到 v0.10.1 | ❌ 未做。**实机 v0.10.0 / 71 路径，官方文档 v0.10.1 / 77 路径** |
| 主模型成本 | ❌ **未测**。且历史用量因只留 1 天已不可查 |
| 换成外部 PostgreSQL | ❌ 未做。⚠ 它**解决不了中文分词**（pgroonga 只有 Docker 配方） |
| 中文分词 | ❌ 未解决 |
| 「大白话零重合」问题 | ❌ 未测。项目侧实测：**53% 提问与原文零字重合；47% 有钩子但只有 4.4% 进前五** |
| 网页管理界面 | ⚠ 曾可用（`npx @vectorize-io/hindsight-control-plane`，:9999），**现已自行退出**。**未设访问密钥**（日志：`No API key configured (public access)`） |

---

## 九、⚠ 事故留痕（今天两次，都已恢复）

| 时间 | 事件 | 结果 |
|---|---|---|
| 2026-09-29 11:33 | **我手工跑 `hindsight-api.exe` 重启**，绕过了插件 | 🔴 继承了本会话的 `no_proxy`（含 IPv6 `[::1]`）⇒ 启动即崩 `Invalid port: ':1]'`；修掉代理变量后再次起来，**又因没走 profile 而连到了空的 `hindsight` 实例**，`banks: []`，看起来数据全丢 |
| 同日 11:33 | 恢复 | ✅ 显式指定 `postgresql://…@127.0.0.1:5432/hindsight` 后，**16 库 / 11.8 万事实全部回来**；数据 6.18 GB **全程未被删未被覆盖** |
| 2026-09-29 16:55 | 插件用 uv 重装了一份 Hindsight | 版本仍 **0.10.0**，数据未动；随后 DSH 宿主在次日 01:02 重启带出了 01:03 的服务重启 |
| 2026-09-29 20:17 | 改 `dsh.env` 时 | 🔴 **我加的 `ENABLE_OBSERVATIONS=true` 被文件末尾原有的 `=false` 覆盖**（同键两次，后者胜）⇒ 复核时抓到并修正 |

---

## 十、给评估者的三个问题

1. 主模型免费窗口到期后，**在不违反"不用付费托管模型"前提下**，`gpt-oss-20b`（官方唯一点名的抽取底模，权重开源）在本机 16 GB 显存 + **三值量化**（现役 27B 三值模型实测占 9.10 GiB）上是否可行？**未测。**
2. 中文分词是硬约束（§5.1），**换外部 PG 也解决不了**（pgroonga 无 Windows 裸机步骤）。是否值得为它引入 Docker？
3. 那 9 张知识页与 11.9 万条未归并的事实，**先补归并（要钱）还是先补分词（不要钱但解决不了）**？
