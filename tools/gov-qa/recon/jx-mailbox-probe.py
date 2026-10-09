"""江西数融站群 —— 信箱接口 `/api/mail/list` 打通探测（2026-10-09）。

背景：§12.5 的未决问题 —— 省直部门站多把公众问答收在各自的信箱系统
（`/api/mail/list`），2026-10-08 只试过**省政府站**的参数（返 0）。

本脚本做三件事（只探测、只打印，落 `recon/jx-mailbox-probe.json`，不落盘语料）：
  1. 抓省政府站的信箱表单页 `/{code}/mail/form.html`，看它引了哪些 js / 内联参数
  2. 对 35 个部门站代号逐个试 `POST /api/mail/list`（带省政府站 userIdObj）
  3. 试几组参数变体（pageNo/pageSize/current 等），打印原始响应体前 300 字

用法：
  python recon/jx-mailbox-probe.py            # 全量
  python recon/jx-mailbox-probe.py page       # 只抓表单页
  python recon/jx-mailbox-probe.py list       # 只试列表接口
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))

import httpx  # noqa: E402

HOST = "https://www.jiangxi.gov.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.5
OUT = HERE / "jx-mailbox-probe.json"

#: 省政府站（jxsrmzf）的 userIdObj —— 来自 recon/jx-config.js
PROV_UID = {
    "tenantId": "1749973237782081536",
    "deptId": "1750348077562798080",
    "siteId": "1750350048251023360",
    "qdId": "1751807511324454912",
}


def load_depts() -> list[dict]:
    cfg = (HERE / "jx-config.js").read_text(encoding="utf-8", errors="replace")
    out = []
    for m in re.finditer(r"websiteCod\s*:\s*'([^']+)'.*?domain\s*:\s*'([^']+)'"
                         r".*?websiteName\s*:\s*'([^']+)'", cfg, re.S):
        out.append({"code": m.group(1), "domain": m.group(2), "name": m.group(3)})
    return out


def get_form(cli: httpx.Client, code: str) -> dict:
    url = f"{HOST}/{code}/mail/form.html"
    try:
        r = cli.get(url, headers={"User-Agent": UA, "Referer": HOST + "/"})
    except Exception as e:                                              # noqa: BLE001
        return {"url": url, "err": type(e).__name__}
    if r.status_code != 200:
        return {"url": url, "status": r.status_code}
    html = r.text
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    inline = re.findall(r"userIdObj\s*[:=]\s*\{[^}]*\}", html)
    return {"url": url, "status": 200, "len": len(html),
            "scripts": scripts, "inline_uid": inline,
            "head": html[:600]}


def try_list(cli: httpx.Client, uid: dict, variants: list[dict]) -> list[dict]:
    out = []
    for v in variants:
        data = dict(uid)
        data.update(v)
        try:
            r = cli.post(HOST + "/api/mail/list", data=data,
                         headers={"User-Agent": UA, "Referer": HOST + "/",
                                  "X-Requested-With": "XMLHttpRequest"})
            body = r.text[:300]
        except Exception as e:                                          # noqa: BLE001
            out.append({"variant": v, "err": type(e).__name__})
            time.sleep(PAUSE)
            continue
        rec = {"variant": v, "status": r.status_code, "body": body}
        try:
            j = r.json()
            rec["json_keys"] = list(j.keys())[:8]
            inner = j.get("data") or j.get("resultData") or {}
            if isinstance(inner, dict):
                rec["total"] = inner.get("total")
                rec["rows"] = len(inner.get("records") or inner.get("list") or [])
        except Exception:                                               # noqa: BLE001
            pass
        out.append(rec)
        time.sleep(PAUSE)
    return out


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    result: dict = {}
    with httpx.Client(timeout=30, follow_redirects=True, trust_env=False) as cli:
        if mode in ("all", "page"):
            codes = ["jxsrmzf"] + [d["code"] for d in load_depts()[:4]]
            for c in codes:
                info = get_form(cli, c)
                result.setdefault("forms", {})[c] = info
                print(f"[form] {c}: {info.get('status', info.get('err'))} "
                      f"len={info.get('len')} scripts={len(info.get('scripts') or [])}",
                      flush=True)
                time.sleep(PAUSE)
        if mode in ("all", "list"):
            variants = [
                {"pageNo": 1, "pageSize": 10},
                {"current": 1, "size": 10},
                {"pageNum": 1, "pageSize": 10},
                {"pageIndex": 1, "rows": 10},
                {},
            ]
            res = try_list(cli, PROV_UID, variants)
            result["prov_list"] = res
            for r in res:
                print(f"[list] {r.get('variant')} → {r.get('status', r.get('err'))} "
                      f"total={r.get('total')} keys={r.get('json_keys')} "
                      f"body={(r.get('body') or '')[:160]!r}", flush=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {OUT.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
