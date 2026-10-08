"""河北两条线 · 适配器落地前实测探针（general-purpose-1, 2026-10-08）。

不依赖 harvest.py 的 _Fetcher（那是给适配器用的），这里直接用 httpx 复现实测：
  1) szj 省数政局留言公开（EWB 接口型）
  2) czt 省财政厅群众信箱（静态型）

跑法（cwd=仓库根 D:\\AI\\work space\\zcode）：
  D:\\AI\\work space\\zcode\\.venv\\Scripts\\python.exe tools/gov-qa/recon/heb-adapters-probe.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

import httpx  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
TAG = re.compile(r"<[^>]+>")
PAUSE = 1.5


def clean(html):
    return re.sub(r"\s+", " ", TAG.sub(" ", html or "")).strip()


def probe_szj(cli):
    B = "http://szj.hebei.gov.cn"
    SITE_GUID = "645ad4ac-16b3-47d8-95bc-294a9052c6a2"
    print("\n=== [1] heb-szj (EWB 接口型) ===")
    # ① 匿名 token
    r = cli.post(B + "/EWB-FRONT/rest/getOauthInfoAction/getNoUserAccessToken",
                 data={"params": "{}"})
    print("token HTTP", r.status_code)
    tok = (r.json().get("custom") or {}).get("access_token")
    print("access_token 前 12 位:", (tok or "")[:12])
    if not tok:
        print("  !! 未取到 token，停")
        return
    H = {"Authorization": "Bearer " + tok}
    # ② 列表
    params = {"siteGuid": SITE_GUID, "subject": "", "postName": "", "replyContent": "",
              "content": "", "startTime": "", "endTime": "", "group": "",
              "pageIndex": 0, "pageSize": 10}
    r = cli.post(B + "/EWB-FRONT/rest/frontAppNotNeedLoginAction/getLetterListByCondition",
                 data={"params": json.dumps(params)}, headers=H)
    print("list HTTP", r.status_code)
    custom = (r.json().get("custom") or {})
    print("total =", custom.get("total"))
    rows = custom.get("data") or []
    print("first page rows =", len(rows))
    if rows:
        print("sample keys:", sorted(rows[0].keys()))
        print("row0:", json.dumps({k: rows[0].get(k) for k in
              ("infoGuid", "subject", "postDate", "handleDate", "boxName", "type")},
              ensure_ascii=False))
        # ③ 明细
        time.sleep(PAUSE)
        d = cli.post(B + "/EWB-FRONT/rest/frontAppNotNeedLoginAction/getLetterDetail",
                     data={"params": json.dumps({"siteGuid": SITE_GUID,
                           "infoGuid": rows[0]["infoGuid"]})}, headers=H)
        print("detail HTTP", d.status_code)
        data = (d.json().get("custom") or {}).get("data") or {}
        print("detail keys:", sorted(data.keys()))
        print("  Q:", (data.get("subject") or "")[:60])
        print("  Q.content:", clean(data.get("content"))[:100])
        print("  A.replycontent:", clean(data.get("replycontent"))[:160])
        print("  postdate/operatedate:", data.get("postdate"), "/", data.get("operatedate"))


def probe_czt(cli):
    B = "http://czt.hebei.gov.cn"
    LIST = B + "/hdjl/qzxx/"
    print("\n=== [2] heb-czt (静态型) ===")
    r = cli.get(LIST + "index.html")
    print("list HTTP", r.status_code, "len", len(r.text or ""))
    cm = re.search(r"countPage\s*=\s*(\d+)", r.text or "")
    print("countPage =", cm.group(1) if cm else None)
    ITEM = re.compile(r'<li class="clearfix">(.*?)</li>', re.S)
    LINK = re.compile(r'<a href="([^"]+)"[^>]*title="([^"]*)"')
    DATE = re.compile(r'<span class="dt">\s*([0-9\-]+)\s*</span>')

    def block_items(html):
        """只在『留言回复列表』标题后的第一个 <ul> 里取条目（否则会混进『受理情况统计』）。"""
        i = html.find("留言回复列表")
        seg = html[i:] if i >= 0 else html
        m = re.search(r"<ul>(.*?)</ul>", seg, re.S)
        out = []
        for blk in ITEM.findall(m.group(1) if m else ""):
            lm = LINK.search(blk)
            if not lm:
                continue
            dm = DATE.search(blk)
            out.append((lm.group(1), lm.group(2), dm.group(1) if dm else None))
        return out

    pages = int(cm.group(1)) if cm else 1
    total = 0
    for p in range(1, pages + 1):
        url = LIST + ("index.html" if p == 1 else f"index_{p-1}.html")
        if p > 1:
            time.sleep(PAUSE)
            r = cli.get(url)
        its = block_items(r.text or "")
        total += len(its)
        print(f"  第 {p}/{pages} 页 items = {len(its)}")
    print("合计 items =", total)
    its = block_items(r.text or "")
    if its:
        print("last-page item0:", its[0])
        u = its[0][0]
        url = u if u.startswith("http") else LIST + u.lstrip("./")
        time.sleep(PAUSE)
        d = cli.get(url)
        print("detail HTTP", d.status_code, url)
        h = d.text or ""
        tm = re.search(r'<div class="c_title">(.*?)</div>', h, re.S)
        sm = re.search(r'<div class="c_subtitle">(.*?)</div>', h, re.S)
        print("  Q:", clean(tm.group(1))[:60] if tm else None)
        print("  sub:", clean(sm.group(1))[:120] if sm else None)
        rt = re.search(r"答复结果[:：]\s*</td>\s*<td[^>]*>(.*?)</td>", h, re.S)
        print("  A:", clean(rt.group(1))[:160] if rt else "NOT FOUND")


def main():
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        try:
            probe_szj(cli)
        except Exception as e:                                              # noqa: BLE001
            print("szj 探针异常:", type(e).__name__, e)
        time.sleep(PAUSE)
        try:
            probe_czt(cli)
        except Exception as e:                                              # noqa: BLE001
            print("czt 探针异常:", type(e).__name__, e)


if __name__ == "__main__":
    sys.exit(main())
