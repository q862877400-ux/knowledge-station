# 国标有效性查询源分类与多渠道备份矩阵（2026-08-27 实测定型）

> 目的：KnowledgeStation 存量国标状态体检（31,632 个标准号）需要一个**多渠道冗余**的
> 权威查询体系——单渠道被限流时仍有备份。本文按国标分类映射查询源，并给出**分档
> 多渠道备份清单**（主用/备份/受限/待补），附实测证据与体检脚本路由策略。

## 一、国标分类 → 权威查询源

| # | 国标类别 | 编号特征 | 归口 | 必查源 | openstd 收录 |
|---|---|---|---|---|---|
| 1 | 强制性国标 | GB XXXXX | 市场监管总局 | cssn/openstd/std.samr | ✅ |
| 2 | 推荐性国标 | GB/T XXXXX | 市场监管总局 | cssn/openstd/std.samr | ✅ |
| 3 | 指导性技术文件 | GB/Z XXXXX | 市场监管总局 | cssn/openstd/ndls | ✅ |
| 4 | 食品安全国标 | GB 5009/2760/2716 等 | **国家卫健委** | **cssn**/ndls | ❌ |
| 5 | 工程建设国标 | GB 5xxxx | **住建部** | **cssn**/ndls | ❌ |
| 6 | 强制转推荐历史版本 | GB→GB/T 同号 | 市场监管总局 | **cssn**（跨前缀） | ❌ |
| 7 | 行业标准 | AQ/HJ/YB/JB | 各归口部门 | hbba/dbba/ttbz/mee/mem_gov/mohurd | 部分 |

**结论**（2026-08-27 实测）：openstd 仅覆盖 1/2/3 类；食品安全/工程建设/转换标准
（4/5/6 类）openstd 全部查无——此前 270 条 miss（53%）的根因。**cssn 一渠道覆盖 1-6 类**。

## 二、多渠道备份分档清单（实测）

### ① 主用（已 adapter 化，无验证码）
| 渠道 | 域名/接口 | 覆盖 | 状态+发布/实施 | 备注 |
|---|---|---|---|---|
| **cssn** ⭐ | `cssn.net.cn/api/standards/list?keyword=` | **全覆盖 1-6 类** | 现行/被代替/作废/未生效 + a101/a205 + CCS/ICS | **首选**，跨前缀 picker 解 GB↔GB/T，单请求契约 |
| **spc** | `spc.org.cn/basicsearch?text=` | 全覆盖（与 cssn 同源 SPCELEC） | 状态+发布/实施 | 与 cssn 同源，互备 |

### ② 备份（可用，无验证码）
| 渠道 | 域名/接口 | 覆盖 | 状态+日期 | 备注 |
|---|---|---|---|---|
| **std.samr** | `std.samr.gov.cn/gb/search/gbQueryPage?searchText=` | 普通国标(1/2/3 ∩) | STATE + 发布/实施 + 历史版本全 | 200 JSON，**实测 GB 30871-2022 现行** |
| **openstd** | `openstd.samr.gov.cn/bzgk/std/std_list?p.p2=` | 仅 1/2/3 类 | 四态+日期 | 无食品安全/工程/转换（miss 高） |
| **csres 工标网** | `www1.csres.com/s.jsp?keyword=` | 全类别**题录** | 标题/题录（GBK，状态需按行解析） | 出售网站，**实测 GB 30871-2022 命中**；GBK 编码，作题录备份 |
| **bzfxw 标准分享网** | `www.bzfxw.com/so/index.php?keyword=` | 全类别**题录/下载** | 题录+资料下载页 | **实测 GB 30871-2022 命中、无验证码**；标准下载站，作题录备份 |

### ③ 兜底（有验证码/受限）
| 渠道 | 接口 | 覆盖 | 备注 |
|---|---|---|---|
| **ndls** | `ndls.cnis.ac.cn/api/standard/list` | 全覆盖 | **Jiasule 5320 验证码**；IP 惩罚期 100% 拦截；机场/数据中心 IP 直接挑战；详情给**废止日期/代替链**（唯一有废止日期的） |

### ④ 实测受限 / 反爬 / 需登录（本机三轮扫描，2026-08-27）
第一轮：xuetutu / biaozhun.org / antpedia / stdxx / bzzg —— TLS 握手断连或 404/需登录。
第二轮：sac.gov.cn（官方门户，非标准查询接口）/ cnis.ac.cn（跳转页）/ biaozhuns（BBS 搜索需另外参数）/
gongbiaowang（搜索返回 404）/ doc88 / docin / chem17 / antpedia —— 搜索多为 JSON/JS 渲染或需登录。
第三轮：广东/浙江标准化平台（SSLError/404）/ 企业标准公示 qybz（SSLError）/ 安规/标准库/标准分享xzdz/bzdown
（需登录/反爬）——地方与企标（DB/Q）非国标，对国标体检价值低。
**卫健委食品安全平台 sppt.cfsa.net.cn（无头浏览器实测）**：是「国家卫健委智慧健康服务平台/食品安全风险评估
业务应用」**内部应用，需用户名+短信验证码登录**——非公开查询接口，无法作公开渠道；cssn 已覆盖其数据。
住建部工程建设标准源需逆向前端——留权威背书，体检不依赖。

### ⑤ 行业/部门渠道（已有，巡检用）
hbba（行标 sacinfo）/ dbba（地标）/ ttzb / mee（生态环境 HJ）/ mem_gov / mohurd / govcn。

## 三、体检脚本路由策略（`scripts/std_status_check.py`）

- **第一轮（默认 `--channel cssn`）**：全覆盖主查，随机间隔 `--gap-min/--gap-max`。
- **备用路由**：cssn 被限 → `--channel openstd`（普通国标）→ `--channel ndls`（需验证码，
  直连住宅 IP + 冷却）→ csres 题录兜底（需 GBK 解析）。
- **resume 契约**：`results.jsonl` 只跳过 `found=True` 且无 error 的号；失败/查无自动续查；
  多轮追加同号保留最后一条（报告脚本已去重）。
- 渠道能力矩阵决定降级顺序：`cssn > openstd/std.samr > csres > ndls`。

## 四、反爬组合（所有渠道统一）

curl_cffi **chrome TLS 指纹**（默认 transport）+ 浏览器 UA/Referer 模拟 + 契约内 `_pace`
限速（1.0s）+ 脚本随机抖动（`--gap-min/--gap-max`）+ 验证码长冷却 + 指数退避重试 +
Clash IP 旋转（对 ndls 实测无效——机场 IP 信誉差，保留给其他场景）。

## 五、状态「到期翻转」（2026-08-27）

体检从 cssn 拿「即将实施(upcoming) + 实施日期(a205)」，本地按实施日期**到点自动翻现行**，
不等巡检。**读取时惰性决议**：`src/core/knowledge/legal_status.py::resolve_status`
（upcoming + `effective_from`(YYYY-MM-DD) ≤ 今天 → effective）。已接入
doc_list/doc_categories/检索证据/时效提醒 + clause_repo 带出 effective_from。
零写库、即时生效、schema 冻结不变。若需真正改库+变更日志，可加后台扫描落库（write_queue+event_log）。

> 关键坑：cssn 曾误判是 keyword 传**无空格全大写** `GB5009.247-2025`（拆词成 2025 捞噪声），
> 正确传**带空格完整号** `GB 5009.247-2025`（精确行排第 1）；跨前缀 picker 解决 GB↔GB/T。
