"""福建省生态环境厅 · wyzx 页明细链接形态挖掘。

列表接口（/was5/web/search?channelid=280067&classsql=dockind=3）只回登记字段，
问答正文在明细页 —— 本脚本从 wyzx 页全文里找明细链接的拼法
（recid/metadataid 模板、.shtml 形态、JS url 拼接），证据存 recon/fujian-wyzx-full.html。
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

PAGE = "https://sthjt.fujian.gov.cn/gzcy/tzxx/wyzx/"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(PAGE)
    t = r.text
    (HERE / "fujian-wyzx-full.html").write_text(t, encoding="utf-8")

    pats = sorted(set(re.findall(
        r'["\'](/[^"\']*(?:recid|metadataid|mid|infoid)[^"\']*)["\']', t, re.I)))
    print("id-link templates:", *(f"  {p}" for p in pats[:10]), sep="\n")

    tmpl = sorted(set(re.findall(r'href\s*=\s*["\']([^"\']*\.shtml)["\']', t)))
    print("shtml links:", *(f"  {p}" for p in tmpl[:8]), sep="\n")

    for m in re.finditer(r"(url|href|link)\s*[:=][^;]{10,200}", t):
        s = m.group(0)
        if any(k in s.lower() for k in ("recid", "metadataid", "detail", ".shtml")):
            print("JS>", s[:220])

    # wasdoc 模式的列表渲染：找 rows/fields 映射（s1..t2 用在哪）
    for m in re.finditer(r"\bs(\d{1,2})\b[^;{}]{0,80}", t):
        pass  # 太泛，跳过
    idx = t.find("recid")
    if idx > 0:
        print("context around recid:")
        print(t[max(0, idx - 300):idx + 500])
    return 0


if __name__ == "__main__":
    main()
