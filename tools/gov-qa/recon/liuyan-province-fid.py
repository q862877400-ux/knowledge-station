"""找「地方领导」页并抠出各省 fid（若能按省 fid 采，df 就从随机采样变定向覆盖）。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

CANDIDATES = [
    "https://liuyan.people.com.cn/",
    "https://liuyan.people.com.cn/localLeaders",
    "https://liuyan.people.com.cn/threads/localList",
]


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        for url in CANDIDATES:
            try:
                r = c.get(url)
            except Exception as e:                                          # noqa: BLE001
                print(f"[skip] {url} {type(e).__name__}")
                continue
            t = r.text or ""
            fids = sorted(set(re.findall(r"fid=(\d{2,6})", t)))
            print(f"[{r.status_code}] {url} len={len(t)} fid 命中 {len(fids)}: {fids[:20]}")
            # 省名 + fid 的成对出现（链接文本或 JS 数据里）
            pairs = re.findall(r'fid["\']?\s*[:=]\s*["\']?(\d{2,6})["\']?[^>]{0,80}?>([^<>]{2,8}(?:省|市|自治区|区))', t)
            if pairs:
                print("   省- fid 对：", pairs[:10])
            if "地方领导" in t:
                print("   （页面含「地方领导」）")
    return 0


if __name__ == "__main__":
    main()
