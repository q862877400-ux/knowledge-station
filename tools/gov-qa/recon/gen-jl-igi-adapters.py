"""按表生成吉林 IGI 厅局适配器（薄壳）——**34 个厅局**。

## 怎么来的
交接 §4.2「IGI 还有大量厅局没探」，第二批用**猜域名**的办法大量 ConnectError。
本轮换了做法：吉林 IGI 是 **`haiyun.jl.gov.cn/IGI` + `(siteId=117, appId=96)` 全省固定、
只有 `groupId` 区分厅局** ⇒ 直接**扫 groupId 一个整数维度**，不依赖任何厅局域名。
扫描结果见 `recon/jl-groupid-roster.txt`（**38 个厅局 / 3,497 封信**），本表的 34 个即
其中尚未落适配器的部分（另 4 个 = 159 交通 / 170 人社 / 172 生态 / 178 卫健 已在库）。

## 两个实测事实（`recon/jl-groupid-scan-evidence.txt`）
1. `groupId` **确实是厅局选择器**（159 只回交通厅、186 只回统计局……）；
   **不带 `groupId`** 回的是**全厅混合池**（total=3802）—— 别拿它当"全量"，会与分组重复。
2. `Referer` **不要求匹配站点**（拿人社的页面当 Referer 请求别的 groupId 一样 200）。

## 已知缺项（如实记）
上游列表接口的 `PUBLISHURL` 字段**全为 null** ⇒ 拿不到该厅信件公示页的真实地址，
故 `entry` 统一指向平台主机；记录里 `id`（=METADATAID）仍是准的。

用法：python recon/gen-jl-igi-adapters.py
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE.parent / "adapters"

BASE = "https://haiyun.jl.gov.cn/IGI"
SITE_ID = "117"
APP_ID = "96"
REFERER = "https://hrss.jl.gov.cn/"

#: (key, 厅局名, groupId, 信件数) —— 信件数取自 recon/jl-groupid-roster.txt
TARGETS = [
    ("jl-tjj", "吉林省统计局", "186", 606),
    ("jl-wlt", "吉林省文化和旅游厅", "177", 353),
    ("jl-ypj", "吉林省药品监督管理局", "195", 239),
    ("jl-nynct", "吉林省农业农村厅", "175", 187),
    ("jl-scjd", "吉林省市场监督管理厅", "183", 139),
    ("jl-zyy", "吉林省中医药管理局", "194", 137),
    ("jl-fgw", "吉林省发展和改革委员会", "161", 107),
    ("jl-gxj", "吉林省工业和信息化厅", "164", 84),
    ("jl-zrzy", "吉林省自然资源厅", "171", 78),
    ("jl-czt", "吉林省财政厅", "169", 76),
    ("jl-tyj", "吉林省体育局", "185", 66),
    ("jl-tyjr", "吉林省退役军人事务厅", "179", 64),
    ("jl-zfcx", "吉林省住房和城乡建设厅", "173", 62),
    ("jl-mzt", "吉林省民政厅", "167", 57),
    ("jl-ybj", "吉林省医疗保障局", "187", 56),
    ("jl-slt", "吉林省水利厅", "174", 51),
    ("jl-sjt", "吉林省审计厅", "181", 49),
    ("jl-sft", "吉林省司法厅", "168", 48),
    ("jl-lyj", "吉林省林业和草原局", "191", 41),
    ("jl-gfdy", "吉林省国防动员办公室", "190", 41),
    ("jl-kjt", "吉林省科学技术厅", "163", 40),
    ("jl-yjt", "吉林省应急管理厅", "180", 38),
    ("jl-gzw", "吉林省国有资产监督管理委员会", "184", 38),
    ("jl-xmy", "吉林省畜牧业管理局", "158", 37),
    ("jl-wsb", "吉林省外事办公室", "182", 33),
    ("jl-jyj", "吉林省监狱管理局", "193", 29),
    ("jl-ggzy", "吉林省公共资源交易中心", "255", 29),
    ("jl-nyj", "吉林省能源局", "192", 26),
    ("jl-mzw", "吉林省民族事务委员会", "165", 25),
    ("jl-jgsw", "吉林省机关事务管理局", "188", 25),
    ("jl-gbdsj", "吉林省广播电视局", "160", 24),
    ("jl-lsj", "吉林省粮食和物资储备局", "189", 24),
    ("jl-swt", "吉林省商务厅", "176", 23),
    ("jl-gat", "吉林省公安厅", "166", 20),
]

TEMPLATE = '''"""适配器：**{name}·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

⚠ **本文件由 `recon/gen-jl-igi-adapters.py` 生成**，请勿手改；
要调整参数请改生成器的 TARGETS 再跑一次。

参数（`recon/jl-groupid-roster.txt` 扫 groupId 所得）：
 · 全省共用 host `{base}`（**吉林不是每厅局一个域名**）
 · siteId={sid}, appId={aid} 全省固定，**只有 groupId={gid} 区分厅局**
 · 须带 `Referer`（但**不必匹配本厅站点**，见 `recon/jl-groupid-scan-evidence.txt`）
 · 上游 `PUBLISHURL` 为 null ⇒ `entry` 指向平台主机，记录 id 仍准
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {{
    "key": "{key}",
    "name": "{name}·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "{entry}",
    "status": "ok",
    "note": "IGI 平台（siteId={sid}, appId={aid}, groupId={gid}）；带省/市/区三级归属",
}}

BASE = "{base}"
SITE_ID = "{sid}"
APP_ID = "{aid}"
GROUP_ID = "{gid}"
REFERER = "{referent}"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
'''


def main() -> int:
    for key, name, gid, _n in TARGETS:
        body = TEMPLATE.format(key=key, name=name, gid=gid, sid=SITE_ID, aid=APP_ID,
                               base=BASE, entry=BASE, referent=REFERER)
        (OUTDIR / f"{key.replace('-', '_')}.py").write_text(body, encoding="utf-8")
        print("written", key)
    print(f"共 {len(TARGETS)} 个；信件合计 {sum(t[3] for t in TARGETS)}")
    return 0


if __name__ == "__main__":
    main()
