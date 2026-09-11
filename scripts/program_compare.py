# -*- coding: utf-8 -*-
"""逐本「原文逐页 vs 右侧重建预览(.fulltext)」成对截图 + VLM 比对的自助校验 harness。

泛化版 ks_page_compare.py（2026-09-02 用户验收方法论）：
- 入参是**一个 PDF 路径**（非硬编码 doc_id），按需经 run_full_ingest 入库后取 doc_id；
- 产出 <out>/orig_pN.png（原文：PDF 页嵌入扫描位图，不经 OCR/重渲染）与
  <out>/prev_pN.png（预览：复刻 .fulltext 页窗截图），并写 manifest.json（成对路径+页号+采样标记）；
- VLM 由调用方 read_image 逐页对比（origin 是数据层「OCR/解析认错」+ 渲染错位）。

巨本限样：页数 > threshold 时只截采样页（首页/末页/含图表公式页/等距 N 页），并明确标记。
用法：
  python scripts/program_compare.py --pdf "<abs.pdf>" [--out <dir>] [--reingest]
      [--no-preview] [--pages-threshold 80] [--sample-n 8] [--force-deep/--no-force-deep]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # PyMuPDF

from scripts._stdparse import _STD_RE, derive_standard  # noqa: E402

TMP = Path(os.environ.get("TEMP", r"C:\Users\Zegel\AppData\Local\Temp"))
URL = "http://127.0.0.1:5173"
DB = r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db"

# 与库内 clause 页界一致：`.page-break[data-page=N]`，页 1 无标记（初始即页 1）
_PB_SEL = ".page-break[data-page='{p}']"


def _b4_exe() -> str:
    sh = shutil.which("browser4-cli")
    if sh and sh.lower().endswith(".exe"):
        return sh
    if sh and sh.lower().endswith(".cmd"):
        d = Path(sh).parent / "node_modules" / "browser4-cli" / "bin"
        for f in d.glob("browser4-cli-*.exe"):
            if f.exists():
                return str(f)
    return r"C:\Users\Zegel\AppData\Roaming\npm\node_modules\browser4-cli\bin\browser4-cli-win32-x64.exe"


_B4 = _b4_exe()


def b4(*args):
    r = subprocess.run([_B4, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    return (r.stdout or r.stderr)


def ev(js: str):
    b = base64.b64encode(js.encode("utf-8")).decode()
    return b4("eval", "--base64", b, "--json")


def _doc_page_count(pdf: Path) -> int:
    with fitz.open(str(pdf)) as d:
        return len(d)


def _has_text_layer(pdf: Path) -> bool:
    """多数页可从文本层取文本 → force_deep=False（快路径）；否则走 MinerU 深解析/OCR。"""
    try:
        with fitz.open(str(pdf)) as d:
            n = len(d)
            if n == 0:
                return False
            samples = max(1, min(n, 6))
            with_text = 0
            for i in range(0, n, max(1, n // samples)):
                t = d[i].get_text().strip()
                if len(t) > 20:
                    with_text += 1
            return with_text >= max(1, samples // 2)
    except Exception:
        return False


def render_orig(pdf: Path, n_pages: int, out: Path, dpi: int = 150) -> list[dict]:
    """原件图片：**直接把 PDF 每页转成图片**（用户统一要求），不经 OCR、不经抠嵌入位图。"""
    meta = []
    with fitz.open(str(pdf)) as doc:
        for i in range(n_pages):
            p = out / f"orig_p{i + 1}.png"
            try:
                doc[i].get_pixmap(dpi=dpi).save(str(p))
            except Exception as e:
                print(f"  [warn] orig_p{i + 1} render fail: {e}", flush=True)
            meta.append({"page": i + 1, "orig": str(p)})
    return meta


def _db_query(sql, args):
    import sqlite3
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def _db_standard(doc_id: str) -> str:
    rows = _db_query("SELECT standard_no FROM doc_meta WHERE doc_id=?", (doc_id,))
    return rows[0]["standard_no"] if rows else ""


def ensure_doc(pdf: Path, reingest: bool, force_deep: bool) -> str:
    """查库（file_hash）→ 不存在则 run_full_ingest 入库；返回 doc_id。"""
    file_hash_file = None
    try:
        import hashlib
        file_hash_file = hashlib.sha256(pdf.read_bytes()).hexdigest()
    except Exception:
        pass

    if file_hash_file:
        rows = _db_query("SELECT doc_id FROM doc_meta WHERE file_hash=?", (file_hash_file,))
        if rows and not reingest:
            print(f"  [db] 已存在 doc_id={rows[0]['doc_id']}（file_hash 命中，skip ingest）", flush=True)
            return rows[0]["doc_id"]

    std_no, std_name = derive_standard(pdf)
    print(f"  [ingest] standard_no={std_no!r} name={std_name!r} reingest={reingest} force_deep={force_deep}", flush=True)
    from src.core.ingestion.pipeline import run_full_ingest
    res = run_full_ingest(pdf, std_no, std_name, reingest=reingest,
                          force_deep=force_deep)
    print(f"  [ingest] result={json.dumps(res, ensure_ascii=False)}", flush=True)
    if res.get("status") in ("ok", "duplicate", "standard_exists") and res.get("doc_id"):
        return res["doc_id"]
    if res.get("status") == "standard_exists" and res.get("existing_doc_id"):
        return res["existing_doc_id"]
    raise RuntimeError(f"入库失败: {res}")


def _wait(pred_js: str, tries: int = 25, pause: float = 1.0) -> bool:
    """轮询 eval pred_js 返回真（非 0/false/-1）即停；超时返回 False。"""
    for _ in range(tries):
        r = ev(pred_js)
        s = str(r).strip()
        try:
            v = json.loads(s)["output"]["result"] if s.startswith("{") else None
        except Exception:
            v = None
        if v is not None:
            if isinstance(v, bool) and v:
                return True
            if isinstance(v, (int, float)) and v > 0:
                return True
            if isinstance(v, str) and v.strip() not in ("", "0", "-1", "false", "False"):
                return True
        if v is None and s not in ("", "0", "-1", "false", "False"):
            return True
        time.sleep(pause)
    return False


def _evr(js: str):
    """eval 并返回 output.result（供调试打印）。"""
    s = ev(js)
    try:
        return json.loads(s)["output"]["result"]
    except Exception:
        return s


def preview_open(standard_no: str):
    b4("open", "--headed", "--fresh", URL)
    time.sleep(6)
    # fileNavOpen 默认 true（抽屉已开）；仅在未开时点按钮，否则会把它关掉
    ev('''() => { const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim()==='📚 文件目录'); if (b && !document.querySelector('.toc-drawer')) b.click(); return 'n'; }''')
    time.sleep(1)
    # 搜索键用标准号**数字段**（如 '10-2013'），文件目录按此召回最稳
    m = re.search(r"(\d+(?:\.\d+)*-\d{4})", (standard_no or "").replace(" ", ""))
    skey = m.group(1) if m else (standard_no or "").replace(" ", "")
    if skey:
        print(f"  [nav] fill skey={skey} ->", _evr('''() => { const i = document.querySelector('.toc-drawer input'); if(!i) return 'no-input'; const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(i,''' + json.dumps(skey) + '''); i.dispatchEvent(new Event('input',{bubbles:true})); return 'q'; }'''), flush=True)
    # 轮询等 .toc-child 出现（文件目录树是异步加载的）
    ok1 = _wait('''() => { const d = document.querySelector('.toc-drawer'); if(!d) return 0; const c = Array.from(d.querySelectorAll('.toc-child')).filter(e=>String(e.textContent||'').replace(/[\\s/]+/g,'').includes(''' + json.dumps(skey) + ''')); return c.length; }''')
    print(f"  [nav] toc-child found={ok1}", flush=True)
    # 点击整行 .toc-child（承载 onClick→openDocFromNav→loadDocument）
    print("  [nav] click ->", _evr('''() => { const d = document.querySelector('.toc-drawer'); if(!d) return 'no-drawer'; const c = Array.from(d.querySelectorAll('.toc-child')).find(e=>String(e.textContent||'').replace(/[\\s/]+/g,'').includes(''' + json.dumps(skey) + ''')); if(c){c.click(); return 'opened';} return 'no-leaf'; }'''), flush=True)
    # 轮询等 .fulltext-clause 渲染（loadDocument 完成后才有）
    ok2 = _wait('''() => { return document.querySelectorAll('.fulltext-clause').length; }''', tries=30)
    print(f"  [nav] fulltext-clause rendered={ok2}", flush=True)
    time.sleep(0.5)


def doc_open(doc_id: str, standard_no: str):
    """优先用 __ksOpenDoc(doc_id) 直接打开文档（最稳）；无 hook 时回退目录导航。"""
    b4("open", "--headed", "--fresh", URL)
    time.sleep(6)
    r = ev('''() => { return typeof window.__ksOpenDoc === 'function'; }''')
    if str(r).strip().lower().startswith("true"):
        ev('''() => { window.__ksOpenDoc(''' + json.dumps(doc_id) + '''); return 'opened'; }''')
        print("  [doc_open] via __ksOpenDoc (direct)", flush=True)
        time.sleep(12)
    else:
        print("  [doc_open] __ksOpenDoc 缺失 → 目录导航兜底", flush=True)
        preview_open(standard_no)


def _preview_page_count() -> int:
    """.fulltext 已渲染的 .fulltext-clause 数量（预览加载判据，替代稀疏的 .page-break）。"""
    r = ev('''() => { return document.querySelectorAll('.fulltext-clause').length; }''')
    try:
        return int(json.loads(r)["output"]["result"])
    except Exception:
        try:
            return int(str(r).strip().strip('"') or 0)
        except Exception:
            return 0


def preview_shots(n_pages: int, sample: list[int] | None, out: Path, doc_id: str | None = None) -> list[dict]:
    """按条款 page_start 聚合逐页截图：对页 N 滚动到第一处 data-page>=N 的 clause
    （即该页起始条），截图 .fulltext 视口；页 1 用顶部。"""
    meta = []
    ev('''() => { const pv=document.querySelector('.fulltext'); if(pv){pv.scrollTop=0;} return 'top'; }''')
    time.sleep(0.5)
    pages = sample if sample else list(range(1, n_pages + 1))
    for i in pages:
        pv = out / f"prev_p{i}.png"
        js = ('''() => { const pv=document.querySelector('.fulltext'); if(!pv) return 'no-fulltext'; const pb=Array.from(pv.querySelectorAll('.page-break')).find(x=>x.dataset.page===''' + str(i) + '''); if(pb){pb.scrollIntoView({block:'start'}); return 'pb' + ''' + str(i) + ''';} const cls=Array.from(pv.querySelectorAll('.fulltext-clause')); const t=cls.find(c=>parseInt(c.dataset.page||'0',10)>=''' + str(i) + '''); if(t){t.scrollIntoView({block:'start'}); return 'p' + ''' + str(i) + ''';} if(pv){pv.scrollTop=''' + str(i) + '''>1?pv.scrollHeight:0;} return 'p' + ''' + str(i) + '''; }''')
        ev(js)
        time.sleep(0.7)
        # 截图前校验 .fulltext 是真实文档预览(有 clause 且高度充足)；否则重开文档，避免截到整窗 QA 页面
        st = str(ev('''()=>{const pv=document.querySelector('.fulltext'); if(!pv) return 'no'; if(!pv.querySelectorAll('.fulltext-clause').length) return 'empty'; if(pv.getBoundingClientRect().height<200) return 'tiny'; return 'ok';}'''))
        if 'ok' not in st and isinstance(doc_id, str):
            print('  [shot] .fulltext 非文档预览(%s) → 重开文档' % st, flush=True)
            b4('open', '--headed', '--fresh', URL); time.sleep(6)
            r = ev('()=>{return typeof window.__ksOpenDoc==="function";}')
            if str(r).strip().lower().startswith('true'):
                ev('()=>{window.__ksOpenDoc(' + json.dumps(doc_id) + '); return "opened";}')
                time.sleep(12)
                ev('()=>{const pv=document.querySelector(".fulltext"); if(pv) pv.scrollTop=0; return "t";}')
                time.sleep(1.2)
                ev(js); time.sleep(0.7)
        b4("screenshot", ".fulltext", "-o", str(pv))
        # browser4 元素截图字节常是 JPEG 却标 .png；按魔数修正扩展名（read_image 需正扩展名）
        if pv.exists():
            head = pv.read_bytes()[:3]
            if head == b"\xff\xd8\xff":
                jp = pv.with_suffix(".jpeg")
                if jp.exists():
                    jp.unlink()
                pv.rename(jp)
                pv = jp
        meta.append({"page": i, "orig": str(out / f"orig_p{i}"), "prev": str(pv),
                     "sampled": sample is not None and i in sample})
        print(f"  prev_p{i} done", flush=True)
    return meta


def compute_sample(n_pages: int, threshold: int, sample_n: int) -> list[int]:
    """巨本限样：首页/末页 + 等距 sample_n 页。"""
    if n_pages <= threshold:
        return None
    pages = {1, n_pages}
    step = max(1, n_pages // sample_n)
    p = 1 + step
    while p < n_pages:
        pages.add(p)
        p += step
    return sorted(pages)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", default=str(TMP / "pagecmp"))
    ap.add_argument("--reingest", action="store_true", dest="reingest")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--pages-threshold", type=int, default=80)
    ap.add_argument("--sample-n", type=int, default=8)
    ap.add_argument("--force-deep", action="store_true", dest="force_deep")
    ap.add_argument("--no-force-deep", action="store_true", dest="no_force_deep")
    a = ap.parse_args()

    pdf = Path(a.pdf)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # 清空上次 orig/prev，保证本次成对截图干净无残留
    for f in list(out.glob("orig_*")) + list(out.glob("prev_*")):
        try:
            f.unlink()
        except Exception:
            pass
    # 正常入库识别流程：默认走 MinerU 深度解析（有 GPU），生成完整 page_breaks/图/表/公式；
    # 仅显式 --no-force-deep 时才走文本层快路径。
    if a.no_force_deep:
        force_deep = False
    else:
        force_deep = True
    print(f"[force_deep] {force_deep} (默认 MinerU 深度解析)", flush=True)

    std_no, std_name = derive_standard(pdf)
    print(f"[std] {std_no!r} / {std_name!r}", flush=True)

    print("[ingest/ensure]", flush=True)
    doc_id = ensure_doc(pdf, a.reingest, force_deep)
    if not a.no_force_deep:
        pass
    print(f"[doc_id] {doc_id}", flush=True)
    stored_std = _db_standard(doc_id)
    print(f"[stored_std] {stored_std!r}", flush=True)

    n_pages = _doc_page_count(pdf)
    print(f"[pages] {n_pages}", flush=True)

    sample = compute_sample(n_pages, a.pages_threshold, a.sample_n)
    print(f"[sample] {'full' if sample is None else sample}", flush=True)

    print("[orig] render", flush=True)
    orig_meta = render_orig(pdf, n_pages, out)

    manifest = list(orig_meta)
    if not a.no_preview:
        open_std = stored_std or std_no
        print(f"[prev] open {open_std!r} / {doc_id}", flush=True)
        doc_open(doc_id, open_std)
        print("[prev] wait for .fulltext", flush=True)
        for _ in range(20):
            if _preview_page_count() > 0:
                break
            time.sleep(1)
        prev_count = _preview_page_count()
        print(f"[prev] preview page marks={prev_count}", flush=True)
        meta = preview_shots(n_pages, sample, out, doc_id)
        # 融合：orig 全页，prev 采样/全页按实际生成
        prev_by_page = {m["page"]: m for m in meta}
        merged = []
        for m in orig_meta:
            pm = prev_by_page.get(m["page"])
            merged.append({"page": m["page"], "orig": m["orig"],
                           "prev": pm["prev"] if pm else None,
                           "sampled": bool(pm and pm.get("sampled"))})
        manifest = merged

    (out / "manifest.json").write_text(
        json.dumps({"doc_id": doc_id, "standard_no": std_no, "standard_name": std_name,
                    "stored_standard_no": stored_std, "n_pages": n_pages, "sample": sample,
                    "pairs": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[done] 成对截图清单: {out}", flush=True)
    print(f"[done] manifest.json 已写（{len(manifest)} 页）", flush=True)
    print("VLM 逐页对比：read_image 每页 orig_pN.png + prev_pN.png", flush=True)


if __name__ == "__main__":
    main()
