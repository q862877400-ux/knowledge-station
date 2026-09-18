# -*- coding: utf-8 -*-
"""VLM OCR 通道器（2026-09-15 用户指令：本次进化循环**只走 VLM**）。

规则（用户原话）：「必须用 VLM，云 VLM 不通就跑本地 VLM，pipeline 不参与本次
循环进化。」故本工具：

1. **云 VLM 优先**：`mineru_cloud_submit_and_wait`（`model_version=vlm`，
   由 `KS_VLM_ONLY=1` 强制）；
2. **云不通 → 本地 VLM**：`do_parse(backend="vlm-engine")`（MinerU2.5-Pro-1.2B，
   实测 0.028 p/s）；
3. **pipeline 一律不参与**：本工具不调用任何 `backend="pipeline"` 路径，
   并以 `KS_VLM_ONLY=1` 让产品层也拒绝 pipeline（`_local_backend()`）。

产物的落位是**关键**：写到 `parse_out/<doc_id>/`（覆盖前把旧目录改名留档），
这样 `_cached_parse_result` / `middle_locator` 找到的就是 VLM 产物——
`evolve.py eval` 于是评估 VLM 输出，而非历史的 pipeline 输出。

云额度护栏：`KW_DAILY_CLOUD_FILES`（默认 1000）按日累计，超出即自动转本地 VLM。

用法：
  python var/ocr-loop/vlm_ocr.py --docs 3                 # 库里前 3 部（云→本地）
  python var/ocr-loop/vlm_ocr.py --docs 50 --channel auto
  python var/ocr-loop/vlm_ocr.py --pdf-root "D:\\...\\GBT" --docs 10
  python var/ocr-loop/vlm_ocr.py --status
"""
from __future__ import annotations

import itertools
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("KS_VLM_ONLY", "1")   # 本工具自身也强制 VLM（防误配）
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.core.config import get_settings                     # noqa: E402

STATE = HERE / "vlm_ocr_state.json"
LOG = HERE / "vlm_ocr_log.jsonl"
QUOTA = HERE / "vlm_cloud_quota.json"
#: 云 VLM 日额度上限。**用户给定口径（2026-09-15）：5000 个文件/日**——
#: 我最初按「1000 页/日」记账是错的（单位与数值都错），会导致还没到额度就
#: 切到慢 20 倍的本地 VLM。**单位 = 文件（文档），不是页**。
#: 可用 `KW_DAILY_CLOUD_FILES` 覆盖。本计数器只统计**本工具**提交量；
#: 控制台真值更高时以控制台为准（可用 `--set-used N` 校准）。
DAILY_CLOUD_FILES = int(os.environ.get("KW_DAILY_CLOUD_FILES", "5000"))

#: 云账号别名集合（keys_pool 的别名口径）。**这些字串永远不得出现在 state 键里**
#: ——它们是账号标识，不是文档标识。见 commit_rec 的键护栏。
_ALIAS_KEYS = {"project"} | {f"loop{i}" for i in range(1, 10)}


def db_path() -> str:
    return str(get_settings().db_path)


def parse_out() -> Path:
    return Path(get_settings().data_dir) / "parse_out"


def pages_of(pdf: Path) -> int:
    import fitz
    with fitz.open(pdf) as d:
        return d.page_count


def load_json(p: Path, default):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return default
    return default


def save_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def append_log(obj: dict) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def recover_state(state: dict, log_path: Path, alias_keys: set[str]) -> tuple[int, int]:
    """由 append-only 日志回补 state 中缺失的文档条目 + 剪掉历史别名键。

    为什么必须有：断点续跑的记账**不能只靠 state 一个易损文件**。一旦
    `rec["key"]` 被别名覆盖（见 commit_rec 护栏注释），state 会把整批文档
    压进一个别名键，而**日志里每条记录的 std_no/产物路径都在**——用
    `standard_no` 反查 doc_id 即可把已完成的部数无损补回，避免重启后重做。

    返回 `(回补条数, 剪除别名键数)`。
    - 已存在于 state 的键**不动**（运行中的实例拥有更新信息）；
    - 别名键（云账号）**从 state 剪除**——它们是历史缺陷留下的死条目，会让
      `--status` 把 `loop1` 这类死键计成"失败 1 部"（实测误报）；
    - 库里查不到的标准号（非库内语料，如 `--pdf-root` 模式）按原键保留。
    """
    pruned = 0
    for k in [k for k in state if k in alias_keys]:
        # 先尝试把它还原成真文档键：能把该文档的记账救回来，就别丢
        std = str((state.get(k) or {}).get("std_no") or "")
        did = _doc_id_of(std)
        if did and did not in state:
            state[did] = state.pop(k)
        else:
            state.pop(k, None)
            pruned += 1
    if not log_path.exists():
        return 0, pruned
    try:
        recs = [json.loads(x) for x in log_path.read_text(encoding="utf-8").splitlines()
                if x.strip()]
    except Exception:  # noqa: BLE001
        return 0, pruned
    added = 0
    ids_cache: dict[str, str] = {}
    for r in recs:
        raw = str(r.get("key") or "")
        did = "" if raw in alias_keys else raw
        if not did:
            std = str(r.get("std_no") or "")
            if std not in ids_cache:
                ids_cache[std] = _doc_id_of(std)
            did = ids_cache[std]
        if not did or did in state:
            continue
        state[did] = r
        added += 1
    return added, pruned


def _doc_id_of(standard_no: str) -> str:
    """标准号 → doc_id（只读库；查不到返回空串）。跨轮一律按标准号配对。

    ⚠ 查之前折**存储形**（§11.0 R6c-3f；复核 b34 的 D 项把这里点名为"未折的等值读"）：
    库里存的是半角（写入侧已收口），这里的入参来自文件名/manifest，**可能带全角 `／`**
    ——不折就会静默查不到（复核说明：它没能构造出"仅因未折而失败"的活复现，
    因为现有 stem 都带名称后缀；但那是**当前数据**的运气，不是这段代码对了）。
    """
    if not standard_no:
        return ""
    try:
        from src.core.text_utils import store_standard_no
        conn = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True)
        row = conn.execute("SELECT doc_id FROM doc_meta WHERE standard_no=?",
                           (store_standard_no(standard_no),)).fetchone()
        conn.close()
        return str(row[0]) if row else ""
    except Exception:  # noqa: BLE001
        return ""


def cloud_files_today() -> int:
    """今日已提交云 VLM 的**文件数**（单位=文档，非页）。"""
    q = load_json(QUOTA, {})
    return int(q.get(time.strftime("%Y-%m-%d"), 0))


def add_cloud_files(n: int = 1) -> None:
    q = load_json(QUOTA, {})
    day = time.strftime("%Y-%m-%d")
    q[day] = int(q.get(day, 0)) + n
    save_json(QUOTA, q)


def set_cloud_files_used(n: int) -> None:
    """用控制台真值校准今日用量（`--set-used N`）。"""
    q = load_json(QUOTA, {})
    q[time.strftime("%Y-%m-%d")] = int(n)
    save_json(QUOTA, q)


def targets_from_db(limit: int | None) -> list[dict]:
    conn = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT doc_id, standard_no, standard_name, file_path "
                        "FROM doc_meta ORDER BY standard_no").fetchall()
    conn.close()
    out = []
    for r in rows:
        p = Path(r["file_path"] or "")
        if not p.exists() and p.suffix == "":
            p = Path(str(p) + ".pdf")
        if not p.exists():
            continue
        out.append({"doc_id": r["doc_id"], "std_no": r["standard_no"],
                    "std_name": r["standard_name"] or "", "pdf": p})
    return out[:limit] if limit else out


def targets_from_root(root: Path, limit: int | None) -> list[dict]:
    pdfs = sorted(root.rglob("*.pdf"))
    if limit:
        pdfs = pdfs[:limit]
    return [{"doc_id": "", "std_no": p.stem, "std_name": p.stem, "pdf": p}
            for p in pdfs]


def targets_from_corpus_list(list_file: Path, limit: int | None) -> list[dict]:
    """按**指定清单**取目标（`build_fresh_corpus.py` 产出的工作集）。

    为什么需要它而不是 `--pdf-root`：避免过拟合要**精确控制语料身份**——
    目录模式会把整棵树的 PDF 都当成目标（含撞键副本、含已审过的文档），
    而清单模式只跑被显式选中的那批（全新、不撞键、与旧语料零重叠）。

    doc_id 仍为空（这些文档尚未入库），故产物落 `parse_out/<标准化源文件名>/`，
    由 `artifact_index` 的稳定键索引定位——跨轮一律按 standard_no 配对。
    """
    obj = json.loads(list_file.read_text(encoding="utf-8"))
    paths = [Path(p) for p in (obj.get("paths") or [])]
    out = []
    for p in paths:
        if not p.exists():
            continue
        out.append({"doc_id": "", "std_no": p.stem, "std_name": p.stem, "pdf": p})
    return out[:limit] if limit else out


def land_dir(t: dict) -> Path:
    """产物落位目录：库内文档用其 doc_id（复用链路直接命中），否则用 PDF 名。"""
    key = t["doc_id"] or t["std_no"]
    return parse_out() / _land_key(key)


def _land_key(key: str) -> str:
    """落位/输出名消毒（**单一所有者**，与 `artifact_index._land_key` 同口径）。

    改这里必须同步改 `artifact_index._land_key`，否则新语料产物定位失效。
    """
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in key)[:80]


def stash_old(d: Path, key: str, keep_blocks: bool = True) -> str:
    """把既有产物挪到**查找路径之外**留档（可回滚），返回留档目录。

    必须挪出 `parse_out/<key>/`：否则新旧产物同处一棵树，`find_middle_files`
    把两批都找出来（`middle_files[0]` 取哪个不确定）→ 循环评估的到底是
    VLM 产物还是历史 pipeline 产物就不可控了。

    `keep_blocks=True`（默认）：**保留** `blocks.json`（文本层直取产物）——
    文本层提取不是 OCR（fitz 直读，零识别误差），比任何 OCR 更保真。用户指令
    约束的是 **OCR 引擎**（VLM 而非 pipeline），不是"把有文本层的原生数字版
    国标降级成 OCR"。

    `keep_blocks=False`（`--ocr-textlayer`）：把 blocks 也挪走，**强制走 VLM**。
    为什么需要它：少数 PDF 的文本层是**缺字形**的（fitz 读出来是私用区 PUA，
    如 '张\\ue3e4\\ue3e4'、'r2\\ue03cQ'）——文本层保真原则在此**失效**，
    因为真值根本不在文本层里。此时唯一能取回真字的是**像素 OCR**（VLM）。
    若不挪走 blocks：`_cached_parse_result` 优先命中 blocks → 仍读文本层 →
    OCR 白跑（实测口径：pipeline.py 先 `blocks.json` 后 `find_middle_files`）。
    """
    if not d.is_dir():
        return ""
    moves = [p for p in d.iterdir()
             if not (keep_blocks and p.name == "blocks.json")]
    if not moves:
        return ""
    bak = parse_out() / ".stash" / key / time.strftime("%Y%m%d-%H%M%S")
    bak.mkdir(parents=True, exist_ok=True)
    for p in moves:
        shutil.move(str(p), str(bak / p.name))
    return str(bak)


KEYS_FILE = HERE / ".cloud_keys"
LEGACY_KEY_FILE = HERE / ".cloud_key2"
KEY_LOG = HERE / "vlm_key_usage.json"


def keys_pool() -> list[tuple[str, str]]:
    """云密钥池：`[(别名, key), ...]`。

    2026-09-15（用户指令）：多给几个账号的 key，**一个云通道卡住就换另一个 key
    重试**。这些 key **一律不写进项目配置**（用户明确要求），只存在循环私有文件
    `var/ocr-loop/.cloud_keys`（每行一个；`var/` 已被 gitignore）。
    顺序：①项目已配置的 key（别名 project）→ ②③… 循环专用 key（loop2/loop3…）。
    配额是按账号计的，多号即多额度。
    """
    out: list[tuple[str, str]] = []
    from src.core.config import get_settings
    pk = (getattr(get_settings(), "mineru_cloud_api_key", "") or "").strip()
    if pk:
        out.append(("project", pk))
    lines: list[str] = []
    for f in (LEGACY_KEY_FILE, KEYS_FILE):
        if f.exists():
            lines += [x.strip() for x in f.read_text(encoding="utf-8").splitlines()
                      if x.strip()]
    known = {k for _, k in out}
    for k in lines:
        if k in known:
            continue
        known.add(k)
        out.append((f"loop{len(out) + 1}", k))
    return out


def use_key(key: str) -> None:
    """把密钥设为**内存中的**当前值（不落配置、不改项目文件）。

    **2026-09-15 并发 bug 修复**：原实现先 `reset_settings()` 清全局缓存再取，
    4 个 worker 线程并发时另一线程会看到缓存为 None →
    `AttributeError: 'NoneType' object has no attribute 'mineru_cloud_api_key'`
    直接搞死整个批量（实测日志）。清缓存本无必要：
    `mineru_cloud._resolve_settings()` 每次调用都现读该属性，直接赋值即可
    （CPython 属性赋值是原子的），且不再触碰全局缓存。
    """
    from src.core.config import get_settings
    s = get_settings()
    if s is not None:
        s.mineru_cloud_api_key = key


def mask(k: str) -> str:
    return f"{k[:6]}…{k[-4:]}" if len(k) > 12 else "***"


def add_key_use(alias: str) -> None:
    """⚠ **诊断用的粗计数，不是权威口径**（2026-09-16 实测教训）。

    **本函数是无锁 read-modify-write**：`load_json` → `+1` → `save_json`。
    批量侧有 24 个线程 + 可能并存的多个 driver 同时调用 → **互相覆盖丢失**，
    实测偏差极大：本文件报 `project 2109 / loop2 304 / loop3 6`，
    而**权威口径**（记录自身的 `cloud_key` 字段）显示批 10 实际是
    `loop2: 138 · project: 136 · loop3: 3`——**几乎完全均衡**。

    ⚠ 我曾据本文件的数字误判"轮转被竞态吃掉、key 用量失衡"，
    并据此写了一轮错误归因（已撤回，见 `evolve/instrument_fixes.jsonl`）。
    **要查 key 的真实使用分布，请统计 `vlm_ocr_state.json` 里每条记录的
    `cloud_key` 字段**，不要用本文件。

    本函数保留原语义（不引入锁）：它只用于"大致看有没有 key 被完全闲置"，
    精确判断一律以 state 为准。

    ⚠ **且它绝不能因自身失败而影响批次**（2026-09-16 实测）：并发下 `save_json`
    的 `tmp.replace()` 会抛 `PermissionError: [WinError 32] 另一个程序正在使用此文件`
    ——该异常从 `run_cloud` 穿出会**杀掉整批**。故此处整体兜住：**计数丢了无所谓**。
    """
    try:
        d = load_json(KEY_LOG, {})
        d[alias] = int(d.get(alias, 0)) + 1
        save_json(KEY_LOG, d)
    except Exception:  # noqa: BLE001 —— 诊断计数器失败绝不许影响业务流程
        pass


#: **起始 key 的轮转计数器**（2026-09-16 立，见 `run_cloud` 里的缺陷说明）。
#: 用 `itertools.count` 的自增——CPython 下 `next()` 对内置迭代器是原子的，
#: 24 个 worker 线程各取一个序号不会撞号，无需额外加锁。
#: 作用：把"24 个线程齐射同一个 key"摊成"每线程从一个不同的 key 起步"。
_KEY_SLOT = itertools.count()


def _is_capability_boundary(err_text: str) -> bool:
    """`MineruCloudError` 的文本 → 是否**云侧能力边界**（云再试也不可能成功）。

    **为什么要分开**（2026-09-16 实测）：`MineruCloudError` 同时承载
      · 能力边界：`number of pages exceeds limit (200 pages)`、格式不支持；
      · 瞬时类：`429 Too Many Requests`、`retry limit reached`、超时、5xx。
    两者都当 fatal 的后果：429 风暴里 135 部被判"云做不了" → 转本地 GPU
    （慢约 20 倍、串行独占）→ 白烧数小时；而它们重投云几秒即成功。

    判据取**能力边界白名单**（命中才算 fatal），其余一律当瞬时类换 key 重试。
    白名单优于"瞬时黑名单"：新增的未知错误默认**走重投**（更保守、代价更低）——
    误判成可重投只会多花一次云调用；误判成 fatal 会白烧数分钟 GPU。
    实测文本（`vlm_batch7.err` / state）：
      · `云能力边界：批次 … 解析失败: retry limit reached` ← **不是**能力边界，是重试耗尽
      · `number of pages exceeds limit (200 pages)` ← 是
    """
    t = (err_text or "").lower()
    #: 明确的瞬时/限流特征——**先排除**，避免被下面的宽松词误收
    for bad in ("429", "too many requests", "retry limit", "timeout", "timed out",
                "502", "503", "504", "connection", "temporarily"):
        if bad in t:
            return False
    #: 能力边界白名单
    for good in ("exceeds limit", "超过限制", "page limit", "unsupported",
                 "not supported", "格式不支持", "pages exceeds"):
        if good in t:
            return True
    #: 兜底：都不像 → 当瞬时类（可重投），并把原文留在消息里供人工判定
    return False


def run_cloud(pdf: Path, d: Path, attempts: int = 2,
              poll_timeout: float = 900.0) -> dict:
    """云 VLM。**轮询超时放宽 + 重试 + 换 key**。

    实测（2026-09-14）：单个云任务会卡住（30 分钟无结果）——串行时它阻塞全体；
    重投往往很快出结果；**换另一个账号的 key 也常能绕开**（用户 2026-09-15 指令）。

    **超时口径修订（2026-09-15）**：原 180s 对 50+ 页文档偏紧——云侧解析本就要
    数分钟，超时即被当失败、换 key 重投，反而白烧次数与配额（实测日志连续
    「云解析失败 → 换 key 重试」）。
    两阶段架构（本地 VLM 改为云阶段结束后串行兜底）之后，**云可以放心等**：
    多等几分钟远比落到慢 20 倍的本地 VLM 划算。故默认 900s。
    """
    from src.core.ingestion.mineru_cloud import (mineru_cloud_available,
                                                 mineru_cloud_submit_and_wait,
                                                 _model_version)
    pool = keys_pool()
    if not pool:
        return {"channel": "cloud", "status": "unavailable",
                "msg": "无可用云 key"}
    last = ""
    #: **云端业务性失败必须当数据、不能当异常**（2026-09-15 实测：一次超限文件
    #: 杀掉整个 500 部批次）。`_poll_result` 对"解析失败"是 `raise MineruCloudError`
    #: ——实测一条 `number of pages exceeds limit (200 pages)` 从工作线程穿出
    #: ThreadPool，**整个批量进程当场死亡**（批次只跑 116/500）。
    #: 云对这些文档是**能力边界**（>200 页不能云解析），不是临时故障：
    #: 换 key 无用，应立即转本地 VLM 兜底（`cloud_stage` 的 failed 分支会做）。
    from src.core.ingestion.mineru_cloud import MineruCloudError
    # **起始 key 必须按文档轮转**（2026-09-16 实测批 9 缺陷）。
    #
    # 缺陷：原实现每个线程都从 `pool[(k-1) % len(pool)]` 的**第一个** key 起步
    # （k=1 → pool[0] = project）→ `parallel=24` 时 **24 个线程齐射同一账号** →
    # 持续 429。实测批 9：361 条失败里 **343 条是 429**，秒败按分钟分布
    # 03:16×130 / 03:20×15 / 03:21×114 / 03:22×53（**跨 6 分钟四波，不是启动突发**）。
    # 而单账号探针（40 部）零 429——样本太小没撞到该账号的速率阈值。
    #
    # 修法：给每部文档一个递增序号，起始 key 取 `(序号 % len(pool))`
    # → 24 个并发线程自然摊到多账号；重试仍在池内轮转（保持"换 key 重试"语义）。
    # 只改**起点**，没改重试顺序与池的大小。
    _slot = next(_KEY_SLOT)
    for k in range(1, attempts + 1):
        alias, key = pool[(_slot + k - 1) % len(pool)]
        # ❗**绝不调用 `use_key(key)`**（2026-09-16 找到根因后删掉）。
        #
        # `use_key()` 写的是**全局 settings**，而 `keys_pool()` 又**读同一个全局**
        # 来构造池（`pk = get_settings().mineru_cloud_api_key`）→ **自污染**。
        # 实测（`probe_key_alias.py` 家族）：
        #     调用前  pool = [project:sk-4IW, loop2:sk-HWq, loop3:sk-Z2L]   ← 3 项
        #     use_key(sk-Z2L) 之后
        #     调用后  pool = [project:sk-Z2L, loop2:sk-HWq]                 ← 只剩 2 项
        # 即：`project` 项被"刚用过的 key"覆盖、**真 key 被去重丢掉、池越用越短**。
        # 后果：别名与实发 key 错配（日志 `key=project sk-HWq…`）、轮转索引漂移、
        # 且**池会随使用逐步退化**。
        #
        # 现在 key 由下面 `api_key=key` **显式传入**，全局写入已无任何必要；
        # 删掉它之后，池的构造不再受使用过程影响，共享可变体也一并消失。
        #
        # 可用性检查改为**在显式 key 上直接判**（原 `mineru_cloud_available()` 走
        # `_resolve_settings()` 读全局，同样会被污染）。
        if not key.strip():
            last = f"{alias} 不可用：key 为空"
            continue
        try:
            # **key 显式传入**（2026-09-16）：实发 key 由本变量决定，与全局无关。
            r = mineru_cloud_submit_and_wait(pdf, d, timeout=poll_timeout,
                                             api_key=key)
        except MineruCloudError as e:
            add_key_use(alias)
            # ❗**"能力边界"必须窄判**（2026-09-16 实测，代价是数小时 GPU）。
            #
            # 缺陷：原先**所有** `MineruCloudError` 都返回 `fatal=True`。但该异常同时
            # 承载两类完全不同的语义：
            #   · **能力边界**（页数超限 / 格式不支持）→ 云真做不了，转本地是对的；
            #   · **瞬时/限流类**（`429 Too Many Requests`、`retry limit reached`、
            #     超时、服务端 5xx）→ 云**能**做，只是此刻不行 → **必须重投云**。
            # 实测后果：429 风暴期间每部都被判"云再也不可能成功" → 送进慢约 20 倍的
            # 本地 GPU（3–10 分钟/部，串行独占）→ 实测 135 部被判 fatal，
            # 等于把**数小时 GPU 时间**烧在"重投云几秒就能成"的文档上。
            # 这与本项目自己的告警（见上文"云**拥塞**导致的超时**必须重试云**"）
            # 正好相反，属实现与设计相悖。
            if _is_capability_boundary(str(e)):
                return {"channel": "cloud", "status": "failed", "fatal": True,
                        "msg": f"云能力边界：{str(e)[:150]}",
                        "model_version": _model_version()}
            # 瞬时类：换 key 重试（多账号独立限流，换 key 常能绕开），
            # 全部 key 都失败则落 `failed`（**不设 fatal**）→ 由
            # `_requeue_cloud_failures` / `_carry_over` 带进下一批**重投云**。
            last = f"云瞬时错误（非能力边界，将重投云）: {str(e)[:120]}"
            print(f"    ↳ {last} → 换 key 重试", flush=True)
            continue
        except Exception as e:  # noqa: BLE001 —— 其余异常也不许杀批次
            last = f"云调用异常 {type(e).__name__}: {str(e)[:120]}"
            print(f"    ↳ {last} → 换 key 重试", flush=True)
            continue
        add_key_use(alias)
        if r is not None:
            # **字段名避让**：这里返回的 rec 会被 cloud_stage 用 rec.update() 合并，
            # 而 rec["key"] 是**文档键**（doc_id/标准号）。先前此处写 "key": alias
            # 把文档键覆盖成云账号别名 → 所有文档都落进 state["project"] 一个键，
            # 断点续跑记账全废（每次重启都从第 13 部重做）。实测 125 行 JSONL 全同键。
            return {"channel": "cloud", "status": "ok",
                    "out": str(r.get("output_dir")), "attempt": k,
                    "cloud_key": alias, "model_version": _model_version()}
        # **消息要说清"配置值"而不是实测值**（2026-09-16 修正）：原文案写"轮询 240s"，
        # 读起来像"真的等了 240 秒"，实测却有 `wall_s=42.8s` 的失败——因为
        # `mineru_cloud_submit_and_wait` 把 HTTP 层异常也归为失败并记这条消息，
        # 而它**并未等满** poll_timeout。这条歧义害我把根因误判成"240s 超时簇"，
        # 实际是连接层异常。故改为"配置超时 Ns"，实际耗时看记录的 `wall_s`。
        last = (f"第 {k}/{attempts} 次云解析失败（key={alias} "
                f"{mask(key)}，配置超时 {poll_timeout:.0f}s）")
        print(f"    ↳ {last} → 换 key 重试", flush=True)
    return {"channel": "cloud", "status": "failed", "msg": last,
            "model_version": _model_version()}


def run_local_vlm(pdf: Path) -> dict:
    """本地 VLM（vlm-engine）。**不提供 pipeline 分支**——按用户指令。"""
    from mineru.cli.common import do_parse
    tmp = Path(tempfile.mkdtemp(prefix="ks_vlmlocal_"))
    try:
        # **输出名必须消毒**（2026-09-15 实测）：国标源文件名常含**全角斜杠**
        # `／`（U+FF0F，如 'GB／T 16751.1-2023 …'）——Windows 禁止该字符作文件名，
        # MinerU 用它建输出文件时被拒 → `OSError: [Errno 22] Invalid argument`，
        # 本地 VLM 兜底整条失败（实测 241 页的 GB/T 16751.1-2023 正是此因）。
        # 与 `land_dir` 同一消毒口径：只用于 MinerU 的**输出名**，不影响源文件读取。
        safe_stem = _land_key(pdf.stem)
        do_parse(str(tmp), [safe_stem], [pdf.read_bytes()], ["ch_server"],
                 backend="vlm-engine", parse_method="auto",
                 f_draw_layout_bbox=False, f_draw_span_bbox=False,
                 f_dump_orig_pdf=False, f_dump_model_output=False)
    except Exception as e:  # noqa: BLE001
        return {"channel": "local-vlm", "status": "failed",
                "msg": f"{type(e).__name__}: {str(e)[:150]}", "tmp": str(tmp)}
    # MinerU 输出 tmp/<stem>/vlm/...；整体搬到落位目录的 mineru/
    cands = [p for p in tmp.iterdir() if p.is_dir()]
    if not cands:
        return {"channel": "local-vlm", "status": "failed", "msg": "本地 VLM 无产物",
                "tmp": str(tmp)}
    return {"channel": "local-vlm", "status": "ok", "produced": str(tmp),
            "tmp": str(tmp)}


def has_text_layer(d: Path) -> bool:
    """该文档是否已有非空文本层产物（blocks.json）——有则无需 OCR。"""
    bp = d / "blocks.json"
    if not bp.exists():
        return False
    try:
        raw = json.loads(bp.read_text(encoding="utf-8"))
        return any(isinstance(b, dict) and b.get("text") for b in raw)
    except Exception:  # noqa: BLE001
        return False


def has_usable_product(d: Path) -> bool:
    """落位目录里是否**已有可用的解析产物**（非空 middle/layout json）。

    **为什么需要**（用户指令 2026-09-15）：「本地已经 OCR 好了的、本地有文件的，
    你就直接用吧，就算他是巨型文件……只有说未来遇到了要再次 OCR 的时候就把它跳过」。
    即巨型文档**不该无条件丢弃**——若产物已经在盘上，直接用（零成本）；
    「跳过」只适用于**需要重新 OCR** 的情形（云页数硬限 + 本地极慢）。

    判据与展示链路一致（`artifact_index.PATTERNS` 同款 glob），避免"以为有产物、
    实际链路取不到"。文件非空即认可用（空 json 是失败残留）。
    """
    for pat in ("*_middle.json", "middle.json", "*_layout.json", "layout.json"):
        for f in d.rglob(pat):
            try:
                if f.stat().st_size > 0:
                    return True
            except OSError:
                continue
    return False


def cloud_stage(t: dict, c_to: float, c_at: int, force_ocr: bool,
                force_textlayer: bool = False) -> dict:
    """单部「云阶段」：留档 → 云 VLM。**不做本地兜底**（并发调用，纯 I/O）。

    `force_textlayer=True`（`--ocr-textlayer`）：连文本层产物一起留档 →
    强制走像素 OCR。用于文本层**缺字形**（PUA）的文档，见 `stash_old` 注释。

    返回 rec；`status` ∈ ok / failed / textlayer / skipped-quota。
    """
    key = t["doc_id"] or t["std_no"]
    d = land_dir(t)
    d.mkdir(parents=True, exist_ok=True)
    pg = pages_of(t["pdf"])
    rec: dict = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "key": key,
                 "std_no": t["std_no"], "pages": pg, "pdf": str(t["pdf"])}
    if has_text_layer(d) and not force_ocr and not force_textlayer:
        rec.update({"channel": "textlayer", "status": "textlayer", "wall_s": 0.0,
                    "msg": "有文本层，无需 OCR（保留 fitz 直取产物）"})
        return rec
    rec["stashed"] = stash_old(d, key, keep_blocks=not force_textlayer)
    t0 = time.monotonic()
    r = run_cloud(t["pdf"], d, attempts=c_at, poll_timeout=c_to)
    rec.update(r)
    rec["wall_s"] = round(time.monotonic() - t0, 1)
    return rec


def local_stage(t: dict, rec: dict) -> dict:
    """本地 VLM 兜底（**串行**：GPU 独占）。"""
    key = t["doc_id"] or t["std_no"]
    d = land_dir(t)
    t0 = time.monotonic()
    lr = run_local_vlm(t["pdf"])
    if lr.get("status") == "ok":
        mine = Path(lr["produced"])
        targets_dir = d / "mineru"
        targets_dir.mkdir(parents=True, exist_ok=True)
        for p in mine.iterdir():
            shutil.move(str(p), str(targets_dir / p.name))
        shutil.rmtree(lr["tmp"], ignore_errors=True)
    rec.update({k: v for k, v in lr.items() if k != "tmp"})
    rec["wall_s"] = round(rec.get("wall_s", 0.0) + time.monotonic() - t0, 1)
    return rec


def commit_rec(state: dict, rec: dict) -> None:
    """落盘一条记录。**键护栏**：状态键必须是文档键，不是云账号别名。

    缺陷证据（2026-09-15 实测）：`run_cloud` 曾把云账号别名写进 `"key"`，
    `cloud_stage` 的 `rec.update(r)` 把它盖到文档键上 → 全部文档压进
    `state["project"]` 一个键（日志 133 条里 116 条同键），断点续跑记账全废
    （每次重启从第 13 部重做）。此处护栏让同类回归**当轮就炸**，而不是
    静默把台账写坏——静默损坏的代价远高于一次显式报错。
    """
    key = rec.get("key")
    if not key or key in _ALIAS_KEYS:
        raise RuntimeError(
            f"! 状态键非法={key!r}（std_no={rec.get('std_no')!r}）——云账号别名不得"
            f"当作文档键，否则全体文档撞成一个键、断点续跑失效。")
    state[key] = rec
    save_json(STATE, state)
    append_log(rec)
    mark = "✓" if rec.get("status") in ("ok", "textlayer") else "✗"
    print(f"    {mark} {rec.get('channel')} {rec.get('status')} "
          f"{rec.get('wall_s')}s {str(rec.get('msg') or '')[:60]}", flush=True)


def _pid_alive(pid: int) -> bool:
    """该 pid 是否活着。

    **为什么不能只用 `Get-Process`**（2026-09-15 实测）：`Get-Process -Id <不存在>`
    在 pwsh 里会写非终止错误流，输出为空——而本函数原来的兜底是"查不动就当活着"
    （保守）。于是**已死 pid 被判成活着** → 陈旧锁永不被接管 → 闸门永久堵死
    （下一次启动被让位、却没人再干活）。实测：pid=999999 的陈旧锁没能被接管。

    故改用 `tasklist`（Windows 自带、退出码语义明确），并在**只有真报错**时
    才保守判活；"进程不存在"是明确答案，不是"查不动"。
    """
    if pid <= 0:
        return False
    try:
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                           capture_output=True, text=True, timeout=30)
    except Exception:  # noqa: BLE001
        return True          # 工具都起不来 → 保守（宁可堵住也不覆盖台账）
    out = (r.stdout or "").strip()
    if not out:
        return False
    # **必须判"这行是不是真的进程行"**：无匹配时 tasklist 只打印一行提示
    # （英文 "INFO: No tasks are running which match the specified criteria."、
    #  中文 "信息: 没有运行的任务匹配指定标准。"），里面**不含任何数字**；
    # 真实进程行形如 "python.exe   12345 Console   1   519,168 K"。
    # 早先写成 `str(pid) in out` 是错的：提示语里同样有 "PID" 字样（实测踩过），
    # 会把"已死"判成"活着" → 陈旧锁永不被接管 → 闸门永久堵死。
    import re as _re
    return bool(_re.search(r"\b\d+\b", out)) and str(pid) in out


#: 单实例闸门抢不到锁时的**等待时长**（秒）。可用 `--lock-wait <秒>` 覆盖
#: （测试与"只想探一次"的场景需要短等待）。
#: **为什么必须等而不是立刻退出**（2026-09-15 实测）：driver 看到进程退出就重拉
#: （每 20 秒一次，最多 5 次）。若闸门立刻退出，driver 的 5 次机会会在 100 秒内
#: 耗尽 → 报"反复中断 → 待人工"，**整条推进链静默停住**——而真正在跑的那个实例
#: 其实完全正常（实测场景：本地 VLM 正在跑 408 页文档，需 68–90 分钟，期间 driver
#: 无从得知"它在正常干活"）。等待让 driver 的每次重启都变成一次"等着接手"的机会。
LOCK_WAIT_S = 900.0

#: **云尝试闸门**（2026-09-15 加）：`--channel local` 时**不提交任何云任务**，
#: 所有非完成态文档直接进本地队列。用途：用户要求「本地跑着、等谷价再走 API」时，
#: 让本地 GPU 继续产出，同时**零 API 消耗**。
#: 注意：`--channel` 此前**只是个打印标签**（实测 `chan` 只出现在输出那一行里，
#: 路由完全无视它）——已改为真正生效的开关。
_CLOUD_DISABLED = False


def cloud_disabled() -> bool:
    return _CLOUD_DISABLED


#: **巨型文档跳过阈值（页）**（2026-09-15 用户指令）。
#: 用户原话：「像这种巨型文档过于长的，不利于我们快速迭代、快速寻找问题、
#: 快速进化的这个路径的文档可以直接跳过，寻找正常尺寸的去进行识别和参与循环就好」。
#:
#: **为什么是 200**：这正是云服务的页数硬限（实测 241 页文档报
#: `number of pages exceeds limit (200 pages)`）。超过它意味着：
#:   ① 云**必然**拒绝（连试都不用试，白等一次超时）；
#:   ② 只能走本地 VLM，而本地实测极慢——346 页用 8114s（135 分钟）、
#:      369 页用 4617s（77 分钟）、408 页单部 1 小时以上；
#:   ③ 本地 VLM 是**串行 GPU 独占**，一部巨文档就把整批推进钉住数小时。
#: 三者叠加 = 循环速度的毒药：500 部/批的节奏被 5–7 部巨型文档拖成十几小时。
#: 跳过后它们**记入 `vlm_oversize_skipped.json`**（不丢账），需要时可按清单补跑。
OVERSIZE_PAGES = 200


def oversize_skip_enabled() -> bool:
    return OVERSIZE_PAGES > 0


def _guard_single_instance(corpus_hint: str, wait_s: float | None = None) -> bool:
    """**单实例闸门**：同一时刻只允许一个 `vlm_ocr` 在跑。抢不到返回 False。

    锁文件用 `os.open(O_CREAT|O_EXCL)` 原子创建做互斥；已有锁且持有者 pid
    仍活着 → **等待锁释放**（最长 `LOCK_WAIT_S`），超时才放弃；持有者已死
    → 接管（被杀/崩溃留下的陈旧锁必须能接管，否则闸门永久堵死）。

    **为什么必须有**（2026-09-15 实测，会把整批拖死）：
    `commit_rec` 是 `state[key] = rec; save_json(STATE, state)` —— **整体读改写、
    无跨进程锁**。两个实例并发跑同一批时，后写者用**自己启动时的旧快照**覆盖
    已落盘记录：前者的完成记录被抹掉（重启后重复提交、重复烧云额度），实测批次 3
    还出现**双方都卡在 8/500、日志数分钟不动、CPU 30 秒只涨 0.7 秒**的僵局。
    当时 driver 每 20 秒重拉一次，正是双实例的来源（根因已在 driver 侧用
    `START_GRACE_S` 修掉；本闸门是**第二道**，防 watchdog/driver 之外的重复拉起）。

    判活只用 **pid 存活**，用锁文件的**存在性本身**做互斥：`os.open(O_CREAT|O_EXCL)`
    是原子创建，两个进程同时抢只有一个能成功。**不用心跳过期判活**——本地 VLM
    单部可达 52 分钟（实测 241 页 `wall_s=3129`），任何心跳阈值都会误杀正在
    正常工作的长文档（watchdog 那次踩的就是这个坑）。
    进程被杀/崩溃留下的陈旧锁：由 pid 判活放行（pid 已死即接管）。
    """
    lock = HERE / "vlm_ocr.lock"
    payload = json.dumps({"pid": os.getpid(), "ts_unix": time.time(),
                          "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                          "corpus": corpus_hint}, ensure_ascii=False)
    for attempt in (0, 1):
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, payload.encode("utf-8"))
            os.close(fd)
            if attempt:
                print("[单实例闸门] 已接管陈旧锁并继续", flush=True)
            return True
        except FileExistsError:
            try:
                obj = json.loads(lock.read_text(encoding="utf-8"))
                opid = int(obj.get("pid") or 0)
            except Exception:  # noqa: BLE001
                opid = 0
            if _pid_alive(opid):
                # **等一段时间再放弃**（2026-09-15 补）：driver 看到进程退出就会
                # 重新拉起（每 20 秒一次，最多 5 次）。若这里立刻退出，driver 的
                # 5 次机会会在 100 秒内耗尽 → 报"反复中断，待人工"，**整条推进链
                # 静默停住**（而真正在跑的那个实例其实一切正常）。
                # 故在锁被占用时**等待锁释放**（最长 LOCK_WAIT_S），让 driver 的
                # 每次重启都变成一次"等着接手"的机会；期间真在跑的实例不受影响。
                wait_s = LOCK_WAIT_S if wait_s is None else wait_s
                print(f"[单实例闸门] 已有 vlm_ocr 在跑（pid={opid}，"
                      f"corpus={obj.get('corpus') if isinstance(obj, dict) else '?'}"
                      f"）→ 本进程等待锁释放（最长 {wait_s:.0f}s）", flush=True)
                t0 = time.time()
                while time.time() - t0 < wait_s:
                    time.sleep(10.0)
                    try:
                        cur = json.loads(lock.read_text(encoding="utf-8"))
                        cur_pid = int(cur.get("pid") or 0)
                    except Exception:  # noqa: BLE001
                        cur_pid = 0
                    if cur_pid != opid or not _pid_alive(opid):
                        print("[单实例闸门] 锁已释放 → 接管", flush=True)
                        break
                else:
                    print(f"[单实例闸门] 等待 {wait_s:.0f}s 后锁仍被 pid={opid} 持有"
                          f"→ 本进程正常退出（避免双实例覆盖台账；"
                          f"若确认它卡死：先 Stop-Process，或删除 {lock.name} 后重试）",
                          flush=True)
                    return False
                continue                        # 锁已释放 → 重试抢锁
            print(f"[单实例闸门] 陈旧锁（pid={opid} 已死）→ 接管", flush=True)
            try:
                lock.unlink()
            except OSError:
                pass
            continue                        # 重试一次抢锁
        except OSError as ex:
            print(f"[单实例闸门] 锁文件不可用（{type(ex).__name__}: {ex}）→ 放行",
                  flush=True)
            return True
    return False


def _clear_lock() -> None:
    """释放锁（仅当锁属于本进程——避免清掉接管者的锁）。"""
    lock = HERE / "vlm_ocr.lock"
    try:
        obj = json.loads(lock.read_text(encoding="utf-8"))
        if int(obj.get("pid") or 0) == os.getpid():
            lock.unlink()
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    args = sys.argv[1:]
    if "--status" in args:
        from src.core.ingestion.mineru_cloud import _model_version
        st = {k: v for k, v in load_json(STATE, {}).items() if k not in _ALIAS_KEYS}
        c: dict[str, int] = {}
        for v in st.values():
            c[str(v.get("status"))] = c.get(str(v.get("status")), 0) + 1
        ok_n = c.get("ok", 0) + c.get("textlayer", 0)
        # **口径必须分桶**（2026-09-15 修）：原来一律 `总数-ok = 失败`，
        # 把"云侧超时待重做"、"巨型跳过"、"试满上限待人工"全算成"失败"，
        # 于是一个健康推进的批次看起来像"失败 58 部"（实测），
        # 而真正需要人管的只有待人工那一桶。
        print(f"已处理 {ok_n} 部 · 待重做 {c.get('pending-local', 0)}"
              f" · 待人工 {c.get('needs-human', 0)}"
              f" · 失败 {c.get('failed', 0)}"
              f" · 巨型跳过 {c.get('skipped-oversize', 0)}"
              f" / 共 {len(st)} 条")
        print(f"今日云文件已用 {cloud_files_today()}/{DAILY_CLOUD_FILES} 个")
        print(f"KS_VLM_ONLY={os.environ.get('KS_VLM_ONLY')} · 云版本={_model_version()}")
        return
    if "--rebuild-state" in args:
        # 由 append-only 日志重建断点记账（合并式，不丢 state 里的新条目）。
        # 用途：键护栏上线前被别名覆盖的那批已完成部数，靠日志无损补回，
        # 避免重启后白重做（云配额与时间都是真成本）。
        st = load_json(STATE, {})
        before = len(st)
        bak = STATE.with_suffix(f".json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        if STATE.exists():
            shutil.copy2(STATE, bak)
        n_add, n_prune = recover_state(st, LOG, set(_ALIAS_KEYS))
        if n_add or n_prune:
            save_json(STATE, st)
        ok_n = sum(1 for v in st.values() if v.get("status") in ("ok", "textlayer"))
        print(f"state 重建：{before} → {len(st)} 条（回补 {n_add} · 剪除别名键 "
              f"{n_prune}，其中 ok/textlayer {ok_n} 部）")
        print(f"  备份：{bak.name if bak.exists() else '（state 不存在，未备份）'}")
        return
    if "--set-used" in args:
        set_cloud_files_used(int(args[args.index("--set-used") + 1]))
        print(f"今日云文件用量已校准为 {cloud_files_today()} 个")
        return

    n = int(args[args.index("--docs") + 1]) if "--docs" in args else 3
    chan = args[args.index("--channel") + 1] if "--channel" in args else "auto"
    # `--channel local`：**不提交任何云任务**（用户要求"本地跑着、等谷价再走 API"）。
    global _CLOUD_DISABLED
    _CLOUD_DISABLED = (chan.strip().lower() == "local")
    root = args[args.index("--pdf-root") + 1] if "--pdf-root" in args else ""
    clist = args[args.index("--corpus-list") + 1] if "--corpus-list" in args else ""
    reset = "--reset" in args
    force = "--force-ocr" in args
    #: `--ocr-textlayer`：文本层**缺字形**（PUA）的文档强制走像素 OCR。
    #: 与 `--force-ocr` 的区别：后者只覆盖"跳过决策"，仍**保留** blocks.json →
    #: 链路优先命中 blocks，OCR 产物白跑（实测 `_cached_parse_result` 先 blocks
    #: 后 middle）；本开关把 blocks 一起留档，产物才真正切到 VLM。
    force_tl = "--ocr-textlayer" in args
    c_to = float(args[args.index("--cloud-timeout") + 1]) \
        if "--cloud-timeout" in args else 900.0
    c_at = int(args[args.index("--cloud-attempts") + 1]) \
        if "--cloud-attempts" in args else 2
    #: 并发度：**这个才是吞吐的瓶颈**（额度 5000 文件/日远大于串行器能吃的量）。
    #: 实测单个云任务会卡住（30 分钟无结果），串行时它阻塞全体；并发下互不阻塞。
    par = int(args[args.index("--parallel") + 1]) if "--parallel" in args else 1
    lock_wait = (float(args[args.index("--lock-wait") + 1])
                 if "--lock-wait" in args else None)
    # **单实例闸门必须在读 state 之前**（见 _guard_single_instance 注释）：
    # 双实例不只是浪费额度，`recover_state` + `save_json` 的读改写也会互相覆盖。
    # 抢不到锁就**正常返回**（不是异常）：driver 看到"进程退出"会走它自己的
    # 等待/重拉逻辑；报非零反而会被当成"启动失败"而提前放弃。
    if not _guard_single_instance(clist or root or "db", lock_wait):
        return
    state = {} if reset else load_json(STATE, {})
    # 启动即自愈：日志是 append-only 的权威账本，state 缺失的部数由日志回补，
    # 保证「记账损坏 → 重启重做」这类静默浪费不会再发生（每次启动都修一次）。
    if not reset:
        healed, pruned = recover_state(state, LOG, set(_ALIAS_KEYS))
        if healed or pruned:
            save_json(STATE, state)
            print(f"[state 自愈] 由日志回补 {healed} 条 · 剪除历史别名键 {pruned} 个"
                  f"（现 {len(state)} 条）", flush=True)

    if clist:
        tg = targets_from_corpus_list(Path(clist), n)
    elif root:
        tg = targets_from_root(Path(root), n)
    else:
        tg = targets_from_db(n)
    pending = []
    #: 云**能力边界**（页数超限等，state 里 fatal=True）的文档：不提交云，
    #: 直接进本地队列（见下方待做判定注释）。它们在云阶段结束后与"云失败件"
    #: 一起串行跑本地 VLM。
    local_direct: list[dict] = []
    #: 本次被跳过的巨型文档（写台账 vlm_oversize_skipped.json）
    oversize: list[dict] = []
    skip = 0
    for t in tg:
        key = t["doc_id"] or t["std_no"]
        st = state.get(key) or {}
        s = st.get("status")
        # **只有 ok / textlayer 算做完**（2026-09-15 修正）。
        #
        # `pending-local` 分两种，**必须区别对待**（用户指令：云能用时优先云）：
        #   - `fatal=True`（云返回"页数超限"等**能力边界**）：云再试也不可能成功，
        #     直接进本次的本地队列，不浪费一个云提交 + 20 分钟超时等待；
        #   - 其余（云**拥塞**导致的超时）：**必须重试云**。早先的实现把它当"待本地"
        #     跳过云直接进本地队列，于是云恢复后这些文档仍被送去慢 20 倍的本地 GPU
        #     ——实测 40 部因拥塞落本地的文档，重试云全部 6 秒成功。
        if s in ("ok", "textlayer") and not reset:
            skip += 1
            continue
        if (s == "pending-local" and st.get("fatal") and not reset):
            # 巨型文档已在下方被跳过（不会走到这里，因为状态已是 skipped-oversize）
            local_direct.append(t)
            continue
        # **巨型文档直接跳过**（用户指令 2026-09-15，见 OVERSIZE_PAGES 注释）：
        # 页数 >200 = 云必拒 + 本地极慢（单部 1–2 小时且 GPU 独占串行）→
        # 会把整批推进钉住数小时，是循环速度的毒药。跳过并登记台账，不参与循环。
        if oversize_skip_enabled():
            pg = pages_of(t["pdf"])
            if pg > OVERSIZE_PAGES:
                # **先看盘上有没有现成产物**（用户指令 2026-09-15）：
                # 「本地已经 OCR 好了的、本地有文件的，你就直接用吧，就算他是巨型文件
                #   ……只有说未来要再次 OCR 的时候才跳过」。
                d = land_dir(t)
                if has_usable_product(d):
                    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "key": key,
                           "std_no": t["std_no"], "pages": pg, "pdf": str(t["pdf"]),
                           "channel": "reuse", "status": "ok", "wall_s": 0.0,
                           "out": str(d),
                           "msg": f"巨型文档（{pg} 页）但**盘上已有产物** → 直接复用，"
                                  f"不重新 OCR"}
                    commit_rec(state, rec)
                    continue
                # 无现成产物 → 需要重新 OCR → 按用户指令跳过（保循环速度）
                rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "key": key,
                       "std_no": t["std_no"], "pages": pg, "pdf": str(t["pdf"]),
                       "channel": "skipped", "status": "skipped-oversize",
                       "msg": f"巨型文档（{pg} 页 > {OVERSIZE_PAGES} 页）且**无现成产物**："
                              f"跳过以保循环速度；台账 vlm_oversize_skipped.json"}
                commit_rec(state, rec)
                oversize.append({"std_no": t["std_no"], "pages": pg,
                                 "pdf": str(t["pdf"]),
                                 "ts": rec["ts"]})
                continue
        pending.append(t)
    print(f"=== VLM OCR（KS_VLM_ONLY=1，pipeline 不参与）· 目标 {len(tg)} 部"
          f"（走云 {len(pending)}，云能力边界直入本地 {len(local_direct)}，"
          f"巨型跳过 {len(oversize)}，已完成 {skip}）· 通道 {chan}"
          f" · 并发 {par} · 今日云文件 {cloud_files_today()}/{DAILY_CLOUD_FILES} ===")
    ok = fail = 0
    par = max(1, par)
    from concurrent.futures import ThreadPoolExecutor

    # **两阶段：先云后本地**（2026-09-15 实测修正）。
    #
    # 缺陷：原实现把本地 VLM 兜底**嵌在 chunk 循环里**，而本地 VLM 是
    # **in-process 串行**（GPU 独占）。实测一个 241 页文档（超云 200 页硬限）
    # 把整个 chunk 钉住 20–40 分钟，**并发 4 的另外 3 个 worker 全在等它**——
    # 并行度被一个慢文档吞掉。逐批跑 35,243 部时这会成为主要瓶颈。
    #
    # 修法：云阶段保持并发、**只做云**；需要本地兜底的文档**收集到队列**，
    # 云阶段全部结束后**串行**跑本地 VLM。这样等待时间从"每 chunk 都被慢文档
    # 拖住"降到"只等一次"。
    local_queue: list[tuple[dict, dict]] = []
    # 云能力边界件**直接入本地队列**（不提交云）。先把状态落成 `pending-local`
    # （与云失败件同一状态），这样若进程中途被杀，下轮仍会按 fatal 分支直接入队，
    # 不会因为"无状态"而重新提交云、白等一次超时。
    for t in local_direct:
        k = t["doc_id"] or t["std_no"]
        rec = dict(state.get(k) or {})
        rec.update({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "key": k,
                    "std_no": t["std_no"], "pages": pages_of(t["pdf"]),
                    "pdf": str(t["pdf"]), "channel": "cloud",
                    "status": "pending-local", "fatal": True,
                    "model_version": "", "wall_s": 0.0,
                    "msg": "云能力边界（页数超限）：直接走本地 VLM，不提交云"})
        commit_rec(state, rec)
        local_queue.append((t, rec))
    if local_direct:
        print(f"[路由] {len(local_direct)} 部为云能力边界（页数超限）→ 直接本地，"
              f"不提交云（省一次 20 分钟超时等待）", flush=True)

    def _safe_stage(t: dict) -> dict:
        """**批次级安全网**：单部文档抛任何异常都不许杀掉整批。

        实测（2026-09-15）：`mineru_cloud_submit_and_wait` 对"页数超限"抛
        `MineruCloudError`，异常从工作线程穿出 ThreadPool —— **整个 500 部批次
        当场死亡**（只跑了 116 部）。用 VLM 跑 35,243 部，任何一部的问题文件
        都不该让批次归零；故此处兜住并转本地 VLM，同时把异常写进记录供取证。
        """
        if cloud_disabled():
            # 云闸门关闭：直接当"云能力边界"处理 → 进本地队列，零 API 调用。
            # ⚠ **`key` 必填**：这条记录会直接进 `commit_rec`，缺 key 会被键护栏抛
            # RuntimeError 并杀死整个 worker（见 `_safe_stage` 异常分支同样的注释）。
            return {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "key": t.get("doc_id") or t.get("std_no"),
                    "std_no": t.get("std_no"), "pages": t.get("pages"),
                    "pdf": str(t.get("pdf") or ""),
                    "channel": "local", "status": "failed", "fatal": True,
                    "msg": "云通道已关闭（--channel local）：直接走本地 VLM"}
        try:
            return cloud_stage(t, c_to, c_at, force, force_tl)
        except Exception as e:  # noqa: BLE001
            # ⚠ **`key` 必填**（2026-09-16 实测，崩过整批）：`commit_rec` 的键护栏会拒绝
            # 缺键记录并抛 `RuntimeError`，从 `main()` 穿出 → **整个 worker 死亡**。
            # 原先此处只写 channel/status/msg，而 429 限流让这条异常路径变成常态，
            # 于是"异常被兜住了"变成"整批崩掉"（实测 `vlm_batch7.err`）。
            #
            # ❗**`fatal` 不能一律为 True**（2026-09-16 实测，同类缺陷第三次）：
            # `fatal=True` 的含义是"云再试也不可能成功 → 转本地 VLM"，而本地比云
            # **慢约 20 倍且串行独占 GPU**。实测 34 条 `PermissionError`
            # （`WinError 32 另一个程序正在使用此文件` / `Errno 13 Permission denied`，
            # 两台 worker 重启时争同一目录造成）被一律标成 fatal → 又要白烧数十分钟 GPU。
            # **临时文件占用重试即可**，与"云能力边界"毫无关系。
            # 故：只有**明确的不可重试**异常才标 fatal；其余落 `failed`（不设 fatal）→
            # 由 `_requeue_cloud_failures` / `_carry_over` 带进下一批重做。
            _retryable = isinstance(e, (PermissionError, OSError, TimeoutError,
                                        ConnectionError))
            return {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "key": t.get("doc_id") or t.get("std_no"),
                    "std_no": t.get("std_no"), "pages": pages_of(t["pdf"]),
                    "pdf": str(t.get("pdf") or ""),
                    "channel": "cloud", "status": "failed",
                    "fatal": not _retryable,
                    "msg": (f"云阶段异常（{'可重试' if _retryable else '不可重试'}）"
                            f"{type(e).__name__}: {str(e)[:150]}")}

    # **单流并行**（恢复为已验证的实现）。
    #
    # **为什么放弃"多 key 并行"**（2026-09-15 实测，用户提问引发的调查）：
    #   ① 干净对照显示**没有 per-key 限速**——同一组 8 部文档、每 key 并发 4：
    #      `project` 11.6s、`loop2` 11.5s，两 key 表现完全一致（8/8 全成，单部 ~6s）。
    #      故"分散到多 key"不会提升吞吐。
    #   ② 进程内**无法安全实现**：`use_key()` 写的是**全局 settings 属性**，而
    #      `mineru_cloud` 在函数入口用 `_resolve_settings()` 读它。多线程各写各的
    #      → 谁最后写谁生效：实测分组跑了 12 部，**全部落在 project**（state 里
    #      `cloud_key=project` ×4、loop2/loop3 一次都没成功），属"看似并行、实则单 key"。
    #      要真并行必须改成"每 key 一进程 + 文档分片 + 台账分片"（大改，收益为零）。
    #   ③ 之前那个"三 key 均分快 88%"的观测**不可信**——同一竞态使 12 部可能全落在
    #      同一 key，差异来自**文档本身**而非 key。
    # 结论：**保留单流 + 失败换 key 重试**（key 在失败路径上轮换，那条路径是串行的、
    # 无竞态）。三 key 的价值在于**容灾与额度兜底**（各 5000/日），不是并行提速。
    # **流水线调度**（2026-09-15 实测修正，替换"分块+块屏障"）：
    #
    # 缺陷：分块实现里 `with ThreadPoolExecutor(...)` 的 `__exit__` 会**等整块跑完**，
    # 于是每个"块屏障"都让 8 个 worker 空转等最慢的那一部。实测批次 5 的成功文档
    # 耗时分布：中位 28.6s、均值 51.5s、**最大 215s**（`>240s` 的为 0——说明超时
    # 设得正确，没有误杀正常文档）。也就是说：**慢的那 10 部（>180s）会把整块
    # 拖到 3–4 分钟**，而其余 7 部早在 30 秒内就好了、却必须空等。
    #
    # 改法：所有文档**同时**提交给一个固定 `par` 并发的池子，**谁完成就立刻补下一部**
    # （`as_completed` 顺序处理）→ 没有任何块屏障，worker 全程满载。
    # state 落盘仍在**主线程**（worker 只回传 rec），避免引入台账竞态。
    from concurrent.futures import as_completed
    total_pending = len(pending)
    for j, t in enumerate(pending, 1):
        print(f"[{j}/{total_pending}] {t['std_no'][:30]:<32} "
              f"{pages_of(t['pdf']):>3}页 云VLM…", flush=True)
    _exec_inline = par > 1
    # **超时事件标志**（在分支外定义，两个分支与收尾处都要读）：
    # 只有真的发生过整体超时，才在收尾时放弃等待卡死线程——`wait=True` 会把
    # "带超时的消费"重新变成永久阻塞，修复就白做了。用 `list` 当可变单元。
    _timed_out = [False]
    if par <= 1:
        _recs_iter = [(t, _safe_stage(t)) for t in pending]
    else:
        # **必须在 `with` 内消费 `as_completed`**（2026-09-15 修正）：写成
        # `[(t, fu.result()) for fu in as_completed(...)]` 会把整个列表先算完，
        # 等于**又等了一次全部完成**——流水线白做。语义差别在这里：
        # 逐个取结果 → 主线程**立刻落盘该部**、worker 立刻补下一部；
        # 一次性取完 → 所有落盘都退到批末。
        ex = ThreadPoolExecutor(max_workers=par)
        _fut2doc = {ex.submit(_safe_stage, t): t for t in pending}
        # **`fu.result()` 必须带超时**（2026-09-16 实测缺陷，见下）。
        #
        # 缺陷现场：批次 7（`--parallel 24`）跑到 `00:45:20` 后 **状态文件 16 分钟零字节
        # 增长**、日志几乎不动，而进程 CPU 仍在烧（60s 内 +11.9s）、27 线程、只有 3 条
        # established 连接（24 个 worker 若都在轮询 HTTP 应有 ~24 条）→ 线程卡在**本地**，
        # 不是云侧轮询。此时 `as_completed` 一个结果都交不出来 → 主线程永久阻塞在
        # `fu.result()` → **剩余 476 部连提交都不会发生**（测到 62 部就再无产出）。
        #
        # 为什么单部超时不够：`mineru_cloud_submit_and_wait` 有 240s deadline，但它只在
        # **轮询循环**里检查；线程若卡在 connect/连接复用/重连路径（httpx `timeout=120`）
        # 之外，deadline 管不到 → 该 future 可以永远不返回。
        # 故在主线程侧再加一道**兜底**：超时即把该部记为可重做（`failed` +
        # `channel=cloud`，由 `_requeue_cloud_failures`/`_carry_over` 带进下一批重投），
        # **并继续消费后续 future**——绝不让一部文档钉死整批。
        # 超时值取云端预算 ×1.6：健康文档实测最大 215s、预算 240s，故不会误杀正常文档。
        _fut_wait = c_to * c_at * 1.6

        def _iter_done(fmap: dict, wait_s: float):
            """带超时的 `as_completed` 消费器；超时项按"可重做失败"产出。

            `_timed_out` 在上面**分支外**定义（两个分支与收尾处都要读），
            此处**不得再定义一次**——否则闭包写的是内层对象、外面读的是外层，
            标志永远为 False，收尾就会照旧 `wait=True` 永久阻塞（实测踩过）。
            """
            from concurrent.futures import TimeoutError as _FTimeout

            def _fallback_rec(t: dict, why: str, **extra) -> dict:
                """给"没能走到 `cloud_stage`"的文档造一条**完整**记录。

                ⚠ **必须有 `key`**（2026-09-16 实测，崩过整批）：`commit_rec` 的键护栏
                要求记录键是**文档键**（不是云账号别名），缺失即 `RuntimeError`。
                原先的超时/异常分支只写 `status/channel/msg` → 主线程一落盘就抛
                `! 状态键非法=None（std_no=None）`，**整个 worker 当场死亡**
                （实测 `vlm_batch7.err` 末尾就是这个 traceback，批 7 的 worker 死在
                `main()` 的 `commit_rec`）。这是**预先存在的缺陷**：`_safe_stage` 的
                except 分支（"云阶段异常"）同样缺 `key`，任何云阶段异常都会崩 worker；
                429 限流成为常态后才把它暴露出来。
                """
                return {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "key": t.get("doc_id") or t.get("std_no"),
                        "std_no": t.get("std_no"), "pages": t.get("pages"),
                        "pdf": str(t.get("pdf") or ""),
                        "channel": "cloud", "status": "failed",
                        "msg": why, **extra}

            try:
                it = as_completed(fmap, timeout=wait_s)
                for fu in it:
                    try:
                        yield fmap[fu], fu.result()
                    except Exception as e:  # noqa: BLE001 —— worker 内异常也不许杀批
                        yield fmap[fu], _fallback_rec(
                            fmap[fu], f"云阶段异常 {type(e).__name__}: {str(e)[:120]}")
            except _FTimeout:
                # **超时不再等于整批停摆**：把还没返回的都标成可重做，然后收尾走人。
                _timed_out[0] = True
                stuck = [f for f in fmap if not f.done()]
                print(f"❗云阶段 {len(stuck)}/{len(fmap)} 部超过 {wait_s:.0f}s 未返回"
                      f"（单部已超云端预算）→ 记为可重做，本批不再等它们",
                      flush=True)
                for f in stuck:
                    _t = fmap[f]
                    yield _t, _fallback_rec(
                        _t,
                        f"云阶段整体超时（{wait_s:.0f}s 未返回）：线程疑似卡在连接层，"
                        f"已记为可重做，下批重投",
                        # `_abandoned_keys` 供主线程把"被我放弃的文档键"登记进 `_abandoned`，
                        # 这样那个线程**迟到返回时不会覆盖**已判记录（见主循环注释）。
                        _abandoned_keys=[_t.get("doc_id") or _t.get("std_no")])
                for f in fmap:
                    f.cancel()          # 未开始的可取消；已跑完的忽略

        _recs_iter = _iter_done(_fut2doc, _fut_wait)
    if True:                      # 保持下方缩进结构不变（见上方注释的流水线说明）
        _abandoned: set[str] = set()   # 已被判"可重做"的文档键（防迟到者覆盖）
        for t, rec in _recs_iter:
            _k = t.get("doc_id") or t.get("std_no")
            # 超时分支产出的记录自带 `_abandoned_keys`：先登记，再按普通失败落盘。
            for _ak in (rec.pop("_abandoned_keys", None) or []):
                _abandoned.add(_ak)
            # **迟到结果不许覆盖已判记录**（2026-09-16）：超时后我们把卡住项写成
            # `failed`（可重做），而那个线程稍后**可能真的返回 ok**。若不拦，它会
            # 把记录改回 ok 并计一次成功——但 driver 早已按 failed 计入残留、
            # `_carry_over` 也会再带一遍 → 同一部被重复处理、口径串味。
            # 故：已被放弃的键，其迟到的结果**只记日志、不落盘**。
            if _k in _abandoned:
                print(f"    ↳ 迟到结果已忽略（{_k} 先前判为可重做）: "
                      f"{str(rec.get('status'))}", flush=True)
                continue
            if rec.get("status") == "ok":
                add_cloud_files(1)
            if rec.get("status") == "failed":
                if rec.get("fatal"):
                    # 云**能力边界**（页数超限等）：云再试也好不了 → 排队走本地
                    print(f"    ↳ {str(rec.get('msg'))[:60]} → 排队等本地 VLM",
                          flush=True)
                    # **落盘状态必须是 pending-local，不能是 failed**（2026-09-15 修正）：
                    # 本地 VLM 兜底在**批次末尾串行跑**才更新这条记录，而此间进程可能
                    # 被杀（停滞自愈会 kill；崩溃、断电同理）。若此处写 failed，
                    # 那些文档就变成**终态失败**，下次启动 `status=="ok"` 跳过判据
                    # 之外的 failed 条目**不会被重做** → 内容永久缺口，
                    # 而 driver 的 `done+failed>=total` 还会把这批判成"已完成"。
                    rec["status"] = "pending-local"
                    local_queue.append((t, rec))
                    commit_rec(state, rec)
                    continue            # 末尾本地跑完再更新为 ok/failed
            commit_rec(state, rec)
            if rec.get("status") in ("ok", "textlayer"):
                ok += 1
            else:
                fail += 1
        if _exec_inline:
            # 发生过整体超时 → 放弃等待卡死线程（否则永久阻塞，修复失效）；
            # 否则正常回收（`shutdown` 对已全部消费完的池子是立即返回的）。
            ex.shutdown(wait=not _timed_out[0])

    if local_queue:
        print(f"\n=== 云阶段结束：{len(local_queue)} 部需本地 VLM（串行，GPU 独占）===",
              flush=True)
        for n, (t, rec) in enumerate(local_queue, 1):
            print(f"[本地 {n}/{len(local_queue)}] {t['std_no'][:34]}", flush=True)
            rec = local_stage(t, rec)
            commit_rec(state, rec)
            if rec.get("status") in ("ok", "textlayer"):
                ok += 1
            else:
                fail += 1

    if oversize:
        led = HERE / "vlm_oversize_skipped.json"
        try:
            cur = json.loads(led.read_text(encoding="utf-8")) if led.exists() else {}
        except Exception:  # noqa: BLE001
            cur = {}
        for o in oversize:
            cur[o["std_no"]] = o
        led.write_text(json.dumps(cur, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"[巨型跳过] {len(oversize)} 部已记入 {led.name}"
              f"（累计 {len(cur)} 部）", flush=True)
    print(f"\n完成：ok={ok} fail={fail} skip={skip} "
          f"巨型跳过={len(oversize)} "
          f"· 今日云文件 {cloud_files_today()}/{DAILY_CLOUD_FILES} 个")
    _clear_lock()


def _install_exit_diagnostics() -> None:
    """装"死因取证"仪表（2026-09-16 立）。

    **为什么需要**（HANDOFF §10.23）：批 8 观测到 worker **静默消失**两次——
    `.log`/`.err` 都在同一条超时消息处戛然而止、**无 traceback**、driver 与
    watchdog 都未杀它。没有留痕，只能靠推测；本函数把"它为何退出"落到磁盘。

    三个通道（互补，都只写文件、不改业务流程）：
      1. **`atexit`**：正常退出/`SystemExit` 会走到 → 记 ISO 时间、pid、退出码来源。
         静默死亡若**没有**这条记录 → 说明进程是被**外部强杀**（TerminateProcess
         不走 atexit），这是区分"自行退出"与"被杀"的关键判据。
      2. **`faulthandler.enable()`**：段错误/C 层崩溃会打印原生栈到 `diagnostics.log`。
      3. **`faulthandler.dump_traceback_later(…, repeat=True)`**：进程若长时间不退出，
         周期性把**全部线程的 Python 栈**写进同一文件 —— 降级窗口内"24 线程全在
         长轮询"的现场可直接看到（这是 §10.23 最需要的证据）。

    ⚠ 刻意不装 SIGTERM/SIGINT 处理器：Windows 上强杀通常不可捕获，
    装了反而会让人误以为"没记录=没被杀"。
    """
    import atexit
    import faulthandler
    from datetime import datetime

    diag = HERE / "worker_diagnostics.log"

    def _stamp(why: str) -> None:
        try:
            with diag.open("a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat(timespec='seconds')}] "
                        f"pid={os.getpid()} {why}\n")
        except Exception:  # noqa: BLE001 —— 取证失败不许影响主流程
            pass

    _stamp("START")
    atexit.register(_stamp, "ATEXIT（正常退出 / SystemExit —— 若某次死亡缺这一行，"
                            "说明进程是被外部强杀）")
    try:
        fh = diag.open("a", encoding="utf-8")
        faulthandler.enable(file=fh)
        # 每 10 分钟 dump 一次全部线程栈：降级窗口内"24 线程卡在长轮询"可直读
        faulthandler.dump_traceback_later(600, repeat=True, file=fh)
        _stamp("faulthandler 已启用（崩溃打原生栈；每 600s dump 全线程 Python 栈）")
    except Exception as e:  # noqa: BLE001
        _stamp(f"faulthandler 启用失败：{type(e).__name__}: {e}")


if __name__ == "__main__":
    _install_exit_diagnostics()
    main()
