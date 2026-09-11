# ANOM-003 · official_gb 适配器与真实 openstd 页面不匹配 DCP

## 现象
真实巡检：12 个 GB 标准全部 gray（查无此号）。但真实站点可用——
curl_cffi 探针：`https://openstd.samr.gov.cn/bzgk/std/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=GB%2030871-2022`
返回 200、筛选面板显示「标准状态：现行(1)」（对 GB 30871-2022）。

## 结论
适配器（official_gb.py）对真实 HTML 的解析失败或请求路径过期：
- 页面已重定向到 /bzgk/std/std_list（旧 /bzgk/gb/std_list 会跳转）
- 结果表行疑似异步/结构与 mock 预期不同（锚点 30871 落在 ICS 筛选面板内）
- mock fixture 是理想化 HTML，未覆盖真实结构 ⇒ 单元测试全绿但真机全灭（测试盲区：mock 与 live 脱节）

## 复现与取证
- var/tmp/probe_openstd.py / probe_openstd_dump.py / probe_gov_channels.txt
- RUN_LIVE 门控机制已存在（tests/test_update_channels.py）

## 修复要求（canonical owner = channels/official_gb.py）
1. 用 curl_cffi 实机核对 /bzgk/std/std_list 真实结果行 HTML 结构（tr/td/状态文字 现行/即将实施/已废止）
2. 修正 URL 路径与解析逻辑，正确抽取：标准号、名称、状态→legal_status、发布日期
3. 追加 RUN_LIVE 门控 live 用例：GB 30871-2022 断言 found=True 且 legal_status=effective（默认 skip）
4. mock fixture 同步补一行贴近真实结构的样例，防回归
5. 全量 ≥293+3；RUN_LIVE=1 实跑通过

[DCP_VALID]
