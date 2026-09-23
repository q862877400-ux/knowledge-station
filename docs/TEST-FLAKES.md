# 测试 flake 清单（已知偶发/竞态型，非回归勿背锅）

> 批3 尾件 3/4（2026-09-22）。登记口径：**只有被独立复核复现过**的才进表；表内条目
> 不作为"本批回归"计罪，但**不许**用来掩盖真回归（同名失败要看机理：竞态签名 vs 语义变化）。

| 用例 | 症状 | 机理（已查证） | 处置 |
|---|---|---|---|
| `tests/test_filing_state_pipeline.py::test_bulk_endpoint_passes_force_and_reingest` | 422 UPD-2001 批次互撞，偶发 | `abort_batch` 与后台 `fast_scan` 状态写竞态；`sleep(0.2)` 补丁压不住（复核 verify-ui-s2fix 3/3 复现；机理与修法见 var/tmp/verify-ui-s2fix-report.md §八） | ✅ **已修（`4de96f8`）**：引擎条件状态写根治复活 + 测试换轮询到终态；复活判据变异自证 |
| `tests/test_filing_state_pipeline.py::test_zero_clause_ingest_is_failed_and_still_visible_in_inbox` | 全量串行链里偶发 1 次红（2026-09-22 收工门禁），单跑即过 | 同上表**同文件同竞态族**（ingest/fast_scan 写竞的姊妹症状）；单跑复现 1/1 过 ⇒ 按 flake 纪律登记 | ⚠ **更正（复核 verify-freeze-yi 打回，2026-09-22）**：原划「已修（随同族条件状态写根治）」**依据站不住**——条件写修的是 `bulk_import_batch.status`，而本用例断的是 `doc_filing_state`（`set_filing_state` 无条件 upsert、`run_full_ingest` 不走 `_save_ckpt`），**修的不是它断的那张表**，且"本就是轮询式同步"与代码不符（同步直调、无轮询无 sleep）。降级为「**随①缓解，未独立证**」；错话原文保留于此。 |
| `plugin/scripts/smoke-chatmode.mjs`（历史） | 曾 2 次 172/173 | **已更正**：并发假红说无证据（AGENTS.md 门禁节留痕）；实为写盘失败型一次 + 串行链一次 | 已结案，留档防误引 |

## 处置纪律

1. 新偶发先跑 3 次单跑 + 1 次串行链——**单跑可复现 = 不是 flake**，按真缺陷查。
2. 表内条目失败时：重跑一次并留两次日志；仍红按真缺陷处理。
3. 修掉一条就从表里划掉（保留行做历史，标「已修 <提交>」）。
