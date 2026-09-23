"""门禁基线里的"跳过节点"必须**真的还在**（2026-09-24，审计 B5）。

## 这一组在守什么

``scripts/gates-baseline.json`` 里有两份 nodeid 名单：

* ``environmental_skip_nodeids``：**环境类**跳过（模型没下到、网络不通……）——随环境出现/消失
  属正常，所以门禁**不当回归**；但正因为"白名单**外**的新 skip 才判红"，一份**永不清理**的
  白名单就是**永久放水**：某条用例被删/改名之后名字还留在名单里，将来**同一个名字**再以
  非环境原因跳过，门禁会当成"已知的环境跳过"放过去。
* ``skip_nodeids``：记基线时那一次真实跑出来的跳过节点（棘轮的另一半）。

``scripts/run-gates.ps1`` 的 ``-UpdateBaseline`` 把旧白名单**逐字抄回** ⇒ 名单**只增不减**。
实测到的第一个幽灵：``tests.test_compliance::test_behavior_review_face_collection`` ——
它整个测试文件 (``tests/test_compliance.py``) 在 2026-09-22 的删单批 (``683c6f6``) 里被删除，
名字却还在 ``environmental_skip_nodeids`` 里，并被 2026-09-23 的 ``-UpdateBaseline`` (``4252385``)
原样抄了下来。
⚠ **就地更正（2026-09-24 独立复核查证）**：把它登记进白名单的**首次**是更早的 `ea31479`
（不是 4252385）——上面那句只说了"最近一次把它抄下来的人"。更完整的事实是：**它被删用例之后
又经历了若干次 `-UpdateBaseline`，一次都没被剔掉**（这正是"只增不减"的实物标本）。

## 判据（两条，互为对照）

1. 名单里**每一条**都必须"还在"：模块文件在、且那个 ``def`` 在（或它在这一跑真的被收集到）。
   ⚠ **主体判据是静态扫描，不是"这一跑收集到没有"**：单跑本文件时 ``request.session.items``
   只有本文件那几条 ⇒ 白名单里每一条都会显得"不在"，那是**假红**。运行时会话只作**补充**证据
   （全量跑时它能兜住"动态生成、静态扫不出"的用例）。
2. **判据自己要被验**（否则"扫描器恒真"就是新的假绿）：``test_the_alive_checker_itself_...``
   三向自检 —— 模块不存在 ⇒ 必须判"不在"；模块在但 ``def`` 不在 ⇒ 必须判"不在"；
   真模块里真有的 ``def`` ⇒ 必须判"在"。三条都在断言里，每次运行都跑。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "scripts" / "gates-baseline.json"

#: 基线里的名单字段（两份都要守）。
LIST_FIELDS = ("environmental_skip_nodeids", "skip_nodeids")


def _module_candidates(dotted: str) -> list[Path]:
    """junit 形态的点分名（**可能带类名**）⇒ 候选文件路径，由长到短。

    `tests.test_x.TestY::test_z` 的第一段是 `tests.test_x.TestY`（junit 把类名塞进
    `classname`）⇒ 先试 `tests/test_x/TestY.py`、再退到 `tests/test_x.py`。
    """
    parts = [p for p in dotted.split(".") if p != ""]
    return [REPO.joinpath(*parts[:i]).with_suffix(".py") for i in range(len(parts), 0, -1)]


def _split_entry(entry: str) -> tuple[str, str]:
    """`tests.test_x.TestY::test_z[p]` → ('tests.test_x.TestY', 'test_z')。

    收集期跳过的键是 `::<模块>` 形态（junit 的 `classname=""`）⇒ 左半为空、右半是模块名。
    """
    left, _, right = entry.partition("::")
    if left == "":
        return right, ""
    return left, right


def alive_static(entry: str) -> bool:
    """**静态**判一条 nodeid 还在不在：模块文件在、**类段在**、且那个 def 在。

    不依赖"这一跑收集到了什么" ⇒ 子集跑（`pytest tests/xxx.py`）也判得准。

    ⚠ **类段必须一起验**（2026-09-24 独立复核点出的洞）：junit 形态把类名塞进点分前缀
    （`tests.test_x.TestY::test_z`）。只验 `def` 的话，`tests.test_x.改过的类::真方法名`
    会被判成"在"——因为模块文件确实在、同名 `def` 也确实在。⇒ 前缀里**多出来的每一段**
    都要在文件里找到 `class <名字>`。
    """
    module, test = _split_entry(entry)
    test = test.split("[", 1)[0]
    parts = [p for p in module.split(".") if p != ""]
    for i in range(len(parts), 0, -1):                        # 由长到短找模块文件
        cand = REPO.joinpath(*parts[:i]).with_suffix(".py")
        if not cand.is_file():
            continue
        if test == "":
            return True
        src = cand.read_text(encoding="utf-8", errors="replace")
        for cls in parts[i:]:                                # 类段：多出来的每一段都要有 class
            if re.search(rf"^\s*class\s+{re.escape(cls)}\b", src, re.M) is None:
                return False
        return re.search(rf"^\s*def\s+{re.escape(test)}\s*\(", src, re.M) is not None
    return False


def _session_keys(request) -> set[str]:
    """这一跑真收集到的节点，折成与基线同一形状（**补充**证据，不是主体判据）。"""
    keys: set[str] = set()
    for item in request.session.items:
        parts = str(item.nodeid).replace("\\", "/").split("::")
        head = parts[0]
        if head.endswith(".py"):
            head = head[:-3]
        head = head.replace("/", ".")
        rest = parts[1:]
        if not rest:
            keys.add(f"::{head}")
            continue
        keys.add(f"{head}::{'::'.join(rest)}")
        if len(rest) >= 2:                       # 类里的用例：junit 形态是 `模块.类::用例`
            keys.add(f"{head}.{rest[0]}::{'::'.join(rest[1:])}")
    return keys


def test_gate_baseline_skip_lists_have_no_vanished_nodes(request):
    """两份名单里的每一条都必须还在；有幽灵 ⇒ 红，并把幽灵逐条点名。"""
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    session_keys = _session_keys(request)

    def alive(entry: str) -> bool:
        return alive_static(entry) or entry in session_keys

    vanished: list[str] = []
    for field in LIST_FIELDS:
        for raw in (data.get(field) or []):
            entry = str(raw)
            if not alive(entry):
                vanished.append(f"{field} 里的 `{entry}`")

    assert not vanished, (
        "门禁基线的跳过名单里有**已经消失的节点**（白名单只增不减 ⇒ 永久放水）：\n  - "
        + "\n  - ".join(vanished)
        + f"\n（判法：模块文件在且 `def` 在，或它在这一次运行里真的被收集到；基线文件 `{BASELINE}`）"
        + "\n⇒ 删掉这些条目（或用 `scripts/run-gates.ps1 -Full -UpdateBaseline` 让它自己剔除），"
          "别让一个不存在的名字继续替将来的跳过背书。"
    )


def test_the_alive_checker_itself_is_not_a_tautology():
    """判据自己要被验：三种情形各断言一次（缺一不可，否则"什么都判在/判不在"看不出来）。"""
    # ① 模块文件不存在 ⇒ 不在
    assert alive_static("tests.test_no_such_module_zzz::test_ghost") is False

    # 锚：真实存在的第一个 tests/test_*.py（不写死名字 —— 写死的话文件一改名这条自检就哑了）
    mods = sorted((REPO / "tests").glob("test_*.py"))
    assert mods, "tests/ 下一个 test_*.py 都没有 ⇒ 自检的锚没了，这条判据已经失效"
    anchor = mods[0]
    dotted = f"tests.{anchor.stem}"

    # ② 模块在、def 不在 ⇒ 不在
    assert alive_static(f"{dotted}::test_ghost_zzz") is False

    # ③ 模块在、def 也在 ⇒ 在（没有这一条，①②可能是"什么都判不在"而不是真的判准了）
    src = anchor.read_text(encoding="utf-8", errors="replace")
    found = re.search(r"^\s*def\s+(\w+)\s*\(", src, re.M)
    assert found is not None, f"{anchor.name} 里连一个 def 都没有 ⇒ 自检的锚不成立"
    assert alive_static(f"{dotted}::{found.group(1)}") is True
