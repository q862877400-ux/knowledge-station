# 法规/标准发布源路径总表（2026-10-08 实测）

> 对象：**会发布「法律法规 / 国家标准 / 行业标准 / 团体标准」更新公告**的官方入口。
> 方法：逐条真机抓取（curl_cffi chrome TLS 指纹，走本机代理），再用**生产解析器**
> `src/core/update/announce.py::parse_list_page` 判定「能不能真抓到条目」。
> 判据：`有效` = 解析出 ≥5 条；`边缘` = 1~4 条；`接口` = 返回 JSON；
> `空壳/JS壳` = HTTP 200 但解析 0 条（需换入口）；`被拦` = 403/412 WAF；`不通` = 超时/502。

**实测 236 条**：有效 110 · 边缘 21 · 接口 6 · 空壳/JS壳 35 · 被拦 7 · 不通/失效 54 · 异常 3

## 一、有效路径（按四类）

### 法律法规（50）

| 状态 | 名称 | 解析条目 | URL |
|---|---|---|---|
| 有效 | 中国政府网-政策文件库检索 | 50 | https://www.gov.cn/zhengce/xxgk/ |
| 有效 | 中国证监会-法律法规 | 50 | http://www.csrc.gov.cn/csrc/c101803/common_list.shtml |
| 有效 | 农业农村部-通知公告 | 50 | http://www.moa.gov.cn/gk/tzgg_1/ |
| 有效 | 北京市人大常委会-重要发布 | 50 | https://www.bjrd.gov.cn/zyfb/ |
| 有效 | 北京市人民政府-政策文件 | 50 | https://www.beijing.gov.cn/zhengce/zhengcefagui/ |
| 有效 | 司法部-备案审查 | 50 | https://www.moj.gov.cn/ |
| 有效 | 广东人大网 | 50 | https://www.gdpc.gov.cn/ |
| 有效 | 文化和旅游部-政策法规 | 50 | https://www.mct.gov.cn/whzx/ |
| 有效 | 最高人民检察院-法律法规规范性文件 | 50 | https://www.spp.gov.cn/spp/flfgxwj/ |
| 有效 | 浙江省司法厅 | 50 | https://sft.zj.gov.cn/ |
| 有效 | 生态环境部-法规标准 | 50 | https://www.mee.gov.cn/ywgz/fgbz/ |
| 有效 | 首都之窗-市政府令(按文号) | 50 | https://www.beijing.gov.cn/zhengce/zfwj/zfwj2016/szfl/ |
| 有效 | 自然资源部-通知公告 | 49 | http://www.mnr.gov.cn/gk/tzgg/ |
| 有效 | 水利部-政务公开 | 45 | http://www.mwr.gov.cn/zwgk/ |
| 有效 | 发改委-通知 | 44 | https://www.ndrc.gov.cn/xxgk/zcfb/tz/ |
| 有效 | 税务总局-政策 | 41 | https://www.chinatax.gov.cn/chinatax/n810341/n810755/index.html |
| 有效 | 应急管理部-法律法规 | 40 | https://www.mem.gov.cn/fw/flfgbz/fg/index.shtml |
| 有效 | 交通运输部-政府信息公开政策 | 38 | https://xxgk.mot.gov.cn/zhengce/index.html |
| 有效 | 广东省司法厅-政策文件 | 37 | http://sft.gd.gov.cn/sfw/zwgk/zcwj/ |
| 有效 | 中国人民银行-条法司 | 35 | http://www.pbc.gov.cn/tiaofasi/144941/index.html |
| 有效 | 北京市人大 | 35 | https://www.bjrd.gov.cn/ |
| 有效 | 发改委-公告 | 34 | https://www.ndrc.gov.cn/xxgk/zcfb/gg/ |
| 有效 | 广东省人民政府-文件库 | 32 | https://www.gd.gov.cn/zwgk/wjk/qbwj/ |
| 有效 | 广东省人民政府-粤府令 | 32 | https://www.gd.gov.cn/zwgk/wjk/qbwj/yfl/index.html |
| 有效 | 中国人大网-立法 | 30 | http://www.npc.gov.cn/npc/c2/c183/ |
| 有效 | 广东人大-权威发布公告通知 | 30 | https://www.gdpc.gov.cn/gdrdw/zyfb/ggtz/index.html |
| 有效 | 上海市人大-法规公布 | 29 | https://www.shrd.gov.cn/shrd/fggb/fggb.html |
| 有效 | 中国人大网-法律文件 | 29 | http://www.npc.gov.cn/npc/c2/c12435/c12488/ |
| 有效 | 司法部-国家行政法规库(xzfg) | 29 | http://xzfg.moj.gov.cn/search2.html |
| 有效 | 财政部-政策发布 | 25 | http://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/ |
| 有效 | 首都之窗-地方性法规镜像 | 25 | https://www.beijing.gov.cn/zhengce/dfxfg/ |
| 有效 | 最高人民法院-司法解释 | 23 | https://www.court.gov.cn/fabu/gengduo/16.html |
| 有效 | 上海市人民政府-近期信息公开 | 21 | https://www.shanghai.gov.cn/nw12344/index.html |
| 有效 | 上海市司法局-规范性文件 | 20 | https://sfj.sh.gov.cn/2020jcgk_gfxwj/ |
| 有效 | 浙江省司法厅-政策文件 | 19 | https://sft.zj.gov.cn/col/col1229247318/index.html |
| 有效 | 科技部-法规政策 | 18 | https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/ |
| 有效 | 交通运输部-规章库 | 15 | https://xxgk.mot.gov.cn/2020/gz/ |
| 有效 | 司法部-部门规章栏目 | 15 | https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzbmgz/ |
| 有效 | 应急管理部-规章(法定主动公开) | 15 | https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/ |
| 有效 | 首都之窗-政府规章(现行有效) | 15 | https://www.beijing.gov.cn/gongkai/zfxxgk/zc/gz/ |
| 有效 | 上海市人民政府-政府规章库 | 10 | https://www.shanghai.gov.cn/xxzfgzwj/ |
| 有效 | 广东人大-常委会公报 | 10 | https://www.gdpc.gov.cn/gdrdw/rdhy/cwhhy/cwhgb/index.html |
| 有效 | 浙江省人民政府-政府规章省级有效 | 10 | https://www.zj.gov.cn/col/col1229836653/index.html |
| 有效 | 国家金融监督管理总局 | 7 | https://www.nfra.gov.cn/cn/view/pages/index/index.html |
| 有效 | 中国政府网-国家规章库 | 6 | https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm |
| 有效 | 商务部-政策 | 5 | https://www.mofcom.gov.cn/zfxxgk/ |
| 边缘 | 国家市场监督管理总局-法规司 | 2 | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/ |
| 接口 | 上海市人大-法规公布AJAX(TrueCMS) | JSON | https://www.shrd.gov.cn/TrueCMS/messageController/getMessage.do |
| 接口 | 中国政府网-最新政策静态JSON | JSON | https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json |
| 接口 | 国家法律法规数据库-检索列表API | JSON | https://flk.npc.gov.cn/law-search/search/list |

### 国家标准（13）

| 状态 | 名称 | 解析条目 | URL |
|---|---|---|---|
| 有效 | 全国标准信息公共服务平台-国家标准公告 | 50 | https://std.samr.gov.cn/gb.html |
| 有效 | 技术委员会公告(sacinfo) | 50 | http://org.sacinfo.org.cn/tcrm/cmrNotice/announcement/list?menuItem=11 |
| 有效 | 中国标准在线服务网-首页 | 39 | https://www.spc.org.cn/ |
| 有效 | 全国标准信息公共服务平台-标准公告查询 | 30 | https://std.samr.gov.cn/noc |
| 有效 | 全国标准信息公共服务平台-技术委员会 | 25 | https://std.samr.gov.cn/org |
| 有效 | 中国标准在线服务网 | 15 | https://www.spc.org.cn/standardonline/replace?type=0 |
| 有效 | 中国标准在线服务网-标准公告 | 15 | https://www.spc.org.cn/news/stdbzgg |
| 有效 | 国家标准全文公开系统 | 9 | https://openstd.samr.gov.cn/bzgk/std/ |
| 有效 | 国家标准全文公开系统(index) | 9 | https://openstd.samr.gov.cn/bzgk/std/index |
| 边缘 | 国家标准批准发布公告 | 4 | https://std.samr.gov.cn/noc/nocGB |
| 边缘 | 全国标准信息公共服务平台-国家标准目录 | 3 | https://std.samr.gov.cn/gb/gbQuery |
| 边缘 | 全国标准信息公共服务平台-技术委员会公告 | 3 | https://std.samr.gov.cn/noc/nocCMR |
| 边缘 | 市场监管总局-标准技术管理司 | 2 | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bzcxs/ |

### 行业标准（46）

| 状态 | 名称 | 解析条目 | URL |
|---|---|---|---|
| 有效 | 中国地震局 | 50 | https://www.cea.gov.cn/ |
| 有效 | 中国标准化研究院 | 50 | https://www.cnis.ac.cn/wap/ |
| 有效 | 中国气象局-行业标准 | 50 | http://www.cma.gov.cn/root7/auto13139/ |
| 有效 | 农业农村部-政策法规 | 50 | http://www.moa.gov.cn/gk/zcfg/ |
| 有效 | 国家外汇管理局 | 50 | https://www.safe.gov.cn/ |
| 有效 | 国家文物局 | 50 | http://www.ncha.gov.cn/ |
| 有效 | 国家档案局 | 50 | https://www.saac.gov.cn/ |
| 有效 | 国家烟草专卖局-标准 | 50 | http://www.tobacco.gov.cn/ |
| 有效 | 国家矿山安全监察局 | 50 | https://www.chinamine-safety.gov.cn/ |
| 有效 | 国家移民管理局 | 50 | https://www.nia.gov.cn/ |
| 有效 | 国家粮食和物资储备局 | 50 | http://www.lswz.gov.cn/ |
| 有效 | 国家统计局 | 50 | https://www.stats.gov.cn/ |
| 有效 | 国家药品监督管理局 | 50 | https://www.nmpa.gov.cn/ |
| 有效 | 国家邮政局 | 50 | https://www.spb.gov.cn/ |
| 有效 | 国家铁路局 | 50 | http://www.nra.gov.cn/ |
| 有效 | 国家食品安全风险评估中心 | 50 | https://www.cfsa.net.cn/ |
| 有效 | 国家中医药管理局 | 49 | http://www.natcm.gov.cn/ |
| 有效 | 中国标准出版社 | 45 | http://www.spc.net.cn/ |
| 有效 | 标准网(中机生产力促进中心) | 42 | http://www.bzw.com.cn/ |
| 有效 | 生态环境部-标准发布 | 35 | https://www.mee.gov.cn/ywgz/fgbz/bz/bzfb/index.shtml |
| 有效 | 生态环境部-部文件公告 | 35 | https://www.mee.gov.cn/zcwj/bwj/gg/index.shtml |
| 有效 | 生态环境部标准 | 35 | https://www.mee.gov.cn/ywgz/fgbz/bz/bzfb/ |
| 有效 | 国家药监局-公告通告 | 32 | https://www.nmpa.gov.cn/xxgk/ggtg/ |
| 有效 | 国家林业和草原局-公告 | 30 | https://www.forestry.gov.cn/c/www/gkgjlyjgb.jhtml |
| 有效 | 国家林业和草原局-公示公告 | 28 | https://www.forestry.gov.cn/gsgg.jhtml |
| 有效 | 国家国防科技工业局 | 25 | http://www.sastind.gov.cn/ |
| 有效 | 国家粮食和物资储备局-政策发布 | 24 | http://www.lswz.gov.cn/html/zcfb/index.shtml |
| 有效 | 全国标准信息公共服务平台-行业标准 | 23 | https://std.samr.gov.cn/hb |
| 有效 | 国家能源局-标准管理 | 23 | https://www.nea.gov.cn/ztzl/nybz/bzgl/index.htm |
| 有效 | 中国气象局-标准 | 20 | http://www.cma.gov.cn/zfxxgk/gknr/flfgbz/bz/ |
| 有效 | 工程建设标准化信息网 | 20 | https://www.ccsn.org.cn/News/More.aspx?ClassID=004001 |
| 有效 | 应急管理部-AQ行业标准公告 | 20 | https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/ |
| 有效 | 中国民用航空局-信息公开 | 19 | http://www.caac.gov.cn/XXGK/ |
| 有效 | 水利部-技术标准查询 | 14 | http://gjkj.mwr.gov.cn/jsjd1/bzcx/ |
| 有效 | 国家广播电视总局-标准 | 10 | http://www.nrta.gov.cn/col/col2081/index.html |
| 有效 | 交通运输标准化信息系统-标准公告 | 7 | https://jtst.mot.gov.cn/noc |
| 有效 | 国家疾病预防控制局 | 6 | https://www.ndcpa.gov.cn/ |
| 有效 | 交通运输标准化信息系统 | 5 | https://jtst.mot.gov.cn/search/std?q= |
| 有效 | 行业标准备案月报(cnas.spc) | 5 | https://cnas.spc.net.cn/cnas/newinfo/stdbzgg |
| 边缘 | 国土资源标准化信息服务平台 | 3 | http://www.lrs.org.cn/channels/198.html |
| 边缘 | 工信部-科技司文件发布 | 3 | https://www.miit.gov.cn/jgsj/kjs/wjfb/index.html |
| 边缘 | 行业标准公告(nocHB) | 3 | https://std.samr.gov.cn/noc/nocHB |
| 边缘 | 国家能源局-行业标准查询 | 2 | https://www.nea.gov.cn/ztzl/nybz/bzgl/hybzcx.htm |
| 边缘 | 中华全国供销合作总社 | 1 | http://www.chinacoop.gov.cn/ |
| 边缘 | 住房和城乡建设部标准公告 | 1 | https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index.html |
| 边缘 | 工业和信息化部-公告 | 1 | https://www.miit.gov.cn/zwgk/zcwj/wjfb/gg/ |

### 团体标准（7）

| 状态 | 名称 | 解析条目 | URL |
|---|---|---|---|
| 有效 | 中国工程建设标准化协会 | 50 | http://www.cecs.org.cn/ |
| 有效 | 中国标准化协会 | 50 | http://www.china-cas.org/ |
| 有效 | 全国团体标准信息平台-首页 | 50 | https://www.ttbz.org.cn/ |
| 有效 | 企业标准信息公共服务平台 | 20 | https://www.qybz.org.cn/ |
| 有效 | 全国团体标准信息平台 | 10 | https://www.ttbz.org.cn/standard.html |
| 边缘 | 全国标准信息公共服务平台-团体标准 | 3 | https://std.samr.gov.cn/tb/ |
| 边缘 | 中国通信标准化协会 | 2 | https://www.ccsa.org.cn/standard |

### 地方标准（12）

| 状态 | 名称 | 解析条目 | URL |
|---|---|---|---|
| 有效 | 北京市市场监督管理局 | 50 | https://scjgj.beijing.gov.cn/ |
| 有效 | 山东省市场监督管理局 | 50 | http://amr.shandong.gov.cn/col/col76510/index.html?number=SD1002 |
| 有效 | 广东省市场监督管理局 | 46 | https://amr.gd.gov.cn/zwgk/tzgg/index.html |
| 有效 | 辽宁省市场监督管理局 | 33 | https://scjg.ln.gov.cn/scjdglj/fw/wyb/bz/index.shtml |
| 有效 | 四川省市场监督管理局 | 24 | http://scjgj.sc.gov.cn/scsjgj/c104492/list.shtml |
| 有效 | 上海市市场监督管理局 | 15 | http://scjgj.sh.gov.cn/ |
| 有效 | 全国标准信息公共服务平台-地方标准公告 | 14 | https://std.samr.gov.cn/db |
| 有效 | 浙江省市场监督管理局 / 浙江标准在线 | 13 | https://zlzx.zjamr.zj.gov.cn/bzzx/public/news/list/lstd/ALL/1.html |
| 有效 | 江苏省市场监督管理局 | 5 | http://scjgj.jiangsu.gov.cn/col/col78963/index.html |
| 边缘 | 全国标准信息公共服务平台-地方标准(旧路径) | 3 | https://std.samr.gov.cn/db/dbQuery |
| 边缘 | 地方标准备案公告(nocDB) | 3 | https://std.samr.gov.cn/noc/nocDB |
| 边缘 | 浙江标准在线-标准查询 | 3 | https://zlzx.zjamr.zj.gov.cn/bzzx/public/std/list/ALL/1.html |

### 国际标准（3）

| 状态 | 名称 | 解析条目 | URL |
|---|---|---|---|
| 有效 | ISO | 50 | https://www.iso.org/standards.html |
| 边缘 | 全国标准信息公共服务平台-国外标准动态 | 3 | https://std.samr.gov.cn/gw/news?channelId=87 |
| 边缘 | 全国标准信息公共服务平台-国际标准动态 | 3 | https://std.samr.gov.cn/gj/news?op=ISO |

### 聚合入口（6）

| 状态 | 名称 | 解析条目 | URL |
|---|---|---|---|
| 有效 | 北京市司法局-法律法规规章 | 24 | https://sfj.beijing.gov.cn/sfj/zwgk/2024zcwj/744120751/index.html |
| 边缘 | 广东人大-广东省法规规章规范性文件数据库 | 3 | https://www.gdpc.gov.cn/bascdata/ |
| 边缘 | 浙江省政策文件库 | 1 | https://www.zj.gov.cn/col/col1229577560/index.html |
| 接口 | 国家法律法规数据库-枚举字典 | JSON | https://flk.npc.gov.cn/law-search/search/enumData |
| 接口 | 国家法律法规数据库-详情 | JSON | https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs=ff8081819ff541ea01a07eb41e2709fb |
| 接口 | 国家法律法规数据库-首页聚合 | JSON | https://flk.npc.gov.cn/law-search/index/aggregateData |

## 二、无效路径与抢救结论

| 原状态 | 名称 | URL | 结论 |
|---|---|---|---|
| 空壳 | 国家法律法规数据库-检索列表 | https://flk.npc.gov.cn/search | — |
| 被拦 | 住房和城乡建设部-政策发布 | https://www.mohurd.gov.cn/gongkai/zhengce/ | **WAF 403**：政策页被拦；标准公告 `/gongkai/fdzdgknr/bzgg/` 可用 |
| 被拦 | 国家卫生健康委员会 | https://www.nhc.gov.cn/ | **WAF 412**：chrome 指纹+会话预热均被挡 ⇒ 需无头浏览器 |
| 被拦 | 海关总署-法规 | http://www.customs.gov.cn/customs/302249/index.html | **WAF 412**：同上 |
| 不通 | 上海市司法局 | https://sft.sh.gov.cn/ | **已救活** → `sfj.sh.gov.cn/2020jcgk_gfxwj/`（20条） |
| 不通 | 上海市司法局(http) | http://sft.sh.gov.cn/ | — |
| 不通 | 交通运输部-规章速递 | http://law.mot.gov.cn/listNewLaw.action | — |
| 不通 | 商务部-政务公开 | http://www.mofcom.gov.cn/article/zwgk/ | **部分救活** → `/zfxxgk/`（5条） |
| 不通 | 浙江人大-法规公告(http) | http://www.zjrd.gov.cn/sylf/fggg/ | — |
| 空壳 | 人力资源和社会保障部 | https://www.mohrss.gov.cn/ | **JS 反爬挑战**（混淆脚本）⇒ 需无头浏览器 |
| 空壳 | 人力资源社会保障部-政策法规 | http://www.mohrss.gov.cn/xxgk2020/fdzdgknr/zcfg/ | — |
| 空壳 | 司法部-国家行政法规库入口(实为跳转flk) | https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzflk/ | — |
| 空壳 | 国务院公报 | https://www.gov.cn/gongbao/ | — |
| 空壳 | 国家发展改革委-政策发布 | https://www.ndrc.gov.cn/xxgk/zcfb/ | **已救活** → `/xxgk/zcfb/tz/`（44条）+ `/xxgk/zcfb/gg/`（34条） |
| 空壳 | 工业和信息化部-政策文件 | https://www.miit.gov.cn/zwgk/zcwj/index.html | — |
| 空壳 | 市场监管总局-法定主动公开 | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/ | **JS 壳**；法规司 `/fdzdgknr/fgs/` 可用（2条） |
| 空壳 | 教育部-信息公开 | http://www.moe.gov.cn/jyb_xxgk/ | **返回「信息提示」跳转页** ⇒ 换栏目 `srcsite/` 再试 |
| 空壳 | 浙江省人民政府-省政府文件 | https://www.zj.gov.cn/col/col1229019364/index.html | — |
| 空壳 | 科技部-信息公开 | https://www.most.gov.cn/xxgk/ | **已救活** → `/xxgk/xinxifenlei/fdzdgknr/fgzc/`（18条） |
| 已失效 | 交通运输部-政策解读 | https://www.mot.gov.cn/zhengcejiedu/ | **已救活** → `xxgk.mot.gov.cn/zhengce/index.html`（38条）+ `xxgk.mot.gov.cn/2020/gz/`（15条） |
| 已失效 | 国家税务总局-政策文件 | http://www.chinatax.gov.cn/chinatax/n810341/index.html | **已救活** → `/chinatax/n810341/n810755/index.html`（41条） |
| JS壳 | 浙江省人大 | https://www.zjrd.gov.cn/ | — |
| JS壳 | 浙江省人大-省域立法法规公告 | https://www.zjrd.gov.cn/sylf/fggg/ | — |
| 被拦 | 湖南省地方标准 | http://db43.hnbzw.com/StdSearch.aspx | **WAF** ⇒ 用 `dbba.sacinfo.org.cn`（全国地方标准统一平台） |
| 不通 | 上海市地方标准 | http://www.cnsis.org.cn/law/LawQueryServlet | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 云南省地方标准 | http://222.172.223.74:8090/web/guest/-4 | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 内蒙古地方标准 | http://www.imisinfo.org.cn/ | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 北京市地方标准 | http://innerapp.capital-std.com.cn/outerApp/standardSearchAction.do?method=specialSearch | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 吉林省地方标准 | http://221.8.65.189/stdcore/standard/info/findLocalStandard.do | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 四川省地方标准 | http://118.114.77.13/bzwxup/stdsearch.jsp | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 天津市地方标准 | http://60.29.186.229/wenxianpdf/c_gonggao4.asp | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 宁夏地方标准 | http://www.nstd.org.cn/ | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 山西省地方标准 | http://bqts.gov.cn/office/show.action?alias=bzhc | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 广东省地方标准 | http://gdstandard.gdqts.gov.cn:8089/gdzj-lsips/modules/details/open.jsp | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 江苏省地方标准 | http://218.94.159.231:8012/zjkms/kms/publish.rkt?type_code=gy | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 河北省地方标准 | http://www.bzsb.info/ | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 浙江省地方标准(旧) | http://db33.sinostd.com/stdlist.aspx | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 海南省地方标准 | http://qtsb.hainan.gov.cn/ywdt/dfbz/ | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 湖北省地方标准 | http://223.75.53.52:81/finddbSearch | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 福建省地方标准 | http://pt.fjbz.org.cn:8060/StandardSearch/StdSearch.aspx | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 西藏地方标准 | http://www.xzzj.gov.cn/xzzj/bsdt/dfbzfb/list/ | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 贵州省地方标准 | http://cloud.gzqts.gov.cn/dfbz/index.action | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 辽宁省地方标准 | http://218.60.145.253/ywcx/cx/listAction.do?key=011 | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 重庆市地方标准 | http://113.204.47.237:81/SharePage/bzgkBzjs.htm?code=bzgk | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 陕西省地方标准 | http://219.144.196.28/std/db_std.asp | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 青海省地方标准 | http://125.72.41.89:8008/home/res/search?keywords=DB | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 黑龙江省地方标准 | http://www.hljqts.gov.cn/ | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 空壳 | 地方标准信息公共服务平台 | https://dbba.sacinfo.org.cn/stdList | — |
| 空壳 | 山东省地方标准 | http://www.bz100.cn/member/standard/standard!getfreedb.action | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 空壳 | 江西省地方标准 | http://www.jxbz.org.cn/list.aspx?nid=11 | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 空壳 | 甘肃省地方标准 | http://www.gsdfbz.cn | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 已失效 | 安徽省地方标准 | http://bzxx.ahbz.org.cn/search_list.html | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 已失效 | 河南省地方标准 | http://www.hndb41.com/publish/index.jhtml | **2019 旧址，多已停用** ⇒ 地方标准统一走 `dbba.sacinfo.org.cn` + `std.samr.gov.cn/db` |
| 不通 | 全国标准信息公共服务平台(旧域名) | http://www.std.gov.cn/ | **已死** ⇒ 用 `std.samr.gov.cn` |
| 不通 | 国家标准委-全文公开(gb688) | http://www.gb688.cn/bzgk/gb/index | **已死** ⇒ 用 `openstd.samr.gov.cn` |
| 空壳 | 国家标准化管理委员会 | https://www.sac.gov.cn/bzhdt/index.html | — |
| 空壳 | 国家标准化管理委员会-标准公告查询 | https://std.sacinfo.org.cn/PCNoc/queryAll | **JS 应用**（Vue，需接口）——但 `std.samr.gov.cn/noc` 已覆盖同类 |
| 空壳 | 国家标准化管理委员会-通知公告 | https://www.sac.gov.cn/xw/tzgg/ | **JS 壳** ⇒ 公告可从 `sac.gov.cn` 首页/`std.samr.gov.cn/noc` 取 |
| 空壳 | 市场监管总局-标准技术管理司通知公告 | https://www.samr.gov.cn/bzjss/tzgg/index.html | **JS 壳**；标准公告走 `std.samr.gov.cn/noc` |
| 已失效 | 中国政府网-标准查询 | http://www.gov.cn/fuwu/bzxxcx/bzh.htm | **已死** ⇒ 用 `gov.cn/zhengce/xxgk/` |
| 异常 | 全国专业标准化技术委员会管理系统 | http://tc.sacinfo.org.cn/ | — |
| 被拦 | 卫生标准网 | http://www.nhc.gov.cn/zhuz/wjjsbz/wsbz.shtml | **WAF 412** ⇒ 用 `cfsa.net.cn` / `nhc.gov.cn` 食品标准栏目 |
| 被拦 | 国家卫生健康委-食品安全标准 | https://www.nhc.gov.cn/sps/new_index.shtml | **WAF 412**：同上；食品国标可由 cssn/std.samr 覆盖 |
| 被拦 | 国家卫生健康委-食品安全标准司 | http://www.nhc.gov.cn/sps/new_index.shtml | — |
| 不通 | 中国标准服务网(ccsainfo) | http://www.ccsainfo.com/ | **已死**（502/DNS 失败）⇒ 用 `cssn.net.cn` 替代 |
| 不通 | 体育标准化信息平台 | http://tybz.sport.gov.cn/home/standard | — |
| 不通 | 卫生标准网(旧) | http://wsbz.nhfpc.gov.cn/wsbzw/ | — |
| 不通 | 国家工程建设标准化信息网 | http://www.ccsn.gov.cn/ | **旧址已死** ⇒ 用 `ccsn.org.cn` |
| 不通 | 国家林业标准化管理信息系统 | http://124.205.185.55/bzk/search_standard_catalog.asp | — |
| 不通 | 测绘地理信息标准化服务平台 | http://bzgk.nasg.gov.cn/ | — |
| 不通 | 生态环境部-科技标准司 | http://kjs.mee.gov.cn/hjbhbz/ | **旧址已死** ⇒ 用 `mee.gov.cn/ywgz/fgbz/bz/bzfb/` |
| 不通 | 金融标准化技术委员会 | http://www.cfstc.org/ | **换址** → `cfstc.pbc.gov.cn/`（仍为 JS 壳，需二次开发） |
| 不通 | 金融标准化技术委员会-标准公开 | http://www.cfstc.org/bzgk/gk | **旧址已死** ⇒ 用 `cfstc.pbc.gov.cn/bzgk/`（JS 壳） |
| 不通 | 食品安全国家标准数据检索平台 | http://bz.cfsa.net.cn/db | **旧址已死** ⇒ 用 `cfsa.net.cn` / 卫健委食品标准 |
| 空壳 | 中国标准化研究院 | https://www.cnis.ac.cn/ | — |
| 空壳 | 中国电力企业联合会-标准化 | http://dls.cec.org.cn/zhongdianlianbiaozhun/ | — |
| 空壳 | 人力资源和社会保障部-政务公开 | http://www.mohrss.gov.cn/gkml/index.html | — |
| 空壳 | 住建部-工程建设标准文告 | https://www.mohurd.gov.cn/gongkai/zc/wgk/ | — |
| 空壳 | 公安部-公共安全行业标准 | http://app.mps.gov.cn:9000/gdnps/index.jsp | — |
| 空壳 | 国家能源局公告 | https://www.nea.gov.cn/policy/gg.htm | — |
| 空壳 | 工信部-文件查询 | https://www.miit.gov.cn/gyhxxhbwjcx/ | — |
| 空壳 | 工信部标准信息服务平台 | https://std.miit.gov.cn/ | — |
| 空壳 | 应急管理部标准 | https://www.mem.gov.cn/fw/flfgbz/bz/ | — |
| 空壳 | 行业标准信息公共服务平台 | https://hbba.sacinfo.org.cn/stdList | — |
| 空壳 | 行业标准信息服务平台-公告/计划 | https://hbba.sacinfo.org.cn/snList | — |
| 已失效 | 中国交通运输标准服务平台 | http://jtysbz.com.cn/ | — |
| 已失效 | 中国民航标准计量网 | http://www.caac.gov.cn/website/old/BZJL/MHBZ/ | **旧址已死** ⇒ 用 `caac.gov.cn/XXGK/` |
| 已失效 | 住建部-标准公告(第2页) | https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index_1.html | — |
| 已失效 | 商务部-流通标准 | http://ltbzh.mofcom.gov.cn/ltbzh_index.shtml | **旧址已死** ⇒ 用 `mofcom.gov.cn/zfxxgk/` |
| 已失效 | 国家林业和草原局-公告公示 | https://www.forestry.gov.cn/lyj/1/gsgg/ | **已救活** → `forestry.gov.cn/gsgg.jhtml`（28条）+ `/c/www/gkgjlyjgb.jhtml`（30条） |
| 已失效 | 国家铁路局-标准规范 | http://www.nra.gov.cn/jgzf/bzgf/ | **旧址已死** ⇒ 用 `nra.gov.cn` 首页 |
| 已失效 | 工信部-标准库 | http://www.miit.gov.cn/n1146295/n1146567/index.html | **旧址已死** ⇒ 用 `miit.gov.cn/jgsj/kjs/wjfb/` |
| 已失效 | 海洋标准化信息系统 | http://www.ncosm.org.cn/ncosm/ | — |
| 异常 | 国家消防救援局 | https://www.119.gov.cn/ | **412 JS 挑战**（「请稍候…」）⇒ 需无头浏览器 |
| JS壳 | 金融标准全文公开系统 | https://cfstc.pbc.gov.cn/bzgk/ | — |
| JS壳 | 金融标准化技术委员会 | https://cfstc.pbc.gov.cn/ | **换址** → `cfstc.pbc.gov.cn/`（仍为 JS 壳，需二次开发） |
| 异常 | IEC | https://www.iec.ch/ | — |
| 空壳 | 中国电子工业标准化技术协会 | https://www.cesa.cn/ | — |
| 已失效 | 团体标准公告(nocTB) | https://std.samr.gov.cn/noc/nocTB | — |

## 三、接口型（走渠道适配器，不进 announce.sources）

| 名称 | URL | 说明 |
|---|---|---|
| 国家法律法规数据库-枚举字典 | https://flk.npc.gov.cn/law-search/search/enumData | 返回 JSON |
| 国家法律法规数据库-详情 | https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs=ff8081819ff541ea01a07eb41e2709fb | 返回 JSON |
| 国家法律法规数据库-首页聚合 | https://flk.npc.gov.cn/law-search/index/aggregateData | 返回 JSON |
| 上海市人大-法规公布AJAX(TrueCMS) | https://www.shrd.gov.cn/TrueCMS/messageController/getMessage.do | 返回 JSON |
| 中国政府网-最新政策静态JSON | https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json | 返回 JSON |
| 国家法律法规数据库-检索列表API | https://flk.npc.gov.cn/law-search/search/list | 返回 JSON |

> 已有适配器：`cssn` / `openstd` / `std_samr_hb` / `hbba` / `dbba` / `ttbz` / `ndls` / `mee` / `flk` / `govcn`。

---

## 四、怎么拿到「最新更新公告」——官方渠道方法论

| 类别 | **首选（权威、可编程）** | 次选 | 说明 |
|---|---|---|---|
| **法律法规** | 国家法律法规数据库 `flk.npc.gov.cn`（JSON API：`/law-search/search/list`） | 中国政府网政策文件库 `gov.cn/zhengce/xxgk/`；司法部行政法规库 `xzfg.moj.gov.cn` | flk 是唯一权威全库；gov.cn 出国务院/部门文件 |
| **国家标准** | 全国标准信息公共服务平台 `std.samr.gov.cn/noc`（标准公告查询）+ `std.samr.gov.cn/gb.html` | 国家标准全文公开系统 `openstd.samr.gov.cn`；市场监管总局标准技术司 `samr.gov.cn/bzjss/tzgg/` | `/noc` 是「第 N 号公告」总库，一条公告含几十项标准 |
| **行业标准** | 行业标准信息服务平台 `hbba.sacinfo.org.cn`（POST `stdQueryList`） | 各部委标准公告栏目（见下表）；`cnas.spc.net.cn` 月度备案汇总 | 部委公告是「源头」，hbba 是「汇总库」 |
| **团体标准** | 全国团体标准信息平台 `ttbz.org.cn`（POST `getPortalStandardList`） | `std.samr.gov.cn/tb`；各协会官网 | ttbz 是国家唯一团标备案平台 |
| **地方标准** | 地方标准信息服务平台 `dbba.sacinfo.org.cn`（POST `stdQueryList`） | `std.samr.gov.cn/db`（备案公告） | ⚠ 31 个省级老平台基本已停用/迁移，统一用 dbba |

**关键：部委「公告栏目」才是更新最快的一手源**（`hbba`/`std.samr` 是汇总，有滞后）。已收录的部委公告栏目见「一、有效路径」的行业标准段。

## 五、本次扩面：GitHub 与搜索找到的工具/资源

| 资源 | 类型 | 链接 | 价值 |
|---|---|---|---|
| `pengxiao-song/awesome-chinese-legal-resources` | 法律数据源大全 | github.com/pengxiao-song/awesome-chinese-legal-resources | 法律数据源清单 |
| `jamess010/AwesomeStandardsList` | 国内外标准门户大全 | github.com/jamess010/AwesomeStandardsList | ★ 本次 31 省地方平台清单来源 |
| `SocialSisterYi/OpenSTD_Spider` | 国标全文下载 | github.com/SocialSisterYi/OpenSTD_Spider | 国标 PDF 下载链路 |
| `jhao/policy_monitor` | 政策信息监控平台 | github.com/jhao/policy_monitor | 多站点抓取+通知 |
| `twang2218/law-datasets` / `whthomas/china-laws` / `szhuima/Laws` / `DennisDZh/law_spider` / `gongkanshan-ship-it/legal-scraper` | flk 抓取脚本 | GitHub | 印证 flk API 用法 |
| `hyooeewe/Toolbox-of-Standard` | 标准查询下载工具箱 | github.com/hyooeewe/Toolbox-of-Standard | 查询实现参考 |
| CN Law Hub | 10 官方数据源 skill | kaiyuanbang.cn/zh-cn/repo/zongziforu-cn-law-hub | 十个官方源清单 |
| `changedetection.io` / `urlwatch` | 通用网页变更监控 | GitHub | 兜底方案（无接口时） |

> **结论**：没有现成的「全类别更新公告聚合器」可直接用；**最稳的组合 = flk(法规) + std.samr/noc(国标) + hbba+各部委栏目(行标) + ttbz(团标) + dbba(地标)**，
> 其中「部委公告栏目」用 `announce.py` 的通用列表页解析直接抓，其余走已有的 10 个渠道适配器。

## 六、本次更新了什么（2026-10-08 · 第二轮）

| 存储 | 改前 | 改后 | 说明 |
|---|---|---|---|
| `announce.sources`（**实际监控名单**） | 2 条 | **111 条** | 法规 46 / 国标 9 / 行标 38 / 团标 5 / 地标 9 / 国际 1 / 聚合 1（+原 2） |
| `update_channel` 台账 | 131 行 | **280 行** | 更新 163 + 新增 73；ok 151 / 可疑 39 / 未探 29 / down 61 |
| `SOURCES_MAX` 常量 | 50（硬上限） | **已删除** | 业主拍板：源数量**不设上限** |
| `announce.scan_soft_cap_s` | 无（默认 300s） | **1800s** | 源多了相应放宽，否则后半截源被 skipped_timeout |

代码改动：`src/core/update/announce.py`（删 `SOURCES_MAX` + 新增 `_scan_soft_cap_s()` 可配置）、
`tests/test_update_announce.py`（用例改为「加 60 条无上限」）、`routes_update.py` / `client/api.ts`（文档同步）。
测试：`tests/test_update_announce.py` **21 passed**。

备份（可回滚）：`var/tmp/path-audit/backup2-*.json`。

---

## 七、逐源复验 + 攻关结论 + 自包含工具（2026-10-08 · 第三轮）

### 7.1 「每个源头都有效吗」——逐条复验

对已入库的 **111 个 announce.sources** 逐条真机抓取 + 生产解析器判定：

| 结果 | 条数 | 说明 |
|---|---|---|
| ✅ 有效（解析出条目） | **110** | 含部委公告栏目、标准平台、地方监管局等 |
| ❌ 失效 | 1 | `国家档案局 saac.gov.cn` —— SSL 证书链异常（需关校验） |

⇒ **111 个里 110 个是真能抓到东西的**，不是"登记了就算"。

### 7.2 攻关：7 个硬骨头 —— 结论与解法

| 站点 | 症状 | 攻关过程 | 结论 |
|---|---|---|---|
| 国家卫健委 食品标准 | HTTP 412 | 6 种 TLS 指纹 × 移动 UA × 会话预热 **全被挡** | 需**无头浏览器**（JS 挑战） |
| 海关总署 法规 | HTTP 412 | 同上 | 需无头浏览器 |
| 住建部 政策发布 | HTTP 403 | 同上 | 需无头浏览器 |
| 国家消防救援局 | HTTP 412/405 | 同上 | 需无头浏览器 |
| 人社部 政策法规 | 988B 混淆 JS | 同上 | 需无头浏览器 |
| 金融标准全文公开系统 | 462KB 但 0 条 | 无 `JR/T` 字样、0 个 `<a>` ⇒ **Nuxt 客户端渲染** | 需无头浏览器 |
| 浙江人大 法规公告 | 76KB 但 0 条 | 408 处 `shtml` 全是页头图片链，正文列表**异步加载** | 需无头浏览器 |

**攻关结论**：这 7 个站都是**纯客户端渲染 / JS 挑战**，静态抓取（含 chrome TLS 指纹）拿不到；
唯一可行解法是**无头浏览器**。已在本机确认 `playwright / selenium / DrissionPage` **均未安装**，
故：**工具内置可选 playwright 后端**（装了就能抓，没装则如实标 `needs_browser`）。

### 7.3 自包含工具 `std-watch`

位置：`D:/AI/work space\std-watch\`（独立目录，**不依赖 zcode / 不依赖任何 Agent 软件**）

```
std-watch/
├── stdwatch.py     # 单文件主程序（纯标准库；自动检测 curl_cffi / playwright）
├── sources.json    # 源登记表（119 条，可直接编辑）
├── run.cmd         # Windows 一键入口
├── setup.cmd       # 可选增强自举（建 .venv 装 curl_cffi / playwright）
├── README.md       # 用法
└── out/            # 产物：stdwatch.db / report.md / report.csv / *.json
```

**实测（裸 Python，无任何第三方库）**：

| 后端 | 结果 |
|---|---|
| stdlib urllib（零依赖） | **109 有效 / 1 边缘 / 8 需浏览器 / 1 被拦** |
| + curl_cffi（可选） | **110 有效 / 1 边缘 / 8 需浏览器 / 0 失败** |

命令：`selftest`（离线自检）· `list` · `check`（体检）· `scan`（抓取+去重落库）· `report` · `export`。
定时：Windows 计划任务调 `run.cmd scan` 即可，无需任何 Agent。

---

## 八、硬骨头攻关结果（2026-10-08 · 第四轮，五路并行）

派 5 路并行子代理分头攻坚，**8 个端点被拿下**，3 个确认必须无头浏览器：

| 站点 | 判定 | 解法（已固化进 std-watch） |
|---|---|---|
| **住建部 政策发布** | ✅ SOLVED | CMS 接口 `GET /api-gateway/jpaas-publish-server/front/page/build/unit`，`pageId=7841fd2fed53438e8d1cbc50910d429c`、`tagId=信息公开栏目_内容1` |
| **住建部 文件库** | ✅ SOLVED | 同上，`pageId=vhiC3JxmPC8o7Lqg4Jw0E` |
| **住建部 规章库** | ✅ SOLVED | 同上，`pageId=DDOs7kRcD3aqX6vDea1GY` |
| **住建部 文告库** | ✅ SOLVED | 同上，`pageId=2b9996f111a0454ebc4a278e9ae92571` |
| **住建部 标准公告** | ✅ SOLVED | 同上，`pageId=Y53uSscFTKvrbHxaF9Cvp`、`tagId=栏目-list` |
| **人社部 政策法规** | ✅ SOLVED | 挑战 cookie 是**定值** `__tst_status=2648665512#`（JS 里三个随机数之和恒定），带上即通 |
| **浙江人大 法规公告** | ✅ SOLVED | 列表**内嵌在 JS `rightList` 数组**里（页面无 `<a>`），正则抽取 ⇒ **398 条** |
| **金融标准全文公开系统** | ✅ SOLVED | 逆出 `POST /prod-bzgk/bzgk/bzgksodt0103/public/list` + **纯 Python SM4/SM3 签名头** `cjdp-identifier` ⇒ **654 条** |
| 国家卫健委 食品标准 | ❌ NEEDS_BROWSER | 网宿 WZWS：226KB VM 混淆 JS，非可复算 cookie |
| 海关总署 法规 | ❌ NEEDS_BROWSER | 加速乐；**连 CDP 驱动的浏览器都被拒**（412→挑战JS→canvas→400） |
| 国家消防救援局 | ❌ NEEDS_BROWSER | 腾讯云 WAAP：JS 指纹 + 鼠标行为 + **滑块拼图** |

**关键技术细节（踩过的坑）**：
- 住建部接口返回 **JSON**，真正的 HTML 片段在 `data.html` 里（不是直接 HTML）。
- 金融标准签名里的 **path 不含 `/prod-bzgk` 前缀**（实际请求含），签错就 417。
- 金融标准的 SM4 前端实现用了**算术右移**（`>>`）而非标准逻辑右移 —— 标准库对不上，必须照抄。
- 接口请求的 `Accept` 必须是 JSON（用 HTML 的 Accept 会被 417 拒）。

**攻关后工具成绩**（122 源）：裸 stdlib **117 可用**；带 curl_cffi **118 可用 / 0 失败**。
