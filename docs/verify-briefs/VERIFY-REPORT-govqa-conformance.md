# 独立复核报告 —— `verify-freeze-govqa-conformance`

复核对象：冻结 tag `verify-freeze-govqa-conformance`（**annotated tag** `05d276a2a1affdf96d5b7ad5b630eb36ee04e352` → commit `7bc67704ff07b32780b15091550bd70bc55d1b91`）。

> 注：任务书写「tag = 提交 7bc67704」。实测该 tag 是 annotated tag，其指向的 commit 正是 `7bc67704`。**tag 与提交一致，无出入。**

提取树：`%TEMP%\verify-govqa`（`git worktree add --detach`，真拷贝依赖，未用 junction）。

---

## 0. 首尾各记一次（要求项）

**报告开头**

```
$ git rev-parse HEAD
478cc5b3...            ← 见下方说明，此为会话起始 HEAD
$ git status --short | Measure-Object
total=791  tracked_modified=44  untracked=747
```

**报告结尾**

```
$ git rev-parse HEAD
0041c270cd59d493d8371bdb6f9b7eaf5137c11e
$ git status --short | Measure-Object
total=768  tracked_modified=39  untracked=729
```

### ⚠ 发现 0：复核期间主仓 HEAD 被移动（另有一方在写这棵树）

`git rev-parse HEAD` 在会话开始时为 `478cc5b3`，结束时为 `0041c270`。中间落进 **19 笔提交**：

```
$ git log --oneline 478cc5b3..HEAD
02b4eac6 fix(govqa/005): T502 —— 「明确未做」的断言是「或」，塞假数字照样过（独立复核 Finding 13）
7fdd2c15 docs(006): spec 收口 ...
9df6d8b7 feat(law): 法规目录定时刷新 + 历次版本链 + 反爬挑战页修复（spec 006）
fdaa6759 chore(govqa/005): 棘轮基线锁定 T208 成果 —— 时间倒置 3399 -> 1516
05bef187 fix(govqa/005): T208 —— `sc-yibin` 的 1,883 条哨兵日期 `2000-01-01` 置空
c1f233ad fix(govqa/005): T201 之二 —— `xz-lasa` 列表翻页扛瞬时断连（否则只收到 859/1031）
... （共 19 笔）
```

- **严重度**：中（流程）—— 不是被审代码的缺陷，是"边改边验"的双向污染风险。
- **本次是否影响结论**：**未影响**。全部复核在 `7bc67704` 的提取树内完成；主仓只用于两处"未跟踪数据文件"的读数（标注见 §3、§5）。
- **已变异验证**：不适用。
- **给父代理的动作**：本批仍在被并行修改（`T502` 那笔的标题本身就写着"独立复核 Finding 13"）。若要收口，需再冻结一次。

---

## 1. 声称 A —— 门禁接入与条数

**主张**：`pyproject.toml` 的 `testpaths` 已含 `tools/gov-qa/tests`；根 pytest 从 2745 → **2847**。

### A1（PASS）：`testpaths` 确已接入

```
$ python -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['tool']['pytest']['ini_options']['testpaths'])"
TOML_OK
testpaths= ['tests', 'tools/gov-qa/tests']
```
TOML 合法，`testpaths` 只出现一次（无重复键）。

### A2（**FAIL**）：绝对条数不是 2847，是 **2803**

```
$ python -m pytest --collect-only -q --no-header -p no:cacheprovider
2803 tests collected in 4.11s
```

分量：

```
$ python -m pytest --collect-only -q --no-header -p no:cacheprovider tests
2701 tests collected in 1.10s
$ python -m pytest --collect-only -q --no-header -p no:cacheprovider tools/gov-qa/tests
102 tests collected in 0.04s
```

**2745 这个基数是「工作区」的数，不是冻结提交的数。** 差 44 条来自 4 个**不在冻结提交里**的测试文件：

```
$ git diff --name-status 7bc67704..HEAD -- tests/
（空 —— 冻结提交之后才有下面这些）
$ foreach file: git cat-file -e "7bc67704:<file>"
tests/test_jev_cn_baseline.py          at_freeze_exists=False  status=??  (5 条)
tests/test_law_catalog_refresh.py      at_freeze_exists=False  (18 条，来自 9df6d8b7，冻结之后)
tests/test_law_history.py              at_freeze_exists=False  (11 条，来自 9df6d8b7)
tests/test_law_source_http_antibot.py  at_freeze_exists=False  (10 条，来自 9df6d8b7)
```

2701 + 44 = 2745；2745 + 102 = 2847。**"+102" 是对的；两个绝对值是错的。**

逐提交实测（三个独立 worktree）：

```
b50cbb9a (fb88d66e^)  testpaths = ["tests"]                       => 2701 tests collected
fb88d66e (T101)       testpaths = ["tests", "tools/gov-qa/tests"] => 2803 tests collected
7bc67704 (冻结)       testpaths = ["tests", "tools/gov-qa/tests"] => 2803 tests collected
```

⇒ 正确的增量表述是 **2701 → 2803（+102）**。

### A3（**FAIL**）：实跑读数与文档记的也不符

```
$ python -m pytest -q --no-header -p no:cacheprovider   # 在冻结树
2800 passed, 3 skipped, 38 warnings in 418.05s (0:06:58)
```

- 文档写（`pyproject.toml` 注释）：**2845 passed / 2 skipped / 0 failed**
- 实测：**2800 passed / 3 skipped**

pass 与 skip 两个数都对不上。

### A4（低）：同一事实两处两个数

- `pyproject.toml` 注释：「从 2745 → **2845** passed / 2 skipped」
- `scripts/run-gates.ps1` 注释：「`pytest --collect-only` 从 2745 → **2847**」

同一件事，一处 2845、一处 2847。

- **严重度**：中（A2/A3）／低（A4）
- **已变异验证**：否（读数类，非判据类）
- **是否已证伪**：是

---

## 2. 声称 B —— 四项判据（`recon/gate-quality.py`）

**主张**：默认走棘轮（比**率**不比绝对条数），`--strict` 才判绝对阈值；`--quiet` 纯 ASCII。

### B1（PASS）：`--quiet` 是纯 ASCII

```
$ python tools/gov-qa/recon/gate-quality.py --quiet > q.txt
$ python tools/gov-qa/recon/gate-quality.py --missing-cities --quiet > m.txt
nonASCII_bytes(q.txt)=0
nonASCII_bytes(m.txt)=0
```

### B2（PASS）：两种模式退出码确实不同（主仓，数据完整）

```
$ python tools/gov-qa/recon/gate-quality.py --quiet
ABS_CHECKS_FAILED=2
RATCHET_CHECKS_FAILED=0
MODE=ratchet
RATCHET=on
rc=0

$ python tools/gov-qa/recon/gate-quality.py --strict --quiet
ABS_CHECKS_FAILED=2
RATCHET_CHECKS_FAILED=0
MODE=strict
RATCHET=on
rc=1
```

默认 rc=0、`--strict` rc=1 ⇒ **"默认只判棘轮、strict 才判绝对阈值"属实**。棘轮比的是率：`ratchet()` 里 `cur_rate = cur_n / cur_t * 100000`，基线文件 `quality-baseline.json` 存 `{answer_empty, content_dups, time_inverted, total}` ⇒ 比率的说法成立。

### B3：变异测试（10 处，8 死 2 活）

夹具：内存字节快照 + 锚点替换 + 跑 pytest + 还原（未跟踪文件不能 `git checkout`）。还原后 `git status --short -- tools/gov-qa/` 为空。

| # | 变异 | 结果 |
|---|---|---|
| M1 | `verdicts` 的「无单源答复大面积为空」改恒真 | **红** 1 failed |
| M2 | 时间倒置改回裸比字符串 | **红** 4 failed |
| M3 | 棘轮改回比绝对条数 | **红** 1 failed |
| M4 | `coverage` 归集改回 `counts.get(c.key,0)` | **红** 2 failed |
| M5 | `health`「无重复 id」改恒真 | **红** 1 failed |
| M6 | `audit-coverage` 重复 id 退回单文件口径 | **绿（存活）** ← 见 §4 |
| M7 | `_igi_common._real` 改回不过滤 `null` | **红** 2 failed |
| M8 | `gate-quality --quiet` 的 `MODE` 改输出中文 | **绿（存活）** ← 见 §4 |
| M9 | `common.ascii_kv` 不过滤非 ASCII | **红** 1 failed |
| M11 | `--quiet` 分支绕过 `ascii_kv` 直写非 ASCII（闸门实跑 nonASCII=4） | **绿（存活）** ← 见 §4.1 |

- **严重度**：B1/B2 PASS；B3 的两个存活项见 §4
- **已变异验证**：是（9 处）

---

## 3. 声称 C —— 数据缺陷（逐条独立复现）

> 语料口径：冻结树 552 个 jsonl / **388,139** 条（仅跟踪文件）。§3.7 另记主仓 562 个 / **398,062** 条。

### C1（PASS）：`xz-lasa` 空答复 1030 → 1

```
$ 扫 tools/gov-qa/data/xz-lasa*.jsonl，数 answer.strip() 为空
匹配文件: ['xz-lasa-拉萨市·来信选登.jsonl']
总条数=1030  answer为空的条数=1
```

### C2（PASS）：`ln-8890` 时间倒置 7807 → 0

```
$ 数 source=ln-8890 里 answered_at < asked_at（解析后，容差 60s）
总条数=21748
解析后倒置(容差60s)=0
裸比字符串倒置(旧口径)=0
两个字段都有值但解析不了=0
```
零倒置、零不可解析 ⇒ 修得干净，且不是靠"解析不了就不算"糊过去的。

### C3（PASS）：IGI 字面 `"null"` 153 → 0

```
$ 数 question.strip().lower()=='null'
question.strip().lower()=='null' 条数=0（其中 source 含 igi 的 0）
answer.strip().lower()=='null' 条数=0
```

### C4（**部分不符**）：`extra.city` 住址 48 → 1

**用任务书给的判据（含门牌/小区/花园/公司/镇/村）实测是 0，不是 1：**

```
主仓：含 门牌/小区/花园/公司/镇/村 的 extra.city  条数 = 0   （声称修后 1）
```

**用 `FIXES-2026-10-10.md` 自述的两轮判据也复现不出 1：**

```
--- 判据[文档第1轮 门牌/楼栋] 命中 0 条 / 0 个不同值 ---
--- 判据[文档第2轮 +公司/园区/大厦/街/路] 命中 0 条 / 0 个不同值 ---
```

文档说"保留的那 1 条"是 `宁夏回族自治区固原市隆隆德县`（理由：是行政区划、站方笔误）。该串含 `县`，**不含** 门牌/小区/花园/公司/镇/村 中的任何一个 ⇒ 它本来就不在判据命中集里。所以"48 → 1"这个读数的**分母口径没写清**：按所述判据是 **48 → 0**。

**但 `extra.city` 确有残渣（原判据未覆盖的形态）：**

```
=== nx-zxxx 的 extra.city：归一化后不在 334 名录内、且含机构/楼栋词的 ===
不同值 31 个，记录 34 条
     2  '永宁四中'
     1  '西夏区宁夏大学政法学院'
     1  '银川市西夏区橡民B区'
     1  '彭阳县永信商贸综合楼'
     1  '花博园机场'
     1  '金凤区世茂悦玺'
     1  '宁夏银川市灵武市壹号公馆'
     ...
```

原值确实存进了 `extra.city_raw`（65 条 / 64 个不同值，其中 30 个是门牌级住址）：

```
city_raw 条数 = 65，不同值 64
其中像门牌级住址的 = 30
   '宁夏西吉县紫薇嘉园1号楼1单元702'
   '海原县四季花城B区九号楼二单元401'
   '银川市贺兰县宝庆国际花园31-1-801'
   ...
```

⇒ **降级处理（挪到 `city_raw`）属实；"1" 这个数复现不出（按所述判据是 0）；`extra.city` 本身仍留 34 条非地名值。**

- **严重度**：低-中（读数口径不严；且残渣仍在，但已移出被消费的 `city` 字段）
- **已变异验证**：否

### C5（PASS）：隐形 source 393 → 0

```
通道数 = 345
有数据的 source 数 = 706
旧口径下「不在销号表内」的 source = 393 个 / 121762 条   ← 与声称的 393 / 121,762 完全一致
新口径下仍无归属的 source = 0 个 / 0 条
```
样例：`ln-8890-kb: 13941`、`sx-igi-24: 5998`、`sx-igi-32: 5696`、`nmg-igi-66: 5650`。

### C6（PASS）：`coverage-report` 两入口数值 + 退出码一致

```
$ python tools/gov-qa/coverage-report.py --quiet
CITY_NONE=0
CITY_MISSING_FROM_334=176
rc=1

$ python tools/gov-qa/coverage-report.py --missing-cities --quiet
CITY_MISSING=176
rc=1
```
176 == 176，rc 都是 1 ⇒ 矛盾已消。（冻结树为 177/177、rc 均为 1，同样一致。）

- **严重度**：C1/C2/C3/C5/C6 PASS；C4 部分不符
- **已变异验证**：C1-C3、C5 为独立重算（非变异）；C6 见 §4 M10

---

## 4. 重点 —— 第 4 处「有牙但咬错对象」+ 测试恒真/空过面

> 用户自述写过 3 处同类（时间倒置裸比字符串 / 正则抠总量 / 截断前缀判据）。
> **找到第 4 处，以及另外 2 处同类。** 三者形态一致：判据会红，但红的不是它声称的那个东西。

### 发现 4.1（第 4 处，**核心发现**）：`--quiet` 纯 ASCII 判据测的不是 `--quiet`

**位置**：`tools/gov-qa/tests/test_gate_quality.py`，用例名 `test_quiet_output_is_pure_ascii`。

**主张**：该用例声称「`--quiet` 是给闸门读的，必须纯 ASCII」，文档字符串也这么写。

**反证**：把 `gate-quality.py` 里真正决定 `--quiet` 输出内容的 `MODE` 值改成中文，**闸门输出真的变脏了，而这条用例仍然全绿**：

```
[变异后] gate-quality.py --quiet   rc=1  ['MODE=??']  非ASCII字符数=0
[变异后] 该用例                    rc=0  ['1 passed in 0.05s']
[还原后] gate-quality.py --quiet   rc=1  ['MODE=ratchet']  非ASCII字符数=0
```

（`MODE=??` 是 GBK 控制台回显；关键证据是**该用例 rc=0**。）

**根因**：用例正文最后一行是

```python
ascii_kv({"TOTAL": 1, "NOTE": "中文"}, stream=buf)
buf.getvalue().encode("ascii")
```

它直接调 `common.ascii_kv` 并喂一个中文值 —— 测的是 **`ascii_kv` 会替换非 ASCII**（这一条被 M9 正确钉住），**根本没有执行 `gate-quality.py --quiet` 分支**。真正决定 `--quiet` 输出的是 `main()` 里那个 `ascii_kv({...})` 的字典内容，而它由 `MODE` 等值决定；**没有任何用例断言过那个字典**。

**更强的反证（M11：绕过 `ascii_kv` 消毒，直接写非 ASCII）** —— 闸门输出真的变脏，而**整个测试文件 20 条全绿**：

```
变异：在 --quiet 分支开头插入  sys.stdout.write("MODE=棘轮\n")
[闸门实跑] rc=0  stdout bytes=240  nonASCII=4  MODE 行含非 ASCII = True
[pytest]   rc=0  20 passed in 0.08s          ← 全绿
[还原后]   闸门 nonASCII=0
```

⇒ **门禁赖以解析的机器接口已经输出了非 ASCII 字节，而守它的 20 条用例一条都没红。**
与用户自述的三处**完全同型**：判据有牙（M9 证明它会红），但它咬的是 `ascii_kv`，不是 `gate-quality --quiet` 的出口。

- **严重度**：**高**（这是"给门禁读的机器接口必须纯 ASCII"这条硬约束的唯一守卫，而它没守住）
- **已变异验证**：是（M8）

### 发现 4.2（同类）：`test_dup_detection.py` 没有钉住真实实现

**位置**：`tools/gov-qa/tests/test_dup_detection.py`。

**主张**：文档字符串写「受控复现：两个文件各一条同 `(source,id)`，旧写法算出 0。⇒ 本用例钉住'全局计数'这个行为；**谁改回按文件计数，它必红**。」

**反证**：把 `audit-coverage.py` 的真实实现退回单文件口径（键里加文件名），**三条用例仍然全绿**：

```
[变异后] audit-coverage.py --gate  rc=0  ['DUPS=0']
[变异后] test_dup_detection.py      rc=0  ['3 passed in 0.04s']
[还原后] audit-coverage.py --gate  rc=0  ['DUPS=0']
[还原后] test_dup_detection.py      rc=0  ['3 passed in 0.05s']
```

**根因**（合成语料复现）：

```
合成语料：a.jsonl 与 b.jsonl 各一条同 (source=X, id=1)
  正确（全局）口径 dups = 1
  变异（加文件名）口径 dups = 0
```

- 前两条用例**自己内联复刻**了计数逻辑（`hits`/`dups` 在测试文件里重写一遍），测的是副本，不是实现；
- 第三条 `test_source_implementations_use_global_counting` 只断言 `"hits" in body` —— 变异后 `hits` 仍在 body 里，**照样通过**。

⇒ 文档写"谁改回去必红"，实测**必绿**。声称与事实相反。

- **严重度**：中-高
- **已变异验证**：是（M6）

### 发现 4.3（同类）：`health.py` 仍带着本批已修的同类盲区

**位置**：`tools/gov-qa/health.py`，`collect()` 里的 `per_src`。

**主张**：本批（T203 之二）声称修好了「重复 id 判据的跨文件盲区」，并在 `audit-coverage.py` 里留了详细注释。

**反证**：`health.py` 的同名判据**仍然是单文件口径**：

```
=== health.py 重复 id 判据：同文件 vs 跨文件 ===
A 同文件同 id 两条      => dups=1  (期望 1)
B 跨文件同 (source,id)  => dups=0  (期望 1；若为 0 即跨文件盲区)
C 同文件不同 id        => dups=0  (期望 0)
```

源码对照 —— `health.py`：

```python
for p in files:
    per_src: dict[str, dict[str, int]] = defaultdict(...)   # ← 在文件循环内
    ...
    for c in per_src.values():
        dups += sum(c.values()) - len(c)
```

`audit-coverage.py`（已修）：

```python
hits: dict[tuple, int] = {}
for p in glob.glob(...):        # ← per-file 状态提到循环外
    ...
    hits[key] = hits.get(key, 0) + 1
dups = sum(n - 1 for n in hits.values() if n > 1)
```

**当前语料未触发**（实测无跨文件重复），所以是**潜伏缺陷**，不是现网假绿：

```
记录总数 = 388139
health.py 口径（每文件内重复）dups = 0
跨文件同 (source,id) 的键数 = 0
health.py 漏掉的 = 0
```

**且 `health.py` 未被任何门禁调用**：

```
$ grep health scripts/run-gates.ps1 tools/gov-qa/gate/check.sh
(empty)
```

⇒ 本批把 `audit-coverage.py` 的那处修了、写了测试、写了注释，**同一个 bug 在兄弟文件里原样留着**，而且那个文件连门禁都没接。

- **严重度**：中（潜伏；若将来出现跨文件重复，`health.py` 会报 `dups=0`）
- **已变异验证**：是（探针 + M5）

### 发现 4.4：`test_coverage_report_consistency.py` 只判"一致"，不判"对"

**位置**：`tools/gov-qa/tests/test_coverage_report_consistency.py`。

**主张**：核心判据是「两个入口报出的缺失数必须**相等**」。

**反证**：把 `_missing_cities_detail` 改成"全部市都算已覆盖"（两边都报 0），**四条用例全绿**：

```
{"label":"M10 coverage-report: both entrypoints report ZERO missing",
 "applied": true, "rc": 0, "red": false, "tail": ["....  [100%]","4 passed in 29.95s"]}
```

两个入口**一致地报错**，判据照样通过。用例只锁"两者相等"，不锁"这个数是对的"。

**关于"模块级缓存会不会让某条用例实际没测到"**（任务书点名问的）：

- **结论：不会。** `_CACHE` 以 `"quiet"` / `"missing"` 为键，4 条用例每条都至少读一个缓存结果并对其做断言；两条 `subprocess.run` 真实执行。没有用例是"因为缓存所以没跑"。
- **真正的问题是上面那条**：一致 ≠ 正确。

- **严重度**：中
- **已变异验证**：是（M10）

### 发现 4.5（PASS）：其余 6 个新测试文件**未**发现恒真/空过面

- `test_igi_null.py` —— M7 红（`_real` 改回不过滤 `null`）⇒ 有牙。含反向用例 `test_real_keeps_genuine_content`。
- `test_child_source_attribution.py` —— M4 红 ⇒ 有牙。含反向用例 + 端到端语料用例。
- `test_health_checks.py` —— M5 红 ⇒ 逐项钉住，确实解决了它文档里说的"四项同时改才变红"。
- `test_gate_quality.py` 的其余 19 条 —— M1/M2/M3/M9 红 ⇒ 有牙。**仅 `test_quiet_output_is_pure_ascii` 一条空过面**（§4.1）。
- `test_coverage.py`、`test_poll.py`（本批改）—— 未逐一变异（**未验**）。

---

## 5. 声称 D —— "我故意没做"的，是否说实话

### D1（PASS）：`sd-yantai` 1,629 条**不是截断** —— 回原站取证，作者说的是真的

抓任务书给的原站详情页（注意：http 会跨域重定向，须用 https）：

```
$ web_fetch https://www.yantai.gov.cn/api-gateway/jpaas-jact-web-server/front/mail-pub-detail?iid=d7fed600dfe140c4ac2631f4b0a4e1a8
HTTP 200
| 答复部门： | 栖霞市纪委 | 答复日期： | 2026-10-08 |
| 答复内容： | 通过  |
```

原站 `答复内容` **确实只有「通过」两个字**。⇒ **不是截断，判据措辞改为"待核对"是正确的。**

本地语料侧：

```
total 19907
  1629 '<同一段长答复>'      ← 声称的 1,629 条是"同一段长答复重复"，不是"被截断"
    17 '通过'                 ← 与详情页一致
前缀判据（短答复是长答复前缀）命中 73 个值 / 2555 条
```

- **严重度**：—（PASS）
- **已变异验证**：否（原站取证）

### D2（PASS）：重复**打标记不删**，总数仍为 398,062

```
$ 主仓扫 tools/gov-qa/data/*.jsonl
主仓 jsonl 文件数 = 562
主仓记录总数 = 398062   （声称 398,062）
```

标记确实存在（且是"两个都留"的形态）：

```
  8380  content_dup_role=duplicate
  5580  content_dup_role=canonical
  1020  same_id_role=duplicate
   689  same_id_role=canonical
   + content_dup_group=<hash> 分组标记
```

⇒ 13,960 条 = 8380+5580；1,709 条 = 1020+689。**与声称的 T203/T206 数字对得上，且没有删记录。**

- **严重度**：—（PASS）
- **已变异验证**：否（读数）

### D3（PASS）：`T301` 只登记 39/345 有真值，且拒绝正则候选

```
=== targets.json ===
targets 类型=dict, 条目数=345
  _status=needs-probe: 306
  _status=verified-total: 37
  _status=verified-probe: 2
有真值 = 39 / 345
```

39/345 = 11.3% ⇒ 与"只有 39/345 有真值"一致。`_status_legend` 明写 `needs-probe: 可能有总量但本批未核实（**不写猜测值**）`。

正则候选被拒的证据（`gd-amr` 那条）：

```
[verified-probe] {"total": 807, "cap": null, "_status": "verified-probe",
                  "_landed": 6134,
                  "note": "2026-10-10 实测打印的总量｜hdjlpt letter/pubList；探测年窗 total=773"}
```

`773`（正则抠出）与 `807`（真值）并列留在 note 里 ⇒ "拒绝 80 个候选"的说法**与数据一致**（我未逐条核对那 80 个候选的清单，**该部分未验**）。

- **严重度**：—（PASS，候选清单未验）
- **已变异验证**：否

### D4（PASS）：未碰 `gx-igi-*`

```
$ git log --name-only --oneline 88644c6..7bc67704 | Select-String "gx-igi"
(无输出)
```
⇒ 该区间内 `gx-igi-*` 一次都没出现在变更文件里，**属实**。

补充事实（不矛盾）：主仓有 10 个 `gx-igi-*.jsonl` 是**未跟踪**的（另一采集方所写），冻结树里没有：

```
?? tools/gov-qa/data/gx-igi-145-...jsonl
?? tools/gov-qa/data/gx-igi-152-...jsonl
... 共 10 个
```

- **严重度**：—（PASS）
- **已变异验证**：否

---

## 6. 重点 —— `coverage.py::_attribute_counts` 的最长前缀消歧

**主张**：最长前缀消歧正确，不重不漏。

**反证（构造 `a` / `a-1` / `a-1-2` 边界用例）**：

```
counts={'a': 100, 'a-1': 20, 'a-1-2': 3}  channel_keys={'a-1','a','a-1-2'}
  _attribute_counts('a')     = (total=100, n_src=1)
  _attribute_counts('a-1')   = (total=20,  n_src=1)
  _attribute_counts('a-1-2') = (total=3,   n_src=1)
  三个通道合计 = 123   （期望 123）        ← 不重算 ✓

channel_keys={'a'}        (只有 a 是通道)
  _attribute_counts('a') = (123, 3)         ← 不漏算 ✓

channel_keys={'a-1'}      (a 不是通道)
  _attribute_counts('a-1') = (23, 2)        ← a-1 + a-1-2 ✓

counts={'ab':5,'a':7} keys={'a','ab'} 合计=12  ← 无分隔符不误吞 ✓
```

**真实语料交叉验证（不重不漏的强证据）**：

```
通道数=345  有数据的 source 数=696
所有通道归集到的条数合计 = 388139
语料里 source 非空的记录总数 = 388139
差额 = 0
被多个通道 key 前缀匹配的 source 数 = 33   （>0 ⇒ 消歧确实在用）
```

⇒ **`_attribute_counts` 的最长前缀消歧正确。** 33 个 source 会命中多个通道 key，消歧把差额压到 0；`len(ck) > len(owner)` 的取最长逻辑在同长度下不可能并列（两个不同 key 不可能同为同一 `k` 的前缀）。

- **严重度**：—（PASS）
- **已变异验证**：是（M4 把归集改回精确匹配 ⇒ 红）

---

## 7. 复核方法学与偏差声明

1. **提取树缺少 `.venv`**：`git worktree` 不含被 `.gitignore` 的 `.venv`。首轮全量跑出 3 条 `test_coverage_report_consistency.py` 失败，根因是 `PY = ROOT.parent.parent/".venv"/...` 在该树里不存在（`FileNotFoundError`）。在提取树内建了一个**真 venv** 后，同一组用例 **4 passed**。⇒ 那 3 条红是**我的环境假红**，不是被审批次的缺陷。**已更正**。
   - 附带发现（低）：`test_coverage_report_consistency.py` 与 `test_gbk_safety.py` 硬编码 `.venv` 相对路径 ⇒ **任何提取树/CI 上都会红**。
2. **提取树缺少 10 个未跟踪数据文件**：首轮 `gate-quality.py` 报 `RATCHET_CHECKS_FAILED=2` / rc=1，根因是语料只有 552 个文件（388,139 条）而非完整 562 个（398,062 条），分母不同。把主仓的 10 个未跟踪 `gx-igi-*.jsonl` 真拷贝进提取树后，**rc=0**。⇒ 那两红同样是环境假红。**已更正**。
3. **`TIME_INVERTED` 在主仓(1516)与冻结树(3399)不同**：不是矛盾，是冻结之后落的 `05bef187 fix(govqa/005): T208 —— sc-yibin 的 1,883 条哨兵日期 2000-01-01 置空` + `fdaa6759 棘轮基线锁定 T208 成果 —— 时间倒置 3399 -> 1516`。冻结树的基线文件写 3399，两棵树各自自洽。
4. **所有变异均在内存字节快照下完成并还原**；还原后 `git status --short -- tools/gov-qa/` 为空。变异**未**在活动工作区进行。
5. 我**未**修改任何被审代码。主仓内我只写了 `.tmp-verify-*.txt` 中间产物（自己的取证记录）与本报告。

---

## 8. 按严重度排序的清单

| # | 严重度 | 发现 | 位置（可搜索文本） | 已变异验证 |
|---|---|---|---|---|
| 1 | **高** | `--quiet` 纯 ASCII 判据测的是 `common.ascii_kv`，**从未执行 gate 的 `--quiet` 出口**；让 `--quiet` 真的输出非 ASCII（实测 nonASCII=4）后，该测试文件 **20 条仍全绿** | `test_gate_quality.py` → `def test_quiet_output_is_pure_ascii` | 是（M8、M11） |
| 2 | **中-高** | `test_dup_detection.py` 前两条内联复刻计数逻辑、第三条只断言 `"hits" in body`；真实实现退回单文件口径后**三条全绿**（文档却写"谁改回去必红"） | `test_dup_detection.py` → `def test_duplicate_id_across_two_files_is_detected` / `def test_source_implementations_use_global_counting` | 是（M6） |
| 3 | **中** | 根 pytest 条数不是 2847 而是 **2803**（2701+102）；2745 是含 4 个冻结外/未跟踪测试文件的工作区数 | `pyproject.toml` → `testpaths = ["tests", "tools/gov-qa/tests"]` 上方的注释块；`scripts/run-gates.ps1` → `#   实测：\`pytest --collect-only\` 从 2745 → **2847**` | 否 |
| 4 | **中** | 实跑 **2800 passed / 3 skipped**，文档写 2845 passed / 2 skipped（pass 与 skip 都不符） | 同上注释块 `实测合并无冲突：\`pytest tests tools/gov-qa/tests\` ⇒ **2845 passed / 2 skipped / 0 failed**` | 否 |
| 5 | **中** | `health.py` 的重复 id 判据**仍是单文件口径**（跨文件恒 0）—— 本批在 `audit-coverage.py` 修掉的同一个 bug，兄弟文件原样留着；且 `health.py` **未被任何门禁调用** | `health.py` → `per_src: dict[str, dict[str, int]] = defaultdict(...)`（在 `for p in files:` 之内） | 是（探针 + M5） |
| 6 | **中** | 一致性用例只判"两入口相等"，不判"数对不对"；两边一致地报 0 时四条全绿 | `test_coverage_report_consistency.py` → `def test_two_entrypoints_agree_on_missing_count` | 是（M10） |
| 7 | 低-中 | `extra.city` 住址"48 → 1"复现不出：按所述判据（含门牌/小区/花园/公司/镇/村）实测 **0**；保留的那 1 条含"县"不含任何所述标记；且 `extra.city` 仍留 34 条非地名值（`永宁四中`/`花博园机场`/`西夏区宁夏大学政法学院`…） | `FIXES-2026-10-10.md` → `## T207 · \`extra.city\` 里的个人住址（48 → 1）` | 否 |
| 8 | 低 | 同一事实两处两个数（`pyproject.toml` 写 2845、`run-gates.ps1` 写 2847） | `scripts/run-gates.ps1` → `从 2745 → **2847**` vs `pyproject.toml` → `**2845 passed**` | 否 |
| 9 | 低 | 两个测试文件硬编码 `.venv` 相对路径 ⇒ 提取树/CI 上必红 | `test_coverage_report_consistency.py` → `PY = ROOT.parent.parent / ".venv" / "Scripts" / "python.exe"`（`test_gbk_safety.py` 同形） | 否（环境复现） |
| 10 | 低（流程） | 复核期间主仓 HEAD 被移动 19 笔（`478cc5b3` → `0041c270`） | `git reflog` | 否 |

**通过项（干净，不造发现）**：`testpaths` 已接入；`--quiet` 纯 ASCII；棘轮 vs `--strict` 退出码语义；9 处变异中 7 处正确报红；`xz-lasa` 1030→1；`ln-8890` 倒置→0；IGI `"null"`→0；隐形 source 393/121,762→0；`coverage-report` 两入口 176/176 rc 一致；`_attribute_counts` 最长前缀消歧（含 `a`/`a-1`/`a-1-2` 边界 + 真实语料差额 0）；`sd-yantai` 回原站证实"通过"二字为真；重复打标记不删且总数 398,062；`T301` 39/345；未碰 `gx-igi-*`；模块级缓存**未**使任何用例空过。

**未验**：`test_coverage.py` / `test_poll.py` 的变异；`T301` 被拒的 80 个正则候选清单（只验了 `gd-amr` 773/807 这一条留在 note 里的证据）。

---

## 9. 总判定

**有条件 PASS。**

- 声称的四项数据缺陷（C1/C2/C3/C5/C6）**全部独立复现成立**，C4 的"1"复现不出但降级处理属实；
- 声称"故意没做"的四条（D1–D4）**全部属实**，其中 D1 已回原站取证确认；
- 门禁接入、棘轮/严格两模式语义、`_attribute_counts` 消歧**均正确**；
- **但**：本批新增测试里存在 **1 处高严重度空过面**（`--quiet` 纯 ASCII 判据，正是用户要找的第 4 处"有牙但咬错对象"）、**1 处中-高**（重复 id 测试没钉住真实实现）、**2 处中**（一致性用例只判相等；`health.py` 同类盲区未修且未接门禁）；
- 以及**门禁文档里的核心读数 2847/2845 与实际 2803/2800 不符**（"+102" 增量正确，绝对值是工作区数而非冻结提交数）。

⇒ 结论：**功能实现层面基本可信；"判据确实咬住了它声称的对象"这一层仍有 4 处未达标，且其中 1 处正是本批的核心自述教训。** 建议按 #1–#6 逐条整改后重跑一次冻结复核。

---

## 10. 报告结尾状态（要求项）

```
$ git rev-parse HEAD
0041c270cd59d493d8371bdb6f9b7eaf5137c11e

$ git status --short
total=768  tracked_modified=39  untracked=729
```

（会话起始 HEAD = `478cc5b3`；复核期间被移动 **19 笔**，见 §0。`tracked_modified` 从 44 变 36→39 的抖动来自并行写入方，不是本次复核所为 —— 本次复核**只在提取树内改文件并全部还原**，主仓只写了自己的取证中间产物与本报告。）

被审对象（冻结 tag，全程未变）：

```
$ git rev-parse verify-freeze-govqa-conformance
05d276a2a1affdf96d5b7ad5b630eb36ee04e352      （annotated tag）
$ git rev-parse verify-freeze-govqa-conformance^{commit}
7bc67704ff07b32780b15091550bd70bc55d1b91
```
