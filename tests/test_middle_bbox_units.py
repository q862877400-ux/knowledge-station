"""spec 012 R1 判据：MinerU 4.0 的**归一化 bbox** 必须换算成**绝对点**。

## 这个缺陷是什么（2026-10-12 实测定位）

MinerU **4.0** 的 block `bbox` 是**归一化比例**（0~1），而 MinerU **3.4** 的是**绝对点**。
`middle_schema._convert_40_to_34` 原来只做**结构映射**（`pages`→`pdf_info`）、
**不做单位换算** ⇒ 比例被当点往下传。

后果（实测 `GB 1094.1-2013`）：
```
原始   [0.116, 0.138, 0.937, 0.176]        ← 比例
下游   y' = H − y 翻转（按"点"处理）
库里   [0.116, 3455.82, 0.937, 3455.86]    ← x 是比例、y 是"H 减比例"
前端   箭头只有一个点大 → 被退化框闸门拒收 → 红箭头永远不出现
```
影响面：**756 篇 / 253,222 条条款（13.7%）**，全部是 2026-10-07 MinerU 4.0 那批。

## 判据设计

**不测"代码里有没有乘页宽"**（那是实现细节，换个写法就假红），
测**行为**：喂一份 4.0 产物 ⇒ 出来的 bbox 必须是**点**（在 0~页宽/页高 内、且尺寸正常）。
"""
from __future__ import annotations

import pytest


def _mk_40(width: float = 2456.0, height: float = 3456.0,
           block_bbox=None) -> dict:
    """造一份最小的 MinerU 4.0 产物（形状照真产物）。"""
    if block_bbox is None:
        block_bbox = [0.116, 0.138, 0.937, 0.176]
    return {
        "schema": "docvortex.middle",
        "schema_version": "2.0",
        "pages": [{
            "page_idx": 0,
            "blocks": [{
                "type": "doc_title",
                "bbox": block_bbox,
                "content": [{"type": "text", "content": "电力变压器 第1部分：总则"}],
            }],
        }],
        "extensions": {
            "docvortex_layout": {
                "pages": [{"page_idx": 0, "width_pt": width, "height_pt": height}],
            },
        },
    }


class Test归一化bbox换算成点:
    """★ 核心判据：4.0 的比例 bbox ⇒ 输出必须是点。"""

    def test_比例bbox被换算成页尺寸量级(self):
        """喂 `[0.116, 0.138, 0.937, 0.176]`（比例）⇒ 出 `[285, 477, 2301, 608]`（点）。"""
        from src.core.ingestion.middle_schema import normalize_middle

        out = normalize_middle(_mk_40())
        bb = out["pdf_info"][0]["para_blocks"][0]["bbox"]
        # 0.116*2456 = 284.9 / 0.138*3456 = 476.9 / 0.937*2456 = 2301.3 / 0.176*3456 = 608.3
        assert bb[0] == pytest.approx(284.9, abs=1.0), f"x0 没乘页宽: {bb}"
        assert bb[1] == pytest.approx(476.9, abs=1.0), f"y0 没乘页高: {bb}"
        assert bb[2] == pytest.approx(2301.3, abs=1.0), f"x1 没乘页宽: {bb}"
        assert bb[3] == pytest.approx(608.3, abs=1.0), f"y1 没乘页高: {bb}"

    def test_换算后通过退化闸门(self):
        """★ 这是**用户可见的效果**：换算后箭头才画得出来（不再被当碎片丢掉）。

        引擎侧 `attach_bboxes` 与宿主侧 `/ks/bbox` 都拒收 宽<5pt 或 高<3pt 的框
        ⇒ 换算前的"0.8pt 宽"必被丢；换算后应是几百 pt。
        """
        from src.core.ingestion.middle_schema import normalize_middle

        out = normalize_middle(_mk_40())
        bb = out["pdf_info"][0]["para_blocks"][0]["bbox"]
        w, h = abs(bb[2] - bb[0]), abs(bb[3] - bb[1])
        assert w >= 5.0, f"宽 {w:.2f}pt 仍小于退化阈值 5pt ⇒ 箭头还是画不出"
        assert h >= 3.0, f"高 {h:.2f}pt 仍小于退化阈值 3pt ⇒ 箭头还是画不出"

    def test_坐标落在页尺寸内(self):
        """换算后 x 必须 ≤ 页宽、y ≤ 页高（不越界）。"""
        from src.core.ingestion.middle_schema import normalize_middle

        out = normalize_middle(_mk_40(width=600.0, height=800.0,
                                      block_bbox=[0.1, 0.2, 0.9, 0.8]))
        bb = out["pdf_info"][0]["para_blocks"][0]["bbox"]
        assert 0 <= bb[0] <= 600 and 0 <= bb[2] <= 600, f"x 越界: {bb}"
        assert 0 <= bb[1] <= 800 and 0 <= bb[3] <= 800, f"y 越界: {bb}"

    def test_页尺寸不同则换算结果不同(self):
        """防"写死 595/841"：同一比例在 600×800 与 2456×3456 上结果必须不同。"""
        from src.core.ingestion.middle_schema import normalize_middle

        a = normalize_middle(_mk_40(width=600.0, height=800.0))["pdf_info"][0]["para_blocks"][0]["bbox"]
        b = normalize_middle(_mk_40(width=2456.0, height=3456.0))["pdf_info"][0]["para_blocks"][0]["bbox"]
        assert a != b, "两种页尺寸算出同一个框 ⇒ 页尺寸没被用上（写死了默认值）"


class Test已是点的bbox不被重复缩放:
    """★ 反向判据：本来就 >1 的坐标**不许**再乘一次页宽。

    若不加这道闸，一份"已经是点"的产物会被再放大 2456 倍 ⇒
    箭头画到页外（比不画更糟）。判据用"值 >1"来区分两套单位。
    """

    def test_绝对值bbox原样保留(self):
        """喂 `[285, 477, 2301, 608]`（已经是点）⇒ 不许再乘。"""
        from src.core.ingestion.middle_schema import normalize_middle

        out = normalize_middle(_mk_40(block_bbox=[285.0, 477.0, 2301.0, 608.0]))
        bb = out["pdf_info"][0]["para_blocks"][0]["bbox"]
        assert bb == pytest.approx([285.0, 477.0, 2301.0, 608.0], abs=0.01), \
            f"已经是点的坐标被重复缩放了: {bb}"

    def test_混合值不被缩放(self):
        """只要有一个值 >1，整条**原样返回**（不猜、不部分缩）。"""
        from src.core.ingestion.middle_schema import normalize_middle

        out = normalize_middle(_mk_40(block_bbox=[0.5, 477.0, 0.9, 608.0]))
        bb = out["pdf_info"][0]["para_blocks"][0]["bbox"]
        assert bb == pytest.approx([0.5, 477.0, 0.9, 608.0], abs=0.01), \
            f"混合单位时被误缩: {bb}"

    def test_空bbox不炸(self):
        from src.core.ingestion.middle_schema import normalize_middle

        mj = _mk_40(block_bbox=[])
        out = normalize_middle(mj)
        assert out["pdf_info"][0]["para_blocks"][0]["bbox"] == []


class Test行级bbox也换算:
    """★ 行级 bbox 是**真正画箭头用的那个**（`pipeline` 优先取 line.bbox）。

    只换算块级、漏了行级 ⇒ 箭头仍画不出（行级才是 evidence 的 span）。
    """

    def test_行级bbox也乘页尺寸(self):
        from src.core.ingestion.middle_schema import normalize_middle

        out = normalize_middle(_mk_40(block_bbox=[0.1, 0.2, 0.9, 0.8]))
        line = out["pdf_info"][0]["para_blocks"][0]["lines"][0]
        bb = line["bbox"]
        assert bb[0] == pytest.approx(0.1 * 2456.0, abs=1.0), \
            f"行级 bbox 没换算（行级才是箭头真正用的）: {bb}"


class Test3_4产物行为不变:
    """★ 回归护栏：3.4 产物**原样返回**，既有行为一字不变。

    3.4 的 bbox 本来就是点 ⇒ 若本修法误伤了它，会让 6,417 篇正常文档全变坏。
    """

    def test_34产物原样返回(self):
        from src.core.ingestion.middle_schema import normalize_middle

        mj = {
            "pdf_info": [{
                "page_idx": 0,
                "page_size": [595.0, 841.0],
                "para_blocks": [{"type": "text", "bbox": [69.0, 690.89, 562.0, 723.89],
                                 "lines": []}],
                "discarded_blocks": [],
            }],
        }
        out = normalize_middle(mj)
        assert out is mj, "3.4 产物应原样返回（同一对象）"
        assert out["pdf_info"][0]["para_blocks"][0]["bbox"] == [69.0, 690.89, 562.0, 723.89], \
            "3.4 的 bbox 被改动了（它本来就是点）"
