"""C1 资产端点：parse_out 图片回源 + 防穿越白名单（2026-09-01 排版还原）。"""
import hashlib


DOC = "doc_0123456789ABCDEFGHJKMNPQRS"


def _mk_asset(doc_id: str, content: bytes = b"\xff\xd8fakejpg") -> str:
    from src.core.config import get_settings
    h = hashlib.sha256(content).hexdigest()
    d = (get_settings().data_dir / "parse_out" / doc_id
         / "mineru" / "auto" / "images")
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{h}.jpg").write_bytes(content)
    return f"{h}.jpg"


def test_asset_served(client):
    c, token = client
    name = _mk_asset(DOC)
    r = c.get(f"/api/v1/documents/{DOC}/assets/{name}",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/jpeg")
    assert r.content.startswith(b"\xff\xd8")


def test_asset_traversal_and_whitelist_rejected(client):
    c, token = client
    hdr = {"Authorization": f"Bearer {token}"}
    for bad in ["../secret.jpg", "A" * 64 + ".jpg", "0" * 63 + ".jpg",
                "0" * 64 + ".exe", "..%2F..%2Fx.jpg", "0" * 64]:
        r = c.get(f"/api/v1/documents/{DOC}/assets/{bad}", headers=hdr)
        assert r.status_code == 404, bad


def test_asset_bad_doc_id_rejected(client):
    c, token = client
    hdr = {"Authorization": f"Bearer {token}"}
    for bad_doc in ["..", "doc_small", "evil_dir"]:
        r = c.get(f"/api/v1/documents/{bad_doc}/assets/" + "0" * 64 + ".jpg",
                  headers=hdr)
        assert r.status_code == 404, bad_doc


def test_asset_missing_404(client):
    c, token = client
    r = c.get(f"/api/v1/documents/{DOC}/assets/" + "0" * 64 + ".jpg",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
