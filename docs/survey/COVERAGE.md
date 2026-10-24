# 覆盖对账（九个面）

> **由 `scripts/survey/04-reconcile.py` 生成。**
> 这份文件的用途：让下一棒一眼看到**哪些面查全了、哪些只是抽样**。

## 一、九个面各自覆盖到什么程度

| 面 | 口径 | 结果 | 判据 |
|---|---|---|---|
| A 文件面 | 受控 3,584 + 未跟踪 754 − 生成物 14 = 4,324；另被忽略 468 条 | ✅ 全量枚举 | 甲+乙−戊 == 清单条数 |
| B 符号面（Python） | 1,271 个 .py → 解析成功 1,271 / 失败 0 → 7,025 个符号 | ✅ 全量枚举 | 成功+失败 == 总数 |
| D 数据面 | 种子库反射：表 59 / 列 470 / 索引 42 | ✅ 全量枚举 | 表数 == sqlite_master |
| E 接口面 | 后端 176 条（装饰器 176） + 前端注册 37 条 | ✅ 全量枚举 | 装饰器命中 == 输出条数 |
| F 测试面 | 测试文件 184 / 静态 def 2,567 | ✅ 全量枚举 | 文件数 == tests/ 下实际数 |
| G 文档面 | 文档 249 份 / 孤儿 117 份 / 链接 570 条 | ✅ 全量枚举 | 文档数 == docs/ 下实际数 |
| H 门禁面 | 步 15 / 冒烟套 44 | ✅ 全量枚举 | 套数 == SUITES 条数 |
| 生成物齐备 | 20/20 份存在 | ✅ | 每份都落盘 |
| 深化面 JSON | 9/9 份存在 | ✅ | 模块/接口/配置/表读写 |
| I 运行时面（实测） | 真启动引擎，探 176 条端点；状态分布 200:37, 400:1, 404:29, 409:1, 422:36, 500:1, timeout:71 | ✅ 已实测 | 起引擎 + 逐条调用（隔离数据目录） |
| I' 运行时面（说明） | 手写（`09-runtime.md`），每条标已验证/未验证 | ⚠ 部分未验证 | 启动/端口/令牌/数据目录的说明 |

## 二、明确**没有**覆盖的

| 项 | 为什么 |
|---|---|
| **运行时真实行为（最大缺口）** | **从未真正启动引擎、从未调过任何端点** —— 静态检查只能看到代码写了什么，验不了跑起来会怎样 |
| **需求编号体系** | 代码注释里到处引 `R24` / `F-xx` / `NOT-DOING #16`，但 `REQUIREMENTS-v4.3.md`（208 KB）**没有通读** ⇒ 编号指什么、哪条被撤了，本检查**答不上来** |
| **业务规则的语义** | 抓到了正则/判据的**符号与行号**，但「什么算条款头」这类规则的**含义**要读正文才知道 |
| **数据样例** | 记了每张表在种子库的行数，**没抽样看行内容**（隐私敏感的表更没看） |
| 测试运行期覆盖率 | 要 coverage 数据，本检查没取 |
| 前端符号的 AST 级清单 | 没有现成 TS AST 工具链，用正则，**近似** |
| `tools/gov-qa` 948 MB 内容细节 | 只查结构与归属；隐私是**抽样** 3/594 个文件 |
| 浏览器像素效果 | 需要真浏览器 |
| 除旧工作区之外的绝对路径 | 通用扫描器误报率 >90%，已弃用 |
| `var/data` 74 GB 逐部核 | 只做了统计 |

## 三、怎么复核这份对账

```powershell
.venv\Scripts\python.exe scripts/survey/00-inventory.py --check
.venv\Scripts\python.exe scripts/survey/01-symbols.py --check
.venv\Scripts\python.exe scripts/survey/04-reconcile.py
```

## 四、数字过期了怎么办

重跑四个生成器（合计约 30 秒），**不要手改 md**：

```powershell
.venv\Scripts\python.exe scripts/survey/00-inventory.py
.venv\Scripts\python.exe scripts/survey/01-symbols.py
.venv\Scripts\python.exe scripts/survey/02-surface.py
.venv\Scripts\python.exe scripts/survey/03-render.py
.venv\Scripts\python.exe scripts/survey/04-reconcile.py
```