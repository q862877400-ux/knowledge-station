"""迁移：修复 nat-mohurd 的 230 条 `question` 为空。

## 为什么不能只重采

采集器的 id 是**内容指纹** `md5(question|asked_at|answer|user)`。
`question` 从空变成有内容 ⇒ **指纹变了 ⇒ 新 id** ⇒ 重采会与旧记录**并存**，
形成「同一问答两条记录」的内容重复。

**所以必须做替换迁移**：按「不依赖 question 的键」匹配新旧，用新替旧。

## 匹配键

`(answer, asked_at, user)` —— **不含 question**（它正是要修的那个字段）。

## 宪法 V 要求

「留痕不许悄悄删」⇒ 本脚本：
1. 迁移前**强制备份**（到 `state/migration-backup-<ts>.jsonl`）
2. 输出**逐条变更报告**
3. **不删任何东西** —— 只做「替换 + 写回」，且报告里写明删了几条（那几条是被替换的旧记录）
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import human, now_iso, save_json                      # noqa: E402

DATA = ROOT / "data"
STATE = ROOT / "state"
CHANNEL = "nat-mohurd"


def _key(rec: dict) -> tuple:
    """匹配键：**不含 question**（那正是要修的字段）。"""
    ex = rec.get("extra") or {}
    user = (ex.get("user") if isinstance(ex, dict) else "") or ""
    return (str(rec.get("answer") or ""), str(rec.get("asked_at") or ""), str(user))


def _new_id(rec: dict) -> str:
    """与 adapter 一致的新 id 算法（含 question）。"""
    ex = rec.get("extra") or {}
    user = (ex.get("user") if isinstance(ex, dict) else "") or ""
    return hashlib.md5(
        f"{rec.get('question') or ''}|{rec.get('asked_at') or ''}|"
        f"{rec.get('answer') or ''}|{user}".encode("utf-8")
    ).hexdigest()[:16]


def main() -> int:
    files = sorted(DATA.glob(f"{CHANNEL}-*.jsonl"))
    if not files:
        human(f"❌ 找不到 {CHANNEL} 数据文件")
        return 1
    path = files[0]

    # ---- 读旧数据 -------------------------------------------------------
    old_rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("{"):
            try:
                old_rows.append(json.loads(line))
            except Exception:                                           # noqa: BLE001
                pass

    broken = [r for r in old_rows if not (r.get("question") or "").strip()]
    human(f"旧数据 {len(old_rows)} 条，其中 question 为空 {len(broken)} 条")

    if not broken:
        human("✅ 无需迁移")
        return 0

    # ---- 备份（宪法 V：留痕） -------------------------------------------
    STATE.mkdir(parents=True, exist_ok=True)
    bak = STATE / f"migration-backup-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    shutil.copy2(path, bak)
    human(f"已备份 → {bak.name}")

    # ---- 重新采集（用修好的 adapter） -----------------------------------
    human("重新采集（用修好的解析器）…")
    try:
        sys.path.insert(0, str(ROOT))
        import adapters
        mod = adapters.load(CHANNEL)
        import httpx
        import os
        os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
        UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Safari/537.36")
        client = httpx.Client(timeout=30, headers={"User-Agent": UA},
                              follow_redirects=True, trust_env=False, verify=False)
        fresh = mod.harvest(client.get, limit=5000)
    except Exception as e:                                              # noqa: BLE001
        human(f"❌ 重采失败：{type(e).__name__}: {e}")
        return 1

    human(f"重采得到 {len(fresh)} 条")

    # ---- 建索引：新记录按匹配键 -----------------------------------------
    fresh_by_key: dict[tuple, dict] = {}
    for r in fresh:
        if (r.get("question") or "").strip():
            fresh_by_key[_key(r)] = r

    # ---- 替换 -----------------------------------------------------------
    replaced = 0
    still_broken = 0
    out_rows: list[dict] = []
    for r in old_rows:
        if (r.get("question") or "").strip():
            out_rows.append(r)                      # 本来就好的，原样保留
            continue
        nk = _key(r)
        nr = fresh_by_key.get(nk)
        if nr is None:
            out_rows.append(r)                      # 匹配不上 ⇒ 保留（不删）
            still_broken += 1
            continue
        # 用新记录替换旧记录，但保留原有的标签字段（避免重跑分类器）
        ex_old = r.get("extra") or {}
        ex_new = nr.setdefault("extra", {})
        for k in ("msg_type_norm", "msg_type_source", "ingested_at"):
            if isinstance(ex_old, dict) and ex_old.get(k) and not ex_new.get(k):
                ex_new[k] = ex_old[k]
        nr["id"] = _new_id(nr)
        nr["extra"]["migrated_from"] = r.get("id")     # ★ 留痕：记下从哪条改来的
        nr["extra"]["migrated_at"] = now_iso()
        out_rows.append(nr)
        replaced += 1

    # ---- 写回 -----------------------------------------------------------
    with open(path, "w", encoding="utf-8") as fh:
        for r in out_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    human("")
    human(f"**替换 {replaced} 条**｜仍为空 {still_broken} 条｜写回共 {len(out_rows)} 条")
    human(f"（旧文件已备份到 {bak.name}）")
    return 0 if still_broken == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
