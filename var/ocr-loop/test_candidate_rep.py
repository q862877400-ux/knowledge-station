# -*- coding: utf-8 -*-
"""候选选择：**撞键组保留一个代表**的契约测试（2026-09-16 立，HANDOFF §10.31）。

**为什么必须有**：原实现 `[v[0] for v in byname.values() if len(v) == 1]`
把**归一 stem 撞键的组整组丢弃** → 实测抽样 200 组**零覆盖**，
外推约 **3,228 个标准从未被 OCR**，且 driver 的剩余候选永远不含它们
（链跑到底也补不上）。这是本仓库发现的最大内容缺口。

修复后必须钉死两条不变量：
  ① **每组恰好一个代表**（不再整组丢弃）——否则缺口回归；
  ② **代表被处理后再调用，整组不再产出候选**——否则会退化成
     "逐个试、最终撞同一个键"（把 HISTORY 那次《民法典》误报的坑重新踩回来）。

外加：代表优先"无 `(N)` 副本后缀"的那份、单成员组行为不变、
block 命中的组不产出、以及**真实语料上的回归护栏**。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import next_batch as NB  # noqa: E402

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


def with_fake_corpus(files: list[str], blocked_rel: set[str]):
    """在假语料 + 假 block 上跑 `candidates()`（其余用生产实现）。

    `blocked_rel` 传**相对路径**（相对该假语料根）——由本函数解析成绝对路径，
    否则调用方会拿另一个临时目录的路径去 block，永远不命中（我第一版就错在这）。
    """
    tmp = Path(tempfile.mkdtemp(prefix="ks-cand-"))
    corpus = tmp / "corpus"
    for rel in files:
        p = corpus / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF-1.4\n")
    blocked = {str((corpus / r)) for r in blocked_rel}
    ev = tmp / "evolve"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "holdout.json").write_text(json.dumps({"paths": []}), encoding="utf-8")
    old = (NB.CORPUS, NB.EV, NB.used_paths, NB.prior_batch_paths)
    NB.CORPUS, NB.EV = corpus, ev
    NB.used_paths = lambda: set(blocked)              # type: ignore[assignment]
    NB.prior_batch_paths = lambda: set()              # type: ignore[assignment]
    try:
        return [p.name for p in NB.candidates()]
    finally:
        (NB.CORPUS, NB.EV, NB.used_paths, NB.prior_batch_paths) = old


print("=== ① 撞键组：**恰好一个代表**（不再整组丢弃）===")
got = with_fake_corpus([
    "GB 1499.1-2024 钢筋混凝土用钢.pdf",
    "GB 1499.1-2024 钢筋混凝土用钢(1).pdf",
    "GB 1499.1-2024 钢筋混凝土用钢(2).pdf",
], set())
check("3 份同标准副本 → 产出 1 个候选", len(got), 1)
check("代表＝**无 (N) 后缀**的那份",
      got, ["GB 1499.1-2024 钢筋混凝土用钢.pdf"])

print("\n=== ② 全角空格/无空格变体（真实语料里的第二种撞键）===")
got = with_fake_corpus([
    "GB 3836.15-2024 爆炸性环境 第15部分.pdf",
    "GB 3836.15-2024 爆炸性环境　第15部分.pdf",
], set())
check("2 份变体 → 产出 1 个候选", len(got), 1)

print("\n=== ③ 关键不变量：代表被处理后再调用 → 整组不再产出 ===")
FILES = [
    "GB 8951-2016 食品安全国家标准 蒸馏酒.pdf",
    "GB 8951-2016 食品安全国家标准 蒸馏酒(1).pdf",
]
rep = with_fake_corpus(FILES, set())
check("首次：产出 1 个", len(rep), 1)
rep_path = str(Path(tempfile.gettempdir()) / "x")  # 占位，实际用下面真实路径
# 用真实路径复跑（把代表加入 block）
tmp2 = Path(tempfile.mkdtemp(prefix="ks-cand2-"))
corpus2 = tmp2 / "corpus"
for rel in FILES:
    p = corpus2 / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4\n")
ev2 = tmp2 / "evolve"
ev2.mkdir(parents=True, exist_ok=True)
(ev2 / "holdout.json").write_text(json.dumps({"paths": []}), encoding="utf-8")
old = (NB.CORPUS, NB.EV, NB.used_paths, NB.prior_batch_paths)
try:
    NB.CORPUS, NB.EV = corpus2, ev2
    NB.used_paths = lambda: set()
    NB.prior_batch_paths = lambda: set()
    first = NB.candidates()
    rep_abs = str(first[0])
    # 代表"已被跑过" → 进入 block
    NB.used_paths = lambda: {rep_abs}
    second = NB.candidates()
finally:
    (NB.CORPUS, NB.EV, NB.used_paths, NB.prior_batch_paths) = old
check("代表进 block 后：该组**不再产出候选**（非代表不浮出）",
      len(second), 0)

print("\n=== ④ 单成员组：行为不变（未被 block → 产出；被 block → 不产出）===")
check("单成员、未 block → 产出",
      len(with_fake_corpus(["GB 1-2020 甲.pdf"], set())), 1)
check("单成员、被 block → 不产出",
      len(with_fake_corpus(["GB 1-2020 甲.pdf"], {"GB 1-2020 甲.pdf"})), 0)

print("\n=== ⑤ 真实语料回归护栏（不写任何东西）===")
real = NB.candidates()
print(f"     candidates() 实测 = {len(real)}")
check("候选数已含撞键组代表（应 > 21,000；修复前为 20,609）",
      len(real) > 21000, True)
# 同一 norm_stem 在结果里只能出现一次
import artifact_index as AI  # noqa: E402
norms = [AI.norm_stem(p.stem) for p in real]
check("结果里 norm_stem 无重复（一个键一个代表）",
      len(norms) == len(set(norms)), True)

print()
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
