# 自动化执行记忆：gov-qa 推进到全国省市全覆盖

## 轮次台账

### 第 11 轮 · 2026-10-09 深夜场（22:37–23:1x）

- **提交** `d5bc982`（代码+文档+数据，38 个文件）；**快照** `step-361-govqa-igi-city4`
  （`^{commit}` 已核 = `d5bc982` = HEAD）。
- **开工盘点（任务书前提第 11 次过时）**：**314** 适配器 / **零数据仍只有 2 个**
  （`hb-rst-igi`/`hb-wjw`，均 `status=dup`）⇒ 不照单执行。
- **现场归属**：开工时另一对话 r10 进程全停（`r10-*.log` 停在 22:36:5x）；
  **收工时它已回来**（跑 `harvest.py --site sd-yantai --limit 2000`）⇒
  山东烟台 / 江苏扬州 / gx·sx·nx-igi / 人民网 fid / 部委线 **一律不碰**。
  我走**新建城市门户适配器**（零冲突）。
- **★ 选线**：接手第 10 轮 §10.1 明确留下的「**11 个新 IGI 地级市门户待枚举**」。
  用独立脚本 `var/tmp/r11/city-igi-scan.py`（**不提交**，口径同 `igi-siteid-scan.py`）四路并行枚举。
- **★★ 本轮核心方法（判据）：用「枚举 `siteId→totalResults` 映射」判「同省城市门户是否 = 省门户同一实例」**
  - 判据三条同时成立 ⇒ 同一实例 ⇒ **弃**（否则同一批信件记两遍）：
    ① 城市站集合 ⊆ 省站集合（独有 == 0）；② 共同 siteId 的 total 逐字相同占绝大多数；③ 总数≈。
  - 结果：**贵州、广西 = 集中式**（`zunyi`/`anshun`/`bijie`/`guilin` 4 城判重复、弃）；
    **山西 / 陕西 / 湖北 / 内蒙古 / 海南 = 各自独立部署**。
  - 成本近零（枚举本来就要做）⇒ **接入前应无条件先做**。
- **★ 接 8 条新线**（全部新建适配器）：`shannan-igi`(西藏 7 站/191) · `danzhou-igi`(海南 20 站/27,694)
  · `xianyang-igi`(陕西 17 站/**52,859**，本轮最大) · `baoji-igi`(陕西 49 站/12,561) ·
  `chifeng-igi`(内蒙古 53 站/11,485) · `changzhi-igi`(山西 15 站/6,657) · `jingzhou-igi`(湖北 29 站/5,130) ·
  `tongliao-igi`(内蒙古 39 站/3,843)。适配器 **314 → 322**。
- **落盘 +4,118**（8 条线，18 个新文件，**跨轮续采中**）：
  shannan 190｜danzhou 545｜chifeng 763｜baoji 797｜changzhi 400｜jingzhou 400｜tongliao 639｜xianyang 384。
  审计：**0 重复 id / 0 空答复 / 0 <10 字 / 0 噪声**；⚠ danzhou 1 条「答复==问题」（上游回填）；
  ⚠ tongliao 地域非空 34%（真实但稀疏）；shannan 地域 100%（真实三级链）。
  **JSONL 逐行 `json.loads`：3,174 行 ⇒ 0 失败**（审计时点）。
- **★ 共享文件只暂存自己的行**：`adapters/__init__.py` 与 `SITE-REGISTRY.md` 用
  `git show HEAD:` + 插入我的增量 → `hash-object -w` → `update-index --cacheinfo` ⇒
  **另一对话的 zhangye/jiujiang 注册与 §二十未被夹带**（脚本 `var/tmp/r11/stage-shared.py`）。
- **收工**：7 个 IGI 采集 + 4 个枚举**全部 `TaskStop`**；复核无残留 igi-chunked 进程。
- **未碰**：`MINISTRY-ENTRIES.md`/`probe-ministries.py`/`mem_gov.py`/`mee_gov.py`、
  sd-yantai/js-yangzhou/gx·sx·nx-igi、共享生成产物（`coverage-*`/`locate-rate.json`/`assets-*`）。

### 下一轮可挑（第 11 轮重排）

0. **★ 8 条新线续采**（重跑只取新增，全部托管后台、收工 `TaskStop`）：
   ```bash
   .venv/Scripts/python.exe -u tools/gov-qa/recon/igi-chunked.py <mod> \
     --sites-json igi-siteid-<tag>.json --page-chunk 20 --resume-margin 20
   # danzhou/xianyang/baoji/chifeng/changzhi/jingzhou/tongliao（shannan 已完成）
   ```
   枚举上界 27,694 / 52,859 / 12,561 / 11,485 / 6,657 / 5,130 / 3,843 ⇒ **单轮跑不完**。
1. **第 10 轮遗留（仍无人认领）**：`gz-igi-93` 页 1-220 补采（≈4,400 条被限流跳过）；
   修 `igi-chunked.py` 两个坑（列表非 200 不触发 `--retries`；进度文件多进程互相覆盖）；
   天津 `tj.gov.cn` IGI 明细恒 500。
2. **11 城枚举的复用**：4 个判重复的（guilin/zunyi/anshun/bijie）**别再接**。
3. 人民网 fid 密集扫描续跑（第 10 轮停在 fid 26xx）。

### 别再试（第 11 轮新增）

- **贵州三城（遵义/安顺/毕节）+ 广西桂林** ⇒ 与省门户**同一实例**，接了只会重复计数。
- `danzhou` 地域字段是门户默认值（报「海口市」）；`xianyang`/`chifeng` 地域全空 ⇒ 都不能扩区县归属。

### 第 9 轮 · 2026-10-09 傍晚场（18:16–18:52）

- **提交** `7c7769d`（代码+文档+数据，25 个文件）；**快照** `step-358-govqa-igi-r9`
  （`^{commit}` 已核 = `7c7769d` = HEAD）。
- **开工盘点（任务书前提第 9 次过时）**：312 适配器 / 466 数据文件，**零数据仍只有 2 个**
  （`hb-rst-igi`/`hb-wjw`，均 `status=dup`）⇒ 不照单执行。
- **现场归属**：另一对话在跑 `sx_igi`（12:16 起，至 18:1x 仍在翻 siteId=41）、`js-yangzhou`、
  `sd-yantai` ⇒ **sx/gx/nx、扬州、烟台不碰**。我走「我建的 7 条 IGI 线」。
- **★ 落盘 +5,387**（7 条线，全部托管后台、`--page-chunk 20`）：
  shenyang +800｜nanjing +922｜xining +800｜nmg +800｜gz +718｜baotou +925｜hb-wuhan +422。
  15 个新文件 + 4 个追加文件。审计：**0 重复 / 0 空答复 / 0 答复==问题 / 0 <10字**；
  **20,106 行逐行 `json.loads` ⇒ 0 失败**。
- **★ 新能力 `igi-chunked.py --resume-margin N`**（**默认 0 = 旧行为**，另一个对话的
  `igi-resume.sh` 不受影响）：按 (key,siteId) 记「已翻完的最大页号」到
  `recon/.igi-page-progress.json`（临时文件 + `os.replace`），下轮从 `已翻页+1-N` 续、
  窗口按 `--page-chunk` 对齐；只在窗口真翻完才记进度。
  **动机（本轮实测）**：每轮重跑都把已落盘页重列一遍（shenyang 白翻 40 页、nmg/gz 各 160 页，
  全部「新增 0」）⇒ 7 条线一轮白烧约 **26 分钟**。
  **⚠ 已知代价**：上游若把新信插在**列表头部**，续跑会漏 ⇒ 要「新信不漏」就不传本参数。
  已用**历史日志**播种 35 个 siteId（判据：`页pf-pt: 新增` 行是窗口写盘**之后**才打印的），
  并在 `nanjing-igi-126` 上验证生效。
- **★ 顺手修 2 个共享脚本的「半行」容错**（**影响另一个对话**，只加容错不改口径）：
  `recon/coverage-by-level.py` 与 `measure-locate-rate.py` 遇到半行直接崩
  （两个对话同时采集时必然出现）⇒ 整份验收产物刷不出来。已改成「跳过并计数」。
- **验收产物（刷新，均不提交）**：总 **320,131** 条 / 省级 31 / 来源 607；
  三级 **省 12,315｜省+市 568｜省+市+县 30,615｜无链 276,633**；
  覆盖 省级 31 / 省市 191 / 省市县 612；**可用考卷 24,235 条**。
  ⚠ 这三个脚本会重写约 **600 个 `assets-*.json`** ⇒ 工作区脏但不 `git add`。
- **★ 负面结论（天津）**：`tj.gov.cn` IGI 列表可达（siteId=186 = 123,546）但
  **明细接口恒 HTTP 500「未找到该信件！」**、列表行 `REPLYS` 恒空 ⇒ **拿不到答复 = 暂不可采**；
  `/zmhd/` 首页 160KB 里 grep `openGovmsgbox` 零命中 ⇒ 要接必须先抓真浏览器 XHR。
  与 `tj-enorth` 的 id 重叠本页 5 条实测为 0。
- **★ 复现第 6 轮结论**：`hb-wuhan` 10 条 `&nbsp;` 噪声**全在旧主文件**（逐条定位到行号）
  = `clean()` 修复前的存量 ⇒ 「历史行不会被改写」在**第三个来源**上复现。
- **第三条线**：fid 密集扫描 1,825 → **1,981 行（+156）**，扫到 **fid 2581**（≈5.9 fid/分钟）。
- **收工**：7 个 IGI + 1 个 fid **全部 `TaskStop`**；进程复核只剩另一对话的 3 条。

### 下一轮可挑（第 9 轮重排）

0. **★ 七条线续采 —— 这次带上 `--resume-margin 20`**（直接省掉重列；重跑只取新增）：
   `igi-chunked.py <mod> --sites-json igi-siteid-<tag>.json --page-chunk 20 --resume-margin 20`
   （`shenyang_igi`/`nanjing_igi`/`xining_igi`/`nmg_igi`/`gz_igi`/`baotou_igi`；
   `hb_wuhan` 走 `--page-chunk 20 --max-pages 165 --resume-margin 20`，**无** `--sites-json`）。
   ⚠ 全部托管后台、收工 `TaskStop`。
1. **`nanning-igi` 续采**（1,193 / 18,977；**必须显式 `--max-pages 949`**，≈56 s/页）。
2. **沈阳 `siteId=118`（4,109）/`88`（914）/`44`（746）** 仍未碰 —— 沈阳 17,369 里的大头。
3. 天津 IGI 要接先抓真浏览器 XHR（明细恒 500，见上）；`igi-siteid-scan.py` 补扫
   `guiyang`/`yinchuan`（接前先验与 `gz-igi`/`nx-igi` 的 id 重叠）。
4. 人民网 fid 密集扫描续跑（停在 **fid 2581**，剩余 `2582..4600`）。

### 第 8 轮 · 2026-10-09 傍晚场（17:08–17:45）

- **提交**：`88740ff`（沈/宁适配器 + `igi-geo-sample.py`）→ `0a8bd1f`（前缀修复）→
  `36406bf`（西宁）→ `dc9f7fa`（台账 §十八）→ `0b47a3d` + 第二批（数据）→
  `6a91fda`（更正）→ `8d50969`（收工状态）。
  **快照** `step-356-govqa-igi-city3`（= `da46d6b`）+ **最终** `step-357-govqa-igi-city3-final`
  （= `8d50969`，`^{commit}` 已核 = HEAD）。
- **开工盘点（任务书前提第 7 次过时）**：309 适配器，**零数据仍只有 2 个**
  （`hb-rst-igi`/`hb-wjw`，均 `status=dup`）⇒ 不照单执行。
- **现场归属**：另一对话在跑 `sx_igi`（igi-resume.sh，12:16 起）+ `js-yangzhou` + `sd-yantai`
  ⇒ **sx/gx/nx、江苏扬州、山东烟台不碰**。我走 IGI 城市门户线 + hb-wuhan。
- **★★ 本轮主发现：城市门户地域有【三种形态】，接站前必须实测**
  - 真·多变：南宁（44% 稀疏）、西宁（**7% 稀疏**）
  - 恒定默认值（假）：包头（内蒙古/包头/市辖区）、沈阳（辽宁/沈阳/**和平区** 100/100）、
    南京 130（江苏/南京/市辖区 23/100）
  - 空：南京 126（0/100）
  - **新工具 `recon/igi-geo-sample.py`**（抽 5 页×20=100 行，统计 distinct）—— 必跑。
- **★ 三个新适配器**（辽宁/江苏/青海的**首条** IGI 线）：
  | key | siteId | 枚举上界 | 地域 | 该省存量 |
  |---|---|---|---|---|
  | `shenyang-igi` | 53 | 17,369 | 假（剥离） | 21,808 |
  | `nanjing-igi` | 63 | 4,065 | 空/假（剥离） | 20,604 |
  | **`xining-igi`** | 2 | **5,826** | 真但**稀疏 7%** | **353 ⇒ ≈16 倍** |
- **★ 西宁 = 弱省解法新范式**：青海**省**门户不可达（BLOCK/ConnectTimeout），
  但**西宁市**门户 IGI 正常 ⇒ **弱省可「绕过省门户、打市级门户」**。
- **★★ 修了上一轮自己埋的缺陷**：`recon/coverage-matrix.py` 的 `PROVINCE_PREFIX`
  漏了**城市门户前缀**（`nanning-` 不是 `gx-`、`shenyang-` 不是 `ln-`）
  ⇒ **1,907 条掉「未归属」**（baotou 1,464 + nanning 443）。加 4 行 + `xining-` 后**归零**。
  **固化成纪律：每接一个城市门户，这张表必须同步加一行。**
- **★ 自我更正（写进台账，保留原话 + 更正）**：西宁地域初判「真实且含区县」**只抽了 5 行**；
  落盘 400 行后实测**非空仅 29/400 = 7%** ⇒ 改为「真但稀疏」。
  **判「真/假」可小样本，判「覆盖率」必须上量。**
- **落盘 +5,557**（17:38 实测）：nmg +800 / gz +794 / baotou +1,052 / nanning +399 /
  shenyang +800 / nanjing +868 / xining +400 / hb-wuhan +444。
  审计（`audit-igi-prov.py`）：全部 **0 重复 / 0 空答复 / 0 答复==问题 / 0 <10字**；
  hb-wuhan 跨 3 文件核 id **3,601/3,601 唯一**。
- **第三条线**：fid 密集扫描 1,645 → **1,825**（+180，扫到 fid 2425），**产物不提交**。
- **负面结论（别再试）**：**福州**（IGI 路径 4 个 siteId 全 403 HTML，随后连首页 ReadTimeout）、
  **乌鲁木齐**（ConnectTimeout）；**河南 `hn-hdjl` 622/629、北京 `bj-hdjl` 195/215 是「上游见底」
  不是 limit 截断**；**云南三线全死**（WAS5 已弃用 / 12345 无公开列表 / 信访 mailbox 需 JWT）。
- **收工**：8 个 IGI + 1 个 fid **全部 `TaskStop`**；全部 IGI 数据 **56,779 行逐行
  `json.loads` ⇒ 0 失败**（强杀不留半行）。
- **未碰**：`MINISTRY-ENTRIES.md`/`probe-ministries.py`/`mem_gov.py`/`mee_gov.py`、
  sx/gx/nx IGI、js-yangzhou、sd-yantai、共享生成产物（`coverage-*`/`locate-rate.json`/`assets-*`）。

### 下一轮可挑（第 8 轮重排）

0. **★ 沈/宁/西宁三条新线续采**（直接重跑，只取新增，全部托管后台）：
   - `igi-chunked.py shenyang_igi --sites-json igi-siteid-shenyang.json --page-chunk 20`（53 站/869 页）
   - `igi-chunked.py nanjing_igi --sites-json igi-siteid-nanjing.json --page-chunk 20`（63 站/204 页）
   - `igi-chunked.py xining_igi --sites-json igi-siteid-xining.json --page-chunk 20`（2 站/292 页；≈40 s/页）
1. **★ 内蒙古/贵州/包头/南宁四条老线续采**（仍无人认领）。
2. **`igi-siteid-scan.py` 补扫 `yinchuan` / `guiyang`**（已确认有 IGI 但未枚举）；
   ⚠ 接前先验与 `nx-igi`/`gz-igi` 的 id 重叠。`haikou` 只有 2 站/31 条 ⇒ 放弃。
3. **天津 `tj.gov.cn` IGI（siteId=186 = 123,546 条）仍无人认领** —— 接前先验与 `tj-enorth` 的重叠。
4. **`hb-wuhan` 剩余缺口**（3,750 / 6,541）—— 用 `igi-chunked.py hb_wuhan --page-chunk 20 --max-pages 165`。
5. 人民网 fid 密集扫描续跑（本轮停在 fid ≈2,425）。

### 第 7 轮 · 2026-10-09 下午场（16:06–16:48）

- **提交** `04038cf`（代码+文档）→ `a713dea`（数据）；**快照** `step-350-govqa-igi-cityportals-20261009`（`^{commit}` 已核 = `a713dea`）。
- **开工盘点（任务书前提第 6 次过时）**：307 个适配器，**零数据仍只有 2 个**（`hb-rst-igi`/`hb-wjw`，均 `status=dup`）
  ⇒ 不再照任务书找活，沿 §十六 的 **IGI 线**横向扩展。
- **★★ 本轮最关键的教训（踩了才明白）**：`nohup … &` 起的采集**会被工具杀掉**。
  实测三个（nmg/gz/nanning）日志都只写到启动后几十秒，`Get-CimInstance Win32_Process` 复核**三个进程全没**
  （只剩另一对话的 `sx_igi`）。⇒ **必须 `run_in_background=true` + 命令体直接是 python**，
  **不加 `&`、不加 `nohup`**（输出重定向到 `recon/*.log` 仍可用）。改姿势后四路**立即稳定推进**。
  ⚠ 之前 6 轮之所以没踩到：都是先 `nohup &` 再靠运气/靠别的进程……本轮是**第一次在这条线上实测确认**。
- **★ 现场归属**：另一对话在跑 `sx_igi`（`igi-resume.sh`，12:16 起）+ `nat-cnipa` + `sd-yantai` + `js-yangzhou`
  ⇒ **sx/gx/nx、部委线、山东/江苏地市都不碰**；我走 **nmg-igi / gz-igi / 包头 / 南宁**。
- **★ 新接两个城市门户**（任务书点名的「登记了却没数据」问题，本轮真正解决）：
  - `nanning-igi`（南宁市，IGI siteId=8，枚举上界 **18,977**；广西此前全部存量仅 **1,869** ⇒ ≈**10 倍**）
  - `baotou-igi`（包头市，IGI 42 站 / **7,243**；内蒙古）
  - 两个都：明细可达（答复在 `datas.REPLYS[].REPLYHTMLCONTENT`）；与同省既有线**抽 100 条 id 重叠 0**；
    南宁地域**真实**（14 种南宁下辖区县）⇒ 不剥离；包头地域**恒定默认值** ⇒ `postprocess` 剥离。
- **落盘 +4,655 条**（四路并行，全部托管后台）：
  | 线 | 起点→终点 | 新增 | 窗口 |
  |---|---|---|---|
  | `nmg-igi`(66) | 1,200→**2,400** | +1,200 | 页 61-80 / 81-100 / 101-120 |
  | `gz-igi`(70) | 1,194→**2,391** | +1,197 | 页 61-80 / 81-100 / 101-120 |
  | `baotou-igi`(46,57) | 0→**1,464** | +1,464 | 46 **整站 1,068/1,068（答复率 100%）** + 57 页 1-20 |
  | `nanning-igi`(8) | 0→**794** | +794 | 页 1-20 / 21-40 |
  审计：**重复 0 / 空答复 0 / 答复==问题 0 / <10字 0**（四条线全部）。
- **★ 新工具 `recon/igi-city-probe.py`**（只读：可采性 + id 重叠 + 地域抽样）。
  为什么必须新建：`igi-siteid-scan.py` 只证明「列表返回 totalResults>0」，**不等于能采**
  （贵州 11 个 siteId 里 6 个 404）。实测**沈阳（53 站/17,369）、南京（63 站/4,065）可采**，登记为下一轮。
- **★ 两条口径（写探针时踩到）**：
  ① **IGI 列表行是【大写键】**（`METADATAID/ISREPLY/PROVINCE/CITY/AREA`）——
     按小写驼峰取字段会**静默拿到空值**，探针第一版因此误报「答复正文长度=0」、看着像不可采。
  ② **没有 `--sites-json` 时 `igi-chunked.py` 的页数上界默认 300**（= 6,000 条硬顶，§十六 同源）
     ⇒ 必须显式 `--max-pages`（南宁按 `--max-pages 949` = ⌈18977/20⌉）。
- **★ 南宁速率**：约 **56 s/页**（20 页窗口 ≈ 1,000 s / 395-400 条）⇒ 949 页全量 ≈ **15 h**，跨轮续采。
- **★ 南宁地域稀疏（新观察）**：页 1-20 的 395 条 **89%** 有地域；页 21-40 的 399 条 **0%**
  ⇒ 合并 794 条只有 **44%** 非空。`order=1` 是倒序（新→旧）⇒ **地域只对较新信件填充**，越往后越低。
  **不剥离**（不是单值恒定，是真实但稀疏），靠 `coverage-matrix.py` 的 `PROVINCE_PREFIX` 归省。
- **顺手第三条线**：人民网 fid 密集扫描 `1559..4600` ⇒ jsonl **1,464→1,645 行（+181 fid，扫到 fid 2245）**。
  ⚠ 该 jsonl 是**共享生成产物 ⇒ 不提交**，只登记增量。实测 ≈**5.6 fid/分钟**。
- **收工**：`TaskStop` 掉全部 5 个后台任务（4 IGI + fid）。被停时各线正在翻的窗口整块丢失
  = `--page-chunk` 的设计代价（损失 ≤1 窗口）。
- **未碰**：sx/gx/nx、部委线（`MINISTRY-ENTRIES.md`/`probe-ministries.py`/`mem_gov.py`/`mee_gov.py`）、
  共享生成产物（`coverage-*`/`locate-rate.json`/`assets-*`）、另一对话在写的 `sd-yantai`。

### 下一轮可挑（第 7 轮重排）

0. **★ 四条 IGI 续采（最高优先，仍无人认领）** —— 直接重跑，只取新增：
   - `igi-chunked.py nmg_igi --sites-json igi-siteid-neimenggu.json --page-chunk 20`（66 站 283 页，现到 120）
   - `igi-chunked.py gz_igi --sites-json igi-siteid-guizhou.json --page-chunk 20`（70 站 822 页，现到 120）
   - `igi-chunked.py baotou_igi --sites-json igi-siteid-baotou.json --page-chunk 20`（46 站已完成；57 站 751 条待续）
   - `igi-chunked.py nanning_igi --max-pages 949 --page-chunk 20`（**必须显式给 `--max-pages`**，现到 40 页）
   ⚠ 全部**必须托管后台**（`run_in_background=true`，命令体直接是 python，**不加 `&`/`nohup`**）。
1. **沈阳（53 站 / 17,369）、南京（63 站 / 4,065）接适配器** —— 列表/明细已实测可采，
   接前先 `recon/igi-city-probe.py shenyang nanjing` 验 id 重叠与地域。
2. `igi-siteid-scan.py` 补扫 **西宁 / 银川 / 贵阳 / 长春 / 福州 / 青岛 / 长沙 / 深圳 / 成都**。
3. 人民网 fid 密集扫描 `2246..4600`（本轮停在 fid 2245）。

### 第 6 轮 · 2026-10-09 下午场（15:11–16:0x）

- **提交** `935bc31`（能力+两处修复）→ `b3ba5d0`（数据）；**快照** `step-344-govqa-igi-pagechunk-20261009`（已核 = `b3ba5d0`）
- **开工盘点（任务书前提第 5 次过时）**：307 个适配器，**零数据仍只有 2 个**（均 `status=dup`）；
  待补缺口 `hb-hdjl` 3461/3535、`sn-igi` 4084/4097、`heb-szj` 1043/1043、`xj-dchs` 227/227 全部已收口。
- **★ 现场归属（本轮最关键的一步）**：`8d49641`(13:10) 一个提交含 **山东大城市 + 江苏扬州 +
  `recon/igi-resume.sh`** ⇒ **IGI 的 sx/gx/nx 续采已归另一对话**（脚本明写 sx→gx→nx、单源上限 2 万）。
  `cf6c797`(14:42「浙江 11 市」) 还**顺带提交了 `sx-igi-24`** ⇒ 本仓第 3 次「工作区被别人的提交带走」。
  ⇒ **sx/gx/nx 不要再碰**；选 **`nmg-igi` / `gz-igi`**（我 §十五 建、各只有 3 条、上界 26,074 / 30,041）。
- **★★ 发现 1（静默截断）**：`igi-chunked.py` 旧代码 `max_pages=300` 写死 = **每站 6,000 条硬顶**。
  山西 `siteId=24` 枚举 **14,662**（需 734 页）⇒ 实测落盘正好 **5,998** ⇒ **少取 8,664 条（59%）**，
  且**日志上看不出来**。贵州 `siteId=70`（16,421 / 822 页）同理。已按 `ceil(total/20)` 修
  ⇒ **`igi-resume.sh` 不改一行，下次跑 `sx_igi` 自动翻满 734 页**（对它是增量续采）。
- **★★ 发现 2（实体残留）**：`_igi_common.clean()` 不还原 HTML 实体 ⇒ `&nbsp;` 以**字面 6 字符**留在正文。
  实测 `sx-igi` 7,281 条：**958 条（13.2%）含、422 条（5.8%）以它开头**。**影响全部 96 个 IGI 适配器**。
  已修（先去标签、再 `html.unescape`）；参数名 `html`→`frag`（原名遮蔽 `html` 模块）。
  ⚠ 历史行不会被改写 ⇒ 存量要清必须整站重采（`skip_ids=set()`）。
- **★ 新能力**：`_igi_common.harvest_igi(page_from=1)` + `igi-chunked.py --page-chunk N / --max-pages N`
  ⇒ **大站站内也能增量落盘**。实测 **20 页/窗口 ≈ 9.2 分钟 / 400 条**（27 s/页）
  ⇒ 中断损失从「整站 ~2 h」压到「≤1 窗口」（原 `sx-igi-24` 5,998 条跑了 8,133 s）。
  ⚠ `--only` 路径没有枚举 total，不给 `--max-pages` 会**空翻 300 个窗口**（本轮踩到，已修）。
- **落盘**：`nmg-igi-66` 页 1-60 **+1,197**（全站 283 页 ≈21%）；`gz-igi-70` 页 1-60 **+1,191**（822 页 ≈7%）。
  质量：重复 id 0 / 空答复 0 / 答复==问题 0 / <10字 0 / **含 `&nbsp;` 0**（修复生效的证据）；
  JSONL 逐行可解析、失败 0。
- **新增**：`recon/audit-igi-prov.py`（按前缀 glob 的通用 IGI 审计；`audit-igi-new.py` 硬编码文件名用不了）。
- **★ 新操作纪律**：**跑分片驱动一律加 `python -u`**（`harvest_igi` 的 `print` 没 `flush`，
  重定向到文件时块缓冲 ⇒ `-u` 一加日志就实时）；**收工必须 `TaskStop` 干净停掉后台采集**
  （留着跨轮会与下一轮同站进程叠加速率、违反「间隔 ≥1.5 s」）。
- **未碰**：sx/gx/nx、共享生成产物（`coverage-*` / `locate-rate.json` / `assets-*`）、另一对话的地盘。

### 下一轮可挑（第 6 轮重排）

0. **★ 内蒙古 / 贵州 IGI 续采（最高优先，明确无人认领）**
   - `.venv/Scripts/python.exe -u tools/gov-qa/recon/igi-chunked.py nmg_igi --sites-json igi-siteid-neimenggu.json --page-chunk 20`
   - `.venv/Scripts/python.exe -u tools/gov-qa/recon/igi-chunked.py gz_igi --sites-json igi-siteid-guizhou.json --page-chunk 20`
   - 重跑自动只取新增。内蒙古剩 ~263 页、贵州剩 ~762 页。⚠ **收工 `TaskStop`**。
1. **★ 4 个城市门户接适配器**（`recon/igi-siteid-<tag>.json` 已枚举，**接前必须先验 id 重叠**）：
   南宁（1 站/**18,977**）、沈阳（53 站/**17,369**）、包头（42 站/7,243，**内蒙古 ⇒ 与 nmg-igi 交叉去重**）、
   南京（63 站/4,065）。**海口只有 2 站/31 条 ⇒ 放弃。**
2. `igi-siteid-scan.py` 补扫 **西宁 / 银川 / 贵阳 / 长春 / 福州 / 青岛 / 长沙 / 深圳 / 成都**（§十五 只扫了 5 个）。
3. 人民网 fid 密集扫描 `1559..4600`（第 4 轮实测停在 2065）。

### 别再试（第 6 轮新增）

- **`--only` + `--page-chunk` 不传 `--max-pages`** ⇒ 空翻 300 个窗口。
- 海口 IGI 只有 **2 站 / 31 条** ⇒ 放弃。
- **sx/gx/nx 的 IGI 续采** ⇒ 已归另一对话（`igi-resume.sh`），别碰。

### 第 5 轮 · 2026-10-09 上午场（11:20–12:0x）
- **提交** `5b896ee` → `d3422c8` → `5f51025` → `8736a87` → `0428638`
- **开工盘点（第 4 次确认任务书前提过时）**：305 个适配器，**零数据只剩 2 个**（均 `status=dup`）
  ⇒ 不再照任务书找活，沿 §十四 的 **IGI 线**横向扩展。
- **★★ 最大发现：IGI 平台远不止 9 个省 —— 做了「门户横向普查」**（新工具 `recon/igi-portal-sweep.py`）
  | 集 | 命中 |
  |---|---|
  | 省门户（22）| **内蒙古**、天津 |
  | 城市门户（34）| 包头、沈阳、南京、南宁、海口、贵阳、西宁、银川 |
- **内蒙古 = 42 站 / 26,074 条**（该省存量仅 67 ⇒ **≈389 倍**，正是任务书点名的缺口）⇒ `nmg-igi`
- **贵州** siteId 窗口 1..60→1..300 ⇒ **44 站 / 30,041 条**（最大 siteId=70 有 16,421）⇒ `gz-igi`
  （剔除 gz-portal 已占 11 站，实跑 33 站）
- **天津 `tj.gov.cn` IGI siteId=186 = 123,546 条**（复验为真）⇒ **只登记线索、不建适配器**
  （天津已有 `tj-enorth`，另一对话线；怕「source 不同 ⇒ 同一信件记两遍」）
- **★ 口径校准**：枚举 `totalResults` 是**全部信件**，不是可采量。广西 siteId=206：列表 5,184
  行（= 枚举值，吻合），`ISREPLY=1` 只有 **857** ⇒ 入库 831（答复率 **16.5%**）；宁夏 187 是 100%。
  ⇒ **别再用 totalResults 估工作量**。
- **★ 修 `igi-chunked.py` 跨省 id 污染**：原硬编码 `existing_ids("sx-szxx")` 对所有模块生效
  ⇒ 改为模块声明 `EXTRA_SEEN_KEYS`。
- **★ 上轮战略失误**：`--limit 1300` 全耗在最小站（126 只 1 条、65 只 7 条），
  **山西最大的 24/32/41/92/45/36 一条没采** ⇒ 跑大站**必须降序**。
- **★ 弱省不是死锁**：`yn-xf` 66/66、`nmg-xinxiang` 67/67、`fj-hdjl` 143/143 全部跑尽
  ⇒ 弱省的解法是**找第二个源**。
- **★ 日志假死新成因**：`_igi_common.harvest_igi` 的 `print` **没有 flush**（块缓冲）⇒
  `tail` 停在十几分钟前**不代表卡住**；判进度看 `igi-chunked.py` 的「累计」行。

### 第 4 轮 · 2026-10-09 上午场（10:41–11:1x）
- **提交** `178d743`；**快照** `step-329-govqa-sx-gx-igi-20261009`
- **★ 任务书三处清单再次全部过时**（第 3 轮已判过、本轮复核仍成立）：302 个适配器
  **只剩 2 个零数据**，且都是 `status=dup`（`hb-rst-igi`/`hb-wjw` 与 `hb-hdjl` 同后端）。
- **选线**：另一个对话在跑 浙江地市/衢州、江苏扬州、天津 enorth、国家部委
  ⇒ 选**无人认领**的 **IGI `siteId` 枚举**。
- **★ 核心发现（写进 SITE-REGISTRY §十四）**：IGI siteId 枚举有**双重盲区**
  ① 旧脚本只扫 1..60（宁夏有效 115、湖北有效 71 都在窗口外）；
  ② **山西/广西/宁夏从未被枚举过**。扫 1..300（**空 appId**）后实测：
  **山西 46 站 / 84,381 条**（旧 400）、**广西 208 站 / 34,938 条**（旧 138）、
  **宁夏 65 站 / 13,014 条**（旧 597）。
- **两个可复用的硬结论**：
  1. **`appId` 是过滤条件**（山西 siteId=36：带 appId 826 / 空 appId 4653）⇒ 枚举与采集用空 appId。
  2. **地域字段逐站判真伪**：湖北/宁夏/广西是真地域；**山西逐条恒定=门户自身位置（假）**
     ⇒ 山西必须剥离，否则污染三级归属。
- **落盘**：山西 849、广西 567、宁夏 664（+67）；三省全量 8.4 万/3.5 万/1.3 万，
  **分片增量、跨轮续采**。
- **新增**：`recon/igi-siteid-scan.py`、`recon/igi-chunked.py`、`adapters/sx_igi.py`、
  `adapters/gx_igi.py`、`adapters/nx_igi.py`。
- **★ 同一个坑踩了两次**：两次按**扫描中途的日志**下结论 —— 先写「山西只有 29 个 siteId」
  （实为 **46**），后又写「宁夏只有 1 个 siteId、无可枚举增量」（实为 **65 个 / 13,014 条**）。
  ⇒ **枚举清单必须等扫描跑完、从 json 取，绝不能用中途日志。**
- **质量**：山西 `sx-igi-28` 有 18 条「X月没有政务建议咨询类信息」**占位记录**
  （question == answer）⇒ 适配器加丢弃规则 + 已落盘就地清理。

### 第 3 轮 · 2026-10-09 早场（06:41–07:2x）
- **提交** `608c34a`；**快照** `step-328-govqa-jx-hygz-20261009`
- **★ 任务书前提已过时**：「45 个零数据适配器」已全部有数据（实测全库 301 个适配器
  只剩 26 个零数据，其中 23 个是另一对话**当时正在跑**的 `sc-*-zwfw`）；
  同时刻有 **13 个 python 采集进程**在跑。⇒ 别再照任务书第一优先找活。
- **选线**：唯一无人认领的两条 = ① 人民网 fid 密集扫描未扫区间 ② **江西**。
- **落盘**：江西 **388 → 425**。
  1. `jx-zf` 388→410：hygz 只落 129/430 的根因是**正文形态**（旧解析只认「问：…答：…」，
     实测另有「正文仅 `答：…`，问题在标题」「`来电人反映… 答：…`」两种）
     ⇒ 按**第一个「答：」切分**；`dept` 回退 `metadata.Source`；
     `_text()` 加 `html.unescape`（**先去标签再还原实体**）。
     ⚠ 改了 `_text` ⇒ **必须整站重采**才清存量实体（harvest 按 id 去重、不改写已落盘行）。
  2. 新源 `jx-gzw-lyxd` 15 条（省国资委·留言选登）。
- **新负面结论**（写进 SITE-REGISTRY §十二）：`recon/jx-config.js` 的 35 个省直部门站 ×
  24 个通用栏目代号全扫（840 次请求）⇒ 16 站有数据，但**只有 `lyxd` 是真问答**；
  `hydt`/`yjzj`/`zxft`/`sjxx`/`hdjl`/`ldxx` 分别是新闻稿/征求意见/访谈实录/审计报告/联系方式/简历。
- **fid 密集扫描**：`601..1558` 已扫满（任务书说的三段缺口也过时），真缺口只有 `1559..4600`。
  本轮后台 +117 个 fid（≈3.7 fid/分钟 ⇒ 全程约 13 小时，跨轮长任务）。
  ⚠ 该 jsonl 是共享生成产物（开工时已有别人未提交增量）⇒ **不提交**，只写文档。
- 未改任何共享基座；`adapters/__init__.py` 只加 1 行（加前核过 diff 不含他人改动）。

### 第 2 轮 · 2026-10-08 深夜（23:16–00:40，跨零点）
- **提交** `8d73cfb`；**快照** `step-316-govqa-js-jact-20261008`
- **选线判据**：「45 个零数据适配器」里 9 省门户 + 贵州 6 已由另一对话跑出数据
  （bj-hdjl 195 / cq-hdjl 500 / fj-hdjl 143 / hlj-hdjl 3952 / hn-hdjl 500 / nmg-xinxiang 67 /
  jx-zf 388 / yn-xf 66 / zj-mhww 1000；贵州 6 站 2~100）。
  `find -newermt '-10 minutes'` 命中另一对话在跑 `cq-igi`/`gs-*`/`sd-*`/`tj_enorth`
  ⇒ **唯一无人认领的真缺口 = 江苏 12 厅局**（`adapters/js_*.py` 冻结在 19:03）。
- **落盘**：首采 12 站 +1,997（`recon/js-zero-batch.sh`）；
  续采 3 站 +826（js-da +387 / js-czt +249 / js-doc +190，`recon/js-extend-batch.sh`）。
  江苏 js-* 口径 1,930 → **4,753**（16 → 28 站）；全库 68,447 → **74,491 条**（含另一对话增量）。
- **两个新发现**（写进 SITE-REGISTRY §十）：
  1. `js-jyt` sysid=126 报 totalRecord=810 但列表**只给 76 行**；复跑同样 76、新增 0
     ⇒ **`totalRecord` 只能当上界、不能当目标**（贵州 6/11 个 siteId 404 是同类第二个实例）。
  2. jact「内容回复」字段混着**内部办理批注**（`已电话回复咨询人。`/`拟请会计处阅办`…），
     161 条 <10 字 ⇒ 无依据、不污染考卷，但虚增语料；下游可按长度/黑名单过滤。
- **质量复核** 2,823 条：空答复 0 / 答复==问题 0 / 重复 id 0。
- **归属文档**：`tools/gov-qa/SITE-REGISTRY.md` §十 + `recon/ROUND-2026-10-08-js.md`。
- **没改共享基座**（`_jact_common.py` / `harvest.py` / `adapters/__init__.py` 全未动）。

### 第 1 轮 · 2026-10-08 夜（22:36–23:1x）
- **提交** `9e6df9c`；**快照** `step-315-govqa-zj-sn-xz-20261008`
- **结果**：语料 65,482 → 67,626 条；浙江 28→1,028、陕西 207→1,002、西藏 22→364、甘肃 18→434；
  「未归属」414 → 0；三级（省+市+县）归属 3,053 → 9,016 条。
- **落盘**：`zj-mhww` +1000（新源，两轮各 500）、`sn-igi` +795、`xz-igi` +342。
- **修的两个真缺陷**：
  1. 「无游标列表接口 ⇒ 第二轮恒 0 新增」（命中 zj-mhww / sn-igi / xz-igi）——
     修法 = 适配器开跑先读自己已落盘的 id，命中则不请求明细、不计入 limit；
     `_igi_common.py` 加 `existing_ids()` + `harvest_igi(skip_ids=None)`（默认 None = 旧行为不变）。
  2. `recon/coverage-matrix.py` 的 `PROVINCE_PREFIX` 漏 `gs-`（414 条掉「未归属」）——补一行。
- **归属文档**：`tools/gov-qa/SITE-REGISTRY.md` §九「2026-10-08 夜场」（全部事实与证据在此）。

## ★ 每轮开工必做（踩出来的）

1. **先判"另一个对话是否正在写"**：`find tools/gov-qa -newermt '-10 minutes' -type f` +
   查 python 进程。命中就**只碰没人动的那条线**。
2. **`git add` 只加自己的文件，加完立刻 commit**，提交前 `git diff --cached --name-only` 逐条核。
   **绝不 `git add tools/gov-qa`**（暂存区全仓共享）。
3. **不要提交共享的生成产物**（`coverage-matrix.*`、`coverage-by-level.*`、`locate-rate.json`、
   `assets-*.json`）—— 工作区里那些常是**另一个对话写一半的**。
   要数字就用**只读计算**（import coverage-matrix 模块、不落盘）。
4. **盘点零数据必须一起看 `status`**：只看"有没有 data 文件"会把 `hb-rst-igi`/`hb-wjw`
   误报成缺口 —— 它们是 `status=dup`（与 `hb-hdjl` 同后端）。
5. **`recon/*.log` 被 gitignore** ⇒ 关键日志证据要**抄进文档**才算留痕。
6. **`harvest.py` 只在跑完时落盘** ⇒ `timeout` 必须 > `limit × 单条耗时`；
   单条耗时：jact ≈ **1.5s**、zj-mhww ≈ 2.5s、IGI ≈ 1.5s。
   **别用「文件没长」判死**（进程跑完前文件本来就不长）。
7. **`data/js-*.jsonl` 全部未入库**（另一对话 19:03 那批也没提交）⇒
   本轮只 add 自己这 15 个（12 新 + 3 续采），其余 13 个留给它的主人。

## ★ 下一轮开工前必看（第 3 轮更新）

**任务书里的「第一优先 / 待补缺口 / fid 缺口」三处清单已全部过时**（第 3 轮实测）：

| 任务书说 | 实测（2026-10-09 早场） |
|---|---|
| 45 个零数据适配器（江苏 21 + 9 省门户 + 贵州 6） | **全部有数据**；全库只剩 26 个零数据，23 个是另一对话在跑的 `sc-*-zwfw` |
| fid 缺口 `970-1599`/`1890-2599`/`2820-4600` | `601..1558` **已扫满**；真缺口只有 `1559..4600` |
| 待补缺口 hb-hdjl/hb-wuhan/heb-szj/xj-dchs/sn-igi/xz-igi | `heb-szj` 1043 ✅、`xj-dchs` 227 ✅ 已到目标；hb-* 是另一对话 02:22 起在推（`recon/gap-hb-r3.sh`） |

⇒ **开工第一步永远是现场盘点，不是照单执行**：
`find tools/gov-qa -newermt '-10 minutes'` + `Get-CimInstance Win32_Process` 取 python 命令行
+ 跑「零数据适配器」盘点脚本。命中别人在跑的线就**换线**。

## 下一轮可挑（第 5 轮重排）

0. **★ IGI 大站续采（最高优先，明确无人认领）** —— 逐 siteId 落盘、重跑只取新增：
   - `.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py nmg_igi`（内蒙古 42 站 / 26,074）
   - `.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py gz_igi`（贵州 33 站 / 30,041）
   - `.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py sx_igi`（山西 45 站 / 84,381）
   - `.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py gx_igi`（广西 207 站 / 34,938）
   - `.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py nx_igi`（宁夏 63 站 / 13,014）
   - ⚠ 全部是**上界**（只落已答复，答复率逐站 16%~100% 不等）；**跑大站要降序**、limit 别给太大
     （单块跑完才落盘，limit 1200 ≈ 半小时）。
1. **★ 8 个城市门户 IGI 待枚举/接入**（`igi-siteid-scan.py` 已加好 tag）：
   `shenyang / nanjing / xining / haikou / baotou / nanning / guiyang / yinchuan`
   - 优先 **西宁（青海 338）、海口（海南 2241）** —— 对应两个**弱省**，边际价值最高。
   - ⚠ 南宁/贵阳/银川可能与省级门户（gx-igi/gz-igi/nx-igi）**重叠** ⇒ 接入前先比 id。
   - 枚举结果在 `recon/igi-siteid-<tag>.json`。
2. **天津 `tj.gov.cn` IGI（siteId=186 = 123,546 条）待认领**：
   接之前**必须先验它与 `tj-enorth` 的重叠**（同一批信件两 source 会记两遍）。
3. **三条硬缺口收尾**（本轮已起后台）：`hb-hdjl` 2,356/3,535、`hb-wuhan` 3,306/6,541、
   `sn-igi` 3,205/4,097 ⇒ 直接重跑 `harvest.py --site <k> --limit <目标>`。
4. **WAF 拦住的 10 个门户待复测**（IGI 有无**未证实**）：甘肃/青海（省）+ 长春/福州/青岛/长沙/深圳/成都/兰州/乌鲁木齐（市）。
5. **人民网 fid 密集扫描 `1559..4600`**（第 4 轮实测停在 fid 2065，≈3.3 fid/分钟）
   - ⚠ 该 jsonl 是**共享生成产物** ⇒ **不提交**，增量写进 SITE-REGISTRY。
6. 85 个 IGI 薄壳适配器批量续采（基座已修 `45ce28b`）—— 开工前先确认另一对话是否已停。

### 别再试（第 5 轮新增负面结论）

- **无 IGI**（已实测证伪，别再试）：北京/河北/辽宁/黑龙江/上海/江苏/浙江/安徽/福建/江西/河南/湖南/
  广东/海南省/四川/云南/新疆/山东（山东 http 返 404）；城市里 **太原 404、呼和浩特 422、
  石家庄/南昌/济南/苏州 = 首页 HTML 兜底**、大连/哈尔滨/杭州/宁波/厦门/郑州/广州/昆明/拉萨/西安/无锡 404。
- 弱省（云南 `yn-xf` 66、内蒙古 `nmg-xinxiang` 67、福建 `fj-hdjl` 143）**上游=存量，已跑尽**，
  **不是续采死锁**，别再重跑旧适配器找增量。

## 下一轮可挑（第 4 轮重排）

0. **★ 山西 / 广西 / 宁夏 IGI 续采（最高优先，明确无人认领）**
   - `.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py sx_igi`
   - `.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py gx_igi`
   - `.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py nx_igi`
   - 全量 山西 **8.4 万** / 广西 **3.5 万** / 宁夏 **1.3 万**，单轮跑不完 ⇒
     **逐 siteId 落盘、跨轮续采**（重跑自动跳过已落盘 id，只取新增）。
     默认按 totalResults **降序**；想先铺站点用 `--only`。
   - 枚举清单在 `recon/igi-siteid-{shanxi,guangxi,ningxia}.json`（权威，别用日志手抄）。
1. **西藏 / 贵州 / 湖北门户的 siteId>60 未重扫**（旧扫只到 60，可能还有增量）：
   `.venv/Scripts/python.exe tools/gov-qa/recon/igi-siteid-scan.py xizang|guizhou|hubei`
2. **人民网 fid 密集扫描 `1559..4600`**（第 4 轮实测：**进程已停**在 fid 2065，
   日志 `recon/liuyan-fid-dense-scan-r5.log`；可续跑，脚本按已扫 fid 自动跳过）
   - ⚠ 该 jsonl 是**共享生成产物** ⇒ **不提交**，增量写进 SITE-REGISTRY。
3. 85 个 IGI 薄壳适配器批量续采（基座已修 `45ce28b`）—— 开工前先确认另一对话是否已停。

## 下一轮可挑（第 3 轮重排，多数已过时，保留作对照）

1. **人民网 fid 密集扫描 `1559..4600`**（最明确的无人认领线，可续跑）
   - 命令：`.venv/Scripts/python.exe tools/gov-qa/recon/liuyan-fid-dense-scan.py 1559 4600 liuyan-fid-dense-scan.jsonl 1.0 120`
   - **实测 ≈3.7 fid/分钟**（每约 13 个 fid 撞一次 403，冷却 120s）⇒ 剩余约 2,925 个 fid ≈ **13 小时**，
     属**跨轮长任务**，每轮接着跑（脚本按已扫 fid 自动跳过）。
   - ⚠ 该 jsonl 是**共享生成产物**（开工时已有别人未提交增量）⇒ **不提交**，增量写进 SITE-REGISTRY。
2. **江西部门站的信箱接口 `/api/mail/list`**（未打通，可能是江西的主要增量）
   - 每个部门站有自己的 `pc2024/js/config.js`（内含 `tenantId/deptId/siteId/qdId`）。
     2026-10-08 只试过**省政府站**的参数 ⇒ 返 0。拿**部门站自己的** `userIdObj` 再试。
   - 已有工具：`recon/jx-dept-probe.py`（35 站 × 栏目代号扫描）、`recon/jx-dept-sample.py`（结构核验）。
3. **85 个 IGI 适配器批量续采**（基座已修 `45ce28b`）—— ⚠ 第 3 轮时另一对话把它列为自己的下一轮目标，
   **开工前先确认它是否已停**。
4. `zj-mhww`（49,218 存量）/ `sn-igi`（4,097 存量）续采 —— 都已修好续采，直接反复跑。
   ⚠ 浙江地市、江苏地市、四川、山东、天津、甘肃**都是另一对话在跑**，别重复。

### 别再试（累计负面结论）

- `js-jyt` sysid=126（76 条见底，复跑 0 新增）；`wlt`（HTTP 521）；`ybj3`（空栏目）；`js-suqian`（服务端翻页坏，只有 40 个唯一 id）。
- 江西 `jx-zf` 的 `hygz` 上游 430 − 151 = **279 条是真没答复**（正文无「答」字），别再挖。
- 江西省政府站其余栏目 `wszx/zxxx/zjdc/yjzj/gzly/lyxd/zxly/tsjb/zmhd/wtzx/zjzj` 全 `total=0`。
- 江西 35 个省直部门站里**只有省国资委 `lyxd` 是真问答**（其余栏目是新闻稿/征求意见/访谈/审计/联系方式/简历）。
