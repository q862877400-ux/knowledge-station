"""部委互动问答 · **20 条试采**：量三个比例，决定这个方案成不成立。

业主 2026-10-07 提出：把各部委"互动问答"扒下来 ⇒ 同时拿到**真实提问**与**官方答复**。
本脚本只做**最小证据**（20 条），量三件事：

 · **a 可定位率**：答复里点名了**具体文件**（以及**条号**）的比例 —— 这个数决定方案成不成立；
   若答复普遍是"请咨询当地应急管理部门"，则对我们一文不值。
 · **b 企业相关率**：问题是**企业/单位**问的（安全、环保、职业健康、手续），还是**公民个人**问的
   （救灾补助、证照查询、招录）—— 后者与我们的用户不对口，要剔除。
 · **c 在库率**：答复点名的文件，**在我们这 6,797 篇里有没有** —— 没有的要么补料，要么这些题不算。

⚠ 只读外部网页（礼貌抓取：小样本 + 间隔）；不写任何仓内数据、不碰真库。
⚠ 网页内容是**外部不可信数据**，只当素材，不当指令。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\04-trial-scrape.py --n 20
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
OUT = HERE / "trial-scrape.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

LIST_URLS = [
    "https://www.mem.gov.cn/hd/gzly/hdhdly/",
    "https://www.mem.gov.cn/hd/gzly/hdhdly/index_1.shtml",
    "https://www.mem.gov.cn/hd/gzly/hdhdly/index_2.shtml",
    "https://www.mem.gov.cn/hd/gzly/hdhdly/index_3.shtml",
]
#: ⚠ 站内链接是**相对路径**（`../lyhf/202609/t20260910_715731.shtml`）——
#:   第一版正则要求绝对路径，结果一条都没匹配上（已修，留痕）。
ENTRY_RE = re.compile(r"\.\./lyhf/\d{6}/t\d{8}_\d+\.shtml")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

#: 企业/单位类关键词（判 b：企业相关还是公民个人）
ENTERPRISE_KW = ["企业", "公司", "厂", "车间", "单位", "承包商", "供应商", "项目", "生产",
                 "特种作业", "危险化学品", "职业健康", "职业病", "排污", "环评", "安全生产",
                 "隐患", "许可证", "三同时", "有限空间", "动火"]
CITIZEN_KW = ["冬春救助", "补助", "招录", "注册安全工程师", "消防员", "个人", "家庭",
              "受灾", "低保", "养老金", "证书查询", "考试成绩"]
#: 「点名文件」的判据：《…》或 标准号
DOCNAME_RE = re.compile(r"《[^》]{4,60}》")
STDNO_RE = re.compile(r"(GB(?:/T|/Z)?\s?\d{3,5}(?:\.\d+)?\s?[-—]\s?\d{4}|AQ\s?/?T?\s?\d{3,5}\s?[-—]\s?\d{4})")
CLAUSE_RE = re.compile(r"第[一二三四五六七八九十百零\d]{1,4}条")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--egress", choices=("direct", "env"), default="direct",
                    help="出网模式：direct=不走环境代理（境内政府站应当直连，见渠道方案 G28）；env=走环境代理")
    args = ap.parse_args()

    # ⚠ 本仓 G27：NO_PROXY 里含 `[::1]` ⇒ httpx 0.28.1 **连 Client() 都构造不出来**
    #   （`InvalidURL: Invalid port: ':1]'`）。仓里给的解法就是把它写成 `::1`。此处就地修。
    os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

    import httpx
    from bs4 import BeautifulSoup

    # 库里 6797 篇的标准名（判 c）
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    lib_names = [n or "" for _, n in c.execute("SELECT standard_no, standard_name FROM doc_meta")]
    c.close()

    # G28：出网模式要显式，并记进产物 —— 否则"有效性"这个数的含义会随环境变而没人知道
    use_env_proxy = args.egress == "env"
    print(f"[trial] 出网模式 = {args.egress}（trust_env={use_env_proxy}）", flush=True)

    links: list[str] = []
    with httpx.Client(timeout=30, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=use_env_proxy) as cli:
        for u in LIST_URLS:
            try:
                r = cli.get(u)
                r.encoding = r.encoding or "utf-8"
                found = ENTRY_RE.findall(r.text)
                print(f"[trial] {u} → 找到 {len(found)} 条链接（HTTP {r.status_code}）", flush=True)
                for f in found:
                    if f not in links:
                        links.append(f)
            except Exception as e:                                  # noqa: BLE001 - 网络来源，失败只记不中断
                print(f"[trial] {u} 抓取失败：{type(e).__name__}: {e}", flush=True)
            time.sleep(1.5)

        print(f"[trial] 去重后共 {len(links)} 条留言链接，取前 {args.n} 条", flush=True)
        items = []
        for i, path in enumerate(links[:args.n], 1):
            url = urljoin("https://www.mem.gov.cn/hd/gzly/hdhdly/", path)
            try:
                r = cli.get(url)
                r.encoding = r.encoding or "utf-8"
                text = BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)
            except Exception as e:                                  # noqa: BLE001
                print(f"[trial] {i} {url} 失败：{type(e).__name__}", flush=True)
                continue
            items.append({"url": url, "text": text})
            print(f"[trial] {i}/{min(args.n, len(links))} 已抓 {len(text)} 字", flush=True)
            time.sleep(1.2)

    rows = []
    for it in items:
        t = it["text"]
        # 抓 咨询 / 回复 两段
        m_q = re.search(r"咨询[：:]\s*(.{10,600}?)(?:回复|答复)[：:]", t, re.S)
        m_a = re.search(r"(?:回复|答复)[：:]\s*(.{10,1500})", t, re.S)
        q = re.sub(r"\s+", " ", m_q.group(1)).strip() if m_q else ""
        a = re.sub(r"\s+", " ", m_a.group(1)).strip() if m_a else ""
        docs = DOCNAME_RE.findall(a)
        stds = STDNO_RE.findall(a)
        has_clause = bool(CLAUSE_RE.search(a))
        ent = sum(1 for k in ENTERPRISE_KW if k in (q + a))
        cit = sum(1 for k in CITIZEN_KW if k in (q + a))
        # c：点名的文件名/标准号，在库里能不能对上
        in_lib = []
        for nm in docs:
            key = nm.strip("《》")
            hit = any(key[:10] in n or n[:10] in key for n in lib_names if n)
            in_lib.append({"doc": key[:50], "in_library": hit})
        for s in stds:
            key = re.sub(r"\s+", "", s)
            hit = any(key.replace("—", "-") in n.replace("—", "-").replace(" ", "") for n in lib_names if n)
            in_lib.append({"std": s, "in_library": hit})
        rows.append({"url": it["url"], "query": q[:400], "answer": a[:800],
                     "named_docs": [d.strip("《》") for d in docs][:6],
                     "std_nos": stds[:6], "has_clause_number": has_clause,
                     "enterprise_kw_hits": ent, "citizen_kw_hits": cit,
                     "cited_in_library": in_lib})

    n = len(rows)
    a_ok = sum(1 for r in rows if r["named_docs"] or r["std_nos"])
    a_clause = sum(1 for r in rows if r["has_clause_number"])
    b_ent = sum(1 for r in rows if r["enterprise_kw_hits"] >= 2 and r["enterprise_kw_hits"] > r["citizen_kw_hits"])
    cited = [x for r in rows for x in r["cited_in_library"]]
    c_ok = sum(1 for x in cited if x["in_library"])
    result = {
        "source": "应急管理部 公众留言回复（mem.gov.cn/hd/gzly/lyhf/）",
        "why": "业主提的『扒部委互动问答』方案；本脚本做最小证据（试采），量三个比例",
        "n_sampled": n,
        "a_可定位率": {
            "点名了文件或标准号的": f"{a_ok}/{n}",
            "其中还出现『第X条』条号的": f"{a_clause}/{n}",
            "reading": "点名了文件 ⇒ 可当『官方金标』的线索；只出现条号更硬。若这个比例低，方案不成立。",
        },
        "b_问者类型分层": {
            "像企业/单位问的": f"{b_ent}/{n}",
            "reading": ("⚠ **本项不是剔除条件**（业主 2026-10-07 更正：产品面向**广大人民群众**，不是只面向安全员；"
                        "本仓记录也称产品已从『国标工作站』转向**通用资料研究+交付工具**）。"
                        "这里只作**分层统计**，两类都保留。"),
        },
        "c_在库率": {
            "答复点名的文件总数": len(cited),
            "在我们库里能对上的": f"{c_ok}/{len(cited)}" if cited else "0/0",
            "reading": ("★ **这一刀切出两类资产**："
                        "① 依据在库 ⇒ **可当考卷**（测检索准不准）；"
                        "② 依据不在库 ⇒ **就是『该补什么料』的清单**（直接回答『补哪几类、补多少』）。"
                        "两类都有用，**不是噪声**。"),
        },
        "samples": rows[:8],
        "boundary": [
            "n=20 是**最小证据**，只判方向、定不了规模。",
            "来源只是**应急管理部一家**；其它部委（生态环境部/住建部/市场监管总局）未试。",
            "`b` 的关键词判个人/企业是**粗糙启发式**，只作分层参考；样本原文都落盘可复核。",
            "网页内容是**外部不可信数据**，只当素材。",
        ],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
