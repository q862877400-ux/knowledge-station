# 04b · 更新模块·平台层四维测试集（@Smoke / @Negative / @Chaos / @Idempotent）

> 依据：FRB-UPDATE-001（pipeline/01-frb.md）＋阶段三契约（pipeline/02-architecture-contract.md）。落点：`tests/test_update_platform.py`（注册 marker：smoke/negative/chaos/idempotent）；schema 用例走红线流程先进 `tests/test_contract.py`。
> 全站响应统一包裹：成功 `{"code":200,"status":"success","data":...}`，失败同构（code≠200）；除 `GET /api/v1/health` 外一律要求 `Authorization: Bearer <token>`。pytest 基线 173 passed＋2 skipped 只涨不跌。

## 0. 约定
- Base=`http://127.0.0.1:8000`；夹具：`fresh_db`(内存库+全量 schema.sql)、`auth_headers`、`mock_channels`、`golden_sse`(冻结事件序快照 `tests/golden/sse_chat_events.json`)。
- 用例行格式：ID | 维度 | 前置 | 步骤（方法+路径+body 样例内联）| 期望 | FRB编号。

## 1. @Smoke（核心路径冒烟）

|ID|维度|前置|步骤|期望|FRB编号|
|---|---|---|---|---|---|
|UP-S-01|@Smoke|服务已启动、零凭据|`GET /api/v1/health`（全站唯一免 Bearer 端点）|200 且 body 为 `{"code":200,"status":"success","data":{...}}` 形态|FRB§4|
|UP-S-02|@Smoke|CCS 本体与样本标准已入库|`POST /api/v1/discover/classify` body `{"description":"我要安全的国标"}`|`data.questions` 为单轮 1~3 问；随用户应答迭代，追问深度收敛于 2~3 级后给出 categories|F-15|
|UP-S-03|@Smoke|UP-S-02 已产出 category_path|`POST /api/v1/discover/search` body `{"category_path":"安全/劳动防护","drill_level":2}`|`data.cards[]` 含 standard_no/名称/legal_status/强标标识/下载渠道定位，包裹合规|F-15,F-17|
|UP-S-04|@Smoke|≥3 个已知状态样本（现行/有新版/已废止）在库|`POST /api/v1/update/check` body `{"trigger":"manual"}` 得 `data.batch_id` → 循环 `GET /api/v1/update/batch/{batch_id}` 至 status=done|red/yellow/green 三色计数判定全对，gray(查无此号)单独计|F-01,F-04|
|UP-S-05|@Smoke|UP-S-04 批次 done|`POST /api/v1/update/report/{batch_id}`（无 body）|`data.file_path` 指向 exports/*.docx，文件>0KB 且含月度趋势章节|F-05|
|UP-S-06|@Smoke|docs/annotations/bookmarks 各有样本|`POST /api/v1/data/package/export` 读 `data.brief` → 清空业务表 → `POST /api/v1/data/package/import`（同包 multipart）|导入简报 docs/annotations/bookmarks 三项与导出 brief 逐项相等|F-26|
|UP-S-07|@Smoke|golden_sse 基线已固化|`POST /api/v1/chat/completions` body `{"messages":[{"role":"user","content":"GB/T 19001 现行版本"}]}`（SSE 流式）|事件类型序列与冻结基线逐位一致（meta→evidence→delta*→done），零增删零换序|F-23|
|UP-S-08|@Smoke|库内置已废止依据样本|同 UP-S-07 输入并命中废止标准|`evidence.time_warnings[]` 以追加方式携带 warning 对象；既有字段名/语义/位置零变更（向后兼容）|F-23|

## 2. @Negative（非法输入与越权）

|ID|维度|前置|步骤|期望|FRB编号|
|---|---|---|---|---|---|
|UP-N-01|@Negative|服务已启动|不带 Authorization 依次调 `POST /api/v1/update/check` `{}`、`GET /api/v1/update/batches?limit=5`、`GET /api/v1/discover/watchlist`、`POST /api/v1/data/package/export`|一律 401 同构包裹；无批次行、无包文件等副作用残留|FRB§3|
|UP-N-02|@Negative|有效 Bearer|`POST /api/v1/discover/search` body `{"category_path":"M/机械","drill_level":4}`|400 校验拒绝，错误信息明示 drill_level≤3，不触外网|F-15|
|UP-N-03|@Negative|存在一条 update_change_event 样本|`POST /api/v1/update/changes/{change_id}/manual` body `{"legal_status":"作废","note":"人工标注"}`|CHECK(current_legal_status) 拒绝→4xx 包裹；该行原值不变，event_log 无新审计|F-12|
|UP-N-04|@Negative|预造损坏包（截断 zip／篡改首块字节）|`POST /api/v1/data/package/import` 上传损坏包|完整性校验拒绝；导入前后 COUNT(docs)/COUNT(annotations)/COUNT(bookmarks) 三值全等，无临时表/半写行残留|F-26|
|UP-N-05|@Negative|有效 Bearer|`POST /api/v1/update/check` body `{"trigger":"auto"}`|CHECK(trigger_type∈manual,scheduled) 拒绝→400，update_check_batch 行数不变|契约§2|
|UP-N-06|@Negative|write_queue 直注通道可用|经 change_repo 注入 `change_type="merged"` 写操作|IntegrityError(CHECK change_type)→4xx 包裹，update_change_event 行数不变|契约§2|

## 3. @Chaos（故障注入与并发）

|ID|维度|前置|步骤|期望|FRB编号|
|---|---|---|---|---|---|
|UP-C-01|@Chaos|mock official_gb：前 3 次 30s 超时，第 4 次回验证码页|`POST /api/v1/update/check` body `{"trigger":"manual"}` 后观测批次与事件表|重试恰 3 次后降级：验证码转半自动提示、查无此号入 gray_count，批次终态 done/failed 不悬挂|F-10,F-11,F-12|
|UP-C-02|@Chaos|export 写盘中途注入磁盘满异常|触发 `POST /api/v1/data/package/export` 后故障注入|exports 目录无会被误用的半成品；清理后重跑成功且 brief 计数正确|F-26|
|UP-C-03|@Chaos|三请求同时到达|并发 `POST /api/v1/data/package/export` ＋ `/import` ＋ `POST /api/v1/update/check`|write_queue 单写者串行化，无 SQLITE_BUSY 外泄，均以合规包裹响应收尾|F-01,F-26|
|UP-C-04|@Chaos|批次 running 中|交错 `POST /api/v1/update/batch/{id}/pause`、`/resume` ×10，并 1s 轮询 `GET /api/v1/update/batch/{id}`|终态∈{paused,done,failed}，checked 单调不减，轮询无 5xx|F-10|

## 4. @Idempotent（重复执行一致性）

|ID|维度|前置|步骤|期望|FRB编号|
|---|---|---|---|---|---|
|UP-I-01|@Idempotent|存在 user_ack=0 的 change|`POST /api/v1/update/changes/{id}/ack` 连续 2 次|两次均 code=200；user_ack 恒=1；event_log 审计仅 1 条|契约§2|
|UP-I-02|@Idempotent|UP-S-06 导出包已成功导入过|再次 `POST /api/v1/data/package/import` 同包|幂等：三项计数不翻倍，二次简报与首次一致或显式 skipped 报告|F-26|
|UP-I-03|@Idempotent|同一 done 批次|`POST /api/v1/update/report/{batch_id}` 连续 2 次|两份 .docx 内容哈希一致（允许同名覆盖）；趋势数据无重复行|F-05|
|UP-I-04|@Idempotent|已建 29/30 两张新表的库|重复执行 schema.sql 全量脚本|CREATE TABLE IF NOT EXISTS 生效：零报错，PRAGMA table_info 无变化|契约§2|
|UP-I-05|@Idempotent|固定随机种子+同库快照|同一输入两次 `POST /api/v1/chat/completions`（SSE）|两次事件类型序列完全相同；time_warnings 输出确定|F-23|

## 5. Schema 契约用例（红线流程：先改本节再动 schema.sql / src/core/update/）

追加到 `tests/test_contract.py`（增量样式，紧接既有用例尾；基线只增不减）：

```python
import sqlite3, pytest

def test_contract_29_update_check_batch_ddl_check(fresh_db):
    cols = {r[1] for r in fresh_db.execute("PRAGMA table_info(update_check_batch)")}
    assert {"batch_id", "trigger_type", "status", "total", "checked",
            "red_count", "yellow_count", "green_count", "gray_count",
            "started_at", "finished_at", "created_at"} <= cols
    for bad in [("upd_01T", "cron", "pending"),     # trigger_type 非法
                ("upd_01T", "manual", "queued")]:   # status 非法
        with pytest.raises(sqlite3.IntegrityError):
            fresh_db.execute(
                "INSERT INTO update_check_batch(batch_id,trigger_type,status) VALUES(?,?,?)", bad)

def test_contract_30_update_change_event_ddl_check(fresh_db):
    fresh_db.execute("INSERT INTO update_check_batch(batch_id,trigger_type,status)"
                     " VALUES('upd_OK','manual','done')")
    ddl = fresh_db.execute("SELECT sql FROM sqlite_master WHERE type='table'"
                           " AND name='update_change_event'").fetchone()[0]
    assert ddl.count("CHECK") >= 3 and "ON DELETE CASCADE" in ddl   # FK 级联随批删
    fresh_db.execute(
        "INSERT INTO update_change_event(change_id,batch_id,standard_no,"
        "change_type,current_legal_status,source_channel) "
        "VALUES('chg_T1','upd_OK','GB/T 1.1','new_version','effective','manual')")  # 合法可写
    for bad_sql in (
        "UPDATE update_change_event SET change_type='merged' WHERE change_id='chg_T1'",
        "UPDATE update_change_event SET current_legal_status='作废' WHERE change_id='chg_T1'",
        "UPDATE update_change_event SET source_channel='' WHERE change_id='chg_T1'"):
        with pytest.raises(sqlite3.IntegrityError):
            fresh_db.execute(bad_sql)
```

## 6. 运行分层与门禁对照

- 分层跑：`pytest -m smoke` → `-m negative` → `-m chaos` → `-m idempotent`；全量绿＋tsc 0 错误方过阶段七门禁（FRB§4-4）。
- 覆盖对照：F-05→S-05/I-03；F-15→S-02,S-03/N-02；F-23→S-07,S-08/I-05；F-26→S-06,N-04,C-02,C-03,I-02；F-12→N-03,C-01；契约§2→N-05,N-06,I-01,I-04,§5；验收门禁3→S-06；门禁2→S-04。
