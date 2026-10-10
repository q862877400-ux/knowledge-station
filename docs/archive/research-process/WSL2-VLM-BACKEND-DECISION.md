# 决策记录：WSL2 解锁 vlm/hybrid 本地后端 —— 否决（2026-09-14）

**状态**：否决，保留复议权。本文档为执行计划 v3 阶段 0c 归档件（对评审 R6 的闭环）。

## 背景

评审 R6 指出：「无 WSL」被当作恒真约束，但「安装 WSL2 解锁 MinerU vlm/hybrid 本地后端」
全程未进入候选清单——16GB 跑量化 VLM 是否可行可以论证后拒绝，但必须留下评估记录，
否则这是方案空间的盲区而非约束。本记录即补齐的评估。

## 评估

### 可行性（技术层：成立）
- WSL2 + CUDA on Windows（WSLg GPU 半虚拟化）在 RTX 4080 SUPER 上技术可行
- vLLM 有 Linux wheel → MinerU vlm/hybrid 后端在 WSL2 内可部署
- 实测障碍确认：Windows 原生无 vLLM（`ModuleNotFoundError: No module named 'vllm._C'`，
  MinerU issue #4957），当前 pipeline 后端即为此限制下的选择

### 显存账（勉强成立）
- MinerU 2.5 VLM（1.2B，BF16）推理约 3-4GB；与双 pipeline daemon（2×~5GB）并存勉强
- 但 vlm 模式单进程串行（无攒批），吞吐低于 pipeline 攒批通道

### 工程账（负项）
- 一次性：WSL2 安装 + WSL 内 CUDA toolkit + vLLM 环境 + 持久化（估 0.5-1 人日）
- 持续性：双运行环境（Windows pipeline + Linux vlm）的维护成本长期存在

### 收益账（决定性负项）
- vlm 后端对复杂版面（公式密集/跨页表）精度高于 pipeline
- **但**：当前架构云优先（2026-09-08 反转），MinerU 官方云 API 用的正是同一 VLM
  能力——vlm 本地化的增量仅剩「云配额耗尽/未配 Key 时的本地 VLM 兜底」
- 该场景已被「本地 pipeline 兜底 + ch_server 升档（执行计划阶段 1）」部分覆盖

## 结论

**否决。** 成本（双环境维护 + 一次性搭建）> 增量收益（云已覆盖同一 VLM 能力），
且违反架构演进史的简洁方向（2026-09-01 本地优先 → 09-08 云优先两次反转均朝
「减少运行环境分叉」走）。

**复议触发条件**（满足其一重开评估）：
1. 云配额长期不可用（MinerU 官方云停服 / 用户 Key 长期限流）
2. 扫描件入库占比显著上升（>50% 新增文档为无文本层扫描件）
3. 出现 pipeline 后端无法解决、VLM 后端可解的系统性错误类别（以 0a 归因表
   / ocr_suspects 证据为准）

## 关联文档
- 执行计划：`var/tmp/ocr-upgrade-execution-plan-v3.md`（阶段 0c）
- 评审回复 R6：`var/tmp/ocr-upgrade-review-response.md`
