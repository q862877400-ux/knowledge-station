# 测试索引（每个测试钉住了什么）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

`tests` = 每个 `def test*` 的名字、所在类、行号，以及它的 **docstring 第一句**（很多测试没 docstring，那就空着）。**名字本身就是本仓的覆盖说明书**（测试名写成中文描述）。

## 二、总账

| 项 | 数 |
|---|---:|
| 测试文件 | **184** |
| 测试函数 | **2,567** |
| 有 docstring | 1,419 |
| 没有 docstring | 1,148 |

> **这一份的用途**：想确认「某功能有没有被测试钉住」，按关键词在本文件里搜，
> 不用读测试体。测试名本身就是描述。

## 三、每个文件的测试清单

### `tests/test_ccs_chain.py`（58 个）

- `test_keyword_forms_ordered_full_to_bare` — 形式由**精确到宽泛**、且去重（业主：「完整标准号容易搜不到」⇒ 不许只赌一种）。
- `test_keyword_form_target_is_also_cleaned` — **关键词与匹配目标必须一起抠干净**（真机实测抓到的我自己的缺陷，回归哨兵）。
- `test_keyword_forms_strip_trailing_junk` — **尾部杂字**要能抠掉（真机 380 篇实测：真库标准号字段混着中文）。
- `test_two_digit_year_year4_form_matches` — 两位年代（`GB 228-87` = 1987 版）靠 `year4` 那档命中，且目标也是四位号。
- `test_not_a_standard_no_is_not_applicable` — **不像标准号的字段 ⇒ `not_applicable`，而且一次网络都不打。
- `test_other_edition_match_is_rejected_not_used` — **年份不同的他版不许当命中**（真机实测抓到的真缺陷，会打错标签）。
- `test_official_api_hit_reports_source_and_form` — 正例：官方接口命中 ⇒ `source=official_api` 且**记下**是哪种关键词形式命中的。
- `test_official_hit_never_calls_web_scrape` — **反向**：官方接口通了就**不许**再抓网页。
- `test_official_empty_falls_back_to_web_scrape` — **官方接口永远返回空 ⇒ 必须回退到网页抓取，且来源记为 `web_scrape`**。
- `test_keyword_form_escalates_when_full_form_misses` — 完整号搜不到时**继续试**别的形式，并把**真正中的那种**记下来。
- `test_html_block_anchored_on_standard_no_not_title` — 网页块必须按**标准号**（`ph_list_title`）切：号↔标题↔CCS 三者对得上。
- `test_local_table_hit_needs_no_network` — 人工核实表命中 ⇒ `source=local_table`，且**一次网络都不打**。
- `test_seed_file_hit_needs_no_network` — 种子文件命中 ⇒ `source=seed_file`（批量入库那条路：命中即零网络）。
- `test_use_network_false_is_local_only` — `use_network=False` ⇒ 只走本地（批量场景/离线重跑的口径）。
- `test_transport_error_is_network_failed_not_not_found` — **三层里网络层全炸 ⇒ `network_failed`**，绝不是"官方查无"。
- `test_answered_but_no_such_number_is_not_found` — 站点答了、解得出条目、里面确实没有这个号 ⇒ `not_found`（**不是** network_failed）。
- `test_broken_html_structure_is_parse_failed` — **两层都答了、却一层都读不出** ⇒ `parse_failed`，如实说"读不出条目"。
- `test_official_answers_clearly_so_not_found_even_if_scrape_broken` — 官方答得清清楚楚（条目列表里没有这个号）⇒ `not_found`，**不因网页那层读不出而改口**。
- `test_matched_number_without_ccs_says_so` — 站点**有这个号**、但那一行/那一条**没有分类号** ⇒ `parse_failed` 且原因说清是哪种。
- `test_empty_standard_no_is_not_a_network_failure` — 没有标准号 ⇒ 如实说"没有号"，**不许**记成网络失败（那会误导人去查网络）。
- `test_lowercase_site_code_becomes_readable_uppercase_tag` — 站点给**小写** ``a825`` 时，写出来的标签必须是**读得出来**的大写码。
- `test_record_and_apply_tag_are_idempotent` — 写台账 / 追加标签：**幂等**，且**不动**已有的别的标签。
- `test_record_failure_keeps_reason_and_leaves_tags_alone` — 未命中 ⇒ 台账记 `outcome` + `reason` + 流水，**domain_tags 一个字都不动**。
- `test_record_rejects_unknown_outcome` — 不认识的结论**当场报错**（不许静默写进一个没定义的状态）。
- `test_plan_finds_only_missing_ones` — 候选**算出来**：只挑 `doc_type='standard'` 且 `domain_tags` 里没有 `CCS:` 的。
- `test_backfill_writes_through_to_db` — **核心**：自愈跑完 ⇒ `domain_tags` 里**真的多了一条** `CCS:…` + 台账有来源。
- `test_backfill_rerun_is_noop` — **可重跑 / 幂等**：已经有分类号的篇不再进候选 ⇒ 再跑一遍 = 0 篇。
- `test_backfill_all_layers_dead_records_failure_in_db` — **变异②的口径**：三层全掐掉 ⇒ 台账必须**如实记**失败，而不是"什么都没有"。
- `test_backfill_cancel_is_honest` — **可中断**：按停 ⇒ 标志置上、没轮到的进 `skipped_list`，`cancelled` 如实。
- `test_backfill_busy_is_refused_not_queued` — **同一时刻只跑一批**：已有批次在跑 ⇒ `RuntimeError('ccs_backfill_busy')`（**不排队**）。
- `test_api_ccs_summary_and_plan` — `/kb/ccs/summary` 与 `/kb/ccs/plan`：只读、字段齐、**不联网**。
- `test_api_ccs_backfill_runs_and_reports_status` — `POST /kb/ccs/backfill` ⇒ 后台真跑。
- `test_api_inbox_reports_ccs_reason` — 「待分类」每篇带 `ccs_outcome` / `ccs_reason` —— 界面「没有建议要写明为什么」的依据。
- `test_api_ccs_plan_rejects_bad_limit` — 非法 `limit` ⇒ 422（不许静默按默认值跑）。
- `test_ingest_records_ccs_source` — 真跑一次入库 ⇒ 标签进 `domain_tags`、**来源进台账**（"每篇都要能说出是哪一层命中的"）。
- `test_ingest_records_failure_not_silence` — **反向（本次重做的核心）**：那条链失败时，台账**必须**留下结论与原因。
- `test_undo_journal_is_written_before_the_first_write` — **先备份、后写库**：第一次网络查询发生时，回退记录**已经在盘上**、。
- `test_undo_journal_honours_ks_backup_dir` — 回退记录落在**既有快照那个备份目录**，并**尊重 ``KS_BACKUP_DIR`` 覆盖**。
- `test_backfill_refuses_to_start_when_journal_write_fails` — **回退记录写不成 ⇒ 一篇都不写、当场报错**（"备份失败但照写"是明令禁止的）。
- `test_revert_restores_tags_and_ledger_verbatim` — **回退真能退**：``domain_tags`` 与 ``doc_ccs_state`` **逐字**回到改前。
- `test_revert_twice_is_safe` — **回退两次是安全的**（幂等）：第二次一篇都不动，如实记"已经是改前的样子"。
- `test_revert_does_not_touch_docs_outside_the_batch` — **反向判据**：回退只动这一批记录里的篇 —— 没被选中的篇（含"也是缺号"的那些）。
- `test_missing_split_partitions_and_tracks_each_bucket` — ``missing_split`` **五桶之和 == total**，且每一桶按台账 ``outcome`` 如实归类。
- `test_stop_reason_limit_selected_done_and_no_candidates` — **为什么停：各是各的值**（业主要求"不许合并成一个结束"）。
- `test_selected_batch_cut_by_limit_says_limit_not_selected_done` — **F1（复核 MED，2026-09-24 修）**：勾选批次被 ``limit`` 截过 ⇒ 说"到量"，。
- `test_decide_stop_reason_truth_table` — **七个值互斥且各是各的**：决策函数按优先级取一个（不许有"两个都对"的糊账）。
- `test_revert_also_restores_updated_at` — **F2（复核 MED，2026-09-24 修）**：回退要把 ``updated_at`` 也**逐字**退回去。
- `test_db_path_is_honoured_by_the_worker_thread` — **F3（复核 LOW，2026-09-24 修）**：``db_path`` 必须一路传到**干活线程**。
- `test_broken_domain_tags_is_refused_not_silently_wiped` — **F4（复核 LOW，2026-09-24 修）**：``domain_tags`` 非空却不是 JSON 数组 ⇒ **拒改**，。
- `test_stop_reason_exhausted_when_plan_had_no_remainder` — ``exhausted`` = **候选扫完了**（计划里没有剩余候选），不是"全库都补上了"。
- `test_all_mode_pages_serially_and_stops_at_hard_cap` — **「全部补完」**：按 ``MAX_BACKFILL_DOCS`` 一页一页串行，撞硬上限就停，**如实说**。
- `test_all_mode_refuses_doc_ids_and_allows_zero_limit` — ``all`` 与勾选篇目**不能同时用**（两件事）。
- `test_apply_ccs_tag_replaces_instead_of_appending` — **HIGH-1**：同一篇**只许有一条** ``CCS:`` 标签 —— 换号是**替换**（就地），不是追加。
- `test_force_refresh_tag_and_tree_read_the_same_code` — **HIGH-1 的端到端判据**：``force=True``（刷新）之后，**台账与分类树读到同一个码**。
- `test_backfill_classifies_exceptions_by_type_not_all_network` — **MED-1 + MED-2**：异常**按类型如实归类并落台账** —— 代码缺陷**不许**冒充网络问题。
- `test_run_loop_error_does_not_wedge_running_and_lock` — **MED-5**：循环体外的异常**不许**把 ``running`` 与锁永久卡死。
- `test_api_ccs_summary_reports_stop_reasons_and_split` — ``/kb/ccs/summary`` 把"还剩多少（拆开）"与"为什么停"的说法**由后端下发**。
- `test_api_ccs_backfill_all_flag` — ``POST /kb/ccs/backfill {"all": true}``：分页跑到硬上限并**如实**说停在硬上限。

### `tests/test_material_harvest.py`（57 个）

**TestSsrfGate**

- `test_loopback_is_refused_and_nothing_is_fetched` — **最重要的一条**：内网地址在**抓取之前**就被拒，且不建材料。
- `test_private_and_non_http_are_refused`
- `test_blank_url`
**TestHappyPath**

- `test_fetches_and_registers_as_pending`
- `test_title_comes_from_the_page`
- `test_caller_title_wins`
- `test_script_and_style_do_not_become_content` — 页面里的 JS/CSS **不能**进正文（采集最脏的来源）。
- `test_note_records_the_fetch`
- `test_same_page_twice_is_a_duplicate`
- `test_injected_transport_is_used` — 不需要真网络：注入一个假 transport 就能测通路。
- `test_content_type_is_recorded_for_the_reviewer` — Content-Type 进 `tier_reason`：判据**可见**，评审人能自己复核白名单判得对不对。
- `test_missing_content_type_is_stated_honestly` — 服务端没给 Content-Type ⇒ 放行，但**如实写明"未给"**（不是假装检查过）。
- `test_text_plain_page_is_accepted` — 纯文本通知（`text/plain`）是**合法**的资料来源，白名单必须放它。
**TestNotAPageIsRefused**

- `test_non_page_content_types_are_refused`
- `test_real_bytes_gate_catches_a_mislabeled_png` — **Content-Type 撒谎说自己是 html**：只有真实字节能认出 PNG。
- `test_real_bytes_gate_catches_a_mislabeled_pdf`
- `test_the_type_gate_is_not_bypassed_by_a_title` — 调用方给了 title 也不能让"不是网页"的东西变成材料（标题不是通行证）。
- `test_content_type_header_key_case_does_not_skip_the_gate` — 响应头的**键名大小写**不许决定白名单是否生效（2026-09-17 复核 E 的 LOW）。
**TestTransportContractIsStrict**

- `test_transport_without_fetch_page_is_refused_loudly` — **严格**契约：只有 `fetch`（拿不到 Content-Type/真实字节）的 transport ⇒ 拒绝。
**TestFailsLoudlyAndRegistersNothing**

- `test_bad_responses_do_not_create_material`
- `test_transport_exception_is_reported_not_raised`
- `test_404_does_not_register`
**TestTruncation**

- `test_long_page_is_truncated_and_says_so`
**TestNoProductionBypass**

- `test_collect_url_has_no_private_allow_switch` — **结构性约束**：不得存在"允许内网"之类的参数（那是给严格版开后门）。
- `test_it_calls_the_ssrf_owner_exactly_once_per_url` — **行为**断言（不是"源码里有这个字符串"）：判据真的被调、且每跳都调。
- `test_the_ssrf_verdict_actually_gates` — 判据的结论**真的**决定结果：换成"一律拒绝"的替身 ⇒ 连公网地址也不抓。
- `test_no_second_address_judgement_in_the_module` — 粗护栏（**不是**上面那条行为断言的替代品）：本模块不自己解析地址。
**TestRedirectsAreNotFollowed**

- `test_contract_forwards_allow_redirects_false` — `allow_redirects=False` 是**承重**的（`page_transport` 内部就断言了这一点，。
- `test_http_is_retried_on_https_same_host`
- `test_redirect_after_upgrade_is_refused_not_followed`
- `test_https_url_that_redirects_is_refused` — https 没有可升级的空间 ⇒ 直接拒绝（不给"再试一次"的假动作）。
- `test_https_upgrade_only_changes_the_scheme`
- `test_real_transport_does_not_follow_a_redirect` — **真实传输**下的证明：本地 302（Location 指向内网元数据端点）拿到的是 **302 本身**。
**TestEmptyReasonDistinguishesTwoKinds**

- `test_original_body_empty` — **原文本身为空**（连标签都没有）→ 原因串说"响应为空"。
- `test_tag_only_body_is_reported_as_converted_empty` — **原文非空但转换后为空**（只有标签）→ 原因串必须说清是"转换后"为空。
- `test_nonempty_body_that_becomes_empty_after_conversion`
**TestHtmlToTextOwner**

- `test_equivalent_to_clause_health_without_script_or_style` — 规范实现与既有 `clause_health_html_to_text` 逐字符等价——**除两条有意差异**。
- `test_deliberate_difference_on_uppercase_table_tags` — **有意差异②**：大写 `</TD>`/`</TR>` 在本函数里照样转表格分隔。
- `test_deliberate_difference_on_script_and_style` — **有意不同**：本函数丢掉 script/style 的**内容**（那三份不会）。
**TestScriptStyleStrippingEdges**

- `test_html5_semantics_slash_does_not_self_close` — **HTML5**：`<script src="a.js"/>` 里的 `/` 被忽略 ⇒ 到 `</script>` 之间是**脚本**。
- `test_style_self_closing_slash_also_does_not_self_close` — 同一条语义的 style 版：`<style/>` 之后的可见文字**属于样式内容**，浏览器不显示。
- `test_html_comment_does_not_hide_a_script_from_the_sweep` — **OVERKILL-1**（复核 D②）：注释里的 `<script>` **不是标签**，不许吞掉其后正文。
- `test_end_tag_with_junk_is_recognized` — **OVERKILL-2**：`</script foo>` 是浏览器接受的结束标签，第一版认不出 ⇒ 吞掉其后正文。
- `test_literal_script_inside_an_attribute_is_not_a_tag` — **OVERKILL-3**：属性值里的字面 `<script>` 不是标签（否则其后正文被吞）。
- `test_literal_script_in_an_UNQUOTED_attribute_is_not_a_tag_either` — **OVERKILL-4**（2026-09-17 复核 LOW 顺带实测，v3 修）：**无引号**属性值同理。
- `test_a_bare_less_than_in_the_text_does_not_disable_the_sweep` — **上面那条守卫的风险方向**：正文里的裸 `<` **不许**让真 `<script>` 变成文本。
- `test_the_guard_runs_on_the_ORIGINAL_string_not_a_rewritten_one` — **顺序是承重的**（2026-09-17 独立复核 b7 的 MEDIUM）。
- `test_only_the_raw_text_families_browsers_hide_are_stripped` — **真机裁决**：这一族里只有三个是"浏览器不显示"的（复核 b8 的 LOW-5 → b9 的 MEDIUM-4）。
- `test_script_inside_raw_text_elements_is_text_not_a_tag` — **raw text 元素里的字面 `<script>` 是文字**（复核 b10 的 LOW-1，2026-09-18 修）。
- `test_raw_text_guard_is_not_opened_by_attribute_values_or_nesting` — **守卫不许被打开**：两种形状里那个"raw text 元素"都不是真元素（复核 b12 的 MEDIUM-1）。
- `test_real_script_outside_raw_text_is_still_stripped` — **反向对照**：元素**外面**的 `<script>`/`<style>` 仍必须剥掉。
- `test_guard_requirement_one_is_load_bearing` — 守卫的**要求①**（`<` 之后必须紧跟字母或 `/`）是**承重的**，必须有正面用例。
- `test_unclosed_script_swallows_the_tail_like_a_browser` — 未闭合 ⇒ 其后全部是脚本文本（HTML5），**不得**把 JS 当正文留下来。
- `test_unclosed_style_swallows_the_tail`
- `test_uppercase_and_mixed_case_tags` — **大小写敏感性要有钉子**（独立复核 M3 变异体 GREEN：原先零覆盖）。
- `test_close_tag_inside_a_script_string` — 脚本里的字符串含 `</p>` 这类片段**不能**骗过剥离（用闭合标签本身定位）。
- `test_normal_closed_tags_still_work`

### `tests/test_channel_repo.py`（49 个）

**Test号段列与读写**

- `test_表里真的有号段列`
- `test_补列清单必须包含号段列`
- `test_写入读回_并归一`
- `test_写入坏形状要抛且不动原值`
- `test_种子导入也能带号段` — 种子（`_DESCRIPTIVE`）与人工写走同一条校验 ⇒ 不允许多一条绕过路径。
**TestCategoryNormalization**

- `test_已知写法都能归一`
- `test_未知写法落_other_且调用方保留原文`
**TestCrud**

- `test_插入_读取_列出_删除`
- `test_拼错字段要抛而不是静默丢`
- `test_非法类别要抛`
- `test_缺_name_的新建要抛`
- `test_更新保留未提到的字段`
- `test_启停不删数据`
**TestHealthSemantics**

- `test_ok_清零失败计数并记_last_ok`
- `test_suspicious_也算失败` — R1 的 G14：应急部标准页 465B、bzw 列表页"共0条" —— **200 不等于有数据**。
- `test_unknown_只记尝试`
- `test_非法状态与不存在的渠道都要抛`
- `test_summary_把注册数与能力数分开报` — 本模块最重要的一条口径：total 是台账条数，by_wiring['wired'] 才是能干活条数。
**TestSeed**

- `test_导入幂等且不覆盖健康度`
- `test_显式_overwrite_health_才覆盖` — `overwrite_health=True` = 允许 payload 里的健康度字段落库（默认一律不落）。
- `test_种子文件缺失或格式坏要抛`
**TestApi**

- `test_列表带_summary_且能按类别筛选`
- `test_非法筛选值要_422_而不是空结果`
- `test_limit_越界要_422`
- `test_单条详情_不存在要_404`
- `test_每条都带_has_probe_target` — R6：面板要能分开「⚪ 无探针」与「⚪ 还没探过」——否则灰行读不出该不该动手。
- `test_探测端点_不存在的_id_要_404` — `POST /api/v1/channels/probe`：ids 里有台账里没有的 → 404（不是静默跳过）。
- `test_探测端点_ids_类型不对要_422`
- `test_探测端点_只探配了目标的渠道` — ⚠ 关键口径：不传 ids 时**只探有探针目标的**（今天 28 条），绝不盲探 131 条。
**TestShippedSeed**

- `test_种子可读且_id_唯一`
- `test_兜底链现状_web_已摘除_govcn_已换棒` — R1 的 G6 抓出**两根**死兜底棒。
- `test_降级链里不再有已知失效的渠道` — 链上的每一棒都必须是"能用"的：`broken` 在种子里应为 0。
- `test_接线名字不一致的渠道已在种子里记明` — R2 发现 G23（注册表键 `ttzb` vs 适配器名 `ttbz`）。
- `test_能力数远小于台账条数` — 口径用例：如果哪天这两个数相等，说明有人把"调研到"当成了"能干活"。
- `test_种子号段形状与大小写` — 每条的 `segments_json` 必须是**非空字符串数组**、无前后空白/重复。
- `test_已声明号段不许是死号段` — 拿**真库形状**的号表量每一个已声明的号段：一个号都不命中 ⇒ 红。
**Test单位性质**

- `test_表里真的有单位性质列`
- `test_补列清单必须包含单位性质列`
- `test_枚举校验_坏值出声拒绝`
- `test_关键词粗分类回填`
- `test_人工标的永不被回填覆盖`
- `test_回填幂等`
**Test渠道已知文件测试**

- `test_配样本与读回`
- `test_没配样本直接说没配`
- `test_拉到并认出_比对通过_留痕_ok`
- `test_认出但对不上_留痕_fail`
- `test_拉取失败与没认出_都留痕_fail`
- `test_识别口径_常见号都能认_大小写横竖线比对归一`
- `test_classify_org_kind_second_pass_on_real_names` — 分类补准判据（2026-09-22 第二轮）：60 条首版未命中真名的代表例逐条归位。

### `tests/test_material_api.py`（48 个）

**TestAuthAndValidation**

- `test_requires_token`
- `test_create_project_needs_name`
- `test_authority_policy_must_be_object`
- `test_unknown_project_is_404`
- `test_bad_status_filter_is_422`
- `test_tiers_endpoint_lists_all`
**TestEndToEnd**

- `test_scan_review_read_then_searchable` — 建项目 → 丢文件 → scan → 读切片 → 搜到。
- `test_inbox_lists_dropped_files`
- `test_reject_removes_from_search`
**TestAxesAndLifecycle**

- `test_tier_change_is_用户可改_and_recorded`
- `test_bad_tier_is_422`
- `test_role_criterion_is_settable_and_searchable` — 公司制度例走 API：来源层级不高，但**是本任务的准则**。
- `test_bad_role_is_422`
- `test_lifecycle_promote`
- `test_delete_removes_material`
**TestCollectEndpoint**

- `test_unknown_project_is_404`
- `test_missing_or_blank_url_is_422`
- `test_source_tier_is_refused_loudly_and_registers_nothing` — **采集者不得自 claim 可信度**（轴 A 只能由系统判据起或用户改）。
- `test_unknown_body_keys_are_refused_not_ignored` — **未知字段一律拒绝**（2026-09-17 复核 A 的 MEDIUM）。
- `test_ssrf_refusal_is_a_reason_not_an_error_code` — SSRF 拒绝对是**本次**抓取的结果，不是"你的请求写错了"⇒ 200 + 原因。
- `test_fetch_registers_pending_then_approval_makes_it_searchable` — 端到端：**采集 → 待评审 → 检索不到 → 批准 → 检索到**。
- `test_binary_response_is_refused_over_the_route` — "不是网页正文"在**路由层**也挡住了（两条判据：Content-Type 白名单 + 真实字节）。
- `test_mislabeled_binary_is_refused_by_real_bytes` — Content-Type 撒谎（说自己是 html）也挡得住——判据落在**真实字节**上。
- `test_route_does_not_offer_a_batch_entry` — **结构性约束**：不得存在批量采集入口（预算/频率上限未定，方案 §11.4）。
**TestApprovalTriggersTrackL**

- `test_standard_material_is_imported_on_approval`
- `test_plain_material_is_skipped_on_approval`
- `test_rejection_does_not_run_track_l` — 拒绝**不触发**：返回体里连 `track_l` 键都不该有（"没决策"与"决策=skip"是两回事）。
- `test_track_l_failure_is_reported_not_raised` — Track L 抛错**不改写评审结果**，但必须在 `data.track_l` 里如实报出来。
**TestSlowEndpointsAreDeclaredSync**

- `test_declared_sync` — 这条路径上**这个 HTTP 方法**的端点必须是 `def`（线程池），不能是 `async def`。
- `test_async端点必须在显式名单里` — **通则（§10.87）**：`/api/` 路由上的每条 `async def` 端点都必须在 `_ASYNC_ENDPOINTS`。
- `test_端点上不许用_asyncio_to_thread` — **通则之三（§10.93）**：`/api/` 端点不许用 `asyncio.to_thread` / `run_in_executor`。
- `test_名单里的_async_端点要么量过要么写明不可量` — **量具接名单（第二层，§10.94）**：名单里的每条 async 端点，要么被**量**过，。
- `test_T1_零await的async端点必须是def` — **通则之一（§10.86，修复核 b15 的 MEDIUM-1）**：`async def` 且源码里**没有任何。
- `test_async_endpoints_that_only_read_body_are_not_heavy` — **通则之三（T2）**：`async def` 端点若**唯一的 `await` 只是读 body**（或没有 await），。
- `test_名单第二关的判据_effective_real_await` — §10.88：名单第二关的判据在**六种形状**上都必须判对（b17 的 MEDIUM-2 + MEDIUM-3）。
- `test_def端点返回StreamingResponse仍然真流式` — §10.89（独立复核 b18 的 MEDIUM-1）：**`def` 端点也能真流式** —— 这是判据的前提。
- `test_内联递归的深度上限被唯一钉住` — §10.90/§10.91（独立复核 b19 的 N4 + b20 的 N2）："深度上限 = 4" 必须被**唯一**钉住。
- `test_判据本体的边界样本` — §10.86：两条判据的**边界形状**（b15 的 INFO-1 / INFO-3）。
- `test_nested_async_generators_without_await_are_rejected` — **通则之二**：端点里嵌套的 `async def` **生成器**若**一个 `await` 都没有** ⇒ 红。
- `test_没有函数叠着两个_docstring` — **结构判据**：一个函数/类体里不许**连着两个字符串常量语句**（b14 的 LOW-3）。
- `test_两条通则的判据走_AST_不会被注释骗` — §10.85：判据本身也要验——**注释不是行为**（独立复核 b14 的 MEDIUM-2）。
- `test_嵌套生成器判据只数自己作用域` — §10.86 自查：`yield`/`await` 必须只数**该函数自己作用域**里的。
- `test_module_has_no_async_endpoint` — **文件级**闸门：这些模块注册的端点，**一个都不许是 `async def`**。
**TestEndpointIndexMatchesReality**

- `test_docstring_index_equals_registered_routes`
**TestLocatorEndpoints**

- `test_project_summary_and_single_health` — ⚠ **不抓网**：材料直接用 `collect_text` 造（离线也要能验端点形状）。
- `test_old_material_shows_up_as_unknown_in_the_summary` — 老材料（入库时没记指纹）在总览里算 **unknown** ——**不假装 ok**。
- `test_unknown_material_is_404`
- `test_reverify_reports_unavailable_without_a_source_file` — **没有留存源文件** ⇒ `unavailable`（不是 match）——这条语义必须在端点上如实。

### `tests/test_update_inspector.py`（47 个）

- `test_ins_a_01_smoke_five_effective_done` — /INS-A-01 5 号全现行：pending→running→done，checked=total=5，green=5 余 0。
- `test_ins_a_02_concurrency_two_pairwise` — /INS-A-02 峰值并发恒=2，按清单序两两成组推进。
- `test_ins_a_03_pause_resume_monotonic` — /INS-A-03 running 中 pause → paused → resume 续跑，checked 单调不回退。
- `test_ins_a_04_resume_from_checkpoint_no_dup_events` — /INS-A-04 跑到 3/10 断点（模拟进程重启），resume 自第 4 号续扫且无重复事件。
- `test_ins_a_05_timeout_retry3_then_failed` — /INS-A-05 单号 delay31>30s：预算 3 次耗尽记 failed，不阻塞他号、不误降级。
- `test_ins_a_06_resume_missing_batch_404` — /INS-A-06 不存在的 batch_id：UPD-2003 且零副作用。
- `test_ins_a_07_chaos_persistent_error_reaches_terminal` — /INS-A-07 第 2 号持续异常：终态 done+finished_at，无挂死，审计齐全。
- `test_ins_a_08_sqlite_exception_isolated` — /INS-A-08 中途注入一次 SQLite 异常：异常号隔离，其余照跑，批次可达 done。
- `test_ins_a_09_terminal_batch_refuses_restart` — /INS-A-09 终态批次：check/resume 拒绝重启，重复 pause 幂等返回同状态。
- `test_anom001_all_channels_unreachable_failed_not_done` — /ANOM-001 回归：三渠道全程不可达（生产 SSL EOF 场景）→ 批次终态 failed，。
- `test_ins_c_01_captcha_pauses_not_gray` — /INS-C-01 captcha=true：批次 paused、该号不计 gray/failed、聚合告警落库。
- `test_ins_c_02_resume_retries_same_number_first` — /INS-C-02 过点后 resume：同一号优先补查成功，批次续跑至 done。
- `test_ins_c_03_scheduler_never_auto_resumes_captcha` — /INS-C-03 paused 批次等一个调度周期：定时器不得自动 resume 验证码/人工暂停。
- `test_ins_c_04_three_captchas_one_aggregated_pause` — /INS-C-04 连续 3 号验证码：合并单次暂停一条告警。
- `test_ins_c_05_interleaved_pause_resume_state_machine` — /INS-C-05 交错 pause×2 / resume×2：无非法迁移，resume 生效一次不重复扫描。
- `test_ins_d_01_effective_green` — /INS-D-01 现行 → green，current_legal_status='effective' 落库。
- `test_ins_d_02_upcoming_treated_current` — /INS-D-02 upcoming 有新版：legal_status 如实 'upcoming'，不触废止对比流程。
- `test_ins_d_03_superseded_red_per_directive` — /INS-D-03 被代替(superseded) → 红（批次2指令：废止/替代→red。
- `test_ins_d_04_withdrawn_red` — /INS-D-04 废止 → red + change_type=withdrawn。
- `test_四棒链的最后一棒不被预算截断` — §11.0 R6c-3e：**链长 4 > MAX_ATTEMPTS(3) 时最后一棒以前永远探不到**（复核 b34 实测）。
- `test_单根链的重试预算不变` — 改预算是 `max(MAX_ATTEMPTS, len(链))` ⇒ **短链行为一字不变**（单根链仍有 3 次预算）。
- `test_某根棒抛异常不挤掉后面的棒` — §11.0 R6c-3f（复核 b36 的 D-新问题）：**全链共享重试池**会让异常吃掉后面的棒。
- `test_台账停用的渠道巡检不再问它` — §11.0 R6h：台账里 `enabled=0` 的渠道**真的不会被问**。
- `test_号段声明的渠道巡检真的会问它` — §11.0 R7：台账里**号段**声明的渠道，巡查**真的会去问**（接线，不是助手）。
- `test_全链都抛异常才算failed` — 每根棒各自重试到上限。
- `test_五类结论记进同一条事件` — §11.0 R6c-4c：**五类结论记进那一条事件的 `latest_info`**（不新增列、不写 ×5 条）。
- `test_灰号的五类记录说清为什么没答` — 整链都没命中（灰）也要能回答"五类各自为什么没答"（§11.0 R6c-4c）。
- `test_台账记down但真答了_五类仍如实记answered` — ⚠ 复核 b37 的 C 项（它列为最高风险）：**归因不能看台账 state**。
- `test_台账读失败要出声` — ⚠ 复核 b37 的 B 项：台账读失败时**零告警** ⇒ 与"本来就不该记"不可区分。
- `test_结构性unanswerable_不算done` — §11.0 R6c-4d：五类里有**结构性答不出来**（`no_capability`/`off_chain`）的号 ⇒ 批次不算 done。
- `test_提交后被杀_欠账从事件行收回` — §11.0 R6c-4e：**已提交号**的结构性欠账，在"进程被杀 → pause → resume"后仍要算数。
- `test_only_not_probed_不出现在unanswerable` — ⚠ **`not_probed` 不许算进 `classes_unanswerable`**：那是"这次没轮到问"，不是"答不出来"。
- `test_ins_d_05_all_channels_miss_gray` — /INS-D-05 三渠道查无 → gray，legal_status 保持 NULL，末渠道 govcn 兜底。
- `test_ins_d_06_illegal_enum_rejected_not_silent` — /INS-D-06 非法枚举：CHECK 拒绝+回滚零脏行。
- `test_ins_d_07_replay_dedup_counts_not_doubled` — /INS-D-07 相同 mock 序列重放判定：跨批同 doc 同结论跳过建行，计数不翻倍。
- `test_ins_d_08_mixed_twenty_identity` — /INS-D-08 20 号混合四态：恒等式成立，已知样本判定全部正确。
- `test_retry_within_channel_before_degrade` — /INS-B-06 编排层复核：前 2 次异常第 3 次命中 → 不提前降级仍由 official_gb 完成。
- `test_tier_selection_watch_and_first_check` — tier0 = watch_list ∪ 未首检。
- `test_tier_selection_doc_bookmark` — 增强③遗留（B 方案）：user_doc_bookmark（标准收藏）并入 tier0 高频巡检。
- `test_budget_override_stop_and_next_day_resume` — 万级预算：覆盖值=3，当日达预算停留待次日，次日调度器恢复续跑。
- `test_budget_default_500_when_unconfigured` — 默认 daily_full_sweep_budget=500（35k ÷ 500 ≈ 70 天一轮）。
- `test_scheduler_creates_due_batches_once` — schedule_days 到期自动建批（scheduled），周期内不重复建。
- `test_scheduler_backdated_due_again` — 距上次 scheduled 建 ≥N 天再次到期。
- `test_scheduler_disabled_when_zero` — schedule_days≤0 视为关闭调度。
- `test_scheduler_thread_lifecycle` — 轮询线程 start/stop 存活冒烟（2s 模式，测试用 50ms 加速）。
- `test_tier0_includes_subscribed_domain_docs` — F-13/A15：订阅'消防'后，已首检的消防域标准被重新提入 tier0。
- `test_inspect_lists_exclude_laws` — 法规（doc_type='法律法规'）不进查号巡检（无国标号，时效走 flk 溯源检查）。

### `tests/test_ledger_chain.py`（46 个）

**Test过滤**

- `test_人工停用不进链`
- `test_known_broken_不进链`
- `test_探针说_down_也不过滤` — R6a 实测：down 的 13 条里混着瞬时/WAF/我方 TLS 指纹 ⇒ 按一次探针踢渠道会让链抖动。
- `test_台账里没有的成员保留_fail_open` — 没 seed 的库不该让巡检失去整条链。
- `test_顺序就是名单顺序`
**Test成员资格不是wired**

- `test_wired_不等于兜底成员` — 核心回归：`wiring='wired'` 的专用渠道**不许**被自动塞进兜底链。
- `test_候选要被报出来而不是被悄悄提升`
**Test一致性报告**

- `test_名单里有代码里没有的适配器要报出来且不进链` — 独立复核 b29 抓到的欠账：`known` 参数原先承诺过却没用（`_ = known` 是死代码）。
- `test_名单重复成员去重且要告警` — 复核 b29-fix 的 a：不去重的话链里会出现两次同名（巡检白跑一遍）而没人知道。
- `test_名单成员在台账里没有行要提一句` — 复核 b29-fix 的 b：按设计 fail-open 保留，但不能一个字都不说。
- `test_写法差异也要被挡住` — 复核 b29-fix 的 c：`BROKEN` / `'0'` 这类写法差异过去会让"已知失效"照旧留在链里。
- `test_这些不算停用` — `None`（没写）/`True`/`1`/`'1'` 都不是"停用"——别把缺失读成人工意图。
- `test_生成器名单也照收` — 复核 b29-fix2 的坑：生成器只能消费一次，而 report 要遍历它好几遍 ⇒ 入口先固化。
- `test_重复成员的报告不重复列`
- `test_台账说wired但代码里没有适配器要报出来`
- `test_非适配器渠道不参与缺失判定` — `seed:law-cn:*` / `tool:*` 本来就不是适配器名，不该被报成"台账/代码不一致"。
- `test_wired_且探针_down_要报出来`
**Test真库**

- `test_缺省名单下真库过滤后等于今天的链`
- `test_真库报告里不含种子外的噪音`
- `test_专用渠道在候选里而不在链里` — 前缀专用渠道（DB→dbba、行标→hbba）**不在泛查兜底链里**，所以是"可提升候选"。
- `test_ndls_已毕业进兜底链` — R6c-3b：`ndls` 从"可提升候选"变成"链上成员"，这条正面钉住它别再被挪走。
**Test巡检真的按台账走**

- `test_人工停用让巡检不再问它` — `enabled=0` ⇒ 该渠道**从巡检的链里消失**（不只是面板上显示停用）。
- `test_known_broken_让巡检不再问它`
- `test_前缀首选也受台账管` — 前缀首选（HJ→`mee`）同样受过滤：人工停用它，HJ 号就退回泛查链。
- `test_没有台账行时不过滤也不读库` — `rows=None` ⇒ 原样返回 `select_chain`（**不读库、不 I/O**）。
- `test_台账缺该行则保留_fail_open` — 台账里**查不到**某成员 ⇒ 保留（fail-open）：没 seed 的库不该让巡检失去整条链。
- `test_不做加法_只做减法` — 台账 `wired` 但**不在** `select_chain` 里的渠道，不会因为这个函数进链。
**Test号段加法**

- `test_号段命中就多一根尾巴` — `mee` 声明 `GB` ⇒ GB 号在泛查链之后多问一根 `mee`（今天它一条 GB 号都到不了）。
- `test_只加尾巴_路由链顺序不动`
- `test_号段不许把人工停用的渠道加回来` — **加法与过滤的正确交互**：`ndls` 被停用、但它也声明了 `GB` ⇒ 不许被加回链尾巴。
- `test_号段不命中就没尾巴`
- `test_代码里没有的适配器不进链`
- `test_已经在前缀首选里的渠道不会重复出现` — `HJ` 号本来就首选 `mee`，`mee` 又声明 `HJ` ⇒ 链里只出现一次（去重）。
- `test_rows_None_时也不做加法且不读库` — 没有台账行 ⇒ 既不过滤也不加法（fail-open 的同一条口径）。
- `test_号段匹配口径`
- `test_号段顺序确定_同一库上可复现` — 尾巴顺序 = 台账顺序（`list_channels` 的 ORDER BY category,name）⇒ 链不抖。
**Test号段报告**

- `test_死号段被点名` — 写了 `T/` 而真库里一个 T/ 号都没有 ⇒ 必须报出来（否则"渠道永不进链"没人知道）。
- `test_没给号表就说判不准_不假装没欠账` — **不给号表**（`[]`）⇒ `dead`/`gained` 一律不下结论，并在 `note` 里说清。
- `test_有适配器却到不了也没号段要列成待办` — 这就是 R6g 那 10 条的形状：有适配器、今天任何号都到不了、也没声明号段。
- `test_号段带来的号数按号去重` — 多个号段命中同一个号只算一次（否则"带来多少号"虚高）。
- `test_被排除的行不计入带来多少号` — 人工停用的渠道不该在"带来多少号"里贡献数字（那是虚高）。
**Test号段形状校验**

- `test_非数组被拒`
- `test_空项或非字符串被拒`
- `test_归一_去空白_保序去重`
- `test_None_表示清空`
- `test_读路径容错_坏值给空元组而不是抛` — 库里的历史脏数据不许把巡检弄炸（写路径拒绝、读路径容错）。

### `tests/test_dryrun_report.py`（43 个）

- `test_verdict_pua_mangled_blocks` — 乱码（适配器判定的 PUA 错位不可修复）→ block B1。
- `test_verdict_collapse_blocks` — 正文 ≥2000 字却切不出条款 → block B2（坍缩）。
- `test_verdict_weird_ratio_blocks` — 异常字符占比 ≥30%（采样窗口之外的乱码，适配器采样不到）→ block B5。
- `test_verdict_replacement_ratio_blocks` — 替换字符 U+FFFD 占比 ≥5% → block B6（与 B5 不同：FFFD 属正常区符号）。
- `test_verdict_preview_never_asks_for_deep` — **零外发**的关键断言：预览必须传 deep_fallback=False 且 force_deep=False。
- `test_verdict_scan_warn_when_deep_skipped`
- `test_blk_severe_skew`
- `test_blk_sparse_pages`
- `test_blk_fragmented_not_blocked` — 碎片化文本（120 行 3 字词）**不判 block**——它切出一条「前置说明」，字数也没到坍缩线。
- `test_blk_broken_file`
- `test_blk_missing_file`
- `test_blk_wrong_suffix`
- `test_blk_good_doc_not_blocked`
- `test_blk_pua_recovered_not_blocked` — 可归一化修复的 PUA 错位必须被救回（否则白走 OCR 丢字）。
- `test_blk_scanned_is_warn_not_block` — 扫描件（无文本层）应当是 warn + 零外发，不是 block。
- `test_blk_multipage_scan_is_warn_not_block` — **多页**扫描件同样只 warn：B4「近乎空白」不得对"无文本层"开火。
- `test_blk_straight_not_flagged` — 正排（θ=0）不许出现倾斜判据。
- `test_blk_mild_skew_warns_not_blocks` — 2° 轻度倾斜 → warn（W2），不 block。
- `test_verdict_clean_is_ok`
- `test_verdict_mixed_skew_blocked_by_page_ratio` — B3 第二支：文档中位倾角未到 3°，但**多数页各自严重倾斜** → 仍须拦。
- `test_verdict_skew_boundary_2_9_warns_3_0_blocks` — 倾斜阈值边界：2.9° → warn(W2)。
- `test_verdict_missing_metric_never_blocks` — 缺失度量不得触发 block（docstring 承诺）：无 chars_per_page 时 B4 不得开火。
- `test_verdict_weird_ratio_boundary` — 异常字符率边界：29.9% 不拦。
- `test_verdict_replacement_boundary_and_zero` — 替换字符率边界：0% 不拦、4.99% 不拦、5% 拦。
- `test_verdict_collapse_boundary` — 坍缩边界：chars=1999 不拦、2000 且 clauses=1 拦、2000 且 clauses=2 不拦。
- `test_verdict_sparse_pages_boundary` — 近乎空白边界：4 页不拦（下限 5）、5 页且 19.9 字/页拦、20 字/页不拦。
- `test_verdict_w3_suspect_ratio` — W3 可疑条款占比（verifier 审计：原无覆盖）。
- `test_verdict_w5_low_type_confidence` — W5 分型置信度偏低（原无覆盖）。
- `test_verdict_w10_low_clause_density` — W10 条款密度异常偏低（原无覆盖）。
- `test_verdict_duplicate_warns` — W6 与库内重复 → warn（不 block：重复是可覆盖的正常情形）。
- `test_grade_boundaries` — 分级边界（R13 契约）：0.95→A、0.85→B、0.8499→C。
- `test_clause_ocr_confidence_units` — 条款级置信度的扣分项（含原不可达的 tiny 与不可打印字符）。
- `test_clause_head_is_raw_prefix` — `head` 必须**逐字符**等于原文前 80 字（证据文本不可变红线。
- `test_preview_table_tags_are_live` — **表格类体检标签在预览里可达**（verifier 审计 P0-3 的回归网）。
- `test_preview_table_pipeline_runs_on_real_pdf` — 真 PDF 层：合成框线表必须被预览的表格重建捕获（不再只走文本层）。
- `test_preview_doc_type_changes_typing` — `doc_type` 必须**真的影响分型**（不是参数回显）。
- `test_tail_samples_when_fewer_than_n` — 条款数 ≤ N 时尾部样本退回全部（原实现给空数组。
- `test_dry_no_row_written_any_table`
- `test_dry_no_new_table`
- `test_dry_temp_dir_under_data_dir_and_hash_isolated` — 临时产物必须落在 data_dir/dryrun/tmp/<hash16>/，且不同文件互不覆盖。
- `test_dry_no_pdf_copy` — 预览不得复制/移动用户文件（源文件与目录清单不变）。
- `test_dry_analyze_preview_contract_frozen` — 既有 `analyze_preview` 的返回键集合不得变化（它是被别处依赖的老接口）。
- `test_dry_typing_uses_doc_type` — F8 修复的证据：预览分型必须把 doc_type 传下去（法规类文档要出现 legal）。

### `tests/test_text_utils.py`（41 个）

- `test_join_plain_wrap` — 普通折行（CJK 直连）→ 拼接。
- `test_keep_para_boundary` — 句末标点 + 下一行是编号/条款 → 保留段落断行。
- `test_ascii_space` — 字母数字跨界拼接补空格。
- `test_idempotent` — 幂等：已清洗文本再执行无变化。
- `test_empty_and_none`
- `test_katex_hat_and_bar` — 说明行 ^Ci→\hat{C}_{i}、C̄i→\bar{C}_{i}。
- `test_katex_body_zero_touch` — 正文段（无 ——— 说明行）e^x 零误伤。
- `test_katex_idempotent` — 幂等：已处理段不再嵌套。
- `test_katex_weave_pipeline` — weave → katex 全链路：34406 3.7 原文形态。
- `test_hier_from_no` — 标准号 → 效力层级：GB/T、GB/Z 推导。
- `test_std_type_by_hierarchy` — 层级 → standard_type：推荐性/指导性/强制。
- `test_pua_bond_dash` — PUA 键横线 → em dash：34406 §4 原文形态。
- `test_sup_unit_exponents` — 单位负指数 → <sup> 上标：cm-1 波数形态。
- `test_space_clause_numbers` — 段首条款编号补空格：4原理→4 原理。
- `test_ingest_trio_text` — 入库路三件套（纯文本形态，GB/T 34406 §4 原文）：—/cm⁻¹/编号空格 + 幂等。
- `test_exit_ingest_form_converged` — 形态收敛：入库路产出的干净形态过出口重放零变化（新旧文档渲染同形）。
- `test_strip_formula_leader_label_inner_space` — 缺陷证据：VLM 把 'C.3' 识别成 'C. 3'，编号捕获紧排 → 整条不匹配、点线原样落库。
- `test_strip_formula_leader_bare_threshold_aligned` — 裸点线阈值与检测器对齐：6 个 ASCII 点即剥（原 7 点 → 差一处就漏网）。
- `test_strip_formula_leader_reverse_controls` — 反向对照（修复纪律要求）：正文合法形态必须存活，不许被引导线规则误伤。
- `test_strip_formula_leader_idempotent` — 幂等：清洗后文本不再命中两条规则。
- `test_clean_clause_text_is_single_owner` — `clean_clause_text` = 入库与评估共用的**唯一**清洗次序。
- `test_clean_clause_text_shape_invariants` — 行数与长度不变形、空输入安全、幂等——入库靠行号定位页界，字形不得改行数。
- `test_strip_watermark_lines_removes_pirate_site_headers` — 盗版站水印行整行删除（裸 URL 与"短标签+URL"两族）。
- `test_strip_watermark_lines_keeps_real_citations` — **反向对照（关键）**：正文里的合法 URL 与参考文献引用必须一字不动。
- `test_strip_watermark_lines_rejects_bare_domain_pattern` — **回归护栏**：判据不得放宽为裸域名，否则普通条款被误判成 URL。
- `test_strip_watermark_lines_removes_aspose_tool_watermark` — 工具水印（无 URL）必须清除——旧守卫只认 URL 载体，使整族漏网。
- `test_strip_watermark_lines_drops_header_tail_but_keeps_body_intact` — **行尾页眉**（不锚行首）必须剥掉，且正文一字不动。
- `test_strip_watermark_lines_aspose_strips_inline_but_keeps_body` — **关键**：水印被拍进长单行中间时，只删水印、**正文一字不动**。
- `test_strip_watermark_lines_keeps_standard_refs_in_body` — **反向对照（关键）**：正文里的标准号引用/表数据不得被当成页眉删掉。
- `test_strip_watermark_lines_aspose_idempotent` — 幂等：重复清洗结果不变（清洗链可重入的前提）。
- `test_clean_clause_text_strips_watermark_in_chain` — 水印剥离已接入清洗链（`clean_clause_text`），入库与评估同源生效。
- `test_pua_decor_stripped_to_space` — 装饰类 PUA（项目符号/表格分隔/版权页位标）→ 空格。
- `test_pua_meaningful_codepoints_survive` — **反向对照（关键）**：有语义、但拿不到确定真值的码点必须原样保留。
- `test_pua_separator_original_cases_intact` — 首轮两个分隔符码点的原有行为不得回归。
- `test_strip_duplicate_suffix_only_touches_the_tail` — 只吃**结尾**的 `(数字)`。
- `test_clean_standard_name_strips_prefix_and_dup_suffix` — 文件名 → 干净名：剥开头标准号 + 去结尾副本后缀。
- `test_derive_standard_keeps_cleaned_name` — `scripts/_stdparse.derive_standard`：清理过的名**不许**被原始 stem 覆盖回去。
- `test_looks_like_binary_bytes_is_the_real_byte_path` — **字节**入口才认得出 PNG/JPEG（文本入口那些签名是死分支）。
- `test_looks_like_binary_bytes_only_reads_the_head` — 签名必须在**开头**。
- `test_looks_like_binary_text_path_reaches_only_ascii_heads_and_nul` — **文本**入口的诚实边界（复核指出原测试制造了假信心）。
- `test_looks_like_binary_known_false_positives_are_documented` — **已知误伤**（复核 2026-09-17 的 LOW）：不再声称"零误伤"，而是把它们钉成事实。

### `tests/test_material_track_l.py`（37 个）

**TestGates**

- `test_missing_material_is_skip`
- `test_unapproved_material_is_BLOCKED` — **评审硬门没有例外**：未批准的材料绝不可能进法条库。
- `test_rejected_material_is_also_blocked`
- `test_non_standard_material_is_skip_even_if_approved`
- `test_approved_standard_without_library_copy_needs_import`
**TestLinkWhenLibraryAlreadyHasIt**

- `test_approved_standard_already_in_library_links_only`
- `test_apply_link_points_the_material_at_the_doc`
- `test_apply_link_on_import_does_NOTHING_and_says_so` — `import` 动作下 **什么都不写**，且返回值必须让人看到"还没入库"。
- `test_apply_link_refuses_when_blocked` — 未批准时 `apply_link` 也必须**拒绝**（不能因为"只是回指"就放行）。
**TestStandardNoKey**

- `test_equivalent_writings_share_a_key`
- `test_different_standards_do_not_collide`
- `test_empty_is_empty`
- `test_find_existing_doc_matches_across_writings` — 库内写 `GB 10146-2015`，采集侧给 `GB10146-2015` —— 必须能匹配上。
**TestLawNameKey**

- `test_the_amendment_year_is_part_of_the_identity`
- `test_same_law_in_different_writings_shares_a_key`
- `test_empty_is_empty`
- `test_find_existing_law_does_not_point_a_new_amendment_at_an_old_one` — 库里只有 **2014 修正版**时，**2021 修正版**必须判成"库内没有"。
**TestIntentParsing**

- `test_intent_is_read_from_tier_evidence`
- `test_non_standard_has_no_intent`
- `test_broken_json_evidence_does_not_raise`
- `test_actions_constant_is_the_single_definition`
**TestImportToLibrary**

- `test_unapproved_never_touches_the_law_chain` — **最要紧的一条**：未批准时入库函数必须彻底不动法条链。
- `test_approved_standard_is_imported_and_linked`
- `test_imported_standard_is_resolvable_by_the_law_chain` — 入库之后，法条链**自己**的查询要能找到它（否则"入库"没有意义）。
- `test_second_import_of_same_material_is_idempotent` — 再跑一次不该造出第二部标准（既有管线的查重会让它退化为回指）。
- `test_reconcile_dispatches_link_and_never_writes_for_blocked` — `reconcile` 的分派：link 走回指。
- `test_material_without_chunks_refuses_to_import` — 没有正文的采集件不得入库——那会造出一部空标准。
- `test_unparsable_body_fails_loudly_instead_of_silently` — 切不出条款时必须**如实报错**，不能静默"成功"或造出一部空标准。
- `test_collected_LAW_text_is_now_recognized_and_imported` — **法规正文现在能走通了**（2026-09-17 起）。
- `test_import_of_law_without_a_name_refuses_loudly` — 法规名没取到 ⇒ **拒绝入库**（没有名字就没法在库里认它，宁可不入）。
- `test_hierarchy_and_clause_type_are_honest` — 复核 step-31~34 的两条 MEDIUM：**标准条款的类型**与**采集件的效力/质量默认值**。
- `test_imported_standard_clauses_are_rules_not_legal` — 标准入库后，条款的 `knowledge_type` 必须是 `rule`（不是 `legal`）。
- `test_imported_collected_doc_is_marked_unknown_not_effective` — 采集件落库后：效力**未知**（不是 effective）、质量 **C**、类型**不声明**。
- `test_collected_standard_lands_in_the_standard_tree` — **进对树**：`auto_tag` 的归一形 `GB12321-2021`（无空格）也要被认成标准。
- `test_law_hierarchy_is_conservative_and_says_undecided` — 层级推断**只用不会错的规则**，其余一律 `未定`（**不假装知道位阶**）。
**TestTreeClassificationOfStandardNumbers**

- `test_standard_numbers_go_to_the_standard_tree`
- `test_law_names_do_not_become_standards` — 反方向也不能错：法规名不许被当成标准号（白名单**不是**"任何带数字的东西"）。

### `tests/test_material_repo.py`（35 个）

**TestProject**

- `test_create_and_get`
- `test_list_contains_created`
- `test_get_unknown_is_none`
**TestMaterialDefaults**

- `test_new_material_born_status_by_origin` — S3-b（2026-09-22 业主裁定 NOT-DOING #15）：出生评审状态**按来源**——。
- `test_user_material_defaults_to_t1_system` — 用户自有原件默认 T1（对其自身内容是初级证据），由 system 判。
- `test_collected_material_is_not_trusted_by_default` — **自采默认不可信**（T3 起）：网上找来的在没证据前不该默认可信。
- `test_invalid_enums_rejected`
- `test_tier_evidence_roundtrips`
**TestReviewGate**

- `test_approved_materials_is_the_hard_gate` — 硬门核原样：自采未经批准不得进作答。
- `test_collected_pending_is_not_in_gate` — 自采出生 pending ⇒ 不在门内（硬门前提原样）。
- `test_review_note_and_timestamp_recorded`
- `test_set_review_unknown_id_returns_false`
- `test_invalid_status_rejected`
**TestTwoAxes**

- `test_task_role_is_independent_of_source_tier` — 公司制度例：**来源层级低**但**是本任务的准则**——两轴必须能并存。
- `test_user_can_override_tier_and_it_is_recorded` — 业主明说"用户可以改效力层级"⇒ 改完要能看出是**人**定的（留痕）。
- `test_invalid_tier_and_role_rejected`
- `test_lifecycle_promote`
- `test_tier_labels_cover_all_tiers`
**TestChunks**

- `test_chunks_keep_char_offsets_and_order`
- `test_empty_text_chunks_are_skipped`
- `test_char_end_defaults_to_text_length`
**TestSearch**

- `test_search_only_returns_approved` — **硬门写在 SQL 里**：未批准的材料不可能被搜出来。
- `test_rejected_material_is_not_searchable`
- `test_search_returns_citation_fields` — 命中的每一项都要带"能标注 + 能点回原文"的字段（可见性硬需求）。
- `test_search_labelling_shows_both_axes`
- `test_search_is_project_scoped` — A 项目的材料不该出现在 B 项目的检索结果里。
- `test_search_junk_query_does_not_raise`
- `test_limit_respected`
- `test_bad_arguments_raise_instead_of_silently_finding_nothing` — **坏参数不许静默变成"没有命中"**（verifier 2026-09-17 报的 LOW）。
- `test_real_sql_failure_is_loud_not_empty` — **表/SQL 真坏了必须留痕**，不能伪装成"材料里没有命中"。
- `test_programming_error_is_not_swallowed` — **非 sqlite 异常必须冒出来**（这是从兜底 `Exception` 收窄的全部意义）。
**TestDelete**

- `test_delete_material_removes_chunks_and_index`
**TestLawChainIsolation**

- `test_material_ops_do_not_touch_law_chain` — **行为级**证明零耦合：材料操作前后，法条链三张表行数完全不变。
- `test_link_doc_only_writes_material_side` — Track L 的回指**写在材料侧**（doc_id 列），不改 doc_meta。
**TestStorageLocation**

- `test_materials_dir_is_under_data_dir_and_per_project` — 材料原件放数据区（代码树零运行产物），且**按项目分目录**。

### `tests/test_update_channels.py`（35 个）

- `test_每个链上的渠道名都能在适配套表里查到` — **接线不变量**：`routing.select_chain()` 返回的每个渠道名，都必须在。
- `test_ttzb_那一个渠道的键与名不一致要按名建表` — 具体到那个不一致的渠道：字典里必须能按 `ttbz`（链里的名字）取到。
- `test_httpx_自检能看出本机是否可用` — `httpx_usable()` 必须**既**能报可用、也能把不可用的原因变成一句人话。
- `test_两个栈都不可用时日志点名原因` — `curl_cffi` 缺 + httpx 构造失败 ⇒ **ERROR 且点名**，而不是一条 WARN 就回退。
- `test_httpx_可用时只打_WARN`
- `test_govcn_真接口命中_按摘要里的标准号` — **换棒的实证**（R1 的 G6：旧实现只解 mock dict ⇒ 真实网络恒 miss）。
- `test_govcn_真接口空结果算_miss_不算命中`
- `test_govcn_旧的_mock_契约仍然可用` — 离线 fixture 走的是 mock 分支（`{"announcements": [...]}`）——换棒**不许**把它弄坏。
- `test_fixture_matrix_contract` — fixture 自检：≥12 行组合（INS-B-07 口径）、key 唯一、渠道与必填段齐全。
- `test_channel_matrix_deterministic_and_idempotent` — INS-B-07：逐组合断言字段唯一确定 + 两轮重跑逐位一致。
- `test_combo_tuple_stable_across_rounds` — 全矩阵遍历：(channel, change_type, 色) 元组两轮恒等，无不确定场景。
- `test_captcha_marker_only_never_writes_db` — INS-C-01：captcha 结果只返回标记。
- `test_live_openstd_homepage_default_transport_200` — RUN_LIVE=1 时经新默认 transport（curl_cffi 指纹优先）GET openstd 首页断言 200。
- `test_official_gb_parses_real_openstd_html` — ANOM-003 回归：真实 HTML 结果表 → ChannelResult 正确（现行→effective/no_change、被代替→superseded）。
**TestOfficialGb实施日期**

- `test_两个日期格取第二个`
- `test_只有一个日期格时不猜` — ⚠ 一格时发布/实施**不可区分** ⇒ 两个槽都留空（§11.0 R6c-3f）。
- `test_没有日期格`
- `test_多出第三格时仍取实施日期而不是最后一个` — 为什么取 `[1]` 而不是 `[-1]`：列**追加**比**重排**常见。
**Test发布日期槽**

- `test_official_gb_发布取第1格`
- `test_official_gb_只有一格时发布留空` — ⚠ **不许把唯一那格当发布**：此时发布/实施不可区分，宁缺勿错。
- `test_ttzb_实施与发布各归各的槽` — b34 的真机反例：T/CECS 2350-2026 发布 2026-06-12、实施 2026-12-01。
- `test_ttzb_只有发布时实施留空` — 旧实现会把这个发布日期填进 `effective_date` —— 那正是要修的形态。
- `test_ttzb_三级回退顺序`
**TestNormNoFullWidth**

- `test_全角与半角斜杠归一到同一个号`
- `test_按归一号挑行时全角目标能命半角行` — 这条是"匹配失手"的最小复现：目标写全角、站点返回半角。
**TestNdlsRefererIsAscii**

- `test_全角号不再让请求发出前就炸`
- `test_referer_是纯_ascii_且关键词被转义`
**TestQueryUsesHalfWidthForm**

- `test_送出去的请求里没有全角斜杠`
- `test_query_no_不打乱既有写法` — `query_no` 只换字符形状：**空格必须保留**（cssn/mee 实测"带空格完整号"才排第一）。
- `test_ndls_搜索体与_web_的_q_也必须用规范形` — b31 的反例：`ndls` 的 **JSON 搜索体**（可达渠道！）与 `web` 的 `q` 仍是原始全角。
**TestNormNoDashes**

- `test_各种连字符都折成半角减号`
- `test_与_canon_standard_no_在这些输入上一致`
**Test废止日期落自己的槽**

- `test_ndls_详情_实施与废止分槽`
- `test_ndls_降级档_没有a206就不填废止日期` — ⚠ 不知道 ≠ 拿实施日期顶（这正是"按能力判定兜住"失败的现场）。
- `test_hbba_废止行_两个日期分槽`

### `tests/test_contract.py`（34 个）

- `test_sse_event_order_frozen`
- `test_search_channels_frozen`
- `test_modality_strength_dict_frozen`
- `test_models_instantiate`
- `test_invalid_knowledge_type_rejected`
- `test_schema_all_tables`
- `test_bookmark_folder_schema` — 收藏夹目录（2026-10）契约：夹表 + 两张收藏表的 folder_id 列 + 夹名 UNIQUE。
- `test_doc_bookmark_columns` — user_doc_bookmark（标准级书签）契约：列集 + doc_id UNIQUE + FK 级联。
- `test_egress_audit_contract` — Task 10.0 契约（v5 红线 #4 外发可审计）：debug_dump 必须承载外发审计所需字段。
- `test_clause_revision_page_breaks_column` — B3 页界列：clause_revision.page_breaks TEXT 可空（run-start 编码。
- `test_clause_revision_figure_html_column` — C2 插图通道列：clause_revision.figure_html TEXT 可空（fig-strip 占位。
- `test_update_tables_exist` — 29/30 号表存在性（pipeline/02 §2 数据契约增量）。
- `test_update_tables_ulid_pk_style` — 29/30 表主键为 ULID 风格 TEXT 主键，DDL 注释声明 upd_/chg_ 前缀。
- `test_update_batch_check_enums` — update_check_batch：trigger_type 二枚举、status 五枚举 CHECK。
- `test_update_event_change_type_enum` — update_change_event：change_type 恰好五枚举。
- `test_update_event_legal_status_and_nullable_doc` — current_legal_status 四枚举且可空。
- `test_update_event_fk_cascade` — batch_id 外键：孤儿事件插入被拒、删批次级联删事件。
- `test_bulk_import_batch_exists_and_columns` — 31 号表存在性 + 巡检侧最小列集（tier/checkpoint_json 是编排器刚需）。
- `test_bulk_import_batch_ulid_pk_style` — 主键为 ULID 风格 TEXT 主键，DDL 注释声明 bul_ 前缀。
- `test_bulk_import_batch_check_enums_and_defaults` — CHECK 枚举（batch_kind/trigger_type/status/tier）+ 默认值（status/计数/tier）。
- `test_announce_table_exists` — announcement_observed（32 号表）存在。
- `test_announce_observed_columns` — announcement_observed 契约：列集完备。
- `test_announce_dedup_unique` — 去重键 UNIQUE(source_id, url_hash)：重复 (source_id,url_hash) 写入被拒。
- `test_announce_ulid_pk_style` — observed_id 须为 TEXT 主键且 DDL 带 ann_ 前缀注释（ULID 风格契约）。
- `test_folder_tables_exist` — folder / folder_member / doc_filing_state 三张表存在（方案 §3 定死的形状）。
- `test_folder_columns`
- `test_folder_ulid_pk_style` — folder_id 须为 TEXT 主键且 DDL 带 fld_ 前缀注释（与 30/32 号表同款契约）。
- `test_folder_member_columns_and_pk`
- `test_doc_filing_state_columns_and_stage_enum`
- `test_folder_member_kind_enum_and_pk_rejects_dup` — item_kind 只有 folder/file。
- `test_folder_same_name_same_level_rejected_by_indexes` — 同名同层拒绝**必须**含根层：`parent_id IS NULL` 时表级 UNIQUE 无效（NULL 互不相等），。
- `test_clause_vec_doc_id_metadata_column` — `clause_vec` 必须有 `doc_id` **元数据列**（范围下推修复）。
- `test_clause_repo_writes_doc_id_into_clause_vec` — spec 003 · FR-009：写向量的**两处**都必须带 `doc_id`（**静态锚点**）。
- `test_clause_repo_write_path_sets_doc_id` — spec 003 · FR-009 / SC-005（**端到端**）：真经写侧跑一条 ⇒ `clause_vec.doc_id` 必须对。

### `tests/test_credentials_namespace.py`（34 个）

- `test_every_channel_name_is_namespaced` — 所有通道的所有变量名必须带 KS_ 前缀（这次事故的形态就是漏了前缀）。
- `test_legacy_names_disjoint_from_write_names` — 旧名不能同时是写入名（否则等于一边叫它旧、一边继续用它）。
- `test_llm_reader_order_namespaced_first`
- `test_no_source_writes_a_legacy_name_or_registry` — 源码级扫描：**全仓库代码**里没有任何文件把旧全局名/注册表当写入目标。
- `test_legacy_names_appear_only_in_reviewed_files` — 旧名出现的位置白名单化：新增引用会红，逼一次人工复核（防偷偷搬回裸名）。
- `test_set_credential_writes_encrypted_store_not_registry`
- `test_write_path_does_not_touch_winreg_at_all` — 最强结构断言：把 winreg 换成"一碰就炸"，保存仍必须成功。
- `test_dash_clears_store_value`
- `test_blank_value_skips_without_clobbering`
- `test_unknown_channel_rejected`
- `test_stored_channels_reports_booleans_only`
- `test_store_value_is_read`
- `test_env_override_beats_store`
- `test_store_beats_legacy_system_layer` — 存储是权威：系统层里还有旧值也不该压过它（否则"设置页改了不生效"）。
- `test_legacy_system_layer_still_readable_for_backward_compat` — **关键兼容断言**：没迁移的老机器（系统层里只有旧名）必须照旧能跑。
- `test_legacy_env_still_readable`
- `test_env_beats_legacy_registry_for_same_name`
- `test_base_url_and_model_chain`
- `test_cloud_channel_reads_from_store`
- `test_defaults_when_nothing_configured`
- `test_system_layer_status_reports_presence_without_values`
- `test_legacy_status_reports_presence_without_values`
- `test_adopt_legacy_moves_into_store_and_keeps_system_layer_by_default`
- `test_adopt_legacy_delete_removes_registry_after_verify`
- `test_adopt_legacy_never_clobbers_existing_store_value` — verifier P1 回归：存储里已有值（用户在设置页刚存的新 Key）绝不能被旧值冲掉。
- `test_adopt_legacy_delete_refuses_to_drop_conflicting_legacy`
- `test_adopt_legacy_force_discards_conflicting_legacy`
- `test_adopt_legacy_invalidates_settings_cache` — 迁移后必须失效进程内缓存（verifier mut6 曾证明此处空洞）。
- `test_adopt_legacy_noop_when_nothing_legacy`
- `test_adopt_legacy_unknown_channel_rejected`
- `test_import_system_layer_moves_same_named_vars` — 同名搬家：KS_MINERU_CLOUD_API_KEY 从系统层搬进加密存储。
- `test_import_system_layer_keeps_existing_store_value`
- `test_clean_system_layer_deletes_only_named_targets`
- `test_clean_system_layer_reports_env_untouched`

### `tests/test_kb_folder_api.py`（34 个）

- `test_list_top_level_order_is_the_hand_set_order` — **顶层实际顺序**必须是 标准 → 法律法规 → 公司制度 → 待分类（不只比 sort 值）。
- `test_list_empty_folder_gives_empty_array_not_error`
- `test_list_unknown_folder_is_404`
- `test_list_subfolders_sorted_by_sort_then_pinyin` — 同级排序 = (sort, 拼音, 名)：``A 综合`` 按拼音是 a…，必须排在 ``安全`` 前。
- `test_list_pagination_boundary`
- `test_subfolder_deep_file_count`
- `test_items_empty_and_pagination`
- `test_items_unknown_folder_is_404`
- `test_create_folder_under_parent_and_errors`
- `test_rename_and_conflict`
- `test_move_folder_from_to`
- `test_move_a_two_places_folder_leaves_the_other_place_alone` — **第 2 步修准的那处语义**：同时挂在两处的目录，挪一处**不再**把另一处带走。
- `test_move_from_a_copy_to_the_top_really_lands_at_the_top` — ④ ``to_parent_id=null`` ⇒ **真的挪到顶层**（复核 2026-09-21 打回的假成功）。
- `test_move_from_a_place_that_does_not_hold_it_is_409`
- `test_move_rejects_own_subtree`
- `test_copy_folder_shares_members`
- `test_copy_into_own_subtree_is_422`
- `test_delete_empty_folder_directly`
- `test_delete_nonempty_without_mode_is_409`
- `test_delete_top_level_reparent_rejected_when_nonempty`
- `test_delete_purge_keeps_files_present_elsewhere`
- `test_delete_preview_numbers`
- `test_delete_unknown_folder_is_404`
- `test_members_add_is_idempotent`
- `test_members_add_errors`
- `test_members_remove_move_copy`
- `test_inbox_lists_unfiled_with_suggestion_only_from_existing` — **只匹配现有目录，绝不自行新建**：真形状的树里命中 ⇒ 给**正确的那个**目录。
- `test_inbox_suggestion_is_null_when_the_tree_has_no_such_folder` — 反向用例：树里**没有**对应的目录 ⇒ **必须** None，不许瞎指一个（哪怕「标准」在）。
- `test_inbox_confirm_accept_existing_new`
- `test_inbox_confirm_errors_are_atomic` — 整批全成或全败：中间一条非法 ⇒ 前面的也不许落。
- `test_scope_resolve_union_and_deeper`
- `test_scope_resolve_unknown_is_404_not_empty` — ⚠ 绝不静默返回空范围（空范围会让"在此范围内提问"悄悄变成全库提问）。
- `test_all_kb_endpoints_require_token`
- `test_folder_effect_deep_counts` — 批D2 判据（2026-09-22）：目录行的**效力分色灯**数据 —— `effect_deep` 按子树聚合。

### `tests/test_material_collect.py`（33 个）

**TestAlwaysPendingAndEphemeral**

- `test_collected_material_is_pending`
- `test_collected_material_never_enters_retrieval_before_review` — 硬门在采集路径上同样成立：未批准 → 搜不到。
- `test_default_lifecycle_is_ephemeral` — 业主裁定：其它资料默认**当前任务一次性**。
- `test_module_exposes_no_way_to_approve` — **结构性约束**：本模块不得提供任何能设置评审状态的**代码路径**。
- `test_the_structural_detector_itself_works` — **检测器的自测**：否则上面那条"结构性约束"可能是空转的。
**TestSourceProvenance**

- `test_url_is_recorded_and_domain_extracted`
- `test_no_url_means_unknown_identity` — 没有 url/domain ⇒ 身份未知 ⇒ 按 authority 的纪律**不能互证**。
- `test_collected_defaults_to_T3_not_trusted` — 不给层级时"网上找来的"从 T3 起——**默认不可信，靠证据升级**。
- `test_caller_can_set_a_higher_tier_with_evidence` — 调用方有证据时可以给更高层级（判据是"有没有证据"，不是"谁采的"）。
- `test_note_lands_in_tier_reason_for_the_reviewer`
**TestDeduplication**

- `test_identical_text_is_not_registered_twice`
- `test_near_duplicate_is_registered_but_flagged` — 近似（改了标点）**仍然登记**，但标注 `near_duplicate_of` 给评审人看。
- `test_different_articles_are_not_flagged`
**TestTrackL**

- `test_standard_text_is_recognised_and_only_recorded` — 认出疑似标准正文 ⇒ 只**记录意图**，不在采集路径上入库（入库在评审通过之后）。
- `test_non_standard_text_is_other`
- `test_caller_can_override_kind`
**TestLawRecognition**

- `test_law_text_is_recognized_with_name_and_clause_count`
- `test_direct_recognizer_thresholds` — 四条证据都要齐：标题/法规名 + **从第一条起** + **立法句式** + 条数门槛。
- `test_a_single_clause_citation_is_not_a_law` — **零误伤方向**：正文里顺口引用一条"第X条"的文章不许被当成法规。
- `test_standard_number_wins_over_law_shape` — **优先级**：同时像标准与法规时，走**标准**那一支（标准号判据更精确）。
**TestLawRecognitionFalsePositives**

- `test_news_quoting_law_names_is_not_a_law` — 新闻：标题正常、正文引了《…》+ 几条法条 ⇒ **不许**认成法规。
- `test_contract_is_not_a_law` — 合同：有第一条/第二条、有《设备采购合同》⇒ **不许**认成法规。
- `test_judgment_is_not_a_law` — 判决书：正文引《合同法》，但自称"本院"而不是"本法"⇒ **不许**认成法规。
- `test_law_without_the_recital_phrase_is_still_refused` — 缺**立法句式**（"本法"/"本条例"）就不算——这是四条证据之一，不是装饰。
- `test_must_start_at_article_one` — 引用的条号**不从第一条开始** ⇒ 是节选/引用，不是法规全文。
- `test_law_name_is_never_taken_from_the_body` — **根因钉子**：法规名**只能**来自标题——正文里的 `《…》` 一律不算。
**TestInputValidation**

- `test_blank_title_is_refused`
- `test_blank_text_is_refused` — 没有正文的采集件不该登记——那会让评审人对着空白"批准"（盲签）。
- `test_chunks_keep_the_fidelity_invariant` — 采集件的切片也要满足**逐字取回**（引用点回原文的地基）。
- `test_bad_max_chars_is_refused_by_the_shared_guard` — `max_chars` 的校验只有一处所有者（`material_ingest`），采集路径也要吃到它。
- `test_binary_container_is_refused_at_the_door` — **唯一的采集门**自己就要挡住二进制（不能只靠采集器自觉）。
- `test_binary_signature_in_the_middle_is_not_refused` — 保守：签名只在**开头**算——正文中间提到 `%PDF-` 的文章不该被误杀。
**TestDomainHelper**

- `test_domain_of`

### `tests/test_material_ingest.py`（33 个）

**TestChunking**

- `test_offsets_round_trip_exactly` — **保真不变量（最强口径）**：全文[块.start:块.end] **逐字**等于块文本。
- `test_chunk_spanning_blank_line_keeps_original_separators` — 跨空行/跨页的块必须**原样保留**原文分隔符（2026-09-17 被验收测试抓到的 bug：。
- `test_short_lines_pack_into_one_chunk`
- `test_max_chars_splits`
- `test_overlong_single_line_is_hard_split`
- `test_blank_text_yields_nothing`
- `test_page_mapping`
- `test_build_document_spans_self_consistent`
**TestExtract**

- `test_txt`
- `test_docx_is_page_1`
- `test_pdf_keeps_page_numbers`
- `test_empty_txt_gives_no_pages`
**TestIngest**

- `test_txt_becomes_approved_by_birth_with_offsets` — S3-b1 对账（业主裁定 NOT-DOING #15）：人工上传**免评审**，出生即 approved。
- `test_title_strips_duplicate_suffix`
- `test_duplicate_content_is_not_registered_twice`
- `test_file_outside_project_dir_is_copied_in` — 材料平面要自包含：外面来的文件复制进项目目录（独立存储）。
- `test_file_already_in_project_dir_is_referenced_in_place`
- `test_unparsable_pdf_is_registered_but_flagged` — 扫描件（无文本层）：**仍登记**（用户得看得见），但如实说明没解析出文本。
- `test_judged_garbled_pdf_is_not_reported_as_scanned` — **成因要分开回显**（2026-09-25 复核 P-4）：文本层被判乱码 ≠ 没有文本层。
- `test_empty_txt_does_not_guess_a_cause` — **取不到文本层状态时不许臆测原因**（2026-09-25 第 2 轮复核 Q4：这条分支无测试）。
- `test_unsupported_suffix_rejected`
- `test_project_dir_ingest_is_batch_and_ok`
- `test_scan_is_stable_and_filtered`
- `test_ingested_material_gate_closes_and_reopens` — 端到端串一遍硬门（免评审口径，裁定 #15）：收件 ⇒ 出生即可用 ⇒。
**TestPhaseAAcceptance**

- `test_pdf_gate_search_and_citation_point_back`
- `test_pdf_citation_is_exact_without_strip` — 引用区间必须**逐字**取回（不是"去掉空白后相等"）。
- `test_page_of_contract_on_separator` — `page_of` 的精确契约：落在**页间分隔符**上返回**最后一页**（不是上一页）。
**TestMaxCharsGuard**

- `test_chunk_text_rejects_non_positive`
- `test_rejected_even_when_text_is_empty` — **同一参数只能有一种命运**：空文本早退也不得放过非法参数。
- `test_bool_is_rejected` — `True` 是 int 的子类但不是合法块大小——别把它当 1 悄悄接受。
- `test_ingest_file_rejects_before_touching_content` — 公开入口同样拒绝——**即使该文件解析不出文本**（那时 `chunk_text` 不会被调用）。
- `test_legal_small_value_still_works` — 合法小值照常硬切（修复不能把正常能力一起砍掉）。
- `test_scan_pdf_needs_explicit_deep_and_is_flagged` — 扫描件（无文本层）在**默认不外发**下拿不到内容 —— 但材料仍登记并如实标注。

### `tests/test_folder_store.py`（32 个）

- `test_create_and_same_name_same_level_rejected`
- `test_rename_folder_and_conflict`
- `test_name_and_depth_limits_have_readable_errors`
- `test_folder_name_allows_slash` — ⚠ CCS 区间名自带斜杠（P15/19）⇒ 目录名必须允许 `/`，否则真实分类树建不出来。
- `test_one_file_in_two_folders`
- `test_add_member_is_idempotent_and_unknown_doc_rejected`
- `test_move_member_between_folders`
- `test_copy_folder_shares_members_and_is_independent`
- `test_copy_folder_into_own_subtree_rejected`
- `test_copy_folder_rejects_its_own_subtree` — 第 2 步补：``copy_folder`` 自己也要拒环。
- `test_top_level_order_is_sort_then_pinyin` — 四个顶层（标准 10 / 法律法规 20 / 公司制度 30 / 待分类 90）必须按 **sort** 排。
- `test_move_folder_rejects_cycle`
- `test_move_folder_by_from_to_updates_main_position_when_from_is_main`
- `test_move_folder_defaults_to_the_main_position` — 省略 ``from_parent_id`` = 挪"这个目录本身"（旧调用的行为一字不变）。
- `test_move_folder_from_a_copy_to_a_third_place_adds_the_new_edge` — ③ 从**复制出来的那一处**挪到**第三处** ⇒ 删源边 **+ 补新边**（业主裁定以代码为准）。
- `test_move_folder_from_a_copy_to_the_top_really_lands_at_the_top` — ④ ``to_parent_id=None``（挪到顶层）⇒ **真的到顶层**，不是"删条边 + 回 moved=true"。
- `test_move_folder_from_a_place_that_does_not_hold_it`
- `test_move_folder_to_the_same_place_is_a_noop`
- `test_move_folder_name_conflict_at_target`
- `test_delete_empty_folder_ok`
- `test_delete_nonempty_requires_mode`
- `test_delete_reparent_moves_members_to_parent`
- `test_delete_reparent_rejects_top_level_folder` — 业主点名的边界①：一级目录没有上一层 ⇒ reparent 必须报可读中文错，。
- `test_delete_purge_keeps_docs_present_elsewhere` — 业主点名的边界②：purge 时**还挂在别的目录里**的文件只是丢归属，**不真删**。
- `test_purge_uses_given_db_path` — ⚠ 安全用例：purge 的真删**必须**落在传进来的那个库上。
- `test_describe_folder_delete_numbers` — 「先问一句」要的数字：一级目录 reparent 不可用。
- `test_list_folder_pagination_and_deep_counts`
- `test_list_root_shows_toplevel_folders_and_unfiled_docs`
- `test_folder_scope_includes_deeper_levels_and_unions`
- `test_build_folder_tree_batch_atomic`
- `test_build_folder_tree_reuse_existing_is_idempotent` — ``reuse_existing=True`` ⇒ 同一批 nodes 重复跑**不建重复目录**（一次性归位脚本要的幂等）。
- `test_filing_state_lifecycle_and_lists`

### `tests/test_material_authority.py`（32 个）

**TestBehaviourTable**

- `test_every_tier_has_a_behaviour`
- `test_t4_is_excluded_t3_needs_corroboration`
**TestRules**

- `test_t0_t1_t2_are_usable`
- `test_single_source_t3_is_LEAD_ONLY` — **核心纪律**：一篇网络文章**不得**支撑结论。
- `test_two_independent_domains_promote_t3_to_corroborated`
- `test_same_domain_twice_is_NOT_corroboration` — **最常见的假互证**：同一站点转载两篇，只有一个来源。
- `test_t4_never_usable_and_is_disclosed`
- `test_t4_with_many_sources_still_excluded` — T4 **多源也不放行**——"不可回溯"是来源性质问题，不是数量问题。
- `test_criterion_is_listed_and_not_downgraded_by_tier` — 公司制度例（轴 B 独立于轴 A）：来源层级低，但**是本任务的准绳**。
- `test_criterion_t3_single_source_still_governs` — 用户把一份二手转述**指定为准绳**时，轴 B 优先——但标注仍说实话（T3）。
- `test_unapproved_material_never_reaches_assembly` — 评审硬门在检索层就已经挡住 ⇒ 装配层看不到未批准材料（这里再确认一次）。
- `test_no_hits_yields_honest_note`
**TestRendering**

- `test_render_carries_both_axes_and_a_locator`
- `test_render_shows_declared_role_label` — 声明了轴 B 之后，渲染里出现的是「本任务准则」而不是「未声明效力」。
- `test_render_shows_lead_only_section_separately`
- `test_render_includes_excluded_section`
**TestT4BeatsAxisB**

- `test_t4_declared_criterion_is_NOT_load_bearing`
- `test_t4_criterion_is_visibly_marked_in_both_notes_and_text`
- `test_t3_criterion_still_governs` — 轴 B 的**正常**用法不能被上一条误伤：T3 单一来源当准则仍然算准则。
**TestCorroborationIsFalsifiable**

- `test_two_copies_without_any_source_identity_do_NOT_corroborate`
- `test_url_provides_identity_so_two_domains_corroborate`
- `test_url_identity_normalizes_scheme_www_and_case` — `A.COM` / `www.a.com` / `http://a.com` 是**同一个**来源（旧口径算 3 个）。
- `test_unknown_identity_does_not_drag_down_known_corroboration` — 混合场景：两个已知域名互证 ⇒ 那两条升为辅证。
**TestSameStoryIsNotIndependentSources**

- `test_identical_text_on_two_domains_is_ONE_source`
- `test_copy_with_reworded_punctuation_is_still_ONE_source` — 只改标点/空白/全半角的"转载"仍是同一篇（归一化后相等）。
- `test_same_domain_two_articles_is_still_ONE_source` — 同一家媒体的两篇不同文章 = 一个来源（这是域名图的节点语义）。
- `test_syndicated_pair_plus_one_real_second_source` — `a.com` X + `b.com` 转载 X + `c.com` **另一篇** ⇒ 合并后是 **2** 个来源 ⇒ 可互证。
**TestNoSingleScoreSorting**

- `test_module_exposes_no_tier_sorting_helper` — **两轴不可压成一个分数**：本模块不得提供"按层级/综合分排序材料"的函数。
- `test_usable_order_follows_groups_not_tiers` — **行为级**两轴护栏：承重集合的顺序按"组"（准则在前）而**不是**按层级。
**TestCitationIndices**

- `test_indices_are_contiguous_across_groups_in_group_order`
- `test_render_marks_every_hit_with_its_index`
- `test_index_matches_usable_hits_order` — `usable_hits()` 的返回顺序必须与编号一致（下游按它拼引用，不一致就错位）。

### `tests/test_middle_schema.py`（30 个）

**TestDetect**

- `test_detects_34`
- `test_detects_40`
- `test_pdf_info_wins_when_both`
- `test_unknown_shape_raises`
- `test_non_dict_raises`
- `test_empty_object_raises`
**TestNormalize34**

- `test_identity_same_object`
- `test_no_mutation_of_input`
**TestConvert40**

- `test_root_key_is_pdf_info`
- `test_page_size_from_docvortex_layout`
- `test_discarded_blocks_excluded_from_para_blocks`
- `test_title_types_mapped`
- `test_inline_equation_kept`
- `test_standalone_equation_block`
- `test_nested_content_flattened`
- `test_table_caption_and_html`
- `test_image_body_path`
- `test_chart_caption_kept`
- `test_empty_pages_ok`
- `test_missing_docvortex_falls_back`
**TestLoadJson**

- `test_reads_and_normalizes_40`
- `test_missing_file_raises`
- `test_bad_json_raises`
- `test_unknown_shape_raises`
**TestGuard**

- `test_load_middle_items_consumes_40`
- `test_load_middle_items_splits_40_into_clauses`
- `test_load_middle_items_raises_not_silent` — 未知结构必须**抛**，不许像修复前那样 `mj.get("pdf_info", [])` 静默给空。
- `test_cloud_guard_accepts_40`
- `test_cloud_guard_rejects_unknown`
- `test_cloud_guard_rejects_empty_pdf_info`

### `tests/test_research_report.py`（30 个）

**TestBuild**

- `test_sections_and_counts`
- `test_grouping_reuses_the_authority_owner` — **结构性约束**：分组标题必须来自 `authority.GROUP_ORDER`（不许自己再写一套）。
- `test_pending_is_never_silently_dropped`
- `test_no_approved_materials_says_so`
- `test_missing_project_raises`
- `test_html_is_escaped` — 标题/结论里的 HTML 必须**转义**（报告是可交付文件，不是网页）。
**TestCitationChecking**

- `test_unknown_index_is_warned`
- `test_valid_index_is_not_warned`
- `test_law_refs_are_counted_but_not_pretended_verified` — `[[c:i]]` 本次**无法校验** ⇒ 如实计数（不假装查过）。
- `test_conclusion_without_query_is_declared_unchecked` — 不给 `query` 就没有依据集可比 ⇒ **必须**说出来（不许默默放过引用）。
- `test_negative_index_is_caught` — 负数编号也要被抓（历史缺陷：提示词侧曾漏掉 `[[m:-1]]`）。
**TestAnchorVisibility**

- `test_fresh_material_has_no_anchor_noise` — 刚入库的材料锚点 `ok` ⇒ **不许**加标记（标记得只在有问题时出现，否则人人无视）。
- `test_health_crash_is_not_reported_as_unverified` — **健康度算不出来 ≠ 材料未验证**（复核 b9 的 INFO-3）。
- `test_old_material_is_marked_unverified` — 入库时没记指纹的老材料 ⇒ 标记 + warning（措辞必须是"未经验证"，不是"有问题"）。
- `test_changed_fingerprint_is_marked_needing_recompute` — 指纹变了 ⇒ 「⚠锚点需复算」+ warning（措辞："需要复算"，不是"已经坏了"）。
**TestEvidenceAnchorMarks**

- `test_report_marks_the_evidence_lines` — 报告「三、依据」的**引用行**上必须看得到锚点标记（这条就是验收条件）。
- `test_without_the_map_the_rendering_is_unchanged` — **P1 保证**：不传 map（= 答案链那条路）时，渲染里**不许**出现任何锚点标记。
- `test_marks_vocabulary_has_one_owner` — 三个短标记的措辞**只有一份**（`locator.STATUS_MARKS`），两处都从它取。
**TestEvidenceAssemblyGate**

- `test_报告侧装配失败翻成可操作错误码`
- `test_报告侧项目不存在仍按_ValueError_放行`
- `test_落盘路径同样走那个唯一入口` — `write_research_report`（真正落盘那条）也必须经过它——否则"先渲染后落盘"的。
**TestWrite**

- `test_files_are_written_and_named`
- `test_unsafe_title_is_sanitised`
**TestTrackLStatus**

- `test_lists_track_l_targets_without_writing` — `track_l_status` 只读（不得往法条链写任何东西）。
**TestEndpoint**

- `test_export_writes_files_and_returns_them`
- `test_dry_run_does_not_write`
- `test_missing_project_is_404`
- `test_missing_project_id_is_422`
- `test_wrong_types_are_422`
- `test_requires_token`

### `tests/test_clause_head_gates.py`（28 个）

**TestNumSegments**

- `test_numeric`
- `test_appendix_letter`
- `test_numeric_before_appendix`
- `test_unorderable`
**TestContinuationShape**

- `test_right_paren`
- `test_tilde_range`
- `test_sentence_period`
- `test_connector_word`
- `test_dot_leading_rest`
- `test_real_head_not_flagged`
**TestContinuationOrder**

- `test_duplicate_number_rejected`
- `test_lower_number_rejected`
- `test_increasing_accepted`
- `test_parent_then_child_accepted`
- `test_appendix_duplicate_rejected`
- `test_appendix_progression_accepted`
- `test_prefix_ignored`
**TestDepthCap**

- `test_deep_number_full_capture`
**TestUnitBracketGate**

- `test_unit_then_paren_rejected`
- `test_spaced_unit_then_paren_rejected`
- `test_title_starting_with_latin_kept`
**TestCascadeResistance**

- `test_real_head_after_false_head`
- `test_connector_needs_reference`
**TestIntegration**

- `test_continuation_does_not_duplicate`
- `test_deep_number_kept_distinct`
- `test_normal_progression_unaffected`
- `test_false_head_does_not_collapse_document`
- `test_unit_wrapped_title_not_clause`

### `tests/test_ks_answer.py`（28 个）

- `test_filter_effective_drops_non_effective_and_keeps_effective`
- `test_reference_clause_never_reaches_the_basis_list` — **征求意见稿（`reference`）绝不能当依据**（业主 2026-09-24：那种只能"仅参考"）。
- `test_dedupe_by_revision_id_and_on_pairs`
- `test_cap_enforces_upper_bound_8`
- `test_tier_three_states`
- `test_is_substantive`
- `test_clause_public_evidence_has_spec_fields_and_no_underscore`
- `test_parse_llm_answer_json_with_citation`
- `test_parse_llm_answer_code_fence_and_bare_text_fallback`
- `test_parse_llm_answer_out_of_range_index`
- `test_answer_direct_tier_returns_full_struct`
- `test_answer_effective_exclusive_and_upcoming_note` — 跨版本 5.2.1（现行2022/即将2025/已废止2018）→ 只保留现行，notes 说明即将生效。
- `test_answer_synthesis_tier`
- `test_answer_reference_tier_and_verification_marks`
- `test_answer_verification_flags_unsupported_clause`
- `test_answer_degrades_gracefully_when_llm_unavailable`
- `test_build_messages_includes_system_and_c_marks`
- `test_answer_rejects_empty_query`
- `test_answer_marks_every_evidence_item_with_bookmarked` — 逐条透出 bookmarked（宿主与提示词据此判断"范围过滤是否真的生效"）。
- `test_answer_bookmarks_only_filters_and_says_so` — bookmarks_only=True 且收藏集可用 → 只返回收藏条款，并在 notes 如实说明。
- `test_answer_bookmarks_only_with_empty_collection_returns_nothing`
- `test_answer_bookmarks_only_zero_hits_is_not_a_query_failure` — 收藏集查询成功、但**检索本身 0 命中** → 必须仍然声明"已限定"，绝不能输出。
- `test_answer_marks_bookmarked_unknown_when_collection_returns_none` — 查询函数返回 None（而非抛错）同样表示"未知"，不得当成空收藏集。
- `test_answer_bookmarks_only_filters_before_the_evidence_cap` — 上限**只在收藏集内**生效（verifier 六轮 P1）：先 `_cap` 再过滤时，收藏集条款。
- `test_answer_bookmarks_only_widens_the_candidate_pool` — 仅收藏时检索候选池被放大（默认 k=8 时收藏条款几乎进不了候选）。
- `test_answer_bookmarks_only_zero_hits_note_does_not_blame_the_collection` — 空结果时的措辞：不得断言"收藏集里没有相关条款"（可能只是没被检索到）。
- `test_answer_marks_bookmarked_unknown_when_collection_query_fails` — 收藏集查询失败：**不得**把"查不到"当成 False（那会让模型误报"过滤未生效"），。
- `test_answer_without_bookmarks_only_still_flags` — 未开仅收藏：仍透出真值（不写 notes 的范围声明）。

### `tests/test_channel_probe.py`（27 个）

**TestClassify**

- `test_判据表`
- `test_正文报错的措辞要提示先怀疑请求体` — 实测教训：flk 的 500 是我**请求体**不对，不是渠道坏 —— 措辞必须能分开这两件事。
**TestMinLinks**

- `test_链接数不足判可疑并点名`
- `test_链接数够且锚点在则通过`
- `test_两个期望可以叠加_任一不满足即不算通过` — 锚点对、但页面没链接（或反之）都不算过——消息要把两条都列出来。
- `test_链接计数大小写与换行都算`
- `test_只配_url_不配期望仍记_unknown`
- `test_429_是限流不是死` — R6a 实测：GitHub 上两条被 429，判 down 会让业主以为该换渠道。
- `test_坏_min_links_在读表时就要抛` — `probe_channel` 的契约是**不抛异常**——所以配置错误必须在读表时响亮报错。
- `test_目标形状坏也在读表时抛` — 独立复核 b28 / b28-fix 的发现：原先只校验 `min_links` ⇒ 字符串 target **静默过表**，。
- `test_大写_scheme_的_url_不该被误拒` — 反向：`startswith("http")` 会把合法的 `HTTP://e.com` 误拒（b28-fix 的 N2）。
- `test_合法_url_仍然照过` — 收紧 netloc/端口校验时最容易顺手误伤合法写法——这条钉住"12 个合法 URL 全照过"里的代表。
- `test_JSON_顶层数组允许` — `json` 只允许 dict 会把"发一个数组"误拒（b28-fix 的 N4）。
- `test_响应体不可序列化也不抛` — S1（b28-fix）：`json.dumps` 原先在 try 之外 ⇒ 怪响应体会从 probe_channel 逃出去，。
- `test_空_expect_若绕过校验就是假绿` — 把"为什么必须在读表时拒"钉成可执行的证据：空串锚点判恒真。
**TestProbeChannel**

- `test_成功路径带延迟与证据头`
- `test_dict_正文会被序列化后判锚点`
- `test_超时与传输异常都分级不抛`
- `test_没有_url_的渠道记_unknown_而不是_失败`
- `test_POST_的_method_必须真的传下去` — ⚠ dry-run 实测缺陷：漏传 `method` ⇒ transport 走 GET，而 flk/dbba **两层都回 200**。
- `test_POST_json_体与_headers_都传下去`
**TestProbeChannels**

- `test_persist_true_写台账_persist_false_一个字都不写`
- `test_没配目标的渠道不在默认探测集里`
- `test_指定不存在的渠道要抛`
- `test_目标表格式坏要抛`
**TestShippedProbes**

- `test_每个目标都有_url_与出处`
- `test_目标指向的渠道都在种子里` — 探针目标不许指向一个台账里不存在的渠道（否则永远探不到、也没人发现）。

### `tests/test_glue_ocr_units.py`（27 个）

**TestSplitValue**

- `test_split_value_with_unit`
- `test_split_value_micrometre`
- `test_three_digit_split`
- `test_no_unit_no_glue`
- `test_idempotent_split_value`
**TestSubscriptResidue**

- `test_subscript_joins_letter`
- `test_multi_subscript_variable`
- `test_product_variables`
- `test_superscript_on_unit`
- `test_greek_variable`
- `test_leading_subscript_not_merged_forward`
- `test_no_cross_type_still`
**TestGlue**

- `test_decimal_digits`
- `test_two_digit_group`
- `test_letter_units_min`
- `test_letter_units_mm`
- `test_letter_units_ssu`
- `test_type_boundary_no_cross_glue`
- `test_superscript_joins_segment`
- `test_normal_line_unchanged`
- `test_chinese_unchanged`
- `test_letter_pair_not_glued_unless_unit`
- `test_digit_pair_glues`
- `test_idempotent`
- `test_multiline`
- `test_empty_and_none`
- `test_leading_dash_number`

### `tests/test_material_dedup.py`（27 个）

**TestNormalize**

- `test_punctuation_and_whitespace_are_dropped`
- `test_fullwidth_folds_to_halfwidth`
- `test_case_folds`
- `test_empty_inputs_are_empty`
**TestSimilarity**

- `test_identical_is_one`
- `test_punctuation_only_change_is_near_one`
- `test_one_word_changed_stays_a_near_duplicate` — 改一两个词仍是"同一篇稿子"（**判据是阈值，不是 0.9**）。
- `test_different_wording_is_low` — **改写过的独立报道必须被判为不同**（否则会掐掉真互证）。
- `test_unrelated_text_is_low`
- `test_short_texts_fall_back_to_equality` — 短文本（< 3n）不做 n-gram：相等=1，不等=0（样本太短，Jaccard 不稳定）。
- `test_one_side_empty_is_zero_except_both_empty`
- `test_empty_against_empty_normalized`
- `test_threshold_is_configurable` — 阈值可调，且**行为随阈值单调**（用实测相似度定位，不靠我猜具体数值）。
**TestGroupByContent**

- `test_identical_texts_group_together`
- `test_distinct_texts_stay_separate`
- `test_output_is_deterministic`
- `test_empty_input`
**TestIndependentSourceCount**

- `test_syndicated_pair_counts_as_one`
- `test_two_genuinely_different_reports_count_as_two`
- `test_same_domain_two_articles_is_ONE_source` — 同一家媒体的两篇不同文章 = 一个来源（节点语义，不是内容分组数）。
- `test_syndicated_pair_plus_a_second_real_source`
- `test_unknown_identity_is_excluded` — 无域名的条目**不参与**（它们本来就不能互证，判据在 authority 那一层）。
- `test_all_unknown_gives_zero`
- `test_transitivity_is_handled_by_components` — 近似关系不传递（A≈B、B≈C 但 A≉C）——连通分量把它们并成一组（可复现的定义）。
**TestHonestLimits**

- `test_heavy_rewrite_is_not_detected` — **已知边界**：把通稿大改一遍后重发，本模块**抓不到**（判据只是"文字近似"）。
- `test_threshold_is_documented`
- `test_never_raises_on_missing_input`

### `tests/test_filing_state_pipeline.py`（26 个）

- `test_real_ingest_writes_filing_state` — 正例：真跑一次入库 ⇒ `doc_filing_state` 有这一行、`stage` 与识别率**真的被写**。
- `test_reverse_without_the_hook_no_state_row` — **反向哨兵**：把"写状态"这个出口打断 ⇒ 状态行**必须**不出现。
- `test_zero_clause_ingest_is_failed_and_still_visible_in_inbox` — 一条正文条款都没提出来 ⇒ `failed` + 失败原因 + `catalog_hidden=1`，**但仍在「待分类」里**。
- `test_reverse_good_doc_is_hidden_zero` — 反向：提出真条款的那一篇 ⇒ `catalog_hidden` 必须是 **0**（显式复位那条语句）。
- `test_reingest_parses_the_same_file_again_and_resets_hidden` — 「重来一次」：同一篇（先被隐藏）重导后 ⇒ 新行 `catalog_hidden=0` + 状态 `confirming`。
- `test_reingest_endpoint_marks_recognizing_and_parses` — **端点级**：`POST /kb/inbox/reingest` 立刻返回 + 真的把这一篇重导了（另起后台线程）。
- `test_reingest_endpoint_skips_missing_source_and_rejects_empty` — 边界：源文件不在磁盘上 ⇒ **如实跳过并说明**。
- `test_bulk_import_really_parses_and_writes_states` — 批量导入：`resume` 之后**真的有条款** + 占位行的状态从 `recognizing` 走到终态。
- `test_bulk_import_batch_flag_is_declared_and_default_false` — 批次开关：`create_bulk_batch(..., reingest=True)` 落在 checkpoint 里。
- `test_bulk_terminal_state_carries_files_whose_state_was_not_written` — 把"写状态"这个出口打断 ⇒ **批次终态**里要带出"哪几篇的状态没写进去"。
- `test_bulk_terminal_state_is_empty_when_states_were_written` — **反向**：状态正常写进去时，那一份清单必须是**空的**、接口报 0（不许恒报"有文件没写"）。
- `test_confidence_none_means_uncomputable_on_both_sides` — 识别率**算不出来**时：入库侧写 NULL、预览侧给 `None` —— **都不是 0.0**。
- `test_grading_tells_the_truth_when_confidence_is_uncomputable` — `grade_document(None)`：档位仍是 C（结果不变），但**理由**必须说"算不出来"。
- `test_bulk_endpoint_passes_force_and_reingest` — 接口层：`POST /ingest/bulk` 的 `reingest` / `force` 都要真的传下去（两个名字同义）。
- `test_abort_is_sticky_against_worker_resurrection` — 乙1 判据（2026-09-22）：中止后的终态**不许**被工作线程的状态写复活。
- `test_filed_doc_failure_writeback_flips_and_shows_in_inbox` — 乙3 判据（2026-09-22）：预标 `filed`（上传即归位）的文档，解析失败的回写必须。
- `test_flat_folders_supports_search_and_depth` — `GET /kb/folders/flat`：整棵树带路径、可按名字/路径搜、`depth` 是路径段数。
- `test_stage_labels_endpoint_is_the_single_owner` — 标签由**接口**下发（界面上那份镜像不再是唯一所有者）。
- `test_failure_kind_vocabulary_matches_the_migration_script` — 失败原因的**中文字面量**只有一个所有者：迁移脚本那份必须与 `folder_store` 逐字相同。
- `test_inbox_payload_carries_new_suggestion_fields` — 「待分类」每一项都带 `stage_label` / `suggest_new_parent_id` / `suggest_new_name` / `catalog_hidden`。
- `test_inbox_suggest_new_names_the_missing_segment` — 分类口径比命中的现有目录**更深** ⇒ 给出"在 XXX 下新建 XXX"的两个真值。
- `test_inbox_hidden_but_failed_doc_is_listed` — `catalog_hidden=1` 且 `stage='failed'` 的那一篇**必须**在列表里（§十七的硬要求）。
- `test_reingest_busy_is_409_not_a_queue` — 同一时刻只跑一批：锁被占 ⇒ **409 `reingest_busy`**（不许"排队等"）。
- `test_reingest_rejects_too_many_docs` — 边界：一次点太多 ⇒ 422（后台线程是串行的，防"手一抖选 379 篇"）。
- `test_reingest_plan_is_read_only` — `plan_reingest` 是**只读**的：它不许写状态、不许动库。
- `test_json_marker_file_path_is_skipped_honestly` — 快扫/异常行的 `file_path` 是标记 JSON ⇒ 如实跳过（不许拿它去 open）。

### `tests/test_mineru_cloud.py`（26 个）

- `test_validate_middle_passes`
- `test_validate_middle_rejects_bad_json`
- `test_validate_middle_rejects_missing_pdf_info`
- `test_validate_middle_rejects_empty_pages`
- `test_validate_middle_rejects_missing_page_idx`
- `test_normalize_landing_copies_and_prefixes`
- `test_normalize_landing_keeps_existing_prefix`
- `test_normalize_landing_no_middle_raises`
- `test_safe_extract_rejects_zip_slip`
- `test_safe_extract_normal`
- `test_available_false_without_key`
- `test_submit_and_wait_end_to_end`
- `test_submit_and_wait_guard_failure_raises`
- `test_submit_and_wait_network_failure_returns_none`
- `test_probe_token_ok`
- `test_probe_token_bad_auth`
- `test_adapter_uses_cloud_when_local_missing` — 本地未装 MinerU + 配了云 Key → 走云兜底（产物路径透传）。
- `test_adapter_no_local_no_key_returns_none`
- `test_adapter_no_key_uses_local_and_skips_cloud` — 未配置云 Key → 纯本地，云绝不被调用（2026-09-08 修订后语义）。
- `test_adapter_ks_mineru_local_zero_forces_cloud` — KS_MINERU_LOCAL=0（用户机器跑不动）→ 即使本地装了也直接走云。
- `test_egress_recorded_when_guard_fails_after_upload` — P0 门禁（verifier F2）：PDF 字节已外发后产物守卫失败 → 仍登记外发审计。
- `test_egress_recorded_when_poll_fails_after_upload` — 上传成功但轮询超时（网络类失败 → 返回 None）同样必须留审计。
- `test_429_backs_off_and_retries_once` — **限流 429 要原地退避重试一次**，而不是直接当网络失败返回 None。
- `test_429_backoff_is_not_infinite` — **429 持续存在时不许无限重试**——退避一次后仍失败就返回 None（交上层换 key）。
- `test_non_429_network_error_does_not_backoff` — **反向对照：非 429 的网络错误不许退避**（它们不是速率问题，退避无益且白等）。
- `test_explicit_api_key_overrides_global` — **显式 `api_key` 必须覆盖全局 settings 的 key**（竞态治本的关键）。

### `tests/test_question_router.py`（26 个）

**Test规则**

- `test_缺省就是五类_顺序按词表`
- `test_候选顺序就是链的顺序` — 前缀专用渠道天然排在兜底棒前面（T/ 号 → ttbz 第一）。
- `test_不在链上的渠道不进候选` — `ch:cssn` 声明能答"废止"，但它不在任何链上 ⇒ 候选里没有它，声明里还有它。
- `test_only_ok_滤掉判死_但不动声明` — 设计稿验收 2：台账判死 ⇒ 从候选消失。
- `test_unknown_与无探针不滤` — 没有证据说它死了 ⇒ 不能滤（滤掉等于凭空缩链）。
- `test_tool_永不出现` — 规则 5：`tool:` 的 `answers` 本来就是空的（规则 1 排除它）。
- `test_链注入两种写法都认` — `ndls` 与 `ch:ndls` 是同一根棒（换链源那天不会因一个前缀判成"不在链上"）。
- `test_链保序去重`
**Test空候选三种原因**

- `test_no_capability`
- `test_off_chain`
- `test_all_down`
- `test_有候选就是ok且不算unanswerable`
- `test_unanswerable_classes只点名空的那些`
**Test入参**

- `test_非法类别抛`
- `test_传单个字符串要说清楚` — `"废止"` 会被逐字拆成 `'废'`/`'止'`，报"不是五类之一"很费解 ⇒ 单独拦。
- `test_重复类别去重`
- `test_空类别列表返回空dict`
**Test真机对照**

- `test_废止候选非空且无tool`
- `test_与独立复算逐条一致` — 独立复算：直接读 JSON + `select_chain` + `first_route`，**不用**本模块的内部函数。
- `test_废止类会先问真拿得到废止日期的那根` — §11.0 R6c-4c 的**全部收益**就在这一条上：`废止` 类把 `ndls` 排到 `official_gb` 之前。
- `test_前缀专门渠道不被能力排序降级` — ⚠ 我第一版按判定**全局**排序，结果 HJ 号的"发布"先去问 `official_gb`——**把专门渠道降级**。
- `test_注入链也要保专门渠道在先` — ⚠ 复核 b37 的 A①：我第一版只在 `chain is None` 时算 `keep_first`，。
- `test_注入同一条链结果必须逐位相同` — **注入链不变式**（复核 b38 的开放项⑤）：把自然链原样注入，结果必须一字不差。
- `test_未审计的棒不越过partial` — ⚠ 复核 b37 的 A②：我第一版把"没审计（None）"与 `supported` 同键，。
- `test_已知缺口已被兜底链补掉_HJ不再一判死就丢两类` — **记录型用例：它按设计红过一次，这里是红过之后**有意**改成的样子。
**Test人用脚本**

- `test_json_模式能跑通且是合法json`

### `tests/test_answer_materials.py`（25 个）

**TestNoScopeIsByteIdentical**

- `test_prompt_unchanged_without_materials`
- `test_none_and_empty_string_are_equivalent`
**TestMaterialsSection**

- `test_materials_appended_as_separate_section`
- `test_addendum_carries_criterion_precedence_and_tier_rules` — 规则文本必须真的说了那四件事（**提示词就是产物**，直接断言文字）。
**TestCitationMarkers**

- `test_material_marker_does_not_trip_law_index_check` — `[[m:0]]` 不能被法条越界校验误判（两个平面各有各的编号空间）。
- `test_out_of_range_material_marker_is_flagged`
- `test_imagined_material_marker_is_flagged_when_no_materials` — **没给材料却引材料** = 凭想象引用，必须报出来（默认参数下同样成立）。
- `test_law_marker_still_checked`
- `test_negative_indices_are_flagged` — **负数越界必须被抓**（独立复核 2026-09-17 报的缺陷）。
- `test_conclusion_is_scanned_too` — **结论区也要扫**：规则 1 要求"每条结论后紧跟引用标记"，而旧实现只扫推导区。
**TestAnswerIntegration**

- `test_scoped_answer_injects_materials_and_records_usage`
- `test_unscoped_answer_has_no_material_usage`
- `test_unapproved_material_never_reaches_prompt` — **评审硬门在答案链上同样成立**：pending 材料的正文不得出现在提示词里。
- `test_unknown_project_is_reported_as_not_found`
- `test_t3_lead_only_is_labelled_in_prompt` — **业主验收点的后半句**：单独一条二手转述必须以"仅线索"进提示词，不得当依据。
- `test_material_load_failure_is_not_silent` — 材料取不到时必须说出来——否则会产出一份"看着正常、其实没用上制度"的答案。
**TestNaturalLanguageRecall**

- `test_natural_language_question_matches` — **最关键的一条**：用户用自然语言提问，必须能命中材料。
- `test_standard_number_query_does_not_silently_fail` — 带连字符的标准号不再触发 FTS 语法错误后静默空结果。
- `test_expression_builder_quotes_every_term` — 每个词都加引号 ⇒ 标点不可能被当 FTS 语法。
- `test_expression_uses_or_not_implicit_and`
- `test_known_limit_all_single_char_query` — **已知边界（钉住，别当 bug 反复"修"）**：全单字符词的查询无 FTS 表达式。
**TestFtsMatchExprIsTheSingleOwner**

- `test_matches_old_law_side_implementation`
- `test_latin_prefix_is_the_documented_exception` — **P3.1 的例外要显式钉住**，不能靠"那 15 条恰好没覆盖到"来蒙。
- `test_law_side_delegates_to_the_owner`
- `test_duplicate_query_side_tokenizer_is_gone` — verifier 报的"第三份查询侧分词实现"已随迁移**删除**（不是只记一笔）。

### `tests/test_channel_system_wiring.py`（25 个）

**Test自动巡检已接线**

- `test_run_真的调用_start_update_scheduler`
- `test_run_真的调用_stop_update_scheduler`
- `test_启动失败不阻塞引擎` — `start_update_scheduler()` 必须在 try/except 里 —— 线程起不来不该让引擎起不来。
**Test调度器幂等与生命周期**

- `test_重复_start_只起一个线程`
- `test_stop_后_is_running_为假`
- `test_未跑时_stop_幂等`
- `test_stop_后能再_start`
**Test建批后真的执行**

- `test_tick_and_run_会执行建出来的批` — 注入假 tick：返回一个"建了"的批 ⇒ 必须去跑它。
- `test_没建批时不去跑`
- `test_单批失败不拖累其余批`
**Test调度开关**

- `test_关闭时_tick_不建批` — `schedule_days()` 返回 0（关闭）⇒ `_create_scheduled_batches` 直接返回空。
- `test_接线没有绕过_scheduler_的_tick` — 结构判据：`tick_and_run` 必须**调 `tick()`**，不许自己另写建批逻辑。
**Test入库补CCS**

- `test_标准入库会查_CCS_并写标签` — 判据：`ingest_law_text` 对 standard 类型会调 `resolve_ccs`。
- `test_与_pipeline_同一所有者` — B4：CCS 判据**只有一个所有者**（`ccs_fetcher`），不许另写一份解析。
- `test_查不到_CCS_不阻塞入库` — B2：`resolve_ccs` 抛异常/返回 None 时，入库**必须仍成功**。
**Test绝不自动下载**

- `test_巡检代码里没有自动下载调用` — `inspector.py`（巡检执行体）里不许直接调 `archive_pdf`。
- `test_判定_new_version_不触发下载` — 结构判据：`new_version` 分支里不许出现下载动作。
**Test识别占位回退**

- `test_占位回退被判为失败` — 模拟 `archive_pdf` 写了占位 ⇒ `download_gate` 必须报失败。
- `test_真文件被判为成功` — 对照：真下到东西（比占位大）⇒ 报成功。
- `test_占位阈值引用唯一所有者` — 结构判据：不许自己抄一份占位字节数（判据分叉）。
**Test下载走审批门**

- `test_审批门问句说清来源与形态` — FR-010：问句必须含"来源 + 形态"（业主口径：不让用户读全文）。
- `test_拒绝则不下载`
- `test_同意则下载`
**Test下载校验非PDF**

- `test_archive_pdf_校验_PDF_魔数` — **复用**既有校验，不另写一份 —— 结构判据。
- `test_download_gate_不另写校验` — C4b：download_gate **不许**自己写一份 `%PDF` 校验（判据分叉）。

### `tests/test_real_question_ruler.py`（25 个）

**Test规模与结构**

- `test_恰好_500_条`
- `test_每条都有必填字段`
- `test_gold_std_不为空`
- `test_q_len_与实际长度一致`
**Test不把测不出来的算进分数**

- `test_没有投诉举报类`
- `test_没有超长问句`
- `test_没有过短问句`
- `test_stats_也如实声明`
**Test不偏科**

- `test_最大单一来源不超过_10_百分比`
- `test_覆盖至少_20_个来源`
- `test_stats_与复算一致`
**Test可追溯**

- `test_trace_key_格式正确`
- `test_trace_key_不重复`
- `test_url_允许为空但不允许错`
**Test可复现**

- `test_种子被记录`
- `test_输入规模被记录`
- `test_五道过滤计数齐全`
**Test分层如实**

- `test_分层计数与复算一致`
- `test_zero_overlap_很少是已知事实` — ⚠ 这条**故意断言它很少** —— 防止有人把 0.8% 说成"大白话损耗很小"。
**Test新分层有区分度**

- `test_各档合计等于条数`
- `test_至少四档非空`
- `test_最大一档不超过七成` — 若某一档占了绝大多数，说明分层退化成"一档独大" ⇒ 又没区分度了。
- `test_overlap_值在_0_到_1_之间`
- `test_overlap_中位与_stats_一致`
- `test_答复原文没被写进产物` — 答复原文受版权/使用条款约束（README 已写明），**不入库**。

### `tests/test_term_bridge.py`（24 个）

- `test_term_entry_re_splits_number_name_english_and_definition`
- `test_term_entry_re_accepts_unnumbered_and_dotted_numbering`
- `test_term_entry_re_rejects_full_width_paren_numbering_and_that_is_measured` — 全角括号编号（`（3）危险作业 …`）**收不下** —— 这是**有意的边界，不是洞**。
- `test_term_entry_re_rejects_rows_without_an_english_name` — 没有英文名的行**不是**术语条款 —— 拒掉才不会把正文句子当成术语。
- `test_term_entry_re_requires_a_chinese_definition_after_the_english_name` — 英文名后面必须还有中文 —— 否则只是一行英文标题。
- `test_merge_round_robin_interleaves_rather_than_concatenates` — **这条是 P1 扇出收益的机制**：轮转必须让第二份的第一条**插在**第一份的第二条前面。
- `test_merge_round_robin_dedups_keeping_first_occurrence`
- `test_merge_round_robin_tolerates_empty_and_missing_lists`
- `test_topk_by_cos_numpy_path_agrees_with_the_python_reference`
- `test_topk_by_cos_ties_break_by_smallest_index_on_both_paths` — 同分必须**按下标**定序，否则两条实现会在边界上给出不同答案。
- `test_topk_by_cos_ties_break_by_smallest_index_even_when_unsorted_prefix` — 并列 + `argpartition` 前缀乱序时，仍必须按小下标取。
- `test_topk_by_cos_head_is_sorted_and_that_assertion_is_not_vacuous` — **返回的头必须是降序**——而且这条用例的前提本身要被机械检查。
- `test_topk_by_cos_caps_k_at_the_number_of_candidates`
- `test_topk_by_cos_zero_vector_is_not_a_crash`
- `test_term_index_save_load_round_trip`
- `test_term_index_select_returns_empty_without_vectors`
- `test_term_index_matrix_cache_invalidates_when_the_length_changes`
- `test_term_index_matrix_cache_invalidates_when_the_candidate_set_is_replaced` — **等长换集**也必须失效（复核 2026-09-25 抓到的洞）。
- `test_term_index_matrix_is_normalised`
- `test_extract_term_entries_keeps_only_the_first_clause_per_term`
- `test_extract_term_entries_keep_all_exposes_the_dropped_same_name_entries` — `keep_all=True` 把**同名**的其余定义也取出来 —— 把"有损"变成可实验的东西。
- `test_extract_term_entries_strips_wrapping_punctuation_and_folds_whitespace`
- `test_extract_term_entries_skips_non_term_rows`
- `test_saved_cache_keeps_the_field_names_the_script_expects` — `measure-term-bridge.py` 按字段名读缓存。

### `tests/test_material_locator.py`（23 个）

**TestIngestRecordsTheProvenance**

- `test_file_material_records_hash_and_fingerprint` — 入库必须记下**派生全文哈希 + 解析器指纹**（否则锚点无从判定）。
- `test_web_material_records_the_collect_fingerprint` — 网页材料的指纹是**采集通道**那一个（它没有源文件可重解析）。
- `test_no_text_means_no_derived_hash` — 解析不出文本 ⇒ `derived_text_hash` 存 **NULL**（不是"空文本的哈希"）。
**TestCheapHealth**

- `test_untouched_material_is_ok_but_the_wording_is_honest`
- `test_old_material_without_provenance_is_unknown_not_ok` — 2026-09-17 之前的材料没有这两列 ⇒ **unknown**（不假装 ok）。
- `test_changed_fingerprint_is_stale` — 指纹变了 ⇒ `stale`（**不是**"已经坏了"——要说清要复算）。
- `test_no_chunks_means_no_locators`
- `test_no_chunks_with_text_says_which_cause` — `no_locators` 的**另一种**成因：有派生文本、但切块没产出（INFO-5）。
- `test_missing_content_hash_is_not_a_missing_file` — **文件在、但没有字节哈希** ≠ **文件不在**（复核 b10 的 LOW-3）。
- `test_pdf_cheap_check_refuses_to_claim_ok` — PDF 的完整指纹含**只有解析后才知道**的 text_layer/ocr ⇒ 便宜比对**不许说 ok**。
**TestSourceFileIdentity**

- `test_deleted_source_file_is_not_ok`
- `test_replaced_source_file_is_stale_not_ok` — 换成另一份同名文件 ⇒ `stale`，且**说清是源文件变了**（不是"解析器变了"）。
- `test_replaced_pdf_is_stale_not_unknown` — PDF 也一样：**字节变了就是 stale**，不许因为"指纹前缀相同"停在 unknown。
- `test_unchanged_source_still_ok` — **反向对照**：文件真的没变时必须仍然给 `ok`。
- `test_web_material_has_no_source_axis` — 网页件没有源文件 ⇒ 这一轴**不参与**（不是"源文件不在"的告警）。
**TestStrongReverify**

- `test_unchanged_source_matches` — 源文件没变 ⇒ 重解析**逐字节一致**（这才是真正的保证）。
- `test_changed_parser_output_is_a_mismatch` — **解析器变了**（模拟：重解析得到不同文本）⇒ `mismatch`，且措辞点明"区间已失效"。
- `test_web_material_cannot_be_reverified` — 没有留存源文件 ⇒ `unavailable`（**不是 ok**）。
- `test_text_then_blank_reparse_is_a_mismatch` — 入库时**有**文本、现在重解析**一个字都得不到** ⇒ **确定的失效**。
- `test_missing_material_raises`
**TestProjectSummary**

- `test_one_crashing_material_does_not_kill_the_whole_overview` — **一份材料的判据挂掉，不该毁掉整个项目总览**（INFO-3 的同型问题，2026-09-18 修）。
- `test_counts_and_attention_list`
- `test_bootstrap_guarantees_the_material_columns` — **引导契约**：`init_schema()` + 两个 ensure 之后，两张表的追加列都在。

### `tests/test_ocr_regression_fixtures.py`（23 个）

**TestLeqslantLeak**

- `test_positive_clean` — 修复形态：泄漏形态归一到 ≤。
- `test_negative_leaked_form` — 负向：清洗产物不得含 ≤slant / ≥slant。
- `test_eq_tag_path` — 行内公式 <eq>…</eq> 全链路同样不泄漏（入库路径）。
**TestWideSpacedDigits**

- `test_property_digit_glue` — 性质：数字间单空格形态应被粘合（宽字距还原）。
**TestPuaNormalize**

- `test_positive_recover` — 修复形态：犬部+数字平移整体还原。
- `test_property_no_pua_residue` — 性质：任何 PUA 输入归一化后无犬部码位残留。
- `test_positive_sqrt_body` — 修复形态：根号 PUA 替身 '槡' → '√'（34406 公式区实测）。
- `test_property_ascii_digits_restored` — 性质：0x21-0x2A 平移区字符全部还原为数字（无一漏网）。
**TestAreaSubscript**

- `test_positive_sub` — 修复形态：面积判据（>数值）下 A° → Aₑ。
- `test_positive_area_context` — 修复形态：'有效散热面积'上下文同样转换。
- `test_negative_angle_untouched` — 负向（防误伤）：无面积判据的角度 A° 不转。
**TestChemBondDash**

- `test_positive_bond` — 修复形态：PUA 键 → em dash。
- `test_negative_no_raw_pua` — 负向：键线产物不得残留  原码位。
**TestMeaningMarks**

- `test_positive_hat_bar`
**TestWatermarkStrip**

- `test_positive_wm_url_gone`
- `test_negative_inline_url_untouched` — 负向（防误伤）：行中合法 URL 引用不剥（仅整行水印语义才剥）。
- `test_property_pageno_forms_covered` — 性质：全角/罗马页码形态剥后不留。
**TestSymbolTable2026Additions**

- `test_symbols_present` — 正向：24276 实测缺漏的符号全部可转换。
- `test_property_word_boundary_no_eat` — 性质：词边界防前缀误吃（\pm 不吃 \pmb。
- `test_long_key_priority` — 性质：长键优先（\leqslant 先于 \leq，否则被前缀吞掉）。
**TestShiftedDigitGuard**

- `test_negative_normal_text_not_mangled` — 负向（防误伤核心）：正常文本（正常标点 + 正常数字占比）判 False。
- `test_positive_shifted_digits_detected` — 正向：真数字平移型（!-* 密集 + 正常数字≈0）仍判 True。
- `test_property_digit_ratio_gate` — 性质：判据二的数字占比门槛——含足量正常数字的文本不触发整体平移判定。

### `tests/test_standard_no_ocr_suffix.py`（23 个）

**Test剥来源后缀**

- `test_剥掉半角括号后缀`
- `test_剥掉全角括号后缀`
- `test_剥掉后两侧空白`
- `test_真库样例_带书名号截断的那种`
- `test_连续两个后缀`
**Test不动合法括号**

- `test_合法括号_聚丙烯PP树脂`
- `test_合法括号_湿式非金属类`
- `test_合法括号_结尾也是括号`
- `test_副本后缀不动_那是另一个判据`
**Test不动官方标准尾部中文**

- `test_官方标准_食品安全国家标准`
- `test_官方标准_术语`
- `test_四篇里的每一篇都不动`
**Test不动以中文括号结尾的名字**

- `test_刑法修正案_中文括号结尾`
- `test_规则试行_中文括号结尾`
- `test_公告_中文括号结尾`
- `test_已废止_中文括号结尾`
- `test_测试夹具_中文括号结尾`
- `test_真库那_88_条的形态都不动` — 把真库实测的 88 条形态**逐条**过一遍（这是从库里抄下来的，不是编的）。
**Test边界**

- `test_空串`
- `test_None`
- `test_只有后缀_剥成空`
- `test_幂等`
- `test_中间的OCR采集不动`

### `tests/test_apply_folder_filing.py`（22 个）

- `test_dry_run_writes_nothing`
- `test_dry_run_prints_what_would_happen`
- `test_apply_builds_tops_and_skips_the_redundant_level`
- `test_states_and_members_are_exactly_the_plan`
- `test_hidden_docs_go_to_pending_as_failed`
- `test_hidden_doc_with_real_clauses_gets_an_honest_failure_kind` — 库里**有**正文条款还写着"正文条款为零"就是编 —— 必须换成如实的话。
- `test_reused_tops_get_the_hand_set_order` — 早先以 sort=0 建出来的顶层目录，复用后 sort 要对齐到业主手定的。
- `test_apply_twice_changes_no_counts`
- `test_missing_tables_are_created_and_nothing_else_is_touched`
- `test_ddl_comes_from_schema_sql` — 建表语句必须是**从 schema.sql 现取的**那三张表的（不手抄一份）。
- `test_backup_is_taken_and_verified`
- `test_backup_failure_aborts_before_writing` — 备份目录不可用 ⇒ 退出码 2，**库一个字节都没动、一行都没写**。
- `test_apply_aborts_when_an_existing_index_is_missing` — ① 先删掉一个既有索引 ⇒ ``--apply`` 必须非 0 且**零写入**。
- `test_apply_aborts_when_an_existing_table_gained_a_column` — ② 给既有表**加**一列 ⇒ **不中止**（只登记）。
- `test_apply_aborts_when_a_declared_column_is_missing` — ② 库里少了 ``schema.sql`` 声明的列 ⇒ **中止**。
- `test_dry_run_prints_zero_write_proof_and_three_size_numbers` — 预演要**打印三个数**（.db / -wal / 合计）与"零写入证据"（第 2 步的措辞修）。
- `test_schema_drift_reports_extras_but_does_not_fail_on_them` — ``schema_drift`` 的四个清单各就各位：多列只登记。
- `test_declared_objects_splits_sql_despite_comments_and_semicolons` — ``declared_objects`` 必须真的解析出列。
- `test_refuses_when_the_unskipped_tree_is_already_there` — 顶层已经有「国家标准·行业标准·团体标准」⇒ 拒绝，免得建出两棵并存的树。
- `test_skipped_level_and_top_names_come_from_one_owner` — 「跳过哪一段 / 真顶层叫什么」只有**一个**所有者（复核 2026-09-21 的①）。
- `test_read_back_matches_the_database` — 读回自证的数字必须与**直接查库**的结果一致（不是自说自话）。
- `test_engine_running_prints_a_warning_but_does_not_block` — 引擎在跑 ⇒ 打印醒目警告，但**不阻塞**（预演仍然跑完、仍然一个字不写）。

### `tests/test_dryrun_batch.py`（21 个）

- `test_batch_buckets_conserve`
- `test_batch_single_failure_does_not_abort` — 把坏文件排到第 2 位，后面 6 个仍必须全部被评估。
- `test_batch_sample_is_deterministic_stride` — sample=5 抽 5 本，且两次跑结果完全相同（确定性等距）。
- `test_batch_sample_zero_or_none_means_all`
- `test_batch_no_db_write`
- `test_batch_limit_files_truncates`
- `test_batch_rows_are_thin` — 每行只有摘要字段（不回传全文——payload 红线）。
- `test_batch_scan_preview_dir_missing`
- `test_batch_scan_preview_dir_sorted_and_filtered`
- `test_batch_never_asks_for_deep` — **批量路径默认不外发**：不传 deep_fallback 时每个文件都必须以 False 解析。
- `test_batch_deep_switch_defaults_off_and_optin_really_wires_through` — D5 后的新契约（**替代**原 `test_batch_preview_batch_has_no_deep_switch`）。
- `test_batch_limit_files_negative_is_clamped` — 负的 limit_files 不得静默"从尾部砍"（审计 P2-2）：夹到 0 → 一个都不评估。
- `test_api_preview_ok_envelope`
- `test_api_preview_bad_requests`
- `test_api_preview_requires_token`
- `test_api_blocked_doc_is_200_not_5xx` — 坏文档 → HTTP 200 + verdict=block（不是 500，也不是 4xx）。
- `test_api_preview_allow_deep_is_wired_and_reported` — D5：`allow_deep=true` 从"422 拒绝"改为**真接线 + 如实标注**（替代原。
- `test_api_preview_allow_deep_non_bool_is_rejected` — `allow_deep` 必须**严格布尔**，且**只有真布尔 true 才开启**（独立复核 F4）。
- `test_api_preview_accepts_extensionless_pdf` — **无扩展名的 PDF 必须被接受**（真机发现）：DSH 附件是哈希文件名。
- `test_api_preview_rejects_non_pdf_content` — 内容是垃圾、后缀也不是 .pdf → 请求级 422（判定权在 dry_run，路由不重复实现）。
- `test_api_batch_and_inbox`

### `tests/test_govqa_label_review.py`（21 个）

**Test产物存在且规模对**

- `test_四份产物都在`
- `test_两半条数相同且与源一致`
- `test_与源_CSV_条数一致`
- `test_两半的_qid_集合相同`
- `test_qid_不重复`
**Test两半必须分开**

- `test_语言半不含_label_字段`
- `test_语言半字段恰好是_qid_与_question`
- `test_事实半含_label_与_label_source`
- `test_语言半的_md_条目区不出现_现标字样`
- `test_事实半的_md_每条都有现标`
**Test标注为_AI_判定而不是人工确认**

- `test_事实半标注了_AI_判定`
- `test_语言半标注了_AI_判定`
- `test_摘要的_kind_是_AI_判定`
- `test_摘要声明了规格原文没改`
- `test_不声称已满足规格` — 产物里**不许**把"已满足 FR-004/SC-003"当成**结论**说出来。
**Test不声称准确率**

- `test_摘要的_accuracy_是_null`
- `test_产物里不出现具体准确率数字`
**Test标签口径**

- `test_摘要的标签全集是_11_类`
- `test_摘要的标签分布合计等于条数`
- `test_摘要的_label_source_分布合计等于条数`
- `test_事实半的标签都在全集内`

### `tests/test_jev_guard.py`（21 个）

- `test_guard_triggers_on_all_ten_measured_hits` — 该触发的 10 条**一条不漏**（含 8 条隐性合规——词表对它们 1/8）。
- `test_guard_silent_on_all_ten_technical_messages` — **不该触发的 10 条技术话一条都不许"触发"**（词表瘦身前 9/9 误触发）。
- `test_guard_three_technical_ones_land_in_review` — 实测的三条**中间档**：不静默、不触发——这正是"review 阈值"存在的理由。
- `test_guard_review_band_does_not_trigger` — 中间档：分数落在 review 与 action 之间 ⇒ review，**不**触发。
- `test_guard_severity_escalates_review_to_trigger` — 严重度越线 ⇒ 把 review 升级成触发（官方护栏蓝本的 severity 通道）。
- `test_guard_degrades_to_none_when_jev_unavailable` — **Jev 挂 ⇒ 返回 None（调用方退回词表）**，绝不让合规护航整体失效。
- `test_guard_degrades_when_key_missing` — 没配 Key ⇒ 直接 None（不联网、不报错）。
- `test_guard_rejects_malformed_answer` — 响应不合契约（缺 noul / 类型不对）⇒ 当不可用，**不猜**。
- `test_guard_questions_all_have_criteria` — **每道 Noul 都必须带 criteria**（官方硬要求。
- `test_client_pins_model_version` — **模型名钉死版本**，不用会漂移的别名（官方：调过阈值就别用别名）。
- `test_client_rejects_bad_values` — **坏值不许当判定**（独立复核 MED-2：`True` / `1.1` / 模型别名都曾被当合法）。
- `test_client_score_range_is_levels_not_unit_interval` — ⚠ **Score 不是 0~1**（2026-09-24 真机踩到：我的校验把三个字段一起按 0~1 判，。
- `test_client_score_range_unknown_scale_does_not_reject` — **量表档数拿不到时，不判 `score` 的值域**（独立复核 2026-09-24 MED 抓到的假严）。
- `test_client_rejects_bad_confidence` — Choice 的 `confidence` 必须在 0~1（`jev_ingest` 的 clear/review 门控靠它）。
- `test_breaker_reopens_after_cooldown` — **冷却一过、下一次失败会重新开熔断**（独立复核 MED-1 实测的洞：。
- `test_every_egress_is_audited` — **每一次外发都审计**（独立复核 MED-6：原先只有成功路径登记 ⇒ HTTP 503 那次查不到）。
- `test_audit_failure_does_not_break_decision` — 审计写失败**不反噬**判断结果（审计比判断重要，但不能让外部服务把护栏带崩）。
- `test_compliance_guard_endpoint_contract` — 端点契约（独立复核 MED-5：禁掉 `if verdict is None` 那支，26 条测试仍全绿 ⇒ 没钉住）。
- `test_change_signals_endpoint_contract` — `/laws/change-signals` 的契约（2026-09-24 真机核查时补的）。
- `test_compliance_guard_is_heavy_path` — 2s 外网 ⇒ 吃重活令牌（MED-3。
- `test_client_breaker_trips_after_repeated_failures` — 连续失败到阈值 ⇒ 熔断，后续**不再发请求**（省掉每条消息一次超时）。

### `tests/test_ks_answer_bbox.py`（21 个）

- `test_attach_bboxes_fills_bbox_and_page`
- `test_attach_bboxes_prefers_page_start`
- `test_attach_bboxes_falls_back_to_first_when_page_start_missing`
- `test_attach_bboxes_skips_when_no_span_on_page_start` — `page_start=5` 但该条款的 span 只在第 9 页 ⇒ **留空**，不许退化到 spans[0]。
- `test_attach_bboxes_uses_page_start_span_when_cross_page` — 跨页条款：只要 `page_start` 那一页**有** span，就取它（不取 sort_order 第一个）。
- `test_attach_bboxes_leaves_absent_when_no_span`
- `test_attach_bboxes_never_writes_zero_placeholder` — **假证据**防线：0 兜底会让前端在页面左上角画一个错箭头。
- `test_attach_bboxes_skips_malformed_bbox`
- `test_attach_bboxes_rejects_non_finite`
- `test_attach_bboxes_survives_db_error`
- `test_attach_bboxes_survives_missing_connection`
- `test_attach_bboxes_noop_on_empty`
- `test_attach_bboxes_noop_when_no_revs`
- `test_attach_bboxes_handles_multiple_revs`
- `test_attach_bboxes_rejects_degenerate_box` — **退化框必须拒收** —— 真库实测 `GB 17681-2024` 全篇 370/370 条都是这种碎片。
- `test_attach_bboxes_rejects_thin_box` — 只满足一个维度也不许 —— 宽 200pt 但高 0.5pt 的"一条线"同样看不见。
- `test_attach_bboxes_rejects_narrow_box` — 高 13pt（正常）但宽 2pt 的窄条也不许（画出来是一根看不见的竖线）。
- `test_attach_bboxes_accepts_normal_line` — **正常正文行必须通过**（防"阈值太松把正常行也拒了"）—— 用真库实测的中位量级。
- `test_degenerate_thresholds_are_the_documented_values` — 阈值是**规范值**（有实测依据），不许随手改。
- `test_attach_bboxes_skips_degenerate_but_keeps_normal` — 同一条款有多个 span 时：退化框被跳过，**正常框仍被采用**（不是整条丢弃）。
- `test_attach_bboxes_all_degenerate_leaves_empty` — 该条款的 span **全是**退化框 ⇒ 留空（不许拿任意一个凑数）。

### `tests/test_pool_depth_ruler.py`（21 个）

- `test_exact_and_modality_are_never_truncated` — ★ 每一条臂里 `exact`/`modality` 都必须**原样全量**（唯一变量只有 fts/vec 的池深）。
- `test_a0_prod_replicates_production_caps` — ★ A0_prod = 生产：fts/vec 各 20 条（它是仪器对照臂，不许漂）。
- `test_pool_depth_arms_take_declared_depth` — ★ 池深臂按各自声明取数（100 / 1000）。
- `test_take_doc_diverse_caps_per_doc_and_budget` — ★ 每篇文档最多 `per_doc` 条、总数不超过 `budget`，且**保序**。
- `test_take_doc_diverse_skips_unknown_docs` — ★ 查不到文档的 id 必须跳过（与生产 `fetch_full_clause` 取不到就跳过同向）。
- `test_doc3_arm_uses_doc_diverse_not_plain_truncation` — ★ `P1000_doc3` 的 fts/vec 必须走**文档去重**（预算 20），不是简单取前 20。
- `test_oracle_pool_is_union_then_truncate_per_channel` — ★ oracle 池 = `exact ∪ modality ∪ fts[:d] ∪ vec[:d]`（**逐路截断**再并集）。
- `test_hit_rate_is_inclusive_at_boundary` — ★ 名次恰等于 20 算命中。
- `test_flip_and_delta_direction` — ★ 非对称样本上 `(翻进 b, 翻出 c)` 与 Δ 的方向：净改善必须读成正 Δ。
- `test_missing_item_raises` — ★ 缺一条必须抛错，不许静默补 0（补 0 会让 @20 的分母错而读数看不出来）。
- `test_oracle_aggregation_counts_booleans` — ★ oracle 聚合必须数 `True` 的比例（写成数非空会让它恒 100%）。
- `test_instrument_check_counts_identical` — ★ 仪器对照读数必须数 `check_identical`（它不是装饰，是整批作废的开关）。
- `test_pool_median_definition_is_pinned` — ★ `pool_median` 取**上中位** `sorted[n//2]`：排序后 [10,20,30,1000] ⇒ 30（≠ 下中位 20）。
- `test_fused_hit_n_and_median_are_defined_on_top20` — ★ `fused_hit_n` / `fused_median_rank` **定义在 @20 上**（与冻结版逐位一致）。
- `test_arm_rank_reads_both_ledger_shapes` — ★ `arm_rank()` 必须同时吃**新台账**（`rank20/100/1000`）与**旧台账**（`rank` + `hit@100`）。
- `test_top100_and_top1000_are_not_copies_of_top20` — ★ **第 15 轮复核 P1-1 的回归判据**：`@100`/`@1000` 必须用**对应深度的名次**算。
- `test_legacy_ledger_reports_only_measured_depths` — ★ **第 15 轮复核 P1-1 的修法判据**：旧台账（只有 `rank` + `hit@100`）下，。
- `test_by_subset_top20_partitions_by_label` — ★ `by_subset_top20` 按 label 分组 + 组内闭区间。
- `test_production_caps_and_exp7_reuse_points_still_exist` — ★ 生产的两处硬编码上限（A0_prod 复刻的对象）+ exp-7 的复用点必须仍在。
- `test_ledger_stores_three_depths_separately` — ★ 台账必须**分别存** `rank20`/`rank100`/`rank1000`（第 15 轮复核 P1-1 的根因锚点）。
- `test_stop_loss_preregistered_contract` — ★ 预注册文件必须在，主终点 = `fused@20`，臂表与代码一致。

### `tests/test_update_announce.py`（21 个）

- `test_ann_n01_normalize_url_variants` — 尾斜杠/默认端口/大写 host/追踪参数/fragment 归一为同串 → 同 hash。
- `test_ann_n02_private_url_rejected` — SSRF：内网 IP/loopback/.local/非 http(s) → True。
- `test_ann_n03_parse_normal_page_with_date_and_stdno` — 正常页：条目抽取/相对链接绝对化/日期变体归一/标准号识别/噪音过滤。
- `test_ann_n03b_directory_links_are_not_announcements` — **栏目导航链接不是公告**（2026-09-24 真机缺陷的判据）。
- `test_ann_n04_parse_empty_and_js_shell` — 空页 → parse_empty 语义交由调用方。
- `test_ann_n05_parse_item_cap_50` — 每页条目上限 50（truncated 标记）——防导航页误判成万条目。
- `test_ann_n06_parse_illegal_date_left_blank` — 非法日期（2026-13-45）诚实留空，不猜测。
- `test_ann_n07_source_crud_validation` — CRUD 校验矩阵：缺字段/内网拒绝 → UPD-3008。
- `test_ann_n08_no_source_cap` — **源数量不设上限**（2026-10-08 删 `SOURCES_MAX`）：加 60 条都应成功。
- `test_ann_n09_scan_baseline_then_dedup` — 首扫基线（不计新）→ 二扫去重 0 新 → 换源同 URL 两行隔离。
- `test_ann_n10_scan_new_items_and_recent` — 列表页新增条目 → new_count 与 recent（≤5）正确。
- `test_ann_n11_scan_failure_honesty` — 失败诚实：http 500 / 验证码页 / JS 壳 / 空 parse —— 每源 failed+reason，。
- `test_ann_n12_scan_409_running_gate` — 409 双闸：进程内已有扫描登记 → request_scan 抛 UPD-2006。
- `test_ann_n13_scan_stale_recovered` — 僵尸扫描自愈：state running 但进程内无登记 → 新扫描照常开（记审计）。
- `test_ann_n14_disabled_source_skipped` — 禁用源不抓取（不进 per_source 清单也不发 HTTP）。
- `test_ann_x15_export_reopenable` — xlsx 落 exports、openpyxl 重开：源状态 sheet（逐源行）+ 明细全量行数。
- `test_ann_x16_export_empty` — 空库/从未扫描：同样出文件，明细仅表头。
- `test_ann_n17_discover_next_pages_js_pager` — **JS 拼的翻页**（应急管理部那种）：原始 HTML 里没有真 `<a>`，只有。
- `test_ann_n18_discover_next_pages_real_links_and_none` — **真 `<a>` 翻页链**收同目录的"下一页"。
- `test_ann_n19_scan_walks_pages` — **翻页真的翻**：列表 3 页（第 2/3 页由 `index_1/index_2.shtml` 拼）。
- `test_ann_n20_scan_stops_when_caught_up` — **追上历史就提前停**：所有条目都见过时，不许把预算页数全翻完。

### `tests/test_watermark_own_standard.py`（19 个）

- `test_table_last_cell_survives_with_own_standard` — 传了自家标准号 → 表格末格（别人的标准号）不再被当成页眉删掉。
- `test_own_header_tail_is_still_removed` — 自家的行尾页眉仍必须删干净 —— 修缺口不等于把真页眉一起放过。
- `test_own_header_line_is_still_removed` — 整行即页眉（`^…$` 族）同样只按自家标准号判定。
- `test_foreign_standard_only_line_is_kept` — 整行只有**别的**标准号时，不再整行删除（那可能是一格独立成行的数据）。
- `test_own_standard_fullwidth_still_matches` — 库里的标准号可能是**全角斜杠**（实测 `GB／T 10067.6-2023`）。
- `test_header_written_without_slash_t_is_still_removed` — **页眉常把 `GB/T` 印成 `GB`**（实测 226 行属此类）→ 比较键必须只认"号 + 年"。
- `test_different_number_same_family_is_kept` — 同一个前缀族但**号不同** → 是别人的标准，必须保住（表格里的引用）。
- `test_different_part_same_number_is_kept` — 分册号不同（10029.2 vs 10029）→ 不同分册，必须保住。
- `test_fullwidth_slash_inside_text_is_not_matched` — **已知限制（有意保留，不修）**：正文里的全角斜杠标准号不被页眉判据识别。
- `test_legitimate_text_still_survives_with_own_standard` — 传 own_standard_no 不得削弱原有的"合法引用必存活"保证。
- `test_watermark_tokens_still_removed_with_own_standard` — URL / 工具水印两族与 own_standard_no 无关，仍应照删。
- `test_without_own_standard_behaviour_is_unchanged` — **不传 own_standard_no 时保持历史行为**（表格末格仍会被删）。
- `test_canon_standard_no`
- `test_ingest_wiring_passes_own_standard` — **端到端接线**：`build_clause_models(doc_id, standard_no, …)` 必须把文档自己的。
- `test_ingest_removes_own_header_end_to_end` — 自家页眉（页码 + 本文档标准号）在真链路里仍被删掉。
- `test_ingest_inline_furniture_keeps_foreign_standard` — **行内**家具片段也已接上下文：引用**别的**标准的片段（表格末格）不再被剥掉。
- `test_ingest_short_block_keeps_foreign_standard` — **短块**（≤80 字）走切分层的家具剥离 —— 传了标准号后同样不再误删。
- `test_splitter_without_standard_keeps_historic_behaviour` — **向后兼容**：不传 `standard_no` 时，切分层的家具剥离仍是历史行为（一律剥掉）。
- `test_own_key_of_rejects_placeholder` — `_own_key_of` 必须把"看着不像标准号"的占位符挡回 None。

### `tests/test_disagreement.py`（18 个）

**TestO2Fallback**

- `test_collapsed_when_dominant_high`
- `test_not_collapsed_when_mixed`
- `test_empty_scores_is_collapsed`
- `test_select_2c_input_score_mode`
- `test_select_2c_input_legacy_when_collapsed`
**TestSimilarity**

- `test_identical`
- `test_whitespace_insensitive`
- `test_totally_different`
- `test_empty_both`
- `test_empty_one_side`
- `test_partial`
**TestCompare**

- `test_agree`
- `test_disagree`
- `test_threshold_semantics`
**TestReport**

- `test_assembly_counts`
- `test_report_dict_roundtrip`
- `test_disagree_item_captures_both_heads`
**TestConstants**

- `test_disagree_ratio_sane`

### `tests/test_pipeline.py`（18 个）

- `test_load_middle_items_drops_discarded`
- `test_split_clauses_and_table_binding`
- `test_split_rejects_table_value_clause_heads` — E8 表格数值防误判（2026-08-28 生产实测）：成分表数据行不得切成 0.x/伪章号条款。
- `test_pua_detector_catches_cid_garbage_without_pua_glyphs` — E9 cid 乱码变体（2026-08-28 GB/T 20529.2-2010 实测）：文本层不含。
- `test_pua_detector_catches_ascii_mapped_garbage` — E9b 判据四：cid 错位第四形态——汉字被映射为 ASCII（GB/T 35210.1-2023。
**TestNonChineseTextIsNotMangled**

- `test_english_paper_text_is_not_mangled`
- `test_garbled_ascii_mapped_chinese_is_still_mangled` — 对照：**原来的真乱码案例仍须判中**（别为了修误伤把这条判据废掉）。
- `test_the_two_signals_separate_english_from_garbled_ascii` — 把判据背后的**两个量**单独钉住（这样以后谁改了阈值，能看出动的是哪一条）。
**TestLatinProseThresholdIsAnchored**

- `test_real_english_excerpt_stays_above_both_thresholds` — 活锚：真语料里较难的一段，两个量都还高过阈值**且留有余量**。
- `test_thresholds_sit_inside_the_measured_gap` — 阈值不许贴住真英文下界（这一条杀"改严"：0.70→0.90 就死在这里）。
- `test_every_repo_garbled_fixture_is_still_caught` — **行为不变量**：仓里每一条乱码夹具都必须仍被判中（这一条杀"改宽"）。
- `test_letter_ratio_side_has_no_repo_fixture_lower_bound` — **诚实登记**：字母/标点那一侧的**下界在本仓钉不住**——别假装钉住了。
- `test_delete_document_uses_bulk_fts_delete` — E10 性能根因（2026-08-28 试点实测）：clause_fts.clause_revision_id 是。
- `test_build_models_classification_and_edges`
- `test_classifier_details`
- `test_real_middle_json_integration`
- `test_interline_equation_restored` — 2026-09-01 独立公式行（interline_equation）不再蒸发（GB/T 24276。
- `test_resolve_edges_reports_unresolved` — 未解析引用必须留痕（iteration-6 自查 §8.2，代码级核实）。

### `tests/test_secret_store.py`（18 个）

- `test_store_path_matches_config_data_dir` — 存储路径规则必须与 config._default_data_dir 一致（两份规则，一条断言钉住）。
- `test_store_path_matches_config_WITHOUT_override` — ⚠ **缺口钉子（2026-10-18 补）**：**不设 `KS_DATA_DIR`** 时两边也必须一致。
- `test_protect_roundtrip_and_no_plaintext`
- `test_unprotect_wrong_entropy_returns_empty` — 别的程序（换 entropy）拿到密文也解不开 —— 但我们得**降级**而不是崩。
- `test_unprotect_garbage_returns_empty`
- `test_empty_plaintext_roundtrip`
- `test_protect_rejects_non_str`
- `test_oversize_value_rejected`
- `test_file_contains_names_but_no_plaintext`
- `test_write_is_merge_and_delete`
- `test_write_zero_values_is_noop`
- `test_no_temp_files_left_behind`
- `test_corrupt_file_degrades_to_empty`
- `test_wrong_shape_json_degrades`
- `test_unwritable_dir_raises_on_write_but_read_still_safe` — 写失败必须**吵**（不能静默丢 Key）。
- `test_concurrent_writes_do_not_lose_values` — 两个线程各写一个通道名：锁必须让两个名字都留下（不能后写覆盖前写）。
- `test_stale_lock_is_reclaimed` — 崩溃遗留的锁文件不能永久卡死写入。
- `test_write_path_never_touches_winreg` — 把 winreg 换成"一碰就炸"，写入仍然成功 ⇒ 写路径一行 winreg 都没有。

### `tests/test_class_outcomes.py`（17 个）

**Test结论抽取**

- `test_发布要发布日期_没有就不算答` — ⚠ 不许拿实施日期顶发布——那正是 R6c-3c/3e 修掉的错标。
- `test_修订三态都算答了` — **否定的结论也是结论**：`no_change` = "没有被代替"，是 `修订` 类的答案。
- `test_废止_现行也是结论_非废止时无废止日期` — ⚠ 这一条是**拿真机演示改出来的**：我第一版只在 `withdrawn` 时才算答了，。
- `test_现行性与编号核验`
- `test_非法类名要抛`
**Test组装**

- `test_答的棒在候选里才算answered`
- `test_候选在但没轮到它_记not_probed而不是答不出来` — 第一棒命中了 ⇒ 这一类的候选**根本没被问过**。
- `test_答的棒在候选里但没给字段_记channel_gave_no_field` — 对照上一条：候选里**有**答的这根棒，所以是"问了、没给"，不是"没问"。
- `test_问了但没给这一类要的字段` — `mee` 对"发布"答不了：它的列是**实施时间**，而这一条**不许拿实施日期顶发布**。
- `test_渠道给了否定结论也算answered` — 对照上一条：`official_gb` 说"现行" ⇒ `废止` 类**答了**（否定的答案），带 partial。
- `test_空候选的原因原样带出`
- `test_三类结构性原因都算unanswerable`
- `test_真表跑一遍_结论与判定都对得上` — 用**真能力表**跑一次（不注入 table）：`completeness` 应当来自 b35 的审计。
- `test_词表封闭`
**Test整链都没命中**

- `test_候选在_记not_probed`
- `test_结构性缺口照样进unanswerable`
- `test_没有channel与conclusion字段` — 没有"谁答的"这回事——所以不许出现 `channel`/`conclusion`（免得下游误读成答过）。

### `tests/test_embedding_rebuild_resume.py`（17 个）

- `test_display_text_matches_production_formula`
- `test_production_source_still_has_the_same_formula` — 静态锚点：生产源码里必须仍有 `title or ''` + `content_text[:512]` 的 f-string。
- `test_text_formula_sha_is_stable_and_sensitive`
- `test_ckpt_guard_allows_matching`
- `test_ckpt_guard_rejects_each_mismatch`
- `test_fake_vector_is_deterministic_and_normalized`
- `test_resume_is_row_identical_to_one_shot`
- `test_resume_with_limit_below_total_writes_exactly_target` — ★ **`limit < 非空总数` + 续跑**时必须只补缺口（`LIMIT max(0, target - done)`）。
- `test_checkpoint_never_drifts_from_data` — `ckpt.done` 必须恒等于影子表行数 —— 这是"checkpoint 与数据同事务"的可观测不变量。
- `test_rerun_is_idempotent`
- `test_stop_after_batches_boundary_is_inclusive` — `--stop-after-batches N` 必须**恰好跑 N 批**（边界是 `>=`，不是 `>`）。
- `test_ckpt_records_all_guard_keys`
- `test_instruct_prefix_is_the_official_string` — 官方原串，逐字。
- `test_real_embedder_source_keeps_e4_pooling_and_truncation` — **静态锚点**：真嵌入函数必须仍是 E4 的口径 —— EOS 池化 + MRL 截断 + 重新 L2 归一化。
- `test_shadow_dim_matches_production_schema` — 影子表维度必须 = 生产 `clause_vec` 的维度 ⇒ 换表**不需要改 schema**。
- `test_ckpt_and_data_are_committed_in_the_same_transaction` — **静态锚点**：提交块里 `_write_ckpt(...)` 必须**先于**唯一的 `conn.commit()`。
- `test_module_has_no_write_path_to_source` — 只读承诺的机械检查：脚本源码里不许出现对 `--source` 的写语句。

### `tests/test_fts_latin_prefix.py`（17 个）

- `test_chinese_and_standard_numbers_are_byte_identical_under_both_modes` — 默认口径（开前缀）**不许**动到中文查询与标准号查询。
- `test_chinese_expression_contains_no_prefix_star`
- `test_english_inflection_is_findable_only_with_the_prefix_mode` — 同段只有 `extinguisher`，用 `extinguishers` 搜：。
- `test_english_plural_and_gerund_and_past_are_all_covered` — 三个方向各测一次（复数 / 进行式 / 过去式），别只测一个就下"英文能搜了"的结论。
- `test_the_reverse_direction_also_works` — 文档是**长形**、提问是**词干形**时也要能中（前缀查询天生覆盖这一向）。
- `test_acronyms_and_identifiers_are_not_expanded` — 全大写缩写、哈希、配置键都不许被改写（`porter` 在这些东西上是**破坏性**的，。
- `test_short_function_words_are_not_expanded` — `the`/`and`/`to` 这类虚词做前缀查询只会灌候选池，判据里明确放过它们。
- `test_short_stems_are_not_expanded` — **词干太短**的不扩写（词面够长也不行）。
- `test_internal_capitals_are_not_expanded` — **有内部大写**的标识符/缩写不扩写（`camelCase`/`backgroundColor`/`MAYBECAPS`）。
- `test_sentence_initial_capital_is_still_expanded` — 句首大写的普通词**要**放行（否则英文提问一半都白搭）。
- `test_known_false_hit_proper_noun_is_pinned` — **钉住一个已知的误命中，并用一条 xfail 留出"规则变好"的出口。
- `test_known_false_hit_actually_happens_end_to_end` — **钉害处**，不只钉表达式形状（复核 2026-09-25 建议）。
- `test_mixed_query_keeps_chinese_intact_and_expands_only_the_english_word`
- `test_expression_is_always_valid_fts5_syntax` — 口径错的典型症状是**静默无命中**（报错被兜底 except 吞掉），。
- `test_prefix_star_only_ever_follows_a_quoted_token` — `"abc"*` 是合法前缀查询。
- `test_stem_helper_is_usable_from_many_threads` — **判据（不是普通用例）**：本函数由 FastAPI 的**同步路由**调用，那些路由跑在。
- `test_stem_helper_itself_is_thread_safe` — 直接压那条取词干的路径（不经过 jieba），把它单独钉住。

### `tests/test_law_verify.py`（17 个）

- `test_effective_mapping_payload_contract`
- `test_status_mapping_strict`
- `test_sxx_string_form_normalized` — 官方偶发字符串形态（"3"）也应归一映射，不误判为未知。
- `test_graded_ttl_by_status`
- `test_unmarked_uses_12h_ttl` — 详情非空但官方未标注时效 → unmarked，不从可访问性推断。
- `test_not_found_negative_cache_60s` — 详情 data 为空 → 查无。
- `test_minimal_mock_without_raw_treated_as_not_found` — 无 raw 属性且无 sxx 的最小对象 → 无可判定信息，按查无处理（不猜）。
- `test_exception_degrades_to_unverified_never_cached`
- `test_timeout_degrades_within_budget` — 上游卡死 > 单请求超时 → 截断降级 unverified（总耗时受预算约束）。
- `test_unknown_sxx_warns_and_does_not_guess` — 未知 sxx → unverified + WARN 告警，不猜测、不缓存。
- `test_bool_sxx_is_not_mapped` — bool 是 int 子类：True/False 不得误判成 1/0 映射。
- `test_empty_bbbs_no_network`
- `test_cache_hit_second_call_skips_network`
- `test_ttl_expiry_refetches`
- `test_disk_persistence_warm_restart` — 落盘写穿 + 进程重启模拟（清内存）：温启动后仍命中缓存、不打接口。
- `test_corrupt_cache_file_is_cold_start`
- `test_singleflight_merges_concurrent_calls` — 同 bbbs 并发 N 路 → 上游只被打一次，全部拿到同一结论。

### `tests/test_phase6.py`（17 个）

- `test_version_chain`
- `test_compare_docs_with_modality_change`
- `test_compare_added_removed`
- `test_compare_removed_lists_only_truly_absent` — 反向对照：新版→旧版时只列出「新版有而旧版无」的条款。
- `test_compare_paired_and_removed_are_disjoint` — 不变量：任何被 paired 的条款号都不得出现在 removed 里。
- `test_cross_doc_compare_same_key` — R16 跨标准：相同 clause_key 的条款可对照（不同标准号）。
- `test_operation_log_after_ingest` — R8：真实入库路径应写 operation_log（走 law_text 直灌）。
- `test_operation_log_api` — R8/R11：时间线 API 聚合 operation_log + event_log。
- `test_alias_extract_and_expand`
- `test_alias_two_line_format` — GB 风格：术语行 + 下一行定义（无冒号）。
- `test_alias_three_line_format` — MinerU 三行式：编号行 / 术语行 / 定义行。
- `test_alias_endpoint`
- `test_alias_does_not_extract_foreword_or_toc` — **前言/目录不许被当成术语抽走**（2026-10-10 实测缺陷的回归判据）。
- `test_alias_section_span_requires_a_real_boundary` — 区间定位的**边界语义**：`3.1 动火作业：…` 是术语条目，**不是**章节边界。
- `test_alias_no_span_means_no_extraction` — **区间定位不到 ⇒ 一条都不抽**（2026-10-10 实测缺陷的回归判据）。
- `test_alias_does_not_sliding_window_long_definitions` — **散文式长定义不许被滑窗切成碎片**（2026-10-10 实测缺陷的回归判据）。
- `test_alias_expand_ignores_dirty_aliases` — `expand_with_alias` 不许把**脏别名**并进查询（现有防御的判据）。

### `tests/test_query_rewrite_ruler.py`（17 个）

- `test_d1_without_terms_equals_baseline` — ★ 没扩到词 ⇒ D1 与 A0 **逐字相同**（空扩展不是一次改写）。
- `test_prefix_arms_are_exact` — B1/C1 的前缀必须与常量逐字一致（否则测的不是那一条前缀）。
- `test_prf_df_is_document_frequency_not_term_frequency` — ★ df 是文档频率：同一篇里重复 5 次只算 1 次 ⇒ 达不到 min_df=3。
- `test_prf_excludes_query_terms_and_non_cjk_and_short` — 提问里已有的词、非中文串、单字都不许被扩进来。
- `test_prf_ordering_is_deterministic_by_df_then_length_then_lex` — 排序：df 降序 → 词长降序 → 字典序（确定性，重跑逐字节相同）。
- `test_prf_respects_top_m`
- `test_rank_of_counts_strictly_better_only` — ★ 名次 = 严格更优的条数 + 1。
- `test_top_k_indices_is_descending_and_bounded`
- `test_hit_rate_counts_none_as_miss` — ★ 未召回（None）算不中，不许从分母里摘掉。
- `test_hit_rate_threshold_is_inclusive_at_boundary` — ★ 边界：名次**恰等于**阈值算命中（`r <= thr`，不是 `<`）。
- `test_median_rank_ignores_none_and_is_deterministic`
- `test_mcnemar_exact_matches_known_values` — ★ McNemar 双侧精确二项：b=2,c=0 ⇒ 0.5。
- `test_flip_counts`
- `test_flip_counts_direction_is_b_then_c_on_asymmetric_sample` — ★ 方向：返回 `(翻进 b, 翻出 c)` —— b = base=False→arm=True，c = base=True→arm=False。
- `test_frozen_constants_are_pinned` — 口径常量被钉住（改了要显式改测试，不许静默漂移）。
- `test_stoploss_registered_with_expected_endpoint_and_thresholds` — 契约锚：预注册止损线在盘上，且主终点/阈值与代码口径一致。
- `test_still_uses_production_embedder_and_model` — ★ 契约锚：本尺子用的必须是**生产**的向量入口与**生产**的模型名。

### `tests/test_research_draft.py`（17 个）

**TestGuards**

- `test_只装配一次` — **同源不变量的门禁**（§10.98，复核 b25 的 LOW-3）：起草全流程只能装配**一次**。
- `test_材料装配失败时报可操作错误码` — §10.98（复核 b25 的 MEDIUM-1）：依据集取不到 ⇒ 500 `materials_load_failed`。
- `test_项目不存在仍然按_ValueError_放行` — ⚠ 翻错误码**只翻"意外的失败"**：项目不存在那类 `ValueError` 必须照原样放行。
- `test_没有可承重材料时一次_LLM_都不调` — 只有 T3 单一来源（仅线索）⇒ 可承重集合为空 ⇒ **不许**调模型。
- `test_项目不存在时_ValueError`
- `test_LLM_不可用时报可操作的错误`
- `test_空输出不是成功`
**TestHappyPath**

- `test_草稿带未批准标记且引用校验与报告同源`
- `test_提示词里材料另起一节且编号与校验同一套` — **同源不变量**：提示词里的 `[[m:i]]` 编号必须与校验用的 assembled 是同一个。
**TestCitationWarnings**

- `test_不存在的编号_草稿原样保留且两层都报警`
- `test_引用仅线索的材料会被列出来` — 可作依据的 T1 在前面、仅线索的 T3 在后面 ⇒ 引用后者必须被点名。
- `test_不喂法条时不该冒噪声警告_但出现法条编号要明说` — §10.98（复核 b25 的 LOW-2）：**噪声警告换成准确的那一条**。
**TestEndpoint**

- `test_缺少_query_是_422`
- `test_缺少_project_id_是_422`
- `test_项目不存在_404`
- `test_正常路径_200_且带未批准标记`
- `test_LLM_不可用_500_llm_unavailable`

### `tests/test_understanding.py`（17 个）

- `test_intent_classification`
- `test_slot_extraction_and_declared`
- `test_v1_slot_table_removed` — Task 13.1 死代码清除：v1 槽位表函数已删除（追问 v2 由 LLM 自判）。
- `test_clarify_event_when_missing` — R9 v2：不再用规则槽位表预先追问——统一先检索，由 LLM 单次自判（问还是答）。
- `test_no_clarify_when_slots_full` — R9 免追问：带前置声明 [甲类/高层] → 直接出答案。
- `test_condition_filter_and_rank`
- `test_rank_with_hierarchy_gbt_is_a_national_standard` — **`GB/T` 必须与国家标准的位阶相符**（2026-09-17 实测补漏，§10.51）。
- `test_standard_type_is_a_real_sort_term_not_a_dead_one` — `standard_type` 那一项**曾经是死项**（2026-09-17 独立复核 b7 的 MEDIUM-4）。
- `test_fetch_full_clause_fills_standard_type` — `fetch_full_clause` 必须把 `doc_meta.standard_type` 带出来（否则排序项又成死项）。
- `test_sufficiency_note`
- `test_special_work_theme_no_clarify` — R9 追问合理性：高处作业分级是规则查询，不追问建筑参数，直接检索。
- `test_theme_missing_slots`
- `test_theme_scoped_slots` — 通用主题作用域：特殊作业不提取建筑高度槽位（不做死标签）。
- `test_grade_question_is_rule_query`
- `test_refine_search_query`
- `test_title_clause_expansion` — 命中标题条款（8.1 作业分级）应附带子条款（8.1.1 分级内容）。
- `test_correction_detection`

### `tests/test_update_discover.py`（17 个）

- `test_seed_tree_shape` — 24 大类齐全，每类 3~8 个二级子类，全部节点 source=seed 待扩充。
- `test_classify_broad_safety_asks_questions` — 「我要下载安全的国标」→ 一轮追问 ≤3 问，绝不硬选大类。
- `test_classify_fire_hits_unique_path` — 「消防」→ 唯一命中路径 C/C80 消防。
- `test_classify_leaf_shadows_branch_keyword` — 「消防安全」由 leaf 词遮蔽 branch 词，直接命中不追问。
- `test_classify_multi_hit_and_miss_both_ask` — 多 leaf 命中与完全未识别都走一轮追问，绝不猜测续跑。
- `test_classify_labor_protection_hits_c60` — 「劳保穿戴/劳动保护用品」→ 唯一命中 C/C60 劳动安全（2026-08-26 实测修复：。
- `test_classify_cleans_colloquial_noise` — 口语虚词清洗只作用于关键词匹配，不破坏既有语义。
- `test_llm_classify_hit_when_rules_miss` — 规则 miss 时 LLM 兜底：返回合法路径即采用（开放说法不再依赖词表穷举）。
- `test_validate_ccs_code_rejects_bad_codes` — LLM 输出的 code 必须 ∈ 种子树二级子类。
- `test_parse_llm_json_tolerates_noise` — LLM 输出容错：代码块围栏/前后缀不影响 JSON 提取。
- `test_llm_classify_caches_repeat` — 同描述重复分类只调一次 LLM（LRU 缓存，重复问零成本）。
- `test_search_rejects_drill_level_over_limit` — drill_level=4 拒绝：UpdateError 且错误码 UPD-3002（校验层）。
- `test_search_mock_three_cards_fields_complete` — mock 三条结果：卡片字段完整且与 fixture expect 逐位一致。
- `test_search_dedupes_and_skips_unparseable_rows` — 同号重复行去重保序。
- `test_search_http_miss_returns_empty_not_raise` — HTTP 非 200 不抛错返回 []（与 channels._miss 同语义）。
- `test_search_transport_failure_normalized_to_upd1xxx` — 传输层异常归一：超时→UPD-1001，其余→UPD-1004。
- `test_download_later_add_idempotent_then_remove` — 加两次只一条（幂等）。

### `tests/test_effect_report.py`（16 个）

- `test_eff_01_colors_and_flip` — 五色映射 + resolve_status 双向翻转口径（复用不复制）。
- `test_eff_01b_reference_is_its_own_filterable_category` — 🔵 仅参考**能单独筛出来**（业主要的就是"在有效性里作为单独的一个类别"），。
- `test_eff_02_flip_doc_lands_in_green_bucket` — 实施日已到的 upcoming → 报告行 status=effective（惰性翻转复用）。
- `test_eff_03_tree_shape_two_tops_no_mixed` — 两棵树不混排：std（CCS 大类→区间→类目）与 law（效力等级→部门/领域）。
- `test_eff_04_windows` — 窗口四档：upcoming90（2099 不入）/recent90（含今天边界）/retired90 只认。
- `test_eff_05_color_filter` — color 子集过滤：只看红色清单。
- `test_eff_06_docs_endpoint_validation` — top/l2 必填 422 语义。
- `test_eff_07_docs_limit_offset` — limit/offset 分页。
- `test_eff_08_export_xlsx_reopenable` — xlsx 落 exports、openpyxl 重开：sheet 名/总览数字/明细行数与层级列。
- `test_eff_09_export_empty_db` — 空库：出文件、汇总全 0、明细仅表头（镜像"空批次同样出报告"）。
- `test_eff_10_no_hidden_docs` — catalog_hidden=1 在聚合/明细/导出三处全部缺席。
- `test_eff_11_by_color_topn` — 全库按色取 top-N：只含该色、色内按标准号、limit 截断、count 为过滤后总数。
- `test_eff_12_by_color_per_color_multi` — verifier F4：多色一次聚合（per_color=True）每色各取 n 条。
**TestExportEndpointBody**

- `test_no_body_still_exports` — 完全没有 body（host 侧老调用点就是这么发的）⇒ 照常出文件。
- `test_explicit_window_body`
- `test_malformed_json_is_422_not_silently_empty` — 非法 JSON：**422**（不是"当成空 body 照常出文件"）——这是 §10.71 的有意收紧。

### `tests/test_formula_fragment_glue.py`（16 个）

**TestDotSplit**

- `test_digit_dot_digit_glued`
- `test_decimal_untouched`
- `test_dot_with_one_side_space`
**TestAttachedDigitPair**

- `test_after_open_paren`
- `test_after_cjk`
- `test_after_cjk_with_unit`
- `test_multi_char_tokens_not_merged`
**TestAlnumTail**

- `test_upper_pair_after_digit_glued`
- `test_single_upper_letter_after_digit_kept`
- `test_mixed_run_glued`
**TestTwoLetterUnitInch**

- `test_inch_glued`
**TestReverseControls**

- `test_variable_product_kept`
- `test_legit_value_unit_space_kept`
- `test_thousands_separator_kept`
- `test_plain_text_untouched`
- `test_idempotent`

### `tests/test_golden_criterion.py`（16 个）

- `test_same_clause_number_in_another_standard_is_not_a_hit` — **核心用例**：同一条款号、不同标准 ⇒ 必须判不中。
- `test_matching_pair_is_a_hit`
- `test_any_expected_answer_counts` — 金标一条题可以有多个可接受答案，命中任一即可。
- `test_empty_expect_is_never_a_hit`
- `test_order_of_returned_pairs_does_not_matter`
- `test_standard_key_normalisation_equates_case_and_dashes`
- `test_key_matches_standard_no_with_trailing_chinese` — 真库 4 篇 `standard_no` 尾部带中文 ⇒ 判据必须允许"键是前缀部分"。
- `test_key_does_not_match_a_longer_number_that_merely_ends_with_it` — **核心反例**：裸「包含」过头——`2033-2008` 是 `GBT12033-2008` 的子串。
- `test_empty_key_never_matches`
- `test_row_filter_helper_is_boundary_based_not_bare_containment` — **打在行筛函数上**（第四轮复核的"残余 1"）。
- `test_known_standard_keys_drops_what_the_library_does_not_have` — **库里没有的标准号不许筛**（否则会把权重最高的通道 A 整条清空）。
- `test_unknown_standard_in_query_behaves_exactly_like_no_standard` — **打在调用点上**：删掉引擎里那道守卫，本用例会红。
- `test_row_filter_actually_scopes_to_the_named_standard` — **行筛**本身也要有覆盖（第三轮复核的变异 C 盲区）。
- `test_regex_finds_real_standard_numbers`
- `test_regex_does_not_treat_clause_numbers_or_years_or_doc_numbers_as_standards` — 条款号 / 年份 / 文号 / 表号 / 日期区间都不许被当成标准号。
- `test_regex_alone_is_not_the_defence_for_lookalike_tokens` — **诚实登记**：`FY2021-2022` 这种"字母+4位数字+连字符+4位数字"**形态上确实像**标准号，。

### `tests/test_latex_spacing.py`（16 个）

**TestDigitRuns**

- `test_three_single_digits_merged`
- `test_two_digit_run_merged_with_unit_anchor`
- `test_plain_number_run`
- `test_two_tokens_protected`
**TestLetterRuns**

- `test_three_letter_run_merged`
- `test_kpa_merged`
- `test_variable_product_protected`
- `test_two_letter_unit_not_merged`
**TestAttachments**

- `test_superscript_attaches`
- `test_micro_prefix_attaches`
- `test_subscript_chain_attaches`
- `test_percent_escape`
**TestNoRegression**

- `test_symbol_mapping_intact`
- `test_frac_still_semantic`
- `test_real_10401_formula`
- `test_idempotent`

### `tests/test_store_standard_no.py`（16 个）

**Test存储形**

- `test_全角折半角_其余一字不动`
- `test_不动空格大小写与年份`
- `test_空值不炸`
- `test_不改变是不是同一部标准` — 1:1 换形状的**全部意义**：`norm_no` 前后必须相等（否则就动了语义）。
- `test_与比较键的分工没被搞混` — `canon_standard_no`/`standard_no_key` 是**比较键**（去空格去斜杠），存储形**不**那样做。
**Test写入收口**

- `test_insert_document折不折三个列`
- `test_名称里的全角连字符不许折` — ⚠ 复核 b33 的最高风险：**名称里的全角 `－` 是文字，不是形状**。
- `test_普通号一字不动`
- `test_不改调用方的dict` — 调用方常复用同一个 dict（pipeline 里就复用）——被就地改掉会很难查。
- `test_折完撞车会报IntegrityError而不是静默写第二行` — ⚠ **行为变化**（有意）：以前全角/半角是两个不同的串，所以"同一标准两份文件"能并存。
- `test_裸INSERT入口_bulk_也折` — `bulk.py` 用自己的 INSERT（不过收口）——源码级检查它确实调了对应折法。
- `test_UPDATE入口_auto_tag_也折`
- `test_查重侧也要折_全角号能查到半角行` — §11.0 R6c-3d（复核 b33 的次高风险）：**写入折了、查重不折** ⇒ 全角重复件会绕过护栏、。
- `test_入口清单与实现一致` — 入口清单要"能逐条核"（b32 就是靠逐条点名找到漏口的），且清单本身要**承认不完备**。
**TestOCR循环脚本**

- `test_GBZ_T_不再退化成裸前缀`
- `test_普通号与GB分支不变`

### `tests/test_figure_legend.py`（15 个）

**TestLegendDetect**

- `test_header_standard`
- `test_header_garbled_ocr`
- `test_single_line_multi_items`
- `test_two_item_lines`
- `test_normal_clause_not_legend`
- `test_mention_without_items_not_legend`
- `test_empty`
**TestLegendGeometry**

- `test_adjacent_below_top_origin`
- `test_adjacent_above_image_accepted`
- `test_far_block_rejected`
- `test_x_far_rejected`
- `test_missing_bbox`
**TestIntegration**

- `test_legend_attached_to_figure_not_clause`
- `test_far_legend_stays_text`
- `test_clause_text_kept`

### `tests/test_law_catalog_refresh.py`（15 个）

- `test_refresh_days_default_is_one` — 未设 ⇒ 缺省 1 天。
- `test_refresh_days_values`
- `test_due_when_never_refreshed` — 从没刷过 ⇒ 视为到期，触发刷新并写 last_refresh_at。
- `test_skips_when_not_due` — 刚刷过（1 天内）⇒ 跳过，且**不碰网络**。
- `test_due_again_after_period` — 超过周期 ⇒ 再次触发。
- `test_disabled_when_zero` — 周期 ≤0 ⇒ 关闭，不触发。
- `test_naive_last_refresh_treated_as_utc` — 历史值无时区 ⇒ 按 UTC 解释，不得抛 TypeError。
- `test_failure_does_not_stamp_last_refresh` — ★ 刷新失败 MUST NOT 写 last_refresh_at —— 否则一整个周期不再重试。
- `test_start_is_idempotent_and_stop_cleans` — start 两次只起一个线程。
- `test_loop_survives_exception` — 循环体抛异常不得终止线程（后台线程必须存活）。
- `test_restart_after_stop_runs_again` — stop 后能再 start，且新线程**真的在跑**（每次新 Event，旧线程不得复活）。
- `test_stop_timeout_does_not_lie_or_double_start` — ★ join 超时后：`is_running()` 不得假阴，`start` 不得再起第二个线程。
- `test_stop_returns_true_when_clean` — 正常退出 ⇒ stop 返回 True（与超时分支可区分）。
- `test_run_starts_and_stops_law_refresh` — ★ 生产启动点 `server.run()` 必须真的**调用** start / stop 刷新线程。
- `test_refresh_module_is_not_the_dead_scheduler` — ★ 反向断言：刷新线程**不依赖**那个死调度器（它的 start() 无人调用）。

### `tests/test_middle_locator.py`（15 个）

**TestPatterns**

- `test_pattern_order_legacy_first`
- `test_layout_in_patterns`
**TestFind**

- `test_finds_legacy_middle`
- `test_finds_layout_cloud_rename`
- `test_finds_bare_middle`
- `test_all_three_coexist_deduped`
- `test_legacy_first_when_both`
- `test_empty_or_missing_root`
- `test_sorted_within_pattern`
- `test_iter_yields_same_as_find`
- `test_nested_depth`
- `test_non_json_ignored`
- `test_finds_mineru40_middle_json` — 4.0 的产物名 `middle_json.json` 必须被识别。
- `test_finds_stemmed_middle_json`
- `test_legacy_preferred_over_40_when_both`

### `tests/test_retrieval.py`（15 个）

- `test_exact_channel_hit`
- `test_exact_superseded_excluded`
- `test_null_legal_status_is_not_silently_excluded` — **NULL（未核验）≠ 已废止**：它也要能被精确命中抓到。
- `test_unverified_clause_does_not_outrank_an_effective_one` — **未核验不许在通道内占优**（复核 b9 的 LOW-3，2026-09-18 修）。
- `test_modality_channel_ranks_verified_before_unverified` — 模态通道（D）的**通道内名次**必须是确定的，且未核验不占优（复核 b9 的 INFO-6）。
- `test_legal_element_channel_order_is_deterministic` — 法理要素通道（E）**同族缺陷、自查发现**：它原先也没有 ORDER BY。
- `test_legal_element_channel_ranks_verified_before_unverified` — 法理要素通道（E）也要"未核验沉底 + 确定"（§10.65 补齐。
- `test_fts_channel`
- `test_modality_channel`
- `test_legal_element_channel`
- `test_behavior_scope_channel`
- `test_vec_channel`
- `test_rrf_exact_beats_fts`
- `test_query_modality_extraction`
- `test_search_with_details`

### `tests/test_threadpool_bound.py`（15 个）

- `test_收窄函数真的把线程池设成常量`
- `test_线程池收窄是按事件循环的` — §10.88（独立复核 b17 的 MEDIUM-1）：**第二个事件循环**也必须被收窄到 16。
- `test_常量不会比默认值更大`
- `test_每个请求都会尝试收窄` — 挡"有人把中间件里那一行删了"：拿替身记录它被调用过。
**TestHeavyGate**

- `test_重活路径表覆盖了那些被量出秒级的端点`
- `test_laws_里两条廉价端点不被关进闸门` — §10.93：`/laws/*` **只逐条列重活**，不用前缀——否则会顺手把两条廉价端点也关起来。
- `test_asyncio_to_thread_绕过_anyio_闸门` — **§10.93 的立论**：`asyncio.to_thread` 不受 anyio 那道 16 令牌的约束（所以禁用）。
- `test_轻活路径不占重活闸门`
- `test_重活路径会_acquire_并_release`
- `test_廉价的前缀例外不被关在闸门里` — `/ingest/preview/inbox` 只是列目录 ⇒ 必须在 `HEAVY_SKIP` 里（**闸门自己不许造排队**）。
- `test_重活闸门真的把并发卡在_HEAVY_TOKENS` — **行为级**：真发 `HEAVY_TOKENS * 3` 条并发重活请求，并发峰值必须**恰好**是 `HEAVY_TOKENS`。
- `test_流式响应的令牌要等响应体发完才放` — **为什么闸门必须是纯 ASGI**（b14 的 MEDIUM-1）。
- `test_异常或截断路径也必须释放且只放一次` — `app` 中途抛错（或从不发最后一块）⇒ `finally` 兜底释放，**且只放一次**。
- `test_闸门缓存不会把死循环留在字典里` — LOW-4：缓存键必须是**循环对象**（弱引用字典），不是 `id(loop)`。
- `test_非重活路径在中间件这一层就不碰闸门` — 轻活路径连 `acquire` 都不该调（不是"调了又立刻放"——那也会排队）。

### `tests/test_toc_ingest.py`（15 个）

- `test_toc_entry_predicate_positives` — 目录条目四种实测形态全命中（含并块）。
- `test_toc_entry_predicate_reverse_controls` — **反向对照**：不带点线页码尾的正文/章头/表格数值行一律不认。
- `test_toc_entry_regex_requires_page_tail`
- `test_toc_page_not_ingested_as_clauses` — **缺陷现场重放**：目录页整页不得产出任何条款。
- `test_toc_single_entry_blocks_not_ingested` — 逐行成块的目录条目（GB/T 28853-2012 形态）不得成为条款。
- `test_toc_no_dots_block_is_toc_entry` — 无点线目录块命中第二签名（实测原文）。
- `test_toc_no_dots_reverse_controls` — **反向对照**：正文多行块不得被第二签名吃掉。
- `test_toc_no_dots_then_dots_block_not_ingested` — **缺陷现场重放**：无点线目录块 + 其后的点线目录块都不得成为条款。
- `test_index_entry_predicate` — 索引条目签名（词条 + 点线 + **小数页码**），且单行不认。
- `test_untitled_index_entries_not_absorbed` — **索引没有标题块**时，条目也不得进正文（`_is_index_entry` 的用途）。
- `test_index_head_predicate` — 只有"整块恰为索引"才算索引起始（含空格变体）。
- `test_index_head_accepts_prefixed_titles` — 前缀白名单：`中文索引`/`英文索引`/`术语索引` 也是索引起始。
- `test_prefixed_index_section_not_absorbed` — 前缀索引标题之后的词条也不得进条款（缺陷现场重放，GB/T 13964-2008 形态）。
- `test_index_section_not_absorbed_into_clause` — **缺陷现场重放**：索引小节不得并入前一条款，正文必须保留。
- `test_index_section_does_not_eat_preceding_clauses` — 反向对照：索引**之前**的条款必须完好（索引态不得提前置位）。

### `tests/test_index_guard.py`（14 个）

**TestLeaderRun**

- `test_zeros_run`
- `test_dots_run`
- `test_short_not_leader`
- `test_number_with_other_digits_not_leader`
- `test_text_not_leader`
- `test_stripped`
**TestOrderingOnBareNumber**

- `test_same_parent_backward_rejected`
- `test_duplicate_rejected`
- `test_cross_parent_backward_accepted`
- `test_body_progression_accepted`
- `test_no_history_accepted`
**TestIntegration**

- `test_index_rows_not_clauses`
- `test_bare_number_with_title_still_clause`
- `test_leader_content_not_lost`

### `tests/test_kb_scope_retrieval.py`（14 个）

- `test_answer_is_findable_only_inside_the_scope` — 范围 = 范围内那篇 ⇒ 命中。
- `test_unrestricted_search_still_sees_both` — 反向哨兵：不给范围（`doc_ids=None`）时**两篇都能查到** —— 证明上一条不是"检索坏了"。
- `test_scope_filter_is_in_retrieval_not_post_filter` — **核心判据**：范围过滤必须发生在**检索层**。
- `test_every_channel_is_restricted` — 六条召回通道**逐条**验证：范围外的那篇在任何一条通道上都进不来。
- `test_vec_channel_is_restricted_without_the_model` — **向量通道**也要被堵住 —— 直接塞假向量，模型离线也能验。
- `test_vec_scope_holds_with_more_than_one_document` — **范围里有 ≥2 篇文档**时，向量通道也必须整体下推（spec 003 · FR-003）。
- `test_empty_scope_returns_nothing_never_the_whole_kb` — `doc_ids=[]` = "范围内一篇都没有" ⇒ **一条都不返回**（绝不退化成全库）。
- `test_answer_scope_is_echoed_and_restricts_retrieval` — `ks_answer.answer(kb_folder_ids=[甲])`：检索被限定（范围外那篇的证据进不来）+ 范围如实回显。
- `test_answer_still_answers_when_out_of_scope_hits_saturate_topk` — **"在取回后筛"必红的那一条**（`top_k` 被范围外命中吃光的情形）。
- `test_answer_rejects_unknown_folder_instead_of_falling_back` — 目录不存在 ⇒ **报错**（`KbScopeNotFound`），绝不静默当成"没给范围"全库检索。
- `test_answer_with_empty_doc_scope_does_not_search` — 空范围（目录存在但里面一篇没有）⇒ **不检索**、如实说"范围内没有"，且**不调 LLM 拿全库编答案**。
- `test_bookmark_folder_and_kb_scope_are_two_different_things` — 两种"夹"不混：`folder_id`（收藏夹）**不动检索**（只后置过滤证据），`kb_folder_ids` 才限定检索。
- `test_api_returns_404_for_unknown_kb_folder` — 端点级：`POST /api/v1/ks/answer` 带不存在的目录 ⇒ **404**（不是 200 + 空答案）。
- `test_two_endpoints_agree_on_too_many_folders` — **同一条件两个端点必须给同一个状态码**（复核 LOW-3 打回）。

### `tests/test_law_source.py`（14 个）

- `test_whitelist_accepts_official_hosts`
- `test_whitelist_rejects_third_party`
- `test_magic_checks`
- `test_flk_search_payload`
- `test_govcn_parse_rows`
- `test_govcn_fetch_detail_extracts_official_download`
- `test_convert_probe_never_raises`
- `test_find_libreoffice_honours_KS_SOFFICE` — `$KS_SOFFICE` 显式覆盖（2026-10-18 加）—— 便携场景要能指定**包内**的 LibreOffice。
- `test_pdf_completeness_detects_truncation` — LibreOffice 截断检测：docx 文本量远大于 PDF → 判截断（False）。
- `test_flk_level_map`
- `test_law_source_dir_sanitizes`
- `test_build_docx_from_html`
- `test_find_by_source_roundtrip`
- `test_check_law_updates_status_change`

### `tests/test_layout_fidelity.py`（14 个）

- `test_load_middle_items_line_boxes_aligned` — B5 底座：MidItem.line_boxes 与 text 行序列一一对齐（行界=line）。
- `test_split_rows_page_attribution` — B3 采集：SplitClause.rows 逐行携带 0-based 页号（跨页拼接行页号正确）。
- `test_build_page_breaks_run_start` — B3 页界编码：run-start [[行号, PDF页], ...]，行号 = content_text 0-based。
- `test_build_row_pipeline_furniture_strip` — 家具剥离在 rows 上做：整行标准号丢弃后行号收缩，页界编码仍与。
- `test_build_line_spans_full_no_cap` — B5：行级 span 全量入库（退役 [:8] 封顶），bbox=折行行框、sort_order。
- `test_build_spans_fallback_when_line_boxes_missing` — 行框整体缺失（旧 middle.json 无 line.bbox）→ 回退块级 span（宁粗不高灭），。
- `test_build_truncation_rowwise` — [:4000] 截断在 rows 上做：整行入账、末行可截半，截断后行号/页界不漂移。
- `test_build_uncaptioned_table_identity` — B4：无题注表格条款（绑定全失配落单）不被 <4 守卫整表丢弃，。
- `test_storage_roundtrip_page_breaks` — 存储面：insert_clauses 写 page_breaks JSON → fetch_full_clause 读回一致。
- `test_api_page_break_divider` — 渲染面：page_breaks 非空 → 页号切换处插 <div class="page-break"。
- `test_pipeline_image_load_bind_figure_html` — C2：image 块进 MidItem。
- `test_locate_middle_figure_fallback` — C3：/figure 文字层锚定失败 → middle.json image_caption 匹配图号取。
- `test_locate_middle_figure_bare_image_path` — 24276 实测回归：image_path 裸文件名（无 images/ 前缀）、物理文件在。
- `test_strip_keeps_caption_lines_with_table_tokens` — 24276 实测回归：图题行 token（不带通风口/有效散热面积/1,25）与系数表。

### `tests/test_preview_jobs.py`（14 个）

**TestStateMachine**

- `test_create_returns_pending_view_with_total`
- `test_full_run_reaches_done_and_buckets_conserved`
- `test_batch_size_truncates`
- `test_single_file_failure_does_not_break_batch`
**TestAbort**

- `test_abort_on_terminal_is_idempotent_noop`
- `test_abort_running_marks_aborted_keeps_done_rows`
**TestZombie**

- `test_zombie_running_thread_dead_becomes_failed` — 伪造僵尸：直接往任务表塞 status=running + thread_alive=False。
- `test_alive_thread_not_zombie` — thread_alive=False 但 thread_ref 活着（正常切换间隙）→ 不误杀。
**TestRetentionPolicy**

- `test_prune_keeps_recent_jobs`
**TestPagination**

- `test_rows_pagination`
**TestConfidenceIsNeverFaked**

- `test_crashed_item_is_none_not_zero`
- `test_uncomputable_report_keeps_none_and_normal_keeps_number`
**TestEgressContract**

- `test_default_job_is_no_egress`
- `test_explicit_optin_reaches_parser_and_is_recorded`

### `tests/test_catalog_hidden_retrieval.py`（13 个）

**Test可见性片段**

- `test_隐藏文档被排除`
- `test_按条款的片段同口径` — ★ 两处必须**同时**排除同一批文档（结构判据钉住，防只改一处）。
- `test_列不存在时不加条件` — ★ `catalog_hidden` 是**增量列**（不在 `schema.sql`）⇒ 老库上没有它。
- `test_没有隐藏文档时片段仍然生成` — ★ 反向：片段**不依赖"当前有没有隐藏文档"**。
**Test那6篇真标准该挡而不是不该挡**

- `test_隐藏规则是零normal条款而非零条款`
- `test_那6篇真标准只有附录没有正文` — 若**显式点名真库**，直接核那 6 篇的 `normal` 条数为 0。
**Test假样本不进检索**

- `test_假样本不在检索结果里`
**Test守卫真的拼进了各通道SQL**

- `test_三条join通道都带vis_doc`
- `test_fts两条通道都带vis_clause`
- `test_向量通道在Python里筛隐藏文档` — ★ 通道 C（vec0 虚表）**刻意不拼 SQL**，改用 Python 筛 —— 判据钉住这个决定。
**Test隐藏集合本身被算出来**

- `test_隐藏集合在片段生效时被算出来` — 片段非空 ⇒ 必须去查隐藏集合（不许用 `if False` 之类把它关掉）。
- `test_隐藏集合的行为` — 行为判据：真库可达时，隐藏集合必须**恰好等于** `catalog_hidden=1` 的集合。
- `test_片段默认参数与生产别名一致` — ★ 结构判据：片段的默认参数**必须**是 `dm.doc_id`。

### `tests/test_channel_answers.py`（13 个）

**Test覆盖与词表**

- `test_台账每一条都有声明`
- `test_只许出现五类词`
- `test_每条都有出处与置信`
- `test_五类就是设计稿那五个`
**Test口径**

- `test_mock才供数的字段不算能力` — R6c-1 口径①：`discover.py` 卡片契约读 `item["status"]`，但只有 mock 会填。
- `test_工具类一律不参与五类` — 口径②：代码仓库/工具不是采集通路——它们是**规则判空**或**逐条判空**，不是"我们没查"。
- `test_r1_那批是调研期声明_标_medium`
**Test查询**

- `test_channels_for_错误类名要抛`
- `test_能答现行性的渠道包含真实通路`
- `test_未登记的渠道返回空而不抛`
- `test_only_ok_会滤掉探针判死的渠道` — 能力与可用性是两根轴：声明不改，但选渠道时要能滤。
- `test_coverage_小结`
- `test_真库默认路径能读`

### `tests/test_credentials_migrate_script.py`（13 个）

- `test_dry_run_writes_nothing`
- `test_nothing_to_migrate_is_clean_noop`
- `test_clean_system_without_apply_refused`
- `test_force_without_clean_system_refused`
- `test_apply_migrates_into_encrypted_store_and_keeps_system_layer`
- `test_apply_writes_no_plaintext`
- `test_clean_system_deletes_verified_entries`
- `test_clean_system_two_pass_deletes_previously_migrated` — 批2 真实踩到的回归：先 --apply（第一遍搬完），再 --apply --clean-system（第二遍）。
- `test_clean_system_reports_env_only_entries` — 只在进程环境变量里的条目删不掉 —— 必须如实上报，不谎报已清理。
- `test_clean_system_never_deletes_when_store_has_other_value` — verifier P1 的脚本层回归：存储里已有新 Key → 不覆盖，且不删冲突的系统层旧值。
- `test_force_discards_conflicting_system_layer_value`
- `test_import_does_not_run_main`
- `test_script_documents_dsh_restart_and_rollback` — 文档级守卫：这几句不许被删（verifier 指出旧版全仓库都没写"必须重启 DSH"）。

### `tests/test_fused_rewrite_ruler.py`（13 个）

- `test_b1_c1_only_touch_vector_channel` — ★ B1/C1 是**指令前缀**：只改向量通道的嵌入输入，FTS 必须保持原样。
- `test_d1_touches_vector_and_fts` — ★ D1 是**内容扩展**：向量与 FTS 都该用扩展串（精确/模态通道不走这两个钩子）。
- `test_a0_touches_nothing` — ★ A0 = 生产口径：两个通道都用原样提问。
- `test_headline_excludes_multi_def_and_dup` — ★ headline 必须真的剔掉 `gold_multi_def`/`gold_dup_text`（否则与 exp-8/exp-13 不同卷）。
- `test_fused_top20_is_inclusive_at_boundary` — ★ 名次恰等于 20 算命中。
- `test_flip_side_treats_boundary_20_as_hit` — ★ 翻转统计那一侧也必须把**名次恰等于 20** 当命中 ——。
- `test_flip_and_delta_direction_on_asymmetric_sample` — ★ 非对称样本上 `(翻进 b, 翻出 c)` 与 Δ 的**方向**：净改善必须读成正 Δ。
- `test_missing_cell_raises_instead_of_silently_filling` — ★ 缺一格必须抛错，不许静默补 0（补 0 会让 @20 的分母错而读数看不出来）。
- `test_by_subset_top20_partitions_by_label_and_is_inclusive` — ★ 副终点 `by_subset_top20` 必须**按 subset label 分组**、且组内阈值同样闭区间（`r<=20`）。
- `test_fused_hit_n_counts_non_none_ranks` — ★ 副终点 `fused_hit_n`（池内召回条数）必须数"名次非 None"，且与 `@20` 口径可分。
- `test_pool_median_definition_is_pinned` — ★ 上报的 `pool_median` 定义（偶数条取**上中位** `sorted[n//2]`）必须钉住 ——。
- `test_production_hook_points_still_exist` — ★ 三个钩子（只读连接注入 + 两个改写调用点）必须仍在生产代码里。
- `test_stop_loss_preregistered_contract` — ★ 预注册文件必须在，且主终点是 `fused@20`（不是向量路）。

### `tests/test_head_unit_fragment_gate.py`（13 个）

**TestValueFragmentRejected**

- `test_unit_slash_unit`
- `test_unit_with_cjk_punct`
- `test_compound_unit_slash`
- `test_inequality_expression`
- `test_unit_times_cjk`
- `test_unit_space_cjk`
- `test_conc_mmol`
- `test_value_only_line`
**TestReverseControls**

- `test_english_abbrev_title_kept`
- `test_latin_started_title_kept`
- `test_type_label_kept`
- `test_cjk_title_kept`
- `test_tabular_rest_still_rejected`

### `tests/test_run_gates_ratchet_wiring.py`（13 个）

- `test_run_gates_exists`
- `test_pristine_file_wires_ratchet_at_all_eight_sites` — 原样件必须零违规 —— 否则下面的自验没有意义。
- `test_exactly_eight_code_sites_are_found` — 8 个判定点必须都能被**逐处**定位（自验的地基）。
- `test_every_single_site_mutation_is_caught` — **核心判据**：把 8 处**任意一处**改回 `$totalRan` ⇒ 必须报违规。
- `test_all_reads_mutation_is_caught` — 7 个读取点全改回（PSSA 唯一抓得住的那一种）也必须被本检测器报出。
- `test_anchor_names_are_present_in_code_lines` — 三个锚点必须各自出现在**至少一行代码**里（缺一 ⇒ 判据 3 静默失效）。
- `test_anchor_rename_is_caught` — **核心**：把任一锚点全文改名（只改名、语义不变）⇒ 必须报违规。
- `test_anchor_mixing_is_caught` — 注入一行「锚点 + `$totalRan`」混用 ⇒ 必须报出（证明判据 3 不是空转）。
- `test_detector_is_not_always_true` — 反向自验：无关改动（改注释、改无关标识符）必须**零报** —— 防「扫描器恒真」。
- `test_comment_occurrence_is_excluded_from_the_count` — 文档化那第 9 次出现（注释）**不算**判定点 —— 防止有人把注释删掉就以为少了一处。
- `test_base_total_primary_source_exists` — 原样件里 `$baseTotal` 的首选来源**恰有一处**（判据 5 的地基）。
- `test_deleting_base_total_source_is_caught` — **C2 的核心**：删掉 `$baseTotal = [int]$base.pytest_total` 那一行 ⇒ **必须报违规**。
- `test_base_total_source_swap_is_caught` — 把首选来源**换成别的字段**（语义变了但行还在）⇒ 也必须报。

### `tests/test_t06.py`（13 个）

- `test_pass_through`
- `test_modality_weakened_intercepted`
- `test_modality_strengthened_warns_not_blocks`
- `test_number_tampered_intercepted`
- `test_number_pdf_space_artifact_not_flagged` — 2026-09-06 真机回归（GB 30871-2022 §9.1 吊装分级实测）：PDF 宽字距数字。
- `test_mention_only_clause_not_modality_missing` — 2026-09-06 真机回归第二轮（吊装答案引用 §5.1.1 仅作区分）：条款号出现在。
- `test_number_selective_quote_not_flagged` — E2E 真实案例回归：证据同时含 10m/30m/60m，LLM 只引用 10m —— 不是篡改。
- `test_numeric_semantic_equivalence_passes` — 阶段2.1 评审 P1 案例回归：语义等价的数值变体不应误拦。
- `test_numeric_real_tamper_still_blocked` — 防回退：百分比容差方案会放过真篡改，浮点严格相等必须仍拦截。
- `test_fabricated_clause_intercepted`
- `test_legal_exception_missing_intercepted`
- `test_evidence_prompt_minimal`
- `test_sse_verification_event_with_mock_llm` — SSE 全链路：mock 掉 LLM 流（无 Key 场景走占位答案），核验事件带真实结果。

### `tests/test_update_api.py`（13 个）

- `test_update_endpoints_require_token` — 无 token 一律 401（除 health 外全站口径），错误体 unauthorized。
- `test_classify_hit_and_broad_two_modes` — classify 正常态（唯一 leaf 命中给路径）/ 过泛态（一轮追问 ≤3 问）。
- `test_search_drill_level_over_limit_error_code` — drill_level=4 → 422 / UPD-3002（校验层冻结码。
- `test_pause_resume_and_get_missing_batch_404` — 批次不存在：GET 进度 / pause / resume 均 404 + UPD-2003。
- `test_watchlist_add_list_remove_idempotent_chain` — F-18 幂等链：add → list → 重复 add 不翻倍 → remove → 空 → 再 remove 无操作。
- `test_report_missing_batch_business_error` — report 对不存在批次 → 404 业务错误码 UPD-2003（不产出文件）。
- `test_manual_illegal_status_422_module_frozen_code` — manual 非法 legal_status → 422。
- `test_ack_missing_change_404` — ack 对不存在变更事件 → 404 / UPD-2002。
- `test_batches_and_changes_listing_shape` — 历史批次与变更明细列表端点：包裹格式正确、返回 list（空库亦然）。
- `test_subscriptions_get_default_all_enabled` — 订阅 GET：缺省全开（vocab 全量 enabled=True）。
- `test_subscriptions_put_save_and_get_consistent` — 订阅 PUT：全量替换保存后 GET 一致。
- `test_subscriptions_illegal_tag_422` — 订阅 PUT：非法 tag → 422/UPD-3001，且不落库（GET 仍为全开或上次状态）。
- `test_doc_full_clauses_returns_rich_text_with_page` — 2026-08-27 全文富文本预览接口：某文档全部条款含 content_html 与 page_start。

### `tests/test_update_routing.py`（13 个）

- `test_route_aq_to_ndls`
- `test_route_engineering_to_ndls`
- `test_route_group_to_ttbz`
- `test_route_hj_to_mee`
- `test_route_local_to_dbba`
- `test_route_other_gb_to_ndls`
- `test_全角号与半角号同链` — §11.0 R6c-3b：`select_chain` 是**第 7 个读原始号的站点**（R6c-2b 统一 6 个查询点漏了它）。
- `test_前缀首选要问路由本身` — R6c-3b：`first_route` 是"前缀首选"的**唯一来源**。
- `test_兜底链第二棒是状态权威而不是政策库` — R6c-3b 的核心断言（量出来的）：`ndls` 在 `govcn` 之前。
- `test_route_industry_to_hbba`
- `test_route_no_feature_falls_back`
- `test_route_foreign_prefix_no_match`
- `test_降级链只有一个所有者` — §11.0 R6：兜底链**只有一份**，且 inspector 拿到的就是 routing 那个对象。

### `tests/test_latex_frac_tag.py`（12 个）

**TestFrac**

- `test_simple_frac`
- `test_frac_with_subscripts`
- `test_expression_operands_parenthesized`
- `test_nested_frac`
- `test_chained_fracs`
**TestTag**

- `test_tag_number_extracted_with_close_paren`
- `test_empty_tag_removed`
- `test_tag_plain_number`
- `test_no_tag_unchanged`
**TestNoRegression**

- `test_plain_symbol_mapping_still_works`
- `test_subsup_outside_frac`
- `test_real_10401_formula`

### `tests/test_law_catalog.py`（12 个）

- `test_extract_category_leaves_skips_placeholder_and_dedups`
- `test_sxx_label_mapping`
- `test_parse_aggregate_tolerant_shapes`
- `test_refresh_full_crawl_dedup_and_result`
- `test_reconcile_mismatch_records_warning`
- `test_single_category_failure_degrades_to_warning`
- `test_aggregate_fetch_failure_is_silent_and_catalog_usable` — aggregateData 端点已核实不返回 JSON（SPA HTML/405）。
- `test_query_pagination_filters_and_order`
- `test_manifest_incremental_skip_and_sxx_change`
- `test_progress_events_shape`
- `test_并发ensure_catalog_schema在缺列旧表上不抛异常` — §10.87（独立复核 b16 的 INFO-3）：32 线程并发建表/补列，不许抛 `duplicate column name`。
- `test_稳态下ensure_catalog_schema不拿写锁` — §10.87：表/列/索引都齐（**稳态**）时，它必须走**只读快路径**，不碰写锁。

### `tests/test_law_enum_split.py`（12 个）

**TestEnumSplit**

- `test_splits_enum_numbering`
- `test_body_kept`
- `test_subitem_not_split` — 「（一）（二）」是子项，不是条款 —— 必须留在所属条目正文里。
- `test_enum_number_not_matched_mid_line` — 行内出现的「一、」不算条款头（要求行首）。
- `test_law_text_finds_nothing_here`
- `test_article_doc_unaffected_by_enum_splitter`
- `test_halfwidth_paren_form` — 半角 `(一)` 做**顶层编号**：老规范（《保护海底电缆规定》）如此。
- `test_markdown_heading_prefix` — 编号在 markdown 标题里：`## 二、爱卫会的组织`（《爱国卫生运动委员会…规定》如此）。
- `test_fullwidth_paren_still_not_split` — **全角 `（一）` 是子项**，不许被当成条款（否则一条法规会被切碎）。
**TestEndToEnd**

- `test_enum_doc_ingests` — 端到端：这种文件**必须能入库**，而不是回退成"未识别到条文"。
- `test_article_doc_still_uses_article_splitter`
- `test_unparseable_still_errors` — 两种编号都没有 ⇒ 仍须**如实报错**，不许静默当一条。

### `tests/test_law_source_http_antibot.py`（12 个）

- `test_looks_like_antibot_detects_challenge`
- `test_looks_like_antibot_ignores_json` — Content-Type 是 json 就不该被当挑战（即使正文里恰好含那串字）。
- `test_looks_like_antibot_ignores_normal_html` — 非 JSON 声明的响应一律视为被挡（站点有时返回别的 HTML 页，无特征串）。
- `test_looks_like_antibot_empty_body_is_blocked` — 空正文也算没拿到数据 ⇒ 走重试，而不是当场 JSONDecodeError。
- `test_json_or_challenge_raises_antibot`
- `test_json_or_challenge_passes_json`
- `test_fetch_json_retries_through_challenge` — ★ 挑战页之后成功 ⇒ fetch_json 应当**穿过挑战**拿到 JSON（不是直接失败）。
- `test_fetch_json_uses_long_backoff_for_challenge` — ★ 挑战页必须走**秒级**退避（亚秒退避对它无效）——断言 sleep 参数。
- `test_fetch_json_still_raises_on_real_error` — 真 5xx 不该被当挑战处理（保持既有语义：抛 RuntimeError）。
- `test_mixed_failure_still_uses_long_backoff` — ★ 混合失败序列（挑战、挑战、连接错）**必须仍走长退避轮**。
- `test_pure_network_error_does_not_use_antibot_backoff` — ★ 反向：全程都不是挑战（纯连接错）⇒ **不该**拖进分钟级长退避。
- `test_whitelist_rejection_not_retried` — 非白名单域必须**当场拒绝**、不重试（策略拒绝语义透传）。

### `tests/test_mineru_cloud_mode.py`（12 个）

**TestReadNormalization**

- `test_default_is_pipeline`
- `test_case_insensitive`
- `test_illegal_falls_back`
- `test_vm_html_kept`
**TestWriteValidation**

- `test_illegal_raises`
- `test_llm_channel_rejects_mode`
- `test_unknown_channel_rejected`
**TestStatusExposure**

- `test_status_has_mode_and_choices`
**TestRequestBody**

- `test_upload_url_body_carries_vlm`
- `test_upload_url_body_carries_pipeline`
- `test_model_version_helper_reads_settings`
- `test_model_version_helper_sanitizes`

### `tests/test_bookmark_folders.py`（11 个）

- `test_folder_crud`
- `test_folder_delete_keeps_bookmarks` — 删夹 → 收藏回未分类（folder_id NULL），收藏行本身绝不删。
- `test_add_bookmark_with_folder_and_move` — 带夹收藏 + 移动（同夹改选 = 移动语义）+ 未分类。
- `test_folder_scope_union_semantics` — 范围 = 夹内 doc 收藏（整本）∪ 夹内条款收藏（单条）。
- `test_folder_endpoints`
- `test_answer_folder_id_filters_by_union` — folder_id → 证据限定在（doc_ids ∪ clause_keys）内，notes 如实说明。
- `test_answer_folder_id_clause_only_scope` — 条款级收藏 → 只有那一条入范围（同文档其他条款被滤掉）。
- `test_answer_folder_id_missing_folder_degrades_honestly` — 夹不存在（folder_scope → None）→ 过滤不执行，notes 如实说明，不静默全库。
- `test_answer_folder_id_scope_query_failure_degrades_honestly` — folder_scope 抛异常 → 同上如实降级。
- `test_answer_folder_id_empty_folder_returns_empty_honestly` — 空夹 = 合法空范围 → 证据空 + notes 说明已限定（不是查库失败）。
- `test_answer_folder_id_widens_candidate_pool` — 夹范围激活时候选池扩容（同 bookmarks_only 的 BOOKMARKS_MIN_TOP_K）。

### `tests/test_formula_leader.py`（11 个）

**TestNumberedLeader**

- `test_long_u2026_leader_with_broken_number`
- `test_short_u2026_leader`
- `test_ascii_dots_with_number`
- `test_closing_paren_already_present`
**TestBareLeader**

- `test_ascii_dots_run_removed`
- `test_long_u2026_run_removed`
**TestProsePreserved**

- `test_two_char_ellipsis_survives`
- `test_plain_text_unchanged`
- `test_empty`
**TestIdempotent**

- `test_idempotent_numbered`
- `test_idempotent_bare`

### `tests/test_law_history.py`（11 个）

- `test_history_sorted_desc` — 多版本 ⇒ 按 gbrq 降序。
- `test_history_null_gbrq_sinks` — ★ gbrq 实测可为 null ⇒ 必须沉底且不抛错。
- `test_history_highlight_normalised` — 官方字段名是 highLight（驼峰）⇒ 输出归一成 highlight。
- `test_history_empty_when_no_lsyg` — 没有 lsyg ⇒ 空列表（这是"确实没有历次版本"，不是失败）。
- `test_history_tolerates_non_list` — lsyg 不是 list（接口结构变了）⇒ 返空，不炸。
- `test_history_skips_non_dict_items` — 链上混进非 dict 项 ⇒ 跳过该项，其余照常。
- `test_history_raises_on_network_failure` — ★ 网络失败 MUST 抛异常 —— 绝不用 [] 冒充"无版本"（spec FR-007）。
- `test_history_endpoint_missing_bbbs`
- `test_history_endpoint_ok`
- `test_history_endpoint_502_on_failure` — ★ 官方不可达 ⇒ 502，**不是** 200 + 空链（否则前端无法区分）。
- `test_history_endpoint_empty_is_200` — 确实无历次版本 ⇒ 200 + 空链（与 502 明确区分）。

### `tests/test_law_split_quality.py`（11 个）

**TestFrontMatterStripped**

- `test_front_matter_not_in_body`
- `test_first_chapter_heading_kept_as_context` — **首个**章标题要留（那才是上下文该带的东西）。
- `test_later_heading_not_in_first_clause` — 前一条不该带上**后面**章节的标题。
- `test_strip_returns_text_after_marker`
- `test_strip_without_marker_falls_back`
**TestLineStartSplit**

- `test_reference_does_not_split` — **本修正的核心**：句子中间的「第X条」是引用，不是新条款。
- `test_reference_stays_in_body`
- `test_line_start_clause_splits`
- `test_bold_form_still_splits`
**TestEnumStillWorks**

- `test_enum_doc_unaffected` — 修正只动「第X条」这条路，枚举那条路不受影响。
**TestFallbackAlsoStripsFrontMatter**

- `test_fallback_clause_has_no_front_matter`

### `tests/test_legal_status.py`（11 个）

- `test_upcoming_past_date_flips_to_effective` — upcoming + 实施日期在昨天 → 翻成 effective。
- `test_upcoming_today_flips_to_effective` — upcoming + 实施日期就是今天 → 翻成 effective（今天起施行）。
- `test_upcoming_future_date_stays` — upcoming + 实施日期在未来 → 仍 upcoming。
- `test_upcoming_missing_date_stays` — upcoming + 缺实施日期 → 保持 upcoming（不猜）。
- `test_upcoming_malformed_date_stays` — upcoming + 非 YYYY-MM-DD → 保持 upcoming。
- `test_effective_untouched`
- `test_effective_future_date_flips_to_upcoming` — effective + 实施日期在未来 → 即将实施（2026-08-29 反向翻转：入库从封面。
- `test_effective_today_stays_effective` — effective + 实施日期就是今天 → 现行（今天起施行）。
- `test_effective_malformed_date_stays` — effective + 非 YYYY-MM-DD → 保持（不猜）。
- `test_superseded_withdrawn_untouched`
- `test_none_untouched`

### `tests/test_loop2_oracle.py`（11 个）

- `test_ratio_basic`
- `test_parse_page_breaks_roundtrip`
- `test_json_str_key_roundtrip_no_false_missing`
- `test_missing_content_forces_fail`
- `test_scan_na_non_blocking`
- `test_pagmap_aligned_and_misaligned`
- `test_table_text_included_in_preview`
- `test_strip_html_and_orig_noise`
- `test_object_expected_figures_missing`
- `test_object_expected_figures_na_without_middle`
- `test_mode_textlayer_vs_scan`

### `tests/test_patches.py`（11 个）

- `test_patch_overlay_and_immutability`
- `test_patch_fts_resync`
- `test_patch_rollback`
- `test_patch_upsert_overrides`
- `test_patch_validation`
- `test_patch_audit_log`
- `test_patch_api_crud`
- `test_content_markdown_patch_drives_table_md` — 表格修改必须落 content_markdown 补丁 → 卡片/检索读的 table_md 立即生效。
- `test_rich_html_patch_roundtrip` — 富文本补丁（上下标/加粗/表格 → content_markdown）必须被 _content_html 完整返回。
- `test_content_html_joins_ocr_wraps` — _content_html 对旧数据（正文含 OCR 折行）必须先拼折行再转 <p>——否则卡片出现多余回车。
- `test_patch_guard_fail_closed_on_exception` — 防乱检测内部异常时必须 fail-closed：422 拒绝且不落库，绝不 fail-open 放行脏补丁。

### `tests/test_appendix_split.py`（10 个）

- `test_clause_appendix_regex_forms` — 字母章号三种排版形态全命中。
- `test_plausible_appendix_head_gates` — 四道护栏：孤立编号/图表题注/引用句/表格数值行全拒绝。
- `test_table_caption_accepts_letter_dot` — _TABLE_CAPTION 扩字母点号：表A.1 / 表A. 1 此前 False（45 处失效）。
- `test_hierarchy_path_supports_letters` — 层级路径支持字母首段：A.5.2 → 'A > A.5'（此前恒空串）。
- `test_split_appendix_sub_clauses` — 附录内 A.1/A.2/A.3/A.4 切成独立子条款。
- `test_split_appendix_multiline_block` — 附录内多行块：行首 A.N 同样切分（行级分支）。
- `test_appendix_split_does_not_touch_normal` — 附录细分的两处分支只在 in_appendix 生效：正文数字条款口径零变化。
- `test_lone_number_block_lookahead` — 编号独行块前瞻（GB/T 1032-2023 重导实测）：MinerU 把术语条目拆成。
- `test_exact_channel_prefers_letter_clause_no` — _CLAUSE_NO_APPENDIX_RE：E.5.2 不再被截成 5.2（错标准条款）。
- `test_expand_title_clauses_gate_accepts_letters` — _expand_title_clauses 门控正则接纳 E.1（两处同步放宽）。

### `tests/test_bulk_import.py`（10 个）

- `test_fast_scan_creates_skeleton_rows` — 验收1：快扫 → 骨架行（quality_grade=C、pending_parse 标记）+ 批次清单。
- `test_fast_scan_dedup_and_quarantine` — 验收1：重复文件防重跳过。
- `test_running_batch_rejected` — pending/running/paused 期间拒绝再建（409/UPD-2001 语义，pending 态即拦截）。
- `test_pause_resume_and_budget_pause` — 验收2/3：暂停→恢复续跑。
- `test_strict_dedup_new_source_not_skipped` — 严格防重：换源（同内容换文件名 / 同标准号换内容）一律不静默跳过。
- `test_bad_dir_rejected`
- `test_fast_scan_concurrent_matches_serial` — 增强1：并发快扫（scan_concurrency=4）6 文件 → 6 骨架行、无异常、结果与串行等价。
- `test_extract_name_fallback_full_text` — 增强2：首页无名称时从全文回退（第 2 页 ASCII 名称）。
- `test_fast_scan_no_cap_scans_all_450` — R-A 验收①：450 文件 + batch_size=200 → 一次 fast_scan 扫完全部（无 200 截断）。
- `test_fast_scan_midway_pause_then_resume_finishes` — R-A 验收②：第 250 个文件时外部置 paused → 扫描就近停止且保持 paused。

### `tests/test_change_signal.py`（10 个）

- `test_change_signal_detected`
- `test_no_signal_when_title_does_not_say_it` — 标题没写变化 ⇒ `None`（**宁漏不猜**：标了没写的＝误导人）。
- `test_bare_verb_without_standard_object_is_not_a_signal` — **只有动词、没有“标准/规范/目录/条例”这类对象 ⇒ 不是法规标准的变化**。
- `test_real_signals_survive_the_object_requirement` — 加了“必须有对象词”这道闸之后，**真正的信号一条都不能被误杀**。
- `test_signal_priority_draft_beats_repealed` — 一条标题可能同时命中多个（「修订征求意见稿」含"修订"、"征求"）⇒ 取优先级最高的。
- `test_change_signal_orthogonal_to_legal_status` — **正交**：文件自己现行有效（effective），同时是"某法规被废止"的证据（repealed）。
- `test_change_signal_column_exists_and_is_written` — 落库：`doc_meta.change_signal` 列在，且 `ingest_law_text(change_signal=...)` 会写进去。
- `test_insert_document_writes_optional_columns_it_lists` — **防回潮（窄口径）**：`insert_document` 的 INSERT 清单里列出来的可空列，得真能写进去。
- `test_change_signal_not_written_when_caller_omits` — 不给 `change_signal` ⇒ **不写这列**（既有调用方行为一字不变，`__default__` 哨兵）。
- `test_real_db_backfilled_values_match_rule` — **真库回填后逐条复算**（只读。

### `tests/test_embedder_health.py`（10 个）

**TestHealthIsCheap**

- `test_从没试过时是_unknown_而不是去加载`
- `test_加载成功过才是_ok`
- `test_最近一次失败是_offline`
**TestFailureCooldown**

- `test_窗口内不重试`
- `test_窗口过去后允许再试一次`
- `test_成功之后清掉上次失败` — 先失败、冷却过去、再成功 ⇒ `_load_error` 必须被清掉，`health()` 变 ok。
- `test_窗口长度是个正数秒的常量`
**TestHealthEndpointsDoNotLoad**

- `test_健康端点不加载向量模型`
- `test_health_的_vector_engine_取值在三态之内`
- `test_健康看板的_vector_同样在三态之内`

### `tests/test_law_source_api.py`（10 个）

- `test_law_sources_lists_whitelist`
- `test_law_search_flk`
- `test_law_search_govcn`
- `test_law_search_rejects_third_party` — 白名单外域被拒（403），不静默放行。
- `test_law_ingest_flk`
- `test_law_ingest_requires_bbbs_or_url`
- `test_law_catalog_query_shape_and_filter` — GET /api/v1/laws/catalog 返回分页形状。
- `test_law_catalog_refresh_mocked` — POST /api/v1/laws/catalog/refresh 透传 refresh_catalog 结果（mock 网络）。
- `test_law_verify_passthrough` — GET /api/v1/laws/verify?bbbs= 透传 verify_law 载荷（mock 网络）。
- `test_law_verify_missing_bbbs`

### `tests/test_mineru_channel.py`（10 个）

- `test_no_cloud_key_goes_local_only` — 未配置云 Key → 纯本地，绝不触云。
- `test_cloud_key_prefers_cloud` — 配置了云 Key → 云优先（本地不被调用）。
- `test_cloud_failure_falls_back_to_local` — 云失败 → 本地兜底。
- `test_cloud_disabled_env_forces_local` — KS_MINERU_CLOUD=0 → 显式禁用云（即使 Key 已配置）。
- `test_cloud_fail_and_local_disabled_returns_none` — KS_MINERU_LOCAL=0 且云失败 → 无更多通道（None），不抛异常。
- `test_deep_disabled_skips_everything` — KS_MINERU_DEEP=0 → 整体跳过（云与本地都不触）。
- `test_local_failure_after_cloud_failure_returns_none` — 云失败 + 本地也失败 → None（不抛出，入库继续走文本层降级）。
- `test_cloud_silent_none_falls_back_to_local` — P0 门禁（verifier F1）：云解析**返回 None**（网络/超时/HTTP 类失败的真实。
- `test_cloud_none_and_local_disabled_returns_none` — 云返回 None + KS_MINERU_LOCAL=0 → 无更多通道（None），不抛异常。
- `test_cloud_and_local_both_disabled_returns_none` — KS_MINERU_CLOUD=0 + KS_MINERU_LOCAL=0 → 两通道皆关（calls 为空、返回 None）。

### `tests/test_resolve_clause_normalization.py`（10 个）

- `test_fullwidth_clause_number_resolves` — 全角条款号必须能解析到半角那条（原实现返回 None）。
- `test_whitespace_and_leading_zero_tolerated`
- `test_exact_form_wins_over_normalized_form` — **这条是修法的护栏**：库里同时有 '06' 与 '6' 时，查 '06' 必须命中 '06'。
- `test_table_reference_with_space_resolves` — 「表 2」中间带空格也要进表格引用 fallback（归一后为「表2」）。
- `test_no_false_positive_for_absent_clause` — 归一不能把不存在的条款号"变"出来。
- `test_standard_number_still_disambiguates` — 同一条款号在不同标准下不得串号（原样优先不应破坏精确匹配）。
- `test_resolve_route_accepts_fullwidth` — 走真端点的同一路径（客户端可能把全角原样送上来）。
- `test_superscript_input_does_not_crash` — R3（**曾在生产端点打 500**）：`str.isdigit()` 对上标/下标等 128 个码点为 True，。
- `test_verbatim_lookup_is_tried_first` — R1：库里若真存在**带空白**的条款号，原样查询必须仍能命中它。
- `test_table_reference_is_consistent_with_and_without_spaces` — R2：`'表2'` 与 `' 表2 '` 必须给出**同一个**结果。

### `tests/test_batch7_security_hardening.py`（9 个）

- `test_crash_mid_write_keeps_previous_state` — 写入中途崩溃（os.replace 之前死掉）→ 主文件保持上一次完整内容。
- `test_crash_after_replace_keeps_new_state` — rename 落地后崩溃 → 新状态完整可见（原子写的另一半保证）。
- `test_no_partial_tmp_left_after_crash` — 崩溃后残留 tmp 必须是'可识别的半成品'（.tmp 前缀），主文件无恙。
- `test_backup_dir_default_is_data_dir_backups`
- `test_backup_dir_env_redirects_outside_data_dir` — KS_BACKUP_DIR 重定向到外部目录（模拟另一块盘）→ 快照落在外部。
- `test_snapshot_lands_in_external_backup_dir` — 端到端：重定向下 create_snapshot 的产物落在外部目录。
- `test_backup_dir_empty_env_falls_back` — 空串/纯空白 → 回落默认（显式覆盖必须是有意义的值）。
- `test_probe_token_records_egress_on_both_paths` — 探测成功/失败都必须留 egress 痕迹（record_egress 被调）。
- `test_probe_token_audit_failure_does_not_block` — 审计自身炸掉 → 探测结果照常返回（审计失败不阻塞业务）。

### `tests/test_channels_write_api.py`（9 个）

**Test人工新增**

- `test_新增成功_默认值正确_并留一条痕迹`
- `test_缺name与非法字段都出声拒绝`
- `test_新增的渠道出现在列表与小结里`
**Test人工复核编辑**

- `test_改描述性字段_留痕带改前改后`
- `test_编辑不许碰健康度_启停要走去自己的端点`
- `test_号段可人工维护_坏形状出声拒绝` — §11.0 R7：**号段是业主可维护的事实**，所以它必须是可写字段。
- `test_探针跑过之后人工改链接不清空健康度` — 人工改的是"描述性字段"，**不许**顺手把实测状态抹掉（`overwrite_health=False`）。
**Test人工启停与删除**

- `test_启停留痕`
- `test_删除留痕带删除前整行快照`

### `tests/test_cover_dates.py`（9 个）

- `test_iso_compact_cover` — GB 封面实测形态：ISO 连排 + 换行分隔。
- `test_cjk_year_month_day` — 行标常见"2025年3月16日发布"排版 → 归一化 2025-03-16。
- `test_spaced_and_slash_variants` — 带空格 / 斜杠分隔 / 全角括注容忍。
- `test_body_mention_not_cover_only_scope` — 正则只认"数字+发布/实施"连排。
- `test_no_false_hit_on_clause_numbers` — 条款号/标准号不误触发（"GB 25596-2025"无发布/实施词）。
- `test_missing_leaves_none` — 无封面日期 → 诚实留空（不猜测）。
- `test_middle_cover_blocks_fallback` — 扫描版兜底：fitz 文本层为空时，从 middle.json 前 2 页提取封面块。
- `test_middle_cover_blocks_missing_file` — middle.json 缺失/坏件 → 空表（诚实留空）。
- `test_gate3_value_unit_wrap_not_clause_head` — E8 闸门 3（2026-09-01）：正文折行后行首"1.5m时，为了计算…"是量值+单位。

### `tests/test_debug_dump_retention.py`（9 个）

- `test_egress_volume_cannot_evict_question_evidence` — **正向**：灌满审计窗口之后，提问证据必须一条不少。
- `test_the_whole_table_prune_would_evict_them` — **反向**：同一批数据喂给旧的"全表裁"，提问证据**必须**被挤掉。
- `test_pruning_one_type_leaves_the_other_alone` — 按类型清理**只裁自己那一类**（这条是修复的全部要点）。
- `test_keep_bound_is_respected_and_returns_the_count` — `keep` 生效、且返回删掉的条数（调用方可据此观测）。
- `test_the_newest_are_the_ones_kept` — 留下的是**最新**的（同一秒内插入时靠 rowid 兜底成全序）。
- `test_question_evidence_outlives_the_audit_window` — **意图**要写进断言：提问证据的保留上限必须**大于**审计的——。
- `test_record_egress_call_site_prunes_its_own_type_with_its_own_cap` — `record_egress` 必须裁 **egress**、且用**它自己的上限**。
- `test_debug_dump_has_the_type_created_index_and_the_paging_query_uses_it` — 索引必须在，且**分页查询真的用得上它**。
- `test_init_schema_recreates_the_index_on_an_existing_db` — **已有库**（缺这条索引）在 `init_schema` 时会被**自动补建** —— 这是"不必写迁移函数"的依据。

### `tests/test_doc_render_api.py`（9 个）

**TestTableImage**

- `test_渲染成功_带比例还原头` — 有 middle.json + 页码/序号合法 ⇒ 200 + PNG + 三个 X-Frac-* 头。
- `test_无深度产物_错误码是_table_geo_not_found` — 删掉 middle.json ⇒ 404 `table_geo_not_found`（前端按码隐藏占位）。
- `test_序号越界_错误码是_table_not_found`
- `test_未知文档_错误码是_doc_not_found`
**TestFormula**

- `test_未知文档`
- `test_条款不存在`
- `test_渲染成功_返回_PNG` — 有 middle.json 的 `interline_equation` 块 ⇒ fno=1 **真的渲染成功**。
- `test_公式序号不存在_错误码是_formula_not_found` — 不存在的公式序号（99）⇒ 明确 404（前端按码隐藏占位）。
- `test_缺_clause_参数是_422` — `clause` 是必填查询参数：漏传应当是 422（不是 500、也不是 200）。

### `tests/test_folder_filing_plan.py`（9 个）

- `test_plan_uses_the_same_classification_as_the_catalog` — **接线断言**：计划给的路径必须就是 `classify_document` 那四级，。
- `test_plan_puts_unclassified_into_pending_without_folders`
- `test_plan_excludes_hidden_docs`
- `test_plan_deep_and_direct_counts`
- `test_plan_records_anomalies_instead_of_guessing` — 值为空 / 名字超上限 ⇒ 进 anomalies，**不**静默塞进某个目录。
- `test_plan_duplicate_and_missing_ids_are_anomalies`
- `test_plan_is_repeatable`
- `test_apply_plan_on_small_fixture_db` — 小 fixture 库上真跑一遍：目录树、归属、状态、含更深层计数都读得回来。
- `test_render_text_has_the_sections_the_owner_asked_for`

### `tests/test_latex_array.py`（9 个）

**TestArrayEnvironment**

- `test_full_env_no_residue`
- `test_row_break_becomes_separator`
- `test_bare_leak_from_real_artifact`
- `test_column_spec_variants`
- `test_thin_space_commands`
**TestArrayReverseControls**

- `test_word_containing_array_untouched`
- `test_variable_product_preserved`
- `test_normal_digits_preserved`
- `test_frac_still_converted`

### `tests/test_middle_bbox_units.py`（9 个）

**Test归一化bbox换算成点**

- `test_比例bbox被换算成页尺寸量级` — 喂 `[0.116, 0.138, 0.937, 0.176]`（比例）⇒ 出 `[285, 477, 2301, 608]`（点）。
- `test_换算后通过退化闸门` — ★ 这是**用户可见的效果**：换算后箭头才画得出来（不再被当碎片丢掉）。
- `test_坐标落在页尺寸内` — 换算后 x 必须 ≤ 页宽、y ≤ 页高（不越界）。
- `test_页尺寸不同则换算结果不同` — 防"写死 595/841"：同一比例在 600×800 与 2456×3456 上结果必须不同。
**Test已是点的bbox不被重复缩放**

- `test_绝对值bbox原样保留` — 喂 `[285, 477, 2301, 608]`（已经是点）⇒ 不许再乘。
- `test_混合值不被缩放` — 只要有一个值 >1，整条**原样返回**（不猜、不部分缩）。
- `test_空bbox不炸`
**Test行级bbox也换算**

- `test_行级bbox也乘页尺寸`
**Test3_4产物行为不变**

- `test_34产物原样返回`

### `tests/test_naming_convention_scanner.py`（9 个）

- `test_tracked_files_returns_real_paths_not_escaped` — 非 ASCII 路径必须是**真路径**，不能是 `\345\271\277` 这种八进制转义。
- `test_non_ascii_paths_survive_round_trip` — 带中文的路径必须是**真路径**（转义形态 `\345\271\277` 必然不是）。
- `test_govqa_data_dir_is_excluded` — 采集数据目录必须被剪掉——它由另一个自动化拥有，不归本命名规范管。
- `test_code_files_are_not_flagged_for_underscores` — **R3 的核心**：Python 的 `snake_case.py` 是**正确写法**，不是违规。
- `test_current_tree_has_zero_violations` — 当前树必须零违规——这是这条规范**已经被执行过**的机械证据。
- `test_scanner_has_teeth_on_doc_filename` — **变异验证（R1 有牙）**：`foo_bar.md` 必须被判违规，`foo-bar.md` 必须放过。
- `test_code_filenames_are_exempt_from_R1` — **R1 的边界**：`snake_case.py` **不许**被判违规（这是 v1 被推翻的直接原因）。
- `test_scanner_has_teeth_on_dir_name` — **变异验证（R2 有牙）**：含大写的目录名必须被判违规，全小写必须放过。
- `test_skip_dir_check_handles_nested_and_prefix_paths` — 剪枝判据本身要正确：嵌套目录要剪、正常文档不能误剪。

### `tests/test_phase4.py`（9 个）

- `test_bookmark_crud_and_boost`
- `test_annotation_crud`
- `test_project_crud`
- `test_document_tree`
- `test_clauses_by_prefix` — 目录展开 API：前缀查子条款（点 ▸ 懒加载该标题下所有条款，2026-08-23 新增）。
- `test_exports` — R19 引用块（**纯文本**）。
- `test_export_download_guard`
- `test_sse_time_warnings_and_enrichment` — 证据事件应带时效警示（upcoming 文档）与收藏/置信度富化字段。
- `test_doc_bookmark_crud` — 标准级书签（user_doc_bookmark）：幂等、列表带 doc_meta、按 id/doc 删除、。

### `tests/test_pypdf_backfill.py`（9 个）

- `test_terminator_hits_structural_markers` — 表/图/附录编号、页眉、工具水印 → 必须终止归并。
- `test_terminator_does_not_hit_body_text` — **反向对照**：普通正文与条款号不得被当成边界（否则正文被腰斩）。
- `test_page_clauses_stops_at_table_anchor` — **核心回归**：条款正文在表编号处收口，不再吞下页尾。
- `test_page_clauses_next_clause_still_splits` — 终止锚不得破坏原有的"下一条款切分"行为。
- `test_page_clauses_appendix_anchor` — 附录编号行也必须终止（实测 `表E.4`/`附录A` 是越界的主要来源之一）。
- `test_backfill_syncs_fts_with_patched_text` — **核心回归**：回填后 `clause_fts` 必须反映**补丁正文**，而不是补丁前原文。
- `test_backfill_fts_untouched_when_rejected` — 反向对照：回填被拒（越界）时**不得**动 FTS（否则索引指向不存在的正文）。
- `test_backfill_rejects_oversized_text` — 回填若把文本撑成原文的 3 倍以上（越界抽取的直接特征）→ 拒绝打补丁。
- `test_backfill_accepts_reasonable_text` — **反向对照**：长度合理且数字更多的回填必须被接受（护栏不得打掉真修复）。

### `tests/test_reingest_keeps_filing.py`（9 个）

- `test_reingest_moves_every_membership_and_touches_nothing_else` — 重导一篇归在两个目录里的文件 ⇒ 新 doc_id 的归属集合 == 旧集合。
- `test_both_delete_paths_clear_membership_and_state` — ``clause_repo.delete_document``（单篇）与 ``doc_delete.delete_documents``（批量）。
- `test_reingest_keeps_failed_old_state_from_smearing_a_success` — 旧行是 ``failed``、这次解析成功 ⇒ 新行**不许**还是 ``failed``（也不许停在 recognizing）。
- `test_reingest_of_failed_parse_marks_failed_even_when_membership_carried` — 已归位的那篇这次解析**失败**（正文为零）⇒ ``failed``（不假装成功），归属照旧搬过去。
- `test_no_carry_without_an_old_document` — **反向哨兵**：没有旧文档可替换（全新标准号 / 普通入库）⇒ 一条都不搬。
- `test_restore_refuses_a_missing_target_and_is_idempotent` — 原地判 ``restore_filing_assets``：目标文档不存在 ⇒ ``doc_not_found``（**且什么都没写**）。
- `test_carry_failure_is_reported_not_silent` — 搬运**失败**必须与"没有旧文档要搬"分得开（``filing_assets_carry_error`` 非空）。
- `test_restore_skips_folders_deleted_after_the_snapshot` — 拍快照之后、落盘之前目录被删掉 ⇒ **不插**那条悬空挂靠。
- `test_restore_says_the_truth_when_every_folder_was_deleted` — 快照里的目录**全被删** ⇒ 一条都没搬成 ⇒ **不许**说它还归位在某个目录里。

### `tests/test_span_calibration.py`（9 个）

- `test_page_line_centers_and_vote_top_bottom_none` — ①两页 PDF 三行已知文本：top-origin bbox 判 top。
- `test_calibrate_new_idempotent` — ②纯函数版：顶部原点翻为底部原点后二次调用零变化。
- `test_calibrate_new_supports_source_span_model` — pipeline 接入形态：SourceSpanModel 对象同样原地归一为底部原点。
- `test_fragment_vote_no_split_50140_style` — ③50140 复验式：条款块中段碎片 bbox 用最近行投票一致判定，不再分裂。
- `test_calibrate_db_rowid_update_and_audit` — ④存量路径（带内真值裁决）：rowid 精确 UPDATE + event_log 审计。
- `test_calibrate_dry_run_and_empty_safe` — ⑤dry-run 只报告零写库。
- `test_calibrate_both_hit_uses_direction_no_double_flip` — v2 回归：采样 span 落在镜像对称区（两种解释都命中）时，已正确的文档**不得**被翻转。
- `test_calibrate_direction_vote_flips_when_text_unverifiable` — v2 回归：无文字层页（模拟乱码/纯扫描件）带内文字无法判定 → 阅读方向证据兜底：。
- `test_calibrate_new_uses_direction_with_groups` — pipeline 形态：calibrate_new 传入条款分组后，方向判别生效（无文字层也能翻）。

### `tests/test_announce_ingest.py`（8 个）

- `test_scope_rules_strong_cue_wins_deny_otherwise` — 范围判定：**强规范性线索压过排除词**。
- `test_summary_counts_match` — 进度计数：已发现 / 已入库 / 还差多少 / 跳过多少 —— 四个数互相自洽。
- `test_ingest_pending_writes_and_is_idempotent` — 批量入库：真写库 + 分档计数 + 非规范性跳过 + **重复跑不重复入** + pending_left 归零。
- `test_reingest_reports_already_in_library_not_ingested` — **已经入过的再点一次**：必须报 `skipped/already_in_library`，不许再报"入库成功"。
- `test_force_ingests_named_non_normative` — `force=True` 是**逃生口**：范围判错了时业主不必等改代码（连部门决算也入）。
- `test_limit_bounds_and_failures_are_honest` — `limit` 封顶（一次点下去不会抓几百页）+ 取不到页如实报 `failed`，且**不算**成入库。
- `test_batch_caps_and_dedupe_have_teeth` — 三条"防跑飞"的机制**各自要有判据**（独立复核 MED-2/3/4：此前只有自然语言宣称，。
- `test_routes_pending_and_ingest_wire` — 两个端点的**接线**：待入库计数出得来、入库入参原样转下去、非法 limit 给 422。

### `tests/test_answer_confidence.py`（8 个）

- `test_two_call_sites_are_the_same_function` — `server._answer_confidence` 必须是**转发**，不是第二份实现。
- `test_both_field_spellings_agree` — 裸名与下划线名必须给出**同一个档位**。
- `test_empty_evidence_is_low_not_high` — **空证据 ⇒ low**。
- `test_failed_verification_is_low`
- `test_low_confidence_evidence_is_mid`
- `test_all_high_confidence_is_high`
- `test_threshold_boundary`
- `test_missing_confidence_defaults_to_high` — 没有 `type_confidence` 字段时按 1.0 处理（缺字段 ≠ 低可信）。

### `tests/test_api_config.py`（8 个）

- `test_set_credential_writes_both_names`
- `test_set_credential_skips_blank_and_dash_clears`
- `test_cloud_dash_clears_base_url`
- `test_unknown_channel_rejected`
- `test_status_never_leaks_key`
- `test_status_accepts_namespaced_llm_key` — 新名（本机保存后的形态）必须让 configured 为真。
- `test_settings_reads_cloud_key_from_env`
- `test_settings_cloud_base_url_default`

### `tests/test_deep_server.py`（8 个）

- `test_提交_攒批_返回_output_dir`
- `test_任务失败_返回_None_回退信号`
- `test_无服务超时_返回None并清理任务文件`
- `test_开关关闭_不提交任务`
- `test_提交与等待拆分_先投后收`
- `test_开关关闭_submit返回None`
- `test_并发冷启动_按目标数拉起不超额` — 单飞锁：多客户端同时发现 daemon 不足，只补足 KS_DEEP_WORKERS 个，。
- `test_任务抢占_两个收集者不重叠` — v5 抢占锁：daemon A 领走的任务，daemon B 的 _collect_jobs 拿不到。

### `tests/test_figure_legend_strip.py`（8 个）

**TestLegendSegmentStripped**

- `test_real_artifact_shape`
- `test_caption_terminates_segment`
- `test_two_segments_in_one_block`
- `test_idempotent`
**TestLegendReverseControls**

- `test_head_without_entries_kept`
- `test_dash_line_without_head_kept`
- `test_plain_text_untouched`
- `test_empty`

### `tests/test_jev_ingest.py`（8 个）

- `test_ingest_judges_all_samples` — 13 条逐条判对：clear 只给"够确信是行政事务"的，灰区与规范一律 keep。
- `test_ingest_never_clears_change_signal` — 变更信号**永远不清**——哪怕 choice 判成 admin、confidence 也很高。
- `test_ingest_low_confidence_admin_stays_keep` — **不够确信 ⇒ 留着**（官方分类范式：报更粗的标签，而不是丢掉）。
- `test_ingest_degrades_to_none_when_unavailable` — Jev 挂 ⇒ `None`（调用方按规则原样处理，绝不因为外部服务挂了就误清库）。
- `test_ingest_rejects_malformed` — 响应不合契约 ⇒ None（不猜）。
- `test_ingest_asks_both_questions_in_one_call` — **一次调用问两题**（官方 parallel_questions：打包更便宜更快）。
- `test_triage_pending_is_read_only_and_buckets` — `triage_pending`：只读分档——清/灰/留三个桶 + 每条带判据（choice/confidence）。
- `test_rule_passes_through_several_admin_documents` — **已证事实的登记用例**：规则（强线索词优先）会漏放这几条行政事务。

### `tests/test_normalize_std_slash.py`（8 个）

- `test_普通行会被归一`
- `test_与已存在的行撞车必须跳过` — 同一标准的两个文件：一条已是半角、一条是全角 ⇒ 全角那条要**跳过**（不制造重复）。
- `test_计划内自撞也要跳过` — ⚠ 复核 b32 的 4.4：两行全角、归一到**同一个尚不存在**的目标。
- `test_清单内列与目标值不重复` — 清单级断言（上面那条是行为级）——防以后改坏判重逻辑。
- `test_没有全角就不产生变更`
- `test_standard_name_里的全角也归一`
**Test单事务语义**

- `test_中断会回滚` — `write_transaction` 必须对 `BaseException` 也回滚。
- `test_同进程第二次调用不炸` — 旧代码 `conn2.close()` 会把线程局部共享连接关掉 ⇒ 第二次 `ProgrammingError`。

### `tests/test_pua_separators.py`（8 个）

**TestSeparatorRestore**

- `test_date_separator_becomes_hyphen`
- `test_name_separator_becomes_space`
- `test_value_prefix_separator_becomes_space`
- `test_consecutive_codepoints_all_handled`
**TestNoRegression**

- `test_plain_text_unchanged`
- `test_empty`
- `test_other_pua_untouched`
- `test_idempotent`

### `tests/test_backup.py`（7 个）

- `test_snapshot_create_and_restore`
- `test_snapshot_rollout_auto_keep_7`
- `test_snapshot_checksum_mismatch`
- `test_snapshot_api`
- `test_snapshot_copies_secrets_json` — 批1整改：快照必须把 secrets.json 密文带进备份目录（密钥安全网）。
- `test_snapshot_without_secrets_json` — secrets.json 不存在（当前真机正是此状态）→ secrets_copied=False，快照照常成功。
- `test_snapshot_secrets_rollout_cleanup` — 自动快照滚动淘汰时 .secrets.json 副本一起删，不留孤儿密文文件。

### `tests/test_egress.py`（7 个）

- `test_record_egress_writes_dump`
- `test_chat_flow_leaves_egress_record` — chat 链路每次提问自动落外发记录（user_export，含 prompt/llm_output）。
- `test_egress_audit_api`
- `test_egress_query_keyset_cursor` — keyset 深翻页（2026-08-26）：按 (created_at, dump_id) 键集翻页无重复无遗漏。
- `test_egress_audit_export`
- `test_ks_answer_leaves_audit_record` — D2 红线回归：取证端点 `/ks/answer` 也必须落 debug_dump（user_export）。
- `test_ks_answer_record_is_not_evicted_by_egress_volume` — **服务端那个写入者**必须裁「提问证据」这一类（2026-09-26 复核 MED-1 的另半边）。

### `tests/test_formula_leader_appendix.py`（7 个）

**TestAppendixLetterLeader**

- `test_letter_number_normalized`
- `test_multiple_letter_numbers`
- `test_dotted_letter_number`
- `test_plain_digit_still_works`
- `test_idempotent`
**TestProseEllipsisSurvives**

- `test_two_ellipsis_kept`
- `test_normal_text_untouched`

### `tests/test_long_clause_tail_ruler.py`（7 个）

- `test_head_tail_split_is_512_chars` — 按字符切在 512：短于 512 ⇒ tail 为空。
- `test_production_still_uses_the_512_char_cap` — ★ 契约锚：尺子的 512 必须**真的**对应生产代码里的截断点。
- `test_tail_only_excludes_head_and_title` — `tail_only` = tail 词 − head 词 − title 词（title 也在向量里，必须一起扣）。
- `test_token_drop_partition_adds_up` — ★ 两段账：`gain`（去掉代码上限能白捡）+ `residual`（模型窗口仍挡）= 总丢量。
- `test_token_drop_partition_never_negative` — 边界：head 自己就超窗口（实测 2/4000）⇒ gain 不能为负。
- `test_model_window_is_pinned_to_512` — ★ 第二道截断点（**模型窗口**）必须被钉住 —— 独立复核 P2-1 实测：。
- `test_model_window_matches_local_tokenizer_config` — 契约锚：本机若有 bge-small-zh 的 `tokenizer_config.json`，其 `model_max_length` 必须 == MODEL_WINDOW。

### `tests/test_patch_guard.py`（7 个）

- `test_ok_minor_fix` — 正常 OCR 纠错（局部小改）→ ok。
- `test_reject_unrelated_paste` — 贴完全无关内容 → reject。
- `test_reject_garbage` — 大量不可打印字符（乱码/二进制）→ reject。
- `test_warning_length_grow` — 长度暴增 3 倍以上 → warning（疑似贴了多余内容）。
- `test_warning_length_shrink` — 长度骤减到 1/3 以下 → warning（疑似误删大段）。
- `test_warning_language_shift` — 中文占比骤降（贴英文代码）→ warning。
- `test_short_original_skips_similarity` — 原文太短（<12 字）跳过相似度检查。

### `tests/test_phase5.py`（7 个）

- `test_build_messages_history_order_and_cap`
- `test_build_messages_truncates_long_history`
- `test_expand_query_with_history`
- `test_modality_window_union_fixes_false_positive` — 4.10 场景：条款号两次出现，首个窗口无模态词，第二窗口含"不应"。
- `test_modality_weakened_still_caught_with_union` — 窗口并集后，真实减弱（应→宜）仍必须拦截。
- `test_sse_accepts_history_and_confidence`
- `test_llm_history_forwarded_with_mock` — mock LLM：确认 history 真正传到流式客户端（不真调 API）。

### `tests/test_quality_rules.py`（7 个）

- `test_qh_01_clause_health_diff_vs_inline` — 两件事一起锁：。
- `test_qh_04_html_to_text_byte_identical` — 表格 html→文本 必须与冻结副本**逐字符相等**（含 None/空/无表格）。
- `test_qh_04b_html_to_text_custom_limit` — limit 参数语义保持（旧签名有 limit 参数）。
- `test_qh_05_table_md_400_prefix_semantics` — `ClauseHealth.table_md` 保持"先 400 字截断"的既有语义（长表格漏检是已知缺陷，不在此修）。
- `test_qh_07_no_second_regex` — 反熵：`src/core/quality/` 里不得出现第二套标准号/文件名正则，也不得 import scripts/。
- `test_qh_02_quality_issues_endpoint_shape` — 端点响应形状/键集合/截断长度必须与抽取前一致（FAIL：键多/少，或截断长度不符）。
- `test_qh_03_quality_issues_limit_break` — limit 早停语义 + SQL 排序保持（FAIL：返回 >limit 条，或不是排序后的前 N 条）。

### `tests/test_real_corpus_retrieval.py`（7 个）

- `test_seed_fixture_actually_has_corpus` — 先证明 fixture 里真有语料 —— 否则后面每条断言都会"通过"，但什么都没验。
- `test_real_clause_is_resolvable` — 真条款能按「标准号 + 条款号」定位到 —— **空库上验不出来**（空库返回 None）。
- `test_real_clause_carries_source_spans` — 真条款带**位置片段**（可点链接要用）—— 空库上没有 span 可查。
- `test_absent_clause_returns_none_not_a_wrong_standard` — **查不到的条款号必须返回 None**，不许串到别家标准。
- `test_standard_number_disambiguates_between_documents` — 同一个条款号在不同标准下必须是不同条款（不许串号）。
- `test_hybrid_search_finds_real_methanol_clause` — **六路检索**在真语料上能召回到甲醇条款。
- `test_fts_channel_works_on_real_corpus` — FTS 通道在真语料上能查到中文词。

### `tests/test_reranker.py`（7 个）

- `test_reranker_scores_align_with_input` — 判据：返回的分数必须与 `texts` **一一对应**，不许替调用方排序。
- `test_reranker_rejects_length_mismatch` — 判据：分数个数与候选条数不匹配时必须**当场抛错**（fail-closed），不许静默错位。
- `test_reranker_pipeline_reorders_by_score` — 判据（端到端）：`_rerank_results` 真的会**按分数改顺序**。
- `test_rerank_offline_degrades_to_original` — 模型不可用时（monkeypatch 加载失败）→ 原序返回 + rerank_offline=true。
- `test_rerank_exception_clause_kept` — 含但书的例外条款即使被 rerank 挤出也必须保留（P1 例外保护）。
- `test_rerank_integration_smoke` — rerank 接入 perform_hybrid_search：模型离线时返回原序不抛错（R30 降级）。
- `test_reranker_real_model_reorders` — 真实模型单测：**正确条款（下标 1）应得最高分**（机制有效性证明）。

### `tests/test_update_package.py`（7 个）

- `test_pkg_01_export_brief_counts_match_direct_count` — 导出简报计数与直接 COUNT 一致。
- `test_pkg_02_announcement_pdf_and_quarantine_list` — 公告存档 PDF 随包拷贝。
- `test_pkg_03_tampered_checksum_rejected_zero_side_effect` — 篡改 checksum → 拒绝且零副作用：不建保护快照、不写台账。
- `test_pkg_04_manifest_missing_or_corrupt_rejected` — manifest 缺失 / 目录无 manifest / JSON 损坏 → 一律 package_manifest_missing。
- `test_pkg_05_non_empty_target_rejected_upd3003` — /UPD-3003 目标库非空拒绝。
- `test_pkg_06_strict_import_prepared_then_same_checksum_rejected` — strict 空库成功准备（含自动快照+简报）。
- `test_pkg_07_unknown_mode_rejected` — 未知导入模式在触碰任何文件前拒绝。

### `tests/test_api.py`（6 个）

- `test_health_no_token`
- `test_missing_token_401`
- `test_wrong_token_401`
- `test_sse_event_order`
- `test_resolve_clause_marks_basis_scope` — 定位端点必须把「能否作为依据」做成**机器可读**字段（红线：只引现行版）。
- `test_resolve_clause_reference_tier_speaks_chinese` — 新增的 `reference` 档（征求意见稿等**仅参考**件）也必须给**中文**禁令说明。

### `tests/test_credential_readers_scan.py`（6 个）

- `test_findings_in_text_finds_old_and_new_names`
- `test_findings_in_text_empty`
- `test_old_new_name_lists_are_disjoint`
- `test_scan_credential_files_reports_presence`
- `test_scan_credential_files_missing_home`
- `test_scan_shell_configs_autorun_absent`

### `tests/test_loop2_driver.py`（6 个）

- `test_consecutive_only_on_round1_pass`
- `test_fail_and_blocked_reset_consecutive`
- `test_three_strike_arms_and_solve_clears`
- `test_converged_requires_5_round1_and_no_blocked`
- `test_build_queue_dedups`
- `test_seed_issues_populates_classes`

### `tests/test_phase10_blindspots.py`（6 个）

- `test_r3_table_fidelity` — R3 表格/公式保真：content_markdown 表格与 table_summary 落库不丢失。
- `test_r47_quality_review_flag` — R47 质量评分/待复核：is_suspicious 标记 + 纠错联动转可信。
- `test_r62_special_chars` — R62 特殊字符保真：℃/≥/m² 等入库不被破坏。
- `test_r71_multi_column_order` — R71 多栏验证：MinerU 阅读顺序块按页序稳定输出（load_middle_items 顺序保持）。
- `test_r55_reference_integrity` — R55 引用完整性：cross_refs 引用应能解析到库内存在条款。
- `test_rl2_effectiveness_ranking` — R-L2 效力层级排序：法律效力高的文档条款应排前（rank_with_hierarchy）。

### `tests/test_phase7.py`（6 个）

- `test_import_policy_sections`
- `test_build_obligations`
- `test_gap_analysis_verdicts`
- `test_gap_analysis_red_when_no_coverage`
- `test_gap_api_flow`
- `test_export_citations_body_contract` — `POST /export/citations` 的 **HTTP 层**契约（§10.76）。

### `tests/test_seed_db_guard.py`（6 个）

- `test_seed_db_exists_and_size_is_sane` — 规模合理：不能是空库，也不能膨胀到没法进版本控制。
- `test_seed_db_has_all_required_standards` — 缺陷现场必须完整 —— 少一部标准，那条 bug 就复现不了。
- `test_seed_db_fts_is_populated` — FTS 必须是**真插入**过的，不是空壳。
- `test_cross_standard_false_hit_is_fixed` — **跨标准误命中已修**（wiki §四 #2，2026-10-23）。
- `test_all_victim_standards_no_longer_cross_hit` — 那 **9 部受害标准**逐个验：查不存在的条款号**一律不许串到别家**。
- `test_year_tolerance_forward_path_still_works` — 年份宽容的**正向**路径：旧版号要能宽松到现行版（修兜底时不能改坏）。

### `tests/test_unsupported_context.py`（6 个）

- `test_same_standard_not_retrieved_is_actionable` — 情形 a：引用了**同一部标准**里未被检索的条款 → 应报"检索未召回"。
- `test_outside_evidence_standard_is_distinguished` — 情形 b：引用**本轮未讨论**的标准 → 应报 `outside_evidence_standard`。
- `test_no_standard_nearby_reports_unknown_never_guesses` — 情形 c：附近没有标准号 → 必须报 `unknown`，**不得猜**。
- `test_evidence_clause_produces_no_context_entry` — 反向对照：证据**内**的条款号不得产生任何 context 条目（不是告警对象）。
- `test_context_length_matches_unsupported_length` — 结构不变量：两条列表**一一对应**（消费方可以按下标配对）。
- `test_blocking_behaviour_unchanged` — **边界**：分类只增信息，**不放行**——证据外条款仍使 is_valid=False。

### `tests/test_change_ack.py`（5 个）

- `test_mark_ack_applies_withdrawn_to_doc_meta` — 确认废止变更 → doc_meta.legal_status 同步为 withdrawn + 审计两条。
- `test_mark_ack_applies_superseded`
- `test_mark_ack_not_applied_for_new_version` — new_version 变更只确认不落状态（引导导入新版而非改写现行状态）。
- `test_mark_ack_cancel_does_not_apply` — 取消确认（ack=False）不落库。
- `test_mark_ack_missing_change_raises`

### `tests/test_classical_segmentation_ruler.py`（5 个）

- `test_char_seg_gives_one_token_per_cjk_char` — B 口径：每个汉字一个 token。
- `test_char_level_requires_relaxing_the_single_char_drop` — ★ 这条路的核心代价：**字级查询不能复用 `fts_match_expr`**。
- `test_no_drop_expr_differs_from_production_only_by_the_single_char_rule` — A+ 口径：**索引不动**，只关掉"丢弃单字符词"这条规则。
- `test_single_ratio_counts_occurrences_not_documents` — ★ 单字占比必须按**出现次数**（`cnt`）算。
- `test_ngram_counts_segments_not_occurrences` — n-gram 的计数单位是**段**：一个词在同一段里出现 5 次只算 1。

### `tests/test_file_digest.py`（5 个）

- `test_empty_file_digest` — 空文件的 SHA-256 是标准常量 —— 算错说明初始化/循环写错了。
- `test_known_content_digest` — `b"abc"` 的 SHA-256 是公开标准值。
- `test_chunk_boundaries_match_whole_file_hash` — 跨分块边界时，分块算法必须与「一次读全」得到同一个指纹。
- `test_two_call_sites_share_one_implementation` — 两个历史调用点必须**指向同一个函数对象**（防有人又各写一份）。
- `test_chunk_size_is_frozen` — 分块大小是**历史指纹的契约**，不许改。

### `tests/test_gates_tracked_total.py`（5 个）

- `test_only_untracked_tests_are_excluded` — **正向**：tracked 的照算、untracked 的那 2 条被扣掉。
- `test_the_reverse_the_naive_total_would_count_them` — **反向**：不扣减的口径（= 旧行为）会把 untracked 的算进去 ⇒ 两个数必须不同。
- `test_unmappable_names_are_not_subtracted` — **保守**：认不出文件的条目**不许扣**（宁可少扣，不可多扣）。
- `test_class_based_and_parametrised_names_map_to_the_file` — 类里的用例（junit 把类名塞进 classname）与参数化（`name[param]`）都要认得出。
- `test_helper_raises_instead_of_guessing_when_git_is_unavailable` — **调用方的安全网**：没有 git（如 `git archive` 提取树没有 `.git`）时**必须抛**，。

### `tests/test_models_dir_override.py`（5 个）

- `test_models_dir_defaults_inside_the_bundle` — ⚠ 2026-10-18 契约变更：默认从 `<data_dir>/models` 改成**包内**。
- `test_models_dir_does_not_follow_data_dir_anymore` — 反向钉子：换 `KS_DATA_DIR` **不再**带着模型目录跑。
- `test_models_dir_honours_override`
- `test_models_override_does_not_move_data_or_db`
- `test_models_override_dir_is_created_by_ensure_dirs`

### `tests/test_scnet_readchain.py`（5 个）

- `test_reads_from_encrypted_store_first`
- `test_env_var_wins_without_store`
- `test_registry_fallback_still_works` — 加密存储没有 → 注册表覆盖链仍可用（只读，为 CI/老 setx 值保底）。
- `test_missing_everywhere_returns_false`
- `test_ks_namespace_alias_in_store` — 加密存储里若用的是 KS_ 命名空间名，同样能取到（并存注入）。

### `tests/test_standard_body.py`（5 个）

- `test_extracts_standard_body_not_year`
- `test_returns_none_when_no_body`
- `test_body_hits_respects_numeric_boundary` — `GBZ 24-2025` 的主体 `24` **不许**命中 `GB/T 13537-2024`。
- `test_body_hits_accepts_exact_and_prefixed` — 边界判据不许把**该命中**的挡掉。
- `test_body_hits_handles_none`

### `tests/test_table_binding.py`（5 个）

- `test_caption_number_must_not_steal_chapter_clauses` — 回归核心（物理就近语义）：题注"表1/表2"不得撞号挂到章级条款 1/2。
- `test_table_follows_physical_position_over_reference` — 物理就近优先于引用（新语义）：表5 物理落在章"4"之后（4其他 独立成章、。
- `test_appendix_table_binds_appendix_clause` — 附录表（表A.1）挂附录条款。
- `test_word_boundary_no_false_reference` — 引用判定词边界："表1.1"不算引用"表1"。
- `test_multi_table_same_clause_append` — 同一条款多张表（正表+续表）保持追加语义，不覆盖。

### `tests/test_web_ingest.py`（5 个）

- `test_web_i01_classify_status_priority` — 效力档判定：**先认"征求意见稿"**（标题里同时出现"办法"也要判成仅参考），。
- `test_web_i02_extract_body_text_drops_chrome` — 正文抽取：**去掉导航/脚本/页脚**，只留正文，且段落之间保留换行。
- `test_web_i03_ingest_writes_document_with_source_url` — 真入库：**令/规章**那种有"第X条"的正文走 `law_text` 通道，。
- `test_web_i04_no_clause_announcement_uses_single_clause` — **没有"第X条"的公告**（政府站常见）也要能入库：整篇作一条（编号"全文"），。
- `test_web_i05_draft_ingested_as_reference_and_failures` — **征求意见稿必须入库**（业主 2026-09-24 更正），但效力档是 `reference`（参考资料/仅参考）——。

### `tests/test_api_cold_start.py`（4 个）

- `test_effect_report_serves_a_brand_new_db` — 冷启动：效力报告不能 500（这是那个缺陷的精确复现式）。
- `test_document_catalog_endpoints_serve_a_brand_new_db` — 同一类读者（`server.py` 里也用 `catalog_hidden`）在空库上同样不能 500。
- `test_effect_report_docs_endpoint_serves_a_brand_new_db` — 明细端点也走同一个 `_load_docs()`（避免"只修了汇总"）。
- `test_bootstrap_guarantees_the_columns_readers_use` — **契约级**钉子：`init_schema()` + `ensure_additive_columns()` 之后，。

### `tests/test_assets_endpoint.py`（4 个）

- `test_asset_served`
- `test_asset_traversal_and_whitelist_rejected`
- `test_asset_bad_doc_id_rejected`
- `test_asset_missing_404`

### `tests/test_ccs_fetcher.py`（4 个）

- `test_ccs_to_tag_fallback_local` — 网络不可用时回退本地映射表（不阻塞入库）。
- `test_ccs_to_tag_live_result` — 有网络结果 → 用实时 CCS。
- `test_classify_uses_ccs_tag` — 分类优先用 domain_tags 的 CCS 标签（4 级树）。
- `test_law_classify_levels` — 法规分类（三级体系《法律法规分类编码体系》）：效力层级 → 法律部门 → 业务领域。

### `tests/test_credential_reconcile.py`（4 个）

- `test_same_key_reports_consistent`
- `test_forked_key_reports_divergence`
- `test_missing_dsh_file_is_honest`
- `test_engine_only_side`

### `tests/test_doc_batch_delete.py`（4 个）

- `test_batch_delete_cascades_all_tables`
- `test_batch_delete_requires_confirm`
- `test_batch_delete_validates_input`
- `test_batch_delete_missing_only_leaves_db_untouched`

### `tests/test_jev_cn_baseline.py`（4 个）

- `test_cn_baseline_file_is_self_consistent` — **硬断言**：基线文件自洽（20 条 / 三档合法 / 每条三���分数都在 / 模型名钉版本）。
- `test_cn_baseline_covers_implicit_compliance` — 基线必须**覆盖 8 条隐性合规**（官方蓝本里最值钱的一档：词表看不见的那些）。
- `test_live_checker_exists_and_is_not_wired_into_judgments` — 真机对照脚本必须在（它是"持续盯"的载体），且**不得**被 pytest 当判据调用。
- `test_scores_in_plausible_range` — 概率类分数必须在 0~1（**severity 例外**：它是档位下标 0..档数−1）。

### `tests/test_loop2_vlm.py`（4 个）

- `test_both_images_sent_and_structured`
- `test_retry_on_transient_error`
- `test_no_key_degrades_not_raises`
- `test_parse_json_tolerates_fences`

### `tests/test_patch_migration.py`（4 个）

- `test_migrate_patches_three_branches`
- `test_content_hash_backfill` — content_hash 列迁移 + 存量回填（幂等）。
- `test_content_hash_on_insert`
- `test_migrate_patches_api`

### `tests/test_phase13_blindspots.py`（4 个）

- `test_r13_quality_grade_tag` — R13 质量分级标签：doc_meta.quality_grade 落库与校验约束。
- `test_r44_offline_flag_exists` — R44 离线模式：app_config 离线开关存在性与默认值（功能隐藏由前端门控）。
- `test_r59_coverage_mode_switch` — R59 覆盖范围模式：include_superseded 开关影响检索时效过滤。
- `test_r67_transition_both_valid` — R67 过渡期并行有效：upcoming 与 effective 文档同时存在时不互斥。

### `tests/test_phase8.py`（4 个）

- `test_health_board`
- `test_debug_trace_recorded_by_default` — P9.4：每次提问默认落 Debug Trace，含各阶段 trace 数据，无需显式参数。
- `test_debug_trace_clarify_recorded` — R9 v2：追问由 LLM 单次自判。
- `test_session_file_written` — 引擎 run() 应写 engine.session.json（用 create_app 前先验证函数存在性）。

### `tests/test_selfcheck_fixes.py`（4 个）

- `test_query_modality_compound_guard`
- `test_write_queue_stale_processing_recovered`
- `test_same_standard_different_hash_blocked` — R43: 同标准号不同 hash 不崩溃，返回 standard_exists 供上层确认。
- `test_ingest_missing_file`

### `tests/test_storage.py`（4 个）

- `test_pragmas`
- `test_foreign_key_cascade`
- `test_fts5_and_vec_tables`
- `test_write_queue_serializes`

### `tests/test_update_report.py`（4 个）

- `test_rep_04_tier_grouping_and_trend_window` — tier 分组取自 bulk_import_batch 锚行。
- `test_rep_05_xlsx_export_reopenable_with_key_content` — Excel 版落盘 exports、openpyxl 可重开。
- `test_rep_06_xlsx_empty_batch_still_exports` — 空批次（total=0、零事件）也能出 xlsx：汇总全 0、明细仅表头。
- `test_rep_07_xlsx_missing_batch_upd2003_zero_side_effect` — 批次不存在：抛 UPD-2003 且不在 exports 目录产生任何 .xlsx。

### `tests/test_vision.py`（4 个）

- `test_image` — 生成含规范文字的小图（复用 var/vision_test.png 或现场生成）。
- `test_vision_locate_ocr_and_retrieve` — 端到端：图片 OCR 文本应能检索到库内条款（GB30871 5.2.x 系列）。
- `test_vision_locate_missing_image`
- `test_vision_api`

### `tests/test_auto_tag.py`（3 个）

- `test_auto_tag_standard_and_superseded`
- `test_auto_tag_filename_fallback`
- `test_apply_tags_does_not_touch_clause`

### `tests/test_doc_catalog_std_no.py`（3 个）

- `test_forms_that_must_count_as_standard`
- `test_forms_that_must_not_count_as_standard`
- `test_classify_document_uses_the_same_judgement` — **接线断言**：`classify_document` 必须走这条判据（不能自己再写一份判断）。

### `tests/test_docx_ingest.py`（3 个）

- `test_parse_docx_text`
- `test_run_docx_ingest_direct`
- `test_run_docx_ingest_missing`

### `tests/test_golden_gate.py`（3 个）

- `test_golden_gate_baseline_present` — 门禁前置：基线必须存在（**不得**由本测试自行重建）。
- `test_golden_gate_no_regression`
- `test_golden_gate_minimums` — 硬底线：核心指标不得低于可接受线（防集体塌方式缓慢劣化）。

### `tests/test_govcn_archive.py`（3 个）

- `test_archive_downloads_real_pdf`
- `test_archive_falls_back_placeholder_on_bad_content`
- `test_archive_falls_back_placeholder_without_url`

### `tests/test_label_gap_not_jev.py`（3 个）

- `test_facts_still_hold` — 量测结论的前提是这些事实。
- `test_change_signal_column_exists_after_migration` — `change_signal` 列：真库已 ALTER 补上（2026-09-24），全新库由 schema.sql 直接带。
- `test_decision_recorded` — 本文件是**决策留痕**（不是待办）：B3-⑦ 不由 Jev 填，理由=单一真源/既有机制已有归属。

### `tests/test_law_text_edges.py`（3 个）

- `test_edge_source_is_the_referring_clause` — 边的 source 必须是**引用别人的那一条**，不是"文档的最后一条"。
- `test_last_clause_has_no_outgoing_edges` — 反向：被引用的**最后一条**不该凭空多出任何出边（缺陷的签名就是它）。
- `test_edge_count_matches_reference_sites` — 边的**条数**也要对：该文档共 2 处引用 ⇒ 恰好 2 条边（不多不少）。

### `tests/test_llm_empty_retry.py`（3 个）

- `test_empty_then_good_retries_and_succeeds` — 第一次空、第二次有 ⇒ 用第二次结果，不标 llm_unavailable。
- `test_always_empty_degrades_honestly` — 一直空 ⇒ 诚实降级，且说明重试过。
- `test_llm_error_not_retried` — 配置类错误不重试 —— 否则 Key 错时会白等 max_attempts 倍。

### `tests/test_measure_harness.py`（3 个）

- `test_尺能量出_async_def_把事件循环堵住`
- `test_尺能量出_def_没有把事件循环堵住`
- `test_两条端点的耗时同量级_证明尺量的是谁被占住而不是谁慢`

### `tests/test_mineru_gpu_lock.py`（3 个）

- `test_gpu_lock_互斥_第二持锁者等待期间抢不到`
- `test_gpu_lock_释放后_可再次获取`
- `test_gpu_lock_禁用开关_KS_GPU_LOCK_0_直通`

### `tests/test_modality_window_false_positive.py`（3 个）

- `test_correct_keke_not_reported_as_strengthened` — 模型正确复述「可」时，不许报 strengthened（2026-10-19 真机误报）。
- `test_real_weakened_still_intercepted` — 真问题必须还在：把「不应」写成「应」时，仍要拦截。
- `test_correct_buneng_passes` — 模型正确保留「不应」时，不许误报。

### `tests/test_phase12.py`（3 个）

- `test_office_roundtrip_full_cycle` — 12.1：创建会话 → 模拟编辑（改写 docx）→ 轮询检出 → 提交落库 → 撤销/清理。
- `test_backlinks` — 12.2：条款被 收藏/义务清单/审查点 引用时全量召回。
- `test_phase12_api`

### `tests/test_r5a.py`（3 个）

- `test_loosened_internal_refs`
- `test_expand_evidence_chain`
- `test_search_with_details_expansion`

### `tests/test_sqlite_conn_registry.py`（3 个）

- `test_close_all_connections_reaches_another_thread_and_keeps_it_usable` — ① 别的线程那份被关掉（文件能删）。
- `test_close_thread_connection_forgets_its_registry_entry` — ③ `close_thread_connection()` 关掉之后，登记表里**不许**再留着那条死登记。
- `test_close_all_connections_is_safe_when_nothing_is_registered` — ④ 空表/重复调用都不许炸（两个 fixture 收尾都会调它）。

### `tests/test_supervisor.py`（3 个）

- `test_supervisor_restarts_then_clean_exit`
- `test_supervisor_circuit_break`
- `test_supervisor_no_restart_on_clean`

### `tests/test_table_position_render.py`（3 个）

- `test_tables_interleaved_back_to_source_pages` — 表甲（第10页）插在第10页两行之后、12页页界之前。
- `test_tables_tail_append_without_spans` — 无表格 span（存量文档）→ 旧末尾追加行为，零变化。
- `test_tables_tail_append_on_span_count_mismatch` — span 数与 <table> 数不对齐（旧库部分 span 丢失）→ 宁可缀尾不可错位。

### `tests/test_dry_run_concurrency.py`（2 个）

- `test_同一份源文件的并发预览被串行化` — 同一 content ⇒ 同一 `<hash16>` 目录 ⇒ 必须串行（并发峰值 = 1）。
- `test_不同文件的并发预览允许并行` — **反向断言**：不同文件（分片不同）不许被一把全局锁串起来。

### `tests/test_dryrun.py`（2 个）

- `test_analyze_preview_no_write`
- `test_analyze_preview_missing`

### `tests/test_fewshot.py`（2 个）

- `test_fewshot_injection_from_feedback`
- `test_fewshot_empty_no_change`

### `tests/test_gate_baseline_whitelist.py`（2 个）

- `test_gate_baseline_skip_lists_have_no_vanished_nodes` — 两份名单里的每一条都必须还在。
- `test_the_alive_checker_itself_is_not_a_tautology` — 判据自己要被验：三种情形各断言一次（缺一不可，否则"什么都判在/判不在"看不出来）。

### `tests/test_golden_set.py`（2 个）

- `test_qa_retrieval_hits_golden` — 对真实库做检索命中基准（库含 GB30871 时启用）。
- `test_golden_qa_api_structure` — 问答 API 结构基准（不依赖真实库内容）。

### `tests/test_legal_status_reference.py`（2 个）

- `test_ref_migration_rebuilds_doc_meta` — 四值 ⇒ 五值：迁移前写不进、迁移后写得进。
- `test_ref_migration_leaves_other_enum_alone` — **不动** `update_change_event.current_legal_status`（四值）—— 它没有生产者要写 reference。

### `tests/test_rag_gate_not_adopted.py`（2 个）

- `test_measure_file_exists_and_has_all_queries`
- `test_low_score_does_not_mean_irrelevant_documented` — **决策钉死**：前两组 top-5 的「相关」分全低，但它们**命中的法规是对的**。

### `tests/test_write_queue_bootstrap.py`（2 个）

- `test_worker_consumes_ingest_doc_and_skips_unknown`
- `test_ingest_doc_missing_file_fails_cleanly` — 真实 handler：文件不存在 → failed（不悬挂、不抛穿线程）。
