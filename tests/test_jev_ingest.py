"""公告入库"Jev 管清"回归用例（2026-09-24 真机实测分数回放，零联网零花费）。

样本与 `tests/test_jev_guard.py` 同源：18 条有标准答案的中文公告标题。
⚠ 本文件钉的是**我们的门与归并逻辑**（0.90/0.70 两道 + "不够确信就留"），
不是 Jev 的准确率——后者靠人工真机复核。
"""
from __future__ import annotations

import pytest

from src.core.update import jev_ingest
from src.core.update.web_ingest import classify_scope
from src.core.llm import jev_client

#: (标题, 真值 clear/review/keep, Jev choice, 真机 confidence)
#: ⚠ **真值是三档不是两档**：`review`（0.70≤conf<0.90）= 灰区、**交人看不动作**，
#:   效果上等价于"留"，但**不是** `keep`（它的对外含义不同：待人工确认清单里会出现）。
#:   第一版我把 conf=0.87 那条真值写成 keep，判据就假红——**分清判据错还是读数错**（七条清单第 1 条）。
SAMPLES: list[tuple[str, str, str, float]] = [
    # 标题, 真值, Jev choice, 真机 confidence
    ("应急管理部关于给予刘名芳等12名同志奖励的决定", "clear", "admin", 1.00),
    ("应急管理部关于给予刘德宝等78名同志和国家危险化学品应急救援中原油田队一大队等5个集体奖励的决定",
     "clear", "admin", 1.00),
    ("应急管理部2026年第二季度政府网站检查情况通报", "clear", "admin", 1.00),
    ("应急管理部2025年第四季度政府网站检查情况通报", "clear", "admin", 1.00),
    ("应急管理部 司法部 人力资源社会保障部 中华全国总工会 全国普法办关于开展第七届应急管理普法知识竞赛活动的通知",
     "clear", "admin", 1.00),
    ("应急管理部 全国总工会 共青团中央 河南省人民政府关于举办第四届全国危险化学品救援技能竞赛的通知",
     "clear", "admin", 1.00),
    ("国务院安委会办公室关于安全生产领域部分弄虚作假典型案例的通报", "clear", "admin", 0.99),
    ("国家防汛抗旱总指挥部关于防汛抗旱责任人的通报", "clear", "admin", 0.99),
    ("应急管理部关于印发《全国应急管理系统法治宣传教育第八个五年规划（2021—2025年）》的通知",
     "clear", "admin", 0.99),
    ("应急管理部办公厅关于开展安全生产培训“走过场”专项整治工作的通知", "review", "admin", 0.87),
    # 规则本该留的（征求意见稿/办法/目录）——本层压根不该收到它们，但 Jev 也应判 keep
    ("关于公开征求《危险化学品经营许可证管理办法(修订征求意见稿)》意见的通知",
     "keep", "change_signal", 0.73),
    ("应急管理部 住房城乡建设部 国家矿山安监局关于印发《特种作业目录》的通知",
     "keep", "normative", 0.85),
    ("应急管理部办公厅关于印发《淘汰落后危险化学品安全生产工艺技术设备目录（第二批）》的通知",
     "keep", "normative", 0.64),
]
#: 真机上实测的"变更信号"分数（change noul），按标题回放
CHANGE_NOUL: dict[str, float] = {
    "应急管理部关于给予刘名芳等12名同志奖励的决定": 0.02,
    "应急管理部关于给予刘德宝等78名同志和国家危险化学品应急救援中原油田队一大队等5个集体奖励的决定": 0.02,
    "应急管理部2026年第二季度政府网站检查情况通报": 0.02,
    "应急管理部2025年第四季度政府网站检查情况通报": 0.02,
    "应急管理部 司法部 人力资源社会保障部 中华全国总工会 全国普法办关于开展第七届应急管理普法知识竞赛活动的通知": 0.02,
    "应急管理部 全国总工会 共青团中央 河南省人民政府关于举办第四届全国危险化学品救援技能竞赛的通知": 0.02,
    "国务院安委会办公室关于安全生产领域部分弄虚作假典型案例的通报": 0.02,
    "国家防汛抗旱总指挥部关于防汛抗旱责任人的通报": 0.02,
    "应急管理部关于印发《全国应急管理系统法治宣传教育第八个五年规划（2021—2025年）》的通知": 0.03,
    "应急管理部办公厅关于开展安全生产培训“走过场”专项整治工作的通知": 0.03,
    "关于公开征求《危险化学品经营许可证管理办法(修订征求意见稿)》意见的通知": 0.92,
    "应急管理部 住房城乡建设部 国家矿山安监局关于印发《特种作业目录》的通知": 0.07,
    "应急管理部办公厅关于印发《淘汰落后危险化学品安全生产工艺技术设备目录（第二批）》的通知": 0.08,
}


@pytest.fixture()
def fake_jev(monkeypatch):
    def _fake(state, questions, **kw):
        title = state if isinstance(state, str) else str(state)
        for t, _truth, choice, conf in SAMPLES:
            if t == title:
                return {"answers": {
                    "kind": {"type": "choice", "choice": choice, "confidence": conf,
                             "probabilities": {choice: conf, "other": round(1 - conf, 2)}},
                    "change": {"type": "noul", "noul": CHANGE_NOUL[title]},
                }, "model": "jev-1.13.0"}
        raise AssertionError(f"样本里没有这条：{title}")
    monkeypatch.setattr(jev_client, "system_one", _fake)
    jev_client.reset_breaker_for_tests()
    return _fake


def test_ingest_judges_all_samples(fake_jev):
    """13 条逐条判对：clear 只给"够确信是行政事务"的，灰区与规范一律 keep。"""
    wrong = []
    for title, truth, _choice, _conf in SAMPLES:
        out = jev_ingest.judge_one(title)
        got = (out or {}).get("verdict")
        if got != truth:
            wrong.append((title[:40], truth, got))
    assert not wrong, f"判错 {len(wrong)} 条：{wrong}"


def test_ingest_never_clears_change_signal(fake_jev, monkeypatch):
    """变更信号**永远不清**——哪怕 choice 判成 admin、confidence 也很高。"""
    t = "应急管理部办公厅关于印发《淘汰落后危险化学品安全生产工艺技术设备目录（第二批）》的通知"

    def _admin_but_change(state, questions, **kw):
        return {"answers": {
            "kind": {"type": "choice", "choice": "admin", "confidence": 0.99,
                     "probabilities": {"admin": 0.99}},
            "change": {"type": "noul", "noul": 0.95},
        }, "model": "jev-1.13.0"}
    monkeypatch.setattr(jev_client, "system_one", _admin_but_change)
    assert jev_ingest.judge_one(t)["verdict"] == jev_ingest.KEEP


def test_ingest_low_confidence_admin_stays_keep(fake_jev, monkeypatch):
    """**不够确信 ⇒ 留着**（官方分类范式：报更粗的标签，而不是丢掉）。"""
    t = "应急管理部办公厅关于开展安全生产培训“走过场”专项整治工作的通知"
    assert jev_ingest.judge_one(t)["verdict"] == jev_ingest.REVIEW   # 0.87 落灰区
    # 再压到 0.5 ⇒ 仍 keep（不是 clear，也不是把"没把握"当 clear）
    monkeypatch.setattr(jev_client, "system_one", lambda *a, **k: {"answers": {
        "kind": {"type": "choice", "choice": "admin", "confidence": 0.5,
                 "probabilities": {"admin": 0.5}},
        "change": {"type": "noul", "noul": 0.01}}, "model": "jev-1.13.0"})
    assert jev_ingest.judge_one(t)["verdict"] == jev_ingest.KEEP


def test_ingest_degrades_to_none_when_unavailable(monkeypatch):
    """Jev 挂 ⇒ `None`（调用方按规则原样处理，绝不因为外部服务挂了就误清库）。"""
    def _boom(*_a, **_k):
        raise jev_client.JevUnavailable("测试：不可用")
    monkeypatch.setattr(jev_client, "system_one", _boom)
    jev_client.reset_breaker_for_tests()
    assert jev_ingest.judge_one("应急管理部2026年第二季度政府网站检查情况通报") is None


def test_ingest_rejects_malformed(monkeypatch):
    """响应不合契约 ⇒ None（不猜）。"""
    monkeypatch.setattr(jev_client, "system_one", lambda *a, **k: {
        "answers": {"kind": {"type": "choice", "choice": "admin"},
                    "change": {"type": "noul", "noul": 0.1}}, "model": "x"})
    assert jev_ingest.judge_one("任意标题") is None
    monkeypatch.setattr(jev_client, "system_one", lambda *a, **k: {
        "answers": {"kind": {"type": "choice", "choice": "外星人", "confidence": 0.9,
                             "probabilities": {}},
                    "change": {"type": "noul", "noul": 0.1}}, "model": "x"})
    assert jev_ingest.judge_one("任意标题") is None


def test_ingest_asks_both_questions_in_one_call(fake_jev):
    """**一次调用问两题**（官方 parallel_questions：打包更便宜更快）。"""
    seen = {}

    def _capture(state, questions, **kw):
        seen["q"] = sorted(questions)
        seen["service"] = kw.get("service")
        for t, _truth, choice, conf in SAMPLES:
            if t == state:
                return {"answers": {
                    "kind": {"type": "choice", "choice": choice, "confidence": conf,
                             "probabilities": {choice: conf}},
                    "change": {"type": "noul", "noul": CHANGE_NOUL[state]},
                }, "model": "jev-1.13.0"}
        raise AssertionError(state)
    import src.core.llm.jev_client as jc
    original = jc.system_one
    jc.system_one = _capture
    try:
        jev_ingest.judge_one("应急管理部2026年第二季度政府网站检查情况通报")
    finally:
        jc.system_one = original
    assert seen["q"] == ["change", "kind"], seen
    assert seen["service"] == "jev-ingest", seen


def test_triage_pending_is_read_only_and_buckets(db, monkeypatch):
    """`triage_pending`：只读分档——清/灰/留三个桶 + 每条带判据（choice/confidence）。

    ⚠ **不删库**：这条端点只提供证据，删除是业主的决定（他的口径是判据，不是授权我下手）。
    ⚠ 样本必须是**规则判不收**的那类（`classify_scope != normative`）——因为
      `triage_pending` 只处理"规则说别收、但要不要真清"那批。第一版拿"规则本就放行"的
      样本去试 ⇒ total=0（它们压根不进这个函数），属**用例取样错**，不是实现错。
    """
    from src.core.storage.sqlite_db import get_db_connection
    from src.core.update import web_ingest

    # 规则判不收、但真机确认是噪声的家族。
    # ⚠ 取样**由规则自己筛**（`classify_scope`），不手挑——手挑会挑到"规则本就放行"的
    #   那类（第一版 5 条里 4 条被放行 ⇒ total=1，红得莫名其妙）。规则是权威口径，
    #   用例与它对齐，而不是另建一套"我以为的名单"。
    TRIAGE_ROWS = [
        "应急管理部2025年度部门决算",
        "应急管理部2024年第四季度政府网站检查情况通报",
        "应急管理部关于给予王金海等10名同志奖励的决定",
        "关于征集消防标准化技术委员会委员人选的通知",
        "应急管理部办公厅关于开展防汛抢险急需技术装备揭榜攻关的通知",
        "应急管理部本级2026年度部门预算",
    ]
    conn = get_db_connection()
    conn.execute("DELETE FROM announcement_observed")
    conn.commit()
    # ⚠ 取样里**故意包含规则会漏放的那几条**（检查通报/奖励决定/征集选聘/揭榜攻关）：
    #   它们含"决定/通知/办法"等强线索词 ⇒ `classify_scope` 判 normative（规则放行）。
    #   但 2026-09-24 真机确认它们是行政事务 ⇒ **"规则会漏放"是已证事实**，不是假设。
    #   本层（Triage）按设计只处理"规则判不收"的，故 `triage_pending` 只会看到其中 2 条
    #   ——**这正是"规则管留、Jev 管清"分工的已知缺口**，本轮只登记、不扩范围。
    for i, title in enumerate(TRIAGE_ROWS):
        conn.execute(
            "INSERT INTO announcement_observed(observed_id, source_id, source_name, title, url,"
            " url_hash, published_date) VALUES(?,?,?,?,?,?,?)",
            # ⚠ 用**序号**而不是 hash()：hash() 对 str 默认按进程随机加盐（PYTHONHASHSEED），
            #   同一条标题在两个进程会得到不同 id ⇒ url_hash 唯一键行为不可复现。
            # ⚠ 用本用例专属 source_id：唯一键是 (source_id, url_hash)，同库其它用例留下的
            #   `src_t` 行会撞（实测 UNIQUE constraint failed）——会话级共享库，隔离靠 source_id。
            (f"ann_tg{i:03d}", "src_triage", "测试源", title,
             f"https://exp.example.com/tg{i:03d}.shtml", f"tg{i:03d}", "2026-09-24"))
    conn.commit()
    before = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    rule_passed = [t for t in TRIAGE_ROWS if web_ingest.classify_scope(t) == "normative"]
    rule_rejected = [t for t in TRIAGE_ROWS if web_ingest.classify_scope(t) != "normative"]
    assert rule_rejected, "取样里至少要有一条是规则判不收的（本层只处理那批）"

    def _stub(title, **kw):
        return {"verdict": jev_ingest.CLEAR, "choice": "admin", "confidence": 0.97,
                "change": 0.02}
    monkeypatch.setattr("src.core.update.jev_ingest.judge_one", _stub)

    out = web_ingest.triage_pending()
    assert out["total"] == len(rule_rejected), \
        f"本层只处理规则判不收的 {len(rule_rejected)} 条（规则漏放的 {len(rule_passed)} 条不进本层）"
    assert out["counts"] == {"clear": len(rule_rejected), "review": 0, "keep": 0}, out["counts"]
    for it in out["items"]:
        assert it["title"] and it["url"] and it["verdict"] in ("clear", "review", "keep"), it
        assert isinstance(it["confidence"], float), it
    # 只读：doc_meta 一行没动
    assert conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0] == before


def test_rule_passes_through_several_admin_documents(db):
    """**已证事实的登记用例**：规则（强线索词优先）会漏放这几条行政事务。

    这不是"要修的 bug"——是**分工的边界**：`classify_scope` 看到"决定/通知/办法"就放行
    （宁漏清、勿误清），Jev 只在规则判不收的那批里再捞回。要让 Jev 也管这一批，
    是**范围决策**（业主一句话），本轮只把事实钉住、登记为残余。
    """
    passed_through = [
        "应急管理部2024年第四季度政府网站检查情况通报",
        "应急管理部关于给予王金海等10名同志奖励的决定",
        "关于征集消防标准化技术委员会委员人选的通知",
    ]
    for t in passed_through:
        assert classify_scope(t) == "normative", f"规则行为变了（这条开始被规则拦下）：{t}"
