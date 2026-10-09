# 契约：覆盖销号表命令 `coverage-report.py`

**对应需求**: FR-007 ~ FR-011 ｜ **对应成功判据**: SC-004 / SC-005 / SC-006

---

## 命令面

```bash
# 生成全国销号表（省级 + 地级）
python tools/gov-qa/coverage-report.py

# 只看某层级
python tools/gov-qa/coverage-report.py --level province
python tools/gov-qa/coverage-report.py --level city

# 只看薄弱地区（按缺口降序）
python tools/gov-qa/coverage-report.py --thin --top 20

# 看某个地区缺什么渠道
python tools/gov-qa/coverage-report.py --region 云南省 --uncovered

# 调整达标下限（默认 省级 3000 / 地级 500）
python tools/gov-qa/coverage-report.py --threshold-province 2000 --threshold-city 300

# 按口径过滤（配合 GOAL.md 的「口径收窄」）
python tools/gov-qa/coverage-report.py --scope law_std

# 机器可读
python tools/gov-qa/coverage-report.py --quiet
```

---

## 退出码

| 码 | 含义 |
|---|---|
| `0` | 报告生成成功（**不代表覆盖达标**） |
| `1` | 有 `none`（无来源）的单元 —— 用于「覆盖完整性」闸门 |
| `2` | 生成失败（数据读不到等） |

> ⚠ **退出码 `1` 的语义**：有地区**完全没有来源**。这是硬缺口，必须报红。
> 「有来源但数据少」（`thin`）**不**触发退出码 1 —— 那是深度问题，不是缺失问题。

---

## 输出契约

### 人类可读（默认，中文）

```
覆盖销号表 —— 全国政务问答来源（生成于 2026-10-10 04:10）

【省级】31 个单元
  ✅ ok    18 个（≥3000 条）
  ⚠️ thin  13 个（有来源但不足）
  ❌ none   0 个

  缺口最大的 10 个：
    云南省            84 条    还差 2,916 条   （中位数 0.03 倍）  ← 缺 4 类渠道
    福建省           175 条    还差 2,825 条   （中位数 0.06 倍）
    新疆维吾尔自治区  232 条    还差 2,768 条   （中位数 0.08 倍）
    ...

【地级】333 个单元
  ✅ ok    92 个
  ⚠️ thin 156 个
  ❌ none  85 个          ← 这 85 个城市完全没有来源
  ...
```

### 机器可读（`--quiet`，**纯 ASCII**）

```
PROV_TOTAL=31 PROV_OK=18 PROV_THIN=13 PROV_NONE=0
CITY_TOTAL=333 CITY_OK=92 CITY_THIN=156 CITY_NONE=85
UNIT=province|云南省|84|3000|2916|0.03|thin|4
UNIT=province|福建省|175|3000|2825|0.06|thin|3
...
```

---

## 行为契约

| # | 性质 | 如何验证 |
|---|---|---|
| 1 | 每个省级行政区都有行 | 行数 = 31（不含脏值） |
| 2 | 每个地级行政区都有行 | 行数 = 333 |
| 3 | 缺口数值可执行 | `gap = max(0, threshold - total)`，且 `total + gap ≥ threshold` |
| 4 | **能列出未覆盖渠道** | `--region X --uncovered` 输出该地区**尚未建源的渠道清单**（FR-010） |
| 5 | 「查完没有」与「没查」可区分 | 已穷尽的地区显式写「已穷尽」，不留空 |
| 6 | 下限可调 | 改 `--threshold-*` 后所有 `gap` 同步变化 |

---

## 前置条件

- `tools/gov-qa/data/*.jsonl` 可读
- `tools/gov-qa/SITE-REGISTRY.md` 或 adapter 元数据可读（用于地区归属）

## 副作用

**只读**。不写任何数据文件。
可选 `--out <file>` 输出报告到指定路径。

## 明确未做

- ❌ 不自动补采（那是 `poll.py` / `harvest.py` 的职责）
- ❌ 不修改达标状态（状态是**算出来的**，不是存下来的 —— 避免状态与实际不一致）
- ❌ 不做可视化（用户要的是能查的表，不是图）
