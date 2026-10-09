# 契约：增量轮询命令 `poll.py`

**对应需求**: FR-001 ~ FR-006 ｜ **对应成功判据**: SC-001 / SC-002 / SC-003

---

## 命令面

```bash
# 全部通道轮询一遍（主用法）
python tools/gov-qa/poll.py --all

# 只轮询指定通道
python tools/gov-qa/poll.py --channel sd-yantai --channel rd-hn

# 只轮询某个层级 / 地区
python tools/gov-qa/poll.py --level province
python tools/gov-qa/poll.py --region 云南省

# 干跑（不落盘、不动水位，只报告会采到什么）
python tools/gov-qa/poll.py --all --dry-run

# 机器可读输出
python tools/gov-qa/poll.py --all --quiet

# 忽略水位，强制全量（水位损坏时的逃生口）
python tools/gov-qa/poll.py --all --full
```

---

## 退出码（**这是契约的核心**）

| 码 | 含义 | 调用方应如何反应 |
|---|---|---|
| `0` | 全部通道轮询成功（含「无新增」） | 正常 |
| `1` | **有通道失败**，但其他通道已完成 | 看报告，失败的通道下轮重试 |
| `2` | **致命错误**（如水位文件损坏且无法退化） | 人工介入 |
| `3` | **有人在跑**（锁冲突） | **不是失败**，等下一轮 |

> ⚠ 退出码 `3` 与 `1` 的区别很重要：锁冲突是**正常现象**（并行 agent），
> 不该被当成故障报警。

---

## 输出契约

### 人类可读（默认，中文）

```
轮询 331 个通道（水位类型：page 289 / since 38 / idset 4）
  ✅ sd-yantai       +12 条（水位 page 12 → 14）
  ✅ rd-hn           +0 条（无新增）
  ⚠️ nx-igi          跳过（锁冲突）
  ❌ nat-mot         失败：连接超时（连续失败 3 次）
...
汇总：成功 328 / 跳过 2 / 失败 1 ｜ 新增 1,847 条 ｜ 用时 6m12s
```

### 机器可读（`--quiet`，**纯 ASCII**）

```
POLLED=331
OK=328
SKIPPED=2
FAILED=1
ADDED=1847
ELAPSED=372
CHANNEL=sd-yantai ADDED=12 WATERMARK=14
CHANNEL=rd-hn ADDED=0 WATERMARK=3
...
```

---

## 行为契约（**必须保证的性质**）

| # | 性质 | 如何验证 |
|---|---|---|
| 1 | **幂等** | 连续两次 `--all`，第二次 `ADDED=0`，且全库 id 集合不变（SC-002） |
| 2 | **水位只在成功后前移** | 制造一次失败，检查 `watermarks.json` 的 `value` 未变（FR-003） |
| 3 | **中断可续** | 采集途中 kill，重跑后 `ADDED` 只含未采部分，无重复（SC-003） |
| 4 | **水位损坏可退化** | 删掉/写坏 `watermarks.json`，跑 `--all` 不报错，退化为全量（FR-006） |
| 5 | **故障隔离** | 单通道失败不阻塞其他通道（SC-012） |
| 6 | **并发安全** | 两个进程同时 `--all`，其中一个返回 `3`，另一个正常完成（R7） |

---

## 前置条件

- `tools/gov-qa/state/watermarks.json` 可写（不存在则视为全库无水位）
- 网络可达（失败按通道隔离，不中断整轮）
- **不在 `--full` 模式下要求水位**（该模式就是为绕过水位设计的）

## 副作用

- 追加写 `tools/gov-qa/data/*.jsonl`（**边采边落盘**，R3）
- 更新 `tools/gov-qa/state/watermarks.json`
- 写锁文件 `tools/gov-qa/state/.poll.lock`（结束时删除）
- **不删任何数据**
- **不改动 `data/` 里已存在的行**

## 明确未做

- ❌ 不做定时调度（那是 `automation` 的职责，不是本命令的）
- ❌ 不做数据清洗（那是 `dedup-data.py` / `label-classify.py` 的职责）
- ❌ 不做新口径过滤（口径是独立一层，本命令只负责「取增量」）
