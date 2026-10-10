# Tasks: UI 精修（spec 007）

**Feature**: `007-ui-polish` ｜ **Spec**: [spec.md](./spec.md) ｜ **Plan**: [plan.md](./plan.md)

**Created**: 2026-10-10

---

## 阶段 0：取证（已完成，登记）

- [x] **T001** 真机审查设置面（`browser_*`，真宿主 + 真主题，两档窗口宽）
  —— 证据：`var/tmp/ui-shots/realhost/*.png`（`read_image` 自己看过）。
  - **判据**：截图存在且我看过；看到的事实写进 `research.md`。
  - **结果**：看到 D3（Base URL 被裁）与"各类目默认收起 ✅"。

- [x] **T002** token 归属审计（按**源码归属**判，不按渲染产物判）
  —— 工具 `var/tmp/token-ownership.py`。
  - **判据**：KS 源码引用的 `--dsw-*` 必须 ⊆ 官方主题 403 个定义；`--ks-*` 必须 ⊆ `ksGuideStyles.ts` 定义。
  - **结果**：D1（`--ks-radius`）+ D2（`--ks-font-mono`）；另两个产物里的缺口经核实**属别的插件**，不是 KS 的。

- [x] **T003** 官方规范逐条对照
  —— `D:\AI\DSH\deepseek-harness\docs\web-styling.md` + `docs/ui-radius.md`。
  - **判据**：每条要求给出"KS 现状 + 判"。
  - **结果**：见 spec §三（4 条 ✅、1 条 ❌、1 条 🟡）。

## 阶段 1：D1 + D2 —— token 缺口

- [x] **T010** `ksGuideStyles.ts` 补 `--ks-radius` 定义，**值必须落回官方 token**
  —— 实测落地为 `--ks-radius:var(--dsw-radius-md)`（官方 `ui-radius.md`：凸舌是 H32 标准控件档 ⇒ R12；
     **不引入** 10/14/18/24 这种本地值）。
  - **判据**：定义存在。✅
  - **变异**：删掉该定义 ⇒ T012 的判据**精确红在那一条**。✅

- [x] **T011** `ksGuideStyles.ts` 补 `--ks-font-mono` 定义
  —— 实测落地为 `--ks-font-mono:var(--ds-font-family-code)`（**落回官方 token**）。
     ⚠ 为什么不用裸 `monospace` 兜底：官方 `ui-theme/src/styles/base.css` 第 4 行逐字写着
     「Code font stack deliberately omits a bare monospace tail (Windows CJK falls back to SimSun otherwise)」。
     顺带把本仓另外 **3 处**硬写 `ui-monospace,Consolas,monospace` 的（`.ks-kb-no` / `.ks-field-v-mono` /
     `.ks-ing-mono`）一并改走它 —— 同一件事不再有第二份写法。
  - **判据**：定义存在。✅
  - **变异**：删掉该定义 ⇒ T012 判据**精确红在那一条**。✅

- [x] **T012** 给 D1/D2 立**机械判据**，进 `smoke-ui-scale.mjs`（已在门禁链里）
  —— 从 `ksGuideStyles.ts` 抠出所有 `var(--ks-*)` 引用集合与 `--ks-*:` 定义集合，
  要求 **引用 ⊆ 定义**；带兜底值的（`var(--x, y)`）**单独列出并放行**（它们是刻意兜底，不是缺陷）。
  - **判据**：原样件 PASS；删任一 token 定义 ⇒ FAIL 并点名缺的是谁。
  - **变异**：**逐条**做（删 `--ks-radius` / 删 `--ks-font-mono`），各红一次。
  - **⚠ 反向也要有牙**：把判据写成恒真（比如比对空集合）⇒ 必须能被"注入一个假缺口"打红。
  - **实测**：原样件 PASS（引用 48 个 / 定义 54 个 / **缺失 0**）；两条变异各红一次，还原后 sha256 逐字节一致。✅
  - ⚠ **踩坑留痕（本批踩了 4 次同一个坑）**：给这段加注释时**在模板字符串里写了反引号**，
    把 `KS_STYLES` 截断 ⇒ `:root` 块解析成 0 个、脚本报"剥除口径已与文件结构脱节"。
    `ui-render-shot.mjs` 的**注入脚本**（也在模板字符串里）同一个坑又踩了 3 次。
  - ✅ **收口核验（2026-10-10 14:1x，接手方独立复跑，不是转述上文）**：本任务原先**只勾了子项、
    主复选框一直没勾**，看上去像未完成。**我重跑了全部三个变异，结论：判据真的在、且真有牙。**
    | 变异 | 做法 | 实测读数 | exit |
    |---|---|---|---|
    | 原样件 | 不动 | `引用 48 个 / 缺失 0 个` | **0** |
    | 删 `--ks-radius` 定义（L75） | 删那一行 | `❌ --ks-radius（引用了但本文件没有定义）` | **1** |
    | 删 `--ks-font-mono` 定义（L65） | 删那一行 | `❌ --ks-font-mono`（并打印"带兜底、故放行 1 个"） | **1** |
    | **反向**：注入假缺口 | 把 `var(--ks-radius)` 改成 `var(--ks-nonexistent-token)` | `❌ --ks-nonexistent-token` | **1** |
    三次变异**都精确点名缺的是哪一个 token**（不是笼统报错）；**还原后 sha256 逐字节一致**。
    ⇒ **本条据实勾选**（证据是本轮实跑，非抄上文）。

## 阶段 2：D3 —— 表单溢出（有真机证据）

- [x] **T020** `KsSettingsSection.tsx` 的凭据表单修"说明读不全"
  —— ⚠ **修法不是挤布局**（第一版只加 `minWidth:0`，实测**不够**：600 宽下仍红）。
     正解 = placeholder 从 `Base URL（留空保持不变；输 "-" 恢复内置默认）` 缩短为 `Base URL（可留空）`
     （完整规则本来就由"改动时出现"的说明行承担；本轮顺手把"Base URL 清除后回到内置默认"补进那句，
     信息量不减）；同时给可收缩项加 `minWidth: 0`。
  - **约束**：改动**不得**落在 `AnnounceTriageSection` 区间内（禁碰区）。
    施工前 `grep -n "function AnnounceTriageSection"` 拿行号区间，施工后**再核一次**。
  - **判据**：T021 的真浏览器量点通过。

- [x] **T021** `ui-render-shot.mjs` 加 `settings` 页 + 量点 + Node 侧判
  —— 真浏览器量 `clipped`（canvas 量 placeholder 实宽 vs 框内可用宽）与 `overflow`；量不到即红。
  - **判据**：修复后 **400 / 600 / 1018 三档全 PASS**；把长 placeholder 改回 ⇒ **600 宽下红**
    （报 `文字实宽 266px > 框内可用 222px ⇒ 用户看到的是半截说明`）。✅
  - ⚠⚠ **第一版量错了对象（本批最重要的留痕）**：第一版量的是"输入框右缘是否越过所在行"，
    **变异打不红**（把修复改回去仍 PASS）—— 因为真机里的现象**不是**"容器溢出"，
    而是"**框太窄、说明被截断**"。改成量 `clipped` 后才抓住。**这是最该被复核的一条。**
  - **⚠ 不许进 `MATRIX`**（那会要求同批改 `EXPECTED_RUNS`，把 diff 扯到冻结清单上）；
    用单独命令量，并把命令写进 tasks 与文档。

## 阶段 3：四个主面逐态审查（留痕）

- [x] **T030** 用 `ui-render-shot` 把 kb / ingest / capabilities / materials 的交互态各渲一遍并看图
  —— 证据 `var/tmp/ui-shots/survey/`（四面各一张）与 `var/tmp/ui-shots/states/`（kb 的 10 个交互态）。
  - **结论**：四面板式成体系、无裁切；逐条写在 `docs/UI-BASELINE.md` §5aa 第四节。✅
  - **诚实边界**：**都是离屏**（没有宿主外壳），**不是真机**；真机只看到设置面。
  - ⚠ **`--interact kb-detail` 退出码 1**：已**机械证明是既有状态**——用冻结前的脚本
    （`git show c136363b:plugin/scripts/ui-render-shot.mjs`）跑同一场景，**同样红**；
    原因是该组合没在 `PAD_REQUIRED` 里声明期望元素（脚本按"声明了就必须判"的棘轮报红）。
    **不是本批的回归。**

- [x] **T031** 把本轮结论写进归属层
  —— `docs/UI-BASELINE.md` §5aa + `docs/DEVELOPMENT-HISTORY.md` §10.232。✅

## 阶段 4：收口

- [x] **T040** 重建交付产物 `plugin/client.js`（`node scripts/build-client.mjs`）
  - **判据**：`smoke-client-entry` 的"产物 ↔ 从源码现构建整份一致"断言 PASS。✅（205/205）

- [x] **T041** 跑门禁 —— **已完成（门禁锁释放后补跑）**
  - `tsc` exit 0 ｜ `smoke-client-entry` **205/205** ｜ `smoke-ui-scale` exit 0 ｜
    `ui-render-shot --page settings` 400/600/1018 三档全绿。✅
  - **`smoke-all` → 42/42 套全过 · exit 0**。✅
  - **`run-gates.ps1 -Full` → 10/10 步 · exit=0**（pytest 2854 passed / 0 failed / 2 skipped；棘轮通过）。✅
  - ⚠ 首次尝试时**门禁锁被并行线占用**（退出码 3 = "有人在跑"，按纪律**不并发**），
    等锁释放后补跑 —— **这是"不并发"纪律的一次实际执行**，不是漏跑。

- [x] **T042** 小提交 + 快照
  - 提交 `1ee35df0`（源码+判据+产物）、`a91b6d5b`（开发史）；快照 `step-367-ui-polish-spec007`。✅

- [x] **T043** 派独立复核（属必验类别：改了共享样式 + 新增判据）—— **两轮，都已收**
  - **第一轮**（冻结 `step-367-ui-polish-spec007` → `a91b6d5b`）：复核者只有只读工具，
    做了源码级分析，**发现我新增的两处判据有假绿**（R1 裹注释 / R2 宽度依赖 / R3 关键字覆盖不全）
    ⇒ 我逐条复现后修掉（`d79ec7c8`）。**它的分析原样存在 `var/tmp/verifier-readonly-analysis.md`。**
  - **第二轮**（冻结 `step-368-ui-polish-spec007-r2` → `d79ec7c8`，换 `worker` 角色）：
    报告 [VERIFY-REPORT-spec007-ui-polish](../../docs/verify-briefs/VERIFY-REPORT-spec007-ui-polish.md)，
    ⚠ **路径更正（2026-10-10）**：原文写 `verify-briefs/…`（相对本文件）⇒ 解析成
    `specs/007-ui-polish/verify-briefs/…`，**那个目录不存在**（实测断链）。
    报告实际在 **`docs/verify-briefs/`** ⇒ 从本文件出发是 `../../docs/verify-briefs/…`。
    （本仓其它 spec 引这份报告一律用**仓库根相对**写法 `docs/verify-briefs/…`，
    见 `specs/002/tasks.md:156`、`specs/003/tasks.md:193`；此处用相对写法以保持 Markdown 可点。）
    判定 **PASS —— R1/R2/R3 三条全部真堵住了、不是只堵举例**（R3 用**对照实验**实证）。
    另报 **P1 × 1 + P2 × 6** ⇒ 我修了 P1 与两条 P2（`94b1a4d8`）。
  - ⚠ **流程失误（我的，已留痕）**：第一轮先派了 `reviewer` 角色，而该角色 **deny write/edit/pwsh**，
    与任务书要求（跑提取树、做变异、落盘报告）**直接矛盾**；且队友工具表在**创建那一刻定死**，
    `update_teammate` 的 `allow_tools` **改不动已建会话的注册表**。
    ⇒ **教训：派活前先核对该角色的 deny 清单与任务书要求是否相容。**
  - **仍未修**：P2-2（判据不在 `smoke-all` 链 + 真机弹窗可用宽≈600 是推断）、
    P2-5（shipped harness 到不了配置态）、P2-6（`DEVELOPMENT-HISTORY.md` §10.232 编号重复，
    属别人批次，**不擅自改**）。

---

## 依赖关系

```
T001/T002/T003（取证）── 已完成
      ↓
T010 → T011 → T012（token 缺口 + 判据）
      ↓
T020 → T021（表单溢出 + 判据）
      ↓
T030 → T031（逐面审查 + 留痕）
      ↓
T040 → T041 → T042 → T043（收口）
```
