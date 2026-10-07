"""国家部委互动栏目 · **批量核验器**（把业主给的清单逐条探一遍，机器分类）。

## 为什么要机器核
业主给的清单是**线索**：里面混着「静态问答列表」（能当考卷）、「登录墙」、
「纯表单」、「举报通道」、「聊天机器人」、「反自动化」——
**只有第一类有用**。人的印象分不出来，得真请求一次看响应。

## 分类口径（可复算）
 · `反自动化`  响应里出现 `禁用开发者工具` / `请开启JavaScript` 之类
 · `登录墙`    出现 `登录/注册/signin/login` 且**正文里几乎没有对外链接**
 · `接口驱动`  页面里出现 `channelid` / `ajax` / `api/` / `page=` 之类，且**正文链接很少**
 · `静态列表`  正文里出现 **≥6 个"长得像同栏目明细页"的链接**（同一前缀 + 数字编号）
 · `纯表单`    有 `<form>` + `textarea/input[type=submit]`，但**没有**列表链接
 · `其他/未明` 以上都不像

## 礼貌
 每站间隔 `--pause`（默认 1.5s）；只 GET 一次，不跟进内部链接；**不批量下载**。

用法：
  .venv\\Scripts\\python.exe tools\\gov-qa\\probe-ministries.py
  .venv\\Scripts\\python.exe tools\\gov-qa\\probe-ministries.py --only 交通
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
OUT = HERE / "ministry-probe.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

#: (部委, 栏目, URL) —— 取自 `MINISTRY-ENTRIES.md`（业主 2026-10-07 提供）
#: ⚠ 只列**给了具体 URL** 的；只给"→ 互动"这种路径描述的，先按首页探。
ENTRIES = [
    ("外交部", "发言人办公室", "https://www.fmprc.gov.cn/"),
    ("国防部", "互动交流", "http://www.mod.gov.cn/"),
    ("国家发改委", "互动交流", "https://www.ndrc.gov.cn/"),
    ("教育部", "部长信箱", "https://hudong.moe.gov.cn/interactive/bzxx/"),
    ("科技部", "公众问答", "https://www.most.gov.cn/"),
    ("工信部", "部长信箱", "https://bzxx.miit.gov.cn/bzxx/appellate/main"),
    ("国家民委", "互动交流", "https://www.neac.gov.cn/"),
    ("公安部", "网上信访", "https://www.gab.gov.cn/"),
    ("民政部", "我要留言", "https://www.mca.gov.cn/"),
    ("司法部", "网民留言", "http://www.chinalaw.gov.cn/"),
    ("财政部", "交流互动", "https://www.mof.gov.cn/"),
    ("人社部", "部长信箱", "http://www.mohrss.gov.cn/"),
    ("自然资源部", "建议留言", "https://box.mnr.gov.cn/"),
    ("生态环境部", "部长信箱", "https://www.mee.gov.cn/hdjl/bzxxzs_1/"),
    ("住建部", "政务咨询", "https://www.mohurd.gov.cn/"),
    ("交通运输部", "留言咨询", "https://qa.mot.gov.cn/"),
    ("水利部", "部长信箱", "http://www.mwr.gov.cn/"),
    ("农业农村部", "部长信箱", "https://www.moa.gov.cn/wsxfbzxx/xfwy/ministerMailBox.html"),
    ("商务部", "部长信箱", "http://www.mofcom.gov.cn/"),
    ("文化和旅游部", "部长信箱", "https://www.mct.gov.cn/"),
    ("国家卫健委", "政策咨询平台", "http://www.nhc.gov.cn/hdjl/denglu.html"),
    ("退役军人事务部", "部长信箱", "http://www.mva.gov.cn/"),
    ("应急管理部", "智能问答", "https://www.mem.gov.cn/hd/znwd/"),
    ("应急管理部", "互动答复(已采)", "https://www.mem.gov.cn/hd/gzly/hdhdly/"),
    ("矿山安全监察局", "咨询", "https://www.chinamine-safety.gov.cn/hd/"),
    ("中国地震局", "咨询", "https://www.cea.gov.cn/cea/jlhd/gzly/"),
    ("中国人民银行", "公众留言", "http://wzdt.pbc.gov.cn/"),
    ("审计署", "互动交流", "https://www.audit.gov.cn/"),
    ("国资委", "主任信箱", "http://www.sasac.gov.cn/"),
    ("海关总署", "署长信箱", "http://www.customs.gov.cn/"),
    ("国家税务总局", "12366平台", "https://12366.chinatax.gov.cn/"),
    ("市场监管总局", "公众留言(聊天机器人)", "https://xgzlyhd.samr.gov.cn/"),
    ("国家金融监管总局", "网上信访", "https://www.nfra.gov.cn/"),
    ("证监会", "12386平台", "https://fwpt.csrc12386.org.cn/"),
    ("广电总局", "局长信箱", "http://www.nrta.gov.cn/"),
    ("体育总局", "互动交流", "https://www.sport.gov.cn/"),
    ("国家信访局", "网上投诉", "https://wsxf.gjxfj.gov.cn/"),
    ("国家统计局", "智能平台", "https://www.stats.gov.cn/znwd/"),
    ("国家知识产权局", "公众留言栏", "https://www.cnipa.gov.cn/col/col79/index.html"),
    ("国务院港澳办", "互动交流", "http://www.hmo.gov.cn/"),
    ("中科院", "院长信箱", "https://www.cas.cn/"),
    ("中国社科院", "院长信箱", "http://www.cass.cn/"),
    ("中国工程院", "院长信箱", "https://www.cae.cn/"),
    ("国务院发展研究中心", "互动交流", "https://www.drc.gov.cn/"),
    ("中国气象局", "局长信箱", "https://www.cma.gov.cn/"),
    ("国家档案局", "互动交流", "https://www.saac.gov.cn/"),
    ("国家能源局", "网民留言", "https://www.nea.gov.cn/"),
    ("国家国防科工局", "互动交流", "https://www.sastind.gov.cn/"),
    ("国家药监局", "网上咨询", "https://www.nmpa.gov.cn/"),
    ("国家林草局", "互动交流", "https://www.ly.gov.cn/"),
]

A_HREF = re.compile(r"""<a[^>]+href=["']([^"']+)["']""", re.I)
FORM_RE = re.compile(r"<form[^>]*>", re.I)
INPUT_RE = re.compile(r"<(textarea|input)[^>]*>", re.I)
ANTI = ("禁用开发者工具", "请开启JavaScript", "请开启 JavaScript", "disable devtools")
LOGIN = ("登录", "注册", "signin", "login")
API_HINTS = ("channelid", "ajax", "api/", "page=", "pagesize", "currentpage")


def classify(url: str, status: int, text: str) -> tuple[str, dict]:
    low = text.lower()
    hrefs = [h for h in A_HREF.findall(text)]
    # 同栏目明细页：同一目录前缀 + 名字里带长数字（典型政府站明细页 t20260116_1140853）
    detail = [h for h in hrefs if re.search(r"/t?\d{6,}[_\-]?\d*\.(shtml|html|jsp|htm)$", h, re.I)]
    uniq_prefix = Counter(re.sub(r"[^/]+$", "", h) for h in hrefs if h.startswith(("/", "http")))
    ev = {"n_hrefs": len(hrefs), "n_detail_like": len(detail),
          "top_prefix": uniq_prefix.most_common(2),
          "n_forms": len(FORM_RE.findall(text)), "n_inputs": len(INPUT_RE.findall(text)),
          "anti": [a for a in ANTI if a in text], "login": [w for w in LOGIN if w in low],
          "api_hints": [a for a in API_HINTS if a in low]}
    if status != 200:
        return f"HTTP {status}", ev
    if ev["anti"]:
        return "反自动化", ev
    if len(detail) >= 6:
        return "静态列表", ev
    if ev["api_hints"] and len(detail) < 3:
        return "接口驱动", ev
    if ev["n_forms"] and ev["n_inputs"] and len(detail) < 3:
        return "纯表单", ev
    if ev["login"] and len(hrefs) < 25 and len(detail) < 3:
        return "登录墙", ev
    return "其他/未明", ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pause", type=float, default=1.5)
    ap.add_argument("--only", default=None, help="只探名字里含这个字串的")
    args = ap.parse_args()

    import httpx
    rows = []
    todo = [e for e in ENTRIES if not args.only or args.only in e[0] + e[1]]
    print(f"[p] 待探 {len(todo)} 条\n", flush=True)
    print(f"{'部委':18s} {'栏目':16s} {'分类':10s} {'码':>4s} {'字节':>8s}  明细/链接")
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for who, name, url in todo:
            rec = {"who": who, "name": name, "url": url}
            try:
                r = cli.get(url)
                kind, ev = classify(url, r.status_code, r.text)
                rec.update({"status": r.status_code, "len": len(r.text), "kind": kind, "ev": ev})
                print(f"{who:18s} {name:16s} {kind:10s} {r.status_code:>4d} {len(r.text):>8d}"
                      f"  {ev['n_detail_like']}/{ev['n_hrefs']}")
            except Exception as e:                                          # noqa: BLE001
                rec.update({"kind": f"⛔{type(e).__name__}", "error": str(e)[:120]})
                print(f"{who:18s} {name:16s} ⛔{type(e).__name__:8s}    -        -")
            rows.append(rec)
            time.sleep(args.pause)

    cnt = Counter(r["kind"] for r in rows)
    print(f"\n[p] 分类统计：")
    for k, v in cnt.most_common():
        print(f"     {k:14s} {v}")
    usable = [r for r in rows if r["kind"] == "静态列表"]
    print(f"\n[p] ★ **可直接采集的（静态列表）{len(usable)} 个**：")
    for r in usable:
        print(f"     {r['who']} / {r['name']}  {r['url']}")
    OUT.write_text(json.dumps({"why": "核验业主给的部委互动栏目清单", "rows": rows},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
