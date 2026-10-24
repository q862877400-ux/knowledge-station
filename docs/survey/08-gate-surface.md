# 门禁面

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、总账

| 项 | 数 |
|---|---:|
| `Add-Step` 步 | **15** |
| 冒烟套（`smoke-all.mjs` 的 `SUITES`） | **44** |
| 被调用的脚本字面量 | 29 |

> `steps` 含 `selftest` 分支（门禁自测用的假步），所以并不全是真实验证步。**这是解析结果，不是设计意图** —— 每一步具体跑什么要读 run-gates.ps1 原文。

## 二、步名（按 `run-gates.ps1` 里的出现顺序）

1. `selftest（必失败）`
2. `selftest（命令不存在）`
3. `pssa-guard-selftest（门禁自测）`
4. `tsc（客户端类型）`
5. `mypy（引擎类型）`
6. `verify:commands`
7. `pssa-guard（命令层）`
8. `smoke（全链）`
9. `pytest（引擎用例）`
10. `引擎门禁（uvicorn）`
11. `verify-tools-real（真 ToolRuntime）`
12. `真宿主 e2e（临时 profile）`
13. `gov-qa 质量闸门`
14. `gov-qa 幂等验证`
15. `gov-qa 通道台账最新`

## 三、冒烟套清单

- `scripts/smoke-anchor-mark.mjs`
- `scripts/smoke-bbox-degenerate.mjs`
- `scripts/smoke-build-purity.mjs`
- `scripts/smoke-cancel.mjs`
- `scripts/smoke-catalog-ui.mjs`
- `scripts/smoke-channels-ai.mjs`
- `scripts/smoke-channels-routes.mjs`
- `scripts/smoke-chatmode.mjs`
- `scripts/smoke-class-summary.mjs`
- `scripts/smoke-client-entry.mjs`
- `scripts/smoke-collect-tool.mjs`
- `scripts/smoke-collect-ui.mjs`
- `scripts/smoke-compliance-sentry.mjs`
- `scripts/smoke-docimage.mjs`
- `scripts/smoke-draft-ui.mjs`
- `scripts/smoke-effect-tool.mjs`
- `scripts/smoke-engine-guard.mjs`
- `scripts/smoke-evidence-prefs.mjs`
- `scripts/smoke-evidence-warn.mjs`
- `scripts/smoke-icon-system.mjs`
- `scripts/smoke-ingest.mjs`
- `scripts/smoke-kb-cols.mjs`
- `scripts/smoke-kb-pad-pixels.mjs`
- `scripts/smoke-kb-page-render.mjs`
- `scripts/smoke-lifecycle.mjs`
- `scripts/smoke-materials-routes.mjs`
- `scripts/smoke-materials-rows.mjs`
- `scripts/smoke-materials-tool.mjs`
- `scripts/smoke-pdf-fit.mjs`
- `scripts/smoke-pdf-panel.mjs`
- `scripts/smoke-report-routes.mjs`
- `scripts/smoke-report-ui.mjs`
- `scripts/smoke-sanitize.mjs`
- `scripts/smoke-settings-guard.mjs`
- `scripts/smoke-settings.mjs`
- `scripts/smoke-tool-catalog.mjs`
- `scripts/smoke-tool-concurrency.mjs`
- `scripts/smoke-tool-contract.mjs`
- `scripts/smoke-trim.mjs`
- `scripts/smoke-turn-routes.mjs`
- `scripts/smoke-turn-tab.mjs`
- `scripts/smoke-ui-scale.mjs`
- `scripts/smoke-wire-contract.mjs`
- `scripts/ui-badge-pixels.mjs`

## 四、门禁里被点到名字的脚本

- `base.py`
- `prev.py`
- `scripts/gates-tracked-total.py`
- `scripts/verify-engine-uvicorn.py`
- `scripts\gates-tracked-total.py`
- `src/core/config.py`
- `test_compliance.py`
- `test_gate_baseline_whitelist.py`
- `test_phase4.py`
- `test_retrieval.py`
- `tests/conftest.py`
- `tests/test_compliance.py`
- `tests/test_gate_baseline_whitelist.py`
- `tests/test_golden_gate.py`
- `tests/test_jev_cn_baseline.py`
- `tests/test_poll.py`
- `tools/gov-qa/recon/gate-quality.py`
- `tools/gov-qa/recon/gen-channel-table.py`
- `tools/gov-qa/recon/verify-idempotent.py`
- `gate-lock.mjs`
- `plugin/scripts/e2e-install-compose.mjs`
- `plugin/scripts/smoke-all.mjs`
- `plugin/scripts/verify-tools-real.mjs`
- `scripts/smoke-all.mjs`
- `run-gates.ps1`
- `scripts/pssa-guard.ps1`
- `scripts/run-gates.ps1`
- `scripts\pssa-guard-selftest.ps1`
- `scripts\pssa-guard.ps1`