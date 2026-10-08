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
