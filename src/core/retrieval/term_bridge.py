"""术语桥（P1 第 2 步"翻译层"的第一版实现）。

**它解决什么**：用户用大白话问，而库里说的是术语。实测（见
`docs/research/lay-gap-decomposition.md`）：1832 条大白话里 **53% 与原文一个字都对不上**，
按字找**原理上无解**；而库内共现只接得上 20.9%、外部百科（中文维基重定向）只接得上 1.5%。

**它怎么做**（每一步都有本会话实测支撑）：
1. **语义选术语**——不问"怎么把大白话翻成任意说法"，而问
   "这条大白话指的是我库里这几个术语中的哪一个"（**有界选择**，不是自由生成）。
   实测：字面判据 ≈ 随机（top-1 0.7% vs 0.20%，且排对的那些是**0 字重合靠字母序蒙的**）；
   语义 top-1 **22.2%** / top-5 **47.3%**（**500 个候选**，生产同款 `bge-small-zh-v1.5`）。
   ⚠ 500 是**说法文件里那 500 个答案术语**（最乐观上界）；全库 42,181 个候选下这条路
   塌到 top-1 **2.5%** / top-5 **8.6%**（探针，见下）。
2. **术语用"定义正文"表示**（不是只用术语名）——500 候选下实测 22.2% vs 16.4%。
   定义正文库里现成：术语条款天生是「中文名 英文名 定义」三段式。
3. **扇出 top-k 个术语、每个各查一次，用「轮转交错」合并**——
   实测（k=5、每术语前 20、500 候选、非 A 子集 1,651 条）：
   顺序拼接 前 20 **20.6%** → 轮转 **29.7%**，
   **查询数不变、零额外成本**。机制：顺序拼接时 top-1 术语的 20 条把返回位占满，
   后面选中的术语一条都进不了前 20 ⇒ **扇出的收益被合并顺序吃掉**。

**代价**：术语表与它的向量是**离线算好的**（候选表变了才重算，全库 42,181 条实测 531 s）；
在线只多一次嵌入 + k 次 FTS。实测 1651 条的嵌入+选择合计约 2 秒（单条约 1.2 ms），
k=5 的额外 FTS 约 53 ms。

🔴 **最重要的边界：上面那个"前 20 29.7%"是 500 个候选下的数。真实候选集是全库 42,181 个
（84 倍），同一批说法上实测塌成 8.4%**（2026-09-25，`scripts/measure-term-bridge.py --all`）：

| 候选集 | A 基线 前20 | 桥·轮转 前20 | "选对术语" 前1/前5 |
|---|---|---|---|
| 500（早期实验口径） | 4.6% | 32.6% | 22.2% / 47.3% |
| **42,181（真实口径）** | 4.6% | **8.4%** | **2.5% / 8.6%** |

⇒ 机制**成立且为正**（4.6% → 8.4%），但**瓶颈是候选集太大**，不是翻译本身。
已实测**无效**的缩减法：先选文档再在文档内选术语（级联后与单层一样）、
给查询加 bge 官方检索指令前缀（无差别）。详细取证见 `docs/research/lay-gap-decomposition.md` §四·补五。

⚠ 其它边界：
* 只用了"定义正文"这一种术语表示（500 候选下优于术语名），**全库候选下哪种最好未测**；
* 以上全部只测了**按字找这一路**（`fts_match_expr` + `clause_fts`）；向量那一路能否叠加，未测；
* 靶子是"该术语的**定义条款**"，对大白话偏苛刻。
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

#: 「编号 中文名 英文名 中文定义」——术语条款的形态。
#: ⚠ **口径唯一**：本会话的探针脚本各自抄过一份，这里收拢成一份，别再抄第二份。
TERM_ENTRY_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)

#: 术语名的清洗：去首尾标点
_TRIM = "（）()·、-—"


@dataclass(frozen=True)
class TermEntry:
    """一条术语（取自某个术语条款）。"""

    term: str
    english: str
    clause_revision_id: str
    doc_id: str
    definition: str                      # 已把空白折叠过的定义正文（供嵌入用）


@dataclass
class TermIndex:
    """术语表 + 它们的向量。`vectors[i]` 对应 `entries[i]`。"""

    entries: list[TermEntry] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)
    #: 归一化后的矩阵缓存（`None` = 还没建）。见 `_matrix`。
    _mat: object = None
    #: 缓存**认的是"哪一份 vectors 对象"**，不是条数。
    #: ⚠ 复核 2026-09-25 抓到：只按 `len(vectors)` 失效时，
    #: **等长换集**（收窄候选时换了内容但条数没变）会**静默复用旧矩阵**。
    #: 现在存对象引用比对（`is`）；原地改同一个 list 的内容仍看不出来——
    #: 但本仓没有任何地方这么干，且那是 Python 层面的普遍坑，不是这一处的。
    _mat_src: object = None

    def __len__(self) -> int:
        return len(self.entries)

    def _matrix(self):
        """把向量堆成**已归一化**的矩阵（懒建，按条数失效）。

        为什么需要：真实候选集是**全库 42,181 条**，纯 Python 逐条算余弦
        实测约 **数小时**（1651 条说法 × 42,181 条 × 512 维）；矩阵乘一次查询
        只有 42,181×512 次乘加，交给 BLAS 是**毫秒级**。
        这不是优化洁癖——**不这么做，真实候选集那个边界就量不了**。
        """
        if not self.vectors:
            return None
        try:
            import numpy as np
        except ImportError:                     # pragma: no cover - 环境相关
            return None
        if self._mat is None or self._mat_src is not self.vectors:
            # ⚠ **float64（不是 float32）**：这是**设计理由，不是测量结论**——
            #   `_cos`（纯 Python 参照实现）用 Python 浮点＝float64，
            #   让加速路径与它在**同一精度**上算，可以少一类"边界上名次变了"的可能。
            #   代价是矩阵大一倍（42,181×512 ≈ 173 MB）＋ BLAS 慢约 2×（仍是毫秒级）。
            #   ⚠ 原来这里写的是"**必须** float64，否则边界名次会变"——
            #   **那句话没有实测支撑**（复核 2026-09-25 指出，我认）。已改成现在这种说法。
            #   已测到的是另一件事：float64 矩阵下，加速路径与参照实现在 25 条真查询 ×
            #   42,181 候选上 **top-5/top-20 集合与名次全部相同**（探针 probe-topk-equivalence.py）。
            m = np.asarray(self.vectors, dtype=np.float64)
            n = np.linalg.norm(m, axis=1, keepdims=True)
            n[n == 0] = 1.0
            self._mat = m / n
            self._mat_src = self.vectors
        return self._mat

    # ── 构建 ───────────────────────────────────────────────────────────────
    @classmethod
    def build(cls, conn: sqlite3.Connection, *, with_vectors: bool = True) -> "TermIndex":
        entries = extract_term_entries(conn)
        idx = cls(entries=entries)
        if with_vectors and entries:
            from src.core.retrieval import embedder
            # 用**定义正文**当术语的表示（实测优于只用术语名）
            idx.vectors = embedder.embed_batch([e.definition for e in entries])
        return idx

    # ── 存取（离线算一次，在线只读盘）───────────────────────────────────────
    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.write_text(json.dumps({
            "entries": [{"term": e.term, "english": e.english,
                         "clause_revision_id": e.clause_revision_id,
                         "doc_id": e.doc_id, "definition": e.definition}
                        for e in self.entries],
            "vectors": self.vectors,
        }, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TermIndex":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            entries=[TermEntry(**e) for e in d["entries"]],
            vectors=d.get("vectors") or [],
        )

    # ── 查询侧 ─────────────────────────────────────────────────────────────
    def select(self, query: str, k: int = 5) -> list[TermEntry]:
        """语义选出最像的 k 个术语（有界选择）。向量没建时退回空表。"""
        if not self.entries or not self.vectors:
            return []
        from src.core.retrieval import embedder
        qv = embedder.embed_query(query)
        k = max(1, min(k, len(self.entries)))
        return [self.entries[i] for i in topk_by_cos(qv, self.vectors, k, self._matrix())]


def topk_by_cos(qv, vectors, k: int, matrix=None, *, use_numpy: bool = True) -> list[int]:
    """按余弦相似度取前 `k` 个**下标**（**分数降序；同分下标小的在前**）。

    `use_numpy=False` 或没装 numpy 时走**纯 Python 参照实现**——
    它是这条判据的**唯一真源**，`use_numpy=True` 那条只是它的加速等价物
    （`tests/test_term_bridge.py` 拿前者当裁判逐点比后者）。
    `matrix` 是调用方传进来的归一化矩阵（`TermIndex._matrix()`），省得每次重建。

    ⚠ **同分那条保证是 2026-09-25 复核打回后补上的**：原来写的是
    `head = head[np.argsort(-sims[head], kind="stable")]`，而 `argpartition` 取出的
    前 k 个**本身就是乱序**的，`kind="stable"` 只保留"argpartition 给出的那个乱序"，
    **不等于"同分按下标"**（复核构造出并列输入，两条路径给出不同序列）。
    现在改成显式按 `(分数, 下标)` 排序，注释说的才算数。
    """
    k = max(1, min(k, len(vectors)))
    if use_numpy:
        try:
            import numpy as np
            if matrix is None:
                m = np.asarray(vectors, dtype=np.float64)
                n = np.linalg.norm(m, axis=1, keepdims=True)
                n[n == 0] = 1.0
                matrix = m / n
            q = np.asarray(qv, dtype=np.float64)
            qn = float(np.linalg.norm(q))
            if qn:
                q = q / qn
            sims = matrix @ q
            head = np.argpartition(-sims, k - 1)[:k]
            # ⚠ 这一行**不是**可有可无的收尾：`argpartition` 只保证"这 k 个是最大的"，
            #   **不保证它们有序**。实测（探针见 tests 里那条前提断言）：
            #   d=8、n=2000、k=20 的一组输入上，argpartition 的前缀有 6 处逆序。
            #   显式排序同时把"同分按下标"这条保证做实。
            return sorted((int(i) for i in head), key=lambda i: (-float(sims[i]), i))
        except ImportError:                     # pragma: no cover - 环境相关
            pass
    return sorted(range(len(vectors)), key=lambda i: -_cos(qv, vectors[i]))[:k]


def extract_term_entries(conn: sqlite3.Connection, *,
                         keep_all: bool = False) -> list[TermEntry]:
    """从库里扫出所有术语条款。默认同一个术语名只留**第一条**。

    ⚠⚠ **这是个有损选择，不是"库里只有一条"**（2026-09-25 独立标签审计实测，此前这里只写
    了"与实测口径一致"，把有损说得像客观事实）：
      · 库里术语条目 **48,524** 条，但不同术语名只有 **42,181** 个 ⇒ **6,343 条同名定义被丢掉**；
      · 500 个**答案术语**里 **484 个**在库里有 ≥2 条**定义正文互不相同**的同名条目。

    **实测后果**（只换"用哪一条同名定义"这一个变量、模型与做法全不变）：
    真术语进全库前 5 从 **8.6% → 13.7%**、前 50 从 **25.7% → 34.2%**、中位名次 386 → 170。
    ⚠ 但那是 **oracle 上界**（挑哪条定义时看了答案），**不是可部署数字**：longest / shortest /
    centroid / corpusfreq 四种**事前可定**的规则只把前 5 挪到 **7.9~8.8%** ⇒ **oracle 那 5 个点
    不能靠规则免费拿到**。两句都要一起引用，只引一句会得出相反的结论。
    ⚠ 另有实打实的**抽错**：`松动爆破` / `休止位置` 这两条，术语名与说法都对，
    库里也另有更贴切的同名定义，只是"第一条"恰好不是它。

    ⚠ 还有一处**口径打架**（审计点名）：`scripts/measure-term-selection.py` 判"选对没有"时，
    **靶子**是"该术语的**任意一条**定义条款"，而**向量**是这里的**第一条**定义 ——
    靶子比向量宽，两个数不是一把尺子量的。`keep_all=True` 可以把全部同名条目都取出来，
    给"哪条定义"这类对照实验用。
    ⚠ 默认值**保持** `False`：改默认会动到已入库主判据的口径（属于单独一轮 + 必验），
    本函数只把"有损"这件事**说清并给出口**，不在这一批偷偷改数。
    """
    seen: set[str] = set()
    out: list[TermEntry] = []
    for cid, doc, txt in conn.execute(
            "SELECT clause_revision_id, doc_id, content_text FROM clause_revision"):
        m = TERM_ENTRY_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip(_TRIM)
        if not t or (t in seen and not keep_all):
            continue
        seen.add(t)
        out.append(TermEntry(term=t, english=m.group(2).strip(),
                             clause_revision_id=cid, doc_id=doc,
                             definition=re.sub(r"\s+", " ", txt or "").strip()))
    return out


def merge_round_robin(lists: Sequence[Sequence[str]]) -> list[str]:
    """**轮转交错**合并（1,1,1,1,1,2,2,2,…），并去掉重复。

    为什么不是顺序拼接：实测顺序拼接时 top-1 术语的 N 条把返回位占满，
    后面选中的术语**一条都进不了前 20** ⇒ 扇出的收益被合并顺序吃掉。
    ⚠ **两个数别混**（复核 2026-09-25 抓到同一件事在树里有两个值）：
    * **29.4%** = 暂存区那批实验（`var/tmp/repro-fanout.py`，自带一套内联选择逻辑）量到的**轮转前 20**，
      同批前 5 是 **15.7%**；
    * **29.7%** = 入库复算脚本 `scripts/measure-term-bridge.py`（本模块的选择逻辑）量到的，前 5 **15.8%**。
    两次是**不同实现上的两次实验**，数字接近但不是同一个数——所以本文件统一写
    **入库脚本的那一组（29.7% / 15.8%）**，早期那组只在文档里作为出处保留。
    """
    out: list[str] = []
    seen: set[str] = set()
    if not lists:
        return out
    longest = max(len(x) for x in lists)
    for pos in range(longest):
        for L in lists:
            if pos < len(L):
                v = L[pos]
                if v not in seen:
                    seen.add(v)
                    out.append(v)
    return out


def bridge_search(
    conn: sqlite3.Connection,
    index: TermIndex,
    query: str,
    *,
    k_terms: int = 5,
    per_term: int = 20,
) -> tuple[list[str], list[TermEntry]]:
    """术语桥检索：语义选 k 个术语 → 每个各查一次 → 轮转交错合并。

    返回 `(clause_revision_id 列表, 选中的术语)`。
    只用**按字找**这一路（`fts_match_expr` + `clause_fts`），与实测口径一致。
    """
    from src.core.text_utils import fts_match_expr

    picked = index.select(query, k=k_terms)
    if not picked:
        return [], []
    lists: list[list[str]] = []
    for e in picked:
        expr = fts_match_expr(e.term)
        if not expr.strip():
            lists.append([])
            continue
        try:
            lists.append([r[0] for r in conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, per_term)).fetchall()])
        except sqlite3.OperationalError:
            lists.append([])
    return merge_round_robin(lists), picked


def _cos(a: Iterable[float], b: Iterable[float]) -> float:
    s = na = nb = 0.0
    for x, y in zip(a, b):
        s += x * y
        na += x * x
        nb += y * y
    return s / (na ** 0.5 * nb ** 0.5) if na and nb else 0.0
