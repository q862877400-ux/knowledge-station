"""测试：地级行政区的**口径**必须只有一套说法（spec 005 T603）。

## 为什么

此前同一个数在三个地方有三个说法：
- `regions.py` 模块文档：**333** 个地级行政区
- `regions.total_cities()` docstring：应为 **333**
- `coverage.known_cities()` docstring：**334**
- `coverage.build_units` 注释：**333**

实际 `total_cities()` 返回 **334**。多出来的是 **济源市**（河南省，**省直辖县级市**，
行政级别上不是地级行政区）。

⇒ 现在统一为：**本表收录数 334**（含济源市）+ **严格意义 333**
（`PREREFECTURE_COUNT_STRICT`），两个数**都有名字**，调用方按需要取。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import regions                                                      # noqa: E402


def test_total_cities_is_334_and_documented_as_such():
    """`total_cities()` 是**本表收录数**，实测 334。"""
    assert regions.total_cities() == 334


def test_strict_prefecture_count_is_333():
    """**严格意义的地级行政区**是 333（不含省直辖县级市济源市）。"""
    assert regions.PREREFECTURE_COUNT_STRICT == 333


def test_the_difference_is_exactly_one_province_direct_city():
    """两个数的差**恰好 1**，且那一个是济源市 —— 把差异钉成可执行的证据。"""
    diff = regions.total_cities() - regions.PREREFECTURE_COUNT_STRICT
    assert diff == 1, f"差应为 1，实际 {diff}"
    all_cities = [c for cs in regions.PROVINCE_CITIES.values() for c in cs]
    # 济源市在表里
    assert "济源市" in all_cities, "济源市应在本表（它的数据真实存在）"
    # 且它是省直辖县级市：河南省直辖，不属任何地级市
    assert "济源市" in regions.PROVINCE_CITIES.get("河南省", []), \
        "济源市应挂在河南省下"


def test_no_module_doc_claims_333_as_the_table_size():
    """**结构判据**：`regions.py` 模块文档不得再把"本表有 333 项"当结论说。

    （允许出现 333 —— 但必须是"严格意义"那个口径，且与 334 一起出现。）
    """
    src = (ROOT / "regions.py").read_text(encoding="utf-8")
    head = src[:src.find('"""', src.find('"""') + 3) + 3]      # 模块 docstring
    if "333" in head:
        assert "334" in head, "文档里提 333 就必须同时提 334（两个口径都要说清）"
        assert "PREREFECTURE_COUNT_STRICT" in head or "严格意义" in head, \
            "提 333 必须说明它是「严格意义」口径"
