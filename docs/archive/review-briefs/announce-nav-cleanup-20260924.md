# 真库清理留档：22 条"栏目导航"型误发现（2026-09-24）

**为什么要留档**：这是我唯一一次**删真实数据**的动作（删除 22 行 `announcement_observed`），
而当时的日志写在 `var/tmp/real-cleanup.log` —— 那个目录被 `.gitignore` 挡着，收尾清树会连证据一起没
（本仓 §10.184 已经吃过一次这个亏）。所以把**删了什么、按什么判据删的、怎么复算**搬到这里。

## 判据（与新代码同一口径）

`src/core/update/announce.py::looks_like_article`：**URL 路径以 `/` 结尾 = 栏目目录，不是公告**。
真机证据：这 22 条 **22/22 都以 `/` 结尾**，且**全都没有发布日期**（`published_date IS NULL`）。
它们是应急管理部网站列表页左右栏的**栏目链接**，旧解析把标题一抽就当成了公告；
不清理的话，下一步"批量入库"会把导航页抓回来当法规正文入库。

## 删掉的 22 行（全部，逐字）

| 标题 | URL |
|---|---|
| 灾害事故信息 | https://www.mem.gov.cn/xw/zhsgxx/ |
| 政府信息公开 | https://www.mem.gov.cn/gk/zfxxgkpt/ |
| 事故及灾害查处 | https://www.mem.gov.cn/gk/sgcc/ |
| 建议提案办理 | https://www.mem.gov.cn/gk/jytabljggk/ |
| 原国家安全监管总局文件 | https://www.mem.gov.cn/gk/gwgg/ |
| 法律法规标准 | https://www.mem.gov.cn/fw/flfgbz/ |
| 应急管理部行政许可 | https://www.mem.gov.cn/fw/yajzjxzxk/ |
| 行政执法公示 | https://www.mem.gov.cn/fw/xzzfgs/ |
| 应急管理部电子证照 | https://www.mem.gov.cn/fw/dzzz/ |
| 国家政务服务投诉与建议 | https://www.mem.gov.cn/hd/tsjb/ |
| 社会救援服务 | https://www.mem.gov.cn/shjyfw/ |
| 应急科普场馆 | https://www.mem.gov.cn/kp/yjkpcg/ |
| 应急管理部公报 | https://www.mem.gov.cn/gk/tzgg/yjglbgg/ |

（上面 13 条里有 9 条**在两个源下各存了一份**（`src_01M1VMRBG6CHCMQQGK0JX8ZFVD` =
应急部标准公告、`src_01M38ECS0DRQH0JTTBA2G0C9P9` = 应急部通知公告），所以行数是 **22** 而不是 13。）

## 怎么复算 / 怎么撤回

- **复算**（只读，任何时候可跑）：
  `sqlite3 <真库> "SELECT COUNT(*) FROM announcement_observed WHERE url LIKE '%/'"` ⇒ 应为 **0**
  （修完 `looks_like_article` 后重新扫描也不会再把它们收进来）。
- **撤回**：这些行是"发现记录"，不是知识库正文（`doc_meta` 一行都没删）。
  要恢复只需让公告源再扫一次 —— 但**新代码不会再把目录型链接当公告**，
  所以"恢复"没意义；真要那 13 条链接，本表就是完整清单。

## 当时的前后数

- 清理前：`announcement_observed` **558** 行（含这 22 行导航）。
- 清理后：**536** 行；`ingest_summary` = 已发现 536 / 已入库 411 / 待入库 0 / 按范围跳过 125。
- `doc_meta`：6417 → **6797**（真实新增 **380** 篇 mem.gov.cn 来源；411 是"已发现行里算进库"的行数口径）。
