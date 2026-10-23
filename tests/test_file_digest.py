"""`src/core/file_digest.py` 的判据（2026-10-23 统一化第二批）。

## 为什么单独测它

同一个「64KB 分块算 SHA-256」原来在**两处逐字存在**：
`storage/backup.py::_checksum` 与 `update/data_package.py::_file_sha256`。
`data_package.py` 的 docstring 自己写着「与 `backup._checksum` 同一口径」——
**注释不能防止将来有人只改一处**。

这两个指纹**会被互相比较**（"数据包里的库和备份里的库是不是同一份"），
一旦口径分叉，那个判断会给出错误答案。

## 判据分三组

1. **已知值**：对固定内容算出的指纹必须等于标准值（防算法被改）；
2. **分块边界**：0 / 恰好 64K / 64K+1 都要对（分块实现最容易在这里错）；
3. **两个调用点确实共用同一实现**（这条防「又写回去一份」）。
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.file_digest import CHUNK_SIZE, file_sha256  # noqa: E402


def test_empty_file_digest():
    """空文件的 SHA-256 是标准常量 —— 算错说明初始化/循环写错了。"""
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        p = Path(f.name)
    try:
        assert file_sha256(p) == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    finally:
        p.unlink(missing_ok=True)


def test_known_content_digest():
    """`b"abc"` 的 SHA-256 是公开标准值。"""
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"abc")
        p = Path(f.name)
    try:
        assert file_sha256(p) == (
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    finally:
        p.unlink(missing_ok=True)


@pytest.mark.parametrize("size", [0, 1, CHUNK_SIZE - 1, CHUNK_SIZE,
                                  CHUNK_SIZE + 1, CHUNK_SIZE * 3 + 7])
def test_chunk_boundaries_match_whole_file_hash(tmp_path, size):
    """跨分块边界时，分块算法必须与「一次读全」得到同一个指纹。

    ⚠ 这是分块实现最容易错的地方：边界少读/多读 1 字节，指纹就变了，
    而小文件测试**照样通过**。
    """
    data = bytes((i * 37 + 11) % 256 for i in range(size))
    p = tmp_path / f"f{size}.bin"
    p.write_bytes(data)
    assert file_sha256(p) == hashlib.sha256(data).hexdigest()


def test_two_call_sites_share_one_implementation():
    """两个历史调用点必须**指向同一个函数对象**（防有人又各写一份）。

    `backup._checksum` 与 `data_package._file_sha256` 都是 `file_sha256` 的别名，
    所以 `is` 判等应当成立。若将来有人把某一处改回本地 `def`，这条会红。
    """
    from src.core.storage import backup
    from src.core.update import data_package

    assert backup._checksum is file_sha256, "backup._checksum 不是公共实现"
    assert data_package._file_sha256 is file_sha256, "data_package._file_sha256 不是公共实现"


def test_chunk_size_is_frozen():
    """分块大小是**历史指纹的契约**，不许改。

    历史备份快照与数据包的指纹存在数据库和文件名里；改 CHUNK_SIZE 会让
    「同一文件的新旧指纹」不再相等，那些历史记录就永久对不上了。
    """
    assert CHUNK_SIZE == 65536, "CHUNK_SIZE 改了会让所有历史指纹失效"
