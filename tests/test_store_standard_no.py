# -*- coding: utf-8 -*-
"""标准号"存储形"收口测试（§11.0 R6c-2d）。

**为什么有这个文件**：独立复核 b32 把我"入库侧不需要改、没有活的派生路径产出全角斜杠"的结论
**证伪了**——监听文件夹那条路会把 `GB／T 10058-2023 电梯技术条件(1).pdf` 的 stem 原样写进
`standard_no`/`short_code`；OCR 循环的 manifest 里还有 **8205 条带全角**（其中约 2322 条 PDF 尚未入库）。
也就是说：只做存量回填**挡不住再长回来**。本文件钉住"收口之后不会再漏"。

守四件：
  1. `store_standard_no` 是 **1:1 换形状**——不动空格/大小写/年份，也不改变"是不是同一部标准"
     （`norm_no(旧)==norm_no(新)`）；
  2. **写入边界收口**：`insert_document` 三个列都折（`short_code` 是从 `standard_no` 派生的，
     只在某个调用方折一定会漏）；
  3. **裸 INSERT / UPDATE 两个入口也过同一个 helper**（清单在 `clause_repo._STORE_FORM_COLUMNS` 旁）；
  4. ⚠ **折完撞车会变成 IntegrityError**（`standard_no` 有 UNIQUE）：这是**行为变化**，
     必须有用例说明——以前"同一标准两份文件"能靠全角/半角差异并存，现在会**报错**而不是静默写第二行。
"""
from __future__ import annotations

import sqlite3

import pytest

from src.core.storage import clause_repo
from src.core.text_utils import canon_standard_no, standard_no_key, store_standard_no
from src.core.update.channels.base import norm_no


class Test存储形:
    def test_全角折半角_其余一字不动(self):
        assert store_standard_no("GB／T 10058-2023") == "GB/T 10058-2023"
        assert store_standard_no("GB／T10058－2023") == "GB/T10058-2023"   # 连字符也折
        assert store_standard_no("GB/T 10058-2023") == "GB/T 10058-2023"   # 幂等
        assert store_standard_no("GBZ／T 160.27-2004") == "GBZ/T 160.27-2004"

    def test_不动空格大小写与年份(self):
        for s in ("GB 18218-2018", "gb/t 1.1-2020", "AQ/T 3016-2008", "T/CECS 1000-2021"):
            assert store_standard_no(s) == s

    def test_空值不炸(self):
        assert store_standard_no(None) == ""
        assert store_standard_no("") == ""

    def test_不改变是不是同一部标准(self):
        """1:1 换形状的**全部意义**：`norm_no` 前后必须相等（否则就动了语义）。"""
        for s in ("GB／T 10058-2023", "GBZ／T 160.27-2004", "AQ／T 3016-2008",
                  "DB44／T 1234-2020", "GB／T 14308-2010"):
            assert norm_no(store_standard_no(s)) == norm_no(s), s

    def test_与比较键的分工没被搞混(self):
        """`canon_standard_no`/`standard_no_key` 是**比较键**（去空格去斜杠），存储形**不**那样做。

        这条用例存在的理由：复核的教训里反复出现"看起来都在归一，其实是三个不同口径"。
        """
        raw = "GB／T 10058-2023"
        assert store_standard_no(raw) == "GB/T 10058-2023"          # 保留空格与斜杠
        assert canon_standard_no(raw) == "GBT10058-2023"            # 去空格去斜杠（比较用）
        assert standard_no_key(raw) == "GBT10058-2023"


def _doc(**over) -> dict:
    base = dict(doc_id="doc_STORE1", standard_no="GB/T 1-2020", standard_name="测试",
                short_code="GB/T1-2020", current_revision_id="rev_1",
                file_path="x.pdf", file_hash="h" * 8)
    base.update(over)
    return base


class Test写入收口:
    """⚠ 这些用例**必须自己清理**：`db` fixture 是**会话级同一个库**（`_isolate_data_dir` 整场只建一次），
    所以写进去的行会留给后面的用例。我第一版没清，全量跑时 `test_折完撞车…` 直接红
    （前一个用例留下的同号行让"第一条 INSERT"就抛 IntegrityError）——**单跑绿、全量红**，
    正是这种"顺序依赖"最容易骗过人的形态。
    """

    @pytest.fixture(autouse=True)
    def _tidy(self, db):
        db.execute("DELETE FROM doc_meta WHERE doc_id LIKE 'doc_STORE%'")
        db.commit()
        yield
        db.execute("DELETE FROM doc_meta WHERE doc_id LIKE 'doc_STORE%'")
        db.commit()

    def test_insert_document折不折三个列(self, db):
        clause_repo.insert_document(db, _doc(
            standard_no="GB／T 10058-2023",
            short_code="GB／T100582023",
            standard_name="GB／T 10058-2023 电梯技术条件"))
        row = db.execute("SELECT standard_no, short_code, standard_name FROM doc_meta "
                         "WHERE doc_id='doc_STORE1'").fetchone()
        assert tuple(row) == ("GB/T 10058-2023", "GB/T100582023",
                              "GB/T 10058-2023 电梯技术条件")

    def test_普通号一字不动(self, db):
        clause_repo.insert_document(db, _doc())
        row = db.execute("SELECT standard_no, short_code FROM doc_meta "
                         "WHERE doc_id='doc_STORE1'").fetchone()
        assert tuple(row) == ("GB/T 1-2020", "GB/T1-2020")

    def test_不改调用方的dict(self, db):
        """调用方常复用同一个 dict（pipeline 里就复用）——被就地改掉会很难查。"""
        doc = _doc(standard_no="GB／T 10058-2023")
        clause_repo.insert_document(db, doc)
        assert doc["standard_no"] == "GB／T 10058-2023"

    def test_折完撞车会报IntegrityError而不是静默写第二行(self, db):
        """⚠ **行为变化**（有意）：以前全角/半角是两个不同的串，所以"同一标准两份文件"能并存
        （真库现存那一对 `GB／T 14308-2010` / `GB/T 14308-2010` 就是这么来的）。
        收口之后第二份会撞 `standard_no` 的 UNIQUE ⇒ **报错**。
        选"报错"而不是"再折一次让它并进去"，是因为静默写第二行正是数据被污染的形态；
        操作者拿到的是一个明确冲突，而不是一份查不出所以然的重复。

        ⚠ 号**每次随机**：会话级共享库里可能有别的用例留下的同号行（见类 docstring 的教训）。
        """
        import uuid
        n = 10000 + uuid.uuid4().int % 80000
        half = f"GB/T {n}-2020"
        clause_repo.insert_document(db, _doc(doc_id="doc_STORE_A", standard_no=half))
        with pytest.raises(sqlite3.IntegrityError):
            clause_repo.insert_document(db, _doc(doc_id="doc_STORE_B",
                                                standard_no=half.replace("/", "／")))
        rows = db.execute("SELECT COUNT(*) FROM doc_meta WHERE standard_no=?", (half,)).fetchone()
        assert rows[0] == 1

    def test_裸INSERT入口_bulk_也折(self):
        """`bulk.py` 用自己的 INSERT（不过收口）——源码级检查它确实调了同一个 helper。

        为什么不行为级测：那条路的输入来自 PDF 首页解析（`_NO_RE` 字符类是 `[/\\s]`），
        构造"带全角的解析结果"要靠 monkeypatch 才能做，而这里要钉的其实是**入口清单别漏**。
        """
        import inspect

        from src.core.ingestion import bulk
        src = inspect.getsource(bulk)
        assert "store_standard_no(no)" in src and "store_standard_no(name or no)" in src

    def test_UPDATE入口_auto_tag_也折(self):
        import inspect

        from src.core.knowledge import auto_tag
        src = inspect.getsource(auto_tag.apply_tags_to_doc_meta)
        assert "store_standard_no(tags.standard_no)" in src

    def test_入口清单与实现一致(self):
        """`_STORE_FORM_COLUMNS` 旁登记的四个入口，每个都能在代码里找到折叠调用。

        这条防的是"清单写了、代码漏了"以及反过来"代码改了、清单没改"——
        复核 b32 正是靠逐个点名入口才找到漏口的。
        """
        import inspect

        from src.core.ingestion import bulk
        from src.core.knowledge import auto_tag
        from src.core.storage import clause_repo as cr

        assert cr._STORE_FORM_COLUMNS == ("standard_no", "short_code", "standard_name")
        assert "store_standard_no" in inspect.getsource(cr._store_form_doc)
        assert "store_standard_no(no)" in inspect.getsource(bulk)
        assert "store_standard_no(tags.standard_no)" in inspect.getsource(auto_tag.apply_tags_to_doc_meta)
        from pathlib import Path
        script = (Path(__file__).resolve().parents[1] / "scripts"
                  / "normalize-standard-no-slash.py").read_text(encoding="utf-8")
        assert '"／", "/"' in script or "'／','/'" in script or "／" in script


class TestOCR循环脚本:
    """`var/ocr-loop/ingest_from_manifest.py`（**已入库 53 个跟踪文件之一**，不是随手脚本）。

    它压着 manifest 里 **8205 条带全角**（其中约 2322 条 PDF 尚未入库）——
    复核 b32 的结论是：只要这个循环再跑一次，刚清掉的脏号就会长回来。
    这条用真函数（不是源码字符串）钉住它剥号正确，因为 b32 抓到的正是**行为**错：
    head 里漏了 `GBZ／T` ⇒ `std_no` 被压成裸 `GBZ／T`（真库现存那一行就是它的指纹）。
    """

    @staticmethod
    def _mod():
        import importlib.util
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "var" / "ocr-loop" / "ingest_from_manifest.py"
        spec = importlib.util.spec_from_file_location("_ks_ingest_from_manifest", p)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_GBZ_T_不再退化成裸前缀(self):
        mod = self._mod()
        std_no, std_name = mod.split_std("GBZ／T 160.33-2004 工作场所空气有毒物质测定硫化物")
        assert std_no == "GBZ/T 160.33-2004"
        assert std_name.startswith("工作场所空气有毒物质测定")

    def test_普通号与GB分支不变(self):
        mod = self._mod()
        assert mod.split_std("GB 11660-1989 炼铁厂卫生防护距离标准")[0] == "GB 11660-1989"
        assert mod.split_std("GB／T 10058-2023 电梯技术条件")[0] == "GB/T 10058-2023"
        assert mod.split_std("GBZ 1-2010 工业企业设计卫生标准")[0] == "GBZ 1-2010"
