# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Unit tests for config."""

import os

import pytest

import gerrit_to_platform.config  # type: ignore
from gerrit_to_platform.config import (  # type: ignore
    get_config,
    get_setting,
    has_section,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "fixtures",
)

TEST_CONFIG = os.path.join(FIXTURE_DIR, "testconfig.ini")


def test_get_config(mocker):
    """Test getting config data."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "G2P_CONFIG_FILE",
        TEST_CONFIG,
    )
    assert get_config()


def test_has_section(mocker):
    """Test has_section function."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "G2P_CONFIG_FILE",
        TEST_CONFIG,
    )
    expected = True
    actual = has_section("github.com")
    assert expected == actual
    expected = False
    actual = has_section("foo")
    assert expected == actual


def test_get_setting(mocker):
    """Test get_setting function."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "G2P_CONFIG_FILE",
        TEST_CONFIG,
    )
    expected = ["user", "token"]
    actual = get_setting("github.com")
    assert expected == actual

    expected = "foo"
    actual = get_setting("github.com", "user")
    assert expected == actual

    with pytest.raises(Exception, match="No section: 'foobar'"):
        get_setting("foobar")
    with pytest.raises(Exception, match="No option 'baz' in section: 'github.com'"):
        get_setting("github.com", "baz")
