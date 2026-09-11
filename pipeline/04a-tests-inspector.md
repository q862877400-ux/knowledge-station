# 更新模块 · 巡检引擎四维测试集（04a）

> 依据：FRB-UPDATE-001 v1.0 ＋ pipeline/02-architecture-contract.md（§1 inspector/channels、§2 schema、§3 API）
> 落点：`tests/test_update_inspector.py`＋`tests/test_update_channels.py`｜本文档只定义测试集，不改任何产品代码。

## 0. 全局约定（零联网）

- **Mock 表驱动**：三渠道适配器注入 `MockChannelTransport`，应答全部来自 fixtures `tests/fixtures/update_channels.json`，断网可跑。一行 mock = 一次渠道应答：
  `{"key","channel":"official_gb|web|govcn","seq":n,"respond":{"http":200,"body":{...}} | {"delay_s":31} | {"raise":"Timeout"} | {"captcha":true}}`
- 同一 key 的应答按 seq 依次弹出，耗尽后复用末条；时间用假时钟注入；DB 用内存 SQLite，write_queue 同步排空后再断言。
- **四色恒等式**（done 批次）：`red+yellow+green+gray = total`，每个 standard_no 恰归一桶。
- 用例格式（一行一条）：`ID | 维度 | 前置 | 步骤 | 期望 | FRB编号`。维度 ∈ {@Smoke,@Negative,@Chaos,@Idempotent}。

## 1. 巡检编排：并发=2 / 断点续扫 / 暂停恢复（inspector.py）

| ID | 维度 | 前置 | 步骤 | 期望 | FRB |
|---|---|---|---|---|---|
| INS-A-01 | @Smoke | 库内 5 个 standard_no，mock 全部 effective | POST `/update/check` → 轮询 batch | pending→running→done；checked=total=5，green=5 余 0 | F-01 |
| INS-A-02 | @Smoke | 10 个待查号，transport 记录活跃水位 | 启动批次并采样并发数 | 峰值并发恒=2，按清单序两两成组推进 | F-01 |
| INS-A-03 | @Smoke | 批次 running 中 | POST pause → GET 进度 → POST resume | paused→running；checked 单调不回退 | F-10 |
| INS-A-04 | @Idempotent | 跑到 3/10 时 pause，杀进程重启服务 | resume 续跑 | 自第 4 号续扫；前 3 号 update_change_event 无重复 chg_ 新增 | F-10 |
| INS-A-05 | @Negative | 某号 transport delay_s=31（>30s 超时） | 跑完整批 | 该号按重试=3 次后记 failed，不阻塞他号；单号 30s 上界生效 | F-01,F-10 |
| INS-A-06 | @Negative | 目标 batch_id 不存在 | POST `/batch/{id}/resume` | 404+明确错误码；零副作用写入 | §3 |
| INS-A-07 | @Chaos | 第 4 号连续异常，余号正常 | 完整跑批 | 终态必为 done/failed 且 finished_at 落库，无 running 挂死；event_log 含 `update/change_detected` 审计 | F-10 |
| INS-A-08 | @Chaos | running 中途注入一次 SQLite 异常 | 异常排除后续跑 | write_queue 重放不丢事件，批次可达 done | F-10 |
| INS-A-09 | @Idempotent | 批次已 done | 再发 check / pause / resume | 终态批次拒绝重启；重复 pause 幂等返回同状态 | §3 |

## 2. 渠道适配器降级链 official_gb→web→govcn（channels/*，表驱动）

| ID | 维度 | 前置 | 步骤 | 期望 | FRB |
|---|---|---|---|---|---|
| INS-B-01 | @Smoke | mock：official_gb 命中现行版 | 单号巡检 | 仅调 official_gb（web/govcn 零调用）；source_channel=official_gb | F-02 |
| INS-B-02 | @Smoke | official_gb http503 → web 命中新版 | 单号巡检 | 依序降级命中 web；source_channel=web，change_type=new_version | F-02 |
| INS-B-03 | @Smoke | official_gb 超时、web 空结果、govcn 命中公告 | 单号巡检 | source_channel=govcn；archived_pdf_path 非空并入库 doc_type='announcement' | F-02,F-03 |
| INS-B-04 | @Negative | 三渠道全 miss（空/404 组合） | 单号巡检 | change_type=not_found，gray+1；结果含「内置渠道无法查询」标记，manual 维护入口可用 | F-12 |
| INS-B-05 | @Negative | body 缺 version/effective_date，legal_status 为非法串 | 解析该应答 | 降级为告警事件不崩溃；warning 入 event_log，不写脏行 | §2 |
| INS-B-06 | @Chaos | official_gb 前 2 次 raise 第 3 次命中（预算内） | 单号巡检 | 不提前降级：仍由 official_gb 完成，source_channel=official_gb | F-02,F-10 |
| INS-B-07 | @Idempotent | mock 矩阵 ≥12 行渠道响应组合 | 参数化遍历全组合并重跑一轮 | 每组 (source_channel, change_type, 色) 唯一确定；两轮结果逐位一致 | F-02 |

## 3. 验证码半自动：批次 paused→用户过点→resume（official_gb）

| ID | 维度 | 前置 | 步骤 | 期望 | FRB |
|---|---|---|---|---|---|
| INS-C-01 | @Smoke | mock 应答 captcha=true | 单号巡检 | 批次转 paused；任务卡片提示「请过验证码后继续」；当前号挂起，不误记 gray/failed | F-11 |
| INS-C-02 | @Smoke | 因验证码 paused，模拟用户过点 | POST resume（mock 下次应答正常） | 同一 standard_no 重试 official_gb 成功，批次续跑至 done | F-11 |
| INS-C-03 | @Negative | paused 批次无人过点 | 等待一个调度周期 | 定时器不得自动 resume（必须人工确认）；批次维持 paused | F-08,F-11 |
| INS-C-04 | @Chaos | 连续 3 号均返回验证码 | 继续跑批 | 合并为单次暂停（一条提示聚合 3 号，不逐号刷屏）；resume 后逐号补查不漏 | F-11 |
| INS-C-05 | @Idempotent | 批次已 paused | 交错发送 pause×2、resume×2 | 状态机无非法迁移；resume 生效一次，扫描不重复执行 | F-10,F-11 |

## 4. 三色判定 ↔ legal_status 枚举映射（effective/upcoming/superseded/withdrawn）

映射基准（对齐 FRB F-04）：effective→🟢；upcoming→🟢（有新版未施行按现行对待，**不**触发对比）；superseded→🔴（在用已被替代）；withdrawn→🔴；change_type=new_version（有新版）→🟡；not_found（legal_status=NULL）→⚪gray。

| ID | 维度 | 前置 | 步骤 | 期望 | FRB |
|---|---|---|---|---|---|
| INS-D-01 | @Smoke | mock 返回 legal_status=effective | 判定该号 | green+1；current_legal_status='effective' 落库 | F-04,C9 |
| INS-D-02 | @Smoke | mock 返回 upcoming | 判定该号 | 按 🟢 现行对待；不触发废止对比流程 | F-04,F-06 |
| INS-D-03 | @Smoke | mock 返回 superseded | 判定该号 | red+1，change_type=superseded；受影响批注/审查清单数据可取 | F-04,F-07 |
| INS-D-04 | @Smoke | mock 返回 withdrawn | 判定该号 | red+1，change_type=withdrawn；引用该号的审查任务标「需重审」 | F-04,F-07 |
| INS-D-05 | @Smoke | 三渠道查无此号 | 判定该号 | gray+1；current_legal_status 保持 NULL；manual 状态维护生效 | F-12 |
| INS-D-06 | @Negative | mock 返回枚举外值 legal_status='draft' | 写入 update_change_event | CHECK 约束拒绝、事务回滚无脏行；该号转告警而非静默丢弃 | §2,C9 |
| INS-D-07 | @Idempotent | 同批判定结果已落库 | 以相同 mock 序列重放判定 | 事件按 (batch_id, standard_no) 幂等去重，四色计数不翻倍 | §2 |
| INS-D-08 | @Chaos | 20 号混合现行/有新版/已废止/查无随机序 | 整批判定 | 四色恒等式成立；≥3 个已知状态样本判定全部正确（验收演练口径） | F-04,§4 |

## 5. FRB 覆盖对照与门禁

- F-01→A-01/02/05｜F-02→B-01~07｜F-03→B-03｜F-04→D-01~08｜F-06→D-02｜F-07→D-03/04｜F-08→C-03｜F-10→A-03~09,C-05｜F-11→C-01~05｜F-12→B-04,D-05
- 门禁：本集全绿计入 pytest 基线（只涨不跌，现基线 173 passed+2 skipped）；全程零联网，CI 可离线复跑；@Chaos 用例经 mock 化后必须确定性通过，不允许 xfail 豁免。
- 边界说明：schema/契约红线（先改 contract.md＋test_contract.py）不在本集范围，由 test_contract.py 把关；本集仅覆盖 inspector 与 channels 层行为。
