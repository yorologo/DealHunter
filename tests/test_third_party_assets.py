import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "src/dealhunter/web/static/css/bootstrap.min.css": "3c8f27e6009ccfd710a905e6dcf12d0ee3c6f2ac7da05b0572d3e0d12e736fc8",
    "src/dealhunter/web/static/js/bootstrap.bundle.min.js": "0833b2e9c3a26c258476c46266e6877fc75218625162e0460be9a3a098a61c6c",
    "src/dealhunter/web/static/js/htmx.min.js": "449317ade7881e949510db614991e195c3a099c4c791c24dacec55f9f4a2a452",
    "src/dealhunter/web/static/js/chart.umd.min.js": "08dfa4730571b23810c34fc39c5101461ecafca56c3f92caf4850509cb158f30",
}


def test_vendored_asset_hashes_match_inventory():
    inventory = (ROOT / "docs" / "third-party-assets.md").read_text()
    for relative, expected in EXPECTED.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected, relative
        assert expected in inventory


def test_vendored_asset_versions_are_documented():
    inventory = (ROOT / "docs" / "third-party-assets.md").read_text()
    for version in ("5.3.3", "1.9.12", "4.4.2"):
        assert version in inventory
    assert "MIT" in inventory
    assert "0BSD" in inventory
