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

import json
import os

import pytest

import gerrit_to_platform.config  # type: ignore
from gerrit_to_platform.config import (  # type: ignore
    CONFIG,
    REPLICATION,
    get_config,
    get_mapping,
    get_replication_remotes,
    get_setting,
    has_section,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "fixtures",
)

TEST_CONFIG = os.path.join(FIXTURE_DIR, "testconfig.ini")
REPLICATION_CONFIG = os.path.join(FIXTURE_DIR, "replication.config")
REPLICATION_MULTI_FETCH_CONFIG = os.path.join(
    FIXTURE_DIR, "replication_multi_fetch.config"
)

MOCK_CONFIG_FILES = {
    CONFIG: TEST_CONFIG,
    REPLICATION: REPLICATION_CONFIG,
}


def test_get_config(mocker):
    """Test getting config data."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "CONFIG_FILES",
        MOCK_CONFIG_FILES,
    )
    assert get_config().has_section("github.com")
    assert get_config(REPLICATION).has_section('remote "github"')


def test_get_config_tolerates_duplicate_keys(mocker):
    """Multi-valued ``fetch`` refspecs in replication.config must parse.

    Gerrit's pull-replication plugin writes multiple ``fetch = ...``
    lines under a single ``[remote "..."]`` section (valid git config
    syntax for representing a list).  Python's ``configparser`` defaults
    to ``strict=True`` and raises ``DuplicateOptionError`` for that
    pattern, which previously crashed every g2p hook the moment
    ``find_and_dispatch`` called ``get_replication_remotes()``.  This
    test loads such a config and asserts it parses without raising.
    """
    mocker.patch.object(
        gerrit_to_platform.config,
        "CONFIG_FILES",
        {
            CONFIG: TEST_CONFIG,
            REPLICATION: REPLICATION_MULTI_FETCH_CONFIG,
        },
    )
    config = get_config(REPLICATION)
    assert config.has_section('remote "onap"')
    # ``strict=False`` keeps the last value when keys repeat; verify
    # the URL field (which is single-valued) survives intact, and the
    # multi-valued ``fetch`` field at least returns a string rather
    # than raising.
    assert config.get('remote "onap"', "url") == (
        "https://gerrit.onap.org/r/a/${name}.git"
    )
    assert config.has_option('remote "onap"', "fetch")


def test_get_replication_remotes_tolerates_duplicate_keys(mocker):
    """``get_replication_remotes`` must succeed against a multi-fetch
    replication.config (regression for the field-observed crash).
    """
    mocker.patch.object(
        gerrit_to_platform.config,
        "CONFIG_FILES",
        {
            CONFIG: TEST_CONFIG,
            REPLICATION: REPLICATION_MULTI_FETCH_CONFIG,
        },
    )
    remotes = get_replication_remotes()
    assert "github" in remotes
    assert "github-g2p" in remotes["github"]
    assert remotes["github"]["github-g2p"]["owner"] == ("modeseven-gerrit-onap")
    assert remotes["github"]["github-g2p"]["remotenamestyle"] == "dash"


def test_get_mapping(mocker):
    """Test get_mapping"""
    mocker.patch.object(
        gerrit_to_platform.config,
        "CONFIG_FILES",
        MOCK_CONFIG_FILES,
    )
    expected = {"recheck": "verify", "reverify": "verify", "remerge": "merge"}
    actual = get_mapping("comment-added")
    assert expected == actual

    expected = None
    actual = get_mapping("foo")
    assert expected == actual


def test_get_replication_remotes(mocker):
    """Test getting replication remotes."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "CONFIG_FILES",
        MOCK_CONFIG_FILES,
    )
    REPLICATION_REMOTES_RETURN = os.path.join(
        FIXTURE_DIR, "replication_remotes_return.json"
    )
    with open(REPLICATION_REMOTES_RETURN) as remotes_return:
        expected = json.load(remotes_return)
    actual = get_replication_remotes()
    assert expected == actual


def test_has_section(mocker):
    """Test has_section function."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "CONFIG_FILES",
        MOCK_CONFIG_FILES,
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
        "CONFIG_FILES",
        MOCK_CONFIG_FILES,
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
