"""测其他省份的厅局域名下是否也存在广东同款 `/hdjlpt` 平台。

动机：广东 37 个厅局共用 hdjlpt（一个省=一片）；若他省也用同款，
就又是一片。本脚本对**可达省份**的厅局域名试 `{dom}/hdjlpt?via=pc`，
200 且页面带平台特征（app.gd.gov.cn 资源 / XSRF cookie）即命中。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

#: (省, 厅局, 域名) —— 只列**此前探测确认可达**的省
CANDS = [
    ("四川", "生态环境厅", "sthjt.sc.gov.cn"),
    ("四川", "应急管理厅", "yjt.sc.gov.cn"),
    ("北京", "生态环境局", "sthjj.beijing.gov.cn"),
    ("北京", "应急管理局", "yjglj.beijing.gov.cn"),
    ("上海", "生态环境局", "sthj.sh.gov.cn"),
    ("上海", "应急管理局", "yjgl.sh.gov.cn"),
    ("浙江", "生态环境厅", "sthjt.zj.gov.cn"),
    ("浙江", "应急管理厅", "yjglj.zj.gov.cn"),
    ("安徽", "生态环境厅", "sthjt.ah.gov.cn"),
    ("安徽", "应急管理厅", "yjt.ah.gov.cn"),
    ("福建", "生态环境厅", "sthjt.fujian.gov.cn"),
    ("辽宁", "生态环境厅", "sthj.ln.gov.cn"),
    ("吉林", "生态环境厅", "sthjt.jl.gov.cn"),
    ("贵州", "生态环境厅", "sthj.guizhou.gov.cn"),
    ("宁夏", "生态环境厅", "sthjt.nx.gov.cn"),
    ("天津", "生态环境局", "sthj.tj.gov.cn"),
]


def main() -> int:
    import httpx

    out = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=15, follow_redirects=True) as c:
        for prov, dept, dom in CANDS:
            base = f"https://{dom}"
            rec = {"province": prov, "dept": dept, "dom": dom}
            try:
                r = c.get(base + "/hdjlpt?via=pc")
                rec["status"] = r.status_code
                html = r.text or ""
                rec["len"] = len(html)
                # 广东平台的指纹
                rec["gd_platform"] = ("app.gd.gov.cn" in html or "hdjlpt" in html
                                      and "XSRF" in str(r.cookies))
                rec["cookies"] = list(getattr(r, "cookies", {}) or {})[:5]
                if r.status_code == 200 and rec["gd_platform"]:
                    print(f"[{prov} {dept}] ★ 可能同款平台 {dom} len={len(html)}")
                else:
                    print(f"[{prov} {dept}] {r.status_code} len={len(html)} "
                          f"cookies={rec['cookies']}", flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = type(e).__name__
                print(f"[{prov} {dept}] {type(e).__name__}", flush=True)
            out.append(rec)
            time.sleep(1.5)
    (HERE / "other-province-hdjlpt-probe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    hits = [r for r in out if r.get("gd_platform")]
    print(f"\n[hits] {len(hits)}/{len(out)} 疑似同款平台："
          f"{[(r['province'], r['dept']) for r in hits]}")
    return 0


if __name__ == "__main__":
    main()
