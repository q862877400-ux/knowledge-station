# -*- coding: utf-8 -*-
"""临时诊断：效力报告骨架 vs 节点明细一致性（只读）。"""
from src.core.exports import effect_report

rep = effect_report.collect_effect_report()
print("total:", rep["total"], "colors:", rep["colors"])


def walk(nodes, path):
    for n in nodes:
        p = path + [n["name"]]
        if "count" in n:  # L4
            if n["count"] > 0:
                docs = effect_report.collect_effect_docs(
                    top=p[0], l2=p[1], l3=p[2], l4=n["name"])
                ok = "OK " if docs["count"] == n["count"] else "MISMATCH"
                if docs["count"] != n["count"]:
                    print(f"{ok} count={n['count']} docs={docs['count']} path={p}")
                else:
                    print(f"{ok} count={n['count']} first={docs['docs'][0]['standard_no'] if docs['docs'] else '-'} path={p[1:]}")
        else:
            walk(n.get("items", []), p)


for top in rep["tree"]:
    walk([top], [])
