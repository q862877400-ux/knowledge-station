# 国家部委 / 中央级反馈平台 · 核验台账（worker-national）

> **来源**：worker-national 2026-10-09 逐条实测（证据见 `recon/nat-*`）。
> **判据**（同 MINISTRY-ENTRIES.md）：① 列表型（问题+官方答复、可翻页）② 无需登录 ③ 答复点名《文件》/GB。
> **取值**：`✅ 可用` / `🟡 需挖接口` / `🔴 登录墙或反爬` / `❌ 纯表单·举报·聊天机器人` / `⬜ 未核`
> **本目录只读参考**（不动 `MINISTRY-ENTRIES.md`）；产出用 `nat-*` 前缀。

## 一、结论汇总（先看这里）

| 源 | 结论 | 中间件 | 实测条数 | 适配器 |
|---|---|---|---|---|
| 交通运输部·留言咨询 | ✅ 可用 | 自研 JSON+HTML 明细 | **7,808** | `nat_mot` ⚠IP级反爬 |
| 住房和城乡建设部·政务咨询 | ✅ 可用 | jpaas build/unit | **672** | `nat_mohurd` |
| 科学技术部·公众问答 | ✅ 可用 | RuoYi 后台 | **8,811** | `nat_most` |
| 国家税务总局·12366 网上留言 | ✅ 可用 | 自研 | **38,404** | `nat_tax` |
| 国家知识产权局·留言咨询 | ✅ 可用 | jact | **≈251,020** | `nat_cnipa` |
| 国家能源局·留言选登 | ✅ 可用 | 新华 Xhwpage 伪数据源 | **145** | `nat_nea` |
| 自然资源部·建议留言 | ❌ 纯表单/个人查询 | — | 0 | — |
| 司法部·网民留言 | 🔴 登录墙 | SPA `/sfbconsult/` | 0 | — |
| 市场监管总局·公众留言 | ❌ 登录墙+聊天机器人 | — | 0 | — |
| 国家统计局·智能问答 | ❌ 聊天机器人 | chatapi.so-gov.cn | 0 | — |
| 国家信访局·网上信访 | ❌ 纯表单 | — | 0 | — |
| 海关总署 | 🔴 瑞数 412（HTML 路径） | — | ? | — |
| 中国民航局 | 🔴 JS 反爬（Terminal 检测） | — | ? | — |
| 国家药监局 | ❌ 无公开问答列表 | — | 0 | — |
| 中国气象局·公众留言 | 🟡 待挖接口 | — | ? | — |
| 国家林业和草原局·互动留言 | 🟡 待挖接口 | — | ? | — |
| 国家医保局·交流公开 | 🟡 待挖接口 | — | ? | — |
| 中国政府网「我向总理说句话」 | ❌ 纯表单（需登录） | — | 0 | — |
| 国务院「互联网+督查」全国版 | 🟡 有回声栏目，接口未定位 | — | ? | — |
| 中央纪委国家监委举报网站 | ❌ 举报通道（无答复文本） | — | 0 | — |

> 6 个可用源合计约 **30.7 万条**（其中知识产权局占 25 万）。

## 二、逐条核验（部委 | 栏目 | 入口 | 结论 | 条数 | 证据）

### 国务院组成部门

| 部委 | 栏目 | 入口 | 结论 | 实测条数 | 证据（URL + 状态码） |
|---|---|---|---|---|---|
| 自然资源部 | 建议留言 | `box.mnr.gov.cn` | ❌ 纯表单/个人查询 | 0 | `http://box.mnr.gov.cn/bzxxww/pages/fillLetter_list.html` 200：表单只有「编号+手机号」检索**个人**留言，非公开列表；主页 form 提交到 `form.mlr.gov.cn/appmanager/gtmail/send.jsp`（需登录 `dlyz.mnr.gov.cn`） |
| **交通运输部** | 留言咨询 | `qa.mot.gov.cn/mapplys/` | ✅ 可用 | **7808** | `GET /mapplys/pub/visitor/userIndex/getUserByLeavingMessage?pageNo=1&pageSize=3&orderByFiled=CRTIME` 200，`totalSize=7808`；明细 `questionDetail?id=<id>` 200，答复点名《…意见》交海发〔2014〕142号。⚠短时~30请求触发**IP级403**，需熔断+冷却（`recon/nat-mot-*`） |
| **住房和城乡建设部** | 政务咨询 | `mohurd.gov.cn/hudong/zwzx/` | ✅ 可用 | **672** | `GET /api-gateway/jpaas-publish-server/front/page/build/unit?...&paramJson={"pageNo":2,"pageSize":20,…}` 200，`count=672`，问+答同页内联（`recon/nat-mohurd-unit2.html`） |
| **科学技术部** | 公众问答 | `app.most.gov.cn/ac_gzcy_app/gzwd` | ✅ 可用 | **8811** | `POST /ac_gzcy_app/gzwd/viewMessagelist?tid=N` 200；tid1/2/3/4=4797/2065/582/1367；答复内联 `answerinfoTotal`，点名国科发资〔2024〕28号（`recon/nat-most-list.json`） |
| 司法部 | 网民留言 | `chinalaw.gov.cn/hdjl/hdjlwmly/` | 🔴 登录墙 | 0 | `/hdjl/hdjlwmly/` 200 但内联 JS 跳 `/sfbconsult/index.html#/consult/consultRemind`；`/sfbconsult/` 302（需会话） |
| 国家发展改革委 | 互动交流 | `ndrc.gov.cn` | 🟡 未挖 | ? | 首页含 `services.ndrc.gov.cn/ecdomain/portal/.../itemlist/`（清单线索） |
| 教育部 | 部长信箱 | `hudong.moe.gov.cn/interactive/bzxx/` | 🔴 需实名注册（清单已知） | 0 | 清单标注需实名注册 |
| 工业和信息化部 | 部长信箱 | `bzxx.miit.gov.cn/bzxx/appellate/main` | ⬜ 未核 | ? | — |
| 公安部 | 网上信访 | `gab.gov.cn` → 互动 | ⬜ 未核（信访类，大概率无答复文本） | ? | — |
| 民政部 | 我要留言/查询 | `mca.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 财政部 | 咨询留言 | `mof.gov.cn` → 交流互动 | ⬜ 未核 | ? | — |
| 人力资源社会保障部 | 部长信箱 | `mohrss.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 水利部 | 部长信箱 | `mwr.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 农业农村部 | 部长信箱/网上信访 | `moa.gov.cn/wsxfbzxx/…` | ⬜ 未核 | ? | — |
| 商务部 | 部长信箱 | `mofcom.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 文化和旅游部 | 部长信箱 | `mct.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 国家卫生健康委 | 政策咨询平台 | `nhc.gov.cn/hdjl/denglu.html` | 🔴 疑登录墙（清单已知） | 0 | URL 含 "denglu" |
| 退役军人事务部 | 部长信箱 | `mva.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 应急管理部 | 智能问答 | `mem.gov.cn/hd/znwd/` | ⬜ 未核（`mem` 静态线已采 60 条 ✅） | — | 见 `adapters/mem_gov.py` |
| 中国人民银行 | 公众留言 | `wzdt.pbc.gov.cn` | ⬜ 未核 | ? | — |
| 审计署 | 互动交流 | `audit.gov.cn` → 互动 | ⬜ 未核 | ? | — |

### 直属特设机构 / 直属机构 / 办事机构 / 事业单位

| 部委 | 栏目 | 入口 | 结论 | 实测条数 | 证据 |
|---|---|---|---|---|---|
| **国家税务总局** | 12366 网上留言 | `12366.chinatax.gov.cn/nszx/onlinemessage/main` | ✅ 可用 | **38404** | `POST /nszx/onlinemessage/messagelist`（`currentPage`）200，`maxCount=38404`；明细 `detail?id=<code>` 200，点名《中华人民共和国契税法》主席令第五十二号（`recon/nat-tax-detail.json`） |
| **国家知识产权局** | 留言咨询 | `cnipa.gov.cn/col/col79/index.html` | ✅ 可用 | **≈251020** | jact：`POST /jact/front/dataproxy_mailpublist.do?sysid=N&startrecord=&endrecord=&perpage=`；sysid 6/11/12/13/14/16 = 137327/14369/464/76302/16611/5947；明细 `mailpubdetail.do?transactId=&sysid=`（`recon/nat-cnipa-sysid-hunt.txt`） |
| 市场监管总局 | 公众留言 | `xgzlyhd.samr.gov.cn/gjjly/` | ❌ 登录墙+聊天机器人 | 0 | `samr.gov.cn/hd/index.html` 200 只有在线访谈/信访指南；`gjjly` → 302 跳 `login.samr.gov.cn` |
| 海关总署 | 署长信箱/互动 | `customs.gov.cn` | 🔴 瑞数 412 | ? | `http://www.customs.gov.cn/` → **412**（HTML 路径被 WAF 拦；未试出 JSON 接口路径） |
| 国家金融监督管理总局 | 网上信访 | `nfra.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 中国证券监督管理委员会 | 12386/给主席写信 | `fwpt.csrc12386.org.cn` | ⬜ 未核 | ? | — |
| 国家广播电视总局 | 局长信箱 | `nrta.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 国家体育总局 | 互动交流 | `sport.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| **国家统计局** | 公众服务智能平台 | `stats.gov.cn/znwd/` | ❌ 聊天机器人 | 0 | SPA bundle `index-BUQM0mbh.js` 引用 `https://chatapi.so-gov.cn/`（答复现生成） |
| 国务院港澳办 | 互动交流 | `hmo.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 中科院 | 院长信箱 | `cas.cn` → 互动 | ⬜ 未核 | ? | — |
| 中国社科院 | 院长信箱 | `cass.cn` → 互动 | ⬜ 未核 | ? | — |
| 中国工程院 | 院长信箱 | `cae.cn` → 互动 | ⬜ 未核 | ? | — |
| 国务院发展研究中心 | 互动交流 | `drc.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| **中国气象局** | 公众留言/回应关切 | `cma.gov.cn/wmhd/gzly/` | 🟡 需挖接口 | ? | `gzly/` 与 `cjwt/` 均 200 但为留言须知/导航壳，列表由 JS 拉取；另见 `cmastd.cmatc.cn/seekAdvicePage.jspx` |
| 国家行政学院 | 互动交流 | `nasa.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 国家档案局 | 互动交流 | `saac.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 广电总局（nrta） | — | — | ⬜ 未核 | ? | 同上 |

### 部委管理的国家局

| 国家局 | 栏目 | 入口 | 结论 | 实测条数 | 证据 |
|---|---|---|---|---|---|
| **国家能源局** | 网民留言/留言选登 | `nea.gov.cn/hudong/liuyan.htm` | ✅ 可用 | **145** | 新华伪数据源 `http://www.nea.gov.cn/hudong/ds_24f63667cf564f6ba14c152e90a7ca10.json` 200（145 条）；明细页 `detailContent`，答复点名《危险性较大的分部分项工程安全管理规定》住建部37号令（`recon/nat-nea-detail.html`） |
| 国家国防科工局 | 互动交流 | `sastind.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| **国家药品监督管理局** | 网上咨询/投诉举报 | `nmpa.gov.cn` → 互动 | ❌ 无公开问答列表 | 0 | 首页 `/hudong/` 仅「图片新闻/在线访谈/网站管理/联系我们」；`hd/nmpa_zxxf_form.html` 为信访表单 |
| 国家林业和草原局 | 互动留言 | `forestry.gov.cn/hdly.jhtml` | 🟡 需挖接口 | ? | `hdly.jhtml` 200（40KB）含「留言与回复」但列表由 JS 拉取（受理数/反馈数空） |
| **国家医疗保障局** | 交流公开 | `nhsa.gov.cn/col/col12/index.html` | 🟡 需挖接口 | ? | `col12` 200 → 跳 `/col/col59/index.html`（交流公开）；栏目存在但列表未定位；官网 留言 走 `liuyan.www.gov.cn/…?q=gjybj` |

### ★ 专门反馈 / 问政平台（用户点名）

| 平台 | 栏目 | 入口 | 结论 | 证据 |
|---|---|---|---|---|
| 中国政府网 | 我向总理说句话 | `liuyan.www.gov.cn/2025wwzfgzbgtjy/` | ❌ 纯表单（需登录） | `bmdf.html?q=zjb` 200：表单页「请登录后留言」，无公开问答列表 |
| 国务院 | 互联网+督查（全国版） | `tousu.www.gov.cn/dc/index.htm` | 🟡 有「督查回声/曝光台」栏目，列表接口未定位 | `dc/index.htm` 200 含 `#dchs`(督查回声)/`#expose`(曝光台) 锚点，内容由 JS 载入；`dc/dchs.htm` 等 302；`dc/zhuanti.htm` 200 |
| 国家信访局 | 网上信访 | `wsxf.gjxfj.gov.cn` | ❌ 纯表单 | 200：仅「问题发生地选择」引导，无公开答复文本 |
| 政务服务 | 投诉与建议 | `tousu.www.gov.cn/zwfw/index.htm` | ⬜ 未核（疑纯表单） | 与督查同域 |
| 中央纪委国家监委 | 举报网站 | `www.12388.gov.cn` | ❌ 举报通道（无答复文本） | 200（3.3KB 入口页），属举报通道，不符合判据① |
| 人民网 | 领导留言板 | `liuyan.people.com.cn` | ✅ 已另有适配器 | 见 `adapters/people_liuyan*.py`（部委版块已跑通） |

## 三、适配器清单（worker-national）

| key | 文件 | 状态 | 抽验 |
|---|---|---|---|
| `nat-mot` | `adapters/nat_mot.py` | ✅ 已抽验 | ⚠ **IP 级反爬**：短时 ~30 请求即整站 403，需冷却数十分钟；适配器已内置 403 熔断 |
| `nat-mohurd` | `adapters/nat_mohurd.py` | ✅ 已抽验 | --limit 3 通过 |
| `nat-most` | `adapters/nat_most.py` | ✅ 已抽验 | --limit 3 通过 |
| `nat-tax` | `adapters/nat_tax.py` | ✅ 已抽验 | --limit 3 通过 |
| `nat-cnipa` | `adapters/nat_cnipa.py` | ✅ 已抽验 | --limit 3 通过 |
| `nat-nea` | `adapters/nat_nea.py` | ✅ 已抽验 | --limit 5 通过 |

## 四、给接手的人 · 复用要点

1. **jact 平台又多一个成员**：`cnipa.gov.cn`（国家知识产权局）。列表 `POST /jact/front/dataproxy_mailpublist.do`（分页 `startrecord/endrecord/perpage` **在 query string**），明细 `GET /jact/front/mailpubdetail.do?transactId=&sysid=`。**枚举 sysid 才找到 6 个公开栏目**（1..60 已扫，25..60 全空）。
2. **住建部 = jpaas-publish-server 的「单元构建」接口**：`/api-gateway/jpaas-publish-server/front/page/build/unit`，**分页必须塞 `paramJson`（JSON 字符串）**，顶层 `pageNo/rows` 被忽略。
3. **国家能源局 = 新华 Xhwpage 伪数据源**：列表在 `ds_<id>.json`（id 从页面 `data="datasource:<id>"` 读），明细在 `/<日期>/<hash>/c.html` 的 `<span id="detailContent">`。**新华系政务站（news.cn 系）可复用此模式**。
4. **交通运输部反爬最凶**：整站（含 JSON 接口）短时高频即 **IP 级 403**，冷却后恢复。采它务必放慢、熔断。
5. **判死的常见形态**：`stats.gov.cn/znwd`（聊天机器人 `chatapi.so-gov.cn`）、`samr` 公众留言（登录墙）、`chinalaw` 网民留言（SPA 登录）、`liuyan.www.gov.cn`（表单需登录）、`wsxf.gjxfj.gov.cn`（表单）、`customs.gov.cn`（412 WAF）。
