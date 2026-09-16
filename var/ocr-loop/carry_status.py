# -*- coding: utf-8 -*-
"""只读干跑：现在真实 state 里有多少"未到终点"的残留？（不写 state、不写台账）"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import batch_advance as B  # noqa: E402

paths, rep = B._carry_over([], dry_run=True)
print(f"残留（会被带进下一批清单重跑）：{len(rep['carried'])} 部")
for k in rep["carried"]:
    print("   ", k[:78])
print(f"\n转待人工（能力边界/无源文件/试满 {B.MAX_CARRY} 次）：{len(rep['retired'])} 部")
for k in rep["retired"]:
    print("   ", k[:78])
print(f"\n台账现有携带次数记录：{B._carry_attempts()}")
