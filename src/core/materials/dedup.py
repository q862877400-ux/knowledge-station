# -*- coding: utf-8 -*-
"""材料平面：**近重复检测**（Phase C 前置，2026-09-17）。

## 为什么需要它（业主那句"不是随便找个什么网络文章就当权威信源"的下一层）
`authority._source_identity` 只按**域名**判"独立来源"，独立复核（§10.17）实测出了它的漏洞：
**同一篇通稿被两个站点转载**时算两个"独立来源"，于是二手转述被升成"多源互证"。
域名这一层挡不住"一稿多发"——**必须再看内容**。

本模块提供"这两条命中是不是同一篇稿子"的判据，供 `authority` 把
**内容近似的来源合并成一个独立来源**（连通分量），从而让"≥2 个独立来源"真的意味着
"有两个**各自独立**的报道"，而不是"同一篇稿子出现在两个域名上"。

## 判据与它的诚实边界
- **归一化**：去空白与标点、大小写折叠、全角转半角（复用 `text_utils` 的口径），
  这样"空格/标点/全角"的差异不算不同稿。
- **相似度**：字符 n-gram（默认 5-gram）的 Jaccard。选字符 n-gram 而非词 n-gram，
  是因为中文没有空格分词、且转载常改标点与断行。
- ⚠ **阈值是启发式**（默认 0.8）：它不是在判"事实是否相同"，只是在判
  "**文字是否几乎一样**"。两条**改写过的**报道（真正的独立采写）会被判为**不相似**——
  这是**对的**（它们确实是两个独立来源）；但一个站点把通稿**大改**后重发，本模块抓不到。
  **不要**把它宣传成"辟谣/查重"，它只回答"看起来是不是同一篇稿子"。
- 只用于**降级**（合并来源、把互证收紧），**绝不**用于"自动批准"或"自动判定造假"——
  判据存疑时的默认动作永远是**更保守**（少给一个互证），而不是更激进。
"""
from __future__ import annotations

import re
import unicodedata

#: 字符 n-gram 的 n。5 在中文短句上仍有一定区分度，又不至于因个别改字而崩塌。
DEFAULT_NGRAM = 5

#: 判"同一篇稿子"的相似度阈值。⚠ 见模块头的诚实边界。
DEFAULT_THRESHOLD = 0.8

#: 短文本（归一化后短于这个长度）不做 n-gram——样本太短，Jaccard 极不稳定；
#: 此时退化为"归一化后是否相等"。
_SHORT_TEXT_CHARS = 3 * DEFAULT_NGRAM

_PUNCT_RE = re.compile(r"[\s\W_]+", re.UNICODE)


def normalize_text(raw: str | None) -> str:
    """归一化：全角→半角（NFKC）、大小写折叠、**去掉空白与标点**、只留文字与数字。

    去标点是刻意的：转载最常见的差异就是标点与断行。
    """
    s = unicodedata.normalize("NFKC", str(raw or ""))
    s = s.lower()
    return _PUNCT_RE.sub("", s)


def _ngrams(s: str, n: int) -> set[str]:
    if len(s) <= n:
        return {s} if s else set()
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def similarity(a: str | None, b: str | None, *, n: int = DEFAULT_NGRAM) -> float:
    """归一化后的字符 n-gram Jaccard（0~1）。

    短文本（归一化后 < 3n）退化为"相等则 1，否则 0"——见 `_SHORT_TEXT_CHARS` 的理由。
    两侧都为空（归一化后无内容）时返回 **1.0**（"都没有内容"算同类，
    因为对互证而言它们同样提供不了独立信息；调用方另有空文本的兜底）。
    """
    na, nb = normalize_text(a), normalize_text(b)
    if na == "" and nb == "":
        return 1.0
    if na == "" or nb == "":
        return 0.0
    if len(na) < _SHORT_TEXT_CHARS or len(nb) < _SHORT_TEXT_CHARS:
        return 1.0 if na == nb else 0.0
    ga, gb = _ngrams(na, n), _ngrams(nb, n)
    if not ga or not gb:
        return 1.0 if na == nb else 0.0
    inter = len(ga & gb)
    union = len(ga | gb)
    return inter / union if union else 0.0


def near_duplicate(a: str | None, b: str | None, *, threshold: float = DEFAULT_THRESHOLD,
                   n: int = DEFAULT_NGRAM) -> bool:
    """两条文本是否"看起来是同一篇稿子"（相似度 ≥ 阈值）。"""
    return similarity(a, b, n=n) >= threshold


def group_by_content(texts: list[str], *, threshold: float = DEFAULT_THRESHOLD,
                     n: int = DEFAULT_NGRAM) -> list[list[int]]:
    """把下标按"内容近似"聚成组（**并查集**连通分量），返回组列表。

    用连通分量而不是"贪心分配"：近似关系**不传递**（A≈B、B≈C 但 A≉C 是可能的），
    贪心会让结果依赖遍历顺序；连通分量是可复现的定义（同输入同输出）。

    ⚠ 复杂度是 O(k²)（k = 命中条数，实际 ≤ limit=8），**不做**任何索引优化——
    这里批评测集太小，而"少写一个近似索引"比"多一个只在极端数据下错的优化"划算。
    """
    m = len(texts)
    parent = list(range(m))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    for i in range(m):
        for j in range(i + 1, m):
            if near_duplicate(texts[i], texts[j], threshold=threshold, n=n):
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(m):
        groups.setdefault(find(i), []).append(i)
    # 组间按"最小下标"排序，保证输出稳定（不依赖 dict 序）
    return [groups[k] for k in sorted(groups)]


def independent_source_count(domains: list[str | None], texts: list[str], *,
                             threshold: float = DEFAULT_THRESHOLD,
                             n: int = DEFAULT_NGRAM) -> tuple[int, list[list[str]]]:
    """**独立来源数**：在**域名**上做连通分量，内容近似的域名被并成一组。

    这就是"一稿多发不算两个来源"的落地。三类情形都要对：
      · `a.com` 与 `b.com` 载**同一篇稿子** → 并成一组 → **1 个**独立来源；
      · `a.com` 载**两篇不同**文章 → 同一个节点，仍 **1 个**来源（同一家）；
      · `a.com` 载 X、`b.com` 载另一篇 Y → 两个分量 → **2 个**来源。

    ⚠ 第一版我按"内容分组的个数"计数——那会把"同一家媒体的两篇不同文章"算成两个来源。
    正确的图是**域名图**（节点=域名，边=承载近似内容），不是内容图。

    Args:
        domains: 每条命中的来源域名（`None` = 身份未知，**不参与**）。
        texts: 与 `domains` 等长的命中文本。
    Returns:
        `(独立来源数, 合并后的域名分组)`；分组用于在 notes 里如实说明谁与谁被并了。
    """
    known = sorted({str(d) for d in domains if d})
    if not known:
        return 0, []
    parent = {d: d for d in known}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    pairs = [(i, j) for i in range(len(domains)) for j in range(i + 1, len(domains))
             if domains[i] and domains[j] and domains[i] != domains[j]]
    for i, j in pairs:
        if near_duplicate(texts[i], texts[j], threshold=threshold, n=n):
            union(str(domains[i]), str(domains[j]))

    groups: dict[str, list[str]] = {}
    for d in known:
        groups.setdefault(find(d), []).append(d)
    merged = [sorted(v) for _k, v in sorted(groups.items())]
    return len(merged), merged
