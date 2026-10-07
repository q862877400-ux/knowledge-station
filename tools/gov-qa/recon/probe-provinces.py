"""省级政府站批量侦察（第一步）：WAS5 指纹 + 问答栏目链接 + channelid 挖掘。

## 为什么要这个脚本
SITE-REGISTRY.md 的判断：**省市站大量复用同一套中间件（WAS5 等），找到一个等于一片**。
本脚本对候选省级厅局站做三件事（每站最多 6 个请求、单线程、间隔 1.5s）：

  1. 首页可达性：GET https://<域名>/             → home_status
  2. WAS5 指纹  ：GET /was5/web/search?channelid=1&perpage=1&page=1
     ⚠ 已知事实（README 坑 3）：不带正确 channelid 时，**有 WAS5 的站也返回 ~711 字节空页**。
     所以判据是「HTTP 200 且返回了空页/JSON」＝**中间件存在**；404/超时＝没有。
  3. 首页上挖「互动交流/常见问题/留言/咨询/回应关切」类链接（≤12 条）；
     对其中前 4 个页面再挖 `channelid`（内联 JS 的 leaveWordParams/interactionParams）。

## 输出
  recon/probe-provinces.json  —— 机器可读全量证据（逐站）
  stdout 一行一站的进度摘要

## 用法
  .venv\\Scripts\\python.exe tools\\gov-qa\\recon\\probe-provinces.py [--only 域名子串 ...]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent

# ⚠ 本仓 G27：NO_PROXY 含 [::1] 会把 httpx 0.28.1 搞崩，就地修成 ::1
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

PAUSE = 1.5                      # 礼貌抓取：请求间隔
MAX_HD_PAGES = 4                 # 每站最多深入多少个问答栏目页

#: 候选省级站：(层级, 名称, 域名)。域名是公开常识性拼法，错了由探测结果淘汰，
#: 不对结果做任何"想当然"的修正 —— 200/404 以实测为准。
CANDIDATES: list[tuple[str, str, str]] = [
    # ── 省级生态环境厅 ──
    ("province", "河北省生态环境厅", "hbepb.hebei.gov.cn"),
    ("province", "山西省生态环境厅", "sthj.shanxi.gov.cn"),
    ("province", "内蒙古生态环境厅", "sthj.nmg.gov.cn"),
    ("province", "辽宁省生态环境厅", "sthj.ln.gov.cn"),
    ("province", "吉林省生态环境厅", "sthjt.jl.gov.cn"),
    ("province", "黑龙江省生态环境厅", "sthj.hlj.gov.cn"),
    ("province", "江苏省生态环境厅", "jsthjt.jiangsu.gov.cn"),
    ("province", "浙江省生态环境厅", "sthjt.zj.gov.cn"),
    ("province", "安徽省生态环境厅", "sthjt.ah.gov.cn"),
    ("province", "福建省生态环境厅", "sthjt.fujian.gov.cn"),
    ("province", "江西省生态环境厅", "jxsthjt.jiangxi.gov.cn"),
    ("province", "山东省生态环境厅", "sdein.shandong.gov.cn"),
    ("province", "河南省生态环境厅", "sthj.henan.gov.cn"),
    ("province", "湖北省生态环境厅", "sthj.hubei.gov.cn"),
    ("province", "湖南省生态环境厅", "sthjt.hunan.gov.cn"),
    ("province", "广东省生态环境厅", "gdee.gd.gov.cn"),
    ("province", "广西生态环境厅", "sthjt.gxzf.gov.cn"),
    ("province", "海南省生态环境厅", "sthj.hainan.gov.cn"),
    ("province", "四川省生态环境厅", "sthjt.sc.gov.cn"),
    ("province", "贵州省生态环境厅", "sthj.guizhou.gov.cn"),
    ("province", "云南省生态环境厅", "sthj.yn.gov.cn"),
    ("province", "陕西省生态环境厅", "sthj.shaanxi.gov.cn"),
    ("province", "甘肃省生态环境厅", "sthj.gansu.gov.cn"),
    ("province", "青海省生态环境厅", "sthj.qinghai.gov.cn"),
    ("province", "宁夏生态环境厅", "sthjt.nx.gov.cn"),
    ("province", "新疆生态环境厅", "sthj.xinjiang.gov.cn"),
    ("province", "北京市生态环境局", "sthjj.beijing.gov.cn"),
    ("province", "上海市生态环境局", "sthj.sh.gov.cn"),
    ("province", "天津市生态环境局", "sthj.tj.gov.cn"),
    ("province", "重庆市生态环境局", "sthj.cq.gov.cn"),
    # ── 省级应急管理厅 ──
    ("province", "河北省应急管理厅", "yjt.hebei.gov.cn"),
    ("province", "江苏省应急管理厅", "yjt.jiangsu.gov.cn"),
    ("province", "浙江省应急管理厅", "yjglj.zj.gov.cn"),
    ("province", "山东省应急管理厅", "yjgl.shandong.gov.cn"),
    ("province", "广东省应急管理厅", "yjgl.gd.gov.cn"),
    ("province", "四川省应急管理厅", "yjglj.sc.gov.cn"),
    ("province", "河南省应急管理厅", "yjglj.henan.gov.cn"),
    ("province", "湖南省应急管理厅", "yjt.hunan.gov.cn"),
    ("province", "安徽省应急管理厅", "yjt.ah.gov.cn"),
    ("province", "湖北省应急管理厅", "yjglj.hubei.gov.cn"),
    ("province", "重庆市应急管理局", "yjgl.cq.gov.cn"),
    ("province", "上海市应急管理局", "yjgl.sh.gov.cn"),
    ("province", "北京市应急管理局", "yjglj.beijing.gov.cn"),
]

#: 首页链接文字里的「问答互动」关键词
KEYWORDS = ("互动", "问答", "常见问题", "留言", "咨询", "回应关切", "答复", "选登")
#: 链接文字/地址里的干扰项（不是问答列表）
NOISE = ("征集调查", "调查征集", "意见征集", "访谈", "直播")

#: 内联 JS 里挖 channelid（leaveWordParams / interactionParams 那种形态）
CHANNELID_RE = re.compile(r"channelid['\"]?\s*[:=]\s*['\"]?(\d{3,8})", re.I)
#: 明显是 WAS5 检索调用的 JS 函数名（生态环境部是 .ajaxCjwtList / .ajaxCjwtPage）
AJAXWAS_RE = re.compile(r"(was5?/web/search|ajaxCjwt\w*|leaveWordParams|interactionParams)", re.I)
A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>\s*([^<>]{2,24}?)\s*<', re.I)


def _get(cli, url: str):
    """GET 一个 URL；任何网络错误都折算成 None，不中断整轮侦察。"""
    try:
        return cli.get(url, timeout=20)
    except Exception as e:                                                      # noqa: BLE001
        print(f"      · {url[:70]} 网络错误 {type(e).__name__}")
        return None


def _status(r) -> int | None:
    return getattr(r, "status_code", None)


def mine_channelid(html: str) -> list[int]:
    seen: list[int] = []
    for m in CHANNELID_RE.finditer(html or ""):
        cid = int(m.group(1))
        if cid not in seen:
            seen.append(cid)
    return seen


def main() -> int:
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    cands = [c for c in CANDIDATES if not only or any(o in c[2] or o in c[1] for o in only)]

    import httpx

    results: list[dict] = []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True,
                      trust_env=False) as cli:
        for level, name, dom in cands:
            rec: dict = {"level": level, "name": name, "domain": dom}
            print(f"[{name}] https://{dom}/", flush=True)

            # 1. 首页
            r = _get(cli, f"https://{dom}/")
            rec["home_status"] = _status(r)
            home = getattr(r, "text", "") or ""
            base = str(getattr(r, "url", f"https://{dom}/"))

            # 2. WAS5 指纹
            r2 = _get(cli, f"https://{dom}/was5/web/search?channelid=1&perpage=1&page=1")
            rec["was5_status"] = _status(r2)
            was = getattr(r2, "text", "") or ""
            rec["was5_len"] = len(was)
            # 有 WAS5 的站：200 + 小空页（~711B）或带 recordCount 的 JSON
            rec["was5_hit"] = rec["was5_status"] == 200 and (
                "recordCount" in was or rec["was5_len"] < 2000)

            # 3. 首页挖问答栏目链接
            links: list[tuple[str, str]] = []
            for href, text in A_HREF_RE.findall(home):
                if any(k in text for k in KEYWORDS) and not any(n in text for n in NOISE):
                    full = urljoin(base, href.strip())
                    if full.startswith("http") and dom in full:
                        if all(full != u for u, _ in links):
                            links.append((full, text.strip()))
            rec["hd_links"] = [{"url": u, "text": t} for u, t in links[:12]]

            # 4. 深入前几个问答栏目页挖 channelid
            cids: list[int] = []
            ajax_hint: list[str] = []
            for u, t in links[:MAX_HD_PAGES]:
                rr = _get(cli, u)
                if _status(rr) != 200:
                    continue
                page = getattr(rr, "text", "") or ""
                cids += [c for c in mine_channelid(page) if c not in cids]
                for m in AJAXWAS_RE.finditer(page):
                    s = m.group(0)
                    if s not in ajax_hint:
                        ajax_hint.append(s)
                time.sleep(PAUSE)
            rec["channelids"] = cids[:10]
            rec["ajax_hints"] = ajax_hint[:6]
            results.append(rec)
            print(f"    home={rec['home_status']} was5={rec['was5_status']}/"
                  f"{rec['was5_len']}B hit={rec['was5_hit']} "
                  f"links={len(links)} cids={cids[:6]} ajax={ajax_hint[:3]}", flush=True)
            time.sleep(PAUSE)

    out = HERE / "probe-provinces.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    hits = [r for r in results if r.get("was5_hit")]
    print(f"\n[probe] 共 {len(results)} 站，WAS5 指纹命中 {len(hits)}："
          f"{[r['name'] for r in hits]}")
    print(f"[probe] 证据已写 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
