"""政务问答采集 · 站点适配器登记处。

## 给接手的人（尤其要接着扒**各省市**的那位）

**加一个新站点 = 写一个适配器 + 在下面登记**，不用改别的地方。

### 适配器要长什么样
一个模块，暴露两个东西：

```python
SITE = {
    "key": "mee",                    # 短名，做文件名与去重前缀
    "name": "生态环境部",
    "kind": "api",                   # api | static  （怎么取：接口 or 静态列表）
    "level": "national",             # national | province | city
    "entry": "https://www.mee.gov.cn/hdjl/",
    "status": "ok",                  # ok | blocked | todo | chat_only
    "note": "WAS5 检索中间件；列表由内联 JS 调 /was5/web/search",
}

def harvest(fetch, *, limit=None) -> list[dict]:
    '''返回**统一的记录格式**（见下）。fetch(url, **kw) 是注入的 HTTP 函数。'''
```

### 统一的记录格式（**所有适配器都必须返回这个形状**）
```json
{
  "source": "mee",                       // = SITE["key"]
  "id": "1791251",                       // 站内唯一 id（用于去重）
  "url": "http://.../t20260116_1140853.shtml",
  "question": "关于十三五期间环保政策文件是否有效的咨询",
  "answer": "《生态环境部行政规范性文件制定和管理办法》适用于……",
  "asked_at": "2025.10.24 08:05:00",     // 可为 null
  "answered_at": "2025.10.27 11:04:00",  // 可为 null
  "dept": "办公厅",                       // 回复单位，可为 null
  "channel": "常见问题",                   // 该站内的栏目名，可为 null
  "extra": {}                            // 站点特有字段原样留着，别丢
}
```

⚠ **`answer` 必须是答复原文**，不要清洗、不要摘要 ——
下游要靠它抽出「答复点名了哪些文件」来判断这条能不能当考卷。

### 三条硬规矩（踩过的坑，别重踩）
1. **礼貌抓取**：请求之间 `sleep >= 1.5s`；能用接口就别逐页爬静态列表。
2. **`NO_PROXY` 里 `[::1]` 会让 httpx 直接崩**（本仓 G27）⇒ 动手前先把它改成 `::1`。
   政务站还常见「配置了代理反而被拦」，见 `README.md` 的"代理"一节：
   **实测代理与直连结果一样**，412 是站点反爬、405 是路径/方法不对。
3. **不许批量下载数据集**：这是"取问答文本"，不是"镜像网站"。一次一个站，取完就停。
"""
from __future__ import annotations

from typing import Callable

#: 已登记的适配器：key → 模块路径。
#: ⚠ **新增站点在这里加一行**，`harvest.py --list` 会读它。
ADAPTERS: dict[str, str] = {
    "hunan-st": "adapters.hunan_sthjt",   # 湖南省生态环境厅（统一互动平台，已跑通）
    "hunan-yj": "adapters.hunan_yjt",     # 湖南省应急管理厅（同一平台，已跑通）
    # —— 湖南统一互动平台扩厅局（2026-10-08）：2 → 32 家。deptId 取自各厅
    #    `/<前缀>/xhtml/js/hdjl_index.js`（少数内联在互动页 HTML）。证据 recon/hunan-dept-hunt.txt ——
    "hunan-fgw": "adapters.hunan_fgw",         # 湖南省发展和改革委员会
    "hunan-jyt": "adapters.hunan_jyt",         # 湖南省教育厅
    "hunan-kjt": "adapters.hunan_kjt",         # 湖南省科学技术厅
    "hunan-gxt": "adapters.hunan_gxt",         # 湖南省工业和信息化厅
    "hunan-mzw": "adapters.hunan_mzw",         # 湖南省民族宗教事务委员会
    "hunan-gat": "adapters.hunan_gat",         # 湖南省公安厅
    "hunan-mzt": "adapters.hunan_mzt",         # 湖南省民政厅
    "hunan-sft": "adapters.hunan_sft",         # 湖南省司法厅
    "hunan-czt": "adapters.hunan_czt",         # 湖南省财政厅
    "hunan-rst": "adapters.hunan_rst",         # 湖南省人力资源和社会保障厅
    "hunan-zrzyt": "adapters.hunan_zrzyt",     # 湖南省自然资源厅
    "hunan-zjt": "adapters.hunan_zjt",         # 湖南省住房和城乡建设厅
    "hunan-jtt": "adapters.hunan_jtt",         # 湖南省交通运输厅
    "hunan-slt": "adapters.hunan_slt",         # 湖南省水利厅
    "hunan-agri": "adapters.hunan_agri",       # 湖南省农业农村厅
    "hunan-swt": "adapters.hunan_swt",         # 湖南省商务厅
    "hunan-whhlyt": "adapters.hunan_whhlyt",   # 湖南省文化和旅游厅
    "hunan-wjw": "adapters.hunan_wjw",         # 湖南省卫生健康委员会
    "hunan-tyjrswt": "adapters.hunan_tyjrswt",  # 湖南省退役军人事务厅
    "hunan-sjt": "adapters.hunan_sjt",         # 湖南省审计厅
    "hunan-lyj": "adapters.hunan_lyj",         # 湖南省林业局
    "hunan-amr": "adapters.hunan_amr",         # 湖南省市场监督管理局
    "hunan-tyj": "adapters.hunan_tyj",         # 湖南省体育局
    "hunan-tjj": "adapters.hunan_tjj",         # 湖南省统计局
    "hunan-ybj": "adapters.hunan_ybj",         # 湖南省医疗保障局
    "hunan-mpa": "adapters.hunan_mpa",         # 湖南省药品监督管理局
    "hunan-lshwzcbj": "adapters.hunan_lshwzcbj",  # 湖南省粮食和物资储备局
    "hunan-jgswj": "adapters.hunan_jgswj",     # 湖南省机关事务管理局
    "hunan-xfj": "adapters.hunan_xfj",         # 湖南省信访局
    "hunan-gzw": "adapters.hunan_gzw",         # 湖南省国资委
    # —— 新增省份：IGI 同族（2026-10-08 由「24 省系统性重探」发现，见 recon/province-platform-hunt.txt）——
    "nx-zxxx": "adapters.nx_zxxx",             # 宁夏回族自治区·主席信箱（IGI siteId=115/appId=4，带三级归属）
    "sx-szxx": "adapters.sx_szxx",             # 山西省·省长信箱（IGI siteId=110/appId=1742326）
    "ah-kb": "adapters.ah_kb",                 # 安徽省直部门·共享问答知识库（全省站群 label 8888，跨厅局聚合 2282 条）
    # —— 「静态列表型」省份（2026-10-08：无统一接口平台，静态列表 + 明细页，同安徽旧模式）——
    "tj-hdjl": "adapters.tj_hdjl",             # 天津市·政民互动·留言选登（~500 条）
    "sn-lyxd": "adapters.sn_lyxd",             # 陕西省·我向省长说句话·留言选登（~290 条）
    "cq-hdjl": "adapters.cq_hdjl",             # 重庆市·互动交流·留言选登（~840 条）
    "hlj-hdjl": "adapters.hlj_hdjl",           # 黑龙江省·政民互动（列表 total=4082）
    "fj-hdjl": "adapters.fj_hdjl",             # 福建省·12345 诉求公开（avalon JS + /apigateway 接口）
    "hn-hdjl": "adapters.hn_hdjl",             # 河南省·互动交流·网上咨询（~629 条）
    # —— 江苏 jact 平台（2026-10-08）：省门户聚合多厅局，**一厅一 sysid**（同广东 hdjlpt 模式）。
    #    基座 adapters/_jact_common.py；证据 recon/js-jact-hunt.txt ——
    "js-sthjt": "adapters.js_sthjt",           # 江苏省生态环境厅（sysid=143，~431 条）
    "js-jtyst": "adapters.js_jtyst",           # 江苏省交通运输厅（sysid=137）
    "js-jtyst2": "adapters.js_jtyst2",         # 江苏省交通运输厅（第二实例）
    "js-jyt": "adapters.js_jyt",               # 江苏省教育厅
    "js-jyt2": "adapters.js_jyt2",             # 江苏省教育厅（第二实例）
    "js-da": "adapters.js_da",                 # 江苏省档案局（sysid=107）
    "js-da2": "adapters.js_da2",               # 江苏省档案局（第二实例）
    "js-ybj": "adapters.js_ybj",               # 江苏省医疗保障局（sysid=200）
    "js-ybj2": "adapters.js_ybj2",             # 江苏省医疗保障局（第二实例）
    "js-tj": "adapters.js_tj",                 # 江苏省体育局（sysid=99）
    "js-tj2": "adapters.js_tj2",               # 江苏省体育局（第二实例）
    "js-czt": "adapters.js_czt",               # 江苏省财政厅（sysid=134）
    "js-czt2": "adapters.js_czt2",             # 江苏省财政厅（第二实例）
    "js-jswater": "adapters.js_jswater",       # 江苏省水利厅
    "js-doc": "adapters.js_doc",               # 江苏省地方志办公室（sysid=120）
    "js-jsgd": "adapters.js_jsgd",             # 江苏省广电局
    "js-nynct": "adapters.js_nynct",           # 江苏省农业农村厅
    "js-mzt": "adapters.js_mzt",               # 江苏省民政厅
    "js-gxt": "adapters.js_gxt",               # 江苏省工业和信息化厅
    "js-gxt2": "adapters.js_gxt2",             # 江苏省工业和信息化厅（第二实例）
    "js-fzggw": "adapters.js_fzggw",           # 江苏省发展和改革委员会（sysid=112）
    "js-jssxfj": "adapters.js_jssxfj",         # 江苏省信访局
    "js-jsip": "adapters.js_jsip",             # 江苏省知识产权局
    "js-jsip2": "adapters.js_jsip2",           # 江苏省知识产权局（第二实例）
    "js-credit": "adapters.js_credit",         # 江苏省信用办
    "js-jsdk": "adapters.js_jsdk",             # 江苏省地质矿产勘查局
    "js-jsstyj": "adapters.js_jsstyj",         # 江苏省应急管理厅
    "js-jsstyj2": "adapters.js_jsstyj2",       # 江苏省应急管理厅（第二实例）
    # —— 北京 / 内蒙古（2026-10-08 由「24 省重探」发现，证据 recon/bj-nmg-hunt.txt）——
    "bj-hdjl": "adapters.bj_hdjl",             # 北京市·政民互动·信件选登（195 条，答复常点名条例）
    "nmg-xinxiang": "adapters.nmg_xinxiang",   # 内蒙古自治区·政民互动·反馈回应（67 条）
    # —— 江西 / 云南（2026-10-08：江西挖到 SPA 里的真实接口；云南 WAS5 已弃用，改走信访站白名单）——
    "jx-zf": "adapters.jx_zf",                 # 江西省·queryList 接口（我向省长建言 259 + 政策问答库 430）
    "yn-xf": "adapters.yn_xf",                 # 云南省·信访站案例选登（免鉴权白名单接口，66 条全量）
    "sc-st": "adapters.sc_sthjt",      # 四川省生态环境厅（互动知识库，静态页，量小）
    "ah-st": "adapters.ah_sthjt",      # 安徽省生态环境厅（问答知识库，约145条，翻页）
    "ln-st": "adapters.ln_sthjt",      # 辽宁省生态环境厅（历史咨询服务，问答内联）
    "jl-st": "adapters.jl_sthjt",      # 吉林省生态环境厅（海云平台接口，省/市/区三级归属）
    "gz-st": "adapters.gz_sthjt",      # 贵州省生态环境厅（同款 IGI 平台，省/市/区三级归属）
    "gz-wjw": "adapters.gz_wjw",       # 贵州省卫健委（同款 IGI 平台）
    "jl-wjw": "adapters.jl_wjw",       # 吉林省卫健委（同款 IGI 平台，groupId 不同）
    "gz-jyt": "adapters.gz_jyt",         # 贵州省教育厅（IGI，生成器产出）
    "gz-rst": "adapters.gz_rst",         # 贵州省人社厅（IGI，生成器产出）
    "gz-zfcx": "adapters.gz_zfcx",       # 贵州省住建厅（IGI，生成器产出）
    "gz-nynct": "adapters.gz_nynct",     # 贵州省农业农村厅（IGI，生成器产出）
    "gz-swt": "adapters.gz_swt",         # 贵州省商务厅（IGI，生成器产出）
    "gz-zrzy": "adapters.gz_zrzy",       # 贵州省自然资源厅（IGI，生成器产出）
    # —— 贵州 IGI 扩厅局 第 3 轮（2026-10-08）：从省门户部门导航取**真实域名**（不再猜域名），
    #    27 站全部实测 n>0 且带省/市/区三级归属。生成器 recon/gen-gz-igi-adapters.py，
    #    证据 recon/gz-igi-hunt-3.txt ——
    "gz-fgw": "adapters.gz_fgw",         # 贵州省发展和改革委员会（502516/1225）
    "gz-kjt": "adapters.gz_kjt",         # 贵州省科学技术厅（501485/542）
    "gz-gxt": "adapters.gz_gxt",         # 贵州省工业和信息化厅（500653/307）
    "gz-mzw": "adapters.gz_mzw",         # 贵州省民族宗教事务委员会（500471/327）
    "gz-mzt": "adapters.gz_mzt",         # 贵州省民政厅（501697/699）
    "gz-sft": "adapters.gz_sft",         # 贵州省司法厅（97/92）
    "gz-czt": "adapters.gz_czt",         # 贵州省财政厅（502606/1299）
    "gz-mwr": "adapters.gz_mwr",         # 贵州省水利厅（501659/684）
    "gz-whhly": "adapters.gz_whhly",     # 贵州省文化和旅游厅（500430/225）
    "gz-tyjrswt": "adapters.gz_tyjrswt",  # 贵州省退役军人事务厅（88/77）
    "gz-yjgl": "adapters.gz_yjgl",       # 贵州省应急管理厅（500484/1054）
    "gz-sjt": "adapters.gz_sjt",         # 贵州省审计厅（503134/1396）
    "gz-gzw": "adapters.gz_gzw",         # 贵州省国资委（502072/793）
    "gz-tyj": "adapters.gz_tyj",         # 贵州省体育局（68/46）
    "gz-stjj": "adapters.gz_stjj",       # 贵州省统计局（502060/858）
    "gz-ylbzj": "adapters.gz_ylbzj",     # 贵州省医疗保障局（101/94）
    "gz-dsj": "adapters.gz_dsj",         # 贵州省大数据发展管理局（500670/358）
    "gz-lyj": "adapters.gz_lyj",         # 贵州省林业局（500437/237）
    "gz-lshwzcb": "adapters.gz_lshwzcb",  # 贵州省粮食和物资储备局（503368/1421）
    "gz-atcm": "adapters.gz_atcm",       # 贵州省中医药管理局（500440/242）
    "gz-invest": "adapters.gz_invest",   # 贵州省投资促进局（500470/331）
    "gz-stymj": "adapters.gz_stymj",     # 贵州省生态移民局（500472/618）
    "gz-wsb": "adapters.gz_wsb",         # 贵州省外事办公室（501794/696）
    "gz-wsg": "adapters.gz_wsg",         # 贵州省文史研究馆（501489/577）
    "gz-jyglj": "adapters.gz_jyglj",     # 贵州省监狱管理局（502238/674）
    "gz-jdglj": "adapters.gz_jdglj",     # 贵州省戒毒管理局（502602/1282）
    "gz-jkj": "adapters.gz_jkj",         # 贵州省疾控局（503467/1636）
    "jl-hrss": "adapters.jl_hrss",       # 吉林省人社厅（海云平台，appId=96+groupId=170）
    "jl-jt": "adapters.jl_jt",           # 吉林省交通运输厅（海云平台，appId=96+groupId=159）
    # —— 吉林 IGI 扩厅局（2026-10-08）：扫 groupId 得 38 个厅局，此处补 34 个未接的。
    #    生成器 recon/gen-jl-igi-adapters.py；花名册 recon/jl-groupid-roster.txt ——
    "jl-tjj": "adapters.jl_tjj",         # 吉林省统计局（groupId=186）
    "jl-wlt": "adapters.jl_wlt",         # 吉林省文化和旅游厅（177）
    "jl-ypj": "adapters.jl_ypj",         # 吉林省药品监督管理局（195）
    "jl-nynct": "adapters.jl_nynct",     # 吉林省农业农村厅（175）
    "jl-scjd": "adapters.jl_scjd",       # 吉林省市场监督管理厅（183）
    "jl-zyy": "adapters.jl_zyy",         # 吉林省中医药管理局（194）
    "jl-fgw": "adapters.jl_fgw",         # 吉林省发展和改革委员会（161）
    "jl-gxj": "adapters.jl_gxj",         # 吉林省工业和信息化厅（164）
    "jl-zrzy": "adapters.jl_zrzy",       # 吉林省自然资源厅（171）
    "jl-czt": "adapters.jl_czt",         # 吉林省财政厅（169）
    "jl-tyj": "adapters.jl_tyj",         # 吉林省体育局（185）
    "jl-tyjr": "adapters.jl_tyjr",       # 吉林省退役军人事务厅（179）
    "jl-zfcx": "adapters.jl_zfcx",       # 吉林省住房和城乡建设厅（173）
    "jl-mzt": "adapters.jl_mzt",         # 吉林省民政厅（167）
    "jl-ybj": "adapters.jl_ybj",         # 吉林省医疗保障局（187）
    "jl-slt": "adapters.jl_slt",         # 吉林省水利厅（174）
    "jl-sjt": "adapters.jl_sjt",         # 吉林省审计厅（181）
    "jl-sft": "adapters.jl_sft",         # 吉林省司法厅（168）
    "jl-lyj": "adapters.jl_lyj",         # 吉林省林业和草原局（191）
    "jl-gfdy": "adapters.jl_gfdy",       # 吉林省国防动员办公室（190）
    "jl-kjt": "adapters.jl_kjt",         # 吉林省科学技术厅（163）
    "jl-yjt": "adapters.jl_yjt",         # 吉林省应急管理厅（180）
    "jl-gzw": "adapters.jl_gzw",         # 吉林省国有资产监督管理委员会（184）
    "jl-xmy": "adapters.jl_xmy",         # 吉林省畜牧业管理局（158）
    "jl-wsb": "adapters.jl_wsb",         # 吉林省外事办公室（182）
    "jl-jyj": "adapters.jl_jyj",         # 吉林省监狱管理局（193）
    "jl-ggzy": "adapters.jl_ggzy",       # 吉林省公共资源交易中心（255）
    "jl-nyj": "adapters.jl_nyj",         # 吉林省能源局（192）
    "jl-mzw": "adapters.jl_mzw",         # 吉林省民族事务委员会（165）
    "jl-jgsw": "adapters.jl_jgsw",       # 吉林省机关事务管理局（188）
    "jl-gbdsj": "adapters.jl_gbdsj",     # 吉林省广播电视局（160）
    "jl-lsj": "adapters.jl_lsj",         # 吉林省粮食和物资储备局（189）
    "jl-swt": "adapters.jl_swt",         # 吉林省商务厅（176）
    "jl-gat": "adapters.jl_gat",         # 吉林省公安厅（166）
    "mem": "adapters.mem_gov",            # 应急管理部（静态列表，已跑通）
    "mee": "adapters.mee_gov",            # 生态环境部（WAS5 接口，已跑通）
    "people-liuyan": "adapters.people_liuyan",  # 人民网领导留言板·部委版块（接口+签名，已跑通）
    "people-liuyan-df": "adapters.people_liuyan_df",  # 同平台·地方版块（省/市/县全国覆盖，已跑通）
    "people-liuyan-fid": "adapters.people_liuyan_fid",  # 同平台·按 fid 定向深采（广度+深度两段打法）
    "people-liuyan-prov": "adapters.people_liuyan_prov",  # 按省级 fid 规律逐省采（31 省）
    "gd-st": "adapters.gd_sthj",          # 广东省生态环境厅（hdjlpt，全历史 3329）
    "gd-yj": "adapters.gd_yjgl",          # 广东省应急管理厅（hdjlpt，全历史 179）
    "gd-hr": "adapters.gd_hrss",          # 广东省人社厅（hdjlpt，6120；⚠ 每窗 510 疑截断）
    "gd-jt": "adapters.gd_jt",            # 广东省交通运输厅（hdjlpt，381）
    "gd-ws": "adapters.gd_wsjkw",         # 广东省卫健委（hdjlpt，909）
    "gd-jy": "adapters.gd_eea",           # 广东省教育厅（hdjlpt，513）
    "gd-fg": "adapters.gd_drc",           # 广东省发改委（hdjlpt，330）
    "gd-szyyj": "adapters.gd_szyyj",  # 广东省中医药局（年窗 23）
    "gd-gdcss": "adapters.gd_gdcss",  # 广东省人民政府参事室（年窗 8）
    "gd-gdyjzx": "adapters.gd_gdyjzx",  # 广东省人民政府发展研究中心（年窗 7）
    "gd-gzw": "adapters.gd_gzw",  # 广东省人民政府国有资产监督管理委员会（年窗 10）
    "gd-dfz": "adapters.gd_dfz",  # 广东省人民政府地方志办公室（年窗 9）
    "gd-zfcxjst": "adapters.gd_zfcxjst",  # 广东省住房和城乡建设厅（年窗 24）
    "gd-tyj": "adapters.gd_tyj",  # 广东省体育局（年窗 8）
    "gd-coop": "adapters.gd_coop",  # 广东省供销合作联社（年窗 4）
    "gd-gdwsxf": "adapters.gd_gdwsxf",  # 广东省信访局（年窗 11）
    "gd-dara": "adapters.gd_dara",  # 广东省农业农村厅（年窗 18）
    "gd-hsa": "adapters.gd_hsa",  # 广东省医疗保障局（年窗 11）
    "gd-com": "adapters.gd_com",  # 广东省商务厅（年窗 33）
    "gd-gdaudit": "adapters.gd_gdaudit",  # 广东省审计厅（年窗 6）
    "gd-gdii": "adapters.gd_gdii",  # 广东省工业和信息化厅（年窗 10）
    "gd-amr": "adapters.gd_amr",  # 广东省市场监督管理局（年窗 773）
    "gd-gbdsj": "adapters.gd_gbdsj",  # 广东省广播电视局（年窗 25）
    "gd-zfsg": "adapters.gd_zfsg",  # 广东省政务服务和数据管理局（年窗 31）
    "gd-edu": "adapters.gd_edu",  # 广东省教育厅（年窗 68）
    "gd-whly": "adapters.gd_whly",  # 广东省文化和旅游厅（年窗 13）
    "gd-jgsw": "adapters.gd_jgsw",  # 广东省机关事务管理局（年窗 9）
    "gd-lyj": "adapters.gd_lyj",  # 广东省林业局（年窗 21）
    "gd-smzt": "adapters.gd_smzt",  # 广东省民政厅（年窗 107）
    "gd-gdjyj": "adapters.gd_gdjyj",  # 广东省监狱管理局（年窗 14）
    "gd-gdstc": "adapters.gd_gdstc",  # 广东省科学技术厅（年窗 12）
    "gd-gdgrain": "adapters.gd_gdgrain",  # 广东省粮食和物资储备局（年窗 12）
    "gd-stats": "adapters.gd_stats",  # 广东省统计局（年窗 711）
    "gd-nr": "adapters.gd_nr",  # 广东省自然资源厅（年窗 106）
    "gd-mpa": "adapters.gd_mpa",  # 广东省药品监督管理局（年窗 32）
    "gd-czt": "adapters.gd_czt",  # 广东省财政厅（年窗 18）
    "gd-dva": "adapters.gd_dva",  # 广东省退役军人事务厅（年窗 14）
}

#: 用户要能直接 `from adapters import load`
FetchFn = Callable[..., object]


def load(key: str):
    """按 key 载入适配器模块（延迟导入，免得没装的依赖拦住别的站）。"""
    import importlib

    path = ADAPTERS.get(key)
    if not path:
        raise KeyError(f"未登记的站点 key：{key}；已登记：{sorted(ADAPTERS)}")
    return importlib.import_module(path)
