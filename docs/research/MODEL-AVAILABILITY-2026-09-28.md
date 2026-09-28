# 调度记录：免费模型逐个真调（2026-09-28）

> **为什么有这份**：本轮六个子代理在写报告前全部被限流掐死。业主判断「是模型限流了，你死了子代理也停了」——
> **核实后成立**，并找到了具体是哪个额度在限。
> **方法不是我的发明**：抄 `~/.dsh/settings.yaml.imported` 第 69–70 行的既有实测纪律逐字照做：
> 「GET /v1/models 对本账户列出 82 个，但『**列表 ≠ 可用**』。逐个真调 /chat/completions（25s 超时）
>  + function calling 后，真正能出字的是……」
> ⇒ **不看列表，只看真调。** 探针 `var/tmp/probe-free-models.py`，原始输出 `var/tmp/probe-free-models-out.txt`。

---

## 一、结论表（今天 2026-09-28 实测）

| 模型 | provider | 能否出字 | **能否真调工具** | 延迟 | 判断 |
|---|---|---|---|---|---|
| `space-bunny-free` | OpenCode Zen | ✅ | ✅ **1 call** | 1.0–2.0 s | **可用**（本会话正在用的就是它） |
| `deepseek/deepseek-chat-v3.1` | OpenRouter | ✅ | ✅ **1 call** | 1.0–1.2 s | **可用**（最快） |
| `mimo-v2.6-flash` | MiMo | ✅ | ✅ **1 call** | 1.3–1.6 s | **可用** |
| `z-ai/glm-5.3-flash` | OpenRouter | ✅ | ✅ **1 call** | 0.8–4.9 s | 可用（延迟波动大） |
| `mimo-v2.6-pro` | MiMo | ✅ | ⚠ 本次 1 call / 上次 0 call | 1.2–4.1 s | 弱，备用 |
| `openai/gpt-5-mini` | OpenRouter | ✅ | ❌ **0 call** | 2.0–3.9 s | **不能当子代理** |
| 🔴 `stealth/space-bunny-alpha` | OpenRouter | ❌ **429** | — | — | **今日额度用尽** |
| 🔴 `step-5-preview` | StepFun | ❌ **402** | — | — | 额度用尽 |
| 🔴 `openai/gpt-oss-120b` | NVIDIA NIM | ❌ **410 Gone** | — | — | 已下线 |
| 🔴 `qwen/qwen3-coder-480b` | NVIDIA NIM | ❌ **410 Gone** | — | — | 已下线 |
| 🔴 `deepseek-v4-flash`(nifer) | — | ❌ SSL EOF | — | — | 连接失败 |
| 🔴 `qwen3.8-27b`(本地 LM Studio) | 本地 | ❌ 连接被拒 | — | — | 服务未起（127.0.0.1:1234） |
| ⚠ `kimi-k3` | Moonshot | **未判** | — | — | 探针缺陷，见 §三 |

## 二、**限流的真凶（这一条直接解释了今天的死法）**

`stealth/space-bunny-alpha` 的错误逐字：

> `{"error":{"message":"Rate limit exceeded: free-models-per-day-stealth. ","code":429,...`

**是"每日免费模型额度"用尽，不是"每分钟"。**

⚠ 这与本会话开头的模型切换记录一致：会话早些时候跑在
`deepseek/deepseek-flash` 与 `openrouter/stealth/space-bunny-alpha` 上，之后切到 `space-bunny-alpha`、
再到 `opencode-zen/space-bunny-free`，最后是本模型。⇒ **一天的额度被前面几轮会话 + 六个子代理吃完了。**

## 三、探针自己的两处错（如实登记，不推给模型）

1. **环境变量名抄错**：第一轮我写 `MOONSHOT_API_KEY` / `XIAOMIMIMO_API_KEY`，而 settings 里真实键名是
   `MOONSHOTAI_CN_API_KEY` / `MIMO_API_KEY` ⇒ 第一轮那两条的 `NO-KEY` **是我的错，不是模型不可用**。
2. **`kimi-k3` 仍未判**：错误是 `invalid temperature: only 1 is allowed for this model`。
   我改了无工具那条分支去掉 `temperature`，但**工具那条分支仍带 `temperature: 0`**（代码改动没生效在正确路径上）
   ⇒ **该模型的真实状态未知，不据此判死。**

## 四、这一轮暴露的两条调度教训

1. 🔴 **"列表 ≠ 可用"要自己真调**，且**必须显式要求模型用工具**——
   我第一版探针只把工具放进 `tools`、提示语是 "Reply with exactly: OK"，
   于是 `openai/gpt-5-mini` 回了纯文本、**0 tool_calls**，我差点把它判成"能用"。
   改成"必须调用 probe_tool"之后，**五个模型的工具能力才区分出来**。
   ⇒ **只测"能不能出字"会漏掉最关键的那一项**（子代理完全靠工具）。
2. 🔴 **长报告任务是限流放大器**：六个代理同时跑、各自抓几百个文件，
   在额度耗尽时**全部死在写报告之前** ⇒ 抓的原始件还在（`raw/BANN` 2.1 GB 等），
   **结论全在代理上下文里、代理一死就没了**。
   **对策已写进 `var/tmp/study/problems/RESUME-BRIEF.md` 的「落盘形状」：先写半份、立刻落盘、再补全。**

## 五、由此定下的并发规则

> **同一模型不超过 3 个；把所有可用的免费模型都用上。**

按 §1，**真正"免费 + 带工具调用"的有 4 个**（`space-bunny-free` / `deepseek-chat-v3.1` / `mimo-v2.6-flash` / `glm-5.3-flash`）
⇒ **同时最多 12 个子代理**。

⚠ **但本轮不一次开满**：额度是**每日**的，开满 12 个会在半路再次集体耗尽。
**本轮实派 6 个**（每组一个），并要求**先落盘再补全**，把"死前无产出"这个风险去掉。

> **边界**：本文件只记调度事实。**未改动任何模型配置**（`~/.dsh/` 下只读），
> 未改仓库任何被跟踪的文件。
