"""知识库多级目录 · 对真库执行归位（KB-FOLDER-PLAN §五第 1 步的"落库"那一半）。

方案真源：``docs/KB-FOLDER-PLAN.md``。姊妹脚本 ``scripts/preview-folder-filing.py``
是**只读预览**（在真库副本上跑、产出业主过目的清单）；本脚本是**对真库落库**的那一步。

════════════════════════ 它默认什么也不做 ════════════════════════

默认是**预演**：只用 ``mode=ro`` 打开真库（SQLite 保证不写），算出"将要发生什么"并打印摘要，
**一个字节都不写、不建备份、不落任何文件**（除非显式给 ``--report``）。加 ``--apply`` 才写库。

════════════════════════ 写库的顺序（任一步不成立就中止）════════════════════════

1. **先看引擎在不在**（``%APPDATA%\\KnowledgeStation\\engine.session.json`` 或 ``$KS_DATA_DIR``
   下同名文件）：端口有人听 ⇒ 打印一行**醒目警告**（说明正在写库），但**不阻塞**
   （SQLite 允许单写者，写锁冲突有 60 秒 busy_timeout 兜着）。
2. **先备份**：用 SQLite 的 backup 接口把**整份真库**备份到
   ``%APPDATA%\\KnowledgeStation\\backups\\knowledge-pre-folders-<时间戳>.db``，
   然后**读回核对**（页数 / 文档数 / schema 对象数三项都要对上）。备份失败 ⇒ 立即中止，
   **绝不在没有备份的情况下写**。
3. **只建三张新表**（``folder`` / ``folder_member`` / ``doc_filing_state``）：DDL 从
   ``src/core/storage/schema.sql`` 里**现取**（不是手抄一份，免得日后漂移）。
   建表前后比对库内**全部** schema 对象的 SQL 指纹：既有对象只要有一个被改/被删 ⇒ 中止；
   新增的对象也必须属于这三张表。**本步绝不动任何既有表/列。**
4. **顶层预建四个空目录**（业主 2026-09-21 定）：
   「标准」(sort=10) ·「法律法规」(20) ·「公司制度」(30) ·「待分类」(90)。
   手定的 ``sort`` 表达**业务顺序**（按拼音会把「待分类」排到第二位，不是业主要的）；
   其余目录 ``sort`` 一律 0，交给第 2 步的拼音兜底。**按名字复用**已存在的顶层目录 ⇒ 幂等。
5. **标准树挂到「标准」下面，跳过重复的那一层**：计划推导出来的第一层叫
   「国家标准·行业标准·团体标准」，它挂在「标准」下面就是**重复** ⇒ 把它下面的第二层
   （``A 综合``/``B 农业林业``/…）**直接作为「标准」的子目录**。
   「法律法规」「公司制度」**保持空的**（真数据里这两支 0 篇）。
6. **「待分类」**：映射里"没有分类"的那些（真库实测 379 篇）放进去、``stage='queued'``；
   再加 ``doc_meta.catalog_hidden=1`` 的那 2 篇（``GB/T 12668.8-2017`` / ``GB 9706.222-2022``，
   正文条款为零 ⇒ 被踢出目录，见方案 §十）—— 它们的 ``stage='failed'``、
   ``failure_kind`` 写中文说明。**登记 failure_kind 前先真的去数一下条款**（``clause_revision``）：
   只有"正文条款确实为零"才写"正文条款为零"，数出来不为零就如实写另一句（不编）。
7. **读回自证**：写完**关连接、重新打开真库**读（不看写函数的返回值自说自话），打印
   各级目录数 / 成员行数 / 「待分类」里多少篇 / 随机抽 20 个目录的"目录名 → 里面的文件名"，
   以及"库文件（含 -wal/-shm）写入前后是否一致地增长"，最后把**计划推出的预期数字**与
   库里的实际数字逐条对照（不一致 ⇒ 退出码 3）。另附一份机器可读 JSON（``--report``）。

⚠ 两条**刻意**的取舍（免得被当成 bug）：
  · 预演时判定"真库没被动过"只看 ``.db`` 本体的**大小 + mtime**（与预览脚本同口径），
    不看 ``-wal/-shm`` —— 引擎在跑时它自己会写 WAL，那**不是本脚本的写入**。
  · "库文件总量增长了"只**打印**、不当作失败闸门：引擎的 checkpoint 会把 WAL 收进 .db、
    量可能变小；**真正的闸门是行数**（读回来的目录/归属/状态条数对不对）。

════════════════════════════ 回退办法 ════════════════════════════

本次只**新增**三张新表的行，**没有改任何既有表、任何既有列**（第 3 步的 schema 指纹就是证据）
⇒ 回退不用碰任何既有数据：

    ① 清空这三张表（推荐：库结构留着，第 2 步还要用）——
       .venv\\Scripts\\python.exe -c "import sqlite3;c=sqlite3.connect(r'<库路径>');c.executescript('DELETE FROM folder_member; DELETE FROM folder; DELETE FROM doc_filing_state;');c.commit();c.close()"
    ② 连表一起删（第 2 步要重建）——
       .venv\\Scripts\\python.exe -c "import sqlite3;c=sqlite3.connect(r'<库路径>');c.executescript('DROP TABLE IF EXISTS folder_member; DROP TABLE IF EXISTS folder; DROP TABLE IF EXISTS doc_filing_state;');c.commit();c.close()"
    ③ 用第 2 步的备份**整份还原**（先**停掉引擎**，再把 knowledge.db-wal / knowledge.db-shm 删掉）——
       copy /Y "<备份路径>" "<库路径>"

（脚本把这三条连同本次的实际路径**打印出来**，不用回来翻文档。）

════════════════════════════ 跑法 ════════════════════════════

    .venv\\Scripts\\python.exe scripts\\apply-folder-filing.py                  # 预演（不写）
    .venv\\Scripts\\python.exe scripts\\apply-folder-filing.py --apply          # 真写（先备份）
    .venv\\Scripts\\python.exe scripts\\apply-folder-filing.py --source D:\\x\\knowledge.db
    .venv\\Scripts\\python.exe scripts\\apply-folder-filing.py --apply --report D:\\out.json

输出默认写到**数据区**（``%APPDATA%\\KnowledgeStation\\filing-apply\\``），不污染代码树。
退出码：0 成功；2 前置条件不成立（已中止、**没写**）；3 读回自证对不上。
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import socket
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.core.knowledge import folder_filing_plan as plan_mod  # noqa: E402
from src.core.knowledge import folder_store as fs  # noqa: E402

#: 真库默认位置（Windows 数据区）
DEFAULT_SOURCE = Path(os.path.expandvars(
    r"%APPDATA%\KnowledgeStation\database\knowledge.db"))
#: 备份默认位置（业主点名要的目录）
DEFAULT_BACKUP_DIR = Path(os.path.expandvars(r"%APPDATA%\KnowledgeStation\backups"))
#: 报告默认位置（数据区，不在代码树里）
DEFAULT_OUT_DIR = Path(os.path.expandvars(r"%APPDATA%\KnowledgeStation\filing-apply"))
#: DDL 真源
DEFAULT_SCHEMA = _REPO / "src" / "core" / "storage" / "schema.sql"

#: 本步只碰这三张新表（schema.sql 里的 33~35 号表）
TARGET_TABLES: tuple[str, ...] = ("folder", "folder_member", "doc_filing_state")

#: 顶层预建（业主 2026-09-21 定）：名字 → 手定顺序（写进 folder.sort）。
#: ⚠ 名字清单的**唯一所有者**是 ``folder_store.PREBUILT_TOP_NAMES``。
#: ⚠ **更正（复核 2026-09-21 打回这条说法）**：这里原写"（**接口侧也读它**，免得两处各写一份）"——
#:   **那句是错的**：`PREBUILT_TOP_NAMES` 目前**只有本脚本一个代码消费者**；
#:   `routes_kb_folders.py` 反而明写"**不限制顶层名字**"（它按库里的实际目录走）。
#:   站得住的说法只有：**名字不许在本脚本里再抄一份**（下面那条断言管这件事）。
#: ⚠⚠ 同一次复核还指出：下面那条断言是**自反的**（两边同源 ⇒ 恒真），只能拦"在这一行改字面量"，
#:   拦不住"别处另写一份" ⇒ 已改成与**冻结字面量**比（改常量就得动这一行，逼人显式确认）。
_TOP_SORTS: tuple[int, ...] = (10, 20, 30, 90)
#: 冻结字面量：**故意**手写一遍（这是"改动必须显式"的那道闸，不是冗余）。
FROZEN_TOP_NAMES: tuple[str, ...] = ("标准", "法律法规", "公司制度", "待分类")
assert fs.PREBUILT_TOP_NAMES == FROZEN_TOP_NAMES, (
    "顶层名字变了 —— 真树的形状跟着变；确认无误后同步改 FROZEN_TOP_NAMES 与方案文档")
PREBUILT_TOPS: tuple[tuple[str, int], ...] = tuple(zip(fs.PREBUILT_TOP_NAMES, _TOP_SORTS))
STANDARD_TOP = fs.STANDARD_TOP_NAME
PENDING_TOP = fs.PENDING_TOP_NAME
#: 计划里推导出来的第一层。它挂在「标准」下面就是**重复的一层** ⇒ 跳过（方案 §九业主已定）。
#: ⚠ "跳过哪一段 / 真顶层叫什么"这两件事的**唯一所有者**是 ``folder_filing_plan``
#: （``SKIPPED_PLAN_TOP`` / ``tree_path_of``）；这里只是取它的值，不许另写字面量 ——
#: 接口侧的"建议去向"也走同一条规则（复核实测：两处口径不一致时建议恒为 null）。
PLAN_STD_LEVEL1 = plan_mod.SKIPPED_PLAN_TOP

#: 第 1 步实测的真库数字（2026-09-21，提交 43d1fa5/44a6cfb/7991e8c/2d60bf6）。
#: 只用来在预演时**提示**"和记录不一样"，**不作为闸门**（真库会变，闸门会变成假红）。
RECORDED = {"total_docs": 6417, "filed": 6036, "no_class": 379, "hidden": 2, "folders": 1124}

#: SQLite 自己的表（对账时不算"用户对象"）
_SQLITE_INTERNAL = ("sqlite_",)

#: 清点"既有对象一个都没动"时跳过的表（它们**大且可重建**，清点行数很贵又没信息量：
#: FTS/向量虚拟表及其影子表由引擎维护，行数本就随索引重建而变）
_HEAVY_TABLE_PREFIXES = ("clause_fts", "material_fts", "vec_", "doc_vec", "clause_vec")

#: 归位要读的列（与 /documents/categories 同口径；catalog_hidden 读取时自适应）
_DOC_COLS = ("doc_id", "standard_no", "standard_name", "legal_hierarchy", "doc_type",
             "domain_tags")

#: 解析失败的说明（业主口径：这两篇是"正文条款为零"被踢出目录的）
FAILURE_KIND_ZERO_CLAUSES = "解析失败（正文条款为零）"

BANNER = "=" * 78


class Abort(Exception):
    """前置条件不成立 ⇒ 中止（退出码 2），**绝不带着问题往下写**。"""


# ──────────────────────────────── 小工具 ────────────────────────────────

def _data_dir() -> Path:
    """数据区目录（**不调 get_settings()**：它会 mkdir，预演时不该有副作用）。"""
    override = os.environ.get("KS_DATA_DIR")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "KnowledgeStation"


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    """**只读**打开（``mode=ro``）——SQLite 保证连一个字节都不写，也不建 -wal/-shm。"""
    uri = "file:" + str(db_path).replace("\\", "/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _db_files(db_path: Path) -> dict[str, Any]:
    """库本体 + ``-wal`` + ``-shm`` 的大小与 mtime（WAL 模式下只看 .db 会看不出写入）。"""
    out: dict[str, Any] = {"path": str(db_path)}
    for label, p in (("db", db_path),
                     ("wal", db_path.with_name(db_path.name + "-wal")),
                     ("shm", db_path.with_name(db_path.name + "-shm"))):
        if p.exists():
            st = p.stat()
            out[label] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns,
                          "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(
                              timespec="seconds")}
        else:
            out[label] = {"size": 0, "mtime_ns": 0, "mtime": None}
    out["total_size"] = sum(out[k]["size"] for k in ("db", "wal", "shm"))
    return out


def _engine_status(data_dir: Path) -> dict[str, Any]:
    """引擎会话文件 + "那个端口有没有人听"。只读探测，**不阻塞**。"""
    sess = data_dir / "engine.session.json"
    out: dict[str, Any] = {"session_file": str(sess), "exists": sess.exists(),
                           "listening": False, "port": None, "pid": None, "note": ""}
    if not sess.exists():
        out["note"] = "没有会话文件（引擎没在跑，或从没启动过）"
        return out
    try:
        info = json.loads(sess.read_text(encoding="utf-8"))
    except Exception as e:                                  # 坏文件不该让脚本挂掉
        out["note"] = f"会话文件读不出来：{type(e).__name__}: {e}"
        return out
    port = info.get("port")
    out["port"], out["pid"] = port, info.get("pid")
    if not port:
        out["note"] = "会话文件里没有 port"
        return out
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.5):
            out["listening"] = True
            out["note"] = "端口有人听（引擎在跑）"
    except OSError as e:
        out["note"] = f"端口没人听（{type(e).__name__}）—— 会话文件可能是陈旧的"
    return out


# ─────────────────────────── 只取三张表的 DDL ───────────────────────────

def _strip_sql_comments(raw: str) -> list[str]:
    """去掉 SQL 注释后切分成**语句列表**。

    ⚠ **必须连行内 `--` 一起去掉**（2026-09-21 实测踩到）：schema.sql 里
    ``page_breaks TEXT,   -- 2026-09-01 B3: 页界 …`` 这种**行尾**注释若留着，最后一段
    会被读成一个叫 ``PDF页`` 的"列" ⇒ 对账凭空报"缺列"。

    ⚠ **切分 `;` 必须避开字符串字面量**（同一次实测踩到，更凶）：schema.sql 里有
    ``DEFAULT '...;...'``（FTS 的 ``tokenize`` 参数、触发器体里的 ``';'``）
    ⇒ 无脑按 `;` 切会切出 ``'i'`` / ``'d'`` / ``')'`` 这种碎片，把后面几条
    ``CREATE TABLE`` 整段吃掉，于是脚本报"**找不到这三张表的建表语句**"。
    所以这里按**单引号状态机**切分（SQLite 用 `''` 表示字面量里的单引号）。

    ⚠ **返回 list，不返回 join 起来的字符串**（实测踩到的第三个坑）：返回字符串时
    调用方 ``for stmt in ...`` 迭代的是**单个字符**，`re.match` 一条都匹配不上
    —— 症状与"schema.sql 里没有这三张表"一模一样，极难往这里想。
    """
    out: list[str] = []
    cur: list[str] = []
    in_str = False
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if in_str:
            cur.append(ch)
            if ch == "'":
                if i + 1 < n and raw[i + 1] == "'":      # '' = 字面量里的一个单引号
                    cur.append("'")
                    i += 2
                    continue
                in_str = False
            i += 1
            continue
        if ch == "'":
            in_str = True
            cur.append(ch)
            i += 1
            continue
        if ch == "-" and i + 1 < n and raw[i + 1] == "-":   # 行注释：吃到换行为止
            while i < n and raw[i] != "\n":
                i += 1
            continue
        if ch == ";":
            out.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    out.append("".join(cur).strip())
    return [s for s in out if s]


def target_ddl(schema_path: Path = DEFAULT_SCHEMA) -> list[str]:
    """从 ``schema.sql`` 里**现取**那三张表的建表/建索引语句（不手抄一份）。

    取法：切分 SQL 语句 → 只留 ``CREATE TABLE/INDEX IF NOT EXISTS`` 且**目标就是这三张表**
    的那些（索引按 ``ON <表>`` 判定）。安全一条不省：每条必须真的带 ``IF NOT EXISTS``、
    括号必须配平（防止切分切出半截语句还照跑）。
    """
    out: list[str] = []
    for stmt in _strip_sql_comments(schema_path.read_text(encoding="utf-8")):
        head = re.match(r"CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX)\s+IF\s+NOT\s+EXISTS\s+"
                        r"([A-Za-z_]\w*)", stmt, re.IGNORECASE)
        if head is None:
            continue
        kind, name = head.group(1).upper(), head.group(2)
        if kind == "TABLE":
            keep = name in TARGET_TABLES
        else:
            on = re.search(r"\bON\s+([A-Za-z_]\w*)", stmt, re.IGNORECASE)
            keep = on is not None and on.group(1) in TARGET_TABLES
        if not keep:
            continue
        if "IF NOT EXISTS" not in stmt.upper():
            raise Abort(f"schema.sql 里这条没有 IF NOT EXISTS，拒绝执行：{stmt[:120]}")
        # 括号必须配平（防"切分切出半截语句还照跑"；索引的 WHERE 子句在括号外，
        # 所以**不能**用"以 ) 收尾"当判据 —— 部分唯一索引就不以 ) 收尾）
        if stmt.count("(") != stmt.count(")"):
            raise Abort(f"schema.sql 里这条括号不配平（像是被切断了），拒绝执行：{stmt[:120]}")
        out.append(stmt)
    missing = [t for t in TARGET_TABLES
               if not any(re.match(rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{t}\b", s,
                                   re.IGNORECASE) for s in out)]
    if missing:
        raise Abort(f"schema.sql 里找不到这几张表的建表语句：{missing}")
    return out


# ─────────────────────── schema 指纹（证明没动既有东西） ───────────────────────

def _schema_fingerprint(conn: sqlite3.Connection) -> dict[str, str]:
    """库里**全部** sqlite_master 对象的 ``type:name → sql``（列改动也会体现在 sql 上）。"""
    out: dict[str, str] = {}
    for r in conn.execute("SELECT type, name, sql FROM sqlite_master"
                          " WHERE sql IS NOT NULL"):
        if str(r["name"]).startswith("sqlite_"):
            continue
        out[f"{r['type']}:{r['name']}"] = r["sql"]
    return out


def _assert_only_additions(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """既有对象一个都不许改、不许删；新增的必须是那三张表自己的东西。返回新增清单。

    ⚠ **这条只管"本次建表前后"**（三条 DDL 全是 ``IF NOT EXISTS`` ⇒ 它只可能看见新增）。
    对"库**事先**就被人动过"（删了索引 / 少了列）**零侦测力** —— 那由
    ``schema_drift`` 拿 ``schema.sql`` 对账兜住（2026-09-21 复核实测的"没有牙的保护"）。
    """
    changed = [k for k, v in before.items() if after.get(k) != v]
    if changed:
        raise Abort(f"既有表/列被改动了（本步绝不许）：{changed[:10]}")
    added = [k for k in after if k not in before]
    for k in added:
        if not any(re.search(rf"\b{t}\b", after[k], re.IGNORECASE) for t in TARGET_TABLES):
            raise Abort(f"新建的对象不属于那三张表：{k} → {after[k][:120]}")
    return added


# ═══════════ 对账：schema.sql 声明的既有对象 ⇄ 库里的实际对象 ═══════════
#
# ⚠ **为什么必须有这一块**（2026-09-21 独立复核在 `verify-freeze-kb-filed` 上实测）：
# 原来那句"既有表/列指纹一个都没变"**只比"本次建表前后"**，而三条建表语句全是
# `IF NOT EXISTS` ⇒ 那个分支**永远不会响**。实测：先删掉一个既有索引
# （`idx_alias_lookup`）或给 `doc_meta` 加一列，再 `--apply` ⇒ **exit 0 照写**、
# 还打印"一个都没变"。
#
# 现在改成**拿 schema.sql 里声明的对象当基准，与库里的实际对象对账**：
#   · 库里**少了**声明的表 / 索引 / 列  ⇒ 报（这是"库被删过东西"）
#   · 库里多出**声明之外的列**          ⇒ **只登记、不中止**（生产的 `ensure_additive_columns`
#     合法地给既有表加列，拿它当中止条件会把正常库判死）
# 对不上 ⇒ 由调用方**中止不写**。

_VIRTUAL_TABLE = re.compile(r"\)\s*USING\s+\w+", re.IGNORECASE)


def _split_top_level(body: str) -> list[str]:
    """按**顶层**逗号切分一段 SQL（括号里的逗号不算）。"""
    parts: list[str] = []
    depth = 0
    cur = ""
    in_str: str | None = None
    for ch in body:
        if in_str:
            cur += ch
            if ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"'):
            in_str = ch
            cur += ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def _columns_from_create(stmt: str) -> list[str]:
    """``CREATE TABLE`` 语句里声明的列名（表级约束与虚拟表列自动跳过）。

    跳过：以 ``CONSTRAINT`` / ``PRIMARY`` / ``UNIQUE`` / ``CHECK`` / ``FOREIGN``
    开头的表级约束；``sqlite_`` 内部列；FTS 的 ``*`` 列；虚拟表（带 ``USING``）
    —— 它的列由扩展定义，拿 DDL 对账会假红。
    """
    if _VIRTUAL_TABLE.search(stmt):
        return []
    i = stmt.find("(")
    j = stmt.rfind(")")
    if i < 0 or j <= i:
        return []
    cols: list[str] = []
    for part in _split_top_level(stmt[i + 1:j]):
        head = part.strip()
        if not head:
            continue
        m = re.match(r'^(?:"([^"]+)"|`([^`]+)`|\[([^\]]+)\]|([A-Za-z_]\w*))', head)
        if not m:
            continue
        name = next((g for g in m.groups() if g), "")
        if not name or name.startswith(_SQLITE_INTERNAL):
            continue
        if name.upper() in ("CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK", "FOREIGN"):
            continue
        cols.append(name)
    return cols


def declared_objects(schema_path: Path = DEFAULT_SCHEMA) -> dict:
    """``schema.sql`` 声明的对象：``{"tables": {名: [列…]}, "indexes": {名: 表}}``。"""
    tables: dict[str, list[str]] = {}
    indexes: dict[str, str] = {}
    for stmt in _strip_sql_comments(schema_path.read_text(encoding="utf-8")):
        if not stmt:
            continue
        m = re.match(r"CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX)\s+IF\s+NOT\s+EXISTS\s+"
                     r"([A-Za-z_]\w*)", stmt, re.IGNORECASE)
        if not m:
            continue
        kind, name = m.group(1).upper(), m.group(2)
        if kind == "TABLE":
            tables[name] = _columns_from_create(stmt)
        else:
            on = re.search(r"\bON\s+([A-Za-z_]\w*)", stmt, re.IGNORECASE)
            indexes[name] = on.group(1) if on else ""
    return {"tables": tables, "indexes": indexes}


def _live_objects(conn: sqlite3.Connection) -> dict:
    """库里的用户对象：``{"tables": {名: [列…]}, "indexes": {名: 表}}``（不含 ``sqlite_*``）。"""
    tables: dict[str, list[str]] = {}
    for r in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
        name = str(r["name"])
        if name.startswith(_SQLITE_INTERNAL) or name in _HEAVY_TABLE_PREFIXES \
                or name.startswith(_HEAVY_TABLE_PREFIXES):
            continue
        cols = [str(c[1]) for c in conn.execute(f'PRAGMA table_info("{name}")')]
        tables[name] = cols
    indexes: dict[str, str] = {}
    for r in conn.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"):
        name = str(r["name"])
        if name.startswith(_SQLITE_INTERNAL):
            continue
        indexes[name] = str(r["tbl_name"])
    return {"tables": tables, "indexes": indexes}


def schema_drift(db_path: Path, schema_path: Path = DEFAULT_SCHEMA) -> dict:
    """拿 ``schema.sql`` 声明的对象与库里的实际对象**对账**（只读）。

    * ``missing_tables`` —— 声明了、库里没有的表。
    * ``missing_columns`` —— 声明了、库里那一列没有（形如 ``表.列``）。
    * ``missing_indexes`` —— 声明了、库里没有的索引（表还在才算 —— 表自己都没了就
      已经在 ``missing_tables`` 里报了，不必报两遍）。
    * ``extra_columns`` —— 库里**有**、``schema.sql`` 没声明的列。**合法**（生产的
      ``ensure_additive_columns`` 就这么给既有表加列）⇒ **只登记、不当中止理由**。

    ⚠ **本步自己那三张表（``TARGET_TABLES``）不参与缺列检查**（2026-09-21 实测踩到）：
    它们**本来就可能还不存在**（老库靠本脚本建），而"声明了却没有"对它们正是
    **要动手做的事**，不是"库被人动过"的证据 ⇒ 拿它当中止理由会让脚本永远开不了工。
    它们的建成与否由 ``_target_tables_present`` / ``IF NOT EXISTS`` 管。

    ⚠ **缺列只在"库里那张表有列信息"时才判**：``PRAGMA table_info`` 对虚拟表返回空，
    拿空当"列全缺"就是纯假红。
    """
    declared = declared_objects(schema_path)
    conn = _open_readonly(db_path)
    try:
        live = _live_objects(conn)
    finally:
        conn.close()
    missing_tables = [t for t in declared["tables"]
                      if t not in live["tables"] and t not in TARGET_TABLES]
    missing_columns = [f"{t}.{c}" for t, cols in declared["tables"].items()
                       if t not in TARGET_TABLES and t in live["tables"]
                       and live["tables"][t]
                       for c in cols if c not in live["tables"][t]]
    missing_indexes = [ix for ix, tbl in declared["indexes"].items()
                       if ix not in live["indexes"] and tbl in live["tables"]]
    extra_columns = [f"{t}.{c}" for t, cols in live["tables"].items()
                     if t in declared["tables"]
                     for c in cols if c not in declared["tables"][t]]
    ok = not (missing_tables or missing_columns or missing_indexes)
    return {"ok": ok, "missing_tables": missing_tables,
            "missing_columns": missing_columns, "missing_indexes": missing_indexes,
            "extra_columns": extra_columns,
            "declared_counts": {"tables": len(declared["tables"]),
                                "indexes": len(declared["indexes"])},
            "live_counts": {"tables": len(live["tables"]), "indexes": len(live["indexes"])}}


def _entity_tables(conn: sqlite3.Connection) -> list[str]:
    """实体表清单（清点"库有没有被动过"用；虚拟表/影子表/内部表排除）。"""
    out: list[str] = []
    for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        name = str(r["name"])
        if name.startswith(_SQLITE_INTERNAL):
            continue
        if name.startswith(_HEAVY_TABLE_PREFIXES) or name in _HEAVY_TABLE_PREFIXES:
            continue
        out.append(name)
    return sorted(out)


def db_state(db_path: Path) -> dict:
    """"库有没有被动过"的一个总指纹（给"中止不写"当证据用，只读）。

    四样：``.db`` 大小 + ``-wal`` 大小 + **每张实体表的行数** + **schema 对象名集合**。
    任何一项变了就说明有人写过（哪怕只是一行）。
    """
    st = db_path.stat()
    wal = db_path.with_name(db_path.name + "-wal")
    conn = _open_readonly(db_path)
    try:
        rows = {t: int(conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
                for t in _entity_tables(conn)}
        objects = sorted(f"{r['type']}:{r['name']}" for r in conn.execute(
            "SELECT type, name FROM sqlite_master WHERE sql IS NOT NULL"
            " AND name NOT LIKE 'sqlite_%'"))
    finally:
        conn.close()
    return {"db_size": st.st_size, "db_mtime_ns": st.st_mtime_ns,
            "wal_size": wal.stat().st_size if wal.exists() else 0,
            "rows": rows, "objects": objects}


# ─────────────────────────── 建三张新表（只许新增） ───────────────────────────

def ensure_target_tables(db_path: Path, schema_path: Path = DEFAULT_SCHEMA) -> dict:
    """按 schema.sql 的 DDL 建那三张表（``IF NOT EXISTS``），并证明**没动任何既有东西**。

    两道检查（**先对账、再建表**）：
    ① ``schema_drift`` —— 拿 ``schema.sql`` 声明的对象与库里的实际对象对账（"库**事先**
       就被人删过东西"只有它能侦测到）；
    ② ``_assert_only_additions`` —— 本次建表前后既有对象一个都没改（防"建表语句自己写错"）。
    """
    drift = schema_drift(db_path, schema_path)
    if not drift["ok"]:
        raise Abort("库与 schema.sql 对不上（缺表/缺列/缺索引），拒绝建表更拒绝写数据："
                    f"tables={drift['missing_tables'][:5]} cols={drift['missing_columns'][:5]}"
                    f" indexes={drift['missing_indexes'][:5]}")
    stmts = target_ddl(schema_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=60000")
        before = _schema_fingerprint(conn)
        have_before = _target_tables_present(conn)
        for s in stmts:
            conn.execute(s)
        conn.commit()
        added = _assert_only_additions(before, _schema_fingerprint(conn))
        return {"statements": len(stmts), "existed_before": have_before,
                "created_objects": added, "schema_drift": drift,
                "targets_present": _target_tables_present(conn)}
    except sqlite3.Error as e:
        conn.rollback()
        raise Abort(f"建表失败（既有表/列没动）：{type(e).__name__}: {e}") from e
    finally:
        conn.close()


# ──────────────────────────────── 读真库 ────────────────────────────────

def _load_docs(conn: sqlite3.Connection) -> list[dict]:
    """读全部文档（``catalog_hidden`` 列在才读，与 ``/documents/categories`` 同口径）。"""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(doc_meta)").fetchall()]
    sel = [c for c in _DOC_COLS if c in cols]
    if "catalog_hidden" in cols:
        sel.append("catalog_hidden")
    rows = conn.execute(
        f"SELECT {', '.join(sel)} FROM doc_meta ORDER BY standard_no").fetchall()
    return [dict(zip(sel, tuple(r))) for r in rows]


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _target_tables_present(conn: sqlite3.Connection) -> list[str]:
    have = _table_names(conn)
    return [t for t in TARGET_TABLES if t in have]


def _existing_row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """三张新表里**已经有多少行**（复跑时先看清"是不是干净的白纸"）。表不存在就不列。"""
    have = _table_names(conn)
    return {t: int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
            for t in TARGET_TABLES if t in have}


def _existing_folders(conn: sqlite3.Connection) -> tuple[dict[tuple[str | None, str], str],
                                                         list[str]]:
    """``(父 id, 名字) → 目录 id`` 的全量索引（判断"复用"用），外加根层名字清单。"""
    if "folder" not in _table_names(conn):
        return {}, []
    idx: dict[tuple[str | None, str], str] = {}
    roots: list[str] = []
    for r in conn.execute("SELECT folder_id, parent_id, name FROM folder"):
        idx[(r["parent_id"], r["name"])] = r["folder_id"]
        if r["parent_id"] is None:
            roots.append(r["name"])
    return idx, roots


def _clause_counts(conn: sqlite3.Connection, doc_ids: list[str]) -> dict[str, dict] | None:
    """"这篇到底有几条条款、几条是正文（content_type='normal'）" —— 写 failure_kind 的证据。

    表/列不在（老库、或只跑过 init_schema）⇒ 返回 None（= **核对不了**，不许假装数过）。
    """
    if not doc_ids:
        return {}
    cols = [r[1] for r in conn.execute("PRAGMA table_info(clause_revision)").fetchall()]
    if not cols:
        return None
    has_type = "content_type" in cols
    expr = "SUM(CASE WHEN content_type='normal' THEN 1 ELSE 0 END)" if has_type else "NULL"
    out: dict[str, dict] = {}
    for i in range(0, len(doc_ids), 500):
        chunk = doc_ids[i:i + 500]
        ph = ",".join("?" * len(chunk))
        for r in conn.execute(
                f"SELECT doc_id, COUNT(*) AS total, {expr} AS normal"
                f" FROM clause_revision WHERE doc_id IN ({ph}) GROUP BY doc_id", chunk):
            out[r["doc_id"]] = {"total": int(r["total"] or 0),
                                "normal": (None if r["normal"] is None else int(r["normal"]))}
    for d in doc_ids:
        out.setdefault(d, {"total": 0, "normal": (0 if has_type else None)})
    return out


# ─────────────────────── 计划 → 要落库的"节点/归属/状态" ───────────────────────

def build_payload(plan: dict, existing: dict[tuple[str | None, str], str],
                  docs_by_id: dict[str, dict], clause_counts: dict[str, dict] | None,
                  placed_by: str) -> dict:
    """把归位计划翻译成"四个顶层 + 标准树（跳过重复层）+ 待分类"的节点/归属/状态。

    ⚠ 为什么**不直接**用 ``folder_filing_plan.apply_plan``：那一步建的是计划原样的树
    （顶层只有「国家标准·行业标准·团体标准」、没有「待分类」、没有隐藏文档）。本步要的是
    **映射结果**再按业主的三条定案重排一次，所以复用 ``plan_filing``（映射）与
    ``folder_store.build_folder_tree``（落库），**不另写一份判断**。
    """
    nodes: list[dict] = []
    key_map: dict[str, str] = {}          # 计划 key → 本步 key（跳层/复用都体现在这）
    resolved: dict[str, str | None] = {}  # 本步 key → 库里已存在的 id（None = 本次新建）
    reused: dict[str, str] = {}
    top_key: dict[str, str] = {}

    def _add(key: str, name: str, parent_key: str | None, sort: int, depth: int) -> None:
        """登记一个目录节点；父**在库里真的存在**时才查"同名已存在"（新建的父不可能有子）。"""
        if parent_key is None:
            pid: str | None = None
            lookupable = True                      # 根层：可以查重
        else:
            if parent_key not in resolved:
                raise Abort(f"目录顺序不是父先子后：{key} 的上级 {parent_key} 还没处理")
            pid = resolved[parent_key]
            lookupable = pid is not None            # 父是本次新建的 ⇒ 不可能有同名子目录
        found = existing.get((pid, name)) if lookupable else None
        nodes.append({"key": key, "name": name, "parent_key": parent_key, "sort": sort,
                      "depth": depth})
        resolved[key] = found
        if found is not None:
            reused[key] = found

    # ① 四个顶层（手定顺序）
    for name, sort in PREBUILT_TOPS:
        key = f"top:{name}"
        top_key[name] = key
        _add(key, name, None, sort, 1)

    # ② 计划里的目录
    skipped_level1: list[str] = []
    for n in plan["nodes"]:
        depth = int(n["depth"])
        if depth == 1:
            # ⚠ 判定"这一段是不是被真树跳过的重复层"**走唯一所有者那条规则**
            #   （``plan_mod.tree_path_of``：分类口径 L1 → 真树顶层名），不是拿字面量比名字。
            mapped_top = plan_mod.tree_path_of(n["path"])[0]
            if mapped_top != n["name"]:
                # 这一段被跳过/改名了 ⇒ 它的下级**直接**挂到映射后的真顶层下
                if mapped_top not in top_key:
                    raise Abort(f"被跳过的层「{n['name']}」映射到「{mapped_top}」，"
                                f"而它不是预建顶层之一 {list(top_key)}")
                key_map[n["key"]] = top_key[mapped_top]
                skipped_level1.append(n["name"])
                continue
            if n["name"] in top_key:
                key_map[n["key"]] = top_key[n["name"]]      # 与预建顶层同名 ⇒ 复用
                continue
            key = f"plan:{n['key']}"
            _add(key, n["name"], None, 0, 1)
            key_map[n["key"]] = key
            continue
        parent_key = key_map[str(n["parent_key"])] if str(n["parent_key"]) in key_map \
            else None
        if parent_key is None:
            raise Abort(f"计划的目录顺序不是父先子后：{n['key']} 的上级 {n['parent_key']}")
        key = f"plan:{n['key']}"
        _add(key, n["name"], parent_key, 0, depth)
        key_map[n["key"]] = key

    # ③ 归属与状态（已归位的 + 无分类进「待分类」）
    memberships: list[dict] = []
    states: list[dict] = []
    for a in plan["assignments"]:
        fkey = key_map[a["key"]]
        memberships.append({"folder_key": fkey, "item_kind": "file", "item_id": a["doc_id"]})
        states.append({"doc_id": a["doc_id"], "stage": "filed", "placed_folder_key": fkey,
                       "placed_by": placed_by})
    pending_key = top_key[PENDING_TOP]
    for item in plan["no_class"]:
        memberships.append({"folder_key": pending_key, "item_kind": "file",
                            "item_id": item["doc_id"]})
        states.append({"doc_id": item["doc_id"], "stage": "queued", "placed_by": placed_by})

    # ④ 解析失败被隐藏的那几篇（方案 §十：它们**不该静默消失**）
    failed: list[dict] = []
    for doc_id in plan["hidden_docs"]:
        counts = None if clause_counts is None else clause_counts.get(doc_id)
        if counts is None:
            kind = FAILURE_KIND_ZERO_CLAUSES + "（条款数这次没核对上）"
        elif counts.get("normal") == 0:
            kind = FAILURE_KIND_ZERO_CLAUSES
        else:
            kind = (f"解析失败（判据待核：库里有 {counts.get('normal')} 条正文条款、"
                    f"共 {counts.get('total')} 条，与“正文条款为零”不符）")
        d = docs_by_id.get(doc_id, {})
        failed.append({"doc_id": doc_id, "standard_no": d.get("standard_no"),
                       "standard_name": d.get("standard_name"),
                       "clause_total": (None if counts is None else counts.get("total")),
                       "clause_normal": (None if counts is None else counts.get("normal")),
                       "failure_kind": kind})
        memberships.append({"folder_key": pending_key, "item_kind": "file", "item_id": doc_id})
        states.append({"doc_id": doc_id, "stage": "failed", "placed_by": placed_by})

    by_depth: dict[int, int] = {}
    for n in nodes:
        by_depth[n["depth"]] = by_depth.get(n["depth"], 0) + 1
    return {"nodes": nodes, "memberships": memberships, "states": states,
            "key_map": key_map, "reused": reused, "failed": failed,
            "skipped_level1": skipped_level1, "pending_key": pending_key,
            "by_depth": by_depth, "pending_docs": len(plan["no_class"]) + len(failed)}


def align_top_sorts(db_path: Path) -> int:
    """把四个顶层目录的 ``sort`` 对齐到业主手定的值（**只改这四行的 sort 列**）。

    为什么要单独一步：复用已存在的顶层目录时**不动**它的 sort，若那四行是早先以 sort=0
    建出来的，顺序就会变成拼音序（「待分类」会跑到第二位）—— 那是业主明确不要的结果。
    只碰我们自己的新表、只碰这四行，且只碰 sort 一列。
    """
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction(db_path) as conn:
        n = 0
        for name, sort in PREBUILT_TOPS:
            cur = conn.execute(
                "UPDATE folder SET sort=? WHERE parent_id IS NULL AND name=?",
                (sort, name))
            n += cur.rowcount
        return n


# ──────────────────────────────── 备份 ────────────────────────────────

def backup_db(src: Path, backup_dir: Path, stamp: str) -> dict:
    """SQLite backup 接口整份备份 + **读回核对**。任一步不对 ⇒ Abort（不许带着没备份往下走）。"""
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise Abort(f"备份目录不能用（**没有写库**）：{backup_dir}｜{type(e).__name__}: {e}") \
            from e
    if not backup_dir.is_dir():
        raise Abort(f"备份路径不是目录（**没有写库**）：{backup_dir}")
    dest = backup_dir / f"knowledge-pre-folders-{stamp}.db"
    n = 2
    while dest.exists():                     # 同一秒跑两次也不覆盖上一次的备份
        dest = backup_dir / f"knowledge-pre-folders-{stamp}-{n}.db"
        n += 1
    t0 = time.time()
    try:
        src_conn = _open_readonly(src)
        try:
            dst_conn = sqlite3.connect(str(dest))
            try:
                src_conn.backup(dst_conn)     # 源是 mode=ro ⇒ 只读地整份复制
            finally:
                dst_conn.close()
        finally:
            src_conn.close()
    except Exception as e:
        raise Abort(f"备份失败（**没有写库**）：{type(e).__name__}: {e}") from e
    if not dest.exists() or dest.stat().st_size <= 0:
        raise Abort(f"备份没落盘或大小为零（**没有写库**）：{dest}")
    try:
        a, b = _open_readonly(src), _open_readonly(dest)
        try:
            checks = {
                "page_count": (a.execute("PRAGMA page_count").fetchone()[0],
                               b.execute("PRAGMA page_count").fetchone()[0]),
                "doc_count": (a.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0],
                              b.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]),
                "schema_objects": (
                    a.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0],
                    b.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]),
            }
        finally:
            a.close()
            b.close()
    except Exception as e:
        raise Abort(f"备份读回核对失败（**没有写库**）：{type(e).__name__}: {e}") from e
    mismatch = {k: v for k, v in checks.items() if v[0] != v[1]}
    if mismatch:
        raise Abort(f"备份与真库对不上（**没有写库**）：{mismatch}")
    return {"path": str(dest), "size": dest.stat().st_size,
            "seconds": round(time.time() - t0, 2),
            "checks": {k: {"source": v[0], "backup": v[1]} for k, v in checks.items()}}


# ──────────────────────────────── 读回自证 ────────────────────────────────

def _depth_counts(conn: sqlite3.Connection) -> tuple[dict[int, int], int]:
    """各级目录数（按 ``folder.parent_id`` 递归；够不到的另外报出来）。"""
    rows = conn.execute(
        "WITH RECURSIVE d(folder_id, depth) AS ("
        "  SELECT folder_id, 1 FROM folder WHERE parent_id IS NULL"
        "  UNION ALL"
        "  SELECT f.folder_id, d.depth + 1 FROM folder f JOIN d ON f.parent_id = d.folder_id"
        "  WHERE d.depth < 20"
        ") SELECT depth, COUNT(*) AS n FROM d GROUP BY depth ORDER BY depth").fetchall()
    by_depth = {int(r["depth"]): int(r["n"]) for r in rows}
    total = int(conn.execute("SELECT COUNT(*) FROM folder").fetchone()[0])
    return by_depth, total - sum(by_depth.values())


def read_back(db_path: Path, *, plan: dict, payload: dict, existing_total: int,
              sample: int, seed: int) -> dict:
    """**重新打开真库**读回自证（不看写函数的返回值自说自话）。

    预期数字全部由**计划**（``payload``）+ **写之前那次只读读数**（``existing_total``）推出，
    不引用 ``build_folder_tree`` 的返回值。
    """
    from src.core.knowledge import folder_store as fs
    from src.core.storage.sqlite_db import close_thread_connection, get_db_connection

    close_thread_connection()               # 丢掉写路径上的缓存连接 ⇒ 真的是从库里重读
    conn = get_db_connection(db_path)
    out: dict[str, Any] = {}

    by_depth, unreachable = _depth_counts(conn)
    out["folders_by_depth"] = by_depth
    out["folders_total"] = int(conn.execute("SELECT COUNT(*) FROM folder").fetchone()[0])
    out["folders_unreachable"] = unreachable
    out["member_rows"] = {r["item_kind"]: int(r["n"]) for r in conn.execute(
        "SELECT item_kind, COUNT(*) AS n FROM folder_member GROUP BY item_kind")}
    out["member_rows_total"] = int(
        conn.execute("SELECT COUNT(*) FROM folder_member").fetchone()[0])
    out["state_rows_by_stage"] = {r["stage"]: int(r["n"]) for r in conn.execute(
        "SELECT stage, COUNT(*) AS n FROM doc_filing_state GROUP BY stage")}
    out["state_rows_total"] = int(
        conn.execute("SELECT COUNT(*) FROM doc_filing_state").fetchone()[0])

    tops = [dict(r) for r in conn.execute(
        "SELECT folder_id, name, sort FROM folder WHERE parent_id IS NULL"
        " ORDER BY sort, name")]
    out["top_level"] = [{"name": t["name"], "sort": t["sort"]} for t in tops]
    top_names = [t["name"] for t in tops]
    out["top_level_duplicates"] = [r["name"] for r in conn.execute(
        "SELECT name FROM folder WHERE parent_id IS NULL GROUP BY name"
        " HAVING COUNT(*) > 1")]

    std = next((t for t in tops if t["name"] == STANDARD_TOP), None)
    out["standard_children"] = ([r["name"] for r in conn.execute(
        "SELECT f.name FROM folder f JOIN folder_member m"
        "  ON m.item_id=f.folder_id AND m.item_kind='folder'"
        " WHERE m.folder_id=? ORDER BY f.name", (std["folder_id"],))] if std else [])
    out["standard_children_count"] = len(out["standard_children"])
    out["standard_has_redundant_level"] = PLAN_STD_LEVEL1 in out["standard_children"]

    pend = next((t for t in tops if t["name"] == PENDING_TOP), None)
    out["pending_docs"] = 0
    out["pending_by_stage"] = {}
    out["pending_sample"] = []
    if pend:
        rows = conn.execute(
            "SELECT d.standard_no, COALESCE(s.stage,'queued') AS stage,"
            " s.failure_kind AS failure_kind FROM folder_member m"
            " JOIN doc_meta d ON d.doc_id=m.item_id"
            " LEFT JOIN doc_filing_state s ON s.doc_id=d.doc_id"
            " WHERE m.folder_id=? AND m.item_kind='file' ORDER BY d.standard_no",
            (pend["folder_id"],)).fetchall()
        out["pending_docs"] = len(rows)
        for r in rows:
            out["pending_by_stage"][r["stage"]] = \
                out["pending_by_stage"].get(r["stage"], 0) + 1
        out["pending_sample"] = [dict(r) for r in rows[:10]]
        # 「待分类」**列表接口**里能看到几篇：它按 catalog_hidden=0 过滤，所以被隐藏的那几篇
        # 只在这一级目录里看得到、不在列表里（方案 §十 的"回来的路"要跟状态一起修）
        out["pending_list_visible"] = int(
            fs.list_pending_filing(offset=0, limit=1, db_path=db_path)["total"])

    # 随机抽 N 个目录：完整路径 → 里面的文件名（人工抽查用；读函数复用 list_folder）
    all_folders = [dict(r) for r in conn.execute(
        "SELECT folder_id, name FROM folder ORDER BY folder_id")]
    rng = random.Random(seed)
    picked = rng.sample(all_folders, min(sample, len(all_folders))) if all_folders else []
    spot: list[dict] = []
    for f in picked:
        info = fs.list_folder(f["folder_id"], file_limit=5, db_path=db_path)
        spot.append({
            "path": " › ".join(x["name"] for x in info["breadcrumb"]) or f["name"],
            "direct_subfolders": len(info["subfolders"]),
            "files_total": info["files_total"],
            "files": [f"{x.get('standard_no') or ''} {x.get('standard_name') or ''}".strip()
                      for x in info["files"]],
        })
    out["spot_check"] = spot

    # ── 预期 vs 实际（预期只看计划 + 写前读数）──
    n_file_members = len(plan["assignments"]) + payload["pending_docs"]
    n_folder_edges = sum(1 for n in payload["nodes"] if n["parent_key"] is not None)
    expect = {
        # 目标树全建出来 = 计划里的节点数 + 库里**不属于**这棵树的老目录（正常应为 0）
        "folders_total": len(payload["nodes"]) + (existing_total - len(payload["reused"])),
        "member_rows_total": n_file_members + n_folder_edges,
        "file_members": n_file_members,
        "folder_edges": n_folder_edges,
        "state_rows_total": n_file_members,
        "stage_filed": len(plan["assignments"]),
        "stage_queued": len(plan["no_class"]),
        "stage_failed": len(plan["hidden_docs"]),
        "pending_docs": payload["pending_docs"],
        "standard_children_count": sum(1 for n in payload["nodes"]
                                       if n["parent_key"] == f"top:{STANDARD_TOP}"),
        "top_level_names": [n for n, _ in PREBUILT_TOPS],
        "folders_unreachable": 0,
    }
    got = {
        "folders_total": out["folders_total"],
        "member_rows_total": out["member_rows_total"],
        "file_members": out["member_rows"].get("file", 0),
        "folder_edges": out["member_rows"].get("folder", 0),
        "state_rows_total": out["state_rows_total"],
        "stage_filed": out["state_rows_by_stage"].get("filed", 0),
        "stage_queued": out["state_rows_by_stage"].get("queued", 0),
        "stage_failed": out["state_rows_by_stage"].get("failed", 0),
        "pending_docs": out["pending_docs"],
        "standard_children_count": out["standard_children_count"],
        "top_level_names": top_names,
        "folders_unreachable": unreachable,
    }
    out["expected"] = expect
    out["mismatch"] = {k: {"expected": expect[k], "got": got[k]}
                       for k in expect if got[k] != expect[k]}
    # 层级分布只在"库里的目录全都属于这棵树"时才逐级比（否则混进别的目录就是假红）
    out["depth_matches_plan"] = (existing_total == len(payload["reused"])
                                 and by_depth == payload["by_depth"])
    return out


# ──────────────────────────────── 打印 ────────────────────────────────

def _print_rollback(db_path: Path, backup_path: str | None) -> None:
    """回退办法（确切命令；本次只新增三张新表的行，没动任何既有表/列）。"""
    py = str(_REPO / ".venv" / "Scripts" / "python.exe")
    print(f"\n{BANNER}\n回退办法（本次只**新增**下面三张表的行，没改任何既有表/列）\n{BANNER}")
    print("① 清空这三张表（推荐：库结构留着，第 2 步还要用）：")
    print(f'   "{py}" -c "import sqlite3;c=sqlite3.connect(r\'{db_path}\');'
          "c.executescript('DELETE FROM folder_member; DELETE FROM folder;"
          " DELETE FROM doc_filing_state;');c.commit();c.close()\"")
    print("② 连表一起删（第 2 步要重建）：")
    print(f'   "{py}" -c "import sqlite3;c=sqlite3.connect(r\'{db_path}\');'
          "c.executescript('DROP TABLE IF EXISTS folder_member;"
          " DROP TABLE IF EXISTS folder; DROP TABLE IF EXISTS doc_filing_state;');"
          'c.commit();c.close()"')
    print("③ 用备份整份还原（先停掉引擎，再把 knowledge.db-wal / knowledge.db-shm 删掉）：")
    print(f'   copy /Y "{backup_path or "<本次备份路径>"}" "{db_path}"')


def _db_state_diff(before: dict, after: dict) -> dict:
    """两次 ``db_state`` 的差异（只报变化项；给"中止不写"当证据）。"""
    changed: dict[str, Any] = {}
    for k in ("db_size", "wal_size"):
        if before[k] != after[k]:
            changed[k] = {"before": before[k], "after": after[k]}
    rows = {t: {"before": before["rows"].get(t), "after": after["rows"].get(t)}
            for t in set(before["rows"]) | set(after["rows"])
            if before["rows"].get(t) != after["rows"].get(t)}
    if rows:
        changed["rows"] = rows
    gone = [o for o in before["objects"] if o not in set(after["objects"])]
    new = [o for o in after["objects"] if o not in set(before["objects"])]
    if gone:
        changed["objects_removed"] = gone
    if new:
        changed["objects_added"] = new
    return changed


def _print_no_write_proof(src: Path, before: dict, after: dict) -> None:
    """把"真的一个字节都没写"打印成**可核对的三个数**。"""
    diff = _db_state_diff(before, after)
    print(f"{BANNER}\n零写入证据（同一个库，中止/预演前后各清点一次）\n{BANNER}")
    print(f"- .db 大小 {before['db_size']:,} → {after['db_size']:,}"
          f"（{after['db_size'] - before['db_size']:+,} 字节）")
    print(f"- -wal 大小 {before['wal_size']:,} → {after['wal_size']:,}")
    print(f"- 既有表行数：清点了 {len(before['rows'])} 张；变化的 "
          f"{len(diff.get('rows', {}))} 张")
    print(f"- schema 对象：{len(before['objects'])} 个；新增 "
          f"{len(diff.get('objects_added', []))}、消失 "
          f"{len(diff.get('objects_removed', []))}")
    if diff:
        print(f"  ⚠ **竟然变了**：{diff}")
    else:
        print("  ✓ 三样全同 ⇒ 这次运行**连一行都没写**")
    print(BANNER)


def _print_plan_summary(plan: dict, payload: dict, existing: dict, tables: dict,
                        engine: dict, apply: bool, backup_dir: Path,
                        backup_path: str | None, rows_before: dict | None = None) -> None:
    s = plan_mod.summarize_plan(plan)
    n_nodes = len(payload["nodes"])
    n_reuse = len(payload["reused"])
    print(f"\n计划（只读算出）：库里 {s['total_docs']} 篇；本次归位 {s['planned_docs']} 篇；"
          f"无分类 {s['no_class_total']} 篇；隐藏(catalog_hidden=1) {s['hidden_docs']} 篇；"
          f"异常 {s['anomaly_total']} 条")
    if s["anomaly_total"]:
        print(f"  ⚠ 异常明细：{s['anomalies_by_kind']} —— 这些**不会**被塞进任何目录"
              "（也不进「待分类」）")
    diff = {k: {"现在": s[k2], "第1步记录": v} for k, (k2, v) in {
        "total_docs": ("total_docs", RECORDED["total_docs"]),
        "filed": ("planned_docs", RECORDED["filed"]),
        "no_class": ("no_class_total", RECORDED["no_class"]),
        "hidden": ("hidden_docs", RECORDED["hidden"]),
        "folders": ("folders_total", RECORDED["folders"]),
    }.items() if s[k2] != v}
    if diff:
        print(f"  ⚠ 与第 1 步实测（2026-09-21）的记录不同：{diff}"
              "（真库会变；这是提示，不是闸门）")

    print("\n将要做什么：" + ("" if apply else "（预演，**一个字节都不写**）"))
    print(f"- 建表：{', '.join(TARGET_TABLES)}"
          f"（已经存在：{tables['present'] or '无'}；本次发出 {tables['statements']} 条 DDL）。"
          "既有表/列一个都不动")
    if rows_before:
        n_rows = sum(rows_before.values())
        print(f"- 这三张表里**现在已有 {n_rows} 行**：{rows_before}"
              + ("（干净的白纸，第一次落库）" if n_rows == 0 else
                 "  ⚠ 不是白纸：会按名字复用目录、覆盖状态，并**再备份一份**"))
    else:
        print("- 这三张表**还不存在**（全新库）⇒ 本次按 schema.sql 把它们建出来（含索引）")
    tops = " · ".join(f"{n}(sort={v})" for n, v in PREBUILT_TOPS)
    print(f"- 顶层目录：{tops}；按名字复用已存在的 "
          f"{len([n for n, _ in PREBUILT_TOPS if (None, n) in existing])} 个")
    print(f"- 标准树：跳过重复的那一层「{PLAN_STD_LEVEL1}」"
          f"（共 {len(payload['skipped_level1'])} 个），它的下级**直接**挂在「{STANDARD_TOP}」下")
    print(f"- 目录总数：{n_nodes} 个（层级 {dict(sorted(payload['by_depth'].items()))}）；"
          f"复用已存在的 {n_reuse} 个 ⇒ **新建 {n_nodes - n_reuse} 个**")
    print(f"- 归属行：{len(payload['memberships'])} 条"
          f"（标准树 {len(plan['assignments'])} + 待分类 {payload['pending_docs']}）")
    print(f"- 状态行：{len(payload['states'])} 条（filed {len(plan['assignments'])} /"
          f" queued {len(plan['no_class'])} / failed {len(payload['failed'])}）")
    for f in payload["failed"]:
        print(f"    · 解析失败 → 待分类：[{f['doc_id']}] {f['standard_no']} "
              f"{f['standard_name']}｜条款 total={f['clause_total']} "
              f"normal={f['clause_normal']}｜failure_kind={f['failure_kind']}")
    backup_line = (("已写到 " + backup_path) if backup_path
                   else str(backup_dir) + os.sep + "knowledge-pre-folders-<时间戳>.db")
    print(f"- 备份：{backup_line}")
    print(f"- 引擎：{engine['note']}（会话文件 {engine['session_file']}）")


def _print_read_back(v: dict, after: dict) -> None:
    print(f"\n{BANNER}\n读回自证（**关连接后重新打开真库读**）\n{BANNER}")
    print(f"- 目录总数 {v['folders_total']}；各级 {v['folders_by_depth']}；"
          f"够不到的（父链断/成环）{v['folders_unreachable']}")
    print(f"  层级分布与计划逐级一致：{v['depth_matches_plan']}")
    print(f"- 成员行 {v['member_rows_total']}（按类型 {v['member_rows']}；"
          f"文件归属 {v['member_rows'].get('file', 0)} + 目录父子边 "
          f"{v['member_rows'].get('folder', 0)}）")
    print(f"- 状态行 {v['state_rows_total']}（按状态 {v['state_rows_by_stage']}）")
    print(f"- 顶层目录（按 sort）：{v['top_level']}")
    if v["top_level_duplicates"]:
        print(f"  ⚠ 顶层有重名：{v['top_level_duplicates']}")
    print(f"- 「{STANDARD_TOP}」直接下级 {v['standard_children_count']} 个："
          f"{v['standard_children'][:12]}{' …' if v['standard_children_count'] > 12 else ''}")
    if v["standard_has_redundant_level"]:
        print(f"  ⚠ 「{STANDARD_TOP}」下面又出现了「{PLAN_STD_LEVEL1}」——重复层没跳过！")
    print(f"- 「{PENDING_TOP}」里 {v['pending_docs']} 篇（按状态 {v['pending_by_stage']}）")
    if "pending_list_visible" in v:
        print(f"  其中「待分类」**列表接口**看得到 {v['pending_list_visible']} 篇 ——"
              f"差额 {v['pending_docs'] - v['pending_list_visible']} 篇是 catalog_hidden=1"
              "（方案 §十：那几篇只有在这一级目录里看得见，"
              "「放回目录」的路要在第 4 步跟状态一起修）")
    for p in v["pending_sample"][:4]:
        print(f"    · {p['standard_no']} [{p['stage']}] {p['failure_kind'] or ''}")
    print(f"- 库文件（含 -wal/-shm）：写入前 {after['before_total']:,} 字节 → "
          f"写入后 {after['after_total']:,} 字节（{after['delta']:+,}）；"
          f".db 本体 {after['db_before']:,} → {after['db_after']:,}"
          f"（{after['db_after'] - after['db_before']:+,}）；"
          f"-wal {after['wal_before']:,} → {after['wal_after']:,}"
          f"（{after['wal_after'] - after['wal_before']:+,}）")
    print("  ⚠ 这三个数要**一起看**：`-wal` 被 checkpoint 收进 `.db` 时总量可能变小，"
          "而 `.db` 本体**是涨的**（第 1 步实测 `.db` +2,879,488 / 合计 −1,965,664，"
          "只看合集会读成「库没长大」）")
    print(f"  {'✓ 总量一致地增长了' if after['grew'] else '⚠ 总量没涨（引擎 checkpoint 也会这样）'}")
    print(f"\n随机抽 {len(v['spot_check'])} 个目录（种子 {after['seed']}）"
          "——目录名 → 里面的文件名：")
    for s in v["spot_check"]:
        print(f"  · {s['path']}  [下级目录 {s['direct_subfolders']}；"
              f"本级文件 {s['files_total']}]")
        for name in s["files"]:
            print(f"      - {name}")
        if s["files_total"] > len(s["files"]):
            print(f"      …还有 {s['files_total'] - len(s['files'])} 个")
    if v["mismatch"]:
        print(f"\n⚠ 预期与实际对不上的项：{v['mismatch']}")


# ──────────────────────────────── 主流程 ────────────────────────────────

def _main(argv: list[str] | None) -> int:
    ap = argparse.ArgumentParser(
        description="知识库多级目录 · 对真库执行归位（默认只预演；--apply 才写库）")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="真库路径")
    ap.add_argument("--apply", action="store_true",
                    help="**真的写库**（不加这个就只预演，一个字节都不写）")
    ap.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="备份放哪")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR),
                    help="报告放哪（默认数据区；只有 --apply 时才默认落一份）")
    ap.add_argument("--report", default=None, help="机器可读 JSON 写到这个路径")
    ap.add_argument("--sample", type=int, default=20, help="抽查几个目录（默认 20）")
    ap.add_argument("--seed", type=int, default=20260921, help="抽查用的随机种子")
    ap.add_argument("--placed-by", default="apply-folder-filing", help="归位记录里的“谁”")
    args = ap.parse_args(argv)

    src = Path(args.source)
    if not src.exists():
        print(f"[FAIL] 真库不存在: {src}", file=sys.stderr)
        return 2
    print(f"{BANNER}\n知识库目录归位 · {'写库（--apply）' if args.apply else '预演（不写库）'}"
          f"\n{BANNER}\n真库：{src}")

    before = _db_files(src)
    print(f"- .db {before['db']['size']:,} 字节（mtime {before['db']['mtime']}）｜"
          f"-wal {before['wal']['size']:,}｜-shm {before['shm']['size']:,}｜"
          f"合计 {before['total_size']:,}")

    engine = _engine_status(_data_dir())
    if engine["listening"]:
        print(f"\n{'!' * 78}\n!! 警告：引擎正在运行（端口 {engine['port']} 有人听，"
              f"pid={engine['pid']}）。\n"
              + ("!! **本次是预演、不写库**；但真跑 --apply 时引擎也在写这个库。\n"
                 if not args.apply else
                 "!! **本脚本现在就要写这个库**，而引擎也在用它。\n")
              + "!! 只警告、不阻塞：SQLite 允许单写者，本脚本用 BEGIN IMMEDIATE + 60 秒 "
              "busy_timeout，会排队等锁。\n"
              "!! 但**为稳妥起见，建议先停掉引擎再跑 --apply**。\n"
              "!! 附带影响：预演的「真库未改动」判定看的是 .db 的大小与 mtime，"
              "引擎自己的 checkpoint 会改它\n"
              "!! ⇒ 可能报「预演期间 .db 变了」。那不是本脚本写的（预演全程 mode=ro）。\n"
              + "!" * 78)
    else:
        print(f"- 引擎：{engine['note']}")

    # ── 只读算出计划（这一步之后才可能写）──
    try:
        ro = _open_readonly(src)
    except sqlite3.Error as e:
        print(f"[FAIL] 只读打开真库失败：{e}", file=sys.stderr)
        return 2
    try:
        present = _target_tables_present(ro)
        rows_before = _existing_row_counts(ro)
        existing, root_names = _existing_folders(ro)
        docs = _load_docs(ro)
        plan = plan_mod.plan_filing(docs)
        clause_counts = _clause_counts(ro, list(plan["hidden_docs"]))
    finally:
        ro.close()

    docs_by_id = {str(d.get("doc_id")): d for d in docs}
    payload = build_payload(plan, existing, docs_by_id, clause_counts, args.placed_by)
    existing_total = len(set(existing.values()))
    tables = {"present": present, "statements": len(target_ddl())}
    _print_plan_summary(plan, payload, existing, tables, engine, args.apply,
                        Path(args.backup_dir), None, rows_before)

    # ── 对账：库里的实际对象 vs schema.sql 声明的对象（只读；先做，早于任何写入）──
    state_before = db_state(src)
    drift = schema_drift(src)
    print(f"- 对账（库 vs schema.sql）：声明的表 {drift['declared_counts']['tables']} /"
          f" 索引 {drift['declared_counts']['indexes']}；库里实体表"
          f" {drift['live_counts']['tables']} / 索引 {drift['live_counts']['indexes']}"
          f" ⇒ {'对得上' if drift['ok'] else '**对不上**'}")
    if drift["extra_columns"]:
        print(f"  · 库里多出 schema.sql 没声明的列 {len(drift['extra_columns'])} 个"
              f"（**合法**：生产用 ensure_additive_columns 给既有表加列，例如"
              f" catalog_hidden）⇒ 只登记、不中止：{drift['extra_columns'][:8]}")
    if not drift["ok"]:
        print(f"\n[FAIL] 库里有 schema.sql 声明、实际却**缺失**的东西 —— 库在跑本脚本之前"
              f"就被人动过。\n       本脚本**中止、一个字节都不写**（连备份都不建）。",
              file=sys.stderr)
        for label, key in (("缺表", "missing_tables"), ("缺列", "missing_columns"),
                           ("缺索引", "missing_indexes")):
            if drift[key]:
                print(f"       {label}：{drift[key][:20]}", file=sys.stderr)
        print("       先弄清是谁动过（或从备份还原），再重跑。", file=sys.stderr)
        _print_no_write_proof(src, state_before, db_state(src))
        _print_rollback(src, None)
        return 2

    # 老结构（没跳层）还在 ⇒ 拒绝往下走：静默建出两棵并存的树是最坏的一种错
    if PLAN_STD_LEVEL1 in root_names:
        print(f"\n[FAIL] 真库顶层已经有「{PLAN_STD_LEVEL1}」这个目录 —— 说明早先按**没跳层**的"
              "结构落过一次。\n       现在再跑会建出**两棵并存的树**，所以拒绝往下走。\n"
              "       先按下面的回退办法清空那三张表（或删掉那棵旧树），再重跑。",
              file=sys.stderr)
        _print_rollback(src, None)
        return 2

    if not args.apply:
        after = _db_files(src)
        untouched = (before["db"]["size"] == after["db"]["size"]
                     and before["db"]["mtime_ns"] == after["db"]["mtime_ns"])
        wal_note = ("" if before["wal"]["size"] == after["wal"]["size"] else
                    "；⚠ -wal 变了（可能是引擎自己在写，不是本脚本）")
        print(f"\n{BANNER}\n预演到此为止：**真库一个字节都没写**"
              f"（.db 大小与 mtime {'✓ 前后一致' if untouched else '⚠ 竟然变了！'}{wal_note}）\n"
              f"要真的落库，加上 --apply（会先整份备份）。\n{BANNER}")
        _print_no_write_proof(src, state_before, db_state(src))
        _print_rollback(src, None)
        if args.report:
            _write_report(args, plan, payload, {"dry_run": True, "untouched": untouched})
        if not untouched:
            print(f"[FAIL] 预演期间 .db 变了：before={before['db']} after={after['db']}\n"
                  "       本脚本预演**全程只用 mode=ro**（根本没有写的能力），所以那是"
                  "**别的进程**（多半是正在跑的引擎，或它的 checkpoint）写的。\n"
                  "       要一遍干净的证据：先停掉引擎再重跑预演。", file=sys.stderr)
            return 3
        return 0

    # ═══════════════ 从这里开始写库（顺序是死的） ═══════════════
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_db(src, Path(args.backup_dir), stamp)          # 失败 ⇒ Abort
    print(f"\n[备份 OK] {backup['path']}\n          {backup['size']:,} 字节，"
          f"耗时 {backup['seconds']} 秒；读回核对 {backup['checks']}")

    ensure = ensure_target_tables(src)
    print(f"[建表 OK] 已有 {ensure['existed_before'] or '无'}；新增对象 "
          f"{len(ensure['created_objects'])} 个；对账 {ensure['schema_drift']['ok']}"
          "（① 库 vs schema.sql 声明；② 本次建表前后既有对象指纹）")

    from src.core.knowledge import folder_store as fs
    t0 = time.time()
    res = fs.build_folder_tree(payload["nodes"], payload["memberships"], payload["states"],
                               db_path=src, reuse_existing=True)
    n_sorts = align_top_sorts(src)          # 复用来的顶层目录也要带上手定顺序
    # failure_kind 不在 build_folder_tree 的入参里 ⇒ 走公开的状态写入口补上（只有那几篇）
    for f in payload["failed"]:
        fs.set_filing_state(f["doc_id"], "failed", db_path=src,
                            failure_kind=f["failure_kind"])
    write_seconds = round(time.time() - t0, 2)
    print(f"[落库 OK] 新建目录 {res['folders_created']} / 复用 {res['folders_reused']}；"
          f"归属 +{res['members_added']}（同处重复跳过 {res['members_skipped']}）；"
          f"状态 {res['states_set']}；顶层 sort 对齐 {n_sorts} 行；耗时 {write_seconds} 秒")
    _print_plan_summary(plan, payload, existing, tables, engine, True,
                        Path(args.backup_dir), backup["path"], rows_before)

    verify = read_back(src, plan=plan, payload=payload, existing_total=existing_total,
                       sample=args.sample, seed=args.seed)
    after = _db_files(src)
    grew = after["total_size"] > before["total_size"]
    _print_read_back(verify, {
        "before_total": before["total_size"], "after_total": after["total_size"],
        "delta": after["total_size"] - before["total_size"],
        "db_before": before["db"]["size"], "db_after": after["db"]["size"],
        "wal_before": before["wal"]["size"], "wal_after": after["wal"]["size"],
        "grew": grew, "seed": args.seed})
    _print_rollback(src, backup["path"])

    report = _write_report(args, plan, payload, {
        "dry_run": False, "apply": {k: v for k, v in res.items() if k != "key_to_id"},
        "top_sorts_aligned": n_sorts,
        "write_seconds": write_seconds, "backup": backup, "ensure_tables": ensure,
        "before": before, "after": after, "grew": grew, "verify": verify, "engine": engine,
    })
    if report:
        print(f"\n机器可读报告：{report}")

    bad: list[str] = []
    if verify["mismatch"]:
        bad.append(f"读回自证对不上：{verify['mismatch']}")
    if verify["standard_has_redundant_level"]:
        bad.append("「标准」下面还有重复层")
    if verify["top_level_duplicates"]:
        bad.append(f"顶层重名：{verify['top_level_duplicates']}")
    if not grew:
        print("⚠ 库文件总量没有增长（引擎 checkpoint 也会这样）——"
              "以行数为准，见上", file=sys.stderr)
    if bad:
        for b in bad:
            print(f"[FAIL] {b}", file=sys.stderr)
        return 3
    print(f"\n[OK] 落库完成并读回自证通过（{verify['folders_total']} 个目录、"
          f"{verify['member_rows_total']} 条归属、{verify['state_rows_total']} 条状态）")
    return 0


def _write_report(args, plan: dict, payload: dict, extra: dict) -> str | None:
    """机器可读报告。预演下**只在显式给了 --report 时**才落盘（否则预演一个字都不写）。"""
    path = args.report
    if not path and not extra.get("dry_run"):
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = str(out_dir / f"folder-filing-apply-"
                             f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    if not path:
        return None
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": args.source, "apply": bool(args.apply), "placed_by": args.placed_by,
        "prebuilt_tops": [{"name": n, "sort": s} for n, s in PREBUILT_TOPS],
        "skipped_level1": payload["skipped_level1"],
        "by_depth": {str(k): v for k, v in sorted(payload["by_depth"].items())},
        "nodes_total": len(payload["nodes"]),
        "nodes_reused": len(payload["reused"]),
        "memberships": len(payload["memberships"]),
        "states": len(payload["states"]),
        "failed_docs": payload["failed"],
        "summary": plan_mod.summarize_plan(plan),
        "recorded_20260921": RECORDED,
        **extra,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except Abort as e:
        print(f"\n[FAIL] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
