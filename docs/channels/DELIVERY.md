# 全国规范性文件公告 · 存量交付说明

> 本文由 `scripts/channels-delivery-report.py` 从**实际数据**生成，不是手写、不含估计值。

生成时间：2026-11-02 12:08:01

## 一、总账（实测）

| 口径 | 数值 |
|---|---:|
| 已抓站点 | **169** |
| 条目 | **8,569** |
| 正文篇数 | **7,875** |
| 正文总字数 | **27,926,489** |
| 附件引用处 | 474 |
| 附件文件 | **470 个 / 389.3 MB** |
| 抓到条目的站 | 147 |
| **能翻多页的站** | **50** |

## 二、按层级（发现阶段实测状态）

| 层级 | 发现 | ok | hub | js_rendered | no_board_found | unreachable |
|---|---:|---:|---:|---:|---:|---:|
| city | 274 | 192 | 0 | 13 | 62 | 7 |
| ministry | 26 | 26 | 0 | 0 | 0 | 0 |
| province | 14 | 14 | 0 | 0 | 0 | 0 |

## 三、条目最多的 15 个站

| 站 | 条目 | 正文 | 页 | 附件 |
|---|---:|---:|---:|---:|
| 池州市 | 1010 | 996 | 40 | 5 |
| 汕头市 | 691 | 691 | 40 | 5 |
| 国家药品监督管理局 | 547 | 0 | 20 | 0 |
| 攀枝花市 | 536 | 536 | 20 | 9 |
| 湖南省 | 451 | 451 | 34 | 3 |
| 茂名市 | 384 | 384 | 26 | 5 |
| 湛江市 | 354 | 354 | 20 | 5 |
| 国家外汇管理局 | 339 | 339 | 27 | 4 |
| 潮州市 | 322 | 322 | 20 | 5 |
| 惠州市 | 319 | 319 | 20 | 5 |
| 汕尾市 | 229 | 229 | 14 | 5 |
| 阳江市 | 132 | 132 | 7 | 5 |
| 保定市 | 132 | 132 | 8 | 0 |
| 宿州市 | 128 | 124 | 11 | 8 |
| 苏州市 | 128 | 124 | 11 | 8 |

## 四、怎么重跑（可复用能力）

```powershell
# 1) 只看列表与翻页（快，用于确认站点还活着、有没有新条目）
.venv\Scripts\python.exe scripts/national-crawl-fetch.py --kindnormative --list-only --concurrency 6

# 2) 补正文与附件（已有的自动跳过）
.venv\Scripts\python.exe scripts/national-crawl-fetch.py--text-only --concurrency 6

# 3) 单站复跑（验证某站）
.venv\Scripts\python.exe scripts/national-crawl-fetch.py --site湖南省 --list-only --pages 60

# 4) 脚本渲染的站用浏览器通道
.venv\Scripts\python.exe scripts/national-crawl-browser.py--sites 贵阳市 --pages 2

# 5) 把实测规则沉淀成配置 / 重新导出
.venv\Scripts\python.exe scripts/national-crawl-fetch.py --export-rules
```

**增量怎么看**：每站 `site-state.json` 里的 `items_new_this_run` 就是「这次比上次多出的条目数」，`prev_items_total` 是上次的总数。连续跑两次第 2 次应为 0（已验证：+12 → +0）。

## 五、缺口与原因（都是实测出来的）

1. **翻页不吃 URL 参数**：45 个站试过 13 种规则，0 命中；省站同样。只能浏览器逐页点，单页 20~50 秒。
2. **列表靠脚本渲染**：24 站静态抽不到条目；13 个已知地址的站浏览器救回 7 个。
3. **省门户/部委入口难定**：27 个候选里 6 个是占位页或 404（加 `www.` 救回 6 个）；部委目录页 `gov.cn/guowuyuan/` 连浏览器都 403，改从部委站导航挖到 61 家。

## 六、数据在哪

- 条目：`var/data/national/<省>/<站>/items.jsonl`（每行一条，UTF-8 JSON）
- 正文：`var/data/national/<省>/<站>/text/<hash>.txt`
- 附件：`var/data/national/<省>/<站>/attachments/<sha256前16>_<原名>`
- 逐站快照：`site-state.json`
- 逐站清单（机器可读）：`docs/channels/data/inventory.json`
