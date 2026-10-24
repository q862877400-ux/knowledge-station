# 配置面（环境变量 + 配置键）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

环境变量 = `os.environ.get/getenv/env[...]` 与 `process.env.X` 的字面量；配置键 = `_read_json_key` / `_write_json_key` / `get_config` / `set_config` 的实参，**并解析模块级常量**（本仓大量写成 `SOURCES_KEY = "announce.sources"` 再传常量）。**拼接出来的键名看不到**。`used_by` 只列前 12 个引用点。

## 二、总账

| 项 | 数 |
|---|---:|
| 环境变量 | **47** |
| 代码里的配置键 | 11 |
| 种子库里的配置键 | 7 |
| 两者并集 | **13** |

`app_config` 表有 `is_encrypted` 列（实测 7 行全是 0）。这里只记键名与值的字节长度，**不记值本身**（有的键存的是源清单/状态，抄进来会让人误以为那是当前配置）。

## 三、环境变量

| 变量 | 引用文件数 | 引用点（前 12） |
|---|---:|---|
| `APPDATA` | 5 | `scripts/apply-folder-filing.py`、`scripts/check-fixture-leak.py`、`scripts/make_handoff_zip.py`、`scripts/loop2/oracle_score.py` …共 5 |
| `B1_CAP_S` | 1 | `scripts/verify-seeds/b1-reingest-e2e.py` |
| `DEEPSEEK_API_KEY` | 1 | `tests/test_credentials_namespace.py` |
| `HTTPS_PROXY` | 1 | `scripts/channel-anchor-measure.py` |
| `KS_BACKUP_DIR` | 1 | `src/core/storage/backup.py` |
| `KS_CCS_SEED_FILE` | 1 | `scripts/std_bulk_import.py` |
| `KS_CHATMODE_DIR` | 1 | `plugin/src/chatmode.js` |
| `KS_DATA_DIR` | 13 | `src/core/config.py`、`scripts/apply-folder-filing.py`、`scripts/audit-async-endpoints.py`、`scripts/measure-endpoint-blocking.py` …共 13 |
| `KS_DEEP_BATCH_MAX` | 1 | `src/core/ingestion/deep_server.py` |
| `KS_DEEP_BATCH_MIN` | 1 | `src/core/ingestion/deep_server.py` |
| `KS_DEEP_BATCH_WAIT` | 1 | `src/core/ingestion/deep_server.py` |
| `KS_DEEP_SERVER` | 2 | `src/core/ingestion/deep_server.py`、`src/core/ingestion/mineru_adapter.py` |
| `KS_DEEP_WORKERS` | 1 | `src/core/ingestion/deep_server.py` |
| `KS_ENGINE_ROOT` | 1 | `plugin/src/engine.js` |
| `KS_GPU_LOCK` | 1 | `src/core/ingestion/mineru_adapter.py` |
| `KS_GPU_LOCK_PATH` | 1 | `src/core/ingestion/mineru_adapter.py` |
| `KS_GPU_LOCK_TIMEOUT` | 2 | `src/core/ingestion/mineru_adapter.py`、`tests/test_mineru_gpu_lock.py` |
| `KS_MINERU_CLOUD` | 1 | `src/core/ingestion/mineru_adapter.py` |
| `KS_MINERU_DEEP` | 1 | `src/core/ingestion/mineru_adapter.py` |
| `KS_MINERU_LOCAL` | 1 | `src/core/ingestion/mineru_adapter.py` |
| `KS_MINERU_LOCAL_BACKEND` | 2 | `src/core/ingestion/deep_server.py`、`src/core/ingestion/mineru_adapter.py` |
| `KS_MODELS_DIR` | 4 | `src/core/config.py`、`tests/test_long_clause_tail_ruler.py`、`tests/test_reranker.py`、`plugin/src/engine.js` |
| `KS_PYTHON` | 1 | `plugin/src/engine.js` |
| `KS_REAL_DB` | 3 | `tests/test_catalog_hidden_retrieval.py`、`tests/test_change_signal.py`、`tests/test_label_gap_not_jev.py` |
| `KS_SCNET_OCR_API_KEY` | 1 | `tests/test_scnet_readchain.py` |
| `KS_SOFFICE` | 1 | `src/core/knowledge/law_source/convert.py` |
| `KS_VERIFY_CACHE_OFF` | 1 | `src/core/knowledge/law_source/verify.py` |
| `KS_VLM_ONLY` | 3 | `src/core/ingestion/deep_server.py`、`src/core/ingestion/mineru_adapter.py`、`src/core/ingestion/mineru_cloud.py` |
| `LOOP2_MAX_BLOCKED` | 1 | `scripts/loop2/driver_v2.py` |
| `LOOP2_MAX_ROUNDS` | 1 | `scripts/loop2/driver_v2.py` |
| `LOOP2_M_SILENCE` | 1 | `scripts/loop2/driver_v2.py` |
| `LOOP2_ROOT` | 1 | `scripts/loop2/driver_v2.py` |
| `LOOP2_STOP_CONSECUTIVE` | 1 | `scripts/loop2/driver_v2.py` |
| `LOOP2_VLM_ENDPOINT` | 1 | `scripts/loop2/vlm_check.py` |
| `LOOP2_VLM_MODEL` | 1 | `scripts/loop2/vlm_check.py` |
| `LOOP2_VLM_RETRIES` | 1 | `scripts/loop2/vlm_check.py` |
| `LOOP2_VLM_TIMEOUT` | 1 | `scripts/loop2/vlm_check.py` |
| `MINERU_MODEL_SOURCE` | 1 | `plugin/src/engine.js` |
| `MINERU_TOOLS_CONFIG_JSON` | 1 | `plugin/src/engine.js` |
| `MOONSHOT_API_KEY` | 1 | `scripts/loop2/vlm_check.py` |
| `NO_PROXY` | 1 | `src/core/main.py` |
| `RUN_LIVE` | 1 | `tests/test_update_channels.py` |
| `SCNET_OCR_API_KEY` | 2 | `scripts/std_bulk_import.py`、`tests/test_scnet_readchain.py` |
| `TEMP` | 2 | `scripts/preview-folder-filing.py`、`scripts/verify-seeds/b1-reingest-e2e.py` |
| `TMP` | 1 | `scripts/preview-folder-filing.py` |
| `USERPROFILE` | 1 | `scripts/make_handoff_zip.py` |
| `X` | 1 | `scripts/survey/05-deep.py` |

## 四、配置键（`app_config` 表 + 代码里出现的）

| 键 | 库里值的字节 | 加密 | 代码引用数 |
|---|---:|:--:|---:|
| `announce.min_interval_hours` | — |  | 2 |
| `announce.scan_soft_cap_s` | 4 |  | 1 |
| `announce.scan_state` | 2822 |  | 1 |
| `announce.sources` | 25305 |  | 2 |
| `data_package.imported` | — |  | 1 |
| `discover.download_later` | — |  | 1 |
| `inspect.budget_date` | 10 |  | 2 |
| `inspect.budget_used` | 1 |  | 2 |
| `inspect.daily_full_sweep_budget` | — |  | 2 |
| `law.catalog_last_refresh_at` | 25 |  | 0 |
| `update.domain_subscriptions` | 54 |  | 0 |
| `update.schedule_days` | — |  | 2 |
| `update.schedule_tiers` | — |  | 1 |