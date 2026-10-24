# 前端清单（文件 / 导出 / 说明）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

`exports` / `declarations` 用**正则**抽取（没有 TS AST 工具链），**这是近似，不是完整符号表**。`header_note` 取文件开头 40 行内第一条注释的首句。

## 二、总账

| 项 | 数 |
|---|---:|
| 文件 | **50** |
| 导出 | 629 |
| 声明 | 754 |
| 含 JSX 的 | 18 |

## 三、每个文件

| 文件 | 行数 | 导出 | 声明 | 开头说明 |
|---|---:|---:|---:|---|
| `plugin/client/api.ts` | 5,012 | 225 | 35 | ks-dsh-plugin — client/api.ts |
| `plugin/client/KsKnowledgePage.tsx` | 3,869 | 2 | 28 | ks-dsh-plugin — client/KsKnowledgePage.tsx |
| `plugin/client/KsEvidenceTab.tsx` | 2,835 | 1 | 49 | ks-dsh-plugin — client/KsEvidenceTab.tsx |
| `plugin/src/index.js` | 1,892 | 18 | 40 | — |
| `plugin/client/KsSettingsSection.tsx` | 1,637 | 7 | 18 | ks-dsh-plugin — client/KsSettingsSection.tsx |
| `plugin/client/KsMaterialsPanel.tsx` | 1,410 | 17 | 24 | ks-dsh-plugin — client/KsMaterialsPanel.tsx |
| `plugin/src/chatmode.js` | 1,392 | 29 | 57 | — |
| `plugin/client/ksGuideStyles.ts` | 1,136 | 2 | 5 | ks-dsh-plugin — client/ksGuideStyles.ts |
| `plugin/src/inspection.js` | 1,078 | 12 | 47 | — |
| `plugin/src/engine.js` | 941 | 24 | 26 | — |
| `plugin/src/announce.js` | 928 | 13 | 41 | — |
| `plugin/client/KsChannelsPanel.tsx` | 906 | 13 | 23 | ks-dsh-plugin — client/KsChannelsPanel.tsx |
| `plugin/client/KsFilesTab.tsx` | 806 | 3 | 34 | ks-dsh-plugin — client/KsFilesTab.tsx |
| `plugin/src/ingest.js` | 762 | 12 | 42 | — |
| `plugin/client/KsBookmarksTab.tsx` | 688 | 3 | 16 | ks-dsh-plugin — client/KsBookmarksTab.tsx (2026-10 收藏目录) |
| `plugin/client/KsTurnTab.tsx` | 594 | 16 | 12 | ks-dsh-plugin — client/KsTurnTab.tsx  （S1-a 空态 + S1-b 依据行，2026-09-22） |
| `plugin/client/KsIngestPanel.tsx` | 572 | 2 | 6 | ks-dsh-plugin — client/KsIngestPanel.tsx |
| `plugin/client/entry.ts` | 510 | 3 | 9 | ks-dsh-plugin — client/entry.ts (the client half's cordis entry) |
| `plugin/src/materials_routes.js` | 471 | 4 | 19 | — |
| `plugin/client/KsCapabilityPage.tsx` | 465 | 7 | 8 | ks-dsh-plugin — client/KsCapabilityPage.tsx |
| `plugin/client/ksSidebar.ts` | 420 | 37 | 25 | ks-dsh-plugin — client/ksSidebar.ts  (2026-09-16 官方 sidebar 迁移) |
| `plugin/client/KsDocTextView.tsx` | 394 | 3 | 6 | ks-dsh-plugin — client/KsDocTextView.tsx |
| `plugin/src/report.js` | 350 | 6 | 19 | — |
| `plugin/src/channels.js` | 339 | 4 | 12 | — |
| `plugin/src/materials.js` | 328 | 1 | 7 | — |
| `plugin/src/collect.js` | 301 | 2 | 6 | — |
| `plugin/client/ksHostPrimitives.d.ts` | 287 | 36 | 0 | ks-dsh-plugin — client/ksHostPrimitives.d.ts |
| `plugin/src/compliance-sentry.js` | 274 | 16 | 20 | — |
| `plugin/client/pdfFit.ts` | 260 | 21 | 16 | ks-dsh-plugin — client/pdfFit.ts (2026-09-09，规则三次修订，末次 2026-09-17) |
| `plugin/src/settings.js` | 236 | 3 | 9 | — |
| `plugin/client/ksEvidence.ts` | 230 | 8 | 8 | ks-dsh-plugin — client/ksEvidence.ts |
| `plugin/client/pdfPanel.ts` | 189 | 13 | 17 | ks-dsh-plugin — client/pdfPanel.ts (2026-09-09) |
| `plugin/src/docimage.js` | 172 | 3 | 5 | — |
| `plugin/client/KsScopeChip.tsx` | 155 | 2 | 1 | ks-dsh-plugin — client/KsScopeChip.tsx (2026-10 收藏目录) |
| `plugin/src/route_util.js` | 154 | 6 | 6 | — |
| `plugin/client/KsEvidenceHost.tsx` | 144 | 4 | 2 | ks-dsh-plugin — client/KsEvidenceHost.tsx  (2026-09-16 官方 sidebar 迁移) |
| `plugin/src/trust.js` | 135 | 7 | 8 | — |
| `plugin/client/ksPrefs.ts` | 111 | 7 | 10 | ks-dsh-plugin — client/ksPrefs.ts  (2026-09-16 官方 sidebar 迁移) |
| `plugin/client/ksSearchSyntax.ts` | 108 | 3 | 4 | ks-dsh-plugin — client/ksSearchSyntax.ts |
| `plugin/src/trim.js` | 104 | 5 | 7 | — |
| `plugin/client/ks-evidence-props.ts` | 87 | 6 | 0 | ks-dsh-plugin — client/ks-evidence-props.ts |
| `plugin/client/pdf-configure.ts` | 71 | 3 | 3 | ks-dsh-plugin — client/pdf-configure.ts |
| `plugin/src/tool-details.js` | 71 | 2 | 4 | — |
| `plugin/client/KsArrowOverlay.tsx` | 70 | 6 | 7 | ks-dsh-plugin — client/KsArrowOverlay.tsx |
| `plugin/src/turn.js` | 65 | 3 | 5 | — |
| `plugin/client/KsKnowledgeGuide.tsx` | 63 | 1 | 1 | ks-dsh-plugin — client/KsKnowledgeGuide.tsx |
| `plugin/client/kbListUi.tsx` | 56 | 3 | 2 | ks-dsh-plugin — client/kbListUi.tsx |
| `plugin/client/KsPdfGuideIcon.tsx` | 50 | 1 | 1 | ks-dsh-plugin — client/KsPdfGuideIcon.tsx |
| `plugin/client/KsKnowledgeGuideIcon.tsx` | 45 | 1 | 1 | ks-dsh-plugin — client/KsKnowledgeGuideIcon.tsx |
| `plugin/client/KsAnchorWarn.tsx` | 44 | 3 | 3 | ks-dsh-plugin — client/KsAnchorWarn.tsx |
## 三之二、与「真 AST」对照（**两份各有盲区，不选边**）

仓库根已有 `typescript@5.9.3`，用它建真 AST 抽了一遍（`scripts/survey/09-web-ast.cjs`）。

| 口径 | 文件 | 导出 | 声明 |
|---|---:|---:|---:|
| **AST**（`ts.createSourceFile`） | 50 | **592** | **1139** |
| 正则（本节上表） | 50 | 629 | 754 |

**差异说明（不判断谁对）**：

| 现象 | 原因 |
|---|---|
| AST 导出数**少** 37 | AST 只走**顶层语句**；`declare module '…' { export … }` 里的导出不在顶层 ⇒ 没进去 |
| AST 声明数**多** 385 | 正则只认 `function/const/class` 三种，**漏掉 `interface` / `type` / `enum`** |

导出数差 ≥3 的文件（AST / 正则 / 文件）：

- 0 / 36 / `plugin/client/ksHostPrimitives.d.ts`


## 四、每个文件导出了什么（逐个列）

### `plugin/client/KsAnchorWarn.tsx`

`KS_WARN_STYLE`、`KsAnchorWarn`、`ksWarnCssText`

### `plugin/client/KsArrowOverlay.tsx`

`KS_ARROW_SVG`、`KS_ARROW_SVG_SIBLING`、`KS_SIBLING_OPACITY`、`KsArrowOverlay`、`KsSiblingArrowsOverlay`、`arrowBackground`

### `plugin/client/KsBookmarksTab.tsx`

`KsBookmarkJump`、`KsBookmarksView`、`KsBookmarksViewProps`

### `plugin/client/KsCapabilityPage.tsx`

`KsCapabilityPage`、`KsEgressPage`、`KsFixPage`、`KsGapPage`、`KsOfficeRow`、`OFFICE_ITEMS`、`OfficeItem`

### `plugin/client/KsChannelsPanel.tsx`

`KsChannelsPanel`、`KsChannelsPanelProps`、`ORG_KIND_LABEL`、`buildChannelFixPrompt`、`copyTextToClipboard`、`describeWhen`、`filterChannels`、`generateNewsLine`、`groupRowsByOrgKind`、`groupRowsBySite`、`needsAttention`、`parseSegments`、`sortChannels`

### `plugin/client/KsDocTextView.tsx`

`KsDocTextView`、`KsDocTextViewProps`、`sanitizeDocHtml`

### `plugin/client/KsEvidenceHost.tsx`

`KsEvidenceHost`、`KsEvidenceHostInjected`、`KsEvidenceHostProps`、`KsEvidenceHostRuntime`

### `plugin/client/KsEvidenceTab.tsx`

`KsEvidenceTab`

### `plugin/client/KsFilesTab.tsx`

`KsFilesView`、`KsFilesViewProps`、`countDocs`

### `plugin/client/KsIngestPanel.tsx`

`KsIngestPanel`、`KsIngestPanelProps`

### `plugin/client/KsKnowledgeGuide.tsx`

`KsKnowledgeGuide`

### `plugin/client/KsKnowledgeGuideIcon.tsx`

`KsKnowledgeGuideIcon`

### `plugin/client/KsKnowledgePage.tsx`

`KB_PAGE_SEARCH`、`KsKnowledgePage`

### `plugin/client/KsMaterialsPanel.tsx`

`AnchorMark`、`AnchorNoteLine`、`DraftAction`、`DraftFlow`、`KsMaterialsPanel`、`KsMaterialsPanelProps`、`canApplyDraft`、`cancelApplyDraft`、`confirmApplyDraft`、`deliverableKind`、`draftArrived`、`draftReducer`、`emptyDraftFlow`、`folderOf`、`requestApplyDraft`、`statusDisablesReverify`、`userTypedConclusion`

### `plugin/client/KsPdfGuideIcon.tsx`

`KsPdfGuideIcon`

### `plugin/client/KsScopeChip.tsx`

`KsScopeChip`、`KsScopeChipProps`

### `plugin/client/KsSettingsSection.tsx`

`KS_SETTINGS_PREFS_KEY`、`KS_SHOW_ARROW_KEY`、`KsAnnounceSourcesSection`、`KsEvidenceNavPort`、`KsInspectionPanel`、`KsSettingsSection`、`KsSettingsSectionInjected`

### `plugin/client/KsTurnTab.tsx`

`KsTurnEmptyState`、`KsTurnEvidenceGroup`、`KsTurnEvidenceItem`、`KsTurnEvidenceRow`、`KsTurnInjected`、`KsTurnModeChip`、`KsTurnRecord`、`KsTurnTab`、`KsTurnTabProps`、`KsTurnTabRuntime`、`clauseOrderKey`、`compareClauseOrder`、`groupTurnEvidence`、`siblingEvidenceOf`、`snippetCarriesClauseNo`、`turnEvidenceHref`

### `plugin/client/api.ts`

`BatchDeleteResult`、`BboxSpan`、`ClauseMeta`、`DOC_IMAGE_NOT_FOUND`、`DocBookmark`、`DocImageResult`、`EngineAuthError`、`EngineSession`、`FetchBboxResult`、`FetchDocImageOutcome`、`InspectionHttpError`、`KsAnnounceIngestItem`、`KsAnnounceIngestPending`、`KsAnnounceIngestResult`、`KsAnnounceLast`、`KsAnnounceLastIngest`、`KsAnnouncePerSource`、`KsAnnounceRecentItem`、`KsAnnounceSource`、`KsAnnounceSummary`、`KsAnswerResult`、`KsAnswerScope`、`KsApiChannel`、`KsApiChannelStatus`、`KsApiConfigStatus`、`KsBookmark`、`KsBookmarkFolder`、`KsBulkIngestStatus`、`KsCategoryNode`、`KsChangeSignalItem`、`KsChangeSignalsResult`、`KsChannelList`、`KsChannelProbeResult`、`KsChannelRecord`、`KsChannelSummary`、`KsChannelTestCase`、`KsChatMode`、`KsClause`、`KsClausePatch`、`KsCollectOutcome`、`KsDoc`、`KsDocClause`、`KsEffectColors`、`KsEffectDoc`、`KsEffectDocs`、`KsEffectReport`、`KsEffectTreeNode`、`KsEffectWindow`、`KsEgressAudit`、`KsEgressAuditRecord`、`KsFolderDocNode`、`KsFolderTreeFolder`、`KsGapResult`、`KsIngestBatch`、`KsIngestBatchRow`、`KsIngestClauseSample`、`KsIngestInbox`、`KsIngestInboxFile`、`KsIngestJobView`、`KsIngestReport`

### `plugin/client/entry.ts`

`KS_SETTINGS_TAB_ID`、`apply`、`inject`

### `plugin/client/kbListUi.tsx`

`KbListCol`、`KsCrumb`、`KsListHead`

### `plugin/client/ks-evidence-props.ts`

`KsEvidenceComponent`、`KsEvidencePrefs`、`KsEvidenceProps`、`KsEvidenceTabRecord`、`KsPanelWidthPort`、`KsSessionScope`

### `plugin/client/ksEvidence.ts`

`EVIDENCE_ORIGIN`、`EVIDENCE_PATH`、`KsEvidence`、`KsEvidenceSibling`、`evidenceUrlOf`、`isBbox`、`isKsEvidenceUrl`、`parseEvidence`

### `plugin/client/ksGuideStyles.ts`

`KS_STYLES`、`ensureKsStyles`

### `plugin/client/ksHostPrimitives.d.ts`

`Button`、`Checkbox`、`DshButtonProps`、`DshButtonVariant`、`DshCheckboxProps`、`DshIconProps`、`DshMenuItem`、`DshMenuProps`、`DshModalProps`、`DshSwitchProps`、`DshTagTone`、`IconChecklistOutlineRegular`、`IconChevronDownOutlineRegular`、`IconChevronLeftOutlineRegular`、`IconChevronRightOutlineRegular`、`IconClockOutlineRegular`、`IconCloseOutlineRegular`、`IconEllipsisOutlineRegular`、`IconFolderOpenOutlineMedium`、`IconFolderOpenOutlineRegular`、`IconInfoOutlineRegular`、`IconListPenOutlineRegular`、`IconPlanOutlineRegular`、`IconPlusOutlineRegular`、`IconQuestionOutlineRegular`、`IconRefreshOutlineRegular`、`IconSearchOutlineRegular`、`IconTrashOutlineRegular`、`IconWarningOutlineRegular`、`Input`、`Menu`、`Modal`、`Pill`、`Switch`、`Tag`、`Toast`

### `plugin/client/ksPrefs.ts`

`KS_PREFS_DEFAULT`、`KS_SETTINGS_PREFS_KEY`、`KS_SHOW_ARROW_KEY`、`KsPrefs`、`getPrefsSnapshot`、`subscribePrefs`、`updatePrefs`

### `plugin/client/ksSearchSyntax.ts`

`KsQuery`、`describeKsQuery`、`parseKsQuery`

### `plugin/client/ksSidebar.ts`

`KS_EVIDENCE_ADDRESS`、`KS_EVIDENCE_IMPL_ID`、`KS_EVIDENCE_KIND`、`KS_EVIDENCE_RESOURCE_PREFIX`、`KS_GUIDE_ORDER_PDF`、`KS_KB_ADDRESS`、`KS_KB_IMPL_ID`、`KS_KB_KIND`、`KS_KB_RESOURCE_PREFIX`、`KS_TURN_ADDRESS`、`KS_TURN_IMPL_ID`、`KS_TURN_KIND`、`KS_TURN_RESOURCE_PREFIX`、`KsEvidenceNavParams`、`KsGuideCardProps`、`KsGuideEntry`、`KsIconProps`、`KsKbInjected`、`KsKbNavParams`、`KsKbPage`、`KsPaneBodyProps`、`KsSidebarRight`、`KsTabDefinition`、`KsTabRegistry`、`UseKsTabInfo`、`evidenceTabTitle`、`isKsEvidenceResource`、`isKsKbResource`、`isKsTurnResource`、`ksEvidenceDefinition`、`ksGuideEntryDescription`、`ksGuideEntryTitle`、`ksKbDefinition`、`ksKbTabTitle`、`ksTurnDefinition`、`ksTurnTabTitle`、`toNavParams`

### `plugin/client/pdf-configure.ts`

`PDF_WASM_DIR`、`PDF_WORKER_PATH`、`configurePdfWorker`

### `plugin/client/pdfFit.ts`

`FitInput`、`FitResult`、`MANUAL_MAX_PERCENT`、`MANUAL_MIN_PERCENT`、`MAX_BACKING_PIXELS`、`MAX_SCALE`、`MIN_SCALE`、`PAGE_PADDING`、`ZOOM_AUTO`、`ZOOM_PRESET_PERCENTS`、`ZOOM_SLIDER_STEP`、`ZoomSource`、`ZoomState`、`ZoomView`、`backingStoreDpr`、`clampManualPercent`、`fitPageScale`、`isOnSliderGrid`、`zoomForAutoFit`、`zoomForManual`、`zoomScale`

### `plugin/client/pdfPanel.ts`

`MIN_CONVERSATION_WIDTH`、`PANEL_MAX_WIDTH`、`PANEL_MIN_WIDTH`、`PANEL_WIDEN_RATIO`、`PanelWidthPort`、`TOC_COLUMN_WIDTH`、`TOC_PUSH_MAX_WIDTH`、`growPanelForToc`、`hasPendingPanelRestore`、`pdfPanelTargetWidth`、`restorePanelAfterPdf`、`shrinkPanelAfterToc`、`widenPanelForPdf`

### `plugin/src/announce.js`

`KS_ANNOUNCE_AUTO_INGEST_PATH`、`KS_ANNOUNCE_CHANGE_SIGNALS_PATH`、`KS_ANNOUNCE_EXPORT_PATH`、`KS_ANNOUNCE_INGEST_PATH`、`KS_ANNOUNCE_INGEST_PENDING_PATH`、`KS_ANNOUNCE_SCAN_PATH`、`KS_ANNOUNCE_SOURCES_PATH`、`KS_ANNOUNCE_SUMMARY_PATH`、`KS_ANNOUNCE_TRIAGE_PATH`、`announceFilePath`、`announceStartupCheck`、`registerKsAnnounceRoutes`、`triggerAfterInspection`

### `plugin/src/channels.js`

`KS_CHANNELS_ITEM_PREFIX`、`KS_CHANNELS_PATH`、`KS_CHANNELS_PROBE_PATH`、`registerKsChannelsRoutes`

### `plugin/src/chatmode.js`

`BOOKMARKS_COMMAND`、`FORENSIC_BOOKMARKS_PROMPT`、`FORENSIC_COMMAND`、`FORENSIC_FOLDER_PROMPT`、`FORENSIC_MATERIALS_PROMPT`、`FORENSIC_PROMPT`、`FORENSIC_SECTION_NAME`、`FORENSIC_SECTION_ORDER`、`KS_CHAT_MODE_PATH`、`MATERIALS_COMMAND`、`MAX_SESSIONS`、`__resetChatModeForTests`、`__sweepArtifactsForTests`、`__writeStateFileAsPeerForTests`、`allowStateReload`、`chatModeFilePath`、`effectiveChatMode`、`ensureLoaded`、`forensicPromptFor`、`getMode`、`hasActiveForensicSessions`、`makeChatModeCommands`、`makeChatModeSection`、`normalizeSessionId`、`registerKsChatModeCommands`、`registerKsChatModeRoutes`、`setChatModeLogger`、`setMode`、`stateStatus`

### `plugin/src/collect.js`

`MAX_COLLECT_PER_SESSION`、`makeCollectTool`

### `plugin/src/compliance-sentry.js`

`COMPLIANCE_SECTION_NAME`、`COMPLIANCE_SECTION_ORDER`、`COMPLIANCE_SKILL_BODY`、`COMPLIANCE_TTL_MS`、`KS_COMPLIANCE_SENTRY`、`STD_NO_PREFIXES`、`buildComplianceNextStep`、`buildComplianceSection`、`collectAskReason`、`complianceNextStepMessage`、`extractL1`、`isComplianceTriggered`、`markComplianceTriggered`、`matchComplianceSentry`、`registerComplianceAskGate`、`registerKsComplianceRoutes`

### `plugin/src/docimage.js`

`KS_DOC_IMAGE_PATH`、`parseDocImagePath`、`registerKsDocImageRoutes`

### `plugin/src/engine.js`

`DEFAULT_PYTHON`、`ENGINE_ROOT`、`EngineManager`、`HEALTH_PATH`、`KS_ANSWER_PATH`、`MODULE_ARG`、`apiGet`、`apiGetBytes`、`apiPost`、`combineSignals`、`dataRoot`、`describeTransportFailure`、`ensureMineruConfig`、`findEngineRoot`、`healVenvHome`、`isProcessAlive`、`killPid`、`modelEnv`、`modelsRoot`、`originUrl`、`parseSession`、`readSessionFile`、`resolvePythonPath`、`sessionFilePath`

### `plugin/src/index.js`

`CONFIG_KEYS`、`Config`、`KS_BBOX_PATH`、`KS_EVIDENCE_ORIGIN`、`KS_EVIDENCE_PATH`、`KS_PDF_WASM_PATH`、`KS_PDF_WORKER_PATH`、`KS_SESSION_PATH`、`apply`、`evidenceAnchor`、`inject`、`makeAnswerTool`、`makeEffectReportTool`、`makePingTool`、`makeResolveTool`、`name`、`trimAnswer`、`trimVerification`

### `plugin/src/ingest.js`

`KS_INGEST_BATCH_PATH`、`KS_INGEST_INBOX_DEFAULT_PATH`、`KS_INGEST_INBOX_PATH`、`KS_INGEST_JOB_ABORT_PREFIX`、`KS_INGEST_JOB_START_PATH`、`KS_INGEST_JOB_STATUS_PREFIX`、`KS_INGEST_PREVIEW_PATH`、`defaultInboxDir`、`ensureInboxDir`、`ingestJobFilePath`、`ingestJobStartupCheck`、`registerKsIngestRoutes`

### `plugin/src/inspection.js`

`KS_INSPECTION_EXPORT_PATH`、`KS_INSPECTION_RUN_PATH`、`KS_INSPECTION_SETTINGS_PATH`、`KS_INSPECTION_SUMMARY_PATH`、`__resetInspectionForTests`、`byClassEmpty`、`emptyByClass`、`inspectionFilePath`、`inspectionStartupCheck`、`reduceOneClassRow`、`registerKsInspectionRoutes`、`sanitizeLast`

### `plugin/src/materials.js`

`makeMaterialsTool`

### `plugin/src/materials_routes.js`

`KS_MATERIALS_PATH`、`KS_MATERIALS_PATHS`、`REVIEW_DECISIONS`、`registerKsMaterialsRoutes`

### `plugin/src/report.js`

`KS_REPORT_DOCS_PATH`、`KS_REPORT_DRAFT_PATH`、`KS_REPORT_EFFECT_PATH`、`KS_REPORT_EXPORT_PATH`、`KS_REPORT_RESEARCH_PATH`、`registerKsReportRoutes`

### `plugin/src/route_util.js`

`ROUTE_BODY_CAP`、`errorBody`、`jsonResponse`、`mapProbe`、`pickQuery`、`readJsonBody`

### `plugin/src/settings.js`

`KS_API_CONFIG_PATH`、`KS_API_CONFIG_TEST_PATH`、`registerKsSettingsRoutes`

### `plugin/src/tool-details.js`

`KS_ANSWER_DETAIL`、`firstUseReceipt`

### `plugin/src/trim.js`

`REASON_CAP`、`VERIFY_LIST_CAP`、`shortList`、`trimUnsupportedContext`、`trimVerification`

### `plugin/src/trust.js`

`LOOPBACK_HOSTS`、`guardRequest`、`guardRoute`、`guardWebServer`、`parseAuthority`、`requireJsonBody`、`trustedNames`

### `plugin/src/turn.js`

`KS_TURN_LAST_PATH`、`recordKsTurn`、`registerKsTurnRoutes`
