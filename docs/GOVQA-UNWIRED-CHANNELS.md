# 未接线渠道清单（**给接线的对话用**）

> **这份文档是自包含的**：接手的人不需要读别的就能开始干活。
> **生成**：2026-10-11，从真库 `update_channel` 表**现读现算**（不手写）。
> **复算命令**：`.venv\Scripts\python.exe var\tmp\export-unwired.py`（或见 §六）。

---

## 一、先弄清「接线」是什么意思

台账里每条渠道有两个**互相独立**的字段（这条纪律写在 `src/core/storage/channel_repo.py`）：

| 字段 | 回答的问题 | 取值 |
|---|---|---|
| **`wiring`** | **我们自己的适配器能不能解析它** | `wired`（能）/ `seed_only`（只登记了，没接）/ `unwired`（明确未接） |
| **`verification`** | 研究期一次性实测：这个站**当时**好不好使 | `verified` / `broken` / `unverified` |

⚠ **`wiring` 与 `verification` 不是一回事**（这是 R1 的实测教训）：
`verification='verified'` 只说明**当时**探过；**能不能解析**是 `wiring` 的事。
反过来，`verification='broken'` 的渠道**也可能**接线成功（当时坏 ≠ 现在坏）。

**⇒ 「接线」= 给这条渠道写一个适配器，让 `wiring` 从 `seed_only` 变成 `wired`。**

**样板**（这 13 条已经接好了，照着它们的形状做）：

| 渠道 | 类别 | 取法（`fetch_kind`） |
|---|---|---|
| 国家标准全文公开系统 | `internal` | 服务端渲染 HTML 表格（curl_cffi chrome 指 |
| gov.cn 公告检索 + PDF 存档 | `internal` | 预期 JSON（mock）HTML 未解析；PDF 走原始字节  |
| 国家数字标准馆（中国标准化研究院） | `internal` | JSON 查询接口（搜索 + 详情两段，可只发搜索） |
| 行业标准信息服务平台（sacinfo） | `internal` | JSON 查询接口（真实解析） |
| 地方标准信息服务平台（sacinfo） | `internal` | JSON 查询接口（真实解析，与 hbba 同一基类） |
| 全国团体标准信息平台 | `internal` | JSON 查询接口 + 静态 HTML 详情（JSON-LD / |
| 生态环境部 HJ 标准 | `internal` | 服务端渲染报告页 HTML（含隐藏列的全文 PDF 直链逆向） |
| 住房和城乡建设部-政策发布 | `law` | api |
| 住房和城乡建设部-文件库 | `law` | api |
| 住房和城乡建设部-规章库 | `law` | api |
| 人力资源和社会保障部-政策法规 | `law` | html |
| 住房和城乡建设部-标准公告 | `std_hb` | api |
| 国家消防救援局-信息公开 | `std_hb` | html |

---

## 二、总账：**273 条没接线**

| `wiring` | 条数 |
|---|---|
| **`seed_only`（登记了，没接）** | **262** |
| **`unwired`（明确未接）** | **11** |
| （对照）`wired` 已接 | 13 |
| **合计** | **286** |

**按类别**：

| 类别 | 没接线 | 说明 |
|---|---|---|
| `std_hb` | **81** | 行业标准 |
| `law` | **74** | 法律法规 |
| `std_db` | **42** | 地方标准 |
| `tool` | **24** | 工具项目 |
| `std_gb` | **21** | 国家标准 |
| `internal` | **11** | 内部/既有能力 |
| `std_tb` | **9** | 团体标准 |
| `aggregator` | **7** | 聚合入口 |
| `std_intl` | **4** | 国际标准 |

**按核验状态**（决定接线时要不要先探一遍）：

| `verification` | 条数 | 接线时怎么办 |
|---|---|---|
| `verified` | **154** | 研究期已验过 ⇒ 直接写适配器，风险低 |
| `broken` | **66** | 研究期验出坏的 ⇒ **先重探一次**，可能已经修好或改版 |
| `unverified` | **53** | 没验过 ⇒ **必须先探**，别直接写适配器 |

**按来源文件**（当初是哪份调研把它登记进来的）：

| 来源 | 条数 |
|---|---|
| `PATH-REGISTRY-2026-10-08` | 149 |
| `law-cn.md` | 58 |
| `std-cn.md` | 37 |
| `oss-decomposition.md` | 18 |
| `internal-inventory.md` | 11 |

---

## 三、逐条清单（按类别分组）

> **怎么读**：`取法` 空着的 = 当初登记时**没写清怎么取** ⇒ 这类要**先探**。
> `答案类型` = 这条渠道能回答哪几类变更信号（发布/修订/废止/征求意见/编号核验）。

### 行业标准（`std_hb`）—— **81 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | 中华全国供销合作总社 | http://www.chinacoop.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 2 | 中国交通运输标准服务平台 | http://jtysbz.com.cn/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 3 | 中国地震局 | https://www.cea.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 4 | 中国标准出版社 | http://www.spc.net.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 5 | 中国标准化研究院 | https://www.cnis.ac.cn/wap/ | html_list | ✅ 研究期已验过 |  | std-cn.md |
| 6 | 中国标准化研究院 | https://www.cnis.ac.cn/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 7 | 中国标准服务网(ccsainfo) | http://www.ccsainfo.com/ | unknown | ❌ 研究期验出是坏的 |  | std-cn.md |
| 8 | 中国民用航空局-信息公开 | http://www.caac.gov.cn/XXGK/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 9 | 中国民航标准计量网 | http://www.caac.gov.cn/website/old/BZJL/MHBZ/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 10 | 中国气象局-标准 | http://www.cma.gov.cn/zfxxgk/gknr/flfgbz/bz/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 11 | 中国气象局-行业标准 | http://www.cma.gov.cn/root7/auto13139/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 12 | 中国电力企业联合会-标准化 | http://dls.cec.org.cn/zhongdianlianbiaozhun/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 13 | 交通运输标准化信息系统 | https://jtst.mot.gov.cn/search/std?q= | html_list | ✅ 研究期已验过 | 现行性/编号核验 | std-cn.md |
| 14 | 交通运输标准化信息系统-标准公告 | https://jtst.mot.gov.cn/noc | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 15 | 人力资源和社会保障部-政务公开 | http://www.mohrss.gov.cn/gkml/index.html | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 16 | 住建部-工程建设标准文告 | https://www.mohurd.gov.cn/gongkai/zc/wgk/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 17 | 住建部-标准公告(第2页) | https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index_1.html | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 18 | 住房和城乡建设部标准公告 | https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index.html | js_rendered | ✅ 研究期已验过 | 发布/修订/废止/编号核验 | std-cn.md |
| 19 | 体育标准化信息平台 | http://tybz.sport.gov.cn/home/standard | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 20 | 全国标准信息公共服务平台-行业标准 | https://std.samr.gov.cn/hb | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 21 | 公安部-公共安全行业标准 | http://app.mps.gov.cn:9000/gdnps/index.jsp | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 22 | 农业农村部-政策法规 | http://www.moa.gov.cn/gk/zcfg/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 23 | 卫生标准网 | http://www.nhc.gov.cn/zhuz/wjjsbz/wsbz.shtml | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 24 | 卫生标准网(旧) | http://wsbz.nhfpc.gov.cn/wsbzw/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 25 | 商务部-流通标准 | http://ltbzh.mofcom.gov.cn/ltbzh_index.shtml | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 26 | 国土资源标准化信息服务平台 | http://www.lrs.org.cn/channels/198.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 27 | 国家中医药管理局 | http://www.natcm.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 28 | 国家卫生健康委-食品安全标准 | https://www.nhc.gov.cn/sps/new_index.shtml | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 29 | 国家卫生健康委-食品安全标准司 | http://www.nhc.gov.cn/sps/new_index.shtml | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 30 | 国家国防科技工业局 | http://www.sastind.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 31 | 国家外汇管理局 | https://www.safe.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 32 | 国家工程建设标准化信息网 | http://www.ccsn.gov.cn/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 33 | 国家广播电视总局-标准 | http://www.nrta.gov.cn/col/col2081/index.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 34 | 国家文物局 | http://www.ncha.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 35 | 国家林业和草原局-公告 | https://www.forestry.gov.cn/c/www/gkgjlyjgb.jhtml | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 36 | 国家林业和草原局-公告公示 | https://www.forestry.gov.cn/lyj/1/gsgg/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 37 | 国家林业和草原局-公示公告 | https://www.forestry.gov.cn/gsgg.jhtml | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 38 | 国家林业标准化管理信息系统 | http://124.205.185.55/bzk/search_standard_catalog.asp | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 39 | 国家档案局 | https://www.saac.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 40 | 国家消防救援局 | https://www.119.gov.cn/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 41 | 国家烟草专卖局-标准 | http://www.tobacco.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 42 | 国家疾病预防控制局 | https://www.ndcpa.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 43 | 国家矿山安全监察局 | https://www.chinamine-safety.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 44 | 国家移民管理局 | https://www.nia.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 45 | 国家粮食和物资储备局 | http://www.lswz.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 46 | 国家粮食和物资储备局-政策发布 | http://www.lswz.gov.cn/html/zcfb/index.shtml | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 47 | 国家统计局 | https://www.stats.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 48 | 国家能源局-标准管理 | https://www.nea.gov.cn/ztzl/nybz/bzgl/index.htm | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 49 | 国家能源局-行业标准查询 | https://www.nea.gov.cn/ztzl/nybz/bzgl/hybzcx.htm | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 50 | 国家能源局公告 | https://www.nea.gov.cn/policy/gg.htm | html_list | ⬜ 没验过 | 发布/编号核验 | std-cn.md |
| 51 | 国家药品监督管理局 | https://www.nmpa.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 52 | 国家药监局-公告通告 | https://www.nmpa.gov.cn/xxgk/ggtg/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 53 | 国家邮政局 | https://www.spb.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 54 | 国家铁路局 | http://www.nra.gov.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 55 | 国家铁路局-标准规范 | http://www.nra.gov.cn/jgzf/bzgf/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 56 | 国家食品安全风险评估中心 | https://www.cfsa.net.cn/ | html_list | ✅ 研究期已验过 |  | std-cn.md |
| 57 | 工业和信息化部-公告 | https://www.miit.gov.cn/zwgk/zcwj/wjfb/gg/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 58 | 工信部-文件查询 | https://www.miit.gov.cn/gyhxxhbwjcx/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 59 | 工信部-标准库 | http://www.miit.gov.cn/n1146295/n1146567/index.html | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 60 | 工信部-科技司文件发布 | https://www.miit.gov.cn/jgsj/kjs/wjfb/index.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 61 | 工信部标准信息服务平台 | https://std.miit.gov.cn/ | js_rendered | ⬜ 没验过 |  | std-cn.md |
| 62 | 工程建设标准化信息网 | https://www.ccsn.org.cn/News/More.aspx?ClassID=004001 | html_list | ✅ 研究期已验过 | 发布/修订/废止 | std-cn.md |
| 63 | 应急管理部-AQ行业标准公告 | https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 64 | 应急管理部标准 | https://www.mem.gov.cn/fw/flfgbz/bz/ | js_rendered | ⬜ 没验过 |  | std-cn.md |
| 65 | 标准网(中机生产力促进中心) | http://www.bzw.com.cn/ | js_rendered | ✅ 研究期已验过 | 发布 | std-cn.md |
| 66 | 水利部-技术标准查询 | http://gjkj.mwr.gov.cn/jsjd1/bzcx/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 67 | 测绘地理信息标准化服务平台 | http://bzgk.nasg.gov.cn/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 68 | 海洋标准化信息系统 | http://www.ncosm.org.cn/ncosm/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 69 | 生态环境部-标准发布 | https://www.mee.gov.cn/ywgz/fgbz/bz/bzfb/index.shtml | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 70 | 生态环境部-科技标准司 | http://kjs.mee.gov.cn/hjbhbz/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 71 | 生态环境部-部文件公告 | https://www.mee.gov.cn/zcwj/bwj/gg/index.shtml | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 72 | 生态环境部标准 | https://www.mee.gov.cn/ywgz/fgbz/bz/bzfb/ | html_list | ✅ 研究期已验过 | 发布/修订/编号核验 | std-cn.md |
| 73 | 行业标准信息公共服务平台 | https://hbba.sacinfo.org.cn/stdList | json_api | ⬜ 没验过 | 发布/修订/废止/现行性/编号核验 | std-cn.md |
| 74 | 行业标准信息服务平台-公告/计划 | https://hbba.sacinfo.org.cn/snList | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 75 | 行业标准公告(nocHB) | https://std.samr.gov.cn/noc/nocHB | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 76 | 行业标准备案月报(cnas.spc) | https://cnas.spc.net.cn/cnas/newinfo/stdbzgg | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 77 | 金融标准全文公开系统 | https://cfstc.pbc.gov.cn/bzgk/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 78 | 金融标准化技术委员会 | http://www.cfstc.org/ | unknown | ❌ 研究期验出是坏的 |  | std-cn.md |
| 79 | 金融标准化技术委员会 | https://cfstc.pbc.gov.cn/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 80 | 金融标准化技术委员会-标准公开 | http://www.cfstc.org/bzgk/gk | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 81 | 食品安全国家标准数据检索平台 | http://bz.cfsa.net.cn/db | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |

### 法律法规（`law`）—— **74 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | 上海市人大-法规公布 | https://www.shrd.gov.cn/shrd/fggb/fggb.html | html_list | ✅ 研究期已验过 | 发布/修订/废止 | law-cn.md |
| 2 | 上海市人大-法规公布AJAX(TrueCMS) | https://www.shrd.gov.cn/TrueCMS/messageController/getMessage.do | json_api | ✅ 研究期已验过 | 发布/修订/废止 | law-cn.md |
| 3 | 上海市人民政府-政府规章库 | https://www.shanghai.gov.cn/xxzfgzwj/ | html_list | ✅ 研究期已验过 | 发布/修订/现行性/编号核验 | law-cn.md |
| 4 | 上海市人民政府-近期信息公开 | https://www.shanghai.gov.cn/nw12344/index.html | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 5 | 上海市司法局 | https://sft.sh.gov.cn/ | broken | ❌ 研究期验出是坏的 |  | law-cn.md |
| 6 | 上海市司法局(http) | http://sft.sh.gov.cn/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 7 | 上海市司法局-规范性文件 | https://sfj.sh.gov.cn/2020jcgk_gfxwj/ | html_list | ✅ 研究期已验过 | 发布/现行性 | law-cn.md |
| 8 | 中国人大网-法律文件 | http://www.npc.gov.cn/npc/c2/c12435/c12488/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 9 | 中国人大网-立法 | http://www.npc.gov.cn/npc/c2/c183/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 10 | 中国人民银行-条法司 | http://www.pbc.gov.cn/tiaofasi/144941/index.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 11 | 中国政府网-国家规章库 | https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm | js_render | ✅ 研究期已验过 | 现行性 | law-cn.md |
| 12 | 中国政府网-政策文件库检索 | https://www.gov.cn/zhengce/xxgk/ | html_list | ✅ 研究期已验过 |  | law-cn.md |
| 13 | 中国政府网-最新政策静态JSON | https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json | json_static | ✅ 研究期已验过 | 发布 | law-cn.md |
| 14 | 中国证监会-法律法规 | http://www.csrc.gov.cn/csrc/c101803/common_list.shtml | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 15 | 交通运输部-政府信息公开政策 | https://xxgk.mot.gov.cn/zhengce/index.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 16 | 交通运输部-政策解读 | https://www.mot.gov.cn/zhengcejiedu/ | broken | ❌ 研究期验出是坏的 |  | law-cn.md |
| 17 | 交通运输部-规章库 | https://xxgk.mot.gov.cn/2020/gz/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 18 | 交通运输部-规章速递 | http://law.mot.gov.cn/listNewLaw.action | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 19 | 人力资源和社会保障部 | https://www.mohrss.gov.cn/ | js_render | ⬜ 没验过 |  | law-cn.md |
| 20 | 人力资源社会保障部-政策法规 | http://www.mohrss.gov.cn/xxgk2020/fdzdgknr/zcfg/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 21 | 住房和城乡建设部-政策发布 | https://www.mohurd.gov.cn/gongkai/zhengce/ | broken | ❌ 研究期验出是坏的 |  | law-cn.md |
| 22 | 农业农村部-通知公告 | http://www.moa.gov.cn/gk/tzgg_1/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 23 | 北京市人大 | https://www.bjrd.gov.cn/ | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 24 | 北京市人大常委会-重要发布 | https://www.bjrd.gov.cn/zyfb/ | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 25 | 北京市人民政府-政策文件 | https://www.beijing.gov.cn/zhengce/zhengcefagui/ | html_list | ✅ 研究期已验过 | 发布/废止 | law-cn.md |
| 26 | 发改委-公告 | https://www.ndrc.gov.cn/xxgk/zcfb/gg/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 27 | 发改委-通知 | https://www.ndrc.gov.cn/xxgk/zcfb/tz/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 28 | 司法部-国家行政法规库(xzfg) | http://xzfg.moj.gov.cn/search2.html | html_list | ✅ 研究期已验过 | 发布/修订/现行性/编号核验 | law-cn.md |
| 29 | 司法部-国家行政法规库入口(实为跳转flk) | https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzflk/ | redirect_js | ⬜ 没验过 |  | law-cn.md |
| 30 | 司法部-备案审查 | https://www.moj.gov.cn/ | unknown | ✅ 研究期已验过 |  | law-cn.md |
| 31 | 司法部-部门规章栏目 | https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzbmgz/ | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 32 | 商务部-政务公开 | http://www.mofcom.gov.cn/article/zwgk/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 33 | 商务部-政策 | https://www.mofcom.gov.cn/zfxxgk/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 34 | 国务院公报 | https://www.gov.cn/gongbao/ | js_render | ⬜ 没验过 |  | law-cn.md |
| 35 | 国家卫生健康委员会 | https://www.nhc.gov.cn/ | broken | ❌ 研究期验出是坏的 |  | law-cn.md |
| 36 | 国家发展改革委-政策发布 | https://www.ndrc.gov.cn/xxgk/zcfb/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 37 | 国家市场监督管理总局-法规司 | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/ | js_render | ✅ 研究期已验过 |  | law-cn.md |
| 38 | 国家法律法规数据库-检索列表API | https://flk.npc.gov.cn/law-search/search/list | api | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 39 | 国家税务总局-政策文件 | http://www.chinatax.gov.cn/chinatax/n810341/index.html | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 40 | 国家金融监督管理总局 | https://www.nfra.gov.cn/cn/view/pages/index/index.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 41 | 工业和信息化部-政策文件 | https://www.miit.gov.cn/zwgk/zcwj/index.html | js_render | ⬜ 没验过 |  | law-cn.md |
| 42 | 市场监管总局-法定主动公开 | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 43 | 广东人大-常委会公报 | https://www.gdpc.gov.cn/gdrdw/rdhy/cwhhy/cwhgb/index.html | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 44 | 广东人大-权威发布公告通知 | https://www.gdpc.gov.cn/gdrdw/zyfb/ggtz/index.html | html_list | ✅ 研究期已验过 | 发布/修订 | law-cn.md |
| 45 | 广东人大网 | https://www.gdpc.gov.cn/ | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 46 | 广东省人民政府-文件库 | https://www.gd.gov.cn/zwgk/wjk/qbwj/ | html_list | ✅ 研究期已验过 | 发布/编号核验 | law-cn.md |
| 47 | 广东省人民政府-粤府令 | https://www.gd.gov.cn/zwgk/wjk/qbwj/yfl/index.html | html_list | ✅ 研究期已验过 | 发布/编号核验 | law-cn.md |
| 48 | 广东省司法厅-政策文件 | http://sft.gd.gov.cn/sfw/zwgk/zcwj/ | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 49 | 应急管理部-法律法规 | https://www.mem.gov.cn/fw/flfgbz/fg/index.shtml | html_list | ✅ 研究期已验过 |  | law-cn.md |
| 50 | 应急管理部-规章(法定主动公开) | https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/ | html_list | ✅ 研究期已验过 | 发布/修订/编号核验 | law-cn.md |
| 51 | 教育部-信息公开 | http://www.moe.gov.cn/jyb_xxgk/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 52 | 文化和旅游部-政策法规 | https://www.mct.gov.cn/whzx/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 53 | 最高人民检察院-法律法规规范性文件 | https://www.spp.gov.cn/spp/flfgxwj/ | js_render | ✅ 研究期已验过 |  | law-cn.md |
| 54 | 最高人民法院-司法解释 | https://www.court.gov.cn/fabu/gengduo/16.html | html_list | ✅ 研究期已验过 | 发布/修订/编号核验 | law-cn.md |
| 55 | 水利部-政务公开 | http://www.mwr.gov.cn/zwgk/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 56 | 浙江人大-法规公告(http) | http://www.zjrd.gov.cn/sylf/fggg/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 57 | 浙江省人大 | https://www.zjrd.gov.cn/ | js_render | ❌ 研究期验出是坏的 |  | law-cn.md |
| 58 | 浙江省人大-省域立法法规公告 | https://www.zjrd.gov.cn/sylf/fggg/ | html_list | ✅ 研究期已验过 | 发布/修订 | law-cn.md |
| 59 | 浙江省人大-首页 | https://www.zjrd.gov.cn/ | html_list | ⬜ 没验过 | 发布 | law-cn.md |
| 60 | 浙江省人民政府-政府规章省级有效 | https://www.zj.gov.cn/col/col1229836653/index.html | js_render | ✅ 研究期已验过 |  | law-cn.md |
| 61 | 浙江省人民政府-省政府文件 | https://www.zj.gov.cn/col/col1229019364/index.html | js_render | ❌ 研究期验出是坏的 |  | law-cn.md |
| 62 | 浙江省人民政府-省政府文件栏目 | https://www.zj.gov.cn/col/col1229019364/index.html | redirect_js | ⬜ 没验过 |  | law-cn.md |
| 63 | 浙江省司法厅 | https://sft.zj.gov.cn/ | html_list | ✅ 研究期已验过 |  | law-cn.md |
| 64 | 浙江省司法厅-政策文件 | https://sft.zj.gov.cn/col/col1229247318/index.html | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 65 | 海关总署-法规 | http://www.customs.gov.cn/customs/302249/index.html | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 66 | 生态环境部-法规标准 | https://www.mee.gov.cn/ywgz/fgbz/ | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 67 | 科技部-信息公开 | https://www.most.gov.cn/xxgk/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 68 | 科技部-法规政策 | https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 69 | 税务总局-政策 | https://www.chinatax.gov.cn/chinatax/n810341/n810755/index.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 70 | 自然资源部-通知公告 | http://www.mnr.gov.cn/gk/tzgg/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 71 | 财政部-政策发布 | http://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 72 | 首都之窗-地方性法规镜像 | https://www.beijing.gov.cn/zhengce/dfxfg/ | html_list | ✅ 研究期已验过 | 发布 | law-cn.md |
| 73 | 首都之窗-市政府令(按文号) | https://www.beijing.gov.cn/zhengce/zfwj/zfwj2016/szfl/ | html_list | ✅ 研究期已验过 | 发布/修订/废止/现行性/编号核验 | law-cn.md |
| 74 | 首都之窗-政府规章(现行有效) | https://www.beijing.gov.cn/gongkai/zfxxgk/zc/gz/ | html_list | ✅ 研究期已验过 | 发布/修订/现行性/编号核验 | law-cn.md |

### 地方标准（`std_db`）—— **42 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | 上海市地方标准 | http://www.cnsis.org.cn/law/LawQueryServlet | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 2 | 上海市市场监督管理局 | http://scjgj.sh.gov.cn/ | html_list | ✅ 研究期已验过 |  | std-cn.md |
| 3 | 云南省地方标准 | http://222.172.223.74:8090/web/guest/-4 | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 4 | 全国标准信息公共服务平台-地方标准(旧路径) | https://std.samr.gov.cn/db/dbQuery | json_api | ✅ 研究期已验过 |  | std-cn.md |
| 5 | 全国标准信息公共服务平台-地方标准公告 | https://std.samr.gov.cn/db | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 6 | 内蒙古地方标准 | http://www.imisinfo.org.cn/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 7 | 北京市地方标准 | http://innerapp.capital-std.com.cn/outerApp/standardSearchAction.do?method=… | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 8 | 北京市市场监督管理局 | https://scjgj.beijing.gov.cn/ | unknown | ✅ 研究期已验过 |  | std-cn.md |
| 9 | 吉林省地方标准 | http://221.8.65.189/stdcore/standard/info/findLocalStandard.do | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 10 | 四川省地方标准 | http://118.114.77.13/bzwxup/stdsearch.jsp | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 11 | 四川省市场监督管理局 | http://scjgj.sc.gov.cn/scsjgj/c104492/list.shtml | html_list | ✅ 研究期已验过 | 发布/修订 | std-cn.md |
| 12 | 地方标准信息公共服务平台 | https://dbba.sacinfo.org.cn/stdList | json_api | ⬜ 没验过 | 发布/修订/废止/现行性/编号核验 | std-cn.md |
| 13 | 地方标准备案公告(nocDB) | https://std.samr.gov.cn/noc/nocDB | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 14 | 天津市地方标准 | http://60.29.186.229/wenxianpdf/c_gonggao4.asp | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 15 | 宁夏地方标准 | http://www.nstd.org.cn/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 16 | 安徽省地方标准 | http://bzxx.ahbz.org.cn/search_list.html | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 17 | 山东省地方标准 | http://www.bz100.cn/member/standard/standard!getfreedb.action | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 18 | 山东省市场监督管理局 | http://amr.shandong.gov.cn/col/col76510/index.html?number=SD1002 | html_list | ✅ 研究期已验过 | 发布/废止/编号核验 | std-cn.md |
| 19 | 山西省地方标准 | http://bqts.gov.cn/office/show.action?alias=bzhc | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 20 | 广东省地方标准 | http://gdstandard.gdqts.gov.cn:8089/gdzj-lsips/modules/details/open.jsp | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 21 | 广东省市场监督管理局 | https://amr.gd.gov.cn/zwgk/tzgg/index.html | html_list | ✅ 研究期已验过 | 发布 | std-cn.md |
| 22 | 江苏省地方标准 | http://218.94.159.231:8012/zjkms/kms/publish.rkt?type_code=gy | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 23 | 江苏省市场监督管理局 | http://scjgj.jiangsu.gov.cn/col/col78963/index.html | html_list | ✅ 研究期已验过 | 发布 | std-cn.md |
| 24 | 江西省地方标准 | http://www.jxbz.org.cn/list.aspx?nid=11 | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 25 | 河北省地方标准 | http://www.bzsb.info/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 26 | 河南省地方标准 | http://www.hndb41.com/publish/index.jhtml | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 27 | 浙江标准在线-标准查询 | https://zlzx.zjamr.zj.gov.cn/bzzx/public/std/list/ALL/1.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 28 | 浙江省地方标准(旧) | http://db33.sinostd.com/stdlist.aspx | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 29 | 浙江省市场监督管理局 / 浙江标准在线 | https://zlzx.zjamr.zj.gov.cn/bzzx/public/news/list/lstd/ALL/1.html | html_list | ✅ 研究期已验过 | 发布/修订/现行性/编号核验 | std-cn.md |
| 30 | 海南省地方标准 | http://qtsb.hainan.gov.cn/ywdt/dfbz/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 31 | 湖北省地方标准 | http://223.75.53.52:81/finddbSearch | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 32 | 湖南省地方标准 | http://db43.hnbzw.com/StdSearch.aspx | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 33 | 甘肃省地方标准 | http://www.gsdfbz.cn | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 34 | 福建省地方标准 | http://pt.fjbz.org.cn:8060/StandardSearch/StdSearch.aspx | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 35 | 西藏地方标准 | http://www.xzzj.gov.cn/xzzj/bsdt/dfbzfb/list/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 36 | 贵州省地方标准 | http://cloud.gzqts.gov.cn/dfbz/index.action | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 37 | 辽宁省地方标准 | http://218.60.145.253/ywcx/cx/listAction.do?key=011 | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 38 | 辽宁省市场监督管理局 | https://scjg.ln.gov.cn/scjdglj/fw/wyb/bz/index.shtml | html_list | ✅ 研究期已验过 | 发布 | std-cn.md |
| 39 | 重庆市地方标准 | http://113.204.47.237:81/SharePage/bzgkBzjs.htm?code=bzgk | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 40 | 陕西省地方标准 | http://219.144.196.28/std/db_std.asp | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 41 | 青海省地方标准 | http://125.72.41.89:8008/home/res/search?keywords=DB | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 42 | 黑龙江省地方标准 | http://www.hljqts.gov.cn/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |

### 工具项目（`tool`）—— **24 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | @sanmis/crawler | https://www.npmjs.com/package/@sanmis/crawler (declared source repo https:/… | Not obtainable. Keywords conserv | ⬜ 没验过 |  | oss-decomposition.md |
| 2 | GBMCP | https://github.com/LoyDgIk/GBMCP | httpx.AsyncClient (no browser au | ✅ 研究期已验过 |  | oss-decomposition.md |
| 3 | GovPing | https://github.com/search?q=GovPing | unknown | ❌ 研究期验出是坏的 |  | law-cn.md |
| 4 | GovPing | https://www.npmjs.com/package/govping-mcp-server (declared source repo http… | Not obtainable (source repo 404) | ⬜ 没验过 |  | oss-decomposition.md |
| 5 | Law-Crawler-RPA-RAG-MCP | https://github.com/Yuhamixli/Law-Crawler-RPA-RAG-MCP | unknown | ✅ 研究期已验过 |  | law-cn.md |
| 6 | Law-Crawler-RPA-RAG-MCP | https://github.com/Yuhamixli/Law-Crawler-RPA-RAG-MCP | httpx.AsyncClient as async conte | ✅ 研究期已验过 |  | oss-decomposition.md |
| 7 | National Standard Monitor Skill | https://clawhub.ai/sereinone/skills/national-standard-monitor-skill/securit… | UNVERIFIABLE - page body is clie | ⬜ 没验过 |  | oss-decomposition.md |
| 8 | OpenSTD_Spider | https://github.com/SocialSisterYi/OpenSTD_Spider | httpx.AsyncClient + aiofiles str | ✅ 研究期已验过 |  | oss-decomposition.md |
| 9 | RegRadar | https://github.com/kingabzpro/RegRadar | unknown | ✅ 研究期已验过 |  | law-cn.md |
| 10 | RegRadar | (ambiguous - at least 6 same-named repos, no single authoritative one) | Not decomposed - referent uniden | ⬜ 没验过 |  | oss-decomposition.md |
| 11 | at-ris-mcp | https://github.com/paragraflabs/at-ris-mcp | unknown | ✅ 研究期已验过 |  | law-cn.md |
| 12 | at-ris-mcp | https://github.com/paragraflabs/at-ris-mcp | httpx client (src/ris_client/cli | ✅ 研究期已验过 |  | oss-decomposition.md |
| 13 | changedetection.io | https://github.com/dgtlmoon/changedetection.io | requests fetcher: urllib3 Retry( | ✅ 研究期已验过 |  | oss-decomposition.md |
| 14 | china-law-search | https://github.com/search?q=china-law-search | unknown | ❌ 研究期验出是坏的 |  | law-cn.md |
| 15 | china-law-search | (not found) | n/a | ❌ 研究期验出是坏的 |  | oss-decomposition.md |
| 16 | gb-downloader | https://github.com/suwadaimyojin/gb-downloader | requests.Session(); ddddocr Dddd | ✅ 研究期已验过 |  | oss-decomposition.md |
| 17 | gb688_downloader | https://github.com/inntran/gb688_downloader | requests, fully synchronous, NO  | ✅ 研究期已验过 |  | oss-decomposition.md |
| 18 | gbqw | https://github.com/RhettTien/gbqw | WebView human browsing. Sets a d | ✅ 研究期已验过 |  | oss-decomposition.md |
| 19 | legal-database | https://github.com/sublatesublate-design/legal-database | unknown | ⬜ 没验过 |  | law-cn.md |
| 20 | legal-database | (no single canonical repo found) | n/a | ❌ 研究期验出是坏的 |  | oss-decomposition.md |
| 21 | policy-monitor | (not found) | n/a | ❌ 研究期验出是坏的 |  | oss-decomposition.md |
| 22 | regwatch-eu | https://github.com/scka-de/regwatch-eu | httpx synchronous; each source w | ✅ 研究期已验过 |  | oss-decomposition.md |
| 23 | standards-version-check | https://github.com/cuipointer/ageis (skill at .claude/skills/standards-vers… | subprocess call to the external  | ✅ 研究期已验过 |  | oss-decomposition.md |
| 24 | urlwatch | https://github.com/thp/urlwatch | UrlJob with CHARSET_RE for text/ | ✅ 研究期已验过 |  | oss-decomposition.md |

### 国家标准（`std_gb`）—— **21 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | 中国政府网-标准查询 | http://www.gov.cn/fuwu/bzxxcx/bzh.htm | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 2 | 中国标准在线服务网 | https://www.spc.org.cn/standardonline/replace?type=0 | html_list | ✅ 研究期已验过 | 修订/废止 | std-cn.md |
| 3 | 中国标准在线服务网-标准公告 | https://www.spc.org.cn/news/stdbzgg | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 4 | 中国标准在线服务网-首页 | https://www.spc.org.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 5 | 全国专业标准化技术委员会管理系统 | http://tc.sacinfo.org.cn/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 6 | 全国标准信息公共服务平台(旧域名) | http://www.std.gov.cn/ | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 7 | 全国标准信息公共服务平台-国家标准公告 | https://std.samr.gov.cn/gb.html | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 8 | 全国标准信息公共服务平台-国家标准目录 | https://std.samr.gov.cn/gb/gbQuery | json_api | ✅ 研究期已验过 | 发布/废止/现行性/编号核验 | std-cn.md |
| 9 | 全国标准信息公共服务平台-技术委员会 | https://std.samr.gov.cn/org | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 10 | 全国标准信息公共服务平台-技术委员会公告 | https://std.samr.gov.cn/noc/nocCMR | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 11 | 全国标准信息公共服务平台-标准公告查询 | https://std.samr.gov.cn/noc | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 12 | 国家标准全文公开系统 | https://openstd.samr.gov.cn/bzgk/std/ | html_list | ✅ 研究期已验过 | 发布/废止/现行性/编号核验 | std-cn.md |
| 13 | 国家标准全文公开系统(index) | https://openstd.samr.gov.cn/bzgk/std/index | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 14 | 国家标准化管理委员会 | https://www.sac.gov.cn/bzhdt/index.html | html_list | ⬜ 没验过 |  | std-cn.md |
| 15 | 国家标准化管理委员会-标准公告查询 | https://std.sacinfo.org.cn/PCNoc/queryAll | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 16 | 国家标准化管理委员会-通知公告 | https://www.sac.gov.cn/xw/tzgg/ | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 17 | 国家标准委-全文公开(gb688) | http://www.gb688.cn/bzgk/gb/index | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |
| 18 | 国家标准批准发布公告 | https://std.samr.gov.cn/noc/nocGB | json_api | ✅ 研究期已验过 | 发布/修订 | std-cn.md |
| 19 | 市场监管总局-标准技术管理司 | https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bzcxs/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 20 | 市场监管总局-标准技术管理司通知公告 | https://www.samr.gov.cn/bzjss/tzgg/index.html | html | ⬜ 没验过 |  | PATH-REGISTRY-2026-10-08 |
| 21 | 技术委员会公告(sacinfo) | http://org.sacinfo.org.cn/tcrm/cmrNotice/announcement/list?menuItem=11 | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |

### 内部/既有能力（`internal`）—— **11 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | 中国标准服务网 | GET https://www.cssn.net.cn/api/standards/list?keyword=<标准号（保留空格）> | JSON 查询接口（真实解析，跨 GB/GB-T/GB-Z 前缀 | ⬜ 没验过 | 发布/修订/废止/现行性/编号核验 | internal-inventory.md |
| 2 | 中国标准服务网 CCS 分类抓取 | GET https://www.cssn.net.cn/api/cssn/list?keyword=<数字号> | HTML 列表页正则解析（httpx，超时 20s） | ⬜ 没验过 |  | internal-inventory.md |
| 3 | 住建部工程建设标准文告 | GET https://www.mohurd.gov.cn/gongkai/zc/wgk/（+ index_N.shtml 分页，逐条文告详情页） | HTML 列表页 + HTML 详情页（正则解析，预算 2 页  | ⬜ 没验过 | 发布/废止 | internal-inventory.md |
| 4 | 全国标准信息公共服务平台·行业标准目录 | GET https://std.samr.gov.cn/hb/search/hbPage?searchText=<归一号>&op=&ISSUE_DATE= | JSON 查询接口（真实解析） | ⬜ 没验过 | 发布/修订/废止/现行性/编号核验 | internal-inventory.md |
| 5 | 国务院政策文件库官方源客户端 | GET https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q=…&searchfi… | JSON 查询接口（真数据接口）+ HTML 详情页 + doc | ⬜ 没验过 | 发布 | internal-inventory.md |
| 6 | 国家法律法规数据库官方源客户端 | POST /law-search/search/list · GET /law-search/search/flfgDetails?bbbs= · G… | JSON API + 签名文件下载（law_source/htt | ⬜ 没验过 | 发布/修订/废止/现行性 | internal-inventory.md |
| 7 | 国家法律法规数据库（flk.npc.gov.cn） | POST https://flk.npc.gov.cn/law-search/search/list（JSON body，pageNum=1/page… | JSON 查询接口（真实解析） | ⬜ 没验过 | 发布/修订/废止/现行性/编号核验 | internal-inventory.md |
| 8 | 应急管理部 AQ 行业标准公告 | GET https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/（+ index_N.shtml 分页，逐条公告详情页） | HTML 列表页 + HTML 详情页（正则解析，预算 2 页  | ⬜ 没验过 | 发布/废止 | internal-inventory.md |
| 9 | 找标检索（openstd 分类检索） | GET https://openstd.samr.gov.cn/db/search?q=<分类路径 标准>&page=<drill_level> | 预期 JSON（mock）；走 HttpxTransport（无 | ⬜ 没验过 |  | internal-inventory.md |
| 10 | 用户自定义公告源（现有台账形态） | 用户配置的任意公网 http/https 列表页 URL（app_config 键 announce.sources） | HTML 列表页启发式解析（零 LLM：正则抽 a 标签 + 噪 | ⬜ 没验过 | 发布 | internal-inventory.md |
| 11 | 网络逐号补漏搜索（Bing） | GET https://www.bing.com/search?q=<标准号 标准名> | 预期 JSON（mock）；实际响应为 HTML，代码无解析分支 | ⬜ 没验过 | 发布/修订/废止 | internal-inventory.md |

### 团体标准（`std_tb`）—— **9 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | 中国工程建设标准化协会 | http://www.cecs.org.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 2 | 中国标准化协会 | http://www.china-cas.org/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 3 | 中国电子工业标准化技术协会 | https://www.cesa.cn/ | js_rendered | ⬜ 没验过 |  | std-cn.md |
| 4 | 中国通信标准化协会 | https://www.ccsa.org.cn/standard | js_rendered | ✅ 研究期已验过 |  | std-cn.md |
| 5 | 企业标准信息公共服务平台 | https://www.qybz.org.cn/ | html_list | ✅ 研究期已验过 |  | std-cn.md |
| 6 | 全国团体标准信息平台 | https://www.ttbz.org.cn/standard.html | js_rendered | ✅ 研究期已验过 |  | std-cn.md |
| 7 | 全国团体标准信息平台-首页 | https://www.ttbz.org.cn/ | html | ✅ 研究期已验过 |  | PATH-REGISTRY-2026-10-08 |
| 8 | 全国标准信息公共服务平台-团体标准 | https://std.samr.gov.cn/tb/ | json_api | ✅ 研究期已验过 | 发布/编号核验 | std-cn.md |
| 9 | 团体标准公告(nocTB) | https://std.samr.gov.cn/noc/nocTB | html | ❌ 研究期验出是坏的 |  | PATH-REGISTRY-2026-10-08 |

### 聚合入口（`aggregator`）—— **7 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | 北京市司法局-法律法规规章 | https://sfj.beijing.gov.cn/sfj/zwgk/2024zcwj/744120751/index.html | html_list | ✅ 研究期已验过 | 现行性 | law-cn.md |
| 2 | 国家法律法规数据库-枚举字典 | https://flk.npc.gov.cn/law-search/search/enumData | json_api | ✅ 研究期已验过 | 编号核验 | law-cn.md |
| 3 | 国家法律法规数据库-检索列表 | https://flk.npc.gov.cn/search | json_api | ⬜ 没验过 | 发布/修订/废止/现行性/编号核验 | law-cn.md |
| 4 | 国家法律法规数据库-详情 | https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs=ff8081819ff541ea0… | json_api | ✅ 研究期已验过 | 发布/修订/废止/现行性/编号核验 | law-cn.md |
| 5 | 国家法律法规数据库-首页聚合 | https://flk.npc.gov.cn/law-search/index/aggregateData | json_api | ✅ 研究期已验过 | 发布 | law-cn.md |
| 6 | 广东人大-广东省法规规章规范性文件数据库 | https://www.gdpc.gov.cn/bascdata/ | js_render | ✅ 研究期已验过 | 发布/现行性 | law-cn.md |
| 7 | 浙江省政策文件库 | https://www.zj.gov.cn/col/col1229577560/index.html | js_render | ✅ 研究期已验过 |  | law-cn.md |

### 国际标准（`std_intl`）—— **4 条**

| # | 渠道 | 网址 | 取法 | 核验 | 答案类型 | 来源 |
|---|---|---|---|---|---|---|
| 1 | IEC | https://www.iec.ch/ | js_rendered | ⬜ 没验过 |  | std-cn.md |
| 2 | ISO | https://www.iso.org/standards.html | js_rendered | ✅ 研究期已验过 |  | std-cn.md |
| 3 | 全国标准信息公共服务平台-国外标准动态 | https://std.samr.gov.cn/gw/news?channelId=87 | html_list | ✅ 研究期已验过 |  | std-cn.md |
| 4 | 全国标准信息公共服务平台-国际标准动态 | https://std.samr.gov.cn/gj/news?op=ISO | html_list | ✅ 研究期已验过 |  | std-cn.md |

---

## 四、接线完成的判据（**别自己定义**）

一条渠道算「接好了」，要同时满足：

1. **`wiring` 变成 `wired`** —— 我们的适配器**真能解析**它的响应（不是只解 mock 的 dict）。
2. **`verification` 有实测支撑** —— 探针跑过，**留下证据**（响应片段或截图路径）。
3. **进台账校验** —— `python tools/gov-qa/recon/gen-channel-table.py --check` **exit=0**。
4. **门禁不红** —— 根门禁那三步（质量闸门 / 幂等验证 / 通道台账最新）全过。

⚠ **反面样板**（本仓真发生过）：`web` / `govcn` 两根兜底棒**在链上但只解 mock 的 dict** ⇒
真实 HTML 下**恒 miss**。它们当时就是「看着接好了、实际不能用」。**别重复这个。**

---

## 五、接线前必读（省得踩重复的坑）

| 文档 | 看什么 |
|---|---|
| `tools/gov-qa/PLAYBOOK.md` | **中间件指纹库** —— 政府网站高度复用同一套 CMS，**先认中间件再挖站**（找到一个接口 = 找到一片站点） |
| `tools/gov-qa/SITE-REGISTRY.md` | 逐站台账：每个站怎么取、状态如何、下一个该试哪里 |
| `tools/gov-qa/WRITE-SCOPE.md` | **两个对话同时写这个目录的分工规矩**（`git add` 只加自己的文件；`adapters/__init__.py` 是共享文件） |
| `docs/CHANNEL-COVERAGE-PLAN.md` | 轮次台账 R1–R19 + 每轮的退出判据 |
| `src/core/storage/channel_repo.py` | `wiring` / `verification` / `state` 三个字段的**准确含义** |

**已知的「别再试」（负面结论，省下重复侦察的时间）**：

| 结论 | 证据 |
|---|---|
| 广东 `hdjlpt` **不是**全国通用平台（16 域名 0 命中） | `recon/other-province-hdjlpt-probe.json` |
| 其他省**没有** `haiyun.*.gov.cn` 主机（10 省全 ConnectError/Timeout） | `recon/haiyun-spread-probe.txt` |
| IGI 指纹在天津/上海/北京/浙江/福建/宁夏/云南/陕西 **8 省未发现** | `recon/igi-spread-scan.txt` |
| 留言板**没有**「按省列下级版块」接口 | `recon/liuyan-substation-probe2.json` |
| 留言板**没有**「按省聚合」过滤参数（10 个候选除 `fid` 外全被忽略） | `recon/liuyan-province-filter-probe.json` |
| 四川全省问政平台 `wz.sc.gov.cn` **本机不可达** | `recon/sc-wenzheng-probe.json` |

---

## 六、怎么复算这份清单

```powershell
Set-Location 'D:\AI\work space\zcode'

# ① 重新导出（读真库，只读）
.venv\Scripts\python.exe var\tmp\export-unwired.py

# ② 看某个渠道的完整字段
.venv\Scripts\python.exe -c "import sqlite3,os,json;db=os.path.expandvars(r'%APPDATA%\KnowledgeStation\database\knowledge.db');c=sqlite3.connect(f'file:{db}?mode=ro',uri=True);print(json.dumps(dict(zip([x[1] for x in c.execute('PRAGMA table_info(update_channel)')],c.execute('SELECT * FROM update_channel WHERE name LIKE \"%标准%\" LIMIT 1').fetchone())),ensure_ascii=False,indent=1))"
```

**机器可读版**：`var/tmp/channels-not-wired.json`（含全部字段，未截断）。

---

*本清单由真库现读生成；真库会变（渠道在增），引用前请重跑 §六 的复算命令。*
