# 工作交接（`tools/gov-qa/`）

> **这一页是接手须知**：现状数字 + 怎么接着干 + 别再试什么。
> 模块介绍看 [README](README.md)，逐站发现与踩坑看 [SITE-REGISTRY](SITE-REGISTRY.md)，
> **两个对话同时写这个目录的分工规矩看 [WRITE-SCOPE](WRITE-SCOPE.md)**（交接前必读）。
>
> 交接时点：**2026-10-08 08:4x**（数字均为当时实测，非估算）。

---

## 一、这摊活是什么，现在到哪了

**干什么**：把**部委 / 省市**官网上的「公众问答 / 常见问题 / 留言答复」扒下来，
整理成统一记录格式，再切成两类资产 ——
① 答复点名的依据**在我们库里** ⇒ **可当考卷**；② 点名的依据**不在库里** ⇒ **补料清单**。
**为什么要**：拿**真人真问**与**官方保守答复**，替代 AI 模拟提问。

**现在到哪了（实测）**：

| 指标 | 数值 |
|---|---|
| 语料总量 | **37,457 条** |
| 来源数 | **56 个**（注册适配器 56 个；`data/` 56 个 jsonl）|
| 覆盖省级行政区 | **31 个（全国省级已铺满）** |
| 三级（省+市+县）归属 | **406 条 / 102 个省市县组合** |
| **可当考卷** | **4,048 条** |
| 补料清单 / 无依据 | 12,859 / 20,435 条 |
| 比对用的库内文档 | 8,917 份 |

**各来源量级（前几名）**：广东市监 6,134、广东人社 6,120、广东统计 4,275、
湖南生态 3,813、广东生态 3,329、广东自然资源 1,682、留言板四通道合计 1,211、
广东教育 1,165、安徽生态 145。

---

## 二、五分钟上手（照抄即可）

```powershell
Set-Location 'D:\AI\work space\zcode'

# ① 看有哪些站、什么状态
.venv\Scripts\python.exe tools\gov-qa\harvest.py --list

# ② 采一个站（可反复跑：按 id 去重、只追加新记录）
.venv\Scripts\python.exe tools\gov-qa\harvest.py --site gz-jyt --limit 30

# ③ 验证某个站（不写盘，只看取到的前 3 条）
.venv\Scripts\python.exe tools\gov-qa\harvest.py --site gz-jyt --limit 5 --dry-run

# ④ 刷新两份验收产物
.venv\Scripts\python.exe tools\gov-qa\recon\coverage-matrix.py     # 省级 × 来源 矩阵
.venv\Scripts\python.exe tools\gov-qa\recon\coverage-by-level.py   # 省/市/县 三级统计
.venv\Scripts\python.exe tools\gov-qa\measure-locate-rate.py       # 可考卷/补料/无依据

# ⑤ 每轮收尾：小提交 + 快照
& .\scripts\snapshot-project.ps1 -Label 'govqa-<短名>'
```

---

## 三、三轨状态（业主定的推进方向）

### 轨① 人民网留言板·地方流（**广度主力**）

| 通道 | key | 条数 | 说明 |
|---|---|---|---|
| 部委版块 | `people-liuyan` | 37 | 国家级；答复=`dataType==4`，网友跟帖另存 |
| 地方时间流 | `people-liuyan-df` | 172 | **按时间倒序**，靠**游标**续采 |
| 定向版块 | `people-liuyan-fid` | 245 | 按已发现 fid 轮转深采（含北京各区）|
| **分省直达** | `people-liuyan-prov` | 757 | **31 省全覆盖**，按省轮转 |

**关键机制**：省级版块**按行政区划顺序两两编号**（省委书记 `539+2i`、省长 `+1`，539~600 已全部实扫确认）⇒ 想采哪个省就采哪个省。

### 轨② 逐省平台（**省线成绩**）

| 平台 | 省 | 来源数 | 条数 | 境界 |
|---|---|---|---|---|
| `hdjlpt` | 广东 | 37 厅局 | 31,112 | 全省统一平台，一次采完全历史 |
| 湖南统一信箱 | 湖南 | 2 厅 | 4,351 | 复制薄适配器填 `deptId` |
| **IGI 平台** | **贵州** | **6 厅局** | **280** | ★ **带省/市/区三级归属**（生态 120 / 卫健 40 / 教育·人社·住建·农业农村 各 30）|
| **IGI 平台** | **吉林** | **2 厅局** | **134** | ★ 同上；须带 `Referer` |
| 问答知识库 | 安徽 | 1 厅 | 145 | 答复常点名依据 |
| 历史咨询服务 | 辽宁 | 1 厅 | 24 | 问答内联在列表页 |
| 互动知识库 | 四川 | 1 厅 | 15 | FAQ 简答 |

**IGI 是唯一能拿「县级」归属的通道**（留言板只到省市两级）——
省/市/区三级共 406 条即来自它。

### 轨③ 与另一个对话的分工

**不越界**：部委侧（`MINISTRY-ENTRIES.md` / `probe-ministries.py` / `mem_gov.py` / `mee_gov.py`）
归**另一个对话**；本对话做**省市侧**。规矩见 [WRITE-SCOPE](WRITE-SCOPE.md)——
那里记着**两次真事故**（`git add` 整目录 → 把别人写一半的文件提交了；暂存区隔轮存放 → 被别人的提交扫走）。

---

## 四、没做的事（接手请从这里挑）

1. **★ 无人值守循环已停**（宿主重启，`job_list` 已空）。
   原配方：每批 `--limit 30` 采留言板时间流，睡 65 分钟后重复。
   重启即可继续积累（游标在 `data/.people-liuyan-*.cursor`，**不会重采**）。
2. **IGI 平台还有大量厅局没探**：目前只探了生态环境、卫健、教育、人社、住建、农业农村。
   贵州/吉林其余厅局、以及**地市州一级**（`xxx.<市>.gov.cn`）都可能挂着同款 —— 用
   `recon/igi-hunt.py` 改候选表即可自动「指纹识别→抠参数→调接口验证」。
3. **两个已知但未通则的参数组合**（API 返 200 但 `n=0`）：
   贵州市场监管局（`siteId=41, appId=88`）、吉林人社（`siteId=117, appId=96, groupId=170`）
   —— 大概率 `groupId` 不对，值得再抠一次。
4. **留言板分省深度未拉平**：西部省份版块**本身存量少**（黔/滇/新/藏/甘/青 4~7 条），
   别为拉平数字反复空跑；配额留给存量大的省与市县定向。
5. **市/县级**：留言板只给两级；IGI 给三级但只有两省。全国地级市县版块编号带是
   **764~4000+（数千个）**，没有列举接口 ⇒ 只能「时间流带出 + 已发现 fid 轮转」。
6. **未落适配器的省**：天津、上海、北京、浙江、福建、宁夏、云南、陕西、甘肃、青海、
   新疆、西藏、内蒙古、黑龙江、江西、湖北、河南、山东、海南、重庆、广西、山西、河北、
   江苏、吉林（除 2 厅）、贵州（除 6 厅）…… 多数是**没有统一平台**或**域名本机不可达**（见第五节）。

---

## 五、别再试的事（负面结论速查，**省下重复侦察的时间**）

| 结论 | 证据 |
|---|---|
| 广东 `hdjlpt` **不是**全国通用平台（16 域名 0 命中） | `recon/other-province-hdjlpt-probe.json` |
| 其他省**没有** `haiyun.*.gov.cn` 主机（10 省全 ConnectError/Timeout） | `recon/haiyun-spread-probe.txt` |
| IGI 指纹在天津/上海/北京/浙江/福建/宁夏/云南/陕西 **8 省未发现** | `recon/igi-spread-scan.txt` |
| 留言板**没有**「按省列下级版块」接口（`substation` 只回空配置，4 个猜名路径 404） | `recon/liuyan-substation-probe2.json` |
| 留言板**没有**「按省聚合」过滤参数（10 个候选除 `fid` 外全被忽略） | `recon/liuyan-province-filter-probe.json` |
| 四川全省问政平台 `wz.sc.gov.cn` **本机不可达**；四川厅知识库量小（15 条） | `recon/sc-wenzheng-probe.json` |
| 一批省域名**本机连不上**（山西/江苏/山东/河南/湖北/广西/海南/云南/陕西/青海/新疆/重庆…） | `recon/probe-provinces.json` |

---

## 六、机制与坑（重踩一次要浪费半天）

1. **游标**：留言板流按时间**倒序**，不带游标每轮只新增 ~1 条（实测）。三条通道各有独立游标
   （`data/.people-liuyan-df.cursor`、`.people-liuyan-fid-<fid>.cursor`、`.people-liuyan-prov.rotation`）。
   **看到「从游标续采」才算生效**；`lastItem` 数值**递减**属正常。
2. **限流**：留言板每窗约 **40 次调用**；`PAUSE ≥ 2.5s`、单批 ≤35 条、批间歇 ≥1h。
   **403 就停**（别硬刷）；去重天然续采。
3. **IGI 接口必须带 `Referer`**（指向该厅站点），否则一律 **403**（JSON 错误体）。
4. **Windows 控制台是 GBK**：答复里的下标字符（`PM₂.₅` 的 ₂）会让 `print` 直接崩，
   **把整个采集带下去**。已统一走 `harvest.py::_safe()`；**新写脚本的打印也要注意**。
5. **归属层级**：统一从 `extra.pForumNames`（省→市→县）读；IGI 另给
   `extra.province/city/area`。**留言板只到两级**，别把「省市县全覆盖」当已达成。
6. **抓明细前先看真实标记**：我两次照旧印象写正则（四川的「解答内容：」、安徽的「问…答」）
   **实测都 0 命中**——先存一份原始 HTML 看清结构再写解析器（`recon/*-debug.txt` 就是干这个的）。
7. **留言板版块编号分层**：省 539~600 / 直辖市辖区+县级 601~763 / 地级市县 764~4000+ / 部委 5050~5120。

---

## 七、纪律（这个目录的既有约定）

1. **提交**：`git add` **只加自己的文件**，永不 `git add tools/gov-qa`；**加完立刻 commit**
   （暂存区是全仓共享的，隔轮会被别人的提交带走）。共享文件（`adapters/__init__.py`、
   `harvest.py`、`README.md`、`measure-locate-rate.py`）**只加自己那几行**，
   提交消息写明**「影响另一个对话」**。
2. **每轮 = 小提交 + 快照**：`& .\scripts\snapshot-project.ps1 -Label <短名>`。
3. **质量复核**：新通道进得快就要抽查「空答复 / 答复==问题 / 答复<10字 / 答复像问题」
   （`recon/audit-prov-fid.py` 是模板）。本模块**真出过**问题当答复、网友跟帖串位两类污染。
4. **只报证据**：数字给命令与产物路径；负面结论也要落文件（第五节就是这么攒出来的）。

---

## 八、文件地图

| 路径 | 作用 |
|---|---|
| `harvest.py` | 统一入口：`--list` / `--site` / `--limit` / `--dry-run`；注入 `_Fetcher`（可调用=GET，另有 `.post`）|
| `adapters/__init__.py` | `ADAPTERS` 注册表（**共享文件**）|
| `adapters/_liuyan_common.py` | 留言板基座（签名、游标、答复取值）|
| `adapters/_igi_common.py` | **IGI 平台基座**（列表+明细，带三级归属）|
| `adapters/_was5_common.py` | TRS WAS5 基座（部委/部分省站）|
| `adapters/_hunan_hd_common.py` / `_gd_hdjlpt_common.py` | 湖南/广东平台基座 |
| `recon/gen-gd-adapters.py` / `gen-gz-igi-adapters.py` | **生成器**（薄壳适配器批量产出，别手改生成物）|
| `recon/coverage-matrix.py` → `.md/.json` | 验收产物①：省级 × 来源矩阵 |
| `recon/coverage-by-level.py` → `.md/.json` | 验收产物②：省/市/县三级统计 |
| `measure-locate-rate.py` → `locate-rate.json` | 验收产物③：可考卷/补料/无依据 + `assets-*.json` |
| `recon/igi-hunt.py` / `liuyan-province-fid-scan.py` / `dept-hd-dig.py` | 侦察工具（自动找平台/扫编号/挖互动栏目）|
| `recon/audit-*.py` | 质量复核脚本 |
| `SITE-REGISTRY.md` | **逐站台账**：已跑通、未决问题、负面结论、纪律 |
| `data/*.jsonl` | 语料（统一格式）；`.` 开头的是**游标文件**，不是数据 |
| `assets-*.json(l)` | 两类资产 + 网友跟帖资产 |

---

## 九、接手检查单（建议按顺序做）

1. 跑 `harvest.py --list` 与 `measure-locate-rate.py`，确认数字与本文第一节**对得上**
   （对不上说明有人在我们之后改过，先查 `git log --oneline -10 tools/gov-qa`）。
2. **重启无人值守循环**（第四节第 1 条），让它自己积累留言板时间流。
3. 从第四节挑一件推进；**优先「IGI 扩厅局」**——那是唯一能扩县级覆盖的路，且已有自动化脚本。
4. 每轮收尾：刷新三份验收产物 → 小提交（消息写清「改了什么/为什么/边界」）→ 快照。
