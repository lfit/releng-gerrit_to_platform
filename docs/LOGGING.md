<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Logging in `gerrit_to_platform`

The `gerrit_to_platform` package ships a centralised, opt-in logging
framework operators can enable without editing any installed source.
This guide documents the operator-facing configuration surface and the
developer contract used by the in-tree modules.

The design rationale lives in
`gerrit-action/docs/G2P-LOGGING-IMPROVEMENTS.md`; this file documents
the implementation that ships in `gerrit_to_platform/_logging.py`.

## TL;DR for operators

By default the package logs at `WARNING` to **stderr** and produces the
exact same user-facing stdout it always has.  To turn on diagnostics:

```bash
# Verbose, human-readable, captured into a file beside Gerrit's logs.
export G2P_LOG_LEVEL=INFO
export G2P_LOG_FILE=/var/gerrit/logs/gerrit_to_platform.log

# JSON for downstream aggregation (Loki, ELK, GitHub Actions log artefact, ...).
export G2P_LOG_FORMAT=json

# Re-emit DEBUG for the GitHub client, leave the rest at INFO.
export G2P_LOG_LEVEL_OVERRIDES=gerrit_to_platform.github=DEBUG
```

Every line carries a short correlation id so a single Gerrit event
remains greppable across log lines, even when the file aggregates
output from concurrent hook invocations.  Hook wrappers (e.g. the
`gerrit-action` wrapper script) may seed the same id by exporting an
environment variable named in `G2P_LOG_CORRELATION_ID_ENV`.

## Configuration surface

`configure()` resolves settings in this precedence (highest first):

1. `G2P_LOG_*` environment variables.
2. The `[logging]` section of `gerrit_to_platform.ini` (if present).
3. Built-in defaults.

<!-- markdownlint-disable MD013 -->

| Env var / INI key       | Default   | Purpose                                                                 |
| ----------------------- | --------- | ----------------------------------------------------------------------- |
| `level`                 | `WARNING` | Root level: `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`.                |
| `level_overrides`       | empty     | Comma-separated `logger.name=LEVEL` pairs.                              |
| `format`                | `text`    | `text` (human) or `json` (one JSON object per line).                    |
| `file`                  | empty     | Optional secondary file sink; primary remains stderr.                   |
| `file_mode`             | `append`  | `append` or `overwrite`.                                                |
| `redact_request_bodies` | `true`    | When `false`, request bodies log at DEBUG (still scrubbed of secrets).  |
| `correlation_id_env`    | empty     | If set, `configure()` reads the cid from this env var (parent wrapper provides it). |

<!-- markdownlint-enable MD013 -->

INI example:

```ini
[logging]
level = INFO
format = json
file = /var/gerrit/logs/gerrit_to_platform.log
correlation_id_env = G2P_PARENT_CID
level_overrides = gerrit_to_platform.github.dispatch=DEBUG
```

## Log line format

Default `text` layout:

```text
2026-05-12T14:30:00Z [INFO ] [cid=abc123] gerrit_to_platform.patchset_created: dispatching workflow gerrit-verify.yaml on owner/repo
```

`json` layout (one object per line, includes `schema_version` so
downstream consumers can tolerate future change):

```json
{"cid":"abc123","level":"INFO","logger":"gerrit_to_platform.patchset_created","message":"dispatch attempt platform=github owner=owner repo=repo workflow=verify ...","schema_version":"1","ts":"2026-05-12T14:30:00Z"}
```

Any keys passed via `logger.info("...", extra={...})` land under the
JSON `extra` sub-object.

## Logger hierarchy

```text
gerrit_to_platform                       # root, level governed by `level`
├── gerrit_to_platform.patchset_created  # patchset-created hook entry
├── gerrit_to_platform.comment_added     # comment-added hook entry
├── gerrit_to_platform.change_merged     # change-merged hook entry
├── gerrit_to_platform.helpers           # dispatch loop & helpers
├── gerrit_to_platform.config            # INI / replication.config loader
└── gerrit_to_platform.github            # GitHub HTTP client
    └── gerrit_to_platform.github.dispatch
```

Operators raise one subsystem when they need it:

```bash
G2P_LOG_LEVEL=INFO \
G2P_LOG_LEVEL_OVERRIDES='gerrit_to_platform.github=DEBUG'
```

## Sensitive-data handling

`configure()` attaches a `RedactingFilter` to **every** handler so any
future sink (file, syslog, network) inherits the same protection
automatically.  The filter scrubs:

- GitHub token shapes: `gh[posr]_…` (PAT, OAuth, server, refresh).
- `Authorization: Bearer …` and `Authorization: token …` headers.
- `?token=…`, `?access_token=…`, `?api_key=…` query-string parameters.
- `token=`, `secret=`, `password=` labelled values in any text.

The unit-test `test_no_token_reaches_handler_via_logger` asserts that a
synthetic token logged at DEBUG never reaches the underlying stream
verbatim.

## Correlation IDs

Each hook invocation carries a short URL-safe correlation id.  When no
parent provides one, `configure()` generates a fresh value on first
access.  When an enclosing wrapper process already minted one (for
example the `gerrit-action` hook wrapper that tees stdout/stderr into
a per-event file), the wrapper exports that value under any env-var
name and tells `gerrit_to_platform` to pick it up:

```bash
export G2P_LOG_CORRELATION_ID_ENV=G2P_PARENT_CID
export G2P_PARENT_CID="abc12345"
```

The shared id then appears in both the wrapper log and the package
log, making a single Gerrit event greppable across processes.

## Operator playbook

When an event misbehaves:

1. Reproduce: push a change, leave a comment, or merge.
2. Locate the correlation id in the wrapper's per-event log header.
3. `grep "cid=<value>" /var/gerrit/logs/gerrit_to_platform.log`.
4. Read the structured trace top-to-bottom:
   - `hook=… project=…` entry line.
   - `event parsed change_number=…` (DEBUG verbosity).
   - `platform detected platform=… owner=… repo=…`.
   - `workflow lookup … candidates=N`.
   - `dispatch attempt …` and `dispatch success/failure …`.
   - `hook=… exit … elapsed_ms=…`.

Where the trace ends tells the operator which subsystem broke:

<!-- markdownlint-disable MD013 -->

| Trace ends at...      | Probable culprit                                        |
| --------------------- | ------------------------------------------------------- |
| Nothing logged        | Gerrit hook script never fired (Gerrit/wrapper issue).  |
| `hook=…` alone        | INI/replication.config parse failure or empty remotes.  |
| `platform detected`   | Workflow lookup failed (perms, missing repo, network).  |
| `workflow lookup`     | No matching workflows in the target repo.               |
| `dispatch failure`    | GitHub API rejected the dispatch (status logged).       |

<!-- markdownlint-enable MD013 -->

## Developer contract

Inside the package, any module that needs to log obtains its logger
like this:

```python
from gerrit_to_platform._logging import get_logger

log = get_logger(__name__)

log.info("dispatching workflow=%s owner=%s repo=%s", name, owner, repo)
```

Rules:

- Never call `logging.basicConfig`, `logging.getLogger("root")` or
  attach handlers/formatters/filters in any module other than
  `_logging.py`.
- Hook entry-points call `_logging.configure()` as their first
  non-trivial step.  The call is idempotent.
- Treat user-facing `print()` (dispatch confirmation echoed to Gerrit
  hook stdout) as a separate, parallel channel.  Do not delete it.
- Use `extra={...}` for structured fields; the JSON formatter promotes
  them automatically.
- Never log raw GitHub tokens, request bodies or response payloads
  larger than ~200 chars.  The `RedactingFilter` is a safety net, not
  a substitute for thoughtful messages.

## Tests

The `tests/test_logging.py` module covers the framework's behaviour:

- Default `WARNING` to stderr.
- Env-over-INI precedence and per-logger overrides.
- Idempotent `configure()` and `force=True` reset.
- Broken file sink falls back to stderr without raising.
- All redaction patterns (token, bearer header, query string, `extra`
  attributes, end-to-end through a real logger).
- Text and JSON formatter layouts and `schema_version`.
- Correlation id generation and inheritance from env.
