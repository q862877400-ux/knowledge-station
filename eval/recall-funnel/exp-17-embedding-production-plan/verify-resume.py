"""exp-17 · 断点续跑 / 幂等 / 口径的**验证脚本**（读数落 `result.json`）。

五项（每项都对应一个"看起来对但其实是坏"的失败模式）：

| # | 验什么 | 失败模式 | 判据 |
|---|---|---|---|
| T1 | 一次跑完 vs 中断续跑，**逐行（id + 2048 B 向量）完全一致** | 续跑从错误的游标接着算 ⇒ 漏条/重条/错位，而行数看起来一样 | 逐行 bytes 相等 + 行数相等 |
| T2 | **真强杀**（`Popen.terminate()`，不是干净退出）后续跑，仍与一次跑完逐行一致 | 只在"批次边界干净退出"下才对 ⇒ 真实强杀会留下半批 | 同上 |
| T3 | 对已完成的库**原样重跑**：写入 0 条、行内容不变（幂等） | 重跑把所有向量重算一遍（浪费 GPU）或 `INSERT OR REPLACE` 改了字节 | `rows_written == 0` 且全表哈希不变 |
| T4 | **真模型口径**：用本脚本的嵌入函数重算 64 条，与 E4 已冻结的 `clause_vec_qwen`（`exp-4` 的 `exp.db`）**逐字节相同** | 模型加载/池化/截断/归一化/序列化 任一处抄错 ⇒ 新表与 E4 量过的那张表不是同一个东西 | 64/64 字节相等 |
| T5 | **真库一行没动**（mtime + 两张表行数前后一致） | 脚本"只读"只是口头承诺 | mtime 与计数都不变 |

⚠ T4 的对照物是 **E4 第一轮的产物**，按本仓纪律（第 13/14 轮教训）"仪器对照的参照物必须是
同期重跑"—— 这里**是例外且理由要说清**：T4 不是"复现某个名次读数"，而是**验证嵌入函数的字节级
口径**；`exp.db` 是**冻结输入**（corpus 也是冻结的 521,978 条），重算同一个冻结输入**本来就该逐字节相同**。
若哪天 `exp.db` 被改动，T4 会红 —— 那正是它该红的时候。

用法：
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-17-embedding-production-plan\\verify-resume.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

EXP4_DB = ROOT / "eval" / "recall-funnel" / "exp-4-embedding-shadow" / "exp.db"
WORK = ROOT / "var" / "tmp" / "exp-17"
SOURCE = Path(os.environ.get("APPDATA", "")) / "KnowledgeStation" / "database" / "knowledge.db"
SCRIPT = HERE / "rebuild-shadow.py"
OUT_JSON = HERE / "result.json"

N_SMALL = 300        # T1/T3 的规模
N_KILL = 20_000      # T2 的规模（要跑得够久，好在中途强杀）
N_REAL = 64          # T4 的规模


def _load_mod():
    spec = importlib.util.spec_from_file_location("rebuild_shadow", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _rows(path: Path) -> dict[str, bytes]:
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    assert load_vec_extension(c), "sqlite-vec 加载失败"
    try:
        return {r[0]: r[1] for r in c.execute("SELECT clause_revision_id, embedding FROM clause_vec_qwen")}
    finally:
        c.close()


def _table_digest(rows: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for k in sorted(rows):
        h.update(k.encode())
        h.update(rows[k])
    return h.hexdigest()


def _py(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def _db_fingerprint() -> dict:
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{SOURCE.as_posix()}?mode=ro", uri=True)
    assert load_vec_extension(c)
    try:
        return {"mtime": SOURCE.stat().st_mtime, "size": SOURCE.stat().st_size,
                "clause_vec": c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0],
                "clause_revision": c.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]}
    finally:
        c.close()


def t1_resume_equals_oneshot(mod, log) -> dict:
    one, two = WORK / "t1-one.db", WORK / "t1-two.db"
    for p in (one, two):
        for suf in ("", "-wal", "-shm"):
            f = Path(str(p) + suf)
            if f.exists():
                f.unlink()
    log("T1 · 一次跑完 …")
    a = mod.run(SOURCE, one, limit=N_SMALL, batch=16, commit_every=5,
                embedder=_fake(mod))
    log("T1 · 跑到 5 批就停，再续跑 …")
    b = mod.run(SOURCE, two, limit=N_SMALL, batch=16, commit_every=5,
                stop_after_batches=5, embedder=_fake(mod))
    c = mod.run(SOURCE, two, limit=N_SMALL, batch=16, commit_every=5, embedder=_fake(mod))
    r1, r2 = _rows(one), _rows(two)
    diff = [k for k in set(r1) | set(r2) if r1.get(k) != r2.get(k)]
    return {"one_shot_rows": len(r1), "resumed_rows": len(r2),
            "partial_after_stop": b["shadow_rows"], "resume_wrote": c["rows_written"],
            "n_diff": len(diff), "diff_sample": diff[:5],
            "identical": (len(r1) == len(r2) == N_SMALL and not diff),
            "one_shot_digest": _table_digest(r1), "resumed_digest": _table_digest(r2)}


def t2_real_kill(mod, log) -> dict:
    one, three = WORK / "t2-one.db", WORK / "t2-kill.db"
    for p in (one, three):
        for suf in ("", "-wal", "-shm"):
            f = Path(str(p) + suf)
            if f.exists():
                f.unlink()
    log(f"T2 · 一次跑完 {N_KILL} 条（假嵌入）…")
    a = mod.run(SOURCE, one, limit=N_KILL, batch=8, commit_every=10, embedder=_fake(mod))
    log(f"T2 · 起子进程跑 {N_KILL} 条，中途 terminate() 强杀 …")
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--out", str(three), "--limit", str(N_KILL),
         "--batch", "8", "--commit-every", "10", "--fake-embed"],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    killed_at = 0
    deadline = time.time() + 120
    while time.time() < deadline:
        time.sleep(0.05)
        if proc.poll() is not None:      # 跑完了 ⇒ 杀不到，本项作废（不许读成"通过"）
            killed_at = -1
            break
        try:
            from src.core.storage.sqlite_db import load_vec_extension
            cc = sqlite3.connect(f"file:{three.as_posix()}?mode=ro", uri=True)
            load_vec_extension(cc)
            killed_at = cc.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
            cc.close()
        except Exception:
            killed_at = 0
        if killed_at >= 2000:
            break
    if killed_at >= 0:
        proc.terminate()
    try:
        proc.wait(timeout=20)
    except Exception:
        proc.kill()
    log(f"T2 · 强杀时已落盘 {killed_at} 行；续跑到 {N_KILL} …")
    if killed_at <= 0:
        return {"killed_at": killed_at, "identical": False,
                "note": "⛔ 没能在中途杀到 ⇒ 本项【未验证】（不许读成通过）"}
    c = mod.run(SOURCE, three, limit=N_KILL, batch=8, commit_every=10, embedder=_fake(mod))
    r1, r3 = _rows(one), _rows(three)
    diff = [k for k in set(r1) | set(r3) if r1.get(k) != r3.get(k)]
    return {"killed_at": killed_at, "one_shot_rows": len(r1), "resumed_rows": len(r3),
            "resume_wrote": c["rows_written"], "n_diff": len(diff), "diff_sample": diff[:5],
            "identical": (len(r1) == len(r3) == N_KILL and not diff)}


def t3_idempotent(mod, log) -> dict:
    one = WORK / "t1-one.db"
    before = _rows(one)
    log("T3 · 对已完成的库原样重跑 …")
    r = mod.run(SOURCE, one, limit=N_SMALL, batch=16, commit_every=5, embedder=_fake(mod))
    after = _rows(one)
    return {"rows_written_on_rerun": r["rows_written"], "rows_before": len(before),
            "rows_after": len(after),
            "digest_before": _table_digest(before), "digest_after": _table_digest(after),
            "idempotent": (r["rows_written"] == 0 and _table_digest(before) == _table_digest(after))}


def t4_real_model_bytes(mod, log) -> dict:
    """用本脚本的嵌入函数重算 N_REAL 条，与 E4 冻结的 `clause_vec_qwen` 比对。

    **两条读数，缺一不可**（第一版只做 B，报 16/64 ⇒ 差点被读成"口径抄错了"）：

    · **A 复刻 E4 的分批**（非空正文 + `ORDER BY rowid`，每批 16）⇒ 期望 **逐字节相同**。
      这才是"口径一致"的判据。
    · **B 换一种分批**（把同一批 64 条一次喂进去）⇒ 期望**不**逐字节相同，差在 **fp16 的
      批不变性**上：cuBLAS 对不同 batch/序列长度会挑不同 kernel，累加顺序不同 ⇒ 末位差
      ~1e-4。B 的读数用来**证明这不是口径错误**（余弦仍 ≈1）。
    """
    from src.core.storage.sqlite_db import load_vec_extension
    import array
    import math

    if not EXP4_DB.exists():
        return {"available": False, "note": "exp-4/exp.db 不在（5.7 GB，不入库）⇒ 本项未验证"}
    c = sqlite3.connect(f"file:{EXP4_DB.as_posix()}?mode=ro", uri=True)
    assert load_vec_extension(c)
    try:
        rows = c.execute(
            "SELECT clause_revision_id, title, content_text FROM clause_revision"
            " WHERE trim(coalesce(content_text,'')) <> '' ORDER BY rowid LIMIT ?",
            (N_REAL,)).fetchall()
        ids = [r[0] for r in rows]
        ph = ",".join("?" * len(ids))
        frozen = {r[0]: r[1] for r in c.execute(
            f"SELECT clause_revision_id, embedding FROM clause_vec_qwen"
            f" WHERE clause_revision_id IN ({ph})", ids)}
    finally:
        c.close()
    missing = [i for i in ids if i not in frozen]
    if missing:
        return {"available": True, "n": len(ids), "n_missing_in_e4": len(missing),
                "all_identical": False, "note": "抽样 id 不在 E4 表里 ⇒ 本项不成立"}

    log(f"T4 · 真模型重算 {len(ids)} 条（A 复刻 E4 分批 16 / B 单批全量）…")
    emb = mod.real_embedder_factory()
    t0 = time.perf_counter()
    got_a: list[list[float]] = []
    for i in range(0, len(rows), 16):                       # A：E4 的批次边界
        chunk = rows[i:i + 16]
        got_a.extend(emb([mod.display_text(r[1], r[2]) for r in chunk]))
    el_a = time.perf_counter() - t0
    t0 = time.perf_counter()
    got_b = emb([mod.display_text(r[1], r[2]) for r in rows])  # B：同一批 64 条
    el_b = time.perf_counter() - t0

    def _cmp(got):
        n_ok = 0
        cos_min, d_max = 1.0, 0.0
        for i, v in zip(ids, got):
            f = array.array("f"); f.frombytes(frozen[i])
            if array.array("f", v).tobytes() == frozen[i]:
                n_ok += 1
            nv = math.sqrt(sum(x * x for x in v)) or 1.0
            nf = math.sqrt(sum(x * x for x in f)) or 1.0
            cos_min = min(cos_min, sum(a * b for a, b in zip(v, f)) / (nv * nf))
            d_max = max(d_max, max(abs(a - b) for a, b in zip(v, f)))
        return n_ok, cos_min, d_max

    ok_a, cos_a, d_a = _cmp(got_a)
    ok_b, cos_b, d_b = _cmp(got_b)
    norms = [sum(x * x for x in v) ** 0.5 for v in got_a]
    return {"available": True, "n": len(ids),
            "A_batch_matched_identical": ok_a, "A_all_identical": ok_a == len(ids),
            "A_cos_min": round(cos_a, 10), "A_maxdiff": d_a, "A_embed_s": round(el_a, 2),
            "B_single_batch_identical": ok_b, "B_cos_min": round(cos_b, 10),
            "B_maxdiff": d_b, "B_embed_s": round(el_b, 2),
            "dims": sorted({len(v) for v in got_a}),
            # fp16 ⇒ 范数只能到 ~1e-4 量级（不是 fp32 的 1e-7）；阈值取 1e-3
            "l2_norm_min": round(min(norms), 6), "l2_norm_max": round(max(norms), 6),
            "l2_normalized": all(abs(n - 1.0) < 1e-3 for n in norms),
            "note": "A 是口径判据；B 的差异是 fp16 批不变性（cuBLAS kernel 选择），不是口径错误"}


def _fake(mod):
    e = mod.fake_embedder_factory()
    e._is_fake = True
    return e


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    mod = _load_mod()
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        lines.append(msg)

    fp_before = _db_fingerprint()
    out: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "source_db": str(SOURCE), "source_before": fp_before,
                 "text_formula_sha": mod.text_formula_sha(),
                 "out_dim": mod.OUT_DIM, "table": mod.TABLE}
    out["T1_resume_equals_oneshot"] = t1_resume_equals_oneshot(mod, log)
    out["T2_real_kill_then_resume"] = t2_real_kill(mod, log)
    out["T3_idempotent_rerun"] = t3_idempotent(mod, log)
    out["T4_real_model_bytes_vs_e4"] = t4_real_model_bytes(mod, log)
    fp_after = _db_fingerprint()
    out["source_after"] = fp_after
    out["T5_source_untouched"] = {"mtime_same": fp_before["mtime"] == fp_after["mtime"],
                                  "size_same": fp_before["size"] == fp_after["size"],
                                  "clause_vec_same": fp_before["clause_vec"] == fp_after["clause_vec"],
                                  "clause_revision_same": fp_before["clause_revision"] == fp_after["clause_revision"]}
    out["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out["verdict"] = {
        "T1": out["T1_resume_equals_oneshot"]["identical"],
        "T2": out["T2_real_kill_then_resume"]["identical"],
        "T3": out["T3_idempotent_rerun"]["idempotent"],
        "T4": bool(out["T4_real_model_bytes_vs_e4"].get("A_all_identical")
                   and out["T4_real_model_bytes_vs_e4"].get("l2_normalized")),
        "T5": all(out["T5_source_untouched"].values()),
    }
    out["all_pass"] = all(out["verdict"].values())
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== 判定 ===")
    for k, v in out["verdict"].items():
        print(f"  {k}: {'✅ PASS' if v else '⛔ FAIL'}")
    print(f"  all_pass = {out['all_pass']}")
    print(f"  读数 → {OUT_JSON}")
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
