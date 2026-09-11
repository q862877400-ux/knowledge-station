# 阶段七 · 集成验证异常台账 & 阶段八 DCP

## 异常台账（仅事实记录）

- **ANOM-001**：巡检批次 `bul_01M0SGMKA5522MTQZ3H5MPVZ67` 终态 done，`checked=19/total=19`，
  但 red/yellow/green/gray 全为 0；`GET /changes?batch_id` 返回 0 条。违反四色恒等式
  （red+yellow+green+gray == total）。冒烟时间 2026-08-24 17:12，引擎端口 13679。

### 其余冒烟项全部通过
401 鉴权 ✓ / classify 过泛追问 1 问 ✓ / classify 消防→C/C80 conf 0.95 ✓ / 批次启动 ✓ / 报告 docx 导出存在 ✓

---

## DCP 故障诊断上下文包（DCP-UPDATE-001）

```json
{
  "baseline": {
    "kind": "content-snapshot",
    "pytest": "292 passed + 2 skipped",
    "note": "无 git 环境，按业主决议以内容快照哈希为基线；涉及文件清单见 fix_scope"
  },
  "repro": {
    "endpoint": "POST /api/v1/update/check {trigger:'manual'}",
    "poll": "GET /api/v1/update/batch/{batch_id} 直至终态",
    "observe": "status=done, checked==total==19, 四色计数均 0",
    "second": "GET /api/v1/update/changes?batch_id={id} -> items=0"
  },
  "expected_vs_actual": {
    "expected": "red+yellow+green+gray == total(19)；每个 standard_no 恰归一桶（04a §0 四色恒等式）",
    "actual": "0+0+0+0 != 19",
    "deviation_pct": 100
  },
  "runtime_fingerprint": {
    "python": ".venv 3.12",
    "engine_port": 13679,
    "modules": ["src/core/update/inspector.py", "change_repo.py", "channels/*"]
  },
  "log_window": "var/engine.log 尾部批次 TRACE 段；渠道探测逐条日志在案"
}
```

## 8.5 DCP 仲裁门禁

| 检查项 | 结果 |
|---|---|
| 有效基线指纹 | ✅ pytest 数字基线（无 git 环境按决议替代） |
| 完整端点与载荷 | ✅ 复现步骤含端点+body |
| 同时含 Expected 与 Actual | ✅ 含偏差量化 |
| 版本锁定 | ✅ 运行时指纹+模块清单 |
| 日志窗口 | ✅ engine.log TRACE 段可查 |

**[DCP_VALID]** → 转阶段九根因诊断与修复工单。

## 修复范围预估（fix_scope）
inspector.py 结果聚合/落库路径（green/no_change 未计数嫌疑最大）；回归用例补恒等式断言（INS-A-01 已有，需真实路径复验）。
