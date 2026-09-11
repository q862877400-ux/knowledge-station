# -*- coding: utf-8 -*-
"""国标存量状态体检（2026-08-27 改版：openstd 主渠道）。

扫目录文件 → 文件名提取标准号（去重）→ 逐号查官方状态 →
输出清单：标准号 | 名称 | ✅现行 / ⛔废止(日期) / ⏳即将实施 / ❓查无 / ⚠查询失败。

渠道策略（2026-08-27 实测定型，两轮闭环）：
- **第一轮 --channel openstd（默认）**：openstd.samr.gov.cn 国家标准全文公开系统
  std_list 核验状态**无验证码**（1.4-1.7s/号实测，覆盖 ~97% 存量）；
  状态取 现行/即将实施/被代替/废止，同主体自动取最新年代；缺废止日期（HTML 无该列）。
- **第二轮 --channel ndls**：从 results.jsonl 自动续查 miss（found=False）与失败号
  （GB/T 5xxxx 工程建设标准等 openstd 目录外），ndls 全门类 + 废止日期。
  ndls 有 Jiasule 验证码（IP 惩罚期曾 100% 拦截，需冷却），第二轮回补时通常已解除。

反爬（用户要求 24h 不间断跑一轮但注意反爬）：
- 单线程串行 + **请求间隔随机化**（默认均匀随机 1.0-2.5s，--gap-min/--gap-max 可调），
  打破固定节奏的风控模式识别；--gap S 可改回固定间隔；
- ndls 模式默认不发详情请求（状态取搜索行 a000，请求减半）；--detail 才补详情；
- **--rotate IP 旋转**：被验证码限流时自动换出口 IP 重试同号
  （优先 Clash Verge 节点旋转——经 named pipe 切换国家落地组；或 --proxies 静态代理文件）；
- 指数退避重试（429/5xx/超时：1s×2^n cap 30s，最多 3 次；401/403 不重试即停）；
- 验证码/风控特征检测（旋转耗尽后指数暂停，连击进入长冷却，不硬闯）；
- 结果缓存 <out-dir>/results.jsonl（**只跳过已查到状态的号**，失败/查无自动续查）；
- 进度写 <out-dir>/progress.json（每 500 条）。

用法：
  python scripts/std_status_check.py --dir "<国标目录>" [--limit N] [--gap-min S] [--gap-max S]
      [--channel openstd|ndls] [--detail] [--rotate [--proxies FILE]] [--out-dir PATH]

数据/代码分离（2026-08-26 项目原则）：体检结果默认写到**国标目录同级**的
"体检结果/"（如 D:\\AI\\work space\\标准\\体检结果\\），不落代码树 var/。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.update.channels.base import UpdateError  # noqa: E402
from src.core.update.channels.cssn import CssnAdapter  # noqa: E402
from src.core.update.channels.ndls import NdlsAdapter  # noqa: E402
from src.core.update.channels.official_gb import OfficialGbAdapter  # noqa: E402
from src.core.update.channels.proxy_rotate import (  # noqa: E402
    ProxyCurlTransport,
    build_rotator,
    random_gap,
)

#: 文件名标准号提取（GB/GBT/GB-T/GBZ/GBZ-T/GBZ／T 等 + 点分号 + 年代；兼容全角斜杠 ／）
_STD_NO_RE = re.compile(
    r"^(GB\s*(?:[／/]Z|Z)?\s*(?:[／/]?\s*T)?)\s*(\d+(?:\.\d+)*)\s*[-—–]\s*(\d{4})")
#: 反爬节奏基线（实际间隔经 --gap-min/--gap-max 随机化；此值仅作 argparse 默认参考）
RETRYABLE = {408, 429, 500, 502, 503, 504}
MAX_RETRIES = 3
BACKOFF_BASE = 1.0
CAPTCHA_MARKERS = ("验证码", "captcha", "风控", "频繁", "too many")

STATUS_LABEL = {
    "effective": "✅ 现行", "withdrawn": "⛔ 已废止", "superseded": "🟡 已被替代",
    "upcoming": "⏳ 即将实施", None: "❓ 查无/未标注",
}


def extract_standard_no(filename: str) -> str | None:
    """从文件名头部提取标准号（如 'GB 1094.1-2013 电力变压器…' → 'GB 1094.1-2013'）。"""
    m = _STD_NO_RE.search(filename)
    if not m:
        return None
    prefix = m.group(1).replace("／", "/").replace(" ", "").upper()   # GB / GBT / GBZ/T
    return f"{prefix} {m.group(2)}-{m.group(3)}"


def looks_like_captcha(text: str) -> bool:
    low = (text or "").lower()
    return any(mk in low for mk in CAPTCHA_MARKERS)


def _evidence_url(url: str | None) -> str | None:
    """openstd 行证据链 showInfo:<hcno> → 真实详情页 URL（无则原样返回）。"""
    if url and url.startswith("showInfo:"):
        return "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=" + url[len("showInfo:"):]
    return url


def probe_one(make_adapter, std: str, *, detail: bool = False,
              rotator=None, max_rot: int = 4) -> dict:
    """查单号（含被限换 IP 重试）：验证码命中且旋转器可用 → 换 IP + 新 session
    重试同号（最多 max_rot 次）；旋转不可用/耗尽 → 返回 captcha_blocked 交上层冷却。
    """
    adapter = make_adapter()
    r = probe_with_retry(adapter, std, detail=detail)
    for _ in range(max_rot):
        if r.get("error") != "captcha_blocked":
            return r
        if rotator is None:
            return r
        new_proxy = rotator.rotate()
        if not new_proxy:
            return r
        print(f"[rotate] 换出口 → {new_proxy}，重试 {std}", flush=True)
        adapter = make_adapter(new_proxy)
        time.sleep(random_gap(0.5, 1.0))
        r = probe_with_retry(adapter, std, detail=detail)
    return r


def probe_with_retry(adapter, std: str, *, detail: bool = False) -> dict:
    """查单号状态（退避重试 + 验证码检测），返回可落 jsonl 的结果 dict。

    渠道自适应：ndls 支持 detail（True 补详情/False 体检模式 row-only）；
    openstd 固定 1 请求取搜索行状态（无废止日期列），mode="openstd_row"。
    """
    channel = adapter.name
    is_ndls = isinstance(adapter, NdlsAdapter)
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = adapter.probe(std, detail=detail) if is_ndls else adapter.probe(std)
            if getattr(r, "captcha", False):
                return {"standard_no": std, "error": "captcha_blocked",
                        "message": "渠道验证码/风控拦截"}
            raw = r.raw or {}
            rrow = raw.get("row") if isinstance(raw.get("row"), dict) else {}
            return {
                "standard_no": std,
                "found": r.found,
                "legal_status": r.legal_status,
                "status_text": raw.get("status_text") or rrow.get("state"),
                "publish_date": raw.get("issue_date") or raw.get("a101") or raw.get("publish_date"),
                "effective_date": r.effective_date or raw.get("impl_date") or raw.get("a205"),
                "withdrawn_date": raw.get("withdrawn_date") or raw.get("a206"),
                "replaced_by": (raw.get("a462list") or raw.get("a461list") or [])[:5],
                "ccs_code": raw.get("ccs_code") or rrow.get("a825"),
                "ccs_name": raw.get("ccs") or rrow.get("a825name"),
                "ics": raw.get("ics") or rrow.get("a826name"),
                "standard_name": rrow.get("a298") or rrow.get("name") or rrow.get("标准名"),
                "evidence_url": _evidence_url(r.evidence_url),
                "mode": raw.get("mode") or ("detail" if detail and is_ndls else "row"),
                "channel": channel,
                # 渠道原始返回完整留档（网站能挖到的都存，报告/后续任意字段可查）
                "raw": raw,
                "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        except UpdateError as e:
            code = getattr(e, "code", "")
            msg = str(e)
            if looks_like_captcha(msg) or "captcha" in msg:
                return {"standard_no": std, "error": "captcha_blocked", "message": msg[:200]}
            if attempt >= MAX_RETRIES:
                return {"standard_no": std, "error": "failed", "message": msg[:200]}
            wait = min(BACKOFF_BASE * (2 ** attempt), 30.0)
            time.sleep(wait)
        except Exception as e:  # noqa: BLE001
            if attempt >= MAX_RETRIES:
                return {"standard_no": std, "error": "failed", "message": f"{type(e).__name__}: {e}"[:200]}
            time.sleep(min(BACKOFF_BASE * (2 ** attempt), 30.0))
    return {"standard_no": std, "error": "failed"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="国标存量状态体检（cssn 全覆盖主渠道）")
    ap.add_argument("--dir", required=True, help="国标文件目录")
    ap.add_argument("--limit", type=int, default=0, help="只查前 N 个去重标准号（冒烟）")
    ap.add_argument("--gap", type=float, default=None,
                    help="固定请求间隔秒（默认随机 1.0-2.5s；与 --gap-min/--gap-max 二选一）")
    ap.add_argument("--gap-min", type=float, default=1.0, help="随机间隔下限秒")
    ap.add_argument("--gap-max", type=float, default=2.5, help="随机间隔上限秒")
    ap.add_argument("--channel", choices=("cssn", "openstd", "ndls"), default="cssn",
                    help="cssn=中国标准服务网（默认，全覆盖无验证码）；openstd=国家标准全文公开系统；ndls=数字标准馆（Jiasule 验证码，补 miss 用）")
    ap.add_argument("--detail", action="store_true",
                    help="ndls 模式补详情请求（废止日期/代替关系；默认只发搜索请求）")
    ap.add_argument("--rotate", action="store_true",
                    help="被验证码限流时换出口 IP 重试（Clash 节点旋转，或 --proxies 静态列表）")
    ap.add_argument("--proxies", type=str, default=None,
                    help="静态代理列表文件（每行一个 proxy URL；配 --rotate 时优先于 Clash）")
    ap.add_argument("--out-dir", type=str, default=None,
                    help="结果输出目录（默认 <国标目录同级>/体检结果，不落代码树）")
    args = ap.parse_args(argv)
    if args.gap is not None:
        args.gap_min = args.gap_max = args.gap

    root = Path(args.dir)
    # 数据/代码分离：结果默认写到国标目录同级的"体检结果"（数据区）
    out_dir = Path(args.out_dir) if args.out_dir else (root.parent / "体检结果")
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.jsonl"
    progress_path = out_dir / "progress.json"

    # 1) 扫描 + 提取标准号 + 去重（同标准多文件只查一次）
    stds: dict[str, str] = {}   # standard_no -> 第一个文件名
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() != ".pdf":
            continue
        no = extract_standard_no(p.name)
        if no:
            stds.setdefault(no, p.name)
    print(f"[scan] PDF 文件提取标准号去重后 {len(stds)} 个", flush=True)

    # 2) 断点：**只跳过已查到状态的号**（found=True 且无 error）；
    #    失败/查无（含 openstd 查无的 GB/T 5xxxx）留待本轮/下轮渠道续查
    done: dict[str, dict] = {}
    skip: set[str] = set()
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
                done[d["standard_no"]] = d
            except (ValueError, KeyError):
                continue
        skip = {no for no, d in done.items() if d.get("found") and "error" not in d}
        print(f"[resume] 已缓存 {len(done)} 条，其中已查到状态 {len(skip)} 条（跳过）；"
              f"失败/查无 {len(done) - len(skip)} 条将续查", flush=True)

    # 3) 渠道 + 旋转器
    rotator = build_rotator(args.proxies) if args.rotate else None

    def make_adapter(proxy: str | None = None):
        if args.channel == "ndls":
            return NdlsAdapter(transport=ProxyCurlTransport(proxy)) if proxy else NdlsAdapter()
        if args.channel == "cssn":
            return CssnAdapter(transport=ProxyCurlTransport(proxy)) if proxy else CssnAdapter()
        return (OfficialGbAdapter(transport=ProxyCurlTransport(proxy))
                if proxy else OfficialGbAdapter())

    print(f"[channel] {args.channel}"
          + ("（ndls 体检模式，不发详情）" if args.channel == "ndls" and not args.detail
             else "（ndls 详情模式）" if args.channel == "ndls"
             else "（cssn 全覆盖状态：食品安全/工程/转化标准均收录，无验证码）"
             if args.channel == "cssn"
             else "（openstd 状态核验，无验证码）")
          + f" 间隔=随机[{args.gap_min},{args.gap_max}]s"
          + (" +IP旋转" if rotator else ""), flush=True)
    order = [s for s in stds if s not in skip]
    if args.limit:
        order = order[: args.limit]
    total = len(order)
    print(f"[run] 本次待查 {total} 个（去重后共 {len(stds)}，已查 {len(skip)}）", flush=True)
    start = time.monotonic()
    ok = fail = notfound = withdrawn = 0
    captcha_streak = 0
    long_cooling = False   # ndls 模式：IP 惩罚期长冷却（15min 档）

    def flush_progress(i: int) -> None:
        el = time.monotonic() - start
        rate = i / el if el > 0 else 0
        progress_path.write_text(json.dumps({
            "done": i, "total": total, "elapsed_s": round(el, 1),
            "rate_per_s": round(rate, 2), "eta_s": round((total - i) / rate, 1) if rate else None,
            "ok": ok, "fail": fail, "notfound": notfound, "withdrawn": withdrawn,
            "channel": args.channel,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    with results_path.open("a", encoding="utf-8") as f:
        for i, std in enumerate(order, 1):
            r = probe_one(make_adapter, std, detail=args.detail, rotator=rotator)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if r.get("error") == "captcha_blocked":
                # IP 旋转已耗尽/不可用：风控连击指数暂停 60s→120s→240s→480s→600s 封顶；
                # 连续 3 次（IP 惩罚期特征）转 15min 长冷却，期间不打任何请求
                captcha_streak += 1
                if captcha_streak >= 3 and not long_cooling:
                    long_cooling = True
                    print(f"[!] 连续 {captcha_streak} 次验证码（旋转耗尽）→ 疑似 IP 惩罚期，"
                          f"进入 15min 长冷却（{std}）", flush=True)
                    time.sleep(900)
                    captcha_streak = 0
                else:
                    pause = min(60 * (2 ** (captcha_streak - 1)), 600)
                    print(f"[!] 风控第 {captcha_streak} 连击（{std}），暂停 {pause}s 降温", flush=True)
                    time.sleep(pause)
                fail += 1
            else:
                captcha_streak = 0
                if "error" in r:
                    fail += 1
                else:
                    ok += 1
                    st = r.get("legal_status")
                    if st is None:
                        notfound += 1
                    elif st in ("withdrawn", "superseded"):
                        withdrawn += 1
            if i % 500 == 0 or i == total:
                flush_progress(i)
                print(f"[{i}/{total}] ok={ok} 废止/替代={withdrawn} 查无={notfound} 失败={fail} "
                      f"{(i/(time.monotonic()-start)):.2f}号/s", flush=True)
            time.sleep(random_gap(args.gap_min, args.gap_max))
    flush_progress(total)
    print(f"[done] {args.channel} 共查 {total} 号：ok={ok} 废止/替代={withdrawn} "
          f"查无={notfound} 失败={fail} 耗时 {round((time.monotonic()-start)/3600, 2)}h", flush=True)
    print(f"[out] {results_path}  进度 {progress_path}", flush=True)
    # emoji/非 GBK 字符路径用 unicode_escape 转义打印（控制台 GBK 安全）
    esc_dir = args.dir.encode("unicode_escape").decode("ascii")
    print(f"[next] 查无/失败号可第二轮补查：python scripts/std_status_check.py "
          f"--dir \"{esc_dir}\" --channel ndls --out-dir \"{out_dir}\"", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
