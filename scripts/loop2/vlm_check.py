# -*- coding: utf-8 -*-
"""VLM candidate-difference checker (loop2 step 3, design §B).

The VLM is a LOW-STAKES AUXILIARY detector, never a pass/fail gate (the deterministic
oracle is the only gate). It produces a structured candidate list of visual deltas
(missing figure/table, formula shape, superscript/subscript, symbol corruption,
two-column mis-layout) for a given (orig, prev) image pair.

Fixes the historical single-image bug: ``_dl_vision.py`` sent only ``orig`` to the
vision model while claiming a two-image comparison. This module ALWAYS sends BOTH
``orig`` and ``prev`` (base64) plus a fixed prompt, parses structured JSON, retries
on transient errors, and records every cloud call through ``egress_audit``.

Note: a "no differences" VLM verdict can NEVER mark a book as passed; it only means
"no candidate visual delta reported" (the oracle still decides).

CLI:
  python scripts/loop2/vlm_check.py --orig <png> --prev <png> [--out <dir>] [--json]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # noqa: E402
    sys.path.insert(0, str(REPO))

from src.core.llm.egress_audit import record_egress  # noqa: E402

MODEL = os.environ.get("LOOP2_VLM_MODEL", "moonshot-v1-8k-vision-preview")
ENDPOINT = os.environ.get("LOOP2_VLM_ENDPOINT", "https://api.moonshot.cn/v1/chat/completions")
RETRIES = int(os.environ.get("LOOP2_VLM_RETRIES", "2"))
TIMEOUT = int(os.environ.get("LOOP2_VLM_TIMEOUT", "90"))

PROMPT = (
    "你是版面差异审查助手。对比两张图：LEFT=原始PDF页面转图；RIGHT=右侧文本重建预览。"
    "找出重建预览相对原图丢失或错位的内容，重点：图/表格/公式缺失或错位、公式形态、"
    "上下标（如 Ĉ/C̄/±/下标）、符号丢失、错行、双栏布局破坏。"
    "输出严格 JSON："
    '{"differences":[{"type":"missing|wrong|layout","what":"简述","severity":"high|mid|low"}],'
    '"summary":"一句话结论"}。若无差异，differences 为空数组且 summary 为 "ok"。'
)


def get_key() -> str:
    """MOONSHOT_API_KEY from HKCU\\Environment then env (never printed)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, "MOONSHOT_API_KEY")
            if val:
                return str(val)
    except Exception:
        pass
    return os.environ.get("MOONSHOT_API_KEY", "")


def _b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _moonshot_call(payload: dict, key: str, endpoint: str = ENDPOINT,
                   timeout: int = TIMEOUT) -> str:
    """Call the vision model and return the message content text. Raises on failure."""
    import urllib.request
    req = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"]


def _parse_json(content: str) -> dict:
    """Parse VLM JSON content, tolerating code fences / leading prose."""
    s = content or ""
    s = re.sub(r"```(?:json)?", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {"differences": [], "summary": "parse-error", "raw": content[:500]}


def build_payload(orig: Path, prev: Path) -> dict:
    """Both images (the fix) + fixed prompt. Returns JSON-serializable payload."""
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _b64(orig)}},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _b64(prev)}},
            {"type": "text", "text": PROMPT},
        ]}],
        "temperature": 0.0,
        "max_tokens": 800,
    }


def vision_check(orig: Path, prev: Path, key: str | None = None,
                 call=_moonshot_call, egress=True) -> dict:
    """Return structured candidate-difference hints for an (orig, prev) pair.

    `call` is injectable for testing. Never used as a pass/fail gate.
    """
    key = key if key is not None else get_key()
    if not key:
        return {"ok": False, "error": "no MOONSHOT_API_KEY", "hints": []}
    payload = build_payload(orig, prev)
    content = None
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            content = call(payload, key, ENDPOINT, TIMEOUT)
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < RETRIES:
                time.sleep(min(2.0 * (attempt + 1), 6.0))
    if content is None:
        return {"ok": False, "error": str(last_err), "hints": []}
    parsed = _parse_json(content)
    dump_id = None
    if egress:
        try:
            dump_id = record_egress(
                "vlm_check", ENDPOINT, payload,
                response_meta={"model": MODEL},
                query="", prompt_preview=PROMPT)
        except Exception:  # noqa: BLE001 - audit must not break the check
            dump_id = None
    return {"ok": True, "model": MODEL, "dump_id": dump_id,
            "hints": parsed.get("differences", []),
            "summary": parsed.get("summary", ""),
            "parse_fallback": parsed.get("raw") is not None}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--orig", required=True)
    ap.add_argument("--prev", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true", dest="as_json")
    a = ap.parse_args()
    res = vision_check(Path(a.orig), Path(a.prev))
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "vlm_hints.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2 if a.as_json else None))


if __name__ == "__main__":
    main()
