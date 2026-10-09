r"""「静态 `content/post_<id>.html` 列表」族 · 共用采集引擎（2026-10-10 新增）。

## 适用形态（广东 9 个市在用，见 `recon/probe-post-list.py`）

```
列表  {BASE}{LIST}index.html            # 第 1 页
      {BASE}{LIST}index_2.html          # 第 2 页起（⚠ 没有 index_1.html，试了 404）
明细  {BASE}{LIST}content/post_<id>.html
```

明细页是**服务端渲染**，内容放在 `<table class="table_t">` 里，
每行是 `<th>标签</th><td>值</td>` 对（可一行多对）：

```
<tr><th>昵称</th><td>先生</td><th>留言时间</th><td>2026-09-09</td></tr>
<tr><th>主题</th><td>咨询…</td></tr>
<tr><th>内容</th><td>…</td></tr>
...
<tr><th>答复单位</th><td>蓬江区教育局</td></tr>
<tr><th>答复内容</th><td>…</td></tr>
```

⇒ **引擎只做「th/td 对 → dict」**，字段名由各站自己声明
（`Q_KEYS` / `A_KEYS`）—— 因为**栏目名各省不一**（实测踩过：
惠州 `ftjhyg` 是「访谈计划预告」、揭阳 `ldjf` 是「市长简历」，都不是问答）。

## ⚠ 两条实测教训

1. **`content/post_` 不等于「留言」** —— 同一个 CMS 下既挂留言选登，也挂访谈预告、
   领导简历。**必须先取一条明细确认是问答**（GOAL.md #6）再写适配器。
2. **翻页从 `index_2.html` 起**，`index_1.html` 一律 404（`index.html` 才是第 1 页）。
"""
from __future__ import annotations

import html
import re
import time

TAG_RE = re.compile(r"<[^>]+>")
#: `<th>标签</th><td>值</td>`（一行可多对）
TH_TD_RE = re.compile(r"<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", re.S | re.I)
#: 列表页条目
ITEM_RE = re.compile(r'href=["\']([^"\']*?/content/post_(\d+)\.html)["\']'
                     r'[^>]*>(.*?)</a>', re.S | re.I)
PAUSE = 1.0


def clean(frag: str | None) -> str:
    """去标签 + 还原实体 + 压空白（顺序沿用本仓既有教训：先去标签、再还原实体）。"""
    if not frag:
        return ""
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", frag))).strip()


def parse_detail(html_text: str, *, q_keys, a_keys) -> dict:
    """把明细页的 `<th>/<td>` 对解析成字段 dict。

    `q_keys` / `a_keys`：问题侧、答复侧的**字段标签**（各站自己声明）。
    返回 `{"question": ..., "answer": ..., "fields": {标签: 值}}`。
    """
    fields: dict[str, str] = {}
    for th, td in TH_TD_RE.findall(html_text or ""):
        k = clean(th).replace(" ", "")
        v = clean(td)
        if k and v and k not in fields:
            fields[k] = v
    q = "\n".join(fields[k] for k in q_keys if fields.get(k))
    a = "\n".join(fields[k] for k in a_keys if fields.get(k))
    return {"question": q, "answer": a, "fields": fields}


def list_items(fetch, *, BASE: str, LIST: str, page: int) -> "list[tuple[str, str, str]]":
    """取第 `page` 页的 `[(id, url, title)]`。`page=1` 用 `index.html`。"""
    path = f"{BASE}{LIST}index.html" if page <= 1 else f"{BASE}{LIST}index_{page}.html"
    r = fetch(path)
    if getattr(r, "status_code", 0) != 200:
        return []
    out = []
    for href, pid, title in ITEM_RE.findall(r.text or ""):
        url = href if href.startswith("http") else f"{BASE}{href.lstrip('/')}"
        t = clean(title)
        if t:
            out.append((str(pid), url, t))
    return out


def harvest_post_list(fetch, *, SITE: dict, BASE: str, LIST: str,
                      q_keys, a_keys, limit: int | None = None,
                      max_pages: int = 200, pause: float = PAUSE,
                      skip_ids: set | None = None) -> list[dict]:
    """翻列表页 + 逐条取明细，返回统一记录。

    `skip_ids`：已落盘 id（命中则**不请求明细**、不计入 `limit`）⇒ 可反复跑逐轮推进。
    """
    if skip_ids is None:
        skip_ids = existing_ids(SITE.get("key", ""))
    out: list[dict] = []
    skipped = 0
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        items = list_items(fetch, BASE=BASE, LIST=LIST, page=page)
        print(f"    [{SITE['key']}] 列表第 {page} 页：{len(items)} 条")
        if not items:
            break
        for pid, url, title in items:
            if limit and len(out) >= limit:
                break
            if str(pid) in skip_ids:
                skipped += 1
                continue
            time.sleep(pause)
            try:
                r = fetch(url)
            except Exception as e:                                        # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {pid} {type(e).__name__}（跳过）")
                continue
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 明细 {pid} HTTP "
                      f"{getattr(r, 'status_code', '?')}（跳过）")
                continue
            d = parse_detail(r.text or "", q_keys=q_keys, a_keys=a_keys)
            if not d["answer"] or len(d["answer"]) < 10:
                continue
            extra = {"platform": "post-list", "answer_kind": "留言答复（静态列表）"}
            for k, v in d["fields"].items():
                if k in ("答复内容", "内容"):
                    continue
                extra[k] = v
            out.append({
                "source": SITE["key"],
                "id": str(pid),
                "url": url,
                "question": d["question"] or title,
                "answer": d["answer"],
                "asked_at": d["fields"].get("留言时间") or None,
                "answered_at": d["fields"].get("答复时间") or None,
                "dept": d["fields"].get("答复单位") or "",
                "channel": "留言选登·静态列表",
                "extra": extra,
            })
        time.sleep(pause)
    print(f"    [{SITE['key']}] 收 {len(out)} 条"
          + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
    return out


def existing_ids(site_key: str) -> set:
    """读 `data/<site_key>-*.jsonl` 已有 id（供续采，与 `_igi_common.existing_ids` 同义）。"""
    import json
    from pathlib import Path
    ids: set = set()
    data_dir = Path(__file__).resolve().parent.parent / "data"
    try:
        for p in data_dir.glob(f"{site_key}-*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    mid = str(json.loads(line).get("id") or "").strip()
                    if mid:
                        ids.add(mid)
    except Exception:                                                     # noqa: BLE001
        pass
    return ids
