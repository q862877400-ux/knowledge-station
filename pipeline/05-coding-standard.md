# 阶段五 · 更新模块编码规约与可观测性标准

> 本规约作为开发子代理的 System Prompt 前缀注入；与本体既有规范冲突时，本体规范优先。

## 1. 结构化日志格式（引擎日志 var/engine.log 与模块内 logger）

```
[ISO-8601] [UPD] [TRACE=<batch_id>] [SPAN=<stage>] [LEVEL=INFO|WARN|ERROR] 消息 键值对...
示例：[2026-08-24T12:00:00+08:00] [UPD] [TRACE=01JZ...] [SPAN=channel.official_gb] [LEVEL=WARN] captcha_required standard_no="GB 30871-2022"
```

- TRACE 固定为 batch_id（批次级追踪）；SPAN ∈ {inspector, channel.*, discover, report, package}
- 渠道每次探测必落一条（含耗时 ms），供断点续扫与性能探针读取

## 2. 错误码空间（更新模块专用段；API 层沿用全站 {"code","status","error"} 字符串风格）

| 区间 | 含义 | 字符串码示例 |
|---|---|---|
| UPD-1xxx | 网络/渠道层 | UPD-1001 channel_timeout, UPD-1002 captcha_blocked, UPD-1003 rate_limited |
| UPD-2xxx | 业务层 | UPD-2001 batch_already_running, UPD-2002 change_not_found |
| UPD-3xxx | 校验层 | UPD-3001 illegal_legal_status, UPD-3002 drill_level_exceeded(>3), UPD-3003 bad_package |
| UPD-5xxx | 系统内部 | UPD-5001 scheduler_crash |

## 3. 不确定性熔断

- 遇指令歧义/缺失依赖/契约未定义场景 → 输出哨兵 `[NEED_HUMAN_INPUT]` + 一句原因，终止当前子任务，不得猜测续跑
- 落点映射：验证码半自动 = 批次 paused + `event_log(event_type='update/captcha_wait')` + 前端徽章，本质即本熔断的产品化形态

## 4. 硬约束（继承本体铁律，违规即驳回）

1. 写操作一律走 `write_queue`（operation_type='update_check'），禁止裸写
2. 新表 DDL 先改 contract.md + test_contract.py 再实现
3. SSE 事件顺序冻结：问答警示只准追加进 evidence.time_warnings[]
4. 标签/订阅永不改写条款原文；legal_status 变更必须留 event_log 审计
5. 测试隔离：完整 ULID、相对断言、close_thread_connection()
6. 前端样式只用 styles.css 既有 design-token，不散落硬编码色值
7. 中文 JSON 用 httpx/requests；API Key 不落代码库
8. 渠道适配器禁止真实联网的单元测试（mock 表驱动）

## 5. 提交门禁（阶段六每次交付）

- pytest 相关文件全绿 + 全量不低于基线；`npx tsc --noEmit` 0 错误
- 契约静态预检：新增端点的请求/响应字段与本文档 §2 架构契约逐一比对（字段名/类型/必填）
