from dealhunter.cli import build_parser
from dealhunter.db import CURRENT_SCHEMA_VERSION
from dealhunter.metadata import VERSION
from dealhunter.web.app import create_app


def test_rc_runtime_metadata_has_one_version_source():
    assert VERSION == "3.2.0"
    assert CURRENT_SCHEMA_VERSION == 16
    assert f"v{VERSION}" in build_parser().description

    app = create_app({"TESTING": True})
    with app.test_request_context("/"):
        context = {}
        app.update_template_context(context)
    assert context["dealhunter_version"] == VERSION
