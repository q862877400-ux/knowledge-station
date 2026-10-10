> **⚠ 归档说明（2026-10-10 接手方人工轮第 21 轮）**
>
> **本文是从仓库里的临时件字节级搬进来的**，原件**未删**（它是并行自动化的取证现场，按 FR-010「拿不准的进归档、不删」）。
>
> | 项 | 值 |
> |---|---|
> | 原件 | `.tmp-review-spec004.md`（**在 `.gitignore:44` 的 `.tmp-*` 之下，随时会被清**） |
> | 原件 sha256 | `F1D13F28A5E13C1CB238CA485256F72B40919CE8A4B92E977E972B74C6680EFE` |
> | 为什么搬 | 它**被正式文档引用**，却只存在于 gitignore 里 ⇒ 内容会丢 |
> | 谁在引用 | `docs/DEVELOPMENT-HISTORY.md`（§10.232 附近）、`specs/005-govqa-conformance/plan.md` L16、`specs/001-project-consolidation/top-level-inventory.md` |
> | 搬法 | `shutil.copy2` + 只**前置**这段说明，**正文一字未改** |

---

# 独立复核报告 —— `tools/gov-qa/` spec 004 可运维化层

**复核对象**：`poll.py` / `state.py` / `channel.py` / `common.py` / `coverage.py` / `coverage-report.py` / `health.py`、`tests/`（5 文件 58 测试）、`specs/004-govqa-operationalization/`
**复核时点**：2026-10-10 07:20–08:05
**起点 HEAD**：`88644c6fc98a7bd6ff10e7e57a5a98af5ca9f53c`
**终点 HEAD**：`88644c6fc98a7bd6ff10e7e57a5a98af5ca9f53c`（未变）
**基线**：`.venv\Scripts\python.exe -m pytest tools/gov-qa/tests -q` ⇒ `58 passed in 0.69s`
**终点**：同命令 ⇒ `58 passed in 0.53s`

> ⚠ **本报告不做任何修复，不提交任何东西。** 唯一写入的文件是本报告（`.tmp-review-spec004.md`）。
> 变异一律「改一个源文件 → 跑一条测试 → 按字节还原」，每个变异用 sha256 对 `%TEMP%\govqa-bak` 的备份校验还原成功后才继续。

## 变异总表（16 个锚点 + 26 个追加探针）

| # | 源文件 | 被破的行为 | 测试 | 结果 |
|---|---|---|---|---|
| M01 | poll.py | 翻到已知页就停 | `test_incremental_stops_at_known_page` | **RED**（有牙） |
| M02 | poll.py | 幂等：第二次新增 0 | `test_idempotent_second_run_adds_zero` | **RED** |
| M03 | poll.py | FR-003 失败不前移水位 | `test_failure_does_not_advance_watermark` | **RED** |
| M04 | common.py | 边采边落盘立即可读 | `test_atomic_append_writes_immediately` | **RED** |
| M05 | common.py | ascii_kv 纯 ASCII | `test_ascii_kv_is_pure_ascii` | **RED** |
| M06 | state.py | idset 50000 上限 | `test_idset_lru_cap` | **RED** |
| M07 | state.py | 水位损坏被标记 | `test_broken_file_degrades_safely` | **RED** |
| M08 | coverage.py | 真中位数（偶数取均值） | `test_ratio_to_median_is_same_level` | **RED** |
| M09 | coverage.py | 自治州/地区/盟不补「市」 | `test_norm_city` | **RED** |
| M10 | coverage.py | 「市辖区」占位值被过滤 | `test_count_by_city_filters_placeholder_and_falls_back` | **RED** |
| M11 | coverage.py | 补建市级单元不重复计省级 | `test_merge_does_not_inflate_province_total` | **RED** |
| M12 | coverage.py | 「已穷尽」显式不留空 | `test_uncovered_exhausted_is_explicit` | **RED** |
| M13 | health.py | 一次运行检出重复 id | `test_health_detects_all_three_faults` | **RED** |
| M14 | channel.py | 直辖市不算地级市 | `test_municipality_not_counted_as_city` | **RED** |
| M15 | poll.py | `GOVQA_PAGE_FROM` 用完恢复 | `test_incremental_restores_page_env` | **RED** |
| M16 | health.py | 标签覆盖率闸门参与判定 | `test_health_reports_usable` | **GREEN（无牙）** |
| N01 | common.py | health `--quiet` 纯 ASCII | `test_health_quiet_is_pure_ascii` | **GREEN（无牙）** |
| N02/N03 | health.py | 零数据适配器判定 | `-k test_health`（9 条） | **GREEN（无牙）** |
| N04/N05 | poll.py | 退出码 3 / 1 | 全套 58 条 | **GREEN（无牙）** |
| N06/N07 | coverage-report.py | 退出码 1 | 全套 58 条 | **GREEN（无牙）** |
| N08 | state.py | LRU 保留最新 | `test_idset_lru_cap` | **GREEN（无牙）** |
| N09 | channel.py | 市名提取窗口 | `test_city_extraction` | **GREEN（无牙）** |
| N10 | poll.py | `--quiet` 走 ascii_kv | 全套 58 条 | **GREEN（无牙）** |
| P01 | poll.py | 水位被写入并被下轮读取 | 全套 58 条 | **GREEN（无牙）** |
| P02 | poll.py | 水位缺失/损坏驱动 need_full | 全套 58 条 | **GREEN（无牙）** |
| P03 | poll.py | 水位类型影响行为 | 全套 58 条 | **GREEN（无牙）** |
| Q01/Q02/Q03 | health.py | 4 项判据各自参与判定 | `-k test_health` | **GREEN（无牙）** |

**结论：判据不是「普遍无牙」，而是「核心算法层有牙、CLI/契约层无牙」。**
15/16 个算法锚点变异即红；但 **CLI 退出码、契约字段、水位实际被读取这三大块，改坏了没有一条测试会红**。

---

# 发现清单（按严重度）

## 【高】1. 水位只写不读 —— 增量轮询对 `page`/`since` 型通道是**摆设**

**位置**：`poll.py` 中 `def _should_stop(recs, new_this, need_full: bool, wm) -> bool:` 与 `def _next_value(wm, new_recs, need_full):`；`poll.py` 模块文档「三条核心保证」表与 `_should_stop` 文档「**`page` / `since` 型**：本批没有任何新记录 ⇒ 已翻到水位，停」

**主张**：模块文档与 `tasks.md` T015 称「按水位类型决定从哪开始翻 / 翻到哪停」，三种水位类型 `page` / `since` / `idset` 语义不同：
> `page` 型：从第 1 页开始，翻到「本页全部已见过」即停
> `since` 型：**只取时间 > 水位的条目**

**反证**：

```
$ .venv\Scripts\python.exe -c "<end-to-end: 轮询 fake-1，然后把手存水位改成 999999，再轮询>"
  run1 added: 5 pages: 3 batches: 4
  run1 watermark value: 1 type: page
  after setting watermark value=999999:
    run2 added: 0 pages requested: [1]
    => watermark value 999999 did NOT change where fetching starts
```

`_should_stop` 的**代码体**（去掉 docstring 后）只有两行，`recs` 与 `wm` 两个形参**从未被使用**：

```
$ .venv\Scripts\python.exe -c "<打印 _should_stop 的代码体>"
  code-after-docstring: if need_full:
        return False
    return len(new_this) == 0
  recs used in code: False | wm used in code: False
```

`since` 型的「只取时间 > 水位」在 `poll.py` 里**根本不存在**：全文件搜 `asked_at` 只命中 1 处，且是 `_next_value` 里**算新水位**用的，不是**过滤**用的：

```
$ .venv\Scripts\python.exe -c "<grep poll.py>"
  'asked_at': 1 hit(s)
      ts = [str(r.get("asked_at") or "") for r in new_recs]
  'wm.value': 4 hit(s)      ← 全部在 _next_value 里，只写不读
      old = wm.value if isinstance(wm.value, list) else []
      old = int(wm.value or 0)
      return max(ts) if ts else wm.value
      return wm.value
```

停不停**只取决于「本批有没有新 id」**，与水位值、水位类型无关 —— 三种类型走同一条分支。

**变异验证**：P01（删掉 `store.mark_success(...)` 整段）、P02（`need_full = force_full`，不看水位损坏）、P03（把水位类型硬写成 `idset`）—— 三次变异**全套 58 条测试全绿**。

**严重度**：高
**是否已变异验证**：yes

> **注**：`idset` 型（331 通道里的多数）确实靠「翻到全旧就停 + 已落盘 id 去重」实现了正确的增量语义 —— 这一条**站得住**。失效的是文档对 `page`/`since` 的宣称：`page` 型水位值 `1`（见 `state/watermarks.json` 的 `rd-js` 也是 `value: []`）永不被读，`since` 型的时间比较不存在。**用户唯一明说的目的（「一个轮询拿到最新」）在 idset 路径上达成，在另外两条路径上是空壳。**

---

## 【高】2. 覆盖闸门「判据有牙」是假的：`CITY_NONE=0` 与 182 个零记录市同时成立

**位置**：`coverage-report.py` 中 `"CITY_TOTAL": len(city), "CITY_OK": ..., "CITY_NONE": _cnt(city, STATUS_NONE),` 与 `return EXIT_NONE_UNIT if _cnt(sel, STATUS_NONE) > 0 else EXIT_OK`

**主张**：`coverage-report.py` 模块文档称退出码 `1` = 「**有 `none` 单元**（某地区完全没来源）—— 硬缺口」；`contracts/coverage.md` 称「有地区**完全没有来源**。这是硬缺口，必须报红。」

**反证**：

```
$ .venv\Scripts\python.exe tools/gov-qa/coverage-report.py --quiet
PROV_TOTAL=31
PROV_OK=11
PROV_THIN=20
PROV_NONE=0
CITY_TOTAL=157
CITY_OK=70
CITY_THIN=87
CITY_NONE=0
CITY_DATA_ONLY=85
rc=0

$ .venv\Scripts\python.exe tools/gov-qa/coverage-report.py --missing-cities --quiet
CITY_TOTAL=334
CITY_HAVE=152
CITY_MISSING=182
rc=1
```

**同一个工具、同一份数据**：摘要说 `CITY_NONE=0` 且 `rc=0`（闸门绿）；`--missing-cities` 说 182 个地级市**零记录**且 `rc=1`。根因是摘要只统计**已建出单元**的市（157 个 = 83 有通道 + 74 数据口径），而**零记录的市根本没被建单元**，于是永远不可能计入 `CITY_NONE`。⇒ **`CITY_NONE` 恒为 0，`EXIT_NONE_UNIT` 在城市维度恒不触发。**

这正是 `coverage.py` 类文档自己警告过的病（「否则无法区分『查完没有』和『没查』」）在市级闸门上的复发。

**变异验证**：N06/N07（把 `return EXIT_NONE_UNIT if n_miss else EXIT_OK` 与 `... _cnt(sel, STATUS_NONE) > 0 ...` 都改成恒 `EXIT_OK`）—— **全套 58 条测试全绿**。退出码契约零测试覆盖。

**严重度**：高
**是否已变异验证**：yes

---

## 【高】3. `health.py` 的 4 项判据里，**没有任何一项**被测试钉住

**位置**：`health.py` 中 `checks.append(("数据总数 ≥ 地板", s["total"] >= s["floor"],` / `checks.append(("无零数据适配器", s["empty"] == 0,` / `checks.append(("无重复 id", s["dups"] == 0,` / `checks.append((f"标签覆盖率 ≥ {COVERAGE_GATE:.0f}%", s["coverage"] >= COVERAGE_GATE,`

**主张**：`health.py` 是「体检」，「一次运行检出全部故障」（SC-009 / FR-017）。测试 `test_health_detects_all_three_faults` 号称验证这一点。

**反证**：逐项把判据改成恒真：

```
$ <变异：把四项的布尔条件各自改成 True，跑 -k test_health>
  Q01 标签覆盖率闸门参与判定                GREEN (no teeth)   9 passed, 49 deselected
  Q02 数据总数 ≥ 地板 参与判定             GREEN (no teeth)   9 passed, 49 deselected
  Q03 无重复 id 参与判定                GREEN (no teeth)   9 passed, 49 deselected
  M16 COVERAGE_GATE = -1.0               GREEN (no teeth)   1 passed, 57 deselected
```

四项**同时**改成恒真才终于有牙：

```
$ <变异：四项条件全部 -> True>
  all 4 verdict checks -> always True: RED | 1 failed, 57 passed
  failing test: ['FAILED tools/gov-qa/tests/test_health.py::test_health_detects_all_three_faults']
```

⇒ 该测试的牙只来自**断言里写死的字符串** `"VERDICT=not_usable"` 与 `"DUPS=1"`；它验证的是「输出格式」，不是「判定逻辑」。任一项判定失效（例如覆盖率闸门永远放行、地板比较写反）**测试都不会红**。这正是清单第 1 条说的「恒真/空过面」。

**严重度**：高
**是否已变异验证**：yes

---

## 【中】4. 24 个通道（含 35,260 条记录）**完全落在销号表之外**

**位置**：`coverage.py` 中 `else:` 分支 `key = c.level` / `u = other.setdefault(key, CoverageUnit(key, "other", threshold=0))`；`coverage-report.py` 中 `sel = [u for u in units if not args.level or u.level == args.level]` 与 `prov = [u for u in sel if u.level == "province"]` / `city = [u for u in sel if u.level == "city"]`

**主张**：`spec.md` SC-004 要求「全国 31 个省级行政区 + 333 个地级行政区，**每一个**都能在销号表里查到来源数 + 落盘量 + 达标状态」；FR-007/FR-008 要求逐条列出。

**反证**：`build_units` 把 `level` 不是 `province`/`city`（或 `region` 为空）的通道塞进 `other` 桶，而 CLI 只渲染 `province` 与 `city`：

```
$ .venv\Scripts\python.exe -c "<load_channels + build_units，统计未进入 province/city 单元的通道>"
  channels excluded from province/city units: 24
    gs-linxia              level=city      region=''     recs=     0
    mee                    level=national  region=''     recs=   145
    nat-cnipa              level=national  region=''     recs=  6161
    nat-most               level=national  region=''     recs=  8045
    nat-tax                level=national  region=''     recs= 13943
    people-liuyan          level=national  region=''     recs=    37
    people-liuyan-prov     level=province  region=''     recs=   757
    rd-npc                 level=national  region=''     recs=     5
    sc-aba                 level=city      region=''     recs=  2451
    sc-ganzi               level=city      region=''     recs=    14
    sc-liangshan           level=city      region=''     recs=    96
    ... (共 24 个)
  records invisible in the 销号表: 35260
```

两个子问题：

1. **7 个 `level=city` 但 `region` 为空的通道被静默降级为 `other`**（`coverage.py` 的 `elif c.level == "city" and region:` 要求 region 非空）。它们是甘孜州 / 阿坝州 / 凉山州 / 临夏州 —— `channel._city_from_name` 的正则 `^([\u4e00-\u9fa5]{2,6}?市)` 与 `([\u4e00-\u9fa5]{2,4}市)` **只认「市」不认「州/盟/地区」**，所以自治州一律提取失败。这 7 个通道有 2,954 条真实数据，却在销号表里既不进省也不进市。
2. **14 个国家级通道（含 `nat-tax` 13,943 条、`nat-most` 8,045 条）也没有销号行** —— 而 `spec.md` 的 Key Entities 把「部委」列为通道层级之一，`plan.md` 提到 681 个来源。

**变异验证**：no（这是数据/结构事实，用枚举命令取证，非断言变异）
**严重度**：中
**是否已变异验证**：no

---

## 【中】5. `--scope law_std` 把「无此字段」误判成「硬缺口」（退出码 1）

**位置**：`coverage-report.py` 中 `def _scope_filter(scope: str):` 与 `return EXIT_NONE_UNIT if _cnt(sel, STATUS_NONE) > 0 else EXIT_OK`

**主张**：`contracts/coverage.md` 与 `tasks.md` T034 要求支持 `--scope law_std`，让「分母可按新口径重算」。`coverage-report.py` 称退出码 1 = 「有地区**完全没有来源**」。

**反证**：全库 395,829 条记录里 `scope_tag` 字段**出现 0 次**（`data-model.md` E3 把它列为本特性新增字段，`tasks.md` T043 的回填脚本 `recon/backfill-derived.py` 不存在）。过滤器因此丢弃一切：

```
$ .venv\Scripts\python.exe -c "<扫全库统计 scope_tag>"
  scanned 395,829 records: scope_tag=0  ingested_at=0

$ .venv\Scripts\python.exe tools/gov-qa/coverage-report.py --quiet
PROV_TOTAL=31 ... PROV_NONE=0 ... rc=0

$ .venv\Scripts\python.exe tools/gov-qa/coverage-report.py --scope law_std --quiet
PROV_TOTAL=31
PROV_OK=0
PROV_THIN=20→30
PROV_NONE=1          ← 「硬缺口」
rc=1
```

**没有任何一个省真的没有来源**，但工具报 `PROV_NONE=1` 并 `exit 1`。「零匹配」与「真缺口」被混为一谈，正是 `coverage.py` 类文档反对的「无法区分『查完没有』和『没查』」。同时 `--scope` 与 `--missing-cities` 组合也不校验（`--missing-cities` 分支直接用未过滤的 `PROVINCE_CITIES`）。

**严重度**：中
**是否已变异验证**：no（命令实测）

---

## 【中】6. `common.py::human()` 的兜底分支自身会抛 `UnicodeEncodeError`

**位置**：`common.py` 中 `except UnicodeEncodeError:` 下的 `out.write(msg.encode("utf-8", "replace").decode("ascii", "replace") + "\n")`

**主张**：`common.py` 模块文档第 1 条：「Python 打印中文 ⇒ hook 环境 stdout 非 UTF-8 ⇒ `UnicodeEncodeError` ⇒ 凡给程序读的输出，一律走 `ascii_kv()`。中文只出现在给人看的输出里。」`human()` 的兜底注释写「终端编码不支持中文时的兜底，**不让它崩**」。

**反证**：兜底把中文变成 `?`，但**先把 emoji 编成 U+FFFD 再经 `ascii/replace`**，产物里含 `\ufffd`；GBK 也编不了 `\ufffd`，于是兜底**自己**抛异常：

```
$ <io.TextIOWrapper(encoding='gbk', errors='strict') 下调 common.human>
--- human('✅ 当前可用：394,944 条')
    status: RAISED UnicodeEncodeError
    err:    'gbk' codec can't encode character '\ufffd' in position 0: illegal multibyte sequence
--- human('纯中文 当前可用')          ← 不含 emoji 时兜底正常
    status: OK
--- print('✅ emoji')
    status: RAISED UnicodeEncodeError
    err:    'gbk' codec can't encode character '\u2705' in position 0
```

对照 `harvest.py` 的 `_safe()`（同仓已有正确写法）：它用 `sys.stdout.encoding` 按**目标编码**做 replace，`human()` 却固定按 UTF-8→ASCII 转 —— 转换方向错了，兜底产出的 `\ufffd` 仍然编不进 GBK。

**严重度**：中
**是否已变异验证**：no（单元级实测）

---

## 【中】7. spec-004 的**人读输出**确实复现了已知的 GBK 崩溃类；机器可读路径是干净的

**位置**：`health.py` 中 `human(f"✅ 当前可用：{s['total']:,} 条 / ...")`、`human(f"  {mark} {n:22s} {d}")`、`human(f"  ⏱️  用时 {elapsed}s" ...)`；`coverage-report.py` 中 `human(f"  ✅ ok    {_cnt(us, STATUS_OK):3d} 个")`、`human("⚠ **两个口径**：...")`

**主张**（任务书问题 6）：确认 `recon/audit-coverage.py --answers` 的 GBK 崩溃是否在 spec-004 文件里同类复发。

**反证 A —— 已知 bug 复现**：

```
$ .venv\Scripts\python.exe tools/gov-qa/recon/audit-coverage.py --answers
总记录 395,495    答复长度：min=1 p10=41 中位=152 p90=473 max=950789
Traceback (most recent call last):
  File "...\tools\gov-qa\recon\audit-coverage.py", line 133, in show_answers
    print(f"\u26a0 答复 <30 字的记录：{short_all:,}（...）\n")
UnicodeEncodeError: 'gbk' codec can't encode character '\u26a0' in position 0: illegal multibyte sequence
rc=1
```

**反证 B —— 同类代码存在于 spec-004 文件**：`health.py` 的首行结论以 `✅`（U+2705）开头，`coverage-report.py` 的 `human()` 里含 `✅`/`⚠️`/`⏱️`。当前交互式控制台下 **stderr 的 error handler 是 `backslashreplace`**（`<stderr> encoding='gbk' errors='backslashreplace'`），把 emoji 写成字面量 `\u2705` 而**不崩**：

```
$ <subprocess, stderr 重定向到文件>
  health-default   rc=0 UnicodeEncodeError=False
  cov-default      rc=0 UnicodeEncodeError=False
$ Format-Hex health-default.gbk.err
  5C 75 32 37 30 35 20 B5 B1 C7 B0 BF C9 D3 C3 A3   \u2705 当前可用：...
```

⇒ **结论（精确）**：spec-004 的 7 个文件里**没有** `print()`/`human()` 直写非 ASCII 到 GBK 的裸路径 —— `ascii_kv()` 在机器可读路径上是**唯一**出口且确实做了 `encode("ascii","replace")`，`health.py --quiet` / `coverage-report.py --quiet` 的 stdout 实测 `stdout_pure_ascii=True`。**这一条是干净的。** 崩溃面收窄为两点：(a) `common.human()` 兜底自身（见发现 6）；(b) `poll.py` 的 `--quiet` 例外（见发现 8）。

**严重度**：中（`audit-coverage.py` 部分）/ 低（spec-004 部分）
**是否已变异验证**：no（命令实测 + 原始字节取证）

---

## 【中】8. `poll.py --quiet` 的逐通道行绕过 `ascii_kv()`，且含一行死代码

**位置**：`poll.py` 中 `print(f"CHANNEL={r['key']} ADDED={r['added']} STATUS={r['status']}")` 与 `ascii_kv({}, stream=None) if False else None`

**主张**：`common.py` 模块文档：「**所有给程序读的输出都必须走这里**（`ascii_kv`）。」`tasks.md` T021：「`--quiet` 纯 ASCII `KEY=VALUE`（走 T004 的 `ascii_kv`）」。

**反证**：

```
$ .venv\Scripts\python.exe -c "<grep poll.py>"
   ascii_kv(kv)
   ascii_kv({}, stream=None) if False else None      ← 死代码，恒不执行
   print(f"CHANNEL={r['key']} ADDED={r['added']} STATUS={r['status']}")
```

`r['key']` 是通道 key。当前 345 个 adapter key **全部是 ASCII**（`non-ascii keys: []`），所以现在不崩；但这行**未经 `ascii_kv` 的替换保护**，一旦有 adapter 用中文 key（本目录 adapter 命名无强制约束）就会重现 `audit-coverage.py` 同类崩溃。且它同时违背契约（见发现 10）。`ascii_kv({}, stream=None) if False else None` 是永不执行的死代码。

**严重度**：中
**是否已变异验证**：no（源码枚举 + key 集枚举）

---

## 【中】9. 契约与实现不符：3 个已写进契约的 CLI 开关不存在，机器可读格式也不符

**位置**：`contracts/coverage.md` 中 `# 只看薄弱地区（按缺口降序）` 的 `--thin --top 20`、`### 机器可读（--quiet，**纯 ASCII**）` 下的 `UNIT=province|云南省|84|3000|2916|0.03|thin|4`、`## 副作用` 的 `可选 --out <file> 输出报告到指定路径`；`contracts/health.md` 中 `# 只跑单项（调试用）` 的 `--only coverage`；`contracts/poll.md` 中 `CHANNEL=sd-yantai ADDED=12 WATERMARK=14`

**主张**：三份契约是 spec 004 的 Phase 1 交付物，`tasks.md` 标注已走完。

**反证**：

```
$ .venv\Scripts\python.exe tools/gov-qa/health.py --only coverage
usage: health.py [-h] [--detail] [--quiet] [--trace TRACE]
health.py: error: unrecognized arguments: --only coverage
rc=2

$ .venv\Scripts\python.exe tools/gov-qa/coverage-report.py --out x.txt
coverage-report.py: error: unrecognized arguments: --out x.txt
rc=2
```

`--thin` 被 `argparse` 接受（`"--thin"` 在源码里），但 **`args.thin` 出现 0 次** —— 它是纯装饰：

```
$ .venv\Scripts\python.exe -c "<grep coverage-report.py>"
  'args.thin' occurrences: 0
  'thin' argument declaration present: True
$ <比较 stderr>
  --top 3      len(stderr)=964
  --thin --top 3 len(stderr)=964   identical stderr: True
```

机器可读格式也不符：契约 `UNIT=province|云南省|84|3000|2916|0.03|thin|4`，实际是 5 行 `KEY=VALUE`：

```
$ .venv\Scripts\python.exe tools/gov-qa/coverage-report.py --region 云南省 --quiet
UNIT=???
LEVEL=province
RECORDS=66
GAP=2934
STATUS=thin
```

且 `--region` 匹配多个单元时**反复输出同名 `UNIT=`**，无区分字段（实测 `--region 省` 输出 110 行、连续 `UNIT=??? | LEVEL=province` 无法归属）。`poll.py` 的 `CHANNEL=` 行输出 `STATUS=` 而契约写的是 `WATERMARK=`（`--quiet` 下 `store.get(key).value` 从未被打印）。

**严重度**：中
**是否已变异验证**：no（命令实测）

---

## 【中】10. 退出码契约（`poll.py` 0/1/2/3、`coverage-report.py` 1）**零测试覆盖**

**位置**：`poll.py` 中 `EXIT_OK = 0` / `EXIT_PARTIAL = 1` / `EXIT_FATAL = 2` / `EXIT_LOCKED = 3`；`coverage-report.py` 中 `EXIT_NONE_UNIT = 1`

**主张**：`contracts/poll.md` 称「退出码（**这是契约的核心**）」，`poll.py` 模块文档同样列表；`contracts/coverage.md` 称退出码 1 用于「覆盖完整性」闸门。

**反证**：把退出码改坏，**58 条测试全绿**：

```
$ <变异 N04: return EXIT_LOCKED -> return EXIT_OK>
  N04  poll.py  GREEN rc=0  58 passed in 0.53s
$ <变异 N05: return EXIT_OK if failed == 0 else EXIT_PARTIAL -> return EXIT_OK>
  N05  poll.py  GREEN rc=0  58 passed in 1.28s
$ <变异 N06/N07: coverage-report 两处 EXIT_NONE_UNIT -> EXIT_OK>
  N06  coverage-report.py GREEN rc=0  58 passed in 0.53s
  N07  coverage-report.py GREEN rc=0  58 passed in 0.53s
```

测试文件里 `EXIT_LOCKED` / `EXIT_PARTIAL` / `poll.main` 出现次数均为 **0**；`test_lock_blocks_second_runner` 只测了 `common.file_lock` 抛 `LockBusy`，**没有测 `main()` 把 `LockBusy` 映射成 3**（契约行为表第 6 行「两个进程同时 `--all`，其中一个返回 3」）。

**严重度**：中
**是否已变异验证**：yes

---

## 【中】11. `health.py` 的「重复 id」只在**单文件内**检测，跨文件重复漏报

**位置**：`health.py` 中 `for p in files:` … `per_src: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))` … `for c in per_src.values():` / `dups += sum(c.values()) - len(c)`

**主张**：`health.py` 与 `check.sh` 判据③「`DUPS = 0`（重复 id）⇒ 并发写污染」；`contracts/health.md` 行为契约第 5 条「**能定位到文件**：重复 id / 数据缺失时，指出具体是哪个文件」。

**反证**：`per_src` 在 `for p in files` 循环**内部**初始化，跨文件不复用 ⇒ 同一个 `(source, id)` 落在两个文件里时 `dups=0`：

```
$ <两个文件各写一条相同的 {"source":"s","id":"1"}>
  two files, same (source,id) -> total=2 dups=0 (expected 1 if cross-file)
```

而 `poll.py::existing_ids` 恰恰是**跨文件**（`DATA_DIR / f"{channel_key}-*.jsonl"`）判重的 —— 两处「重复」口径不一致。`contracts/health.md` 要求的「定位到具体文件」在 `health.py::main` 里也不存在（`files` 变量不出现在 `main` 的任何输出里）。

**严重度**：中
**是否已变异验证**：no（构造用例实测）

---

## 【中】12. `--missing-cities` 报 `CITY_TOTAL=334`，与契约/文档的 **333** 不一致；多出的是「济源市」

**位置**：`regions.py` 模块文档「共 **333 个地级行政区**（不含港澳台）」、`def total_cities() -> int:` 的 docstring「地级行政区总数（应为 333）」；`coverage.py` 的 `def known_cities() -> set:` docstring「**334 个**地级行政区的全称集合」；`contracts/coverage.md` 行为契约第 2 条「每个地级行政区都有行 | 行数 = 333」

**主张**：同一仓库里 333 与 334 两个数字并存。

**反证**：

```
$ .venv\Scripts\python.exe -c "<regions.total_cities() 与逐省计数>"
  regions total_cities = 334
  regions docstring says 333; total_cities docstring says 应为 333
  DIFF 河南省: list=18 standard=17
  河南省 list: [... '驻马店市', '济源市']
  '济源市' is a 省直辖县级市 (province-administered county-level city), not a prefecture-level city

$ .venv\Scripts\python.exe tools/gov-qa/coverage-report.py --missing-cities --quiet
CITY_TOTAL=334
```

⇒ `regions.py` 把**省直辖县级市 济源市**混进了地级行政区表，导致分母 334；而它的 docstring 和 `contracts/coverage.md` 都写 333。`test_known_cities_covers_334` 反过来把 334 固化成期望值（`assert len(ks) >= 330`），**把口径错误钉死**。`test_province_list_is_31` 只钉了省级。

**严重度**：中
**是否已变异验证**：no（命令实测 + 逐省计数）

---

## 【低】13. `test_label_accuracy_refuses_without_human_check` 的断言是「或」关系，可用假数字骗过

**位置**：`test_health.py` 中 `assert "%" not in out or "未做" in out`

**主张**：测试 docstring 称「**宪法 III**：未人工核对时必须输出『明确未做』，**不给数字**」。

**反证**：往 `label-accuracy.py` 的「明确未做」分支里塞一个假百分比：

```
$ <变异 label-accuracy.py：在 human("⚠️  **明确未做**...") 后追加 human("（模型自评准确率 78.9%）")>
  fake % + word 未做  -> GREEN (false pass)  1 passed, 57 deselected
```

只要「未做」二字还在，`"%" not in out` 为假也照样通过 —— 正是清单第 1 条点名的「恒真/空过面」。正确写法应是 `assert "%" not in out and "未做" in out`。

**严重度**：低
**是否已变异验证**：yes

---

## 【低】14. `health.py` 把 0 字节数据文件当成「已采到数据」

**位置**：`health.py` 中 `def count_empty_adapters(files: "list[str]") -> int:` 的 `for b in bases: for pre, k in prefixes: if b.startswith(pre): have.add(k); break`

**主张**：`health.py` 判据②「无零数据适配器」；FR-020「系统 MUST 区分『采到 0 条』与『采集失败』」。

**反证**：只看**文件名前缀**，不看文件是否有内容：

```
$ <为一个真实 adapter 造 0 字节文件>
  adapter='ah-kb' file='ah-kb-安徽省直部门·...' size=0B
  count_empty_adapters([that file]) = 344  (total adapters = 345)
  => 0-byte file counted as HAVING data: True
```

⇒ 「建了文件但一条没采到」不会被判零数据。这正是交接文档 §8.1「『新增 0』的两种原因」里那个坑（盐城案例）的检测面 —— 判据看不见它。

**严重度**：低
**是否已变异验证**：no（构造用例实测）

---

## 【低】15. 锁文件无陈旧检测：进程被 kill 后锁永久占用，`poll.py` 恒返 3

**位置**：`common.py` 中 `@contextmanager` / `def file_lock(path, *, timeout: float = 0.0):` 的 `except FileExistsError:` 分支

**主张**：`common.py` 模块文档「并发必须加锁」；`LockBusy` 文档「**不是失败**，是『有人在跑』。调用方应返回退出码 3」。

**反证**：

```
$ <file_lock 的 except FileExistsError 段内是否有 stale/age 检查>
  file_lock reads holder only for the message: True
  any staleness/age check: False
$ <预先放一个 pid=99999 的残留锁文件，再抢锁>
  acquired a leftover lock: False -> 锁被占用：C:\...\.poll.lock
```

`file_lock` 只把锁文件内容读出来做**报错消息**，从不判断持有者是否还活着。现场就有实证：复核期间 `tools/gov-qa/state/.poll.lock` 存在，内容 `pid=31704 at=1791589281`（07:41:21），而 `Get-Process -Id 31704` **不存在** —— 一个死进程的锁一直挂着，此时任何 `poll.py` 调用都返回 3。同时 `tasks.md` T001 要求「在 `.gitignore` 里排除 `state/.poll.lock`」**未做**（`git check-ignore` 返回非 0）。

**严重度**：低
**是否已变异验证**：no（构造用例实测）

---

## 【低】16. `tasks.md` 全部 57 个任务**没有一个**勾选，却与代码/文档口径矛盾

**位置**：`specs/004-govqa-operationalization/tasks.md` 全文

**主张**：交接文档 §2.4 称「Specify → Plan → Tasks → Implement 已走完，全部落地」。

**反证**：

```
$ Select-String -Path specs/004-govqa-operationalization/tasks.md -Pattern '^\s*- \[x\]'
0
$ ... -Pattern '^\s*- \[ \] T\d'
57
```

**机械核对的落地情况**（`Test-Path`）：

```
tools/gov-qa/tests/__init__.py -> False          (T002 要求建)
tools/gov-qa/recon/verify-idempotent.py -> False (T028 要求写)
tools/gov-qa/recon/backfill-derived.py -> False  (T043 要求写)
--coverage-table / --gaps / --health / --unit in audit-coverage.py: False (T050/T051)
SITE-REGISTRY.md mentions watermark_type: False  (T052)
state/.poll.lock in .gitignore: False            (T001)
```

**同时反向也不成立**：`tests/` 里是 5 个文件（`test_poll.py` / `test_state.py` / `test_channel.py` / `test_coverage.py` / `test_health.py`），而 T023–T027 要求的是 `test_poll_idempotent.py` / `test_poll_resume.py` / `test_poll_watermark_broken.py` / `test_poll_isolation.py` / `test_poll_lock.py` **5 个独立文件** —— 实现把它们合并了。`tasks.md` 的 `[ ]` 状态**如实**反映了未逐条对齐，但交接文档的「全部落地」与它冲突。**这一条是台账与事实的对账缺口，不是代码缺陷。**

**严重度**：低
**是否已变异验证**：no（机械枚举）

---

## 【低】17. 文档里三处「已验/已覆盖」的宣称超出证据

**位置**：`channel.py` 模块文档「**不重写 adapter，只在它们之上加一层**」与 `PROVINCES` 常量注释「中国省级行政区（用于从 SITE 名称解析归属）」；`coverage.py` 类文档的表格「鞍山市 | 0 个通道 ⇒ 判 `none` | 2,307 条」；`spec.md` 背景「已积累 **359,823 条**…**331 个采集适配器**」

**反证**：

```
$ .venv\Scripts\python.exe -c "<len(adapters.ADAPTERS)>"
  total keys 345
$ .venv\Scripts\python.exe tools/gov-qa/health.py --quiet
  TOTAL=396525 ... ADAPTERS=345
```

- `spec.md` 的 359,823 / 331 是立项时的数，现已 396,525 / 345 —— spec 未标注「数字为立项时点」，`plan.md` 同样写死 331/681/36 万。
- `channel.PROVINCES` 是 **34 项**（含港澳台），`coverage.PROVINCE_NAMES` 是 **31 项**（不含）。两个省级名单**内容不同、用途不同、无同步判据**：`test_channel.py` 钉 `len(PROVINCES) == 34`，`test_coverage.py` 钉 `len(PROVINCE_NAMES) == 31`，但**没有任何测试断言二者在「31 个共同省」上一致**（实测集合恰好相同，是巧合而非判据保护）。`coverage.py` 另有一份 `PROVINCE_NAMES`，与 `regions.PROVINCE_CITIES` 的键**实测相同**（`identical sets: True`），但同样**无同步判据**（`grep` 测试文件：0 处同时引用两者）。

**严重度**：低
**是否已变异验证**：no（枚举实测）

---

# 干净的（一行结论，不制造发现）

- **`common.py::ascii_kv` 本体正确**：机器可读路径确实是纯 ASCII，`--quiet` 输出实测 `stdout_pure_ascii=True`（M05 变异即红）。**任务书问题 6 的「spec-004 是否同类复发」答案：机器可读路径没有复发。**
- **`state.py` 水位层干净**：FR-003（失败不前移）、FR-006（损坏退化）、LRU 上限、类型变更作废、持久化 —— 5 条规则全部有牙（M06/M07/M03 变异即红）。
- **`coverage.py` 的算法层干净**：真中位数、占位值过滤、自治州不补「市」、补建不重复计省级、「已穷尽」显式 —— 5 条全部有牙（M08–M12）。
- **`poll.py` 的 idset 增量语义干净**：翻到全旧即停 + 已落盘 id 去重，M01/M02/M15 变异即红；`--dry-run` 不落盘、环境变量不污染调用方。
- **`channel.py` 的 adapter 覆盖干净**：`SITE.key != ADAPTERS key` 计数 0；`load_channels()` 覆盖全部 345 个 adapter，`test_channels_cover_all_adapters` 有牙。
- **`coverage-report.py` 落盘路径与 `harvest.py` 命名规则一致**：逐 adapter 比对 `data_path_for(...).name` 与 `harvest.py` 的 `f"{site['key']}-{site['name']}.jsonl"`，**分歧 0 个**；含非法字符的 SITE 名 0 个。

---

# 复核过程中对工作树的副作用（如实登记）

1. **变异全部按字节还原**。7 个源文件在复核期间被反复改写；终态与 `%TEMP%\govqa-bak` 备份**规范化后逐字节相同**（`CRLF→LF` 后比较，见下条）：
   `channel.py / common.py / coverage-report.py / coverage.py / health.py / poll.py / state.py` 全部 `normalized-identical=True`。
2. **`common.py` / `coverage.py` / `poll.py` / `state.py` 的换行符在复核期间从 LF 变成了 CRLF**（内容不变，`git diff` 为空、`git status` 干净）。这**不是**我的变异脚本造成的 —— 我的还原写的是 `read_bytes()` 的原样字节。同一时间窗（07:44:04–07:45:35）另有进程在写这棵树（并行的广西 IGI 采集进程 `igi-chunked.py` 从 04:30 起一直在跑，`data/gx-igi-*.jsonl` 持续增长）。`core.autocrlf=true` 且无 `.gitattributes`。**内容零差异**，仅行尾字节不同。
3. **我在 probe15 里跑过一次 `poll.py --all`**，它在 900 秒超时后被 `job_kill`。事后核对：**没有产生任何数据写入** —— `data/` 下无新增文件、全库 `ingested_at` 出现 0 次（`poll.py` 的唯一写入签名）、`state/watermarks.json` mtime 仍为 04:09:35（未被我更新）、`tools/gov-qa/data/*.jsonl` 在 07:45 后只有并行 IGI 进程写的 `gx-igi-202` 有改动。**未发现副作用，但这次运行是我不该跑的**（它会向 345 个真实站点发请求）。
4. **现场存在一个残留死锁**：`tools/gov-qa/state/.poll.lock`，`pid=31704 at=1791589281`（07:41:21），pid 已不存在。**我没有删它**（不属于我的产物）。它会让此后任何 `poll.py` 调用返回 3。
5. **未提交任何东西**，未 `git add`，未 `git commit`。起点/终点 HEAD 均为 `88644c6`。

# 按严重度的最终排序

| 序 | 严重度 | 发现 | 一句话证据 |
|---|---|---|---|
| 1 | 高 | 水位只写不读；`page`/`since` 型是摆设 | 手改水位为 999999，`pages requested` 仍 `[1]`；`_should_stop` 代码体不用 `recs`/`wm` |
| 2 | 高 | 覆盖闸门假绿：`CITY_NONE=0` 与 182 个零记录市同时成立 | `--quiet` rc=0 / `--missing-cities` rc=1，同一工具同一数据 |
| 3 | 高 | `health.py` 四项判据**无一项**被测试钉住 | 四项各自改恒真全绿；四项同时改恒真才红 |
| 4 | 中 | 24 个通道（35,260 条）不在销号表内 | 7 个自治州通道 region 提取失败 + 14 个国家级通道落 `other` 桶 |
| 5 | 中 | `--scope law_std` 把「无此字段」当硬缺口 | 全库 `scope_tag=0` 条；`--scope law_std` 报 `PROV_NONE=1` rc=1 |
| 6 | 中 | `human()` 兜底自身抛 `UnicodeEncodeError` | GBK strict 下 `human('✅ …')` → `can't encode '\ufffd'` |
| 7 | 中 | `audit-coverage.py --answers` GBK 崩溃复现（spec-004 机器路径干净） | `'\u26a0'` 未过 `_safe()`；`--quiet` stdout 实测纯 ASCII |
| 8 | 中 | `poll.py --quiet` 逐通道行绕过 `ascii_kv` + 死代码 | `print(f"CHANNEL={r['key']} …")`；`ascii_kv({}) if False else None` |
| 9 | 中 | 3 个契约开关不存在 + 机器可读格式不符 | `--only` / `--out` rc=2；`--thin` 与无 `--thin` 输出完全相同；`UNIT=` 格式不符 |
| 10 | 中 | 退出码契约零测试覆盖 | 4 处退出码改坏，58 条全绿 |
| 11 | 中 | 重复 id 只在单文件内检测 | 两文件同 `(source,id)` ⇒ `dups=0` |
| 12 | 中 | `CITY_TOTAL=334` vs 契约 333（多出济源市） | `regions.total_cities()=334`，docstring 与 `contracts/coverage.md` 写 333 |
| 13 | 低 | `test_label_accuracy_refuses...` 断言是「或」 | 塞入假百分比后仍 GREEN |
| 14 | 低 | 0 字节数据文件被当成「有数据」 | `count_empty_adapters([0B file]) = 344/345` |
| 15 | 低 | 锁无陈旧检测；现场有死锁；`.gitignore` 未排除 | 死 pid 的锁让 `poll.py` 恒返 3 |
| 16 | 低 | `tasks.md` 57 项全未勾选，与「全部落地」冲突 | `- [x]` 计数 0；3 个要求产物 `Test-Path=False` |
| 17 | 低 | 三处「已验」宣称超出证据 | 331/359,823 vs 345/396,525；31/34 两份省级名单无同步判据 |
