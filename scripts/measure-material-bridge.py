"""用**新语料**测「翻译层」：把用户的大白话接到这份资料自己的说法上，能抢回多少召回？

背景（业主："要用这个翻译层测试"）：
`scripts/measure-material-recall.py` 已实测出，在**这份新资料**（我们自己的 RAG 学习笔记）
上：用材料原话问 ⇒ 前5 **92.8%**；换成大白话问 ⇒ 前5 **20.0%**、前1 **0.0%**。
中间这 73 个百分点，就是"翻译层"要抢回来的东西。

**为什么这一测是通用化的关键**：现在的翻译层是从**法规库的术语表**（42,181 条）建的，
它**不认识这份新资料的词**。所以这里**从这份资料自己身上**建术语表（机械抽：
加粗词、反引号词、中英并列的英文名），再跑同一套"有界选择"机制。
⇒ 同一套机制换一份资料还灵 ⇒ 说明通用；不灵 ⇒ 说明它绑死在法规语料上。

三臂（同一批 20 条大白话提问、同一批靶子）：
  A 基线  ：大白话直接搜
  B 翻译  ：语义选 k 个术语 → **只拿术语搜**（与生产那套一致："先翻译、再搜"）
  C 混合  ：大白话 + 选中术语一起搜
并给**上界参考**（材料原话问）：92.8%（上一个脚本量的）。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-material-bridge.py [--k 5] [--project prj_xxx]
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# 复用召回脚本里的**测试集与材料清单**（单一真源，不抄第二份）
_spec = importlib.util.spec_from_file_location(
    "matrecall", REPO / "scripts" / "measure-material-recall.py")
matrecall = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(matrecall)

from src.core.retrieval import embedder  # noqa: E402
from src.core.retrieval.term_bridge import TermEntry, TermIndex  # noqa: E402
from src.core.storage import material_repo as mr  # noqa: E402

BOLD = re.compile(r"\*\*(.+?)\*\*")
CODE = re.compile(r"`([^`\n]{2,40})`")
PAIR = re.compile(r"[\u4e00-\u9fff]{2,12}[（(]([A-Za-z][A-Za-z0-9+_.\- ]{1,30})[）)]")
HAS_WORD = re.compile(r"[\u4e00-\u9fffA-Za-z]")


def extract_terms(text: str) -> dict[str, str]:
    """从一份笔记里机械抽候选术语 → {术语: 它第一次出现的那一行（当"定义正文"）}。

    只抽**看起来是术语**的：加粗词、反引号里的词、中英并列里的英文名。
    ⚠ 不抽"任意英文单词"——那会把 the/and 之类全收进来（本会话已在别处踩过这个坑）。
    """
    out: dict[str, str] = {}
    lines = text.splitlines()
    cands: list[str] = []
    for m in BOLD.finditer(text):
        cands.append(m.group(1))
    for m in CODE.finditer(text):
        cands.append(m.group(1))
    for m in PAIR.finditer(text):
        cands.append(m.group(1))
    for c in cands:
        t = c.strip().strip("：:，,。.、（）()[]`*\"'")
        if not (2 <= len(t) <= 30) or not HAS_WORD.search(t):
            continue
        if t not in out:
            for ln in lines:                     # 第一次出现的那一行当"定义正文"
                if t in ln and len(ln.strip()) > len(t) + 4:
                    out[t] = ln.strip()[:200]
                    break
            else:
                out[t] = t
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--k", type=int, default=5, help="选几个术语")
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover
            pass

    projects = mr.list_projects()
    pid = args.project or (projects[0]["project_id"] if projects else None)
    if not pid:
        print("库里没有参考资料项目。")
        return 2

    # ── 从这份资料自己身上建术语表 ─────────────────────────────────────────
    terms: dict[str, str] = {}
    docs: dict[str, list[dict]] = {}
    for p in matrecall.NOTES:
        if not p.is_file():
            continue
        terms.update(extract_terms(p.read_text(encoding="utf-8")))
        for m in mr.list_materials(pid):
            if m["title"] == p.stem:
                docs[str(p)] = mr.material_chunks(m["material_id"])
                break
    print(f"资料项目 {pid}；从这 5 份笔记抽出候选术语 **{len(terms)}** 个")
    idx = TermIndex(
        entries=[TermEntry(term=t, english="", clause_revision_id="m", doc_id="m",
                           definition=d) for t, d in terms.items()])
    idx.vectors = embedder.embed_batch([e.definition for e in idx.entries])
    print(f"术语向量建好（{len(idx)} 条）", flush=True)

    # ── 三臂对照（同一批 20 条大白话、同一批靶子）──────────────────────────
    cases: list[tuple[str, str, list[dict]]] = []
    for p in matrecall.NOTES:
        chunks = docs.get(str(p)) or []
        txt = p.read_text(encoding="utf-8") if p.is_file() else ""
        if not chunks:
            continue
        for q, anchor in matrecall.LAY_QUERIES:
            if anchor in txt:
                cases.append((q, anchor, chunks))
    print(f"有效用例 {len(cases)} 条（大白话提问，材料里没有这些说法）")

    def run(mode: str) -> tuple[int, int, int, float, list[str]]:
        h1 = h5 = h8 = 0
        rr = 0.0
        n = 0
        picked_terms: list[str] = []
        for q, anchor, chunks in cases:
            tgt = matrecall._chunk_containing(chunks, anchor)
            if tgt is None:
                continue
            sel = idx.select(q, k=args.k)
            names = [e.term for e in sel]
            if mode == "A":
                query = q
            elif mode == "B":
                query = " ".join(names)
            else:
                query = q + " " + " ".join(names)
            if not query.strip():
                continue
            n += 1
            picked_terms += names[:2]
            res = mr.search_materials(pid, query, limit=8)
            ids = [x.get("chunk_id") for x in res]
            want = chunks[tgt].get("chunk_id")
            if want in ids:
                r = ids.index(want) + 1
                rr += 1.0 / r
                h1 += int(r <= 1)
                h5 += int(r <= 5)
                h8 += int(r <= 8)
        return h1, h5, h8, rr / max(n, 1), picked_terms[:8]

    print()
    print("=" * 74)
    print(f"翻译层在**新语料**上的效果（{len(cases)} 条大白话；选 {args.k} 个术语）")
    print("=" * 74)
    print(f"  {'臂':<28}{'前1':>8}{'前5':>8}{'前8':>8}{'MRR':>8}")
    for mode, label in (("A", "A 基线（大白话直接搜）"),
                        ("B", "B 翻译（只拿选中术语搜）"),
                        ("C", "C 混合（大白话+术语）")):
        h1, h5, h8, mrr, sample = run(mode)
        n = len(cases)
        print(f"  {label:<28}{h1/n:>8.1%}{h5/n:>8.1%}{h8/n:>8.1%}{mrr:>8.3f}")
        if mode == "B":
            print(f"     （B 挑出来的术语样例：{sample}）")
    print()
    print("  上界参考：**用材料原话问**时前5 = 92.8%（`measure-material-recall.py` 量的）。")
    print("  读法：B/C 比 A 涨多少，就是这套机制换一份资料还能不能用的直接证据。")
    print("  ⚠ 术语表是**机械抽的**（加粗/反引号/中英并列），没人工清洗；")
    print("     抽进来的噪声术语会同时拉低 B 与 C，所以这一测给的是**下界**。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
