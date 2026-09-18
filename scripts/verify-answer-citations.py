"""能力表（`channel_answers.json`）里的**行号引用校验**哨兵。

## 为什么要有它（这不是"洁癖"，是一次真实事故）
复核 b41 抓到我一次「引用行号被自己顶歪」：我在同一个提交里给 `hbba.py` 插了 docstring，
把 `map_state_text` 那一行从 65 推到 66，而 `ch:hbba` / `ch:dbba` 的**废止** evidence 还写着 65。
**没有任何测试会红**——JSON 是文本，verdict 也没变，只有人肉核对才发现。
而能力表是"哪条渠道能答哪一类"的**唯一所有者**：它的 `evidence` 是给未来的人（和复核者）看的
**代码级凭据**。凭据指错行，比没有凭据更坏。

## 它检查什么（只查"能机检"的那一半）
- 名单里的每条 `(渠道, 类, 文件, 行号, 该行必须包含的子串)`；
- 该行**确实包含**那个子串（即"我声称的证据真在这一行"）；
- 该行号**确实被这条 evidence/note 引用过**（`文件:行号` 或覆盖它的 `文件:A-B` 区间）。

⚠ 覆盖面是**名单制**、不是全库：全库要先把"每条 evidence 引用了哪几处代码"结构化（另一件事）。
新增/修改 evidence 时，把条目加进 `CHECKS` 即可——**加条目比事后人核便宜**。

用法：`.venv\\Scripts\\python.exe scripts\\verify-answer-citations.py`（退出码 0 = 全过）
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ANSWERS = ROOT / "src" / "core" / "update" / "channel_answers.json"

#: (渠道 id, 类, 文件相对路径, 行号, 该行必须包含的子串)
CHECKS: list[tuple[str, str, str, int, str]] = [
    # R6c-7 改动过的那些引用（ndls 两处、hbba/dbba 各两处）
    ("ch:ndls", "发布", "src/core/update/channels/ndls.py", 256, "a101"),
    ("ch:ndls", "发布", "src/core/update/channels/ndls.py", 268, "issue_date"),
    ("ch:ndls", "发布", "src/core/update/channels/ndls.py", 242, "published_date=pub"),
    ("ch:ndls", "废止", "src/core/update/channels/ndls.py", 258, "a206"),
    ("ch:ndls", "废止", "src/core/update/channels/ndls.py", 278, "effective_date=impl"),
    ("ch:ndls", "废止", "src/core/update/channels/ndls.py", 281, "withdrawn_date=wd"),
    ("ch:hbba", "发布", "src/core/update/channels/hbba.py", 118, "withdrawn_date"),
    ("ch:hbba", "发布", "src/core/update/channels/hbba.py", 133, "published_date"),
    ("ch:hbba", "发布", "src/core/update/channels/hbba.py", 136, "raw="),
    ("ch:hbba", "废止", "src/core/update/channels/hbba.py", 66, "map_state_text"),
    ("ch:hbba", "废止", "src/core/update/channels/hbba.py", 118, "withdrawn_date"),
    ("ch:hbba", "废止", "src/core/update/channels/hbba.py", 128, "effective_date="),
    ("ch:dbba", "发布", "src/core/update/channels/hbba.py", 118, "withdrawn_date"),
    ("ch:dbba", "发布", "src/core/update/channels/hbba.py", 133, "published_date"),
    ("ch:dbba", "废止", "src/core/update/channels/hbba.py", 66, "map_state_text"),
    ("ch:dbba", "废止", "src/core/update/channels/hbba.py", 118, "withdrawn_date"),
]


def _cited(text: str, fname: str, line_no: int) -> bool:
    """该 evidence/note 是否引用过这个行号：`file:N` 或覆盖 N 的 `file:A-B`。"""
    if f"{fname}:{line_no}" in text:
        return True
    for m in re.finditer(re.escape(fname) + r":(\d+)-(\d+)", text):
        if int(m.group(1)) <= line_no <= int(m.group(2)):
            return True
    return False


def main() -> int:
    table = json.loads(ANSWERS.read_text(encoding="utf-8"))["channels"]
    fails = warns = 0
    for cid, cls, path, line_no, needle in CHECKS:
        det = (table.get(cid) or {}).get("answers_detail", {}).get(cls) or {}
        text = f"{det.get('evidence', '')} {det.get('note', '')}"
        fname = pathlib.Path(path).name
        if not _cited(text, fname, line_no):
            warns += 1
            print(f"[WARN] {cid} {cls}: evidence/note 没引用 {fname}:{line_no}"
                  f"（引用清单过期？）")
        lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
        actual = lines[line_no - 1] if 0 < line_no <= len(lines) else "<行号越界>"
        if needle in actual:
            print(f"[ok]   {fname}:{line_no} ⊃ {needle!r}")
        else:
            fails += 1
            print(f"[FAIL] {fname}:{line_no} 应含 {needle!r}\n       实际：{actual.strip()}")
    print(f"\n== 能力表行号引用 {'PASS' if fails == 0 else f'FAIL（{fails} 条）'}"
          f"{'' if warns == 0 else f'（另有 {warns} 条 WARN）'} ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
