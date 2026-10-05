# 开发史明细归档（§10.1 – §10.203）

**这里是什么**：KnowledgeStation 从 2026-09-17 起，**逐轮开发记录**的全文。
**为什么在这**：`docs/DEVELOPMENT-HISTORY.md` 的正文只留「**做过什么**」的叙事与**轮次索引**；
逐轮明细**与 `git log` 高度重复**，读者要的是「从哪看起」，不是逐轮全文。

> **移走的是位置，不是内容。** 按宪法原则 V（留痕不许悄悄删），
> 全文一字未删、一字未改地搬到这里。

---

## 文件

| 文件 | 内容 | 体积 |
|---|---|---|
| `rounds-10.1-10.203.md` | §10.1 – §10.203 逐轮全文（203 轮） | 999 KB / 11,671 行 |

**搬运方式：字节级**，不是手抄（本仓规矩：手抄实测 77 行错 2 处，2.6% 失真）。

**校验**：

| 项 | 值 |
|---|---|
| 搬运前 `docs/DEVELOPMENT-HISTORY.md` 总行数 | 11,889 |
| 保留段（L1–L218，仍在正文） | 54 KB / 218 行 |
| 搬走段（L219–L11889，即本文件） | 11,671 行 |
| **行数** | 搬走段 **11,671 行 = 原文 §10.1+ 的 11,671 行**，**一行不差** |
| **内容差异** | **恰好 22 行 = 11 对**，全部是**相对链接路径**加层级 |
| 搬走段 SHA256（前 16 位，含下述链接修正） | 见提交后的现文件 |

**⚠ 与原件的唯一差异（必须说清，不许含糊）**：
文件下沉两层后，它内部 **11 处相对链接**（`INTERACTION-DESIGN.md`、`CHANNEL-COVERAGE-PLAN.md` 等）
不再指向正确位置，**已各加一级/两级前缀**。
**除此之外，正文一字未改。**

**⇒ 怎么自己核**：

```powershell
# 把原文的 §10.1 起与本文档做 diff，差异应当【只有】22 行链接路径
python - <<'PY'
import subprocess, pathlib, difflib
old = subprocess.run(["git","show","<搬迁前的提交>:docs/DEVELOPMENT-HISTORY.md"],
                     capture_output=True).stdout.decode("utf-8")
arc = pathlib.Path("docs/archive/history/rounds-10.1-10.203.md").read_text(encoding="utf-8")
d = [x for x in difflib.unified_diff("\n".join(old.split("\n")[218:]).split("\n"),
                                     arc.split("\n"), lineterm="", n=0)
     if x.startswith(("+","-")) and not x.startswith(("+++","---"))]
print(len(d), "行差异（应为 22）")
PY
```

**实测结果：22 行差异，全为链接路径，行数 11,671 对 11,671。**

---

## 怎么查

```powershell
# 按轮次号找（例：找 10.152）
Select-String -Path docs/archive/history/rounds-10.1-10.203.md -Pattern '^#+ .?10\.152 '

# 按关键词找
git grep -n '<关键词>' -- docs/archive/history/

# 按提交号找（每轮标题后多带提交号或快照名）
git log --oneline --all | Select-String '<短号>'

# 追某份文件的历史路径（搬迁过的）
git log --follow --oneline -- <路径>
```

**轮次索引**（203 轮，只给标题）在 [../../DEVELOPMENT-HISTORY.md](../../DEVELOPMENT-HISTORY.md) 末尾。

---

## 边界

- **§一 – §九 的叙事没搬**，仍在 `docs/DEVELOPMENT-HISTORY.md` 正文——那是「从零到能跑」的经过，接手的人该读。
- **本归档不可逆地变回"当前真源"**：它记的都是当时的事，不要当作现状引用。
  要复活其中某个结论 ⇒ **作为新结论重新落进它的归属文档**。
