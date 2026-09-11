# 阶段三 · 架构蓝图与接口契约（更新模块）

> 依据：FRB-UPDATE-001 ｜ 原则：与本体规范统一——ULID 前缀、legal_status 枚举、write_queue 单写者、event_log 审计、SSE 冻结不碰

## 1. 模块拓扑（新增代码全部收敛于增量文件）

```
src/core/update/                  # 新包，零侵入现有模块
  __init__.py
  channels/                       # 渠道适配器（可插拔，F-02/F-11/F-12）
    base.py                       #   ChannelAdapter 抽象：probe(standard_no) -> ChannelResult
    official_gb.py                #   国家标准全文公开系统（验证码→半自动降级）
    web_fallback.py               #   网络逐号补漏搜索
    govcn_announce.py             #   gov.cn 公告检索 + PDF 存档
    laws_db.py                    #   国家法律法规数据库（F-22）
  inspector.py                    # 巡检编排：批次状态机 pending→running→paused/done/failed；断点续扫；并发=2
  change_repo.py                  # update_check_batch / update_change_event 读写（走 write_queue 写路径）
  report.py                       # 更新检查报告（界面 JSON + Word 导出，复用 report_export 模板机制）
  discover.py                     # 找标：口语→CCS 分类映射 + 追问 v2 + 结果卡片数据
  data_package.py                 # 全量导出/导入 + 简报计数（VACUUM INTO 扩展）
  scheduler.py                    # 定时巡检（复用 watcher 的轮询线程模式，app_config 存周期）
src/renderer/
  UpdatePanel.tsx                 # 「更新」入口主面板（三色列表/报告/订阅开关）
  TaskCard.tsx                    # 右下角任务小卡片（进度轮询 1s）
  DiscoverDialog.tsx              # 找标对话（追问交互复用问答气泡样式）
tests/
  test_update_inspector.py        # 编排/断点/重试
  test_update_channels.py         # 渠道适配器契约（mock 响应）
  test_update_discover.py         # 分类映射/追问深度 2~3
  test_update_data_package.py     # 导出导入简报一致性
  test_contract.py                # ⬅ 先改这里再动 schema（红线流程）
```

## 2. 数据契约（schema 增量，仅 2 张新表；改动前先改 contract.md + test_contract.py）

```sql
-- 29. 更新巡检批次表
CREATE TABLE IF NOT EXISTS update_check_batch (
    batch_id TEXT PRIMARY KEY,              -- ULID 前缀 upd_
    trigger_type TEXT CHECK(trigger_type IN ('manual','scheduled')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','running','paused','done','failed')),
    total INTEGER DEFAULT 0, checked INTEGER DEFAULT 0,
    red_count INTEGER DEFAULT 0, yellow_count INTEGER DEFAULT 0,
    green_count INTEGER DEFAULT 0, gray_count INTEGER DEFAULT 0,  -- gray=查无此号
    started_at TEXT, finished_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
-- 30. 标准变更事件表
CREATE TABLE IF NOT EXISTS update_change_event (
    change_id TEXT PRIMARY KEY,             -- ULID 前缀 chg_
    batch_id TEXT NOT NULL,
    doc_id TEXT,                            -- 可空：公告命中但库内无此文档
    standard_no TEXT NOT NULL,
    standard_name TEXT,
    change_type TEXT NOT NULL CHECK(change_type IN ('new_version','superseded','withdrawn','not_found','no_change')),
    current_legal_status TEXT CHECK(current_legal_status IS NULL OR current_legal_status IN ('effective','upcoming','superseded','withdrawn')),
    latest_info_json TEXT,                  -- 官方返回 {version,effective_date,url,...}
    source_channel TEXT NOT NULL,           -- official_gb | web | govcn | laws_db | manual
    evidence_url TEXT,
    archived_pdf_path TEXT,                 -- F-03 公告 PDF 存档
    user_ack INTEGER DEFAULT 0,
    detected_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(batch_id) REFERENCES update_check_batch(batch_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_change_batch ON update_change_event(batch_id, change_type);
CREATE INDEX IF NOT EXISTS idx_change_doc ON update_change_event(doc_id);
```

**零 DDL 变更的复用**：`doc_meta.doc_type` 无 CHECK 约束 → `'announcement'` 直接可用；`watch_list` 表已存在 → F-14 特别关注直接用；调度周期/领域订阅存 `app_config`（key: `update.schedule_days`=7 / `update.domain_subscriptions`=JSON）；巡检写路径走 `write_queue` operation_type=`'update_check'`；审计走 `event_log` event_type=`'update/change_detected'`。

## 3. API 契约（新增端点，包裹格式/鉴权与全站一致）

| 方法 | 端点 | 说明 |
|---|---|---|
| POST | `/api/v1/update/check` | 启动巡检批次 `{trigger:"manual"}` → `{batch_id}`；后台执行 |
| GET | `/api/v1/update/batch/{batch_id}` | 进度+统计（前端小卡片 1s 轮询，不走 SSE） |
| POST | `/api/v1/update/batch/{batch_id}/pause` · `/resume` | 断点控制 |
| GET | `/api/v1/update/batches?limit=` | 历史批次 |
| GET | `/api/v1/update/changes?batch_id&change_type` | 变更明细（三色列表数据源） |
| POST | `/api/v1/update/changes/{change_id}/ack` | 用户确认 |
| POST | `/api/v1/update/changes/{change_id}/manual` | 手动维护状态 `{legal_status,note}` |
| POST | `/api/v1/update/report/{batch_id}` | 生成 Word 报告 → exports 目录 |
| POST | `/api/v1/discover/classify` | `{description}` → `{questions[]|categories}`（追问协议对齐 clarify） |
| POST | `/api/v1/discover/search` | `{category_path,drill_level≤3}` → 结果卡片列表 |
| GET | `/api/v1/discover/watchlist` · POST 加入/移除 | 待下载清单 |
| POST | `/api/v1/data/package/export` · `/import` | 全量数据包 + 简报 `{docs,annotations,bookmarks,...}` |

**SSE 冻结不动**：C5 问答警示走既有 `evidence.time_warnings[]`（追加 warning 对象，字段向后兼容），零事件增删。

## 4. 复杂度标注（供动态调度，1~10）

| 模块 | 分 | 理由 |
|---|---|---|
| channels/official_gb.py | **8 → 贵AI** | 反爬/验证码半自动降级，现实不确定性最高 |
| inspector.py | **7 → 贵AI** | 并发+断点+暂停续跑状态机 |
| discover.py | **7 → 贵AI** | CCS 本体映射 + 追问 v2 接线 |
| data_package.py | 6 | VACUUM INTO 已有，难点在简报计数完整性 |
| govcn_announce.py / laws_db.py / web_fallback.py | 5 | 常规适配器 |
| report.py / scheduler.py / change_repo.py | 4 | 组合现成件 |
| 前端 UpdatePanel/TaskCard/DiscoverDialog | 5~6 | 复用样式体系 |

## 5. 并行冲突规避

本模块新增文件如上；**允许触碰的共享文件白名单**（最小化）：`schema.sql`(+2表)、`contract.md`/`test_contract.py`（先于实现）、`sqlite_db.py`（load_vec 不变仅注册）、`server.py`（挂路由）、`App.tsx`（顶部按钮+路由挂载点，≤10 行）、`styles.css`（追加 token 类）。其余一概不碰，规避并行会话冲突。

## 6. ERD 增量

```
update_check_batch 1──N update_change_event N──0..1 doc_meta
                              │
                              └──── archived_pdf_path ──► doc_meta(doc_type='announcement') 新文档
watch_list (既有) ──► F-14 特别关注提醒数据源
app_config: update.schedule_days / update.domain_subscriptions
```
