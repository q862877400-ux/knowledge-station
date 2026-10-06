"""用 v2 提示词生成「外行说法」，调 bunny（space-bunny-free）。

要点：
  · 提示词【从 docs/research/lay-phrasing-prompt.md 的代码块里程序化提取】，
    不手打 —— 本仓纪律：字节级搬运（手抄实测 77 行错 2 处）。
  · model 固定 space-bunny-free（业主硬要求）。
  · 必须带浏览器式 User-Agent（缺 UA 会被 403，实测踩过）。
  · 发车前先跑 1 批校验；失败即停。
  · 每批 5 个术语（约 20 条说法），避免输出被截断。
只读 md 与术语表；结果写 var/tmp。
"""
from __future__ import annotations
import json, pathlib, re, sys, time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = pathlib.Path(r"D:\AI\work space\zcode")
PROMPT_MD = REPO / "docs/research/lay-phrasing-prompt.md"
TERMS = REPO / "var/tmp/terms-new-60.txt"
OUT = REPO / "var/tmp/gen-V3.jsonl"
CRED = pathlib.Path.home() / ".dsh" / ".credentials.yaml"

URL = "https://opencode.ai/zen/v1/chat/completions"
MODEL = "space-bunny-free"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
BATCH = 5
WORKERS = 3
RETRY = 4

key = None
for ln in CRED.read_text(encoding="utf-8", errors="ignore").splitlines():
    if "OPENCODE_GO_API_KEY" in ln:
        key = ln.split(":", 1)[1].strip().strip('"').strip("'")
        break
if not key:
    sys.exit("没找到 OPENCODE_GO_API_KEY")


def extract_prompt() -> str:
    """从 md 的 ``` 代码块里取出提示词全文（整段复制，末尾接术语清单）。"""
    txt = PROMPT_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```\n(.*?)```", txt, re.S)
    for b in blocks:
        if "你是产品调研员" in b and "输入术语" in b:
            return b.rstrip() + "\n"
    sys.exit("没能在 md 里找到提示词代码块")


PROMPT = extract_prompt()


def call(terms):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT + "\n".join(terms)}],
        "max_tokens": 8000,
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8"))
    return (d["choices"][0]["message"].get("content") or "").strip(), d.get("model")


def parse(txt):
    """每行一个 JSON 对象；容错：剥掉可能的代码块标记。"""
    out = []
    for ln in txt.splitlines():
        ln = ln.strip().rstrip(",")
        if ln.startswith("```"):
            continue
        if not ln.startswith("{"):
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def one(batch):
    err = ""
    for a in range(RETRY):
        try:
            txt, model = call(batch)
            rows = parse(txt)
            if rows:
                return {"ok": True, "model": model, "rows": rows, "raw_len": len(txt)}
            err = "解析出 0 行"
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
        time.sleep(2 + a * 2)
    return {"ok": False, "err": err, "batch": batch}


def main():
    terms = [l.strip() for l in TERMS.read_text(encoding="utf-8").splitlines() if l.strip()]
    batches = [terms[i:i + BATCH] for i in range(0, len(terms), BATCH)]
    print("[1/3] 提示词从 md 提取：%d 字符；术语 %d 个 -> %d 批"
          % (len(PROMPT), len(terms), len(batches)), flush=True)

    probe = one(batches[0])
    if not probe.get("ok"):
        print("前置校验失败，不发车：", probe.get("err"), flush=True)
        sys.exit(2)
    print("[2/3] 前置校验通过：model=%s 第一批出 %d 条" % (probe.get("model"), len(probe["rows"])), flush=True)

    rest = batches[1:]
    print("[3/3] 其余 %d 批，并发 %d" % (len(rest), WORKERS), flush=True)
    results = [probe]
    with ThreadPoolExecutor(WORKERS) as ex:
        for r in ex.map(one, rest):
            results.append(r)
            print("  进度 %d/%d" % (len(results), len(batches)), flush=True)

    allterms, lines = set(terms), []
    n_ok = n_empty = 0
    for r in results:
        if not r.get("ok"):
            continue
        for row in r["rows"]:
            t = row.get("term")
            if t not in allterms:
                continue
            lay = row.get("lay") or []
            if not lay:
                n_empty += 1
            n_ok += 1
            lines.append(json.dumps(row, ensure_ascii=False))

    OUT.write_text("\n".join(lines), encoding="utf-8")
    n_lay = sum(len(json.loads(l).get("lay") or []) for l in lines)
    print("\n生成：%d 个术语有输出（其中 %d 个 lay 为空）；说法共 %d 条" % (n_ok, n_empty, n_lay))
    miss = allterms - {json.loads(l)["term"] for l in lines}
    print("没拿到的术语：", sorted(miss) or "无")
    print("结果写", OUT)


if __name__ == "__main__":
    main()
