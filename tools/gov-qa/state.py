"""水位（Watermark）—— 增量轮询的核心数据结构。

对应 spec 004 的 FR-001 ~ FR-006，数据结构见 `data-model.md` 的 E2。

## 水位三种类型（research.md R1）

政务站**没有增量 API**，只能靠「翻到已知位置为止」。不同 adapter 的「可比较位置」不同：

| 类型 | 比较语义 | 增量策略 |
|---|---|---|
| `page`  | 已采到的**最大页码** | 从第 1 页翻，**翻到「本页全部已见过」就停** |
| `since` | 已采到的**最大时间戳** | 只取时间 > 水位的条目 |
| `idset` | 已见过的 **id 集合**（LRU 有上限） | 翻全量但按 id 去重（兜底，保证不重复） |

> ⚠ `page` 型为什么不用「记录页码」而用「翻到全部已见过就停」？
> 因为**列表会因新增内容整体后移**，页码会漂 —— 记页码会漏采。
> 「翻到全部已见过」对列表位移免疫。

## 三条必须守住的规则

1. **水位只在采集成功后前移**（FR-003）—— 失败时只累加 `consecutive_failures`
2. **水位损坏安全退化**（FR-006）—— 解析失败返回「无水位」，不抛异常
3. **`idset` 必须有 LRU 上限**（默认 50,000）—— 否则 JSON 无限膨胀
"""
from __future__ import annotations

from pathlib import Path

from common import load_json, now_iso, save_json

HERE = Path(__file__).resolve().parent
STATE_DIR = HERE / "state"
WM_PATH = STATE_DIR / "watermarks.json"

#: `idset` 型水位保留的最大 id 数。超限按 LRU 淘汰。
#: 为什么要有上限：`idset` 是「翻全量 + 去重」，如果 id 全留着，JSON 会无限膨胀
#: （某源 3 万条 × 16 字符 id ≈ 1MB，几十个源就爆了）。
IDSET_MAX = 50_000

VALID_TYPES = ("page", "since", "idset")


class Watermark:
    """单通道的水位。字段见 data-model.md E2。"""

    __slots__ = ("channel_key", "type", "value", "updated_at",
                 "last_batch_count", "last_success_at", "consecutive_failures")

    def __init__(self, channel_key: str, wtype: str, value=None, *,
                 updated_at: str | None = None, last_batch_count: int = 0,
                 last_success_at: str | None = None, consecutive_failures: int = 0):
        if wtype not in VALID_TYPES:
            raise ValueError(f"未知水位类型 {wtype!r}，应为 {VALID_TYPES}")
        self.channel_key = channel_key
        self.type = wtype
        self.value = value
        self.updated_at = updated_at or now_iso()
        self.last_batch_count = last_batch_count
        self.last_success_at = last_success_at or now_iso()
        self.consecutive_failures = consecutive_failures

    # ---------------------------------------------------------- 序列化

    def to_dict(self) -> dict:
        return {
            "channel_key": self.channel_key,
            "type": self.type,
            "value": self.value,
            "updated_at": self.updated_at,
            "last_batch_count": self.last_batch_count,
            "last_success_at": self.last_success_at,
            "consecutive_failures": self.consecutive_failures,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Watermark":
        return cls(
            channel_key=str(d.get("channel_key") or ""),
            wtype=str(d.get("type") or "idset"),
            value=d.get("value"),
            updated_at=d.get("updated_at"),
            last_batch_count=int(d.get("last_batch_count") or 0),
            last_success_at=d.get("last_success_at"),
            consecutive_failures=int(d.get("consecutive_failures") or 0),
        )

    def __repr__(self) -> str:                                          # pragma: no cover
        v = self.value
        if isinstance(v, list):
            v = f"<{len(v)} ids>"
        return (f"Watermark({self.channel_key!r}, {self.type}, value={v!r}, "
                f"fails={self.consecutive_failures})")


class WatermarkStore:
    """水位存储。**整个进程只开一个**，内部维护内存副本 + 落盘。

    并发安全靠**调用方的文件锁**（`common.file_lock`）——
    本类自己不抢锁，因为一轮轮询应该只抢一次锁，而不是每条水位抢一次。
    """

    def __init__(self, path: Path | str = WM_PATH):
        self.path = Path(path)
        self._data: dict[str, Watermark] = {}
        self.broken = False          # 文件损坏标记（FR-006）
        self._load()

    def _load(self) -> None:
        raw = load_json(self.path, default=None)
        if raw is None:
            # 文件不存在 或 JSON 解析失败 —— 都视为「无水位」
            if self.path.exists():
                self.broken = True   # 存在但读不了 ⇒ 是真损坏，要告知调用方
            return
        if not isinstance(raw, dict):
            self.broken = True
            return
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            try:
                self._data[str(k)] = Watermark.from_dict(v)
            except Exception:                                           # noqa: BLE001
                # 单条坏不影响其他条 —— 局部退化而非整体失败
                continue

    def save(self) -> None:
        save_json(self.path, {k: w.to_dict() for k, w in self._data.items()})

    # ---------------------------------------------------------- 查询

    def get(self, channel_key: str) -> Watermark | None:
        return self._data.get(channel_key)

    def needs_full(self, channel_key: str) -> bool:
        """该通道是否必须全量采（无水位 / 文件损坏）。"""
        return self.broken or channel_key not in self._data

    def __contains__(self, key) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    # ---------------------------------------------------------- 更新

    def ensure(self, channel_key: str, wtype: str) -> Watermark:
        """取或建（不落盘）。"""
        w = self._data.get(channel_key)
        if w is None:
            w = Watermark(channel_key, wtype, value=None,
                          last_success_at=None, updated_at=None)
            self._data[channel_key] = w
        elif w.type != wtype:
            # 类型变了（adapter 改造）⇒ 水位作废，退回全量
            w.type = wtype
            w.value = None
        return w

    def mark_success(self, channel_key: str, *, new_value, batch_count: int) -> None:
        """**采集成功后**前移水位（FR-003）。失败路径**绝不能**调这个。"""
        w = self._data.get(channel_key)
        if w is None:
            raise KeyError(f"通道 {channel_key} 无水位记录，先 ensure()")
        w.value = self._trim(w.value, new_value)
        w.last_batch_count = batch_count
        w.last_success_at = now_iso()
        w.updated_at = now_iso()
        w.consecutive_failures = 0

    def mark_failure(self, channel_key: str) -> int:
        """采集失败：**只累加计数，不动 value**（FR-003）。返回新的失败次数。"""
        w = self._data.get(channel_key)
        if w is None:
            w = self.ensure(channel_key, "idset")
        w.consecutive_failures += 1
        return w.consecutive_failures

    def _trim(self, old, new):
        """`idset` 型做 LRU 裁剪（上限 `IDSET_MAX`）。

        取「新的在前 + 旧的补足」的顺序 ⇒ 天然近似 LRU
        （新见到的 id 优先级更高，老 id 先被淘汰）。
        """
        if not isinstance(new, list):
            return new
        if len(new) <= IDSET_MAX:
            return new
        # 去重保序，再截断
        seen, out = set(), []
        for x in new:
            if x not in seen:
                seen.add(x)
                out.append(x)
            if len(out) >= IDSET_MAX:
                break
        return out
