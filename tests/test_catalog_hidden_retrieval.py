"""spec 013 判据：检索路径必须尊重 `catalog_hidden`。

## 抓什么

`catalog_hidden=1` 以前**只在浏览类接口**被过滤，检索路径**完全不认它**
（`git grep catalog_hidden -- src/core/retrieval/` 当时为空）。

⇒ 实测后果：拿真问题「个人信息处理者处理个人信息应当取得同意吗」跑真实检索
（`top_k=20`），测试假样本 `个人信息保护法(测试)` 的条款排在**第 3 名与第 16 名**
—— 而库里有**真的**《个人信息保护法》（74 条）。

## ⚠ 两处刻意的"不误伤"（判据成对，缺一即假绿）

1. **那 6 篇真标准**（`GB 12331-1990` 等）保持隐藏是**正确的** ——
   它们的 `n_normal = 0`（只抽出附录/前置说明、一条正文都没有），
   而 `pipeline` 的隐藏规则就是 **`n_normal == 0`**。
   ⇒ 判据要钉"它们**本来就该被挡**"，而不是"别挡它们"。
2. **`catalog_hidden=0` 的文档照常可召回** —— 不许把守卫写成"一律少返回"。
"""
from __future__ import annotations

import sqlite3

import pytest


def _mkdb() -> sqlite3.Connection:
    """最小库：`doc_meta` + `clause_revision`（含 `catalog_hidden` 增量列）。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE doc_meta (
            doc_id TEXT PRIMARY KEY, standard_no TEXT, standard_name TEXT,
            legal_status TEXT, catalog_hidden INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE clause_revision (
            clause_revision_id TEXT PRIMARY KEY, doc_id TEXT, clause_number TEXT,
            content_text TEXT, content_type TEXT DEFAULT 'normal',
            modality TEXT, subject TEXT, knowledge_type TEXT,
            standard_no TEXT, title TEXT);
    """)
    conn.execute("INSERT INTO doc_meta VALUES ('d_vis','GB 1-2020','可见标准','effective',0)")
    conn.execute("INSERT INTO doc_meta VALUES ('d_hid','个人信息保护法(测试)','假样本','effective',1)")
    conn.execute("INSERT INTO clause_revision (clause_revision_id, doc_id, clause_number,"
                 " content_text, knowledge_type) VALUES ('c_vis','d_vis','1','可见正文','legal')")
    conn.execute("INSERT INTO clause_revision (clause_revision_id, doc_id, clause_number,"
                 " content_text, knowledge_type) VALUES ('c_hid','d_hid','1','假正文','legal')")
    return conn


class Test可见性片段:
    """判据的唯一所有者：两个片段函数。"""

    def test_隐藏文档被排除(self):
        from src.core.retrieval.hybrid_engine import _catalog_visible_fragment
        conn = _mkdb()
        frag = _catalog_visible_fragment(conn)
        assert frag, "有 catalog_hidden 列却没生成片段"
        rows = conn.execute(
            "SELECT dm.doc_id FROM doc_meta dm WHERE 1=1" + frag).fetchall()
        ids = {r[0] for r in rows}
        assert ids == {"d_vis"}, f"隐藏文档没被排除: {ids}"

    def test_按条款的片段同口径(self):
        """★ 两处必须**同时**排除同一批文档（结构判据钉住，防只改一处）。"""
        from src.core.retrieval.hybrid_engine import (
            _catalog_visible_by_clause, _catalog_visible_fragment,
        )
        conn = _mkdb()
        a = conn.execute("SELECT dm.doc_id FROM doc_meta dm WHERE 1=1"
                         + _catalog_visible_fragment(conn)).fetchall()
        b = conn.execute("SELECT cr.doc_id FROM clause_revision cr WHERE 1=1"
                         + _catalog_visible_by_clause(conn)).fetchall()
        assert {r[0] for r in a} == {r[0] for r in b} == {"d_vis"}, \
            f"两个片段的判据不一致: doc={[r[0] for r in a]} clause={[r[0] for r in b]}"

    def test_列不存在时不加条件(self):
        """★ `catalog_hidden` 是**增量列**（不在 `schema.sql`）⇒ 老库上没有它。

        列不在时必须返回**空串**（不加条件），而不是拼一个会
        `no such column: catalog_hidden` 报错的片段。
        """
        from src.core.retrieval.hybrid_engine import (
            _catalog_visible_by_clause, _catalog_visible_fragment,
        )
        conn = sqlite3.connect(":memory:")
        conn.executescript("CREATE TABLE doc_meta (doc_id TEXT);"
                           "CREATE TABLE clause_revision (clause_revision_id TEXT, doc_id TEXT);")
        assert _catalog_visible_fragment(conn) == "", "列不在却拼了片段 ⇒ 老库会报错"
        assert _catalog_visible_by_clause(conn) == "", "同上（按条款那个）"

    def test_没有隐藏文档时片段仍然生成(self):
        """★ 反向：片段**不依赖"当前有没有隐藏文档"**。

        若写成"没有隐藏文档就不拼片段"，那**第一篇被隐藏的文档入库后**
        守卫会静默失效（而那时正是它该起作用的时候）。
        """
        from src.core.retrieval.hybrid_engine import _catalog_visible_fragment
        conn = _mkdb()
        conn.execute("UPDATE doc_meta SET catalog_hidden = 0")
        assert _catalog_visible_fragment(conn) != "", \
            "没有隐藏文档时不生成片段 ⇒ 第一篇被隐藏后守卫失效"


def _real_db() -> "Path | None":
    """真库路径 —— **只认显式点名的 `KS_REAL_DB`**。

    ## 为什么不用 `get_settings().db_path` / `APPDATA`

    `tests/conftest.py` 的会话级 fixture 把 `KS_DATA_DIR` 指到**临时库**
    （全量测试的既有纪律：不许碰生产库）⇒ 在 pytest 里
    `get_settings().db_path` **永远不是生产库**。
    而直接拼 `APPDATA` 会**绕过**那道隔离 —— 那等于测试偷偷读了生产库，
    是全量测试纪律不允许的事。

    ⇒ 涉及真库的三条判据一律走本函数：**没显式点名就如实跳过**，
    要点名就跑 `KS_REAL_DB=<path> python -m pytest …`。
    """
    import os
    from pathlib import Path
    explicit = os.environ.get("KS_REAL_DB")
    if not explicit:
        return None
    p = Path(explicit)
    return p if p.exists() else None


class Test那6篇真标准该挡而不是不该挡:
    """★ 我 2026-10-12 说错过的一句话：那 6 篇真标准"不该被挡" —— **错了**。

    实测：它们 `n_normal = 0`（只抽出附录/前置说明、一条正文都没有），
    而 `pipeline` 的隐藏规则就是 **`n_normal == 0`** ⇒ **它们本来就该被挡**。
    本判据钉住这个事实，防止下一个人把"别挡它们"当成需求去做。
    """

    def test_隐藏规则是零normal条款而非零条款(self):
        import inspect
        from src.core.ingestion import pipeline
        src = inspect.getsource(pipeline)
        assert "n_normal == 0" in src, \
            "隐藏规则不是 n_normal==0 ⇒ 我对那 6 篇的判定依据要重核"

    def test_那6篇真标准只有附录没有正文(self):
        """若**显式点名真库**，直接核那 6 篇的 `normal` 条数为 0。"""
        db = _real_db()
        if db is None:
            pytest.skip("未显式点名真库（设 KS_REAL_DB=<path> 才跑）")
        conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            rows = conn.execute("""
                SELECT dm.standard_no,
                       SUM(CASE WHEN cr.content_type='normal' THEN 1 ELSE 0 END) n_norm
                FROM doc_meta dm JOIN clause_revision cr ON cr.doc_id = dm.doc_id
                WHERE dm.catalog_hidden = 1 AND dm.standard_no NOT LIKE '%测试%'
                GROUP BY dm.doc_id""").fetchall()
        finally:
            conn.close()
        if not rows:
            pytest.skip("真库没有 catalog_hidden=1 的真标准")
        bad = [(r[0], r[1]) for r in rows if r[1] != 0]
        assert not bad, (
            f"这些被隐藏的真标准**有** normal 条款 ⇒ 隐藏理由（n_normal=0）不成立，"
            f"应当重核而不是继续挡：{bad}")


class Test假样本不进检索:
    """端到端：**必须显式指向真库**才跑（见下）。

    ## 为什么不能"库在就跑"

    `tests/conftest.py` 的会话级 fixture 把 `KS_DATA_DIR` 指到**临时库**
    （这是全量测试的既有纪律：不许碰生产库）。
    ⇒ 在 pytest 里，`get_settings().db_path` **永远不是生产库**
    ⇒ "拿真库跑检索"这件事**在测试套件里结构上做不到**。

    ⇒ 判据分两层：
      · **套件内**：结构判据（上面那两组）钉住"守卫接上了"；
      · **套件外**：本条用 `KS_REAL_DB` 环境变量**显式点名**真库才跑，
        并在真库上验"假样本不进结果"（`python -m pytest -k 真库`
        加 `KS_REAL_DB=<path>`）。
    """

    def test_假样本不在检索结果里(self):
        import os
        from pathlib import Path
        explicit = os.environ.get("KS_REAL_DB")
        if not explicit:
            pytest.skip("未显式点名真库（设 KS_REAL_DB=<path> 才跑；见类注释）")
        db = Path(explicit)
        if not db.exists():
            pytest.skip(f"KS_REAL_DB 指向的库不存在：{db}")
        from src.core.retrieval.hybrid_engine import perform_hybrid_search
        conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            res = perform_hybrid_search("个人信息处理者处理个人信息应当取得同意吗", top_k=20)
            leaked = []
            for r in res:
                row = conn.execute(
                    "SELECT dm.standard_no FROM clause_revision cr"
                    " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
                    " WHERE cr.clause_revision_id = ?",
                    (r.clause_revision_id,)).fetchone()
                if row and "测试" in str(row[0]):
                    leaked.append(row[0])
        finally:
            conn.close()
        assert not leaked, f"测试假样本仍进检索结果：{leaked}"


class Test守卫真的拼进了各通道SQL:
    """★ 结构判据：**每一条通道**都必须带可见性片段。

    ## 为什么必须有这一组（变异自验发现的缺口）

    第一版的判据只测了"片段函数本身对不对"，
    ⇒ 把片段**从某条通道的 SQL 里删掉**（变异 M5）**测不出来**（7 passed，假绿）。
    ⇒ 补结构判据：直接读 `perform_hybrid_search` 的源码，数它引用了片段几次。
    通道 A/D/E 走 `vis_doc`、B/C/F 走 `vis_clause`（C 在 Python 里筛）。
    """

    def test_三条join通道都带vis_doc(self):
        import inspect
        from src.core.retrieval import hybrid_engine as he
        src = inspect.getsource(he.perform_hybrid_search)
        # A / D / E 三条通道各拼一次 vis_doc
        n = src.count("+ vis_doc")
        assert n >= 3, (
            f"只有 {n} 处拼了 `vis_doc` ⇒ 通道 A/D/E 里有的没带可见性"
            f"（三条 JOIN 了 doc_meta 的通道各需一处）")

    def test_fts两条通道都带vis_clause(self):
        import inspect
        from src.core.retrieval import hybrid_engine as he
        src = inspect.getsource(he.perform_hybrid_search)
        n = src.count("+ vis_clause")
        assert n >= 2, (
            f"只有 {n} 处拼了 `vis_clause` ⇒ 通道 B/F 里有的没带可见性")

    def test_向量通道在Python里筛隐藏文档(self):
        """★ 通道 C（vec0 虚表）**刻意不拼 SQL**，改用 Python 筛 —— 判据钉住这个决定。

        理由（写在代码注释里）：`NOT IN` 下推**没验证过**，而这个仓库栽过
        "看着像的写法比不修更糟"（字面量列表会**返回范围外的行**）。
        ⇒ 若有人把它改成 SQL 拼法，本条变红，逼他先去验证。
        """
        import inspect
        from src.core.retrieval import hybrid_engine as he
        src = inspect.getsource(he.perform_hybrid_search)
        assert "hidden_doc_ids" in src, \
            "向量通道没有在 Python 里筛隐藏文档 ⇒ 通道 C 会漏"
        assert "if hidden_doc_ids:" in src, "Python 筛选的判据不见了"


class Test隐藏集合本身被算出来:
    """★ 变异 M4 的缺口：`hidden_doc_ids` 算不算，端到端在**只有假样本**时看不出。

    假样本主要靠 A/D/E 的 SQL 片段挡住；而 `hidden_doc_ids` 只服务**通道 C**。
    若库里那 7 篇都没有向量，通道 C 的筛选**照样不生效也看不出来**。
    ⇒ 用**结构 + 行为**两条判据钉住它。
    """

    def test_隐藏集合在片段生效时被算出来(self):
        """片段非空 ⇒ 必须去查隐藏集合（不许用 `if False` 之类把它关掉）。"""
        import inspect
        from src.core.retrieval import hybrid_engine as he
        src = inspect.getsource(he.perform_hybrid_search)
        # 必须是 `if vis_doc:` 真条件，且体内查了 catalog_hidden
        assert "if vis_doc:" in src, "隐藏集合的计算被关了（或改成了恒假条件）"
        i = src.find("if vis_doc:")
        window = src[i:i + 400]
        assert "catalog_hidden = 1" in window, \
            "`if vis_doc:` 块里没有查 catalog_hidden=1 ⇒ 隐藏集合算不出来"

    def test_隐藏集合的行为(self):
        """行为判据：真库可达时，隐藏集合必须**恰好等于** `catalog_hidden=1` 的集合。

        ⚠ **本测试第一版写错了**（被门禁抓到，如实留痕）：
        我原来查 `SELECT doc_id FROM doc_meta WHERE 1=1 + frag` ——
        而 `frag` 里的参数是 **`dm.doc_id`**（生产里五条通道都写 `doc_meta dm`）
        ⇒ 不带别名查会 `no such column: dm.doc_id`。
        **修法是让测试与生产同口径**（带 `dm` 别名），
        而不是把片段的默认参数改掉 —— 生产五处都带别名，改片段反而会把判据弄松。
        """
        import os
        from pathlib import Path
        # ⚠ 用**同一个**库做"存在性检查"与"查询"，且只认真库显式点名
        #    （第一版用 `APPDATA` 判存在、却查 `get_settings().db_path` ——
        #     门禁里后者是临时库，两者不是同一个文件）。
        db = _real_db()
        if db is None:
            pytest.skip("未显式点名真库（设 KS_REAL_DB=<path> 才跑）")
        from src.core.retrieval.hybrid_engine import _catalog_visible_fragment
        conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            frag = _catalog_visible_fragment(conn)
            if not frag:
                pytest.skip("该库没有 catalog_hidden 列")
            hidden = {r[0] for r in conn.execute(
                "SELECT doc_id FROM doc_meta WHERE catalog_hidden = 1")}
            # ⚠ 必须带 `dm` 别名：片段里的参数就是 `dm.doc_id`（与生产五条通道同口径）。
            visible = {r[0] for r in conn.execute(
                "SELECT dm.doc_id FROM doc_meta dm WHERE 1=1" + frag)}
            allids = {r[0] for r in conn.execute("SELECT doc_id FROM doc_meta")}
            assert visible == allids - hidden, (
                f"可见集合 != 全库 − 隐藏集合（漏 {len(visible - (allids - hidden))}、"
                f"多 {len((allids - hidden) - visible)}）")
        finally:
            conn.close()

    def test_片段默认参数与生产别名一致(self):
        """★ 结构判据：片段的默认参数**必须**是 `dm.doc_id`。

        生产五条通道（A/D/E）都写 `doc_meta dm` ⇒ 片段只能引用 `dm`。
        若有人把默认值改成 `doc_meta.doc_id` 之类，**生产查询会当场报错**
        （`no such column`）—— 而那种错只会在真跑检索时才炸。
        """
        import inspect
        from src.core.retrieval.hybrid_engine import (
            _catalog_visible_by_clause, _catalog_visible_fragment,
        )
        sig = inspect.signature(_catalog_visible_fragment)
        assert sig.parameters["param"].default == "dm.doc_id", \
            f"片段默认参数不是 dm.doc_id：{sig.parameters['param'].default}"
        # 按条款那个的默认参数是 `clause_revision_id`（不带表别名 —— FTS 表直接有这列）
        sig2 = inspect.signature(_catalog_visible_by_clause)
        assert sig2.parameters["param"].default == "clause_revision_id", \
            f"按条款片段的默认参数不对：{sig2.parameters['param'].default}"
