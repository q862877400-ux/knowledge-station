"""设置模块 API 路由（2026-08-27 立；2026-09-11 改写加密存储）。

- GET  /api/v1/settings/api-config          脱敏状态（configured/base_url，绝不回显 Key）
- PUT  /api/v1/settings/api-config          写**引擎加密存储**（secret_store，DPAPI）并
                                            立即 reset 引擎内缓存；**零系统层写入**
- POST /api/v1/settings/api-config/test     活体探测 {channel: mineru_cloud|llm}
"""
from __future__ import annotations

import logging

from fastapi import Request

logger = logging.getLogger(__name__)


def register(app, json_error):
    @app.get("/api/v1/settings/api-config")
    def api_config_get():
        """读 API 配置状态（§10.79：要读凭据/配置文件 ⇒ 同步 I/O，`def`）。

        ⚠ 它与 PUT 是**同一路径的两个方法**：批量转换时按 (方法, 路径) 核对才发现这条 GET
        也是重活（原先只按路径找，`routes[0]` 抓到 GET 就误判成"转换漏了"——**闸门帮我抓的**）。
        """
        from src.core.settings import api_credentials as cred
        try:
            return {"ok": True, **cred.get_status()}
        except Exception as e:  # noqa: BLE001
            logger.warning("api-config 状态读取失败", exc_info=True)
            return json_error(500, "internal_error", str(e))

    @app.put("/api/v1/settings/api-config")
    def api_config_put(body: dict | None = None):
        """写 API 配置（§10.79：body 走**签名**；端点做校验+落盘 ⇒ 必须留在**线程池**里）。

        ⚠ 原先这里是 `async def` + `await request.json()` 包在 `try/except` 里（坏 body → 422
        `bad_request`）。改签名取 body 之后那个 `try` **不可能再抛**（死代码，已删），
        **坏 body 由 FastAPI 直接 422**（判据形状变了：不再是那句"body 必须为 JSON"）——
        与 §10.71/§10.76 同口径。
        """
        from src.core.config import reset_settings
        from src.core.settings import (
            api_credentials as cred,
        )
        body = body or {}
        for channel in ("mineru_cloud", "llm"):
            sec = body.get(channel) or {}
            if not isinstance(sec, dict):
                continue
            try:
                cred.set_credential(channel,
                                    api_key=sec.get("api_key"),
                                    base_url=sec.get("base_url"),
                                    model_version=sec.get("model_version"))
            except cred.UnknownChannel as e:
                return json_error(422, "unknown_channel", str(e))
            except cred.InvalidModelVersion as e:
                # 2026-09-15：模式取值非法 → 422 明确报错（不落脏值、不回显 Key）
                return json_error(422, "invalid_model_version", str(e))
            except cred.secret_store.SecretStoreError as e:
                return json_error(500, "secret_store_write_failed",
                                  f"加密存储写入失败: {e}")
        reset_settings()  # 引擎进程内缓存立即失效，下一次调用即用新值
        return {"ok": True, **cred.get_status()}

    @app.post("/api/v1/settings/api-config/test")
    def api_config_test(body: dict | None = None):
        from src.core.settings import api_credentials as cred
        body = body or {}
        channel = body.get("channel") or ""
        try:
            r = cred.test_channel(str(channel))
        except cred.UnknownChannel as e:
            return json_error(422, "unknown_channel", str(e))
        except Exception as e:  # noqa: BLE001 —— 探测异常透出真实原因
            r = {"ok": False, "detail": str(e)[:200]}
        return {"ok": True, "result": r}
