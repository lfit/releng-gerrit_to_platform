# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2026 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Gerrit REST helpers for change visibility checks.

The hooks this package handles run server-side with full visibility of
every change, including private ones.  The platform-side service
account does not share that visibility: private change refs are not
replicated to the mirrors, so any workflow dispatched for a private
change fails immediately (see issue #116).

The Gerrit hooks plugin does not pass ``--private``/``--wip`` flags to
the ``patchset-created`` hook, so the private state cannot be read from
the hook payload.  Instead, this module probes the change anonymously
over the Gerrit REST API.  Gerrit answers HTTP 404 for changes the
requester cannot see, which is exactly the condition that matters:
a change invisible to anonymous users is also invisible to the
platform-side account and its refs are absent from the mirror.

The probe fails open: any outcome other than a definitive 404 (network
error, timeout, unexpected status, unparseable change URL) allows the
dispatch to proceed, so a Gerrit REST outage can never block CI.
"""

import re
import time
import urllib.error
import urllib.request
from configparser import Error as ConfigParserError
from typing import Optional

from gerrit_to_platform._logging import get_logger
from gerrit_to_platform.config import get_setting

log = get_logger(__name__)

# Seconds to wait for the Gerrit REST endpoint before failing open.
REQUEST_TIMEOUT = 10

# Matches change URLs of the shape emitted by Gerrit hooks:
#     https://gerrit.example.org/r/c/example%2Fproject/+/12345
# Group 1 captures the REST base URL (everything before "/c/").
# The anchored "https?://" prefix also guarantees only http(s)
# schemes ever reach urlopen below.
_CHANGE_URL_RE = re.compile(r"^(https?://.+?)/c/.+/\+/\d+$")


def is_visibility_check_enabled() -> bool:
    """
    Indicate whether the change visibility gate is enabled.

    The gate is on by default.  Operators of Gerrit servers that do not
    allow anonymous REST read access (where every change would probe as
    404 and dispatching would stop entirely) can disable it in
    ``gerrit_to_platform.ini``::

        [gerrit]
        visibility_check = false

    Returns:
        bool: False only when the option is explicitly set to a falsy
            value (``false``, ``no``, ``off`` or ``0``), True otherwise.
    """
    try:
        value = get_setting("gerrit", "visibility_check")
    except ConfigParserError:
        return True

    if isinstance(value, str) and value.strip().lower() in (
        "false",
        "no",
        "off",
        "0",
    ):
        return False

    return True


def get_rest_base_url(change_url: str) -> Optional[str]:
    """
    Derive the Gerrit REST base URL from a change URL.

    Args:
        change_url (str): the change URL passed by the Gerrit hook,
            e.g. ``https://gerrit.example.org/r/c/project/+/12345``

    Returns:
        Optional[str]: the base URL (e.g.
            ``https://gerrit.example.org/r``) or None when the URL does
            not match the expected shape.
    """
    match = _CHANGE_URL_RE.match(change_url)
    if match:
        return match.group(1)
    return None


def is_change_readable(change_url: str, change_number: str) -> bool:
    """
    Best-effort probe of whether a change is readable platform-side.

    Performs an anonymous ``GET <base>/changes/<number>`` against the
    Gerrit server named in the change URL.  Gerrit responds 404 for
    changes the requester cannot see (private changes in particular),
    which mirrors what the platform-side service account and the
    replication mirror can access.

    The check fails open: only a definitive HTTP 404 reports the change
    as unreadable.  Network errors, timeouts, unexpected statuses and
    malformed URLs all return True so that dispatching continues as
    before this check existed.

    Args:
        change_url (str): the change URL passed by the Gerrit hook
        change_number (str): the change number extracted from the URL

    Returns:
        bool: False when Gerrit definitively reports the change as not
            visible, True otherwise.
    """
    if not is_visibility_check_enabled():
        log.debug("visibility check disabled by configuration")
        return True

    base_url = get_rest_base_url(change_url)
    if base_url is None:
        log.warning(
            "cannot derive REST base url from change_url=%s; "
            "skipping visibility check",
            change_url,
        )
        return True

    if not change_number.isdigit():
        log.warning(
            "invalid change_number=%r; skipping visibility check",
            change_number,
        )
        return True

    url = f"{base_url}/changes/{change_number}"
    started = time.monotonic()
    try:
        # Scheme is constrained to http(s) by _CHANGE_URL_RE above.
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT):  # nosec B310
            pass
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if exc.code == 404:
            log.info(
                "change_number=%s is not visible anonymously "
                "(HTTP 404) elapsed_ms=%d",
                change_number,
                elapsed_ms,
            )
            return False
        log.warning(
            "visibility check for change_number=%s returned "
            "unexpected HTTP %d; failing open elapsed_ms=%d",
            change_number,
            exc.code,
            elapsed_ms,
        )
        return True
    except (urllib.error.URLError, OSError) as exc:
        log.warning(
            "visibility check for change_number=%s failed (%s); "
            "failing open elapsed_ms=%d",
            change_number,
            exc,
            int((time.monotonic() - started) * 1000),
        )
        return True

    log.debug(
        "change_number=%s is visible anonymously elapsed_ms=%d",
        change_number,
        int((time.monotonic() - started) * 1000),
    )
    return True
