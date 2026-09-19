# -*- coding: utf-8 -*-
"""审计：**哪些 HTTP 端点声明成 `async def`，却在做同步重活？**（§10.71，复核 b12 的教训）

为什么要有这个探针：§10.59 修了 2 条端点、b12 又发现 2 条**同族**的（产出物那一侧）——
根因不是"漏了",而是**从来没有人把全部端点扫过一遍**。每次靠复核撞见一条修一条，就永远有下一条。

判据分两层（都只看静态代码，不猜）：
  T1「async 但**整个函数体里一个 `await` 都没有**」——零假阳性：这种端点**永远不会让出控制权**，
     写成 async 纯属惯性；真做重活就是**必然**卡事件循环。
  T2「有 await，但**可达路径上**有阻塞标记」（文件 I/O / 哈希 / 子进程 / openpyxl /
     网络 / sleep / 遍历）——与 `/effect/export` 原先的形状一模一样（await 一个 body，再干重活）。

可达性：从端点函数出发按调用图 BFS（depth ≤ 7），名字按**定义模块的 globals + 函数体内的
局部 import** 解析（后者是必须的：库里的端点普遍写成
`def ep(): from src.core.exports import effect_report; effect_report.xxx(...)`）。
解析不了的名字计入 `unresolved` 并**如实打印**（"扫不到"≠"没有"——b12 的 C2 就是这么空过的）。

⚠ **已知盲区（写在明面上）**：这套判据只看"**I/O 形状**的重活"（读文件/哈希/子进程/渲染/网络…）。
**纯 CPU / 纯 SQL 聚合看不见**——`/report/effect` 这类"秒级同步聚合"在审计里是 `heavy=-`，
但它照样是 `await` 都没有的 `async def`（T1 那一栏会点出来）。深度上限也会截断长链
（depth=3 时 `/report/research` 就是"仅轻标记"；§10.71 把它抬到 5 才照出来）。

用法（仓库根，两条都行）：
    `.venv\\Scripts\\python.exe scripts\\audit-async-endpoints.py`
    `.venv\\Scripts\\python.exe scripts\\audit-async-endpoints.py --json var\\tmp\\audit.json`
只读：只在**临时** KS_DATA_DIR 下建一个 app，不碰真库、不改任何文件（`--json` 除外）。
它**不是门禁**（启发式审计，永远退出 0）；真正的闸门是
`tests/test_material_api.py::TestSlowEndpointsAreDeclaredSync`。
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import json
import os
import re
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 允许从任意 cwd 调起

#: 阻塞标记 → 归类。宁可多报（这是**候选清单**，下一步逐条实测）。
MARKERS: list[tuple[str, str]] = [
    (r"\bsha256\b|\bhashlib\b|\bmd5\b|\bfile_hash\b|_sha256_file|blake2", "hashing"),
    (r"read_bytes|read_text|write_bytes|write_text|\bopen\(", "file-io"),
    (r"subprocess|Popen|check_output|check_call|os\.system", "subprocess"),
    (r"\bfitz\.|\bmineru\b|MinerU|extract_text|\bocr\b", "pdf/ocr"),
    (r"openpyxl|load_workbook|Presentation\(|\.save\(", "office/render"),
    (r"urlopen|requests\.|httpx\.|\bsocket\.", "network"),
    (r"time\.sleep", "sleep"),
    (r"os\.walk|\.rglob\(|\.glob\(", "walk"),
    (r"shutil\.|zipfile|\.unlink\(|\.mkdir\(", "fs-copy"),
    (r"executemany|executescript|BEGIN IMMEDIATE", "bulk-db"),
    # ⚠ §10.78 补的**盲区**族：**藏在库内部的**重活。标记表原先只认裸调用
    # （`requests.`/`httpx.`/`open(`），于是"每次调用都去加载/下载一个模型"
    # 这种最贵的活**完全扫不到**——§10.74 那个 `/health` 6.79s 就是这么漏掉的
    # （`fastembed.TextEmbedding(...)` 经 `huggingface_hub` 外发）。
    # 判据是**名字**：项目自己与常见库的加载入口。
    (r"fastembed|TextEmbedding|huggingface_hub|hf_hub_download|snapshot_download|"
     r"sentence_transformers|\bCrossEncoder\b|reranker\.|_get_model|is_available\(", "model-load"),
    (r"\btorch\.|transformers\.|\bwhisper\b|jieba\.|onnxruntime", "ml-runtime"),
]

#: 已知的异步等待（await 之后就让出控制权），不参与 T2 判定——但**不豁免** T1。
_ASYNC_ONLY = re.compile(r"^(await_|asyncio|anyio)")

#: **轻标记**：单独出现说明不了什么（`get_db_connection()` 里就有个 `mkdir`，
#: 于是它顺着"任何碰库的助手"传染到几乎每条端点）。只有重标记才算"做了重活"。
LIGHT_MARKERS = {"fs-copy"}


def _funcs_of(mod) -> dict[str, object]:
    out = {}
    for name, obj in vars(mod).items():
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            out[name] = obj
    return out


def _modules_of(mod) -> dict[str, object]:
    out = {}
    for name, obj in vars(mod).items():
        if inspect.ismodule(obj):
            out[name] = obj
    return out


def _call_names(tree: ast.AST) -> list[tuple[str, str | None]]:
    """收集调用点：('f', None) 表示 `f(...)`；('mod', 'g') 表示 `mod.g(...)`。"""
    names: list[tuple[str, str | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Name):
            names.append((f.id, None))
        elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            names.append((f.value.id, f.attr))
    return names


def _code_only(src: str) -> str:
    """只留**代码**：删掉 docstring 与注释（§10.78 补的一个**假阳性**来源）。

    为什么必须做：标记是**按名字**匹配的，而注释里天天出现这些名字——
    §10.74 我在 `embedder.health()` 的 docstring 里写了"这里原先调 `is_available()`"，
    于是 `/health` 被新标记判成"要加载模型"，而它恰恰是**修好之后不加载**的那条。
    注释不是行为：判据自己得先把它们去掉（`ast.unparse` 天然丢注释；docstring 要手动摘）。
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def _markers_in(src: str) -> set[str]:
    try:
        code = _code_only(src)
    except SyntaxError:                     # pragma: no cover - 源码读坏时退回原文
        code = src
    return {label for pat, label in MARKERS if re.search(pat, code)}


def _local_aliases(fsrc: str, pkg: str) -> tuple[dict[str, object], dict[str, object]]:
    """函数体**内部** `import` 出来的名字 → 模块 / 函数。

    ⚠ 不做这一步就是**盲区**，而且正好漏掉本探针要抓的那一类：库里的端点普遍写成
    `def ep(): from src.core.exports import effect_report; effect_report.xxx(...)`
    ——`effect_report` 在模块 globals 里**根本不存在**，解析不到就被丢进 unresolved，
    于是"做了重活"的端点静默变成"仅轻标记"（§10.71 实测：补这一步之前
    `/report/effect/export` 在审计里**完全隐形**）。**扫不到 ≠ 没有。**
    """
    import importlib
    mods: dict[str, object] = {}
    funcs: dict[str, object] = {}
    for node in ast.walk(ast.parse(fsrc)):
        if isinstance(node, ast.Import):
            for a in node.names:
                try:
                    if a.asname:
                        mods[a.asname] = importlib.import_module(a.name)
                    else:
                        mods[a.name.split(".")[0]] = importlib.import_module(a.name.split(".")[0])
                except Exception:                              # pragma: no cover - 缺依赖的模块
                    continue
        elif isinstance(node, ast.ImportFrom):
            try:
                m = importlib.import_module("." * node.level + (node.module or ""), pkg)
            except Exception:                                  # pragma: no cover
                continue
            for a in node.names:
                obj = getattr(m, a.name, None)
                if obj is None:
                    # `from pkg import submodule`：`getattr(pkg, sub)` 拿不到**子模块**
                    # （`from pkg import x` 能成是靠 import 系统的回退）。少了这一条，
                    # `from src.core.exports import research_report as rrep` 就解析不到，
                    # `/report/research` 于是被判成"仅轻标记"（§10.71 实测踩到）。
                    try:
                        obj = importlib.import_module(f"{node.module}.{a.name}")
                    except Exception:
                        obj = None
                if inspect.ismodule(obj):
                    mods[a.asname or a.name] = obj
                elif obj is not None:
                    funcs[a.asname or a.name] = obj
    return mods, funcs


def awaits_like(src: str) -> int | None:
    """源码里"**会真正让出事件循环**"的三类语法节点总数（§10.86）。

    三类：`Await`（`await x`）、`AsyncFor`（`async for`）、`AsyncWith`（`async with`）。
    ⚠ **`async for` / `async with` 必须算**：它们编译成 `await __anext__` / `__aenter__`，
    但 AST 里**没有 `Await` 节点**——只数 `Await` 会把"只写了 `async for` 的 async 端点"
    误判成"零 await ⇒ 该改 `def`"，而改成 `def` 会直接**语法/语义上不成立**（b15 的 INFO-1）。

    返回 `None` = **源码读不出来**（`ast.parse` 抛 `SyntaxError`）。调用方必须把它当**红**
    （fail-closed），**不许**当"没有 await"（那是静默放行，b15 的 INFO-3）。
    内部先 `textwrap.dedent`：`inspect.getsource()` 对闭包内定义的端点会给**带缩进**的源码。
    """
    try:
        tree = ast.parse(textwrap.dedent(src))
    except SyntaxError:
        return None
    return sum(1 for n in ast.walk(tree)
               if isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)))


def never_yields(src: str) -> bool:
    """这段 `async def` 端点源码**永远不会真正让出控制权**吗？

    判据（**AST，不看文本**）：源码里**没有** `Await`，或者每个 `Await` 都是
    `xxx.json()` / `xxx.body()` 这种"读 body"。

    ⚠ **名字比语义强**（b15 的 INFO-1/INFO-2，两处都**偏保守**）：
      · 只数 `Await` ⇒ 只写了 `async for`/`async with` 的端点会被判成"从不 yield"（多红）；
      · `body = await read_json(request)`（助手内部才 `await request.json()`）被判成"会 yield"（放行）。
    这一条是**诊断量**；"零 await"那一档由 `awaits_like()` 判
    （它把 `async for`/`async with` 也算上），所以那个多红的方向不会漏东西。

    ⚠ **必须走 AST**（独立复核 b14 的 MEDIUM-2）：判据原先写在测试里、读的是**原始源码文本**
    （`[ln for ln in src.splitlines() if "await " in ln]`）——于是
    **一句含 `await ` 的 docstring 或注释就能静默豁免整个端点**（复核实测：同族端点
    docstring 写"本端点唯一的 await 只是读 body" ⇒ 闸门 GREEN 放行）。而 `_code_only()`
    早就为审计脚本修过同一课（"注释不是行为"）——**闸门自己没吃这一课**。

    ⚠ **范围是整段源码，包含嵌套函数**（**有意**，代价已量化）：`/api/v1/chat/completions`
    的外层体内唯一 `await` 只是读 body，但它的嵌套 `async def event_stream()` 里有
    `await anyio.to_thread.run_sync(...)` ⇒ 这条请求在**流式迭代**期间**真会**把事件循环让出去
    （逐块从线程池取 LLM 输出）。若只数外层自己的 `await`，这个端点会被误判成"从不 yield"。

    ⚠ **但"源码里存在" ≠ "执行路径上存在"——这是本判据的能力边界**（独立复核 b16 的 D4）：
    b16 构造出两条静态**判不准**的形状，实测都能冻结事件循环 **0.650s**：
      ① 唯一的 `await` 是 `await _read_json(request)`（助手内部才 `await request.json()`）；
      ② 外层只读 body，嵌套 `async def` 里有真 `await` 但**从不被迭代**。
    两者都因为"源码里出现了一个非读-body 的 await"被判成"会 yield"⇒ 放行。
    ⇒ 所以本函数**只是诊断量**（审计报告 + 名单条目的第二关），**不是闸门**。闸门在
    `tests/test_material_api.py::test_async端点必须在显式名单里`：**async 端点必须在显式名单里
    写明理由，任何新形状默认红**——正确的过程间 + 可达性分析静态上做不到，与其继续打补丁，
    不如把举证责任反过来。

    ⚠ **它是"may"分析**（独立复核 b17 的 LOW-3）：只要源码里**存在**一个非读-body 的 `await`
    就算"会让出"，哪怕那段代码**永远执行不到**——`if False: await x` **一行**就能豁免整条端点；
    同族的还有"await 一个已完成的 Future"、"`try:` 里必然抛的 await"。
    ⇒ 残余逃逸面比 §10.87 §9 登记的两条（助手包装、从不迭代的嵌套生成器）**更宽**。
    这正是闸门在 §10.87 改成**名单制**、并在 §10.88 把第二关换成 `effective_real_await()`
    （会把嵌套助手内联进去）的原因——但**判据永远只是第一道**，量具与人工复核仍是必需的。

    ⚠ **解析失败 ⇒ 返回 True（判成"从不 yield"= 红）**：`SyntaxError` 下**没有**任何依据说
    "它会让出控制权"，fail-open（返回 False）会让一个将来忘记 `dedent` 的调用点**静默放行**
    全部缩进端点（b15 的 INFO-3 实测）。安全侧是 fail-closed。
    """
    try:
        tree = ast.parse(textwrap.dedent(src))
    except SyntaxError:
        return True                          # 读不出来 ⇒ 当成"从不 yield"（红），不静默放行
    awaits = [n for n in ast.walk(tree) if isinstance(n, ast.Await)]
    if not awaits:
        return True
    for a in awaits:
        v = a.value
        if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                and v.func.attr in ("json", "body")):
            return False
    return True


def _own_scope_nodes(fn: ast.AST):
    """`fn` **自己作用域**里的节点（跳过嵌套函数/lambda 的内部）。

    为什么必须这么数（§10.86 自查发现，当时 b15 复核在跑）：`ast.walk(fn)` 会把**嵌套函数**里的
    `Yield`/`Await` 也算到外层头上 ⇒
      ① 一个 `async def helper()` 里若嵌了一个**同步**生成器 `def inner(): yield 1`，
         它会被误判成"没有 await 的 async 生成器"（**假阳性**：`helper` 根本不是生成器；
         实测 `nested_async_gen_without_await` 会返回 `['helper']`）；
      ② 反过来，一个**真** async 生成器若唯一的 `await` 写在嵌套 async 函数里，会被误判成
         "无 await" ⇒ 判据放行（**假阴性**，闸门静默失效）。
    本条判据问的是"**这个函数自己的 body** 有没有 yield/await"，所以按作用域切。
    （`never_yields()` 是**有意**数整段源码的——它的语义是"这条请求会不会让出事件循环"，
    嵌套 async 生成器里的 await 真的会让出；两者的差别写在各自 docstring 里。）
    """
    stack: list[ast.AST] = [fn]
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            stack.append(child)


def nested_async_gen_without_await(src: str) -> list[str]:
    """端点里那些**没有 await 的 async 生成器**的名字（§10.80 的判据，也走 AST）。

    ⚠ `yield`/`await` 都只数**该函数自己作用域**里的（`_own_scope_nodes`）——
    嵌套函数里的 `yield` 不能把外层 `async def` 变成"生成器"。
    """
    out: list[str] = []
    try:
        tree = ast.parse(src)
    except SyntaxError:                      # pragma: no cover
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        own = list(_own_scope_nodes(node))
        has_yield = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in own)
        has_await = any(isinstance(n, ast.Await) for n in own)
        if has_yield and not has_await:
            out.append(node.name)
    return out


# ---------------------------------------------------------------- §10.88：名单的"第二关"判据
def _endpoint_node(tree: ast.AST) -> ast.AST | None:
    """源码里的**第一个**函数定义（= 端点自己）。"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    return None


def _body_read(a: ast.Await) -> bool:
    v = a.value
    return (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
            and v.func.attr in ("json", "body"))


def _call_name(value: ast.AST) -> str | None:
    """`f(...)` ⇒ `"f"`；其它（属性调用、非调用）⇒ None。"""
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id
    return None


def _real_suspension(fn: ast.AST, nested: dict, depth: int = 0) -> bool:
    """`fn`（含它**调用的**嵌套助手）在自己的执行路径上有没有**真**挂起点？

    "真"= 不是读 body 的 `await`，或 `async for`/`async with`/`yield`（迭代时会让出）。
    ⚠ 递归深度上限 4：超过就当"有"（放行）——这种情况交给量具与人工复核，别在这里猜。
    """
    if depth > 4:
        return True
    own = list(_own_scope_nodes(fn))
    if any(isinstance(n, (ast.AsyncFor, ast.AsyncWith, ast.Yield, ast.YieldFrom)) for n in own):
        return True
    for a in (n for n in own if isinstance(n, ast.Await)):
        if _body_read(a):
            continue
        helper = nested.get(_call_name(a.value) or "")
        if helper is not None:
            if _real_suspension(helper, nested, depth + 1):
                return True
            continue                       # 内联后只是读 body ⇒ 不算
        return True                        # 其它任何 await（to_thread / sleep / 未知调用）都算
    used = {n.id for n in own if isinstance(n, ast.Name)}
    for name, node in nested.items():
        if name in used and _real_suspension(node, nested, depth + 1):
            return True                    # 被引用（例如交给 StreamingResponse）的嵌套生成器
    return False


def effective_real_await(src: str) -> bool:
    """这条 async 端点**执行路径上**真的会让出控制权吗？（§10.88：名单第二关的判据）

    ⚠ **它不是 `never_yields()` 的"加严版"——两个方向都有**（独立复核 b18 的 LOW-2 + b19 的 N1：
    原 docstring 写"比 `never_yields` 严一档"，**不处处成立**，同一句错话当时还留在
    `tests/test_material_api.py` 里，b19 一并指出、已一起改）：
      · 更**严**：`await _read_json(request)` 这类**本端点内嵌套的 async 助手**会被内联，
        内联后只剩读 body ⇒ 判"没有真挂起点"（H1 形状；b16 实测它堵 0.650s）；
      · 更**宽**：`async for`/`async with`/`yield` 算挂起点（`never_yields` 只数 `Await` **节点**，
        对"只有 `async for`"的**合法**端点会误红，见 b17 的 **E3** —— 这是"名单不可满足"那一条；
        ⚠ b19 的 N2：这里原写"E3/E6"，**E6 是 `setswitchinterval`/GIL flaky，与 `async for` 无关**）。

    判据顺序：
      ① `async for` / `async with` / `yield` ⇒ **算**（等待点常在库源码里，源码里看不到 `Await`）；
      ② 读 body 的 `await`（`x.json()`/`x.body()`）**不算**；
      ③ **调用本端点内嵌套的 async 助手 ⇒ 内联进去再看**（H1 靠这一层判准）；
      ④ 本端点**引用了的**（名字出现在自己作用域的 `Name` 节点里）嵌套 async 生成器 ⇒ **算**；
      ⑤ 解析失败 ⇒ **False**（fail-closed ⇒ 名单判红）。

    ⚠ **能力边界**（写在明面上）：
      · 只内联**同一段源码里嵌套的** async 助手；`await read_json(request)`（模块级/跨模块）算"有"
        ——过程间分析不在能力内；
      · ④ 的"引用"只看 `Name` 节点：若那条生成器是被**装饰器/模块级注册表**登记的
        （`@register async def stream(): …` + `return StreamingResponse(REGISTRY[-1]())`），
        判据**看不到它** ⇒ 判 False ⇒ **名单会红**（独立复核 b18 的 MEDIUM-1）。
        **这一条是有意保留的**：闸门问的是"**必须** async 吗"，而答案是否定的 ——
        实测(`var/tmp/probe-def-streaming.py`) `def` 端点返回 `StreamingResponse(async_gen())`
        **一样能真流式**（200 + 逐块 `chunk0|chunk1|chunk2|`，与 `async def` 逐字节相同）
        ⇒ 补救是"改成 `def`"，**无害**；所以这里**不放宽**判据（放宽会让 H5 那种
        "端点体里先跑 0.65s 同步活、再返回流"的形状也混过去）。有一条用例钉这个前提：
        `tests/test_material_api.py::test_def端点返回StreamingResponse仍然真流式`。
      · 递归深度上限 4：超过就当"有"（放行；只朝放行截断，不会误红；b18 的 INFO-1 实测第 5 层起放行）。
    """
    try:
        tree = ast.parse(textwrap.dedent(src))
    except SyntaxError:
        return False
    fn = _endpoint_node(tree)
    if fn is None:                                          # pragma: no cover
        return False
    nested = {n.name: n for n in ast.walk(fn)
              if isinstance(n, ast.AsyncFunctionDef) and n is not fn}
    return _real_suspension(fn, nested)


def _is_local(fn, name: str) -> bool:
    """名字是不是这个函数的**局部/闭包变量**（`body.get`、`project_id.strip` 这类）。

    局部变量静态上永远解析不到，把它们全塞进 unresolved 会把"诚实边界"那个数字
    变成噪声（§10.71：1737→ 大幅下降），反而掩盖真正跨模块没解析出来的名字。
    """
    code = getattr(fn, "__code__", None)
    if code is None:
        return False
    return name in (code.co_varnames + code.co_freevars + code.co_cellvars)


def audit_endpoint(ep, depth_max: int = 7) -> dict:
    try:
        raw = textwrap.dedent(inspect.getsource(ep))
    except (OSError, TypeError) as e:                      # pragma: no cover
        return {"error": f"读不到源码: {e}"}
    tree = ast.parse(raw)
    awaits = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Await))

    mod = sys.modules[ep.__module__]
    mod_funcs = _funcs_of(mod)
    mod_mods = _modules_of(mod)

    hits: dict[str, list[str]] = {}          # label -> 命中它的函数名（可达路径）
    unresolved: set[str] = set()
    queue: list[tuple[object, str, int]] = [(ep, ep.__qualname__, 0)]
    seen: set[str] = set()
    while queue:
        fn, label, depth = queue.pop(0)
        key = f"{getattr(fn, '__module__', '?')}.{getattr(fn, '__qualname__', fn)}"
        if key in seen or depth > depth_max:
            continue
        seen.add(key)
        try:
            fsrc = textwrap.dedent(inspect.getsource(fn))
        except (OSError, TypeError):
            continue
        for lab in _markers_in(fsrc):
            hits.setdefault(lab, []).append(label)
        if depth == depth_max:
            continue
        owner = sys.modules.get(getattr(fn, "__module__", ""), mod)
        owner_funcs = _funcs_of(owner)
        owner_mods = _modules_of(owner)
        local_mods, local_funcs = _local_aliases(fsrc, getattr(owner, "__package__", "") or "")
        for a, b in _call_names(ast.parse(fsrc)):
            if b is None:
                tgt = local_funcs.get(a) or owner_funcs.get(a) or mod_funcs.get(a)
                if tgt is None:
                    if a not in ("str", "int", "len", "min", "max", "print", "isinstance") \
                            and not _is_local(fn, a):
                        unresolved.add(a)
                    continue
                if inspect.isfunction(tgt) and tgt is not fn:
                    queue.append((tgt, a, depth + 1))
            else:
                sub = local_mods.get(a) or owner_mods.get(a) or mod_mods.get(a)
                if sub is None:
                    if not _is_local(fn, a):
                        unresolved.add(f"{a}.{b}")
                    continue
                tgt = getattr(sub, b, None)
                if inspect.isfunction(tgt):
                    queue.append((tgt, f"{a}.{b}", depth + 1))
    return {
        "awaits": awaits,
        "markers": {k: sorted(set(v)) for k, v in sorted(hits.items())},
        "unresolved": sorted(unresolved),
        "reached": len(seen),
    }


def main() -> int:
    out_json = None
    if "--json" in sys.argv:
        out_json = sys.argv[sys.argv.index("--json") + 1]

    tmp = tempfile.mkdtemp(prefix="ks_audit_")
    os.environ["KS_DATA_DIR"] = tmp
    from src.core import config
    config.reset_settings()
    from src.core.api.server import create_app
    app = create_app("audit-token")

    rows = []
    for r in app.routes:
        ep = getattr(r, "endpoint", None)
        path = getattr(r, "path", None)
        if ep is None or path is None or not path.startswith("/api/"):
            continue
        if not asyncio.iscoroutinefunction(ep):
            continue                                   # 已经是 def ⇒ 线程池，合格
        info = audit_endpoint(ep)
        rows.append({
            "path": path,
            "methods": sorted(getattr(r, "methods", []) or []),
            "module": ep.__module__,
            "func": ep.__qualname__,
            **info,
        })

    for x in rows:
        x["heavy"] = sorted(k for k in (x.get("markers") or {}) if k not in LIGHT_MARKERS)
    tier1 = [x for x in rows if x.get("awaits") == 0]
    tier2 = [x for x in rows if x.get("awaits", 0) > 0 and x.get("heavy")]

    def _attr(x) -> str:
        """重标记 + 它是**哪个函数**命中的（端点自己还是传递到的助手）。"""
        return " ".join(f"{lab}@{'+'.join(fns[:2])}" for lab, fns in (x.get("markers") or {}).items()
                        if lab not in LIGHT_MARKERS)

    print(f"async 端点总数: {len(rows)}   T1(无 await)={len(tier1)}   T2(有 await+重标记)={len(tier2)}")
    print("=" * 100)
    for title, items in (("T1  async def 但函数体里一个 await 都没有（永远不会让出控制权）", tier1),
                         ("T2  有 await，但可达路径上有**重**阻塞标记", tier2)):
        print(f"\n### {title}  —— {len(items)} 条")
        for x in sorted(items, key=lambda y: (y["module"], y["path"])):
            print(f"  {','.join(x['methods']):8s} {x['path']:58s} {_attr(x) or '(仅轻标记)'}")
    # T1 里带重标记的是最该先修的（必然阻塞 + 真做重活）
    worst = [x for x in tier1 if x.get("heavy")]
    print(f"\n### 优先修：T1 且带**重**标记 —— {len(worst)} 条")
    for x in sorted(worst, key=lambda y: y["path"]):
        print(f"  {','.join(x['methods']):8s} {x['path']:58s} {_attr(x)}")
    print(f"\n[诚实边界] 名字解析不到（跨模块实例方法等）共 "
          f"{sum(len(x.get('unresolved', [])) for x in rows)} 处："
          f"扫不到的**不等于**没有，下一步逐条实测。")
    print("[诚实边界] 轻标记（" + ",".join(sorted(LIGHT_MARKERS)) + "）单独出现不算重活："
          "`get_db_connection()` 里就有一个 `mkdir`，会传染到任何碰库的助手。")
    if out_json:
        Path(out_json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"完整清单已写入: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
