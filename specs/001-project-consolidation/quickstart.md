# 快速验证：怎么证明本特征真达成了

**Feature**: 001-project-consolidation | **Date**: 2026-10-05

本文件是**验收运行指南**。每条给：命令 + 期望输出 + 失败长什么样。
**这些是开工前后都要跑的**——开工前跑一遍存基线，收口再跑一遍比。

---

## 前置

```powershell
Set-Location "D:\AI\work space\zcode"
```

**开跑前必做**：记录基线，否则无法证明"没改坏"。

```powershell
# 别人的未提交改动必须逐字节一致（SC-009）
git status --porcelain | Out-File "$env:TEMP\before-status.txt"
foreach ($f in @("pelican-bike.html","tests/test_jev_cn_baseline.py",
                 "docs/research/HINDSIGHT-CAPABILITY-AUDIT-2026-09-28.md",
                 "docs/research/HINDSIGHT-FACTCHECK-2026-09-30.md")) {
  (Get-FileHash $f -Algorithm SHA256).Hash
}
```

---

## V1. 断链为 0（SC-001）

**这是最重要的一条，且 MUST 独立于门禁做**（门禁扫不到全部文档）。

```powershell
# 全仓搜旧文件名（把 OLD 换成对应表里的现名，逐条跑）
git grep -n "OLD-FILENAME" -- . | Where-Object { $_ -notmatch '^docs/archive/' }
```

**期望**：无输出。
**失败长相**：任何一行输出 ⇒ 有残留引用。

**补充检查**（markdown 链接目标是否存在）：

```powershell
python scripts/docs/check-links.py
```

**期望**：`断链 0 处`。
**注意**：该脚本随本特征新建；若尚未建，**必须建**，不许用"人工看过"顶替。

---

## V2. 文件名分类一致（SC-002）

**抽 20 个文件，只看路径判断分类，与对应表比对。**

```powershell
# 机械辅助：随机抽 20 个
git ls-files "docs/**/*.md" | Get-Random -Count 20
```

**期望**：20/20 与对应表归属一致。
**失败长相**：任何一个文件的归属说不清，或与表不符。

---

## V3. 顶层条目全有归属（SC-003）

```powershell
Get-ChildItem "." -Force | Select-Object -ExpandProperty Name
```

**期望**：每一个名字都能在 `docs/README.md`（大 map）里查到归属。
**失败长相**：有任何一条查不到。

---

## V4. 历史可查，步数 ≤ 3（SC-005）

**动作**：从仓库根 `README.md` 出发，只按文档里的指引走，找一份归档件。

**期望**：≤ 3 步到达。
**失败长相**：需要先猜、或要走 4 步以上。

---

## V5. 外人只读 wiki 能答对（SC-004）

**动作**：找一个**从未读过本仓**的 agent，只给 `README.md`，问三类问题：

1. 这个项目的目标是什么？
2. 现在做到哪一步了？
3. 想改「XX 功能」，该动哪个子系统？

**期望**：正确率 ≥ 80%。
**失败长相**：答不出、或答错主要事实。

**注意**：这条**必须用没读过本仓的 agent**。用我自己验证无效——我已经知道答案，
会不自觉地替文档补全（本仓已有"父代理看串了"的实测记录）。

---

## V6. 组件契约覆盖（SC-006）

```powershell
$subs = Get-ChildItem "src\core" -Directory | Where-Object Name -notmatch '^__'
"代码里的子系统: $($subs.Count)"
$docs = Get-ChildItem "docs\wiki\components" -File -Filter "*.md" -EA SilentlyContinue
"契约文档: $($docs.Count)"
$missing = $subs.Name | Where-Object { $_ -notin ($docs.BaseName) }
if ($missing) { "缺: $($missing -join ', ')" } else { "覆盖 100%" }
```

**期望**：`覆盖 100%`。

---

## V7. 门禁通过、基线不降（SC-007）

```powershell
pwsh -File scripts/run-gates.ps1 -Quick     # 改动面
pwsh -File scripts/run-gates.ps1 -Full      # 收工前
```

**期望**：退出码 0；测试通过数 ≥ 开工前。
**注意**：退出码 3 = "有人在跑门禁"，不是失败。

---

## V8. 当前真源一份没少（SC-008）

**动作**：比对开工前后 `docs/` 里的**当前真源**文件清单。

```powershell
# 真源 = docs/ 下不在 archive/ 与 research/ 的 md
git ls-files "docs/*.md"
```

**期望**：只增不减（`INDEX.md`、`wiki/` 是新增）。
**失败长相**：任何一份真源消失。

---

## V9. 别人的东西没被动（SC-009）

```powershell
git status --porcelain | Out-File "$env:TEMP\after-status.txt"
Compare-Object (Get-Content "$env:TEMP\before-status.txt") (Get-Content "$env:TEMP\after-status.txt")
```

**期望**：其它会话那几份的**状态与哈希都没变**。
**失败长相**：它们出现在 `Compare-Object` 结果里，或哈希变了。

---

## 验收总表

| 验证 | 判据 | 命令 |
|---|---|---|
| V1 | 断链 0 | `git grep` + `check-links.py` |
| V2 | 20/20 分类一致 | 随机抽样 |
| V3 | 顶层条目 0 个无归属 | 列顶层 + 对 map |
| V4 | ≤ 3 步到归档件 | 手动走 |
| V5 | 外人答对率 ≥ 80% | 派一个没读过本仓的 agent |
| V6 | 契约覆盖 100% | 目录比对 |
| V7 | 门禁绿、基线不降 | `run-gates.ps1` |
| V8 | 真源只增不减 | `git ls-files` |
| V9 | 别人东西逐字节一致 | 哈希比对 |
