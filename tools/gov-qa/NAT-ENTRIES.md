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
| 国家林业和草原局·互动留言 | ✅ 可用 | JEECMS 站内接口 | **673** | `nat_forestry` |
| 国家医疗保障局·交流公开 | ✅ 可用 | 自研 JSON（cap:7913） | **37** | `nat_nhsa` |
| 中国气象局·回应关切 | ✅ 可用 | 静态列表+明细 | **≈30** | `nat_cma` |
| 农业农村部·留言回复 | ✅ 可用 | 站内静态 JSON | **824** | `nat_moa` |
| 自然资源部·建议留言 | ❌ 纯表单/个人查询 | — | 0 | — |
| 司法部·网民留言 | 🔴 登录墙 | SPA `/sfbconsult/` | 0 | — |
| 市场监管总局·公众留言 | ❌ 登录墙+聊天机器人 | — | 0 | — |
| 国家统计局·智能问答 | ❌ 聊天机器人 | chatapi.so-gov.cn | 0 | — |
| 国家信访局·网上信访 | ❌ 纯表单 | — | 0 | — |
| 海关总署 | 🔴 瑞数 412（HTML 路径） | — | ? | — |
| 中国民航局 | 🔴 JS 反爬（Terminal 检测） | — | ? | — |
| 国家药监局 | ❌ 无公开问答列表 | — | 0 | — |
| 民政部·留言查询 | ❌ 按编号+验证码查个人留言 | — | 0 | — |
| 水利部·公众咨询 | ❌ 仅使用须知 | — | 0 | — |
| 商务部·互动交流 | ❌ 仅征求意见/访谈 | — | 0 | — |
| 工业和信息化部·部长信箱 | 🔴 Vue SPA（疑登录墙） | — | 0 | — |
| 中国政府网「我向总理说句话」 | ❌ 纯表单（需登录） | — | 0 | — |
| 国务院「互联网+督查」全国版 | ❌ 仅新闻，无公开问答列表 | — | 0 | — |
| 中央纪委国家监委举报网站 | ❌ 举报通道（无答复文本） | — | 0 | — |

> **10 个可用源**合计约 **30.9 万条**（其中知识产权局占 25 万）。翻案：林草局/医保局/气象局/农业农村部由 🟡→✅；国务院督查全国版由 🟡→❌。

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
| 工业和信息化部 | 部长信箱 | `bzxx.miit.gov.cn/bzxx/appellate/main` | 🔴 Vue SPA（疑登录墙） | 0 | 主入口 200（2733B，`gxb-bzxx-web` SPA 壳）；`js/app.*.js` 直取被 SPA 回退成 index.html（2733B）；接口未定位，疑需登录 |
| 公安部 | 网上信访 | `gab.gov.cn` → 互动 | ⬜ 未核（信访类，大概率无答复文本） | ? | — |
| 民政部 | 我要留言/查询 | `mca.gov.cn/n154/index.html` | ❌ 按编号+验证码查个人留言 | 0 | 交流互动页 200；「留言查询」`/consult/queryIndex.jsp` 200 需 `searchName`+`searchCode`(留言编号)+`rand`(验证码)，列表为占位模板（同一标题重复）；非公开列表 |
| 水利部 | 公众咨询 | `mwr.gov.cn/hd/gzzx/` | ❌ 仅使用须知 | 0 | `mwr.gov.cn/hd/gzzx/` 200 → 跳 `zxzj.mwr.gov.cn/gzzx/index.html` 200，正文为《公众咨询使用须知》，无问答列表；另有 `hd/zqyj/`(征求意见)/`hd/jjjb/`(纪检举报) 非问答 |
| 财政部 | 咨询留言 | `mof.gov.cn` → 交流互动 | ⬜ 未核 | ? | — |
| 人力资源社会保障部 | 部长信箱 | `mohrss.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 农业农村部 | 留言回复 | `moa.gov.cn/hd/` → 网民互动 | ✅ 可用（翻案） | **824** | 站内静态 JSON `GET /bzxxlyhf/xfwy/jsonFiles/reply.json` 200 → `[{strMinisterCode,strLetter(问题),strContent(答复HTML),strHandleOrgName,dtHandleStr}]`；**答复内联**，点名《农村综合统计调查制度》（`recon/nat-probe-moa-reply.json`）。⚠ 同域「留言选登」`publish.json` **只有问题无答复**（90 条），不合格 |
| 商务部 | 互动交流 | `mofcom.gov.cn/hdjl/index.html` | ❌ 仅征求意见/访谈 | 0 | 互动交流页 200，内容为「其它征求意见/混委会征求意见」+ 发布会新闻，无「问题+官方答复」列表；部长信箱为独立表单 |
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
| 中国气象局·回应关切 | ✅ 可用（翻案） | 静态列表+明细 | **≈30** | `cma.gov.cn/wmhd/gzly/` 是「留言须知」（局长信箱登录/其他留言表单）；翻案点＝页内「回应关切」`/wmhd/gzly/cjwt/`：静态列表 `createPageHTML(2,0,"index","html")` 共 2 页，明细 `.view.TRS_UEDITOR` 内「内容：/回复：/留言日期：/回复时间：/回复单位：」（`recon/nat-cma-cjwt-*`） |
| 国家行政学院 | 互动交流 | `nasa.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 国家档案局 | 互动交流 | `saac.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| 广电总局（nrta） | — | — | ⬜ 未核 | ? | 同上 |

### 部委管理的国家局

| 国家局 | 栏目 | 入口 | 结论 | 实测条数 | 证据 |
|---|---|---|---|---|---|
| **国家能源局** | 网民留言/留言选登 | `nea.gov.cn/hudong/liuyan.htm` | ✅ 可用 | **145** | 新华伪数据源 `http://www.nea.gov.cn/hudong/ds_24f63667cf564f6ba14c152e90a7ca10.json` 200（145 条）；明细页 `detailContent`，答复点名《危险性较大的分部分项工程安全管理规定》住建部37号令（`recon/nat-nea-detail.html`） |
| 国家国防科工局 | 互动交流 | `sastind.gov.cn` → 互动 | ⬜ 未核 | ? | — |
| **国家药品监督管理局** | 网上咨询/投诉举报 | `nmpa.gov.cn` → 互动 | ❌ 无公开问答列表 | 0 | 首页 `/hudong/` 仅「图片新闻/在线访谈/网站管理/联系我们」；`hd/nmpa_zxxf_form.html` 为信访表单 |
| 国家林业和草原局 | 互动留言 | `forestry.gov.cn/hdly.jhtml` | ✅ 可用（翻案） | **673** | 列表页空壳，内联 JS 调站内接口 `GET /letter/page?title=&page=N&size=20&orderBy=3` 200 → `{code:200,data:{content:[{id,title,content,replyContent,…}],totalElements:673,totalPages:34}}`；**答复内联**，点名《森林法》《陆生野生动物基准价值标准目录》（`recon/nat-forestry-letter-page.json`） |
| **国家医疗保障局** | 交流公开 | `nhsa.gov.cn/col/col59/index.html` | ✅ 可用（翻案） | **37** | col59 正文是 iframe → `cap.nhsa.gov.cn:7903/exchangeOpen.html`；接口基址在 `:7903/assets/api/api.js`（`production=https://cap.nhsa.gov.cn:7913`）；`POST /open/netizen/openInfoList`（body `{page,size}`，**须带 Referer/Origin**，否则 500）200 → `{code:20000,data:{totalRows:37,items:[{content,replyContent,replyDept,replyTime,…}]}}`；**答复内联**，点名《…通知》（`recon/nat-nhsa-openInfoList-p1.json`） |

### ★ 专门反馈 / 问政平台（用户点名）

| 平台 | 栏目 | 入口 | 结论 | 证据 |
|---|---|---|---|---|
| 中国政府网 | 我向总理说句话 | `liuyan.www.gov.cn/2025wwzfgzbgtjy/` | ❌ 纯表单（需登录） | `bmdf.html?q=zjb` 200：表单页「请登录后留言」，无公开问答列表 |
| 国务院 | 互联网+督查（全国版） | `tousu.www.gov.cn/dc/index.htm` | ❌ 仅新闻，无公开问答列表 | `dc/index.htm` 200：`督查回声/曝光台` 锚点**已被注释掉**（`<!-- … -->`）；`gov.cn/hudong/ducha/` 只有大督查新闻稿（李克强主持国常会等），无「问题+官方答复」列表 |
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
| `nat-nhsa` | `adapters/nat_nhsa.py` | ✅ 已抽验 | --limit 3 通过（答复内联） |
| `nat-forestry` | `adapters/nat_forestry.py` | ✅ 已抽验 | --limit 3 通过（答复内联） |
| `nat-cma` | `adapters/nat_cma.py` | ✅ 已抽验 | --limit 3 通过（静态列表+明细） |
| `nat-moa` | `adapters/nat_moa.py` | ✅ 已抽验 | --limit 3 通过（答复内联） |

## 四、给接手的人 · 复用要点

1. **jact 平台又多一个成员**：`cnipa.gov.cn`（国家知识产权局）。列表 `POST /jact/front/dataproxy_mailpublist.do`（分页 `startrecord/endrecord/perpage` **在 query string**），明细 `GET /jact/front/mailpubdetail.do?transactId=&sysid=`。**枚举 sysid 才找到 6 个公开栏目**（1..60 已扫，25..60 全空）。
2. **住建部 = jpaas-publish-server 的「单元构建」接口**：`/api-gateway/jpaas-publish-server/front/page/build/unit`，**分页必须塞 `paramJson`（JSON 字符串）**，顶层 `pageNo/rows` 被忽略。
3. **国家能源局 = 新华 Xhwpage 伪数据源**：列表在 `ds_<id>.json`（id 从页面 `data="datasource:<id>"` 读），明细在 `/<日期>/<hash>/c.html` 的 `<span id="detailContent">`。**新华系政务站（news.cn 系）可复用此模式**。
4. **交通运输部反爬最凶**：整站（含 JSON 接口）短时高频即 **IP 级 403**，冷却后恢复。采它务必放慢、熔断。
5. **判死的常见形态**：`stats.gov.cn/znwd`（聊天机器人 `chatapi.so-gov.cn`）、`samr` 公众留言（登录墙）、`chinalaw` 网民留言（SPA 登录）、`liuyan.www.gov.cn`（表单需登录）、`wsxf.gjxfj.gov.cn`（表单）、`customs.gov.cn`（412 WAF）、`tousu.www.gov.cn/dc`（督查回声锚点被注释，仅新闻）。
6. **JEECMS 站内接口**（国家林草局）：`/r/cms/www/default/js/app.js` 定义 `api.GET(url,data,cb)`，`base=localStorage.getItem('base')||''` ⇒ 接口就是同源 `base+'/letter/page'`。**JEECMS 政务站（`.jhtml` 后缀 + `/r/cms/` 静态目录）可复用此模式**：列表接口返回全字段（含 ip/cookieIdentity 等敏感字段，别原样落库）。
7. **「交流公开」类栏目常藏在 iframe 里**（国家医保局）：门户栏目页只有 `<iframe src="https://cap.<host>:<port>/exchangeOpen.html">`；真正接口在 iframe 的 `assets/api/api.js`（`var production=…`）。**遇到 iframe 先取它的 HTML 再顺 `api.js`**。
8. **自研 JSON 接口要带 `Referer`/`Origin`**（国家医保局）：`openInfoList` 不带 Referer 直接 500，带上 200。政务自研接口（尤其带 `code:20000` 风格的）常见此坑。
9. **静态列表翻页规律**（中国气象局）：页尾 `createPageHTML(N, 0, "index", "html")` ⇒ 共 N 页，第 1 页是目录 `index.html`，第 k(k≥2) 页是 `index_{k-1}.html`。**TRS/大汉 CMS 通用**。
10. **「站内静态 JSON」是最省事的形态**（农业农村部）：列表页内联 JS 里写死 `../jsonFiles/<x>.json`，直接 GET 即得全量（`reply.json` 824 条，问题+答复内联）。**遇到 `$.getJSON('../jsonFiles/…')` 直接抓那个 JSON**，别去解析 DOM。⚠ 同域可能并列多个 JSON（`publish.json`=只问题 / `reply.json`=问题+答复），**要挑有答复字段的那个**。
