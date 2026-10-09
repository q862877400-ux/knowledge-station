"""适配器：**地方人大·法规草案征求意见**（M4 人大系统，2026-10-10 新增）。

## 为什么单列一个模块

人大系统的「法规草案征求意见」**不是问答** —— 它是「草案全文 + 公开征求意见公告」。
但用户在 GOAL.md 里明确要求「**所有人大网站**」都要打通，所以建这条通道。

⇒ **体裁用 `extra.content_kind = "立法征求意见"` 单独标记**，
   避免污染问答语料；`question` = 公告说明，`answer` = 草案全文。

## 站点（2026-10-10 实测）

| key | 站点 | 列表 | 备注 |
|---|---|---|---|
| `rd-hn` | 河南人大 | `https://www.hnrd.gov.cn/channel/16168.html` | 53 条，无分页线索 |
| `rd-sd` | 山东人大 | `http://www.sdrd.gov.cn` 首页栏目 | 21 条，`/articles/chNNNNN/...shtml` |
| `rd-js` | 江苏人大 | `https://www.jsrd.gov.cn/gzcy/fgzqyj/` | 分页 `index_N.shtml` |
| `rd-gd` | 广东人大 | `https://www.gdpc.gov.cn/gdrdw/zyfb/fgyjzj/index.html` | 分页 `index_N.html` |

⚠ 各省模板不同 ⇒ 本模块用**正则配置**驱动，新增省份只需加一条配置。
"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PAUSE = 1.5

#: 列表页里「是征求意见条目」的标题特征
ITEM_KW = ("草案", "征求", "条例", "办法", "规定", "决定")

#: 正文里属于**页面导航壳**的行特征（实测湖南人大正文混入了这些）
NAV_MARK = ("当前位置", "无障碍", "简繁体", "网站地图", "主办单位", "版权所有",
            "ICP备", "公安备", "技术支持", "浏览次数", "打印本页", "关闭窗口",
            "扫一扫", "分享到", "上一篇", "下一篇", "返回顶部")

SITES: dict[str, dict] = {
    "rd-hn": {
        "name": "河南省人大·法规草案征求意见",
        "entry": "https://www.hnrd.gov.cn/channel/16168.html",
        "list_urls": ["https://www.hnrd.gov.cn/channel/16168.html"],
        "level": "province",
    },
    "rd-sd": {
        "name": "山东省人大·法规草案征求意见",
        "entry": "http://www.sdrd.gov.cn",
        "list_urls": ["http://www.sdrd.gov.cn"],
        "level": "province",
    },
    "rd-js": {
        "name": "江苏省人大·法规草案征求意见",
        "entry": "https://www.jsrd.gov.cn/gzcy/fgzqyj/",
        "list_urls": ["https://www.jsrd.gov.cn/gzcy/fgzqyj/"],
        "level": "province",
    },
    "rd-gd": {
        "name": "广东省人大·法规草案征求意见",
        "entry": "https://www.gdpc.gov.cn/gdrdw/zyfb/fgyjzj/index.html",
        "list_urls": ["https://www.gdpc.gov.cn/gdrdw/zyfb/fgyjzj/index.html"],
        "level": "province",
    },
    # ---- 2026-10-10 第 3 轮扩面：探 27 个省级人大，挑出有「法规草案征求意见」栏目的 ----
    "rd-hb": {
        "name": "河北省人大·法规草案征求意见",
        "entry": "https://www.hbrd.gov.cn/lfgz/fgcazqyj/index.shtml",
        "list_urls": ["https://www.hbrd.gov.cn/lfgz/fgcazqyj/index.shtml"],
        "level": "province",
    },
    "rd-ln": {
        "name": "辽宁省人大·法规草案征求意见",
        # ⚠ 必须用 **http** —— 同路径 https 返回 404（实测：http 134721B / https 404）
        "entry": "http://www.lnrd.gov.cn/lnrd/gzcy/fgzqyj/index.shtml",
        "list_urls": ["http://www.lnrd.gov.cn/lnrd/gzcy/fgzqyj/index.shtml"],
        "level": "province",
    },
    "rd-jl": {
        "name": "吉林省人大·法规草案意见征集",
        "entry": "https://www.jlrd.gov.cn/gzjl/fgcayjzj/",
        "list_urls": ["https://www.jlrd.gov.cn/gzjl/fgcayjzj/"],
        "level": "province",
    },
    "rd-tj": {
        "name": "天津市人大·立法公开",
        "entry": "https://www.tjrd.gov.cn/lfjj/lfgs_2/index.shtml",
        "list_urls": ["https://www.tjrd.gov.cn/lfjj/lfgs_2/index.shtml"],
        "level": "province",
    },
}

SITE = SITES["rd-hn"]          # harvest.py 读这个；各 rd-* 模块覆盖它

_A_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S)
_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)


def _plain(html: str) -> str:
    t = _TAG_RE.sub(" ", html)
    t = re.sub(r"<br\s*/?>|</p>|</div>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _items(html: str, base: str) -> list[tuple[str, str]]:
    out = []
    for m in _A_RE.finditer(html):
        href, raw = m.group(1), m.group(2)
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()
        if len(title) < 6 or not any(k in title for k in ITEM_KW):
            continue
        # ★ 标题过滤：要「法规条目」，不要「栏目导航」。
        #   栏目名（「法规草案审议」「法规草案征求意见」）不长这样，必须滤掉。
        #   但**各省命名不统一**：
        #     · 湖南/山东：`关于《XX条例（草案）》公开征求意见的公告`（带《》）
        #     · **江苏**：`江苏省城市更新条例（草案）`（不带《》，用「（草案）」后缀）
        #   ⇒ 旧规则 `if "《" not in title: continue` 把江苏的条目**全滤掉了**（实测 0 条）。
        #   改成：带《》 **或** （含法规名词 + 含「草案」）。
        _DOC_KW = ("条例", "办法", "规定", "决定", "细则", "规则", "章程")
        if "《" not in title and not (any(k in title for k in _DOC_KW) and "草案" in title):
            continue
        if href.startswith("javascript:"):
            continue
        out.append((title, urljoin(base, href)))
    return out


def harvest_rd(fetch, *, site_key: str, limit: int | None = None,
               max_pages: int = 30) -> list[dict]:
    """抓某省人大的法规草案征求意见（标题 + 正文）。`site_key` ∈ SITES。"""
    site = SITES[site_key]
    out: list[dict] = []
    seen: set[str] = set()
    for list_url in site["list_urls"]:
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(list_url, headers={"User-Agent": UA, "Referer": site["entry"]})
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{site_key}] 列表失败 {type(e).__name__}（跳过）")
            continue
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{site_key}] 列表 HTTP {r.status_code}（跳过）")
            continue
        items = _items(r.text or "", list_url)
        print(f"    [{site_key}] {list_url[:56]} → {len(items)} 条")
        for title, url in items:
            if limit and len(out) >= limit:
                return out
            if url in seen:
                continue
            seen.add(url)
            time.sleep(PAUSE)
            try:
                d = fetch(url, headers={"User-Agent": UA, "Referer": list_url})
            except Exception as e:                                      # noqa: BLE001
                print(f"    [{site_key}] 详情 {url[:48]} {type(e).__name__}（跳过）")
                continue
            if getattr(d, "status_code", 0) != 200:
                continue
            body = _plain(d.text or "")
            # ★ 滤掉页面导航壳：含 NAV_MARK 的段落整段丢弃；
            #   再丢掉「短且含站点名」的段落（面包屑、栏目名）。
            paras = []
            for p in body.split("\n"):
                p = p.strip()
                if len(p) < 20:
                    continue
                if any(k in p for k in NAV_MARK):
                    continue
                if len(p) < 60 and ("人大网" in p or "人大" == p[:2]):
                    continue
                paras.append(p)
            if not paras:
                continue
            # ★ 去掉网页 <title> 的尾巴：形如「…公告_法规草案征求意见_湖南人大网」
            paras = [re.sub(r"_[^_]{0,20}人大网\s*$", "", p).strip() for p in paras]
            paras = [p for p in paras if len(p) >= 20]
            if not paras:
                continue
            content = "\n".join(paras)
            if len(content) < 100:
                continue
            out.append({
                "source": site_key,
                "id": re.sub(r"\W+", "_", url)[-48:],
                "url": url,
                "question": title,
                "answer": content,
                "asked_at": None,
                "answered_at": None,
                "dept": site["name"].split("·")[0],
                "channel": "人大·法规草案征求意见",
                "extra": {
                    "title": title,
                    "platform": urlparse(url).netloc,
                    "content_kind": "立法征求意见",     # ★ 与问答区分
                    "msg_type_norm": "征求意见",
                    "msg_type_source": "source_label",
                },
            })
    print(f"    [{site_key}] 收 {len(out)} 条")
    return out
