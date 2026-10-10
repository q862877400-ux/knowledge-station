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

- [ ] **T010** `ksGuideStyles.ts` 补 `--ks-radius` 定义，**值必须落回官方 token**
  —— `--ks-radius: var(--ks-radius-md)`（官方 `ui-radius.md`：不许引入 10/14/18/24 这种本地值）。
  - **判据**：定义存在；且同文件里 `var(--ks-radius)` 的 1 处使用不再指向未定义 token。
  - **变异**：删掉该定义 ⇒ T012 的判据必红。

- [ ] **T011** `ksGuideStyles.ts` 补 `--ks-font-mono` 定义
  —— 落进 `--ks-font-*` 家族；值用**本机真实可用**的等宽栈（不许凭空写一个字体名）。
  - **判据**：定义存在；`var(--ks-font-mono,monospace)` 的兜底可留可去，但**定义必须存在**。
  - **变异**：删掉该定义 ⇒ T012 判据必红。

- [ ] **T012** 给 D1/D2 立**机械判据**，进 `smoke-ui-scale.mjs`（已在门禁链里）
  —— 从 `ksGuideStyles.ts` 抠出所有 `var(--ks-*)` 引用集合与 `--ks-*:` 定义集合，
  要求 **引用 ⊆ 定义**；带兜底值的（`var(--x, y)`）**单独列出并放行**（它们是刻意兜底，不是缺陷）。
  - **判据**：原样件 PASS；删任一 token 定义 ⇒ FAIL 并点名缺的是谁。
  - **变异**：**逐条**做（删 `--ks-radius` / 删 `--ks-font-mono`），各红一次。
  - **⚠ 反向也要有牙**：把判据写成恒真（比如比对空集合）⇒ 必须能被"注入一个假缺口"打红。

## 阶段 2：D3 —— 表单溢出（有真机证据）

- [ ] **T020** `KsSettingsSection.tsx` 的凭据表单修溢出
  —— 给可收缩项加 `minWidth: 0`；**不许**发明第二种解法（本仓已有同坑的留痕）。
  - **约束**：改动**不得**落在 `AnnounceTriageSection` 区间内（禁碰区）。
    施工前 `grep -n "function AnnounceTriageSection"` 拿行号区间，施工后**再核一次**。
  - **判据**：T021 的真浏览器量点通过。

- [ ] **T021** `ui-render-shot.mjs` 加 `settings` 页 + 量点 + Node 侧判
  —— 真浏览器量"每个输入框右缘 ≤ 其所在行容器内容盒右缘"，溢出 > 1px 即红；量不到即红。
  - **判据**：修复后 PASS；把 `minWidth:0` 改回 ⇒ FAIL。
  - **⚠ 不许进 `MATRIX`**（那会要求同批改 `EXPECTED_RUNS`，把 diff 扯到冻结清单上）；
    用单独命令量，并把命令写进 tasks 与文档。

## 阶段 3：四个主面逐态审查（留痕）

- [ ] **T030** 用 `ui-render-shot` 把 kb / ingest / capabilities / materials 的**每个交互态**渲一遍
  —— `--interact` 的全部取值各跑一次，逐张 `read_image`。
  - **判据**：每个面在 `docs/UI-BASELINE.md` 有一行：面名 / 截图 / 看到的事实 / 结论。
  - **诚实边界**：真宿主进不去的面必须写明"**没在真宿主里看过**"。

- [ ] **T031** 把本轮结论写进归属层
  —— `docs/UI-BASELINE.md` §5aa + `docs/DEVELOPMENT-HISTORY.md` §10.232。

## 阶段 4：收口

- [ ] **T040** 重建交付产物 `plugin/client.js`（`node scripts/build-client.mjs`）
  - **判据**：`smoke-client-entry` 的"产物 ↔ 从源码现构建整份一致"断言 PASS。

- [ ] **T041** 跑改动面门禁
  - **判据**：`smoke-all` 全链 PASS + `tsc` exit 0；收工跑 `-Quick`。
  - **⚠ 退出码 3 = 有人在跑门禁，不是失败**。

- [ ] **T042** 小提交 + 快照
  - **判据**：提交消息写清"改了什么 / 为什么 / 边界"；`snapshot-project.ps1` 出新 tag。

- [ ] **T043** 派独立复核（属必验类别：改了共享样式 + 新增判据）
  - **判据**：冻结 tag + 提取树；报告落盘 `docs/verify-briefs/`。

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
