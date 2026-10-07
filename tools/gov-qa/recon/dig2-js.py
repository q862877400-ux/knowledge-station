"""省级站侦察第三步：追外部 JS 里的 channelid / 接口。

上一轮（dig-hd-pages.py）发现：湖南两站的内联 JS 没有 channelid，
真正的互动逻辑在 `/sthjt/xhtml/js/hdjl_*.js`、`/yjt/xhtml/js/hdjl_*.js` 这些外部文件里；
广东应急的 channelid=21926 来自「留言受理情况统计」页；
福建公众参与页的列表逻辑可能在 `/images/20230412sthjt.js`。
本轮把这些文件抓下来逐行找线索，证据落 recon/dig2-js.json。
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

#: 行内出现这些词就算线索
HINT = re.compile(r"(channelid|was5|web/search|searchword|\.ajax\(|url\s*:|getjson|post\()", re.I)
#: 广东应急统计页：channelid 前后文
CTX_RE = re.compile(r".{0,120}channelid.{0,120}", re.I | re.S)
A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")

#: (标签, URL, 挖法)  挖法 = lines | context | links
TARGETS: list[tuple[str, str, str]] = [
    ("湖南生态·hdjl_common.js", "https://sthjt.hunan.gov.cn/sthjt/xhtml/js/hdjl_common.js", "lines"),
    ("湖南生态·hdjl_index.js", "https://sthjt.hunan.gov.cn/sthjt/xhtml/js/hdjl_index.js", "lines"),
    ("湖南生态·hdjl_lm.js", "https://sthjt.hunan.gov.cn/sthjt/xhtml/js/hdjl_lm.js", "lines"),
    ("湖南应急·hdjl_common.js", "https://yjt.hunan.gov.cn/yjt/xhtml/js/hdjl_common.js", "lines"),
    ("湖南应急·hdjl_index.js", "https://yjt.hunan.gov.cn/yjt/xhtml/js/hdjl_index.js", "lines"),
    ("湖南应急·hdjl_lm.js", "https://yjt.hunan.gov.cn/yjt/xhtml/js/hdjl_lm.js", "lines"),
    ("广东应急·留言统计页", "https://yjgl.gd.gov.cn/hd/lytj/index.html", "context"),
    ("广东应急·hdjlpt config.js", "https://yjgl.gd.gov.cn/hdjlpt/static/core/js/config.js", "lines"),
    ("广东应急·hdjlpt index/common.js", "https://yjgl.gd.gov.cn/hdjlpt/static/index/js/common.js", "lines"),
    ("福建生态·公众参与页", "https://sthjt.fujian.gov.cn/gzcy/", "links"),
    ("福建生态·20230412sthjt.js", "https://sthjt.fujian.gov.cn/images/20230412sthjt.js?v=1.11", "lines"),
]


def main() -> int:
    import httpx

    out: list[dict] = []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True,
                      trust_env=False, timeout=25) as cli:
        for label, url, how in TARGETS:
            rec: dict = {"label": label, "url": url}
            try:
                r = cli.get(url)
                rec["status"] = r.status_code
                rec["len"] = len(r.text or "")
                text = r.text or ""
                if how == "lines":
                    hits = []
                    for i, line in enumerate(text.splitlines()):
                        if HINT.search(line):
                            hits.append(line.strip()[:220])
                        if len(hits) >= 40:
                            break
                    rec["hint_lines"] = hits
                elif how == "context":
                    rec["contexts"] = [m.group(0).strip()[:300]
                                       for m in CTX_RE.finditer(text)][:10]
                else:  # links
                    links = []
                    for href, inner in A_HREF_RE.findall(text):
                        t = TAG_RE.sub("", inner).strip()
                        if t:
                            links.append(f"{t} -> {href}")
                    rec["links"] = links[:60]
                print(f"[dig2] {label}: {rec['status']}/{rec['len']}B "
                      f"线索 {len(rec.get('hint_lines', rec.get('contexts', rec.get('links', []))))}", flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}"
                print(f"[dig2] {label}: 网络错误 {type(e).__name__}", flush=True)
            out.append(rec)
            time.sleep(1.5)

    path = HERE / "dig2-js.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[dig2] 证据已写 {path}")
    return 0


if __name__ == "__main__":
    main()
