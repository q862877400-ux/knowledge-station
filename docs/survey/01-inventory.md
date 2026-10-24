# 全仓清单（四本账）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、四本账（覆盖证明）

| 账本 | 条数 | 说明 |
|---|---|---|
| 甲 受控文件 | **3,598** | `git ls-files` |
| 乙 未跟踪文件 | **755** | `git status --porcelain` 的 `??` |
| 丙 合并去重 | **4,353** | 甲 ∪ 乙，重叠 21 |
| 丁 被忽略但存在 | **468** | `git status --ignored` —— **包含生产数据，没有它下一棒会以为仓里没数据** |
| 戊 本检查的生成物 | 21 | 排除在项目统计外 |
| **计入统计** | **4,332** | 丙 − 戊 |

## 二、按分类

| 分类 | 文件 | 体积 | 行数 |
|---|---:|---:|---:|
| 另一条线-政务问答采集 | 2,861 | 943.9 MB | 5,308,467 |
| 评测集 | 430 | 19.6 MB | 114,819 |
| 测试 | 194 | 15.0 MB | 47,346 |
| 文档 | 192 | 6.9 MB | 90,228 |
| 产品代码-引擎 | 162 | 2.6 MB | 51,002 |
| 脚本-工具/门禁 | 98 | 1021 KB | 21,674 |
| 规格-spec-kit | 88 | 686 KB | 12,726 |
| 验证脚本-冒烟/探针 | 60 | 1.5 MB | 25,656 |
| 本地产物-数据/模型 | 54 | 709 KB | 13,799 |
| 文档-历史归档 | 51 | 1.8 MB | 23,314 |
| 文档-项目现状地图 | 41 | 2.3 MB | 34,970 |
| 产品代码-界面 | 33 | 1.1 MB | 23,312 |
| 产品代码-插件宿主 | 23 | 511 KB | 10,654 |
| 规格-spec-kit脚手架 | 20 | 95 KB | 2,392 |
| 其他 | 14 | 123 KB | 2,281 |
| 插件其他 | 6 | 1.8 MB | 45,013 |
| 受控但磁盘缺失 | 2 | 0 KB | 0 |
| 证据原件-PDF | 2 | 3.0 MB | 0 |
| 工具配置 | 1 | 3 KB | 49 |

## 三、被 git 忽略但确实存在（账本丁）

| 路径前缀 | 条目 |
|---|---:|
| `var/ocr-loop` | 216 |
| `tools/gov-qa` | 162 |
| `src/core` | 19 |
| `docs/research` | 18 |
| `.dsh/skills` | 10 |
| `eval/recall-funnel` | 7 |
| `.codebuddy` | 1 |
| `.mypy_cache/.gitignore` | 1 |
| `.mypy_cache/3.12` | 1 |
| `.mypy_cache/CACHEDIR.TAG` | 1 |
| `.pytest_cache` | 1 |
| `.ruff_cache/.gitignore` | 1 |
| `.ruff_cache/0.17.2` | 1 |
| `.ruff_cache/CACHEDIR.TAG` | 1 |
| `.specify/feature.json` | 1 |

> ⚠ **`var/data/` 是生产库与证据原件所在**（35.8 万个文件 / 74 GB）。
> 它被 `.gitignore` 排除，所以**不在甲、乙两本账里**。
> 下一棒要读真实数据，去这里；不要以为仓里只有代码。

## 四、受控但磁盘上没有的文件

- `docs/uniformity/COVERAGE.md` —— `git status` 显示已从工作树删除但未提交
- `var/_trash-2026-10-11/README.md` —— `git status` 显示已从工作树删除但未提交

## 五、各类里最大的 10 个文件

| 文件 | 体积 | 行数 |
|---|---:|---:|
| `tools/gov-qa/recon/.label-model.joblib` | 49.6 MB | 0 |
| `tools/gov-qa/data/ln-8890-辽宁省·12345民心智慧听（咨询投诉+知识库）.jsonl` | 31.1 MB | 21,748 |
| `tools/gov-qa/data/sd-dongying-东营市·政民互动·网上民生（jact）.jsonl` | 29.3 MB | 20,271 |
| `tools/gov-qa/data/sd-yantai-烟台市·互动交流·网上民声（jact网关）.jsonl` | 27.6 MB | 19,907 |
| `tools/gov-qa/data/nat-tax-国家税务总局·12366网上留言.jsonl` | 25.5 MB | 13,943 |
| `tools/gov-qa/data/cq-igi-重庆市人民政府·政民互动（IGI）.jsonl` | 18.8 MB | 11,269 |
| `tools/gov-qa/data/gd-shenzhen-深圳市人民政府·政民互动（hdjlpt）.jsonl` | 17.9 MB | 15,000 |
| `tools/gov-qa/data/tj-enorth-天津市·政民零距离.jsonl` | 16.0 MB | 10,360 |
| `tools/gov-qa/data/gs-zhangye-张掖市·政民互动（IGI）.jsonl` | 15.7 MB | 6,613 |
| `tests/fixtures/seed/knowledge-seed.db` | 12.7 MB | 0 |