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

-- ============================================================================
-- 材料平面（2026-09-17 定位转移：通用资料研究 + 交付）
-- ============================================================================
-- 为什么**另立平面**而不复用 doc_meta：`doc_meta.standard_no TEXT NOT NULL UNIQUE`
-- **结构上就装不下**财报/新闻这类非标准文件；且 doc_meta/clause_revision/source_span
-- 是取证链承重墙（bbox 契约 §9.3 已踩坑两次）。本平面与法条链**零耦合**：
-- Track L（采到库内没有的法规标准）经评审后仍走既有 ingest 入 doc_meta，再由
-- `material.doc_id` **从材料侧回指**——**不改 doc_meta 一个字段**。
--
-- 权威性是**两个正交轴**（业主 2026-09-17 裁定的公司制度例）：
--   · 轴 A 来源可信度 source_tier：T0 法定/官方 · T1 用户自有原件 · T2 权威第三方
--     · T3 二手转述（需≥2 独立来源互证）· T4 不可回溯（禁用于结论）
--     决定"引用时怎么标注、能不能承重"；
--   · 轴 B 任务内效力 task_role：criterion=本任务的准则 / reference=参考。
--     决定"谁说话"——制度来源层级低于国标，但对"我们公司报销怎么走"它是准绳。
-- 二者不可合并成一个分数排序（单轴必然错一个）。
CREATE TABLE IF NOT EXISTS material_project (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    -- JSON：轴 B 的**项目级**效力声明（本项目以哪些材料/规则为准绳）
    authority_policy TEXT,
    note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS material (
    material_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES material_project(project_id),
    -- 来源：用户给的 / 系统自采（自采默认开启，但**必须评审**才可用）
    origin TEXT NOT NULL CHECK(origin IN ('user','collected')),
    -- 分轨：legal=Track L（可评审后入法规库）/ other=Track M（只作参考资料）
    kind TEXT NOT NULL DEFAULT 'other' CHECK(kind IN ('legal','other')),
    title TEXT NOT NULL,
    url TEXT,
    domain TEXT,
    fetched_at TEXT,
    published_at TEXT,
    content_hash TEXT,
    raw_path TEXT,
    mime TEXT,
    -- 轴 A：来源可信度（默认 T1 = 用户自有原件；自采的默认由采集侧按判据给）
    source_tier TEXT NOT NULL DEFAULT 'T1'
        CHECK(source_tier IN ('T0','T1','T2','T3','T4')),
    -- 层级是谁定的：system=规则/系统判，user=用户改（用户可改，留痕以便日后看懂当时的判断）
    tier_source TEXT NOT NULL DEFAULT 'system' CHECK(tier_source IN ('system','user')),
    tier_reason TEXT,
    tier_evidence TEXT,                 -- JSON：判级的机器可查证据（域名/原文URL/时间/是否原文/可交叉验证）
    -- 轴 B：本任务里的角色（null = 未声明，按参考处理）
    task_role TEXT CHECK(task_role IN ('criterion','reference')),
    -- 评审闸门：**未 approved 的材料不得进入检索/分析/引用**（硬门，非提示）
    review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK(review_status IN ('pending','approved','rejected')),
    review_note TEXT,
    reviewed_at TEXT,
    -- 生命周期：默认仅本次任务参考；用户可提名升为长期
    lifecycle TEXT NOT NULL DEFAULT 'ephemeral'
        CHECK(lifecycle IN ('ephemeral','promoted')),
    -- Track L 入法规库后回指 doc_meta（法条链零改动；回指放在材料侧）
    doc_id TEXT,
    -- 引用锚点稳定性（2026-09-17，方案 §12 未决第 5 条 = Phase B 必解）：
    -- `content_hash` 是**源文件字节**的哈希，而 `material_chunk` 的 char_start/char_end/page
    -- 是**解析结果**的坐标 ⇒ 换解析器（PyMuPDF 版本 / MinerU / 开 deep_fallback）会让
    -- 已存区间**静默作废**。这两列让"锚点还对不对"变成**可判定的**：
    --   · derived_text_hash：入库时**派生全文**（build_document 的输出）的 SHA-256；
    --   · parser_fingerprint：**决定这段文本的解析器身份**（引擎/版本/OCR/deep_fallback 等）。
    -- NULL = 未登记（2026-09-17 之前的材料）⇒ 如实报"未知"，**不假装 ok**。
    derived_text_hash TEXT,
    parser_fingerprint TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS material_chunk (
    chunk_id TEXT PRIMARY KEY,
    material_id TEXT NOT NULL REFERENCES material(material_id),
    ord INTEGER NOT NULL,
    text TEXT NOT NULL,
    -- 字符区间（材料内绝对偏移）：引用要能**点回原文位置**，与法条链的 source_span 同精神
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    page INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_material_project ON material(project_id, review_status);
CREATE INDEX IF NOT EXISTS idx_material_review ON material(review_status);
CREATE INDEX IF NOT EXISTS idx_material_hash ON material(content_hash);
CREATE INDEX IF NOT EXISTS idx_material_chunk_mat ON material_chunk(material_id, ord);

-- 材料全文检索（口径与 clause_fts 完全一致：**先 jieba 分词存 segmented 列**，
-- 再交给 tokenize='ascii' 的 FTS5）。分词实现只有一份
-- （`text_utils.segment_for_fts`），两条检索线不得各自漂移。
--
-- ⚠ 检索**必须**经 `material_repo.search_materials()`：它在 SQL 里 join `material`
-- 并强制 `review_status='approved'`（评审硬门）。直接查本虚拟表会绕过评审。
CREATE VIRTUAL TABLE IF NOT EXISTS material_fts USING fts5(
    chunk_id UNINDEXED,
    material_id UNINDEXED,
    title,
    content_segmented,
    tokenize = 'ascii'
);

-- ── 渠道台账（2026-09-18，§11.0 R2）────────────────────────────────────────────
-- 为什么要有这张表：巡检的"渠道"过去只活在两处——代码里的适配器
-- （`update/channels/*`，用户看不见）与公告源 JSON（`announce.py`，只有它能被维护）。
-- 业主诉求 = 前端能看到**每个**渠道的链接 / 有效性 / 上次成功查询，方便人工维护。
--
-- ⚠ 四个字段**刻意分开**（合起来就是"拿一个数字骗自己"，R1 的 G5/G6 是实证）：
--   wiring       接线状态：wired（在 routing 链上）| unwired（注册了但永不被探测）
--                | broken（在链上但**实测恒 miss**，如 web/govcn）| user（用户自加，公告源）
--                | seed_only（调研得来、尚未接线）
--                ⇒ 「13 个适配器」是**注册数**；只有 wiring=wired 才是能力数。
--   verification 研究期实测结论（verified|unverified|broken）——来自研究文档，**冻结的证据**
--   state        运行期健康度（unknown|ok|suspicious|down）——R3 的语义探针写入
--                ⚠ `suspicious` 专给"HTTP 200 但没有预期内容"（应急部标准页仅 465B、
--                bzw 列表页写"共0条"、住建部/ccsa/cesa 是 JS 壳）——只看状态码会判成健康。
--   enabled      人工开关（维护渠道用）
CREATE TABLE IF NOT EXISTS update_channel (
    channel_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,                    -- canonical（channel_repo.CATEGORIES）
    category_raw    TEXT,                             -- 调研文档里的原始写法（证据，不丢）
    -- org_kind  单位性质（2026-09-22 业主定）：**主办单位性质**——国家总局/地方人大/地方厅局…
    --   台账按它做「文件夹树」式分类（与知识库文件目录同交互）。枚举在 channel_repo.ORG_KIND；
    --   NULL=未分类。粗分类由 channel_repo.backfill_org_kind 按名称关键词回填，人工可改
    --   （改过的不再被回填覆盖）。老库由 sqlite_db._ensure_channel_columns 补列。
    org_kind        TEXT,
    url             TEXT,
    fetch_kind      TEXT,                             -- json|html|pdf|rss|js_shell|search|unknown
    list_endpoint   TEXT,
    params_json     TEXT,                             -- 分页/检索参数原样留档
    answers_json    TEXT,                             -- JSON 数组：发布/修订/废止/现行性/编号核验
    covers          TEXT,
    gaps            TEXT,
    -- segments_json  §11.0 R7：**号段**——"这条渠道管哪些标准号"，JSON 字符串数组
    --   （如 ["HJ"]、["GB 50","GB 55"]、["T/"]）。语义：链在路由链之外按这些前缀做**加法**
    --   （只加尾巴、不改顺序，见 update/channels/ledger_chain.py）；匹配口径在 routing.py。
    --   为什么要它：R6g 量出"有适配器的 13 条只有 3 条在链上"，因为"号段→渠道"此前只硬编码
    --   在 routing._PREFIX_ROUTE 里 ⇒ 台账（= 业主能改的那层）无从表达。老库由
    --   sqlite_db._ensure_channel_columns 补列。
    segments_json   TEXT,
    wiring          TEXT NOT NULL DEFAULT 'seed_only',
    verification    TEXT NOT NULL DEFAULT 'unverified',
    state           TEXT NOT NULL DEFAULT 'unknown',
    probe_url       TEXT,                             -- 语义探针目标（R3）
    probe_expect    TEXT,                             -- 探针必须命中的锚点
    enabled         INTEGER NOT NULL DEFAULT 1,
    last_try_at     TEXT,
    last_ok_at      TEXT,
    last_error      TEXT,
    last_error_code TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    latency_ms      INTEGER,
    source_file     TEXT,                             -- 研究文档出处（回查证据）
    note            TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_channel_cat ON update_channel(category, state);
CREATE INDEX IF NOT EXISTS idx_channel_wiring ON update_channel(wiring, enabled);

-- 渠道「已知文件测试」（批C，2026-09-22 业主定案）：每条渠道一个已知文件（样本链接 +
-- 期望标准号）；测试=拉下来/认出来 ⇒ 渠道算数。结果**永远留痕**（ok/fail + 详情 + 时间）。
CREATE TABLE IF NOT EXISTS channel_test_case (
    channel_id   TEXT PRIMARY KEY,
    sample_url   TEXT NOT NULL,
    expect_no    TEXT NOT NULL,                    -- 期望标准号（比对口径见 channel_test._norm_no）
    note         TEXT,
    last_result  TEXT,                             -- ok | fail（没跑过=NULL）
    last_detail  TEXT,
    last_run_at  TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- 知识库多级目录（33~35 号表；2026-09-21，方案真源 docs/KB-FOLDER-PLAN.md §3）
-- ============================================================================
-- 为什么**另立**而不复用 user_bookmark_folder（9c）：那张表是**单层**收藏夹
-- （`UNIQUE(folder_name)` 全库同名拒绝、无 parent_id、夹内只装收藏），装不下
-- "无限层级 + 同名可异层 + 一个目录里既有子目录也有文件"。两张表的 `folder_id`
-- 同形但**互不相干**（各自表内引用），任何查询**不得**跨表 join 它们。
--
-- ⚠ 归属是**多对多**（业主定案："复制 = 多一处位置"，见方案 §一/§二）：
--   `folder_member` 一行 = "某个东西出现在某个目录里一次"。
--     · 复制目录 = 新目录 + **复制那批成员行**（同一个 item_id，不各拷一份）；
--     · 从一处拿掉 = 删一行（**不是**删文件；所有行都没了才轮到真删文件，属第 2 步）；
--     · 一个文件可同时属于多个目录；一个子目录也可以同时挂在多个上级下。
-- ⚠ 两级父子关系（方案 §3 把两者都定死了，本表**照写**，语义分工写在 folder_store 模块头）：
--     · `folder.parent_id` = **主位置**（唯一），`parent_id IS NULL` ⇒ 在**顶层**出现；
--     · `folder_member(item_kind='folder')` = **全部**父子边（可多条）。
--   不变式：`F.parent_id = P` ⇒ 必有成员行 `(P,'folder',F)`（folder_store 维护）。
-- ⚠ 同名同层拒绝用**两条部分唯一索引**表达：`UNIQUE(parent_id,name)` 对一级目录**无效**
--   （parent_id 是 NULL，而 SQLite 里 NULL 互不相等）⇒ 只靠表级 UNIQUE 拦不住根层重名。
-- ⚠ `folder_member.item_id` 是**多态**（item_kind 区分 folder/file）⇒ **无表级 FK**；
--   引用完整性由 `folder_store` 在同一个写事务里校验（与 `user_bookmark.folder_id` 同一取舍）。
--   ⚠ **删除侧没有兜底**（2026-09-24 审计 A1）：删文档的两条路
--   （`doc_delete.delete_documents` / `clause_repo.delete_document`）必须**显式**清掉
--   该文档的 `folder_member(item_kind='file')` 与 `doc_filing_state` 行；重导
--   （`run_full_ingest(reingest=True)`）另有一半：删旧文档**前**拍快照、
--   入库成功后把归属与归位记录落到新 doc_id（`folder_store.snapshot/restore_filing_assets`）。
CREATE TABLE IF NOT EXISTS folder (
    folder_id TEXT PRIMARY KEY,          -- ULID 前缀 fld_
    parent_id TEXT,
    name TEXT NOT NULL,
    sort INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_folder_root_name ON folder(name) WHERE parent_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_folder_child_name ON folder(parent_id, name) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_folder_parent ON folder(parent_id, sort);

CREATE TABLE IF NOT EXISTS folder_member (
    folder_id TEXT NOT NULL,
    item_kind TEXT NOT NULL CHECK(item_kind IN ('folder','file')),
    item_id TEXT NOT NULL,
    added_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (folder_id, item_kind, item_id)
);
CREATE INDEX IF NOT EXISTS idx_folder_member_item ON folder_member(item_kind, item_id);

-- 文件处理状态（方案 §3 第三行「处理状态」+ 第四行「归位记录」）。
-- **不改 doc_meta**（那是取证链承重墙，方案 §七也只允许整表清掉本表重来）：
--   · stage  排队/识别中/待确认/已归位/识别失败 ⇒ queued/recognizing/confirming/filed/failed
--   · confidence 识别率（0~1，NULL = 未知，**不假装 1.0**）
--   · failure_kind 失败类型（overall/table/…，自由文本，不设 CHECK——枚举还会长）
--   · suggested_folder_id 建议去向（现有目录）· suggest_new_path 建议新建路径
--   · placed_* 归位记录：谁在什么时候把它放进了哪个目录（「待分类」确认环节回看用）
-- 两类读取需求都靠它：① 「待分类」列表（stage<>'filed' 或从未归位）；② **所有文件**的状态展示。
CREATE TABLE IF NOT EXISTS doc_filing_state (
    doc_id TEXT PRIMARY KEY,
    stage TEXT NOT NULL DEFAULT 'queued'
        CHECK(stage IN ('queued','recognizing','confirming','filed','failed')),
    confidence REAL,
    failure_kind TEXT,
    suggested_folder_id TEXT,
    suggest_new_path TEXT,
    placed_folder_id TEXT,
    placed_by TEXT,
    placed_at TEXT,
    last_error TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_filing_stage ON doc_filing_state(stage, updated_at);
CREATE INDEX IF NOT EXISTS idx_filing_placed_folder ON doc_filing_state(placed_folder_id);

-- CCS（中国标准分类号）查询台账（2026-09-22「补全分类号」自愈机制）。
-- **为什么不写进 doc_filing_state**：那张表的 stage/failure_kind 是**解析**状态的口径
--   （见 pipeline._write_filing_state 与 folder_store.FAILURE_KIND_*），把"分类号查没查到"
--   塞进 failure_kind 会**覆盖**解析失败的原因、并可能把 stage 改成 failed ⇒ 拿一个功能
--   去毁另一个功能的记录。分类号查询是**另一件事**，所以有**另一张表**。
-- **为什么不写 doc_meta.ccs_code/ccs_name**：那两列是既有的追加列、**全库为空**且没人写；
--   CCS 标签的唯一所有者是 `doc_meta.domain_tags` 里的 `CCS:…` 条目（分类树读的就是它）。
--   同一件事有两个家迟早打架，所以本表**只记"这次查了什么、从哪一层查到的、为什么没查到"**，
--   真正的分类号仍只落 domain_tags 一处。
--   · outcome  查询结论五枚举（ccs_fetcher.OUTCOMES）——**"发不出去"与"官方查无"必须分开**：
--              found / not_found / network_failed / parse_failed /
--              not_applicable（**这一篇的号不像标准号**，如被标成 standard 的法规 ——
--              实测真库那 380 篇里混着 7 篇法规，分类号对它们**永远不适用**）
--   · source   命中的是哪一层（official_api|web_scrape|local_table|seed_file）
--   · keyword_form 命中的是哪种关键词形式（full|clean|compact|core|bare）
--   · matched_no   站点返回的标准号（可能与库里写法不同，如 GB→GB/T）
--   · reason   给界面看的一句人话；attempts_json 是逐层逐形式的审计流水
--   · applied_at 标签被确认在 domain_tags 里的时刻（NULL = 从没成功写进去）
CREATE TABLE IF NOT EXISTS doc_ccs_state (
    doc_id TEXT PRIMARY KEY,
    outcome TEXT NOT NULL
        CHECK(outcome IN ('found','not_found','network_failed','parse_failed',
                          'not_applicable')),
    source TEXT,
    keyword_form TEXT,
    matched_no TEXT,
    ccs_code TEXT,
    ccs_name TEXT,
    reason TEXT,
    attempts_json TEXT,
    checked_at TEXT DEFAULT (datetime('now')),
    applied_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_ccs_state_outcome ON doc_ccs_state(outcome, checked_at);

