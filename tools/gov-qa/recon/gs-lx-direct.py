import os, sys, time
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, "tools/gov-qa")
print("A: before httpx", flush=True)
import httpx
print("B: httpx ok", flush=True)
from adapters import gs_linxia
print("C: imported gs_linxia", flush=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


class F:
    def __init__(self, c):
        self._c = c

    def __call__(self, u, **k):
        return self._c.get(u, **k)

    def post(self, u, **k):
        return self._c.post(u, **k)


print("D: start client", flush=True)
t0 = time.time()
with httpx.Client(timeout=20, headers={"User-Agent": UA}, follow_redirects=True, trust_env=False) as cli:
    print("E: client ok, calling harvest", flush=True)
    rows = gs_linxia.harvest(F(cli), limit=5)
print("F: got", len(rows), round(time.time() - t0, 1), "s", flush=True)
for r in rows[:3]:
    print(r["id"], (r["question"] or "")[:40], "|", (r["answer"] or "")[:40], flush=True)
