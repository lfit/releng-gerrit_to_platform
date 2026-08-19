# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2026 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Unit tests for the gerrit REST helpers."""

import urllib.error
from configparser import NoSectionError

import gerrit_to_platform.gerrit  # type: ignore
from gerrit_to_platform.gerrit import (  # type: ignore
    get_rest_base_url,
    is_change_readable,
    is_visibility_check_enabled,
)

CHANGE_URL = "https://gerrit.example.org/r/c/example/project/+/46421"
CHANGE_NUMBER = "46421"


def _http_error(code: int) -> urllib.error.HTTPError:
    """Build an HTTPError with the given status code."""
    return urllib.error.HTTPError(
        url=f"https://gerrit.example.org/r/changes/{CHANGE_NUMBER}",
        code=code,
        msg="error",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )


def test_get_rest_base_url():
    """Base URL is everything before the /c/ component."""
    assert get_rest_base_url(CHANGE_URL) == "https://gerrit.example.org/r"
    assert (
        get_rest_base_url("https://gerrit.example.org/c/foo/+/1")
        == "https://gerrit.example.org"
    )
    assert (
        get_rest_base_url("https://gerrit.example.org/r/c/foo%2Fbar/+/12")
        == "https://gerrit.example.org/r"
    )


def test_get_rest_base_url_invalid():
    """Unexpected URL shapes return None."""
    assert get_rest_base_url("not-a-url") is None
    assert get_rest_base_url("ftp://gerrit.example.org/c/foo/+/1") is None
    assert get_rest_base_url("https://gerrit.example.org/r/12345") is None


def test_is_visibility_check_enabled_default(mocker):
    """The gate defaults to enabled when unconfigured."""
    mocker.patch(
        "gerrit_to_platform.gerrit.get_setting",
        side_effect=NoSectionError("gerrit"),
    )
    assert is_visibility_check_enabled() is True


def test_is_visibility_check_enabled_disabled(mocker):
    """Explicit falsy values disable the gate."""
    for value in ["false", "False", "no", "off", "0", " false "]:
        mocker.patch(
            "gerrit_to_platform.gerrit.get_setting",
            return_value=value,
        )
        assert is_visibility_check_enabled() is False


def test_is_visibility_check_enabled_truthy(mocker):
    """Any other configured value keeps the gate enabled."""
    for value in ["true", "yes", "on", "1", "anything"]:
        mocker.patch(
            "gerrit_to_platform.gerrit.get_setting",
            return_value=value,
        )
        assert is_visibility_check_enabled() is True


def test_is_change_readable_visible(mocker):
    """A 200 response reports the change as readable."""
    mocker.patch(
        "gerrit_to_platform.gerrit.is_visibility_check_enabled",
        return_value=True,
    )
    urlopen = mocker.patch(
        "gerrit_to_platform.gerrit.urllib.request.urlopen",
        return_value=mocker.MagicMock(),
    )
    assert is_change_readable(CHANGE_URL, CHANGE_NUMBER) is True
    assert urlopen.call_args[0][0] == "https://gerrit.example.org/r/changes/46421"


def test_is_change_readable_not_found(mocker):
    """A 404 response reports the change as unreadable."""
    mocker.patch(
        "gerrit_to_platform.gerrit.is_visibility_check_enabled",
        return_value=True,
    )
    mocker.patch(
        "gerrit_to_platform.gerrit.urllib.request.urlopen",
        side_effect=_http_error(404),
    )
    assert is_change_readable(CHANGE_URL, CHANGE_NUMBER) is False


def test_is_change_readable_unexpected_status_fails_open(mocker):
    """Statuses other than 404 fail open."""
    mocker.patch(
        "gerrit_to_platform.gerrit.is_visibility_check_enabled",
        return_value=True,
    )
    for code in [401, 403, 500, 503]:
        mocker.patch(
            "gerrit_to_platform.gerrit.urllib.request.urlopen",
            side_effect=_http_error(code),
        )
        assert is_change_readable(CHANGE_URL, CHANGE_NUMBER) is True


def test_is_change_readable_network_error_fails_open(mocker):
    """Network errors and timeouts fail open."""
    mocker.patch(
        "gerrit_to_platform.gerrit.is_visibility_check_enabled",
        return_value=True,
    )
    for error in [
        urllib.error.URLError("connection refused"),
        OSError("timed out"),
    ]:
        mocker.patch(
            "gerrit_to_platform.gerrit.urllib.request.urlopen",
            side_effect=error,
        )
        assert is_change_readable(CHANGE_URL, CHANGE_NUMBER) is True


def test_is_change_readable_bad_url_fails_open(mocker):
    """An unparseable change URL skips the probe and fails open."""
    mocker.patch(
        "gerrit_to_platform.gerrit.is_visibility_check_enabled",
        return_value=True,
    )
    urlopen = mocker.patch("gerrit_to_platform.gerrit.urllib.request.urlopen")
    assert is_change_readable("not-a-url", CHANGE_NUMBER) is True
    urlopen.assert_not_called()


def test_is_change_readable_bad_change_number_fails_open(mocker):
    """A non-numeric change number skips the probe and fails open."""
    mocker.patch(
        "gerrit_to_platform.gerrit.is_visibility_check_enabled",
        return_value=True,
    )
    urlopen = mocker.patch("gerrit_to_platform.gerrit.urllib.request.urlopen")
    assert is_change_readable(CHANGE_URL, "46421; rm -rf /") is True
    urlopen.assert_not_called()


def test_is_change_readable_disabled_skips_probe(mocker):
    """A disabled gate never touches the network."""
    mocker.patch(
        "gerrit_to_platform.gerrit.is_visibility_check_enabled",
        return_value=False,
    )
    urlopen = mocker.patch("gerrit_to_platform.gerrit.urllib.request.urlopen")
    assert is_change_readable(CHANGE_URL, CHANGE_NUMBER) is True
    urlopen.assert_not_called()


def test_module_reference():
    """The module exposes the expected public helpers."""
    assert callable(gerrit_to_platform.gerrit.is_change_readable)
