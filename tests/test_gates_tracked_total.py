# -*- coding: utf-8 -*-
"""棘轮口径助手（`scripts/gates-tracked-total.py`）的判据：**只减掉未跟踪用例**。

## 这一组在守什么

棘轮基线原先记"实测总数"，而实测总数可能含**未跟踪文件**里的用例
（本仓实测：`tests/test_jev_cn_baseline.py` 不归 git 管、却贡献 5 条）⇒
一被删就**假红**；而**手工把基线调低**去躲它，又会造出"可以静默删用例"的**余量**
（复核量化：余量 0 → 6）。修法是把这个口径**搬进代码**：比较与记账两侧都只统计 tracked。

## 判据（三条，互相对照）

1. **正向**：临时 git 仓库里一个 tracked 文件 + 一个 untracked 文件 ⇒ 只减掉 untracked 的。
2. **反向**（防空闸门）：**不扣减**时 untracked 的那些会被算进去 ⇒ 两个数必须不同。
3. **保守**：文件名认不出来（模块不存在）⇒ **不扣**、并计入 `unmapped`（宁可少扣，不可多扣）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import importlib.util                                                   # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "gates_tracked_total", REPO / "scripts" / "gates-tracked-total.py")
assert _spec and _spec.loader, "加载脚本失败"
gtt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gtt)


def _junit(path: Path, entries: list[tuple[str, str]]) -> Path:
    """写一份最小 junit：`entries` = [(classname, name), …]。"""
    cases = "".join(f'<testcase classname="{c}" name="{n}"/>' for c, n in entries)
    path.write_text(f'<?xml version="1.0" encoding="utf-8"?><testsuite>{cases}</testsuite>',
                    encoding="utf-8")
    return path


def _git_repo(tmp_path: Path) -> Path:
    """临时 git 仓库（**受控**：tracked / untracked 各一个测试文件）。"""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests" / "test_tracked.py").write_text("def test_a():\n    pass\n",
                                                        encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tests/test_tracked.py"],
                   check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], check=True)
    # 未跟踪的那份：建了但**不 add**
    (tmp_path / "tests" / "test_untracked.py").write_text("def test_b():\n    pass\n",
                                                          encoding="utf-8")
    return tmp_path


def test_only_untracked_tests_are_excluded(tmp_path):
    """**正向**：tracked 的照算、untracked 的那 2 条被扣掉。"""
    repo = _git_repo(tmp_path)
    j = _junit(tmp_path / "j.xml", [
        ("tests.test_tracked", "test_a"),
        ("tests.test_untracked", "test_b"),
        ("tests.test_untracked", "test_c"),
    ])
    info = gtt.compute(j, repo)
    assert info["collected"] == 3
    assert info["untracked"] == 2, info
    assert info["tracked_total"] == 1, info
    assert info["untracked_files"] == {"tests/test_untracked.py": 2}, info


def test_the_reverse_the_naive_total_would_count_them(tmp_path):
    """**反向**：不扣减的口径（= 旧行为）会把 untracked 的算进去 ⇒ 两个数必须不同。

    没有这一条，上面那条可能只是"数值恰好对上"（空闸门）。
    """
    repo = _git_repo(tmp_path)
    j = _junit(tmp_path / "j.xml", [
        ("tests.test_tracked", "test_a"),
        ("tests.test_untracked", "test_b"),
    ])
    info = gtt.compute(j, repo)
    naive = info["collected"]                       # 旧口径：实测总数
    fixed = info["tracked_total"]                   # 新口径
    assert naive == 2 and fixed == 1
    assert naive != fixed, "两种口径给出同一个数 ⇒ 这条判据证明不了任何事"


def test_unmappable_names_are_not_subtracted(tmp_path):
    """**保守**：认不出文件的条目**不许扣**（宁可少扣，不可多扣）。"""
    repo = _git_repo(tmp_path)
    j = _junit(tmp_path / "j.xml", [
        ("tests.test_tracked", "test_a"),
        ("tests.test_no_such_module_zzz", "test_ghost"),
        ("::tests.test_also_missing", ""),          # 收集期跳过的形态
    ])
    info = gtt.compute(j, repo)
    assert info["collected"] == 3
    assert info["unmapped"] == 2, info
    assert info["untracked"] == 0, info
    assert info["tracked_total"] == 3, info


def test_class_based_and_parametrised_names_map_to_the_file(tmp_path):
    """类里的用例（junit 把类名塞进 classname）与参数化（`name[param]`）都要认得出。"""
    repo = _git_repo(tmp_path)
    j = _junit(tmp_path / "j.xml", [
        ("tests.test_untracked.TestK", "test_d[x]"),
    ])
    info = gtt.compute(j, repo)
    assert info["untracked"] == 1, info
    assert info["tracked_total"] == 0, info
