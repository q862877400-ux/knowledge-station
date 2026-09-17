# -*- coding: utf-8 -*-
"""审计：**哪些 HTTP 端点声明成 `async def`，却在做同步重活？**（§10.71，复核 b12 的教训）

为什么要有这个探针：§10.59 修了 2 条端点、b12 又发现 2 条**同族**的（产出物那一侧）——
根因不是"漏了",而是**从来没有人把全部端点扫过一遍**。每次靠复核撞见一条修一条，就永远有下一条。

判据分两层（都只看静态代码，不猜）：
  T1「async 但**整个函数体里一个 `await` 都没有**」——零假阳性：这种端点**永远不会让出控制权**，
     写成 async 纯属惯性；真做重活就是**必然**卡事件循环。
  T2「有 await，但**可达路径上**有阻塞标记」（文件 I/O / 哈希 / 子进程 / openpyxl / pptx /
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


def _markers_in(src: str) -> set[str]:
    return {label for pat, label in MARKERS if re.search(pat, src)}


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
