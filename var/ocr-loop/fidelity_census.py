# -*- coding: utf-8 -*-
"""独立保真度普查：**不信任**循环的判据，直接量条款文本 + 与文本层真值对差。

为什么要独立量（2026-09-15）：循环的"零命中 = 干净"只覆盖 7 条正则 +
若干条件分支，且全部跑在**清洗后的条款文本**上。要回答"OCR 是不是完美"，
必须用**它不看的仪器**去量同一批产物：

  A. 症状普查（在它自己的判据域内 = 条款文本）：清洗前 / 清洗后各来一遍，
     看清洗链**掩盖**了多少可观测症状；
  B. 真值对差（文本层）：有文本层的 PDF，其文字层就是**逐字真值**；
     逐页比字符数与三元组召回 → 抓"整页丢内容 / 重复输出 / 幻觉补字"；
  C. 引擎自报置信：`ocr_confidence` 低的条款有多少、其中有多少被它的判据
     判为"干净"。

只读：不写库、不写 state、不调云、不改产物（只用 `middle_locator` 定位 +
`pipeline` 的切分器，均无写副作用）。
"""
from __future__ import annotations

import json
import os
import re
import sys
import collections
import unicodedata
from pathlib import Path

ROOT = Path(r"D:\AI\work space\zcode")
HERE = ROOT / "var" / "ocr-loop"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import artifact_index as AI                     # noqa: E402
from src.core.ingestion.middle_locator import find_middle_files   # noqa: E402
from src.core.ingestion.pipeline import (                          # noqa: E402
    load_middle_items, split_items_into_clauses, build_clause_models,
    strip_figure_legend_segment)
from src.core.text_utils import clean_clause_text                  # noqa: E402
import audit_text as A                                             # noqa: E402
import classify as C                                               # noqa: E402

# ---------------------------------------------------------------- 症状判据
#: 每条都要求**明确不可辩解**（宁少勿滥，避免把合法写法算成缺陷）。
SYMPTOMS: list[tuple[str, re.Pattern]] = [
    ("replacement-char", re.compile(r"\ufffd")),
    ("pua-residue", re.compile(r"[\ue000-\uf8ff]")),
    ("control-or-zwsp", re.compile(r"[\x00-\x08\x0b-\x1f\u200b-\u200f\ufeff]")),
    ("placeholder-glyph", re.compile(r"[□■▯◻◼]")),
    ("dot-leader-run", re.compile(r"…{3,}|\.{6,}")),
    # 已删除判据：逐字符拉开（真缺陷形态 '1 . 0 mm' 之外，这里只要求 ≥3 个"单字符+空白"对）
    ("spaced-run(已删判据)", re.compile(r"(?<![一-鿿])(?:[A-Za-z0-9₀-₉⁰-⁹][ \t]){3,}")),
    ("split-value", re.compile(
        r"(?<![\d.])(?:\d[ \t]+\d{2,4}|\d{1,2}[ \t]+0\d)\s*"
        r"(?:µ|μ|mm|cm|kg|mg|g|ms|min|mL|L|m|s|V|A|N|W|Hz|Pa|kV)\b")),
    ("unit-midspace", re.compile(
        r"\b(?:k\s+g|m\s+i\s+n|m\s+m|c\s+m|d\s+m|n\s+m|k\s+V|m\s+V|m\s+A|k\s+W|"
        r"k\s+J|M\s+Pa|H\s+z|p\s+H|k\s+N|m\s+L|m\s+s)\b")),
    ("latex-leak", re.compile(r"\\mathrm|\\Nu|\\begin\{|\\frac")),
    ("mfr-unit-misread", re.compile(r"·\s*∞|τ\s*r\s*/\s*min")),
]
#: 低置信阈值（与 evolve.LOW_CONF 同口径）
LOW_CONF = 0.6


def _del_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s)


def page_texts_by_idx(mid: Path) -> dict[int, str]:
    """产物逐页文本，按 `page_idx`（0 基）配对——**不是按列表顺序**。

    **两个实测坑（都曾把"没丢"报成"丢了"）**：
    ① **表格文本住在 `html` / `table_body` 字段里**，不在 `spans[].content`：
       实测 `GB／T 8321.4-2006` 第 4–9 页全是农药用量大表，只读 spans 会得到
       "整页 0 字"→ 误报 88% 内容丢失；读 `html` 后该页 2,366 字符俱在。
    ② **必须用 `page_idx` 配对**：列表顺序与 PDF 页序不保证一致，
       错位一格就会把逐页比对变成噪声。
    """
    try:
        obj = json.loads(mid.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    pages = obj.get("pdf_info") if isinstance(obj, dict) else None
    if not pages:
        return {}

    def collect(node, buf: list[str]) -> None:
        if isinstance(node, dict):
            spans = node.get("spans")
            if isinstance(spans, list):
                for sp in spans:
                    if isinstance(sp, dict) and isinstance(sp.get("content"), str):
                        buf.append(sp["content"])
            for key in ("html", "table_body"):
                v = node.get(key)
                if isinstance(v, str) and v.strip():
                    buf.append(_del_html(v))
            if "spans" not in node:
                for key in ("content", "text"):
                    v = node.get(key)
                    if isinstance(v, str) and v.strip():
                        buf.append(v)
            # **遍历一切子键**（只回避 `discarded_blocks`＝页眉页脚/页码，管线主动丢弃）：
            # 实测按白名单遍历 para_blocks/blocks/lines 会漏掉表格 html 所在的子树，
            # 把"表格在产物里"误报成"整页丢内容"（`GB／T 24915-2020` 第 5 页即此坑）。
            for k, v in node.items():
                if k in ("discarded_blocks", "spans"):
                    continue
                if isinstance(v, (dict, list)):
                    collect(v, buf)
        elif isinstance(node, list):
            for x in node:
                collect(x, buf)

    out: dict[int, str] = {}
    for i, pg in enumerate(pages):
        buf: list[str] = []
        collect(pg, buf)
        idx = pg.get("page_idx")
        out[int(idx) if isinstance(idx, int) else i] = "\n".join(buf)
    return out


def truth_is_plausible(t: str, min_chars: int = 60) -> bool:
    """文本层是否为**可用真值**（拒绝乱码层）。

    **实测必须判**：`GB／T 8321.4-2006` 的文字层是 `!"#!"!#$$$#%!"#$%&’’()*%$…`
    （缺字形/非标准 CMap），拿它当真值会把**正确的中文 OCR 报成 0.0002 召回**。
    判据：去空白后 ≥60 字且「汉字+ASCII 字母数字」占比 ≥85%（乱码层符号占比高）。
    """
    s = re.sub(r"\s+", "", t)
    if len(s) < min_chars:
        return False
    good = sum(1 for ch in s
               if "\u4e00" <= ch <= "\u9fff" or (ch.isascii() and ch.isalnum()))
    return good / len(s) >= 0.85


def product_pages(items) -> dict[int, str]:
    """**用所有者加载器**（`load_middle_items` 的产物）拼逐页文本。

    为什么不再自己遍历 JSON：表格内容住在 `spans[].html`（`type='table'`），
    不在 `spans[].content`；自己写白名单遍历会漏（实测把"表格在产物里"误报成
    "整页 0 字 → 88% 内容丢失"）。`load_middle_items` 是管线唯一所有者，
    它认得 `content` / `html` / `caption` / `image_path`，且**顺手完成管线自己的
    丢弃**（页眉页脚/水印/页码）——正是要比较的口径。
    """
    by: dict[int, list[str]] = {}
    for it in items:
        t = it.text or ""
        h = getattr(it, "html", None)
        if h:
            t = (t + " " + _del_html(h)).strip()
        by.setdefault(int(it.page_idx), []).append(t)
    return {k: "\n".join(v) for k, v in by.items()}


#: 对称归一：水印 URL / 独立页码行（两侧都去掉，避免把"管线主动丢弃的页眉页脚"
#: 算成识别损失，也避免把真值里的水印算成产物缺失）。
_NOISE_LINE = re.compile(r"^\s*(?:www\.[\w.\-]+|[\w.\-]+\.(?:com|cn|net)|\d{1,3}|[ivxlcIVXLC]{1,5})\s*$")
#: 水印/下载站关键词（实测 `学兔兔 www.bzfxw.com 标准下载` 形态，`_NOISE_LINE` 拦不住）。
_NOISE_KW = re.compile(r"bzfxw|学兔兔|标准下载|标准分享网|www\.")
#: 页眉页脚形态：单独一行的标准号（`GBZ 37—2024` / `GB／T 24915—2020`）——管线主动丢弃。
_RUNNING_HEAD = re.compile(
    r"^[A-Z]{2,4}\s*[／/]?\s*T?\s*[\d.．\-—]+\s*[-—]?\s*\d{0,4}$")


def norm_form(s: str) -> str:
    """**形态归一**：NFKC（全角数字/字母/标点 → ASCII，U+3000 → 空格）。

    **为什么必须做**：GB 标准文字层大量使用全角（`７．２　设备到货时间`、
    `１）　本参考合同`、`／`），而 OCR 产物是半角。不归一会把**同一条内容**判成
    "产物里找不到"，把"形态差异"误报成"内容丢失"（实测前者占未命中行的大半）。
    """
    return unicodedata.normalize("NFKC", s)


def norm_lines(t: str) -> list[str]:
    out = []
    for ln in t.splitlines():
        s = ln.strip()
        if not s or _NOISE_LINE.match(s) or _NOISE_KW.search(s) \
                or _RUNNING_HEAD.match(s):
            continue
        out.append(s)
    return out


def line_match(truth: str, prod_grams: set[str]) -> tuple[int, int, list[str]]:
    """真值逐行能否在产物里找到对应（≥80% 的三元组被覆盖即算"有"）。

    返回 `(总行数, 命中行数, 未命中行样例)`。这是**可读的保真度**：
    "这一页的每一行，产物里还有没有"。两侧都过 `norm_form`。
    """
    tot = hit = 0
    miss: list[str] = []
    for ln in norm_lines(truth):
        s = re.sub(r"\s+", "", norm_form(ln))
        if len(s) < 10:
            continue
        tot += 1
        gs = {s[i:i + 3] for i in range(len(s) - 2)}
        if gs and len(gs & prod_grams) / len(gs) >= 0.80:
            hit += 1
        elif len(miss) < 40:
            miss.append(ln[:120])
    return tot, hit, miss


def census(text: str) -> dict[str, int]:
    return {name: len(pat.findall(text)) for name, pat in SYMPTOMS
            if pat.search(text)}


def trigrams(s: str) -> collections.Counter:
    s = re.sub(r"\s+", "", s)
    return collections.Counter(s[i:i + 3] for i in range(max(0, len(s) - 2)))


def recall(truth: str, cand: str) -> tuple[float, int]:
    """真值三元组在候选里被覆盖的比例（内容保留度）。返回 (比例, 真值三元组数)。"""
    t, c = trigrams(truth), trigrams(cand)
    if not t:
        return 1.0, 0
    hit = sum(min(v, c.get(k, 0)) for k, v in t.items())
    return hit / sum(t.values()), sum(t.values())


def main() -> None:
    bn = sys.argv[1] if len(sys.argv) > 1 else "4"
    stride = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    bp = HERE / "evolve" / f"work_batch{bn}.json"
    paths = json.loads(bp.read_text(encoding="utf-8"))["paths"][::stride][:limit]
    state = json.loads((HERE / "vlm_ocr_state.json").read_text(encoding="utf-8"))
    import fitz

    raw_sym: collections.Counter = collections.Counter()
    clean_sym: collections.Counter = collections.Counter()
    engine_cls: collections.Counter = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)
    docs_done = docs_with_sym = 0
    clauses_total = 0
    low_conf = low_conf_clean = 0
    tl_docs = 0
    tl_page_gap: list[tuple[str, int, int, int]] = []   # (std_no, page, truth, ocr)
    tl_recall: list[tuple[str, float, float, int]] = []  # (std_no, recall, ratio, truth_n)
    line_tot = line_hit = 0
    line_miss_examples: list[tuple[str, int, list[str]]] = []
    #: 结构性盲区计量（判据域 vs 产物全部内容）
    audited_chars = table_chars = img_items = truncated_clauses = truncated_chars = 0
    product_page_short: list[tuple[str, int, int]] = []

    for p in paths:
        stem = Path(p).stem
        rec = state.get(stem) or {}
        if rec.get("status") != "ok":
            continue
        mid_files = find_middle_files(Path(rec.get("out") or "")) or \
            find_middle_files(Path(rec.get("out") or "").parent)
        if not mid_files:
            continue
        docs_done += 1
        mid = mid_files[0]
        try:
            items, page_sizes = load_middle_items(mid)
            split = split_items_into_clauses(items)
            models, _ = build_clause_models("probe", stem, "standard", split, page_sizes)
        except Exception as ex:  # noqa: BLE001
            print(f"  [跳过] {stem[:40]}: {type(ex).__name__}: {str(ex)[:60]}")
            continue
        doc_raw: collections.Counter = collections.Counter()
        doc_clean: collections.Counter = collections.Counter()
        for m in models:
            clauses_total += 1
            rt = m.content_text or ""
            audited_chars += len(rt)
            ct = clean_clause_text(rt, legend_stripper=strip_figure_legend_segment)
            doc_raw.update(census(rt))
            doc_clean.update(census(ct))
            for cls in A.audit_clause(ct):
                engine_cls[cls] += 1
            for cls in C.classify_clause(m.clause_number or "", ct,
                                         m.ocr_confidence or 1.0):
                engine_cls[cls] += 1
            if (m.ocr_confidence or 1.0) < LOW_CONF:
                low_conf += 1
                if not census(ct):
                    low_conf_clean += 1
        # **结构性盲区计量**：判据只看 content_text（表格 html 不在其中，且截断 4000 字）
        table_chars += sum(len(_del_html(it.html or "")) for it in items
                           if getattr(it, "kind", "") == "table")
        img_items += sum(1 for it in items if getattr(it, "kind", "") == "image")
        for cl in split:
            full = "\n".join(r[0] for r in cl.rows)
            if len(full) > 4000:
                truncated_clauses += 1
                truncated_chars += len(full) - 4000
        raw_sym.update(doc_raw)
        clean_sym.update(doc_clean)
        if doc_raw:
            docs_with_sym += 1
            for name in doc_raw:
                if len(examples[name]) < 3:
                    for m in models:
                        t = m.content_text or ""
                        mm = dict(SYMPTOMS)[name].search(t)
                        if mm:
                            s = max(0, mm.start() - 40)
                            examples[name].append(
                                f"{stem[:34]} · 条款 {m.clause_number or '?'}: "
                                f"…{t[s:mm.end() + 40].replace(chr(10), ' ')}…")
                            break

        # ---- B. 真值对差（文本层，**只信可信的文本层**）----
        try:
            d = fitz.open(p)
            truth_pages = [pg.get_text() or "" for pg in d]
            d.close()
        except Exception:  # noqa: BLE001
            continue
        valid = [i for i, t in enumerate(truth_pages) if truth_is_plausible(t)]
        if len(valid) < 3 or sum(len(re.sub(r"\s+", "", truth_pages[i]))
                                 for i in valid) < 800:
            continue                     # 无文本层 / 文本层是乱码 → 本机无真值，如实不计
        tl_docs += 1
        ppage = product_pages(items)
        prod_all = norm_form("".join(_del_html(ppage.get(i, "")) for i in valid))
        prod_all = re.sub(r"\s+", "", prod_all)
        prod_grams = {prod_all[j:j + 3] for j in range(max(0, len(prod_all) - 2))}
        truth_join, ocr_join = [], []
        for i in valid:
            truth_join.append(truth_pages[i])
            ocr_join.append(ppage.get(i, ""))
            tn = len(re.sub(r"\s+", "", "".join(norm_lines(truth_pages[i]))))
            on = len(re.sub(r"\s+", "", _del_html(ppage.get(i, ""))))
            if tn >= 120 and on < 0.5 * tn:
                tl_page_gap.append((stem, i + 1, tn, on))
        tr, tn3 = recall("".join(truth_join), "".join(ocr_join))
        t_n = len(re.sub(r"\s+", "", "".join(truth_join)))
        o_n = len(re.sub(r"\s+", "", _del_html(prod_all)))
        tl_recall.append((stem, tr, o_n / max(1, t_n), tn3))
        for i in valid:
            a, b, miss = line_match(truth_pages[i], prod_grams)
            line_tot += a
            line_hit += b
            if miss and len(line_miss_examples) < 25:
                line_miss_examples.append((stem, i + 1, miss[:3]))

    print(f"\n{'='*72}\n批次 #{bn} 抽样 {len(paths)} 部 · 成功解析 {docs_done} 部 · "
          f"条款合计 {clauses_total}\n{'='*72}")

    print("\n【A】症状普查（**条款文本**域，与循环判据同域）")
    print(f"{'症状':<24}{'清洗前':>8}{'清洗后':>8}   被清洗链掩盖")
    for name, _ in SYMPTOMS:
        r, c = raw_sym.get(name, 0), clean_sym.get(name, 0)
        if r or c:
            print(f"{name:<24}{r:>8}{c:>8}   {r - c:>6}")
    print(f"→ 清洗前有症状的文档 {docs_with_sym}/{docs_done}"
          f"（{docs_with_sym/max(1,docs_done):.1%}）· 清洗前症状总计 {sum(raw_sym.values())} · "
          f"清洗后 {sum(clean_sym.values())}")

    print("\n【A'】循环自己的判据（在**清洗后**条款文本上）——即「零命中」的来源")
    if engine_cls:
        for k, v in engine_cls.most_common():
            print(f"    {k:<28}{v:>6} 条")
    else:
        print("    （无命中）→ 与循环报告的「零命中」一致")

    print("\n【C】引擎自报置信")
    print(f"    ocr_confidence < {LOW_CONF} 的条款：{low_conf} / {clauses_total}"
          f"（{low_conf/max(1,clauses_total):.1%}），其中**被症状普查判为干净**的 {low_conf_clean} 条")

    print("\n【B】文本层真值对差（有**可信**文本层的文档 = 逐字真值）")
    if tl_docs:
        rs = sorted(x[1] for x in tl_recall)
        ratios = sorted(x[2] for x in tl_recall)
        print(f"    覆盖文档 {tl_docs} 部 · 真值三元组召回："
              f"最低 {rs[0]:.3f} · 中位 {rs[len(rs)//2]:.3f} · 最高 {rs[-1]:.3f}")
        print(f"    OCR/真值 字符数比：最低 {ratios[0]:.3f} · "
              f"中位 {ratios[len(ratios)//2]:.3f} · 最高 {ratios[-1]:.3f}")
        if line_tot:
            print(f"    **逐行保真**：真值 {line_tot} 行（≥10 字）里，产物能找到对应的 "
                  f"{line_hit} 行 = {line_hit/max(1,line_tot):.1%}")
        bad = [x for x in tl_recall if x[1] < 0.995]
        print(f"    召回 < 0.995 的文档：{len(bad)}/{tl_docs}")
        for st, tr, ratio, tn3 in sorted(bad, key=lambda x: x[1])[:10]:
            print(f"      {tr:.4f}  OCR/真值={ratio:.3f}  真值三元组 {tn3:>7}  {st[:52]}")
        print(f"    整页疑似丢内容（真值 ≥120 字而产物 <50%）：{len(tl_page_gap)} 页")
        for st, pg, tn, on in tl_page_gap[:10]:
            print(f"      {st[:44]} 第 {pg} 页  真值 {tn} 字 → 产物 {on} 字")
    else:
        print("    （抽样里没有带可信文本层的文档）")

    if line_miss_examples:
        print("\n【B'】真值里**找不到对应**的行（抽样，判性质用）")
        for st, pg, miss in line_miss_examples[:8]:
            print(f"  ── {st[:40]} 第 {pg} 页")
            for m in miss:
                print(f"       {m}")

    if examples:
        print("\n【证据】症状实例（可直接回原文核对）")
        for name, exs in examples.items():
            print(f"  ── {name}（清洗前 {raw_sym.get(name,0)} 处 / 清洗后 {clean_sym.get(name,0)} 处）")
            for e in exs:
                print(f"       {e}")
    print("\n【D】判据的**结构性盲区**（这决定了「零命中」能说明什么）")
    tot_c = audited_chars + table_chars
    print(f"    判据能看到的正文（content_text 合计）：{audited_chars:,} 字")
    print(f"    **判据看不到的表格正文（html，只进 content_markdown）**：{table_chars:,} 字"
          f" = 全部正文的 {table_chars/max(1,tot_c):.1%}")
    print(f"    判据看不到的插图：{img_items} 处（图内文字不进条款文本）")
    print(f"    **超 4000 字被截断的条款**：{truncated_clauses} 条 · 未审计字符 {truncated_chars:,}"
          f"（`content_text = rows[:4000]`）")

    out = HERE / "evolve" / f"fidelity_census_b{bn}.json"
    out.write_text(json.dumps({
        "batch": bn, "sampled": len(paths), "parsed": docs_done,
        "clauses": clauses_total,
        "raw_symptoms": dict(raw_sym), "clean_symptoms": dict(clean_sym),
        "engine_classes": dict(engine_cls),
        "docs_with_raw_symptom": docs_with_sym,
        "low_conf": low_conf, "low_conf_but_clean": low_conf_clean,
        "audited_chars": audited_chars, "table_chars": table_chars,
        "image_items": img_items,
        "truncated_clauses": truncated_clauses, "truncated_chars": truncated_chars,
        "line_total": line_tot, "line_hit": line_hit,
        "textlayer_docs": tl_docs,
        "textlayer_recall": [[s, round(r, 4), round(x, 4), n] for s, r, x, n in tl_recall],
        "textlayer_page_gaps": tl_page_gap[:200],
        "examples": {k: v for k, v in examples.items()},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ 明细：{out}")


main()
