"""内容分类器 v2 —— 服务 GOAL.md 的 M3（把内容的标签分好）。

## 为什么有 v2

v1 是**手工关键词规则**，在已标注的 115,478 条上实测**准确率仅 47.1%**。
混淆矩阵暴露根因：**建议 ↔ 咨询 严重重叠**（建议→咨询 误判 12,508 条）——
这两个类在关键词层面没有区分度，靠人写规则写不出来。

v2 改成**从已标注数据里学判别特征**：字符 n-gram TF-IDF + 线性分类器，
用**训练/测试切分**给出诚实准确率（不是自评）。

## 数据情况（2026-10-10）

- 全库 352,813 条，其中 125,228 条有原始标签
- 原始标签 **60 种，且是脏的** —— 混了三类：
  | 类别 | 例子 | 处置 |
  |---|---|---|
  | **真类型** | 咨询 / 建议 / 投诉 / 求助 / 举报 / 表扬 / 申诉 | 归一化后**当训练标签** |
  | **话题** | 省直公积金 7,807、重点行业 76、安全隐患 36 | 不是类型 ⇒ 走模型预测 |
  | **部门** | 办公室 370、社考处 146、自考处 23 | 不是类型 ⇒ 走模型预测 |
- 可归一的真值样本：**115,478 条**

## 用法

```bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe

$P tools/gov-qa/recon/label-classify.py --validate            # 训练/测试切分，报准确率
$P tools/gov-qa/recon/label-classify.py --validate --verbose  # 附分类报告 + top 判别词
$P tools/gov-qa/recon/label-classify.py --apply --dry-run     # 看会改多少条
$P tools/gov-qa/recon/label-classify.py --apply               # 写入（先 git commit！）
```

**写入 `extra.msg_type_norm` + `extra.msg_type_source`，不覆盖原始 `extra.msg_type`** ——
原始值保留，便于回溯与再训练。
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"

TYPES = ("咨询", "建议", "投诉", "举报", "求助", "表扬", "申诉", "反馈问题", "其他")

#: 原始标签 → 规范类型。None = 「不是类型」（话题/部门/栏目），须走模型预测。
NORMALIZE: dict[str, str | None] = {
    "咨询": "咨询", "咨询类": "咨询", "业务咨询": "咨询",
    "民生知识热门问答": "咨询", "企业知识热门问答": "咨询",
    "建议": "建议", "意见建议类": "建议", "意见建议": "建议", "意见": "建议",
    "投诉": "投诉", "普通投诉": "投诉", "监督投诉": "投诉",
    "举报": "举报", "投诉举报": "举报", "揭发控告类": "举报",
    "求助": "求助", "求助类": "求助", "寻求帮助": "求助", "求决": "求助",
    "表扬": "表扬", "表扬类": "表扬", "申诉": "申诉", "申诉类": "申诉",
    "其他": "其他", "其它": "其他",
    # —— 以下不是类型 ⇒ None ——
    "省直公积金": None, "重点行业": None, "安全隐患": None, "政策法规": None,
    "形式主义": None, "一刀切": None, "空壳僵尸": None, "就业创业": None,
    "拥军优抚": None, "办公室": None, "社考处": None, "自考处": None,
    "领导信箱": None, "局长信箱": None, "我要留言": None, "普通留言": None,
}

TYPE_KEYS = ("msg_type", "type", "objective_type", "rqstType", "type_dictText", "letterType")


def normalize_label(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if s in NORMALIZE:
        return NORMALIZE[s]
    for k, v in NORMALIZE.items():
        if k and k in s:
            return v
    return None


def raw_label(rec: dict) -> str | None:
    ex = rec.get("extra") or {}
    if not isinstance(ex, dict):
        return None
    for k in TYPE_KEYS:
        v = ex.get(k)
        if v not in (None, "", [], {}):
            return str(v).strip()
    return None


def read_all():
    for p in glob.glob(str(DATA / "*.jsonl")):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or not line.lstrip().startswith("{"):
                    continue
                try:
                    yield p, json.loads(line)
                except Exception:                                       # noqa: BLE001
                    continue


def doc_text(rec: dict) -> str:
    """只用 question —— answer 是政府生成的，对「提问类型」信号弱且会引噪声。"""
    return (rec.get("question") or "").replace("\n", " ").strip()[:2000]


def build_model(use_word: bool = True):
    """返回 (vectorizer, clf, X_texts, y) —— 用全部已标注数据训练。

    `use_word=True` 时把**字符 n-gram**（2-4）与 **jieba 词 n-gram**（1-2）做 FeatureUnion。
    单用字符 n-gram 实测 78.5%；加词特征通常能再涨几个点。
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion
    from sklearn.svm import LinearSVC

    texts, labels = [], []
    for _p, r in read_all():
        g = normalize_label(raw_label(r))
        if not g:
            continue
        t = doc_text(r)
        if len(t) < 4:
            continue
        texts.append(t)
        labels.append(g)

    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3,
                               max_features=300_000, sublinear_tf=True)
    if use_word:
        import jieba
        import logging
        jieba.setLogLevel(logging.WARNING)

        def _cut(s: str):
            return [w for w in jieba.cut(s) if len(w.strip()) > 1]

        word_vec = TfidfVectorizer(analyzer="word", tokenizer=_cut, preprocessor=None,
                                   token_pattern=None, ngram_range=(1, 2), min_df=3,
                                   max_features=200_000, sublinear_tf=True)
        vec = FeatureUnion([("char", char_vec), ("word", word_vec)])
    else:
        vec = char_vec
    clf = LinearSVC(C=1.0, class_weight="balanced", max_iter=5000)
    return vec, clf, texts, labels


def do_validate(verbose: bool) -> int:
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline

    vec, clf, texts, labels = build_model()
    if not texts:
        print("无可用标注样本")
        return 1
    Xtr, Xte, ytr, yte = train_test_split(texts, labels, test_size=0.2,
                                          random_state=42, stratify=labels)
    pipe = make_pipeline(vec, clf)
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    acc = accuracy_score(yte, pred)

    print(f"标注样本 {len(texts):,} 条（训练 {len(Xtr):,} / 测试 {len(Xte):,}）")
    print(f"**准确率（held-out 测试集）：{acc * 100:.1f}%**\n")
    print(classification_report(yte, pred, digits=3, zero_division=0))

    if verbose:
        # 每类 top 判别词（系数最大的字符 n-gram）
        try:
            v = pipe.named_steps["tfidfvectorizer"]
            c = pipe.named_steps["linearsvc"]
            names = v.get_feature_names_out()
            print("=== 每类 top15 判别字符片段 ===")
            for i, cls in enumerate(c.classes_):
                idx = c.coef_[i].argsort()[-15:][::-1]
                print(f"  {cls:6s} " + " ".join(names[j] for j in idx))
        except Exception as e:                                          # noqa: BLE001
            print(f"（判别词提取失败：{e}）")
    return 0


def do_apply(dry_run: bool, force: bool = False) -> int:
    import numpy as np
    from sklearn.pipeline import make_pipeline

    vec, clf, texts, labels = build_model()
    pipe = make_pipeline(vec, clf)
    pipe.fit(texts, labels)
    print(f"模型已用 {len(texts):,} 条标注样本训练")

    changed = 0
    skipped = 0
    by_type: Counter = Counter()
    by_source: Counter = Counter()

    for p in sorted(glob.glob(str(DATA / "*.jsonl"))):
        lines_out = []
        touched = False
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or not line.lstrip().startswith("{"):
                    lines_out.append(line)
                    continue
                try:
                    r = json.loads(line)
                except Exception:                                       # noqa: BLE001
                    lines_out.append(line)
                    continue
                ex = r.get("extra")
                if not isinstance(ex, dict):
                    ex = {}
                    r["extra"] = ex
                # ★ 增量：已经有 msg_type_norm 的直接跳过，**不跑模型预测**。
                #   采集在持续产生新数据 ⇒ 标签要反复重跑；不这样优化的话每次都要
                #   对全库 35 万条重新预测（2-3 分钟），而实际新增可能只有几百条。
                if ex.get("msg_type_norm") and not force:
                    skipped += 1
                    lines_out.append(line)
                    continue
                norm = normalize_label(raw_label(r))
                src = "source_label"
                if not norm:
                    t = doc_text(r)
                    if len(t) < 4:
                        norm, src = "其他", "too_short"
                    else:
                        norm, src = str(pipe.predict([t])[0]), "model"
                ex["msg_type_norm"] = norm
                ex["msg_type_source"] = src
                changed += 1
                by_type[norm] += 1
                by_source[src] += 1
                touched = True
                lines_out.append(json.dumps(r, ensure_ascii=False) + "\n")
        if touched and not dry_run:
            with open(p, "w", encoding="utf-8") as fh:
                fh.writelines(lines_out)

    print(f"{'[DRY-RUN] ' if dry_run else ''}写入 {changed:,} 条（跳过已最新 {skipped:,}）")
    print("\n=== 规范类型分布 ===")
    for k, v in by_type.most_common():
        print(f"  {k:8s} {v:8,d}")
    print("\n=== 标签来源 ===")
    for k, v in by_source.most_common():
        print(f"  {k:14s} {v:8,d}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="内容分类器 v2（M3）")
    ap.add_argument("--validate", action="store_true", help="训练/测试切分，报准确率")
    ap.add_argument("--verbose", action="store_true", help="附分类报告 + 判别词")
    ap.add_argument("--apply", action="store_true", help="写入 msg_type_norm")
    ap.add_argument("--dry-run", action="store_true", help="配合 --apply：只统计不改文件")
    ap.add_argument("--force", action="store_true",
                    help="配合 --apply：重算**全部**记录（默认只补未标注的，增量很快）")
    args = ap.parse_args()

    if args.validate:
        return do_validate(args.verbose)
    if args.apply:
        return do_apply(args.dry_run, args.force)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
