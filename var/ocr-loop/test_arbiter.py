r"""`arbiter` 判据单元测试（六字段 schema / 盲评四维 / 完整样本复核）。

跑法：`& .\.venv\Scripts\python.exe -X utf8 var\ocr-loop\test_arbiter.py`
（`var/` 已 gitignore，本文件不进项目仓库，故不走 pytest 门禁；但判据必须可回归。）

为什么要有它：六字段 schema 与「新冒类 >3 / 某类升 >20%」是**阻止半份方案与
带回归的修复进入下一轮**的唯一闸门，闸门自己没测试就会静默失效。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import evolve as E  # noqa: E402

FAIL = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


def valid_proposal(**over) -> dict:
    p = {"verifier": "V3", "root_layer": "检测器逻辑",
         "plan": "改 src/core/text_utils.py 的 strip_formula_leader",
         "expected_effect": "命中 4→1", "risk": "误伤正文省略号",
         "rollback": "git revert", "confidence": 0.7}
    p.update(over)
    return p


print("=== 六字段 schema ===")
check("完整方案有效", E.validate_proposal(valid_proposal())[0], True)
for miss in E.ARBITER_FIELDS:
    p = valid_proposal()
    p[miss] = ""
    check(f"缺 {miss} → 无效", E.validate_proposal(p)[0], False)
check("空字符串字段也算缺",
      E.validate_proposal(valid_proposal(plan="   "))[0], False)
check("非法根因层 → 无效",
      E.validate_proposal(valid_proposal(root_layer="随便写的"))[0], False)
check("置信度越界 → 无效",
      E.validate_proposal(valid_proposal(confidence=1.5))[0], False)
check("置信度非数值 → 无效",
      E.validate_proposal(valid_proposal(confidence="高"))[0], False)
check("置信度 0 合法",
      E.validate_proposal(valid_proposal(confidence=0))[0], True)

print("\n=== 盲评四维（各 1–4 分）===")
d = E.auto_score(valid_proposal(root_layer="识别层限制"))
check("识别层限制 → 根因深度 1", d["root_depth"], 1)
d = E.auto_score(valid_proposal(
    root_layer="检测器逻辑",
    plan="在规范所有者层 src/core/text_utils.py 改 strip_formula_leader"))
check("检测器逻辑 + 点明所有者层 → 4", d["root_depth"], 4)
d = E.auto_score(valid_proposal(root_layer="提示词"))
check("提示词层 → 2", d["root_depth"], 2)
d = E.auto_score(valid_proposal(root_layer="检测器逻辑"))
check("检测器逻辑（未提所有者层）→ 3", d["root_depth"], 3)
d = E.auto_score(valid_proposal(rollback="一次 revert 即可"))
check("可 revert → 回滚成本 1", d["rollback_cost"], 1)
d = E.auto_score(valid_proposal(rollback="改配置回滚"))
check("改配置回滚 → 回滚成本 2", d["rollback_cost"], 2)
for _name, _label, _desc in E.ARBITER_DIMS:
    v = E.auto_score(valid_proposal())[_name]
    check(f"{_name} 在 1–4", 1 <= v <= 4, True)

print("\n=== 完整样本复核判据 ===")
check("持平 → 通过", E.recheck({"a": 5}, {"a": 5})["passed"], True)
check("下降 → 通过", E.recheck({"a": 10}, {"a": 4})["passed"], True)
check("新冒 3 类（不超限）→ 通过",
      E.recheck({}, {"n1": 1, "n2": 1, "n3": 1})["passed"], True)
check("新冒 4 类 → 失败",
      E.recheck({}, {"n1": 1, "n2": 1, "n3": 1, "n4": 1})["passed"], False)
check("某类 3→5 (+67%) → 失败", E.recheck({"a": 3}, {"a": 5})["passed"], False)
check("小分母保护 1→2 不判失败",
      E.recheck({"a": 1}, {"a": 2})["passed"], True)
check("小分母保护 2→3 不判失败",
      E.recheck({"a": 2}, {"a": 3})["passed"], True)
check("抵消除旧类不算新冒",
      E.recheck({"a": 3}, {"a": 1})["new_classes"], [])

print("\n=== 子命令解析（分派器传完整 argv，需剥命令名）===")
import inspect  # noqa: E402
src = inspect.getsource(E.cmd_arbiter)
check("已处理 argv 中的命令名", 'a != "arbiter"' in src, True)

print("\n=== toc-ingested-as-clauses 判据（2026-09-15 新语料校准）===")
import classify as C  # noqa: E402

# 真目录行：**必须带点线**才命中
for txt in ["9.1 包装……13", "6.10 轴承温度的测定……………………………3",
            "9.1 包装...13", "4.2 试验方法 ... 5"]:
    check(f"真目录行命中 {txt[:18]!r}", bool(C._RE_TOC_LINE.search(txt)), True)
# 误报源：无点线的「条目+数字」一律不命中（原分支②的 20 条误报）
for txt in ["3.1 驾驶自动化分级原则\n3", "5.1 检验方法概述\n2",
            "7.2.3 過動激結：阿4.8.90", "4.1 结构型式应符合图1的规定。",
            "22.102 带有燃气管路…应有良好的通风。\n4"]:
    check(f"误报不命中 {txt[:18]!r}", bool(C._RE_TOC_LINE.search(txt)), False)

print("\n=== toc-ingested-as-clauses 第二轮收窄（2026-09-15 批次2 · 500 部新语料）===")
# 背景：第一轮只要求"有点线"，批次 2 的 5 条证据里仍有 4 条误报，误报两型：
#   甲・附录索引（点线后是「表/图 + 字母编号」，编号末位数字冒充页码）
#   乙・正文公式/量值恰好以数字收尾（点线前是单位或公式片段，无描述词）
# 补两个必要条件：① 点线前须有描述字（汉字≥1 或 拉丁≥3 整词）
#                 ② 点线后不得是表/图引用
#
# 甲型（实测原文，GB/T 4549.6-2004）：附录索引整页，非目录混入正文 → 必须不命中
_APPENDIX_INDEX = ("… 表 A.9\n密封橡皮 …… 表 A.1\nN\n内窗板 …… 表 A. 10\n"
                   "内窗折页 …… 表 A.")
check("甲型 附录索引不命中", bool(C._RE_TOC_LINE.search(_APPENDIX_INDEX)), False)
check("甲型 无空格变体不命中", bool(C._RE_TOC_LINE.search("表A.1 …… 23")), False)
# 乙型（实测原文，GB/T 36548-2024）：正文效率计算公式 → 必须不命中
_EFF_FORMULA = ("站额定能量效率，并记录，计算方法见公式（5）：\n"
                "= 1/3 (E rd₁/E rc₁ + E rd₂/…")
check("乙型 正文公式不命中", bool(C._RE_TOC_LINE.search(_EFF_FORMULA)), False)
check("乙型 仅公式尾不命中",
      bool(C._RE_TOC_LINE.search("= 1/3 (E rd₁/E rc₁ + E rd₂/…")), False)
check("反向对照 纯拉丁短词不命中", bool(C._RE_TOC_LINE.search("sample …… 5")), False)
check("反向对照 拉丁<3字不命中", bool(C._RE_TOC_LINE.search("5.1 Test …… 3")), False)
# 真目录行：加严后**必须仍命中**（收窄不能把真信号一起收掉——本轮唯一真缺陷
# GB/T 29798-2013 条款 14.5 正是靠它报出来的）
_TOC_TAIL = ("14.1 概述 …… 100\n14.5 出错信息的扩展性 …… 108\n"
             "14.6 主要出错消息 …… 109\n附录 A（规范性附录） 标记约定 …… 128")
check("真 目录尾部（文字与点线间留空格）命中",
      bool(C._RE_TOC_LINE.search(_TOC_TAIL)), True)
check("真 附录目录行命中", bool(C._RE_TOC_LINE.search("附录 B 试验方法 …… 23")), True)
# 表的目录条目（描述字=「试验条件」，被排除的只是前缀 `表 A.1`）**仍应命中**：
# 排除②只针对「点线**紧后**就是表/图引用」的形态（甲型 `密封橡皮 …… 表 A.1`）。
check("真 表的目录条目命中",
      bool(C._RE_TOC_LINE.search("表 A.1 试验条件 …… 23")), True)

print()
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
