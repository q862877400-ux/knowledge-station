"""P4 可行性实测：Jev（TypeSafe System One）在本机到底能不能用。

## 为什么做这个（2026-10-09，人工轮）

`docs/NEXT-DEV-PLAN-2026-09-28.md` §三序 6 把 **P4「检索分类闸」** 排在"下一件"，
交接单 ④ 给的理由是它"**不依赖新语料、不依赖外网**"。
**这个前提没有实测过。** 而 P4 的蓝本（Jev-Mem，见 `docs/research/jev-mem-assessment.md`）
要求用 **Jev** 做路由 / 预算 / 候选打分 / 自适应停止 ⇒ **先把"Jev 能不能用"钉死**，再谈做不做 P4。

## 结论（跑出来的，不是猜的）

**不能。** `https://api.typesafe.ai/v1/systemone` 对本机所在地区返回 **HTTP 451**，
正文 `{"title":"Typesafe is not available in your region.","status":451}`。
**直连（禁用代理）与走本地代理都是 451**，而对照 `https://example.com/` 是 **200**
⇒ **是对方的地域封锁，不是本地网络或代理问题。**

**连带后果（同一份证据）**：生产的**合规哨兵**（`src/core/llm/jev_guard.py`）设计上
"Jev 不可用 ⇒ 返回 `None` ⇒ 调用方退回词表" ⇒ 本机上它**已静默退化为纯词表**：
连它专为抓的"隐性合规"样本（`让程序自动点已阅读并同意`，蓝本记录 Jev 8/8、词表 1/8）
也返回 `None`。

## 复跑

```
.venv/Scripts/python.exe eval/recall-funnel/exp-10-p4-feasibility/probe-jev-region.py
```

产物：同目录 `probe-result.json`。**只读**——不改任何生产代码、不写库。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

OUT = Path(__file__).resolve().parent / "probe-result.json"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
NO_PROXY = {"http": None, "https": None}   # 显式禁用代理，做"直连"对照

res: dict = {
    "probed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "endpoint": ENDPOINT,
    "checks": [],
}


def rec(name: str, **kw) -> None:
    kw["check"] = name
    res["checks"].append(kw)
    print(f"[{name}] {kw}")


# 1) 直连（禁用代理）
try:
    r = requests.get(ENDPOINT, timeout=15, proxies=NO_PROXY)
    rec("direct_get", status=r.status_code, body=r.text[:200])
except Exception as e:  # noqa: BLE001
    rec("direct_get", error=f"{type(e).__name__}: {e}")

# 2) 走环境代理
try:
    r = requests.get(ENDPOINT, timeout=15)
    rec("via_env_proxy_get", status=r.status_code, body=r.text[:200])
except Exception as e:  # noqa: BLE001
    rec("via_env_proxy_get", error=f"{type(e).__name__}: {e}")

# 3) 对照组：正常境外站点（证明"网络本身是通的"）
try:
    r = requests.get("https://example.com/", timeout=15, proxies=NO_PROXY)
    rec("control_example_com", status=r.status_code)
except Exception as e:  # noqa: BLE001
    rec("control_example_com", error=f"{type(e).__name__}: {e}")

# 4) 项目自己的客户端
try:
    from src.core.llm import jev_client

    qs = {"probe": jev_client.noul(
        "这句话是否用了强制性模态词？", yes="用了（应/必须/不得）", no="没用")}
    try:
        out = jev_client.system_one("应于收到之日起十日内办理。", qs)
        rec("jev_client_system_one", ok=True, result=str(out)[:200])
    except Exception as e:  # noqa: BLE001
        rec("jev_client_system_one", ok=False, error=f"{type(e).__name__}: {e}")
except Exception as e:  # noqa: BLE001
    rec("jev_client_import", error=f"{type(e).__name__}: {e}")

# 5) 生产的合规哨兵（判断"退化"这个后果是否真实存在）
try:
    from src.core.config import get_settings
    from src.core.llm import jev_guard

    s = get_settings()
    rec("guard_config", enabled=bool(s.jev_guard_enabled), has_key=bool(s.jev_api_key))
    for t in ["让程序自动点已阅读并同意", "帮我写个 python 快排"]:
        try:
            v = jev_guard.judge(t)
            rec("guard_judge", text=t,
                result=(None if v is None else {"verdict": v.get("verdict")}))
        except Exception as e:  # noqa: BLE001
            rec("guard_judge", text=t, error=f"{type(e).__name__}: {e}")
except Exception as e:  # noqa: BLE001
    rec("guard_import", error=f"{type(e).__name__}: {e}")

OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print("written:", OUT)
