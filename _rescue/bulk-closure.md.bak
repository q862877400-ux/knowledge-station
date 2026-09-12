# 批量导入轮 · 闭环报告（pipeline/11 落地）

```
[PIPELINE_STATUS: SUCCESS]
round: 万级批量导入编排器（35000 PDF / 100+GB 场景）
date: 2026-08-24
baseline: 322+3 → 331+3
```

## 交付
- `src/core/ingestion/bulk.py`：create_bulk_batch / fast_scan（首页抽号+防重+隔离区+骨架行）/ parse_loop（日预算+每5件快照+幂等）/ pause / resume
- API：POST /ingest/bulk（daemon 快扫）、GET /ingest/bulk/{id}（进度）、POST resume（解析）
- 前端：UpdatePanel「📥 批量导入」卡片（目录输入→启动→进度行→恢复解析）
- 测试：test_bulk_import.py 5 用例（骨架/防重隔离/运行拒绝/预算暂停幂等/坏目录）+ API 鉴权 3 条

## 冒烟证据（真实引擎）
```
启动 → 快扫 paused scanned=3 total=3 errors=0 → resume(budget=0)
     → paused pause=daily_budget_reached parsed=0   ✅ 预算门禁生效
```

## 修复的两个真 bug（冒烟暴露）
1. `int(body.get("daily_budget") or DEFAULT)`：0 被 Python falsy 吞成 2000 → 预算暂停失效（改 None 判定）
2. 快扫后 total 未回写（改 _save_ckpt 支持 total 参数）
3. 测试隔离：骨架计数断言误查全表（改按 pending 标记过滤）

## 挂起（下一轮候选）
- laws 法规渠道真机版（flk 已探明 API，见 var/tmp 取证）
- 巡检历史假绿批次订正（bul_...MVZ67/VYAKHKT）
- `_NAME_RE` 名称提取增强（首页无名称时从全文回退）
- 批量导入的 GUI 大目录扫描并发（当前单线程快扫，万级可加 scan_concurrency）
