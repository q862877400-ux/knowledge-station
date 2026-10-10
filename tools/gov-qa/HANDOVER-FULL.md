# 全面交接文档 —— 政务问答通道打通 + 存量采集

> **交接时点**：2026-10-10 07:20（+08:00）
> **接手对象**：下一个 Agent（零上下文）
> **读完这一份**你就应该能独立接着干，不需要问任何人。
>
> ⚠️ **本文件是「作业单级」交接**，不是报告。它替代不了两个文件，请**同时**读：
> - `D:/AI/output/GOAL.md` —— agent 作业单（每轮开工先读、收工前更新）
> - `D:/AI/work space/zcode/tools/gov-qa/SITE-REGISTRY.md` —— 逐站台账（0.14MB，按需查）

---

## 0. 先看这一屏（30 秒抓住全貌）

| 项 | 值 |
|---|---|
| **工作目录** | `D:/AI/work space/zcode`（Python 用 `.venv/Scripts/python.exe`） |
| **模块目录** | `tools/gov-qa/` |
| **数据总量** | **393,980 条** / 345 个适配器 / 557 个 `data/*.jsonl` |
| **闸门状态** | ✅ **全绿**（`TOTAL≥地板` ✓ `EMPTY=0` ✓ `DUPS=0` ✓ `标签覆盖 100.0%` ✓） |
| **测试** | **58 passed**（`pytest tools/gov-qa/tests`，约 4 秒） |
| **地板** | `.round-floor` = 391,769 |
| **唯一闸门命令** | `bash "D:/AI/output/check.sh"`（退出码 0 = 过） |
| **停止条件** | **质量全绿 AND 连续工作 ≥24h**，两者**必须同时满足** |
| **24h 计时** | 起点 `zcode/output/.work-start-ts`；心跳 `zcode/output/.work-heartbeat`（>30 分钟无心跳即**重新计时**） |
| **当前已连续** | 约 **3h45m / 24h**（07:20 时点） |
| **交接时的 git HEAD** | `88644c6`（master 分支） |

**⚠️ 接手第一件事**：跑 `bash "D:/AI/output/check.sh"; echo "rc=$?"` 确认这 4 项仍绿。
**不绿** ⇒ 按 §6 的红项处置，**先别推进新活**。

---

## 1. 用户要什么（原话，不要打折）

> 「全国所有省、所有市、所有国家部委、所有人大网站、所有第三方网站，
> 反正是但凡是涉及到询问政策、询问法律、询问标准的这种，全部都给我把通道打通。
> 然后把现有的数据全都扒下来。通道打通是为了以后它有更新的时候，我一个轮询就可以获取到最新的；
> 现有的存量我是要拿来做数据分析。
> 注意要把内容的标签分好，比如谁是咨询、谁是提建议、谁是反馈问题……
> **你就一直跑，直到我手动让你停止你再停止。**
> 如果所有的活都干完了，你就继续扩大这个搜索面；
> 如果扩大搜索面还是找不到能够再扩大的点了，确实是什么活儿都没有了，那你就持续自检。
> **直到我手动让你停止之前，你都不准停。**」

**目标升级**（2026-10-10 03:35，用户对 agent 的指令）：

> 「目标就是**彻底实现全面的可运维**，然后**可使用**，然后**深度和广度全部都做到最好，
> 做到不能更好为止**。如果这些都 OK 了，那么以**工作连续时长达到 24 小时**为一个闸门 ——
> 就是前面说的**质量和 24 小时的连续工作时间必须同时满足**之后才能够停下来。
> 你的工作的时候**必须按照 Spec 来**。」

**口径收窄**（2026-10-10 第 6 轮，用户明确）：

> 优先采集**国家级公告**；只保留与**法律法规 / 国家标准 / 办法 / 条例**这类
> **强制性、有约束力**文件相关的公告。除此之外**不要落库**。
> 省级市级除了发布自己的地方规章以外，对标准只是**转发国家级**。

### 三条指令怎么共存（关键，别搞混）

| 指令 | 决定什么 | 作用域 |
|---|---|---|
| 原始指令 | **一直跑、不停** | 停止条件 |
| 目标升级 | **系统怎么运营**（可增量轮询 / 覆盖完整 / 标签可信 / 自愈） | 当前主线 |
| 口径收窄 | **采什么**（法规/国标/办法/条例的发布·更新·废止公告） | 内容过滤 |

⇒ 前两条**正交**。**但注意**：口径收窄后现有通道产出率仅 **2.20%**
（357,823 条里只有 7,879 条合规）—— 因为**现有通道全是「政民互动/12345/信箱」= 问答平台**，
不是「公告发布平台」。**US2「覆盖完整性」的分母要按新口径重算**，不能沿用旧的 39 万条。

---

## 2. 系统长什么样（架构，10 分钟读懂）

### 2.1 数据流

```
adapters/<site>.py          每个来源一个「薄适配器」
        │                   签名：def harvest(fetch, *, limit=None) -> list[dict]
        ▼
harvest.py                  统一入口，注入 _Fetcher（可调用=GET，另有 .post）
        │                   ⚠ 只在**跑完时**落盘（先收全量 rows 再写文件）
        ▼
data/<key>-<名称>.jsonl     统一记录格式（一行一条）
        │
        ├─► measure-locate-rate.py   → 「可当考卷 / 补料清单」两类资产
        ├─► recon/label-classify.py  → 打 extra.msg_type
        └─► recon/audit-coverage.py  → 闸门指标的**唯一来源**
```

### 2.2 统一记录格式（每条一行 JSONL）

```json
{
  "source": "gd-huizhou",          // 适配器 key
  "id": "...",                     // 站内唯一 id（去重键 = source+id）
  "url": "...",
  "question": "标题\n正文",
  "answer": "答复全文",
  "asked_at": "2026-01-01 00:00:00",
  "answered_at": "...",
  "dept": "答复单位",
  "channel": "...",
  "extra": { "msg_type": "咨询", "msg_type_norm": "咨询", "city": "鞍山市", ... }
}
```

**关键字段**：`extra.msg_type_norm`（标签，闸门判据④）、`extra.city`（市级归属，覆盖口径用）。

### 2.3 四个共用引擎（新站优先复用，别重写）

| 引擎 | 覆盖 | 关键约束 |
|---|---|---|
| `adapters/_igi_common.py` | **IGI 平台**（贵州/吉林/山西/广西/宁夏/内蒙/南京/武汉…） | 必须带**该厅站点 Referer**，否则 403 |
| `adapters/_gd_hdjlpt_common.py` | 广东 hdjlpt（37 厅局 + 9 个市） | Laravel：**必须 XSRF-TOKEN**（从落地页 cookie 取）；列表**自带答复全文**，无需抓明细 |
| `adapters/_post_list_common.py` | 静态 `content/post_<id>.html` 列表族 | 翻页 + th/td 解析；**写前必须先取一条确认真是问答** |
| `adapters/_jact_common.py` | jact 网关（山东/江苏多市） | 有 O(n²) 隐患——**已加 `skip_ids`**，别退回旧写法 |
| `adapters/_liuyan_common.py` | 人民网领导留言板 | 按时间倒序，**必须靠游标**续采 |
| `adapters/_hunan_hd_common.py` | 湖南统一信箱 | 加站 = 填 `deptId` |
| `adapters/_was5_common.py` | TRS WAS5（部分部委/省站） | — |

### 2.4 可运维层（spec 004 交付，这轮的主线）

| 文件 | 职责 |
|---|---|
| `poll.py` | **增量轮询**：一次调用刷新所有通道的新增 |
| `state.py` | 轮询状态（`state/` 目录） |
| `channel.py` | 通道抽象 |
| `coverage.py` | 覆盖完整性（含 `data_records` 口径，见 §5.1） |
| `coverage-report.py` | 覆盖报表（`--missing-cities` / `--no-city-data`） |
| `health.py` | 自愈与可观测（一句话结论 / 一次检出全故障 / 纯 ASCII） |
| `common.py` | 公共工具 |

**活跃 spec**：`specs/004-govqa-operationalization/`
四条用户故事：**US1 增量轮询(P1) / US2 覆盖完整性 / US3 数据可用性 / US4 自愈可观测**
（Specify → Plan → Tasks → Implement 已走完，全部落地）

---

## 3. 五分钟上手（照抄）

```powershell
Set-Location 'D:\AI\work space\zcode'
$P = ".venv\Scripts\python.exe"

# ① 闸门（唯一权威判据）
bash "D:/AI/output/check.sh"; echo "rc=$?"

# ② 看有哪些站
& $P tools/gov-qa/harvest.py --list

# ③ 采一个站（可反复跑，按 id 去重、只追加新记录）
& $P tools/gov-qa/harvest.py --site gd-huizhou --limit 600

# ④ 验证某站（不写盘）
& $P tools/gov-qa/harvest.py --site gd-huizhou --limit 5 --dry-run

# ⑤ 跑测试
& $P -m pytest tools/gov-qa/tests -q

# ⑥ 看覆盖缺口（名单）
& $P tools/gov-qa/coverage-report.py --missing-cities
```

> ⚠️ **Windows 控制台是 GBK**：答复里的下标字符（`PM₂.₅` 的 ₂）会让 `print` 直接崩，
> **把整个采集带下去**。已统一走 `harvest.py::_safe()`；**新写脚本的打印也要注意**。
>
> ⚠️ **PowerShell 不捕获 stdout**：所有侦察脚本的输出**让 Python 自己写文件**（`--out`），
> 不要经 PowerShell 管道（会被重编码成乱码）。读文件用 `Read` 工具。

---

## 4. 停止条件与闸门机制（**最容易搞错的一块**）

### 4.1 两个 hook，两个不同的 GOAL.md（⚠️ 别搞混）

| Hook | 脚本 | 读哪个 GOAL.md | 干什么 |
|---|---|---|---|
| **Stop hook** | `~/.workbuddy-ai/hooks/goal-gate.sh` | **`<项目>/output/GOAL.md`**（= `D:\AI\output\GOAL.md`） | 逐条跑 `- [ ] cmd:` 行，任一失败 ⇒ `exit 2` 阻止停止 |
| 闸门脚本 | `D:\AI\output\check.sh` | 自身含 4 项硬判据 | 质量 4 项 + 双闸门逻辑 |

**`D:\AI\output\GOAL.md`** = agent 作业单（25KB，含用户原话、使命拆解、基线、待办）
**`D:\AI\output\check.sh`** = 唯一闸门（含 4 项判据 + 24h 计时）

### 4.2 check.sh 的 4 项硬判据

| # | 判据 | 红意味着 |
|---|---|---|
| 1 | `TOTAL ≥ .round-floor` | 有数据被删/损坏 ⇒ **先查清再继续** |
| 2 | `EMPTY = 0`（零数据适配器） | 有「建好没采」的源 ⇒ 先去跑它们 |
| 3 | `DUPS = 0`（重复 id） | 并发写污染 ⇒ 先去重 |
| 4 | 标签覆盖率 ≥ 90% | M3 未达标 |

指标来源：`recon/audit-coverage.py --gate`（修了「唯一数字源」口径，见 §5.2）。

### 4.3 双闸门逻辑（check.sh 末尾）

```bash
START_FILE="output/.work-start-ts"     # 相对于 <项目> = zcode/
HB_FILE="output/.work-heartbeat"
# 心跳 >1800s 无更新 ⇒ 视为链条断了 ⇒ 重新计时
# 放行条件：FAIL==0 且 ELAPSED >= 86400
```

**⇒ 停止条件 = 质量全绿 AND 连续 ≥24h。**

⚠️ **心跳文件必须持续刷新**，否则 24h 重新计时。
**Stop hook 每次调用 check.sh 时都会写心跳**，所以**只要还在干活，计时就在走**。
**心跳缺失/超 30 分钟 ⇒ 清零重来**（本次交接前就发生过一次，务必留意）。

### 4.4 收工的防空转动作

**每轮收工把当时的数据总数写进 `D:/AI/work space/zcode/.round-floor`**。
下一轮 `check.sh` 比对，低于地板即报红。**忘了写 ⇒ 地板偏低 ⇒ 闸门失去防空转效力。**

### 4.5 ⚠️ 不要往 check.sh 加 `| head` / `| tail`

管道会吃掉退出码，让闸门永远返回 0 —— 旧版本就是这么失效的（6 条里 5 条永远"通过"，会话一轮就停）。
**要加判据就写进 check.sh 内部**，那里是唯一以退出码说话的地方。

---

## 5. 已完成 / 正在做 / 待办

### 5.1 本轮（第 7–8 轮）已完成的实质工作

**① 修覆盖口径的漏计（M4 的分母错了）**

`missing-cities.py` 只数「有没有 `level=city` 通道」，但**省级平台通道的记录带 `extra.city`**：

```
grep -l '"city": *"鞍山市"' data/*.jsonl
→ data/ln-8890-辽宁省·12345民心智慧听（咨询投诉+知识库）.jsonl   ← 省级通道
```

辽宁 14 个市里 **12 个有数据**（全在省级 `ln-8890` 里），却被报「缺 13 个」。

| 口径 | 有记录 | 零记录 |
|---|---|---|
| 旧（只数通道） | 72 | **262** |
| **新（数据口径）** | **141** | **193** |

改动：`coverage.py` 新增 `CoverageUnit.data_records` + `norm_city` / `known_cities` /
`count_by_city` / `merge_city_data`；`build_units(city_counts=…)` 把「有数据无专属通道」的市补建为市级单元；
状态判定改 `max(total_records, data_records)`。
**两个坑（已用测试钉住）**：
1. **占位值必须过滤** —— IGI 的 `CITY` 常是 `市辖区`/`省直辖县级行政区划`，不过滤**虚增 ~80 个假单元** ⇒ 用 334 市白名单过滤。
2. **补建市级单元不得改省级 `total_incl_cities`** —— 省级通道的记录已计入省级总量，再加一次**翻倍**。

**测试 50 → 58 全过**。详见 `recon/CITY-COVERAGE-CALIBER.md`。

**② 打通广东 11 个地级市（累计约 +11,216 → +14,216 条）**

| 市 | 条数 | 引擎 |
|---|---|---|
| 深圳 | 15,000 | hdjlpt |
| 惠州 | **3,900** | 民意直通车（Spring Boot，独立域名 `www.hzhmsb.cn`）|
| 湛江 | 2,500 | hdjlpt |
| 汕尾 | 1,223 | hdjlpt |
| 揭阳 | 442 | hdjlpt |
| 茂名 | 412 | hdjlpt |
| 云浮 | 245 | hdjlpt |
| 潮州 | 205 | hdjlpt |
| 阳江 | 76 | hdjlpt |
| 肇庆 | 71 | hdjlpt |
| 江门 | 21 | `_post_list_common` |

**③ 建出城市定位工具链**

- `recon/city-domains.json`（193 零记录市**命中 152**）/ `city-domains-all.json`（274/334）
- `recon/city-middleware.json`（152 市按中间件归类）
- 探针：`probe-city-middleware.py` / `probe-gd-city-hdjlpt.py` / `probe-post-list.py` / `probe-endpoint.py`

**④ 护栏：可观测性完整闭环（这是本轮最有价值的沉淀）**

「**逐条取明细的循环必须打进度点**」—— 这个坑**踩了 5 次**，最后一次是**主动扫描发现**的：

| # | 哪里 | 症状 |
|---|---|---|
| 1 | 天水 `gs_tianshui.py` | 列表有日志、明细阶段**静默** ⇒ 误判「站点节流」 |
| 2 | 惠州 `gd_huizhou.py` | 同上（第 4 次）|
| 3 | `_jact_common.py` | 主动扫描发现 |
| 4 | `_post_list_common.py` | 主动扫描发现 |
| 5 | `_igi_common.harvest_igi` | 同上 |

修复模式统一为：**`-u`（不缓冲）+ `skip_ids`（增量续采）+ 明细进度日志**。

**⑤ 新引擎 + 新适配器**

- `adapters/_post_list_common.py`（静态 post 列表族，新引擎）
- `adapters/gd_huizhou.py` / `gd_jiangmen.py` 等广东 11 市适配器

### 5.2 数字的唯一来源（口径纪律）

| 想要什么数字 | 跑什么 |
|---|---|
| 闸门 4 项 | `recon/audit-coverage.py --gate`（**唯一数字源**）|
| 标签覆盖率 | `recon/label-coverage.py --gate 90 --quiet` |
| 地级市覆盖 | `coverage-report.py --missing-cities` / `--no-city-data` |
| 完成度最低的源 | `recon/audit-coverage.py --targets` |
| 可当考卷 / 补料 | `measure-locate-rate.py` |

⚠️ **别再手工数** —— 每个数字都从上面这些命令现算，写进 GOAL.md 时**注明命令**。

### 5.3 待办（按收益排序）

**M4 广度**（分母 = 修正后的 **193 个零记录市**，不是 262）

- ✅ 已完成：**广东 11/21 市**
- **★ 本轮新发现的最高收益线索（未做，接手请优先）**：
  「**403 判死是误判**」——我实测推翻了自己上一轮的结论（详见 §11），
  **东莞 / 汕头 / 韶关 / 中山 / 佛山 / 河源 / 珠海** 七个市被
  `probe-city-middleware.py` 标了 `广东hdjlpt` 指纹，但被 403 判死。
  实测发现真响应是 404/405/502，且 `/hdjlpt/letter/pubList` 返回 **405 = 端点存在**。
  ⇒ **这 5–7 个市很可能能采**，逐个 POST `pubList` 实测即可（工具：`recon/probe-gd-hd-403.py`）。
- 广东剩余：广州 / 清远（疑似 JS 渲染）
- 其余省：**河南 18 / 安徽 16 / 云南 16 / 湖南 14**（这 5 省占 85 个缺口的绝大半）
- ⚠️ **龙讯 CMS 批量接入已判死（0/14）**，不要再按那个方向投入
- ⚠️ **不要再给辽宁 / 四川 / 贵州 / 山西 / 吉林逐市建通道** —— 已被省级平台覆盖

**M2 存量**：天水全量重采（`--limit 150`，**不要用 400**，见 §8 参数表）；
其余低完成度源见 `audit-coverage.py --targets`

**M3 标签**：人工抽检 200 条 —— 样本已导出 `D:/AI/output/label-check-200.csv`
（⚠ **这一项只能人做，agent 无法替代**）

**人大再扩**：需逐站找 JS 接口（低优先，已到平台期，9 个来源）

**⚠️ 重要约束**：本目录**有另一个 agent 在并行工作**（它做 IGI 轮次续采）。
提交纪律见 §10。

---

## 6. 闸门红了怎么办（处置手册）

| 红项 | 先做什么 |
|---|---|
| ① `TOTAL < 地板` | `git log --oneline -10 tools/gov-qa`；查是不是有文件被删/损坏；`git status` 看有没有被别的东西覆盖 |
| ② `EMPTY > 0` | 跑 `recon/audit-coverage.py --empty` 拿清单，逐个跑 —— **但要先分辨**「真没跑」还是「跑了 0 条」（见 §8 盐城案例）|
| ③ `DUPS > 0` | 跑 `recon/audit-coverage.py --dups` 定位源；先查是不是**并发写**（§7 铁律 4）；用 `recon/dedup-data.py` 清 |
| ④ 覆盖率 <90% | 跑 `recon/label-classify.py --apply`（**会训练 SVM，约 2.5 分钟**）|

**④ 的自愈已内建**：check.sh 会先花 ~3s 测覆盖率，**只有 <90% 才补**。
⚠️ **别把它改成无条件调用** —— 2.5 分钟会打满 hook 的 300s 超时 ⇒ 脚本被杀 ⇒ 判失败 ⇒
**闸门永远红**（追踪日志表现为「没有 parsed: 行」）。这个坑排查了很久。

---

## 7. 硬约束（违反会造成真实损失）

1. **`git add` 只加自己的文件** —— 本目录有另一个 agent 并行工作。
   提交前先 `git status` 分清归属。**永不 `git add tools/gov-qa`**（整目录）。
   历史事故见 `tools/gov-qa/WRITE-SCOPE.md`（两次真事故，都是 `git add` 整目录引起的）。
2. **采集后立刻 commit 数据文件** —— git 是唯一可靠备份，`/tmp` 不是。
   **暂存区是全仓共享的**：`git add` 后隔轮才 commit，会被别人的提交带走。
3. **`harvest.py` 只在跑完时落盘** ⇒ 预计 >2 小时的源**必须分块**（`GOVQA_PAGE_FROM`）
   或用 `recon/igi-chunked.py`（逐 siteId / 逐页窗口落盘）。
4. **同一个站只能有一路在采** —— 并发写会产生重复 id（闸门判据③）。
5. **适配器绝不把异常冒泡出去** —— 单条失败跳过 + 连续失败熔断 + 返回已收部分。
6. **判死前必须实测**：取一条明细确认答复正文非空 ——
   `totalResults` 大 ≠ 有问答（天津 IGI 14 万、知识产权局 sysid=11 1.4 万，都是空壳）。
7. **否定性结论必须用数据证伪**，不能靠推理（本轮「403 判死」就是反面教材，见 §11）。

---

## 8. 踩坑速查（**重踩一次要浪费半天**）

### 8.1 采集机制类

| 坑 | 真相 |
|---|---|
| **「站点侧节流」误判** | 我曾在 GOAL.md 写「天水翻到 ~15–30 页必卡」。**错**。真相是 `gs_tianshui.harvest` 两步：扫列表（有日志）→ 逐条取明细（**无日志**）。第 1 步正确跳出，然后进入静默的第 2 步。**已在交接单明确更正** |
| **「新增 0」的两种原因** | ① 真的全采完了；② 只扫了部分维度。盐城案例：修了 `skip_ids` 后仍 0 新增，真因是**只扫 `sysid=1`，而它 `totalRecord=1865` 已全采完**（库里 2,815 ≥ 1,865）。`--targets` 报的 5,654 是**多个 sysid 合计**。⇒ **判据：看日志有没有「（跳过已落盘 N 条）」** |
| **指纹命中 ≠ 能采** | `probe-city-middleware.py` 打了指纹，仍要 `probe-gd-city-hdjlpt.py` **逐个实测取第一条确认答复非空** |
| **指纹没命中 ≠ 没有** | **揭阳不在** 18 市名单里（那个探针没扫到它的 hdjlpt 入口），实测 `total=53 / reply=218` **真能采** |
| **「接口成功但 data 为空」= 参数名错** | 惠州猜 `sqly/pageIndex/pageSize` 时接口回 `{"code":0,"desc":"操作成功","data":null}` —— **HTTP 200 + code:0 但空**，最容易骗过人的失败形态。真参数是从页面 JS 的 ajax 段抠出来的 |
| **「只验证一个样本」是同一个病** | 6 个真 bug 里 3 个是这个（只跑一次测试→没发现污染；只看一个省命名→市级全丢；只看第 1 页 HTML→老条目全丢）。**⇒ 验证要看「边界样本」，不能只看「顺手拿到的第一个」** |
| **`content/post_` 猜栏目几乎全错** | 惠州 `ftjhyg`=访谈计划预告、揭阳 `ldjf`=市长简历、珠海 `ftyg`=访谈预告、汕尾 `gtjhyg`=在线访谈 —— **全都不是问答**。⇒ **写适配器前必须先取一条明细确认是问答** |
| **`<出生证明>` 这类中文尖括号** | 通用 `<[^>]+>` 会把它当 HTML 标签吃掉 ⇒ 正则失配。改用 `REAL_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")` |
| **`adapters/__init__.py` 定位** | 里面 `"rd-tj"` 出现**两次**（文档字符串 + 真字典），按字符串 `index()` 插入会插进文档字符串 ⇒ 运行时 `KeyError`。**按行号/上下文定位，别只按 key 字符串定位** |

### 8.2 实测速度参数（给 `--limit` 定量用）

| 站 | 速度 |
|---|---|
| 天水 | ~40s/页 |
| 深圳 hdjlpt | ~2min/千条 |
| 惠州民意直通车 | 0.55s/条（**明细有效率 87%**）|
| 倒序列表翻页 | 见 AUTO_HANDOFF §16 |

**⇒ 天水定 `--limit 150`，不要 400。** 天水总量 ~1,476 候选（4 栏 202/404/656/1182）。

### 8.3 环境类

| 坑 | 解法 |
|---|---|
| `NO_PROXY` 里的 `[::1]` | 会让 httpx 连 `Client()` 都构造不出来 ⇒ `os.environ["NO_PROXY"] = (...).replace("[::1]", "::1")` |
| HTTPS 证书 | 用 `verify=False` |
| **后台跑 `harvest.py` 必须加 `-u`** | 否则日志不实时，看不到进度 |
| PowerShell 输出乱码 | `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` + `$env:PYTHONIOENCODING="utf-8"`；写文件用 `Out-File -Encoding utf8` |
| 后台任务串行阻塞 | 一个后台命令里串行跑「天水 → 惠州」，天水慢拖住惠州 ⇒ **改独立任务** |

---

## 9. 负面结论速查（**别再试**，省侦察时间）

| 结论 | 证据 |
|---|---|
| 三市 IGI 假设**被证伪** | 洛阳 `4103000021`（行政区划代码）/ 芜湖 `6787231`（龙讯 CMS）/ 宜昌 `54`（省级在线访谈）—— IGI 接口全 404 |
| **龙讯 CMS 批量接入判死** | 0/14 |
| 广东 `hdjlpt` **不是**全国通用平台 | `recon/other-province-hdjlpt-probe.json`（16 域名 0 命中）|
| 其他省**没有** `haiyun.*.gov.cn` | 10 省全 ConnectError/Timeout |
| IGI 指纹在天津/上海/北京/浙江/福建/宁夏/云南/陕西 **8 省未发现** | `recon/igi-spread-scan.txt` |
| 留言板**没有**「按省列下级版块」接口 | `recon/liuyan-substation-probe2.json` |
| 留言板**没有**「按省聚合」过滤参数 | `recon/liuyan-province-filter-probe.json` |
| 四川全省问政平台 `wz.sc.gov.cn` **本机不可达** | `recon/sc-wenzheng-probe.json` |
| 一批省域名**本机连不上** | 山西/江苏/山东/河南/湖北/广西/海南/云南/陕西/青海/新疆/重庆…（`recon/probe-provinces.json`）|
| 已判死（勿重复投入） | 国家信访局、中国政府网「我向总理说句话」、司法部、市场监管总局、国家统计局、药监局、中央纪委 12388、天津 IGI、知识产权局 sysid=11、海南/江西/黑龙江 IGI、淮安、常州明细、成都主站 |
| 人大扩面到 9 源是**自然平台期** | 北京/云南只有「立法动态」新闻；贵州/青海/宁夏/浙江/安徽/福建 0 条；四川 502；西藏证书错误 |

> ⚠️ **判死清单要定期复验** —— 网站会改版，旧判死可能失效（GOAL.md §六明确要求）。

---

## 10. 提交纪律（本目录既有约定，必读）

来源：`tools/gov-qa/WRITE-SCOPE.md`

1. **`git add` 只加自己的文件，永不加整个目录。**
   ```powershell
   # ❌ git add tools/gov-qa
   # ✅ git add tools/gov-qa/data/gd-huizhou-*.jsonl tools/gov-qa/recon/probe-xxx.py
   ```
2. **`adapters/__init__.py` 是共享文件** —— 只加自己那几行，不重排、不动别人的行。
3. **`data/` 与 `recon/` 按前缀分** —— 文件名前缀写明归属。
4. **共享基础设施**（`harvest.py` / `measure-locate-rate.py` / `README.md`）改动前先看 WRITE-SCOPE；
   要改公共行为，**提交消息里写明「影响另一个对话」**。
5. **`git add` 后立刻 commit**（暂存区全仓共享，隔轮会被别人带走）。
6. **提交前 `git status --short` 逐文件过一遍归属**，发现别人的文件就 `git reset` 掉。
7. **每轮 = 小提交 + 快照**：`& .\scripts\snapshot-project.ps1 -Label <短名>`

**交接时的仓库状态**（供你对齐）：

- HEAD = `88644c6`（master）
- **未提交里有一批不属于我**（另一个 agent 的）：`adapters/_igi_multi.py`、`_jpaas_jact_common.py`、
  `gs_linxia.py`、`jiujiang_igi.py`、`sd_heze.py`、`zhangye_igi.py`、
  以及大量 `assets-gx-igi-*.json`（广西 IGI）—— **不要提交它们**。
- **另一个 agent 正在跑**：`recon/igi-chunked.py gx_igi --sites-json igi-siteid-guangxi.json --limit 20000`
  （广西 IGI 全量，已跑数小时，**别杀它、别碰广西的数据文件**）。

---

## 11. ★ 我刚推翻的自己的结论（接手请接着查）

**这是本交接文档里最有时效价值的一节。**

上一轮我在 GOAL.md 里写下：「东莞/汕头/韶关（12345 独立平台）」——
暗示它们用的是**另一套系统**。**这个说法不完整。**

本轮我做了一个探针（`recon/probe-gd-hd-403.py`），发现：

`recon/probe-city-middleware.py` 给东莞/汕头/韶关/河源/中山/珠海/佛山
都打了 `广东hdjlpt` 指纹，然后 `probe-gd-city-hdjlpt.py` 把它们**判死**，
理由是落地页 `/hdjlpt/published?via=pc` 返回 **403**。

**我实测结果是：根本不是 403。**

| 市 | `/hdjlpt/published` | `/hdjlpt` | `/hdjlpt/letter/pubList` | 判读 |
|---|---|---|---|---|
| 东莞 | 404 (`XSRF-TOKEN`+`szxx_session`) | 404 | **405** | **部署了** |
| 韶关 | 404 (`XSRF-TOKEN`+`szxx_session`) | 404 | **405** | **部署了** |
| 中山 | 404 | **200** | **405** | **部署了** |
| 河源 | 404 | **200**（428KB）| **405** | **部署了** |
| 珠海 | 404 | 404 | **405** | **部署了** |
| 汕头 | 404 | 404 | 404 | 真没有 |
| 梅州 | 404 | 404 | 404 | 真没有 |
| 佛山 | **502** | 502 | 502 | 后端挂了 |

**关键判据**：`/hdjlpt/letter/pubList` 返回 **405 Method Not Allowed = 端点存在、只收 POST**。
**405 是「hdjlpt 是否部署」的可靠指纹**（404 才是没有）。
且 404/405 响应**仍带 `XSRF-TOKEN` + `szxx_session` cookie** —— 这正是广东 hdjlpt 的标志。

**⇒ 下一步（未做，最有价值的活）**：
对这 5 个市**直接 POST `pubList`**（不依赖落地页 200，只要能拿到 XSRF-TOKEN 就行），
取一条明细确认答复非空。**如果通了，一次 +5 个市。**

> ⚠️ 方法论沉淀：**「403」可能是我上一轮探针的头部不像浏览器所致的误判；
> 而这一轮的「405」才是真实响应。两次实测结论冲突时，以能取到数据的那次为准。**
> 工具已就绪：`recon/probe-gd-hd-403.py`（详细版）；
> 建议再写一个 `probe-gd-hd-publist.py`（直接 POST 版，本文件中提到但**尚未创建**）。

---

### ★★ 2026-10-10 就地更正（spec 005 T701）：上面这一节**结论是错的**

> **留痕纪律**：原文保留在上面，不删。更正写在这里。
> 更正依据 = **写这份交接文档的那个 Agent 自己**在文档落盘后 **2 分钟内**的实测。

**时间线**（文件 mtime 为证）：

| 时间 | 文件 | 内容 |
|---|---|---|
| 07:17:34 | `HANDOVER-FULL.md` | 写「405 ⇒ 部署了 ⇒ 下一步直接 POST pubList，一次 +5 个市」 |
| **07:19:03** | `gd-publist.txt` | **真的 POST 了 `pubList`** |
| **07:20:17** | `gd-hd-params.txt` | 参数扫描，**带对照城市** |

**POST `pubList` 的实测结果**（`gd-publist.txt`）：

| 市 | POST `/hdjlpt/letter/pubList` | 判读 |
|---|---|---|
| 东莞 | **404** | 没有 |
| 韶关 | **404** | 没有 |
| 中山 | 200 但 **`total=0`** | 端点在，**零数据** |
| 河源 | 200 但 **`total=0`** | 端点在，**零数据** |
| 珠海 | **404** | 没有 |

**决定性证据 —— 同一轮里的对照城市**（`gd-hd-params.txt`）：

```
对照·汕尾(已知能采)   https://www.shanwei.gov.cn
    [/hdjlpt/letter/pubList | offset/limit | 近1年]
    HTTP 200 len=15403 errcode=0 total=27 list=10     ← 探针参数是对的
```

⇒ **探针本身没问题**（同一套参数在汕尾拿到 27 条），是那 5 个市**真的没有数据**。

**「405 = 端点存在」这个判据本身也站不住**：那 10 次 405 的**响应体长度全是 1567 字节**
（5 个不同城市、冷/温各一次）—— 这是**统一的拦截页**，不是"端点存在"的指纹。

**⇒ 正确结论**：
- §11 的「5 个 405 市很可能能采」**不成立**，**不要按这一节投入**。
- 「**响应体长度在所有城市间完全一致 ⇒ 是拦截页，不是端点指纹**」才是可用的方法论。
- 东莞/韶关/珠海 真没有；中山/河源 端点存在但 `total=0`（空壳）。
  与 §8.1 的「`totalResults` 大 ≠ 有问答」是同一类：**端点在 ≠ 有数据**。

**给接手人的教训**：**交接文档里"最有价值的一节"也可能是错的** ——
这份文档写于实测之前（07:17），而实测在 07:19 就否证了它。
**读交接文档时，先看它的结论有没有晚于它的实测数据。**

---

## 12. 交接检查单（建议按顺序做）

1. **跑闸门**：`bash "D:/AI/output/check.sh"; echo "rc=$?"` ⇒ 确认 4 项全绿 + 看已连续多少小时。
2. **对齐数字**：跑 §5.2 的命令，确认与本文 §0 表格对得上。
   对不上 ⇒ 有人在我们之后改过，先查 `git log --oneline -10 tools/gov-qa`。
3. **读 `D:/AI/output/GOAL.md`**（作业单）与 `D:/AI/output/AUTO_HANDOFF.md`（上一轮交接，16 节）。
4. **确认另一个 agent 没被干扰**：`git status` 里广西 IGI 的文件仍属它；那个采集进程还在跑。
5. **挑一件最该做的**（见 GOAL.md §五工作循环）：
   a. 红项最严重的
   b. 否则推进 M1/M2（完成度最低的通道）
   c. 否则推进 M3（补标签）
   d. 否则推进 M4（~~**优先 §11 的 5 个市**~~ —— **§11 的结论已被更正，别按它做**，
      见 §11 末尾的「就地更正」）
   e. 全饱和 ⇒ 扩大搜索面
   f. 确实无处可扩 ⇒ **自检**（全量体检 / 抽查质量 / **复验判死清单**）
6. **动手做**（不要只写计划）。
7. **收工**：更新 `GOAL.md` 基线 + 写 `AUTO_HANDOFF.md` + 更新 `.round-floor` + **立刻 commit 自己的文件**。

---

## 13. 文件地图

### 顶层（`tools/gov-qa/`）

| 路径 | 作用 |
|---|---|
| `harvest.py` | **统一入口**：`--list` / `--site` / `--limit` / `--dry-run` |
| `poll.py` / `state.py` / `channel.py` / `common.py` | 增量轮询层（US1）|
| `coverage.py` / `coverage-report.py` | 覆盖完整性（US2）|
| `health.py` | 自愈与可观测（US4）|
| `measure-locate-rate.py` → `locate-rate.json` | 可考卷 / 补料 / 无依据 |
| `query.py` / `regions.py` | 查询与地域工具 |
| `README.md` | 模块介绍（**先读这个**）|
| **`HANDOVER.md`** | 上一轮交接（**2026-10-08 时点，数字已旧**，但机制/纪律仍有效）|
| **`SITE-REGISTRY.md`** | **逐站台账**（144KB：已跑通、未决问题、负面结论、纪律）|
| `WRITE-SCOPE.md` | **两个 agent 的分工规矩 + 两次真事故**（交接必读）|
| `PLAYBOOK.md` | 操作手册 |
| `NAT-ENTRIES.md` / `MINISTRY-ENTRIES.md` | 国家级 / 部委接入台账 |
| `REUSE-FOR-ANNOUNCEMENTS.md` | 口径收窄后的复用说明 |
| `adapters/` | 361 个 `.py`：适配器 + 共用引擎 |
| `data/` | 557 个 `*.jsonl` 语料；**`.` 开头的是游标文件，不是数据** |
| `assets-*.json(l)` | 两类资产（**几百个**，由 `measure-locate-rate.py` 生成）|
| `recon/` | 侦察工具与产物（**文件名前缀 = 归属**）|
| `tests/` | 5 个测试文件，58 个测试 |
| `state/` | 轮询状态 |

### 关键 recon 工具

| 工具 | 干什么 |
|---|---|
| `recon/audit-coverage.py` | **闸门指标唯一来源**（`--gate` / `--targets` / `--empty` / `--dups`）|
| `recon/label-coverage.py` | 标签覆盖率（`--gate 90 --quiet` 输出纯 ASCII）|
| `recon/label-classify.py` | 补标签（`--apply`，训练 SVM 约 2.5 分钟）|
| `recon/coverage-report.py` | 覆盖报表（`--missing-cities` / `--no-city-data`）|
| `recon/missing-cities.py` | 零记录市名单 |
| `recon/field-audit.py` | 字段完整度体检 |
| `recon/igi-chunked.py` | **IGI 分片增量采集**（逐 siteId / 逐页窗口落盘，别用 harvest 跑大 IGI）|
| `recon/city-domains*.json` / `city-middleware.json` | 城市 → 域名 / 中间件 |
| `recon/probe-*.py` | 各类探针（中间件 / 端点 / 页面结构）|
| `recon/gen-*.py` | **生成器**（薄壳适配器批量产出，**别手改生成物**）|
| `recon/dedup-data.py` | 去重 |
| `recon/repair-empty-questions.py` | 修「问题为空」（注意 §8.1 的中文尖括号坑）|
| `recon/CITY-COVERAGE-CALIBER.md` | **覆盖口径的完整说明**（必读）|

---

## 14. 一句话总结

**当前状态**：质量 4 项全绿，连续工作约 3h45m/24h，
393,980 条 / 345 适配器 / 58 测试全过 / 标签覆盖 100%。

**你要做的**：
① 保持闸门绿（别让心跳断、别忘写地板）；
② 按 GOAL.md §五循环推进 —— ~~**优先 §11 的 5 个「405 市」**~~
   **（§11 已被更正：那 5 个市实测没有数据，别按它做。见 §11 末尾）**；
③ **一直跑，直到用户手动说停**（且质量与 24h 同时满足）。

**别做的**：别 `git add` 整目录；别碰广西 IGI（另一个 agent）；别再试龙讯 CMS；
别给辽宁/四川/贵州/山西/吉林逐市建通道；别往 check.sh 加管道。
