"""湖南统一互动平台（hd.hunan.gov.cn）验证：deptId + 答复覆盖率 + 状态分布。

发现的接口（湖南生态 hdjl_index.js 挖出，2026-10-07）：
  GET https://hd.hunan.gov.cn/communication/api-mailbox/frontMail/mailList2ie
      ?data={"pageNum":N,"pageSize":M,"sortMap":{"createTime":"desc"},
             "params":{"deptId":"<32位hex>", "phone":"","searchCode":"","status":"","siteNo":"","siteUrl":""}}
  → {"status":"success","data":{"total":…,"pageTotal":…,"rows":[…]}}
  rows 每行自带 title（问题）/ replyContent（答复 HTML）/ replyTime / createTime /
  deptName / objectiveType（咨询/投诉…）/ isPublish / status（已办结…）
  ⇒ **列表接口即全量，不必抓明细页**。

本脚本要回答的三件事：
  1. 湖南应急厅的 deptId（同平台，另一个部门）
  2. pageSize=50 时答复覆盖率如何（多少行 replyContent 非空）
  3. status 字段分布（是否需要按「已办结」过滤）
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
API = "https://hd.hunan.gov.cn/communication/api-mailbox/frontMail/mailList2ie"
DEPT_ST = "c0fc18f40e604da3a01460d02d731d45"      # 湖南省生态环境厅（hdjl_index.js）


def mail_list(cli, dept_id: str, page: int = 1, size: int = 50) -> dict:
    data = {"pageNum": page, "pageSize": size, "sortMap": {"createTime": "desc"},
            "params": {"deptId": dept_id, "phone": "", "searchCode": "",
                       "status": "", "siteNo": "", "siteUrl": ""}}
    r = cli.get(API, params={"data": json.dumps(data, ensure_ascii=False)})
    r.raise_for_status()
    return r.json().get("data") or {}


def main() -> int:
    import httpx

    out: dict = {"api": API, "depts": {}}
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True,
                      trust_env=False, timeout=25) as cli:
        # ① 湖南应急厅的 deptId
        r = cli.get("https://yjt.hunan.gov.cn/yjt/xhtml/js/hdjl_index.js")
        m = re.search(r'deptId\s*=\s*"([0-9a-f]{32})"', r.text)
        dept_yj = m.group(1) if m else None
        print(f"湖南应急 deptId = {dept_yj}")

        # ② + ③ 两个部门各取 2 页 × 50 条，统计答复覆盖率与状态分布
        for label, did in [("湖南省应急管理厅", dept_yj), ("湖南省生态环境厅", DEPT_ST)]:
            if not did:
                continue
            stat = {"deptId": did, "pages": []}
            all_rows: list[dict] = []
            for page in (1, 2):
                d = mail_list(cli, did, page=page, size=50)
                rows = d.get("rows") or []
                stat["pages"].append({"page": page, "total": d.get("total"),
                                      "pageTotal": d.get("pageTotal"),
                                      "rows": len(rows)})
                all_rows += rows
                time.sleep(1.5)
            answered = sum(1 for x in all_rows if (x.get("replyContent") or "").strip())
            pub = sum(1 for x in all_rows if x.get("isPublish") == 1)
            statuses: dict[str, int] = {}
            types: dict[str, int] = {}
            for x in all_rows:
                statuses[x.get("status") or "?"] = statuses.get(x.get("status") or "?", 0) + 1
                types[x.get("objectiveType") or "?"] = types.get(x.get("objectiveType") or "?", 0) + 1
            stat.update({"sampled": len(all_rows), "有答复": answered,
                         "isPublish": pub, "status分布": statuses, "类型分布": types})
            out["depts"][label] = stat
            print(f"[{label}] sampled={len(all_rows)} 有答复={answered} "
                  f"isPublish={pub} status={statuses} 类型={types}")

    path = HERE / "hunan-verify.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[hunan] 证据已写 {path}")
    return 0


if __name__ == "__main__":
    main()
