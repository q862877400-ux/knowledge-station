"""MinerU 云模式切换 CLI（2026-09-15 立）。

用途：设置页那条路要走 DSH host 代理 + 客户端包（需重启/刷新），本脚本直接
走引擎侧的同一条写入路径（`api_credentials.set_credential` + `reset_settings`），
在没有 UI 时也能立刻切换模式。

用法：
  python var/ocr-loop/set_mineru_mode.py            # 看当前模式
  python var/ocr-loop/set_mineru_mode.py vlm        # 切到 VLM
  python var/ocr-loop/set_mineru_mode.py pipeline   # 切回 pipeline
  python var/ocr-loop/set_mineru_mode.py MinerU-HTML

说明：值必须属于官方 v4 契约三选一（pipeline / vlm / MinerU-HTML），
非法值会被拒绝且不落盘。写入落在引擎加密存储（DPAPI），不碰系统层。
**下次云解析即生效**（引擎若已在运行且已缓存 Settings，重启引擎或经设置页
保存一次即可让缓存失效）。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.config import MINERU_CLOUD_MODEL_VERSIONS, get_settings, reset_settings  # noqa: E402
from src.core.settings import api_credentials as cred  # noqa: E402


def show() -> None:
    st = cred.get_status()["mineru_cloud"]
    print(f"云解析：configured={st['configured']} base_url={st['base_url']}")
    print(f"当前模式：{st['model_version']}（可选：{', '.join(st['model_versions'])}）")


def main() -> None:
    if len(sys.argv) < 2:
        show()
        return
    mode = sys.argv[1].strip()
    try:
        cred.set_credential("mineru_cloud", model_version=mode)
    except cred.InvalidModelVersion as e:
        print(f"拒绝：{e}")
        print(f"合法取值：{', '.join(MINERU_CLOUD_MODEL_VERSIONS)}")
        raise SystemExit(2)
    reset_settings()
    print(f"已切换为 {mode!r}")
    show()
    print("云请求将发送 model_version =", get_settings().mineru_cloud_model_version)


if __name__ == "__main__":
    main()
