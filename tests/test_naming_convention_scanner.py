# -*- coding: utf-8 -*-
"""`scripts/docs/scan-rename-targets.py`（命名规范机械扫描器）的单测。

**为什么必须测**：这把扫描器是 `docs/naming-convention.md` 的**唯一机械判据**。
它若坏了（判据写反、剪枝写错），表现是"**零违规**"——一个**看起来完全正常的假绿**，
而它保护的正是"改名的成果不随新增文件漂回去"。所以它必须自己先有牙。

**第一版实测踩到的两个真缺陷**（都留痕，且各有一条判据钉住）：
1. **`git ls-files` 默认把非 ASCII 路径转义成八进制**（`"tools/.../\\345\\271\\277..."`）
   ⇒ `Path()` 拿到一个带引号的单段字符串、`parents` 全是垃圾 ⇒
   实测刷出**几千条假违规**。修法 = `-z` + `core.quotepath=false`。
   判据见 `test_non_ascii_paths_are_not_escaped`。
2. **采集数据目录不归命名规范管**（`tools/gov-qa/data/` 的"目录"其实是中文站点名的转义残留，
   由另一个自动化拥有）⇒ 必须剪掉，否则真违规会被几千条噪声淹掉。
   判据见 `test_govqa_data_dir_is_excluded`。

⚠ 本文件**不测** `main()` 的输出格式（那只是 `print`），只测 `scan()` 与 `tracked_files()`。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "docs" / "scan-rename-targets.py"


def _load():
    spec = importlib.util.spec_from_file_location("ks_scan_rename_targets", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


SCANNER = _load()


def test_tracked_files_returns_real_paths_not_escaped():
    """非 ASCII 路径必须是**真路径**，不能是 `\\345\\271\\277` 这种八进制转义。

    这是第一版的真缺陷：转义后 `Path(...).parts` 只剩一段 ⇒ 目录规则全判错。
    """
    files = SCANNER.tracked_files()
    assert files, "git ls-files 应该能拿到文件"
    # 转义形态的特征：路径里出现反斜杠 + 三位八进制
    escaped = [f for f in files if "\\" in f and any(
        f[i:i + 4].startswith("\\") and f[i + 1:i + 4].isdigit() for i in range(len(f) - 3)
    )]
    assert not escaped, f"这些路径仍是八进制转义：{escaped[:3]}"


def test_non_ascii_paths_survive_round_trip():
    """带中文的路径必须能真的**在磁盘上存在**（转义形态必然不存在）。"""
    files = SCANNER.tracked_files()
    cjk = [f for f in files if any("\u4e00" <= ch <= "\u9fff" for ch in f)]
    assert cjk, "本仓有大量中文文件名，应该能取到至少一条"
    missing = [f for f in cjk if not (REPO / f).exists()]
    assert not missing, f"这些中文路径在磁盘上不存在（说明取到的不是真路径）：{missing[:3]}"


def test_govqa_data_dir_is_excluded():
    """采集数据目录必须被剪掉——它由另一个自动化拥有，不归本命名规范管。"""
    files = SCANNER.tracked_files()
    data_files = [f for f in files if f.startswith("tools/gov-qa/data/")]
    assert data_files, "前提：本仓确实有 tools/gov-qa/data/ 下的受控文件"
    assert all(SCANNER.is_under_skipped_dir(f) for f in data_files), \
        "tools/gov-qa/data/ 下的文件必须全部被剪掉"


def test_code_files_are_not_flagged_for_underscores():
    """**R3 的核心**：Python 的 `snake_case.py` 是**正确写法**，不是违规。

    这是 v1 规范被推翻的直接原因（它把 327 个 `.py` 判成违规 ⇒ 改名会断掉每个 import）。
    """
    violations = SCANNER.scan()
    py_violations = [v for v in violations if v["path"].endswith(".py")]
    assert not py_violations, f"代码文件不许被判违规：{py_violations[:3]}"


def test_current_tree_has_zero_violations():
    """当前树必须零违规——这是这条规范**已经被执行过**的机械证据。"""
    violations = SCANNER.scan()
    assert violations == [], f"当前树有违规：{violations[:5]}"


def test_scanner_has_teeth_on_doc_filename():
    """**变异验证（R1 有牙）**：`foo_bar.md` 必须被判违规，`foo-bar.md` 必须放过。

    没有这条，`test_current_tree_has_zero_violations` 在"规则恒返回 None"时**也是绿的**。
    """
    hit = SCANNER.doc_filename_violation("docs/some_doc_name.md")
    assert hit is not None, "带下划线的文档名必须被判违规"
    assert hit["kind"] == "doc_filename_underscore"
    assert hit["suggest"] == "some-doc-name.md", "建议的新名必须真的把下划线换成连字符"

    assert SCANNER.doc_filename_violation("docs/some-doc-name.md") is None, \
        "已经合规的名字不许被判违规"


def test_code_filenames_are_exempt_from_R1():
    """**R1 的边界**：`snake_case.py` **不许**被判违规（这是 v1 被推翻的直接原因）。"""
    assert SCANNER.doc_filename_violation("src/core/some_module.py") is None
    assert SCANNER.doc_filename_violation("plugin/src/some_module.js") is None
    assert SCANNER.doc_filename_violation("src/core/api/routes_channels.py") is None


def test_scanner_has_teeth_on_dir_name():
    """**变异验证（R2 有牙）**：含大写的目录名必须被判违规，全小写必须放过。"""
    hit = SCANNER.dir_name_violation("docs/SomeDir")
    assert hit is not None, "含大写的目录名必须被判违规"
    assert hit["kind"] == "dir_name_not_lowercase"
    assert hit["suggest"] == "somedir"

    assert SCANNER.dir_name_violation("docs/some-dir") is None, "已合规的目录名不许被判违规"
    assert SCANNER.dir_name_violation("docs/archive") is None


def test_skip_dir_check_handles_nested_and_prefix_paths():
    """剪枝判据本身要正确：嵌套目录要剪、正常文档不能误剪。"""
    assert SCANNER.is_under_skipped_dir("tools/gov-qa/data/anything.json")
    assert SCANNER.is_under_skipped_dir("tools/gov-qa/assets-x-y.json")
    assert SCANNER.is_under_skipped_dir("node_modules/pkg/index.js")
    assert SCANNER.is_under_skipped_dir("docs/archive/old-plans/x.md") is False
    assert SCANNER.is_under_skipped_dir("docs/README.md") is False
