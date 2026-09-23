"""B4 复核 HIGH-1 的最小复现（父代理 2026-09-24 从复核报告里抄出来，做成可复用的）。

用法：& 'D:\\AI\\work space\\zcode\\.venv\\Scripts\\python.exe' repro-ccs-high1.py <要测的树>
  · 传冻结树 `D:\\AI\\work space\\zcode-verify-ccs`（9460344，改前）⇒ 应看到**两条**互相矛盾的 CCS 标签
  · 传实施树（改后）⇒ 应看到**只有一条**（新码），且台账与分类树读到**同一个**码

它只碰自己新建的临时数据目录（KS_DATA_DIR），**不碰真库**。
"""
import json
import os
import sys
import tempfile
import time

TREE = sys.argv[1] if len(sys.argv) > 1 else r'D:\AI\work space\zcode-verify-ccs'
sys.path.insert(0, TREE)
os.environ['KS_DATA_DIR'] = tempfile.mkdtemp(prefix='ks_ccs_repro_')
from src.core import config  # noqa: E402
config.reset_settings()
from src.core.storage.sqlite_db import (get_db_connection, init_schema,  # noqa: E402
                                        write_transaction)
init_schema()
from src.core.storage import clause_repo  # noqa: E402
from src.core.knowledge import ccs_backfill as bf  # noqa: E402
from src.core.knowledge import ccs_store  # noqa: E402
import src.core.knowledge.ccs_fetcher as cfmod  # noqa: E402

with write_transaction() as conn:
    clause_repo.insert_document(conn, {
        'doc_id': 'd1', 'standard_no': 'GB/T 91002-2020', 'standard_name': 'x',
        'short_code': 'GB/T 91002-2020', 'current_revision_id': 'r1',
        'doc_type': 'standard', 'legal_hierarchy': 'GB', 'standard_type': 'mandatory',
        'domain_tags': ['CCS:K41 变压器'], 'file_path': 'C:/tmp/d1.pdf', 'file_hash': 'h1'})

# 这一篇已经有 K41；让链"查到"另一个码 C65，再用 force=True 刷新
cfmod.resolve_ccs = lambda no, name='', **kw: {
    'outcome': 'found', 'code': 'C65', 'sub': '劳动安全技术', 'source': 'official_api',
    'keyword_form': 'full', 'matched_no': no, 'attempts': []}

bf.start_ccs_backfill(doc_ids=['d1'], force=True, pause_s=0.0)
while bf.ccs_backfill_status()['running']:
    time.sleep(0.05)

raw = get_db_connection().execute(
    'SELECT domain_tags FROM doc_meta WHERE doc_id=?', ('d1',)).fetchone()[0]
tags = json.loads(raw)
ccs_entries = [t for t in tags if str(t).startswith('CCS:')]
read_side = ccs_store.ccs_tag_of(raw)
ledger = ccs_store.get_ccs_state('d1')['ccs_code']
from src.core.knowledge.doc_catalog import classify_document  # noqa: E402
lv4 = classify_document({'standard_no': 'GB/T 91002-2020', 'standard_name': 'x',
                         'doc_type': 'standard', 'legal_hierarchy': 'GB',
                         'domain_tags': tags})['level4']

print(f'tree         = {TREE}')
print(f'domain_tags  = {tags}')
print(f'CCS 条目数    = {len(ccs_entries)}   (期望：刷新后仍是 1)')
print(f'读侧 ccs_tag  = {read_side}')
print(f'台账 ccs_code = {ledger}')
print(f'分类树 level4 = {lv4}')
consistent = (ledger is not None and read_side is not None
              and ledger in read_side and ledger in (lv4 or ''))
print(f'台账 / 读侧 / 分类树 一致 = {consistent}   (期望 True)')
print('VERDICT =', 'PASS（只有一条、三处一致）' if (len(ccs_entries) == 1 and consistent)
      else 'FAIL（出现第二条 CCS 标签 / 三处不一致）')
