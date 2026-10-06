"""批量调 bunny 判定 150 条候选：每条独立跑 3 次，收结论。

要点：
  · model 固定 space-bunny-free（业主硬要求：全部用 bunny）
  · 3 次独立调用，不共享上下文 => 才算三路
  · 必须带浏览器式 User-Agent：实测缺 UA 会被 403（上一批 360 次全废的根因）
  · 控制并发 + 失败重试；发车前先跑第 1 条校验，失败即停（不再盲跑整批）
只读 var/tmp 与凭据；结果写 var/tmp。
"""
from __future__ import annotations
import json, pathlib, re, sys, time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = pathlib.Path(r"D:\AI\work space\zcode")
PAIRS = REPO / "var/tmp/pairs-batch.jsonl"
OUT = REPO / "var/tmp/bunny-verdicts.jsonl"
CRED = pathlib.Path.home() / ".dsh" / ".credentials.yaml"

URL = "https://opencode.ai/zen/v1/chat/completions"
MODEL = "space-bunny-free"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
N_PER_ITEM = 3
WORKERS = 4
RETRY = 4
TARGET = 150

key = None
for ln in CRED.read_text(encoding="utf-8", errors="ignore").splitlines():
    if "OPENCODE_GO_API_KEY" in ln:
        key = ln.split(":", 1)[1].strip().strip('"').strip("'")
        break
if not key:
    sys.exit("没找到 OPENCODE_GO_API_KEY")

PROMPT = """你是一个独立判定员。下面给全了你需要的一切。不要去读任何文件、仓库或数据库，不要上网。

# 背景
我们在给一个"用大白话查资料"的系统做考卷：拿一句外行人的问法，配上一条条文，问系统能不能找到那条条文。你的任务：判这一对配得对不对。

# 要判的这一条

## 用户的问法（原话）
{q}

## 系统给的条文（原文）
- 出处：{std}
- 条款号：{no}
- 条文原文：
> {text}

# 怎么判（按顺序做完，再出结论）
第一问：这句问法在问哪一类东西？（A 术语定义 / B 数值要求 / C 试验方法 / D 判定后果 / E 说不清）
第二问：我给的那条条文属于哪一类？（用同一套字母）
第三问：类型对得上吗？（对 / 不对）
第四问：就算类型对得上，两件事指的是同一个对象吗？（材料、场景、主管部门一致吗）

# 输出格式（严格照这个回，别加别的）
第一问：
第二问：
第三问：
第四问：
结论：PASS 或 FAIL
主因：类型不对 / 对象不对 / 两者都不对 / 都对
理由（一句话）：
我有多大把握：高 / 中 / 低

# 四条纪律
1. 不要猜。看不出来就写"看不出来"，不要编。
2. 不要读仓库、不要查数据库、不要上网。
3. 不要去判"库里有没有更对的那条"——你看不到库，判不了。只判我给的那条对不对。
4. 只回答问题本身，不要提改进建议。"""


def call(q, std, no, text):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT.format(q=q, std=std, no=no, text=text)}],
        "max_tokens": 4000,
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    m = d["choices"][0]["message"]
    return {"content": (m.get("content") or "").strip(),
            "finish": d["choices"][0].get("finish_reason"),
            "model": d.get("model")}


def verdict(txt):
    def grab(k):
        m = re.search(k + r"\s*[:：]\s*(.+)", txt)
        return m.group(1).strip() if m else ""
    return {"结论": grab("结论"), "主因": grab("主因"),
            "第一问": grab("第一问"), "第二问": grab("第二问"),
            "第三问": grab("第三问"), "把握": grab("我有多大把握")}


def one(item, k):
    err = ""
    for a in range(RETRY):
        try:
            r = call(item["q"], item["std"], item["no"], item["text"])
            if r["content"]:
                return {"ok": True, "try": a + 1, "raw": r["content"],
                        "model": r["model"], **verdict(r["content"])}
            err = "空 content (finish=%s)" % r["finish"]
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
        time.sleep(1.5 + a * 2)
    return {"ok": False, "err": err}


def main():
    sel = [json.loads(l) for l in PAIRS.read_text(encoding="utf-8").splitlines() if l.strip()]
    sel = sel[:TARGET]
    print("[1/3] 批文件 %d 条，取 %d" % (len(sel), len(sel)), flush=True)

    probe = one(sel[0], 0)
    if not probe.get("ok"):
        print("前置校验失败，整批不发车：%s" % probe.get("err"), flush=True)
        sys.exit(2)
    print("[2/3] 前置校验通过：model=%s 结论=%s 主因=%s"
          % (probe.get("model"), probe.get("结论"), probe.get("主因")), flush=True)

    jobs = [(i, it, k) for i, it in enumerate(sel, 1) for k in range(N_PER_ITEM)]
    jobs = [j for j in jobs if not (j[0] == 1 and j[2] == 0)]
    total = len(jobs) + 1
    print("[3/3] 共 %d 次调用，并发 %d" % (total, WORKERS), flush=True)

    results = {1: [probe]}
    done = [1]
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(one, it, k): (i, k) for i, it, k in jobs}
        for f in futs:
            i, k = futs[f]
            results.setdefault(i, []).append(f.result())
            done[0] += 1
            if done[0] % 30 == 0:
                nok = sum(1 for rs in results.values() for r in rs if r.get("ok"))
                print("  进度 %d/%d  成功 %d" % (done[0], total, nok), flush=True)

    lines = []
    for i, it in enumerate(sel, 1):
        rs = results.get(i, [])
        vs = [r for r in rs if r.get("ok")]
        concl = [r["结论"] for r in vs if r["结论"]]
        agree = len(set(concl)) == 1 if concl else False
        lines.append(json.dumps({
            "i": i, "q": it["q"], "term": it["term"], "ask": it["ask"],
            "std": it["std"], "no": it["no"], "text": it["text"],
            "n_ok": len(vs), "n_total": len(rs),
            "concl": concl, "agree": agree, "detail": rs,
        }, ensure_ascii=False))
    OUT.write_text("\n".join(lines), encoding="utf-8")

    rows = [json.loads(l) for l in lines]
    print("\n完成：%d 条；至少回 1 路 %d；3 路全回 %d；三路一致 %d"
          % (len(rows),
             sum(1 for r in rows if r["n_ok"] > 0),
             sum(1 for r in rows if r["n_ok"] == 3),
             sum(1 for r in rows if r["agree"])))
    print("结果写 %s" % OUT)


if __name__ == "__main__":
    main()
