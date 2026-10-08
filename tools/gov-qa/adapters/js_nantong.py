"""适配器：**南通市·政民互动·市长信箱（truecms getMessageByCondition）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe20~21.txt）
 · 门户 `www.nantong.gov.cn` 互动交流 → 市长信箱
   `https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html`，页面 JS 调
   `POST /truecms/messageController/getMessageByCondition.do`。
 · 接口：`POST https://www.nantong.gov.cn/truecms/messageController/getMessageByCondition.do`
     form: `lmxx=sgkxj`（栏目）、`lmid=b88fd122-d5a3-406e-8388-80b4b55b196b`（市长信箱栏目 uuid）、
           `isGetChild=1`、`pagenum`（页码,1 基）、`pagesize`、`name=`、`type=`
   → JSON：`{"totalCount":302,"pageNum":1,"pageSize":13,"msgList":[{…}]}`
   条目字段（关键）：
     `msgtitle` 标题、`msgcontent` 问题正文、`replycontent` **答复全文**（含 `<br>`）、
     `replyunit` 答复单位、`fbrq`/`createtime` 提交时间（Java date 对象）、`replytime` 答复时间、
     `guid` 主键、`tag` 标签、`htmlpath` 正文页。
   ★ **列表即含问题 + 答复全文**（无需明细）⇒ 采集快。
 · ⚠ `lmid` 才是数据源标识（`lmxx` 只是栏目名，sgkxj/bumxx 用同一 lmid 返回同一批数据）。
 · 时间字段是 Jackson 序列化的 `{year:126,month:8,date:11,…}`（year=距今 1900 年、month 0 基）。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "js-nantong",
    "name": "南通市·政民互动·市长信箱",
    "kind": "api",
    "level": "city",
    "entry": "https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html",
    "status": "ok",
    "note": "POST /truecms/messageController/getMessageByCondition.do；**列表自带问题+答复全文**；totalCount≈302",
}

BASE = "https://www.nantong.gov.cn"
LIST_URL = BASE + "/truecms/messageController/getMessageByCondition.do"
REFERER = SITE["entry"]
LMID = "b88fd122-d5a3-406e-8388-80b4b55b196b"   # 市长信箱栏目 uuid
PAUSE = 1.5
PAGE_SIZE = 20

_TAG = re.compile(r"<[^>]+>")


def _clean(s: str | None) -> str:
    """答复正文是富文本：<br> 换行，其余标签剔除、实体反转义（保留文字逐字不变）。"""
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    return s.strip()


def _jd(v) -> str | None:
    """Jackson Java date 对象 {year,month,date,…} → 'YYYY-MM-DD'。"""
    if not isinstance(v, dict):
        return (v or "").strip() if isinstance(v, str) else None
    try:
        y = int(v.get("year", 0)) + 1900
        mo = int(v.get("month", 0)) + 1
        d = int(v.get("date", 0))
        return f"{y:04d}-{mo:02d}-{d:02d}" if y > 1901 else None
    except (TypeError, ValueError):
        return None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 300) -> list[dict]:
    """翻页取南通市长信箱（列表自带问题 + 答复全文）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch.post(LIST_URL, data={
                "lmxx": "sgkxj", "lmid": LMID, "isGetChild": "1",
                "pagenum": page, "pagesize": PAGE_SIZE, "name": "", "type": "",
            }, headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = r.json() or {}
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = d.get("msgList") or []
        if total is None:
            total = d.get("totalCount")
            print(f"    [{SITE['key']}] 信件总数 totalCount={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("guid") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            answer = _clean(it.get("replycontent"))
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("msgtitle") or "").strip()
            content = _clean(it.get("msgcontent"))
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": _jd(it.get("fbrq") or it.get("createtime")),
                "answered_at": _jd(it.get("replytime")),
                "dept": (it.get("replyunit") or "").strip() or None,
                "channel": "政民互动·市长信箱",
                "extra": {
                    "title": title,
                    "tag": it.get("tag"),
                    "htmlpath": it.get("htmlpath"),
                    "platform": "南通 truecms getMessageByCondition（列表自带答复）",
                },
            })
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
