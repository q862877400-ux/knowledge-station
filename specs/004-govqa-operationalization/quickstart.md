# Quickstart: 政务问答采集系统的可运维化

> **这是验收/运行指南，不是实现文档。** 实现细节见 `tasks.md` 与代码本身。
> 每个场景都可以**照着敲命令、看结果**，用来证明这条能力真的能用。

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
$P tools/gov-qa/poll-all.py --sites mee,nat-tax,hb-wuhan --report
```

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
$P tools/gov-qa/poll-all.py --sites mee,nat-tax,hb-wuhan --report
```

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
$P tools/gov-qa/poll-all.py --sites mee --report --timing
```

**期望**：`--timing` 打印的 `pages_fetched` 明显小于首次（理想情况：只翻 1 页就停）。

### 1.4 水位损坏 → 安全退化全量（FR-006）

```bash
# 备份并破坏水位
cp tools/gov-qa/state/watermarks.json /tmp/wm.bak
echo '{"mee": {"broken": true}}' > tools/gov-qa/state/watermarks.json

$P tools/gov-qa/poll-all.py --sites mee --report
```

**期望**：不报错，日志里出现「水位不可用 → 退化为全量」，
且**不产生重复记录**（`audit-coverage.py --gate` 的 `DUPS=0`）。

```bash
cp /tmp/wm.bak tools/gov-qa/state/watermarks.json   # 还原
```

---

## 场景 2：US2 覆盖销号表

```bash
$P tools/gov-qa/recon/audit-coverage.py --coverage-table
```

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
$P tools/gov-qa/recon/audit-coverage.py --gaps --unit 云南
```

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
$P tools/gov-qa/recon/audit-coverage.py --health
```

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

```bash
# 准备隔离副本
mkdir -p /tmp/health-test && cp -r tools/gov-qa/data /tmp/health-test/

# 故障 1：删一个数据文件（模拟损坏）
mv /tmp/health-test/data/mee-*.jsonl /tmp/

# 故障 2：塞一条重复 id
head -1 /tmp/health-test/data/hb-wuhan-*.jsonl >> /tmp/health-test/data/hb-wuhan-*.jsonl

# 故障 3：注册一个空适配器
# （在副本的 registry 里加一个无数据的源）

$P tools/gov-qa/recon/audit-coverage.py --health --data-dir /tmp/health-test/data
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
