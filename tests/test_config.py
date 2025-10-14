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


def test_get_project_workflow_filter(mocker):
    """Test getting project-specific workflow filter."""
    from gerrit_to_platform.config import get_project_workflow_filter

    testconfig = os.path.join(FIXTURE_DIR, "testconfig.ini")
    mocker.patch("gerrit_to_platform.config.CONFIG_FILES", {"config": testconfig})

    # Test project with filter configured
    actual = get_project_workflow_filter("releng/builder", "verify")
    assert actual == "packer"

    actual = get_project_workflow_filter("releng/builder", "merge")
    assert actual == "packer"

    actual = get_project_workflow_filter("ci-management", "verify")
    assert actual == "jjb"

    # Test project without filter configured
    actual = get_project_workflow_filter("some/other-project", "verify")
    assert actual is None

    # Test project with section but missing filter
    actual = get_project_workflow_filter("releng/builder", "nonexistent")
    assert actual is None
