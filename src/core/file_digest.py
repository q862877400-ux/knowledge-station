"""文件级 SHA-256 指纹（唯一实现）。

## 为什么有这个文件（2026-10-23 统一化第二批）

同一段「64KB 分块算 SHA-256」原来在**两个文件里逐字存在**：

- `storage/backup.py::_checksum`（备份快照完整性）
- `update/data_package.py::_file_sha256`（数据包完整性）

`data_package.py` 那处的 docstring 自己写着「与 `backup._checksum` 同一口径：64KB 分块」
—— 作者知道有两份、选择了写注释而不是复用。统一化尺子的指标 ⑤（跨文件同函数体
α-等价）把它抓成一组 2 处。

## 为什么必须统一（不是风格问题）

这两个指纹**会被互相比较**：备份快照与数据包如果分块口径不同，同一个文件算出来的
**指纹就不一样** ⇒ 「数据包里的库和备份里的库是不是同一份」这个判断会给出错误答案。
注释说"同一口径"不能防止将来有人只改一处。

## 分块大小

`64 KiB`（65536）。这是原两处一致的取值，**不要改** —— 改了会让所有历史指纹失效，
而历史指纹存在数据库和快照文件名里。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

#: 读文件的分块大小。**历史指纹依赖这个值，改它等于让旧指纹全部对不上。**
CHUNK_SIZE = 65536


def file_sha256(path: str | Path) -> str:
    """算文件的 SHA-256 十六进制指纹（小写）。

    按 `CHUNK_SIZE` 分块读，**不把整个文件读进内存** —— 生产库单文件 2.90 GB，
    整读会直接把进程撑爆。

    Args:
        path: 目标文件路径（`str` 或 `Path`）。

    Returns:
        64 位小写十六进制字符串。

    Raises:
        FileNotFoundError: 文件不存在。
        PermissionError: 无读权限。
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()
