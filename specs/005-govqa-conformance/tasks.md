---
description: "Task list for gov-qa 合规收口与目标达成"
---

# Tasks: gov-qa 合规收口与目标达成

**Input**: Design documents from `specs/005-govqa-conformance/`

**Prerequisites**: spec.md ✅ / plan.md ✅

**Tests**: 本特性**包含测试任务** —— 核心目标之一就是"判据有牙"（宪法 III 证据优于断言）。

**Organization**: 按 Phase 分组。Phase 1 是 MVP（其余一切的前提）。

## Format: `[ID] [P?] [Phase] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- 所有路径相对仓库根 `D:/AI/work space/zcode/`

## 硬约束（每个任务都适用）

1. **还原源码一律用 `git checkout -- <file>`**，不用 `write_text`
   （`core.autocrlf=true`，我在诊断阶段实测 `write_text` 会改行尾）。
2. **机器可读输出走 `common.ascii_kv`**（GBK 控制台）。
3. **绝不 `git add tools/gov-qa`**（整目录）—— 另一 Agent 在并行写。
4. **不碰 `data/gx-igi-*.jsonl`**（另一 Agent 正在写）。
5. **门禁一次只跑一个**；退出码 3 = 有人在跑，**不是失败**。

---

## Phase 0: 安全前置（阻塞性 —— 不完成则后续所有写入都可能与并发写打架）

- [ ] **T000** 确认并停止另一 Agent 的 `igi-chunked.py`（PID 15016 / 47408）。
      **停之前先请业主确认**（那是别人的采集任务）；若不能停，则登记"该进程仍在跑"，
      并确保本特性**只改代码不改 `gx-igi-*` 数据**。
- [ ] **T001** 清掉现场死锁 `tools/gov-qa/state/.poll.lock`（实测 pid 31704 已不存在）。
      清前打印锁内容留证；清后跑一次 `poll.py --quiet` 确认不再恒返 3。
- [ ] **T002** [P] 在 `.gitignore` 排除 `tools/gov-qa/state/.poll.lock`（spec 004 的 T001 从未做）。
- [ ] **T003** [P] 把唯一闸门纳入版本控制：`D:/AI/output/check.sh` + `GOAL.md`
      **字节级搬运**到 `tools/gov-qa/gate/`（长文档禁手抄），并登记原位置关系。
- [ ] **T004** 提交当前数据现状作为可回退基线（`git add` 只加 gov-qa 自己的文件）。

---

## Phase 1: 纳入本仓门禁（Priority: P1）🎯 MVP

**目标**：`run-gates.ps1` 跑得到 gov-qa 的测试与质量判据，坏了当场报红。

- [ ] **T101** 在 `scripts/run-gates.ps1` 的 `-Full` 分支**追加**一步
      `Add-Step 'gov-qa 测试' $py @('-m','pytest','tools/gov-qa/tests','-q',...)`。
      **追加在现有步骤之后**，不改动任何既有步骤。
- [ ] **T102** [P] 新建 `tools/gov-qa/recon/gate-quality.py`：
      **四项数据质量判据的唯一数字源**，输出纯 ASCII `KEY=VALUE`：
      - `EMPTY_ANSWER_RATE`（答复为空的比例）+ 按源的清单
      - `CONTENT_DUPS`（内容重复：同 `(question,answer)` 归一化后多 id）
      - `TIME_INVERTED`（`answered_at < asked_at` 计数）
      - `LABEL_COVERAGE`（**只认 `msg_type_norm`**，与 `health.py` 同口径）
      退出码：0 全过 / 1 有超阈值项 / 2 执行失败。
- [ ] **T103** 把 `gate-quality.py` 接进 `run-gates.ps1`（在 T101 之后）。
- [ ] **T104** 堵 `ADAPTERS_ERR` 假绿：`recon/audit-coverage.py --gate` 在
      `adapters` 导入失败时**不得**输出 `EMPTY=0`；`check.sh` 加一条
      "无 `ADAPTERS_ERR` 且 `ADAPTERS>0`" 的判据。
      **变异验证**：注入 `ImportError` ⇒ 门禁必红（现状假绿，我已实测）。
- [ ] **T105** 统一标签覆盖率口径：把 `health.py` 与 `label-coverage.py` 的
      覆盖率计算抽到**一个函数**（`common.py`），两处调用同源。
      **验收**：两工具输出同一个数（现 99.2 vs 100.0）。
- [ ] **T106** [P] 修 `coverage-report.py` 的退出码自相矛盾：
      `--quiet` 报 `CITY_NONE=0` rc=0，而 `--missing-cities` 报 182 市零记录 rc=1。
      **验收**：同一数据两入口给出一致结论。
- [ ] **T107** [P] 修 `common.human()` 的兜底**自身抛 `UnicodeEncodeError`**
      （GBK strict 下 `human('✅…')` 崩在 `\ufffd`）。参照 `harvest.py::_safe()` 的写法。
- [ ] **T108** [P] 修 `recon/audit-coverage.py` 三个子命令的 GBK 崩溃
      （`--answers` / `--targets` / `--fields`，实测 rc=1）：emoji/中文走 `ascii_kv` 或 `_safe`。
- [ ] **T109** [P] `poll.py --quiet` 的逐通道行绕过 `ascii_kv`，且有一处死代码
      `ascii_kv({}) if False else None` —— 一并修掉。
- [ ] **T110** 重记 `scripts/gates-baseline.json` 的 pytest 基线（只涨不跌）。
- [ ] **T111** **变异验证 T102 的四项判据**：逐项改坏 ⇒ **4/4 必红**（SC-003）。
- [ ] **T112** 跑 `run-gates.ps1 -Full`，退出码 0，且输出含 gov-qa 步骤（SC-001）。
      记录总耗时，核对 SC-004（≤ 现状 +60 秒）。
- [ ] **T113** 小提交 Phase 1。

---

## Phase 2: 修静默数据缺陷（Priority: P1）

**目标**：把"字段非空但内容是垃圾"的记录清出语料，并钉住防回退。

- [ ] **T201** **`xz-lasa` 1,030 条空答复**（实测 1030/1030 = 100%）：
      查 `adapters/xz_lasa.py` 取的字段与接口实际返回是否不符。
      **处置二选一**：修好重采 / 该源移出并登记原因。**不得留着不处置。**
- [ ] **T202** [P] **`ln-8890` 7,807 条时间倒置**（实测 `both=7807 inverted=7807`）：
      查字段映射（注意 `ln-8890-kb` 同族 13,941 条**零倒置**，是绝好的对照组）。
      给出根因证据；修好或登记"该源时间字段不可用"。
- [ ] **T203** **8,462 条内容重复**（5,642 组，id 不同）：
      用 `recon/dedup-data.py` 类工具去重；**去重前先 commit 现状**。
      登记修复前后确切条数（SC-006）。
- [ ] **T204** [P] **3,445 条答复截断**：模块自带 `--answers` 判据得 13 源 / 3,167 条，
      独立脚本得 3,445 条。**先统一口径**，再逐源查（`sd-yantai` 2,372 为首）。
- [ ] **T205** [P] **153 条 `question` 为空/字面 `null`** + **6,722 条 ≤5 字符**：
      查是否同一根因（`shannan-igi-*` 126 条为首）。
- [ ] **T206** [P] 跨源重复 3,945 条（湖北三源 98% 重叠、`gs-zhangye-23`↔`zhangye-igi-23`）：
      判定是"站方重复公示"还是"同平台被两个 key 采了"，给出证据后处置。
- [ ] **T207** [P] `extra.city` 混入**个人详细住址**（实测 ≥20 条，如
      "宁夏西吉县紫薇嘉园1号楼1单元702"）—— 合规风险，登记并处置。
- [ ] **T208** 为 Phase 2 的每处修复补测试（改坏 ⇒ 必红），并跑 T102 判据确认转绿。
- [ ] **T209** 小提交 Phase 2。

---

## Phase 3: M1 补齐 —— 345 个通道都有"自报总量"（Priority: P2）

**现状**：`recon/targets.json` 只有 **37/345 = 10.7%** 的适配器登记了自报总量。

- [ ] **T301** 写脚本从各适配器/接口枚举自报总量，补齐 `targets.json`。
      **每个新增登记必须带来源**（接口字段 / 枚举 / 实测），无来源的写"该站不提供总量"。
      **目标 ≥300/345 = 87%**（SC-007）。
- [ ] **T302** [P] 修 `audit-coverage.py --targets` 的 GBK 崩溃（与 T108 同族）。
- [ ] **T303** 修 `_should_stop` 的**水位只写不读**（独立复核 Finding 1，我已复核确认）：
      `page` / `since` 型水位当前是摆设——手改水位为 999999，`pages requested` 仍是 `[1]`。
      要么真正实现读取，要么在契约里明确降级并登记。
- [ ] **T304** 在**真数据**上验证 spec 004 的 US1：`poll.py --channel <key>` 跑两次，
      第二次新增 0 且不重复（不只是单测）。
- [ ] **T305** 小提交 Phase 3。

---

## Phase 4: M2 存量推进（Priority: P3，长周期）

- [ ] **T401** 按 `audit-coverage.py --targets` 挑完成度最低且有效目标 ≥1000 的源补采。
- [ ] **T402** 每轮收工记录：新增条数 / 涉及源 / 耗时（机器可读）。
- [ ] **T403** 明确登记"本轮未做完的部分"与完成度（SC 要求诚实状态）。

---

## Phase 5: M3 标签人工抽检（Priority: P3，需业主）

- [ ] **T501** 现状：`label-check-200.csv` 191 行、`label_ok` **已填 0 行**；
      67.8% 的标签是 SVM 猜的。**准确率只能人工核，agent 无法替代。**
      ⇒ 把样本重新导出到业主能直接填的位置，并**明确请业主抽检**。
- [ ] **T502** 修 `test_label_accuracy_refuses_without_human_check` 的"或"断言
      （`"%" not in out or "未做" in out`，塞入假百分比仍 GREEN）。

---

## Phase 6: M4 覆盖面推进（Priority: P3，长周期）

- [ ] **T601** 按修正后的口径推进零记录市（现 182 个）。
      **注意**：交接文档 §11 的"5 个 405 市"线索**已被作者自己的 POST 实测推翻**
      （东莞/韶关/珠海 404，中山/河源 200 但 `total=0`；同轮对照汕尾 `total=27`）。
      ⇒ **不要按 §11 投入**，改按实测重新定位。
- [ ] **T602** 修 24 个通道（35,260 条，含 `nat-tax` 13,943）不在销号表内
      （7 个自治州 region 提取失败 + 14 个国家级落 `other` 桶而 CLI 只渲染省/市）。
- [ ] **T603** 统一 `CITY_TOTAL=334` 与契约/`regions` docstring 的 333
      （差的是省直辖县级市"济源市"），并修 `test_known_cities_covers_334` 钉死的错口径。

---

## Phase 7: 独立复核 + 登记 + 文档更正（Priority: P1）

- [ ] **T701** **更正交接文档 §11**（就地更正、保留错话 + 更正在后）：
      "405 = 端点存在"已被作者自己 07:19 的 POST 实测推翻。
- [ ] **T702** [P] 全仓 grep 更正 README 两处过时说法
      （"230 条 nat-mohurd 空问题"实测 0 条；"巴中 192 条截断"实测 548 条答复全不同）。
      **宪法 V：自我更正要 grep 全仓。**
- [ ] **T703** 修 `tasks.md`（spec 004）57 项全未勾选与"全部落地"的冲突：
      逐项核对后如实勾选，未落地的标出。
- [ ] **T704** 把诊断 + 复核结论登记进 `docs/DEVELOPMENT-HISTORY.md`（归属层）。
- [ ] **T705** 冻 tag + 派**独立复核**（提取树上验，真拷贝依赖，报告字节级入库）。
      **这是本模块 297 个提交以来的第一次独立复核。**
- [ ] **T706** 收口复核打回的缺陷；按纪律"打回的说法必须就地更正并留痕"。
- [ ] **T707** `git gc` 回收 1.95 GB 孤儿对象（`.git/objects/d5/tmp_obj_DlRsgf`）。
      **动 git 前先确认无并发提交。**
- [ ] **T708** 跑 `run-gates.ps1 -Full` 收尾，贴输出。
- [ ] **T709** 更新 `D:/AI/output/GOAL.md` 基线 + 写收工交接。

---

## Dependencies

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4/5/6 ──► Phase 7
                │                       │
                └── T102 是 T103/T111/T112 的前置
                └── T105 是 T106 的前置（口径统一）
                └── T203/T204/T205 是 T208 的前置
```

- **Phase 1 是 MVP**：不完成它，Phase 2 之后的修复都无法防回退。
- **Phase 7 依赖全部**：复核必须在冻结提交上做。

## 需要业主裁决（不阻塞施工）

1. **停不停另一 Agent 的 `igi-chunked.py`**（T000）—— 那是别人的采集任务。
2. **35 万条非合规问答数据如何处置**（删 / 留 / 隔离）—— 本特性只做索引与判据，**不删数据**。
3. **M2/M4 是否转向"公告发布栏目"** —— 用户已收窄口径到法规/国标公告，
   但"完成这个模块开始设定的目标"字面指 M1–M4 原目标。**本计划按原目标推进**，
   口径冲突登记为判据项（T102 的 `LABEL_COVERAGE` 同族，FR-009）。
4. **M3 标签准确率人工抽检**（T501）—— 只能人做。

## 汇总

| Phase | 任务数 | 可完成 |
|---|---|---|
| 0 安全前置 | 5 | ✅ |
| 1 纳入门禁（MVP） | 13 | ✅ |
| 2 修静默缺陷 | 9 | ✅ |
| 3 M1 补齐 | 5 | ✅ |
| 4 M2 存量 | 3 | ⚠ 推进 |
| 5 M3 标签 | 2 | ⚠ 需业主 |
| 6 M4 覆盖面 | 3 | ⚠ 推进 |
| 7 复核与登记 | 9 | ✅ |
| **合计** | **49** | |
