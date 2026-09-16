"""OCR 循环任务·工具1：候选国标选择器。
从 35000+ 库里选下一部待导入国标——规则：
1. 只选 GB/GJB/HJ 等「标准」类 PDF（跳过法律/规范类）；
2. 与已入库 28 部 + 已试失败清单去重；
3. 优先扫描件特征明显的（后续轮次按体量/多样性轮换）。
产物：var/ocr-loop/next_pick.json（本轮选定 + 已排除清单快照）。"""
import sys, io, os, json, sqlite3, random, re as _re
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 原地改，勿包新 wrapper
ROOT = Path(r"D:\AI\work space\zcode")
LIB = Path(r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)")
VARDIR = ROOT / "var" / "ocr-loop"
VARDIR.mkdir(parents=True, exist_ok=True)


def _norm(s: str) -> str:
    """标准号归一：全角→半角、去所有空白、大写——文件名/库内号可比。"""
    s = s.replace("／", "/").replace("－", "-").upper()
    return _re.sub(r"\s+", "", s or "")


def in_library_titles() -> set:
    db = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT standard_no, standard_name FROM doc_meta").fetchall()
    conn.close()
    return {_norm(r[0] or "") for r in rows} | {_norm(r[1] or "") for r in rows}


def _has_text_layer(pdf: Path) -> bool | None:
    """前 5 页文本层探测：有→文本层文档（OCR 质检无信号，靠后选）；
    无→真扫描件（优先）；探测失败→None（中性）。"""
    try:
        import fitz
        with fitz.open(pdf) as doc:
            pages = min(5, doc.page_count)
            chars = sum(len((doc[i].get_text() or "").strip())
                        for i in range(pages))
            return chars > 50
    except Exception:
        return None


def main() -> None:
    done = in_library_titles()
    tried = set()
    tp = VARDIR / "tried.json"
    if tp.exists():
        tried = {_norm(x) for x in json.loads(tp.read_text(encoding="utf-8"))}
    # 扫 GBT 目录（当前 28 部库内文档主要来源段）
    segs = ["GBT 00001 - GBT 10000", "GBT 10001 - GBT 20000"]
    cands = []
    for seg in segs:
        d = LIB / "GBT" / seg
        if not d.exists():
            continue
        for f in d.glob("*.pdf"):
            name = f.stem
            # 三键去重：全串 / 号段 / 号段+年份（库内号形如 GB/T1.1-2020 无空格）
            squashed = _norm(name)
            m = _re.match(r"(GB/T?\d+(?:\.\d+)?)(?:[-—](\d{4}))?", squashed)
            num_key = m.group(1) if m else None          # GB/T1.1
            num_year = f"{m.group(1)}-{m.group(2)}" if m and m.group(2) else None
            if any(k in done for k in (squashed, num_key, num_year) if k) \
               or squashed in tried:
                continue
            # 只挑 GB/T 单行本（非合订/非目录/非纯图形类——图形符号标准无文本层，
            # OCR 循环质检无条款可检，2026-09-14 轮次1实测 900s 超时）
            if any(w in name for w in ("目录", "合订", "图形符号", "标志", "标识")):
                continue
            cands.append(f)
    print(f"candidates: {len(cands)} (library={len(done)}, tried={len(tried)})")
    if not cands:
        print("NO CANDIDATES")
        return
    # 固定顺序：按文件名排序取首个未试（tried 存归一化文件名全串）。
    # 2026-09-14 轮次 3 起：真扫描件（无文本层）优先——OCR 循环质检的价值
    # 全在扫描通道（文本层文档 conf 恒 1.0 无信号，实测 GB/T 10004-2008）。
    # 轮次 9 起探测持久缓存（text_layer_probe.json）：每轮只探**未探过**的
    # 60 本，累积扫描件池跨轮复用，不再重探同一批（前 60 全文本层时轮次 7-9
    # 空转 3 轮的教训）。
    cands.sort(key=lambda p: p.name)
    untried = [f for f in cands if _norm(f.stem) not in tried]
    cache_p = VARDIR / "text_layer_probe.json"
    cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}
    to_probe = [f for f in untried if _norm(f.stem) not in cache][:60]
    for f in to_probe:
        cache[_norm(f.stem)] = _has_text_layer(f)
    cache_p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    scanned = [f for f in untried
               if cache.get(_norm(f.stem)) is False]
    pool = scanned or untried
    pick = pool[0] if pool else None
    if pick is None:
        print("ALL TRIED")
        return
    out = {"pick": str(pick), "stem": pick.stem,
           "candidates_remaining": len(cands) - 1,
           "scanned_pool": len(scanned),
           "probed_total": len(cache)}
    (VARDIR / "next_pick.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("PICK:", pick.stem)
    print("size_mb:", round(pick.stat().st_size / 1048576, 1),
          f"| scanned_pool: {len(scanned)} | probed: {len(cache)}")


if __name__ == "__main__":
    main()
