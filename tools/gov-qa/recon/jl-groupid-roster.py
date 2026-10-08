"""IGI 吉林：扫 groupId 出一张「厅局花名册」（groupId → 厅局名 + 信件总数）。

## 为什么
交接 §4.2 说「IGI 还有大量厅局没探」。第二批用「猜域名」的办法：大量 ConnectError、
很多站首页没有 IGI 指纹。而吉林的规律是 **base=`haiyun.jl.gov.cn/IGI` +
`(siteId=117, appId=96)` 全省固定，只有 `groupId` 区分厅局** —— 所以**扫一个整数维度**
就能枚举全省厅局，完全不依赖各厅局域名是否可达。

## 两个已实测的关键事实（本脚本步骤 0 会复验）
1. **`groupId` 确实是厅局选择器**：`groupId=159` 只回「吉林省交通运输厅」、
   `160` 只回「吉林省广播电视局」、`170` 人社厅、`172` 生态环境厅、`178` 卫健委；
   而**不带 `groupId`** 回的是**全厅混合池**（别拿它当"全量"，会和分组重复）。
2. **`Referer` 不要求匹配站点**：拿人社的页面当 Referer 请求 159/172/178 全部 200
   ⇒ 扫 groupId 不需要知道新厅局的域名。

## 便宜在哪
列表接口回 `datas.pageInfo.totalResults` ⇒ **一个 groupId 一次请求**（pageSize=1）
就能拿到「该厅局共多少封信」，不必翻页。

用法：
  python recon/jl-groupid-roster.py                # 默认扫 100..300
  python recon/jl-groupid-roster.py 140 200        # 指定区间
输出：`recon/jl-groupid-roster.txt`（每行：groupId · 总数 · 厅局名）
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

BASE = "https://haiyun.jl.gov.cn/IGI"
SITE_ID = "117"
APP_ID = "96"
REFERER = "https://hrss.jl.gov.cn/"          # 已知：不必匹配目标厅局
PAUSE = 1.2
#: 已落适配器的 groupId（花名册里标 ★已接）
ADOPTED = {"159": "jl-jt", "170": "jl-hrss", "172": "jl-st", "178": "jl-wjw"}


def url(gid: str | None) -> str:
    u = (f"{BASE}/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
         f"&siteId={SITE_ID}&order=1&appId={APP_ID}")
    if gid:
        u += f"&groupId={gid}"
    return u + "&pageIndex=1&pageSize=1"


def main() -> int:
    import httpx

    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    out = HERE / "jl-groupid-roster.txt"

    rows: list[tuple[str, int, str]] = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=12,
                      follow_redirects=True) as c:
        with out.open("w", encoding="utf-8") as f:
            f.write(f"# IGI 吉林 groupId 花名册：{lo}..{hi}\n")
            f.write(f"# base={BASE} siteId={SITE_ID} appId={APP_ID} Referer={REFERER}\n\n")

            # ── 步骤 0：复验「groupId 是厅局选择器」+「Referer 不需匹配」──
            f.write("## 步骤0 · 复验（不带 groupId 是混合池；带 groupId 是单厅）\n")
            for gid in [None, "159", "170", "172", "178"]:
                r = c.get(url(gid), headers={"Referer": REFERER})
                d = (r.json().get("datas") or {})
                data = d.get("data") or []
                tot = (d.get("pageInfo") or {}).get("totalResults")
                dept = (data[0].get("REPLYDEPT") if data else None) or "(混合/无)"
                f.write(f"  groupId={str(gid):>4} → HTTP {r.status_code} "
                        f"total={tot} dept={dept}\n")
                time.sleep(PAUSE)
            f.write("\n## 步骤1 · 逐 groupId 花名册\n")

            for gid in range(lo, hi + 1):
                g = str(gid)
                try:
                    r = c.get(url(g), headers={"Referer": REFERER})
                    d = (r.json().get("datas") or {})
                    data = d.get("data") or []
                    tot = (d.get("pageInfo") or {}).get("totalResults") or 0
                except Exception as e:                                  # noqa: BLE001
                    f.write(f"  {gid}\t-1\t{type(e).__name__}\n")
                    time.sleep(PAUSE)
                    continue
                if tot:
                    dept = (data[0].get("REPLYDEPT") if data else "") or "(无答复部门)"
                    tag = f"  ★已接({ADOPTED[g]})" if g in ADOPTED else ""
                    f.write(f"  {gid}\t{tot}\t{dept}{tag}\n")
                    rows.append((g, tot, dept))
                time.sleep(PAUSE)

            f.write(f"\n## 有数据的 groupId 共 {len(rows)} 个；"
                    f"信件总数 {sum(r[1] for r in rows)}\n")
            new = [r for r in rows if r[0] not in ADOPTED]
            f.write(f"## 其中未接的 {len(new)} 个，合计 {sum(r[1] for r in new)} 封\n")

    print(f"花名册完成：{len(rows)} 个厅局 → {out.name}")
    for g, t, d in sorted(rows, key=lambda x: -x[1])[:20]:
        print(f"  {g:>4} {t:>5}  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
