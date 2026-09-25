"""把学习笔记入「参考资料」平面，并**实测导入后的召回效果**（可复算）。

业主问：把教学/学习材料导入我们知识库后，**召回效果怎么样**？
这个脚本同时回答两件事：
  ① **入库**：人工上传的材料免评审、直接可召回（`origin='user'` ⇒ `review_status='approved'`，
     见 `material_repo.add_material` docstring 与 NOT-DOING #15）。支持 `.md`。
  ② **召回实测**：两套查询，同一批材料，比出差距——
     · **术语式**：直接用笔记里的小节标题当查询（材料里原样出现 ⇒ 这是"简单档"）；
     · **大白话**：换成**材料里没有的说法**（这才是用户真实提问的样子 ⇒ "困难档"）。
     两档都机械生成/固定写死，**不挑例子**。

靶子口径：一个查询的"正确答案"＝**包含那段内容的切片**。
  · 术语式：靶子＝含该小节标题那一行的那一片；
  · 大白话：靶子＝含我写的**锚句**的那一片（锚句是我从笔记里挑的实词组合，查询**不含**它）。

⚠ 只读检索侧；写入只发生在「参考资料」平面（**可删**：`material_repo.delete_material`）。
⚠ 重复跑不会产生重复材料（按 `content_hash` 查重）。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-material-recall.py [--project prj_xxx]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.core.ingestion.material_ingest import ingest_material_file  # noqa: E402
from src.core.storage import material_repo as mr  # noqa: E402

#: 要入库的五份笔记（我们自己写的学习笔记 ⇒ 无第三方许可问题）。
NOTES: tuple[Path, ...] = (
    REPO / "docs" / "research" / "rag-encyclopedia-study.md",
    REPO / "var" / "tmp" / "study" / "chunking.md",
    REPO / "var" / "tmp" / "study" / "query.md",
    REPO / "var" / "tmp" / "study" / "eval-routing.md",
    REPO / "var" / "tmp" / "study" / "literature.md",
)

#: 大白话档：**查询里故意不出现**锚句的词，模拟"用户说的和库里写的不一样"。
#: (查询, 该答案所在的锚句——锚句必须在材料里逐字存在)
LAY_QUERIES: tuple[tuple[str, str], ...] = (
    ("怎么才能让回答不瞎编", "Faithfulness"),
    ("检索回来的东西太大一坨怎么办", "EmbeddingsFilter"),
    ("为什么东西一多就挑不准了", "Reimers"),
    ("用户问的和文献写的对不上怎么接", "vocabulary problem"),
    ("英文少写个字母就搜不到", "词干"),
    ("一块内容太长塞不进模型", "嵌入窗口"),
    ("怎么判断这次该找多少条", "top_k"),
    ("答案里的链接点进去要能看到原文", "引用"),
)


def _chunk_containing(chunks: list[dict], needle: str) -> int | None:
    for i, c in enumerate(chunks):
        if needle in (c.get("text") or ""):
            return i
    return None


def _headings(text: str) -> list[str]:
    """取 `## ` / `### ` 小节标题（去掉序号与强调标记），当"术语式"查询。

    ⚠ 第一版忘了剥 markdown 的 `**`，于是产出 `我们**走对了**` 这种**假查询**
    （它不是一句能问的话），白算成"没召回"。已修——**假查询会把命中率算低**。
    """
    out: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^#{2,4}\s+(.+?)\s*$", line)
        if not m:
            continue
        h = m.group(1)
        h = re.sub(r"[*`_]", "", h)                       # 剥强调/代码标记
        h = re.sub(r"^[一二三四五六七八九十\d.、）)\s]+", "", h).strip()
        h = re.sub(r"[（(].*?[）)]", "", h).strip()
        if 4 <= len(h) <= 40 and re.search(r"[\u4e00-\u9fffA-Za-z]", h):
            out.append(h)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None, help="参考资料项目 id（默认用库里已有的第一个）")
    ap.add_argument("--dup-notes", type=int, default=0,
                    help="把前 N 份笔记的**近似副本**也入库（模拟'教程原文与我们笔记并存'），"
                         "测完自动删除。用来量'近重复内容会不会抢名次'")
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover
            pass

    projects = mr.list_projects()
    pid = args.project or (projects[0]["project_id"] if projects else None)
    if not pid:
        print("库里没有参考资料项目；先建一个再跑。")
        return 2
    print(f"参考资料项目：{pid}")

    # ── ① 入库 ────────────────────────────────────────────────────────────
    print()
    print("① 入库（人工上传 ⇒ 免评审、直接可召回）")
    ingested: dict[str, list[dict]] = {}
    for p in NOTES:
        if not p.is_file():
            print(f"   ⚠ 跳过（不存在）：{p}")
            continue
        r = ingest_material_file(pid, p, origin="user")
        mid = r["material_id"]
        chunks = mr.material_chunks(mid)
        ingested[str(p)] = chunks
        flag = "重复（已存在）" if r.get("duplicate") else "新入库"
        print(f"   {p.name:<28}{flag:<12} 切片 {len(chunks):>4}  状态 {r.get('review_status')}")

    # ── ② 术语式档：拿小节标题当查询 ───────────────────────────────────────
    def measure() -> None:
        print()
        print("② 召回实测")
        for label, is_lay in (("术语式（材料里原样有）", False), ("大白话（材料里没有）", True)):
            hits1 = hits5 = hits8 = 0
            rr = 0.0
            n = 0
            misses: list[str] = []
            cases: list[tuple[str, str, list[dict]]] = []
            for p in NOTES:
                chunks = ingested.get(str(p)) or []
                txt = p.read_text(encoding="utf-8") if p.is_file() else ""
                if not chunks:
                    continue
                if is_lay:
                    for q, anchor in LAY_QUERIES:
                        if anchor in txt:
                            cases.append((q, anchor, chunks))
                else:
                    for h in _headings(txt):
                        cases.append((h, h, chunks))

            for q, anchor, chunks in cases:
                tgt = _chunk_containing(chunks, anchor)
                if tgt is None:
                    continue
                n += 1
                res = mr.search_materials(pid, q, limit=8)
                ids = [x.get("chunk_id") for x in res]
                want = chunks[tgt].get("chunk_id")
                if want in ids:
                    rank = ids.index(want) + 1
                    rr += 1.0 / rank
                    hits1 += int(rank <= 1)
                    hits5 += int(rank <= 5)
                    hits8 += int(rank <= 8)
                elif len(misses) < 5:
                    misses.append(q)

            if not n:
                print(f"   {label}：没有有效用例（锚句/标题没对上切片）")
                continue
            print(f"   {label}")
            print(f"     用例 {n:>3}   前1 {hits1/n:>6.1%}   前5 {hits5/n:>6.1%}"
                  f"   前8 {hits8/n:>6.1%}   MRR {rr/n:.3f}")
            if misses:
                print(f"     没召回的例子：{misses}")

    measure()

    # ── ③ 近重复内容的干扰（可选）：模拟"教程原文与我们的笔记并存" ──────────
    if args.dup_notes > 0:
        print()
        print(f"③ 近重复干扰：把前 {args.dup_notes} 份笔记的**近似副本**也入库，再测一遍")
        print("   （为什么这么测：`add_material` 的查重是**按整份文件的哈希**算的，")
        print("     所以我们笔记里的逐字引文**不会**被判重复——两份内容会并存抢名次。）")
        dup_paths: list[Path] = []
        dup_mids: list[str] = []
        for p in NOTES[:args.dup_notes]:
            if not p.is_file():
                continue
            q = REPO / "var" / "tmp" / "study" / f"dup-{p.name}"
            q.write_text("（原文副本·仅用于测量近重复干扰）\n\n" + p.read_text(encoding="utf-8"),
                         encoding="utf-8")
            dup_paths.append(q)
            r = ingest_material_file(pid, q, origin="user")
            dup_mids.append(r["material_id"])
            print(f"   + {q.name:<32} 切片 {len(mr.material_chunks(r['material_id'])):>4}")
        print("   —— 加了副本之后的数字：")
        measure()
        # 自清理：测完把副本材料删掉（**只删我们自己刚建的这几份**）
        for mid in dup_mids:
            mr.delete_material(mid)
        for q in dup_paths:
            q.unlink(missing_ok=True)
        print(f"   （已删除刚建的 {len(dup_mids)} 份副本材料与它们的临时文件，库恢复原状）")

    print()
    print("  读法：**术语式与大白话的差距**才是要害 —— 术语式高、大白话低，")
    print("       说明「换个说法就找不着」这个病**换一种资料照样犯**，不是法规语料特有的。")
    print("       ⚠ 术语式那档是「送分题」（查询词在材料里原样出现），不能当产品效果。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
