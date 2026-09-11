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
    async def api_config_get():
        from src.core.settings import api_credentials as cred
        try:
            return {"ok": True, **cred.get_status()}
        except Exception as e:  # noqa: BLE001
            logger.warning("api-config 状态读取失败", exc_info=True)
            return json_error(500, "internal_error", str(e))

    @app.put("/api/v1/settings/api-config")
    async def api_config_put(request: Request):
        from src.core.config import reset_settings
        from src.core.settings import (
            api_credentials as cred,
        )
        try:
            body = await request.json()
        except Exception:
            return json_error(422, "bad_request", "body 必须为 JSON")
        for channel in ("mineru_cloud", "llm"):
            sec = body.get(channel) or {}
            if not isinstance(sec, dict):
                continue
            try:
                cred.set_credential(channel,
                                    api_key=sec.get("api_key"),
                                    base_url=sec.get("base_url"))
            except cred.UnknownChannel as e:
                return json_error(422, "unknown_channel", str(e))
            except cred.secret_store.SecretStoreError as e:
                return json_error(500, "secret_store_write_failed",
                                  f"加密存储写入失败: {e}")
        reset_settings()  # 引擎进程内缓存立即失效，下一次调用即用新值
        return {"ok": True, **cred.get_status()}

    @app.post("/api/v1/settings/api-config/test")
    async def api_config_test(request: Request):
        from src.core.settings import api_credentials as cred
        try:
            body = await request.json()
        except Exception:
            body = {}
        channel = body.get("channel") or ""
        try:
            r = cred.test_channel(str(channel))
        except cred.UnknownChannel as e:
            return json_error(422, "unknown_channel", str(e))
        except Exception as e:  # noqa: BLE001 —— 探测异常透出真实原因
            r = {"ok": False, "detail": str(e)[:200]}
        return {"ok": True, "result": r}
