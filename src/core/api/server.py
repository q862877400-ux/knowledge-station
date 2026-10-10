"""FastAPI 服务组装（全量路由）：随机端口 + token 鉴权 + /health + SSE 流式 + 证据/补丁/更新 API。"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
import weakref
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse

from src.core.config import get_settings
from src.core.knowledge.legal_status import resolve_status
from src.core.storage.sqlite_db import init_schema, get_db_connection

_STARTED_AT = time.monotonic()

#: 线程池**上限**（anyio 默认 40，这里显式收窄）。
#:
#: 为什么（独立复核 b13 的 MEDIUM-1，2026-09-18）：§10.71–§10.80 把一批**同步重活**从
#: "在事件循环里跑"改成"在线程池里跑"。改前这些活的**并发度天然是 1**（都在事件循环里排队），
#: 改后它们可以**同时开满 anyio 的默认令牌数 40** —— 40 个 MinerU 解析子进程 / 40 份 PDF 渲染
#: 同时来。那是**改动前不存在的形态**，而且吃掉的是**内存与 CPU**（不是延迟）。
#: 复核实测（进程内 ASGI，受害者是真实的 `def` 端点 `/ingest/preview/inbox`）：
#: 无载入 0.0105s → 39 条慢活在飞 0.0014s（不受影响）→ **40 条 0.6595s**（池满后开始排队）。
#:
#: 取 16 的理由：单用户桌面场景同时发起的重活很少超过个位数；16 既掐掉"40 个子进程"的风暴，
#: 又给**文件流式读取**（`FileResponse` 也吃这口池子）留了余量。
#: ⚠ **取舍（诚实登记）**：池子更小 ⇒ "若干条长解析在飞时加载 PDF"会排队。真要同时治好两头，
#: 得给**最长的那几条**挂**专用** `CapacityLimiter`（留出一条"文件流"专用位），见 §10.81 §5。
#: ⚠ **§10.86 之后这个常量的地位变了**（独立复核 b16 的 INFO-2）：那一步把 **51 条**廉价端点
#: （原来是 `async def`、在事件循环里跑）也搬进了这个池，全库 141 条同步端点共享它。
#: 也就是说 —— **"池子有界"从一条性能纪律，变成了 §10.86 那个收益的前提**：
#: 把它调大（尤其调回 anyio 默认的 40）等于**同时取消 §10.86 的收益**（"整类端点在事件循环
#: 里等锁"会换成"整类端点在无界池里并发等锁"）。改这个数字前请先读 §10.81/§10.86。
#: ⚠ `asyncio.to_thread(...)` 走的是 **asyncio 的默认执行器**（`min(32, cpu+4)` 个 worker），
#: **不是**这口 anyio 池 ⇒ **不受**本常量约束、也不吃重活闸门的令牌。
#: §10.93 之前 `/laws/*` 那 5 条正是这么写的（"看着已经让出事件循环，其实换了一口无界的池"）；
#: 现在那 5 条已改回 `def`，**全库 `asyncio.to_thread` 零使用**，并由
#: `tests/test_material_api.py::test_端点上不许用_asyncio_to_thread` 静态钉住
#: （`tests/test_threadpool_bound.py::test_asyncio_to_thread_绕过_anyio_闸门` 是它的理由）。
THREADPOOL_TOKENS = 16

#: **按事件循环**记录"线程池已收窄"（§10.88 修 b17 的 MEDIUM-1）。
#: ⚠ 为什么不能用一个**进程级布尔**：anyio 的 `current_default_thread_limiter()` 是 **RunVar**
#: （**按事件循环**），而 `bound_threadpool_once()` 是每请求调一次。b17 实测：进程级标记置位后，
#: **第二个事件循环**里 `total_tokens` 仍是 anyio 默认的 **40** ⇒ "池子有界"从第二个循环起
#: **静默失效**（生产只有一条长驻循环，所以现网没暴露；但测试/嵌入式多循环会）。
#: 键用**循环对象**（`WeakKeyDictionary`，弱引用）——与 `_get_heavy_limiter()` 同款（b14 的 LOW-4）。
_bound_loops: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def bound_threadpool_once() -> None:
    """把 anyio 默认线程池收窄到 `THREADPOOL_TOKENS`（**按事件循环幂等**；只能在循环里调用）。

    ⚠ anyio 的 limiter 是 **RunVar**：事件循环外读写会抛 `NoEventLoopError`（实测 anyio 4.14）。
    所以它挂在**已有的 HTTP 中间件**里（每请求一次、幂等、跑在循环内）——而不是
    `create_app()`（那是同步上下文，且 `httpx.ASGITransport` 默认**不跑 lifespan**，
    挂 lifespan 会让量具与真实路径行为不一致）。
    ⚠ **幂等的粒度是"每事件循环"**（§10.88）：`_bound_loops` 按循环缓存，第二个循环会**再收窄一次**。
    """
    try:
        import anyio.to_thread
        loop = asyncio.get_running_loop()
        if _bound_loops.get(loop) is True:
            return
        anyio.to_thread.current_default_thread_limiter().total_tokens = THREADPOOL_TOKENS
        _bound_loops[loop] = True
    except Exception:      # noqa: BLE001 — 拿不到 limiter 不该让请求失败；下一次请求还会再试
        pass


#: **重活专用闸门**的令牌数（§10.82）。
#:
#: 为什么在"线程池 16"之外还要再来一层：§10.81 那把全局上限治的是"40 子进程风暴"，但它把
#: **长活**与**文件流式读取**（`FileResponse`，也吃同一口池子）放在一个队里——
#: 16 条长解析在飞时，加载一份 PDF 就得排队（最长可等到一条 135s 的预览跑完）。
#: 这一层把两类活分开：**重活最多 4 条**，其余 12 个线程留给文件流与廉价 DB 操作；
#: 排队发生在**中间件里 `await`**（异步等，**不占线程**），所以"等"本身不消耗任何池子额度。
#: 4 的取法：单用户桌面场景同时发起的重活通常 1–2 条；4 足够容纳"批量预览 + 顺手看一眼图"，
#: 又把最坏情况的子进程数压到 4。
HEAVY_TOKENS = 4

#: **重活路径**（前缀匹配，唯一所有者在这一处）。判据是"这条端点会解析 PDF / 渲染图 /
#: 逐点调 LLM / 打整包 / 逐份 sha256"，即 §10.71–§10.80 里那些被量出"秒级到分钟级"的活。
HEAVY_PREFIXES: tuple[str, ...] = (
    "/api/v1/ingest/preview",                 # 单文件/批量/异步预览（最长可达分钟级）
    "/api/v1/ingest/bulk",                    # 全量入库
    "/api/v1/documents/",                     # figure/formula/table-image/tree/assets（渲染/读盘）
    "/api/v1/materials/projects/",            # scan / collect / locators（子进程解析 + 逐份 sha256）
    "/api/v1/materials/",                     # reverify / locators（同上）
    "/api/v1/report/",                        # 效力报告聚合 / 研究报告（落盘 + 逐份 sha256）
    "/api/v1/export/",                        # xlsx/JSON 落盘 + 引用块取证据
    "/api/v1/snapshots",                      # 造/恢复快照（打整包 + sha256）
    "/api/v1/ks/answer",                      # 取证答案（引擎侧推理，120s 契约）
    "/api/v1/batch/qa",                       # 批量问答
    "/api/v1/vision/locate",                  # 视觉定位（模型 + 渲染）
    "/api/v1/aliases/extract",                # 术语抽取（全库拼接）
    "/api/v1/data/package/",                  # 数据包导出/导入
    "/api/v1/update/report",                  # 更新检查结果 xlsx（openpyxl 落盘）
    # ---- §10.93：`/laws/*` 里**真的会打网络/长跑**的那 5 条 ----
    # 它们原先写成 `async def` + `await asyncio.to_thread(...)` ⇒ 既绕过本表，
    # 又绕过"线程池 16"（走 asyncio 默认执行器）。改回 `def` 之后回到有界的池子，
    # 因此也必须吃重活令牌：`/laws/catalog/refresh` 是分钟级全量爬取、`/laws/ingest`
    # 要下载+转 PDF+走入库管线，`/laws/search`、`/laws/check-updates`、`/laws/verify`
    # 是逐次网络请求（秒级）。
    # ⚠ **故意只列这 5 条，不用前缀 `/api/v1/laws/`**：同一个前缀下还有两条**廉价**端点——
    # `GET /laws/catalog`（本地一读 + 索引已就绪的快路径）与 `GET /laws/sources`（纯静态字典），
    # 把它们关在 4 个令牌后面就会重现 §10.82 那个"**闸门自己造排队**"的坑
    # （开法规目录要排在一条分钟级爬取后面）。这里用**逐条列出**而不是"前缀 + SKIP"来表达：
    # `is_heavy_path` 是 `startswith`，加 `/api/v1/laws/` 再用 `/api/v1/laws/catalog` 去 SKIP
    # 会**连 `/laws/catalog/refresh` 一起豁免**（前缀包含关系），那是把重活放跑的经典错法。
    "/api/v1/laws/search",
    "/api/v1/laws/ingest",
    "/api/v1/laws/check-updates",
    "/api/v1/laws/catalog/refresh",
    "/api/v1/laws/verify",
    # 2026-09-24（独立复核 MED-3）：`/laws/compliance-guard` 会在**线程里打 2s 外网**
    #   （Jev API，带超时+熔断）。它原先没进本表 ⇒ 每条用户消息都可能占住 16 个
    #   线程池令牌之一（4 个并发就够把池子占满）⇒ 其他端点跟着排队。
    #   与上面 5 条同类（"真的会打网络/长跑"），所以逐条列出而不是加 `/laws/` 前缀。
    "/api/v1/laws/compliance-guard",
)

#: **按事件循环缓存**的重活闸门。⚠ 键用**循环对象本身**（`WeakKeyDictionary`），
#: **不用 `id(loop)`**（独立复核 b14 的 LOW-4）：`id()` 在旧循环被回收后**会被新循环复用**
#: （CPython 按地址分配），于是新循环可能拿到一个**绑在死循环上**的 limiter——anyio 的
#: `CapacityLimiter` 内部用 RunVar（只在创建它的循环上有效），表现是闸门行为诡异而**不是报错**。
#: 弱引用键同时避免 id 复用与"每个循环永久留在字典里"。
_heavy_limiters: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

#: **例外：前缀命中但其实是廉价活**的路径（**必须写理由**）。
#: `/ingest/preview/inbox` 只是列一下目录（毫秒级），把它关在 4 个令牌后面会让
#: "打开预览面板"排在 4 条长解析后面——那是**闸门自己造出来的**排队。
HEAVY_SKIP: tuple[str, ...] = (
    "/api/v1/ingest/preview/inbox",
)


def _get_heavy_limiter():
    """取**本事件循环**的重活闸门（按 loop 缓存：anyio 的 limiter 绑定后端/循环，
    测试里一个进程会开很多循环，全局单例会在第二个循环上出问题）。"""
    import anyio
    loop = asyncio.get_running_loop()
    lim = _heavy_limiters.get(loop)
    if lim is None:
        lim = anyio.CapacityLimiter(HEAVY_TOKENS)
        _heavy_limiters[loop] = lim
    return lim


def is_heavy_path(path: str) -> bool:
    if any(path.startswith(p) for p in HEAVY_SKIP):
        return False
    return any(path.startswith(p) for p in HEAVY_PREFIXES)


def warm_retrieval_stack() -> int:
    """把检索要用的**两件慢初始化**做掉（**必须在线程里调**，见 §10.94 的调用点）。

    ## 为什么需要它（实测，不是推断）
    `/api/v1/chat/completions` 是**唯一**剩下的 `async def` 端点（§10.93 之后），而它在进
    生成器之前要跑一遍**同步**检索。冷启动时那一段里有两次一次性慢初始化：

    | 事 | 实测耗时（`var/tmp/probe-chat-blocking.py`，本机） |
    |---|---|
    | fastembed 下载/加载 `BAAI/bge-small-zh-v1.5`（"Fetching 5 files"） | ≈ **5.2s** |
    | jieba 建前缀词典 | ≈ **0.33s** |
    | **合计：事件循环被占** | **6.79s**（`max_gap_s`） |

    这两件事**本该只发生一次**——问题不在"一次"，在**发生的位置**：`def` 端点（如
    `/api/v1/ks/answer`）天生跑在**线程池**里，所以它冷启动只是"这条请求慢"；
    而这条 `async def` 端点把同样的活放在**事件循环**里 ⇒ **启动后第一次提问会把整个引擎
    冻住 ≈7s**（期间连 `/health` 都不响应）。预热之后同一条链路的空档回到 **0.020s**
    （3×0.3s 的分块活照做，耗时 0.91s）。

    ## 为什么不是"在 lifespan 里预热"
    ① `httpx.ASGITransport` **不跑 lifespan**（量具与真实路径会不一致，§10.81 已经踩过）；
    ② 离线机器上启动会卡在一次下载超时；③ `/health` 必须廉价，启动变慢会牵动插件侧的
    就绪握手。**每请求调一次**是幂等的（`is_available()` 热态只读一个全局；jieba 自己认
    `dt.initialized`），热态代价是一次线程跳（实测 0.1–0.15ms，§10.87 的数字）。

    ## 失败怎么办
    **绝不影响请求**：`embedder.is_available()` 自己吞异常并进 60s 冷却（返回 False），
    jieba 那条也包起来。离线机器上最坏是"每 60s 有一次请求在线程里付一次网络超时"——
    与 `def` 端点今天的语义一致，且**不再冻事件循环**。

    返回**实际做过加载尝试的次数**（0 或 1）——给用例/探针一个可断言的返回值，
    而不是靠"没报错就算成了"。
    """
    tried = 0
    try:
        from src.core.retrieval import embedder
        if embedder.health() != "ok":        # 已加载 ⇒ 连 _get_model 都不进
            embedder.is_available()
            tried += 1
    except Exception:                        # noqa: BLE001 — 预热失败不该让请求失败
        pass
    try:
        from src.core.text_utils import segment_for_fts
        segment_for_fts("预热")               # jieba 词典（幂等；jieba 自己缓存）
    except Exception:                        # noqa: BLE001
        pass
    return tried


class _HeavyGateMiddleware:
    """重活专用闸门（**纯 ASGI**，不是 `BaseHTTPMiddleware`）。

    ⚠ **为什么必须是纯 ASGI**（独立复核 b14 的 MEDIUM-1，2026-09-18）：`@app.middleware("http")`
    走的是 starlette 的 `BaseHTTPMiddleware`，它的 `call_next` **只等到 `http.response.start`
    就返回**（base.py），响应体的流式发送发生在 `dispatch_func` **之后**——于是中间件里的
    `finally: release()` 会在**响应体开流之前**跑完，**流式（SSE）重活的令牌立刻被放掉**，
    闸门对它等于不存在。复核实测：12 条并发**非流式**重活峰值恰为 **4**，
    12 条并发**流式**重活峰值 **12**；等量工作的受害者放大比 非流式 ×0.5–1.2 / 流式 **×477–483**。
    而 `HEAVY_PREFIXES` 里的 `/compliance/review/{id}/execute`（逐点 LLM 的 SSE）与
    `/ks/answer`（引擎侧生成器）**正是这个形状**——所以这是"自称已消除的饿死形状换个入口回来"。

    纯 ASGI 中间件的 `await self.app(...)` 会**一直等到响应体发完**（router 内部会
    `await response(scope, receive, send)`），`finally` 的释放时机因此正确；
    另外再在 `http.response.body` + `more_body=False` 时提前释放（正常路径更早、更精确）。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not is_heavy_path(str(scope.get("path") or "")):
            await self.app(scope, receive, send)
            return
        limiter = _get_heavy_limiter()
        await limiter.acquire()
        released = False

        async def _send(message):
            nonlocal released
            try:
                await send(message)
            finally:
                if (not released and message.get("type") == "http.response.body"
                        and not message.get("more_body", False)):
                    released = True
                    limiter.release()

        try:
            await self.app(scope, receive, _send)
        finally:
            if not released:
                released = True
                limiter.release()


# 2026-08-28 表题行（通用）："表1…"、"表B.1…(续)"——编号紧随表字才认定，
# "表面积"等普通词、动词开头的正文引用（"符合表1…"）都不匹配。
import re as _re_mod

_TBL_CAPTION_LINE = _re_mod.compile(r"^表\s*[A-Za-z]?\d+(?:\.\d+)*\s*\S")


def _clause_number_sort_key(clause_number: str) -> list:
    """条款号自然排序键："5.2.1" → [5,2,1]；非数字段（"前言N"/"附录A"）排最后。"""
    parts: list = []
    for seg in (clause_number or "").split("."):
        try:
            parts.append(int(seg))
        except ValueError:
            parts.append(10 ** 6)
    return parts


def create_app(token: str) -> FastAPI:
    app = FastAPI(title="KnowledgeStation Engine", version="0.1.0")
    init_schema()
    # ⚠ **追加列迁移必须在任何请求之前跑过一次**（2026-09-17 冷启动缺陷，§10.43）：
    # `schema.sql` 是 `CREATE TABLE IF NOT EXISTS`，而 **`catalog_hidden` 这一列不在其中**
    # （只由 clause_repo 的迁移添加）。此前那条迁移只挂在**写路径**上 ⇒
    # **全新库（一次都没入库过）**里这一列不存在，而读者照用：
    # `/api/v1/report/effect` 当场 500 `no such column: catalog_hidden`
    # （界面上「效力报告」第一眼就是服务器错误）。
    # ⚠ **措辞更正**（独立复核 b8 的 LOW-2）：这里原先写的是"三列"，
    # 实测 `figure_html` / `page_breaks` **从基线起就在 `schema.sql` 里**
    # （schema.sql:60 / :87）——真实缺口只有 `catalog_hidden` **一列**（影响 3 个端点）。
    # 放在这里 = 与 `init_schema()` 同一个时间点，任何请求都晚于它。**纯 ALTER**。
    from src.core.storage import clause_repo as _clause_repo
    _clause_repo.ensure_additive_columns()
    # 材料表自己的追加列由**它自己的所有者**补（同一时间点、同一理由）：
    # `derived_text_hash` / `parser_fingerprint`（引用锚点稳定性，方案 §12 未决第 5 条）。
    from src.core.storage import material_repo as _material_repo
    _material_repo.ensure_additive_columns()

    # DSH Web GUI（localhost，跨源访问本引擎）需要 CORS；引擎本身仅绑 127.0.0.1 + token。
    # （原注释写的是「开发期前端 vite localhost」——Electron/Vite 已在批 8 退役，
    #   CORS 本体按既有裁决保留：DSH web GUI 在 127.0.0.1:3080 跨源 fetch 引擎。）
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
        # 2026-09-02 需求2：截图原版比例头（X-Frac-*）跨源可读——
        # 引擎端口随机、DSH web GUI（3080）跨端口 fetch，自定义头默认不暴露
        expose_headers=["X-Frac-X0", "X-Frac-W", "X-Frac-H"])

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # ⚠ 线程池容量收窄（§10.81，独立复核 b13 的 MEDIUM-1）：放在**这里**是刻意的——
        # 中间件跑在事件循环里（anyio 的 limiter 只能在循环内设），且**每个请求**都会经过，
        # 包括 `/health`、CORS 预检与 `httpx.ASGITransport` 下的量具请求。幂等，代价一次分支。
        bound_threadpool_once()
        if request.url.path == "/api/v1/health":
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)  # CORS 预检不带 token
        auth = request.headers.get("Authorization", "")
        if not secrets.compare_digest(auth, f"Bearer {token}"):
            return _json_error(401, "unauthorized", "缺少或无效的 token")
        return await call_next(request)

    # ⚠ **重活专用闸门**用**纯 ASGI** 中间件（§10.85 修 b14 的 MEDIUM-1）：见类 docstring。
    # 它**不在** `@app.middleware("http")` 里——那条路是 `BaseHTTPMiddleware`，会在响应体
    # 开流之前就 release，**流式（SSE）重活因此完全不受闸门约束**（复核实测：12 条并发流式
    # 重活的并发峰值是 **12**，而非流式恰好是 4）。
    app.add_middleware(_HeavyGateMiddleware)

    def _json_error(status: int, code: str, message: str):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=status,
                            content={"code": status, "status": "error", "error": code,
                                     "message": message})

    @app.get("/api/v1/health")
    def health():
        from src.core.retrieval import embedder
        try:
            conn = get_db_connection()
            conn.execute("SELECT 1")
            db_status = "ok"
        except Exception:
            db_status = "error"
        return {
            "status": "healthy" if db_status == "ok" else "degraded",
            "uptime_seconds": int(time.monotonic() - _STARTED_AT),
            "db_status": db_status,
            # ⚠ **廉价三态**（§10.74）：`health()` 只读已有证据，**不加载模型**。
            # 这里原先调 `embedder.is_available()` —— 那是"加载一个模型来判断它能不能加载"：
            # 量具实测空缓存下一次 = **6.6s 且全程占着事件循环**（而本端点当时是 `async def`）。
            # 取值：ok（本进程加载成功过）/ offline（最近一次尝试失败）/ unknown（还没试过）。
            "vector_engine": embedder.health(),
            "parser_worker": "ok",
        }

    # ===== 阶段2.1 纠错补丁 API（外部评审响应：OCR/解析错误人工纠偏）=====

    @app.post("/api/v1/clauses/patches")
    def create_patch(body: dict | None = None):
        """创建纠错补丁。内置防乱检测（patch guard）：
        - reject：与原文几乎无关/大量乱码 → 422 拒绝落库
        - warning：长度/语言突变 → 首次返回 code=466 + 警告原因，
          前端二次确认后带 force=true 重新提交才落库（P1 红线：不写脏补丁）。"""
        body = body or {}
        from src.core.storage import clause_repo
        from src.core.exceptions import KnowledgeStationError
        from src.core.verification.patch_guard import check_patch
        clause_id = body.get("clause_revision_id") or ""
        field = body.get("field_name") or ""
        new_val = body.get("patched_value") or ""
        force = bool(body.get("force"))

        # 防乱检测（仅内容字段；取原值做比对）
        if field in ("content_text", "content_markdown"):
            try:
                conn = get_db_connection()
                orig_row = conn.execute(
                    "SELECT content_text, content_markdown FROM clause_revision"
                    " WHERE clause_revision_id=?", (clause_id,)).fetchone()
                patches = conn.execute(
                    "SELECT patched_value FROM clause_patch WHERE clause_revision_id=?"
                    " AND field_name=?", (clause_id, field)).fetchone()
                original = None
                if orig_row is not None:
                    base = orig_row["content_markdown"] if field == "content_markdown" \
                        else orig_row["content_text"]
                    original = patches["patched_value"] if patches else base
                guard = check_patch(original or "", str(new_val), field)
            except Exception:
                # 防乱检测内部异常：fail-closed（P1 不写脏补丁红线）——
                # 保守拒绝写入，绝不把脏/乱码补丁当合法数据落库
                return _json_error(422, "patch_guard_error",
                                   "防乱检测内部异常，已保守拒绝写入；请稍后重试")
            if guard["verdict"] == "reject" and not force:
                return _json_error(422, "patch_rejected",
                                   "修正被拒绝：" + "；".join(guard["reasons"]))
            if guard["verdict"] == "warning" and not force:
                return {"code": 466, "status": "warning",
                        "data": {"warnings": guard["reasons"],
                                 "similarity": round(guard.get("similarity", 1), 2)},
                                "message": "检测到可疑修改，请确认后重新提交"}

        try:
            out = clause_repo.upsert_patch(
                clause_id, field, new_val, body.get("patch_reason"))
        except KnowledgeStationError as e:
            status = 404 if e.code == "clause_not_found" else 422
            return _json_error(status, e.code, str(e))
        return {"code": 200, "status": "success", "data": out}

    @app.get("/api/v1/clauses/resolve")
    def resolve_clause(standard_no: str, clause_number: str,
                       folder_id: str | None = None):
        """引用兜底：按标准号+条款号解析条款（LLM 引用未进证据列表的条款时定位用）。
        标准号做年份宽容（GB/T 3608-2008 → GB 3608-2025 现行版）。

        folder_id（2026-10 收藏目录）：可选。给定时对命中体追加夹范围标记——
        `folder_scope`: "inside"|"outside"|null（null=夹不存在/未查），host 据此
        对夹外条款打禁令（与 bookmarks_scope 同款不抛错设计）。"""
        from src.core.storage import clause_repo, user_data
        c = clause_repo.resolve_clause(standard_no, clause_number)
        if c is None:
            return _json_error(404, "clause_not_found",
                               f"条款不存在: {standard_no} {clause_number}")
        bm = user_data.bookmarked_clause_keys()
        ann = user_data.annotations_by_clause_keys([c.clause_key])
        out = _ev_dict(c, bm, ann)
        # 2026-09-16（iteration-6 自查 §8.1 的修正版）：把「能否作为依据」做成**机器可读**字段。
        #
        # 背景与边界（先说清，别误读成"加了过滤"）：
        # 本端点是**定位**工具（LLM 引用未进证据列表的条款时用），它**故意不过滤**非现行版
        # —— 用户点名问旧版时必须能解析到，并说明其状态与差异（决策 22 的括号部分）。
        # 此前该禁令只写在 `plugin/src/chatmode.js:153` 的取证提示词里（"非 effective 只能作
        # 历史沿革或预告说明，不得作为依据"），属**提示词级约束**；而 `hybrid_engine` 的
        # exact 通道对同一红线是**硬过滤**（`NOT IN ('withdrawn','superseded')`）——
        # 同一红线两条路径强度不同，是本函数此前唯一的合规缺口。
        #
        # 修法不是加过滤（那会破坏"点名问旧版"这个被明确设计支持的场景），而是补一个
        # 与既有 `folder_scope`/`scope_notice` **同款**的代码级标记：让"只能定位、不得作依据"
        # 不再依赖模型正确解读 `legal_status` 枚举。
        # ⚠ 不改 `legal_status` 语义、不改变命中与否、不动 404 分支。
        ls = out.get("legal_status")
        if ls == "effective":
            out["basis_scope"] = "usable"
        elif ls is None:
            # 状态未知：不猜测（与 resolve_status 的"诚实保持原状态"同哲学）
            out["basis_scope"] = "unknown"
            out["basis_notice"] = ("该条效力状态未知（库内未核验），只能用于定位；"
                                   "如需作为依据，请先用 ks_answer 取证确认现行性。")
        else:
            out["basis_scope"] = "locate_only"
            _label = {"superseded": "已被替代", "withdrawn": "已废止",
                      "upcoming": "尚未生效",
                      # 2026-09-24 新增档：征求意见稿等**仅参考**的入库件。
                      # ⚠ 必须给中文名——`_label.get(..., str(ls))` 的兜底会把内部英文标识
                      #   （"reference"）直接显示给业主（最高指令：不许把内部叫法露到界面上）。
                      "reference": "参考资料（仅参考，未生效）"}.get(str(ls), str(ls))
            out["basis_notice"] = (f"该条为「{_label}」，只能用于定位、历史沿革或预告说明，"
                                   "不得写入依据区、不得作为合规结论的依据。")
        if folder_id:
            scope = user_data.folder_scope(folder_id)
            if scope is None:
                out["folder_scope"] = None   # 夹不存在（被删）——host 如实降级
            else:
                inside = (c.doc_id in scope["doc_ids"]
                          or c.clause_key in scope["clause_keys"])
                out["folder_scope"] = "inside" if inside else "outside"
                out["folder_name"] = scope["folder_name"]
        return {"code": 200, "data": out}

    @app.get("/api/v1/data/quality-issues")
    def data_quality_issues(limit: int = 200):
        """数据体检：自动识别 OCR/切分录入质量问题的条款，供前端集中纠错。
        检查项：正文含内嵌表格文本（与 table_md 重复）、英文粘连、页脚/下节标题泄漏、
        表格列数不一致（阶梯）、表格脏单元格。零副作用只读。
        （同步 def：纯 CPU/IO，FastAPI 自动进线程池，不冻结事件循环）

        判据实现已抽到 `src.core.quality.clause_health`（唯一所有者）——同一套规则也服务于
        R27 入库预览（Dry-Run）；这里只保留取数、组装与 limit 早停。
        """
        from src.core.quality import clause_health
        conn = get_db_connection()
        # 游标流式迭代：命中 limit 即停，不再把整表物化进内存
        # （百万条款量级下旧 fetchall 会先吃掉数 GB 再开始正则扫描）。
        rows = conn.execute(
            "SELECT cr.clause_revision_id, cr.clause_number, cr.content_text,"
            " cr.content_markdown, cr.is_suspicious, dm.standard_no"
            " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " ORDER BY dm.standard_no, cr.clause_number")
        patch_rows = conn.execute(
            "SELECT clause_revision_id, field_name FROM clause_patch").fetchall()
        patched: dict[str, list[str]] = {}
        for p in patch_rows:
            patched.setdefault(p["clause_revision_id"], []).append(p["field_name"])
        issues: list[dict] = []
        for row in rows:
            ct = row["content_text"] or ""
            health = clause_health(ct, row["content_markdown"])
            if health.tags:
                issues.append({
                    "clause_revision_id": row["clause_revision_id"],
                    "standard_no": row["standard_no"],
                    "clause_number": row["clause_number"],
                    "is_suspicious": bool(row["is_suspicious"]),
                    "issues": health.tags,
                    "content_text": ct[:200],
                    "table_md": health.table_md[:200],
                    "patched_fields": patched.get(row["clause_revision_id"], []),
                })
                if len(issues) >= limit:
                    break
        return {"code": 200, "status": "success",
                "data": issues, "total": len(issues)}

    @app.get("/api/v1/clauses/patches")
    def get_patches(clause_revision_id: str | None = None, limit: int = 100):
        from src.core.storage import clause_repo
        return {"code": 200, "status": "success",
                "data": clause_repo.list_patches(clause_revision_id, limit)}

    @app.delete("/api/v1/clauses/patches/{patch_id}")
    def remove_patch(patch_id: str):
        """删除补丁（回滚到不可变原始值）。

        ⚠ §10.79：`clause_repo.delete_patch` 在补丁改的是 `content_text` 时会走
        `_reindex_clause_indexes` ⇒ **重算 FTS + 重算向量**（要加载嵌入模型 + 推理，秒级）
        ⇒ 必须是 `def`。审计的 `ml-runtime/model-load` 标记在这里**不是**误报。
        """
        from src.core.storage import clause_repo
        ok = clause_repo.delete_patch(patch_id)
        if not ok:
            return _json_error(404, "patch_not_found", f"补丁不存在: {patch_id}")
        return {"code": 200, "status": "success", "data": {"patch_id": patch_id,
                                                            "rolled_back": True}}

    # ===== T06a 合规审查接口（契约 7.3）=====

    @app.get("/api/v1/documents/{doc_id}/file")
    def get_document_file(doc_id: int | str):
        """PDF 原件字节流（R7 穿透高亮用；受 token 保护）。

        ⚠ **曾经是 `async def`，§10.86 起改成 `def`**：本端点只做一次查询 + 返回
        `FileResponse`，文件字节由 Starlette 用 anyio 流式读出（**不占事件循环**）。
        §10.75 当时把它留成 `async def` 的理由是"它只查一下、不值得进线程池"；§10.86 的判据
        改成"**`async def` 且零有效 await ⇒ 必须 `def`**"（结构性，不看标记表）之后它正好
        落在那一档，于是**一并转**（独立复核 b16 的 LOW-1：这一句原先还写着"故意保持
        `async def`"，与相邻一行的 `def` 直接矛盾）。**行为不变**：b16 复核实测 2.5MB / 18MB /
        **72MB** PDF 的字节数与 sha256 与磁盘一致，非 PDF 仍 404。
        """
        conn = get_db_connection()
        row = conn.execute(
            "SELECT file_path FROM doc_meta WHERE doc_id=?", (str(doc_id),)).fetchone()
        if row is None or not row["file_path"]:
            return _json_error(404, "doc_not_found", f"文档不存在: {doc_id}")
        p = Path(row["file_path"])
        if not p.exists() or not str(p).lower().endswith(".pdf"):
            return _json_error(404, "file_not_found",
                               f"PDF 原件不可用（法律文本直灌文档无原页）: {p.name}")
        return FileResponse(str(p), media_type="application/pdf", filename=p.name)

    @app.get("/api/v1/documents/{doc_id}/figure/{fig_no}")
    def get_document_figure(doc_id: int | str, fig_no: str, dpi: int = 144):
        """图形呈现（2026-08-29，GB/T 34406 图1/图A.1/图A.2 实测，语料级）。

        扫描双层图形无独立图像对象，按图题锚定图区：**流程图先尝试矢量
        重绘**（figure_redraw 内孔检测+OCR+拓扑，任一环不达标返回 None），
        失败回退 PNG 截图（与 PDF 同源，永远不脏）；定位失败 404。
        dpi 参数供前端点击放大时取高清版（72~300 钳制）。
        """
        dpi = max(72, min(300, int(dpi)))
        conn = get_db_connection()
        row = conn.execute(
            "SELECT file_path FROM doc_meta WHERE doc_id=?", (str(doc_id),)).fetchone()
        if row is None or not row["file_path"]:
            return _json_error(404, "doc_not_found", f"文档不存在: {doc_id}")
        p = Path(row["file_path"])
        if not p.exists() or not str(p).lower().endswith(".pdf"):
            return _json_error(404, "file_not_found", f"PDF 原件不可用: {p.name}")
        from src.core.figure_locator import locate_figure
        from src.core.text_utils import normalize_pua_latin

        def _frac_headers(frac_x0, frac_w, frac_h):
            """截图尺寸/位置还原头（2026-09-02 用户契约：截图与原版同尺寸同位）。
            值为页宽/页高比例（0~1），前端乘预览正文宽度还原 px。"""
            return {
                "Cache-Control": "max-age=86400",
                "X-Frac-X0": f"{float(frac_x0):.6f}",
                "X-Frac-W": f"{float(frac_w):.6f}",
                "X-Frac-H": f"{float(frac_h):.6f}",
            }

        # 2026-09-02 曲线/图表优先：MinerU 把曲线图（图1-8、图A.2/A.5）识别为
        # chart 类型（非 image），题注在 chart 块 caption——按题注图号定位
        # bbox → clip 截图（curve 图无 image 块，此前缺失）。
        hit = None
        _geo_c = None
        try:
            from src.core.middle_geo import load as _load_mid_c
            _geo_c = _load_mid_c(
                get_settings().data_dir / "parse_out" / str(doc_id))
            if _geo_c is not None:
                # 数字图号先按题注、再按页序计数兜底（图4/6/8 题注被 OCR 合并）
                _ch = _geo_c.chart_by_no(str(fig_no))
                if _ch is None:
                    _ch = _geo_c.chart_by_caption(str(fig_no))
                if _ch is not None:
                    hit = _ch   # (pno, bbox_px, caption)
        except Exception:   # noqa: BLE001 - chart 定位失败走既有兜底
            pass
        if hit is not None:
            _pno, _bbox_px, _cap = hit
            import fitz
            with fitz.open(str(p)) as pdf:
                if _pno < 0 or _pno >= len(pdf):
                    return _json_error(404, "figure_not_found", f"未定位到图{fig_no}")
                _pg = pdf[_pno]
                assert _geo_c is not None  # hit 非空蕴含 _geo_c 已加载
                _sz = _geo_c.size(_pno + 1)
                if _sz and _sz[0] > 0 and _sz[1] > 0 and len(_bbox_px) == 4:
                    _sx = _pg.rect.width / _sz[0]
                    _sy = _pg.rect.height / _sz[1]
                    _r = fitz.Rect(_bbox_px[0] * _sx, _bbox_px[1] * _sy,
                                   _bbox_px[2] * _sx, _bbox_px[3] * _sy)
                else:
                    _r = fitz.Rect(*_bbox_px)
                _r = fitz.Rect(max(_r.x0, 0), max(_r.y0, 0),
                               min(_r.x1, _pg.rect.width), min(_r.y1, _pg.rect.height))
                if _r.width < 8 or _r.height < 6:
                    return _json_error(404, "figure_not_found", f"未定位到图{fig_no}")
                _pix = _pg.get_pixmap(clip=_r, dpi=dpi)
                _pw, _ph = _pg.rect.width, _pg.rect.height
            from fastapi.responses import Response
            return Response(
                content=_pix.tobytes("png"), media_type="image/png",
                headers=_frac_headers(_r.x0 / _pw, _r.width / _pw, _r.height / _ph))

        if hit is None:
            hit = locate_figure(p, fig_no, normalize_pua_latin)
        if hit is None:
            # 2026-09-01 C3 middle.json 兜底：文字层锚定失败 → MinerU 深度
            # 解析的预裁剪插图（images/<sha256>.jpg，题注 image_caption 匹配
            # 图号），与 PDF 同源；仍无 → 404（前端 onerror 隐藏）。
            # 2026-09-02：full 版本同时返回 bbox/page_size → 按原版比例还原
            # 尺寸与水平位置（与 fitz 路径口径一致）。
            from src.core.figure_locator import locate_middle_figure_full as _full
            mf = _full(get_settings().data_dir / "parse_out" / str(doc_id), str(fig_no))
            if mf is not None:
                crop, _pno, bbox_px, page_size = mf
                media = "image/png" if crop.suffix.lower() == ".png" else "image/jpeg"
                hdr = {"Cache-Control": "max-age=86400"}
                if bbox_px and len(bbox_px) == 4 and page_size and page_size[0] > 0:
                    hdr.update(_frac_headers(
                        bbox_px[0] / page_size[0],
                        (bbox_px[2] - bbox_px[0]) / page_size[0],
                        (bbox_px[3] - bbox_px[1]) / page_size[1]))
                return FileResponse(str(crop), media_type=media, headers=hdr)
            # 2026-09-02 C1 统一图对象层第三途径：MinerU 漏识别（无 chart/image
            # 块）但题注在 OCR 文本块（text_blocks，如 24276 图 A.3）→ OCR 题注
            # 锚定图区（题注上方正文块下缘到题注顶），截图（与 PDF 同源）。
            from src.core.figure_locator import locate_middle_caption as _lcap
            _c = _lcap(get_settings().data_dir / "parse_out" / str(doc_id),
                       str(fig_no))
            if _c is not None:
                _pno2, _rect2 = _c
                import fitz
                with fitz.open(str(p)) as pdf:
                    if 0 <= _pno2 < len(pdf):
                        _pg2 = pdf[_pno2]
                        assert _geo_c is not None  # _c 命中蕴含 _geo_c 已加载（_lcap 依赖其数据）
                        _sz2 = _geo_c.size(_pno2 + 1)
                        if _sz2 and _sz2[0] > 0 and _sz2[1] > 0:
                            _r2 = fitz.Rect(
                                _rect2[0] * _pg2.rect.width / _sz2[0],
                                _rect2[1] * _pg2.rect.height / _sz2[1],
                                _rect2[2] * _pg2.rect.width / _sz2[0],
                                _rect2[3] * _pg2.rect.height / _sz2[1])
                        else:
                            _r2 = fitz.Rect(*_rect2)
                        _r2 = fitz.Rect(max(_r2.x0, 0), max(_r2.y0, 0),
                                        min(_r2.x1, _pg2.rect.width),
                                        min(_r2.y1, _pg2.rect.height))
                        if _r2.width >= 8 and _r2.height >= 6:
                            _pix2 = _pg2.get_pixmap(clip=_r2, dpi=dpi)
                            _pw2, _ph2 = _pg2.rect.width, _pg2.rect.height
                            from fastapi.responses import Response
                            return Response(
                                content=_pix2.tobytes("png"),
                                media_type="image/png",
                                headers=_frac_headers(
                                    _r2.x0 / _pw2, _r2.width / _pw2,
                                    _r2.height / _ph2))
            return _json_error(404, "figure_not_found", f"未定位到图{fig_no}")
        pno, rect = hit
        import fitz
        # 流程图矢量重绘（结构置信度门槛内建，失败= None → PNG 回退）
        try:
            from src.core.figure_redraw import try_redraw
            svg = try_redraw(str(p), pno, fitz.Rect(*rect))
        except Exception:
            svg = None
        if svg:
            from fastapi.responses import Response
            return Response(content=svg.encode("utf-8"), media_type="image/svg+xml",
                            headers={"Cache-Control": "max-age=86400"})

        with fitz.open(str(p)) as pdf:
            page = pdf[pno]
            pix = page.get_pixmap(clip=fitz.Rect(*rect), dpi=dpi)
            pw, ph = page.rect.width, page.rect.height
        from fastapi.responses import Response
        return Response(content=pix.tobytes("png"), media_type="image/png",
                        headers=_frac_headers(rect[0] / pw, rect[2] / pw - rect[0] / pw,
                                              (rect[3] - rect[1]) / ph))

    @app.get("/api/v1/documents/{doc_id}/formula/{fno}")
    def get_document_formula(doc_id: int | str, fno: str, clause: str, dpi: int = 144):
        """公式原图呈现（2026-08-29 起，2026-09-02 定稿）。

        双层扫描文字层把二维公式压平（24276 实测正文公式行**无编号结尾**，
        编号被 OCR 剥除），原排版复刻 = 版面模型公式块（middle.json
        interline_equation，bbox + LaTeX）clip 截图 PNG，与 PDF 同源永远
        不脏。fno 语义 = **条款内公式序号**（展示层 _inject_formulas 阅读序
        计数，1-based）；定位 = 从条款 page_start 页起按 eqs 页序累计第 fno
        个 → LaTeX 与条款 content_text 第 fno 个公式段比对校验（±1 容错）。
        无深度产物 → 回退文字层启发式（locate_formula）。404 → 前端隐藏。
        """
        dpi = max(72, min(300, int(dpi)))
        conn = get_db_connection()
        meta = conn.execute(
            "SELECT file_path FROM doc_meta WHERE doc_id=?", (str(doc_id),)).fetchone()
        if meta is None or not meta["file_path"]:
            return _json_error(404, "doc_not_found", f"文档不存在: {doc_id}")
        p = Path(meta["file_path"])
        if not p.exists() or not str(p).lower().endswith(".pdf"):
            return _json_error(404, "file_not_found", f"PDF 原件不可用: {p.name}")
        crow = conn.execute(
            "SELECT page_start, content_text FROM clause_revision"
            " WHERE doc_id=? AND clause_number=?",
            (str(doc_id), clause)).fetchone()
        if crow is None or crow["page_start"] is None:
            return _json_error(404, "clause_not_found", f"条款不存在: {clause}")
        from src.core.formula_locator import locate_formula, locate_eq_by_number
        parse_root = get_settings().data_dir / "parse_out" / str(doc_id)
        # 2026-09-02 修复 fno 错位：fno 现为**全局公式序号**（展示层按 LaTeX
        # 匹配写入，见 _inject_formulas）→ 全局序取块（locate_eq_by_number），
        # 精确无错位（不再用条款内计数 + ±1 容错——那会因判据式/正文式数量
        # 差而错位到无关区域）。
        hit = locate_eq_by_number(
            str(p), int(crow["page_start"]), fno, parse_root)
        if hit is None:
            # 回退文字层启发式（编号锚 + spans 并集；识别版 PDF 适用）
            hit2 = locate_formula(str(p), int(crow["page_start"]), fno)
            hit = hit2 if hit2 is not None else None
        if hit is None:
            return _json_error(404, "formula_not_found", f"未定位到式({fno})")
        pno, rect = hit
        import fitz
        with fitz.open(str(p)) as pdf:
            page = pdf[pno]
            r = fitz.Rect(*rect)
            r = fitz.Rect(max(r.x0, 0), max(r.y0, 0),
                          min(r.x1, page.rect.width), min(r.y1, page.rect.height))
            if r.width < 8 or r.height < 6:
                return _json_error(404, "formula_not_found", f"未定位到式({fno})")
            pix = page.get_pixmap(clip=r, dpi=dpi)
            pw, ph = page.rect.width, page.rect.height
        from fastapi.responses import Response
        return Response(
            content=pix.tobytes("png"), media_type="image/png",
            headers={
                "Cache-Control": "max-age=86400",
                # 2026-09-02 公式截图按原版比例还原（同 /figure 契约）
                "X-Frac-X0": f"{r.x0 / pw:.6f}",
                "X-Frac-W": f"{r.width / pw:.6f}",
                "X-Frac-H": f"{r.height / ph:.6f}",
            })
    @app.get("/api/v1/documents/{doc_id}/table-image/{page_no}/{tbl_idx}")
    def get_document_table_image(doc_id: int | str, page_no: int,
                                 tbl_idx: int, dpi: int = 144):
        """带图表格整表截图（2026-09-02 用户契约：凡单元格含图片的表格，
        整个表格也一起当图片处理）。

        定位：MinerU 深度解析产物（middle.json）该页 para_blocks 中第 tbl_idx
        个 type=table 的 bbox → clip 渲染 PNG（与 PDF 同源，永远不脏）；
        响应头 X-Frac-* 按原版比例还原尺寸/位置（同 /figure 契约）。
        tbl_idx 由展示层 _content_html 从 middle_geo.image_hit_tables 写入
        （页内带图表格序号，升序）。无深度产物/越界 → 404（前端隐藏）。
        """
        dpi = max(72, min(300, int(dpi)))
        conn = get_db_connection()
        meta = conn.execute(
            "SELECT file_path FROM doc_meta WHERE doc_id=?", (str(doc_id),)).fetchone()
        if meta is None or not meta["file_path"]:
            return _json_error(404, "doc_not_found", f"文档不存在: {doc_id}")
        p = Path(meta["file_path"])
        if not p.exists() or not str(p).lower().endswith(".pdf"):
            return _json_error(404, "file_not_found", f"PDF 原件不可用: {p.name}")
        from src.core.middle_geo import load as load_middle_geo
        geo = load_middle_geo(
            get_settings().data_dir / "parse_out" / str(doc_id))
        if geo is None:
            return _json_error(404, "table_geo_not_found",
                               "无深度版面产物（middle.json 缺失）")
        tables = geo.tables(int(page_no))
        if tbl_idx < 0 or tbl_idx >= len(tables):
            return _json_error(404, "table_not_found", f"页{page_no}无第{tbl_idx}张表")
        bbox_px = tables[tbl_idx]
        sz = geo.size(int(page_no))
        if not sz or sz[0] <= 0 or sz[1] <= 0:
            return _json_error(404, "table_geo_bad", "版面尺寸不可用")
        import fitz
        with fitz.open(str(p)) as pdf:
            pno = int(page_no) - 1
            if pno < 0 or pno >= len(pdf):
                return _json_error(404, "page_not_found", f"页不存在: {page_no}")
            page = pdf[pno]
            sx = page.rect.width / sz[0]
            sy = page.rect.height / sz[1]
            rect = fitz.Rect(bbox_px[0] * sx, bbox_px[1] * sy,
                             bbox_px[2] * sx, bbox_px[3] * sy)
            rect = fitz.Rect(max(rect.x0, 0), max(rect.y0, 0),
                             min(rect.x1, page.rect.width),
                             min(rect.y1, page.rect.height))
            if rect.width < 8 or rect.height < 6:
                return _json_error(404, "table_geo_bad", "表格区域异常")
            pix = page.get_pixmap(clip=rect, dpi=dpi)
            pw, ph = page.rect.width, page.rect.height
        from fastapi.responses import Response
        return Response(
            content=pix.tobytes("png"), media_type="image/png",
            headers={
                "Cache-Control": "max-age=86400",
                "X-Frac-X0": f"{rect.x0 / pw:.6f}",
                "X-Frac-W": f"{rect.width / pw:.6f}",
                "X-Frac-H": f"{rect.height / ph:.6f}",
            })

    @app.get("/api/v1/documents")
    def doc_list():
        """知识库文档列表（对比选择器/知识库浏览用）。"""
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT doc_id, standard_no, standard_name, legal_status, legal_hierarchy,"
            " effective_from, published_at, ccs_code, ccs_name, ics,"
            " superseded_by, withdrawn_date, quality_grade, doc_type FROM doc_meta"
            " WHERE catalog_hidden = 0 ORDER BY standard_no").fetchall()
        data = []
        for r in rows:
            d = dict(r)
            # 到期翻转：upcoming 且实施日期已到 → 按现行展示（倒计时，读取时惰性决议）
            d["legal_status"] = resolve_status(d.get("legal_status"), d.get("effective_from"))
            data.append(d)
        return {"code": 200, "data": data}

    @app.get("/api/v1/documents/categories")
    def doc_categories():
        """文件目录面板数据源（4 级树）：
        标准：L1 国家标准·行标·团标 → L2 CCS 大类 → L3 CCS 区间 → L4 CCS 具体类目+文档
        法规：L1 法律法规 → L2 效力等级 → L3 领域 → **文档叶节点**（法规名称不再作为目录级别，2026-08-24）
        空分类不返回；叶节点含 doc_id/standard_no/standard_name/legal_status。"""
        from src.core.knowledge.doc_catalog import classify_document
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT doc_id, standard_no, standard_name, legal_status, legal_hierarchy,"
            " effective_from, published_at, ccs_code, ccs_name, ics,"
            " superseded_by, withdrawn_date, quality_grade, doc_type, domain_tags FROM doc_meta"
            " WHERE catalog_hidden = 0 ORDER BY standard_no").fetchall()
        top: dict[str, dict] = {}   # top -> {name, order, l2: {l2 -> {l3 -> {l4 -> [docs]} | {docs}}}}
        for r in rows:
            d = dict(r)
            # 到期翻转：upcoming 且实施日期已到 → 按现行展示（读取时惰性决议）
            d["legal_status"] = resolve_status(d.get("legal_status"), d.get("effective_from"))
            try:
                tags = json.loads(d.get("domain_tags") or "[]")
                d["domain_tags"] = tags if isinstance(tags, list) else []
            except Exception:
                d["domain_tags"] = []
            cl = classify_document(d)
            node = top.setdefault(cl["top"], {"name": cl["top_name"], "order": cl["order"], "levels": {}})
            l2 = node["levels"].setdefault(cl["level2"], {})
            l3 = l2.setdefault(cl["level3"], {})
            l4 = l3.setdefault(cl["level4"], [])
            # 2026-09-06 F1 修复：追加**已翻转**的行（d）而非原始行（r）——
            # docstring 声称"已翻转"，此前却 append(dict(r)) 把 raw legal_status
            # 下发（upcoming 到期后目录页仍显示旧态）。效力报告端点当时为隔离
            # 此 bug 自行 resolve（见 effect_report.py 模块头）；现统一修源头。
            l4.append(dict(d))
        out = []
        for tk, node in sorted(top.items(), key=lambda kv: kv[1]["order"]):
            l2s = []
            for l2name, l2map in sorted(node["levels"].items()):
                l3s = []
                for l3name, l3map in sorted(l2map.items()):
                    l4s = [{"name": l4name, "docs": docs}
                           for l4name, docs in sorted(l3map.items())]
                    l3s.append({"name": l3name, "items": l4s})
                l2s.append({"name": l2name, "items": l3s})
            out.append({"name": node["name"], "items": l2s})
        return {"code": 200, "data": out}

    @app.post("/api/v1/documents/batch-delete")
    def documents_batch_delete(body: dict | None = None):
        """批量删除文档（2026-08-31 批量删除 UI 接线）。显式级联见 doc_delete.py 模块注释：
        clause 级 span/patch/obligation/edge/fts(rowid)/vec/revision + doc 级几何/变更事件/关注/元数据。
        用户资产（收藏/批注/项目）不删；不 VACUUM（空间回收走维护面）。
        body: {"doc_ids": [...], "confirm": true}——confirm 必须显式 true（防脚本误调一刀删库）。"""
        from src.core.storage.doc_delete import delete_documents
        try:
            body = body or {}
        except Exception:
            return _json_error(422, "DOC-3001", "请求体必须是 JSON")
        doc_ids = body.get("doc_ids")
        if not isinstance(doc_ids, list) or not doc_ids:
            return _json_error(422, "DOC-3001", "doc_ids 必须是非空列表")
        if body.get("confirm") is not True:
            return _json_error(422, "DOC-3002", "缺少 confirm:true——批量删除需要显式确认")
        try:
            result = delete_documents([str(d) for d in doc_ids])
        except ValueError as e:
            return _json_error(422, "DOC-3001", str(e))
        result["space_hint"] = "已删除。磁盘空间回收请走维护/数据包功能（VACUUM），避免长时间锁库。"
        return {"code": 200, "status": "success", "data": result}

    @app.get("/api/v1/documents/{doc_id}/tree")
    def document_tree(doc_id: str):
        """R37 目录树：优先读 PDF 自带书签（最全最准，含层级+页码），
        无书签时回退「库内 N.M 小节标题 + 文本层猜章标题」；法规类（law-text）用库内「第X章」。

        - 有书签（GB30871 识别版等）：fitz.get_toc() 直接给完整目录，过滤前言/引言/编号/附录表格噪声。
        - 无书签：库内 clause_number 形如 N.M 且正文 ≤15 字为小节标题；章标题从 PDF 文本层猜
          （`^N 标题$` 独立行，且该章在库内有 N.M 子条款）。
        - 法规类（file_path 为 law-text://）：条款号「第一条」格式，无 N.M 小节——
          从库内「第X章」条款提取章标题，返回 level=1。
        返回 [{clause_number, title, page_start, level, source}]，level=1 章 / level=2 小节。
        """
        import re as _re
        conn = get_db_connection()

        # 2026-08-29 附录进目录（通用）：附录（规范性/资料性）是标准正文组成部分，
        # 无书签标准（GB 25596 实测）此前附录 A/B 从目录与全文预览中整体消失。
        # 法规"附则"同规则覆盖（切分层 _APPENDIX_HEAD 把附则归 content_type='附录'）。
        def _appendix_items() -> list[dict]:
            arows = conn.execute(
                "SELECT clause_number, content_text, page_start FROM clause_revision"
                " WHERE doc_id=? AND content_type='附录' ORDER BY rowid",
                (str(doc_id),)).fetchall()
            out, seen_a = [], set()
            for ar in arows:
                ano = (ar["clause_number"] or "").strip()
                if not ano or ano in seen_a:
                    continue
                seen_a.add(ano)
                body = (ar["content_text"] or "").replace("\n", " ").strip()
                # 标题：剥 "附 录 A" 前缀（字间排版空白通用）后取首段
                m_a = _re.match(r"^附\s*录\s*[A-Z]?\s*(.*)$", body)
                title = (m_a.group(1) if m_a else body) or ""
                # 附录头形态 "标题 标题见表A.1。"（标题在说明句里重复）→ 截到"见表"前，
                # 再做 t+t 粘连收缩；无此形态原样，末段 24 字兜底
                title = title.split("见表")[0]
                n = len(title)
                for k in range(1, n // 2 + 1):
                    if 2 * k == n and title[:k] == title[k:]:
                        title = title[:k]
                        break
                title = title[:24] or ano
                out.append({"clause_number": ano, "title": title,
                            "page_start": ar["page_start"], "level": 1,
                            "source": "db-appendix"})
            return out

        def _with_appendix(base: list[dict]) -> list[dict]:
            app = _appendix_items()
            if not app:
                return base
            # 书签已含附录章时不去重补条（避免同页双条目）
            has_app = any("附录" in (b.get("title") or "").replace(" ", "").replace("\u3000", "")
                          for b in base)
            return base if has_app else base + app

        doc = conn.execute(
            "SELECT standard_no, file_path FROM doc_meta WHERE doc_id=?", (str(doc_id),)).fetchone()
        if doc is None:
            return _json_error(404, "doc_not_found", f"文档不存在: {doc_id}")

        rows = conn.execute(
            "SELECT clause_number, content_text, page_start FROM clause_revision"
            " WHERE doc_id=? AND content_type='normal' ORDER BY rowid", (str(doc_id),)).fetchall()

        # ---- 策略 1：PDF 自带书签（最优先）----
        bookmarks: list[dict] = []
        if doc["file_path"] and doc["file_path"].startswith(("http", "law-text")) is False \
                and Path(doc["file_path"]).exists():
            try:
                import fitz
                pdf = fitz.open(doc["file_path"])
                toc = pdf.get_toc()
                noise = ("前言", "引言", "起草说明", "目录", "编制说明")
                for lvl, title, page in toc:
                    t = (title or "").strip()
                    if not t or page is None or int(page) <= 0:
                        continue
                    t_flat = t.replace(" ", "").replace("\u3000", "")
                    if t_flat.startswith(noise) or _re.match(r"^page-\d+$", t):
                        continue
                    # 书签页码是 PDF 物理页（与渲染页码一致）；L1 里标题形如 N.M 自动降为 L2
                    eff_lvl = min(lvl, 2)
                    if eff_lvl == 1 and _re.match(r"^\d{1,2}\.\d{1,2}\s", t):
                        eff_lvl = 2
                    bookmarks.append({"clause_number": "", "title": t,
                                      "page_start": int(page), "level": eff_lvl,
                                      "source": "bookmark"})
                pdf.close()
            except Exception:
                bookmarks = []
        # 书签有效性：垃圾书签（文件名标题 / 负页码）→ 视为无效回退
        if bookmarks:
            junk = [b for b in bookmarks
                    if _re.match(r"^[\w\-]+\.pdf$", b["title"]) or b["page_start"] <= 0]
            if len(junk) > len(bookmarks) / 2:
                bookmarks = []
        if len(bookmarks) >= 3:
            # 剔除附录表格噪声（表A.N / 编号），但保留附录章（附 录 A）与 B.x 小节
            bookmarks = [b for b in bookmarks
                         if not _re.match(r"^(表[A-Z]\.\d+|编号)", b["title"])]
            if bookmarks:
                return {"code": 200, "data": _with_appendix(bookmarks)}

        # ---- 策略 2：法规类（条款号「第X条」格式，无论 file_path 是 law-text 还是测试 PDF）----
        # GB/T 3608 等 N.M 格式（虽 law-text）→ 落策略 3
        if any(_re.match(r"^第[一二三四五六七八九十百千零]+条", (r["clause_number"] or ""))
               for r in rows):
            law_items = []
            for r in rows:
                no = (r["clause_number"] or "").strip()
                body = (r["content_text"] or "").replace("\n", " ").strip()
                m_ch = _re.match(r"^第([一二三四五六七八九十百]+)章", no)
                if m_ch and len(body) <= 60:
                    law_items.append({"clause_number": no,
                                      "title": body[len(no):].strip() or no,
                                      "page_start": r["page_start"], "level": 1,
                                      "source": "law"})
            # 无章结构（纯条文）→ 全部条文进目录，标题取条文首句（≤24 字）
            if not law_items:
                seen_law: set[str] = set()
                for r in rows:
                    no = (r["clause_number"] or "").strip()
                    if not _re.match(r"^第[一二三四五六七八九十百千零]+条", no) or no in seen_law:
                        continue
                    seen_law.add(no)
                    body = (r["content_text"] or "").replace("\n", " ").strip()
                    title = body[len(no):].strip()
                    # 去掉 "（...）" 注音/重复前缀
                    title = _re.sub(r"^[（(][^）)]*[）)]\s*", "", title)[:24] or no
                    law_items.append({"clause_number": no, "title": title,
                                      "page_start": r["page_start"], "level": 2,
                                      "source": "law"})
            if law_items:
                return {"code": 200, "data": _with_appendix(law_items)}

        # ---- 策略 2.5：law-text 且 N.M 格式（如 GB/T 3608-2008，无 PDF 但术语表干净）----
        # 判定：条款形如 N.M，且正文首行 "N.M 标题"（同行）→ 视为标题条款
        if doc["file_path"] and "law-text" in str(doc["file_path"]):
            gl_items = []
            seen_gl: set[str] = set()
            for r in rows:
                no = (r["clause_number"] or "").strip()
                if not _re.match(r"^\d{1,2}\.\d{1,2}$", no) or no in seen_gl:
                    continue
                lines = (r["content_text"] or "").splitlines()
                first = lines[0].strip() if lines else ""
                if first.startswith(no) and len(first) <= 20:
                    seen_gl.add(no)
                    gl_items.append({"clause_number": no,
                                     "title": first[len(no):].strip() or no,
                                     "page_start": r["page_start"], "level": 2,
                                     "source": "db"})
            if gl_items:
                return {"code": 200, "data": _with_appendix(gl_items)}

        # ---- 策略 3：库内 N.M 小节标题 + PDF 文本层猜章标题 ----
        items: list[dict] = []
        seen: set[str] = set()
        for r in rows:
            no = (r["clause_number"] or "").strip()
            m2 = _re.match(r"^(\d{1,2})\.\d{1,2}$", no)
            body = (r["content_text"] or "").replace("\n", " ").strip()
            lines = (r["content_text"] or "").splitlines()
            first_line = lines[0].strip() if lines else ""
            # 小节标题判定（严格）：正文极短 ≤15 字。术语表/正文混排文档（GB 3608-2025）不硬猜，
            # 避免误判；law-text 且 N.M 的干净术语表走下方专门分支。
            if m2 and len(body) <= 15:
                title = body[len(no):].strip() or no
                items.append({"clause_number": no, "title": title,
                              "page_start": r["page_start"], "level": 2,
                              "source": "db"})
                seen.add(no)

        chapters: list[dict] = []
        # ---- 策略 3a：库内章条款提章标题（2026-08-29，GB/T 34406-2017 实测）----
        # 章条款正文形态 "1范围本标准规定了…"（章号+标题+正文粘连）——扫描双层 PUA
        # 文本层 PDF 猜不到 PDF 独立章行，但库内正文（已归一化）可靠。
        # 标题截断：粘连形态无分隔，先查重复单元（"测试报告测试报告…"），
        # 再按正文起始虚词截断（"范围本标准…"→"范围"）。
        _BODY_START = _re.compile(
            r"(本标准|本文件|本部分|本规程|下列|凡|利用|选取|通过|采用|根据|适用|应|宜|包括)")

        def _split_chapter_title(cand: str) -> str:
            for L in range(2, 7):
                if cand[:L] == cand[L:2 * L]:
                    return cand[:L]
            m = _BODY_START.search(cand)
            if m and m.start() >= 2:
                return cand[:m.start()]
            return cand

        chapter_nos: set[str] = set()
        for r in rows:
            no = (r["clause_number"] or "").strip()
            if _re.match(r"^\d{1,2}$", no):
                chapter_nos.add(no)
                if no in seen:
                    continue
                body = (r["content_text"] or "").replace("\n", " ").strip()
                m_ch = _re.match(r"^%s\s*([\u4e00-\u9fa5]{2,14})" % no, body)
                if m_ch:
                    chapters.append({"clause_number": no,
                                     "title": _split_chapter_title(m_ch.group(1)),
                                     "page_start": r["page_start"], "level": 1,
                                     "source": "db"})
                    seen.add(no)
        if doc["file_path"] and doc["file_path"].startswith("law-text") is False \
                and Path(doc["file_path"]).exists():
            try:
                import fitz
                from src.core.ingestion.mineru_adapter import text_layer_pua_mangled
                from src.core.text_utils import normalize_pua_latin
                pdf = fitz.open(doc["file_path"])
                # PUA 错位字体文本层（GB/T 34406-2017 实测）：章行 "1 范围" 的数字
                # 错位/全角，原样猜测必落空 → 文档级判真后归一化再猜（保守回退）。
                # 门控用 chapter_nos（库内存在章条款 N 即证据），比 sub_nos 覆盖
                # 无子条款的章（原理/模型评价等）；PDF 独立行标题最干净，优先采用。
                pua = False
                if pdf.page_count:
                    sample = pdf[0].get_text()[:4000]
                    pua = text_layer_pua_mangled([{"text": sample}])
                for pno in range(pdf.page_count):
                    text = pdf[pno].get_text()
                    if pua:
                        text = normalize_pua_latin(text)
                    for m in _re.finditer(
                            r"(?m)^\s*(\d{1,2})\s*([\u4e00-\u9fa5]{2,12})\s*$", text):
                        num, title = m.group(1), m.group(2)
                        if num not in chapter_nos or num in seen:
                            continue
                        # PDF 命中 → 覆盖库内粘连候选的粗糙标题
                        chapters = [c for c in chapters
                                    if c["clause_number"] != num]
                        chapters.append({"clause_number": num, "title": title,
                                         "page_start": pno + 1, "level": 1,
                                         "source": "pdf"})
                        seen.add(num)
                pdf.close()
            except Exception:
                pass

        def sort_key(x: dict):
            parts = x["clause_number"].split(".")
            try:
                return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0, x["level"])
            except ValueError:
                return (999, 0, x["level"])
        items = sorted(chapters + [i for i in items if i["clause_number"] not in
                                   {c["clause_number"] for c in chapters}],
                       key=sort_key)
        if not items:
            items = _appendix_items()  # 正文无标题条款但有附录时仍给目录
        if not items:
            return _json_error(404, "doc_not_found", f"文档无标题条款: {doc_id}")
        return {"code": 200, "data": _with_appendix(items)}

    @app.get("/api/v1/bookmarks")
    def get_bookmarks():
        from src.core.storage import user_data
        return {"code": 200, "data": user_data.list_bookmarks()}

    @app.post("/api/v1/bookmarks")
    def add_bookmark(body: dict | None = None):
        body = body or {}
        from src.core.exceptions import KnowledgeStationError
        from src.core.storage import user_data
        try:
            return {"code": 200, "data": user_data.add_bookmark(
                body["clause_key"], body.get("remark"), body.get("folder_id"))}
        except KnowledgeStationError as e:
            status = 404 if e.code == "folder_not_found" else 422
            return _json_error(status, e.code, str(e))

    @app.delete("/api/v1/bookmarks/by-clause/{clause_key}")
    def del_bookmark_by_clause(clause_key: str):
        """按 clause_key 取消收藏（toggle 用；无此收藏为 no-op）。"""
        from src.core.storage import user_data
        removed = user_data.remove_bookmark_by_clause_key(clause_key)
        return {"code": 200, "data": {"removed": removed}}

    @app.delete("/api/v1/bookmarks/{bookmark_id}")
    def del_bookmark(bookmark_id: str):
        from src.core.storage import user_data
        if not user_data.remove_bookmark(bookmark_id):
            return _json_error(404, "bookmark_not_found", f"收藏不存在: {bookmark_id}")
        return {"code": 200, "data": {"removed": True}}

    # ===== 标准级书签（增强③-A：DSH「收藏本标准」；区别于条款收藏） =====

    @app.get("/api/v1/doc-bookmarks")
    def get_doc_bookmarks():
        from src.core.storage import user_data
        return {"code": 200, "data": user_data.list_doc_bookmarks()}

    @app.post("/api/v1/doc-bookmarks")
    def add_doc_bookmark(body: dict | None = None):
        body = body or {}
        from src.core.exceptions import KnowledgeStationError
        from src.core.storage import user_data
        try:
            return {"code": 200, "data": user_data.add_doc_bookmark(
                body["doc_id"], body.get("remark"), body.get("folder_id"))}
        except KnowledgeStationError as e:
            status = 404 if e.code == "folder_not_found" else 422
            return _json_error(status, e.code, str(e))

    @app.delete("/api/v1/doc-bookmarks/by-doc/{doc_id}")
    def del_doc_bookmark_by_doc(doc_id: str):
        """按 doc_id 取消收藏（顶部按钮 toggle 用；无此收藏为 no-op）。"""
        from src.core.storage import user_data
        removed = user_data.remove_doc_bookmark_by_doc(doc_id)
        return {"code": 200, "data": {"removed": removed}}

    @app.delete("/api/v1/doc-bookmarks/{doc_bookmark_id}")
    def del_doc_bookmark(doc_bookmark_id: str):
        from src.core.storage import user_data
        if not user_data.remove_doc_bookmark(doc_bookmark_id):
            return _json_error(404, "doc_bookmark_not_found",
                               f"标准收藏不存在: {doc_bookmark_id}")
        return {"code": 200, "data": {"removed": True}}

    # ===== 收藏夹目录（2026-10 收藏目录）：夹 CRUD + 收藏移动 + 收藏目录树 =====

    @app.get("/api/v1/bookmark-folders")
    def get_bookmark_folders():
        from src.core.storage import user_data
        return {"code": 200, "data": user_data.list_folders()}

    @app.post("/api/v1/bookmark-folders")
    def create_bookmark_folder(body: dict | None = None):
        body = body or {}
        from src.core.exceptions import KnowledgeStationError
        from src.core.storage import user_data
        try:
            return {"code": 200, "data": user_data.create_folder(
                body.get("folder_name") or "")}
        except KnowledgeStationError as e:
            status = 404 if e.code == "folder_not_found" else 409 if e.code == "folder_name_conflict" else 422
            return _json_error(status, e.code, str(e))

    @app.put("/api/v1/bookmark-folders/{folder_id}")
    def rename_bookmark_folder(folder_id: str, body: dict | None = None):
        body = body or {}
        from src.core.exceptions import KnowledgeStationError
        from src.core.storage import user_data
        try:
            return {"code": 200, "data": user_data.rename_folder(
                folder_id, body.get("folder_name") or "")}
        except KnowledgeStationError as e:
            status = 404 if e.code == "folder_not_found" else 409 if e.code == "folder_name_conflict" else 422
            return _json_error(status, e.code, str(e))

    @app.delete("/api/v1/bookmark-folders/{folder_id}")
    def delete_bookmark_folder(folder_id: str):
        """删除收藏夹：收藏本身**不删**，全部回「未分类」。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.storage import user_data
        try:
            return {"code": 200, "data": user_data.delete_folder(folder_id)}
        except KnowledgeStationError as e:
            return _json_error(404, e.code, str(e))

    @app.post("/api/v1/bookmark-folders/move-clause")
    def move_clause_bookmark(body: dict | None = None):
        """把一条条款收藏移入夹 / 移回未分类。body: {clause_key, folder_id|null}。"""
        body = body or {}
        from src.core.exceptions import KnowledgeStationError
        from src.core.storage import user_data
        try:
            moved = user_data.move_bookmark_by_clause_key(
                body["clause_key"], body.get("folder_id"))
        except KnowledgeStationError as e:
            status = 404 if e.code == "folder_not_found" else 422
            return _json_error(status, e.code, str(e))
        return {"code": 200, "data": {"moved": moved}}

    @app.post("/api/v1/bookmark-folders/move-doc")
    def move_doc_bookmark(body: dict | None = None):
        """把一条标准收藏移入夹 / 移回未分类。body: {doc_id, folder_id|null}。"""
        body = body or {}
        from src.core.exceptions import KnowledgeStationError
        from src.core.storage import user_data
        try:
            moved = user_data.move_doc_bookmark_by_doc(
                body["doc_id"], body.get("folder_id"))
        except KnowledgeStationError as e:
            status = 404 if e.code == "folder_not_found" else 422
            return _json_error(status, e.code, str(e))
        return {"code": 200, "data": {"moved": moved}}

    @app.get("/api/v1/bookmark-folders/tree")
    def bookmark_folders_tree():
        """收藏目录树（收藏 tab 数据源）。

        结构 = [收藏夹根节点] × N + [未分类]，夹内再挂**该夹收藏文档的文件目录分类路径**
        （L1→L2→L3，复用 classify_document 的四级分类口径，与 /documents/categories 同源）：
        - 标准级收藏 → 文档挂在分类叶（L4）下；条款级收藏 → 文档同样挂分类叶，
          且文档节点带 clause_bookmarks（条款叶子列表）。
        平铺返回（夹→文档→条款三段），前端组装树——目录折叠态由前端自持。
        """
        from src.core.knowledge.doc_catalog import classify_document
        from src.core.storage import user_data
        conn = get_db_connection()
        folders = user_data.list_folders()
        doc_bms = user_data.list_doc_bookmarks()
        clause_bms = user_data.list_bookmarks()

        def classify(doc_row: dict) -> dict:
            try:
                tags = json.loads(doc_row.get("domain_tags") or "[]")
            except Exception:
                tags = []
            d = {**doc_row, "domain_tags": tags if isinstance(tags, list) else []}
            d["legal_status"] = resolve_status(
                d.get("legal_status"), d.get("effective_from"))
            return classify_document(d)

        # 文档分类路径缓存（doc_id -> classify dict；未入库文档/查不到行 → None → 挂「未分类文档」兜底）
        doc_cls_cache: dict[str, dict | None] = {}
        for bm in doc_bms + clause_bms:
            did = bm.get("doc_id")
            if did is not None and did not in doc_cls_cache:
                row = conn.execute(
                    "SELECT doc_id, standard_no, standard_name, legal_status,"
                    " legal_hierarchy, effective_from, published_at, ccs_code,"
                    " ccs_name, ics, superseded_by, withdrawn_date, quality_grade,"
                    " doc_type, domain_tags, catalog_hidden FROM doc_meta"
                    " WHERE doc_id=?", (did,)).fetchone()
                doc_cls_cache[did] = classify(dict(row)) if row is not None else None

        def build_folder(fid: str | None) -> dict:
            """一个收藏夹（fid=None → 未分类）的树数据。"""
            docs: dict[str, dict] = {}
            # 标准级收藏：整本入夹
            for bm in doc_bms:
                if bm.get("folder_id") == fid:
                    docs.setdefault(bm["doc_id"], {
                        "doc_id": bm["doc_id"],
                        "doc_bookmark_id": bm["doc_bookmark_id"],
                        "standard_no": bm.get("standard_no"),
                        "standard_name": bm.get("standard_name"),
                        "legal_status": bm.get("legal_status"),
                        "doc_bookmarked": True,
                        "clause_bookmarks": [],
                    })
            # 条款级收藏：挂到对应文档下（文档未收藏也生成节点）
            for bm in clause_bms:
                if bm.get("folder_id") != fid or bm.get("doc_id") is None:
                    continue
                node = docs.setdefault(bm["doc_id"], {
                    "doc_id": bm["doc_id"],
                    "doc_bookmark_id": None,
                    "standard_no": bm.get("standard_no"),
                    "standard_name": None,  # clause JOIN 不带 standard_name，分类时补
                    "legal_status": bm.get("legal_status"),
                    "doc_bookmarked": False,
                    "clause_bookmarks": [],
                })
                node["clause_bookmarks"].append({
                    "bookmark_id": bm["bookmark_id"],
                    "clause_key": bm["clause_key"],
                    "clause_revision_id": bm.get("clause_revision_id"),
                    "clause_number": bm.get("clause_number"),
                    "title": bm.get("title"),
                    "page_start": bm.get("page_start"),
                    "remark": bm.get("remark"),
                })
            # 分类路径（L1/L2/L3/L4 名称）
            out_docs = []
            for did, node in docs.items():
                cl = doc_cls_cache.get(did)
                if cl is not None:
                    node["path"] = {"l1": cl["top_name"], "l2": cl["level2"],
                                    "l3": cl["level3"], "l4": cl["level4"]}
                else:
                    node["path"] = None
                if not node.get("standard_name"):
                    row = conn.execute(
                        "SELECT standard_name FROM doc_meta WHERE doc_id=?",
                        (did,)).fetchone()
                    node["standard_name"] = row["standard_name"] if row else None
                node["clause_bookmarks"].sort(
                    key=lambda c: _clause_number_sort_key(c.get("clause_number") or ""))
                out_docs.append(node)
            return {"docs": out_docs}

        out_folders = []
        for f in folders:
            payload = build_folder(f["folder_id"])
            out_folders.append({
                "folder_id": f["folder_id"],
                "folder_name": f["folder_name"],
                "doc_count": f["doc_count"],
                "clause_count": f["clause_count"],
                "docs": payload["docs"],
            })
        unfiled = build_folder(None)
        out_folders.append({
            "folder_id": None,
            "folder_name": "未分类",
            "doc_count": sum(1 for d in doc_bms if d.get("folder_id") is None),
            "clause_count": sum(1 for b in clause_bms if b.get("folder_id") is None),
            "docs": unfiled["docs"],
        })
        return {"code": 200, "data": out_folders}

    @app.get("/api/v1/annotations")
    def get_annotations(clause_key: str | None = None):
        from src.core.storage import user_data
        return {"code": 200, "data": user_data.list_annotations(clause_key)}

    @app.post("/api/v1/annotations")
    def add_annotation(body: dict | None = None):
        body = body or {}
        from src.core.storage import user_data
        from src.core.exceptions import KnowledgeStationError
        try:
            out = user_data.add_annotation(body["clause_key"], body["content"],
                                           body.get("annotation_type", "personal"))
        except KnowledgeStationError as e:
            return _json_error(422, e.code, str(e))
        return {"code": 200, "data": out}

    @app.delete("/api/v1/annotations/{annotation_id}")
    def del_annotation(annotation_id: str):
        from src.core.storage import user_data
        if not user_data.delete_annotation(annotation_id):
            return _json_error(404, "annotation_not_found", f"批注不存在: {annotation_id}")
        return {"code": 200, "data": {"removed": True}}

    @app.get("/api/v1/projects")
    def get_projects():
        from src.core.storage import user_data
        return {"code": 200, "data": user_data.list_projects()}

    @app.post("/api/v1/projects")
    def create_project(body: dict | None = None):
        body = body or {}
        from src.core.storage import user_data
        return {"code": 200, "data": user_data.create_project(
            body["project_name"], body.get("project_type", "engineering"))}

    @app.post("/api/v1/projects/{project_id}/clauses")
    def project_add_clause(project_id: str, body: dict | None = None):
        body = body or {}
        from src.core.storage import user_data
        from src.core.exceptions import KnowledgeStationError
        try:
            out = user_data.add_clause_to_project(project_id, body["clause_revision_id"])
        except KnowledgeStationError as e:
            return _json_error(404, e.code, str(e))
        return {"code": 200, "data": out}

    @app.delete("/api/v1/projects/{project_id}/clauses/{clause_revision_id}")
    def project_remove_clause(project_id: str, clause_revision_id: str):
        from src.core.storage import user_data
        from src.core.exceptions import KnowledgeStationError
        try:
            out = user_data.remove_clause_from_project(project_id, clause_revision_id)
        except KnowledgeStationError as e:
            return _json_error(404, e.code, str(e))
        return {"code": 200, "data": out}

    @app.post("/api/v1/compliance/policies")
    def import_policy(body: dict | None = None):
        body = body or {}
        from src.core.compliance.gap_analysis import import_internal_policy
        return {"code": 200, "data": import_internal_policy(
            body["policy_name"], body["policy_text"])}

    @app.get("/api/v1/compliance/policies")
    def list_policies():
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT policy_id, policy_name, file_path, created_at"
            " FROM internal_policy ORDER BY created_at DESC").fetchall()
        return {"code": 200, "data": [dict(r) for r in rows]}

    @app.post("/api/v1/compliance/gap-analysis")
    def run_gap(body: dict | None = None):
        body = body or {}
        from src.core.compliance.gap_analysis import run_gap_analysis
        from src.core.exceptions import KnowledgeStationError
        try:
            return {"code": 200, "data": run_gap_analysis(body["policy_id"])}
        except KnowledgeStationError as e:
            return _json_error(404, e.code, str(e))

    @app.get("/api/v1/documents/{doc_id}/versions")
    def doc_versions(doc_id: str):
        """R29 版本替代链（旧→新）。"""
        from src.core.storage.versioning import version_chain
        chain = version_chain(doc_id)
        if not chain:
            return _json_error(404, "doc_not_found", f"文档不存在: {doc_id}")
        return {"code": 200, "data": {"chain": chain,
                                        "has_versions": len(chain) > 1}}

    @app.get("/api/v1/documents/{doc_id}/clauses-by-prefix")
    def clauses_by_prefix(doc_id: str, prefix: str):
        """目录展开：某章/节前缀下的全部条款（如 prefix=5 → 5.x 全部；prefix=5.1 → 5.1.x 全部）。
        目录点小三角时懒加载；每项含 clause_number/page_start 供跳转。"""
        prefix = (prefix or "").strip().rstrip(".")
        import re as _re
        if not prefix or not _re.match(r"^\d{1,2}(\.\d{1,2})?$", prefix):
            return _json_error(422, "invalid_prefix", f"前缀格式非法: {prefix}")
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT clause_number, page_start FROM clause_revision"
            " WHERE doc_id=? AND content_type='normal'"
            " AND (clause_number=? OR clause_number LIKE ?) ORDER BY rowid",
            (str(doc_id), prefix, prefix + ".%")).fetchall()
        if not rows:
            return _json_error(404, "no_clauses", f"无条款: 前缀 {prefix}")
        return {"code": 200, "data": [dict(r) for r in rows]}

    @app.get("/api/v1/documents/{doc_id}/clauses")
    def doc_full_clauses(doc_id: str):
        """某文档全部条款富文本（2026-08-27 页级文本预览主视图）。

        返回每条 clause_revision_id/clause_number/title/content_text/content_html/page_start。
        前端据此按 page_start 聚合成「按页文本块」，与 PDF 原件栏同步翻页对照。
        """
        conn = get_db_connection()
        # 2026-08-29 附录进全文预览（通用）：附录（含规范性附录的表 A.1/B.1）是标准
        # 正文组成部分，缺失即用户报告的"附录内容呢？"。前置说明（封面文字）不进——
        # 非条文，且与 doc_meta 元数据重复。rowid 序 = 切分序 = 文档阅读序（附录殿后）。
        rows = conn.execute(
            "SELECT cr.clause_revision_id, cr.clause_number, cr.title, cr.content_text,"
            " cr.content_markdown, cr.page_start, cr.page_end, cr.page_breaks,"
            " cr.figure_html"
            " FROM clause_revision cr WHERE cr.doc_id=?"
            " AND cr.content_type IN ('normal','附录')"
            " ORDER BY cr.rowid", (str(doc_id),)).fetchall()
        if not rows:
            return _json_error(404, "no_clauses", f"无条款: doc {doc_id}")
        # 2026-09-01 表格归位：一次批量取全部条款的表格 span 页号（按 sort_order
        # 即条目序，与 content_markdown 的 <table> 出现序同源对齐），供
        # _content_html 把每张表插回原文页位。无 span 的存量条款 → 空表 →
        # 渲染层自动回退旧的末尾追加。
        crids = [r["clause_revision_id"] for r in rows]
        tbl_pg_map: dict[str, list[int]] = {}
        row_box_map: dict[str, list[list[float]]] = {}
        if crids:
            ph = ",".join("?" * len(crids))
            for s in conn.execute(
                    f"SELECT clause_revision_id, page_number FROM source_span"
                    f" WHERE clause_revision_id IN ({ph}) AND span_type='table'"
                    f" ORDER BY clause_revision_id, sort_order", crids):
                tbl_pg_map.setdefault(s["clause_revision_id"], []).append(
                    s["page_number"])
            # 2026-09-02 双栏版面：行级 bbox（span_type='text'，B5 行级）按
            # sort_order = content_text 行序 → _content_html 据此判双栏页并两列
            # 布局还原（x0 分左右栏、y 为阅读序）。无行 bbox（存量未采集 B5）→
            # 渲染层自动回退流式（零行为变化）。
            for s in conn.execute(
                    f"SELECT clause_revision_id, bbox_json FROM source_span"
                    f" WHERE clause_revision_id IN ({ph}) AND span_type='text'"
                    f" AND bbox_json IS NOT NULL"
                    f" ORDER BY clause_revision_id, sort_order", crids):
                try:
                    b = json.loads(s["bbox_json"])
                    if isinstance(b, list) and len(b) == 4:
                        row_box_map.setdefault(
                            s["clause_revision_id"], []).append([float(x) for x in b])
                except Exception:
                    continue
        _chart_done: set = set()
        _asset_done: set = set()
        clauses = [{
            "clause_revision_id": r["clause_revision_id"],
            "clause_number": r["clause_number"],
            "title": r["title"],
            "content_text": r["content_text"],
            "content_html": _content_html(r["content_text"], r["content_markdown"],
                                          str(doc_id), r["clause_number"],
                                          page_breaks=r["page_breaks"],
                                          figure_html=r["figure_html"],
                                          table_pages=tbl_pg_map.get(
                                              r["clause_revision_id"]),
                                          chart_done=_chart_done,
                                          asset_done=_asset_done,
                                          row_boxes=row_box_map.get(
                                              r["clause_revision_id"]),
                                          page_start=r["page_start"],
                                          page_end=r["page_end"]),
            "page_start": r["page_start"],
        } for r in rows]
        return {"code": 200, "data": {"doc_id": str(doc_id), "clauses": clauses}}

    @app.get("/api/v1/documents/{doc_id}/assets/{fname}")
    def doc_asset(doc_id: str, fname: str):
        """C1 解析图片资产回源（2026-09-01 排版还原批次1）。

        MinerU 深度解析把插图落盘 parse_out/<doc_id>/**/images/<sha256>.jpg
        （middle.json 以 image_path 相对引用，前端 content_markdown 的裸
        <img> 由 C2 补 src 后经此端点取图）。防穿越双闸：fname 白名单
        ^[0-9a-f]{64}\\.(jpg|jpeg|png)$（单段文件名、无路径成分）+ doc_id
        ULID 形态校验；命中后再验 resolve() 仍落在 parse_out/<doc_id> 内。
        """
        import re
        if (not re.fullmatch(r"doc_[0-9A-Z]{26}", doc_id)
                or not re.fullmatch(r"[0-9a-f]{64}\.(?:jpg|jpeg|png)", fname)):
            return _json_error(404, "file_not_found", "非法资产标识")
        base = (get_settings().data_dir / "parse_out" / doc_id).resolve()
        if not base.is_dir():
            return _json_error(404, "file_not_found", f"无解析产物: {doc_id}")
        matches = sorted(base.glob(f"**/images/{fname}"))
        if not matches:
            return _json_error(404, "file_not_found", f"资产不存在: {fname}")
        target = matches[0].resolve()
        if base not in target.parents:
            return _json_error(403, "forbidden", "非法路径")
        media = "image/png" if fname.lower().endswith(".png") else "image/jpeg"
        hdr: dict[str, str] = {"Cache-Control": "max-age=86400"}
        # 2026-09-02 需求2（截图与原版同尺寸同位）：按裁剪文件名反查原图
        # bbox → 相对页宽/页高的比例头，前端还原尺寸与水平位置。
        try:
            from src.core.middle_geo import load as _load_middle_geo
            _geo = _load_middle_geo(base)
            _hit = _geo.image_bbox_by_path(fname) if _geo is not None else None
            if _hit is not None:
                _pno, _bbox = _hit
                assert _geo is not None  # _hit 非空蕴含 _geo 已加载
                _sz = _geo.size(_pno)
                if _sz and _sz[0] > 0 and _sz[1] > 0 and len(_bbox) == 4:
                    hdr["X-Frac-X0"] = f"{_bbox[0] / _sz[0]:.6f}"
                    hdr["X-Frac-W"] = f"{(_bbox[2] - _bbox[0]) / _sz[0]:.6f}"
                    hdr["X-Frac-H"] = f"{(_bbox[3] - _bbox[1]) / _sz[1]:.6f}"
        except Exception:   # noqa: BLE001 - 比例头缺失不影响取图
            pass
        return FileResponse(str(target), media_type=media, headers=hdr)

    @app.post("/api/v1/compare")
    def compare_docs_endpoint(body: dict | None = None):
        """R42 版本对照 / R16 跨标准对比（含 R49 模态变化清单）。

        ⚠ `def` 而不是 `async def`（§10.86 通则之一）：本端点**唯一**的 `await` 只是
        `request.json()` ⇒ 读完 body 之后全是同步活，留在事件循环里只会占住它。
        body 改走签名（坏 body 由 FastAPI 直接 422，与 §10.79/§10.83 同口径；
        缺 `doc_a`/`doc_b` 仍是 `KeyError` → 500，与改前一致）。
        """
        body = body or {}
        from src.core.storage.versioning import compare_docs
        from src.core.exceptions import KnowledgeStationError
        try:
            data = compare_docs(body["doc_a"], body["doc_b"])
        except KnowledgeStationError as e:
            return _json_error(404, e.code, str(e))
        return {"code": 200, "data": data}

    @app.get("/api/v1/operation-log")
    def operation_log(limit: int = 50):
        """R8/R11 知识库更新时间线（operation_log + event_log 聚合，倒序）。"""
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT 'op' AS src, operation AS event_type, target_type, target_id,"
            " detail, created_at FROM operation_log"
            " UNION ALL"
            " SELECT 'ev', event_type, target_type, target_id, metadata, created_at"
            " FROM event_log"
            " WHERE event_type NOT LIKE 'write_queue%'"
            " ORDER BY created_at DESC, src DESC LIMIT ?", (limit,)).fetchall()
        return {"code": 200, "data": [dict(r) for r in rows]}

    @app.post("/api/v1/aliases/extract")
    def aliases_extract(body: dict | None = None):
        """R48 术语抽取（对库内已有文档的'术语和定义'章节）。"""
        body = body or {}
        doc_id = body.get("doc_id")
        conn = get_db_connection()
        # 整文档按 rowid 拼接再抽取：MinerU 切分会把"编号/术语/定义"拆到
        # 不同条款，逐条款抽取会丢失行结构（语义必须保留全文拼接）。
        # 2026-08-26：无 doc_id 全库场景改为分段拉取拼接（分批 LIMIT，
        # 避免大结果集一次性物化全部 Row；35k 文档量级时文本本身仍占内存，属批处理设计意图）。
        cond, args = (" WHERE doc_id = ? ", [doc_id]) if doc_id else ("", [])
        text_parts: list[str] = []
        batch, start = 2000, 0
        while True:
            part = conn.execute(
                f"SELECT content_text FROM clause_revision{cond} ORDER BY rowid LIMIT ? OFFSET ?",
                [*args, batch, start]).fetchall()
            if not part:
                break
            text_parts.extend(r["content_text"] for r in part)
            start += batch
            if len(part) < batch:
                break
        from src.core.knowledge.alias_extract import extract_terms_from_text
        total = len(extract_terms_from_text("\n".join(text_parts), source_doc_id=doc_id))
        n = conn.execute("SELECT COUNT(*) FROM alias_store").fetchone()[0]
        return {"code": 200, "data": {"extracted": total, "alias_total": n}}

    @app.post("/api/v1/export/citations")
    def export_citations(body: dict | None = None):
        """R19 引用块（**纯文本**，供前端一键复制）。

        ⚠ §10.76：body 走**函数签名**而不是 `await request.json()`——本端点另有同步活
        （SQL 取证据），必须留在**线程池**里。
        ⚠ **措辞更正**（独立复核 b13 的 LOW-1）：这里原先写"非法 JSON 由**吞成空 body**
        变成 422"——**错了**。实测这条端点**从来没有** `except` 包着读 body ⇒ 改前
        **坏 JSON 是未捕获异常 → 500**（连**没有 body** 也是 500，同一句也抄进了
        `test_phase7.py` 与台账）。方向（收紧成 422）不变，但事实是 **500 → 422**，
        而且顺带修掉了一个没人注意的"没 body 就 500"。

        ⚠ **2026-09-19（EXECUTION-PLAN 第 4 步）**：原先这里还顺手落一份 Word
        （`export_qa_citations_docx`，响应里的 `docx` 字段）——业主否决 Word/PPT 交付物
        （`docs/NOT-DOING.md` 第 1 条）⇒ **已拆除**，响应现在只有 `citation_text`。
        """
        body = body or {}
        from src.core.exports.report_export import build_citation_block
        conn = get_db_connection()
        ids = body.get("clause_revision_ids") or []
        evidences = []
        ph = ",".join("?" * len(ids)) if ids else None
        if ph:
            evidences = [dict(r) for r in conn.execute(
                f"SELECT cr.clause_number, cr.title, cr.content_text, cr.page_start,"
                f" dm.standard_no FROM clause_revision cr"
                f" JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
                f" WHERE cr.clause_revision_id IN ({ph})", ids).fetchall()]
        text = build_citation_block(evidences)
        return {"code": 200, "data": {"citation_text": text}}

    @app.get("/api/v1/export/download")
    def download_export(name: str):
        """下载导出文件（严格限制在 exports 目录内，防路径穿越）。"""
        from src.core.exports.report_export import _exports_dir
        base = _exports_dir().resolve()
        target = (base / name).resolve()
        if base not in target.parents:
            return _json_error(403, "forbidden", "非法路径")
        if not target.exists():
            return _json_error(404, "file_not_found", f"文件不存在: {name}")
        return FileResponse(str(target), filename=target.name)

    @app.post("/api/v1/chat/completions")
    async def chat_completions(request: Request):
        """SSE 骨架：evidence → status → delta → verification → done。

        第一阶段 delta 为规则拼装的占位答案；DeepSeek 真实流式在 T06 接入。
        """
        body = await request.json()
        query = body.get("query", "")
        # ⚠ §10.94：本端点**唯一**剩下的 `async def`，而它进生成器前要跑同步检索。
        # 冷启动的两次一次性慢初始化（fastembed 下载/加载 ≈5.2s + jieba 词典 ≈0.33s）
        # **必须在进循环体之前、在线程里**付掉——否则启动后第一次提问把整个引擎冻住 ≈6.8s
        # （实测见 `warm_retrieval_stack()` 的 docstring）。
        import anyio as _anyio
        await _anyio.to_thread.run_sync(warm_retrieval_stack)
        history = body.get("history") or []   # R60: 多轮历史 [{role, content}]（可选）
        top_k = body.get("top_k", 3)
        channels = body.get("channels")
        include_superseded = body.get("include_superseded", False)
        # P9.4: Debug Trace 默认全量落库（回答不如意时回溯定位问题环节）
        dump_enabled = bool(body.get("dump", True))
        query_mode = body.get("query_mode", "default")  # R9 四档：thorough/default/quick/guess
        answer_scope = body.get("answer_scope", "concise")  # R59: concise/full
        import time as _t
        _trace_start = _t.perf_counter()
        trace = {"stage": "start", "query": query, "query_mode": query_mode,
                 "answer_scope": answer_scope, "history_turns": len(history)}

        # ===== Phase 9.2 Query Understanding Layer（R9/R40/R41/R52/R53/R60）=====
        from src.core.query import understanding as qu

        declared_slots, clean_query = qu.parse_declared(query)
        # 主题作用域槽位提取（通用）：非建筑主题不提取高度等建筑槽位，
        # 避免「4米高处作业」被误标为建筑高度（数值在原文里，LLM 直接可见）
        theme0 = qu.detect_theme(clean_query)
        slots = {**declared_slots, **qu.extract_slots(clean_query, theme=theme0)}
        intent = qu.classify_intent(clean_query)
        # R60 基础：否定维度纠错 → 以正确维度重检索
        correction = qu.detect_correction(clean_query)
        if correction and correction.get("right"):
            clean_query = f"{clean_query} {correction['right']}"
        search_query_raw = clean_query or query
        trace.update({"stage": "query_understanding",
                      "intent": intent, "slots": slots,
                      "declared_slots": declared_slots,
                      "clean_query": clean_query,
                      "correction": correction,
                      "elapsed_ms": round((_t.perf_counter() - _trace_start) * 1000)})

        # R9（v2，通用路径）：不再用规则槽位表判定追问——
        # 统一走检索 + LLM 单次自判「问还是答」（SYSTEM_PROMPT 规则 9）：
        #   关键信息缺失且无法用常识/默认场景推断 → LLM 只输出一行 {"ask":["...",...≤3]}
        #   否则直接作答（常识/假设可用）。一次最多问 3 个点，历史中已有追问不再重复问。
        theme = qu.detect_theme(clean_query)
        user_turns = sum(1 for m in history if m.get("role") == "user")
        trace.update({"stage": "clarify_policy", "theme": theme,
                      "user_turns": user_turns, "mode": "llm-judged"})

        from src.core.retrieval.hybrid_engine import (
            search_with_details, expand_query_with_history)
        from src.core.knowledge.alias_extract import expand_with_alias
        refined = qu.refine_search_query(search_query_raw, intent, theme)
        search_query = expand_with_alias(  # R48 别名反查 + R9 追问增强
            expand_query_with_history(refined, history))
        _t_retr = _t.perf_counter()
        # ⚠ `rerank` 显式写 False：`perform_hybrid_search` 的默认值是 `True`，但 2026-10-09 之前
        #   重排阶段**恒空转**（总纲 P0·0.7 的返回形状缺陷 ⇒ 排序退化成恒等置换）⇒ 那个默认值
        #   一直等价于关闭。0.7 修好后它会**真的重排**，而"要不要把重排接进生产"是**未复核的行为
        #   改动**（实测与判决见 `eval/recall-funnel/exp-11-rerank-fix/`）⇒ 这里显式写 False，
        #   保持与本批之前**逐位等价**的行为。要开启请先改这里，并走必验流程。
        out = search_with_details(search_query, top_k=top_k, channels=channels,
                                  include_superseded=include_superseded,
                                  rerank=False)
        # R5a 证据链扩展：被引用条款并入证据（LLM 可见），主证据不足时自动补链
        evidences = list(out["results"])
        _seen_ids = {e.clause_revision_id for e in evidences}
        for _ex in out.get("expanded", []):
            _cl = _ex.get("clause")
            if _cl and _cl.clause_revision_id not in _seen_ids:
                evidences.append(_cl)
                _seen_ids.add(_cl.clause_revision_id)
        trace.update({"stage": "retrieval",
                      "refined_query": refined,
                      "search_query": search_query,
                      "raw_results": [f"{e.standard_no}-{e.clause_number}"
                                      for e in evidences],
                      "retrieval_ms": round((_t.perf_counter() - _t_retr) * 1000)})
        # R52 条件感知过滤 + R40 强标/层级置顶
        filtered = qu.apply_condition_filter(evidences, slots)
        evidences = qu.rank_with_hierarchy(filtered)
        trace.update({"stage": "filter_rank",
                      "filtered_out": [f"{e.standard_no}-{e.clause_number}"
                                       for e in evidences
                                       if e not in filtered],
                      "final_evidence": [f"{e.standard_no}-{e.clause_number}"
                                         for e in evidences],
                      "elapsed_ms": round((_t.perf_counter() - _trace_start) * 1000)})

        # 阶段4 富化上下文：收藏集合 + 批注映射 + 时效警示（R11/R24/R25/R33）
        from src.core.storage import user_data
        try:
            _bm_keys = user_data.bookmarked_clause_keys()
            _ann_cache = user_data.annotations_by_clause_keys(
                [e.clause_key for e in evidences])
        except Exception:
            _bm_keys, _ann_cache = set(), {}
        time_warnings = []
        _warned_docs = set()
        for e in evidences:
            # 时效提醒用翻转后状态：upcoming 且实施日期已到 → 按现行，不再误报"尚未生效"
            flipped = resolve_status(e.legal_status, getattr(e, "effective_from", None))
            if flipped in ("upcoming", "superseded") and e.doc_id not in _warned_docs:
                _warned_docs.add(e.doc_id)
                if flipped == "upcoming":
                    time_warnings.append(
                        f"【时效提醒】{e.standard_no} 尚未生效（即将实施版本），以下为即将实施的规定")
                else:
                    time_warnings.append(
                        f"【时效提醒】{e.standard_no} 已废止，请确认是否需要现行版本")
        # 标题条款子条款聚合：命中"8.1 作业分级"标题时附带 8.1.1~8.1.x 内容条款
        evidences = _expand_title_clauses(evidences)
        # 2026-08-26（P3-①）：patch_records 批量预取（消除 _ev_dict 内逐条查询的 N+1）
        _patch_cache: dict = {}
        try:
            _ids = [e.clause_revision_id for e in evidences]
            if _ids:
                _ph = ",".join("?" * len(_ids))
                for r in get_db_connection().execute(
                        f"SELECT clause_revision_id, field_name, patched_value,"
                        f" patch_reason, created_at, updated_at FROM clause_patch"
                        f" WHERE clause_revision_id IN ({_ph})"
                        f" ORDER BY updated_at DESC", _ids).fetchall():
                    _patch_cache.setdefault(r["clause_revision_id"], []).append(dict(r))
        except Exception:
            _patch_cache = {}
        ev_dicts = [_ev_dict(e, _bm_keys, _ann_cache, _patch_cache) for e in evidences]

        # T06: 优先真实 LLM 流式；未配 Key / 调用失败 → 占位答案降级（R30 精神）
        use_llm = bool(get_settings().llm_api_key)

        # R9 参数标注 + R53 依据充分度（回答尾部追加）
        # 标注与注入仅限建筑主题（防「高度3米」被误当建筑高度带偏 LLM）；
        # 其他主题的槽位在后台保留但不展示不注入（数字在原文/历史里，LLM 直接可见）
        slots_note = ""
        if slots and theme == 'building':
            labels = {"building_type": "建筑类型", "fire_risk": "火灾危险性",
                      "fire_resistance": "耐火等级", "height": "建筑高度",
                      "subject": "主体", "object": "客体", "behavior": "行为",
                      "consent": "同意状态"}
            slots_note = "已识别参数/要素：" + "、".join(
                f"{labels.get(k, k)}={v}" for k, v in slots.items())
        suff_note = qu.sufficiency_note(intent, len(evidences))
        llm_prompt_query = query
        if slots and theme == 'building':
            llm_prompt_query = f"{query}\n（场景参数：{slots_note}；若参数不适用请说明，"
            "回答时标注前提假设）"

        async def event_stream():
            yield _sse("evidence", {
                "evidences": ev_dicts,
                "time_warnings": time_warnings,
                "expanded_evidences": [
                    {"clause_revision_id": x["clause"].clause_revision_id,
                     "expanded_from": x["expanded_from"],
                     "edge_type": x["edge_type"],
                     "standard_no": x["clause"].standard_no,
                     "clause_number": x["clause"].clause_number,
                     "content_text": (x["clause"].content_text or "")[:400],
                     "page_start": x["clause"].page_start}
                    for x in out.get("expanded", [])]})
            yield _sse("status", {"phase": "streaming_with_verification_pending",
                                  "message": "核验中..."})
            answer_parts: list[str] = []
            try:
                if use_llm:
                    import anyio
                    import json as _json
                    from src.core.llm.deepseek_client import stream_chat_completion
                    # 档位提示：guess 强制作答；quick 仅在完全缺失关键信息时提问
                    mode_hint = ""
                    if query_mode == "guess":
                        mode_hint = "\n（用户档位：guess——请直接作答，不要提问。）"
                    elif query_mode == "quick":
                        mode_hint = "\n（用户档位：quick——除非关键信息完全缺失，否则直接作答。）"
                    gen = stream_chat_completion(
                        llm_prompt_query + mode_hint, ev_dicts, history=history,
                        allow_clarify=user_turns < 2)  # 追问死循环修复：≥2 轮强制作答

                    def _next_chunk():
                        try:
                            return next(gen)
                        except StopIteration:
                            return None

                    # ask 检测：LLM 若选择追问，只会输出一行 {"ask":[...]}；否则是正文。
                    # 缓冲开头若干字符，解析成功则发 clarify 事件，否则按答案流式输出。
                    ask_buf = ""
                    ask_done = False
                    while True:
                        part = await anyio.to_thread.run_sync(_next_chunk)
                        if part is None:
                            break
                        if ask_done:
                            answer_parts.append(part)
                            yield _sse("delta", {"content": part})
                            continue
                        ask_buf += part
                        stripped = ask_buf.lstrip()
                        if stripped.startswith("{"):
                            if len(ask_buf) >= 6:
                                try:
                                    _obj = _json.loads(ask_buf)
                                    _qs = _obj.get("ask")
                                    if isinstance(_qs, list) and _qs and all(
                                            isinstance(x, str) for x in _qs):
                                        ask_done = True
                                        questions = _qs[:3]
                                        if dump_enabled:
                                            trace.update({"stage": "clarify_llm",
                                                          "questions": questions})
                                            _write_debug_dump(
                                                query, search_query, ev_dicts, "",
                                                None, None, history, trace,
                                                clarify=questions)
                                        yield _sse("clarify", {
                                            "questions": questions,
                                            "mode": "llm",
                                            "hint": "请一次性补充以上关键信息后继续提问（最多问一轮）。"})
                                        yield _sse("done", {})
                                        return
                                except Exception:
                                    pass
                                if len(ask_buf) > 800:
                                    ask_done = True
                                    answer_parts.append(ask_buf)
                                    yield _sse("delta", {"content": ask_buf})
                                    ask_buf = ""
                        else:
                            ask_done = True
                            if ask_buf:
                                answer_parts.append(ask_buf)
                                yield _sse("delta", {"content": ask_buf})
                            ask_buf = ""
                    # 流结束仍残留缓冲：最后再判定一次
                    if ask_buf:
                        stripped = ask_buf.lstrip()
                        if stripped.startswith("{"):
                            try:
                                _obj = _json.loads(ask_buf)
                                _qs = _obj.get("ask")
                                if isinstance(_qs, list) and _qs and all(
                                        isinstance(x, str) for x in _qs):
                                    if dump_enabled:
                                        _write_debug_dump(
                                            query, search_query, ev_dicts, "",
                                            None, None, history, trace,
                                            clarify=_qs[:3])
                                    yield _sse("clarify", {
                                        "questions": _qs[:3], "mode": "llm",
                                        "hint": "请一次性补充以上关键信息后继续提问（最多问一轮）。"})
                                    yield _sse("done", {})
                                    return
                            except Exception:
                                pass
                        answer_parts.append(ask_buf)
                        yield _sse("delta", {"content": ask_buf})
                else:
                    answer = _placeholder_answer(query, evidences)
                    for i in range(0, len(answer), 8):
                        chunk = answer[i:i + 8]
                        answer_parts.append(chunk)
                        yield _sse("delta", {"content": chunk})
                        await asyncio.sleep(0.01)
            except Exception as e:  # noqa: BLE001 - LLM 失败降级占位答案
                answer = _placeholder_answer(query, evidences)
                for i in range(0, len(answer), 8):
                    chunk = answer[i:i + 8]
                    answer_parts.append(chunk)
                    yield _sse("delta", {"content": chunk})
                    await asyncio.sleep(0.01)
                yield _sse("status", {"phase": "llm_degraded",
                                      "message": f"大模型不可用，已降级占位答案: {e}"})

            trace.update({"stage": "llm_generation",
                          "llm_used": use_llm,
                          "llm_ms": round((_t.perf_counter() - _trace_start) * 1000)})
            # R9/R53: 回答尾部追加已识别参数标注与依据充分度提示
            tail_notes = []
            joined = "".join(answer_parts)
            # 去重：LLM 可能已复述标注/提示，避免重复追加
            if slots_note and slots_note not in joined:
                tail_notes.append(f"\n\n[{slots_note}]")
            if suff_note and suff_note not in joined:
                tail_notes.append(f"\n{suff_note}")
            if tail_notes:
                for seg in tail_notes:
                    answer_parts.append(seg)
                    yield _sse("delta", {"content": seg})

            # T06: 分型核验（数值/模态/法理）——核验输入用全量条款文本
            # （ev_dicts 的 content_text 被截断，数值可能落在截断外 → 误判篡改，v5 实测修复）
            from src.core.verification.typed_verifier import verify_llm_output
            ev_full = _full_evidence(ev_dicts)
            verification = verify_llm_output("".join(answer_parts), ev_full)
            # R24: 答案层置信度分级（high/mid/low）
            answer_confidence = _answer_confidence(verification, ev_dicts)
            yield _sse("verification", {
                "is_valid": verification.is_valid,
                "answer_confidence": answer_confidence["level"],
                "confidence_reasons": answer_confidence["reasons"],
                "knowledge_types_involved": sorted({e["knowledge_type"] for e in ev_dicts}),
                "unsupported_clauses": verification.unsupported_clauses,
                # 2026-09-16 增量字段（事件顺序不变，仅加字段）：每条证据外条款号的
                # 可操作说明（属于哪部标准 / 检索未召回 vs 模型越界）。见契约台账。
                "unsupported_context": verification.unsupported_context,
                "unverified_numbers": verification.unverified_numbers,
                "modality_violations": [v.model_dump() for v in verification.modality_violations],
                "legal_element_violations": verification.legal_element_violations,
            })
            if dump_enabled:
                trace.update({"stage": "verification",
                              "is_valid": verification.is_valid,
                              "answer_confidence": answer_confidence["level"],
                              "total_ms": round((_t.perf_counter() - _trace_start) * 1000)})
                _write_debug_dump(query, search_query, ev_dicts,
                                   "".join(answer_parts), verification,
                                   answer_confidence, history, trace)
            yield _sse("done", {})

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    def _write_debug_dump(query, search_query, ev_dicts, answer,
                           verification, answer_confidence, history,
                           trace: dict | None = None, clarify: list | None = None) -> None:
        """P9.4 Debug Trace：完整数据流（理解层→检索→过滤→LLM→核验）落库。
        回答不如意时按阶段回溯定位问题环节。默认每次提问都记录。
        """
        from ulid import ULID
        try:
            conn = get_db_connection()
            evs = [{'standard_no': e.get('standard_no'),
                    'clause_number': e.get('clause_number'),
                    'modality': e.get('modality'),
                    'knowledge_type': e.get('knowledge_type')} for e in ev_dicts]
            # 2026-09-16（iteration-6 自查 §1）：兼容 **dict** 形态的 verification。
            # `/ks/answer` 走 `ks_answer._assemble_verification()`，返回的是**普通 dict**
            # （不是 Pydantic 模型）——旧实现在该分支上求值 `verification.is_valid`，
            # 对 dict 抛 AttributeError，被本函数的 except 吞成一条 warning，
            # 结果是"看起来写了、实际什么都没写"。原三元式只覆盖了 SSE 路径的模型形态。
            if verification is None:
                vres = {'is_valid': False}
            elif isinstance(verification, dict):
                vres = dict(verification)
            elif hasattr(verification, 'model_dump'):
                vres = verification.model_dump()
            else:
                vres = {'is_valid': bool(getattr(verification, 'is_valid', False))}
            vjson = json.dumps(vres, ensure_ascii=False, default=str)
            logs = json.dumps({'trace': trace or {},
                              'answer_confidence': answer_confidence,
                              'clarify': clarify}, ensure_ascii=False)
            retr = json.dumps({'search_query': search_query, 'evidences': evs},
                              ensure_ascii=False)
            prompt = json.dumps({'history': history[-4:]}, ensure_ascii=False)
            conn.execute(
                'INSERT INTO debug_dump (dump_id, trigger_type, query,'
                ' retrieval_result, prompt, llm_output, verification_result, logs)'
                ' VALUES (?,?,?,?,?,?,?,?)',
                (f'dump_{ULID()}', 'user_export', query, retr, prompt,
                 (answer or '')[:4000], vjson, logs))
            # ⚠ **按类型清理**（2026-09-25 修真缺陷）：原先这里是**全表**裁到 1000 行，
            #   而外发审计量大（约 110 条/天）⇒ **把提问证据挤出去**——而这一路写的
            #   `retrieval_result`（命中了哪些标准号+条款号）**不可再生**，是 P1/P5 要用的
            #   （实测当时 1,000 行里只剩 8 行带它）。详见
            #   `src/core/storage/debug_dump_retention.py` 的模块说明。
            from src.core.storage.debug_dump_retention import (
                KEEP_QUESTION_EVIDENCE, TYPE_QUESTION, prune as prune_debug_dump,
            )
            prune_debug_dump(conn, TYPE_QUESTION, KEEP_QUESTION_EVIDENCE)
            conn.commit()
        except Exception as e:  # noqa: BLE001
            logger.warning("debug_dump 写入失败: %s", e)

    def _write_ks_answer_dump(data: dict, history: list | None = None) -> None:
        """把 `/ks/answer`（取证答案）落进 debug_dump —— **D2 外发审计履行**。

        背景（2026-09-16，iteration-6 自查 §1，已代码级核实）：
        本端点此前**零落库** —— 既不写 debug_dump，也不写 `record_egress`。
        而它正是 `/forensic` 强制走的那条取证链路（`plugin/src/chatmode.js:9`
        「凡涉法规/国标/合规的问题必须走 ks_answer 取证链路」），且内部会真发一次
        云端 LLM 调用（`ks_answer._stream_llm()` → `OpenAI(api_key=...)`）。
        审计侧只认 `egress_audit._AUDIT_TRIGGER_TYPES = ("user_export","egress")`，
        故该路径的完整 payload 在 `/api/v1/egress/audit` 与导出里**完全不可见**，
        与 `ENCYCLOPEDIA` §1.5 承诺 4 / `INTRODUCTION` §三.10 的"每次云调用（LLM/OCR）的
        完整 payload 落库，UI 可查可导出"直接冲突。

        说明两点边界（不要当它已经解决）：
        1. `ks_answer.answer()` 返回的 `_meta` **本就注明"供已接入的 debug_dump"**
           （`ks_answer.py:687`）——数据一直是准备好的，只是从未接线。
        2. `trigger_type` 沿用 `'user_export'`（与 SSE 路径同口径），**无需改
           `_AUDIT_TRIGGER_TYPES`**。⚠ **保留策略已在 2026-09-25 改掉，这句随之更正**：
           原写"`debug_dump` 有「1000 行滚动」保留策略、生产库约 50 分钟写满一轮，
           故本记录的可查窗口仍然很短"——**现在按类型各自清理**（审计 1000 /
           **提问证据 5000**），所以**本路径写的这条记录不再与审计同寿**，
           不会被审计的量挤掉。⚠ 但"窗口"仍由**写入速率**决定（审计忙碌时实测约 50 分钟
           写满它自己那一档），论"天"没有意义；详见
           `src/core/storage/debug_dump_retention.py` 的模块说明。
        """
        if not isinstance(data, dict):
            return
        meta = data.get("_meta") or {}
        verification = data.get("verification")
        vconf = verification if isinstance(verification, dict) else {}
        derivation = data.get("derivation") or ""
        conclusion = data.get("conclusion") or ""
        _write_debug_dump(
            query=meta.get("query") or "",
            search_query=meta.get("search_query") or "",
            ev_dicts=list(data.get("evidence") or []),
            answer=f"{derivation}\n{conclusion}",
            verification=verification,
            answer_confidence={"level": vconf.get("answer_confidence"),
                               "reasons": vconf.get("confidence_reasons") or []},
            history=list(history or []),
            trace={"stage": "ks_answer", "tier": data.get("tier"),
                   "intent": meta.get("intent"), "theme": meta.get("theme"),
                   "evidence_total": meta.get("evidence_total"),
                   "llm_error": meta.get("llm_error"),
                   "cite_warnings": meta.get("cite_warnings")},
        )


    def _safe_count(conn, table: str) -> int:
        """统计失败（如 vec 扩展未加载）时降级返回 0。"""
        try:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            return 0

    @app.post("/api/v1/ks/answer")
    def ks_answer_endpoint(body: dict | None = None):
        """取证答案（P1a 同步端点，DSH 转生 ks_answer 引擎侧）。

        与 /api/v1/chat/completions（SSE）并存；SSE 事件顺序契约不动。
        入参：{"query": str, "params": {...}|null, "query_mode": "default|thorough|quick|guess"}
        响应包裹：{"code":200,"status":"success","data":{tier,evidence,derivation,conclusion,
        verification,notes,...}}。只引现行版条款；涉即将生效版本进 notes 单独说明。
        """
        body = body or {}
        query = body.get("query", "")
        if not query or not str(query).strip():
            return _json_error(422, "query_required", "query 不能为空")
        params = body.get("params") or {}
        query_mode = body.get("query_mode") or "default"
        from src.core.llm import ks_answer
        try:
            data = ks_answer.answer(query, params=params, query_mode=query_mode)
        except ks_answer.KbScopeNotFound as e:
            # 知识库目录范围里有点不存在的目录 ⇒ **404**（与 /kb/scope/resolve 同一立论：
            # 绝不静默返回"空范围"，更不许降级成全库提问）。
            return _json_error(404, "kb_scope_not_found", str(e))
        except ValueError as e:
            return _json_error(422, "bad_request", str(e))
        except Exception as e:  # noqa: BLE001 - 兜底：返回可审计错误，不崩引擎
            logger.exception("ks_answer 失败: %s", e)
            return _json_error(500, "ks_answer_error", f"取证答案生成失败: {e}")
        # D2 红线履行（2026-09-16，iteration-6 自查 §1）：本端点内部会真发一次云端
        # LLM 调用，此前**零落库** → 该路径的外发 payload 在审计面板与导出里不可见。
        # 补一条 trigger_type='user_export'（与 SSE 路径同口径）。落库失败不阻断答案。
        _write_ks_answer_dump(data, history=params.get("history"))
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/egress/audit")
    def egress_audit(limit: int = 50, offset: int = 0, cursor: str | None = None):
        """外发审计（Task 10.0 / 红线 v2 #4）：云端调用记录只读聚合。
        cursor="created_at|dump_id"（keyset 深翻页，见 query_egress）；旧客户端可继续用 offset。"""
        from src.core.llm.egress_audit import query_egress
        return {"code": 200, "data": query_egress(limit=limit, offset=offset, cursor=cursor)}

    @app.get("/api/v1/egress/audit/export")
    def egress_audit_export():
        """导出全部外发记录为 JSON（落 exports 目录，经 /export/download 下载）。

        §10.76：写文件 ⇒ `def`（审计/导出这一族一律别占事件循环）。
        """
        from src.core.llm.egress_audit import export_egress
        path = export_egress()
        return {"code": 200, "data": {"name": path.name, "path": str(path)}}

    @app.post("/api/v1/documents/{old_doc_id}/migrate-patches")
    def migrate_patches_api(old_doc_id: str, body: dict | None = None):
        """Task 10.4：旧版文档补丁跨修订平移到新版（三分支：平移/冲突入队/孤儿入队）。"""
        body = body or {}
        new_doc_id = body.get("to")
        if not new_doc_id:
            return _json_error(422, "missing_target", "缺少目标文档 id (to)")
        from src.core.storage import clause_repo
        out = clause_repo.migrate_patches(old_doc_id, new_doc_id)
        return {"code": 200, "data": out}

    # ===== Task 12.1 Office 往返编辑 =====

    @app.post("/api/v1/clauses/{clause_revision_id}/office-edit")
    def office_edit_start(clause_revision_id: str, body: dict | None = None):
        from src.core.exports.office_roundtrip import create_edit_session
        from src.core.exceptions import KnowledgeStationError
        rect = None
        try:
            body = body or {}
            rect = body.get("rect") if isinstance(body, dict) else None
        except Exception:
            rect = None
        try:
            sess = create_edit_session(clause_revision_id, rect=rect)
        except KnowledgeStationError as e:
            return _json_error(404, e.code, str(e))
        return {"code": 200, "data": sess.to_dict()}

    @app.get("/api/v1/clauses/office-edit/poll")
    def office_edit_poll(session_id: str):
        """轮询 Office 编辑会话（§10.79：要读会话文件 + 比对哈希 ⇒ 同步 I/O ⇒ `def`）。"""
        from src.core.exports.office_roundtrip import poll_edit_session
        from src.core.exceptions import KnowledgeStationError
        try:
            sess = poll_edit_session(session_id)
        except KnowledgeStationError as e:
            return _json_error(404, e.code, str(e))
        return {"code": 200, "data": sess.to_dict()}

    @app.post("/api/v1/clauses/office-edit/commit")
    def office_edit_commit(body: dict | None = None):
        body = body or {}
        from src.core.exports.office_roundtrip import commit_edit_session
        from src.core.exceptions import KnowledgeStationError
        try:
            out = commit_edit_session(body["session_id"])
        except KnowledgeStationError as e:
            return _json_error(422, e.code, str(e))
        return {"code": 200, "data": out}

    @app.delete("/api/v1/clauses/office-edit/{session_id}")
    def office_edit_cancel(session_id: str):
        from src.core.exports.office_roundtrip import cancel_edit_session
        if not cancel_edit_session(session_id):
            return _json_error(404, "session_not_found", "会话不存在")
        return {"code": 200, "data": {"cancelled": True}}

    # ===== Task 12.2 双向溯源 =====

    @app.get("/api/v1/clauses/{clause_revision_id}/backlinks")
    def clause_backlinks(clause_revision_id: str):
        from src.core.exports.backlinks import query_backlinks
        from src.core.exceptions import KnowledgeStationError
        try:
            data = query_backlinks(clause_revision_id)
        except KnowledgeStationError as e:
            return _json_error(404, e.code, str(e))
        return {"code": 200, "data": data}

    # ===== P1c-RouteA bbox 黄框轻端点（只读 GET，零副作用）=====

    @app.get("/api/v1/clauses/{clause_revision_id}/spans")
    def clause_spans(clause_revision_id: str):
        """某条款在 PDF 原件上的行级/块级 bbox（黄框证据锚点）。

        只读、零副作用。返回 source_span 中该条款本轮次的所有 bbox —— PDF
        底部原点（左下 y 向上）坐标，前端 pdfjs convertToViewPoint 直消费，
        不做任何翻转/缩放/换算。条款不存在 → 404；存在但无 bbox span →
        spans 为空数组（前端无框降级，非错误）。
        """
        conn = get_db_connection()
        row = conn.execute(
            "SELECT 1 FROM clause_revision WHERE clause_revision_id=?",
            (clause_revision_id,),
        ).fetchone()
        if row is None:
            return _json_error(404, "clause_not_found", f"条款不存在: {clause_revision_id}")
        spans = []
        for s in conn.execute(
                "SELECT page_number, bbox_json, span_type, sort_order"
                " FROM source_span"
                " WHERE clause_revision_id=? AND bbox_json IS NOT NULL"
                " ORDER BY sort_order",
                (clause_revision_id,)):
            try:
                b = json.loads(s["bbox_json"])
            except Exception:
                continue
            if not (isinstance(b, list) and len(b) == 4):
                continue
            spans.append({
                "page_number": int(s["page_number"]),
                "bbox": [float(x) for x in b],
                "span_type": s["span_type"] or "text",
            })
        return {"code": 200, "data": {
            "clause_revision_id": clause_revision_id,
            "spans": spans,
        }}

    # ===== P1c-RouteA 收藏元数据（只读 GET，零副作用）=====

    @app.get("/api/v1/clauses/{clause_revision_id}/meta")
    def clause_meta(clause_revision_id: str):
        """某条款的收藏元数据：clause_key + doc_id/page_start + 标准号/条款号/标题。

        只读、零副作用。供前端「收藏此条款」按钮用：收藏 POST /api/v1/bookmarks
        需要 clause_key（sha256(doc_id+条款号)），而证据锚点只带 clause_revision_id
        —— 此端点按 rev 反查收藏所需字段。条款不存在 → 404。
        doc_bookmarked：该条款所属标准是否已被标准级收藏（顶部「收藏本标准」初始态）。
        """
        conn = get_db_connection()
        row = conn.execute(
            "SELECT cr.clause_key, cr.doc_id, cr.page_start, cr.clause_number,"
            " cr.title, dm.standard_no"
            " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " WHERE cr.clause_revision_id=?",
            (clause_revision_id,),
        ).fetchone()
        if row is None:
            return _json_error(404, "clause_not_found", f"条款不存在: {clause_revision_id}")
        doc_bookmarked = conn.execute(
            "SELECT 1 FROM user_doc_bookmark WHERE doc_id=?",
            (row["doc_id"],),
        ).fetchone() is not None
        # 条款级收藏真值（PDF tab 可见性刷新用：收藏 tab 删除后回来要同步）。
        clause_bm = conn.execute(
            "SELECT bookmark_id FROM user_bookmark WHERE clause_key=?",
            (row["clause_key"],),
        ).fetchone()
        return {"code": 200, "data": {
            "clause_revision_id": clause_revision_id,
            "clause_key": row["clause_key"],
            "doc_id": row["doc_id"],
            "page_start": row["page_start"],
            "clause_number": row["clause_number"],
            "title": row["title"],
            "standard_no": row["standard_no"],
            "doc_bookmarked": doc_bookmarked,
            "clause_bookmarked": clause_bm is not None,
            "clause_bookmark_id": clause_bm["bookmark_id"] if clause_bm else None,
        }}

    # ===== Task 12.3 批量问答 =====

    @app.post("/api/v1/vision/locate")
    def vision_locate(body: dict | None = None):
        """截图/图纸反查：本地 MinerU OCR → 混合检索 → 条款定位。"""
        body = body or {}
        image_path = body.get("image_path")
        if not image_path or not Path(image_path).exists():
            return _json_error(422, "missing_image", "缺少有效的 image_path")
        from src.core.vision.local_vision import vision_locate as do_locate
        from src.core.exceptions import KnowledgeStationError
        try:
            return {"code": 200, "data": do_locate(Path(image_path))}
        except KnowledgeStationError as e:
            return _json_error(422, e.code, str(e))

    # ===== Task 13.5 快照备份与回滚 =====

    @app.post("/api/v1/snapshots")
    def create_snapshot(body: dict | None = None):
        body = body or {}
        from src.core.storage.backup import create_snapshot as do_snapshot
        snap_type = body.get("type", "manual")
        return {"code": 200, "data": do_snapshot(snap_type)}

    @app.get("/api/v1/snapshots")
    def list_snapshots():
        from src.core.storage.backup import list_snapshots as do_list
        return {"code": 200, "data": do_list()}

    @app.post("/api/v1/snapshots/{snapshot_id}/restore")
    def restore_snapshot(snapshot_id: str):
        """恢复快照（§10.76：要读+校验+落盘整包、还做 sha256 ⇒ `def`）。"""
        from src.core.storage.backup import restore_snapshot as do_restore
        from src.core.exceptions import KnowledgeStationError
        try:
            return {"code": 200, "data": do_restore(snapshot_id)}
        except KnowledgeStationError as e:
            status = 404 if e.code in ("snapshot_not_found", "snapshot_file_missing") else 422
            return _json_error(status, e.code, str(e))

    @app.post("/api/v1/documents/impact")
    def impact_analysis(body: dict | None = None):
        """R49 影响面分析：旧版被新版替代的影响统计。

        ⚠ `def` 而不是 `async def`（§10.86 通则之一）：唯一的 `await` 只是 `request.json()`。
        body 改走签名（坏 body ⇒ 422；缺字段仍是 `KeyError` → 被下面的 `except` 收成 404，
        与改前一致）。
        """
        body = body or {}
        from src.core.storage.impact import analyze_impact
        try:
            return {"code": 200, "data": analyze_impact(
                body["old_doc_id"], body["new_doc_id"])}
        except Exception as e:
            return _json_error(404, "impact_error", str(e))

    @app.get("/api/v1/diagnostics/health-board")
    def health_board():
        """P8 健康看板：六引擎状态 + 知识库统计。

        ⚠ **`def` 而不是 `async def`**（§10.74）：判据是**结构性**的——本端点做的是同步 I/O
        （七条 `COUNT(*)` + `mineru_available()` 的 import 探测），uvicorn 是单事件循环，
        同步 I/O 留在这里就会占住循环。
        ⚠ **但别夸大收益**（本步实测）：本机 `health_board` 总耗时 **0.017s**；
        `import mineru` 实测 **0.000s**（它是 CLI 包，不是重依赖库——我原先写在注释里的
        "首次导入几秒"是**错的**，已删）；30 万行表上一条 `COUNT(*)` ≈ **1.1ms**（代理测量）
        ⇒ 统计块是**几十毫秒量级**，不是秒级。改成 `def` 是"别把同步 I/O 放事件循环里"的
        一般纪律，不是因为这里很慢。真正的秒级重活在别处（见 §10.73/§10.74 的 before/after）。
        `vector` 那一格改用**廉价三态** `embedder.health()`（不再"加载模型来判断模型"）。
        """
        from src.core.retrieval import embedder
        from src.core.ingestion.mineru_adapter import mineru_available
        conn = get_db_connection()
        try:
            conn.execute("SELECT 1")
            db_ok = True
        except Exception:
            db_ok = False
        from src.core.config import get_settings
        return {
            "code": 200,
            "data": {
                "status": "healthy" if db_ok else "degraded",
                "engines": {
                    "db": "ok" if db_ok else "error",
                    "vector": embedder.health(),
                    "fts": "ok",
                    "parser": "ok" if mineru_available() else "not-installed",
                    "llm": "configured" if get_settings().llm_api_key else "not-configured",
                    "alias": "active",
                },
                "stats": {
                    "documents": conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0],
                    "clauses": conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0],
                    "vectors": _safe_count(conn, "clause_vec"),
                    "patches": conn.execute("SELECT COUNT(*) FROM clause_patch").fetchone()[0],
                    "aliases": conn.execute("SELECT COUNT(*) FROM alias_store").fetchone()[0],
                    "reviews": conn.execute(
                        "SELECT COUNT(*) FROM review_task").fetchone()[0],
                    "debug_dumps": conn.execute(
                        "SELECT COUNT(*) FROM debug_dump").fetchone()[0],
                },
            },
        }

    @app.get("/api/v1/diagnostics/debug-dumps")
    def debug_dumps(limit: int = 20):
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT dump_id, trigger_type, query, created_at, llm_output, logs"
            # 2026-09-14：rowid 作第二排序键。created_at 秒级精度下密集提问
            # （全量测试/快节奏 GUI）同秒平局，无 tie-breaker 时 SQLite 返回
            # 顺序不定——dumps[0] 可能拿到先写入的旧 dump（test_phase8 全量
            # 套件偶发红的根因）。rowid 单调递增 = 写入序，语义正确。
            " FROM debug_dump ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (limit,)).fetchall()
        return {"code": 200, "data": [dict(r) for r in rows]}

    def _expand_title_clauses(evidences: list) -> list:
        """标题条款（如 8.1 作业分级）自动附带其子条款（8.1.1~8.1.3），
        保证分级/要求类回答拿到内容条款而非只有标题。"""
        import re as _re
        conn = get_db_connection()
        out: list = []
        seen: set[str] = set()
        for e in evidences:
            if e.clause_revision_id in seen:
                continue
            seen.add(e.clause_revision_id)
            out.append(e)
            no = e.clause_number or ""
            # 2026-09-13 附录细分配套：接纳附录字母章号（E.1/E.5.2），与
            # ks_answer._expand_title_clauses 同步放宽。
            is_title = bool(_re.fullmatch(r'[0-9A-Z]+(?:[.][0-9A-Z]+)*', no)) and len(e.content_text or "") < 80
            if is_title:
                subs = conn.execute(
                    "SELECT clause_revision_id FROM clause_revision"
                    " WHERE doc_id=? AND clause_number LIKE ? ORDER BY rowid LIMIT 4",
                    (e.doc_id, no + ".%")).fetchall()
                for s in subs:
                    if s["clause_revision_id"] in seen:
                        continue
                    seen.add(s["clause_revision_id"])
                    sub = _fetch_clause(conn, s["clause_revision_id"])
                    if sub is not None:
                        out.append(sub)
        return out[:8]

    def _fetch_clause(conn, cid: str):
        from src.core.storage.clause_repo import fetch_full_clause
        return fetch_full_clause(conn, cid)

    def _answer_confidence(verification, ev_dicts: list) -> dict:
        """R24 答案层置信度分级（三档）。

        high: 核验通过 且 全部证据高可信（type_confidence>=0.85 且非存疑）
        mid : 核验通过，但存在中/低可信或存疑证据
        low : 核验未通过（存在被拦截项）
        """
        reasons = []
        if not verification.is_valid:
            reasons.append("核验拦截项未清零")
            return {"level": "low", "reasons": reasons}
        low_conf = [e["clause_number"] for e in ev_dicts
                    if e.get("is_suspicious") or (e.get("type_confidence") or 1) < 0.85]
        if low_conf:
            reasons.append(f"证据存疑/低可信: {'、'.join(low_conf[:4])}")
            return {"level": "mid", "reasons": reasons}
        reasons.append("核验通过且证据高可信")
        return {"level": "high", "reasons": reasons}

    def _html_to_text(html: str | None, limit: int = 400) -> str:
        """表格 html → 紧凑纯文本（证据 prompt / table_md 用）。解码 HTML 实体 + <eq> 公式转可读。

        实现已抽到 `src.core.quality.clause_health_html_to_text`（唯一所有者，数据体检与
        R27 入库预览共用）；这里保留同名薄壳，避免改动既有调用点（本文件另有一处 usage）。
        """
        from src.core.quality import clause_health_html_to_text
        return clause_health_html_to_text(html, limit)

    # （2026-09-01 撤除本地 _normalize_wraps：出口洗平退役，行界=原文真实折行）

    #: 图题段形态（2026-08-29，GB/T 34406 图1/图A.1/图A.2 实测，语料级）：
    #  '图N<标题>图'——GB 图题以"图"字收尾是最强锚（'图1定性分析判定程序图'/
    #  '图A.1判别分析相关图'）；引用形态（'如图1所示。'/'参见图A.1。'）图号后
    #  跟句读或"所示"，不满足 <标题>图 收尾。前置排除引用引导字（如/见/自），
    #  标题 ≤40 字符防长句误吞。
    # 2026-09-02 判据放宽（24276 实测修正）：扫描版 OCR 题注形态多样——
    #  '图A.1 示例1，计算…的图'（以图收尾 ✓ 原判据）、'图A.3 示例 2,带通风口
    #  的壁挂式外壳的计算'（以"的计算"收尾）、'图 4 不带通风口，…系数c'
    #  （无图字收尾）。放宽 = 独立成行（(?<![^\s<>]) 行首锚，**含 >**：
    #  body 段落以 <p> 包裹，'图' 前是 '>'；行内引用"…见图4所示…"前是
    #  中文仍被挡）+ 图号 + ≤80 字符描述到行尾/句读。误注入（正文引用
    #  行如"图 4 的曲线 1 中"）由 /figure 端点 404 → 前端 onerror 隐藏兜底，
    #  无破图、无视觉伤害（图4 实为系数表时表格照常渲染）。
    # 2026-09-02 治本：排除**引用结尾**——题注描述以『的…中/，/；/：』收尾
    #  是句中引用（'图 4 的曲线 1 中'/'图 6 显示对于…：'），非题注（题注描述
    #  以 '图/曲线/计算/系数c' 等主语/名词收尾）。(?<![中，。；：]) 负向保证。
    _FIG_CAPTION_SEG = _re_mod.compile(
        r"(?<![^\s<>])(?<![如见自于似])图\s*([0-9A-Z]+(?:\.[0-9A-Z]+)?|\d+)"
        r"(?![所示。，,])\s*([^\n<]{2,80}?)(?<![中，。；：])(?=\s*$|。|；|，|<)")

    # 独立公式行判据（2026-09-02 定稿，24276 实测修正）：GB 正文公式行
    # 无编号结尾（OCR 剥除编号），旧判据（编号+√∑）从不命中 → 0 注入。
    # 新判据 = 行首非中文（[^\u4e00-\u9fff<]：公式以变量/Δ/数字起头，叙述句
    # "…功率P=…" 以中文起头被排除）+ 等号前 ≤60 字符且无中文（"A°>1.25m²
    # 时，…x为: x=0.804" 等号前含中文 → 不匹配叙述尾式）+ 行首锚
    # (?<![^\s<>])（前非可见字符——**必须含 >**：body 段落以 <p> 包裹，
    # '图'/'f' 前是 '>'；全角冒号/中文（"式中：X=ab"）仍挡住 → 说明行
    # 安全）；表达式到行尾/标点/"式中"止。展示层与 /formula 端点共用
    # （fno 条款内序号语义对齐）。
    _FORMULA_SEG = _re_mod.compile(
        r"(?<![^\s<>：:])([^\u4e00-\u9fff<][^<>\n\u4e00-\u9fff。；]{0,60}[=＝]"
        r"[^<>。；\n]{1,150}?)(?=\s*式中|\s*$|<|。|；|，)")

    def _content_html(content_text: str | None, content_markdown: str | None,
                      doc_id: str | None = None, clause_no: str | None = None,
                      page_breaks: str | list | None = None,
                      figure_html: str | None = None,
                      table_pages: list | None = None,
                      chart_done: set | None = None,
                      asset_done: set | None = None,
                      row_boxes: list | None = None,
                      page_start: int | None = None,
                      page_end: int | None = None) -> str:
        """条款展示用完整富文本 html：正文段落（保留编辑保存的 <sup>/<sub>/<b>/<i>）+ 表格 html。
        content_markdown 语义 = 富文本片段（编辑保存时含正文+表格；pipeline 只存表格 html）。
        - <eq>LaTeX</eq> 公式 → 可读 Unicode 文本（h_w/m 等）
        - 正文剔除与表格重复的文字块（MinerU 把表格文字也抽进正文 → 卡片重复显示的根因）
        - 2026-08-26：纯文本 LaTeX 泄漏（\\leqslant 等）→ Unicode；转义时保留 <sup>/<sub> 白名单
        - 2026-09-01 B3：page_breaks（页界 run-start 编码 [[行号,PDF页],...]，
          行号 = content_text 0-based 行索引）非空时在页界处插页分隔标记；
          None/空（存量未采集）零行为变化。"""
        import re as _re
        import difflib as _difflib
        from src.core.text_utils import (
            clean_eq_tags, glue_spaced_formulas, katex_sym_html,
            normalize_math_symbols, pua_bond_dash_html,
            reflow_sqrt_formulas, space_clause_numbers_html,
            strip_embedded_table_text, sup_unit_exponents_html,
            weave_meaning_marks)
        md = clean_eq_tags((content_markdown or "").strip())
        # 图题段 → 内嵌截图（2026-08-29 用户诉求"流程图/散点图没识别出来，
        # 数学图形可以直接截图"）：扫描双层图形无独立图像对象，按图题锚定图区
        # 实时渲染 PNG（/figure 端点，与 PDF 同源永远不脏）；定位失败 onerror
        # 隐藏。行级/段内统一覆盖（附录压平后图题是行中段）。编辑保存片段
        # （完整富文本）同样注入——图题文本形态一致。
        # 2026-09-02 位置契约：GB 图题在图区**下方**（"图N 标题"），原版布局
        # = 图在上、题注在下 → 占位插在题注文本**之前**；截图尺寸/水平位置按
        # 响应头 X-Frac-* 还原（前端 fetch 后设 width/margin-left 比例）。
        def _inject_figs(html_body: str) -> str:
            if not doc_id or not html_body:
                return html_body
            # 2026-09-02 C1 架构根治：版面对象为主图源——**在 content_text 上做
            # 正则注入时只注入"不在版面集"的图号**（如 24276 图 A.3——MinerU
            # 漏识别无版面块，但题注在 content/OCR 文本，/figure 端点已有
            # locate_middle_caption OCR 题注锚定可截图）；"在版面集"的图号
            # （图4/7/8…由 chart_queue 注入）跳过——防"图4 的系数c取决于…"
            # 引用句误当题注注入（同类 ≥3 架构反思）。
            try:
                from src.core.middle_geo import load as _load_mid_fg
                _geo_f = _load_mid_fg(
                    get_settings().data_dir / "parse_out" / str(doc_id))
                _fig_in_layout = {
                    _f["no"] for _f in (_geo_f.figures() if _geo_f else [])}
            except Exception:   # noqa: BLE001 - 版面无关则全注入
                _fig_in_layout = set()

            def _fig_sub(m):
                cap = f"图{m.group(1)}{m.group(2)}"
                if (_fig_in_layout and m.group(1) in _fig_in_layout):
                    return m.group(0)   # 版面图号 → chart_queue 注入（防引用误注入）
                # 无 src 占位：/figure 受 Bearer token 保护，<img src> 裸请求
                # 必 401；前端 effect 用带 token 的 fetch 拉 blob 填 src（App.tsx
                # fig-embed effect），定位失败 404 → 前端隐藏，无图文档零破图。
                return (f"<img class=\"fig-embed\" data-fig=\"{m.group(1)}\" "
                        f"alt=\"{cap}\" loading=\"lazy\"/>" + m.group(0))

            # 2026-09-02 表格段不注入（表格单元格内的"图N"是引用/数据，非题注）
            return "".join(
                seg if seg.lstrip().startswith("<table")
                else _FIG_CAPTION_SEG.sub(_fig_sub, seg)
                for seg in _re_mod.split(r"(<table.*?</table>)", html_body,
                                         flags=_re_mod.S))

        # 公式段 → 内嵌原图截图（2026-08-29 用户诉求"复杂公式按原排版复刻"）：
        # 双层扫描的文字层把二维公式（根号套分式/求和带上下限）压平成线性串，
        # 原排版只存在于扫描图——按编号右对齐锚 + 种子行定位公式区 clip 截图
        # 2026-09-02 用户契约：识别公式直接按原版排版呈现（不拆单行）——
        # 判据定稿（24276 实测修正）：正文公式行**无编号结尾**（编号被 OCR
        # 剥除），旧判据（编号+√∑）从不命中 → 0 注入，正文只剩压平的线性
        # 文本 = 用户看到的"拆成单行"。新判据 = 独立公式行：行首锚
        # (?<![^\s<])（前非可见字符=段落开头）防行内公式；行首非中文
        # （[^\u4e00-\u9fff<]：公式以变量/Δ/数字起头，叙述句"…功率P=…"以
        # 中文起头被排除）；等号前≤60 字符且**无中文**（"A°>1.25m²时，…
        # x为: x=0.804" 等号前含中文 → 不匹配叙述尾式）；表达式到行尾/
        # 匹配段文本以 .formula-hide 隐藏（DOM 保留供检索/复制，视觉只留
        # 原版截图）。判据常量 _FORMULA_SEG 定义在 create_app 作用域
        # （/formula 端点同源共用，fno=条款内序号语义对齐）。

        def _inject_formulas(html_body: str) -> str:
            if not doc_id or not clause_no or not html_body:
                return html_body

            # 2026-09-02 修复 fno 错位（用户报告"截图内容乱截"）：fno 不再用
            # body 内公式段序（text 驱动，与 middle.json eqs 数量错位——判据
            # 排除判据式但 eqs 含它们）。改为：匹配段 LaTeX 归一化相似度在**全
            # 文 eqs** 里找最接近的 interline_equation 块，取其**全局序号**作
            # data-fno；端点按全局序精确取块。无匹配 → 保留原文本（不截图，
            # 宁缺勿滥防乱截）。
            eqs_all: list[tuple[int, str]] = []   # [(全局序号, latex)]
            try:
                from src.core.middle_geo import load as _load_middle_geo
                _geo = _load_middle_geo(
                    get_settings().data_dir / "parse_out" / str(doc_id))
                if _geo is not None:
                    _seq = 0
                    for _pno in sorted(_geo.pages):
                        for _bbox, _latex in _geo.eq_blocks(_pno):
                            _seq += 1
                            eqs_all.append((_seq, _latex))
            except Exception:   # noqa: BLE001 - 无深度产物 → 文本保留
                eqs_all = []

            def _norm_eq(lx: str) -> str:
                return _re_mod.sub(r"\\[a-zA-Z]+|[{}_^ ]|[,:]", "", lx or "")

            def _pick_fno(expr: str):
                te = _norm_eq(expr)
                if not te:
                    return None
                best, bs = None, 0.0
                for _seq, _latex in eqs_all:
                    le = _norm_eq(_latex)
                    if not le:
                        continue
                    s = _difflib.SequenceMatcher(None, te, le).ratio()
                    if s > bs:
                        bs, best = s, _seq
                if bs < 0.35:
                    return None
                for _seq, _latex in eqs_all:
                    if _seq == best:
                        return (best, _latex)
                return None

            def _f_sub(m):
                expr = m.group(1)
                pick = _pick_fno(expr)
                if pick is None:
                    return m.group(0)   # 无匹配 → 保留文本
                # 2026-09-02 需求1"公式完美还原（非图片）"：MinerU 公式块 LaTeX
                # → clean_latex_for_katex → KaTeX 真排版。前端 katex-formula
                # effect 渲染（throwOnError:false 失败保留原文本兜底）；点击仍
                # 可拉 /formula 原图（保留端点）。
                from src.core.text_utils import clean_latex_for_katex
                from html import escape as _hesc
                _tex = clean_latex_for_katex(pick[1])
                return (f'<span class="katex-formula" data-fno="{pick[0]}" '
                        f'data-clause="{clause_no}" '
                        f'data-tex="{_hesc(_tex, quote=True)}">{expr}</span>')

            # 2026-09-02 表格内公式不注入（表内计算式是表格文本，无独立公式
            # 块可截图；注入会错位显示无关公式）——<table> 块原样保留，
            # 非表格段（正文段落）跑判据。
            return "".join(
                seg if seg.lstrip().startswith("<table")
                else _FORMULA_SEG.sub(_f_sub, seg)
                for seg in _re_mod.split(r"(<table.*?</table>)", html_body,
                                         flags=_re_mod.S))

        # 2026-08-28 修复：判断"完整富文本"只认 <p>。此前认 <sup>/<sub> 也算，
        # 但框线重建的表格 html 本身合法含 <sup>/<sub>（蛋白质ᵃ、A₁）→
        # 被误判为编辑保存片段 → 只显示表格，正文句子+表题被吞。
        if md and _re.search(r"<p[ >]", md):
            # C2：编辑保存片段也追加插图占位（figure_html 独立通道，不进 md）
            return _inject_formulas(_inject_figs(md)) + (figure_html or "")
        # 旧数据/pipeline：content_markdown 只有表格 html → 正文转段落 + 表格
        # （2026-09-01 退役出口 normalize_wraps：行界=原文真实折行须保留，
        # 洗平是假行界时代补丁；对存量幂等无影响，对新入库是排版破坏）
        # 2026-09-01 B3 页界渲染：「原文哪里换页就哪里换页」。表格剥离改逐行
        # 调用（与整串调用行为等价——其内部本就逐行判定），保住 content_text
        # 行号 ↔ 页界编码的映射不被整行丢弃打漂移；随后按 run-start 编码展开
        # 出每行的页号，页号切换处在段间插分隔标记（不增删任何正文行）。
        starts: list[list[int]] = []
        if page_breaks:
            try:
                _pb = (json.loads(page_breaks)
                       if isinstance(page_breaks, str) else page_breaks)
                for e in _pb or []:
                    starts.append([int(e[0]), int(e[1])])
            except Exception:
                starts = []   # 坏编码宁可不分隔，不可错页
        md_clean = clean_eq_tags(md)
        # 2026-09-01 表格归位（"表格到处跑"根因修复）：旧实现把条款全部表格
        # html 一次性追加在正文末尾（body += md）——跨页条款里第 10 页的表
        # 渲染在第 17 页文本之后，阅读序与页界叙事错位（GB/T 24276 条款 6
        # 实测 4 张表全堆尾部）。现在按表格 span 页号把每张表插回原文页位：
        # 正文行按页推进，推进越过某表的页时把该表插在其页最后一行之后
        # （同页多表保持条目序）。两个前提都来自入库数据：page_breaks
        # （行→页映射）+ table_pages（每张表的页号，与 content_markdown 里
        # <table> 出现序对齐，同源于 cl.items 条目序）。任一缺失/不对齐 →
        # 维持旧的末尾追加（存量文档零行为变化）。
        tbl_pages: list[int] = []
        if table_pages:
            try:
                tbl_pages = [int(p) for p in table_pages]
            except (TypeError, ValueError):
                tbl_pages = []
        tbl_chunks = _re.findall(r"<table.*?</table>", md_clean, _re.S)
        interleave = bool(
            starts and tbl_pages and tbl_chunks
            and len(tbl_chunks) == len(tbl_pages)
            and _re.sub(r"\s+", "", md_clean) == _re.sub(r"\s+", "", "".join(tbl_chunks)))
        # 2026-09-02 带图表格整表转图（用户契约：凡单元格含图片的表格，整个
        # 表格也一起当图片处理）：MinerU 版面坐标（middle.json）同页 table bbox
        # ∩ image bbox > 0 → 该页表格含图（表头/单元格插图）→ 整表替换为
        # img.table-embed 占位（前端 /table-image 端点拉整表截图，与 PDF 同源）；
        # 无深度产物/损坏 → 保持原表格 html（零行为变化）。页内多表按阅读序
        # 与 middle.json 带图表序号（升序）一一对应，超出部分保持表格 html。
        tbl_hits: dict[int, list[int]] = {}
        if doc_id and interleave:
            try:
                from src.core.middle_geo import load as _load_middle_geo
                _geo = _load_middle_geo(
                    get_settings().data_dir / "parse_out" / str(doc_id))
                if _geo is not None:
                    for _tp in dict.fromkeys(tbl_pages):
                        _h = _geo.image_hit_tables(_tp)
                        if _h:
                            tbl_hits[_tp] = _h
            except Exception:   # noqa: BLE001 - 深度产物缺失不阻塞展示
                tbl_hits = {}
        tbl_queue: list[tuple[int, str]] = []
        if interleave:
            _seen: dict[int, int] = {}
            for _tp, _ch in zip(tbl_pages, tbl_chunks):
                _k = _seen.get(_tp, 0)
                _seen[_tp] = _k + 1
                _hits = tbl_hits.get(_tp) or []
                if _k < len(_hits):
                    _ch = (f'<img class="table-embed" data-page="{_tp}" '
                           f'data-tbl="{_hits[_k]}" alt="带图表格" loading="lazy"/>')
                tbl_queue.append((_tp, _ch))
        kept_rows: list[tuple[str, int | None]] = []
        ptr, cur_pg = 0, None
        for i, ln in enumerate((content_text or "").split("\n")):
            while ptr < len(starts) and starts[ptr][0] <= i:
                cur_pg = starts[ptr][1]
                ptr += 1
            kept = strip_embedded_table_text(ln, md_clean)
            if not kept.strip():
                continue
            kept_rows.append((kept, cur_pg if starts else None))
        body_text = normalize_math_symbols("\n".join(r[0] for r in kept_rows))
        # 2026-08-29 出口兜底（幂等重跑）：公式粘合/根号重排等文本修复历史上
        # 只在入库时固化——修复之前入库的存量文档正文串仍是旧形态；此处对展示
        # 串重跑同规则（函数全部幂等，已修复文本无变化）→ 存量立即受益无需重导。
        body_text = reflow_sqrt_formulas(glue_spaced_formulas(body_text))
        # 2026-09-02 C5 上下标+空格还原（出口 reflow 立即生效）：
        # ① 面积下标误识别 'A°>1.25m²' → 'Aₑ>1.25m²'（MinerU 把下标 e 认成度符号）；
        # ② OCR 逐字符数字/单位空格 '1 . 2 5 m ²' → '1.25m²'（正文判据式行）。
        from src.core.text_utils import normalize_area_subscript
        body_text = normalize_area_subscript(body_text)
        body_text = _re_mod.sub(r"(\d)\s+(\d)", r"\1\2", body_text)
        body_text = _re_mod.sub(r"([A-Za-z])\s+([²2])\b", r"\1\2", body_text)
        # 2026-08-29 平均值 bar 织入（说明行 'Ci———样品i的平均值'→'C̄i———…'，
        # 画线 bar 文字层无字符；仅 pipeline 路径，编辑保存片段不动）
        body_text = weave_meaning_marks(body_text)
        from src.core.text_utils import html_unescape as _unesc
        # 行级出口变换（粘合/根号重排/bar 织入）应为行内改写、行数稳定；
        # 防御性计数失配 → 放弃页界分隔（宁可不分隔不可错页）。
        out_lines = body_text.splitlines()
        if starts and len(out_lines) == len(kept_rows):
            out_rows: list[tuple[str, int | None]] = list(
                zip(out_lines, (r[1] for r in kept_rows)))
        else:
            out_rows = [(ln, None) for ln in out_lines]
        paras = []
        prev_pg: int | None = None
        # 2026-09-02 插图按页位归位（用户诉求"图片位置排版与原版相同"，消除
        # C2 插图堆条款尾）：figure_html 的 asset-embed 按 image_path 反查
        # 物理页（middle_geo），页推进越过含图页时插入正文流（非末尾耗尽）。
        # 无页号/无深度产物 → 保持原末尾追加（零行为变化）。
        asset_queue: list[tuple[int, str]] = []
        inserted_asset: list[str] = []
        if doc_id and figure_html:
            try:
                from src.core.middle_geo import load as _load_mid_a
                _geo_a = _load_mid_a(
                    get_settings().data_dir / "parse_out" / str(doc_id))
            except Exception:   # noqa: BLE001 - 无深度产物保持末尾追加
                _geo_a = None
            if _geo_a is not None:
                for _m in _re_mod.finditer(
                        r'<img class="asset-embed"[^>]*?data-asset="([^"]+)"[^>]*>',
                        figure_html):
                    _fn = _m.group(1)
                    _hit = _geo_a.image_bbox_by_path(_fn)
                    if _hit is None:
                        continue
                    _pg = int(_hit[0])
                    # 包裹该 img 的 fig-strip <p>（C2 产物形态）
                    _lb = figure_html.rfind("<p", 0, _m.start())
                    _le = figure_html.find("</p>", _m.end())
                    _seg = (figure_html[_lb:_le + 4]
                            if _lb >= 0 and _le > _m.end() else _m.group(0))
                    asset_queue.append((_pg, _seg))
                    inserted_asset.append(_seg)
                asset_queue.sort(key=lambda x: x[0])
        # 2026-09-02 C1 孤儿图补齐（正确版）：figure_html 只含 split 绑定成功
        # 的图；无题注/未绑定的 image（30871 p6 图）被丢。middle_geo.assets()
        # 给全部 image asset；**asset_done 跨条款去重**（get_clauses 共享）+ 图页
        # ∈ 本条款 page_start/end 才归属（唯一，防页范围重叠重复——此前页范围
        # 版本 12.4/12.5 重叠重复已撤销）。
        if doc_id:
            try:
                from src.core.middle_geo import load as _load_mid_ao
                _geo_ao = _load_mid_ao(
                    get_settings().data_dir / "parse_out" / str(doc_id))
                if _geo_ao is not None:
                    _seen_asset = set()
                    for _seg in inserted_asset:
                        _fm9 = _re_mod.search(r'data-asset="([^"]+)"', _seg)
                        if _fm9:
                            _seen_asset.add(_fm9.group(1))
                    for _a in _geo_ao.assets():
                        _fn = _a["path"].replace("\\", "/").rsplit("/", 1)[-1]
                        if _fn in _seen_asset:
                            continue
                        if asset_done is not None:
                            if _fn in asset_done:
                                continue
                            asset_done.add(_fn)
                        # page 归属（稳定版）：c47265 按 page_start/end 唯一 12.5；
                        # 30871 p6 无 clause 页 → 缺 = 已知架构性边缘（非渲染 bug）。
                        if page_start is not None and page_end is not None \
                                and not (page_start <= int(_a["page"]) <= page_end):
                            continue
                        asset_queue.append((
                            int(_a["page"]),
                            f'<p class="fig-strip"><img class="asset-embed" '
                            f'data-asset="{_fn}" alt="插图" loading="lazy"/></p>'))
                    asset_queue.sort(key=lambda x: x[0])
            except Exception:   # noqa: BLE001 - 无深度产物零变化
                pass
        # chart 块的 caption（OCR 未并入 content_text）→ _inject_figs 无题注可
        # 匹配 → 曲线图缺失。此处按 chart 页位插入 fig-embed（data-fig=图号），
        # /figure 端点（chart 路径）已能按图号截图；跳过 content_text 里已有
        # 题注的图号（图 4/6/8 由 _inject_figs 处理，防重复注入）。
        chart_queue: list[tuple[int, str]] = []
        if doc_id:
            try:
                from src.core.middle_geo import load as _load_mid_ch
                _geo_ch = _load_mid_ch(
                    get_settings().data_dir / "parse_out" / str(doc_id))
                if _geo_ch is not None:
                    # 2026-09-02 C1 根治：版面对象为唯一图源——不再参考
                    # content_text 题注（_fig_in_text，那会与新版面注入冲突），
                    # 直接按版面 figures()（图号权威，数字图全局序兜底）注入；
                    # _inject_figs 版面存在时不跑，引用句不再误注入。image
                    # （插图）由 figure_html/asset 通道，此处只注入 chart（曲线）。
                    for _f in _geo_ch.figures():
                        if _f["kind"] != "chart":
                            continue
                        _pno = int(_f["page"]); _no = _f["no"]
                        # 2026-09-02 图物理页归属：用 clause 真实 page_start/end
                        # （clause_revision 表）替代 page_breaks 派生 _lo/_hi
                        # （后者漏含物理页的图，1032 图4/9 实测缺）。图页 ∈
                        # 条款页范围才归属该条款（跨条款互斥 + chart_done 去重
                        # → 图插物理页条款一次，位置正确）。
                        if page_start is not None and page_end is not None \
                                and not (page_start <= _pno <= page_end):
                            continue
                        # 请求级去重：同图号全文档只插一次（跨条款/子条款）
                        if chart_done is not None:
                            if _no in chart_done:
                                continue
                            chart_done.add(_no)
                        chart_queue.append(
                            (_pno, f'<img class="fig-embed" data-fig="{_no}" '
                                   f'alt="图{_no}" loading="lazy"/>'))
            except Exception:   # noqa: BLE001 - 无深度产物零变化
                chart_queue = []
        chart_queue.sort(key=lambda x: x[0])
        # 2026-09-02 双栏版面：行级 bbox x0 分左右栏（左簇 max + 200 < 右簇 min
        # = 显著双栏分离）。仅当本条款为纯文本双栏（无表/图插入该区间，B5 行
        # bbox 与 content_text 行序对齐）时启用两列布局；否则回退流式。
        _col_mid = None
        _left_paras: list[str] = []
        _right_paras: list[str] = []
        _ri = 0
        _col_mode = False
        _md_tables = bool(md and "<table" in md)
        if row_boxes and len(row_boxes) >= 4 and not _md_tables:
            # 双栏 = 行级 x0 排序后存在**显著间隙**（栏距 >40）分成两簇
            # （左簇 max + 间隙 < 右簇 min）。单栏页 gap 小 → 不双栏。
            # 2026-09-02 修复：**含表格条款不判双栏**——双栏分支只渲染正文
            # 行，会丢 content_markdown 表格（附录A/B 实测 tables=0）→ 有表
            # 回退流式（表格正确），纯文本正文才双栏（5.2.x 双栏页）。
            _xs = sorted(b[0] for b in row_boxes)
            _max_gap, _split = 0, -1
            for _i in range(1, len(_xs)):
                _g = _xs[_i] - _xs[_i - 1]
                if _g > _max_gap:
                    _max_gap, _split = _g, _i
            if _split >= 2 and len(_xs) - _split >= 2 and _max_gap > 40:
                _col_mode = True
                _col_mid = _xs[_split]
        for line, pg in out_rows:
            line = _unesc(line).strip()   # 还原库内已有实体（&lt;→<），下方统一重新转义
            if not line:
                continue
            # 2026-09-01 表格归位：页推进越过某表的页 → 该表插在其页最后一行
            # 之后、下一页页界标记之前（表属于上一页的阅读流）。
            if tbl_queue and pg is not None:
                while tbl_queue and tbl_queue[0][0] < pg:
                    paras.append(tbl_queue.pop(0)[1])
            # 2026-09-01 B3 页界分隔：页号切换处（跨 PDF 物理页）在段间插标记，
            # 前端 .page-break 样式渲染虚线分隔 + 页码角标。
            if pg and prev_pg is not None and pg != prev_pg:
                paras.append(f'<div class="page-break" data-page="{pg}"></div>')
                # 2026-09-02 插图页位归位：越过含图的页（资产页 ≤ 当前页）→
                # 该页图插在页界后（该页正文前），与原版同页位
                while asset_queue and asset_queue[0][0] <= pg:
                    paras.append(asset_queue.pop(0)[1])
                while chart_queue and chart_queue[0][0] <= pg:
                    paras.append(chart_queue.pop(0)[1])
            prev_pg = pg
            # 保留 <sup>/<sub> 白名单（上下标要真渲染，不能转义成字面 <sup>）；
            # 其余 < > & 转义（防注入 + 不把杂散标签当 HTML）
            line = (line.replace("<sup>", "\x01").replace("</sup>", "\x02")
                        .replace("<sub>", "\x03").replace("</sub>", "\x04"))
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            line = (line.replace("\x01", "<sup>").replace("\x02", "</sup>")
                        .replace("\x03", "<sub>").replace("\x04", "</sub>"))
            # 2026-08-28 表题样式（通用）：以"表+编号"开头的行是表题
            # （"表1蛋白质…指标"/"表B.1…(续)"），原件为居中加粗独立行。
            # "表面积/表面"等普通词开头不匹配（编号紧随），正文"符合表1的
            # 规定"以动词开头也不匹配。
            if _TBL_CAPTION_LINE.match(line):
                _p = f'<p class="tbl-cap">{line}</p>'
            else:
                _p = f"<p>{line}</p>"
            if _col_mode and row_boxes and _ri < len(row_boxes):
                # 双栏：按行级 bbox x0 归左右栏（——栏内按阅读序即 sort_order）
                if row_boxes[_ri][0] < _col_mid:
                    _left_paras.append(_p)
                else:
                    _right_paras.append(_p)
            else:
                paras.append(_p)
            _ri += 1
        # 2026-09-02 排版还原：`…，\n其中：\n公式` 在原版是**同行一句**
        # （"图4的系数c…其中：f=h^1.35/A_b"），content_text 被 OCR 拆成 3 行。
        # 这里在**显示层**归并相邻段（不改 content_text 行号 → 页界 run-start
        # 映射不漂移）：句尾逗号段 + "其中：/式中："引导段 + 公式段 → 并为一段，
        # 公式随之行内紧跟（_FORMULA_SEG 锚已放宽兼容"其中："冒号后公式）。
        def _ptext(p: str) -> str:
            return _re_mod.sub(r"<[^>]+>", "", p).strip()
        def _p_lead(p: str) -> bool:
            return bool(_re_mod.match(r"^(其中|式中)[：:]?$", _ptext(p)))
        def _p_formula(p: str) -> bool:
            t = _ptext(p)
            return bool(t) and len(t) < 60 and bool(_FORMULA_SEG.match(t))
        def _p_tail(p: str) -> bool:
            return _ptext(p).endswith(("，", "。", "；")) or "其中" in _ptext(p)
        def _p_join(prev: str, cur: str) -> str:
            # 合并两个 <p> 为一段（去 cur 首尾标签，prev 去尾部 </p>）
            return (prev.rstrip("</p>") + cur.replace("<p>", "", 1).replace("</p>", "")
                    + "</p>")
        def _mrg_col(pl: list[str], p_lead, p_formula, p_tail, p_join) -> str:
            mm: list[str] = []
            for _pp in pl:
                if not mm:
                    mm.append(_pp); continue
                if (p_formula(_pp) and p_tail(mm[-1])) \
                        or (p_lead(_pp) and p_tail(mm[-1])) \
                        or (p_formula(_pp) and p_lead(mm[-1])):
                    mm[-1] = p_join(mm[-1], _pp)
                else:
                    mm.append(_pp)
            return "".join(mm)
        merged: list[str] = []
        for _p in paras:
            if not merged:
                merged.append(_p); continue
            _prev = merged[-1]
            if (_p_formula(_p) and _p_tail(_prev)) \
                    or (_p_lead(_p) and _p_tail(_prev)) \
                    or (_p_formula(_p) and _p_lead(_prev)):
                merged[-1] = _p_join(_prev, _p)
            else:
                merged.append(_p)
        if _col_mode:
            # 双栏：左右两列（flex），栏内各自合并段（"其中：f=h"同行）。
            # **必须附加流式 paras**——页界/表格/asset/chart 的页推进插入都走
            # 流式 `paras`（非左右列）；若省略，双栏页的图/表/页界全部丢失
            # （1032 图4/9 在双栏页 7.6.3.1/11.6.4 实测缺）。
            body = (f'<div class="cols"><div class="col">'
                    f'{_mrg_col(_left_paras, _p_lead, _p_formula, _p_tail, _p_join)}'
                    f'</div><div class="col">'
                    f'{_mrg_col(_right_paras, _p_lead, _p_formula, _p_tail, _p_join)}'
                    f'</div></div>') + "".join(paras)
        else:
            body = "".join(merged)
        if interleave:
            # 2026-09-01 表格归位：页号 ≥ 末行页（或页映射缺失行）的余表按序缀尾。
            body += "".join(chunk for _p, chunk in tbl_queue)
        elif md and "<table" in md:
            body += md
        # 2026-09-02 插图页位归位收尾：页号超过末行页（/无页界）未插入的插图
        # 缀尾；figure_html 剔除已逐张插入的段（防重复）。
        if asset_queue:
            body += "".join(seg for _p, seg in asset_queue)
        if chart_queue:
            body += "".join(seg for _p, seg in chart_queue)
        fig_residual = figure_html or ""
        if inserted_asset:
            for _seg in inserted_asset:
                fig_residual = fig_residual.replace(_seg, "", 1)
        # 2026-08-29 式中 hat/bar 符号 → KaTeX span（用户点名"特殊符号用专门
        # 插件渲染"）：必须在公式截图注入之后——span 的尖括号会切断
        # _FORMULA_SEG 的 [^<>] 匹配；反之 img 标签不含 ^/U+0304 零影响。
        # content_text 零污染，前端 katex.renderToString 出真排版。
        # 2026-08-30 国标排版还原三件套（语料级，GB/T 34406 §4/§5 实测）：
        # PUA 键横线（\ue5c6CH→—CH）/ 单位负指数上标（cm-1→cm⁻¹）/ 段首编号
        # 补空格（4原理→4 原理）。嵌套即执行序：最内层先跑 → formula 截图
        # 注入（干净文本匹配）→ 图题 → 三件套（注入 <sup> 尖括号，必须在
        # _FORMULA_SEG 之后）→ katex span 最后（最外层，其尖括号不影响已
        # 完成的匹配；weave 说明行判定不受 <sup> 干扰）。
        return katex_sym_html(space_clause_numbers_html(sup_unit_exponents_html(
            pua_bond_dash_html(_inject_formulas(_inject_figs(body)))))) + fig_residual


    def _full_evidence(ev_dicts: list) -> list:
        """核验输入用全量条款文本（ev_dicts 的 content_text 被截断，
        数值可能落在截断外导致核验误判——v5 实测修复：核验器从 DB 拉全量）。"""
        try:
            conn = get_db_connection()
            ids = [e["clause_revision_id"] for e in ev_dicts]
            full = {}
            if ids:
                ph = ",".join("?" * len(ids))
                for r in conn.execute(
                        f"SELECT clause_revision_id, content_text, modality, exception,"
                        f" subject, knowledge_type, modality_strength FROM clause_revision"
                        f" WHERE clause_revision_id IN ({ph})", ids).fetchall():
                    full[r["clause_revision_id"]] = dict(r)
        except Exception:
            return ev_dicts
        out = []
        for e in ev_dicts:
            d = dict(e)
            f = full.get(e["clause_revision_id"])
            if f:
                d["content_text"] = f["content_text"]
                d["modality"] = f["modality"]
                d["exception"] = f["exception"]
                d["subject"] = f["subject"]
            out.append(d)
        return out


    def _ev_dict(c, bm_keys: set, ann_cache: dict, patch_cache: dict | None = None):
        # 阶段4 富化：收藏/批注/置信度（R24/R25/R33）
        from src.core.query import understanding as _qu
        anns = ann_cache.get(c.clause_key) or []
        # 2026-08-26（P3-①）：patch_records 由调用方批量预取传入（patch_cache），
        # 消除"每条证据 1 次 clause_patch 查询"的 N+1（chat 批量证据场景）
        patch_records = (patch_cache or {}).get(c.clause_revision_id) or []
        # 人工核对确认（R-核对）：用户按原文核对后标为可信 → 后台联动可信 + 置信度提升
        user_confirmed = any(
            p.get("field_name") == "user_confirmed"
            and str(p.get("patched_value", "")).lower() in ("true", "1")
            for p in patch_records)
        return {
            "clause_revision_id": c.clause_revision_id,
            "doc_id": c.doc_id,
            "clause_key": c.clause_key,
            "knowledge_type": c.knowledge_type,
            "hierarchy_label": _qu.hierarchy_label(c),
            "modality": c.modality,
            "modality_strength": c.modality_strength,
            "standard_no": c.standard_no,
            "clause_number": c.clause_number,
            "title": c.title,
            "page_start": c.page_start,
            "legal_status": resolve_status(c.legal_status, getattr(c, "effective_from", None)),
            "source_spans": [
                {"page_number": s.page_number, "bbox": s.bbox} for s in c.source_spans],
            "content_text": c.content_text[:800],
            "content_html": _content_html(c.content_text, c.content_markdown,
                                          str(c.doc_id), c.clause_number,
                                          page_breaks=c.page_breaks,
                                          table_pages=[s.page_number
                                                       for s in c.source_spans
                                                       if s.span_type == "table"]),
            "table_summary": c.table_summary,
            "table_md": _html_to_text(c.content_markdown),
            "patched_fields": c.patched_fields,
            "patch_records": patch_records,
            "user_confirmed": user_confirmed,
            "type_confidence": max(c.type_confidence or 0, 0.9) if user_confirmed else c.type_confidence,
            "is_suspicious": False if user_confirmed else c.is_suspicious,
            "bookmarked": c.clause_key in bm_keys,
            "annotations": [{"annotation_id": a["annotation_id"],
                             "content": a["content"],
                             "annotation_type": a["annotation_type"]} for a in anns],
            "expanded_from": None,
        }

    def _placeholder_answer(query: str, evidences) -> str:
        if not evidences:
            return f"未在本地知识库中检索到与「{query}」相关的现行有效条款。请先导入文档。"
        lines = [f"根据本地知识库检索（第一阶段占位答案，未接入大模型）：", ""]
        for c in evidences:
            ref = f"[引用:{c.standard_no}-{c.clause_number}]"
            lines.append(f"- {c.standard_no} 第 {c.clause_number} 条：{c.content_text[:200]} {ref}")
            lines.append(f"  （第 {c.page_start} 页）")
        return "\n".join(lines)

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    # ===== 阶段六·批次5：更新模块 API 接线（pipeline/02 §3；鉴权/包裹格式与全站一致）=====

    # 运行中巡检批次的进程内登记（与 DB status='running' 构成双闸，防并发巡检）
    import threading
    _upd_runs_lock = threading.Lock()
    _upd_runs: set[str] = set()

    from src.core.api import routes_update, routes_law
    routes_update.register(app, _json_error)
    routes_law.register(app, _json_error)

    # 效力报告（决策 21 · 用户修订版：按文件目录分类体系，永不混排）
    from src.core.api import routes_report
    routes_report.register(app, _json_error)

    # 渠道台账（§11.0 R2b，2026-09-18）：巡检"渠道"的一等公民——只读
    # （链接/接线状态/运行健康度/上次成功查询），面板 R4 的数据源
    from src.core.api import routes_channels
    routes_channels.register(app, _json_error)

    # 设置→API 配置（2026-08-27：OCR/LLM 双通道凭据管理）
    from src.core.api import routes_settings
    routes_settings.register(app, _json_error)

    # R27 入库预览（Dry-Run）+ 批量分桶（决策 1/2）——只读；
    # 外发**默认关闭**，`allow_deep=true` 才走云深度通道并如实标注 egress（2026-09-17 D5）
    from src.core.api import routes_ingest_preview
    routes_ingest_preview.register(app, _json_error)

    # 材料平面（2026-09-17 定位转移 Phase A）：项目 / 参考资料收件 / 评审硬门 / 已批准材料检索。
    # **不碰法条链**——它只读写 material_project/material/material_chunk/material_fts 四张新表。
    from src.core.api import routes_materials
    routes_materials.register(app, _json_error)

    # 知识库多级目录（KB-FOLDER-PLAN §五第 2 步）：目录增删改查 + 待分类 + 范围集合。
    # ⚠ 与收藏夹（/api/v1/bookmark-folders）**无关**：那是单层收藏夹（folder_id 前缀 bmf_），
    #   本族是无限层级知识库目录（前缀 fld_），两张表各自表内引用，任何查询不得跨表 join。
    from src.core.api import routes_kb_folders
    routes_kb_folders.register(app, _json_error)


    return app


def bind_random() -> tuple[int, str]:
    """随机空闲端口 + 一次性 token（红线 6）。"""
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port, secrets.token_urlsafe(32)


def run() -> None:
    import os
    import uvicorn
    port, token = bind_random()
    app = create_app(token)
    # 单写者队列消费端（2026-08-26，P2-①）：watcher 入队的 ingest_doc 自此被真正消费
    try:
        from src.core.storage.write_queue_bootstrap import start_write_worker
        start_write_worker()
    except Exception:  # noqa: BLE001 - 队列消费失败不阻塞引擎启动
        pass
    # 法规目录定时刷新（spec 006）：按 law.catalog_refresh_days（缺省 1 天）自动刷新。
    # ⚠ 不走 src/core/update/scheduler.py —— 那个调度器的 start() 全仓无人调用（死代码），
    #   接进去刷新永不执行。这里沿用上面 write_queue_bootstrap 的同一模式。
    try:
        from src.core.knowledge.law_source.law_refresh import start_law_refresh
        start_law_refresh()
    except Exception:  # noqa: BLE001 - 刷新线程失败不阻塞引擎启动
        pass
    # token 通过 stdout 交给 Electron 主进程注入（P8：同时写 session 文件供启动器/前端读取）
    print(f"KNOWLEDGE_STATION_PORT={port}", flush=True)
    print(f"KNOWLEDGE_STATION_TOKEN={token}", flush=True)
    try:
        from src.core.config import get_settings
        session = get_settings().data_dir / "engine.session.json"
        session.write_text(
            json.dumps({"port": port, "token": token, "pid": os.getpid(),
                        "started_at": datetime.now().isoformat(timespec="seconds")}),
            encoding="utf-8")
    except Exception:
        pass
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    finally:
        from src.core.storage.write_queue_bootstrap import stop_write_worker
        stop_write_worker()
        try:
            from src.core.knowledge.law_source.law_refresh import stop_law_refresh
            stop_law_refresh()
        except Exception:  # noqa: BLE001 - 关停失败不覆盖启动路径的退出码
            pass
