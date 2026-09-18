# 渠道台账状态快照（自动生成，勿手改）

- 生成时间：2026-09-18 13:15:20（本地） · 数据来源：`C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db` 的 `update_channel` 表
- 台账 **131** 条 · 启用 129 条 · **能干活（wired）7** 条 · 已知失效 **1** 条 · 仅登记 113 条
- 已实测：🟢 22 / 🟡 1 / 🔴 5 / ⚪ 未探 103

> ⚠ 两个数字**必须分开读**：`台账条数` 是「我们知道多少渠道」，`能干活条数` 才是「今天真的能用几条」。R1 的实测教训（G5/G6）：13 个适配器只有 8 个在链上，而在链上的 `web`/`govcn` 两根兜底棒在真实 HTML 下恒 miss。

## 一、我方通路（适配器与采集链路）

| 渠道 | 接线 | 有效性 | 上次成功 | 失败原因 | 链接 |
|---|---|---|---|---|---|
| `ch:dbba` 地方标准信息服务平台（sacinfo） | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-18 04:48:42 | — | POST https://dbba.sacinfo.org.cn/stdQueryList（form: current=1&size=20& |
| `ch:govcn` gov.cn 公告检索 + PDF 存档 | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-18 05:15:10 | — | GET https://sousuo.www.gov.cn/sousuo/search.shtml?q=<标准号 标准名>；归档用 tran |
| `ch:hbba` 行业标准信息服务平台（sacinfo） | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-18 04:48:43 | — | POST https://hbba.sacinfo.org.cn/stdQueryList（form: current=1&size=20& |
| `ch:mee` 生态环境部 HJ 标准 | ✅ 已接线（在 routing 链上） | ⚪ 未探 | — | — | POST http://datacenter.mee.gov.cn/websjzx/report!list.action?xmlname=1 |
| `ch:ndls` 国家数字标准馆（中国标准化研究院） | ✅ 已接线（在 routing 链上） | ⚪ 未探 | — | — | POST https://ndls.cnis.ac.cn/api/standard/list（JSON）+ GET https://ndls |
| `ch:official_gb` 国家标准全文公开系统 | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-18 04:48:41 | — | GET https://openstd.samr.gov.cn/bzgk/std/std_list?searchText=<号>&p.p1= |
| `ch:ttbz` 全国团体标准信息平台 | ✅ 已接线（在 routing 链上） | ⚪ 未探 | — | — | POST https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/getPorta |
| `ch:announce_sources` 用户自定义公告源（现有台账形态） | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | 用户配置的任意公网 http/https 列表页 URL（app_config 键 announce.sources） |
| `ch:ccs_fetcher` 中国标准服务网 CCS 分类抓取 | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | GET https://www.cssn.net.cn/api/cssn/list?keyword=<数字号> |
| `ch:cssn` 中国标准服务网 | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-18 04:48:44 | — | GET https://www.cssn.net.cn/api/standards/list?keyword=<标准号（保留空格）> |
| `ch:discover_search` 找标检索（openstd 分类检索） | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | GET https://openstd.samr.gov.cn/db/search?q=<分类路径 标准>&page=<drill_leve |
| `ch:flk_client` 国家法律法规数据库官方源客户端 | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | POST /law-search/search/list · GET /law-search/search/flfgDetails?bbbs |
| `ch:govcn_client` 国务院政策文件库官方源客户端 | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | GET https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q=…&sea |
| `ch:laws_db` 国家法律法规数据库（flk.npc.gov.cn） | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-18 04:48:42 | — | POST https://flk.npc.gov.cn/law-search/search/list（JSON body，pageNum=1 |
| `ch:mem_gov` 应急管理部 AQ 行业标准公告 | ⚪ 未接线（注册了但巡检不调用） | 🟡 可疑 | — | HTTP 200 但响应里没有预期锚点 '标准公告'（26755 字符）——本领域最常见的假可用（G14） | GET https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/（+ index_N.shtml 分页，逐条公告详 |
| `ch:mohurd` 住建部工程建设标准文告 | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-18 04:48:44 | — | GET https://www.mohurd.gov.cn/gongkai/zc/wgk/（+ index_N.shtml 分页，逐条文告详 |
| `ch:std_samr_hb` 全国标准信息公共服务平台·行业标准目录 | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-18 04:48:43 | — | GET https://std.samr.gov.cn/hb/search/hbPage?searchText=<归一号>&op=&ISSU |
| `ch:web` 网络逐号补漏搜索（Bing） | ❌ 已知失效（在链上但实测不工作） | ⚪ 未探 | — | — | GET https://www.bing.com/search?q=<标准号 标准名> |

## 二、外部渠道（按类别）

### 法规（45 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 上海市人民政府-政府规章库 | 🟢 可抓 | 2026-09-18 04:48:44 | 有 | https://www.shanghai.gov.cn/xxzfgzwj/ |
| 上海市人民政府-近期信息公开 | 🟢 可抓 | 2026-09-18 04:48:45 | 有 | https://www.shanghai.gov.cn/nw12344/index.html |
| 中国政府网-最新政策静态JSON | 🟢 可抓 | 2026-09-18 04:48:41 | 有 | https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json |
| 北京市人大 | 🟢 可抓 | 2026-09-18 04:48:45 | 有 | https://www.bjrd.gov.cn/ |
| 北京市人大常委会-重要发布 | 🟢 可抓 | 2026-09-18 04:48:45 | 有 | https://www.bjrd.gov.cn/zyfb/ |
| 北京市人民政府-政策文件 | 🟢 可抓 | 2026-09-18 04:48:45 | 有 | https://www.beijing.gov.cn/zhengce/zhengcefagui/ |
| 司法部-国家行政法规库(xzfg) | 🟢 可抓 | 2026-09-18 04:48:43 | 有 | http://xzfg.moj.gov.cn/search2.html |
| 司法部-部门规章栏目 | 🟢 可抓 | 2026-09-18 04:48:45 | 有 | https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzbmgz/ |
| 广东人大网 | 🟢 可抓 | 2026-09-18 04:48:44 | 有 | https://www.gdpc.gov.cn/ |
| 应急管理部-法律法规 | 🟢 可抓 | 2026-09-18 04:48:43 | 有 | https://www.mem.gov.cn/fw/flfgbz/fg/index.shtml |
| 应急管理部-规章(法定主动公开) | 🟢 可抓 | 2026-09-18 04:48:43 | 有 | https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/ |
| 浙江省人大 | 🟢 可抓 | 2026-09-18 04:48:44 | 有 | https://www.zjrd.gov.cn/ |
| 生态环境部-法规标准 | 🟢 可抓 | 2026-09-18 04:48:43 | 有 | https://www.mee.gov.cn/ywgz/fgbz/ |
| 上海市人大-法规公布 | 🔴 不可抓 | — | 有 | https://www.shrd.gov.cn/shrd/fggb/fggb.html |
| 上海市人大-法规公布AJAX(TrueCMS) | ⚪ 未探 | — | — | https://www.shrd.gov.cn/TrueCMS/messageController/getMessage.do |
| 上海市司法局 | ⚪ 未探 | — | — | https://sft.sh.gov.cn/ |
| 上海市司法局-规范性文件 | 🔴 不可抓 | — | 有 | https://sfj.sh.gov.cn/2020jcgk_gfxwj/ |
| 中国政府网-国家规章库 | ⚪ 未探 | — | — | https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm |
| 中国政府网-政策文件库检索 | ⚪ 未探 | — | — | https://www.gov.cn/zhengce/xxgk/ |
| 交通运输部-政策解读 | ⚪ 未探 | — | — | https://www.mot.gov.cn/zhengcejiedu/ |
| 人力资源和社会保障部 | ⚪ 未探 | — | — | https://www.mohrss.gov.cn/ |
| 住房和城乡建设部-政策发布 | ⚪ 未探 | — | — | https://www.mohurd.gov.cn/gongkai/zhengce/ |
| 司法部-国家行政法规库入口(实为跳转flk) | ⚪ 未探 | — | — | https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzflk/ |
| 司法部-备案审查 | ⚪ 未探 | — | — | https://www.moj.gov.cn/ |
| 国务院公报 | ⚪ 未探 | — | — | https://www.gov.cn/gongbao/ |
| 国家卫生健康委员会 | ⚪ 未探 | — | — | https://www.nhc.gov.cn/ |
| 国家市场监督管理总局-法规司 | ⚪ 未探 | — | — | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/ |
| 工业和信息化部-政策文件 | ⚪ 未探 | — | — | https://www.miit.gov.cn/zwgk/zcwj/index.html |
| 广东人大-常委会公报 | 🔴 不可抓 | — | 有 | https://www.gdpc.gov.cn/gdrdw/rdhy/cwhhy/cwhgb/index.html |
| 广东人大-权威发布公告通知 | 🔴 不可抓 | — | 有 | https://www.gdpc.gov.cn/gdrdw/zyfb/ggtz/index.html |
| 广东省人民政府-文件库 | ⚪ 未探 | — | — | https://www.gd.gov.cn/zwgk/wjk/qbwj/ |
| 广东省人民政府-粤府令 | ⚪ 未探 | — | — | https://www.gd.gov.cn/zwgk/wjk/qbwj/yfl/index.html |
| 广东省司法厅-政策文件 | ⚪ 未探 | — | — | http://sft.gd.gov.cn/sfw/zwgk/zcwj/ |
| 最高人民检察院-法律法规规范性文件 | ⚪ 未探 | — | — | https://www.spp.gov.cn/spp/flfgxwj/ |
| 最高人民法院-司法解释 | ⚪ 未探 | — | — | https://www.court.gov.cn/fabu/gengduo/16.html |
| 浙江省人大-省域立法法规公告 | ⚪ 未探 | — | — | https://www.zjrd.gov.cn/sylf/fggg/ |
| 浙江省人大-首页 | ⚪ 未探 | — | — | https://www.zjrd.gov.cn/ |
| 浙江省人民政府-政府规章省级有效 | ⚪ 未探 | — | — | https://www.zj.gov.cn/col/col1229836653/index.html |
| 浙江省人民政府-省政府文件 | ⚪ 未探 | — | — | https://www.zj.gov.cn/col/col1229019364/index.html |
| 浙江省人民政府-省政府文件栏目 | ⚪ 未探 | — | — | https://www.zj.gov.cn/col/col1229019364/index.html |
| 浙江省司法厅 | ⚪ 未探 | — | — | https://sft.zj.gov.cn/ |
| 浙江省司法厅-政策文件 | ⚪ 未探 | — | — | https://sft.zj.gov.cn/col/col1229247318/index.html |
| 首都之窗-地方性法规镜像 | ⚪ 未探 | — | — | https://www.beijing.gov.cn/zhengce/dfxfg/ |
| 首都之窗-市政府令(按文号) | ⚪ 未探 | — | — | https://www.beijing.gov.cn/zhengce/zfwj/zfwj2016/szfl/ |
| 首都之窗-政府规章(现行有效) | ⚪ 未探 | — | — | https://www.beijing.gov.cn/gongkai/zfxxgk/zc/gz/ |

### 国标（5 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 中国标准在线服务网 | ⚪ 未探 | — | — | https://www.spc.org.cn/standardonline/replace?type=0 |
| 全国标准信息公共服务平台-国家标准目录 | ⚪ 未探 | — | — | https://std.samr.gov.cn/gb/gbQuery |
| 国家标准全文公开系统 | ⚪ 未探 | — | — | https://openstd.samr.gov.cn/bzgk/std/ |
| 国家标准化管理委员会 | ⚪ 未探 | — | — | https://www.sac.gov.cn/bzhdt/index.html |
| 国家标准批准发布公告 | ⚪ 未探 | — | — | https://std.samr.gov.cn/noc/nocGB |

### 行标（13 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 中国标准化研究院 | ⚪ 未探 | — | — | https://www.cnis.ac.cn/wap/ |
| 中国标准服务网(ccsainfo) | ⚪ 未探 | — | — | http://www.ccsainfo.com/ |
| 交通运输标准化信息系统 | ⚪ 未探 | — | — | https://jtst.mot.gov.cn/search/std?q= |
| 住房和城乡建设部标准公告 | ⚪ 未探 | — | — | https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index.html |
| 国家能源局公告 | ⚪ 未探 | — | — | https://www.nea.gov.cn/policy/gg.htm |
| 国家食品安全风险评估中心 | ⚪ 未探 | — | — | https://www.cfsa.net.cn/ |
| 工信部标准信息服务平台 | ⚪ 未探 | — | — | https://std.miit.gov.cn/ |
| 工程建设标准化信息网 | ⚪ 未探 | — | — | https://www.ccsn.org.cn/News/More.aspx?ClassID=004001 |
| 应急管理部标准 | ⚪ 未探 | — | — | https://www.mem.gov.cn/fw/flfgbz/bz/ |
| 标准网(中机生产力促进中心) | ⚪ 未探 | — | — | http://www.bzw.com.cn/ |
| 生态环境部标准 | ⚪ 未探 | — | — | https://www.mee.gov.cn/ywgz/fgbz/bz/bzfb/ |
| 行业标准信息公共服务平台 | ⚪ 未探 | — | — | https://hbba.sacinfo.org.cn/stdList |
| 金融标准化技术委员会 | ⚪ 未探 | — | — | http://www.cfstc.org/ |

### 地标（10 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 上海市市场监督管理局 | ⚪ 未探 | — | — | http://scjgj.sh.gov.cn/ |
| 全国标准信息公共服务平台-地方标准(旧路径) | ⚪ 未探 | — | — | https://std.samr.gov.cn/db/dbQuery |
| 北京市市场监督管理局 | ⚪ 未探 | — | — | https://scjgj.beijing.gov.cn/ |
| 四川省市场监督管理局 | ⚪ 未探 | — | — | http://scjgj.sc.gov.cn/scsjgj/c104492/list.shtml |
| 地方标准信息公共服务平台 | ⚪ 未探 | — | — | https://dbba.sacinfo.org.cn/stdList |
| 山东省市场监督管理局 | ⚪ 未探 | — | — | http://amr.shandong.gov.cn/col/col76510/index.html?number=SD1002 |
| 广东省市场监督管理局 | ⚪ 未探 | — | — | https://amr.gd.gov.cn/zwgk/tzgg/index.html |
| 江苏省市场监督管理局 | ⚪ 未探 | — | — | http://scjgj.jiangsu.gov.cn/col/col78963/index.html |
| 浙江省市场监督管理局 / 浙江标准在线 | ⚪ 未探 | — | — | https://zlzx.zjamr.zj.gov.cn/bzzx/public/news/list/lstd/ALL/1.html |
| 辽宁省市场监督管理局 | ⚪ 未探 | — | — | https://scjg.ln.gov.cn/scjdglj/fw/wyb/bz/index.shtml |

### 团标（5 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 中国电子工业标准化技术协会 | ⚪ 未探 | — | — | https://www.cesa.cn/ |
| 中国通信标准化协会 | ⚪ 未探 | — | — | https://www.ccsa.org.cn/standard |
| 企业标准信息公共服务平台 | ⚪ 未探 | — | — | https://www.qybz.org.cn/ |
| 全国团体标准信息平台 | ⚪ 未探 | — | — | https://www.ttbz.org.cn/standard.html |
| 全国标准信息公共服务平台-团体标准 | ⚪ 未探 | — | — | https://std.samr.gov.cn/tb/ |

### 国际（4 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| IEC | ⚪ 未探 | — | — | https://www.iec.ch/ |
| ISO | ⚪ 未探 | — | — | https://www.iso.org/standards.html |
| 全国标准信息公共服务平台-国外标准动态 | ⚪ 未探 | — | — | https://std.samr.gov.cn/gw/news?channelId=87 |
| 全国标准信息公共服务平台-国际标准动态 | ⚪ 未探 | — | — | https://std.samr.gov.cn/gj/news?op=ISO |

### 聚合入口（7 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 国家法律法规数据库-枚举字典 | 🟢 可抓 | 2026-09-18 04:48:42 | 有 | https://flk.npc.gov.cn/law-search/search/enumData |
| 北京市司法局-法律法规规章 | 🔴 不可抓 | — | 有 | https://sfj.beijing.gov.cn/sfj/zwgk/2024zcwj/744120751/index.html |
| 国家法律法规数据库-检索列表 | ⚪ 未探 | — | — | https://flk.npc.gov.cn/search |
| 国家法律法规数据库-详情 | ⚪ 未探 | — | — | https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs=ff808181 |
| 国家法律法规数据库-首页聚合 | ⚪ 未探 | — | — | https://flk.npc.gov.cn/law-search/index/aggregateData |
| 广东人大-广东省法规规章规范性文件数据库 | ⚪ 未探 | — | — | https://www.gdpc.gov.cn/bascdata/ |
| 浙江省政策文件库 | ⚪ 未探 | — | — | https://www.zj.gov.cn/col/col1229577560/index.html |

### 工具/Skill（24 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| @sanmis/crawler | ⚪ 未探 | — | — | https://www.npmjs.com/package/@sanmis/crawler (declared source rep |
| GBMCP | ⚪ 未探 | — | — | https://github.com/LoyDgIk/GBMCP |
| GovPing | ⚪ 未探 | — | — | https://github.com/search?q=GovPing |
| GovPing | ⚪ 未探 | — | — | https://www.npmjs.com/package/govping-mcp-server (declared source  |
| Law-Crawler-RPA-RAG-MCP | ⚪ 未探 | — | — | https://github.com/Yuhamixli/Law-Crawler-RPA-RAG-MCP |
| Law-Crawler-RPA-RAG-MCP | ⚪ 未探 | — | — | https://github.com/Yuhamixli/Law-Crawler-RPA-RAG-MCP |
| National Standard Monitor Skill | ⚪ 未探 | — | — | https://clawhub.ai/sereinone/skills/national-standard-monitor-skil |
| OpenSTD_Spider | ⚪ 未探 | — | — | https://github.com/SocialSisterYi/OpenSTD_Spider |
| RegRadar | ⚪ 未探 | — | — | https://github.com/kingabzpro/RegRadar |
| RegRadar | ⚪ 未探 | — | — | (ambiguous - at least 6 same-named repos, no single authoritative  |
| at-ris-mcp | ⚪ 未探 | — | — | https://github.com/paragraflabs/at-ris-mcp |
| at-ris-mcp | ⚪ 未探 | — | — | https://github.com/paragraflabs/at-ris-mcp |
| changedetection.io | ⚪ 未探 | — | — | https://github.com/dgtlmoon/changedetection.io |
| china-law-search | ⚪ 未探 | — | — | https://github.com/search?q=china-law-search |
| china-law-search | ⚪ 未探 | — | — | (not found) |
| gb-downloader | ⚪ 未探 | — | — | https://github.com/suwadaimyojin/gb-downloader |
| gb688_downloader | ⚪ 未探 | — | — | https://github.com/inntran/gb688_downloader |
| gbqw | ⚪ 未探 | — | — | https://github.com/RhettTien/gbqw |
| legal-database | ⚪ 未探 | — | — | https://github.com/sublatesublate-design/legal-database |
| legal-database | ⚪ 未探 | — | — | (no single canonical repo found) |
| policy-monitor | ⚪ 未探 | — | — | (not found) |
| regwatch-eu | ⚪ 未探 | — | — | https://github.com/scka-de/regwatch-eu |
| standards-version-check | ⚪ 未探 | — | — | https://github.com/cuipointer/ageis (skill at .claude/skills/stand |
| urlwatch | ⚪ 未探 | — | — | https://github.com/thp/urlwatch |

## 三、已知失效（**这些会让覆盖率虚高，优先修/换**）

- `ch:web` **网络逐号补漏搜索（Bing）**：⚠ 在链上但恒 miss：只解 `isinstance(body, dict)` 的 mock 契约（web_fallback.py:53-54），真实 bing HTML 恒 miss；缺口：真实 HTML 响应零解析；无 UA/Referer；无验证码判定；无重试限速

## 四、还没配探针的渠道

共 **103** 条处于「未探」状态（含 4 条我方通路）。
下一步（R3c/R5）：按类别优先级补探针——**锚点必须实测看到过**，不许凭想象写。

