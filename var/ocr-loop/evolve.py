# -*- coding: utf-8 -*-
"""国标 OCR 后处理**自进化调试循环**（2026-09-15 立，5-verifier 胜出方案）。

用户规格（逐条落实，见 `evolve/README.md`）：
 1. 每次只处理**一部**文档，处理完立刻审计该部问题，再继续下一部。
 2. 同一类问题**累计命中 3 部文档**即触发根因修复；修完后**从第 1 部重启**（轮的边界）。
 3. 每轮结果**永不删除**（append-only：`evolve/rounds/round-NNN/`）。
 4. **每 5 轮横向对比**：问题是否在越修越少。
 5. 若没有越修越少 → **5 个 verifier** 读「修复历史 + 各轮结果」分析原因。
 6. **全程不落库**：这是纯调试/自进化装置，不写 `doc_meta`/`clause_revision`，
    不动 `parse_out/`，不调云、不占 GPU（详见 `doctor` 的调用图核验与 DB 哨兵）。
 7. 已被真实教训验证的机制：检测器哈希（防仪器漂移误归因）、稳定身份
    （standard_no / 产物稳定索引，不依赖会重发的 doc_id）、单文档灾难性退化护栏、
    不可恢复性度量（假头注入）、误报检测器优先删除。

命令：
  doctor                      只读自检（DB 哨兵 / 检测器哈希 / 产物覆盖）
  index                       重建产物稳定索引
  eval --round N [--limit N]  跑一轮（逐部评估，同类第 3 部即停并交接）
  resume --round N            中断后续跑（幂等：已评估的 skips）
  status                      当前轮/游标/触发类
  compare --window 5          五轮横比（可计算指标 + 判定）
  escalate --window 5         生成 5 份 verifier 提示词（不自行调用模型）
  arbiter plan --class X      五视角修复方案征集（六字段 schema，缺字段判无效）
  arbiter score --file p.json 候选方案 → 盲评四维（各 1–4）→ 取前二实测
  arbiter decide --cls X [--winner F]   实测步骤 + 决策台账（append-only）
  arbiter check [--base-round N] [--cur-round M]   完整样本复核（新冒类>3 或某类升>20% 判失败）
  fix-done --class X --commit SHA --note "…"   修复者回报，关轮 → 下一轮从第 1 部
  poison-test [--std-no …]    假头注入：单文档不可恢复性度量
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import artifact_index as AI   # noqa: E402
import sweep as SW            # noqa: E402 —— 检测器/身份/阈值单一所有者

EVOLVE = HERE / "evolve"
ROUNDS = EVOLVE / "rounds"
WINDOWS = EVOLVE / "windows"
ESCAL = EVOLVE / "escalations"
STATE = EVOLVE / "state.json"
INSTRUMENT = EVOLVE / "instrument.jsonl"
SENTINEL = EVOLVE / "db_sentinel.jsonl"
FIXES = EVOLVE / "fixes.jsonl"
LEDGER = HERE / "fixed_classes.json"

FIX_LINE = SW.FIX_LINE                 # 3：同类命中 3 部文档即达修复线
PREFLIGHT_RATIO = 0.6                  # 条款数跌到 60% 以下判灾难性退化
PREFLIGHT_MIN_DOC = 5
LOW_CONF = 0.85


def db_path() -> str:
    from src.core.config import get_settings
    return str(get_settings().db_path)


def ro(sql: str, args: tuple = ()) -> list[Any]:
    """**唯一允许的 DB 接触**：只读 URI。

    顺带做**写语句闸**：本函数是全循环唯一的 DB 入口，若有人把 INSERT/UPDATE/
    DELETE 传进来，立即计数并在停轮时报告——把"我们是否写库"从"靠代码审查"
    变成**运行时可证**（见 `db_write_attempts`）。
    """
    up = sql.lstrip().upper()
    if up.startswith(("INSERT", "UPDATE", "DELETE", "REPLACE", "DROP", "CREATE",
                      "ALTER")):
        global _DB_WRITE_ATTEMPTS
        _DB_WRITE_ATTEMPTS += 1
        raise RuntimeError(f"循环禁止写库：ro() 收到写语句 {sql[:60]!r}")
    conn = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


#: 本轮内尝试写库的次数（恒应为 0；非 0 即真违规，由停轮报告区分于外部写）。
_DB_WRITE_ATTEMPTS = 0


def db_sentinel() -> str:
    """DB 指纹：大小/mtime/行数 —— 变了说明**有人**写库。

    **归因是关键**（2026-09-15 实测教训）：本指纹把"我们写库"与"**别的程序写库**"
    混为一谈。实测 KnowledgeStation 主程序（`src.core.main`，用户 GUI）常驻运行时
    **持续写 WAL**（11 MB、秒级刷新），于是每一轮都触发"DB 被写入→停轮"，
    把循环彻底卡死——而 `doctor` 的源码核验与 `ro()` 写语句闸都证明**我们一个字
    都没写**。

    处置：指纹照旧（仍能发现异常），但停轮时**必须归因**——只有
    `_DB_WRITE_ATTEMPTS > 0` 或源码核验失败才算我方违规；否则记为
    `external-write` 并继续（外部 app 的写与本循环的不落库纪律无关）。
    """
    p = Path(db_path())
    st = p.stat()
    n_doc = ro("SELECT COUNT(*) FROM doc_meta")[0][0]
    n_cls = ro("SELECT COUNT(*) FROM clause_revision")[0][0]
    h = hashlib.sha256()
    h.update(f"{st.st_size}|{st.st_mtime_ns}|{n_doc}|{n_cls}".encode())
    return h.hexdigest()[:16]


def detector_hash() -> str:
    return SW.detector_hash()


def owner_hash() -> str:
    """被修对象（后处理所有者层）指纹——修复会让它变，属预期。"""
    h = hashlib.sha256()
    for rel in ("src/core/ingestion/pipeline.py", "src/core/text_utils.py",
                "src/core/ingestion/middle_locator.py"):
        f = ROOT / rel
        if f.exists():
            h.update(f.read_bytes())
    return h.hexdigest()[:12]


def fixed_ledger() -> dict:
    if LEDGER.exists():
        try:
            return json.loads(LEDGER.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


#: 登记为「不接受修复」的类：**仍照常计数上报**（诚实口径），但**不驱动修复轮**。
#: 两类：
#:   不修       —— 故意不修（先例 `absorbed-trailing-digits`：源文本歧义，
#:                 启发式会误伤合法长号）
#:   已知限制   —— 该类的成因不在后处理层（先例 `appendix-table-lowconf`：
#:                 它是**识别层置信度**难度，表格密集区 conf 0.59~0.67，
#:                 文本内容本身正确；本循环的目标是后处理，故只登记不改判据）
#: 「未达线」不在其列——那是"累计中"，仍需触发。
_ACCEPTED_MARKERS = ("不修", "已知限制")


def accepted_limitations() -> dict[str, str]:
    """类 → 登记理由（不驱动修复的类）。"""
    out: dict[str, str] = {}
    for cls, e in fixed_ledger().items():
        c = str(e.get("commit", ""))
        if any(m in c for m in _ACCEPTED_MARKERS):
            out[cls] = c[:80]
    return out


def atomic_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ 文档清单
def doc_list() -> list[dict]:
    """库内文档（稳定身份 = standard_no；顺序 = standard_no 升序，可复现）。"""
    rows = ro("SELECT doc_id, standard_no, standard_name, file_path, file_hash "
              "FROM doc_meta ORDER BY standard_no")
    out = []
    for i, r in enumerate(rows, 1):
        out.append({"i": i, "doc_id": r[0], "std_no": r[1] or r[0],
                    "std_name": r[2] or "", "file_path": r[3] or "",
                    "file_hash": r[4] or ""})
    return out


def docs_for(corpus: bool) -> list[dict]:
    """文档清单来源：`corpus=True` → **新语料工作集**（未入库文档），否则库内。

    2026-09-15（用户指令）：原 260 部被反复审计已过拟合，换成全新文档继续循环。
    新文档尚未入库，`doc_list()` 看不到它们，故走 `corpus_docs`（同形记录、
    `doc_id` 留空 → `artifact_index` 按源 PDF 名稳定键定位产物）。
    """
    if not corpus:
        return doc_list()
    import corpus_docs  # noqa: PLC0415 —— 惰性导入：库内路径不依赖清单文件
    return corpus_docs.work_docs()


def order_hash(docs: list[dict]) -> str:
    h = hashlib.sha256()
    for d in docs:
        h.update(f"{d['std_no']}|{d['file_hash']}".encode())
    return h.hexdigest()[:12]


# ------------------------------------------------------------------ 单部评估
def parse_backend_of(mid_path: Path) -> str:
    """产物自带的解析后端标记（`_backend`）——**通道可判别**。

    2026-09-15（用户指令「必须用 VLM，pipeline 不参与本次循环进化」）：
    VLM 产物与历史 pipeline 产物会同时存在于语料里，横比若不分通道，
    就把两种仪器的结果当成一个。

    实现注意（两次踩坑）：
    ① 产物是**大 JSON**（MB 级），截断后 `json.loads` 必然失败 → 用正则；
    ② `_backend`/`_version_name` 在文件**末尾**（实测 GB/T 10002.1 的
       `_backend` 位于 1,367,600 字节处，而 pdf_info 在前）→ **读尾部** 4KB，
       读头部永远拿不到（会恒返回 unknown，等于没有通道判别）。
    """
    import re as _re
    try:
        size = mid_path.stat().st_size
        with open(mid_path, "rb") as f:
            f.seek(max(0, size - 4096))
            tail = f.read().decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return "unknown"
    for key in ("_backend", "_version_name"):
        m = _re.search(r'"' + key + r'"\s*:\s*"([^"]*)"', tail)
        if m and m.group(1).strip():
            return m.group(1).strip().lower()
    return "unknown"


#: 类 → 取证正则。**audit_text.CHECKS 之外的分类器类**没有独立正则（判据写在
#: `classify.classify_clause` 的条件分支里），故在此显式登记其"缺陷签名"正则——
#: 只用于**摘命中原文**，不参与判定（判定仍在 classify 单一所有者处）。
#:
#: **口径纪律**：能引用所有者对象就别抄字面量。本表曾抄 `classify._RE_TOC_LINE`
#: 的旧形态，收窄判据后未同步 → 取证静默返回 0 条（实测踩过）。凡所有者有编译
#: 好的正则对象，一律在 `_evidence_patterns()` 里**直接引用**，杜绝二次漂移。
_EVIDENCE_PATTERNS: dict[str, str] = {
    "ocr-wide-space-units": r"(?<![一-鿿])(?:[A-Za-z0-9₀-₉⁰-⁹][ \t\u00a0]){3,}",
    "punctuation-substitution": r"(?<![A-Za-z0-9µμ°%])(?<![A-Za-z])[A-Z],\d",
    "figure-neighborhood": r"(?:\d{1,3}\s*[—–]{2,}[^\n]{0,24}){2,}",
    "mfr-unit-misread": r"·\s*∞|τ\s*r\s*/\s*min|\\Nu|\\mathrm",
    "formula-flattened": r"\\frac",
    "spurious-clause-number": r"^\d+\.\d+",
    "appendix-table-lowconf": r"附录|表[A-Z]\.",
}


def _evidence_patterns() -> dict[str, re.Pattern]:
    """类 → 取证用编译正则（audit 判据 + classify 缺陷签名 + **所有者对象直引**）。"""
    import audit_text as A
    import classify as C
    out: dict[str, re.Pattern] = dict(A.CHECKS)
    for cls, src in _EVIDENCE_PATTERNS.items():
        out.setdefault(cls, re.compile(src, re.M))
    out["toc-ingested-as-clauses"] = C._RE_TOC_LINE   # 直引所有者，改判据自动跟随
    return out


def _hit_fragments(cls: str, text: str, limit: int = 120) -> list[str]:
    """该类在本条款文本里的**命中原文片段**（取证用，最多 2 条）。

    为什么要有它：修复纪律第 1 条要求「先打印命中原文，判仪器误报 vs 管线真缺陷」。
    而**判据命中时的文本无法事后复算**——按 doc_id 重新定位可能走另一条链路
    （文本层 blocks vs 深度产物），算出不同文本（实测：复算报 0 命中、判据报 13 部）。
    故在判据命中的那一刻把原文摘出来随记录落盘，证据与命中一一对应、永不脱节。
    """
    rx = _evidence_patterns().get(cls)
    if rx is None:
        return []
    frags: list[str] = []
    for m in rx.finditer(text):
        s, e = max(0, m.start() - 24), min(len(text), m.end() + 24)
        frags.append(text[s:e].replace("\n", "\\n"))
        if len(frags) >= limit:
            break
    return frags


def evaluate_doc(doc: dict, index: dict, scratch_root: Path,
                 ambiguous: set[str] | None = None) -> dict:
    """解析（复用产物，零 OCR）+ 切分 + 分类 —— **不落库**。"""
    from src.core.ingestion.pipeline import (build_clause_models,
                                             load_middle_items,
                                             load_middle_items_from_blocks,
                                             split_items_into_clauses,
                                             strip_figure_legend_segment)
    import audit_text as A
    import classify as C

    def _clean_clause(t: str) -> str:
        """评估前把条款文本过**入库同一条清洗链**（单一所有者，见调用点注释）。"""
        from src.core.text_utils import clean_clause_text
        return clean_clause_text(t, legend_stripper=strip_figure_legend_segment)

    rec: dict[str, Any] = {
        "i": doc["i"], "std_no": doc["std_no"], "doc_id": doc["doc_id"],
        "identity": {"file_hash": doc["file_hash"]},
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    db_n = ro("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?", (doc["doc_id"],))
    rec["clauses_db"] = int(db_n[0][0]) if db_n else 0

    art = AI.resolve_to_parse_dir(doc, index, scratch_root=scratch_root,
                                  ambiguous=ambiguous)
    rec["artifact"] = {"kind": art["kind"],
                       "dir": str(art["dir"]) if art["dir"] else "",
                       "why": art["why"], "certain": bool(art.get("certain"))}
    if art["dir"] is None:
        rec.update({"clauses": 0, "len": 0, "low": 0, "classes": {},
                    "ratio": 0.0, "verdict": "GAP"})
        return rec
    try:
        res = _cached(res_dir=Path(art["dir"]), pdf=doc.get("file_path"))
        if res is None:
            rec.update({"clauses": 0, "len": 0, "low": 0, "classes": {},
                        "ratio": 0.0, "verdict": "GAP"})
            return rec
        if res.get("deep_output"):
            from src.core.ingestion.middle_locator import find_middle_files
            mids = find_middle_files(Path(res["deep_output"]))
            if not mids:
                rec.update({"clauses": 0, "verdict": "GAP", "classes": {},
                            "len": 0, "low": 0, "ratio": 0.0})
                return rec
            rec["artifact"]["parse_backend"] = parse_backend_of(mids[0])
            items, page_sizes = load_middle_items(mids[0])
        else:
            rec["artifact"]["parse_backend"] = "textlayer"
            items, _ = load_middle_items_from_blocks(res["blocks"])
            geos = res.get("geometries") or {}
            page_sizes = {int(k) - 1: (float(v["width"]), float(v["height"]))
                          for k, v in geos.items()}
        split = split_items_into_clauses(items)
        models, _ = build_clause_models("probe", doc["std_no"], "standard",
                                        split, page_sizes)
        # **"读不到的表"必须与"本来没有表"区分开**（2026-09-16 审计提出，本循环实现）。
        # `load_middle_items` 只读 `para_blocks`，而 `preproc_blocks` 里可能还有
        # 表格文本没进判据视野——这部分此前**既不进分母、也不触发任何类**，
        # 于是"读不到的表"与"本来没有表"在报告里同形，外部无法证伪。
        # 度量口径**必须文档级**（逐页相减会把页序差异当成丢失，实测偏高 10 倍以上，
        # 详见 `table_probe.table_two_tree_chars` 的注释）。
        tm = {}
        try:
            import table_probe as TP
            mid = None
            if res.get("deep_output"):
                from src.core.ingestion.middle_locator import find_middle_files
                _mids = find_middle_files(Path(res["deep_output"]))
                if _mids:
                    mid = json.loads(_mids[0].read_text(encoding="utf-8"))
            if isinstance(mid, dict):
                _p, _r = TP.table_two_tree_chars(mid)
                tm = TP.table_missing(_p, _r)
        except Exception:  # noqa: BLE001 —— 度量失败不许影响评估
            tm = {}
    except Exception as e:  # noqa: BLE001
        rec.update({"clauses": 0, "len": 0, "low": 0, "classes": {},
                    "ratio": 0.0, "verdict": "ERROR",
                    "error": f"{type(e).__name__}: {str(e)[:120]}"})
        return rec

    hits: Counter = Counter()
    evidence: dict[str, list[dict]] = {}     # 类 → [{clause, frag}]（命中原文，取证用）
    total_len = 0
    table_len = 0                            # **表格字符量**（判据覆盖率的分母用）
    low = 0
    for m in models:
        txt = m.content_text or ""
        # **判据必须看入库后的文本**（2026-09-15 修正结构性缺陷）：
        # 原先直接对 VLM 产物原文跑判据，而清洗链只在 `pipeline.py` 入库时跑 →
        # 清洗器修好的类判据照旧报、留出集永远判不出"修好"（实测 dot-leader
        # 基线 1 → 修复后 1，逻辑上不可能通过）。此处复用**同一所有者**
        # `text_utils.clean_clause_text`（含图例段切除，与入库同一次序）。
        txt = _clean_clause(txt)
        total_len += len(txt)
        if (m.ocr_confidence or 1.0) < LOW_CONF:
            low += 1
        for cls in A.audit_clause(txt):
            hits[cls] += 1
            ev = evidence.setdefault(cls, [])
            if len(ev) < 3:
                for frag in _hit_fragments(cls, txt, limit=2):
                    ev.append({"clause": m.clause_number or "", "frag": frag[:160]})
        # **表格内容也要过判据**（2026-09-15 用户指出并实测确认的口径缺口）：
        # 表格在 `content_markdown`，而本函数原先只读 `content_text` ——
        # 实测"判据视野只覆盖全文 70.1%"，约 30% 的表格内容**未被任何判据检查**，
        # 而表格占字符量约 34.7%（块数只占 1.8%，按块数统计会严重低估）。
        # 处理：把表格 HTML 转成**制表符分隔的纯文本**（`table_probe.table_plain_text`），
        # 走**同一套判据**（`audit_clause` / `classify_clause`）——凡在表格里出现的
        # 同类缺陷（公式扁平、单位被拆、伪条款号…）从此可见。
        # 另跑 `table_probe.table_defects` 抓**表格结构**缺陷并登记为独立类。
        ttxt = ""
        try:
            import table_probe as TP
            thtml = getattr(m, "content_markdown", "") or ""
            # **`image-missing` 曾经恒不可达**（2026-09-16 审计+自查）：
            # `table_defects` 只在传入 `image_exists` 时才检查图片，而此处原先调用
            # **没传** → 该护栏声称"防符号图丢失"，实际一次也不会触发。
            # 实测口径（`probe_table_img.py`，15 部/96 张表）：`<img src>` 是**裸
            # sha256.jpg 文件名**，文件落在 `<产物>/mineru/<标题>/auto/images/`，
            # 故按 basename 在产物树里递归找（带缓存，避免每个单元格重复 walk）。
            _img_cache: dict[str, bool] = {}

            def _img_exists(name: str, _root=art.get("dir"), _c=_img_cache) -> bool:
                if name in _c:
                    return _c[name]
                hit = False
                try:
                    r = Path(str(_root or ""))
                    if r.is_dir():
                        hit = any(r.rglob(Path(name).name))
                except Exception:  # noqa: BLE001 —— 查不到就当存在，不许误报
                    hit = True
                _c[name] = hit
                return hit

            if thtml:
                ttxt = TP.table_plain_text(thtml)
                table_len += len(ttxt)
                for dfc in TP.table_defects(thtml, image_exists=_img_exists):
                    cls = f"table-{dfc['kind']}"
                    hits[cls] += 1
                    ev = evidence.setdefault(cls, [])
                    if len(ev) < 3:
                        ev.append({"clause": m.clause_number or "",
                                   "frag": json.dumps(dfc, ensure_ascii=False)[:160]})
                # 表格内的文本缺陷：单独记 `table-text::<类>`，便于区分"正文里"
                # 与"表格里"（同一个类在两处的修法可能不同）
                if ttxt.strip():
                    # **判据要用"列间不留粘连"的文本**（2026-09-15 实测）：
                    # 制表符分隔下，相邻单元格 `m` 与 `M` 会被 `unit-midspace`
                    # 的 `m\s+m` **跨列匹配**成"单位被劈开"——而真实文本里这两格
                    # 互不相邻（GB 7100-2015 食品安全标准表格实测误报）。
                    # 列分隔符换成空格后，跨单元格的模式不再产生假命中。
                    ttxt_audit = ttxt.replace("\t", " ")
                    # **表格里的"纯点线占位格"不是目录行**（2026-09-15 实测）：
                    # `dot-leader` 本意抓"目录页被吃成条款"，而表格里常见
                    # `名称 代码 / ...... ...... / ××市 ××××0 0 0 0` 这类**空白占位格**
                    # （GB/T 10114-2003、GB/T 15782-2009 实测），点线是**表格布局**，
                    # 与目录无关。判别信号：真目录行**必带条目名称与页码**
                    # （有连续汉字/字母 + 数字），纯占位格只有点线、空格与分隔符。
                    def _table_text_ok(cls: str) -> bool:
                        if cls != "dot-leader":
                            return True
                        rx = _evidence_patterns().get(cls)
                        if rx is None:
                            return True
                        for m in rx.finditer(ttxt_audit):
                            frag = ttxt_audit[m.start():m.end()]
                            if re.search(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{2,}", frag):
                                return True
                        return False

                    # **证据必须一起采**（2026-09-15 实测踩过）：只加计数不采证据，
                    # 报告里就会出现"某类命中 3 部、却一条原文都拿不到"，
                    # 无法人工判定真假（与早期 `classify` 类漏采证据是同一个坑）。
                    for cls in A.audit_clause(ttxt_audit):
                        if not _table_text_ok(cls):
                            continue
                        key = f"table-text::{cls}"
                        hits[key] += 1
                        ev = evidence.setdefault(key, [])
                        if len(ev) < 3:
                            for frag in _hit_fragments(cls, ttxt_audit, limit=2):
                                ev.append({"clause": m.clause_number or "",
                                           "frag": frag[:160]})
                    for cls in C.classify_clause(m.clause_number or "", ttxt_audit,
                                                 m.ocr_confidence or 1.0):
                        key = f"table-text::{cls}"
                        hits[key] += 1
                        ev = evidence.setdefault(key, [])
                        if len(ev) < 3:
                            ev.append({"clause": m.clause_number or "",
                                       "frag": ttxt_audit[:160]})
            else:
                pass          # 见循环外的**文档级** `table-body-missing` 判据
        except Exception as ex:  # noqa: BLE001
            hits["table-probe-error"] += 1
            ev = evidence.setdefault("table-probe-error", [])
            if len(ev) < 3:
                ev.append({"clause": m.clause_number or "",
                           "frag": f"{type(ex).__name__}: {str(ex)[:120]}"})
        for cls in C.classify_clause(m.clause_number or "", txt,
                                     m.ocr_confidence or 1.0):
            hits[cls] += 1
            # **分类器类也要采证据**：`audit_text.CHECKS` 之外的类（如
            # `toc-ingested-as-clauses`、`spurious-clause-number`）由
            # `classify_clause` 的条件分支判定，同样需要命中原文才能取证；
            # 漏了它就会出现"判据报 10 部、取证却一条原文都拿不到"（实测踩过）。
            ev = evidence.setdefault(cls, [])
            if len(ev) < 3:
                for frag in _hit_fragments(cls, txt, limit=2):
                    ev.append({"clause": m.clause_number or "", "frag": frag[:160]})
    # **`table-body-missing` 已删除**（2026-09-16，加了两小时就被证据推翻）
    #
    # 它想补的是"`no-rows` 够不着整体丢失"这个洞（审计提出，方向正确），但我实现错了：
    #   · 第一版按"条款页范围内有表、该条款 md 为空"判 → **3/3 全误报**（GB 30871-2022
    #     报 30 处）。原因是按页范围判实际测的是**表格绑定差异**，不是丢失。
    #   · 第二版改文档级 `table_len < max(200, 0.2×preproc)` → 独立审计全量重跑
    #     **215 部命中（8.5%）**；我实地复核抽样 20 部：**全部 `preproc == para`、
    #     少读 0.0%**——表格一个字都没丢，却被判"整份丢失"。
    #     根因：`0.2×preproc` 对小于 200 字符的表**恒成立**（`para==pre` 时
    #     `max(200, 0.2pre)=200 > para`），`_TABLE_BODY_MIN` 这个固定下限在作怪。
    #   · 反向核对：真正少读 >5% 的文档（如 `GB／T 20892-2020` 少读 14.3%）
    #     **一部都没被它命中**——档位恰好落反。
    #   · **代价**：它 31 部"命中"直接触发"达线类→停止推进"，把整条推进链停在第 6 批
    #     收批处（批 6 基线 32 命中里它占 31 部 = 96.9%，即全批 97% 的"命中"是假的）。
    #
    # 结论：**零真阳性 = 无判别信号**，按项目纪律（同 `col-count-mismatch` /
    # `empty-cell-run`）删除，不保留"先修修看"的第三次尝试。
    # **恢复条件**：出现"文档级表格确实整份丢失"的实测样本（`para` 远小于 `preproc`
    # 且有产物），并给出能把它与"表格本来就小"分开的判据——那种判据必须**相对**
    # （如 `para < 0.5 × preproc` 且 `preproc ≥ 2000`），不能用固定下限。
    # 现状：`table_missing_chars`（口径量）仍在 `rec` 里，并由 `scout` 显式报出；
    # "整份丢失"这一档**目前没有类级护栏**，这是已知缺口，不再用假护栏糊上。
    rec.update({
        "clauses": len(models), "len": total_len, "low": low,
        # **判据覆盖率**（2026-09-15 口径修正）：判据原先只看 `content_text`，
        # 表格在 `content_markdown` 里从未被检查。现在表格文本也过判据，
        # 但仍要把两个量分开报出来——否则"零命中"会被误读成"全文没问题"。
        "table_len": table_len,
        # **"读不到的表"的口径量**（2026-09-16 审计提出）：`preproc` 侧有、而
        # `para` 侧没有的表格字符量。**它不是缺陷类**——实测比值有噪声底噪
        # （379 部里>5% 的 15 部、最差 14.3%，>20% 的 0 部），故只作口径量上报，
        # 让"读不到"与"本来没有"在报告里可区分。`unknown=True` 表示 preproc 侧
        # 表格文本太少、比值不可用（不是"无缺失"）。
        "table_missing_chars": int(tm.get("missing") or 0),
        "table_preproc_chars": int(tm.get("pre") or 0),
        "table_missing_ratio": tm.get("ratio"),
        "table_missing_unknown": bool(tm.get("unknown", True)),
        "coverage": (round(total_len / (total_len + table_len), 4)
                     if (total_len + table_len) else 1.0),
        "classes": dict(hits),
        "evidence": {k: v[:4] for k, v in evidence.items()},
        "items": len(items),
        "ratio": round(len(models) / max(rec["clauses_db"], 1), 3),
        "cascade": _cascade(split, models),
        "verdict": "ok",
    })
    return rec


def _cached(res_dir: Path, pdf: str | None) -> dict | None:
    from src.core.ingestion.pipeline import _cached_parse_result
    p = Path(pdf or "")
    if not p.exists() and p.suffix == "":
        p = Path(str(p) + ".pdf")
    if not p.exists():
        # 无源 PDF 时仍可复用深度产物（几何只在文本层路径用到）
        p = res_dir / "_absent_.pdf"
    return _cached_parse_result(res_dir, p)


def _cascade(split: list, models: list) -> dict:
    """不可恢复性静态信号：顺序依赖占比 + 单条款最大吞并块数。"""
    from src.core.ingestion.pipeline import _num_segments
    nums = [_num_segments(getattr(c, "number", "") or "") for c in split]
    mx: tuple[int, ...] | None = None
    back = 0
    seen = 0
    for s in nums:
        if s is None:
            continue
        seen += 1
        if mx is not None and s < mx:
            back += 1
        if mx is None or s > mx:
            mx = s
    max_items = max((len(getattr(m, "texts", []) or []) for m in models), default=0)
    return {"order_dep_ratio": round(back / max(seen, 1), 3),
            "max_texts_per_clause": max_items,
            "clauses": len(split)}


# ------------------------------------------------------------------ 状态
def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"schema": 1, "round": 1, "cursor": 1, "phase": "idle",
            "open_trigger": None, "fix_attempts": {}, "clean_rounds": 0,
            "retention": "never-delete"}


def save_state(s: dict) -> None:
    atomic_write(STATE, s)


def round_dir(r: int) -> Path:
    return ROUNDS / f"round-{r:03d}"


# ------------------------------------------------------------------ eval
def cmd_eval(args: list[str]) -> int:
    rnd = int(args[args.index("--round") + 1]) if "--round" in args else None
    if rnd is None:
        print("必须显式 --round N（防误写历史轮）")
        return 2
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    resume = "--resume" in args
    # --survey：不因触发而提前停，跑完全库；仍保留触发判定（首个达线类写进 handoff）。
    # 用途：一次看清**所有类**的全貌以便批量甄别仪器误报 vs 真管线缺陷。
    survey = "--survey" in args
    # --vlm-only：只评估 VLM 产物（用户指令：pipeline 不参与本次循环进化）
    vlm_only = "--vlm-only" in args
    rd = round_dir(rnd)
    if rd.exists() and not resume:
        print(f"轮目录已存在：{rd}\n如要续跑请加 --resume（已评估文档会跳过，绝不重写）")
        return 2

    docs = docs_for("--corpus" in args)
    st = load_state()
    if not resume:
        # 新一轮：**从第 1 部开始**（cursor 不跨轮持久化 = 规格 2 的结构保证）
        st.update({"round": rnd, "cursor": 1, "phase": "evaluating",
                   "open_trigger": None})
        save_state(st)
        atomic_write(rd / "order.json",
                     {"round": rnd, "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "order_hash": order_hash(docs), "n": len(docs),
                      "order": "standard_no 升序", "docs": docs})
    inst = {"round": rnd, "detector": detector_hash(), "owner_hash": owner_hash(),
            "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    append_jsonl(INSTRUMENT, inst)
    print(f"=== evolve 轮次 #{rnd} ===")
    print(f"文档 {len(docs)}（standard_no 升序）· 检测器 {inst['detector']} "
          f"· 所有者 {inst['owner_hash']}")
    ck_path = rd / "checkpoint.json"
    ck = {"cursor": 1, "class_docs": {}, "score": 0, "evaluated": 0}
    if resume and ck_path.exists():
        ck = json.loads(ck_path.read_text(encoding="utf-8"))
    index = AI.load()
    scratch = EVOLVE / "scratch"
    accepted = accepted_limitations()
    if accepted:
        print(f"ℹ 已登记的『不修/已知限制』类（仍计数，不驱动修复）："
              f"{ {k: v[:34] for k, v in accepted.items()} }")
    ambiguous = AI.ambiguous_stems(docs)
    if ambiguous:
        print(f"⚠ 撞键（同名言文件）{len(ambiguous)} 个 → 索引对这些键弃用，"
              f"改走各自 PDF 文本层重提：{sorted(ambiguous)}")
    det_before = db_sentinel()
    global _DB_WRITE_ATTEMPTS
    _DB_WRITE_ATTEMPTS = 0          # 写语句闸按轮重置（跨轮累积会把外部写误判成我方）

    for d in docs:
        if d["i"] < ck["cursor"]:
            continue
        if limit and ck["evaluated"] >= limit:
            print(f"到达 --limit {limit}，停。")
            break
        rec = evaluate_doc(d, index, scratch, ambiguous)
        rec["round"] = rnd
        rec["detector"] = inst["detector"]
        # --vlm-only：用户指令「必须用 VLM，pipeline 不参与本次循环进化」。
        # pipeline 产物（_backend=pipeline）**不计类、不触发**，只留档；
        # 文本层直取（fitz，非 OCR）照常计入。
        _pb = rec.get("artifact", {}).get("parse_backend", "unknown")
        if vlm_only and _pb not in ("hybrid", "vlm", "vlm-engine", "textlayer"):
            rec["classes"] = {}
            rec["verdict"] = "SKIP-PIPELINE"
            atomic_write(rd / "docs" / f"{_safe(d['std_no'])}.json", rec)
            ck["evaluated"] += 1
            ck["cursor"] = d["i"] + 1
            atomic_write(ck_path, ck)
            continue
        atomic_write(rd / "docs" / f"{_safe(d['std_no'])}.json", rec)
        append_jsonl(rd / "ledger.jsonl", {k: rec[k] for k in
                                           ("i", "std_no", "verdict", "clauses",
                                            "clauses_db", "ratio", "classes",
                                            "detector")})
        ck["evaluated"] += 1
        ck["cursor"] = d["i"] + 1
        for cls in rec.get("classes", {}):
            ck["class_docs"].setdefault(cls, [])
            if d["std_no"] not in ck["class_docs"][cls]:
                ck["class_docs"][cls].append(d["std_no"])
        atomic_write(ck_path, ck)
        save_state({**st, "cursor": ck["cursor"]})

        flag = {"GAP": " ⛔GAP", "ERROR": " ⛔ERROR"}.get(rec["verdict"], "")
        print(f"[{d['i']:>3}/{len(docs)}] {d['std_no']:<26} {rec['verdict']:<5} "
              f"条款 {rec['clauses']:>4}/{rec['clauses_db']:<4} "
              f"类 {{{','.join(sorted(rec.get('classes', {})))}}}{flag}",
              flush=True)

        # 护栏 1：单文档灾难性退化（样本 6 部曾 1 部 53→3）。
        # **仅在身份可证时触发**：产物定位撞键（如 6 部法律都叫 source.pdf）时
        # 读到的是别人的内容，据此判塌缩是假警报（2026-09-15 实测）。
        if (rec["clauses_db"] >= PREFLIGHT_MIN_DOC and rec["verdict"] == "ok"
                and rec["ratio"] < PREFLIGHT_RATIO):
            if not rec["artifact"].get("certain"):
                rec["verdict"] = "IDENTITY-UNKNOWN"
                atomic_write(rd / "docs" / f"{_safe(d['std_no'])}.json", rec)
                print(f"    ⚠ 条款 {rec['clauses_db']}→{rec['clauses']} 但**产物身份"
                      f"不可证**（{rec['artifact']['why'][:40]}）→ 不判塌缩")
            else:
                return _handoff(rnd, st, ck, kind="COLLAPSE", std_no=d["std_no"],
                                detail=f"条款 {rec['clauses_db']} → {rec['clauses']}"
                                       f"（{rec['ratio']:.0%}）")
        # 护栏 2：DB 哨兵（本循环不该写库）——**必须归因**（见 db_sentinel 注释）
        if db_sentinel() != det_before:
            ours = _DB_WRITE_ATTEMPTS > 0
            append_jsonl(SENTINEL, {"round": rnd, "i": d["i"],
                                    "violation": ours,
                                    "attribution": "ours" if ours else "external",
                                    "db_write_attempts": _DB_WRITE_ATTEMPTS})
            if ours:
                save_state({**st, "phase": "aborted_db_write"})
                print(f"⛔ **我方**写库 {_DB_WRITE_ATTEMPTS} 次——停轮排查。")
                return 3
            # 外部程序（如 KnowledgeStation GUI）在写：本循环只手读，
            # 与不落库纪律无关，**不因此停轮**（否则常驻 GUI 会让循环永久卡死）。
            print(f"  ℹ DB 指纹变化但归因为**外部写**（我方写库尝试 "
                  f"{_DB_WRITE_ATTEMPTS} 次）→ 继续本轮")

        # 触发：同类累计 3 部文档（已登记为「不修/已知限制」的类不驱动修复）
        for cls, std_nos in ck["class_docs"].items():
            if len(std_nos) >= FIX_LINE:
                if cls in accepted:
                    continue
                if survey:
                    ck.setdefault("first_trigger", {"cls": cls,
                                                    "std_nos": list(std_nos),
                                                    "at_i": d["i"]})
                    atomic_write(ck_path, ck)
                    continue
                return _handoff(rnd, st, ck, kind="TRIGGER", cls=cls,
                                std_nos=std_nos, detail=f"累计 {len(std_nos)} 部")
    if survey:
        ft = ck.get("first_trigger")
        if ft:
            return _handoff(rnd, st, ck, kind="TRIGGER", cls=ft["cls"],
                            std_nos=ft["std_nos"],
                            detail=f"普查模式：首个达线类（第 {ft['at_i']} 部）")
    # 跑完无触发 → 干净轮
    metrics = _metrics(rd, docs)
    atomic_write(rd / "metrics.json", metrics)
    st.update({"phase": "clean", "clean_rounds": st.get("clean_rounds", 0) + 1})
    save_state(st)
    print(f"\n✅ 干净轮 #{rnd}：跑完全部 {ck['evaluated']} 部、无类达线")
    print(f"   类命中总计 {metrics['score']} · 达线类 {len(metrics['over_line'])}")
    return 0


def _handoff(rnd: int, st: dict, ck: dict, *, kind: str, cls: str = "",
             std_nos: list[str] | None = None, std_no: str = "",
             detail: str = "") -> int:
    rd = round_dir(rnd)
    metrics = _metrics(rd, None)
    atomic_write(rd / "metrics.json", metrics)
    ho = {"round": rnd, "kind": kind, "cls": cls, "std_nos": std_nos or [],
          "std_no": std_no, "detail": detail,
          "at_i": ck["cursor"] - 1,
          "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
          "evidence": str(rd / "docs"), "instruction":
          "按 systematic-debugging 在**规范所有者层**修复（一次只证伪一个假设；"
          "补丁形状信号；三次修不好即质疑架构）。修好后跑：\n"
          f"  python var/ocr-loop/evolve.py fix-done --class {cls or kind} "
          "--commit <sha> --note \"…\""}
    atomic_write(rd / "handoff.json", ho)
    st.update({"phase": "awaiting_fix" if kind == "TRIGGER" else "aborted",
               "open_trigger": {"kind": kind, "cls": cls,
                                "std_nos": std_nos or [], "std_no": std_no}})
    save_state(st)
    if kind == "TRIGGER":
        att = st.get("fix_attempts", {})
        att[cls] = att.get(cls, 0) + 1
        st["fix_attempts"] = att
        save_state(st)
        print(f"\n⏸ 触发修复：类 `{cls}` 累计 {len(std_nos or [])} 部 → "
              f"{', '.join((std_nos or [])[:5])}")
        if att[cls] >= 3:
            print(f"⚠ 该类已第 {att[cls]} 次触发修复（三次修不好 → 质疑架构/拆类/登记不修）")
    else:
        print(f"\n⛔ 停轮（{kind}）：{std_no} {detail}")
    print(f"   交接单：{rd / 'handoff.json'}")
    return 1


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in s)[:80]


def _metrics(rd: Path, docs: list[dict] | None) -> dict:
    """从本轮 docs/*.json 算出全部指标（可复现；不依赖内存状态）。"""
    score = 0
    cls_docs: dict[str, set] = defaultdict(set)
    per_doc: dict[str, dict] = {}
    n_doc = 0
    for f in sorted((rd / "docs").glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        n_doc += 1
        per_doc[r["std_no"]] = {"verdict": r.get("verdict"),
                                "clauses": r.get("clauses", 0),
                                "classes": r.get("classes", {})}
        for cls, cnt in (r.get("classes") or {}).items():
            score += cnt
            cls_docs[cls].add(r["std_no"])
    over = sorted([c for c, s in cls_docs.items() if len(s) >= FIX_LINE],
                  key=lambda c: -len(cls_docs[c]))
    return {"round": int(rd.name.split("-")[1]), "docs_evaluated": n_doc,
            "score": score,
            "classes": {c: {"docs": len(s), "std_nos": sorted(s)[:60]}
                        for c, s in sorted(cls_docs.items(),
                                           key=lambda kv: -len(kv[1]))},
            "over_line": over,
            "verdicts": dict(Counter(v["verdict"] for v in per_doc.values())),
            "per_doc": per_doc}


# ------------------------------------------------------------------ compare
def _read_round(r: int) -> dict | None:
    rd = round_dir(r)
    if not rd.exists():
        return None
    m = rd / "metrics.json"
    if m.exists():
        return json.loads(m.read_text(encoding="utf-8"))
    return _metrics(rd, None)


def cmd_compare(args: list[str]) -> int:
    w = int(args[args.index("--window") + 1]) if "--window" in args else 5
    st = load_state()
    cur = st.get("round", 1)
    have = [r for r in range(1, cur + 1) if round_dir(r).exists()]
    if len(have) < w:
        print(f"轮数不足：已有 {have}，需要 {w} 轮才做横比。")
        return 0
    win = have[-w:]
    rounds = [(r, _read_round(r)) for r in win]
    rounds = [(r, m) for r, m in rounds if m]
    if len(rounds) < w:
        print(f"窗口内可用轮 {len(rounds)} < {w}")
        return 0
    # 仪器漂移：取同一 detector 的最长连续后缀
    dets = []
    for r, _ in rounds:
        inst = [json.loads(x) for x in INSTRUMENT.read_text(encoding="utf-8").splitlines()
                if x.strip()] if INSTRUMENT.exists() else []
        d = next((x["detector"] for x in reversed(inst) if x["round"] == r), "?")
        dets.append(d)
    suffix = 1
    for k in range(len(dets) - 1, 0, -1):
        if dets[k] == dets[k - 1]:
            suffix += 1
        else:
            break
    basis = "suffix" if suffix < len(dets) else "window"
    used = rounds[-suffix:] if basis == "suffix" else rounds
    sets = [set(m["per_doc"].keys()) for _, m in used]
    common = set.intersection(*sets) if sets else set()
    kvocab: set = set()
    for _, m in used:
        kvocab |= set(m["classes"].keys())

    rows = []
    prev_hits: set | None = None
    seen_hits: set = set()
    for r, m in used:
        hits = {(std, c) for std in common for c in m["per_doc"].get(std, {})
                .get("classes", {})}
        score = len(hits)
        over = len([c for c in m["over_line"] if c in kvocab])
        new_hits = len(hits - seen_hits)
        recur = len(hits & prev_hits) if prev_hits is not None else 0
        rows.append({"round": r, "score": score, "over": over,
                     "new": new_hits, "recur": recur,
                     "docs": m["docs_evaluated"]})
        seen_hits |= hits
        prev_hits = hits

    # 语料漂移闸（2026-09-15，与检测器漂移闸同性质）：**换过语料的轮次不可比**。
    # 用户指令换全新语料防过拟合后，旧轮（库内 260 部）与新轮（全新语料）的
    # 公共文档交集为空 → 横比会静默给出 `flat`，看着像"没进展"，实则无从比较。
    # 故显式判出并把 verdict 改成 inconclusive-corpus-changed，绝不让它冒充结论。
    docsets = [frozenset(m["per_doc"].keys()) for _, m in rounds]
    corpus_drift = len(set(docsets)) > 1
    if len(set.intersection(*[set(s) for s in docsets])) == 0:
        corpus_drift = True

    s1, s5 = rows[0]["score"], rows[-1]["score"]
    bounce = any(rows[i + 1]["score"] > rows[i]["score"] * 1.02
                 for i in range(len(rows) - 1))
    flat = all(abs(rows[i + 1]["score"] - rows[i]["score"]) <= 0.02 * max(s1, 1)
               for i in range(len(rows) - 1))
    over_noninc = all(rows[i + 1]["over"] <= rows[i]["over"]
                      for i in range(len(rows) - 1))
    if corpus_drift:
        verdict = "inconclusive-corpus-changed"
    elif basis == "suffix" and suffix < 2:
        verdict = "inconclusive-needs-recalibration"
    elif not bounce and s5 <= 0.8 * max(s1, 1) and over_noninc:
        verdict = "improving"
    elif flat:
        verdict = "stalled"
    elif bounce or any(rows[i + 1]["over"] > rows[i]["over"]
                       for i in range(len(rows) - 1)):
        verdict = "regressing"
    else:
        verdict = "new-issue" if rows[-1]["new"] > 0 else "flat"

    out = {"window": win, "basis": basis, "detector_series": dets,
           "instrument_changed": len(set(dets)) > 1,
           "corpus_changed": corpus_drift,
           "common_docs": len(common), "rows": rows, "verdict": verdict,
           "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    WINDOWS.mkdir(parents=True, exist_ok=True)
    wid = f"window-{win[0]:03d}-{win[-1]:03d}"
    atomic_write(WINDOWS / f"{wid}.json", out)

    print(f"=== 五轮横比 {win}（检测器 {'变过→' + basis if len(set(dets)) > 1 else '未变'}）===")
    print(f"公共文档 {len(common)} 部 · 判定 **{verdict}**")
    if corpus_drift:
        print("⚠ **语料变过**：各轮文档集不同（该窗口内换过语料）——"
              "跨轮比较无效，请只在同一语料内比，或改用留出集曲线")
    print(f"{'轮':>4} {'类命中':>7} {'达线类':>7} {'新冒出':>7} {'重现':>6}")
    for x in rows:
        print(f"{x['round']:>4} {x['score']:>7} {x['over']:>7} "
              f"{x['new']:>7} {x['recur']:>6}")
    if verdict != "improving":
        print(f"\n❌ 未越修越少（{verdict}）→ 触发 5-verifier 分析："
              f"\n   python var/ocr-loop/evolve.py escalate --window {w}")
    return 0 if verdict == "improving" else 1


# ------------------------------------------------------------------ escalate
V_ROLES = [
    ("V1", "修复历史", "逐个修复：eff(cls) 是否 >0？哪些只对单文档生效、哪些是假修复？"),
    ("V2", "类计数轨迹", "逐类逐轮 docs 命中曲线：单调下降/平台/反弹？下降是否来自检测器漂移？"),
    ("V3", "残留样例证据", "残留是同一根因还是新根因？给出最小复现与根因假设"),
    ("V4", "判据变化", "类计数变化是仪器变化还是真实变化？哪些检测器是误报、应删除而非上报？"),
    ("V5", "未修类", "待修优先级；是否存在结构性原因（判据过宽）导致不断冒新问题？"),
]


def cmd_escalate(args: list[str]) -> int:
    w = int(args[args.index("--window") + 1]) if "--window" in args else 5
    st = load_state()
    cur = st.get("round", 1)
    have = [r for r in range(1, cur + 1) if round_dir(r).exists()][-w:]
    eid = f"esc-{len(list(ESCAL.glob('esc-*'))) + 1:03d}" if ESCAL.exists() else "esc-001"
    ed = ESCAL / eid
    ed.mkdir(parents=True, exist_ok=True)
    prompts = []
    for name, view, ask in V_ROLES:
        p = f"""你是自进化 OCR 循环的独立 verifier（{name}·{view}）。
窗口轮次：{have}。请**只读**以下文件（绝对路径），不要修改任何文件、不要写库：
- 轮结果：`{ROUNDS}` 下 round-{have[0]:03d}..round-{have[-1]:03d} 的
  `docs/*.json`（逐文档条款数/类计数）、`metrics.json`、`handoff.json`
- 修复历史：`{FIXES}`（每行一次修复）、`{LEDGER}`（已修类台账）
- 仪器：`{INSTRUMENT}`（每轮检测器哈希/所有者哈希）
- 横比结果：`{WINDOWS}` 下最新 window json
- 台账与背景：`{HERE / 'NOTES.md'}`

**你的专属问题（只回答这个）**：{ask}

输出必须是严格 JSON（写进 `{ed / (name + '.json')}` 也可只回给我）：
{{"verifier":"{name}","verdict":"假修复|真修复未覆盖存量|判据漂移|新根因|不可判",
 "confidence":0.0,
 "findings":[{{"cls":"…","std_no":"…","claim":"…","evidence_ref":"…"}}],
 "recommend":{{"priority_classes":[],"delete_detectors":[],"rollback_fixes":[],"next_action":"…"}}}}
判据：必须引用具体文件/字段作为证据，禁止猜测；若证据不足就判 `不可判` 并说明缺什么。"""
        prompts.append((name, view, p))
        (ed / f"{name}.prompt.md").write_text(p, encoding="utf-8")
    atomic_write(ed / "manifest.json",
                 {"escalation": eid, "window": have,
                  "verifiers": [{"id": n, "view": v, "prompt": f"{n}.prompt.md"}
                                for n, v, _ in prompts],
                  "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"已生成 {len(prompts)} 份 verifier 提示词 → {ed}")
    for n, v, _ in prompts:
        print(f"  {n} ({v})：{ed / (n + '.prompt.md')}")
    print("\n用 subagent 并行派发（各自独立视角，互不可见）：")
    for n, _, _ in prompts:
        print(f"  subagent prompt={ed / (n + '.prompt.md')} → 结果写 {ed / (n + '.json')}")
    print("回收后按 ≥3/5 共识回流：强制首修类 / 删除误报检测器 / 回滚无效修复。")
    return 0


# ------------------------------------------------------------------ arbiter
#: 指南第四章的**六字段 schema**：缺任一字段即判无效（不接受"半份方案"）。
#: 为什么强制：缺「回滚」就无法回退、缺「根因层」就会退化成下游打补丁、
#: 缺「预期效果」则无法与实测对比、缺「置信度」则无从排序。
ARBITER_FIELDS = ("root_layer", "plan", "expected_effect", "risk",
                  "rollback", "confidence")

#: 指南第五条的**强制排查顺序**（图像预处理 → 提示词 → 分块策略 → 检测器逻辑）。
#: `检测器逻辑` 排最后是刻意的：命中面大时先怀疑上游，别一上来改下游。
ROOT_LAYERS = ("图像预处理", "提示词", "分块策略", "检测器逻辑", "识别层限制")

#: 盲评四维（指南第八条），各 1–4 分。**盲评 = 隐藏候选身份**：
#: 打分时不得知道方案出自哪个视角/哪次尝试，否则会按来源偏袒。
ARBITER_DIMS = (
    ("root_depth", "根因深度", "只治症状=1；到规范所有者层且能解释全部残留=4"),
    ("scope", "改动范围", "改动越大风险越高：1 分=小改动，4 分=大改动"),
    ("rollback_cost", "回滚成本", "回滚越便宜越好：1 分=一次 revert 即可"),
    ("history_similarity", "历史相似性", "与既往失败修复越像越可疑：1 分=不像"),
)

ARB_ROOT = EVOLVE / "arbiter"
ARB_PROPOSALS = ARB_ROOT / "proposals"
ARB_DECISIONS = ARB_ROOT / "decisions.jsonl"


def _arb_id(pending: bool = False) -> str:
    """分配仲裁批次 id（`arb-NNN`）。`pending` = 尚未落盘的下一号。"""
    n = len(list(ARB_ROOT.glob("arb-*"))) + (1 if pending else 0)
    return f"arb-{n:03d}"


def validate_proposal(obj: dict) -> tuple[bool, str]:
    """六字段校验：缺字段 / 根因层非法 / 置信度越界 一律判**无效**。

    返回 `(是否有效, 原因)`。无效方案**不进入盲评**——宁可这一轮没有候选，
    也不让半份方案进实测（实测要花留出集与时间，成本不可逆）。
    """
    missing = [f for f in ARBITER_FIELDS if not str(obj.get(f, "")).strip()]
    if missing:
        return False, f"缺字段 {missing}"
    layer = str(obj.get("root_layer", "")).strip()
    if layer not in ROOT_LAYERS:
        return False, f"根因层 {layer!r} 非法（应为 {list(ROOT_LAYERS)} 之一）"
    try:
        c = float(obj.get("confidence"))
    except (TypeError, ValueError):
        return False, f"置信度 {obj.get('confidence')!r} 不是数值"
    if not 0.0 <= c <= 1.0:
        return False, f"置信度 {c} 越界（应 0–1）"
    return True, ""


def auto_score(obj: dict) -> dict[str, int]:
    """由字段**确定性**推四维分（无 LLM 也能算，避免"盲评"变成走过场）。

    这是**初评**：指南要求盲评隐藏身份，故此处只看方案内容本身、不看它出自
    哪个视角；人工/模型复核可用 `arbiter --score-file` 覆盖（见 cmd_arbiter）。
    """
    layer = str(obj.get("root_layer", ""))
    # 根因深度：点明"在规范所有者层修"最深（4）；检测器逻辑层=3；
    # 识别层限制=1（不修，深度记 1 以示"到此为止"）。
    # 只看 plan/expected_effect 两处正文（不含 risk/rollback），避免回滚措辞里
    # 偶然出现"所有者"就把深度抬上去。
    body = f"{obj.get('plan', '')} {obj.get('expected_effect', '')}"
    if layer == "检测器逻辑" and ("所有者" in body or "single owner" in body.lower()):
        depth = 4
    elif layer in ("检测器逻辑", "分块策略"):
        depth = 3
    elif layer in ("提示词", "图像预处理"):
        depth = 2
    else:                                   # 识别层限制：不修，故深度记 1
        depth = 1
    plan = json.dumps(obj, ensure_ascii=False)
    n_files = max(1, len(re.findall(r"[\w/]+\.(?:py|json|ps1|md)", plan)))
    scope = 4 if n_files >= 6 else 3 if n_files >= 3 else 1
    rb = str(obj.get("rollback", ""))
    rollback_cost = 1 if ("revert" in rb.lower() or "--rollback" in rb) else 2
    sim = str(obj.get("history_similarity", "")) or plan
    history_similarity = 3 if re.search(r"与(此前|上次|第\s*\d+\s*次)", sim) else 2
    return {"root_depth": depth, "scope": scope,
            "rollback_cost": rollback_cost, "history_similarity": history_similarity}


def recheck(before: dict[str, int], after: dict[str, int],
            *, new_limit: int = 3, rise: float = 0.20) -> dict:
    """完整样本复核判据（指南第九条）：**新冒类 >3 或某类上升 >20% 也判失败**。

    `before`/`after` = 类 → 命中**文档数**（不是条数：文档面才是修复是否真覆盖的
    度量）。小分母保护：某类从 1→2 是 +100% 但绝对量微不足道，会淹没真回归，
    故须**同时**满足相对涨幅 >`rise` 且绝对增量 ≥2 才判失败。

    返回 `{passed, new_classes, rising, reasons}`——判失败即**回滚**，不进下一轮。
    """
    new_classes = sorted([c for c in after if c not in before and after[c] > 0])
    rising = []
    for c, a in after.items():
        b = before.get(c, 0)
        if b <= 0:
            continue
        if (a - b) / b > rise and (a - b) >= 2:
            rising.append({"cls": c, "before": b, "after": a,
                           "rise": round((a - b) / b, 3)})
    rising.sort(key=lambda x: -x["rise"])
    reasons = []
    if len(new_classes) > new_limit:
        reasons.append(f"新冒类 {len(new_classes)} 个 >{new_limit}：{new_classes}")
    if rising:
        reasons.append("上升 >20%：" + ", ".join(
            f"{x['cls']} {x['before']}→{x['after']} (+{x['rise']:.0%})"
            for x in rising))
    return {"passed": not reasons, "new_classes": new_classes,
            "rising": rising, "reasons": reasons}


def _cls_docs_of(metrics: dict) -> dict[str, int]:
    """metrics.json → 类 → 命中文档数（复核口径与判据同源）。"""
    return {c: int(v.get("docs", 0))
            for c, v in (metrics.get("classes") or {}).items()}


def cmd_arbiter(args: list[str]) -> int:
    """`arbiter`：五视角提示词（六字段）→ 盲评四维 → 前二实测 → 完整样本复核。

    子命令式（默认 `plan`）：
      plan   --class X [--window 5]   生成五视角提示词 + 校验 schema
      score  --file p1.json [--file p2.json ...]   收集候选 → 六字段校验 → 盲评四维
      decide --cls X [--winner ID]    取前二给实测步骤；给 --winner 则记决策台账
    """
    # 分派器（main）按项目惯例把**完整 argv[1:]** 交给子命令处理函数
    # （与 cmd_escalate 一致），故此处先剥掉命令名本身再取子命令。
    sub_args = [a for a in args if a != "arbiter"]
    sub = sub_args[0] if sub_args and not sub_args[0].startswith("-") else "plan"
    cls = sub_args[sub_args.index("--class") + 1] if "--class" in sub_args else \
        (sub_args[sub_args.index("--cls") + 1] if "--cls" in sub_args else "")
    w = int(sub_args[sub_args.index("--window") + 1]) if "--window" in sub_args else 5
    st = load_state()
    cur = st.get("round", 1)
    have = [r for r in range(1, cur + 1) if round_dir(r).exists()][-w:]

    if sub == "plan":
        if not cls:
            print("用法：arbiter plan --class <类> [--window 5]")
            return 2
        aid = _arb_id(pending=True)
        ad = ARB_ROOT / aid
        ad.mkdir(parents=True, exist_ok=True)
        attempts = _fix_attempts(cls)
        prompts = []
        for name, view, ask in V_ROLES:
            p = f"""你是自进化 OCR 循环的独立 verifier（{name}·{view}）。
**本轮任务不是"报告问题"，而是提出可实测的修复方案。**

目标类：`{cls}`（同类已尝试 {attempts} 次；指南规定**达 3 次必须转本仲裁**，
不再常规修）。窗口轮次：{have}。

只读以下文件（绝对路径），**不要修改任何文件、不要写库**：
- 轮结果：`{ROUNDS}` 下 round-{have[0] if have else 1:03d}..round-{have[-1] if have else 1:03d}
  的 `docs/*.json`、`metrics.json`
- 修复历史：`{FIXES}`；已修类台账：`{LEDGER}`
- 仪器：`{INSTRUMENT}`（每轮检测器/所有者哈希，用于判断"变化是仪器还是真实"）
- 台账与背景：`{HERE / 'NOTES.md'}`、`{EVOLVE / 'README.md'}`

**你的专属问题（只回答这个）**：{ask}

输出必须是**严格 JSON**，且**六字段一个都不能少**（缺任一字段 → 整份方案判无效、
不进入盲评与实测）：
{{"verifier":"{name}",
  "root_layer":"图像预处理|提示词|分块策略|检测器逻辑|识别层限制",
  "plan":"具体改哪个文件/哪个函数，怎么改",
  "expected_effect":"预期该类命中下降多少，依据是什么",
  "risk":"可能误伤哪些合法形态（必须给反向对照样例）",
  "rollback":"如何回滚（一次 revert / 开关 / 备份路径）",
  "confidence":0.0,
  "evidence":[{{"cls":"{cls}","std_no":"…","fragment":"命中原文","file":"…"}}]}}

**强制排查顺序**（指南第五条）：图像预处理 → 提示词 → 分块策略 →
**检测器逻辑（最后）**。命中 >10 部时先自问"这是图像问题还是语义问题"，
不要一上来就改下游检测器——那正是"浅层修复"的病根。
证据必须引用具体文件/字段与命中原文；证据不足就填 `root_layer":"识别层限制"`
并说明缺什么，**不要编造**。"""
            prompts.append((name, view, p))
            (ad / f"{name}.prompt.md").write_text(p, encoding="utf-8")
        atomic_write(ad / "manifest.json",
                     {"arbiter": aid, "cls": cls, "window": have,
                      "attempts_before": attempts,
                      "schema": list(ARBITER_FIELDS),
                      "forced_by_attempts": attempts >= 3,
                      "verifiers": [{"id": n, "view": v, "prompt": f"{n}.prompt.md"}
                                    for n, v, _ in prompts],
                      "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"=== arbiter {aid} · 类 {cls} · 同类已尝试 {attempts} 次"
              f"{'（≥3 → 强制仲裁）' if attempts >= 3 else ''} ===")
        print(f"已生成 {len(prompts)} 份五视角提示词 → {ad}")
        for n, v, _ in prompts:
            print(f"  {n} ({v})：{ad / (n + '.prompt.md')}")
        print(f"\n六字段 schema：{list(ARBITER_FIELDS)}（缺一即判无效）")
        print("回收方案到该目录后：")
        print(f"  python var/ocr-loop/evolve.py arbiter score --file <方案.json> …")
        print(f"  python var/ocr-loop/evolve.py arbiter decide --cls {cls}")
        return 0

    if sub == "score":
        files = [sub_args[i + 1] for i, a in enumerate(sub_args) if a == "--file"]
        if not files:
            print("用法：arbiter score --file p1.json [--file p2.json …]")
            return 2
        aid = _arb_id()
        ad = ARB_ROOT / aid
        ad.mkdir(parents=True, exist_ok=True)
        scored, invalid = [], []
        for f in files:
            try:
                obj = json.loads(Path(f).read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                invalid.append({"file": f, "why": f"读取失败 {type(e).__name__}"})
                continue
            ok, why = validate_proposal(obj)
            if not ok:
                invalid.append({"file": f, "why": why})
                continue
            dims = auto_score(obj)
            scored.append({"file": f, "verifier": obj.get("verifier", ""),
                           "root_layer": obj.get("root_layer", ""),
                           "dims": dims, "total": sum(dims.values()),
                           "confidence": float(obj.get("confidence") or 0)})
        # 前二：四维总分优先，并列看置信度
        scored.sort(key=lambda x: (-x["total"], -x["confidence"]))
        top2 = [x["file"] for x in scored[:2]]
        atomic_write(ad / "scores.json",
                     {"arbiter": aid, "scores": scored, "invalid": invalid,
                      "top2": top2, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"=== arbiter {aid} 盲评四维（各 1–4 分）===")
        if invalid:
            print(f"⚠ 无效方案 {len(invalid)} 份（**不进盲评**）：")
            for x in invalid:
                print(f"    {Path(x['file']).name}：{x['why']}")
        if not scored:
            print("❌ 无有效方案——本轮无候选，不得进实测")
            return 1
        print(f"{'方案':<28}{'根因深度':>8}{'改动范围':>8}{'回滚成本':>8}{'历史相似':>8}{'合计':>6}")
        for x in scored:
            d = x["dims"]
            print(f"{Path(x['file']).name:<28}{d['root_depth']:>8}{d['scope']:>8}"
                  f"{d['rollback_cost']:>8}{d['history_similarity']:>8}{x['total']:>6}")
        print(f"\n前二（进入实测）：{[Path(p).name for p in top2]}")
        print("注意：回滚成本/改动范围分值为「越大越差」，合计是**可比性排序**，"
              "不是好坏绝对值。")
        return 0

    if sub == "decide":
        if not cls:
            print("用法：arbiter decide --cls <类> [--winner <方案文件或 ID>]")
            return 2
        # 找最近一次 scores.json
        cands = sorted([p for p in ARB_ROOT.glob("arb-*/scores.json")],
                       key=lambda p: p.stat().st_mtime)
        if not cands:
            print("⚠ 尚无 scores.json，先跑：arbiter score --file …")
            return 2
        sc = json.loads(cands[-1].read_text(encoding="utf-8"))
        top2 = sc.get("top2") or []
        winner = sub_args[sub_args.index("--winner") + 1] if "--winner" in sub_args else ""
        print(f"=== arbiter decide · 类 {cls}（批次 {sc['arbiter']}）===")
        print("实测步骤（**前二各自实测，留出集降得多者胜**）：")
        for i, f in enumerate(top2, 1):
            print(f"  {i}) 应用 {Path(f).name} 的改动 → "
                  f"python var/ocr-loop/scout.py verify --class {cls} "
                  f"--baseline-round {cur}")
        print("  胜者再跑**完整样本复核**：scout.py scout --vlm-only + "
              "evolve.py eval --round <N> --survey")
        print("  复核判据：新冒类 ≤3 且无某类上升 >20%；否则**判失败并回滚**")
        if winner:
            append_jsonl(ARB_DECISIONS,
                         {"cls": cls, "arbiter": sc["arbiter"], "winner": winner,
                          "top2": top2, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
            print(f"\n✅ 已记决策台账：胜者 {winner}"
                  f"（写入 {ARB_DECISIONS.name}，append-only）")
        else:
            print("\n（实测完成后再带 --winner 落台账）")
        return 0

    if sub == "check":
        # 完整样本复核：base-round → cur-round 的类命中文档数对比（指南第九条）
        br = int(sub_args[sub_args.index("--base-round") + 1]) \
            if "--base-round" in sub_args else max(1, cur - 1)
        cr = int(sub_args[sub_args.index("--cur-round") + 1]) \
            if "--cur-round" in sub_args else cur
        b, a = _read_round(br), _read_round(cr)
        if not b or not a:
            print(f"⚠ 缺轮次结果（base #{br} / cur #{cr}），先跑 eval")
            return 2
        res = recheck(_cls_docs_of(b), _cls_docs_of(a))
        atomic_write(ARB_ROOT / f"recheck-r{br}-r{cr}.json",
                     {"base_round": br, "cur_round": cr, **res,
                      "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"=== 完整样本复核 · 轮 #{br} → #{cr} ===")
        print(f"基线类命中 {len(b.get('classes') or {})} 类 · "
              f"当前 {len(a.get('classes') or {})} 类")
        if res["passed"]:
            print("✅ 通过：无 >3 新冒类、无某类上升 >20% → 可进下一轮")
            return 0
        for r in res["reasons"]:
            print(f"❌ {r}")
        print("\n→ **判失败，必须回滚胜利方案的改动**（不得带着回归进下一轮）")
        return 1

    print("用法：arbiter plan|score|decide|check …（见 evolve.py 模块帮助）")
    return 2


def _fix_attempts(cls: str) -> int:
    """该类历史修复尝试次数（`fixes.jsonl` 计数）——指南"同类最多 3 次"。"""
    if not FIXES.exists():
        return 0
    n = 0
    for line in FIXES.read_text(encoding="utf-8").splitlines():
        try:
            if json.loads(line).get("cls") == cls:
                n += 1
        except Exception:  # noqa: BLE001
            continue
    return n


def cmd_fix_done(args: list[str]) -> int:
    cls = args[args.index("--class") + 1]
    commit = args[args.index("--commit") + 1]
    note = args[args.index("--note") + 1] if "--note" in args else ""
    st = load_state()
    rnd = st.get("round", 1)
    rd = round_dir(rnd)
    atomic_write(rd / "fix.json", {"round": rnd, "cls": cls, "commit": commit,
                                   "note": note,
                                   "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    append_jsonl(FIXES, {"round": rnd, "cls": cls, "commit": commit, "note": note,
                         "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    led = fixed_ledger()
    led[cls] = {"date": time.strftime("%Y-%m-%d"), "commit": commit, "note": note}
    atomic_write(LEDGER, led)
    st.update({"round": rnd + 1, "cursor": 1, "phase": "idle",
               "open_trigger": None})
    save_state(st)
    print(f"✅ 已关轮 #{rnd}（类 {cls} / {commit}）→ **下一轮 #{rnd + 1} 从第 1 部重新开始**")
    return 0


# ------------------------------------------------------------------ doctor
def cmd_doctor(_args: list[str]) -> int:
    import inspect
    from src.core.ingestion import pipeline as P
    print("=== evolve doctor（只读自检）===")
    print(f"DB            {db_path()}")
    print(f"DB 哨兵       {db_sentinel()}")
    print(f"文档          {len(doc_list())} 部")
    print(f"检测器哈希    {detector_hash()}   （audit_text.py + classify.py）")
    print(f"所有者哈希    {owner_hash()}     （pipeline.py + text_utils.py + middle_locator.py）")
    # 调用图核验：评估链路不得含 DB 写
    bad = []
    for fn in (P._cached_parse_result, P.load_middle_items,
               P.load_middle_items_from_blocks, P.split_items_into_clauses,
               P.build_clause_models):
        src = inspect.getsource(fn)
        if any(t in src for t in ("INSERT", "UPDATE ", "DELETE ", "commit()",
                                  "get_db_connection")):
            bad.append(fn.__name__)
    print(f"不落库核验    {'❌ 可疑：' + ','.join(bad) if bad else '✅ 五个评估函数源码内零 DB 写'}")
    idx = AI.load()
    print(f"产物索引      {idx['keys']} 键（{idx['built_at']}，{idx['wall_s']}s）")
    docs = docs_for(False)
    kinds = Counter()
    for d in docs:
        kinds[AI.resolve(d, idx)["kind"]] += 1
    print(f"产物覆盖（库内）" + " · ".join(f"{k}={v}" for k, v in kinds.items()))
    cdocs = docs_for(True)
    ckinds = Counter(AI.resolve(d, idx)["kind"] for d in cdocs)
    print(f"产物覆盖（新语料 {len(cdocs)} 部）"
          + " · ".join(f"{k}={v}" for k, v in ckinds.items()))
    st = load_state()
    print(f"循环状态      轮 #{st.get('round')} · 游标 {st.get('cursor')} · "
          f"phase={st.get('phase')} · 修复尝试 {st.get('fix_attempts')}")
    return 0


# ------------------------------------------------------------------ poison
def cmd_poison_test(args: list[str]) -> int:
    """假头注入：一部文档里插一个「形态侥幸像真头」的假条款头，看塌缩多深。

    这是**不可恢复性**的动态度量：现有判据若顺序依赖，一个假头就能吞掉整篇
    （2026-09-15 实测 GB/T 12706.4-2020：53 → 3 条）。
    """
    from src.core.ingestion.pipeline import (MidItem, load_middle_items,
                                             split_items_into_clauses)
    from src.core.ingestion.middle_locator import find_middle_files
    only = args[args.index("--std-no") + 1] if "--std-no" in args else ""
    idx = AI.load()
    docs = docs_for("--corpus" in args)
    if only:
        docs = [d for d in docs if d["std_no"] == only]
    out = []
    for d in docs[:int(args[args.index("--top") + 1]) if "--top" in args else 5]:
        art = AI.resolve_to_parse_dir(d, idx)
        if art["dir"] is None:
            continue
        res = _cached(Path(art["dir"]), d.get("file_path"))
        if not res or not res.get("deep_output"):
            continue
        mids = find_middle_files(Path(res["deep_output"]))
        if not mids:
            continue
        items, _ = load_middle_items(mids[0])
        base = len(split_items_into_clauses(items))
        worst = base
        for frac in (0.2, 0.4, 0.6):
            k = max(1, int(len(items) * frac))
            fake = MidItem(kind="text", text="40.5kV)挤包绝缘电力电缆及附件",
                           page_idx=items[k].page_idx if k < len(items) else 0)
            poisoned = items[:k] + [fake] + items[k:]
            try:
                n = len(split_items_into_clauses(poisoned))
            except Exception:  # noqa: BLE001
                n = 0
            worst = min(worst, n)
        ratio = round(worst / max(base, 1), 3)
        out.append({"std_no": d["std_no"], "base": base, "worst": worst,
                    "ratio": ratio,
                    "irrecoverable_risk": ratio < 0.5})
        print(f"{d['std_no']:<26} 基准 {base:>4} → 中毒最差 {worst:>4} "
              f"（{ratio:.0%}）{'  ⚠ 不可恢复风险' if ratio < 0.5 else ''}")
    if out:
        atomic_write(EVOLVE / "irrecoverability.json",
                     {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "docs": out})
        risk = [x for x in out if x["irrecoverable_risk"]]
        print(f"\n不可恢复风险文档 {len(risk)}/{len(out)} → {EVOLVE / 'irrecoverability.json'}")
    return 0


def cmd_evidence(args: list[str]) -> int:
    """触发类的**原文证据**：逐部列出命中该类的条款号 + 文本片段（只读）。

    修复前必须看真实样例（仪器可信度优先：判据可能误报，样例一眼就能判）。
    """
    from src.core.ingestion.pipeline import (build_clause_models,
                                             load_middle_items,
                                             load_middle_items_from_blocks,
                                             split_items_into_clauses)
    import audit_text as A
    import classify as C
    rnd = int(args[args.index("--round") + 1]) if "--round" in args else 1
    cls = args[args.index("--class") + 1]
    per = int(args[args.index("--per") + 1]) if "--per" in args else 5
    rd = round_dir(rnd)
    ddir = rd / "docs"
    hits = []
    for f in sorted(ddir.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("classes", {}).get(cls):
            hits.append(r["std_no"])
    idx = AI.load()
    docs = {d["std_no"]: d for d in docs_for("--corpus" in args)}
    out = {"round": rnd, "cls": cls, "docs": [], "generated": time.strftime("%Y-%m-%d %H:%M:%S")}
    for std in hits:
        d = docs.get(std)
        if not d:
            continue
        art = AI.resolve_to_parse_dir(d, idx)
        if art["dir"] is None:
            continue
        res = _cached(Path(art["dir"]), d.get("file_path"))
        if not res:
            continue
        if res.get("deep_output"):
            from src.core.ingestion.middle_locator import find_middle_files
            mids = find_middle_files(Path(res["deep_output"]))
            if not mids:
                continue
            items, ps = load_middle_items(mids[0])
        else:
            items, _ = load_middle_items_from_blocks(res["blocks"])
            ps = {int(k) - 1: (float(v["width"]), float(v["height"]))
                  for k, v in (res.get("geometries") or {}).items()}
        split = split_items_into_clauses(items)
        models, _ = build_clause_models("probe", std, "standard", split, ps)
        samples = []
        for m in models:
            txt = m.content_text or ""
            got = list(A.audit_clause(txt)) + list(
                C.classify_clause(m.clause_number or "", txt, m.ocr_confidence or 1.0))
            if cls in got:
                samples.append({"clause": m.clause_number, "text": txt[:220],
                                "conf": round(m.ocr_confidence or 0.0, 3)})
            if len(samples) >= per:
                break
        out["docs"].append({"std_no": std, "hits": len(samples), "samples": samples})
        print(f"\n【{std}】")
        for s in samples:
            print(f"  {s['clause']:<12} conf={s['conf']:<6} {s['text'][:150]!r}")
    ed = rd / "evidence"
    atomic_write(ed / f"{_safe(cls)}.json", out)
    print(f"\n证据 → {ed / (_safe(cls) + '.json')}（{len(out['docs'])} 部）")
    return 0


def cmd_status(_args: list[str]) -> int:
    st = load_state()
    print(f"轮 #{st.get('round')} · 游标 {st.get('cursor')} · phase={st.get('phase')}")
    print(f"修复尝试：{st.get('fix_attempts')}")
    t = st.get("open_trigger")
    if t:
        print(f"待修触发：{t}")
    r = st.get("round", 1)
    for k in (r, r - 1):
        rd = round_dir(k)
        if rd.exists():
            ck = rd / "checkpoint.json"
            if ck.exists():
                c = json.loads(ck.read_text(encoding="utf-8"))
                cls = {k2: len(v) for k2, v in c["class_docs"].items()}
                top = sorted(cls.items(), key=lambda kv: -kv[1])[:6]
                print(f"轮 #{k}：已评估 {c['evaluated']} 部 · 类命中前三 {top}")
            break
    return 0


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    table = {"eval": cmd_eval, "resume": cmd_eval, "status": cmd_status,
             "compare": cmd_compare, "escalate": cmd_escalate,
             "arbiter": cmd_arbiter,
             "fix-done": cmd_fix_done, "doctor": cmd_doctor,
             "evidence": cmd_evidence, "poison-test": cmd_poison_test,
             "index": lambda a: (AI.build(verbose=True), 0)[1]}
    if cmd not in table:
        print(__doc__)
        sys.exit(2)
    if cmd == "resume" and "--resume" not in args:
        args = args + ["--resume"]
    sys.exit(table[cmd](args))


if __name__ == "__main__":
    main()
