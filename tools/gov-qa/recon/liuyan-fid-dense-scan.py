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
  python recon/liuyan-fid-dense-scan.py                      # 默认 601..4100 → liuyan-fid-dense-scan.jsonl
  python recon/liuyan-fid-dense-scan.py 601 1000             # 指定区间
  python recon/liuyan-fid-dense-scan.py 601 1000 out.jsonl   # 指定输出
  python recon/liuyan-fid-dense-scan.py 601 1000 out.jsonl 2.5   # 指定礼貌停顿秒数
  python recon/liuyan-fid-dense-scan.py 601 4200 out.jsonl 2.5 120  # ★ 长跑推荐：冷却 120s 自动续

## ★★ 限流规律（2026-10-08 实测，**这条决定了怎么跑**）
**每窗口约 15 次请求后必 403，窗口冷却约 2 分钟。**
⇒ 一遇 403 就退出的话，一轮只能扫 15 个 fid；**长跑必须传第 5 个参数（冷却秒数）**，
让脚本自己等窗口、重试同一个 fid（失败的那条**不落盘**，避免变成"假完成"的洞）。

## ★★ 不要多路并行打同一个域名
实测三路并行合计只有 **1.5 倍**收益（29 vs 19 fid/分钟），却把窗口打爆触发**全局 403**
（连原本可用的 fid 都 403）。**并行要跨目标**（不同域名），不要压在同一条链路上。
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

PAUSE = 1.0
RETRY = 2
#: 0 = 遇限流立即停（旧行为）；>0 = 冷却这么多秒后**重试同一个 fid**。
#: ★ 实测限流规律（2026-10-08）：**每窗口约 15 次请求后必 403，窗口冷却约 2 分钟**
#:   ⇒ 长跑应传 `cooldown=120`，让它自己等窗口，而不是跑 15 个就退出。
COOLDOWN = 0.0
#: 连续冷却上限（超过即停，避免无限等）
MAX_COOLDOWNS = 8


def probe(c, fid: str) -> dict:
    """探一个 fid。

    ⚠ **403 必须先于 JSON 解析判定**（2026-10-08 踩过）：被限流时服务端回的是
    **HTML 错误页**，`r.json()` 抛 `JSONDecodeError` ⇒ 若把「解析失败」当偶发去重试，
    就会**在已被限流的情况下继续猛刷**（实测三路并行把窗口打爆，连原本可用的 fid 都 403）。
    ⇒ 这里**先看 status**：403 立刻返回、不重试（由调用方停）；只有 200 才解析 JSON。
    """
    path = "/v1/threads/list/df"
    param = {"fid": fid, "showUnAnswer": 0, "lastItem": "",
             "position": 1, "rows": 2, "orderType": 2}
    last = ""
    for _ in range(RETRY + 1):
        try:
            r = c.post(BASE + path, content=_envelope(path, param),
                       headers=_headers(f"{BASE}/threads/list?fid={fid}"))
            if r.status_code != 200:
                # 403/412 = 限流，**不重试**，交给调用方停
                return {"fid": fid, "status": r.status_code,
                        "error": "rate_limited_or_blocked"}
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
    out = HERE / (sys.argv[3] if len(sys.argv) > 3 else "liuyan-fid-dense-scan.jsonl")
    pause = float(sys.argv[4]) if len(sys.argv) > 4 else PAUSE
    cooldown = float(sys.argv[5]) if len(sys.argv) > 5 else COOLDOWN

    done: set[str] = set()
    if out.exists():
        for ln in out.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    done.add(str(json.loads(ln)["fid"]))
                except Exception:                                       # noqa: BLE001
                    pass
    todo = [str(n) for n in range(lo, hi + 1) if str(n) not in done]
    print(f"区间 {lo}..{hi} → {out.name}：已完成 {len(done)}，本次待扫 {len(todo)}，"
          f"停顿 {pause}s", flush=True)

    hits = 0
    cooldowns = 0
    with httpx.Client(trust_env=False, timeout=20) as c, \
            out.open("a", encoding="utf-8") as f:
        i = 0
        idx = 0
        while idx < len(todo):
            fid = todo[idx]
            i += 1
            rec = probe(c, fid)
            if rec.get("status") not in (200, None):
                # 限流：**这一条不落盘**（否则会变成"假完成"的洞，永远不会被重扫）
                if cooldown > 0 and cooldowns < MAX_COOLDOWNS:
                    cooldowns += 1
                    print(f"⚠ HTTP {rec['status']}（第 {i} 个 fid={fid}）—— "
                          f"冷却 {int(cooldown)}s 后重试（第 {cooldowns}/{MAX_COOLDOWNS} 次）",
                          flush=True)
                    time.sleep(cooldown)
                    continue                       # 不推进 idx，重试同一个 fid
                print(f"⚠ HTTP {rec['status']}，已冷却 {cooldowns} 次仍不通 ⇒ **停止**。"
                      f"已扫的都在 {out.name} 里，稍后续跑即可（会自动跳过已完成的）。", flush=True)
                break
            cooldowns = 0                          # 成功即重置冷却计数
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if rec.get("n"):
                hits += 1
                p = " / ".join(rec.get("p") or [])
                print(f"  [{i}/{len(todo)}] fid={fid} [{p}] "
                      f"{(rec.get('forum') or '')[:22]}", flush=True)
            if i % 100 == 0:
                print(f"  ... {i}/{len(todo)}，命中 {hits}", flush=True)
            idx += 1
            time.sleep(pause)
    print(f"扫描结束：本次处理 {i} 个 fid（成功落盘 {hits} 个命中），"
          f"冷却 {cooldowns} 次 → {out.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
