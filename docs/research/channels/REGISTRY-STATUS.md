# 渠道台账状态快照（自动生成，勿手改）

- 生成时间：2026-10-08 18:13:24（本地） · 数据来源：`C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db` 的 `update_channel` 表
- 台账 **280** 条 · 启用 278 条 · **能干活（wired）7** 条 · 已知失效 **0** 条 · 仅登记 262 条
- 已实测：🟢 151 / 🟡 39 / 🔴 61 / ⚪ 未探 29

> ⚠ 两个数字**必须分开读**：`台账条数` 是「我们知道多少渠道」，`能干活条数` 才是「今天真的能用几条」。R1 的实测教训（G5/G6）：13 个适配器只有 8 个在链上，而在链上的 `web`/`govcn` 两根兜底棒在真实 HTML 下恒 miss。

## 一、我方通路（适配器与采集链路）

| 渠道 | 接线 | 有效性 | 上次成功 | 失败原因 | 链接 |
|---|---|---|---|---|---|
| `ch:dbba` 地方标准信息服务平台（sacinfo） | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-23 05:03:02 | — | POST https://dbba.sacinfo.org.cn/stdQueryList（form: current=1&size=20& |
| `ch:govcn` gov.cn 公告检索 + PDF 存档 | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-23 05:03:05 | — | GET https://sousuo.www.gov.cn/sousuo/search.shtml?q=<标准号 标准名>；归档用 tran |
| `ch:hbba` 行业标准信息服务平台（sacinfo） | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-23 05:03:03 | — | POST https://hbba.sacinfo.org.cn/stdQueryList（form: current=1&size=20& |
| `ch:mee` 生态环境部 HJ 标准 | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-23 05:04:00 | — | POST http://datacenter.mee.gov.cn/websjzx/report!list.action?xmlname=1 |
| `ch:ndls` 国家数字标准馆（中国标准化研究院） | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-23 05:03:58 | — | POST https://ndls.cnis.ac.cn/api/standard/list（JSON）+ GET https://ndls |
| `ch:official_gb` 国家标准全文公开系统 | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-23 05:02:59 | — | GET https://openstd.samr.gov.cn/bzgk/std/std_list?searchText=<号>&p.p1= |
| `ch:ttbz` 全国团体标准信息平台 | ✅ 已接线（在 routing 链上） | 🟢 可抓 | 2026-09-23 05:03:59 | — | POST https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/getPorta |
| `ch:announce_sources` 用户自定义公告源（现有台账形态） | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | 用户配置的任意公网 http/https 列表页 URL（app_config 键 announce.sources） |
| `ch:ccs_fetcher` 中国标准服务网 CCS 分类抓取 | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-23 05:03:59 | — | GET https://www.cssn.net.cn/api/cssn/list?keyword=<数字号> |
| `ch:cssn` 中国标准服务网 | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-23 05:03:07 | — | GET https://www.cssn.net.cn/api/standards/list?keyword=<标准号（保留空格）> |
| `ch:discover_search` 找标检索（openstd 分类检索） | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | GET https://openstd.samr.gov.cn/db/search?q=<分类路径 标准>&page=<drill_leve |
| `ch:flk_client` 国家法律法规数据库官方源客户端 | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | POST /law-search/search/list · GET /law-search/search/flfgDetails?bbbs |
| `ch:govcn_client` 国务院政策文件库官方源客户端 | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | GET https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q=…&sea |
| `ch:laws_db` 国家法律法规数据库（flk.npc.gov.cn） | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-23 05:03:02 | — | POST https://flk.npc.gov.cn/law-search/search/list（JSON body，pageNum=1 |
| `ch:mem_gov` 应急管理部 AQ 行业标准公告 | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-23 05:03:07 | — | GET https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/（+ index_N.shtml 分页，逐条公告详 |
| `ch:mohurd` 住建部工程建设标准文告 | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-23 05:03:07 | — | GET https://www.mohurd.gov.cn/gongkai/zc/wgk/（+ index_N.shtml 分页，逐条文告详 |
| `ch:std_samr_hb` 全国标准信息公共服务平台·行业标准目录 | ⚪ 未接线（注册了但巡检不调用） | 🟢 可抓 | 2026-09-23 05:03:03 | — | GET https://std.samr.gov.cn/hb/search/hbPage?searchText=<归一号>&op=&ISSU |
| `ch:web` 网络逐号补漏搜索（Bing） | ⚪ 未接线（注册了但巡检不调用） | ⚪ 未探 | — | — | GET https://www.bing.com/search?q=<标准号 标准名> |

## 二、外部渠道（按类别）

### 法规（74 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 上海市人大-法规公布 | 🟢 可抓 | — | 有 | https://www.shrd.gov.cn/shrd/fggb/fggb.html |
| 上海市人大-法规公布AJAX(TrueCMS) | 🟢 可抓 | — | 有 | https://www.shrd.gov.cn/TrueCMS/messageController/getMessage.do |
| 上海市人民政府-政府规章库 | 🟢 可抓 | 2026-09-23 05:03:08 | 有 | https://www.shanghai.gov.cn/xxzfgzwj/ |
| 上海市人民政府-近期信息公开 | 🟢 可抓 | 2026-09-23 05:03:08 | 有 | https://www.shanghai.gov.cn/nw12344/index.html |
| 上海市司法局-规范性文件 | 🟢 可抓 | — | 有 | https://sfj.sh.gov.cn/2020jcgk_gfxwj/ |
| 中国人大网-法律文件 | 🟢 可抓 | — | — | http://www.npc.gov.cn/npc/c2/c12435/c12488/ |
| 中国人大网-立法 | 🟢 可抓 | — | — | http://www.npc.gov.cn/npc/c2/c183/ |
| 中国人民银行-条法司 | 🟢 可抓 | — | — | http://www.pbc.gov.cn/tiaofasi/144941/index.html |
| 中国政府网-国家规章库 | 🟢 可抓 | 2026-09-23 05:03:17 | 有 | https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm |
| 中国政府网-政策文件库检索 | 🟢 可抓 | 2026-09-23 05:03:17 | 有 | https://www.gov.cn/zhengce/xxgk/ |
| 中国政府网-最新政策静态JSON | 🟢 可抓 | 2026-09-23 05:02:59 | 有 | https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json |
| 中国证监会-法律法规 | 🟢 可抓 | — | — | http://www.csrc.gov.cn/csrc/c101803/common_list.shtml |
| 交通运输部-政府信息公开政策 | 🟢 可抓 | — | — | https://xxgk.mot.gov.cn/zhengce/index.html |
| 交通运输部-规章库 | 🟢 可抓 | — | — | https://xxgk.mot.gov.cn/2020/gz/ |
| 农业农村部-通知公告 | 🟢 可抓 | — | — | http://www.moa.gov.cn/gk/tzgg_1/ |
| 北京市人大 | 🟢 可抓 | 2026-09-23 05:03:08 | 有 | https://www.bjrd.gov.cn/ |
| 北京市人大常委会-重要发布 | 🟢 可抓 | 2026-09-23 05:03:09 | 有 | https://www.bjrd.gov.cn/zyfb/ |
| 北京市人民政府-政策文件 | 🟢 可抓 | 2026-09-23 05:03:09 | 有 | https://www.beijing.gov.cn/zhengce/zhengcefagui/ |
| 发改委-公告 | 🟢 可抓 | — | — | https://www.ndrc.gov.cn/xxgk/zcfb/gg/ |
| 发改委-通知 | 🟢 可抓 | — | — | https://www.ndrc.gov.cn/xxgk/zcfb/tz/ |
| 司法部-国家行政法规库(xzfg) | 🟢 可抓 | 2026-09-23 05:03:06 | 有 | http://xzfg.moj.gov.cn/search2.html |
| 司法部-备案审查 | 🟢 可抓 | 2026-09-23 05:03:20 | 有 | https://www.moj.gov.cn/ |
| 司法部-部门规章栏目 | 🟢 可抓 | 2026-09-23 05:03:10 | 有 | https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzbmgz/ |
| 商务部-政策 | 🟢 可抓 | — | — | https://www.mofcom.gov.cn/zfxxgk/ |
| 国家市场监督管理总局-法规司 | 🟢 可抓 | 2026-09-23 05:03:21 | 有 | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/ |
| 国家法律法规数据库-检索列表API | 🟢 可抓 | — | — | https://flk.npc.gov.cn/law-search/search/list |
| 国家金融监督管理总局 | 🟢 可抓 | — | — | https://www.nfra.gov.cn/cn/view/pages/index/index.html |
| 广东人大-常委会公报 | 🟢 可抓 | — | 有 | https://www.gdpc.gov.cn/gdrdw/rdhy/cwhhy/cwhgb/index.html |
| 广东人大-权威发布公告通知 | 🟢 可抓 | — | 有 | https://www.gdpc.gov.cn/gdrdw/zyfb/ggtz/index.html |
| 广东人大网 | 🟢 可抓 | 2026-09-23 05:03:08 | 有 | https://www.gdpc.gov.cn/ |
| 广东省人民政府-文件库 | 🟢 可抓 | 2026-09-23 05:03:22 | 有 | https://www.gd.gov.cn/zwgk/wjk/qbwj/ |
| 广东省人民政府-粤府令 | 🟢 可抓 | 2026-09-23 05:03:22 | 有 | https://www.gd.gov.cn/zwgk/wjk/qbwj/yfl/index.html |
| 广东省司法厅-政策文件 | 🟢 可抓 | 2026-09-23 05:03:22 | 有 | http://sft.gd.gov.cn/sfw/zwgk/zcwj/ |
| 应急管理部-法律法规 | 🟢 可抓 | 2026-09-23 05:03:06 | 有 | https://www.mem.gov.cn/fw/flfgbz/fg/index.shtml |
| 应急管理部-规章(法定主动公开) | 🟢 可抓 | 2026-09-23 05:03:07 | 有 | https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/ |
| 文化和旅游部-政策法规 | 🟢 可抓 | — | — | https://www.mct.gov.cn/whzx/ |
| 最高人民检察院-法律法规规范性文件 | 🟢 可抓 | 2026-09-23 05:03:23 | 有 | https://www.spp.gov.cn/spp/flfgxwj/ |
| 最高人民法院-司法解释 | 🟢 可抓 | 2026-09-23 05:03:24 | 有 | https://www.court.gov.cn/fabu/gengduo/16.html |
| 水利部-政务公开 | 🟢 可抓 | — | — | http://www.mwr.gov.cn/zwgk/ |
| 浙江省人大 | 🟢 可抓 | 2026-09-23 05:03:07 | 有 | https://www.zjrd.gov.cn/ |
| 浙江省人民政府-政府规章省级有效 | 🟢 可抓 | 2026-09-23 05:03:25 | 有 | https://www.zj.gov.cn/col/col1229836653/index.html |
| 浙江省司法厅 | 🟢 可抓 | 2026-09-23 05:03:27 | 有 | https://sft.zj.gov.cn/ |
| 浙江省司法厅-政策文件 | 🟢 可抓 | 2026-09-23 05:03:27 | 有 | https://sft.zj.gov.cn/col/col1229247318/index.html |
| 生态环境部-法规标准 | 🟢 可抓 | 2026-09-23 05:03:07 | 有 | https://www.mee.gov.cn/ywgz/fgbz/ |
| 科技部-法规政策 | 🟢 可抓 | — | — | https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/ |
| 税务总局-政策 | 🟢 可抓 | — | — | https://www.chinatax.gov.cn/chinatax/n810341/n810755/index.html |
| 自然资源部-通知公告 | 🟢 可抓 | — | — | http://www.mnr.gov.cn/gk/tzgg/ |
| 财政部-政策发布 | 🟢 可抓 | — | — | http://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/ |
| 首都之窗-地方性法规镜像 | 🟢 可抓 | 2026-09-23 05:03:27 | 有 | https://www.beijing.gov.cn/zhengce/dfxfg/ |
| 首都之窗-市政府令(按文号) | 🟢 可抓 | 2026-09-23 05:03:28 | 有 | https://www.beijing.gov.cn/zhengce/zfwj/zfwj2016/szfl/ |
| 首都之窗-政府规章(现行有效) | 🟢 可抓 | 2026-09-23 05:03:28 | 有 | https://www.beijing.gov.cn/gongkai/zfxxgk/zc/gz/ |
| 上海市司法局 | 🔴 不可抓 | — | 有 | https://sft.sh.gov.cn/ |
| 上海市司法局(http) | 🔴 不可抓 | — | — | http://sft.sh.gov.cn/ |
| 交通运输部-政策解读 | 🔴 不可抓 | — | 有 | https://www.mot.gov.cn/zhengcejiedu/ |
| 交通运输部-规章速递 | 🔴 不可抓 | — | — | http://law.mot.gov.cn/listNewLaw.action |
| 人力资源和社会保障部 | 🟡 可疑 | — | 有 | https://www.mohrss.gov.cn/ |
| 人力资源社会保障部-政策法规 | 🟡 可疑 | — | — | http://www.mohrss.gov.cn/xxgk2020/fdzdgknr/zcfg/ |
| 住房和城乡建设部-政策发布 | 🔴 不可抓 | — | 有 | https://www.mohurd.gov.cn/gongkai/zhengce/ |
| 司法部-国家行政法规库入口(实为跳转flk) | 🟡 可疑 | — | 有 | https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzflk/ |
| 商务部-政务公开 | 🔴 不可抓 | — | — | http://www.mofcom.gov.cn/article/zwgk/ |
| 国务院公报 | 🟡 可疑 | 2026-09-23 05:03:20 | 有 | https://www.gov.cn/gongbao/ |
| 国家卫生健康委员会 | 🔴 不可抓 | — | 有 | https://www.nhc.gov.cn/ |
| 国家发展改革委-政策发布 | 🟡 可疑 | — | — | https://www.ndrc.gov.cn/xxgk/zcfb/ |
| 国家税务总局-政策文件 | 🔴 不可抓 | — | — | http://www.chinatax.gov.cn/chinatax/n810341/index.html |
| 工业和信息化部-政策文件 | 🟡 可疑 | — | 有 | https://www.miit.gov.cn/zwgk/zcwj/index.html |
| 市场监管总局-法定主动公开 | 🟡 可疑 | — | — | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/ |
| 教育部-信息公开 | 🟡 可疑 | — | — | http://www.moe.gov.cn/jyb_xxgk/ |
| 浙江人大-法规公告(http) | 🔴 不可抓 | — | — | http://www.zjrd.gov.cn/sylf/fggg/ |
| 浙江省人大-省域立法法规公告 | 🟡 可疑 | — | 有 | https://www.zjrd.gov.cn/sylf/fggg/ |
| 浙江省人大-首页 | 🟡 可疑 | 2026-09-23 05:03:25 | 有 | https://www.zjrd.gov.cn/ |
| 浙江省人民政府-省政府文件 | 🟡 可疑 | — | 有 | https://www.zj.gov.cn/col/col1229019364/index.html |
| 浙江省人民政府-省政府文件栏目 | 🟡 可疑 | — | 有 | https://www.zj.gov.cn/col/col1229019364/index.html |
| 海关总署-法规 | 🔴 不可抓 | — | — | http://www.customs.gov.cn/customs/302249/index.html |
| 科技部-信息公开 | 🟡 可疑 | — | — | https://www.most.gov.cn/xxgk/ |

### 国标（21 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 中国标准在线服务网 | 🟢 可抓 | 2026-09-23 05:03:34 | 有 | https://www.spc.org.cn/standardonline/replace?type=0 |
| 中国标准在线服务网-标准公告 | 🟢 可抓 | — | — | https://www.spc.org.cn/news/stdbzgg |
| 中国标准在线服务网-首页 | 🟢 可抓 | — | — | https://www.spc.org.cn/ |
| 全国标准信息公共服务平台-国家标准公告 | 🟢 可抓 | — | — | https://std.samr.gov.cn/gb.html |
| 全国标准信息公共服务平台-国家标准目录 | 🟢 可抓 | 2026-09-23 05:03:34 | 有 | https://std.samr.gov.cn/gb/gbQuery |
| 全国标准信息公共服务平台-技术委员会 | 🟢 可抓 | — | — | https://std.samr.gov.cn/org |
| 全国标准信息公共服务平台-技术委员会公告 | 🟢 可抓 | — | — | https://std.samr.gov.cn/noc/nocCMR |
| 全国标准信息公共服务平台-标准公告查询 | 🟢 可抓 | — | — | https://std.samr.gov.cn/noc |
| 国家标准全文公开系统 | 🟢 可抓 | 2026-09-23 05:03:35 | 有 | https://openstd.samr.gov.cn/bzgk/std/ |
| 国家标准全文公开系统(index) | 🟢 可抓 | — | — | https://openstd.samr.gov.cn/bzgk/std/index |
| 国家标准批准发布公告 | 🟢 可抓 | 2026-09-23 05:03:35 | 有 | https://std.samr.gov.cn/noc/nocGB |
| 市场监管总局-标准技术管理司 | 🟢 可抓 | — | — | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bzcxs/ |
| 技术委员会公告(sacinfo) | 🟢 可抓 | — | — | http://org.sacinfo.org.cn/tcrm/cmrNotice/announcement/list?menuIte |
| 中国政府网-标准查询 | 🔴 不可抓 | — | — | http://www.gov.cn/fuwu/bzxxcx/bzh.htm |
| 全国专业标准化技术委员会管理系统 | 🟡 可疑 | — | — | http://tc.sacinfo.org.cn/ |
| 全国标准信息公共服务平台(旧域名) | 🔴 不可抓 | — | — | http://www.std.gov.cn/ |
| 国家标准化管理委员会 | 🟡 可疑 | — | 有 | https://www.sac.gov.cn/bzhdt/index.html |
| 国家标准化管理委员会-标准公告查询 | 🟡 可疑 | — | — | https://std.sacinfo.org.cn/PCNoc/queryAll |
| 国家标准化管理委员会-通知公告 | 🟡 可疑 | — | — | https://www.sac.gov.cn/xw/tzgg/ |
| 国家标准委-全文公开(gb688) | 🔴 不可抓 | — | — | http://www.gb688.cn/bzgk/gb/index |
| 市场监管总局-标准技术管理司通知公告 | 🟡 可疑 | — | — | https://www.samr.gov.cn/bzjss/tzgg/index.html |

### 行标（81 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 中华全国供销合作总社 | 🟢 可抓 | — | — | http://www.chinacoop.gov.cn/ |
| 中国地震局 | 🟢 可抓 | — | — | https://www.cea.gov.cn/ |
| 中国标准出版社 | 🟢 可抓 | — | — | http://www.spc.net.cn/ |
| 中国标准化研究院 | 🟢 可抓 | 2026-09-23 05:03:35 | 有 | https://www.cnis.ac.cn/wap/ |
| 中国民用航空局-信息公开 | 🟢 可抓 | — | — | http://www.caac.gov.cn/XXGK/ |
| 中国气象局-标准 | 🟢 可抓 | — | — | http://www.cma.gov.cn/zfxxgk/gknr/flfgbz/bz/ |
| 中国气象局-行业标准 | 🟢 可抓 | — | — | http://www.cma.gov.cn/root7/auto13139/ |
| 交通运输标准化信息系统 | 🟢 可抓 | 2026-09-23 05:03:46 | 有 | https://jtst.mot.gov.cn/search/std?q= |
| 交通运输标准化信息系统-标准公告 | 🟢 可抓 | — | — | https://jtst.mot.gov.cn/noc |
| 住房和城乡建设部标准公告 | 🟢 可抓 | 2026-09-23 05:03:46 | 有 | https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index.html |
| 全国标准信息公共服务平台-行业标准 | 🟢 可抓 | — | — | https://std.samr.gov.cn/hb |
| 农业农村部-政策法规 | 🟢 可抓 | — | — | http://www.moa.gov.cn/gk/zcfg/ |
| 国土资源标准化信息服务平台 | 🟢 可抓 | — | — | http://www.lrs.org.cn/channels/198.html |
| 国家中医药管理局 | 🟢 可抓 | — | — | http://www.natcm.gov.cn/ |
| 国家国防科技工业局 | 🟢 可抓 | — | — | http://www.sastind.gov.cn/ |
| 国家外汇管理局 | 🟢 可抓 | — | — | https://www.safe.gov.cn/ |
| 国家广播电视总局-标准 | 🟢 可抓 | — | — | http://www.nrta.gov.cn/col/col2081/index.html |
| 国家文物局 | 🟢 可抓 | — | — | http://www.ncha.gov.cn/ |
| 国家林业和草原局-公告 | 🟢 可抓 | — | — | https://www.forestry.gov.cn/c/www/gkgjlyjgb.jhtml |
| 国家林业和草原局-公示公告 | 🟢 可抓 | — | — | https://www.forestry.gov.cn/gsgg.jhtml |
| 国家档案局 | 🟢 可抓 | — | — | https://www.saac.gov.cn/ |
| 国家烟草专卖局-标准 | 🟢 可抓 | — | — | http://www.tobacco.gov.cn/ |
| 国家疾病预防控制局 | 🟢 可抓 | — | — | https://www.ndcpa.gov.cn/ |
| 国家矿山安全监察局 | 🟢 可抓 | — | — | https://www.chinamine-safety.gov.cn/ |
| 国家移民管理局 | 🟢 可抓 | — | — | https://www.nia.gov.cn/ |
| 国家粮食和物资储备局 | 🟢 可抓 | — | — | http://www.lswz.gov.cn/ |
| 国家粮食和物资储备局-政策发布 | 🟢 可抓 | — | — | http://www.lswz.gov.cn/html/zcfb/index.shtml |
| 国家统计局 | 🟢 可抓 | — | — | https://www.stats.gov.cn/ |
| 国家能源局-标准管理 | 🟢 可抓 | — | — | https://www.nea.gov.cn/ztzl/nybz/bzgl/index.htm |
| 国家能源局-行业标准查询 | 🟢 可抓 | — | — | https://www.nea.gov.cn/ztzl/nybz/bzgl/hybzcx.htm |
| 国家药品监督管理局 | 🟢 可抓 | — | — | https://www.nmpa.gov.cn/ |
| 国家药监局-公告通告 | 🟢 可抓 | — | — | https://www.nmpa.gov.cn/xxgk/ggtg/ |
| 国家邮政局 | 🟢 可抓 | — | — | https://www.spb.gov.cn/ |
| 国家铁路局 | 🟢 可抓 | — | — | http://www.nra.gov.cn/ |
| 国家食品安全风险评估中心 | 🟢 可抓 | 2026-09-23 05:03:47 | 有 | https://www.cfsa.net.cn/ |
| 工业和信息化部-公告 | 🟢 可抓 | — | — | https://www.miit.gov.cn/zwgk/zcwj/wjfb/gg/ |
| 工信部-科技司文件发布 | 🟢 可抓 | — | — | https://www.miit.gov.cn/jgsj/kjs/wjfb/index.html |
| 工程建设标准化信息网 | 🟢 可抓 | 2026-09-23 05:03:47 | 有 | https://www.ccsn.org.cn/News/More.aspx?ClassID=004001 |
| 应急管理部-AQ行业标准公告 | 🟢 可抓 | — | — | https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/ |
| 标准网(中机生产力促进中心) | 🟢 可抓 | 2026-09-23 05:03:50 | 有 | http://www.bzw.com.cn/ |
| 水利部-技术标准查询 | 🟢 可抓 | — | — | http://gjkj.mwr.gov.cn/jsjd1/bzcx/ |
| 生态环境部-标准发布 | 🟢 可抓 | — | — | https://www.mee.gov.cn/ywgz/fgbz/bz/bzfb/index.shtml |
| 生态环境部-部文件公告 | 🟢 可抓 | — | — | https://www.mee.gov.cn/zcwj/bwj/gg/index.shtml |
| 生态环境部标准 | 🟢 可抓 | 2026-09-23 05:03:51 | 有 | https://www.mee.gov.cn/ywgz/fgbz/bz/bzfb/ |
| 行业标准公告(nocHB) | 🟢 可抓 | — | — | https://std.samr.gov.cn/noc/nocHB |
| 行业标准备案月报(cnas.spc) | 🟢 可抓 | — | — | https://cnas.spc.net.cn/cnas/newinfo/stdbzgg |
| 中国交通运输标准服务平台 | 🔴 不可抓 | — | — | http://jtysbz.com.cn/ |
| 中国标准化研究院 | 🟡 可疑 | — | — | https://www.cnis.ac.cn/ |
| 中国标准服务网(ccsainfo) | 🔴 不可抓 | — | 有 | http://www.ccsainfo.com/ |
| 中国民航标准计量网 | 🔴 不可抓 | — | — | http://www.caac.gov.cn/website/old/BZJL/MHBZ/ |
| 中国电力企业联合会-标准化 | 🟡 可疑 | — | — | http://dls.cec.org.cn/zhongdianlianbiaozhun/ |
| 人力资源和社会保障部-政务公开 | 🟡 可疑 | — | — | http://www.mohrss.gov.cn/gkml/index.html |
| 住建部-工程建设标准文告 | 🟡 可疑 | — | — | https://www.mohurd.gov.cn/gongkai/zc/wgk/ |
| 住建部-标准公告(第2页) | 🔴 不可抓 | — | — | https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index_1.html |
| 体育标准化信息平台 | 🔴 不可抓 | — | — | http://tybz.sport.gov.cn/home/standard |
| 公安部-公共安全行业标准 | 🟡 可疑 | — | — | http://app.mps.gov.cn:9000/gdnps/index.jsp |
| 卫生标准网 | 🔴 不可抓 | — | — | http://www.nhc.gov.cn/zhuz/wjjsbz/wsbz.shtml |
| 卫生标准网(旧) | 🔴 不可抓 | — | — | http://wsbz.nhfpc.gov.cn/wsbzw/ |
| 商务部-流通标准 | 🔴 不可抓 | — | — | http://ltbzh.mofcom.gov.cn/ltbzh_index.shtml |
| 国家卫生健康委-食品安全标准 | 🔴 不可抓 | — | — | https://www.nhc.gov.cn/sps/new_index.shtml |
| 国家卫生健康委-食品安全标准司 | 🔴 不可抓 | — | — | http://www.nhc.gov.cn/sps/new_index.shtml |
| 国家工程建设标准化信息网 | 🔴 不可抓 | — | — | http://www.ccsn.gov.cn/ |
| 国家林业和草原局-公告公示 | 🔴 不可抓 | — | — | https://www.forestry.gov.cn/lyj/1/gsgg/ |
| 国家林业标准化管理信息系统 | 🔴 不可抓 | — | — | http://124.205.185.55/bzk/search_standard_catalog.asp |
| 国家消防救援局 | 🟡 可疑 | — | — | https://www.119.gov.cn/ |
| 国家能源局公告 | 🟡 可疑 | 2026-09-23 05:03:46 | 有 | https://www.nea.gov.cn/policy/gg.htm |
| 国家铁路局-标准规范 | 🔴 不可抓 | — | — | http://www.nra.gov.cn/jgzf/bzgf/ |
| 工信部-文件查询 | 🟡 可疑 | — | — | https://www.miit.gov.cn/gyhxxhbwjcx/ |
| 工信部-标准库 | 🔴 不可抓 | — | — | http://www.miit.gov.cn/n1146295/n1146567/index.html |
| 工信部标准信息服务平台 | 🟡 可疑 | — | 有 | https://std.miit.gov.cn/ |
| 应急管理部标准 | 🟡 可疑 | — | 有 | https://www.mem.gov.cn/fw/flfgbz/bz/ |
| 测绘地理信息标准化服务平台 | 🔴 不可抓 | — | — | http://bzgk.nasg.gov.cn/ |
| 海洋标准化信息系统 | 🔴 不可抓 | — | — | http://www.ncosm.org.cn/ncosm/ |
| 生态环境部-科技标准司 | 🔴 不可抓 | — | — | http://kjs.mee.gov.cn/hjbhbz/ |
| 行业标准信息公共服务平台 | 🟡 可疑 | 2026-09-23 05:03:51 | 有 | https://hbba.sacinfo.org.cn/stdList |
| 行业标准信息服务平台-公告/计划 | 🟡 可疑 | — | — | https://hbba.sacinfo.org.cn/snList |
| 金融标准全文公开系统 | 🟡 可疑 | — | — | https://cfstc.pbc.gov.cn/bzgk/ |
| 金融标准化技术委员会 | 🔴 不可抓 | — | 有 | http://www.cfstc.org/ |
| 金融标准化技术委员会 | 🟡 可疑 | — | — | https://cfstc.pbc.gov.cn/ |
| 金融标准化技术委员会-标准公开 | 🔴 不可抓 | — | — | http://www.cfstc.org/bzgk/gk |
| 食品安全国家标准数据检索平台 | 🔴 不可抓 | — | — | http://bz.cfsa.net.cn/db |

### 地标（42 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 上海市市场监督管理局 | 🟢 可抓 | 2026-09-23 05:03:28 | 有 | http://scjgj.sh.gov.cn/ |
| 全国标准信息公共服务平台-地方标准(旧路径) | 🟢 可抓 | 2026-09-23 05:03:28 | 有 | https://std.samr.gov.cn/db/dbQuery |
| 全国标准信息公共服务平台-地方标准公告 | 🟢 可抓 | — | — | https://std.samr.gov.cn/db |
| 北京市市场监督管理局 | 🟢 可抓 | 2026-09-23 05:03:29 | 有 | https://scjgj.beijing.gov.cn/ |
| 四川省市场监督管理局 | 🟢 可抓 | 2026-09-23 05:03:30 | 有 | http://scjgj.sc.gov.cn/scsjgj/c104492/list.shtml |
| 地方标准备案公告(nocDB) | 🟢 可抓 | — | — | https://std.samr.gov.cn/noc/nocDB |
| 山东省市场监督管理局 | 🟢 可抓 | 2026-09-23 05:03:31 | 有 | http://amr.shandong.gov.cn/col/col76510/index.html?number=SD1002 |
| 广东省市场监督管理局 | 🟢 可抓 | 2026-09-23 05:03:33 | 有 | https://amr.gd.gov.cn/zwgk/tzgg/index.html |
| 江苏省市场监督管理局 | 🟢 可抓 | 2026-09-23 05:03:33 | 有 | http://scjgj.jiangsu.gov.cn/col/col78963/index.html |
| 浙江标准在线-标准查询 | 🟢 可抓 | — | — | https://zlzx.zjamr.zj.gov.cn/bzzx/public/std/list/ALL/1.html |
| 浙江省市场监督管理局 / 浙江标准在线 | 🟢 可抓 | 2026-09-23 05:03:34 | 有 | https://zlzx.zjamr.zj.gov.cn/bzzx/public/news/list/lstd/ALL/1.html |
| 辽宁省市场监督管理局 | 🟢 可抓 | 2026-09-23 05:03:34 | 有 | https://scjg.ln.gov.cn/scjdglj/fw/wyb/bz/index.shtml |
| 上海市地方标准 | 🔴 不可抓 | — | — | http://www.cnsis.org.cn/law/LawQueryServlet |
| 云南省地方标准 | 🔴 不可抓 | — | — | http://222.172.223.74:8090/web/guest/-4 |
| 内蒙古地方标准 | 🔴 不可抓 | — | — | http://www.imisinfo.org.cn/ |
| 北京市地方标准 | 🔴 不可抓 | — | — | http://innerapp.capital-std.com.cn/outerApp/standardSearchAction.d |
| 吉林省地方标准 | 🔴 不可抓 | — | — | http://221.8.65.189/stdcore/standard/info/findLocalStandard.do |
| 四川省地方标准 | 🔴 不可抓 | — | — | http://118.114.77.13/bzwxup/stdsearch.jsp |
| 地方标准信息公共服务平台 | 🟡 可疑 | 2026-09-23 05:03:31 | 有 | https://dbba.sacinfo.org.cn/stdList |
| 天津市地方标准 | 🔴 不可抓 | — | — | http://60.29.186.229/wenxianpdf/c_gonggao4.asp |
| 宁夏地方标准 | 🔴 不可抓 | — | — | http://www.nstd.org.cn/ |
| 安徽省地方标准 | 🔴 不可抓 | — | — | http://bzxx.ahbz.org.cn/search_list.html |
| 山东省地方标准 | 🟡 可疑 | — | — | http://www.bz100.cn/member/standard/standard!getfreedb.action |
| 山西省地方标准 | 🔴 不可抓 | — | — | http://bqts.gov.cn/office/show.action?alias=bzhc |
| 广东省地方标准 | 🔴 不可抓 | — | — | http://gdstandard.gdqts.gov.cn:8089/gdzj-lsips/modules/details/ope |
| 江苏省地方标准 | 🔴 不可抓 | — | — | http://218.94.159.231:8012/zjkms/kms/publish.rkt?type_code=gy |
| 江西省地方标准 | 🟡 可疑 | — | — | http://www.jxbz.org.cn/list.aspx?nid=11 |
| 河北省地方标准 | 🔴 不可抓 | — | — | http://www.bzsb.info/ |
| 河南省地方标准 | 🔴 不可抓 | — | — | http://www.hndb41.com/publish/index.jhtml |
| 浙江省地方标准(旧) | 🔴 不可抓 | — | — | http://db33.sinostd.com/stdlist.aspx |
| 海南省地方标准 | 🔴 不可抓 | — | — | http://qtsb.hainan.gov.cn/ywdt/dfbz/ |
| 湖北省地方标准 | 🔴 不可抓 | — | — | http://223.75.53.52:81/finddbSearch |
| 湖南省地方标准 | 🔴 不可抓 | — | — | http://db43.hnbzw.com/StdSearch.aspx |
| 甘肃省地方标准 | 🟡 可疑 | — | — | http://www.gsdfbz.cn |
| 福建省地方标准 | 🔴 不可抓 | — | — | http://pt.fjbz.org.cn:8060/StandardSearch/StdSearch.aspx |
| 西藏地方标准 | 🔴 不可抓 | — | — | http://www.xzzj.gov.cn/xzzj/bsdt/dfbzfb/list/ |
| 贵州省地方标准 | 🔴 不可抓 | — | — | http://cloud.gzqts.gov.cn/dfbz/index.action |
| 辽宁省地方标准 | 🔴 不可抓 | — | — | http://218.60.145.253/ywcx/cx/listAction.do?key=011 |
| 重庆市地方标准 | 🔴 不可抓 | — | — | http://113.204.47.237:81/SharePage/bzgkBzjs.htm?code=bzgk |
| 陕西省地方标准 | 🔴 不可抓 | — | — | http://219.144.196.28/std/db_std.asp |
| 青海省地方标准 | 🔴 不可抓 | — | — | http://125.72.41.89:8008/home/res/search?keywords=DB |
| 黑龙江省地方标准 | 🔴 不可抓 | — | — | http://www.hljqts.gov.cn/ |

### 团标（9 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 中国工程建设标准化协会 | 🟢 可抓 | — | — | http://www.cecs.org.cn/ |
| 中国标准化协会 | 🟢 可抓 | — | — | http://www.china-cas.org/ |
| 中国通信标准化协会 | 🟢 可抓 | 2026-09-23 05:03:57 | 有 | https://www.ccsa.org.cn/standard |
| 企业标准信息公共服务平台 | 🟢 可抓 | — | 有 | https://www.qybz.org.cn/ |
| 全国团体标准信息平台 | 🟢 可抓 | 2026-09-23 05:03:58 | 有 | https://www.ttbz.org.cn/standard.html |
| 全国团体标准信息平台-首页 | 🟢 可抓 | — | — | https://www.ttbz.org.cn/ |
| 全国标准信息公共服务平台-团体标准 | 🟢 可抓 | 2026-09-23 05:03:58 | 有 | https://std.samr.gov.cn/tb/ |
| 中国电子工业标准化技术协会 | 🟡 可疑 | — | 有 | https://www.cesa.cn/ |
| 团体标准公告(nocTB) | 🔴 不可抓 | — | — | https://std.samr.gov.cn/noc/nocTB |

### 国际（4 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| ISO | 🟢 可抓 | 2026-09-23 05:03:54 | 有 | https://www.iso.org/standards.html |
| 全国标准信息公共服务平台-国外标准动态 | 🟢 可抓 | 2026-09-23 05:03:55 | 有 | https://std.samr.gov.cn/gw/news?channelId=87 |
| 全国标准信息公共服务平台-国际标准动态 | 🟢 可抓 | 2026-09-23 05:03:55 | 有 | https://std.samr.gov.cn/gj/news?op=ISO |
| IEC | 🟡 可疑 | — | 有 | https://www.iec.ch/ |

### 聚合入口（7 条）

| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |
|---|---|---|---|---|
| 北京市司法局-法律法规规章 | 🟢 可抓 | — | 有 | https://sfj.beijing.gov.cn/sfj/zwgk/2024zcwj/744120751/index.html |
| 国家法律法规数据库-枚举字典 | 🟢 可抓 | 2026-09-23 05:03:01 | 有 | https://flk.npc.gov.cn/law-search/search/enumData |
| 国家法律法规数据库-详情 | 🟢 可抓 | 2026-09-23 05:03:15 | 有 | https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs=ff808181 |
| 国家法律法规数据库-首页聚合 | 🟢 可抓 | 2026-09-23 05:03:16 | 有 | https://flk.npc.gov.cn/law-search/index/aggregateData |
| 广东人大-广东省法规规章规范性文件数据库 | 🟢 可抓 | 2026-09-23 05:03:17 | 有 | https://www.gdpc.gov.cn/bascdata/ |
| 浙江省政策文件库 | 🟢 可抓 | 2026-09-23 05:03:17 | 有 | https://www.zj.gov.cn/col/col1229577560/index.html |
| 国家法律法规数据库-检索列表 | 🟡 可疑 | 2026-09-23 05:03:14 | 有 | https://flk.npc.gov.cn/search |

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

## 四、还没定论的渠道（⚠ 三种处境**必须分开读**）

- **已配探针、还没探过**：0 条 —— 这是「欠账」，下一轮就该探完；
- **只探到连通性**：0 条 —— 渠道**回 200 了**，但我们没给它配语义期望（失败原因列写 `no_anchor_configured`）⇒ 它**不算「可抓」**，也不算欠账；
- **按设计没有探针目标**：29 条 —— 代码仓库（tool）/我方代码通路（internal）等，
  它们不是「没轮到」，而是「这个对象没有独立可探的页面/接口」；
- 合计 ⚪ 未探 **29** 条（面板上对最后一种会标「无探针」）。

下一步（R6 起）：按类别优先级补探针——**锚点必须实测看到过**（逐字子串，不许实体解码/折叠空白）；
可重复生成：`.venv\Scripts\python.exe scripts\channel-anchor-measure.py <channel_id>`。

按设计无探针的渠道：

- `ch:announce_sources`（我方通路）用户自定义公告源（现有台账形态）
- `ch:discover_search`（我方通路）找标检索（openstd 分类检索）
- `ch:flk_client`（我方通路）国家法律法规数据库官方源客户端
- `ch:govcn_client`（我方通路）国务院政策文件库官方源客户端
- `ch:web`（我方通路）网络逐号补漏搜索（Bing）
- `seed:law-cn:at-ris-mcp`（工具/Skill）at-ris-mcp
- `seed:law-cn:china-law-search`（工具/Skill）china-law-search
- `seed:law-cn:govping`（工具/Skill）GovPing
- `seed:law-cn:law-crawler-rpa-rag-mcp`（工具/Skill）Law-Crawler-RPA-RAG-MCP
- `seed:law-cn:legal-database`（工具/Skill）legal-database
- `seed:law-cn:regradar`（工具/Skill）RegRadar
- `tool:at-ris-mcp`（工具/Skill）at-ris-mcp
- `tool:changedetection-io`（工具/Skill）changedetection.io
- `tool:china-law-search`（工具/Skill）china-law-search
- `tool:gb-downloader`（工具/Skill）gb-downloader
- `tool:gb688_downloader`（工具/Skill）gb688_downloader
- `tool:gbmcp`（工具/Skill）GBMCP
- `tool:gbqw`（工具/Skill）gbqw
- `tool:govping`（工具/Skill）GovPing
- `tool:law-crawler-rpa-rag-mcp`（工具/Skill）Law-Crawler-RPA-RAG-MCP
- `tool:legal-database`（工具/Skill）legal-database
- `tool:national-standard-monitor-skill`（工具/Skill）National Standard Monitor Skill
- `tool:openstd_spider`（工具/Skill）OpenSTD_Spider
- `tool:policy-monitor`（工具/Skill）policy-monitor
- `tool:regradar`（工具/Skill）RegRadar
- `tool:regwatch-eu`（工具/Skill）regwatch-eu
- `tool:sanmis-crawler`（工具/Skill）@sanmis/crawler
- `tool:standards-version-check`（工具/Skill）standards-version-check
- `tool:urlwatch`（工具/Skill）urlwatch

