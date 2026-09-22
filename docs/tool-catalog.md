# ks-dsh-plugin 工具目录（生成物——**手改必红**，改说明书后跑 `node plugin/scripts/smoke-tool-catalog.mjs --write`）

> 六件模型工具的说明书与参数表，**从真工具定义生成**（防漂移门禁 = 本目录与定义逐字比对）。

## ks_answer（说明书 998 字）

Forensic (取证) compliance Q&A against the local KnowledgeStation engine; returns three-part 依据/推导/结论 + tier + verification + notes. Own inference ⇒ tens of seconds (timeout >=120s); cheap lookup ⇒ ks_resolve_clause first. Only current-effective clauses cited; "reference"/empty evidence = no direct current provision (structured empty, not an error). Cite evidence_url as [依据：<standard_no> <clause_number>](<evidence_url>). Scope: params.kb_folder_ids / params.kb_doc_ids restrict RETRIEVAL (incl. children; ids and knobs = union). OMIT = whole library. An EMPTY array is NOT "no scope": engine answers 422, no retrieval — never falls back whole-library. verification.unsupported_context listing your cited clause ⇒ that citation is NOT supported: MUST disclose it (standard + case: same_standard_not_retrieved = retrieval gap; outside_evidence_standard = outside evidence/possibly invented). Never present such a citation as support, never omit it was raised. Usage rules arrive once on first call.

| 参数 | 类型 | 说明 |
|---|---|---|
| `query`（必填） | string | The compliance / regulatory question, e.g. "动火作业怎么分级" or "气体探头装多高". Required. |
| `params` | object | Optional retrieval knobs passed to the engine. |
| `query_mode` | enum(default/thorough/quick/guess) | Question-depth / answer mode (default "default"). |

## ks_collect（说明书 349 字）

抓取一个 URL 的正文，登记为该参考资料项目的一条待评审材料（pending）。先自己找原始出处网址再登记，评审由用户决定。纪律：① 一次一条（会话级上限，超出报错）；② 采到的是 T3=仅线索，不得单独支撑结论；③ 本工具不能批准——登记后如实告诉用户"未评审、不进结论"，请他决定；④ 只收网页正文（Content-Type 白名单 + 真实字节签名两道判据；PDF/图片/压缩包/JS/CSS/JSON 接口如实拒绝）——只给真正的网页地址，不给下载链接、接口地址或附件直链；⑤ 优先原始出处（政府/机构/期刊原文），不用转载/聚合页/内容农场。参数：url 必填；project_id 省略=本会话绑定项目（冲突时报错不代换）；title 自选；note 写清为什么值得采（评审人会看）。

| 参数 | 类型 | 说明 |
|---|---|---|
| `url`（必填） | string | 要采集的网页 URL（http/https；内网/保留地址会被 SSRF 纪律拒绝）。 |
| `project_id` | string | 目标参考资料项目 id（prj_…）。省略=用本会话绑定的项目。 |
| `title` | string | 材料标题（省略则取页面 <title>）。 |
| `note` | string | 采集说明：为什么采它、它与本次问题的关系（评审人第一眼看的就是这个）。 |

## ks_effect_report（说明书 238 字）

库内标准/法规的效力现状总览（效力报告）：四色统计（🔴在用已废止/被替代 · 🟡即将实施 · 🟢现行有效 · ⚪状态未知）+ 标准树/法规树分计 + 红/黄清单（各 top 10）。用户问"库里标准还有效吗/有没有已废止的/哪些即将实施/效力报告"时调用。attention_error 非空 = 红/黄清单没取到（统计仍有效，别当成"没有废止文件"）。列已废止标准时把 evidence_url 写成 Markdown 链接。只读零 LLM；完整清单在「效力总览」页。

| 参数 | 类型 | 说明 |
|---|---|---|
| `include_attention` | boolean | 是否附红/黄清单（默认 true）。只想要统计数字时传 false。 |
| `limit` | integer | 红/黄清单每色条数（默认 10，上限 20）。 |

## ks_materials（说明书 335 字）

列出参考资料项目与材料——只读。用户说"用我上传的财报/公司制度分析…"时，先按名字找 project_id，再作为 ks_answer 的 params.material_project_id 传下去（材料只有那样才进作答）。action：projects（默认，列项目）/ materials（列材料：review_status 三态、来源层级 T0~T4、任务效力 criterion=本任务准则/reference、切片数 + 三态计数）/ inbox（参考资料文件夹里尚未登记的文件）。只读：不能批/拒——评审是**用户**的判断（硬门）；有 pending 材料就如实告知"未批准、不进结论"。只有 approved 的材料会进 ks_answer 提示词。

| 参数 | 类型 | 说明 |
|---|---|---|
| `action` | enum(projects/materials/inbox) | projects（默认）=列项目；materials=列某项目材料；inbox=列未登记文件。 |
| `project_id` | string | 项目 id（prj_…）。action=materials/inbox 时必填。 |
| `status` | enum(pending/approved/rejected) | action=materials 时按评审状态过滤（省略=全列，含未批准）。 |

## ks_ping（说明书 414 字）

Probe the local KnowledgeStation engine; returns the live session (port/pid/reused) and the /api/v1/health payload (status/uptime/db_status/vector_engine/parser_worker). vector_engine is a CHEAP tri-state, not a load test: "ok" = model loaded at least once, "offline" = last load attempt failed, "unknown" = never attempted (the engine does NOT load the model just for a health check). Use before querying clauses.

| 参数 | 类型 | 说明 |
|---|---|---|

## ks_resolve_clause（说明书 457 字）

Resolve a "standard_no + clause_number" citation against the local KnowledgeStation library; returns matched clause ids/titles/text or an explicit not-found marker (args URL-encoded by the tool). Hits carry legal_status, evidence_url (clickable PDF anchor) and bookmarked. 查法规模式 on ⇒ a hit outside the bookmarks reports bookmarks_scope:"outside" (locating-only, never a 依据). 在本收藏夹内提问 active ⇒ likewise folder_scope:"outside" with the same locating-only ban.

| 参数 | 类型 | 说明 |
|---|---|---|
| `standard_no`（必填） | string | Standard / law full number, e.g. "GB 30871-2022" or "个人信息保护法". URL-encoded automatically. |
| `clause_number`（必填） | string | Clause number, e.g. "5.2.3", "第四百九十六条", "前言N", "表2". URL-encoded automatically. |
