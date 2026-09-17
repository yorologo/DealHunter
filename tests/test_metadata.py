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
    assert crypto_deps == ["cryptography>=44,<51; sys_platform != 'android'"]


def test_dependency_bounds_are_explicit_and_kiss():
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert project["project"]["dependencies"] == [
        "flask>=3.0,<4",
        "cryptography>=44,<51; sys_platform != 'android'",
        "websockets>=14,<18",
        "aiohttp>=3.10,<4",
    ]
    assert project["project"]["optional-dependencies"]["test"] == [
        "pytest>=8,<10",
        "pytest-asyncio>=0.24,<2",
    ]
    assert project["project"]["scripts"]["dealwatcher"] == "dealhunter.dealwatcher:main"
