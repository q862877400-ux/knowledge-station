# 独立复核报告：E4 第二轮验证（批次 `e4b-round2`）

- **复核者身份**：独立复核者（**不是**作者）。本报告的数**凡标"我实测"的都是我自己跑出来的**，标"我采信"的写明来源，标"我未做"的单列。
- **主仓**：`D:/AI/work space/zcode`（Windows，bash 可用）
- **冻结 tag**：`verify-freeze-e4b-round2`（**注：是 annotated tag**，tag 对象 `599885f`，其 commit = `95cfcfb`）
- **提取树**：`git worktree add D:/AI/verify-trees/e4b verify-freeze-e4b-round2`（**已用完移除**：`git worktree remove --force` + `git worktree prune`）
- **Python**：`D:/AI/work space/zcode/.venv/Scripts/python.exe`（torch 2.13.0+cu126，CUDA 可用；RTX 4080 SUPER 16 GB，复核期间 GPU 空闲）
- **报告落盘**：本文件（UTF-8）。**本报告由复核者亲自落盘**（非转录）。

> ⚠ **提取树里 `exp.db` 的处理（照本仓第一轮复核对 `sanguo.txt` 的做法）**：`10-latency.py` / `11-prefix-ab.py`
> 硬编码引用 `../exp-4-embedding-shadow/exp.db`（**3.3 GB，被 `.gitignore` 忽略 ⇒ 提取树里没有**）。
> 我在提取树里**建了一个符号链接**（`New-Item -ItemType SymbolicLink`，**只读引用主仓那一份**），
> 使脚本**一字不改**即可运行；脚本自身用 `mode=ro` 打开，不写向量。
> 命令：`$link=D:\AI\verify-trees\e4b\...\exp-4-embedding-shadow\exp.db` → `$target=D:\AI\work space\zcode\...\exp.db`（返回 `SYMLINK_OK`）。
> 复核结束、移除提取树前已删掉该符号链接；**主仓 `exp.db` 完好**（`3519893504` 字节，mtime 未变，见 §6）。

---

## 0. 提取树首尾取证

| 时点 | `git rev-parse HEAD` | `git status --short` |
|---|---|---|
| 首（建树后） | `95cfcfb253777c8fd9393eec90266c405830903b` | **空（干净）** |
| 尾（还原后） | `95cfcfb253777c8fd9393eec90266c405830903b` | **空（干净）** |

- 我中途重跑的产物（`latency.json` / `prefix-ab-*.json*` / `verdict.json`）在还原时已 `git checkout --` 回冻结态；
  尾态各产物 SHA256 与冻结备份**逐一致**（见 §3、§4）。
- 变异**只在提取树里做**，跑完按 `git checkout` 还原（见 §4.1）。

---

## 1. 冻结事实（我机械重算，**全部与作者一致**）

```
$ git rev-parse verify-freeze-e4b-round2          → 599885f89007ee69f4752c622e8537717b1fb0c2   (tag 对象)
$ git rev-parse verify-freeze-e4b-round2^{commit} → 95cfcfb253777c8fd9393eec90266c405830903b
$ git rev-list --count 05ff39a..verify-freeze-e4b-round2^{commit} → 2
$ git log --oneline 05ff39a..<tag>
  95cfcfb docs(E4 第二轮): 归属层登记 + 补一处登记缺口（E4 第一轮从没进总纲）
  07c6a50 feat(E4 第二轮): 提问侧成本 + 查询侧指令前缀 —— 前缀 +15.84pt，嵌入成本只占向量路的 2.98%
```

- **两条提交都是本批**：`07c6a50` = 实验本体（15 文件：5 脚本 + 6 产物 + README + 第一轮 README §九）；
  `95cfcfb` = 归属文档（4 docs）。两提交时间 `2026-10-09 04:02:18 / 04:02:19 +0800`。
- **`git diff --stat 05ff39a..<tag> -- src/ plugin/` = 空**（本批**没碰生产代码**）。✅
- 全量 `--numstat`：19 文件 **1524 insertions / 0 deletions**（**纯新增**，无一行被删，见 §8）。

---

## 2. A 臂独立重跑（`10-latency.py`，提取树内）

命令（提取树里跑；`exp.db` 走上面的只读符号链接）：

```
$ "D:/AI/work space/zcode/.venv/Scripts/python.exe" eval/recall-funnel/exp-4b-embedding-round2/10-latency.py
[e4b] 考卷提问 171 条（真实串，不另造）
[e4b] clause_vec=521978 / clause_vec_qwen=521978 ✅
[e4b] CPU bge-small 冷启动 177 ms；warm p50 1.36 ms
[e4b] 参照：KNN 扫描中位 818.1 ms
[e4b] GPU Qwen3 冷启动 2913 ms；warm p50 31.34 ms；峰值显存 1164.0 MiB
[e4b] 附加 Qwen3-CPU 抽样 30 条：p50 72.87 ms
```

**逐格核对作者 README §二 表（我实测 vs 作者自报）**：

| 项 | 作者自报 | **我实测** | 一致？ |
|---|---|---|---|
| 现役 `bge-small` CPU warm p50 | 1.38 ms | **1.36 ms** | ✅（噪声内） |
| 现役 CPU warm p90 / max | 1.58 / 1.95 ms | **1.60 / 2.01 ms** | ✅ |
| 现役 CPU 冷启动 | 712.4 ms | **177.1 ms** | ⚠ 差大（见下） |
| `Qwen3` GPU warm p50 | 32.02 ms | **31.34 ms** | ✅ |
| Qwen3 GPU warm p90 / max | 34.74 / 207.86 ms | **34.02 / 66.04 ms** | ✅（max 是离群） |
| Qwen3 GPU 冷启动 | 5154.3 ms | **2913.5 ms** | ⚠ 差大（见下） |
| Qwen3 参数 | 595,776,512 | **595,776,512** | ✅ 逐位一致 |
| 峰值显存 allocated / reserved | 1149.5 / 1164.0 MiB | **1149.5 / 1164.0 MiB** | ✅ 逐位一致 |
| 副本扫描中位（521,978 行） | 819.7 ms | **818.1 ms** | ✅ |
| 〔附加·抽样 30〕Qwen3 CPU fp32 p50 | 72.88 ms | **72.87 ms** | ✅ |
| 副本 `clause_vec` / `clause_vec_qwen` 行数 | 521,978 / 521,978 | **521,978 / 521,978** | ✅ |

- **结论**：A 臂**每一格都复现**。**冷启动两项差异大**（712→177、5154→2913）——冷启动是**本机 OS 页缓存/装载**决定的一次性耗时，天然波动，**不属于"声称不成立"**；warm 读数（真正进判据的那两个）逐格吻合。
- 作者按 `latency.json` 的副本扫描 819.7 ms 算出 `32.02/819.7 = 3.91%`（副本口径）、按真库 1074.7 ms 算 `32.02/1074.7 = 2.98%`。我用重跑值复算：`31.34/818.1 = 3.83%`、`31.34/1074.7 = 2.92%` —— **同一量级，判定不变**。

---

## 3. B 臂独立重跑（`11-prefix-ab.py`，**核心读数**，提取树内）

命令同上（`exp.db` 走只读符号链接）。**跑通、EXIT=0、耗时 370.1 s**（作者自报 elapsed 636.5 s）。

```
$ ... 11-prefix-ab.py
[e4b] clause_vec_qwen=521978（应 521978）
[e4b] 20/171  35s ... [e4b] 160/171  351s
```

**结果与冻结产物对比**：

```
$ cmp prefix-ab-per-query.jsonl <冻结备份>/prefix-ab-per-query.jsonl   → 逐字节相同
$ sha256sum prefix-ab-per-query.jsonl
  5bdc5c34a2332fdb96c185c42c26040da9209f3cc8306eb24dba0554375e10e9   （与冻结一致）
$ （结果 json 逐键对比，剔除 elapsed_s）
  ALL ELSE EQUAL: True   （elapsed new=370.1 / frozen=636.5）
```

**逐格核对主终点**：

| 终点 | 作者自报 | **我实测** | 一致？ |
|---|---|---|---|
| **Vector@1000（主结果 120）无前缀 → 前缀** | 0.6833 → 0.8417 | **0.6833 → 0.8417** | ✅ |
| **主终点 Δ** | **+15.84pt** | **+15.84pt** | ✅ |
| 主结果 flip 翻进/翻出 | 19 / 0 | **19 / 0** | ✅ |
| Vector@1000（全量 171）Δ | +14.03pt | **+14.03pt**（flip 24/0） | ✅ |
| @100（120/171）Δ | +11.67 / +8.19pt | **+11.67 / +8.19pt** | ✅ |
| @20（120/171）Δ | +5.83 / +5.27pt | **+5.83 / +5.27pt** | ✅ |
| 六路并集@1000（120/171） | 0.6917→0.8500 / 0.6784→0.8187 | **逐位一致** | ✅ |
| FTS@1000（仪器对照）两臂 Δ | +0.00pt | **+0.00pt** | ✅ |

- **B 臂逐条 `per-query.jsonl` 与冻结产物**逐字节相同**（含 `rank@20/100/1000`、`union_*`、`fts@1000`）——这是**最强的复现证据**：换一次重跑，171 条的每一个读数都没变。
- 说明：`prefix-ab-result.json` 除 `elapsed_s` 外逐键相同（`elapsed_s` 是耗时字段，本就每次不同）。

---

## 4. 判据有牙（变异）

### 4.1 变异 (a)：前缀臂改成不加前缀 ⇒ 主终点必须塌 0（**我实测**）

在**提取树里**把 `11-prefix-ab.py:98` 的 `knn(qwen_vec(INSTRUCT + q), K)` 改成 `knn(qwen_vec(q), K)`（两臂都无前缀）：

```
变异后文件 sha256 = 670129a3418942bf2baa67f291130d3790ffc715086d14bceee852df7358522d
变异后第 97–98 行：
  vecs = {"noprefix": knn(qwen_vec(q), K),
          "prefix":   knn(qwen_vec(q), K)}
$ ... 11-prefix-ab.py   （EXIT=0，耗时 306 s）
HEADLINE120 delta_pp rank@1000 = 0.0
ALL171    delta_pp rank@1000 = 0.0
HEADLINE flip = {'in': 0, 'out': 0}
instr = 0 0
```

⇒ **主终点 delta 精确塌成 0.00pt**（`+15.84 → 0.00`）。**判据有牙成立**：那 15.84pt **全部**归因于前缀这一个变量。

**还原（按 SHA256）**：

```
还原前（变异态）worktree sha256 = 670129a3…
还原命令 = git checkout -- <该脚本>
还原后 worktree sha256 = 07f5bcae1f0478d0c1ae823383614d6ef5514210e90120e75aedbc4655ea36e1
还原前（变异前）worktree sha256 = 07f5bcae1f0478d0c1ae823383614d6ef5514210e90120e75aedbc4655ea36e1  ← 一致 ✅
（git blob / LF 形态 sha256 = 99976f2b…，与提交一致）
第 98 行已回到 knn(qwen_vec(INSTRUCT + q), K)
```

### 4.2 替代/补充 (b)：自己重算汇总 + 两臂互换（**我实测**）

不采信作者的 `12-verdict.py`，我从 `prefix-ab-per-query.jsonl` **逐条自己重算**：

```
HEADLINE120: noprefix rank@1000=0.6833  prefix=0.8417  Δ=+15.84pt  flip 19/0
ALL171:      noprefix rank@1000=0.6667  prefix=0.8070  Δ=+14.03pt  flip 24/0
两臂互换：  +15.83pt  →  -15.83pt（HEAD） / +14.04 → -14.04（ALL）   ✅ 符号翻转
```

⇒ 汇总可独立复现；**两臂互换符号必然翻转**（判据对"方向"敏感，不是恒正）。

### 4.3 补充 (c)：`12-verdict.py` / `13-cluster-ci.py` 各跑一遍（**我实测**）

```
# 12-verdict.py：在只含冻结输入的目录里跑 → verdict.json
$ sha256sum verdict.json → f1a2c6eae6fdf3236be87da5b5eda816f00722ec61f539f0e7be45c5efaa6e70
$ cmp verdict.json <冻结备份>/verdict.json → IDENTICAL   ✅ 逐字节复现
# 13-cluster-ci.py：连跑两次 → prefix-cluster-ci.json
$ cmp run1 run2 → IDENTICAL（sha 26c4eebd… 两次相同）    ✅ seed 写死、可复跑
$ 与冻结备份 sha 26c4eebd… 一致
读数：headline_120 Δ=15.83pt CI=[9.43, 22.73] p=0.0 flip 19/0；all_171 Δ=14.04pt CI=[8.84, 19.54] p=0.0 flip 24/0
```

- 我还用**重跑后**的 `latency.json`（新 p50 31.34 / 新扫描 818.1）跑了一次 `12-verdict.py`：A 臂落档仍为「可上线」「共存无压力」，B 臂仍为「进生产评估」——**判定对重跑稳健**。

---

## 5. 仪器对照是否真的成立（**我独立核**）

- 核 `prefix-ab-result.json` 的 `instrument_control`：`round1_selfcheck_mismatch_items = 0`、`fts_mismatch_items = 0`。✅
- **独立验一个**（不采信作者脚本的比对）：我直接拿 `prefix-ab-per-query.jsonl` 的 `noprefix` 臂与 `../exp-4-embedding-shadow/ab-per-query.jsonl` 的 `ctx` 臂**逐条逐字段**比：

```
instrument1 mismatches: 0
  noprefix vs ctx rank@20 / rank@100 / rank@1000        : 0 / 0 / 0
  noprefix vs ctx union_same@20/100/1000                : 0 / 0 / 0
  noprefix vs ctx union_prod / fts@1000                 : 0 / 0
instrument2（两臂 fts@1000 差异）: 0
```

⇒ 无前缀臂**逐条复现第一轮 `ctx` 臂**（不止 `rank@1000`，**8 个字段全 0 不一致**）；FTS 两臂**0 处差异**。**仪器对照成立**——那个 +15.84pt 不是仪器漂移、也不是"换了别的东西"。

---

## 6. 诚实边界（**我实测**）

| 项 | 声称 | **我实测** | 一致？ |
|---|---|---|---|
| 真库 `clause_vec` 行数 | 663,634 | **663,634** | ✅ |
| 真库有没有 `clause_vec_qwen` | （隐含：没有，影子表只在副本） | **无此表**（`OperationalError: no such table`） | ✅ |
| 副本 `clause_vec` / `clause_vec_qwen` 行数 | 521,978 | **521,978 / 521,978** | ✅ |
| 真库 `clause_vec` mtime 有没有被本批改动 | 未动 | **`2026-10-08 18:55:44`（跑前跑后一致）** | ✅ |

- 命令：`sqlite3.connect("file:…knowledge.db?mode=ro", uri=True)` + `load_vec_extension(conn)`（从 `src.core.storage.sqlite_db` 导入）。
- 真库**主文件 mtime 未变**（`3105525760` 字节）。⚠ 诚实说明：我以 `mode=ro` 打开真库时，SQLite 会**触碰 `knowledge.db-shm`**（mtime 变 `04:06`）——这是 WAL 模式的**共享内存读文件**，不是数据写入；真库**主文件 mtime 与字节数均未变**，`clause_vec` 行数未变。
- 副本 `exp.db` mtime 也**未变**（`2026-10-07 04:15:40`），主仓文件完好（`3519893504` 字节）。

---

## 7. 防漂移（阈值单点 / 冻结哈希）

### 7.1 ⚠ **阈值不是单点——发现第二份硬编码**（我 grep 机械核）

- 声称（README §五 + `12-verdict.py` docstring）："脚本里**不重复写死**阈值，防两处漂移"。
- **实测：不成立。** `12-verdict.py` 把阈值**又写死了一遍**：

```
12-verdict.py:34   if gpu_p50 <= 100:
12-verdict.py:40   a_vram = … if vram <= 4096 else …
12-verdict.py:47   if delta_head < 8:
12-verdict.py:49   elif delta_head < 10:
```

- 这几个数（`100` / `4096` / `8` / `10`）**同时**写在 `stop-loss.json`（`"<= 100 ms"` / `"<= 4096 MiB"` / `"< 8pt"` / `"8 ~ 10pt"` / `">= 10pt"`）。
- `12-verdict.py` 虽然 `json.load` 了 `stop-loss.json`，但**只用它取 `decision_rule` 文本和 `honesty_boundary` 来打印**，**分档用的是脚本里那四个字面量**。
- ⇒ **存在两处阈值，改一处另一处不动**。**这条声称（"脚本里不重复写死阈值"）不成立**（列非阻塞发现 F1）。

### 7.2 `stop-loss-freeze.txt` 的 sha256 与 `stop-loss.json` 实际字节

```
$ sha256sum stop-loss.json（worktree 原始，CRLF） = d972c33b…（6377 字节）
$ tr -d '\r' < stop-loss.json | sha256sum          = 67aa10f282b5b9cc177431bd0b63412869df3dbc8881361b308f8dee08b9bde4
$ tr -d '\r' < stop-loss.json | wc -c              = 6290
$ git cat-file -p <tag>:…/stop-loss.json | sha256sum = 67aa10f2…（6290 字节）
冻结文件写：字节数 6290 / 行尾 LF / sha256(raw)=sha256(LF归一)=67aa10f2…
```

- **仓库里存的是 LF**（git blob = `67aa10f2…`，6290 字节）；worktree 工作副本被 `core.autocrlf=true` 转成 **CRLF**（6377 字节，`d972c33b…`）。
- **按 LF 归一后与冻结文件一致**（`67aa10f2…`）。**两种口径都核过一次，通过** ✅。
- ⚠ 时序说明：冻结文件自称"在任何第二轮跑分**之前**生成"（`2026-10-09T03:45:04+08:00`），早于提交时间 `04:02`。**哈希一致可核**；**"跑前落盘"这个时序本身我无法独立证实**（只有作者自报的时间戳）——**采信**。

---

## 8. 文档改动（有没有覆盖旧话 / "E4 零命中"是否属实）

- **`--numstat` 显示本批 19 文件 1524 insertions / 0 deletions** ⇒ **一行旧话都没被删**。`git diff … | grep '^-'`（排除 `---`）**为空**。✅ "错话+更正都留"这条规矩**遵守**。
- 旧话确在：`NEXT-DEV-PLAN` 第 313 行仍保留 `本轮静机复测 **606.0 ms**（52 万行）`（未改），更正以新增 blockquote 形式追加。✅
- **核作者那句"E4 第一轮从没登记进总纲/开发史"**（父提交 `05ff39a`，我逐文件 grep）：

```
docs/DEVELOPMENT-HISTORY.md   @05ff39a : E4=0  Qwen3=0  embedding-shadow=0
docs/RETRIEVAL-LONG-RANGE-PLAN.md @05ff39a : E4=0  Qwen3=0  embedding-shadow=0
docs/NEXT-DEV-PLAN-2026-09-28.md  @05ff39a : E4=0  Qwen3=0  embedding-shadow=0
```

⇒ **这句话是真的**（`E4` / `Qwen3` 两文件零命中，`embedding-shadow` 也零命中）。作者**不是错话**。✅

---

## 9. 判定

**放行（无阻塞）。** 本批**主声称全部成立**：A 臂每一格复现（warm/显存逐位一致）、B 臂主终点 **+15.84pt 逐字节复现**、仪器对照成立、判据有牙（变异塌 0、互换翻符号）、真库只读未被改动、阈值冻结哈希一致、文档纯新增且"零命中"声称属实。

**唯一的"声称不成立"是文档层的一条**（F1：`12-verdict.py` 重复写死阈值）——**不影响任何读数与判定**，按本仓惯例列**非阻塞发现**，请作者就地更正。

---

## 10. 非阻塞发现清单（本仓惯例：复核的非阻塞发现会被作者逐条就地更正）

- **F1（文档/声称不一致）**：README §五 与 `12-verdict.py` docstring 声称"阈值不重复写死、防两处漂移"，但 `12-verdict.py:34/40/47/49` **把 `100` / `4096` / `8` / `10` 又写死了一遍**，与 `stop-loss.json` 重复。建议：要么改成从 `stop-loss.json` 读数分档，要么把 docstring/README 那句"不重复写死"改成"阈值语义以 `stop-loss.json` 为准，脚本内联实现"。
- **F2（同批两个副本扫描读数并存，未说明）**：副本（521,978 行）扫描在 `latency.json` 里是 **819.7 ms**、在 `latency-real-db-scan.json` 里是 **812.3 ms**。README §二表引的是 **812.3**，而"3.91%（副本口径）"这个比例用的是 **819.7**。两数都真、都是同批量的，但**同一张表里混用**会让读者困惑。建议注明来源。
- **F3（写死文案与实际不符）**：`14-real-db-scan.py` / `latency-real-db-scan.json` / `verdict.json` 的 `attribution` 文案写"副本同是 521,978 行却量到 **815.1 ms**"，但**同批实测的副本中位是 812.3 ms**（`latency.json` 那份是 819.7 ms）。`815.1` 是个**对不上任何一份实测值的字面量**（疑似早期草稿数）。建议改为实测值。
- **F4（冷启动波动未标注）**：冷启动我实测 `177.1 / 2913.5 ms`，作者自报 `712.4 / 5154.3 ms`，差 2–4×。冷启动本机一次性、波动大**不是错**，但文档把单次读数当稳定值报，建议加"冷启动波动大"的说明。
- **F5（同一量两种写法）**：主终点 Δ 在 README §三表头/`verdict.json` 写 **+15.84pt**（由四舍五入到 4dp 的率相减），在 CI 表/`prefix-cluster-ci.json` 写 **+15.83pt**（逐条直接计数）。两者都可导出，但同一份文档两种写法，建议统一或注明口径。

---

## 11. 复核者声明

**我实测（自己跑/自己算）**：
- 冻结事实：tag→commit、`rev-list --count=2`、两条提交归属、`src/plugin` diff 为空、全量 numstat、提取树首尾 HEAD/status；
- A 臂 `10-latency.py` 整跑（warm/冷启动/显存/参数/副本扫描/附加 CPU 项）；
- B 臂 `11-prefix-ab.py` 整跑（主终点 + 全表 + `per-query.jsonl` 逐字节比对）；
- 变异：前缀臂去前缀 ⇒ delta 塌 0 + 按 SHA256 还原；两臂互换 ⇒ 符号翻转；
- `12-verdict.py`（冻结输入逐字节复现 + 重跑输入落档）与 `13-cluster-ci.py`（连跑两次逐字节相同）；
- 仪器对照（`noprefix` vs 第一轮 `ctx` 的 8 字段逐条比对；两臂 `fts@1000`）；
- 真库/副本行数与 mtime（只读 `mode=ro` + `load_vec_extension`）；
- 阈值 grep、`stop-loss-freeze.txt` 哈希（raw + LF 归一）；
- 文档 numstat / 旧话保留 / `05ff39a` 处"E4/Qwen3 零命中"。

**我采信（写明来源，未独立复算）**：
- 考卷 `benchmark-v2.jsonl` / `benchmark-v3.jsonl` 的 gold 与 `headline` 归属（作冻结输入，沿用第一轮复核结论）；
- `stop-loss.json` 里引用的**第一轮**数字（`+32.50pt`、CI `[22.95, 42.52]`、`bge 0.3583`）与 `power-factcheck.json` 的 `8.18pt / 11.68pt`——我**核到这些文件里确有这些数**，但**未重跑第一轮**；
- 冻结文件的"跑前落盘"**时序**（哈希一致，时间戳自报）；
- `14-real-db-scan.py` 我没整跑（我另行只读核了它的两个关键结论：真库 663,634 行、真库/副本 mtime 未变）；其"真库扫描 1074.7 ms"我**未独立重测**（沿用作者读数，但与我复现的副本 818.1 ms 量级自洽）。

**我未做**：
- 未重跑整个门禁（`run-gates.ps1`）——按指令只做静态改动面核对（本批 `src/`、`plugin/` **零改动**，无门禁触发面）；
- 未整跑 `14-real-db-scan.py`（只核了它的两个可验证结论）；
- 未独立复算第一轮（E4 round-1）的任何读数；
- 未验中文/领域指令前缀（本批本就未做，不在范围）；
- 未验部署环境 SLA（本批只报本机读数，作者已声明）。

**纪律遵守**：真库全程 `mode=ro`，未写任何向量、未碰 `clause_vec`；未碰 `tools/gov-qa/**`、公告更新组件、他人未提交件；变异只在提取树做且已还原；未在变异期间跑门禁；提取树已 `worktree remove --force` + `prune`，主仓 `exp.db` 完好。
