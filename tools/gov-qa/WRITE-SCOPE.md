# 写入分工（**两个对话同时在写这个目录**）

> **2026-10-07 记。** 业主把这件事拆给两个对话：
> **国家部委接入**（本目录的 `MINISTRY-ENTRIES.md` / `probe-ministries.py` / `adapters/mem_gov.py` / `adapters/mee_gov.py`）
> 与**省市接入**（`adapters/hunan_*.py` / `recon/probe-provinces.py` 等）。
>
> ⚠ **事故留痕**：2026-10-07 17:4x，本对话执行 `git add tools/gov-qa`（整目录）时，
> **把另一个对话当时正在写的 11 个文件一起提交了**（`hunan_*.py`、`_was5_common.py`、
> `probe-provinces.py`、`recon/dig*.py` …，时间戳 17:37–17:47）。
> **这次没造成破坏**（它们的改动是追加式的，`ADAPTERS` 合并无冲突，本对话模块照常跑），
> 但**流程是错的**：提交了别人**写了一半**的东西。

> ⚠ **事故留痕（反向扫入，2026-10-07 18:12）**：省市接入对话（本文另一侧）发现，
> 它暂存的 26 个文件（`data/hunan-*`、`adapters/people_liuyan.py`、`_liuyan_common.py`、
> `recon/liuyan-*` 等）被研究类提交 **1082121**（CESI 论文精读）**一并扫入并提交**——
> 该提交信息与这批文件无关。根源链条：省市对话先违反第 1 条
> （`git add tools/gov-qa` 整目录暂存，之后隔了一段时间才提交），
> 期间**暂存区是全仓共享的**，另一对话提交时把暂存内容一起带走了。
> 两次事故同根 ⇒ 第 1 条规矩升级两条：
> ① **`git add` 后立刻 commit，暂存区不隔轮存放**（暂存 = 交给所有人）；
> ② 提交前 `git status --short` 逐文件过一遍归属，发现别人的文件就 `git reset` 掉。

## 规矩（两边都请遵守）

1. **`git add` 只加自己的文件，永不加整个目录。**
   ❌ `git add tools/gov-qa`
   ✅ `git add tools/gov-qa/MINISTRY-ENTRIES.md tools/gov-qa/probe-ministries.py`
2. **`adapters/__init__.py` 是共享文件**（两边都要往 `ADAPTERS` 里登记）。
   改它时**只加自己那几行**，不要重排、不要动别人的行。
3. **`data/` 与 `recon/` 按前缀分**：文件名前缀写明归属（如 `mee-` / `mem-` = 国家；`hunan-` = 省市）。
4. **共享的基础设施**（`harvest.py` / `measure-locate-rate.py` / `README.md`）改动前先看这页。
   要改公共行为，**在提交消息里写明"影响另一个对话"**。

## 建议的物理分区（**留给两位业主/对话定，本对话不擅自搬别人的文件**）

```
tools/gov-qa/
├── national/     ← 国家部委（本对话负责）
├── province/     ← 省市（另一个对话负责）
└── shared/       ← harvest.py / measure-locate-rate.py / adapters/__init__.py
```

**为什么要分**：现在两边都在 `adapters/` 与 `recon/` 下**同层写文件**，
靠"文件名前缀"自觉区分；`min` 与 `prov` 两套适配器混在一起，`--list` 也会越列越长。
搬迁是**一次性**动作，但**必须两个对话都同意**再做，否则会打断正在跑的一方。
