"""把「省级版块 fid 映射」补全到 31 个省：已扫描命中的标 confirmed，其余按规律标 inferred。

规律（2026-10-07 实扫 539~569 验证）：
  省级版块按**行政区划顺序两两编号**，`书记 fid = 539 + 2×序号`、`省长/市长/主席 fid = 书记 + 1`；
  已确认：北京 539/540 … 河南 569/570（570 未及确认）；据此推算至新疆 599/600。
⚠ inferred 的条目**用前必须实扫确认**（本脚本只做整理，不猜数据内容）。
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN = HERE / "liuyan-province-fid-scan.json"
OUT = HERE / "liuyan-province-fids.json"

#: 行政区划顺序（与留言板编号顺序一致，已由 539~569 实扫佐证）
ORDER = [
    "北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省",
    "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省",
    "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
    "重庆市", "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省",
    "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
]


def main() -> int:
    scan = json.loads(SCAN.read_text(encoding="utf-8")) if SCAN.exists() else []
    confirmed: dict[str, dict[str, str]] = {}
    for rec in scan:
        if rec.get("status") != 200 or not rec.get("p"):
            continue
        prov = rec["p"][0]
        forum = rec.get("forum") or ""
        slot = "secretary" if "书记" in forum else "governor"
        confirmed.setdefault(prov, {})[slot] = rec["fid"]

    out = []
    for i, prov in enumerate(ORDER):
        sec = str(539 + 2 * i)
        gov = str(540 + 2 * i)
        c = confirmed.get(prov, {})
        out.append({
            "province": prov,
            "secretary": c.get("secretary", sec),
            "governor": c.get("governor", gov),
            "confirmed": {"secretary": "secretary" in c, "governor": "governor" in c},
        })
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n_c = sum(1 for x in out if x["confirmed"]["secretary"] or x["confirmed"]["governor"])
    print(f"[province-fids] 省级单位 {len(out)} 个；已实扫确认 {n_c} 个；"
          f"其余为规律推算（用前需确认）")
    print("  已确认:", "、".join(x["province"] for x in out
                                if x["confirmed"]["secretary"] or x["confirmed"]["governor"]))
    print("  待确认:", "、".join(x["province"] for x in out
                                if not (x["confirmed"]["secretary"] or x["confirmed"]["governor"])))
    return 0


if __name__ == "__main__":
    main()
