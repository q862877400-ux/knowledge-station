# 阶段六增补 · 万级标准库批量导入设计（FRB v1.1 增补）

> 业务量：~35,000 个标准 PDF，100+GB。现有单文件入库管线（run_full_ingest）直推全量不可行：
> 扫描版单份可达分钟级 × 35k = 数周连续运转。核心决策：**目录先行、内容异步、分层巡检**。

## 1. 三阶段导入法

```
第一遍·快扫建目录（小时级达可用）
  PyMuPDF 仅提取文本层首页 → 正则抽 standard_no/standard_name/年代号
  file_hash(R43 防重) + doc_meta 骨架行（legal_status='effective' 待核, quality_grade='C' 待解析标记）
  失败件移入 quarantine/ 隔离区并记原因，不阻塞批次
第二遍·后台全量解析（逐夜滚动）
  从待解析队列按优先级取件走完整 run_full_ingest（条款切分/FTS/向量/三型分型规则版，零 LLM 外发）
第三遍·首检入列
  解析完成的标准自动进巡检 tier-0 队列（首次变更核查）
```

## 2. 编排与数值约束（键值对）

| 键 | 默认 | 说明 |
|---|---|---|
| bulk.batch_size | 200 | 一批文件数；批间落 checkpoint |
| bulk.scan_concurrency | 2 | 快扫并发（与巡检同级，防 IO 打满） |
| bulk.parse_daily_budget | 2000 | 第二遍每日解析配额（可夜间加速） |
| bulk.priority_tiers | watch > manual > new > rest | 手动置顶 > 特别关注(watch_list) > 新入库 > 其余 |
| bulk.snapshot_every_batches | 5 | 每 5 批自动 VACUUM INTO 快照 |
| bulk.quarantine_dir | <data>/quarantine/ | 损坏/无法识别文件隔离区 |

- 断点续跑：checkpoint 记录已处理 file_hash 集合（复用 inspector 的批次状态机模式 pending→running/paused/done/failed）
- 资源闸：启动前磁盘剩余空间 ≥ 数据体积 ×1.2 否则拒绝并提示；DB 体积超阈值告警

## 3. 巡检调度同步升级（万级库适配）

| 键 | 默认 | 说明 |
|---|---|---|
| inspect.tier0 | watch_list ∪ 新入库未首检 | 高频层 |
| inspect.daily_full_sweep_budget | 500 | 全库滚动巡检每日预算：35k ÷ 500 ≈ 70 天一轮 |
| inspect.concurrency | 2 | 沿用 |

三色报告按 tier 分列；tier-0 结果即时推送，tier-1 只入报告。

## 4. 落点与契约增量

- 新组件 `src/core/ingestion/bulk.py`（编排器）+ API `/api/v1/ingest/bulk`（POST 启动/暂停/进度 GET）+ 「更新」面板新增「批量导入」页签
- 新表 `bulk_import_batch`（batch_id ULID bul_，status/checkpoint_json/counts/quarantine_count）→ 追加契约 delta
- 快扫产生的骨架行 `quality_grade='C'` + `content_type='pending_parse'` 标记，前端列表可见"已收录·待解析"

## 5. 与并行会话/本体的一致性

- 复用 R43 file_hash 防重、write_queue、backup.py 快照滚动（保留 7 份策略对 35k 库改为按批触发）
- 零外发红线回归：全流程本地解析，不调 LLM（D1 允许云但额度克制原则下默认关）
