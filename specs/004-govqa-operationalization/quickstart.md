# Quickstart: 政务问答采集系统的可运维化

> **这是验收/运行指南，不是实现文档。** 实现细节见 `tasks.md` 与代码本身。
> 每个场景都可以**照着敲命令、看结果**，用来证明这条能力真的能用。

> ## ⚠⚠ 2026-10-10 更正：本文件原有 **4 条命令是错的**（跑不起来）
>
> **实测**（逐条真跑，`rc` 是真实退出码）：
>
> | 原文写的 | 实测 | 正确写法 |
> |---|---|---|
> | `poll-all.py --sites … --report` | **rc=2**（文件不存在） | `poll.py --channel <key> --timing`（`poll-all.py` **从未存在**） |
> | `audit-coverage.py --coverage-table` | **rc=2**（无此开关） | `coverage-report.py --level province` |
> | `audit-coverage.py --gaps --unit 云南` | **rc=2**（无此开关） | `coverage-report.py --region 云南 --uncovered --quiet` |
> | `audit-coverage.py --health` | **rc=2**（无此开关） | `health.py --quiet`（或直接 `health.py` 看中文结论） |
>
> **根因**：本文件是 **Phase 1 设计产物**（写于实现之前），而实现把能力落在了
> **别的入口**（`poll.py` / `coverage-report.py` / `health.py`）——
> 设计稿的命令名**没有跟着实现改**。⚠ 这正是"**设计产物不跟着实现走就会变成谎话**"的实例。
>
> **处置**：下文**逐条改成实测可跑的写法**；**原文保留在上表**（宪法 V：打错的话不许悄悄删）。
> ⚠ **未做**：本文件的 9 个场景**没有逐条重跑并回填实测读数**
> （那是 tasks.md 的 **T054**，仍**未勾选**）—— 本节只修了**命令本身跑不起来**这个更硬的问题。

**前置**：项目根 `D:/AI/work space/zcode`，解释器 `.venv/Scripts/python.exe`。

```bash
cd "D:/AI/work space/zcode"
P=".venv/Scripts/python.exe"
```

---

## 场景 0：现状体检（30 秒，先确认系统健康）

```bash
$P tools/gov-qa/recon/audit-coverage.py --gate
```

**期望**：输出纯 ASCII 的 `KEY=VALUE`，形如

```
TOTAL=357823
EMPTY=0
DUPS=0
```

**判读**：`EMPTY>0` ⇒ 有「建好没采」的通道；`DUPS>0` ⇒ 有重复 id 污染。
两项都为 0 才继续。

---

## 场景 1：US1 增量轮询 —— 证明「第二次只取新增」（P1，核心）

> 对应 spec 的 Independent Test。**这是整个特性最该被证明的一条。**

### 1.1 首次轮询，记录水位

```bash
$P tools/gov-qa/poll.py --channel mee --channel nat-tax --channel hb-wuhan
```

> ⚠ **更正**：原文写 `poll-all.py --sites mee,nat-tax,hb-wuhan --report` —— **那个文件不存在**（实测 rc=2）。
> 实现是 **`poll.py`**，通道用**可重复的 `--channel`**（不是逗号分隔的 `--sites`）；
> 人类可读汇总**默认就打印**（没有 `--report` 开关）。

**期望**：
- 每个通道打印「本次新增 N 条」
- 生成水位文件 `tools/gov-qa/state/watermarks.json`
- 末尾有汇总表：`通道 | 新增 | 水位 | 耗时`

**记下水位**：

```bash
$P -c "import json;d=json.load(open('tools/gov-qa/state/watermarks.json',encoding='utf-8'));print(json.dumps({k:v for k,v in list(d.items())[:3]},ensure_ascii=False,indent=1))"
```

### 1.2 立刻再跑一次（源站无更新）

```bash
$P tools/gov-qa/poll.py --channel mee --channel nat-tax --channel hb-wuhan --timing
```

> ⚠ **更正**：原文写 `poll-all.py --sites mee,nat-tax,hb-wuhan --report` —— **那个文件不存在**（实测 rc=2）。
> 实现是 **`poll.py`**，通道用**可重复的 `--channel`**（不是逗号分隔的 `--sites`），
> 也没有 `--report` 开关（人类可读汇总**默认就打印**）。

**期望（SC-002）**：**每通道新增 0 条**，且

```bash
$P tools/gov-qa/recon/audit-coverage.py --gate
```

`DUPS=0`（没有因为重复采集产生重复记录）。

### 1.3 证明「水位真的省了请求」（不只是去重）

> ⚠ 关键：**只看「新增 0 条」不能证明增量生效** —— 全量翻页 + 去重也会得到「新增 0 条」。
> 必须看**请求数或耗时**是否显著下降。

```bash
# 第二次轮询应比第一次快得多（翻到水位即停，不再翻到底）
$P tools/gov-qa/poll.py --channel mee --timing
```

> ⚠ **更正**：原文写 `poll-all.py --sites mee --report --timing` ⇒ 同样不存在（rc=2）。

**期望**：`--timing` 打印的 `pages_fetched` 明显小于首次（理想情况：只翻 1 页就停）。

### 1.4 水位损坏 → 安全退化全量（FR-006）

```bash
# 备份并破坏水位
cp tools/gov-qa/state/watermarks.json /tmp/wm.bak
echo '{"mee": {"broken": true}}' > tools/gov-qa/state/watermarks.json

$P tools/gov-qa/poll.py --channel mee
```

> ⚠ **更正**：原文写 `poll-all.py --sites mee --report` ⇒ 同样不存在（rc=2）。

**期望**：不报错，日志里出现「水位不可用 → 退化为全量」，
且**不产生重复记录**（`audit-coverage.py --gate` 的 `DUPS=0`）。

```bash
cp /tmp/wm.bak tools/gov-qa/state/watermarks.json   # 还原
```

---

## 场景 2：US2 覆盖销号表

```bash
$P tools/gov-qa/coverage-report.py --level province
```

> ⚠ **更正**：原文写 `audit-coverage.py --coverage-table` —— **`audit-coverage.py` 没有这个开关**（实测 rc=2）。
> 覆盖销号表的正式入口是 **`coverage-report.py`**（`audit-coverage.py` 是"逐适配器体检"，
> 两件事，别混）。
>
> ⚠ **实测退出码提醒**：`--level province --quiet` 在本机**退出码是 1**，而 `PROV_NONE=0`。
> 按 `contracts/coverage.md` 的约定，`1` = "有 `none`（无来源）单元"；这里触发它的是
> **`CITY_MISSING_FROM_334=176`**（**跨层级**：即使只看省级，市级缺口也参与了判定）。
> ⇒ **读退出码时要连输出一起看**，别把"有零记录市"误读成"某个省没来源"。
> （该行为在 `tools/gov-qa/coverage-report.py`，属并行自动化的面，**本轮只登记不改**。）

**期望**：一张表，逐个列出

```
层级   单位        来源数  落盘量   达标线  状态     缺口
省级   云南          2       84     3000    ❌ 不足   -2916
省级   重庆          1    11269     3000    ✅
地级   苏州          1      149     500     ❌ 不足    -351
...
```

**判读（SC-004/SC-005）**：
- 31 个省级 + 333 个地级**每个都出现**（不允许缺行）
- 不足的**100% 标红并给出缺口数值**

### 2.1 查某个薄弱地区「还差哪些渠道」（SC-006）

```bash
$P tools/gov-qa/coverage-report.py --region 云南 --uncovered --quiet
```

> ⚠ **更正**：原文写 `audit-coverage.py --gaps --unit 云南` —— **两个开关都不存在**（实测 rc=2）。
> 正确入口是 `coverage-report.py`，用 **`--region <名称包含匹配>`** + **`--uncovered`**。
> **实测输出**（2026-10-10）：
> ```
> 云南省（province）
> RECORDS=66  GAP=2934  STATUS=thin
>   来源 1 个｜落盘 66 条｜达标线 3,000｜缺口 2,934
>   未覆盖渠道：门户·政民互动、12345 热线、省长信箱、人大·法规征求意见
> ```

**期望**：列出该省**尚未建立来源的渠道清单**（而不是只说"数据少"）。

---

## 场景 3：US3 数据可用性

### 3.1 字段体检（FR-015, SC-008）

```bash
$P tools/gov-qa/recon/field-audit.py
```

**期望**：
- 每个字段的非空率
- **单独列出** `question` 为空但 `answer` 非空的记录，**带来源**
- 明确报告「问题与答复同时为空」的条数（SC-008 要求 = 0）

### 3.2 标签真实准确率（FR-014, SC-007）

```bash
# 随机抽 200 条（覆盖各标签、各来源），导出成可人工核对的表单
$P tools/gov-qa/recon/label-accuracy.py --sample 200 --export /tmp/label-check.csv
```

人工核对 `label-check.csv` 的 `label_ok` 列（1/0），然后：

```bash
$P tools/gov-qa/recon/label-accuracy.py --score /tmp/label-check.csv
```

**期望**：输出真实准确率。**SC-007 要求 ≥ 80%**。

> ⚠ 这是**人工**环节，不是自动跑完就算。未核对时必须报「明确未做」，不许拿模型自评数充数
> （Constitution III）。

---

## 场景 4：US4 自愈与可观测

### 4.1 一句话结论（SC-011）

```bash
$P tools/gov-qa/health.py --quiet
```

> ⚠ **更正**：原文写 `audit-coverage.py --health` —— **没有这个开关**（实测 rc=2）。
> 健康结论的正式入口是 **`health.py`**：`--quiet` 出纯 ASCII，不加则出**中文一句话结论**。
> **实测输出**（2026-10-10）：
> ```
> VERDICT=usable
> TOTAL=398062
> FLOOR=391769
> EMPTY=0
> DUPS=0
> COVERAGE=98.4
> ```

**期望**：一句话，例如

```
✅ 可用：357,823 条 / 0 重复 / 0 空通道 / 标签覆盖 100.0%
```

或

```
❌ 不可用：2 个零数据适配器（hb-wjw, rd-js）
```

### 4.2 故障检出（SC-009）—— 人为制造 3 类故障

> ⚠ **必须在副本上做**，不许动真数据。
> ⚠ **更正**：原文用 `audit-coverage.py --health --data-dir …` —— 那两个开关**都不存在**（实测 rc=2）。
> 正确入口是 `health.py`，且它**没有 `--data-dir`**（隔离靠环境变量 `KS_DATA_DIR`）。
> ⚠ **本节的"3 类故障"演示本轮未重跑**（属 T054 的未做项，见文件抬头的更正块）。

```bash
# 准备隔离副本（用 KS_DATA_DIR 指过去，不是 --data-dir）
mkdir -p /tmp/health-test && cp -r tools/gov-qa/data /tmp/health-test/

# 故障 1：删一个数据文件（模拟损坏）
mv /tmp/health-test/data/mee-*.jsonl /tmp/

# 故障 2：塞一条重复 id
head -1 /tmp/health-test/data/hb-wuhan-*.jsonl >> /tmp/health-test/data/hb-wuhan-*.jsonl

# 故障 3：注册一个空适配器
# （在副本的 registry 里加一个无数据的源）

KS_DATA_DIR=/tmp/health-test $P tools/gov-qa/health.py --detail
```

**期望（SC-009）**：**一次运行内三类故障全部检出**，且每条给出可定位的信息（哪个文件 / 哪个源）。

### 4.3 体检耗时（SC-010）

```bash
time $P tools/gov-qa/recon/audit-coverage.py --gate
```

**期望**：**≤ 60 秒**（当前实测约 20 秒）。

### 4.4 执行轨迹（FR-019）

```bash
tail -20 "D:/AI/output/check-trace.log"
```

**期望**：每次体检都留痕 —— 时间、解析出的数值、结论。

---

## 场景 5：全量验收（收工前跑）

```bash
bash "D:/AI/output/check.sh"; echo "exit=$?"
```

**期望**：`exit=0`（质量 4 项全绿 + 连续工作 ≥24h）。
未满 24h 时必然 `exit=1` —— 这是设计如此，不是故障。

---

## 排错速查

| 症状 | 先查什么 |
|---|---|
| 闸门报「拿不到数据总数」 | `audit-coverage.py --gate` 是否能在**无终端**环境输出纯 ASCII |
| 标签覆盖率假红 | 是否用了 `--quiet`（非 UTF-8 终端会 UnicodeEncodeError） |
| 轮询「新增 0 条」但怀疑没生效 | 看 `--timing` 的 `pages_fetched`，**别只看新增数** |
| 水位越跑越旧 | 检查「采到 0 条不前移水位」这条规则是否被误改 |
| 重复 id | 是否同一个站有两路在采（GOAL.md 硬约束 4） |
