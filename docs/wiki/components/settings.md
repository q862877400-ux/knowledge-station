# settings（设置与凭据）

**位置**：`src/core/settings/`
**一句话**：密钥与通道配置只存在引擎自己这里——不碰系统层。

## 职责

**凭据的唯一写落点**：`secret_store.py` 管 `<data_dir>/secrets.json`（Windows DPAPI 用户态加密、原子写、带锁）；`api_credentials.py` 管通道（两条，**一律 KS_ 前缀**：`mineru_cloud` = `KS_MINERU_CLOUD_API_KEY` + `KS_MINERU_CLOUD_BASE_URL`；`llm` = `KS_LLM_API_KEY` + `KS_LLM_BASE_URL`），以及旧名迁移（`DEEPSEEK_*` → `KS_LLM_*`）与系统层清理。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 密钥读写 | `secret_store.read_value()` / `has_value()` / `write_values()` / `stored_names()` | `api_credentials`、`config.py`（懒 import） |
| 密钥文件路径 | `secret_store.store_path(data_dir)` | `storage/backup.py` |
| 凭据写入与状态 | `api_credentials.set_credential()` / `get_status()` / `stored_channels()` | `api/routes_settings.py` |
| 通道连通性测试 | `api_credentials.test_channel(channel)` | `api/routes_settings.py` |
| 旧系统层迁移 | `import_system_layer()` / `adopt_legacy()` / `legacy_status()` | 设置界面 |
| 系统层检查与清理 | `system_layer_names()` / `system_layer_status()` / `clean_system_layer(names)` | 设置界面 |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| 本机文件系统（`<data_dir>/secrets.json`） | 存储 | 唯一写落点 |
| Windows DPAPI（`CryptProtectData` / `CryptUnprotectData`） | 操作系统 | 用户态加密 |
| `HKCU\Environment` / 进程环境变量 | 操作系统 | **只读**：迁移前兼容与迁移工具的读取源 |

## 明确不做什么

- 🔴 **MUST NOT 碰系统层**：业主 2026-09-11 指令「不要动系统层」——不写注册表、不写系统 / 全局环境变量、不用 `--global`；系统层**只读**。
- **唯一允许的系统层写操作是删除**：`clean_system_layer()`，且**先核对加密存储读回一致才删**。
- **不回显密钥**：只回状态（有没有、来源是哪一层）。
- **不写数据库**：密钥不进表。
- **不替调用方选模型 / 版本之外的事**：只存 `api_key` / `base_url` / `model_version` 三个值，不决定用哪家。
- **不做多用户隔离**（未核：是否有此需求登记）。

## 关键数据

| 对象 | 关键字段 | 说明 |
|---|---|---|
| `<data_dir>/secrets.json` | 通道名 → 加密后的值 | DPAPI 加密；`KS_DATA_DIR` 可重定向 |
| 通道表（`api_credentials.py` 内） | 2 条：`mineru_cloud` / `llm` | 键名与 `KS_` 前缀写死在这里 |

## 改了它会影响谁

- **`api/routes_settings.py`**：设置界面的全部端点
- **`llm`**：Key 未配置时抛 `LLMError`、降级为占位答案
- **`storage/backup.py`**：备份含 `store_path`
- **DSH 宿主**：历史上写系统层曾把 DSH 的模型设置页密钥输入框永久置灰（两次真实事故），本模块就是为断掉这条链而存在


## 规模与覆盖（2026-10-23 实测）

| 项 | 数字 |
|---|---|
| 文件数 | **3** 个 `.py` |
| 行数 | **684** |
| 提到本子系统的测试文件 | **9** 个 |

⚠ 本子系统内有**零测试模块**：`routes_settings`（全仓没有任何一条用例是为它写的）。

> 数字口径：`rglob("*.py")` 排除 `__pycache__`；测试覆盖 = 在 `tests/*.py` 里出现过 `src.core.<本子系统>` 的文件数（**只是「提到」，不等于「被测」**）。

## 已知边界（诚实）

- **DPAPI 是 Windows 用户态**：换用户或换机器，`secrets.json` 解不开。
- **旧名 `DEEPSEEK_*` 仍被读取**（迁移兼容），但**新值只写 `KS_*`**。
