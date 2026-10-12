"""spec 011 更新通道系统三个断点的回归判据。

## 抓什么

本特性**不新建能力**，只把三处「已建成但没接线」接上生产。三组判据各自有牙：

| 组 | 抓什么 | 变异（必须变红） |
|---|---|---|
| **①** 自动巡检 | `server.run()` 真调用 + 幂等 + **建批后真的执行** | 调用换 `pass` / 去掉执行 |
| **②** 补 CCS | 入库后带 `CCS:` 标签 + 查不到不阻塞 + 同一所有者 | 删调用 / 查不到就抛 |
| **③** 下载前弹框 | 判定 `new_version` **不自动下载** + 同意才下 + 非 PDF 拒收 | 改成直接下 / 去掉魔数校验 |

## ⚠ 为什么第 ③ 组的 C1 是**反向断言**

`docs/NOT-DOING.md` 第 20 条写死「**不许**演化成"自动下载"或"默认同意"」。
⇒ 判据必须钉住"**没有**自动下载"，而不是"下载成功了"。
一个"下载成功"的断言**无法区分**合规实现与违规实现 —— 那是假绿。
"""
import ast
import inspect

import pytest


# ══════════════════════════════════════════════════════════════════════════
# Phase ① 自动巡检
# ══════════════════════════════════════════════════════════════════════════

class Test自动巡检已接线:
    """A1：`server.run()` 必须**真的调用**启动函数（不是只 import）。

    为什么用 AST 而不是 `in` 字符串：`run()` 里那行
    `from ... import start_update_scheduler` **本身就含这个字符串** ⇒
    把调用换成 `pass` 时字符串断言**照样绿**（假绿）。
    这个坑 `test_law_catalog_refresh.py` 实测踩过（它自己的注释写着）。
    """

    def test_run_真的调用_start_update_scheduler(self):
        from src.core.api import server
        tree = ast.parse(inspect.getsource(server.run))
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        assert "start_update_scheduler" in called, \
            "run() 没有真正调用 start_update_scheduler（只 import 不算）"

    def test_run_真的调用_stop_update_scheduler(self):
        from src.core.api import server
        tree = ast.parse(inspect.getsource(server.run))
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        assert "stop_update_scheduler" in called, \
            "run() 没有真正调用 stop_update_scheduler（关停路径缺）"

    def test_启动失败不阻塞引擎(self):
        """`start_update_scheduler()` 必须在 try/except 里 —— 线程起不来不该让引擎起不来。"""
        from src.core.api import server
        src = inspect.getsource(server.run)
        i = src.find("start_update_scheduler")
        assert i > 0
        # 它前面最近的 try 与后面最近的 except 之间不该被别的 try 隔开
        head = src[:i]
        assert head.rfind("try:") > head.rfind("except"), \
            "start_update_scheduler() 不在 try 块里"


class Test调度器幂等与生命周期:
    """A2：重复 start 不起第二个线程；stop 后能干净重启。

    ⚠ **为什么要注入替身调度器**：真实 `UpdateScheduler.tick()` 会**查数据库**。
    全量测试里 DB 被别处占着时 `tick()` 会阻塞 ⇒ `stop()` 的 `join(5s)` 超时
    ⇒ `stop` 返回 False ⇒ 生命周期判据**假红**（2026-10-12 实测踩到，11 分钟
    全量跑里这 2 条红、单跑绿）。
    ⇒ 用 `set_scheduler_factory` 换一个**不碰库**的替身，判据才只测"线程生命周期"
    这一件事。
    """

    @pytest.fixture(autouse=True)
    def _no_db_scheduler(self):
        """替身调度器：tick 立刻返回空，不碰数据库。"""
        from src.core.update import scheduler_runner as sr

        class _FakeSched:
            def tick(self, now=None):
                return {"created": [], "resumed": []}

        sr.set_scheduler_factory(_FakeSched)
        yield
        sr.stop_update_scheduler()
        sr.reset_scheduler_factory()

    def test_重复_start_只起一个线程(self):
        from src.core.update import scheduler_runner as sr
        first = sr.start_update_scheduler(poll_interval=60.0)
        second = sr.start_update_scheduler(poll_interval=60.0)
        assert first is True, "第一次 start 应返回 True（新起了线程）"
        assert second is False, "第二次 start 应返回 False（已在跑，不动）"
        assert sr.is_running() is True

    def test_stop_后_is_running_为假(self):
        from src.core.update import scheduler_runner as sr
        sr.start_update_scheduler(poll_interval=60.0)
        ok = sr.stop_update_scheduler()
        assert ok is True, "join 成功应返回 True"
        assert sr.is_running() is False

    def test_未跑时_stop_幂等(self):
        from src.core.update import scheduler_runner as sr
        sr.stop_update_scheduler()          # 确保停
        assert sr.stop_update_scheduler() is True, "未在跑时 stop 应幂等返回 True"

    def test_stop_后能再_start(self):
        from src.core.update import scheduler_runner as sr
        sr.start_update_scheduler(poll_interval=60.0)
        sr.stop_update_scheduler()
        assert sr.start_update_scheduler(poll_interval=60.0) is True, \
            "stop 后应能再起（引用被正确清理）"


class Test建批后真的执行:
    """A3：**这是本特性修的核心缺口** —— `tick()` 只建批不跑。"""

    def test_tick_and_run_会执行建出来的批(self, monkeypatch):
        """注入假 tick：返回一个"建了"的批 ⇒ 必须去跑它。"""
        from src.core.update import scheduler_runner as sr
        from src.core.update import inspector

        ran: list[str] = []

        class FakeSched:
            def tick(self, now=None):
                return {"created": ["bulk_fake_1"], "resumed": []}

        def fake_run_batch(bid, *a, **kw):
            ran.append(bid)
            return {"status": "done"}

        monkeypatch.setattr(inspector, "run_batch", fake_run_batch)
        out = sr.tick_and_run(FakeSched())
        assert ran == ["bulk_fake_1"], "建出来的批没有被执行（这正是断点一的缺口）"
        assert out["ran"][0]["ok"] is True

    def test_没建批时不去跑(self, monkeypatch):
        from src.core.update import scheduler_runner as sr
        from src.core.update import inspector

        called = []
        monkeypatch.setattr(inspector, "run_batch",
                            lambda *a, **kw: called.append(1) or {"status": "done"})

        class FakeSched:
            def tick(self, now=None):
                return {"created": [], "resumed": []}

        out = sr.tick_and_run(FakeSched())
        assert called == [], "没建批却去跑了（空跑）"
        assert out["ran"] == []

    def test_单批失败不拖累其余批(self, monkeypatch):
        from src.core.update import scheduler_runner as sr
        from src.core.update import inspector

        seen = []

        def flaky(bid, *a, **kw):
            seen.append(bid)
            if bid == "bad":
                raise RuntimeError("boom")
            return {"status": "done"}

        monkeypatch.setattr(inspector, "run_batch", flaky)

        class FakeSched:
            def tick(self, now=None):
                return {"created": ["bad", "good"], "resumed": []}

        out = sr.tick_and_run(FakeSched())
        assert seen == ["bad", "good"], "第一批判失败后没继续跑后面的"
        assert [r["ok"] for r in out["ran"]] == [False, True]


class Test调度开关:
    """A4/A5：未到期不建批；`schedule_days=0` 关闭。

    ⚠ 这两条**只验"接线没有绕过 scheduler 自己的开关"** ——
    真正的编排语义（到期判断 / 建几个 tier）由 `scheduler.py` 自己的测试负责，
    本特性**没改它**（spec 的假设 1）。
    """

    def test_关闭时_tick_不建批(self, monkeypatch):
        """`schedule_days()` 返回 0（关闭）⇒ `_create_scheduled_batches` 直接返回空。

        直接调内部函数并 monkeypatch `schedule_days`，**不碰数据库**
        （第一版直接 `s.tick()` 会真查库，在隔离环境下拿不到连接 ⇒ 假红）。
        """
        from src.core.update import scheduler as sch
        monkeypatch.setattr(sch, "schedule_days", lambda: 0)
        s = sch.UpdateScheduler()
        from datetime import datetime, timezone
        created = s._create_scheduled_batches(datetime.now(timezone.utc))
        assert created == [], "schedule_days=0 时应关闭调度，不该建批"

    def test_接线没有绕过_scheduler_的_tick(self):
        """结构判据：`tick_and_run` 必须**调 `tick()`**，不许自己另写建批逻辑。"""
        import ast
        import inspect as _inspect
        from src.core.update import scheduler_runner as sr
        tree = ast.parse(_inspect.getsource(sr))
        called = {n.func.attr for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        assert "tick" in called, \
            "tick_and_run 没调 scheduler 的 tick() ⇒ 绕过了它的编排语义"


# ══════════════════════════════════════════════════════════════════════════
# Phase ② 通道入库补 CCS
# ══════════════════════════════════════════════════════════════════════════

class Test入库补CCS:
    """B1/B2：入库后带 `CCS:` 标签；查不到不阻塞。"""

    def test_标准入库会查_CCS_并写标签(self, monkeypatch):
        """判据：`ingest_law_text` 对 standard 类型会调 `resolve_ccs`。"""
        import ast
        import inspect as _inspect
        from src.core.ingestion import law_text
        src = _inspect.getsource(law_text)
        tree = ast.parse(src)
        # 必须**真的调用** resolve_ccs（不是只 import）
        called = {n.func.id for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "resolve_ccs" in called, \
            "ingest_law_text 没有调用 resolve_ccs ⇒ 通道入库的文档不会有 CCS 标签"

    def test_与_pipeline_同一所有者(self):
        """B4：CCS 判据**只有一个所有者**（`ccs_fetcher`），不许另写一份解析。"""
        import ast
        import inspect as _inspect
        from src.core.ingestion import law_text
        src = _inspect.getsource(law_text)
        assert "from src.core.knowledge.ccs_fetcher import" in src, \
            "必须从 ccs_fetcher 导入（判据唯一所有者）"
        # 不许自己写 CCS 正则（另起一份解析）
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and "CCS" in t.id.upper() and "RE" in t.id.upper():
                        raise AssertionError(
                            f"law_text 里另写了一份 CCS 正则（{t.id}）⇒ 判据分叉")

    def test_查不到_CCS_不阻塞入库(self, monkeypatch):
        """B2：`resolve_ccs` 抛异常/返回 None 时，入库**必须仍成功**。

        ⚠ 判据用 **AST** 而不是"往前找 `try:` 字符串" ——
        后者会被**模块 docstring 里的 `try:` 字样**骗到（第一版就是这么错的：
        `rfind` 找到 -1，因为那段注释在调用之前但不在同一函数里）。
        AST 能准确回答"这个调用是不是包在 try 块里"。
        """
        import ast
        import inspect as _inspect
        from src.core.ingestion import law_text

        tree = ast.parse(_inspect.getsource(law_text))
        # 找所有 try 块体里的调用名
        protected: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    protected.add(sub.func.id)
        assert "resolve_ccs" in protected, \
            "resolve_ccs 不在任何 try 块里 ⇒ CCS 查询失败会阻塞入库"


# ══════════════════════════════════════════════════════════════════════════
# Phase ③ 下载前弹框（碰安全面）
# ══════════════════════════════════════════════════════════════════════════

class Test绝不自动下载:
    """C1：**反向断言** —— 判定 `new_version` 后不许有文件被下载。

    ⚠ 为什么是反向断言：NOT-DOING 第 20 条禁止"自动下载"。
    一个"下载成功"的正向断言**无法区分**合规与违规实现。
    """

    def test_巡检代码里没有自动下载调用(self):
        """`inspector.py`（巡检执行体）里不许直接调 `archive_pdf`。"""
        import inspect as _inspect
        from src.core.update import inspector
        src = _inspect.getsource(inspector)
        assert "archive_pdf" not in src, \
            "inspector 里直接调了 archive_pdf ⇒ 自动下载（违反 NOT-DOING 第 20 条）"

    def test_判定_new_version_不触发下载(self):
        """结构判据：`new_version` 分支里不许出现下载动作。"""
        import inspect as _inspect
        from src.core.update import inspector
        src = _inspect.getsource(inspector)
        i = src.find("new_version")
        assert i > 0, "没找到 new_version 判定"
        # 取该判定附近的一段，确认没有下载
        window = src[max(0, i - 300):i + 300]
        assert "archive_pdf" not in window, "new_version 判定附近出现了下载调用"


class Test下载走审批门:
    """C2/C3：同意才下、拒绝不下。"""

    def test_审批门问句说清来源与形态(self):
        """FR-010：问句必须含"来源 + 形态"（业主口径：不让用户读全文）。"""
        from src.core.update import download_gate
        ask = download_gate.download_ask_reason(
            {"standard_no": "GB/T 50493-2019",
             "title": "石油化工可燃气体和有毒气体检测报警设计标准",
             "evidence_url": "https://www.gov.cn/x.pdf"})
        assert "GB/T 50493-2019" in ask, "问句没写清要下的是哪一份"
        assert "gov.cn" in ask, "问句没写清来源"
        assert "PDF" in ask or "pdf" in ask, "问句没写清形态"

    def test_拒绝则不下载(self, monkeypatch):
        from src.core.update import download_gate
        called = []
        monkeypatch.setattr(download_gate, "_do_download",
                            lambda *a, **kw: called.append(1) or {"ok": True})
        out = download_gate.handle_download(change={"standard_no": "GB 1-2020"},
                                            approved=False)
        assert called == [], "用户拒绝后仍去下载了"
        assert out["downloaded"] is False
        assert out.get("reason"), "拒绝必须如实给理由，不许静默"

    def test_同意则下载(self, monkeypatch):
        from src.core.update import download_gate
        called = []
        monkeypatch.setattr(download_gate, "_do_download",
                            lambda *a, **kw: called.append(1) or {"ok": True, "path": "/x.pdf"})
        out = download_gate.handle_download(change={"standard_no": "GB 1-2020"},
                                            approved=True)
        assert called == [1], "用户同意后没去下载"
        assert out["downloaded"] is True


class Test下载校验非PDF:
    """C4：站点返回 HTML 错误页时必须拒收（复用 archive_pdf 的 `%PDF` 校验）。"""

    def test_archive_pdf_校验_PDF_魔数(self):
        """**复用**既有校验，不另写一份 —— 结构判据。"""
        import inspect as _inspect
        from src.core.update.channels import govcn_announce
        src = _inspect.getsource(govcn_announce)
        assert b"%PDF" in src.encode("utf-8") or "%PDF" in src, \
            "archive_pdf 里没有 %PDF 魔数校验"
        assert "len(content) > 1024" in src, "archive_pdf 里没有大小校验"

    def test_download_gate_不另写校验(self):
        """C4b：download_gate **不许**自己写一份 `%PDF` 校验（判据分叉）。"""
        from src.core.update import download_gate
        src = inspect.getsource(download_gate)
        assert "startswith(b\"%PDF\")" not in src and "[:4] == b\"%PDF\"" not in src, \
            "download_gate 里另写了一份 %PDF 校验 ⇒ 判据分叉（应复用 archive_pdf）"
