"""城市门户 IGI **可采性 + id 重叠** 只读探针（2026-10-09 第 7 轮新增）。

## 为什么需要它
`recon/igi-siteid-scan.py` 只证明了「列表接口对该 siteId 返回 totalResults>0」，
**不等于能采**（第 6 轮实测：贵州门户 11 个 siteId 里 6 个列表接口 404）。
接入城市门户前必须实测两件事：
1. **可采性**：列表接口真返行、`metadataId` 存在、明细接口能取到答复正文；
2. **重叠**：这些 id 是否已存在于省级门户适配器（如 `gx-igi` / `nmg-igi`）
   —— 同一条信件两个 source 会**记两遍**。

## 用法
  .venv/Scripts/python.exe tools/gov-qa/recon/igi-city-probe.py nanning shenyang nanjing baotou
只读：不落盘语料，只在 stdout 打结论。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.5

LIST = ("{base}/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
        "&siteId={sid}&order=1&appId=&pageIndex=1&pageSize={n}")
DETAIL = ("{base}/IGI/nbhd/openGovmsgbox.do?method=viewGovmsgbox"
          "&siteId={sid}&metadataId={mid}")

#: tag → (base, referer, 待测 siteId 列表, 可能重叠的省级适配器 key)
TARGETS: dict[str, tuple[str, str, list[str], list[str]]] = {
    "nanning":  ("https://www.nanning.gov.cn",  "https://www.nanning.gov.cn/",  ["8"],                  ["gx-igi", "gx-mailbox"]),
    "shenyang": ("https://www.shenyang.gov.cn", "https://www.shenyang.gov.cn/", ["123", "118"],         []),
    "nanjing":  ("https://www.nanjing.gov.cn",  "https://www.nanjing.gov.cn/",  ["126", "130"],         []),
    "baotou":   ("https://www.baotou.gov.cn",   "https://www.baotou.gov.cn/",   ["46", "57"],           ["nmg-igi"]),
    "guiyang":  ("https://www.guiyang.gov.cn",  "https://www.guiyang.gov.cn/",  ["70"],                 ["gz-igi"]),
    "yinchuan": ("https://www.yinchuan.gov.cn", "https://www.yinchuan.gov.cn/", ["259"],                ["nx-igi"]),
    # 2026-10-09 第 9 轮追加：天津 `tj.gov.cn` IGI（siteId=186 = 123,546 / 215 = 16,785，
    # 见 scan-tianjin.log）。**接入前必须先验与 tj-enorth / tj-hdjl 的 id 重叠**
    # —— 同一封信两个 source 会记两遍。所以这里 peer_keys 传了那两个已落盘源。
    "tianjin":  ("https://www.tj.gov.cn",       "https://www.tj.gov.cn/",       ["186", "215"],         ["tj-enorth", "tj-hdjl"]),
}


def _existing(keys: list[str]) -> set[str]:
    ids: set[str] = set()
    for k in keys:
        for p in DATA.glob(f"{k}-*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    v = str(json.loads(line).get("id") or "").strip()
                    if v:
                        ids.add(v)
    return ids


def main() -> int:
    tags = sys.argv[1:] or list(TARGETS)
    for tag in tags:
        if tag not in TARGETS:
            print(f"[{tag}] 未知 tag，跳过")
            continue
        base, referer, sids, peer_keys = TARGETS[tag]
        peer = _existing(peer_keys) if peer_keys else set()
        with httpx.Client(timeout=40, headers={"User-Agent": UA}, follow_redirects=True,
                          trust_env=False, verify=False) as cli:
            for sid in sids:
                try:
                    r = cli.get(LIST.format(base=base, sid=sid, n=5),
                                headers={"Referer": referer})
                    code = r.status_code
                    j = r.json() if code == 200 else {}
                except Exception as e:                                       # noqa: BLE001
                    print(f"[{tag}] siteId={sid} 列表异常 {type(e).__name__}: {e}")
                    time.sleep(PAUSE)
                    continue
                datas = (j or {}).get("datas") or {}
                pi = datas.get("pageInfo") or {}
                rows = datas.get("list") or datas.get("rows") or datas.get("data") or []
                total = pi.get("totalResults")
                print(f"[{tag}] siteId={sid} HTTP {code} total={total} 本页行数={len(rows)}")
                if rows:
                    print("   首行键:", sorted(rows[0].keys()))
                hit = 0
                for row in rows[:5]:
                    # ⚠ 列表行是**大写键**（METADATAID/TITLE/PROVINCE…），不是小写驼峰。
                    mid = str(row.get("METADATAID") or row.get("metadataId")
                              or row.get("id") or "").strip()
                    if not mid:
                        continue
                    if mid in peer:
                        hit += 1
                    # 明细可达性：只测第一条，避免刷站
                    if row is rows[0]:
                        try:
                            d = cli.get(DETAIL.format(base=base, sid=sid, mid=mid),
                                        headers={"Referer": referer})
                            dj = d.json() if d.status_code == 200 else {}
                            dd = (dj or {}).get("datas") or {}
                            # ⚠ 答复正文在 `datas.REPLYS[].REPLYHTMLCONTENT`（与
                            #   `_igi_common.harvest_igi` 同路径）；别猜 replyContent/answer。
                            replies = dd.get("REPLYS") or []
                            body = "".join(str((x or {}).get("REPLYHTMLCONTENT") or "")
                                           for x in replies)
                            print(f"   明细 id={mid} HTTP {d.status_code} "
                                  f"REPLYS={len(replies)} 答复正文长度={len(body)}")
                            print(f"   地域 PROVINCE={row.get('PROVINCE')!r} "
                                  f"CITY={row.get('CITY')!r} AREA={row.get('AREA')!r}")
                        except Exception as e:                               # noqa: BLE001
                            print(f"   明细异常 {type(e).__name__}: {e}")
                        time.sleep(PAUSE)
                if peer:
                    print(f"   与 {peer_keys} 的 id 重叠（本页 5 条中）: {hit}")
                time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
