from dealhunter.cli import build_parser
from dealhunter.db import CURRENT_SCHEMA_VERSION
from dealhunter.metadata import VERSION
from dealhunter.web.app import create_app


def test_runtime_metadata_has_one_version_source():
    assert VERSION == "3.3.1"
    assert CURRENT_SCHEMA_VERSION == 17
    assert f"v{VERSION}" in build_parser().description

    app = create_app({"TESTING": True})
    with app.test_request_context("/"):
        context = {}
        app.update_template_context(context)
    assert context["dealhunter_version"] == VERSION


def test_android_packaging_uses_native_cryptography():
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    crypto_deps = [d for d in project["project"]["dependencies"] if d.startswith("cryptography")]
    assert crypto_deps == ["cryptography; sys_platform != 'android'"]
    requirements = (root / "requirements.txt").read_text()
    assert 'cryptography; sys_platform != "android"' in requirements
