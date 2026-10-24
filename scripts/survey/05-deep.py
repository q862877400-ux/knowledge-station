"""检查第 5 步（深化）：模块职责 / 接口明细 / 配置面 / 表读写关系。

前面几步只到「有什么」，这一步补「长什么样、谁用谁」：

| 产出 | 内容 |
|---|---|
| `modules.json` | 每个模块一句话职责（取 docstring 首句）+ 公开符号 + 规模 |
| `endpoints_deep.json` | 每条接口读哪些请求字段、回哪些字段、要不要令牌 |
| `config.json` | 环境变量 / 配置键：名字、出现在哪、被谁读 |
| `tables_io.json` | 每张表被哪些模块写、被哪些模块读 |

**只记录，不判断。**
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import dump, first_sentence  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "survey" / "data"



ALL_ROOTS = ("src", "tests", "scripts", "tools/gov-qa", "eval")


def iter_py(roots=ALL_ROOTS):
    for root in roots:
        d = ROOT / root
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            yield p


# ══════════════════════════════════════════════════════════════════════
# A. 模块职责索引
# ══════════════════════════════════════════════════════════════════════
def step_modules() -> None:
    print("\n[A] 模块职责索引")
    mods = []
    for p in iter_py():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            mods.append({"module": rel, "purpose": "", "parse_error": str(exc)[:120]})
            continue
        doc = ast.get_docstring(tree) or ""
        pub = [n.name for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
               and not n.name.startswith("_")]
        n_lines = p.read_text(encoding="utf-8", errors="replace").count("\n") + 1
        mods.append({
            "module": rel,
            "purpose": first_sentence(doc),
            "has_docstring": bool(doc),
            "public_symbols": pub,
            "n_public": len(pub),
            "lines": n_lines,
        })
    no_doc = [m for m in mods if not m.get("has_docstring")]
    dump("modules", {
        "generated_by": "scripts/survey/05-deep.py::step_modules",
        "caliber": ("`purpose` = 模块 docstring 的第一句（跳过标题行，按 `。`/`；`/换行切，"
                    "上限 160 字）。**没有 docstring 的"
                    "模块 purpose 为空** —— 这是记录，"
                    "不是评价。"),
        "counts": {"modules": len(mods), "with_docstring": len(mods) - len(no_doc),
                   "without_docstring": len(no_doc)},
        "modules": mods,
    })
    print(f"     {len(mods)} 个模块；有 docstring {len(mods) - len(no_doc)} / "
          f"没有 {len(no_doc)}")


# ══════════════════════════════════════════════════════════════════════
# B. 接口明细
# ══════════════════════════════════════════════════════════════════════
ROUTE_RE = re.compile(r'@(?:app|router)\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']')
BODY_KEY_RE = re.compile(r"""(?:body|payload|data)\.get\(\s*["']([a-z_][a-z0-9_]*)["']""")
BODY_IDX_RE = re.compile(r"""(?:body|payload)\[\s*["']([a-z_][a-z0-9_]*)["']\s*\]""")
QUERY_RE = re.compile(r"""^\s{4,8}([a-z_][a-z0-9_]*)\s*:\s*(?:int|str|bool|float)\s*=""")
RET_KEY_RE = re.compile(r"""["']([a-z_][a-z0-9_]*)["']\s*:""")


def step_endpoints_deep() -> None:
    print("\n[B] 接口明细")
    out = []
    for p in sorted((ROOT / "src" / "core" / "api").glob("*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for i, ln in enumerate(lines, 1):
            m = ROUTE_RE.search(ln)
            if not m:
                continue
            # 取这个路由的函数体（到下一个路由或文件尾）
            end = len(lines)
            for j in range(i, len(lines)):
                if ROUTE_RE.search(lines[j]):
                    end = j
                    break
            body = "\n".join(lines[i - 1:end])
            handler = ""
            for j in range(i - 1, min(i + 6, len(lines))):
                hm = re.match(r"\s*(?:async\s+)?def\s+(\w+)", lines[j])
                if hm:
                    handler = hm.group(1)
                    break
            out.append({
                "method": m.group(1).upper(),
                "path": m.group(2),
                "handler": handler,
                "file": str(p.relative_to(ROOT)).replace("\\", "/"),
                "lineno": i,
                "body_keys_read": sorted(set(BODY_KEY_RE.findall(body))
                                         | set(BODY_IDX_RE.findall(body))),
                "query_params": sorted(set(QUERY_RE.findall(body))),
                "response_keys": sorted(set(RET_KEY_RE.findall(body)))[:20],
                "lines": end - i + 1,
                "mentions_token": "authorization" in body.lower()
                or "require_token" in body.lower(),
            })
    # ⚠ 不要统计「多少个 handler 自己查令牌」—— 本仓是 `auth_middleware` 统一做的
    #   （`server.py` 的 `async def auth_middleware`，只放行 `/health` 与 `OPTIONS`）。
    #   每个 handler 里当然看不到令牌代码。第一版把 176 条全算成"没查令牌"，那是误读。
    no_token = [r for r in out if not r["mentions_token"]]
    dump("endpoints_deep", {
        "generated_by": "scripts/survey/05-deep.py::step_endpoints_deep",
        "caliber": ("`body_keys_read` = 函数体里 `body.get(\"k\")` / `body[\"k\"]` 出现的键；"
                    "`query_params` = 形如 `    x: int =` 的函数参数；"
                    "`response_keys` = 函数体里 `\"k\":` 形"
                    "态的键（**近似，不是完整响应模型**）。"
                    "**这是静态抽取，不是运行时 schema**。"),
        "auth_note": (
            "**令牌不是每个 handler 自己查的**：`ser"
            "ver.py` 有 `async def auth_middleware`，"
            "统一校验 `Authorization: Bearer <token>`，只放行 `/health` 与 `OPTIONS`。"
            "所以「handler 里没写令牌代码」是**设计如此**，不是缺鉴权。"
            "`mentions_token` 只记「这个 handler 的函数体里正好提到令牌」这一事实。"
        ),
        "counts": {"routes": len(out),
                   "handlers_mentioning_token": len(out) - len(no_token)},
        "routes": out,
    })
    print(f"     {len(out)} 条；handler 函数体里提到令牌的 "
          f"{len(out) - len(no_token)} 条（令牌由中间件统一校验）")


# ══════════════════════════════════════════════════════════════════════
# C. 配置面
# ══════════════════════════════════════════════════════════════════════
ENV_PAT = [
    re.compile(r"""os\.(?:environ\.get|getenv)\(\s*["']([A-Z_][A-Z0-9_]*)["']"""),
    re.compile(r"""os\.environ\[\s*["']([A-Z_][A-Z0-9_]*)["']"""),
    re.compile(r"""process\.env\.([A-Z_][A-Z0-9_]*)"""),
    re.compile(r"""process\.env\[\s*["']([A-Z_][A-Z0-9_]*)["']"""),
]
# 配置键的两种出现方式：
#   ① 直接写字面量：  _read_json_key("announce.min_interval_hours", 24)
#   ② **先存成模块级常量再传进去**：  SOURCES_KEY = "announce.sources"
#                                    _read_json_key(SOURCES_KEY, [])
# 第二版实测：只按字面量匹配只能抓到 7 个，而实际键有几十个 —— 因为本仓大量用②。
CFG_CALL = re.compile(
    r"""(?:_read_json_key|_write_json_key|get_config|set_config)\(\s*"""
    r"""(?:"([a-z_][a-z0-9_.]*)"|([A-Za-z_][A-Za-z0-9_]*))""")
CFG_CONST = re.compile(r"""([A-Za-z_][A-Za-z0-9_]*)\s*=\s*["']([a-z_][a-z0-9_]*\.[a-z0-9_.]+)["']""")


def step_config() -> None:
    print("\n[C] 配置面")
    env: dict[str, list[str]] = {}
    cfg: dict[str, list[str]] = {}
    for root in ("src", "scripts", "tests", "plugin/src", "plugin/client"):
        d = ROOT / root
        if not d.exists():
            continue
        for p in list(d.rglob("*.py")) + list(d.rglob("*.js")) + list(d.rglob("*.ts")):
            if "__pycache__" in p.parts or "node_modules" in p.parts:
                continue
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pat in ENV_PAT:
                for k in pat.findall(text):
                    env.setdefault(k, [])
                    if rel not in env[k]:
                        env[k].append(rel)
            consts = dict(CFG_CONST.findall(text))
            for lit, ident in CFG_CALL.findall(text):
                key = lit or consts.get(ident, "")
                if not key:
                    continue
                cfg.setdefault(key, [])
                if rel not in cfg[key]:
                    cfg[key].append(rel)
    # ③ 从种子库读真实存在的配置键（**比正则可靠**：正则会漏掉拼接键，
    #    而库里的行就是"确实被写过"的键）。
    db_keys: dict[str, dict] = {}
    seed = ROOT / "tests" / "fixtures" / "seed" / "knowledge-seed.db"
    if seed.exists():
        import sqlite3
        conn = sqlite3.connect(f"file:{seed}?mode=ro", uri=True)
        try:
            cols = [r[1] for r in conn.execute('PRAGMA table_info("app_config")')]
            if cols:
                for row in conn.execute(
                        "SELECT config_key, length(config_"
                        "value), is_encrypted, updated_at "
                        "FROM app_config ORDER BY config_key"):
                    db_keys[row[0]] = {"value_bytes": row[1], "is_encrypted": bool(row[2]),
                                       "updated_at": row[3]}
        finally:
            conn.close()

    dump("config", {
        "generated_by": "scripts/survey/05-deep.py::step_config",
        "caliber": ("环境变量 = `os.environ.get/getenv/env[...]` 与 `process.env.X` 的字面量；"
                    "配置键 = `_read_json_key` / `_write_json_key` / `get_config` / "
                    "`set_config` 的实参，**并解析模块级常量**"
                    "（本仓大量写成 `SOURCES_KEY = \"announce.sources\"` 再传常量）。"
                    "**拼接出来的键名看不到**。`used_by` 只列前 12 个引用点。"),
        "counts": {"env_vars": len(env),
                   "config_keys_in_code": len(cfg),
                   "config_keys_in_seed_db": len(db_keys),
                   "config_keys_union": len(set(cfg) | set(db_keys))},
        "config_keys_in_seed_db": db_keys,
        "config_db_note": (
            "`app_config` 表有 `is_encrypted` 列（实测 7 行全是 0）。"
            "这里只记键名与值的字节长度，**不记值本身**（有的键存的是源清单/状态，"
            "抄进来会让人误以为那是当前配置）。"
        ),
        "env": {k: {"used_by": v[:12], "n_refs": len(v)} for k, v in sorted(env.items())},
        "config_keys": {k: {"used_by": v[:12], "n_refs": len(v)} for k, v in sorted(cfg.items())},
    })
    print(f"     环境变量 {len(env)} 个 / 代码里的配置键 {len(cfg)} 个 / "
          f"种子库里的配置键 {len(db_keys)} 个")


# ══════════════════════════════════════════════════════════════════════
# D. 表读写关系
# ══════════════════════════════════════════════════════════════════════
WRITE_PAT = re.compile(
    r"""\b(?:INSERT\s+(?:OR\s+\w+\s+)?INTO|REPLACE\s+INTO)\s+["']?(\w+)""", re.I)
UPDATE_PAT = re.compile(r"""\bUPDATE\s+["']?(\w+)["']?\s+SET""", re.I)
DELETE_PAT = re.compile(r"""\bDELETE\s+FROM\s+["']?(\w+)""", re.I)
READ_PAT = re.compile(r"""\bFROM\s+["']?(\w+)["']?""", re.I)
JOIN_PAT = re.compile(r"""\bJOIN\s+["']?(\w+)["']?""", re.I)


def step_tables_io() -> None:
    print("\n[D] 表读写关系")
    schema = json.loads((DATA / "schema.json").read_text(encoding="utf-8"))
    known = {t["name"] for t in schema["tables"]}
    io: dict[str, dict[str, list[str]]] = {t: {"write": [], "read": []} for t in known}
    for p in iter_py(("src",)):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        text = p.read_text(encoding="utf-8", errors="replace")
        for pat in (WRITE_PAT, UPDATE_PAT, DELETE_PAT):
            for t in pat.findall(text):
                if t in known and rel not in io[t]["write"]:
                    io[t]["write"].append(rel)
        for pat in (READ_PAT, JOIN_PAT):
            for t in pat.findall(text):
                if t in known and rel not in io[t]["read"]:
                    io[t]["read"].append(rel)
    dump("tables_io", {
        "generated_by": "scripts/survey/05-deep.py::step_tables_io",
        "caliber": ("扫描 `src/**/*.py` 里的 SQL 字面量：写 = INSERT/REPLACE/UPDATE/DELETE "
                    "后面的表名；读 = FROM/JOIN 后面的表名。"
                    "**只抓字面量**：f-string 拼出来的表名看不到（本仓实测有 7 处）。"
                    "表名必须在种子库 `sqlite_master` 里存在，否则丢弃（避免把 CTE 别名当表）。"),
        "counts": {
            "tables": len(known),
            "tables_with_no_writer_found": sum(1 for v in io.values() if not v["write"]),
            "tables_with_no_reader_found": sum(1 for v in io.values() if not v["read"]),
        },
        "tables": io,
    })
    print(f"     {len(known)} 张表；静态查不到写入的 "
          f"{sum(1 for v in io.values() if not v['write'])} 张，"
          f"查不到读取的 {sum(1 for v in io.values() if not v['read'])} 张")


def main() -> int:
    step_modules()
    step_endpoints_deep()
    step_config()
    step_tables_io()
    print("\n全部落盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
