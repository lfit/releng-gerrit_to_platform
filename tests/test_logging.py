# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2025 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Tests for ``gerrit_to_platform._logging``."""

import io
import json
import logging
import os

import pytest

from gerrit_to_platform import _logging


@pytest.fixture(autouse=True)
def _reset_logging_state(monkeypatch):
    """Ensure each test starts from a pristine logging configuration."""
    # Strip any G2P_LOG_* env vars left over from another test.
    for key in list(os.environ):
        if key.startswith(_logging.ENV_PREFIX):
            monkeypatch.delenv(key, raising=False)
    _logging.reset_for_tests()
    yield
    _logging.reset_for_tests()


def _stderr_handler(root):
    return next(h for h in root.handlers if isinstance(h, logging.StreamHandler))


def test_default_configuration_is_warning_to_stderr(monkeypatch):
    """With no env or INI input, the root logger defaults to WARNING."""
    monkeypatch.setattr(_logging, "_settings_from_ini", lambda: {})
    root = _logging.configure(force=True)
    assert root.level == logging.WARNING
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)


def test_env_overrides_ini(monkeypatch):
    """Environment variables MUST win over INI values for matching keys."""
    monkeypatch.setattr(
        _logging,
        "_settings_from_ini",
        lambda: {"level": "ERROR", "format": "json"},
    )
    monkeypatch.setenv("G2P_LOG_LEVEL", "DEBUG")
    root = _logging.configure(force=True)
    assert root.level == logging.DEBUG
    # Format from INI still applies because env did not override it.
    handler = _stderr_handler(root)
    assert isinstance(handler.formatter, _logging.JsonFormatter)


def test_configure_is_idempotent(monkeypatch):
    """Calling ``configure`` twice without ``force`` must not stack handlers."""
    monkeypatch.setattr(_logging, "_settings_from_ini", lambda: {})
    root = _logging.configure(force=True)
    initial_count = len(root.handlers)
    # Second call without `force` is a no-op.
    _logging.configure()
    assert len(root.handlers) == initial_count


def test_configure_force_resets_handlers(monkeypatch):
    """``force=True`` must replace, not append, handlers."""
    monkeypatch.setattr(_logging, "_settings_from_ini", lambda: {})
    root = _logging.configure(force=True)
    initial_count = len(root.handlers)
    _logging.configure(force=True)
    assert len(root.handlers) == initial_count


def test_broken_file_sink_falls_back_to_stderr(monkeypatch, capsys):
    """An unwritable file path must not abort logging configuration."""
    monkeypatch.setattr(
        _logging,
        "_settings_from_ini",
        lambda: {"file": "/proc/cannot/write/here.log"},
    )
    root = _logging.configure(force=True)
    err = capsys.readouterr().err
    assert "failed to open log file" in err
    # Stderr handler still present.
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)


def test_redacting_filter_scrubs_github_tokens():
    """GitHub token shapes must never reach a handler verbatim."""
    f = _logging.RedactingFilter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="leaking ghp_%s token" % ("A" * 36),
        args=(),
        exc_info=None,
    )
    assert f.filter(record) is True
    assert "ghp_" not in record.getMessage()
    assert "***" in record.getMessage()


def test_redacting_filter_scrubs_authorization_header():
    f = _logging.RedactingFilter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="curl -H 'Authorization: Bearer abc123XYZ' https://api.example",
        args=(),
        exc_info=None,
    )
    f.filter(record)
    assert "Bearer abc123XYZ" not in record.getMessage()
    assert "***" in record.getMessage()


def test_redacting_filter_scrubs_query_string_token():
    f = _logging.RedactingFilter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="https://api.example/x?token=supersecret&other=1",
        args=(),
        exc_info=None,
    )
    f.filter(record)
    assert "supersecret" not in record.getMessage()


def test_redacting_filter_handles_extra_dict_strings():
    f = _logging.RedactingFilter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="payload contains nothing here",
        args=(),
        exc_info=None,
    )
    record.payload_summary = "token=abcdefghijklmnopqrstuv"
    f.filter(record)
    assert "abcdefghijklmnopqrstuv" not in record.payload_summary


def test_text_formatter_layout(monkeypatch):
    """Text format includes timestamp, level, cid, logger name, and message."""
    monkeypatch.setattr(_logging, "_settings_from_ini", lambda: {})
    _logging.set_correlation_id("testcid1")
    root = _logging.configure(force=True)
    handler = _stderr_handler(root)
    buffer = io.StringIO()
    handler.stream = buffer
    logger = logging.getLogger("gerrit_to_platform.unit_test")
    logger.warning("hello world")
    line = buffer.getvalue().strip()
    assert "[WARNING]" in line
    assert "[cid=testcid1]" in line
    assert "gerrit_to_platform.unit_test" in line
    assert "hello world" in line


def test_json_formatter_emits_valid_json(monkeypatch):
    monkeypatch.setattr(_logging, "_settings_from_ini", lambda: {"format": "json"})
    _logging.set_correlation_id("jsoncid1")
    root = _logging.configure(force=True)
    handler = _stderr_handler(root)
    buffer = io.StringIO()
    handler.stream = buffer
    logger = logging.getLogger("gerrit_to_platform.unit_test")
    logger.warning("structured", extra={"event": "patchset-created"})
    payload = json.loads(buffer.getvalue().strip())
    assert payload["level"] == "WARNING"
    assert payload["cid"] == "jsoncid1"
    assert payload["logger"] == "gerrit_to_platform.unit_test"
    assert payload["message"] == "structured"
    assert payload["schema_version"] == _logging.JSON_SCHEMA_VERSION
    assert payload["extra"]["event"] == "patchset-created"


def test_correlation_id_inherited_from_env(monkeypatch):
    """A pre-existing env var named in settings must seed the cid."""
    monkeypatch.setenv("G2P_PARENT_CID", "parent12")
    monkeypatch.setattr(
        _logging,
        "_settings_from_ini",
        lambda: {"correlation_id_env": "G2P_PARENT_CID"},
    )
    _logging.configure(force=True)
    assert _logging.get_correlation_id() == "parent12"


def test_correlation_id_is_generated_when_missing(monkeypatch):
    monkeypatch.setattr(_logging, "_settings_from_ini", lambda: {})
    _logging.configure(force=True)
    cid = _logging.get_correlation_id()
    assert cid and len(cid) >= 6


def test_per_logger_overrides(monkeypatch):
    monkeypatch.setattr(
        _logging,
        "_settings_from_ini",
        lambda: {
            "level": "WARNING",
            "level_overrides": "gerrit_to_platform.github=DEBUG",
        },
    )
    _logging.configure(force=True)
    assert logging.getLogger("gerrit_to_platform.github").level == logging.DEBUG
    assert logging.getLogger("gerrit_to_platform").level == logging.WARNING


def test_invalid_level_falls_back_to_warning(monkeypatch):
    monkeypatch.setattr(_logging, "_settings_from_ini", lambda: {"level": "NONSENSE"})
    root = _logging.configure(force=True)
    assert root.level == logging.WARNING


def test_get_logger_returns_module_logger(monkeypatch):
    monkeypatch.setattr(_logging, "_settings_from_ini", lambda: {})
    logger = _logging.get_logger("gerrit_to_platform.example")
    assert logger.name == "gerrit_to_platform.example"


def test_no_token_reaches_handler_via_logger(monkeypatch):
    """End-to-end: a fake token in a real log call never appears verbatim."""
    monkeypatch.setattr(
        _logging,
        "_settings_from_ini",
        lambda: {"level": "DEBUG", "redact_request_bodies": "false"},
    )
    root = _logging.configure(force=True)
    handler = _stderr_handler(root)
    buffer = io.StringIO()
    handler.stream = buffer
    logger = logging.getLogger("gerrit_to_platform.unit_test")
    fake_token = "ghp_" + "X" * 36
    logger.debug("dispatch body token=%s", fake_token)
    output = buffer.getvalue()
    assert fake_token not in output
    assert "***" in output


def test_file_sink_writes_records(monkeypatch, tmp_path):
    log_path = tmp_path / "g2p.log"
    monkeypatch.setattr(
        _logging,
        "_settings_from_ini",
        lambda: {"level": "INFO", "file": str(log_path)},
    )
    _logging.configure(force=True)
    logging.getLogger("gerrit_to_platform.unit_test").info("hello file sink")
    # Force-flush the file handler.
    for handler in logging.getLogger("gerrit_to_platform").handlers:
        handler.flush()
    contents = log_path.read_text()
    assert "hello file sink" in contents
