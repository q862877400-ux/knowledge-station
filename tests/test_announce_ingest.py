"""批量入库（切片②下半，开发史 §10.193）：已发现的公告 → 知识库**正文**。

业主报的问题原话：「有大量应该入库但是放过了的东西，说明这个抓取逻辑有问题」。
本文件钉住那条收口路径的**每一个判据**：

1. **范围判定**（`classify_scope`）：业主点名的非规范性类别（部门决算/公示/挂牌督办）不入库；
   但**规范性线索优先**——「关于公开征求《XX办法》意见的公示」含"公示"而它**必须**入库
   （那正是他说"应该入库却放过了"的那一类：征求意见稿 → `reference` 档）。
2. **进度计数**（`ingest_summary`）：已发现/已入库/还差多少/跳过多少，都能对上。
3. **批量入库**（`ingest_pending`）：真的写库、逐条如实归因；重复跑不会重复入（判据 =
   `doc_meta.source_url`）；`force=True` 是逃生口；`limit` 封顶；跑完 `pending_left` 说得清。
4. **诚实**：取不到页 ⇒ `failed` + 原因，不静默、不假装成功。

全程离线（transport 注入）；`announcement_observed` 用真表真唯一键。
"""
from __future__ import annotations

import pytest

from src.core.update import web_ingest


@pytest.fixture(autouse=True)
def _clean_observed(db):
    """每个用例只看见自己造的公告。

    ⚠ 会话级临时库是**整个 pytest 会话共用**的（conftest 的 `db` 夹具），
    `announcement_observed` 没有按用例清空 ⇒ 本文件第二条用例起就会数到上一条留下的行
    （实测 `tried=4`、`pending_left=6` 这类"凭空多出来"的数）。这里只清**本文件自己**的痕迹：
    全部 `announcement_observed` 行 + 本文件落的那批 `doc_meta`（`source_url` 前缀
    `https://exp.`），不碰别的文件的数据。
    """
    from src.core.storage.sqlite_db import get_db_connection

    def _wipe() -> None:
        conn = get_db_connection()
        conn.execute("DELETE FROM announcement_observed")
        conn.execute("DELETE FROM doc_meta WHERE source_url LIKE 'https://exp.%'")
        conn.commit()

    _wipe()
    yield
    _wipe()


class _FakeTransport:
    def __init__(self, pages: dict[str, tuple[int, str]]):
        self.pages = pages
        self.calls: list[str] = []

    def fetch(self, url: str, **kw):
        self.calls.append(url)
        return self.pages.get(url, (404, "not found"))


_LAW_DETAIL = """<html><head><title>应急管理部令（第23号）社会消防技术服务管理规定</title></head>
<body><div class="TRS_Editor">
<p>第一条 为了加强社会消防技术服务管理，制定本规定。</p>
<p>第二条 本规定适用于在中华人民共和国境内从事社会消防技术服务活动的机构。</p>
</div></body></html>"""

_DRAFT_DETAIL = """<html><body><div class="TRS_Editor">
<p>为加强危险化学品经营许可证管理，现将《危险化学品经营许可证管理办法（修订征求意见稿）》</p>
<p>全文公布，向社会公开征求意见。</p>
</div></body></html>"""

_PLAIN_DETAIL = """<html><body><div class="TRS_Editor">
<p>根据年度预算安排，现将本部门本年度决算情况公开如下，接受社会监督。</p>
<p>本年度收入合计、支出合计与结转结余情况详见附表，公众可通过本页查询完整数据。</p>
</div></body></html>"""

_ANN_ID = 0
#: ⚠ **本文件专用标题命名空间**（2026-09-24 实测踩到）：会话级临时库是**整个 pytest 会话共用**的，
#: 而"入没入库"的判据里有 `doc_meta.standard_no`（= 公告标题）这一把钥匙 ——
#: `tests/test_web_ingest.py` 用的是**同样的真实标题**（部令第23号 / 危化品经营许可征求意见稿），
#: 谁先跑谁就把这些标题占掉 ⇒ 另一个文件里的同名公告被判成"库里已经有"（实测 pending 从 2 变 0）。
#: 给本文件所有标题加一个只有本文件用的前缀，两边就互不干扰。
_NS = "测试公告·"


def _t(title: str) -> str:
    return _NS + title


def _mk_observed(db, title: str, url: str, *, published: str | None = "2026-09-20",
                 source_id: str = "src_t1", source_name: str = "测试公告源") -> None:
    """塞一条"已发现的公告"（真表；url_hash 唯一键必须给不同的）。"""
    global _ANN_ID
    _ANN_ID += 1
    db.execute(
        "INSERT INTO announcement_observed(observed_id, source_id, source_name, title, url,"
        " url_hash, published_date, first_seen, last_seen, scan_id)"
        " VALUES(?,?,?,?,?,?,?,datetime('now'),datetime('now'),'asc_t1')",
        (f"ann_t{_ANN_ID}", source_id, source_name, title, url, f"h{_ANN_ID}:{url}",
         published))
    db.commit()


def test_scope_rules_strong_cue_wins_deny_otherwise():
    """范围判定：**强规范性线索压过排除词**；没有强线索时，排除词生效（默认留）。

    ⚠ 这条钉的是**判序**：判反了要么误杀征求意见稿（业主正在抱怨的毛病），
    要么把委员征集/督察整改那类行政事务全灌进库。
    """
    # 强线索压过排除词：含"公示"但讲的是办法/征求意见 ⇒ 必须入库
    assert web_ingest.classify_scope("关于公开征求《危险化学品经营许可证管理办法》意见的公示") == "normative"
    assert web_ingest.classify_scope("关于《社会消防技术服务管理规定》报批前的公示") == "normative"
    assert web_ingest.classify_scope("某标准报批前公示") == "normative"
    assert web_ingest.classify_scope("中华人民共和国应急管理部令（第23号）") == "normative"
    # 只有弱线索（公告/通知/报告）时不压过排除词
    assert web_ingest.classify_scope("应急管理部2025年度部门决算") == "non_normative"
    assert web_ingest.classify_scope("关于XX事项的公示") == "non_normative"
    assert web_ingest.classify_scope("某重大事故隐患挂牌督办") == "non_normative"
    assert web_ingest.classify_scope("自然灾害调查评估挂牌督办通知书") == "non_normative"
    assert web_ingest.classify_scope("关于征集森林草原火灾防治分技术委员会委员人选的通知") == "non_normative"
    assert web_ingest.classify_scope("应急管理部关于统计督察整改情况的报告") == "non_normative"
    # 默认**留**（没命中排除词就入库：误留比误杀便宜）
    assert web_ingest.classify_scope("商务部等5部门关于调整《向特定国家（地区）出口易制毒化学品管理目录》的公告") == "normative"
    assert web_ingest.classify_scope("关于调整危险化学品目录的公告") == "normative"
    assert web_ingest.classify_scope("中共中央办公厅 国务院办公厅关于进一步加强安全生产工作的意见") == "normative"


def test_summary_counts_match(db):
    """进度计数：已发现 / 已入库 / 还差多少 / 跳过多少 —— 四个数互相自洽。"""
    _mk_observed(db, _t("中华人民共和国应急管理部令（第23号）社会消防技术服务管理规定"),
                 "https://exp.example.com/a.shtml")
    _mk_observed(db, _t("关于公开征求《危险化学品经营许可证管理办法(修订征求意见稿)》意见的通知"),
                 "https://exp.example.com/b.shtml")
    _mk_observed(db, _t("应急管理部2025年度部门决算"), "https://exp.example.com/c.shtml")
    s = web_ingest.ingest_summary()
    assert s == {"total": 3, "ingested": 0, "pending": 2,
                 "pending_by_status": {"effective": 1, "reference": 1, "withdrawn": 0},
                 "skipped_non_normative": 1}, s


def test_ingest_pending_writes_and_is_idempotent(db):
    """批量入库：真写库 + 分档计数 + 非规范性跳过 + **重复跑不重复入** + pending_left 归零。"""
    u_law = "https://exp.example.com/law23.shtml"
    u_draft = "https://exp.example.com/draft1.shtml"
    u_jue = "https://exp.example.com/juesuan.shtml"
    _mk_observed(db, _t("中华人民共和国应急管理部令（第23号）社会消防技术服务管理规定"), u_law)
    _mk_observed(db, _t("关于公开征求《危险化学品经营许可证管理办法(修订征求意见稿)》意见的通知"), u_draft)
    _mk_observed(db, _t("应急管理部2025年度部门决算"), u_jue)
    tp = _FakeTransport({u_law: (200, _LAW_DETAIL), u_draft: (200, _DRAFT_DETAIL),
                         u_jue: (200, _PLAIN_DETAIL)})

    out = web_ingest.ingest_pending(limit=10, transport=tp)
    assert out["tried"] == 2, f"非规范性那条不该被抓（实测 {out['tried']}）"
    assert out["ingested"] == 2 and out["failed"] == 0 and out["skipped"] == 0, out
    assert out["by_status"] == {"effective": 1, "reference": 1, "withdrawn": 0}, out["by_status"]
    assert out["pending_left"] == 0 and out["stopped_early"] is False
    assert out["stop_reason"] is None
    assert u_jue not in tp.calls, "部门决算那条根本不该发请求"

    # 真写库：两条都在 doc_meta，且效力档/来源 URL 都对
    rows = {r["source_url"]: r["legal_status"] for r in db.execute(
        "SELECT source_url, legal_status FROM doc_meta WHERE source_url LIKE 'https://exp.%'"
    ).fetchall()}
    assert rows == {u_law: "effective", u_draft: "reference"}, rows
    # 条款切出来了：令有两条"第X条"，征求意见稿整篇作一条
    n_law = db.execute("SELECT COUNT(*) c FROM clause_revision cr JOIN doc_meta d"
                       " ON d.doc_id=cr.doc_id WHERE d.source_url=?", (u_law,)).fetchone()["c"]
    n_draft = db.execute("SELECT COUNT(*) c FROM clause_revision cr JOIN doc_meta d"
                         " ON d.doc_id=cr.doc_id WHERE d.source_url=?",
                         (u_draft,)).fetchone()["c"]
    assert n_law == 2 and n_draft == 1, (n_law, n_draft)

    # 再跑一次：没有待入库的了 ⇒ 一条都不抓、也不重复写
    again = web_ingest.ingest_pending(limit=10, transport=tp)
    assert again["tried"] == 0 and again["pending_left"] == 0, again
    assert web_ingest.ingest_summary()["pending"] == 0, web_ingest.ingest_summary()
    assert db.execute("SELECT COUNT(*) c FROM doc_meta WHERE source_url LIKE 'https://exp.%'"
                      ).fetchone()["c"] == 2, "重复跑不许重复入库"


def test_reingest_reports_already_in_library_not_ingested(db):
    """**已经入过的再点一次**：必须报 `skipped/already_in_library`，不许再报"入库成功"。

    这条是 2026-09-24 真机跑出来的缺陷的判据：`ingest_law_text` 的 `duplicate` /
    `standard_exists` **一个新行都没插**，而旧代码把所有非 error 都写成 `ingested`
    ⇒ 真机 372 篇被报成 478 篇（差额就是反复重抓这些行）。
    """
    u = "https://exp.example.com/dup1.shtml"
    title_a = _t("某某管理办法／规定（第9号）")        # 全角斜杠（落库时按存储形折成半角）
    title_b = title_a.replace("／", "/")          # 半角斜杠：**写法不同、存储形相同**
    assert title_b != title_a
    _mk_observed(db, title_a, u)
    tp = _FakeTransport({u: (200, _LAW_DETAIL)})
    first = web_ingest.ingest_pending(limit=5, transport=tp)
    assert first["ingested"] == 1 and first["skipped"] == 0, first
    # 落库的是**存储形**（全角斜杠已折半角）—— 这是与查重同一把尺子的证据
    stored = db.execute("SELECT standard_no FROM doc_meta WHERE source_url=?", (u,)
                        ).fetchone()["standard_no"]
    assert stored == title_b, f"standard_no 应当按存储形落库，实测 {stored!r}"

    # ① 同一条再来一次（正文一模一样 ⇒ ingest_law_text 回 duplicate）
    second = web_ingest.ingest_announcement(title_a, u, transport=tp)
    assert second["status"] == "skipped" and second["reason"] == "already_in_library", second
    assert second["ingest_kind"] == "duplicate", second

    # ② 标题**写法不同、存储形相同** ⇒ ingest_law_text 回 standard_exists。
    #    先证明这对标题真的会撞（否则下面那条断言落在空处），再验证它被诚实报成"库里已有"。
    from src.core.text_utils import store_standard_no
    assert store_standard_no(title_a) == store_standard_no(title_b), "这对标题没撞上，换一对"
    u2 = "https://exp.example.com/dup2.shtml"
    third = web_ingest.ingest_announcement(title_b, u2, transport=_FakeTransport(
        {u2: (200, _DRAFT_DETAIL)}))
    assert third["status"] == "skipped" and third["ingest_kind"] == "standard_exists", third
    assert db.execute("SELECT COUNT(*) c FROM doc_meta WHERE source_url=?", (u2,)
                      ).fetchone()["c"] == 0, "standard_exists 不许插第二篇"

    # ③ 这一条也**不再算待入库**（判据按存储形折过 ⇒ 与"插不插得进"同口径；
    #    不然它会被无限重抓 —— 真机就是这么空转 106 次的）
    _mk_observed(db, title_b, u2, source_id="src_t2")
    assert web_ingest.ingest_summary()["pending"] == 0, web_ingest.ingest_summary()
    assert web_ingest.ingest_pending(limit=5, transport=tp)["tried"] == 0


def test_force_ingests_named_non_normative(db):
    """`force=True` 是**逃生口**：范围判错了时业主不必等改代码（连部门决算也入）。"""
    u = "https://exp.example.com/force-jue.shtml"
    _mk_observed(db, _t("应急管理部2025年度部门决算"), u)
    tp = _FakeTransport({u: (200, _PLAIN_DETAIL)})
    assert web_ingest.ingest_pending(limit=5, transport=tp)["tried"] == 0
    out = web_ingest.ingest_pending(limit=5, transport=tp, force=True)
    assert out["tried"] == 1 and out["ingested"] == 1, out
    assert db.execute("SELECT COUNT(*) c FROM doc_meta WHERE source_url=?", (u,)
                      ).fetchone()["c"] == 1


def test_limit_bounds_and_failures_are_honest(db):
    """`limit` 封顶（一次点下去不会抓几百页）+ 取不到页如实报 `failed`，且**不算**成入库。

    ⚠ 待入库的排序是 `published_date DESC, first_seen DESC, observed_id DESC` ——
    四个 `observed_id`（`ann_tN`）是**字符串**序（`ann_t10 < ann_t2`）⇒ 同一天同一秒插的几条
    谁先被处理**取决于全局计数器**。本用例给四条**不同的发布日期**，让顺序由日期决定
    （不然它就是一条"看运气"的用例：实测在计数器跨过 10 之后翻转，报出 failed=2/ingested=0）。
    """
    urls = [f"https://exp.example.com/n{i}.shtml" for i in range(4)]
    for i, u in enumerate(urls):
        _mk_observed(db, _t(f"某某管理办法的通知（第{i}号）"), u, published=f"2026-09-2{4 - i}")
    tp = _FakeTransport({urls[0]: (200, _LAW_DETAIL)})   # 其余三条都会 404
    out = web_ingest.ingest_pending(limit=2, transport=tp)
    assert out["tried"] == 2, f"limit=2 就只该抓 2 条（实测 {out['tried']}）"
    assert out["ingested"] == 1 and out["failed"] == 1, out
    assert tp.calls == [urls[0], urls[1]], f"按发布日期从新到旧抓（实测 {tp.calls}）"
    # ⚠ **失败的那条留在待入库里**（下次再点还会重试它）—— `pending_left` 因此是 3 而不是 2。
    #   这是有意为之：取不到页往往是临时故障，静默丢弃才是真丢东西。
    assert out["pending_left"] == 3, out
    # ⚠ 停止的**归因**要说清：这批是"抓满 limit"还是"时间到了"。
    #   两者都意味着"没做完"（`stopped_early=True`），但界面文案完全不同 ——
    #   "时间到了"会让人以为卡住了，而抓满 limit 是**正常**的、再点一次就继续。
    assert out["stopped_early"] is True and out["stop_reason"] == "limit", out
    # 上限：limit 给 999 也只抓 INGEST_BATCH_MAX 条
    assert web_ingest.INGEST_BATCH_MAX == 20
    out2 = web_ingest.ingest_pending(limit=999, transport=tp)
    assert out2["tried"] <= web_ingest.INGEST_BATCH_MAX, out2["tried"]


def test_batch_caps_and_dedupe_have_teeth(db):
    """三条"防跑飞"的机制**各自要有判据**（独立复核 MED-2/3/4：此前只有自然语言宣称，
    把任一条去掉整个文件仍然全绿 —— 那种"判据"守不住回归）。

    - 条数上限 `INGEST_BATCH_MAX`：给 999 也只抓 20 条（而且**只发 20 次请求**）；
    - 时间预算 `budget_s`：预算为 0 时**一条都不抓**并如实报 `stop_reason='budget'`；
    - 同一批里同一个 URL **只抓一次**（同一条公告挂在两个源下）。
    """
    class _AnyTransport:
        """按 URL 造一份**各自不同**的正文 —— 正文相同的话除了第一条都会被 `law_text` 按哈希判
        `duplicate`（那样它们就永远留在待入库里，见 §10.193 的残余第 7 条），**量不到"上限"**。"""

        def __init__(self):
            self.calls: list[str] = []

        def fetch(self, url: str, **kw):
            self.calls.append(url)
            return (200, f'<html><body><div class="TRS_Editor">'
                         f'<p>第一条 为了加强管理（{url}），制定本办法。</p>'
                         f'<p>第二条 本办法适用于境内从事相关活动的单位。</p>'
                         f'</div></body></html>')

    # M2：25 条待入库，limit=999 ⇒ 只抓 20 条、只发 20 次请求
    for i in range(25):
        _mk_observed(db, _t(f"某某管理办法的通知（第{i}号）"),
                     f"https://exp.example.com/cap{i}.shtml", published=f"2026-08-{i + 1:02d}")
    tp = _AnyTransport()
    out = web_ingest.ingest_pending(limit=999, transport=tp)
    assert out["tried"] == web_ingest.INGEST_BATCH_MAX == 20, out["tried"]
    assert len(tp.calls) == 20, f"上限必须**限制真正发出的请求数**（实测 {len(tp.calls)}）"
    assert out["pending_left"] == 5, out["pending_left"]

    # M3：预算**负值** ⇒ 一条都不抓，且归因是 budget（不是 limit）。
    #   ⚠ 别用 `budget_s=0`：首条处理发生在 `started` 之后**微秒级**，
    #   `now - started > 0` 在那点时间里可能是 0.0 ⇒ 会**偶发**地先抓上一条（这条用例我第一版就踩了）。
    tp2 = _AnyTransport()
    stopped = web_ingest.ingest_pending(limit=10, transport=tp2, budget_s=-1)
    assert stopped["tried"] == 0 and tp2.calls == [], stopped
    assert stopped["stopped_early"] is True and stopped["stop_reason"] == "budget", stopped

    # M4：同一条公告挂在两个源下 ⇒ 同一次调用里只抓一次
    from src.core.storage.sqlite_db import get_db_connection
    get_db_connection().execute("DELETE FROM announcement_observed")
    get_db_connection().commit()
    u = "https://exp.example.com/twice.shtml"
    _mk_observed(db, _t("某某管理办法的通知（两次）"), u, source_id="src_a")
    _mk_observed(db, _t("某某管理办法的通知（两次）"), u, source_id="src_b")
    tp3 = _AnyTransport()
    dedup = web_ingest.ingest_pending(limit=10, transport=tp3)
    assert len(tp3.calls) == 1, f"同一个 URL 只该抓一次（实测 {len(tp3.calls)}）"
    assert dedup["tried"] == 2 and dedup["skipped"] == 1, dedup
    assert dedup["items"][1]["reason"] == "duplicate_url_in_batch", dedup["items"]


def test_routes_pending_and_ingest_wire(client, db, monkeypatch):
    """两个端点的**接线**：待入库计数出得来、入库入参原样转下去、非法 limit 给 422。

    ⚠ 这里**必须替换掉 `ingest_pending`**：真跑会去抓真实网页（测试不许联网）。
    替换的是"抓取那一层"，路由的参数解析/信封/错误码仍然是被测对象。
    """
    _mk_observed(db, _t("某某管理办法的通知（第7号）"), "https://exp.example.com/r7.shtml")
    c, token = client
    h = {"Authorization": f"Bearer {token}"}

    r = c.get("/api/v1/update/announce-ingest/pending", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["pending"] == 1 and data["total"] == 1, data

    seen: dict = {}

    def _fake(limit=10, source_id=None, *, transport=None, budget_s=0.0, force=False,
              trace_id="-"):
        seen.update({"limit": limit, "source_id": source_id, "force": force})
        return {"tried": 1, "ingested": 1, "skipped": 0, "failed": 0,
                "by_status": {"effective": 1, "reference": 0, "withdrawn": 0},
                "pending_left": 0, "stopped_early": False, "items": []}

    monkeypatch.setattr(web_ingest, "ingest_pending", _fake)
    r2 = c.post("/api/v1/update/announce-ingest",
                json={"limit": 3, "source_id": "src_t1", "force": True}, headers=h)
    assert r2.status_code == 200 and r2.json()["data"]["ingested"] == 1, r2.text
    assert seen == {"limit": 3, "source_id": "src_t1", "force": True}, seen

    r3 = c.post("/api/v1/update/announce-ingest", json={"limit": "不是数"}, headers=h)
    # ⚠ 非法 limit 必须是**真 4xx**（独立复核 MED-1）：写成 200 + 信封里的 error 字段时，
    #   客户端 `res.ok` 为真 ⇒ 界面会把"参数非法"当"成功、0 条"；host 代理的 422 分支也永不可达。
    assert r3.status_code == 422, r3.text
    assert r3.json()["error"] == "invalid_limit", r3.text
    # 空 body 也当默认值处理（前端直接点按钮不带参数）
    r4 = c.post("/api/v1/update/announce-ingest", headers=h)
    assert r4.status_code == 200 and seen["limit"] == 10, r4.text
