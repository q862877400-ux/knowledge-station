"""对 F 方案（反推）的问法做【盲判】：判这一对配得对不对。

关键：文档与正向判定【完全一样】，不透露"这是从条文反推来的"。
否则模型会顺着"既然是反推的，那肯定配得上"去答。

复用 bunny-batch-v2.py 的 call/one/verdict。结果写 var/tmp/reverse-verdicts.jsonl。
"""
from __future__ import annotations
import json, pathlib, sqlite3, sys, threading, collections
import importlib.util
from concurrent.futures import ThreadPoolExecutor

REPO = pathlib.Path(r"D:\AI\work space\zcode")
DB = r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db"
spec = importlib.util.spec_from_file_location("bb2", REPO / "var/tmp/bunny-batch-v2.py")
bb = importlib.util.module_from_spec(spec)
sys.modules["bb2"] = bb
spec.loader.exec_module(bb)

SRC = REPO / "var/tmp/reverse-gen.jsonl"
OUT = REPO / "var/tmp/reverse-verdicts.jsonl"
WORKERS = 12
N = 3
_lock = threading.Lock()


def main():
    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    items = []
    for r in rows:
        got = conn.execute("""
            SELECT d.standard_no, d.standard_name FROM clause_revision c
            JOIN doc_meta d ON d.doc_id=c.doc_id WHERE c.clause_revision_id=?""", (r["cid"],)).fetchone()
        std, sname = (got or ("", ""))
        for y in r["lays"]:
            items.append({"q": y["text"], "std": std or "", "std_name": sname or "",
                          "no": r["no"], "text": r["text"][:300], "kind": r["kind"],
                          "register": y.get("register"), "ov": y.get("ov")})
    for i, it in enumerate(items, 1):
        it["i"] = i
    print(f"待盲判 {len(items)} 对 × {N} 路 = {len(items)*N} 次调用，并发 {WORKERS}", flush=True)

    probe = bb.one(items[0], 0)
    if not probe.get("ok"):
        print("前置校验失败：", probe.get("err")); sys.exit(2)
    print(f"前置校验通过：{probe.get('model')} 结论={probe.get('结论')} 主因={probe.get('主因')}", flush=True)

    jobs = [(it, k) for it in items for k in range(N)]
    jobs = [j for j in jobs if not (j[0]["i"] == 1 and j[1] == 0)]
    buf = {1: [probe]}

    def rec(i):
        rs = buf.pop(i)
        it = items[i - 1]
        vs = [r for r in rs if r.get("ok")]
        concl = [r["结论"] for r in vs if r["结论"]]
        line = json.dumps({**it, "n_ok": len(vs), "concl": concl,
                           "agree": (len(set(concl)) == 1) if concl else False,
                           "detail": vs}, ensure_ascii=False)
        with _lock:
            with OUT.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(bb.one, it, k): it["i"] for it, k in jobs}
        for f in futs:
            i = futs[f]
            buf.setdefault(i, []).append(f.result())
            if len(buf[i]) == N:
                rec(i)

    got = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()]
    def maj(r):
        c = collections.Counter(x for x in r["concl"] if x)
        return c.most_common(1)[0][0] if c else None
    ps = sum(1 for r in got if maj(r) == "PASS")
    print(f"\n★ 反推问法的盲判通过率：{ps}/{len(got)} = {ps/max(1,len(got))*100:.1f}%")
    print("按条文类型:", {k: f"{sum(1 for r in got if r['kind']==k and maj(r)=='PASS')}/{sum(1 for r in got if r['kind']==k)}"
                        for k in set(r["kind"] for r in got)})
    print("FAIL 主因:", dict(collections.Counter(
        collections.Counter(d.get("主因", "") for d in r["detail"] if d.get("ok") and d.get("主因")).most_common(1)[0][0]
        for r in got if maj(r) == "FAIL")))
    print("按重叠长度:", {k: f"{sum(1 for r in got if r['ov']==k and maj(r)=='PASS')}/{sum(1 for r in got if r['ov']==k)}"
                        for k in sorted(set(r["ov"] for r in got))})
    print("\n=== 判 FAIL 的样本（看差在哪）===")
    for r in [x for x in got if maj(x) == "FAIL"][:5]:
        print(f"  问：{r['q']}")
        print(f"     条文：{r['std']} {r['no']} {r['text'][:70]}")
        print(f"     主因：{[d.get('主因') for d in r['detail'] if d.get('ok')]}")


if __name__ == "__main__":
    main()
