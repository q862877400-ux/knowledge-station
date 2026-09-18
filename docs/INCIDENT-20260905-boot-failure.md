# DSH 事故复盘：2026-09-05 boot-failure（已处理）

- 事故标记：`C:\Users\Zegel\.dsh\guard\pending-incident.json`（kind=`boot-failure`，时间
  `2026-09-05T03:11:11.739Z` = 本地 11:11:11）
- 事故报告：`C:\Users\Zegel\.dsh\guard\logs\incident-1788577871730.md`
- 处理结论：**根因已定位到"层"，但"具体哪个改动"已不可考（证据被覆盖/轮换）；系统当前健康，回滚已自愈。**
  本文件是这次事故的唯一书面留档（会话结束后不再依赖对话记忆）。

## 1. 有证据的结论

1. **失败模式 = `crashed`，不是超时、不是渲染崩溃。**
   `boot-guard.ps1` 第 105 行：`Wait-Healthy` 只有"探测不健康 **且** 进程已退出"时才返回 `crashed`。
   日志 `[11:10:43] started server (pid 30296)` → `[11:10:45] server not healthy (crashed)`，
   即第一次尝试的 `dsh web` **在启动后约 2 秒就退出**。同机正常启动需要 20–60 秒
   （11:01:18 那次 ok 用 67 秒，11:17:43 那次用 50 秒），2 秒级失败明显是**启动期即退**。
2. **守卫的自愈动作 = 回滚 profile 安装文件 + 重试。**
   `[11:10:46] 回滚 web -> 快照 20260905-110225-811`（= 11:02:25 上次成功启动时自动存的"复活币"），
   重启后 21 秒内健康：`[11:11:07] OK rolled-back-retry`。
   回滚恢复的是四个安装文件：`package.json` / `pnpm-lock.yaml` / `pnpm-workspace.yaml` / `cordis.patch.yml`
   ⇒ 根因位于这四个文件在 **11:02:25–11:10:41** 之间的某次改动；回滚已把它消除，问题不复现。
3. **当前状态健康，未复发。**
   `http://127.0.0.1:3080/` 返回 **HTTP 401**（服务在监听、只是缺 `?token=`，属正常鉴权，非故障）；
   事故报告里"profiles 与最近良好快照对比：web — 无差异"；此后 9/17 09:03、9/18 07:52、9/18 09:06
   多次启动均成功（每次都存了复活币）。

## 2. 为什么"具体是哪个改动"查不到了（诚实边界）

- `boot-guard.ps1` 第 65–66 行把 `server-<stamp>.out/err.log` 路径**只算一次**，重试复用同一路径
  ⇒ **崩溃那次的 stderr 被重试进程的输出覆盖**。现存 `server-20260905-111041.err.log` 里只有重试
  进程的 ComfyUI MCP 启动行，第一次尝试的真实报错已丢。
- 回滚目标快照 `20260905-110225-811` 已被 3 级轮换删除；只剩 `pre-rollback` 备份
  `rollbacks\web\20260905-111045-724`（那是"坏"的那一份）。拿它和今天的 profile 比对，差异里混入了
  9/5 之后的正常演进（9/11 移除 dsh-schedule、fuhuobi 0.3.10→0.3.13、新增 ks-dsh-plugin 等），
  无法反推当次改动。
- **已排除一条假设**：曾怀疑是"我自己装的 KnowledgeStation 插件把 boot 弄坏"。实测那份坏
  `cordis.patch.yml` 里**没有** `ks-dsh-plugin` 行（今天的 profile 里也没有），假设不成立。

## 3. 处置与规避建议

- **不做**：不改 `node_modules/dsh-fuhuobi`（属部署方包，`pnpm install` 会覆盖，改了也留不住）。
- 手工重启 DSH 时，若 guard 报 `crashed`（秒级失败），**直接在前台跑一次 `dsh web`** 看真实报错，
  不要只依赖 guard 日志（崩溃现场会被重试覆盖）。
- 动过 profile 安装文件（加/升/删插件）后，先前台跑一次 `dsh web` 确认能起，再交回 guard 托管。
- 上游建议（dsh-fuhuobi）：① 每次尝试用独立日志名（`server-<stamp>-attempt1/2`），别复用；
  ② 保留最后 N 份回滚目标快照，别让崩溃现场被轮换掉。
