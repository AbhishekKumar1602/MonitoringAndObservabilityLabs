import json
import logging

from app.logging_config import JsonFormatter


def test_json_formatter_emits_required_fields() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="test.event",
        args=(),
        exc_info=None,
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "test.event"
    assert payload["severity"] == "INFO"
    assert payload["service_name"] == "orders-api"
