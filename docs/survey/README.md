# 项目现状地图

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 这是什么

**这个项目当前状态的地图。** 目的是让接手的 Agent **不必从零读整个项目**，
查表就知道东西在哪、长什么样、谁引用谁、验过没有。

## 我（做这份地图的人）的边界

**只检查、只记录。不判断对错，不改任何东西。**
所以下面看到「某函数只被提到 1 次」「某模块没有 docstring」「某文档没入链」
—— 这些**都是计数，不是结论**。该不该改由你判断。

## 怎么用（按你要做的事查表）

| 我要做什么 | 看哪份 |
|---|---|
| 找某个功能在哪个文件 | [`02-code-map.md`](02-code-map.md) |
| 查某个函数有没有别人用 | [`03-cross-ref.md`](03-cross-ref.md) + `data/symbols_py.json` |
| 查某张表有哪些列 | [`04-data-shape.md`](04-data-shape.md) |
| 查某条接口在哪实现 | [`05-api-surface.md`](05-api-surface.md) |
| 查某块有没有测试 | [`06-test-surface.md`](06-test-surface.md) |
| 查某份文档说什么 / 有没有人链它 | [`07-doc-surface.md`](07-doc-surface.md) |
| 查门禁验什么 | [`08-gate-surface.md`](08-gate-surface.md) |
| **先看引擎怎么起、端口令牌在哪** | [`09-runtime.md`](09-runtime.md) |
| **看已观察到的事实（不下结论）** | [`10-observed.md`](10-observed.md) |
| 想知道检查怎么做的、漏没漏 | [`00-method.md`](00-method.md) |

## 机器可读数据（优先读这个，别读散文）

```
docs/survey/data/
  inventory.json    每个文件一条
  symbols_py.json   每个 Python 符号一条（含 text_hits）
  schema.json       每张表 / 列 / 索引
  endpoints.json    每条路由
  tests.json        每个测试文件 + 引用映射
  docs.json         每份文档 + 出入链
  gates.json        门禁步与冒烟套
```

## 怎么重新生成（数字过期了就重跑）

```powershell
.venv\Scripts\python.exe scripts/survey/00-inventory.py
.venv\Scripts\python.exe scripts/survey/01-symbols.py
.venv\Scripts\python.exe scripts/survey/02-surface.py
.venv\Scripts\python.exe scripts/survey/03-render.py
```

重跑很便宜（三个生成器合计约 30 秒）。**改了代码就重跑，不要手改 md。**

## 这份地图**不覆盖**什么（明确边界）

| 不覆盖 | 为什么 |
|---|---|
| 运行时真实行为 | 静态检查只能看到「代码写了什么」，验不了「跑起来会怎样」 |
| 前端符号的 AST 级清单 | 没有现成 TS AST 工具链，用正则，**近似** |
| 测试的运行期覆盖率 | 要 coverage 数据，本检查没取 |
| `tools/gov-qa` 948 MB 的内容细节 | 只查结构与归属，隐私是抽样（写明是抽样） |
| 浏览器里的像素效果 | 需要真浏览器 |
| 任何「该不该改」的判断 | 明确不属于本检查 |