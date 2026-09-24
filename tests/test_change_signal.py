"""**变更信号**（§10.195 目标"实时获取发布/更新/修改/废止"）：判定规则 + 落库。

⚠ **落库的标记是确定性规则算的，不是模型输出**（官方明示 typed output 保证接口、不保证为真；
本项目的规矩是"能拿同一条规则复算出来的事实才落库"）。Jev 只在 `jev_ingest` 做范围分档。
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from src.core.update import web_ingest

#: 2026-09-24 真机抓到的 8 条变更信号（标题逐字来自应急管理部公告列表）
SIGNAL_TITLES = [
    ("关于公开征求《危险化学品经营许可证管理办法(修订征求意见稿)》意见的通知", "draft"),
    ("应急管理部关于废止《重特大自然灾害调查评估暂行办法》的通知", "repealed"),
    ("中华人民共和国应急管理部公告（2025年第10号）：废止3项行业标准", "repealed"),
    ("应急管理部关于学习宣传贯彻新修订的《中华人民共和国突发事件应对法》的通知", "revised"),
    # ⚠ 2026-09-24 人眼审**改判**：这一条原先期望 revised，**判错了**——
    #   「标准**制修订**统筹协调工作细则」是**被引文件自己的标题词**（讲标准怎么制定与修订
    #   的统筹办法），并**没有任何标准被修订**。已移到 BARE_VERB_FALSE_POSITIVES。
    ("应急管理部关于废止原国家安全监管总局印发的《关于在高危行业推进安全生产责任保险的指导意见》的通知",
     "repealed"),
    ("应急管理部办公厅关于修改《危险化学品目录（2015版）实施指南（试行）》涉及柴油部分内容的通知",
     "revised"),
    ("应急管理部关于贯彻实施新修改《中华人民共和国消防法》全面实行公众聚集场所投入使用营业前消防安全检查告知承诺管理的通知",
     "revised"),
]
#: 标题里**没写**变化的 ⇒ 不标（宁漏不猜）
NO_SIGNAL = [
    "中华人民共和国应急管理部令（第23号）社会消防技术服务管理规定",
    "商务部等5部门关于调整《向特定国家（地区）出口易制毒化学品管理目录》的公告",
    "应急管理部关于印发《特种作业目录》的通知",
]


@pytest.mark.parametrize("title,kind", SIGNAL_TITLES)
def test_change_signal_detected(title: str, kind: str):
    assert web_ingest.classify_change_signal(title) == kind, title


@pytest.mark.parametrize("title", NO_SIGNAL)
def test_no_signal_when_title_does_not_say_it(title: str):
    """标题没写变化 ⇒ `None`（**宁漏不猜**：标了没写的＝误导人）。"""
    assert web_ingest.classify_change_signal(title) is None, title


#: 2026-09-24 **真机人眼审**从 55 条回填里抓出的 5 条误标，**同源**：
#: 只看到动词（发布/批准/修订），**没看到对象**（标准/规范/目录/条例…）。
#: ⚠ 脚本"库里的值 == 规则算的值"**证明不了规则没判错**——这几条复算全对、规则本身是错的。
BARE_VERB_FALSE_POSITIVES = [
    # 「制修订」是**被引文件自己的标题词**（讲标准怎么制定与修订的统筹细则），没有任何标准被修订
    "应急管理部 市场监管总局关于印发《安全生产国家标准制修订统筹协调工作细则》的通知",
    # 发布/批准的是**设备、预警、实验室**，不是法规标准
    "国家广播电视总局 国家乡村振兴局 公安部 财政部 应急管理部 关于加快推动农村应急广播主动发布终端建设的通知",
    "国家森林草原防灭火指挥部办公室关于发布高森林火险橙色预警的通知",
    "应急管理部关于批准建设应急管理部重点实验室的通知",
    "应急管理部办公厅关于批准创建“医学救援关键技术装备”等9个应急管理部重点实验室的通知",
]


@pytest.mark.parametrize("title", BARE_VERB_FALSE_POSITIVES)
def test_bare_verb_without_standard_object_is_not_a_signal(title: str):
    """**只有动词、没有“标准/规范/目录/条例”这类对象 ⇒ 不是法规标准的变化**。

    这条是“发布终端建设”“发布预警”“批准建设实验室”“印发…标准制修订…细则”被误标的那一族。
    """
    assert web_ingest.classify_change_signal(title) is None, title


def test_real_signals_survive_the_object_requirement():
    """加了“必须有对象词”这道闸之后，**真正的信号一条都不能被误杀**。"""
    for title, want in [
        ("中华人民共和国应急管理部公告（2023年第2号）：批准12项安全生产行业标准", "issued"),
        ("中华人民共和国应急管理部公告（2024年第5号）：以“KA”代号重新编号发布36项行业标准", "issued"),
        ("中华人民共和国应急管理部等10部门公告（2026年第3号）：将3-氯丙炔等5种化学品纳入《危险化学品目录（2015版）》", "issued"),
        ("人力资源社会保障部办公厅 应急管理部办公厅关于颁布消防设施操作员国家职业技能标准的通知", "issued"),
        ("危化品安全管理条例(2011修订)", "revised"),
        ("应急管理部办公厅关于修改《危险化学品目录（2015版）实施指南（试行）》涉及柴油部分内容的通知", "revised"),
        ("应急管理部关于贯彻实施新修改《中华人民共和国消防法》全面实行公众聚集场所投入使用营业前消防安全检查告知承诺管理的通知", "revised"),
    ]:
        assert web_ingest.classify_change_signal(title) == want, title


def test_signal_priority_draft_beats_repealed():
    """一条标题可能同时命中多个（「修订征求意见稿」含"修订"、"征求"）⇒ 取优先级最高的。"""
    assert web_ingest.classify_change_signal(
        "关于公开征求《X办法（修订征求意见稿）》意见的通知") == "draft"
    # 废止优先于修订：「关于废止并修订部分条款的决定」
    assert web_ingest.classify_change_signal("关于废止并修订部分条款的决定") == "repealed"


def test_change_signal_orthogonal_to_legal_status():
    """**正交**：文件自己现行有效（effective），同时是"某法规被废止"的证据（repealed）。"""
    assert web_ingest.classify_status("应急管理部关于废止《X暂行办法》的通知") == "withdrawn"
    assert web_ingest.classify_status("应急管理部办公厅关于修改《X指南》的通知") == "effective"
    assert web_ingest.classify_change_signal("应急管理部办公厅关于修改《X指南》的通知") == "revised"


def test_change_signal_column_exists_and_is_written(db):
    """落库：`doc_meta.change_signal` 列在，且 `ingest_law_text(change_signal=...)` 会写进去。"""
    from src.core.storage.sqlite_db import get_db_connection
    from src.core.ingestion.law_text import ingest_law_text

    cols = {r[1] for r in get_db_connection().execute("PRAGMA table_info(doc_meta)")}
    assert "change_signal" in cols, "增量列没建（真库 6797 行，靠 ALTER 补）"

    url = "https://example.invalid/sig-test.shtml"
    text = "关于废止《某管理办法》的通知\n\n第一条 兹废止《某管理办法》（2020 年第 1 号发布）。"
    out = ingest_law_text(text, "废止通知·测试", "废止通知·测试",
                          source_url=url, change_signal="repealed",
                          fallback_single_clause=True)
    assert out.get("status") not in ("error", "duplicate", "standard_exists"), out
    row = get_db_connection().execute(
        "SELECT change_signal FROM doc_meta WHERE source_url=?", (url,)).fetchone()
    assert row is not None and row[0] == "repealed", row


def test_insert_document_writes_optional_columns_it_lists(db):
    """**防回潮（窄口径）**：`insert_document` 的 INSERT 清单里列出来的可空列，得真能写进去。

    ⚠ 2026-09-24 实测踩到：`change_signal` 传进 `ingest_law_text`、列也建了，
    但 `clause_repo.insert_document` 的 INSERT 清单里没有它 ⇒ **落库 NULL 而全程不报错**。
    ⚠ 第一版把这条写成"表里每列都必须在清单里" ⇒ **问错了问题**：`catalog_hidden`/`ccs_*`/
    `created_at` 这些由**别处**补写（分类回流、隐藏位、时间戳），本就不归 `insert_document`。
    ⇒ 窄口径：只验"清单里有的可空列真写得进去"。
    """
    from src.core.storage.sqlite_db import get_db_connection
    from src.core.storage.clause_repo import insert_document

    src = Path(inspect.getsourcefile(insert_document) or "")
    body = src.read_text(encoding="utf-8")
    m = re.search(r"INSERT INTO doc_meta\s*\((.*?)\)\s*VALUES", body, re.S)
    assert m, "没在 insert_document 里找到 INSERT INTO doc_meta（源码形状变了？）"
    listed = [c.strip() for c in m.group(1).replace("\n", " ").split(",") if c.strip()]
    assert "change_signal" in listed, \
        "change_signal 不在 insert_document 清单里 ⇒ 传了也会被静默丢弃（今天踩过）"

    # 清单里每一列都得真在表里（少写/多写都会当场 SQL 错）
    table_cols = {r[1] for r in get_db_connection().execute("PRAGMA table_info(doc_meta)")}
    assert set(listed) <= table_cols, f"清单里有表里没有的列：{sorted(set(listed) - table_cols)}"


def test_change_signal_not_written_when_caller_omits(db):
    """不给 `change_signal` ⇒ **不写这列**（既有调用方行为一字不变，`__default__` 哨兵）。"""
    from src.core.storage.sqlite_db import get_db_connection
    from src.core.ingestion.law_text import ingest_law_text

    url = "https://example.invalid/nosig-test.shtml"
    out = ingest_law_text("第一条 测试正文内容足够长以便切分。", "无信号通知·测试", "无信号通知·测试",
                          source_url=url, fallback_single_clause=True)
    assert out.get("status") not in ("error", "duplicate", "standard_exists"), out
    row = get_db_connection().execute(
        "SELECT change_signal FROM doc_meta WHERE source_url=?", (url,)).fetchone()
    assert row is not None, "文档没入库"
    assert row[0] is None, f"不给就不该写（哨兵失效）：{row[0]!r}"


def test_real_db_backfilled_values_match_rule():
    """**真库回填后逐条复算**（只读；真库不在 ⇒ 跳过，不造假绿）。

    ⚠ 真库写入**没有门禁保护**（门禁跑的是 `%TEMP%` 临时库）⇒ "脚本报告写了 55 行"
    不算证据，证据是"**库里的值 == 规则复算值**，且没多没少、没碰计划外的行"。
    2026-09-24 实测：先写 55 行、再逐条比对 ⇒ 0 非法 / 0 不符 / 0 该标未标。
    ⚠ **然后人眼审又抓出 5 条规则本身判错的**（见 `BARE_VERB_FALSE_POSITIVES`）⇒ 已更正，
    带信号 55 → **50**。所以行数要与**更正记录**对账，不是与原始回填计划对。
    ⚠ 这是**脚本复算的固有盲区**："库里的值 == 规则算的值"**证明不了规则没判错**。
    """
    from pathlib import Path
    real = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
    plan_file = Path(r"D:\AI\work space\zcode\var\tmp\change-signal-backfill-plan.json")
    corr_file = Path(r"D:\AI\work space\zcode\var\tmp\change-signal-correct.json")
    if not real.exists() or not plan_file.exists():
        # ⚠ 显式 skip，**不是**静默 return（独立复核 2026-09-24 指出：`return` 让判据恒真，
        #   换台机器就"通过"但什么都没验；`skip` 会进 skip 清单被门禁盯住）。
        import pytest
        pytest.skip(f"真库或回填计划不在（{real} / {plan_file}）——回填没做过或换机器")
    import json
    import sqlite3
    plan = json.loads(plan_file.read_text(encoding="utf-8"))["plan"]
    corrected = set()
    if corr_file.exists():
        corrected = {r["doc_id"] for r in
                     json.loads(corr_file.read_text(encoding="utf-8"))["rows"]}
    expect_n = len(plan) - len(corrected)
    ro = sqlite3.connect("file:" + str(real).replace("\\", "/") + "?mode=ro", uri=True)
    try:
        got = {d: s for d, _n, s in ro.execute(
            "SELECT doc_id, standard_no, change_signal FROM doc_meta")}
    finally:
        ro.close()
    wrong = [(p["standard_no"][:40], p["new"], got.get(p["doc_id"])) for p in plan
             if p["doc_id"] not in corrected and got.get(p["doc_id"]) != p["new"]]
    assert not wrong, f"真库里这些行的信号与规则不符：{wrong[:5]}"
    in_plan = {p["doc_id"] for p in plan}
    n_set = sum(1 for d, v in got.items() if v is not None)
    assert n_set == expect_n, \
        f"带信号行数 {n_set} ≠ 预期 {expect_n}（{len(plan)} 计划 − {len(corrected)} 更正）"
    stray = [d for d, v in got.items() if v is not None and d not in in_plan]
    assert not stray, f"计划外的行被写了信号：{stray[:5]}"
    not_cleared = [d for d in corrected if got.get(d) is not None]
    assert not not_cleared, f"已判定为误标的行还在库里带信号：{not_cleared[:5]}"
