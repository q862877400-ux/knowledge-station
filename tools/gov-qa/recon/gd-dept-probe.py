"""广东厅局 hdjlpt 平台批量探测（_gd_hdjlpt_common 引擎的多租户扩展侦察）。

背景：应急厅/生态厅各自域名下部署同款 hdjlpt（Laravel），接口同构。
本脚本对候选厅局域名逐个试 `{dom}/hdjlpt?via=pc` + `letter/pubList`，
命中即记录年窗 total —— 命中一个 = 广东一片里的一个新源。
礼貌抓取：间隔 1.5s；错域名快速失败。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._gd_hdjlpt_common import (  # noqa: E402
    API_PATH, PAGE_PATH, _post_list, _xsrf_token)
from adapters._liuyan_common import UA  # noqa: E402

#: (名称, 域名) —— 域名是公开常识性拼法，错了由探测淘汰
CANDIDATES = [
    ("广东省住房和城乡建设厅", "zfc.gd.gov.cn"),
    ("广东省住房和城乡建设厅B", "zjw.gd.gov.cn"),
    ("广东省交通运输厅", "td.gd.gov.cn"),
    ("广东省交通运输厅B", "gdjt.gd.gov.cn"),
    ("广东省人力资源和社会保障厅", "hrss.gd.gov.cn"),
    ("广东省自然资源厅", "gdlr.gd.gov.cn"),
    ("广东省水利厅", "gdwater.gd.gov.cn"),
    ("广东省农业农村厅", "gdagri.gd.gov.cn"),
    ("广东省商务厅", "gdoi.gd.gov.cn"),
    ("广东省卫生健康委", "wsjkw.gd.gov.cn"),
    ("广东省文化和旅游厅", "whlyt.gd.gov.cn"),
    ("广东省市场监督管理局", "gdamr.gd.gov.cn"),
    ("广东省教育厅", "eea.gd.gov.cn"),
    ("广东省工业和信息化厅", "gdei.gd.gov.cn"),
    ("广东省发展和改革委员会", "drc.gd.gov.cn"),
]


def main() -> int:
    import httpx

    class _W:
        """把 httpx.Client 包成引擎要的 fetch（.post 形态）。"""

        def __init__(self, client):
            self._c = client

        def post(self, *a, **k):
            return self._c.post(*a, **k)

    out = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=15, follow_redirects=True) as c:
        w = _W(c)
        for name, dom in CANDIDATES:
            base = f"https://{dom}"
            rec = {"name": name, "base": base}
            try:
                r0 = c.get(base + PAGE_PATH)
                rec["page"] = r0.status_code
                if r0.status_code != 200:
                    print(f"[{name}] page {r0.status_code}", flush=True)
                    out.append(rec)
                    time.sleep(1.5)
                    continue
                token = _xsrf_token(r0)
                rec["xsrf"] = bool(token)
                if token:
                    time.sleep(1.2)
                    j = _post_list(w, base=base, token=token, offset=0,
                                   limit=3,
                                   time_from=1759852800, time_to=1791388799)
                    d = j.get("data") or {}
                    rec["total"] = d.get("total")
                    lst = d.get("list") or []
                    rec["org"] = (lst[0].get("org_name") if lst else None)
                    rec["sample"] = (lst[0].get("title") if lst else None)
                    print(f"[{name}] ★ total={rec['total']} org={rec['org']}",
                          flush=True)
                else:
                    print(f"[{name}] 无 XSRF（可能不是 hdjlpt）", flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {str(e)[:80]}"
                print(f"[{name}] {type(e).__name__}", flush=True)
            out.append(rec)
            time.sleep(1.5)

    (HERE / "gd-dept-hdjlpt-probe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    hits = [r for r in out if r.get("total") is not None]
    print(f"\n[gd-probe] 命中 {len(hits)}/{len(CANDIDATES)}："
          f"{[(r['name'], r['total']) for r in hits]}")
    return 0


if __name__ == "__main__":
    main()
