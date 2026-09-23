"""B1 的「真机」证据：真引擎 + 真 PDF + **真库副本**，跑一次「重新解析」并确认它仍在原目录。

为什么是副本：纪律是"不碰真库"。做法 = 把真库（2.2 GB）复制到临时数据目录，只在那份副本上跑。
覆盖的链路：真 `run_full_ingest(reingest=True)`（真解析器，不是合成 blocks）+ 真 `folder_member` /
`doc_filing_state` 搬运 + 界面读的那个出口 `folder_store.list_folder`。
用法（父代理实测入口）：
  $env:KS_BACKUP_DIR='' ; & <venv python> b1-reingest-e2e.py <doc_id>
不给 doc_id 就自己挑一篇"已归位、文件小"的标准。
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

SRC_DATA = Path(os.environ['APPDATA']) / 'KnowledgeStation'
SRC_DB = SRC_DATA / 'database' / 'knowledge.db'
WORK = Path(os.environ.get('TEMP', '/tmp')) / 'ks-b1-real'
CAP_S = int(os.environ.get('B1_CAP_S', '1500'))          # 硬上限，别挂到天亮


def ro_query(sql, args=(), db=None):
    """只读查询。⚠ **默认查真库**（`SRC_DB`）—— 只在"挑样本"阶段这么用；
    跑完重导之后**必须**显式传 `db=副本`，否则会拿真库去读"副本上发生的事"，
    得到一条**假 FAIL**（父代理 2026-09-24 第一版就是这么栽的）。"""
    con = sqlite3.connect(f'file:{db or SRC_DB}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


def pick_doc():
    rows = ro_query("""
      SELECT d.doc_id, d.standard_no, d.file_path,
             (SELECT COUNT(*) FROM folder_member m
               WHERE m.item_kind='file' AND m.item_id=d.doc_id) AS n_folders
      FROM doc_meta d
      WHERE d.doc_type='standard' AND d.file_path NOT LIKE '{%'
      ORDER BY d.standard_no
    """)
    cands = []
    for r in rows:
        p = Path(str(r['file_path']))
        if r['n_folders'] > 0 and p.is_file() and p.suffix.lower() == '.pdf':
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            if sz < 400 * 1024:                            # 小 PDF ⇒ 真解析才快
                # 优先**不是**本仓里的文件（本仓那条是"测试行"，见 var/tmp/B8-residuals.md §6）
                in_repo = os.path.normcase(str(p)).startswith(os.path.normcase(r'D:\AI\work space\zcode'))
                cands.append((in_repo, sz, r))
    cands.sort(key=lambda x: (x[0], x[1]))                  # 先非本仓、再按体积
    return cands[0][2] if cands else None


def main():
    doc_id = sys.argv[1] if len(sys.argv) > 1 else None
    if doc_id is None:
        rec = pick_doc()
        if rec is None:
            print('NO-CANDIDATE: 真库里没有"已归位 + 真 PDF + 体积小"的标准 ⇒ 真机验证做不了')
            return 2
        doc_id = rec['doc_id']
        print(f'挑中：{rec["standard_no"]}  doc_id={doc_id}\n     file={rec["file_path"]}')
    else:
        rec = ro_query('SELECT standard_no, file_path FROM doc_meta WHERE doc_id=?', (doc_id,))
        rec = rec[0] if rec else {'standard_no': '?', 'file_path': '?'}
        print(f'指定：{rec["standard_no"]}  doc_id={doc_id}\n     file={rec["file_path"]}')

    if not SRC_DB.is_file():
        print('真库不在：', SRC_DB)
        return 2

    # ── 复制副本（只读真库、只写临时目录）──
    (WORK / 'database').mkdir(parents=True, exist_ok=True)
    dst = WORK / 'database' / 'knowledge.db'
    if dst.is_file() and dst.stat().st_size == SRC_DB.stat().st_size:
        print(f'副本已存在且大小相同，复用：{dst}')
    else:
        t0 = time.time()
        shutil.copy2(SRC_DB, dst)
    print(f'复制真库副本 → {dst}（{dst.stat().st_size/1024/1024:.0f} MB，{time.time()-t0:.1f}s）')
    copy_db = dst

    os.environ['KS_DATA_DIR'] = str(WORK)
    os.environ.setdefault('KS_MODELS_DIR', str(Path(os.environ.get('TEMP', '/tmp')) / 'ks-gates-models'))

    sys.path.insert(0, r'D:\AI\work space\zcode')
    from src.core import config
    config.reset_settings()
    from src.core.knowledge import folder_store as fs
    from src.core.ingestion import reingest

    before_members = sorted(r['folder_id'] for r in ro_query(
        "SELECT folder_id FROM folder_member WHERE item_kind='file' AND item_id=?", (doc_id,),
        db=copy_db))
    before_state = ro_query('SELECT * FROM doc_filing_state WHERE doc_id=?', (doc_id,), db=copy_db)
    before_total = sum(1 for _ in before_members)
    print(f'改前（读**副本**）：归属 {before_total} 个目录 = {before_members}')
    print(f'改前（读**副本**）：归位记录 stage={before_state[0]["stage"] if before_state else None}')
    before_ui = {fid: fs.list_folder(fid)['files_total'] for fid in before_members}
    print('改前：界面出口 list_folder().files_total =', before_ui)

    t0 = time.time()
    res = reingest.start_reingest([doc_id])
    print('start_reingest →', {k: res[k] for k in ('queued',) if k in res},
          'skipped=', res.get('skipped'))
    while reingest.reingest_status()['running']:
        if time.time() - t0 > CAP_S:
            print(f'⛔ 超过硬上限 {CAP_S}s，放弃等待（解析太慢，如实报告）')
            return 3
        time.sleep(2)
    st = reingest.reingest_status()
    out = (st.get('results') or [{}])[-1]
    print(f'重导结束（{time.time()-t0:.1f}s）：status={out.get("status")} '
          f'new_doc_id={out.get("new_doc_id")} carried={out.get("filing_assets_carried")}')
    new_id = out.get('new_doc_id')

    if not new_id:
        print('⚠ 没换 doc_id（可能是同一篇原地更新）⇒ 归属本就不该动；真实结果见下')
        new_id = doc_id
    after_members = sorted(r['folder_id'] for r in ro_query(
        "SELECT folder_id FROM folder_member WHERE item_kind='file' AND item_id=?", (new_id,),
        db=copy_db))
    after_state = ro_query('SELECT * FROM doc_filing_state WHERE doc_id=?', (new_id,), db=copy_db)
    print(f'改后（读**副本**）：归属 {len(after_members)} 个目录 = {after_members}')
    print(f'改后（读**副本**）：归位记录 stage={after_state[0]["stage"] if after_state else None} '
          f'placed_folder_id={after_state[0]["placed_folder_id"] if after_state else None}')

    # 界面读的那个出口（`fs` 走 KS_DATA_DIR ⇒ 副本）
    after_ui = {fid: fs.list_folder(fid)['files_total'] for fid in set(before_members + after_members)}
    print('改后：界面出口 list_folder().files_total =', after_ui)
    print('界面出口改前/改后一致 =', before_ui == after_ui, f'（改前 {before_ui}）')

    verdict = ((after_members == before_members) and (len(after_members) == before_total)
               and (before_ui == after_ui))
    print('VERDICT =', 'PASS（重导后归属集合与改前完全一致，界面出口篇数也没虚增）' if verdict
          else 'FAIL（归属集合或界面篇数变了 —— 用户的整理成果被弄丢/被改动）')
    return 0 if verdict else 1


if __name__ == '__main__':
    sys.exit(main())
