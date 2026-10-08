"""山东地市 第三轮：枣庄 IGI 实测 + 淄博 jact 实测 + 济南/青岛 接口挖掘。
用法：python recon/sd-city-probe3.py
输出：recon/sd-city-probe3.txt
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

OUT = HERE / "sd-city-probe3.txt"
UA_HDR = {"User-Agent": UA}


def jact_list(c, f, base, sysid, ref):
    url = (f"{base}/jact/front/dataproxy_mailpublist.do"
           f"?startrecord=1&endrecord=19&perpage=19&groupSize=3")
    try:
        r = c.post(url, data={"sysid": str(sysid), "datadetailid": "", "dicvalue": "",
                              "mailnumber": "", "querycode": "", "groupid": "",
                              "mailstate": "", "starttime": "", "endtime": "",
                              "keyword": ""},
                   headers={"Referer": ref, "X-Requested-With": "XMLHttpRequest"}, timeout=15)
        m = re.search(r"totalRecord\s*=\s*([0-9.]+)", r.text or "")
        f.write(f"  jact POST sysid={sysid} {base} → {r.status_code} totalRecord="
                f"{m.group(1) if m else '?'} len={len(r.text)}\n")
    except Exception as e:                                              # noqa: BLE001
        f.write(f"  jact POST sysid={sysid} {base} → {type(e).__name__}: {str(e)[:80]}\n")


def main() -> int:
    import httpx
    with httpx.Client(headers=UA_HDR, trust_env=False, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            # ---------- 枣庄 IGI ----------
            f.write("=" * 70 + "\n## 枣庄 zaozhuang (IGI siteId=124 appId=84)\n")
            zb = "http://www.zaozhuang.gov.cn"
            ref = zb + "/zmhd/"
            for base in [zb + "/IGI"]:
                for order in ["1"]:
                    u = (f"{base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
                         f"&siteId=124&order={order}&appId=84&pageIndex=1&pageSize=20")
                    try:
                        r = c.get(u, headers={"Referer": ref}, timeout=15)
                        body = r.text or ""
                        n = len(((r.json().get("datas") or {}).get("data") or [])) \
                            if "datas" in body else -1
                        f.write(f"  GET {u} → {r.status_code} datas_n={n} len={len(body)}\n")
                        if n >= 0:
                            d0 = ((r.json().get("datas") or {}).get("data") or [{}])[0]
                            f.write(f"     sample TITLE={d0.get('TITLE')!r} "
                                    f"ISREPLY={d0.get('ISREPLY')} "
                                    f"chain={d0.get('PROVINCE')}/{d0.get('CITY')}/{d0.get('AREA')}\n")
                    except Exception as e:                                  # noqa: BLE001
                        f.write(f"  GET {u} → {type(e).__name__}: {str(e)[:80]}\n")
                    time.sleep(1)
            # 明细测试
            u = (f"{zb}/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
                 f"&siteId=124&order=1&appId=84&pageIndex=1&pageSize=3")
            try:
                r = c.get(u, headers={"Referer": ref}, timeout=15)
                rows = ((r.json().get("datas") or {}).get("data") or [])
                if rows:
                    mid = rows[0].get("METADATAID")
                    du = (f"{zb}/IGI/nbhd/openGovmsgbox.do?method=viewGovmsgbox"
                          f"&siteId=124&metadataId={mid}")
                    d = c.get(du, headers={"Referer": ref}, timeout=15)
                    reps = ((d.json().get("datas") or {}).get("REPLYS") or [])
                    f.write(f"  明细 mid={mid} → {d.status_code} REPLYS={len(reps)} "
                            f"first_ans_len={len((reps[0].get('REPLYHTMLCONTENT') or '') if reps else '')}\n")
            except Exception as e:                                          # noqa: BLE001
                f.write(f"  明细 → {type(e).__name__}: {str(e)[:80]}\n")

            # ---------- 淄博 jact ----------
            f.write("\n" + "=" * 70 + "\n## 淄博 zibo (jact)\n")
            zbb = "http://www.zibo.gov.cn"
            for sid in ["1", "54"]:
                jact_list(c, f, zbb, sid, f"{zbb}/jact/front/mailpublist.do?sysid={sid}")
                time.sleep(1)

            # ---------- 济南 ----------
            f.write("\n" + "=" * 70 + "\n## 济南 jinan\n")
            jb = "http://www.jinan.gov.cn"
            ju = (jb + "/api-gateway/jpaas-jact-web-server/front/mail-pub-list.do"
                  "?platformIid=HTMi0SM6aXpdnEJDZH931&govOpen=1&submitTargetIds=0114")
            r = c.get(ju, timeout=15)
            (HERE / "sd-city-jinan-maillist.html").write_text(r.text or "", encoding="utf-8")
            f.write(f"  GET mail-pub-list → {r.status_code} len={len(r.text)}\n")
            # 抠页面里的接口
            for pat in re.findall(r'["\'](/[^"\']*(?:jact|mail|api-gateway|list)[^"\']*)["\']',
                                  r.text or "", re.I)[:20]:
                f.write(f"     api-cand: {pat}\n")
            for sid in ["1", "2", "54"]:
                jact_list(c, f, jb, sid, f"{jb}/jact/front/mailpublist.do?sysid={sid}")
                time.sleep(1)

            # ---------- 青岛 ----------
            f.write("\n" + "=" * 70 + "\n## 青岛 qingdao\n")
            qb = "http://www.qingdao.gov.cn"
            for u in [qb + "/zmhd/", qb + "/GovernmentSJXX/MainFrmNew.aspx",
                      "http://12345wx.qingdao.gov.cn:81/hotline12345/szfwz/base_Seekcode.htm"]:
                try:
                    r = c.get(u, timeout=15)
                    f.write(f"  GET {u} → {r.status_code} len={len(r.text)}\n")
                    if r.status_code == 200:
                        (HERE / ("sd-city-qingdao-" +
                                 re.sub(r'\W+', '_', u)[-40:] + ".html")).write_text(
                            r.text, encoding="utf-8")
                        for pat in re.findall(
                                r'["\']([^"\']*(?:\.do|\.ashx|\.json|api|Seekcode|seekcode|list)[^"\']*)["\']',
                                r.text, re.I)[:15]:
                            f.write(f"     cand: {pat}\n")
                except Exception as e:                                      # noqa: BLE001
                    f.write(f"  GET {u} → {type(e).__name__}: {str(e)[:80]}\n")
                time.sleep(1)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
