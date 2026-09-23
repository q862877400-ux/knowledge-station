# verify-seeds —— 2026-09-24 那批复核留下的**可复用种子**（不是门禁的一部分）

> **为什么放在仓里**：这四份东西原本躺在 `var/tmp/` 里，而那个目录被 `.gitignore` 挡着
> ⇒ 收尾清树会**连证据一起没**（本仓已有"删了复核改前树、原始证据永久丢失"的先例）。
> 它们**没有**被任何脚本引用、**不进**门禁链 —— 是留给下一批的**起点**，不是已接线的判据。
> 出处与结论见 `docs/DEVELOPMENT-HISTORY.md` §10.184（残余登记 A 表）。

| 文件 | 是什么 | 怎么用 | 谁产的 |
|---|---|---|---|
| `hookscan2.js` | 比父代理那把 **sound 的**静态扫描器：能解 import 别名、`const um = useMemo` 不动点、本地含挂钩的助手函数，并递归全树 | `node hookscan2.js <目录>`（需要能 resolive 到本仓的 `node_modules/typescript`） | B6 复核（A10/A11）。父代理那把 `-SimpleMatch` 式的文本扫描**已被复核亲手绕过**（`const _b6h = useMemo` ⇒ 扫描报 NO-SUSPECT、运行时探针报 #300） |
| `repro-ccs-high1.py` | 「补全分类号」按刷新会**追加第二条** CCS 标签、而读侧只取第一条 ⇒ 刷新静默无效 的最小复现 | `& <venv python> repro-ccs-high1.py <要测的树>`；改前树 = **FAIL**、改后树 = **PASS** | B4 复核给的最小复现，父代理做成可传树的版本；B3a 用它做端到端验收 |
| `b1-reingest-e2e.py` | 「重新解析」不许丢目录归属的**真机**端到端：真库**副本** + 真 PDF + 真解析器 | `& <venv python> b1-reingest-e2e.py`（可传 doc_id）；**不碰真库** | 父代理（B1 的证据）。⚠ 它自己踩过一次坑并修好：回读必须连**副本**、不能连真库（否则报假 FAIL） |
| `b6-faceswitch.patch.py` | 给 `plugin/scripts/ui-render-shot.mjs` 加 `--face`（真点标签条）/ `--initial-face` 的补丁 ⇒ 生成"运行时切面探针"，能在**改前**复现黑屏的 #300/#310、套上修复后 5/5 路径全绿 | 见文件头的用法说明 | B6 复核。**建议优先接进门禁**（残余 A 表第 1 条）：文本扫描对这类病根不 sound，运行时探针才是对的判据 |

⚠ **两个已知边界**（照抄复核的原话，别当成"已完备"）：
1. `hookscan2.js` 的**完备性未被证明** —— 复核只堵了"别名 + 本地含挂钩的助手"两类，是否还有第三类绕过未证。
2. 切面探针在切面之后即退出 ⇒ **不产 png**，它的判据是**退出码 + React 原始报错**；真宿主/真槽位
   （`sidebar.right.pane.tab`）那一层从未被测过。

## 用它们做"改前 / 改后"对照：临时建一棵树就行（那些提取树收尾时已删）

本文件入库时，2026-09-24 用过的那 9 棵提取树**已经按 B8 清掉了**。要复现"改前 FAIL / 改后 PASS"
这种对照，自己建一棵临时树即可（**别在主仓里试**）：

```powershell
git -C 'D:\AI\work space\zcode' worktree add --detach "$env:TEMP\ks-seed-tree" <要测的提交>
# 需要跑界面/冒烟时，两份依赖都要**真拷贝**（别用 junction/符号链接，否则 esbuild 会把绝对路径打进产物）：
#   plugin/node_modules 与 仓库根 node_modules
```

对照用的提交（都还在历史里）：
| 用途 | 改前（问题态） | 改后（修好态） |
|---|---|---|
| `repro-ccs-high1.py` | `9460344`（分类号三层链那批的尖端） | `master` |
| `b6-faceswitch.patch.py` | `724b210~1`（黑屏修复的前一笔） | `724b210` 或 `master` |
| `b1-reingest-e2e.py` | —— （B1 是"补上搬运"，没有"改前树"这一说） | `master` |

**入库时的 sha256 前缀**（用来核"这份种子后来有没有被人改过"）：
`9F93022B0EB858A8` b1-reingest-e2e.py ｜ `6792648D2FCDD867` b6-faceswitch.patch.py ｜
`E56F143994C56703` hookscan2.js（与复核报告里给的一致）｜ `41791C55FCB2914E` repro-ccs-high1.py。
