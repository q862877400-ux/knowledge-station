# 覆盖对账（九个面）

> **由 `scripts/survey/04-reconcile.py` 生成。**
> 这份文件的用途：让下一棒一眼看到**哪些面查全了、哪些只是抽样**。

## 一、九个面各自覆盖到什么程度

| 面 | 口径 | 结果 | 判据 |
|---|---|---|---|
| A 文件面 | 受控 3,598 + 未跟踪 755 − 生成物 21 = 4,332；另被忽略 468 条 | ✅ 全量枚举 | 甲+乙−戊 == 清单条数 |
| B 符号面（Python） | 1,275 个 .py → 解析成功 1,275 / 失败 0 → 7,044 个符号 | ✅ 全量枚举 | 成功+失败 == 总数 |
| D 数据面 | 种子库反射：表 59 / 列 470 / 索引 42 | ✅ 全量枚举 | 表数 == sqlite_master |
| E 接口面 | 后端 176 条（装饰器 176） + 前端注册 37 条 | ✅ 全量枚举 | 装饰器命中 == 输出条数 |
| F 测试面 | 测试文件 184 / 静态 def 2,567 | ✅ 全量枚举 | 文件数 == tests/ 下实际数 |
| G 文档面 | 文档 251 份 / 孤儿 119 份 / 链接 572 条 | ✅ 全量枚举 | 文档数 == docs/ 下实际数 |
| H 门禁面 | 步 15 / 冒烟套 44 | ✅ 全量枚举 | 套数 == SUITES 条数 |
| 生成物齐备 | 22/22 份存在 | ✅ | 每份都落盘 |
| 深化面 JSON | 14/14 份存在 | ✅ | 模块/接口/配置/表读写 |
| I 运行时面（实测） | 真启动引擎，探 176 条端点；状态分布 200:37, 400:1, 404:29, 409:1, 422:36, 500:1, timeout:71 | ✅ 已实测 | 起引擎 + 逐条调用（隔离数据目录） |
| I' 运行时面（说明） | 手写（`09-runtime.md`），每条标已验证/未验证 | ⚠ 部分未验证 | 启动/端口/令牌/数据目录的说明 |

## 二、明确**没有**覆盖的

| 项 | 为什么 |
|---|---|
| ~~运行时真实行为~~ | ✅ **已收口**：真启动引擎、探 176 条端点，见 `18-runtime-probe.md`（上面 `I 运行时面（实测）` 那一行）|
| ~~需求编号体系~~ | ✅ **已收口**：扫全部 `docs/**/*.md`，97 条编号定义（61 在需求文档 / 35 在渠道方案 / 2 在归档）+ 代码引用点 + 24 条否决台账，见 `19-requirements.md` |
| ~~业务规则的语义~~ | ✅ **已收口到「字面判据 + 理由」**：从 `src/**/*.py` 抽出 291 条规则常量（160 正则 / 131 阈值），169 条带上方注释原文，见 `20-rules.md`。**仍未到「算法的完整复述」** —— 那需要逐行读函数体 |
| **数据样例** | 记了每张表在种子库的行数，**没抽样看行内容**（隐私敏感的表更没看） |
| 测试运行期覆盖率 | 要 coverage 数据，本检查没取 |
| ~~前端符号的 AST 级清单~~ | ✅ **已补**：用仓库根已有的 `typescript@5.9.3` 建真 AST（`09-web-ast.cjs`），与正则版并列，**两份各有盲区**（AST 漏 `declare module` 内的导出、正则漏 `interface/type/enum`），见 `16-frontend.md` §三之二 |
| `tools/gov-qa` 948 MB 内容细节 | 只查结构与归属；隐私是**抽样** 3/594 个文件 |
| 浏览器像素效果 | 需要真浏览器 |
| 除旧工作区之外的绝对路径 | 通用扫描器误报率 >90%，已弃用 |
| **71 条超时的确切原因** | 已按 handler 函数体关键词粗分，但 41/71 「handler 里看不出明确来源」⇒ 要定因得在超时时抓线程栈，**本检查没做** |
| **把 500 与卡死修掉** | 明确不属于本检查（业主令：只检查不治病） |
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