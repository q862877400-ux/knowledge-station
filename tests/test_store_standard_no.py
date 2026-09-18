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
from src.core.text_utils import (canon_standard_no, standard_no_key, store_standard_name,
                                 store_standard_no)
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

    def test_名称里的全角连字符不许折(self, db):
        """⚠ 复核 b33 的最高风险：**名称里的全角 `－` 是文字，不是形状**。

        真库现存 5 行标准名正拿它当中文连接号（`丙烯腈－丁二烯－苯乙烯（ABS）压力管道系统…`
        `蒸馏－硝酸钍容量法` `氢化物发生－原子荧光光谱法`…）。
        我原来给名称列也用 `store_standard_no`（折 `／` 与 `－`）⇒ 同一标准再入库会写成半角，
        **新旧行名字不一致且没有任何提示**。现在名称列只折 `／`。
        """
        name = "丙烯腈－丁二烯－苯乙烯（ABS）压力管道系统 第1部分：管材"
        clause_repo.insert_document(db, _doc(doc_id="doc_STORE1", standard_name=name))
        got = db.execute("SELECT standard_name FROM doc_meta "
                         "WHERE doc_id='doc_STORE1'").fetchone()[0]
        assert got == name, "名称里的全角连字符被折了（那是改内容，不是折形状）"
        assert "－" in got

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
        """`bulk.py` 用自己的 INSERT（不过收口）——源码级检查它确实调了对应折法。

        为什么不行为级测：那条路的输入来自 PDF 首页解析（`_NO_RE` 字符类是 `[/\\s]`），
        构造"带全角的解析结果"要靠 monkeypatch 才能做，而这里要钉的其实是**入口清单别漏**。
        ⚠ 名与号**用不同的折法**（复核 b33 的 5 行反例），所以这里两个都要点。
        """
        import inspect

        from src.core.ingestion import bulk
        src = inspect.getsource(bulk)
        assert "store_standard_no(no)" in src
        assert "store_standard_name(name or no)" in src

    def test_UPDATE入口_auto_tag_也折(self):
        import inspect

        from src.core.knowledge import auto_tag
        src = inspect.getsource(auto_tag.apply_tags_to_doc_meta)
        assert "store_standard_no(tags.standard_no)" in src

    def test_查重侧也要折_全角号能查到半角行(self, db):
        """§11.0 R6c-3d（复核 b33 的次高风险）：**写入折了、查重不折** ⇒ 全角重复件会绕过护栏、
        直接撞 `insert_document` 的 UNIQUE 抛未捕获的 IntegrityError。

        这是我自己改出来的不对称。`_dup_probe` 是 `run_full_ingest` 查重语义的镜像，用它钉住。
        """
        from src.core.ingestion.dry_run import _dup_probe

        clause_repo.insert_document(db, _doc(doc_id="doc_STORE1",
                                            standard_no="GB/T 10058-2023",
                                            file_hash="a" * 8))
        out = _dup_probe(db, "b" * 8, "GB／T 10058-2023")   # 全角入参、不同 hash
        assert out["kind"] == "standard_no", out
        assert out["doc_id"] == "doc_STORE1"

    def test_入口清单与实现一致(self):
        """入口清单要"能逐条核"（b32 就是靠逐条点名找到漏口的），且清单本身要**承认不完备**。

        ⚠ 我原来写成"**全部**入口"，被复核 b33 证伪：它逐个 grep 后点出 4 个写者不在清单里
        （`fix_standard_name_suffix.py` 直写 `standard_name`、两个 bench 脚本裸 INSERT、
        以及本轮新增的 repair 脚本）。现在措辞改成"已知入口 + 明确列出不在收口路径上的那几个"。
        """
        import inspect

        from src.core.ingestion import bulk
        from src.core.knowledge import auto_tag
        from src.core.storage import clause_repo as cr

        assert cr._STORE_FORM_COLUMNS == ("standard_no", "short_code", "standard_name")
        # 每列各自的折法（名称只折斜杠）
        assert cr._STORE_FORM_FOLDER["standard_name"] is not store_standard_no
        assert cr._STORE_FORM_FOLDER["standard_no"] is store_standard_no
        src_cr = inspect.getsource(cr)
        assert "store_standard_no" in src_cr and "store_standard_name" in src_cr
        # 清单的措辞：不许再出现"全部入口"这种被证伪的说法，且必须点名不在路径上的脚本
        assert "全部入口" not in src_cr
        assert "fix_standard_name_suffix.py" in src_cr
        assert "store_standard_no(no)" in inspect.getsource(bulk)
        assert "store_standard_name(name or no)" in inspect.getsource(bulk)
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
