# 归档：项目内 `.workbuddy-ai/`（WorkBuddy 自动链的记忆与交接）

> **这是历史，不是当前真源。**

## 为什么在这里

业主 2026-10-10：「**workbuddy 现在已经不用了**，要是没啥别的影响把这些东西删除掉好了」。
删之前**先字节级归档到这里** —— 因为这批文件里**有 8 个被 5 处正式文档引用**，
直接删会让那些引用变成断链。

## 原位置

`<仓库根>/.workbuddy-ai/`（**已被删除**；本目录是它的完整副本）。

## 谁在引用这批文件（引用**已同步改到本目录**）

| 引用方 | 引的是哪个 |
|---|---|
| `docs/DEVELOPMENT-HISTORY.md` §10.214 / §10.217 / §10.228 | `memory/CHAIN-UNCLOSED-AUDIT.md` |
| `docs/NEXT-DEV-PLAN-2026-09-28.md` | `memory/CHAIN-UNCLOSED-AUDIT.md` |
| `eval/recall-funnel/exp-12-long-clause-tail/README.md` | `memory/CHAIN-UNCLOSED-AUDIT.md` |
| `docs/HANDOVER-2026-10-09.md`（§接手前先看这三条 / §自动链） | `memory/AUTO-CHAIN-HANDOFF.md`、`memory/autochain-watchdog.py` |
| `docs/verify-briefs/VERIFY-REPORT-rerank-fix.md` | `memory/AUTO-CHAIN-HANDOFF.md` |
| `docs/README.md` | 该目录本身（已改为「历史，见本目录」） |

## 内容清单（逐文件 sha256，字节级复制）

| 文件 | 字节 | sha256（前 12） |
|---|---|---|
| `memory\2026-10-08.md` | 1,772 | `8b78c795732e` |
| `memory\2026-10-09.md` | 179,762 | `1631cf27dc97` |
| `memory\2026-10-10.md` | 10,668 | `9e7494ac694c` |
| `memory\_inspect_automations.py` | 574 | `fbd2d88ff816` |
| `memory\AUTO-CHAIN-HANDOFF.md` | 5,665 | `fc80401da6ef` |
| `memory\autochain-watchdog.log` | 883 | `d3f33b86f07f` |
| `memory\autochain-watchdog.py` | 6,037 | `8801aca86e22` |
| `memory\automations\1b206fd3-357f-47a1-bf5b-e17ec5c419a3\memory.md` | 45,756 | `b4083b9fb490` |
| `memory\automations\3b1225b1-e2f4-4504-ad29-581309175fdb\memory.md` | 376 | `17f069fe5eed` |
| `memory\automations\7d23d426-8743-431f-a95e-62a3e2a6af36\memory.md` | 41,095 | `de2290097ffe` |
| `memory\CHAIN-UNCLOSED-AUDIT.md` | 30,132 | `93d612ebb24b` |
| `memory\HANDOFF-CHECKLIST.md` | 5,155 | `24a083d5057e` |
| `memory\MEMORY.md` | 15,476 | `64b9dfca9476` |

## 它原来是什么

- `memory/MEMORY.md` —— 项目长期记忆（跨会话仍成立的**环境陷阱 / 方法论 / 禁碰**）。
  ⚠ 其中若干条（如 `spawnSync` EBUSY、门禁模型 seed 判据、pytest `--basetemp`）
  **已转写进 `docs/TEST-FLAKES.md` 与 `docs/ENCYCLOPEDIA.md`**，不依赖本目录。
- `memory/CHAIN-UNCLOSED-AUDIT.md` —— 自动推进链「忽略 / 没收口」审计（2026-10-09 人工轮）。
- `memory/AUTO-CHAIN-HANDOFF.md` / `HANDOFF-CHECKLIST.md` —— 每轮覆盖写的交接单。
- `memory/2026-10-{08,09,10}.md` —— 逐日工作日志。
- `memory/automations/*/memory.md` —— 各自动化任务的执行记忆。
- `memory/autochain-watchdog.{py,log}` —— 看门狗（**已退役**，见 HANDOVER-2026-10-09 §自动链）。

## 为什么它不再被使用

WorkBuddy 应用**已于 2026-10-10 19:47 退出**（`AppShutdown reason=before_quit`），
其 `Stop` hook（`~/.workbuddy-ai/hooks/goal-gate.sh`）随之失效。
本项目的自动链此后由 **DSH 侧**推进（见 `output/GOAL.md` 与 `.codebuddy/hooks/check-full-green.sh`）。
