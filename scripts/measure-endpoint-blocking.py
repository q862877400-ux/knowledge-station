# -*- coding: utf-8 -*-
"""**测"端点把事件循环卡住多久"**——「先量 → 再改 → 再量」里那把尺（§10.73）。

## 为什么需要它（不是又一个启发式）
`scripts/audit-async-endpoints.py` 只能**从源码推断**某条端点"做同步重活"；它答不了
"**卡多久**"。而没有时长就无法排序优先级，也无法证明改动**真的**让出事件循环了
（只看代码从 `async def` 变成 `def` 不算证据——Starlette 到底有没有丢线程池，
得**量**）。复核 b10/b12 都是用"变异 + 实测"定的性，这把尺把那种做法固定下来。

## 它量的是什么
用 `httpx.ASGITransport` 在**同一个事件循环**里跑被测 app，同时开一个**心跳协程**
（每 5ms 醒一次，记两次醒之间的间隔）。然后：

* 被测端点是 `async def` ⇒ 它的同步重活在**调用方的任务里**执行，心跳**没法被调度**
  ⇒ `max_gap ≈ 该请求的耗时`（**引擎在这段时间里对所有请求都是死的**）；
* 被测端点是 `def` ⇒ Starlette/anyio 把它丢进**线程池**，心跳照常 5ms 一跳
  ⇒ `max_gap` 掉回**个位数毫秒**。

⚠ 两个边界：① ASGITransport 是**进程内**调用（没有真 socket、没有 uvicorn 的
`--limit-concurrency`），所以它量的是"**事件循环被占住多久**"这个内核事实，不是端到端延迟；
② `blocked_ratio = max(0, max_gap - interval) / duration` 是**下界估计**（心跳只采样到
首尾两次唤醒之间），所以宁可把它读成"至少堵了这么久"。

只读：只建**临时** `KS_DATA_DIR` 下的 app 与临时 PDF，不碰真库、不写仓库。
用法：`.venv\\Scripts\\python.exe scripts\\measure-endpoint-blocking.py [--case NAME] [--pages N] [--json]`
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HEARTBEAT_S = 0.005
TOKEN = "measure-token"
HDR = {"Authorization": f"Bearer {TOKEN}"}


def make_pdf(path: Path, pages: int) -> Path:
    """造一份**文本量可控**的 PDF（不依赖仓库里的任何 fixture，跑在哪都一样）。"""
    import fitz

    doc = fitz.open()
    body = ("本标准规定了生产经营单位动火作业的安全要求、分级审批与监护措施。"
            "动火作业分为特殊动火作业、一级动火作业和二级动火作业。")
    for i in range(pages):
        page = doc.new_page()
        y = 72.0
        for line in range(28):
            page.insert_text((56, y), f"第 {i + 1} 页 第 {line + 1} 行 {body}",
                             fontname="china-s", fontsize=10.5)
            y += 24.0
    doc.save(str(path))
    doc.close()
    return path


async def _heartbeat(stop: asyncio.Event, gaps: list[float], interval: float) -> None:
    last = time.perf_counter()
    while not stop.is_set():
        await asyncio.sleep(interval)
        now = time.perf_counter()
        gaps.append(now - last)
        last = now


async def measure(app, method: str, path: str, *, body: dict | None = None,
                  params: dict | None = None, headers: dict | None = None,
                  interval: float = HEARTBEAT_S) -> dict:
    """跑一次被测请求，返回耗时与事件循环的空档统计。

    ⚠ `app` 由调用方传入（不是在这里 `create_app`）：这样**合成对照**也能用同一把尺
    ——`tests/test_measure_harness.py` 拿两条人造端点（一条 `async def` + `time.sleep`、
    一条 `def` + `time.sleep`）来证明**这把尺真的分得开"堵"与"没堵"**。
    量具自己没有闸门的话，它坏掉的那天所有"after"数字都会变成**假绿**。
    """
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://measure") as c:
        stop = asyncio.Event()
        gaps: list[float] = []
        hb = asyncio.create_task(_heartbeat(stop, gaps, interval))
        await asyncio.sleep(interval * 4)          # 让心跳先跑起来（测基线空档）
        idle = list(gaps)
        gaps.clear()
        t0 = time.perf_counter()
        r = await c.request(method, path, json=body, params=params,
                            headers=headers if headers is not None else HDR)
        duration = time.perf_counter() - t0
        await asyncio.sleep(interval * 2)          # 收尾：把请求尾巴上的空档也采到
        stop.set()
        await hb
    gaps.sort()
    max_gap = gaps[-1] if gaps else 0.0
    return {
        "status": r.status_code,
        "duration_s": round(duration, 4),
        "idle_max_gap_s": round(max(idle) if idle else 0.0, 4),
        "max_gap_s": round(max_gap, 4),
        "p50_gap_s": round(gaps[len(gaps) // 2], 4) if gaps else 0.0,
        "samples": len(gaps),
        # 下界估计：心跳首尾两次唤醒之间至少堵了这么久
        "blocked_s_lower_bound": round(max(0.0, max_gap - interval), 4),
        "body_head": (r.text or "")[:120],
    }


CASES: dict[str, dict] = {}


def case(fn):
    CASES[fn.__name__.removeprefix("case_")] = fn
    return fn


@case
def ingest_preview(ctx: dict) -> dict:
    """`POST /ingest/preview`：单文件体检（sha256 + 真解析，文件里自述"负载下可达 135s"）。"""
    return {"method": "POST", "path": "/api/v1/ingest/preview",
            "body": {"path": str(ctx["pdf"]), "doc_type": "standard"}}


@case
def ingest_preview_inbox(ctx: dict) -> dict:
    """`GET /ingest/preview/inbox`：列目录（`os.walk`，轻但也是同步 I/O）。"""
    return {"method": "GET", "path": "/api/v1/ingest/preview/inbox",
            "params": {"dir": str(ctx["pdf"].parent)}}


@case
def health(ctx: dict) -> dict:
    """`GET /api/v1/health`。

    §10.74 之前它**不是**廉价端点：`embedder.is_available()` 会真加载模型
    （空缓存实测：耗时 6.79s、事件循环空档 6.79s）。现在走廉价的 `embedder.health()`。
    """
    return {"method": "GET", "path": "/api/v1/health", "body": None}


@case
def health_board(ctx: dict) -> dict:
    """`GET /api/v1/diagnostics/health-board`：七条 `COUNT(*)` + `mineru_available()`。

    ⚠ 别指望这条量大：本机实测总耗时 **0.017s**、`import mineru` **0.000s**
    （CLI 包不是重依赖库）、30 万行 COUNT ≈1.1ms。它进这里是因为"**同步 I/O 不该在
    事件循环里**"这条一般纪律，以及"改完要能证明**没**变慢"。
    """
    return {"method": "GET", "path": "/api/v1/diagnostics/health-board", "body": None}


@case
def document_figure(ctx: dict) -> dict:
    """`GET /api/v1/documents/{doc_id}/figure/1`：**真渲染**（PyMuPDF 按题注定位 + 截图）。

    种一行 `doc_meta`（`file_path` 指向生成的 PDF）就够：`parse_out/<doc_id>` 不存在 ⇒
    `middle_geo.load` 返回 None ⇒ 走 `figure_locator.locate_figure`（**逐页 `get_text("dict")`**
    找题注）⇒ 命中后 `get_pixmap(clip, dpi=144)` 出 PNG。所以 PDF 页数直接决定耗时
    ——把题注放在**最后一页**，好让扫描真的走完全部页。
    """
    return {"method": "GET", "path": f"/api/v1/documents/{ctx.setdefault('doc_id', 'doc_figbench')}/figure/1",
            "body": None, "setup": _seed_figure_doc}


def _seed_figure_doc(ctx: dict) -> None:
    """造一份"题注在最后一页"的 PDF + 库内 doc_meta 行（只碰临时库）。"""
    import fitz
    from src.core.storage.sqlite_db import get_db_connection

    pages = ctx.get("pages") or 150
    path = ctx["tmp"] / "figure_bench.pdf"
    doc = fitz.open()
    body = ("本标准规定了动火作业的分级、审批、监护与作业后检查要求，"
            "适用于生产经营单位在禁火区内的动火作业。")
    # ⚠ 每页**写满**（28 行）而不是 1 行：真实标准页是密排文本，`get_text("dict")` 的
    # 成本随文字量走——第一版只写 1 行，量出 0.13s，**不足以代表真机**（诚实边界写在 §10.75）。
    for i in range(max(1, pages - 1)):
        page = doc.new_page()
        y = 72.0
        for ln in range(28):
            page.insert_text((56, y), f"{i + 1}-{ln + 1} {body}", fontname="china-s", fontsize=10.5)
            y += 24.0
    last = doc.new_page()
    last.insert_text((56, 100), "本页给出动火作业流程图。", fontname="china-s", fontsize=11)
    last.insert_text((56, 180), "图1 动火作业流程图", fontname="china-s", fontsize=11)
    doc.save(str(path))
    doc.close()

    ctx["doc_id"] = "doc_figbench"
    ctx["pdf"] = path
    conn = get_db_connection()
    conn.execute("DELETE FROM doc_meta WHERE doc_id=?", (ctx["doc_id"],))
    conn.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (ctx["doc_id"], "GB FIGBENCH-2025", "图渲染基准", "FIGBENCH", "r1", "[]",
         str(path), "h_figbench"))
    conn.commit()


@case
def egress_audit_export(ctx: dict) -> dict:
    """`GET /api/v1/egress/audit/export`：把外发记录导成 JSON 落盘（§10.76）。

    ⚠ **这条本来就不大**：`export_egress()` 读 `debug_dump` 里 `trigger_type in
    ('user_export','egress')` 的行，而那张表有保留策略（最多 1000 行）⇒ 上限就有界。
    种子 1000 行只是把上界铺满，好让"改 `def` 有没有意义"有个数字（而不是靠感觉）。
    """
    return {"method": "GET", "path": "/api/v1/egress/audit/export",
            "body": None, "setup": _seed_egress_audit}


def _seed_egress_audit(ctx: dict) -> None:
    """把 `debug_dump` 的审计行铺到保留上限（1000 行），只碰临时库。"""
    from src.core.storage.sqlite_db import get_db_connection

    conn = get_db_connection()
    rows = [(f"dump_{i:05d}", "egress" if i % 2 else "user_export",
             f"问题 {i}", "x" * 400, "y" * 400, "z" * 200, f"2026-09-18 00:{i % 60:02d}:00")
            for i in range(1000)]
    conn.executemany(
        "INSERT OR REPLACE INTO debug_dump (dump_id, trigger_type, query, prompt,"
        " llm_output, logs, created_at) VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    ctx["seeded_rows"] = len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="ingest_preview", choices=sorted(CASES))
    ap.add_argument("--pages", type=int, default=12, help="生成 PDF 的页数（控制工作量）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="ks_measure_"))
    os.environ["KS_DATA_DIR"] = str(tmp)
    from src.core import config
    config.reset_settings()
    from src.core.api.server import create_app

    app = create_app(TOKEN)
    ctx = {"pdf": make_pdf(tmp / "measure.pdf", args.pages), "tmp": tmp}
    spec = CASES[args.case](ctx)
    # 需要库内数据的用例自带 `setup`（种一行 doc_meta 等）——在**量之前**跑完，
    # 它的耗时不计入被测端点的空档。
    setup = spec.pop("setup", None)
    if setup is not None:
        setup(ctx)
    out = {"case": args.case, "pages": args.pages,
           "pdf_bytes": ctx["pdf"].stat().st_size, **asyncio.run(measure(app, **spec))}
    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(f"case={out['case']}  pages={out['pages']}  pdf={out['pdf_bytes']}B  "
              f"HTTP={out['status']}")
        print(f"  请求耗时        : {out['duration_s']}s")
        print(f"  事件循环最大空档 : {out['max_gap_s']}s   "
              f"(空闲基线 {out['idle_max_gap_s']}s / 中位 {out['p50_gap_s']}s / "
              f"{out['samples']} 个样本)")
        print(f"  ⇒ 至少堵了      : {out['blocked_s_lower_bound']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
