"""测试：`coverage-report.py` 的两个入口必须给出**一致的**缺口结论。

## 为什么（spec 005 T106）

实测矛盾（独立复核 Finding 2）：
- `--quiet` 报 `CITY_NONE=0` rc=**0**
- `--missing-cities` 报「零记录 182」rc=**1**

**同一工具、同一数据、两个结论。** 根因是两条路算的**不是同一件事**：
- `CITY_NONE` = 已建单元里状态 none 的个数（`build_units` 只为「有通道或有数据」
  的市建单元 ⇒ 天然接近 0）
- `--missing-cities` = 334 市全名单减「有数据的市」⇒ 真正的缺口

⇒ 修法：抽出 `_missing_cities_detail()` 作**唯一出处**，
`--quiet` 也报 `CITY_MISSING_FROM_334`，且**退出码按它判**。
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# ⚠ **不要硬编码 `../../.venv/Scripts/python.exe`**（独立复核发现 9）：
#   提取树（`git worktree`）里 `.venv` 被 gitignore ⇒ 那个路径不存在
#   ⇒ 用例在**任何提取树/CI 上都会红**（复核实测 FileNotFoundError）。
#   ⇒ 用 `sys.executable`（正在跑本用例的那个解释器，必然是好的）。
PY = sys.executable
SCRIPT = ROOT / "coverage-report.py"


def _load():
    spec = importlib.util.spec_from_file_location("covrep", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_shared_helper_exists_and_is_the_only_source():
    """**结构判据**：`--missing-cities` 分支不得再自己算一遍。

    谁把那段内联逻辑写回去，本用例必红。
    ⚠ 只看**可执行语句**里的 `PROVINCE_CITIES`（排除注释与错误消息字符串）——
    第一版把错误消息里的 `regions.PROVINCE_CITIES` 也算成"内联"，是误报。
    """
    src = SCRIPT.read_text(encoding="utf-8")
    assert "def _missing_cities_detail" in src, "应有唯一出处函数"
    i = src.find("if args.missing_cities:")
    j = src.find("\n    # ----", i)
    branch = src[i:j if j > 0 else len(src)]
    assert "_missing_cities_detail" in branch, "分支应调用唯一出处函数"
    # 逐行看：只看非注释、且不是字符串字面量里的出现
    for ln in branch.splitlines():
        code = ln.split("#", 1)[0]
        if "PROVINCE_CITIES" in code and "human(" not in code and "f\"" not in code:
            raise AssertionError(f"分支里仍有内联遍历：{ln.strip()}")


def _run(*args) -> subprocess.CompletedProcess:
    return subprocess.run([str(PY), str(SCRIPT), *args], cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


#: ⚠ **每个入口只跑一次**，四条用例共用 —— 每次 `coverage-report.py` 要全表扫
#: 398,000 条记录（约 10–20 秒）。第一版让每条用例各自跑，四条共跑 4 次
#: ⇒ 测试套件从 0.5 秒涨到 85 秒，**违反本特性自己的 SC-004**（门禁耗时 ≤ 现状 +60s）。
#: 用模块级缓存把 4 次降为 2 次。
_CACHE: dict = {}


def _quiet_run() -> subprocess.CompletedProcess:
    if "quiet" not in _CACHE:
        _CACHE["quiet"] = _run("--quiet")
    return _CACHE["quiet"]


def _missing_run() -> subprocess.CompletedProcess:
    if "missing" not in _CACHE:
        _CACHE["missing"] = _run("--missing-cities", "--quiet")
    return _CACHE["missing"]


def test_quiet_reports_missing_from_334():
    """`--quiet` 必须打出 `CITY_MISSING_FROM_334` —— 否则读者只看到 `CITY_NONE=0`。"""
    out = (_quiet_run().stdout or "") + (_quiet_run().stderr or "")
    assert "CITY_MISSING_FROM_334=" in out, f"--quiet 应报真实缺口，实际输出：{out[:300]}"


def test_two_entrypoints_agree_on_missing_count():
    """**核心判据**：两个入口报出的缺失数必须**相等**。"""
    oa, ob = _quiet_run().stdout or "", _missing_run().stdout or ""
    ma = re.search(r"CITY_MISSING_FROM_334=(\d+)", oa)
    mb = re.search(r"CITY_MISSING=(\d+)", ob)
    assert ma and mb, f"两入口都要报缺口数：a={oa[:200]} b={ob[:200]}"
    assert ma.group(1) == mb.group(1), \
        f"两个入口结论不一致：--quiet={ma.group(1)} vs --missing-cities={mb.group(1)}"


def test_both_entrypoints_return_the_same_exit_code():
    """**核心判据**：退出码也必须一致（实测原来是 0 vs 1）。"""
    a, b = _quiet_run().returncode, _missing_run().returncode
    assert a == b, f"退出码不一致：--quiet={a} vs --missing-cities={b}"


def test_missing_count_matches_an_independent_recount():
    """**关键补强（独立复核发现 6）**：一致性不等于正确性。

    原版四条用例只锁"两个入口**相等**" —— 复核实测：把 `_missing_cities_detail`
    改成"全部市都算已覆盖"（两边都报 0），**四条全绿**。
    ⇒ 两个入口**一致地报错**，判据照样通过。

    这条**独立重算**缺失数（不调被测实现），再与入口读数比对。
    """
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from regions import PROVINCE_CITIES
    from coverage import count_by_city, count_by_source, build_units, channel_city_map
    from channel import load_channels

    channels = load_channels()
    counts = count_by_source()
    cc = count_by_city(channel_city_map(channels))
    units = build_units(channels, counts, threshold_province=3000,
                        threshold_city=500, city_counts=cc or None)

    # 独立重算：334 名录里「数据口径下零记录」的有几个
    covered = {u.name for u in units
               if u.level == "city" and max(u.total_records, u.data_records) > 0}
    bare = {n.rstrip("市") for n in covered}
    independent = 0
    for _prov, cities in PROVINCE_CITIES.items():
        for c in cities:
            if c not in covered and c.rstrip("市") not in bare:
                independent += 1

    out = _quiet_run().stdout or ""
    m = re.search(r"CITY_MISSING_FROM_334=(\d+)", out)
    assert m, f"应报 CITY_MISSING_FROM_334：{out[:200]}"
    assert int(m.group(1)) == independent, (
        f"入口报 {m.group(1)}，独立重算是 {independent} —— "
        f"两者不一致说明入口算错了（不只是两入口互相一致）")
