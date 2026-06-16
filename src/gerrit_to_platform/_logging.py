# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2026 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Centralised logging framework for the ``gerrit_to_platform`` package.

This module owns *all* logging configuration for the package.  Every other
module obtains a logger via :func:`get_logger` (a thin wrapper around
``logging.getLogger(__name__)``) and never touches handlers, formatters or
filters directly.

The hook entry-points (``patchset_created``, ``comment_added``,
``change_merged``) call :func:`configure` as their first non-trivial step.
``configure`` is idempotent so repeated invocations in the same process
(common in tests) do not stack handlers.

Design constraints come from
``gerrit-action/docs/G2P-LOGGING-IMPROVEMENTS.md``:

* Standard library only (no new runtime dependencies).
* Default behaviour matches today: ``WARNING`` to stderr.
* Verbose/structured output is opt-in via environment variables or the
  optional ``[logging]`` section in ``gerrit_to_platform.ini``.
* Failure to open a secondary file sink falls back to stderr; logging
  must never abort a hook.
* A :class:`RedactingFilter` scrubs GitHub tokens and ``Authorization``
  headers before *any* handler sees the record.
* Each hook invocation carries a short correlation id, propagated via a
  :class:`logging.LoggerAdapter`-style filter so a single Gerrit event
  remains greppable across log lines.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import sys
import time
from typing import Any, Dict, List, Optional

# Public constants
ROOT_LOGGER_NAME = "gerrit_to_platform"
ENV_PREFIX = "G2P_LOG_"
INI_SECTION = "logging"
JSON_SCHEMA_VERSION = "1"

DEFAULT_LEVEL = "WARNING"
DEFAULT_FORMAT = "text"
DEFAULT_FILE_MODE = "append"

# Module-level state.  `configure()` is idempotent and respects this flag.
_CONFIGURED: bool = False
_CORRELATION_ID: Optional[str] = None

# Sensitive value patterns scrubbed by RedactingFilter.  These cover the
# common GitHub token shapes (``ghp_``, ``gho_``, ``ghs_``, ``ghr_``) and
# bearer/token authorisation headers.
_TOKEN_PATTERN = re.compile(r"gh[posr]_[A-Za-z0-9]{20,}")
_BEARER_PATTERN = re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer|token)\s+\S+")
_QS_TOKEN_PATTERN = re.compile(
    r"([?&](?:token|access_token|api_key)=)[^&\s]+",
    re.IGNORECASE,
)
# Long opaque hex/base64 strings adjacent to a "token" / "secret" label.
_LABELLED_SECRET_PATTERN = re.compile(
    r"(?i)((?:token|secret|password)\s*[:=]\s*)['\"]?([A-Za-z0-9_\-]{16,})['\"]?"
)


class RedactingFilter(logging.Filter):
    """Scrub credentials and other secrets from every log record.

    The filter is attached to every handler installed by :func:`configure`
    so any future handler (syslog, network sink, etc.) inherits the same
    protection automatically.  The filter operates on the rendered log
    message and on string-typed ``extra=`` attributes.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        """Mutate ``record`` in place to remove sensitive substrings."""
        try:
            rendered = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True

        scrubbed = self._scrub(rendered)
        if scrubbed != rendered:
            record.msg = scrubbed
            record.args = ()

        # Scrub any string-valued extras the caller attached to the record.
        for attr_name, value in list(record.__dict__.items()):
            if attr_name in _RECORD_ATTR_BLOCKLIST:
                continue
            if isinstance(value, str):
                cleaned = self._scrub(value)
                if cleaned != value:
                    setattr(record, attr_name, cleaned)
        return True

    @staticmethod
    def _scrub(text: str) -> str:
        """Apply every secret pattern to ``text`` and return the result."""
        text = _TOKEN_PATTERN.sub("***", text)
        text = _BEARER_PATTERN.sub(r"\1***", text)
        text = _QS_TOKEN_PATTERN.sub(r"\1***", text)
        text = _LABELLED_SECRET_PATTERN.sub(r"\1***", text)
        return text


# Standard ``LogRecord`` attributes we do *not* want to mutate via the
# RedactingFilter even if their string value matches a pattern.
_RECORD_ATTR_BLOCKLIST = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
    }
)


class _CorrelationFilter(logging.Filter):
    """Attach the current correlation id to every record as ``cid``."""

    def __init__(self, cid: str) -> None:
        super().__init__()
        self._cid = cid

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "cid") or not getattr(record, "cid", None):
            record.cid = self._cid
        return True


class TextFormatter(logging.Formatter):
    """Human-readable, fixed-width log format.

    Layout: ``{ts} [{level:<5}] [cid={cid}] {logger}: {message}``
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created))
        cid = getattr(record, "cid", "-")
        message = record.getMessage()
        formatted = f"{ts} [{record.levelname:<5}] [cid={cid}] {record.name}: {message}"
        if record.exc_info:
            formatted = f"{formatted}\n{self.formatException(record.exc_info)}"
        return formatted


class JsonFormatter(logging.Formatter):
    """One JSON object per line.

    Carries any ``extra=`` keys passed by the caller under the ``extra``
    sub-object.  A ``schema_version`` field is included so downstream
    consumers can tolerate future format changes.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "cid": getattr(record, "cid", "-"),
            "logger": record.name,
            "message": record.getMessage(),
            "schema_version": JSON_SCHEMA_VERSION,
        }
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RECORD_ATTR_BLOCKLIST
            and key not in {"cid"}
            and not key.startswith("_")
        }
        if extras:
            payload["extra"] = extras
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, sort_keys=True)


def _generate_correlation_id() -> str:
    """Return an 8-char URL-safe correlation id."""
    return secrets.token_urlsafe(6)[:8]


def get_correlation_id() -> str:
    """Return the current correlation id, generating one on first access."""
    global _CORRELATION_ID
    if _CORRELATION_ID is None:
        _CORRELATION_ID = _generate_correlation_id()
    return _CORRELATION_ID


def set_correlation_id(cid: str) -> None:
    """Override the current correlation id (e.g. inherited from a wrapper)."""
    global _CORRELATION_ID
    _CORRELATION_ID = cid or _generate_correlation_id()


def _settings_from_env() -> Dict[str, str]:
    """Collect ``G2P_LOG_*`` environment variables as a settings mapping."""
    return {
        key[len(ENV_PREFIX) :].lower(): value
        for key, value in os.environ.items()
        if key.startswith(ENV_PREFIX) and value != ""
    }


def _settings_from_ini() -> Dict[str, str]:
    """Collect the ``[logging]`` section from ``gerrit_to_platform.ini``.

    Failures (missing file, parse error, missing section) silently yield
    an empty mapping so logging configuration never aborts a hook.
    """
    try:
        # Local import to avoid an import cycle at package load time.
        from gerrit_to_platform.config import get_config

        config = get_config()
    except Exception:
        return {}
    if not config.has_section(INI_SECTION):
        return {}
    return {key.lower(): value for key, value in config.items(INI_SECTION)}


def _resolve_settings() -> Dict[str, str]:
    """Merge defaults, INI values, and environment with env taking priority."""
    settings: Dict[str, str] = {
        "level": DEFAULT_LEVEL,
        "format": DEFAULT_FORMAT,
        "file": "",
        "file_mode": DEFAULT_FILE_MODE,
        "redact_request_bodies": "true",
        "level_overrides": "",
        "correlation_id_env": "",
    }
    settings.update(_settings_from_ini())
    settings.update(_settings_from_env())
    return settings


def _coerce_level(name: str) -> int:
    """Translate a level name to its numeric value, defaulting to WARNING."""
    try:
        return logging._nameToLevel[name.strip().upper()]
    except (KeyError, AttributeError):
        return logging.WARNING


def _bool_setting(value: str, default: bool = True) -> bool:
    """Parse a loose textual boolean (``true``/``false``/``yes``/``no``)."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_request_body_redacted() -> bool:
    """Return ``True`` if request-body logging is suppressed (the default).

    Operators may set ``G2P_LOG_REDACT_REQUEST_BODIES=false`` (or the
    matching INI key) to log scrubbed request bodies at DEBUG.
    """
    return _bool_setting(
        _resolve_settings().get("redact_request_bodies", "true"),
        default=True,
    )


def configure(force: bool = False) -> logging.Logger:
    """Configure the root ``gerrit_to_platform`` logger.

    Called once at the top of each hook entry-point.  Subsequent calls
    are no-ops unless ``force=True`` (used by the test-suite to reset
    state between cases).

    Args:
        force: When ``True``, tear down existing handlers and reinstall
            them from the current environment and INI state.

    Returns:
        The configured root logger.
    """
    global _CONFIGURED
    root = logging.getLogger(ROOT_LOGGER_NAME)
    if _CONFIGURED and not force:
        return root

    settings = _resolve_settings()

    # Resolve correlation id: an inherited value (e.g. from the
    # gerrit-action hook wrapper) wins over a freshly minted one so the
    # entire run remains greppable across processes.
    cid_env = settings.get("correlation_id_env", "")
    inherited = os.environ.get(cid_env, "") if cid_env else ""
    if inherited:
        set_correlation_id(inherited)
    else:
        # Touch the accessor so a default id exists for this run.
        get_correlation_id()

    # Reset any previously installed handlers (idempotent setup).
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # pragma: no cover - defensive
            pass

    root.setLevel(_coerce_level(settings.get("level", DEFAULT_LEVEL)))
    # The root *package* logger should not bubble to the unconfigured
    # Python root logger; that would double-emit records on stderr.
    root.propagate = False

    fmt_kind = settings.get("format", DEFAULT_FORMAT).strip().lower()
    formatter: logging.Formatter
    if fmt_kind == "json":
        formatter = JsonFormatter()
    else:
        formatter = TextFormatter()

    redact = RedactingFilter()
    cid_filter = _CorrelationFilter(get_correlation_id())

    handlers: List[logging.Handler] = []
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    handlers.append(stderr_handler)

    file_path = settings.get("file") or ""
    if file_path:
        mode = (
            "w"
            if settings.get("file_mode", DEFAULT_FILE_MODE).strip().lower()
            == "overwrite"
            else "a"
        )
        try:
            parent = os.path.dirname(file_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            file_handler = logging.FileHandler(file_path, mode=mode, encoding="utf-8")
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except OSError as exc:
            sys.stderr.write(
                "gerrit_to_platform: failed to open log file "
                f"{file_path!r}: {exc}; falling back to stderr only\n"
            )

    for handler in handlers:
        handler.addFilter(redact)
        handler.addFilter(cid_filter)
        root.addHandler(handler)

    # Per-logger overrides arrive as a comma-separated ``name=LEVEL`` list.
    overrides = settings.get("level_overrides", "")
    for entry in overrides.split(","):
        entry = entry.strip()
        if not entry or "=" not in entry:
            continue
        name, level = entry.split("=", 1)
        logging.getLogger(name.strip()).setLevel(_coerce_level(level))

    _CONFIGURED = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a module logger, configuring the framework on first use.

    All package modules call this in place of ``logging.getLogger`` so
    that even import-time logging (rare, but possible) has a working
    handler chain attached.
    """
    if not _CONFIGURED:
        configure()
    return logging.getLogger(name)


def reset_for_tests() -> None:
    """Reset module state.  Test-suite use only."""
    global _CONFIGURED, _CORRELATION_ID
    root = logging.getLogger(ROOT_LOGGER_NAME)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # pragma: no cover - defensive
            pass
    root.setLevel(logging.NOTSET)
    _CONFIGURED = False
    _CORRELATION_ID = None
