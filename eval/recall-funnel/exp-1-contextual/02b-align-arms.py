"""E1 步骤 2b：**把两个臂的候选集合对齐**（这是止损线里写死的 hard_fail 前置）。

问题（中途体检发现）：
 · 对照臂 `clause_vec` = **522,021** 行；
 · 实验臂 `clause_vec_ctx` 只会到 **521,978** 行 —— 因为 `02-build-text.py` 跳过了 **正文为空**的 43 条。

⚠ **那 43 条的向量不是用空换行算的**（**更正留痕**：本文件初版这么写，是**事实错误**）。
实测那 43 条**正是全库唯一有 title 的 43 条**（title 值都是 `图(未识别题注，第1页)`、正文长度 0），
按入库公式 `title + "\\n" + content_text[:512]`，它们的输入是 **`图(未识别题注，第1页)\\n`**。
它们属于**退化的垃圾干扰项**：只有图注、没有正文。复核 F10 指出后自查确认，已改正。

两臂候选集合不一致 ⇒ 名次不可比（少 43 个干扰项会让实验臂的名次**看似变好**，
而这与"换文本"毫无关系）。按 `stop-loss.json` 的 hard_fail，本次会作废。

对齐办法：**从副本里删掉那 43 条对照臂向量**（**只动副本，真库一个字节不碰**），
使两臂都只在"有正文的 521,978 条"上排名。删完必须**重跑对照臂自检**，
确认基线仍是 0.1000 / 0.1750 / 0.3583 —— 若变了，说明那 43 条真的进过某条题的前 1000 名，要单独说。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\02b-align-arms.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension
    conn = sqlite3.connect(str(EXP))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1

    n_base = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    n_txt = conn.execute("SELECT COUNT(*) FROM retrieval_text_ctx").fetchone()[0]
    ids = [r[0] for r in conn.execute(
        "SELECT clause_revision_id FROM clause_vec v"
        " WHERE NOT EXISTS (SELECT 1 FROM retrieval_text_ctx t"
        "                   WHERE t.clause_revision_id = v.clause_revision_id)")]
    print(f"[align] clause_vec={n_base}  retrieval_text_ctx={n_txt}  差集={len(ids)}")

    # 核对：这 43 条应当全是"正文为空"
    if ids:
        ph = ",".join("?" * len(ids))
        bad = conn.execute(
            f"SELECT COUNT(*) FROM clause_revision WHERE clause_revision_id IN ({ph})"
            "   AND content_text IS NOT NULL AND trim(content_text) <> ''", ids).fetchone()[0]
        print(f"[align] 差集里**有正文**的 {bad} 条（应为 0 {'✅' if bad == 0 else '⛔'}）")
        if bad:
            print("   ⇒ 不是'空正文'这一类，停下来别删")
            return 1

        with conn:
            conn.executemany("DELETE FROM clause_vec WHERE clause_revision_id=?", [(x,) for x in ids])
        n_after = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
        print(f"[align] 已从**副本**删除 {len(ids)} 条；clause_vec 现在 {n_after} 行，"
              f"与 retrieval_text_ctx {n_txt} 行一致：{'✅' if n_after == n_txt else '⛔'}")
    else:
        print("[align] 两个集合已经一致，无需处理")

    print("[align] 真库未触碰（只开过副本 exp.db）")
    print("[align] ⚠ 下一步必须重跑 04a-control-check.py —— 删了 43 条后基线仍须是"
          " 0.1000 / 0.1750 / 0.3583")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
