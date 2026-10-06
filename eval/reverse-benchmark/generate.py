"""F 方案 v2：从条文反推外行问法（修了 v1 的提示词缺陷 + 生成换 Gemini）。

v1 实测：盲判通过率 21.2%，但 FAIL 里 51% 是"类型不对"。
根因是 v1 照抄了正向提示词里的一条硬要求「至少 1 条问要不要办手续/合不合规/会不会被罚」——
对【定义类】条文，这条会逼模型写出"问处罚"的问题，而条文根本没讲处罚 ⇒ 自己造出来的不匹配。

v2 修法：按条文类型分支给指令。
  · 定义类 -> 问"这是啥 / 怎么分辨 / 拿它干嘛"，明确禁止问办手续/罚款/合规
  · 要求类 -> 可以问办手续/限值/后果，明确禁止问"这是什么意思"

生成用 Google Vertex 的 gemini-3.8-flash（业主 2026-10-06：「这个模型的语言表现好得多」）。
判定仍用 bunny，保持独立（不拿生成的模型去判自己写的东西）。

只读真库；结果写 var/tmp。
"""
from __future__ import annotations
import json, pathlib, random, sys, time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = pathlib.Path(r"D:\AI\work space\zcode")
POOL = REPO / "var/tmp/clause-pool.jsonl"
CRED = pathlib.Path.home() / ".dsh" / ".credentials.yaml"
MODEL = "gemini-3.8-flash"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

N_DEF, N_REQ = 15, 15
BATCH = 3
WORKERS = 6
RETRY = 4

key = None
for ln in CRED.read_text(encoding="utf-8", errors="ignore").splitlines():
    if ln.strip().startswith("GOOGLE_CLOUD_API_KEY"):
        key = ln.split(":", 1)[1].strip().strip('"').strip("'")
        break
if not key:
    sys.exit("没找到 GOOGLE_CLOUD_API_KEY")
URL = ("https://aiplatform.googleapis.com/v1/publishers/google/models/"
       f"{MODEL}:generateContent?key={key}")

PROMPT = """你是产品调研员。下面是一批标准条文（每行一条，格式：[编号][类型] 条文正文）。

请针对每一条，写出"完全不懂这个领域的外行会怎么问同一件事"。

【最重要的一条】写出来必须是**第一人称的问句**——就像一个人真的张嘴在问。
不许下定义、不许写"这是……""指……""用来……的东西"。

**类型决定问什么，这一步最容易错：**

· 标注 **[定义]** 的（"X 是……"），外行会问**"这是啥 / 怎么分辨出来 / 拿它干嘛 / 它跟另一种有啥区别"**。
  🔴 **绝对不许**问办手续、要不要审批、违规会不会被罚 —— 定义条文里没有这些内容。

· 标注 **[要求]** 的（"应…… / 不应超过…… / 不得……"），外行会问
  **"我要不要办手续 / 我这个数超了没有 / 不这么做会怎样 / 检查时看什么"**。
  🔴 **绝对不许**问"这是什么意思" —— 要求条文不是给你解释词的。

**其余硬规矩（违反就作废）：**
1. **不许出现该条文里连续 4 个及以上的字**（防抄原文）。
2. 每条不超过 30 个字。
3. 必须从**目的、场景或现象**出发，不是复述条文的措辞。
4. 每条条文写 **3 条**，标出说这话的人是谁（consumer / worker / owner 三选一）：
   - 至少 1 条只描述一个具体场景；
   - 至少 1 条带具体数字或具体物件。
5. **如果这条条文外行一辈子不会问**（纯编号、纯表格、纯附录、纯引用别的文件），
   把 lay 写成空数组 []，并在 why_empty 里一句话说明。**这不算失败，是有用的信息。**
6. 不要解释条文是什么意思，不要给答案。

输出格式：每行一个 JSON 对象，不要任何别的文字，不要 Markdown 代码块标记：
{"no":"<条文编号>","lay":[{"text":"说法","register":"consumer"},...],"why_empty":"（只有 lay 为空时才有）"}

条文：
"""


def call(batch):
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": PROMPT + "\n".join(batch)}]}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 1.0},
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read().decode("utf-8"))
    cand = d.get("candidates", [{}])[0]
    txt = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    return txt.strip(), cand.get("finishReason")


def parse(txt):
    out = []
    for ln in txt.splitlines():
        ln = ln.strip().rstrip(",")
        if ln.startswith("```") or not ln.startswith("{"):
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
            txt, fin = call(batch)
            rows = parse(txt)
            if rows:
                return {"ok": True, "rows": rows, "fin": fin}
            err = "解析出 0 行 (finish=%s)" % fin
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
        time.sleep(2 + a * 3)
    return {"ok": False, "err": err, "batch": batch}


def overlap(a, b):
    best = 0
    for i in range(len(a)):
        for j in range(i + best + 1, len(a) + 1):
            if a[i:j] in b:
                best = j - i
            else:
                break
    return best


def main():
    pool = [json.loads(l) for l in POOL.read_text(encoding="utf-8").splitlines() if l.strip()]
    defs = [p for p in pool if p["kind"] == "定义"]
    reqs = [p for p in pool if p["kind"] == "要求"]
    # 换种子，取【新的一批】条文（与 v1 不重复）
    random.seed(20261010)
    sel = random.sample(defs, N_DEF) + random.sample(reqs, N_REQ)
    print(f"[1/3] 抽 {len(sel)} 条（定义 {N_DEF} + 要求 {N_REQ}）；模型 {MODEL}", flush=True)

    def fmt(s):
        return f"[{s['no']}][{s['kind']}] {s['text'][:220]}"

    batches = [sel[i:i + BATCH] for i in range(0, len(sel), BATCH)]
    probe = one([fmt(s) for s in batches[0]])
    if not probe.get("ok"):
        print("前置校验失败：", probe.get("err"), flush=True); sys.exit(2)
    print(f"[2/3] 前置校验通过：第一批出 {len(probe['rows'])} 条（finish={probe.get('fin')}）", flush=True)

    results = [probe]
    with ThreadPoolExecutor(WORKERS) as ex:
        for r in ex.map(lambda b: one([fmt(s) for s in b]), batches[1:]):
            results.append(r)
    ok_batches = sum(1 for r in results if r.get("ok"))
    print(f"[3/3] 跑完 {len(results)} 批，成功 {ok_batches}", flush=True)

    byno = {}
    for r in results:
        if not r.get("ok"):
            continue
        for row in r["rows"]:
            byno.setdefault(str(row.get("no", "")).strip(), []).extend(row.get("lay") or [])

    out, bad = [], 0
    for s in sel:
        lays = byno.get(str(s["no"]).strip(), [])
        good = []
        for x in lays:
            t = (x.get("text") or "").strip()
            if not t:
                continue
            ov = overlap(t, s["text"])
            if ov >= 4:
                bad += 1
                continue
            good.append({"text": t, "register": x.get("register"), "ov": ov})
        out.append({**s, "lays": good, "n_raw": len(lays)})

    OUT = REPO / "var/tmp/reverse-gen-v2.jsonl"
    OUT.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out), encoding="utf-8")

    got = sum(1 for x in out if x["lays"])
    tot = sum(len(x["lays"]) for x in out)
    print(f"\n生成：{got}/{len(out)} 条条文拿到问法；问法 {tot} 条；机械过滤剔掉 {bad} 条")
    print(f"重叠分布：", {k: sum(1 for x in out for y in x['lays'] if y['ov'] == k) for k in range(4)})
    print(f"没拿到的：", [x["no"] for x in out if not x["lays"]])
    print(f"结果写 {OUT}")
    print("\n=== 抽 8 条看（条文 → 问法）===")
    k = 0
    for x in out:
        if not x["lays"]:
            continue
        print(f"  [{x['kind']}] {x['no']} {x['text'][:66]}")
        for y in x["lays"][:2]:
            print(f"        -> ({y['register']}, 重合{y['ov']}) {y['text']}")
        k += 1
        if k >= 8:
            break


if __name__ == "__main__":
    main()
