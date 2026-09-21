"""入库管线**写处理状态** + 「重来一次」+ `catalog_hidden` 复位（KB-FOLDER-PLAN 第 4 步）。

## 这组用例在守什么（每一类都有**反向**用例）

1. **硬前置**：`doc_filing_state` 以前**全仓没人写**（只有 `folder_store` 的定义与归位迁移
   脚本两处引用）⇒「待分类」那列"处理状态"永远是"排队中"、识别率永远是空。
   现在 `run_full_ingest` 在**成功**时写 `confirming` + `confidence`，`bulk.parse_loop` 在
   **开始识别**前写 `recognizing`、失败时写 `failed` + `failure_kind`。
   ⇒ 正例：真跑一次入库，状态行真的被写；**反例**：把写状态的出口打断（monkeypatch 成
   不写）⇒ 状态行就**不会**出现（这条反例就是"接口没接上"的哨兵，防止判据恒真）。
2. **一条正文条款都没提出来**（正文为零/水印页）⇒ 状态是 `failed` + `failure_kind`、
   `catalog_hidden=1`（`run_full_ingest` 的目录卫生），而且**必须仍能在「待分类」里看到**
   （§十七：看不到就修不了）。反例：提出真条款的那一篇 ⇒ `catalog_hidden=0`。
3. **「重来一次」**：`reingest=True` 走**既有**解析路径把同一篇重导一遍 —— 真解析、真换
   `doc_id`、真写状态；**反向**：不重导（走 `/ingest/bulk` 的默认 `reingest=False`）
   ⇒ 那篇被隐藏的文件**仍然是** `catalog_hidden=1`（没有回头路这件事在数据上是真的）。
4. **批量导入那条路**：快扫会先建一行 `file_hash` 相同的**占位** ⇒ 真解析必须带
   `reingest=True` 替换占位，否则 `run_full_ingest` 判 `duplicate`、**一条条款都不解析**
   而进度报 `parsed`（本步实测的真缺陷，见 `bulk._placeholder_still_there`）。

⚠ 全部在 conftest 的**临时库 + tmp_path** 上跑：真库 2.2GB / 6417 篇，一根手指都不碰。
⚠ 解析器换成**合成 blocks**（`monkeypatch` 掉 `run_parser_isolated`）：本组验的是
   **状态机与写库**，不是 MinerU；不换的话每条用例都要跑一次真解析（几分钟起）。
   合成 blocks 走的是**真链路**：`split_items_into_clauses` → `build_clause_models` →
   真入库事务，只有"从 PDF 里抠 blocks"这一步是假的。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import fitz
import pytest

# ⚠ 这两个名字只为了让 `_kb_folder_api_fixtures` 里的**夹具**注册进来（同 test_kb_folder_api 的做法）。
from _kb_folder_api_fixtures import std_tree, tops  # noqa: F401

from src.core.ingestion import bulk
from src.core.ingestion import pipeline as pipeline_mod
from src.core.knowledge import folder_store as fs

#: 一页够切出真条款的正文（条款号 + 中文正文；切分器按行首条款号切）。
REAL_BLOCKS = [
    "1 范围",
    "本标准规定了危险化学品企业特殊作业的安全要求。",
    "2 规范性引用文件",
    "下列文件对于本文件的应用是必不可少的。",
    "3 术语和定义",
    "3.1 特殊作业 指在生产经营过程中可能对操作者造成伤害的作业。",
    "4 基本要求",
    "4.1 作业前应进行风险辨识并办理作业审批手续。",
]
#: 一页"一个字都没提出来"的正文（盗版站水印那种；§十七 实测那 2 篇就是这样）。
WATERMARK_BLOCKS = ["学兔兔 www.bzfxw.com", "学兔兔 www.bzfxw.com"]


def _write_pdf(path: Path, first_line: str = "GB/T 39999-2020") -> Path:
    """一页真实 PDF（只为了让 `run_full_ingest` 的前置检查与 `measure_skew` 有文件可开）。"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), first_line)          # 内置字体只有 ASCII
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def synthetic_parser(monkeypatch):
    """把 `run_parser_isolated` 换成**给定 blocks 的合成结果**（真链路，只有解析这一步是假的）。"""
    def _install(blocks: list[str]) -> None:
        def _fake(pdf_path, output_dir, timeout=900, force_deep=False, deep_fallback=True):
            return {
                "blocks": [{"text": t, "page_number": 1, "bbox": [60.0, 600.0, 530.0, 720.0]}
                           for t in blocks],
                "geometries": {1: {"width": 595.0, "height": 842.0, "rotation": 0}},
                "deep_output": None,
                "is_ocr": False,
            }
        monkeypatch.setattr(pipeline_mod, "run_parser_isolated", _fake)
    return _install


def _uniq_no(base: int) -> str:
    """本会话唯一的标准号（`doc_meta.standard_no` 有唯一约束，临时库是会话级的）。"""
    return f"GB/T 9{base}-20{10 + (base % 80):02d}"


def _inbox_rows(api, c, token) -> dict:
    """把「待分类」**翻页读全**（每页上限 200，按 offset 走到 has_more 为假）。

    ⚠ 为什么不写死 `limit=500`：`MAX_FILE_PAGE=200` ⇒ 那条会 422（本批实测踩到）。
    也不写死 `limit=200` 只读一页：这是**会话级**临时库、别的用例也在往里插文档，
    目标那篇可能被 ORDER BY standard_no 排到第二页去 ⇒ 判据会假红。
    """
    from _kb_folder_api_fixtures import api as _api, data_of
    out: dict = {}
    offset = 0
    while True:
        page = data_of(_api(c, token, "get", "/api/v1/kb/inbox",
                            params={"limit": 200, "offset": offset}))
        for r in page["items"]:
            out[r["doc_id"]] = r
        if not page.get("has_more"):
            return out
        offset += 200
        if offset > 5000:                      # 防呆：不许在这里无限转
            raise AssertionError("待分类翻页没有终点")


@pytest.fixture(autouse=True)
def _offline_embedder(monkeypatch):
    """向量引擎强制离线（与 `test_ks_answer` 同一手法）。

    ⚠ 不打的实测后果：`clause_repo.insert_clauses_in_txn` 会问
    `embedder.is_available()`，而真加载会去 huggingface **下模型** —— 本机没有那个缓存时
    用例**挂在网络等待里**（本批第一次跑就是这样，整文件被 pytest-timeout 掐掉）。
    """
    from src.core.retrieval import embedder as _emb
    monkeypatch.setattr(_emb, "is_available", lambda: False)
    yield


# ═════════════════════ 1. 入库真的写处理状态（+ 反向哨兵） ═════════════════════

def test_real_ingest_writes_filing_state(db, tmp_path, synthetic_parser):
    """正例：真跑一次入库 ⇒ `doc_filing_state` 有这一行、`stage` 与识别率**真的被写**。"""
    synthetic_parser(REAL_BLOCKS)
    pdf = _write_pdf(tmp_path / "good.pdf", "GB/T 90101-2020")
    out = pipeline_mod.run_full_ingest(pdf, _uniq_no(101), "测试标准 101")
    assert out["status"] == "ok", out
    row = fs.get_filing_state(out["doc_id"])
    assert row is not None, "入库成功却没写处理状态行（第 4 步的硬前置没接上）"
    assert row["stage"] == "confirming", row
    assert row["confidence"] is not None, "识别率没写（界面上的识别率会永远空着）"
    assert 0.0 <= float(row["confidence"]) <= 1.0
    # 库里这一篇真的提出了正文条款（不是"报了个 ok"）
    n = db.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?",
                   (out["doc_id"],)).fetchone()[0]
    assert n > 0 and out["total_clauses"] > 0, (n, out["total_clauses"])
    assert out["catalog_hidden"] is False


def test_reverse_without_the_hook_no_state_row(db, tmp_path, synthetic_parser, monkeypatch):
    """**反向哨兵**：把"写状态"这个出口打断 ⇒ 状态行**必须**不出现。

    这条是防"判据恒真"的：如果哪天有人把 `_write_filing_state` 改成空操作、或者把调用点删了，
    上面那条正例仍可能因为别处顺手写了状态而行——所以这里把出口打断，要求结果**真的缺那行**。
    """
    synthetic_parser(REAL_BLOCKS)
    monkeypatch.setattr(pipeline_mod, "_write_filing_state",
                        lambda *a, **kw: False)
    pdf = _write_pdf(tmp_path / "nohook.pdf", "GB/T 90102-2020")
    out = pipeline_mod.run_full_ingest(pdf, _uniq_no(102), "测试标准 102")
    assert out["status"] == "ok", out
    assert out["filing_state_written"] is False
    assert fs.get_filing_state(out["doc_id"]) is None, \
        "出口被打断了却还有状态行 —— 说明状态不是这条链写进去的，判据是假的"


# ═════════════════════ 2. 正文为零 ⇒ failed，且仍能看见 ═════════════════════

def test_zero_clause_ingest_is_failed_and_still_visible_in_inbox(db, tmp_path, synthetic_parser):
    """一条正文条款都没提出来 ⇒ `failed` + 失败原因 + `catalog_hidden=1`，**但仍在「待分类」里**。"""
    synthetic_parser(WATERMARK_BLOCKS)
    pdf = _write_pdf(tmp_path / "watermark.pdf", "GB/T 90103-2020")
    out = pipeline_mod.run_full_ingest(pdf, _uniq_no(103), "水印页标准")
    assert out["status"] == "ok"
    assert out["catalog_hidden"] is True
    row = fs.get_filing_state(out["doc_id"])
    assert row["stage"] == "failed", row
    assert row["failure_kind"] == fs.FAILURE_KIND_ZERO_CLAUSES, row
    # 目录里看不见（目录卫生）……
    assert db.execute("SELECT catalog_hidden FROM doc_meta WHERE doc_id=?",
                      (out["doc_id"],)).fetchone()[0] == 1
    # ……但「待分类」里**看得到**（否则就是"看不到就修不了"）
    items = {r["doc_id"]: r for r in fs.list_pending_filing(limit=500)["items"]}
    assert out["doc_id"] in items, "正文为零/识别失败的文件必须能在「待分类」里看到"
    assert items[out["doc_id"]]["catalog_hidden"] == 1


def test_reverse_good_doc_is_hidden_zero(db, tmp_path, synthetic_parser):
    """反向：提出真条款的那一篇 ⇒ `catalog_hidden` 必须是 **0**（显式复位那条语句）。

    这条同时钉住"解析成功且提出正文条款时显式 `UPDATE … catalog_hidden = 0`"：
    把那一句删掉、只靠"新行 DEFAULT 0"时它**仍然**绿（今天两行都新插）——所以下面
    `test_reingest_resets_catalog_hidden_to_zero` 用**同一 `doc_id` 之外的真路径**再钉一次：
    重导后新行必须显式为 0，而**不重导**的那一篇仍然是 1。
    """
    synthetic_parser(REAL_BLOCKS)
    pdf = _write_pdf(tmp_path / "visible.pdf", "GB/T 90104-2020")
    out = pipeline_mod.run_full_ingest(pdf, _uniq_no(104), "正文正常的标准")
    assert out["status"] == "ok" and out["catalog_hidden"] is False
    assert db.execute("SELECT catalog_hidden FROM doc_meta WHERE doc_id=?",
                      (out["doc_id"],)).fetchone()[0] == 0


# ═════════════════════ 3. 「重来一次」+ catalog_hidden 复位 ═════════════════════

def test_reingest_parses_the_same_file_again_and_resets_hidden(db, tmp_path, synthetic_parser):
    """「重来一次」：同一篇（先被隐藏）重导后 ⇒ 新行 `catalog_hidden=0` + 状态 `confirming`。

    模拟业主真实的回头路：先入库一个"水印页"（被隐藏、failed），再拿**同一标准号**的一份
    **真内容**文件走 `reingest=True`（= 界面上点「重来一次」，或换扫描件重传那条路）。
    """
    synthetic_parser(WATERMARK_BLOCKS)
    pdf_bad = _write_pdf(tmp_path / "bad.pdf", "GB/T 90105-2020")
    no = _uniq_no(105)
    first = pipeline_mod.run_full_ingest(pdf_bad, no, "先入库的水印页")
    assert first["catalog_hidden"] is True
    old_doc = first["doc_id"]

    # 反向：**不重导**再跑一次同一个文件 ⇒ 判 duplicate，什么都不会变（那篇仍是隐藏的）
    again = pipeline_mod.run_full_ingest(pdf_bad, no, "先入库的水印页")
    assert again["status"] == "duplicate", again
    assert fs.get_filing_state(old_doc)["stage"] == "failed"
    assert db.execute("SELECT catalog_hidden FROM doc_meta WHERE doc_id=?",
                      (old_doc,)).fetchone()[0] == 1, "不重导时那篇必须**仍然**是隐藏的"

    # 正向：换成有真内容的文件、带 reingest=True ⇒ 真解析、新 doc_id、显式复位
    synthetic_parser(REAL_BLOCKS)
    pdf_good = _write_pdf(tmp_path / "good2.pdf", "GB/T 90105-2020")
    out = pipeline_mod.run_full_ingest(pdf_good, no, "重导后的真标准", reingest=True)
    assert out["status"] == "ok" and out["reingested"] is True, out
    assert out["doc_id"] != old_doc
    assert out["catalog_hidden"] is False
    assert db.execute("SELECT catalog_hidden FROM doc_meta WHERE doc_id=?",
                      (out["doc_id"],)).fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?",
                      (out["doc_id"],)).fetchone()[0] > 0
    assert fs.get_filing_state(out["doc_id"])["stage"] == "confirming"
    # 旧的那一行已经被删掉（reingest 的语义：新开 doc_id、删旧文档）
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?",
                      (old_doc,)).fetchone()[0] == 0


def test_reingest_endpoint_marks_recognizing_and_parses(db, tmp_path, synthetic_parser,
                                                        client, monkeypatch):
    """**端点级**：`POST /kb/inbox/reingest` 立刻返回 + 真的把这一篇重导了（另起后台线程）。"""
    from _kb_folder_api_fixtures import api, data_of
    c, token = client
    synthetic_parser(WATERMARK_BLOCKS)
    pdf = _write_pdf(tmp_path / "ep.pdf", "GB/T 90106-2020")
    first = pipeline_mod.run_full_ingest(pdf, _uniq_no(106), "端点用例的水印页")
    assert first["catalog_hidden"] is True
    # 端点要的源文件路径来自 doc_meta.file_path（run_full_ingest 写的是真实路径）
    assert db.execute("SELECT file_path FROM doc_meta WHERE doc_id=?",
                      (first["doc_id"],)).fetchone()[0] == str(pdf.resolve())

    # 解析换成"真内容"：重导后这一篇应当变成可见、有条款
    synthetic_parser(REAL_BLOCKS)
    got = data_of(api(c, token, "post", "/api/v1/kb/inbox/reingest",
                      json={"doc_ids": [first["doc_id"]]}))
    assert got["queued"] == 1 and got["skipped"] == []
    # 立刻可见的状态是「识别中」（界面上那一列会如实显示）
    st = fs.get_filing_state(first["doc_id"])
    assert st is not None and st["stage"] in ("recognizing", "confirming", "failed"), st

    # 等后台线程跑完（真解析是几十秒起的事，这里是小样本 ⇒ 给足 60s 仍超时即失败）
    from src.core.ingestion import reingest as reingest_mod
    deadline = time.time() + 60
    while time.time() < deadline and reingest_mod.reingest_status()["running"]:
        time.sleep(0.2)
    assert reingest_mod.reingest_status()["running"] is False, "重导线程 60s 没跑完"
    status = data_of(api(c, token, "get", "/api/v1/kb/inbox/reingest/status"))
    assert status["done"] == 1 and status["results"][0]["status"] == "ok", status
    new_doc = status["results"][0]["new_doc_id"]
    assert new_doc and new_doc != first["doc_id"]
    assert db.execute("SELECT catalog_hidden FROM doc_meta WHERE doc_id=?",
                      (new_doc,)).fetchone()[0] == 0
    assert fs.get_filing_state(new_doc)["stage"] == "confirming"


def test_reingest_endpoint_skips_missing_source_and_rejects_empty(client, db):
    """边界：源文件不在磁盘上 ⇒ **如实跳过并说明**；空数组 / 不存在 ⇒ 422/跳过，不许瞎跑。"""
    from _kb_folder_api_fixtures import api, data_of, error_code, mkdoc_full
    c, token = client
    d = mkdoc_full(db, "re_skip_1")            # file_path='a.pdf'（磁盘上没有这个文件）
    got = data_of(api(c, token, "post", "/api/v1/kb/inbox/reingest", json={"doc_ids": [d]}))
    assert got["queued"] == 0 and len(got["skipped"]) == 1
    assert "源文件不在磁盘上" in got["skipped"][0]["reason"]
    st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/reingest",
                              json={"doc_ids": []}))
    assert (st, code) == (422, "invalid_decision")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/reingest",
                              json={"doc_ids": ["doc_nope_kb4"]}))
    assert st == 200 and code == ""           # 不存在的 doc_id 走 skipped（不是 500）
    body = api(c, token, "post", "/api/v1/kb/inbox/reingest",
               json={"doc_ids": ["doc_nope_kb4"]}).json()
    assert body["data"]["skipped"][0]["reason"].startswith("库里没有这一篇")


# ═════════════════════ 4. 批量导入那条路（占位行 + 状态） ═════════════════════

def test_bulk_import_really_parses_and_writes_states(db, tmp_path, synthetic_parser):
    """批量导入：`resume` 之后**真的有条款** + 占位行的状态从 `recognizing` 走到终态。

    ⚠ 这条用例同时钉住本步修掉的那个真缺陷：快扫建的占位行 `file_hash` 与文件相同
    ⇒ 不带 `reingest=True` 时 `run_full_ingest` 判 `duplicate`、**一条条款都不解析**。
    """
    synthetic_parser(REAL_BLOCKS)
    src = tmp_path / "src"
    src.mkdir()
    _write_pdf(src / "a.pdf", "GB/T 90107-2020")
    batch = bulk.create_bulk_batch(str(src), batch_size=10)
    scan = bulk.fast_scan(batch["batch_id"], batch_size=10)
    item = scan["checkpoint"]["queue"][0]
    placeholder = item["doc_id"]
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?",
                      (placeholder,)).fetchone()[0] == 1

    out = bulk.resume_batch(batch["batch_id"], daily_budget=5)
    assert out["status"] == "done", out
    assert out["checkpoint"]["parsed"] == 1
    # 占位行被真文档**替换**掉了（reingest 语义：新开 doc_id、删旧行）
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?",
                      (placeholder,)).fetchone()[0] == 0
    # ⚠ 认"新文档"必须靠**这一个标准号**，不能 `SELECT doc_id FROM doc_meta` 取第一行 ——
    #   这是**会话级**临时库，别的用例文件早就插了别的文档（本批实测：单跑绿，
    #   与 `test_kb_folder_api` 一起跑就红在"取到别人的行 ⇒ 状态为 None"）。
    row = db.execute("SELECT doc_id FROM doc_meta WHERE standard_no=?",
                     (item["standard_no"],)).fetchone()
    assert row is not None, f"重导后库里没有 {item['standard_no']} 这一行"
    new_doc = row[0]
    n = db.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?",
                   (new_doc,)).fetchone()[0]
    assert n > 0, "批量导入报 parsed 却一条条款都没入库（占位行撞了自己的 file_hash）"
    st = fs.get_filing_state(new_doc)
    assert st is not None and st["stage"] == "confirming", st


def test_bulk_import_batch_flag_is_declared_and_default_false(db, tmp_path):
    """批次开关：`create_bulk_batch(..., reingest=True)` 落在 checkpoint 里；默认是 False。"""
    src = tmp_path / "src2"
    src.mkdir()
    _write_pdf(src / "b.pdf", "GB/T 90108-2020")
    b1 = bulk.create_bulk_batch(str(src))
    assert b1["checkpoint"]["reingest"] is False
    bulk.abort_batch(b1["batch_id"])
    b2 = bulk.create_bulk_batch(str(src), reingest=True)
    assert b2["checkpoint"]["reingest"] is True
    bulk.abort_batch(b2["batch_id"])


def test_bulk_endpoint_passes_force_and_reingest(client, db, tmp_path, monkeypatch):
    """接口层：`POST /ingest/bulk` 的 `reingest` / `force` 都要真的传下去（两个名字同义）。"""
    from _kb_folder_api_fixtures import api, data_of
    c, token = client
    seen: list[dict] = []
    real = bulk.create_bulk_batch

    def spy(src_dir, batch_size=bulk.DEFAULT_BATCH_SIZE, reingest=False):
        seen.append({"reingest": reingest})
        return real(src_dir, batch_size, reingest=reingest)

    monkeypatch.setattr(bulk, "create_bulk_batch", spy)
    src = tmp_path / "src3"
    src.mkdir()
    _write_pdf(src / "c.pdf", "GB/T 90109-2020")
    # 后台线程会跑 fast_scan ⇒ 起完就中止，别让它真解析（本轮不验解析）
    for payload in ({"src_dir": str(src), "force": True},
                    {"src_dir": str(src), "reingest": True}):
        data = data_of(api(c, token, "post", "/api/v1/ingest/bulk", json=payload))
        bulk.abort_batch(data["batch_id"])
        time.sleep(0.2)
    assert [s["reingest"] for s in seen][:2] == [True, True], seen


# ═════════════════════ 5. 目录选择器用的扁平清单 + 标签端点 ═════════════════════

def test_flat_folders_supports_search_and_depth(client, tops, std_tree):
    """`GET /kb/folders/flat`：整棵树带路径、可按名字/路径搜、`depth` 是路径段数。"""
    from _kb_folder_api_fixtures import api, data_of
    c, token = client
    allf = data_of(api(c, token, "get", "/api/v1/kb/folders/flat"))
    assert allf["total"] >= 5
    by_path = {f["path"]: f for f in allf["items"]}
    want = " › ".join(("标准", "P 土木、建筑", "P15/19 工程抗震、工程防火、人防工程", "P16 工程防火"))
    assert want in by_path, list(by_path)[:5]
    assert by_path[want]["folder_id"] == std_tree["P16 工程防火"]
    assert by_path[want]["depth"] == 4
    # 按名字/路径过滤
    hit = data_of(api(c, token, "get", "/api/v1/kb/folders/flat", params={"q": "P16"}))
    assert hit["total"] == 1 and hit["items"][0]["path"] == want
    miss = data_of(api(c, token, "get", "/api/v1/kb/folders/flat", params={"q": "不存在的目录名"}))
    assert miss["total"] == 0 and miss["items"] == []


def test_stage_labels_endpoint_is_the_single_owner(client):
    """标签由**接口**下发（界面上那份镜像不再是唯一所有者）。"""
    from _kb_folder_api_fixtures import api, data_of
    c, token = client
    data = data_of(api(c, token, "get", "/api/v1/kb/stage-labels"))
    assert data["labels"] == dict(fs.STAGE_LABELS)
    assert data["labels"]["failed"] == "识别失败"
    assert data["unfiled"] == list(fs.UNFILED_STAGES)


def test_failure_kind_vocabulary_matches_the_migration_script():
    """失败原因的**中文字面量**只有一个所有者：迁移脚本那份必须与 `folder_store` 逐字相同。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "apply_folder_filing_probe",
        Path(__file__).resolve().parents[1] / "scripts" / "apply-folder-filing.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.FAILURE_KIND_ZERO_CLAUSES == fs.FAILURE_KIND_ZERO_CLAUSES


def test_inbox_payload_carries_new_suggestion_fields(client, db, tops, std_tree):
    """「待分类」每一项都带 `stage_label` / `suggest_new_parent_id` / `suggest_new_name` / `catalog_hidden`。

    兜底桶（认不出）那篇：两个"新建"字段必须都是 **null** —— 界面上就是靠它决定
    **不渲染**「接受建议 / 在建议位置新建」（死按钮按下去会 422）。
    """
    from _kb_folder_api_fixtures import api, data_of, mkdoc_full
    c, token = client
    d = mkdoc_full(db, "inbox_fields_1", standard_no="GB/T 91999-2020", tags=[])
    rows = _inbox_rows(api, c, token)
    assert d in rows
    r = rows[d]
    for key in ("stage", "stage_label", "confidence", "failure_kind", "suggested_folder_id",
                "suggested_path", "suggest_new_parent_id", "suggest_new_name", "catalog_hidden"):
        assert key in r, key
    assert r["stage_label"] == "排队中"
    assert r["suggested_folder_id"] is None
    assert r["suggest_new_parent_id"] is None and r["suggest_new_name"] is None


def test_inbox_suggest_new_names_the_missing_segment(client, db, tops):
    """分类口径比命中的现有目录**更深** ⇒ 给出"在 XXX 下新建 XXX"的两个真值。

    ⚠ 用 **A 那一支**（CCS:A00/09），因为整个测试会话里没有别的用例碰它
    （P 那一支会被 `std_tree` 夹具建全 ⇒ 在 P 上判"缺哪一段"是**顺序相关**的，
    本批第一版就是这么假红的：树里有 L4 时建议直接命中 L4，`suggest_new_name` 自然是 null）。
    """
    from _kb_folder_api_fixtures import api, ensure_folder_path, mkdoc_full
    c, token = client
    # 只建到 L2（L3/L4 谁都没建过）⇒ 缺的那一段就是建议新建的名字
    made = ensure_folder_path(("标准", "A 综合"))
    d = mkdoc_full(db, "inbox_newseg_1", standard_no="GB/T 92000-2020",
                   tags=["CCS:A00/09 标准化管理与一般规定"])
    rows = _inbox_rows(api, c, token)
    r = rows[d]
    assert r["suggested_folder_id"] == made["A 综合"], r
    assert r["suggest_new_parent_id"] == made["A 综合"]
    assert r["suggest_new_name"] == "A00/09 标准化管理与一般规定", r
    # 反向（三档单调）：补齐一层 ⇒ 建议跟着**下探一层**，且"缺的那一段"换人；
    # 补到最深 ⇒ 没有可新建的了（两个字段都回 null）。这条钉住"建议 = 现有目录里最深的一层"。
    l3 = ensure_folder_path(("标准", "A 综合", "A00/09 标准化管理与一般规定"))[
        "A00/09 标准化管理与一般规定"]
    rows2 = _inbox_rows(api, c, token)
    assert rows2[d]["suggested_folder_id"] == l3, rows2[d]
    assert rows2[d]["suggest_new_name"] == "A00 /09 标准化管理与一般规定", rows2[d]
    l4 = ensure_folder_path(("标准", "A 综合", "A00/09 标准化管理与一般规定",
                             "A00 /09 标准化管理与一般规定"))["A00 /09 标准化管理与一般规定"]
    rows3 = _inbox_rows(api, c, token)
    assert rows3[d]["suggested_folder_id"] == l4
    assert rows3[d]["suggest_new_parent_id"] is None and rows3[d]["suggest_new_name"] is None


def test_inbox_hidden_but_failed_doc_is_listed(db, client):
    """`catalog_hidden=1` 且 `stage='failed'` 的那一篇**必须**在列表里（§十七的硬要求）。"""
    from _kb_folder_api_fixtures import api, data_of, mkdoc_full
    c, token = client
    d = mkdoc_full(db, "hidden_failed_1", standard_no="GB/T 92100-2020")
    db.execute("UPDATE doc_meta SET catalog_hidden=1 WHERE doc_id=?", (d,))
    db.commit()
    fs.set_filing_state(d, "failed", failure_kind=fs.FAILURE_KIND_ZERO_CLAUSES)
    rows = _inbox_rows(api, c, token)
    assert d in rows
    assert rows[d]["catalog_hidden"] == 1
    assert rows[d]["failure_kind"] == fs.FAILURE_KIND_ZERO_CLAUSES
    # 反向：同一篇如果是**已归位**，即使 catalog_hidden=1 也不该出现在「待分类」里
    fs.set_filing_state(d, "filed")
    rows2 = set(_inbox_rows(api, c, token))
    assert d not in rows2
    # 收尾：把这篇的隐藏标记还原（session 级临时库，别影响别的用例）
    db.execute("UPDATE doc_meta SET catalog_hidden=0 WHERE doc_id=?", (d,))
    db.commit()


def test_reingest_busy_is_409_not_a_queue(client, db, monkeypatch):
    """同一时刻只跑一批：锁被占 ⇒ **409 `reingest_busy`**（不许"排队等"）。"""
    from _kb_folder_api_fixtures import api, error_code
    c, token = client
    from src.core.ingestion import reingest as reingest_mod
    held = reingest_mod._LOCK.acquire(blocking=False)
    assert held
    try:
        st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/reingest",
                                  json={"doc_ids": ["doc_whatever"]}))
        assert (st, code) == (409, "reingest_busy")
    finally:
        reingest_mod._LOCK.release()


def test_reingest_rejects_too_many_docs(client):
    """边界：一次点太多 ⇒ 422（后台线程是串行的，防"手一抖选 379 篇"）。"""
    from _kb_folder_api_fixtures import api, error_code
    from src.core.ingestion.reingest import MAX_REINGEST_DOCS
    c, token = client
    st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/reingest",
                              json={"doc_ids": [f"doc_x{i}" for i in range(MAX_REINGEST_DOCS + 1)]}))
    assert (st, code) == (422, "invalid_decision")


def test_reingest_plan_is_read_only(db, tmp_path):
    """`plan_reingest` 是**只读**的：它不许写状态、不许动库。"""
    from src.core.ingestion import reingest as reingest_mod
    pdf = _write_pdf(tmp_path / "plan.pdf", "GB/T 90110-2020")
    from _kb_folder_api_fixtures import mkdoc_full
    d = mkdoc_full(db, "plan_doc_1", standard_no="GB/T 92200-2020")
    db.execute("UPDATE doc_meta SET file_path=?, file_hash='h-plan' WHERE doc_id=?",
               (str(pdf), d))
    db.commit()
    before = fs.get_filing_state(d)
    plan = reingest_mod.plan_reingest([d])
    assert [r["doc_id"] for r in plan["ready"]] == [d]
    assert fs.get_filing_state(d) == before, "plan_reingest 只读，不许写状态"


def test_json_marker_file_path_is_skipped_honestly(db):
    """快扫/异常行的 `file_path` 是标记 JSON ⇒ 如实跳过（不许拿它去 open）。"""
    from _kb_folder_api_fixtures import mkdoc_full
    from src.core.ingestion import reingest as reingest_mod
    d = mkdoc_full(db, "marker_doc_1", standard_no="GB/T 92300-2020")
    db.execute("UPDATE doc_meta SET file_path=? WHERE doc_id=?",
               (json.dumps({"bulk_import": "pending_parse"}), d))
    db.commit()
    plan = reingest_mod.plan_reingest([d])
    assert plan["ready"] == [] and len(plan["skipped"]) == 1
    assert "没有可用的源文件路径" in plan["skipped"][0]["reason"]
