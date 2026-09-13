-- KnowledgeStation 权威物理表结构 (T00 冻结, 依据主计划 v4.3 第五部分)
-- 初始化时执行: PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=60000;

-- 1. 文档元数据表
CREATE TABLE IF NOT EXISTS doc_meta (
    doc_id TEXT PRIMARY KEY,
    standard_no TEXT NOT NULL UNIQUE,
    standard_name TEXT NOT NULL,
    short_code TEXT NOT NULL,
    current_revision_id TEXT NOT NULL,
    legal_status TEXT CHECK(legal_status IN ('effective', 'upcoming', 'superseded', 'withdrawn')),
    legal_hierarchy TEXT DEFAULT 'GB',
    standard_type TEXT DEFAULT 'mandatory',
    doc_type TEXT DEFAULT 'standard',
    quality_grade TEXT DEFAULT 'A',
    domain_tags TEXT NOT NULL,
    effective_from TEXT,
    published_at TEXT,
    ccs_code TEXT,
    ccs_name TEXT,
    ics TEXT,
    superseded_by TEXT,
    withdrawn_date TEXT,          -- 废止日期（cssn a206 / ndls a206）
    normative_refs TEXT,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    source TEXT,                 -- 官方来源: flk | govcn（LAW_SOURCE_PLAN §5）
    source_id TEXT,              -- 幂等键: flk bbbs | govcn url hash
    source_url TEXT,             -- 溯源 URL
    downloaded_at TEXT,          -- 下载时间 ISO
    source_status TEXT,          -- flk sxx 时效（3=有效）等
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 2. PDF 页面物理几何参数表
CREATE TABLE IF NOT EXISTS doc_page_geometry (
    doc_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    rotation INTEGER DEFAULT 0,
    crop_box TEXT,
    media_box TEXT,
    PRIMARY KEY (doc_id, page_number),
    FOREIGN KEY (doc_id) REFERENCES doc_meta(doc_id) ON DELETE CASCADE
);

-- 3. 条款修订快照表 (三型知识单元)
CREATE TABLE IF NOT EXISTS clause_revision (
    clause_revision_id TEXT PRIMARY KEY,
    doc_revision_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    clause_key TEXT NOT NULL,
    clause_number TEXT NOT NULL,
    title TEXT,
    content_text TEXT NOT NULL,
    content_markdown TEXT,
    table_summary TEXT,
    figure_html TEXT,                  -- 2026-09-01 C2: MinerU 预裁剪插图占位 <p class="fig-strip">（apiFetch blob 补 src）；独立通道防 md 路径误判
    formula_number TEXT,
    formula_desc TEXT,
    image_text TEXT,
    hierarchy_path TEXT,
    knowledge_type TEXT DEFAULT 'rule',
    type_confidence REAL DEFAULT 1.0,
    modality TEXT,
    modality_strength INTEGER,
    modality_confidence REAL,
    behavior_scope TEXT,
    subject TEXT,
    object TEXT,
    behavior TEXT,
    applicability_condition TEXT,
    restriction TEXT,
    exception TEXT,
    legal_refs TEXT,
    is_mandatory INTEGER DEFAULT 0,
    is_suspicious INTEGER DEFAULT 0,
    ocr_confidence REAL DEFAULT 1.0,
    content_type TEXT DEFAULT 'normal',
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    cross_refs TEXT,
    explanation_ref TEXT,
    content_hash TEXT,                 -- Task 10.4: sha256(content_text)，快照可验证（红线 v2 #2）
    page_breaks TEXT,                  -- 2026-09-01 B3: 页界 run-start 编码 [[行号,PDF页],...]（行号=content_text 0-based 行索引，首条目恒为 [0,首行页]）；NULL=存量未采集，渲染层跳过分隔
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(doc_id) REFERENCES doc_meta(doc_id) ON DELETE CASCADE
);

-- 4. 条款物理原页坐标表
CREATE TABLE IF NOT EXISTS source_span (
    span_id TEXT PRIMARY KEY,
    clause_revision_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    bbox_json TEXT NOT NULL,
    span_type TEXT DEFAULT 'text',
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY(clause_revision_id) REFERENCES clause_revision(clause_revision_id) ON DELETE CASCADE
);

-- 5. FTS5 中文全文检索虚拟表
CREATE VIRTUAL TABLE IF NOT EXISTS clause_fts USING fts5(
    clause_revision_id UNINDEXED,
    clause_number,
    standard_no,
    title,
    content_segmented,
    modality UNINDEXED,
    subject UNINDEXED,
    behavior_scope_segmented,
    tokenize = 'ascii'
);

-- 6. sqlite-vec 向量检索虚拟表 (bge-small-zh-v1.5, 512 维)
CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec USING vec0(
    clause_revision_id TEXT PRIMARY KEY,
    embedding FLOAT[512]
);

-- 7. 术语同义词与别名库
CREATE TABLE IF NOT EXISTS alias_store (
    alias_id TEXT PRIMARY KEY,
    term TEXT NOT NULL,
    alias TEXT NOT NULL,
    source_type TEXT DEFAULT 'auto_extract',
    source_doc_id TEXT,
    confidence REAL DEFAULT 1.0,
    status TEXT DEFAULT 'active'
);

-- 8. 证据依赖图
CREATE TABLE IF NOT EXISTS evidence_edge (
    edge_id TEXT PRIMARY KEY,
    edge_type TEXT NOT NULL,
    source_clause_id TEXT NOT NULL,
    target_clause_id TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(source_clause_id) REFERENCES clause_revision(clause_revision_id) ON DELETE CASCADE,
    FOREIGN KEY(target_clause_id) REFERENCES clause_revision(clause_revision_id) ON DELETE CASCADE
);

-- 9. 用户收藏表
CREATE TABLE IF NOT EXISTS user_bookmark (
    bookmark_id TEXT PRIMARY KEY,
    clause_key TEXT NOT NULL,
    fixed_revision_id TEXT,
    remark TEXT,
    tags TEXT,
    folder_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 9b. 用户标准收藏表（增强③-A 标准级书签；条款级收藏见 user_bookmark）
CREATE TABLE IF NOT EXISTS user_doc_bookmark (
    doc_bookmark_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    remark TEXT,
    folder_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(doc_id) REFERENCES doc_meta(doc_id) ON DELETE CASCADE,
    UNIQUE(doc_id)
);

-- 9c. 收藏夹目录（2026-10 收藏目录功能）：自建收藏夹；收藏夹删除 → 收藏回「未分类」
-- （folder_id 置 NULL，绝不连坐删收藏）。UNIQUE(folder_name) 同名夹拒绝。
CREATE TABLE IF NOT EXISTS user_bookmark_folder (
    folder_id TEXT PRIMARY KEY,
    folder_name TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(folder_name)
);

-- 10. 用户批注表
CREATE TABLE IF NOT EXISTS user_annotation (
    annotation_id TEXT PRIMARY KEY,
    clause_key TEXT NOT NULL,
    content TEXT NOT NULL,
    annotation_type TEXT DEFAULT 'personal',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 11. 项目清单表
CREATE TABLE IF NOT EXISTS project_list (
    project_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    project_type TEXT DEFAULT 'engineering',
    clause_revision_ids TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 12. 合规审查任务表
CREATE TABLE IF NOT EXISTS review_task (
    task_id TEXT PRIMARY KEY,
    project_id TEXT,
    review_type TEXT NOT NULL,
    object_name TEXT,
    object_content TEXT,
    object_file_path TEXT,
    status TEXT DEFAULT 'pending',
    total_points INTEGER DEFAULT 0,
    red_count INTEGER DEFAULT 0,
    yellow_count INTEGER DEFAULT 0,
    green_count INTEGER DEFAULT 0,
    report_data TEXT,
    report_path TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY(project_id) REFERENCES project_list(project_id) ON DELETE SET NULL
);

-- 13. 合规审查点表
CREATE TABLE IF NOT EXISTS review_point (
    point_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    point_type TEXT NOT NULL,
    point_content TEXT NOT NULL,
    matched_clause_ids TEXT,
    match_scores TEXT,
    verdict TEXT,
    verdict_reason TEXT,
    modality_comparison TEXT,
    suggestion TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(task_id) REFERENCES review_task(task_id) ON DELETE CASCADE
);

-- 14. 义务清单与检查表
CREATE TABLE IF NOT EXISTS obligation_list (
    list_id TEXT PRIMARY KEY,
    business_description TEXT NOT NULL,
    mode TEXT DEFAULT 'list',
    items TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 15. 合规差距分析表
CREATE TABLE IF NOT EXISTS gap_analysis (
    gap_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    legal_obligation_id TEXT NOT NULL,
    legal_obligation_text TEXT NOT NULL,
    internal_policy_section TEXT,
    verdict TEXT,
    gap_description TEXT,
    remediation_suggestion TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(task_id) REFERENCES review_task(task_id) ON DELETE CASCADE
);

-- 16. 法定义务清单
CREATE TABLE IF NOT EXISTS legal_obligation (
    obligation_id TEXT PRIMARY KEY,
    clause_revision_id TEXT NOT NULL,
    obligation_text TEXT NOT NULL,
    domain_tag TEXT,
    FOREIGN KEY(clause_revision_id) REFERENCES clause_revision(clause_revision_id) ON DELETE CASCADE
);

-- 17. 内部制度文档表
CREATE TABLE IF NOT EXISTS internal_policy (
    policy_id TEXT PRIMARY KEY,
    policy_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    sections TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 18. 系统设置表
CREATE TABLE IF NOT EXISTS app_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    is_encrypted INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 19. 单写者队列
CREATE TABLE IF NOT EXISTS write_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    result TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    processed_at TEXT
);

-- 20. 统一事件模型
CREATE TABLE IF NOT EXISTS event_log (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor TEXT,
    target_type TEXT,
    target_id TEXT,
    before_state TEXT,
    after_state TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 21. 可重放 Debug Dump
CREATE TABLE IF NOT EXISTS debug_dump (
    dump_id TEXT PRIMARY KEY,
    trigger_type TEXT NOT NULL,
    query TEXT,
    retrieval_result TEXT,
    prompt TEXT,
    llm_output TEXT,
    claim_parsed TEXT,
    verification_result TEXT,
    logs TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 22. 跨版本条款映射队列
CREATE TABLE IF NOT EXISTS remapping_queue (
    queue_id TEXT PRIMARY KEY,
    old_clause_key TEXT NOT NULL,
    new_clause_key TEXT NOT NULL,
    old_doc_id TEXT NOT NULL,
    new_doc_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    user_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 23. 快照表
CREATE TABLE IF NOT EXISTS snapshot_meta (
    snapshot_id TEXT PRIMARY KEY,
    snapshot_type TEXT NOT NULL,
    db_checksum TEXT NOT NULL,
    file_count INTEGER NOT NULL,
    clause_count INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 24. 操作日志表
CREATE TABLE IF NOT EXISTS operation_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    detail TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 25. 审计日志表
CREATE TABLE IF NOT EXISTS audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    user_action TEXT,
    target_type TEXT,
    target_id TEXT,
    detail TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 26. 反馈日志表
CREATE TABLE IF NOT EXISTS feedback_log (
    feedback_id TEXT PRIMARY KEY,
    clause_revision_ids TEXT,
    feedback_type TEXT,
    feedback_content TEXT,
    rating INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 27. 关注清单
CREATE TABLE IF NOT EXISTS watch_list (
    watch_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(doc_id) REFERENCES doc_meta(doc_id) ON DELETE CASCADE
);

-- 28. 条款人工纠错补丁表 (阶段2.1 新增，外部评审响应)
--     R79 不可变快照零侵入：原始 content_text 永不改写，补丁在读路径透明覆写
CREATE TABLE IF NOT EXISTS clause_patch (
    patch_id TEXT PRIMARY KEY,                 -- ULID
    clause_revision_id TEXT NOT NULL,
    field_name TEXT NOT NULL,                  -- content_text | title | table_summary
    patched_value TEXT NOT NULL,
    patch_reason TEXT,
    created_by TEXT NOT NULL DEFAULT 'local-user',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(clause_revision_id, field_name),
    FOREIGN KEY(clause_revision_id) REFERENCES clause_revision(clause_revision_id) ON DELETE CASCADE
);

-- 29. 更新巡检批次表 (阶段三·更新模块新增，契约先行见 pipeline/02 §2 与 pipeline/03)
CREATE TABLE IF NOT EXISTS update_check_batch (
    batch_id TEXT PRIMARY KEY,              -- ULID 前缀 upd_
    trigger_type TEXT CHECK(trigger_type IN ('manual','scheduled')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','running','paused','done','failed')),
    total INTEGER DEFAULT 0, checked INTEGER DEFAULT 0,
    red_count INTEGER DEFAULT 0, yellow_count INTEGER DEFAULT 0,
    green_count INTEGER DEFAULT 0, gray_count INTEGER DEFAULT 0,  -- gray=查无此号
    started_at TEXT, finished_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 30. 标准变更事件表 (阶段三·更新模块新增，契约先行见 pipeline/02 §2 与 pipeline/03)
CREATE TABLE IF NOT EXISTS update_change_event (
    change_id TEXT PRIMARY KEY,             -- ULID 前缀 chg_
    batch_id TEXT NOT NULL,
    doc_id TEXT,                            -- 可空：公告命中但库内无此文档
    standard_no TEXT NOT NULL,
    standard_name TEXT,
    change_type TEXT NOT NULL CHECK(change_type IN ('new_version','superseded','withdrawn','not_found','no_change')),
    current_legal_status TEXT CHECK(current_legal_status IS NULL OR current_legal_status IN ('effective','upcoming','superseded','withdrawn')),
    latest_info_json TEXT,                  -- 官方返回 {version,effective_date,url,...}
    source_channel TEXT NOT NULL,           -- official_gb | web | govcn | laws_db | manual
    evidence_url TEXT,
    archived_pdf_path TEXT,                 -- F-03 公告 PDF 存档
    user_ack INTEGER DEFAULT 0,
    detected_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(batch_id) REFERENCES update_check_batch(batch_id) ON DELETE CASCADE
);

-- 31. 批量导入批次表 (阶段六·批次2 新增，巡检侧最小版；依据 pipeline/06-bulk-ingest-design.md §4)
--     batch_kind='inspect' 由更新巡检编排器使用：tier 分层 + checkpoint_json 断点，
--     与 update_check_batch 以同值 batch_id 成对镜像（锚行），update_change_event 外键落点不变；
--     'bulk_ingest' 为批量导入编排预留（后续批次启用，届时再补 quarantine_count 等列）。
CREATE TABLE IF NOT EXISTS bulk_import_batch (
    batch_id TEXT PRIMARY KEY,              -- ULID 前缀 bul_
    batch_kind TEXT CHECK(batch_kind IN ('inspect','bulk_ingest')),
    trigger_type TEXT CHECK(trigger_type IN ('manual','scheduled')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','running','paused','done','failed')),
    total INTEGER DEFAULT 0, checked INTEGER DEFAULT 0,
    red_count INTEGER DEFAULT 0, yellow_count INTEGER DEFAULT 0,
    green_count INTEGER DEFAULT 0, gray_count INTEGER DEFAULT 0,
    tier TEXT DEFAULT 'tier1' CHECK(tier IN ('tier0','tier1')),
    checkpoint_json TEXT,                   -- 断点续扫 {queue,done,captcha_pending,pause_reason,...}
    started_at TEXT, finished_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 32. 公告源已见公告表 (公告发现模块；契约增量见 pipeline/03「公告发现」节：
--     先改 契约增量文档 + test_contract.py，再动本文件。
--     与查号巡检 update_change_event 是两条独立流程：本表记"源列表页见过一条公告"，
--     无外键（source_id 属 app_config 配置语义，删源不删记录，source_name 快照保可读）。
--     去重键 UNIQUE(source_id, url_hash)：URL 归一化(去 fragment/追踪参数/尾斜杠，
--     host 小写、query 排序)后 SHA-256；命中已有行仅刷新 last_seen，不插行。
--     user_ack 为 P1 已读标记（P0 不暴露 UI，列先行避免二次契约周期）。)
CREATE TABLE IF NOT EXISTS announcement_observed (
    observed_id TEXT PRIMARY KEY,           -- ULID 前缀 ann_
    source_id TEXT NOT NULL,
    source_name TEXT,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL,
    standard_no TEXT,                       -- 标题中正则识别出的标准号（可空，零 LLM）
    published_date TEXT,                    -- 列表页解析日期 YYYY-MM-DD（解析失败留空，不猜）
    first_seen TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now')),
    scan_id TEXT,                           -- 首次发现所在扫描（asc_ 前缀）
    user_ack INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_announce_dedup ON announcement_observed(source_id, url_hash);
CREATE INDEX IF NOT EXISTS idx_announce_first_seen ON announcement_observed(first_seen);
CREATE INDEX IF NOT EXISTS idx_announce_scan ON announcement_observed(scan_id);

-- ===== 索引加速 (5.4 节) =====
CREATE INDEX IF NOT EXISTS idx_clause_lookup ON clause_revision(doc_id, clause_number);
CREATE INDEX IF NOT EXISTS idx_clause_key ON clause_revision(clause_key);
CREATE INDEX IF NOT EXISTS idx_clause_type ON clause_revision(knowledge_type);
CREATE INDEX IF NOT EXISTS idx_clause_modality ON clause_revision(modality);
CREATE INDEX IF NOT EXISTS idx_clause_subject ON clause_revision(subject);
CREATE INDEX IF NOT EXISTS idx_span_clause ON source_span(clause_revision_id, page_number);
CREATE INDEX IF NOT EXISTS idx_doc_short_code ON doc_meta(short_code);
CREATE INDEX IF NOT EXISTS idx_doc_hierarchy ON doc_meta(legal_hierarchy);
CREATE INDEX IF NOT EXISTS idx_alias_lookup ON alias_store(alias);
CREATE INDEX IF NOT EXISTS idx_edge_source ON evidence_edge(source_clause_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_edge_target ON evidence_edge(target_clause_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_write_queue_status ON write_queue(status, created_at);
CREATE INDEX IF NOT EXISTS idx_event_log_target ON event_log(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_review_task_project ON review_task(project_id);
CREATE INDEX IF NOT EXISTS idx_review_point_task ON review_point(task_id);
CREATE INDEX IF NOT EXISTS idx_patch_lookup ON clause_patch(clause_revision_id, field_name);
CREATE INDEX IF NOT EXISTS idx_change_batch ON update_change_event(batch_id, change_type);
CREATE INDEX IF NOT EXISTS idx_change_doc ON update_change_event(doc_id);
-- 规模化补齐（几万文档量级会痛的四个点）：
-- ① legal_obligation 外键无索引 → 级联删除 O(条款数×义务数) 全表扫
CREATE INDEX IF NOT EXISTS idx_legal_obligation_clause ON legal_obligation(clause_revision_id);
-- ② doc_meta.file_hash 防重快速路径 WHERE file_hash=? 无索引 → 每次入库全表扫
CREATE INDEX IF NOT EXISTS idx_doc_file_hash ON doc_meta(file_hash);
-- ③④ 时间线 UNION ALL 排序需要 created_at 索引，否则两表全扫 + 临时 B 树
CREATE INDEX IF NOT EXISTS idx_event_log_created ON event_log(created_at);
CREATE INDEX IF NOT EXISTS idx_operation_log_created ON operation_log(created_at);
