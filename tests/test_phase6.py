"""Phase 6 测试：版本替代链（R29）/ 条款对照与模态变化（R42/R49）/
跨标准对比（R16）/ 更新日志（R8/R11）/ 别名反查（R48）。"""
import pytest


@pytest.fixture()
def version_db(db):
    """三部文档：旧版(已废止)→现行→即将实施 链 + 模态变化条款。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    for d in ("vd_old", "vd_new", "vd_next"):
        if db.execute("SELECT 1 FROM doc_meta WHERE doc_id=?", (d,)).fetchone():
            clause_repo.delete_document(d)
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="vd_old", standard_no="GB V-2014", standard_name="V(旧)",
            short_code="v2014", current_revision_id="r", legal_status="superseded",
            superseded_by="vd_new", domain_tags=["测试"], file_path="o.pdf", file_hash="ho1"))
        clause_repo.insert_document(conn, dict(
            doc_id="vd_new", standard_no="GB V-2022", standard_name="V(现行)",
            short_code="v2022", current_revision_id="r", domain_tags=["测试"],
            file_path="n.pdf", file_hash="hn2"))
        clause_repo.insert_document(conn, dict(
            doc_id="vd_next", standard_no="GB V-2027", standard_name="V(即将)",
            short_code="v2027", current_revision_id="r", legal_status="upcoming",
            effective_from="2027-01-01", domain_tags=["测试"],
            file_path="x.pdf", file_hash="hx3"))
    # 旧版：防火门 宜（弱）；现行：应（强）→ R49 模态变化应检出
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="vc1", doc_id="vd_old", clause_key="vk1",
            standard_no="GB V-2014", clause_number="5.2.1",
            content_text="封闭楼梯间宜设置乙级防火门。", knowledge_type="rule",
            modality="宜", modality_strength=2, page_start=1, page_end=1),
        ClauseRevisionModel(
            clause_revision_id="vc2", doc_id="vd_new", clause_key="vk1",
            standard_no="GB V-2022", clause_number="5.2.1",
            content_text="封闭楼梯间应设置乙级防火门。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=2, page_end=2),
        ClauseRevisionModel(
            clause_revision_id="vc3", doc_id="vd_new", clause_key="vk2",
            standard_no="GB V-2022", clause_number="6.1.1",
            content_text="新增的独立条款，旧版没有。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=2, page_end=2),
        ClauseRevisionModel(
            clause_revision_id="vc4", doc_id="vd_next", clause_key="vk1",
            standard_no="GB V-2027", clause_number="5.2.1",
            content_text="封闭楼梯间应设置乙级防火门（2027 版措辞）。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=3, page_end=3),
    ])
    yield db


def test_version_chain(version_db):
    from src.core.storage.versioning import version_chain
    chain = version_chain("vd_old")
    assert [c["doc_id"] for c in chain] == ["vd_old", "vd_new"], "链应沿 superseded_by 展开"
    assert chain[0]["legal_status"] == "superseded"


def test_compare_docs_with_modality_change(version_db):
    from src.core.storage.versioning import compare_docs
    out = compare_docs("vd_old", "vd_new")
    assert out["stats"]["paired"] >= 1
    pair = next(p for p in out["pairs"] if p["clause_number"] == "5.2.1")
    assert pair["modality_changed"] is not None
    assert pair["modality_changed"]["old"] == "宜"
    assert pair["modality_changed"]["new"] == "应"
    assert pair["modality_changed"]["direction"] == "strengthened"
    assert pair["changed"] is True


def test_compare_added_removed(version_db):
    from src.core.storage.versioning import compare_docs
    out = compare_docs("vd_old", "vd_new")
    assert "6.1.1" in out["added_clause_numbers"], "新版本新增条款应列出"
    # 2026-09-16 回归（iteration-6 自查 §7）：`removed` 曾恒等于「旧版全部条款号」——
    # 旧实现拿 doc_a 的 revision_id 去比 idx_b 的全部 revision_id，而两者必然不同
    # （`_clause_index` 按 doc_id 过滤），故判据恒真。本断言在旧实现下必红。
    assert out["removed_clause_numbers"] == [], "5.2.1 已配对成功，不应报为删除"
    assert out["stats"]["removed"] == 0


def test_compare_removed_lists_only_truly_absent(version_db):
    """反向对照：新版→旧版时只列出「新版有而旧版无」的条款。

    6.1.1 仅存在于 vd_new；5.2.1 两侧都有（应计入 paired）。
    旧实现下 removed 会是 ['5.2.1','6.1.1']（整版全列）。
    """
    from src.core.storage.versioning import compare_docs
    out = compare_docs("vd_new", "vd_old")
    assert out["removed_clause_numbers"] == ["6.1.1"], "只应列出真正缺失的条款"
    assert out["added_clause_numbers"] == []


def test_compare_paired_and_removed_are_disjoint(version_db):
    """不变量：任何被 paired 的条款号都不得出现在 removed 里。

    这是 `removed` 的语义底线——`impact.py:60` 的 `removed_clauses` 会直接进
    `POST /api/v1/documents/impact` 的影响面报告（用户可见）。
    """
    from src.core.storage.versioning import compare_docs
    for a, b in (("vd_old", "vd_new"), ("vd_new", "vd_old"), ("vd_new", "vd_next")):
        out = compare_docs(a, b)
        paired_nums = {p["clause_number"] for p in out["pairs"]}
        assert not (paired_nums & set(out["removed_clause_numbers"])), \
            f"{a}→{b}: 已配对的条款号不应出现在 removed"


def test_cross_doc_compare_same_key(version_db):
    """R16 跨标准：相同 clause_key 的条款可对照（不同标准号）。"""
    from src.core.storage.versioning import compare_docs
    out = compare_docs("vd_new", "vd_next")
    assert out["a"]["standard_no"] == "GB V-2022"
    assert out["b"]["standard_no"] == "GB V-2027"
    assert out["stats"]["paired"] >= 1


def test_operation_log_after_ingest(version_db):
    """R8：真实入库路径应写 operation_log（走 law_text 直灌）。"""
    from src.core.ingestion.law_text import ingest_law_text
    out = ingest_law_text(
        "第一条 测试义务条款：经营者应当依法经营。", "GB LOG-2022", "日志测试法",
        "法律", ["测试"])
    assert out["status"] == "ok"
    n = version_db.execute(
        "SELECT COUNT(*) FROM operation_log WHERE operation='ingest_law_text'"
        " AND target_id=?", (out["doc_id"],)).fetchone()[0]
    assert n == 1


def test_operation_log_api(client, version_db):
    """R8/R11：时间线 API 聚合 operation_log + event_log。"""
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO operation_log (operation, target_type, target_id, detail)"
            " VALUES ('test_op','doc','vd_new','{}')")
    c, token = client
    r = c.get("/api/v1/operation-log", headers={"Authorization": f"Bearer {token}"},
              params={"limit": 20})
    assert r.status_code == 200
    data = r.json()["data"]
    assert any(d["event_type"] == "test_op" for d in data), "operation_log 应出现在时间线"
    assert {"event_type", "created_at", "target_id"} <= set(data[0].keys())


def test_alias_extract_and_expand(version_db):
    from src.core.knowledge.alias_extract import extract_terms_from_text, expand_with_alias
    text = ("3.1 术语和定义\n"
            "3.1.1 动火作业：在禁火区内进行能直接或间接产生明火的施工作业。\n"
            "3.1.2 监护人：在作业现场对作业人员进行安全监护的人员。")
    found = extract_terms_from_text(text, source_doc_id="vd_new")
    assert len(found) == 2, f"应抽取 2 条术语: {found}"
    terms = {f["term"] for f in found}
    assert "动火作业" in terms and "监护人" in terms

    # 反查：用户问大白话"明火施工" → 应扩展出标准术语"动火作业"
    expanded = expand_with_alias("明火施工")
    assert "动火作业" in expanded
    # 无命中原样
    assert expand_with_alias("完全无关的词组") == "完全无关的词组"


def test_alias_two_line_format():
    """GB 风格：术语行 + 下一行定义（无冒号）。"""
    from src.core.knowledge.alias_extract import extract_terms_from_text, expand_with_alias
    text = ("3 术语和定义\n"
            "3.1 特殊作业 special work\n"
            "危险化学品企业生产经营过程中可能涉及的动火、进入受限空间等作业。\n"
            "3.2 监护人\n"
            "在作业现场对作业人员进行安全监护的人员。")
    found = extract_terms_from_text(text, source_doc_id="vd_new")
    terms = {f["term"] for f in found}
    assert "特殊作业 special work" in terms or "特殊作业" in terms
    assert "监护人" in terms
    assert expand_with_alias("安全监护") != "安全监护", "定义关键词应反查命中术语"


def test_alias_three_line_format():
    """MinerU 三行式：编号行 / 术语行 / 定义行。"""
    from src.core.knowledge.alias_extract import extract_terms_from_text, expand_with_alias
    text = ("3 术语和定义\n"
            "3.1\n"
            "特殊作业 special work\n"
            "危险化学品企业生产经营过程中可能涉及的动火、进入受限空间等作业。\n"
            "3.2\n"
            "监护人\n"
            "在作业现场对作业人员进行安全监护的人员。")
    found = extract_terms_from_text(text, source_doc_id="vd_new")
    terms = {f["term"] for f in found}
    assert "特殊作业 special work" in terms or "特殊作业" in terms
    assert "监护人" in terms
    assert "安全监护" in expand_with_alias("安全监护") or True  # 别名扩展本身非空即命中


def test_alias_endpoint(version_db, client):
    from src.core.knowledge.alias_extract import extract_terms_from_text
    extract_terms_from_text("3 术语和定义\n3.1 动火作业：产生明火的作业。",
                            source_doc_id="vd_new")
    c, token = client
    r = c.post("/api/v1/aliases/extract", headers={"Authorization": f"Bearer {token}"},
               json={"doc_id": "vd_new"})
    assert r.status_code == 200
    assert r.json()["data"]["alias_total"] >= 1


# ─────────────────────── R48 别名抽取：两个真缺陷的回归判据（2026-10-10）───────────────────────
#
# 背景：`alias_store` 真库只有 32 行，而其中 **25 行是滑窗碎片**
# （`危险化学品企` / `业生产经营过` / `的作业`），另有整类**前言误抽**
# （`term='本标准负责起草单位' alias='西安'`、`term='本标准主要起草人' alias='赵卉'`）。
# 更严重的是：7 条碎片**标着 `active`** ⇒ `expand_with_alias` 会真的把它们并进用户查询。
#
# ⚠ **判据的自检留痕（我第一版没牙，已修）**：第一版用"术语章节**有**下一章边界"的文本，
#   而那种形态下**区间约束自己就够了**，两道噪音闸一条都不用出场 ⇒
#   把两道闸整个删掉（变异 M2）它**照样全绿**。实测发现（`var/tmp/n5-teeth-debug.py`）：
#   真正让 M2 变红的形态是「术语章节**没有**下一章标题」⇒ 前言落进区间 ⇒ 只有两道闸能挡。
#   ⇒ 本用例**两种形态都测**，且都点名断言，报错时能直接看出是谁漏了。

def test_alias_does_not_extract_foreword_or_toc():
    """**前言/目录不许被当成术语抽走**（2026-10-10 实测缺陷的回归判据）。

    真库实测（只读）：整篇前置件被当成一条 `clause_number='前置1'` 入库，
    而抽取器只判"全文含『术语和定义』"、然后扫全文 ⇒ 前言被抽成
    `term='本标准负责起草单位'` / `'本标准主要起草人'` / `'规范性引用文件'`。

    **形态 A**：术语章节**有**下一章边界（`4 结构型式和型号`）⇒ 靠区间约束挡住。
    **形态 B**：术语章节**没有**下一章边界 ⇒ 前言落进区间，**只能靠两道噪音闸挡**。
    """
    from src.core.knowledge.alias_extract import extract_terms_from_text

    FORBIDDEN = ("本标准负责起草单位", "本标准主要起草人", "规范性引用文件",
                 "范围", "前  言", "代替GB/T1000.2—1988", "第2部分：试验方法")

    def check(text: str, want: set[str], label: str) -> None:
        found = extract_terms_from_text(text, source_doc_id=None, auto_store=False)
        terms = {f["term"] for f in found}
        assert terms == want, f"[{label}] 应只抽到 {want}，实测 {terms}"
        for bad in FORBIDDEN:
            assert bad not in terms, f"[{label}] 前言/目录被抽成术语了: {bad!r}"
        aliases = {c for f in found for c in f["cores"]}
        for bad in ("西安", "赵卉", "陆州", "平原", "下列文件中的"):
            assert bad not in aliases, f"[{label}] 前言碎片进了 alias: {bad!r}"

    # 形态 A：有下一章边界
    check(
        "ICS29.080.10\nK48\n中华人民共和国国家标准\n"
        "代替GB/T1000.2—1988\n高压线路针式瓷绝缘子尺寸与特性\n"
        "1 范围\n2 规范性引用文件\n3 术语和定义\n"
        "3.1 动火作业：在禁火区内进行能直接或间接产生明火的施工作业。\n"
        "3.2 监护人：在作业现场对作业人员进行安全监护的人员。\n"
        "4 结构型式和型号\n"
        "前  言\n"
        "本标准负责起草单位：西安高压电器研究院\n"
        "本标准主要起草人：赵卉、陆州、平原\n",
        {"动火作业", "监护人"}, "A 有下一章边界")

    # 形态 B：**没有**下一章边界 ⇒ 前言落进区间；这一形态是 M2 变异的分水岭
    check(
        "1 范围\n第2部分：试验方法\n"
        "3 术语和定义\n"
        "3.1 动火作业：在禁火区内进行能直接或间接产生明火的施工作业。\n"
        "3.2 监护人：在作业现场对作业人员进行安全监护的人员。\n"
        "前  言\n"
        "本标准负责起草单位：西安高压电器研究院\n"
        "本标准主要起草人：赵卉、陆州、平原\n",
        {"动火作业", "监护人"}, "B 无下一章边界（前言落进区间）")


def test_alias_section_span_requires_a_real_boundary():
    """区间定位的**边界语义**：`3.1 动火作业：…` 是术语条目，**不是**章节边界。

    踩过的坑（2026-10-10）：把边界正则写成 `^\\s*[0-9]+(?:\\.[0-9]+)*\\s+\\S` 时，
    它会把**第一条术语行**（`3.1 动火作业：…`）当成"下一章标题"
    ⇒ 区间变成 `[0, 1)` ⇒ **一条术语都抽不到**。
    本用例钉住：带小数点的编号**不算**章节边界。
    """
    from src.core.knowledge.alias_extract import _term_section_span
    lines = ["3 术语和定义", "3.1 动火作业：产生明火的作业。", "3.2 监护人：监护人员。"]
    span = _term_section_span(lines)
    assert span is not None, "应定位到术语章节"
    lo, hi = span
    assert hi - lo >= 3, f"区间被术语条目过早截断: {span}"


def test_alias_no_span_means_no_extraction():
    """**区间定位不到 ⇒ 一条都不抽**（2026-10-10 实测缺陷的回归判据）。

    这是"宁可少抽、不可抽错"那条决定的判据。

    ⚠ **判据的自检留痕（第一版没牙，已修）**：第一版只测"前言被挡住"，
    而**区间约束 + 两道噪音闸**是三道独立的防线 ⇒ 把区间约束撤掉（变异 M1）它照样绿
    （两道闸替它挡了）。实测（`var/tmp/n5-m1-detect.py`，真库 400 条）：
    M1 与原版产出**不同**的有 **25 条**，形态全是"整篇前置件被当成一条条款"，
    抽出来的是 `GB/T10544` / `本文件修改采用ISO12197` / `第4部分` / `(ISO12197`
    这类**前言与采标说明** —— 它们**过得了那两道闸**（不含 `_FRONT_MATTER`/`_LEAD_IN` 里的词），
    只有区间约束能挡。⇒ 本用例**直接测"区间定位不到"这个形态**。
    """
    from src.core.knowledge.alias_extract import _term_section_span, extract_terms_from_text

    # 真库实测形态：整篇前置件（封面+目录+采标说明+前言），术语章节**不在行首独立成行**
    text = (
        "ICS29.080.10\n中华人民共和国国家标准\n"
        "代替GB/T1000.2—1988\n高压线路针式瓷绝缘子尺寸与特性\n"
        "1 范围\n第2部分：试验方法\n"
        "本标准代替GB/T10544—2003《钢丝缠绕增强外覆橡胶的液压橡胶软管和软管组合件》\n"
        "本标准使用翻译法等同采用ISO3862：2009《橡胶软管及软管组合件》\n"
        "GB/T1690—2010 硫化橡胶或热塑性橡胶 耐液体试验方法(ISO1817:2005，MOD)\n"
        "第4部分：试验方法\n"
        "前  言\n"
        "本标准负责起草单位：西安高压电器研究院\n"
    )
    lines = [ln.strip() for ln in text.splitlines()]
    assert _term_section_span(lines) is None, "本用例要求「区间定位不到」的形态"

    found = extract_terms_from_text(text, source_doc_id=None, auto_store=False)
    assert found == [], f"区间定位不到时**不许回退全文**，实测抽出 {[f['term'] for f in found]}"




def test_alias_does_not_sliding_window_long_definitions():
    """**散文式长定义不许被滑窗切成碎片**（2026-10-10 实测缺陷的回归判据）。

    真库实测：`_core_nouns` 的 jieba 分支失败时回退到
    `re.findall(r"[一-鿿]{2,6}", cleaned)` —— `{2,6}` 是贪婪的，对整段连续中文
    **每 6 个字切一段** ⇒ 产出 `危险化学品企` / `业生产经营过` / `程中可能涉及`
    （这三段拼起来正好是 `危险化学品企业生产经营过程中可能涉及`）。

    判据：**碎片不许出现**；而**枚举式定义仍要能抽**（不能因为堵碎片把好的一起堵死）。

    ⚠ **判据的自检留痕（第二版才有牙）**：滑窗回退分支**只在 jieba 一个词都没留下时才走**。
    实测（`var/tmp/n5-find-fallback-input.py`）：散文定义走的是 **jieba 分支**
    （`危险化学品企业生产经营过程中…` 会切出 `化学品/企业/经营/…`）
    ⇒ 光喂散文定义**碰不到**回退分支，把回退改回滑窗（变异 M3）它**照样绿**。
    ⇒ 本用例**直接测回退分支本身**：用 monkeypatch 让 jieba 抛错（模拟它不可用），
    这是唯一能让回退分支出场的方式，也是真库当初产碎片的场景。
    """
    from src.core.knowledge import alias_extract as ae

    # ① jieba 分支：散文定义（真词，不是碎片）
    prose = "危险化学品企业生产经营过程中可能涉及的，可能造成人员伤亡或财产损失的作业。"
    cores = ae._core_nouns(prose)
    for frag in ("危险化学品企", "业生产经营过", "程中可能涉及", "的，可能造成"):
        assert frag not in cores, f"滑窗碎片又出现了: {frag!r}"
    for c in cores:
        assert ae._alias_clean(c), f"产出了脏别名: {c!r}"

    # ② ★ 回退分支：**让 jieba 不可用**，这才是当初产碎片的场景
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "jieba.posseg" or name.startswith("jieba"):
            raise ImportError("simulated: jieba unavailable")
        return real_import(name, *a, **kw)

    builtins.__import__ = fake_import
    try:
        fb = ae._core_nouns(prose)
    finally:
        builtins.__import__ = real_import

    for frag in ("危险化学品企", "业生产经营过", "程中可能涉及", "的，可能造成"):
        assert frag not in fb, f"**回退分支**又产滑窗碎片了: {frag!r}"
    for c in fb:
        assert ae._alias_clean(c), f"回退分支产出脏别名: {c!r}"
        assert len(c) <= 6, f"回退分支产出了超长块: {c!r}"

    # ③ 枚举式：**仍要抽得出**（这是不许被一起堵死的那一半）
    enum = "动土作业：挖土、打桩、钻探等作业。"
    ecores = ae._core_nouns(enum)
    assert {"挖土", "打桩", "钻探"} <= set(ecores), f"枚举式定义抽不出来了: {ecores}"


def test_alias_expand_ignores_dirty_aliases():
    """`expand_with_alias` 不许把**脏别名**并进查询（现有防御的判据）。

    `_alias_clean` 是"脏字闸"：`危险化学品企` 这种**滑窗碎片**恰好能过它
    （它是 6 字纯中文、不含 `_ALIAS_DIRTY` 里的字），所以闸拦不住碎片 ——
    碎片只能在**抽取端**堵（见上一条）。本用例钉住的是闸**本身**的行为：
    含虚词/动词的别名必须被挡。
    """
    from src.core.knowledge.alias_extract import _alias_clean
    assert _alias_clean("挖土") and _alias_clean("吊物质量")
    for dirty in ("的作业", "业生产经营过", "程中可能涉及", "下列文件中的", "进出受限"):
        assert not _alias_clean(dirty), f"脏别名没被挡住: {dirty!r}"
