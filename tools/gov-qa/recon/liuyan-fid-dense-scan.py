"""留言板 fid **密集**扫描 —— 枚举全国所有版块（省/市/县）。

## 为什么必须「逐号」扫
2026-10-08 密度实测（fid 651..680，见下）：**fid 是连续密集编号的**，
每个 fid 就是一个版块，**按行政区划顺序排列**：

```
651 北京大兴区   652 北京怀柔区   653 北京平谷区   654 北京密云区   655 北京延庆区
656 天津和平区   657 天津河北区   658 天津河东区   659 天津河西区   660 天津南开区
661 天津红桥区   662 天津滨海新区 665 天津东丽区 …  673 天津宁河区
674 上海黄浦区   676 上海徐汇区   677 上海长宁区 …
```

⇒ 之前 `liuyan-city-band-scan.py` 用 **step 100** 采样（只 10 个点），
**会漏掉 99% 的版块**；`liuyan-fid-band-scan.py` 用 step 10 也漏 90%。
**要枚举全国版块只能 step=1。**

## 分层（已知）
`539~600` 省级（31 省 × 书记/省长）· `601~763` 直辖市辖区 · `764~4000+` 地级市/县 · `5050~5120` 部委。

## 可续跑
结果逐行追加到 `liuyan-fid-dense-scan.jsonl`；重跑时**先读已完成的 fid 跳过**
（65 分钟一轮，别因一次中断全丢）。

用法：
  python recon/liuyan-fid-dense-scan.py                 # 默认 601..4100
  python recon/liuyan-fid-dense-scan.py 601 1000        # 指定区间
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import BASE, _envelope, _headers  # noqa: E402

OUT = HERE / "liuyan-fid-dense-scan.jsonl"
PAUSE = 1.0
RETRY = 2


def probe(c, fid: str) -> dict:
    """探一个 fid；JSONDecodeError 重试 RETRY 次（实测偶发）。"""
    path = "/v1/threads/list/df"
    param = {"fid": fid, "showUnAnswer": 0, "lastItem": "",
             "position": 1, "rows": 2, "orderType": 2}
    last = ""
    for _ in range(RETRY + 1):
        try:
            r = c.post(BASE + path, content=_envelope(path, param),
                       headers=_headers(f"{BASE}/threads/list?fid={fid}"))
            d = (r.json().get("resultData") or {})
            data = d.get("data") or []
            rec = {"fid": fid, "status": r.status_code, "n": len(data)}
            if data:
                rec["p"] = data[0].get("pForumNames") or []
                rec["forum"] = data[0].get("forumName")
                rec["sample"] = (data[0].get("subject") or "")[:40]
            return rec
        except Exception as e:                                          # noqa: BLE001
            last = type(e).__name__
            time.sleep(1.5)
    return {"fid": fid, "error": last}


def main() -> int:
    import httpx

    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 601
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 4100

    done: set[str] = set()
    if OUT.exists():
        for ln in OUT.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    done.add(str(json.loads(ln)["fid"]))
                except Exception:                                       # noqa: BLE001
                    pass
    todo = [str(n) for n in range(lo, hi + 1) if str(n) not in done]
    print(f"区间 {lo}..{hi}：已完成 {len(done)}，本次待扫 {len(todo)}", flush=True)

    hits = 0
    with httpx.Client(trust_env=False, timeout=20) as c, \
            OUT.open("a", encoding="utf-8") as f:
        for i, fid in enumerate(todo, 1):
            rec = probe(c, fid)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if rec.get("n"):
                hits += 1
                p = " / ".join(rec.get("p") or [])
                print(f"  [{i}/{len(todo)}] fid={fid} [{p}] "
                      f"{(rec.get('forum') or '')[:22]}", flush=True)
            if i % 100 == 0:
                print(f"  ... {i}/{len(todo)}，命中 {hits}", flush=True)
            time.sleep(PAUSE)
    print(f"扫描结束：本次 {len(todo)} 个 fid，命中 {hits} 个版块 → {OUT.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
