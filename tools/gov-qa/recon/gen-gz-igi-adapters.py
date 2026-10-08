"""按表生成贵州 IGI 厅局适配器（薄壳）。

背景：贵州是**省级统一部署**——多个厅局站都用 IGI 平台，只是 (host, siteId, appId, groupId) 不同。
本生成器把已验证通过的目标写成适配器文件；**不要手改生成出来的文件**，
要改就改本表的 TARGETS 再跑一次（避免生成物与来源不一致）。

用法：python recon/gen-gz-igi-adapters.py
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE.parent / "adapters"

#: (key, 名称, host 前缀, siteId, appId, groupId, 入口页, 备注)
TARGETS = [
    ("gz-jyt", "贵州省教育厅·厅长信箱", "https://jyt.guizhou.gov.cn", "501486", "571", None,
     "https://jyt.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-07 自动搜寻验证）"),
    ("gz-rst", "贵州省人力资源社会保障厅·厅长信箱", "https://rst.guizhou.gov.cn", "502566", "1233", None,
     "https://rst.guizhou.gov.cn/", "IGI 省级统一部署（同上）"),
    ("gz-zfcx", "贵州省住房城乡建设厅·厅长信箱", "https://zfcxjst.guizhou.gov.cn", "69", "50", None,
     "https://zfcxjst.guizhou.gov.cn/", "IGI 省级统一部署（同上）"),
    ("gz-nynct", "贵州省农业农村厅·厅长信箱", "https://nynct.guizhou.gov.cn", "502053", "731", None,
     "https://nynct.guizhou.gov.cn/", "IGI 省级统一部署（同上）"),
    ("gz-swt", "贵州省商务厅·厅长信箱", "https://swt.guizhou.gov.cn", "502590", "1247", None,
     "https://swt.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，igi-hunt-2.txt）"),
    # —— 2026-10-08 第 3 轮扩厅局：门户真实域名逐个抓信箱页，27 站全部接口验证 n>0 ——
    #    证据 recon/gz-igi-hunt-3.txt（含未通站点的负面结论）
    ("gz-fgw", "贵州省发展和改革委员会·厅长信箱", "https://fgw.guizhou.gov.cn", "502516", "1225", None,
     "https://fgw.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-kjt", "贵州省科学技术厅·厅长信箱", "https://kjt.guizhou.gov.cn", "501485", "542", None,
     "https://kjt.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-gxt", "贵州省工业和信息化厅·厅长信箱", "https://gxt.guizhou.gov.cn", "500653", "307", None,
     "https://gxt.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-mzw", "贵州省民族宗教事务委员会·厅长信箱", "https://mzw.guizhou.gov.cn", "500471", "327", None,
     "https://mzw.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-mzt", "贵州省民政厅·厅长信箱", "https://mzt.guizhou.gov.cn", "501697", "699", None,
     "https://mzt.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-sft", "贵州省司法厅·厅长信箱", "https://sft.guizhou.gov.cn", "97", "92", None,
     "https://sft.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-czt", "贵州省财政厅·厅长信箱", "https://czt.guizhou.gov.cn", "502606", "1299", None,
     "https://czt.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-mwr", "贵州省水利厅·厅长信箱", "https://mwr.guizhou.gov.cn", "501659", "684", None,
     "https://mwr.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-whhly", "贵州省文化和旅游厅·厅长信箱", "https://whhly.guizhou.gov.cn", "500430", "225", None,
     "https://whhly.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-tyjrswt", "贵州省退役军人事务厅·厅长信箱", "https://tyjrswt.guizhou.gov.cn", "88", "77", None,
     "https://tyjrswt.guizhou.gov.cn/hdjl/tzxx/xjgs/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-yjgl", "贵州省应急管理厅·厅长信箱", "https://yjgl.guizhou.gov.cn", "500484", "1054", None,
     "https://yjgl.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-sjt", "贵州省审计厅·厅长信箱", "https://sjt.guizhou.gov.cn", "503134", "1396", None,
     "https://sjt.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-gzw", "贵州省国有资产监督管理委员会·厅长信箱", "https://gzw.guizhou.gov.cn", "502072", "793", None,
     "https://gzw.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-tyj", "贵州省体育局·厅长信箱", "https://tyj.guizhou.gov.cn", "68", "46", None,
     "https://tyj.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-stjj", "贵州省统计局·厅长信箱", "https://stjj.guizhou.gov.cn", "502060", "858", None,
     "https://stjj.guizhou.gov.cn/zmhd/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-ylbzj", "贵州省医疗保障局·厅长信箱", "https://ylbzj.guizhou.gov.cn", "101", "94", None,
     "https://ylbzj.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-dsj", "贵州省大数据发展管理局·厅长信箱", "https://dsj.guizhou.gov.cn", "500670", "358", None,
     "https://dsj.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-lyj", "贵州省林业局·厅长信箱", "https://lyj.guizhou.gov.cn", "500437", "237", None,
     "https://lyj.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-lshwzcb", "贵州省粮食和物资储备局·厅长信箱", "https://lshwzcb.guizhou.gov.cn", "503368", "1421", None,
     "https://lshwzcb.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-atcm", "贵州省中医药管理局·厅长信箱", "https://atcm.guizhou.gov.cn", "500440", "242", None,
     "https://atcm.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-invest", "贵州省投资促进局·厅长信箱", "https://invest.guizhou.gov.cn", "500470", "331", None,
     "https://invest.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-stymj", "贵州省生态移民局·厅长信箱", "https://stymj.guizhou.gov.cn", "500472", "618", None,
     "https://stymj.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-wsb", "贵州省人民政府外事办公室·厅长信箱", "https://wsb.guizhou.gov.cn", "501794", "696", None,
     "https://wsb.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-wsg", "贵州省文史研究馆·厅长信箱", "https://wsg.guizhou.gov.cn", "501489", "577", None,
     "https://wsg.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-jyglj", "贵州省监狱管理局·厅长信箱", "https://jyglj.guizhou.gov.cn", "502238", "674", None,
     "https://jyglj.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-jdglj", "贵州省戒毒管理局·厅长信箱", "https://jdglj.guizhou.gov.cn", "502602", "1282", None,
     "https://jdglj.guizhou.gov.cn/hdjl/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
    ("gz-jkj", "贵州省疾病预防控制局·厅长信箱", "https://jkj.guizhou.gov.cn", "503467", "1636", None,
     "https://jkj.guizhou.gov.cn/", "IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）"),
]

TEMPLATE = '''"""适配器：**{name}**——IGI 平台（贵州省级统一部署的一个厅局）。

⚠ **本文件由 `recon/gen-gz-igi-adapters.py` 生成**，请勿手改；
要调整参数请改生成器里的 TARGETS 再跑一次。

参数（自动搜寻验证所得，见 `recon/igi-hunt.txt`）：
 · host `{host}` → 接口基址 `{host}/IGI`
 · siteId={sid}, appId={aid}{gid_note}
 · 须带 `Referer`（该厅站点），否则 403。
{note_line}
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {{
    "key": "{key}",
    "name": "{name}",
    "kind": "api",
    "level": "province",
    "entry": "{entry}",
    "status": "ok",
    "note": "IGI 平台（siteId={sid}, appId={aid}{gid_short}）；带省/市/区三级归属",
}}

BASE = "{host}/IGI"
SITE_ID = "{sid}"
APP_ID = "{aid}"
GROUP_ID = {gid_repr}
REFERER = "{referent}"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
'''


def main() -> int:
    for key, name, host, sid, aid, gid, entry, note in TARGETS:
        body = TEMPLATE.format(
            key=key, name=name, host=host, sid=sid, aid=aid,
            gid_note=f", groupId={gid}" if gid else "",
            gid_short=f", groupId={gid}" if gid else "",
            gid_repr=repr(gid) if gid else "None",
            entry=entry, referent=host + "/",
            note_line=f"## 备注\n{note}\n" if note else "",
        )
        (OUTDIR / f"{key.replace('-', '_')}.py").write_text(body, encoding="utf-8")
        print("written", key)
    return 0


if __name__ == "__main__":
    main()
