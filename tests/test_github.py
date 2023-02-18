# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Unit tests for github."""

import json
import os

import gerrit_to_platform.config  # type: ignore
import gerrit_to_platform.github  # type: ignore
from gerrit_to_platform.github import filter_workflows, get_workflows  # type: ignore

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "fixtures",
)

GITHUB_WORKFLOW_LIST = os.path.join(FIXTURE_DIR, "github_workflow_list.json")
GITHUB_WORKFLOW_LIST_RETURN = os.path.join(
    FIXTURE_DIR, "github_workflow_list_get_workflows_return.json"
)

GITHUB_EMPTY_WORKFLOW_LIST = os.path.join(
    FIXTURE_DIR, "github_workflow_empty_list.json"
)
GITHUB_EMPTY_WORKFLOW_LIST_RETURN = os.path.join(
    FIXTURE_DIR, "github_workflow_empty_list_get_workflows_return.json"
)

GITHUB_FILTERED_LIST = os.path.join(
    FIXTURE_DIR, "github_workflow_list_filter_workflows_return.json"
)


def test_get_workflows(mocker):
    """Test workflow acquisition."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "G2P_CONFIG_FILE",
        os.path.join(FIXTURE_DIR, "testconfig.ini"),
    )

    with open(GITHUB_WORKFLOW_LIST) as list_file:
        workflow_list_json = json.load(list_file)

    def mock_list_repo_workflows(owner: str, repository: str) -> dict:
        return workflow_list_json

    mock_GhApi = mocker.MagicMock()
    mock_GhApi.actions.list_repo_workflows = mock_list_repo_workflows

    mocker.patch(
        "gerrit_to_platform.github.GhApi",
        return_value=mock_GhApi,
    )
    with open(GITHUB_WORKFLOW_LIST_RETURN) as list_file:
        expected = json.load(list_file)
    actual = get_workflows("example", "repository")
    assert expected == actual

    with open(GITHUB_EMPTY_WORKFLOW_LIST) as list_file:
        workflow_list_json = json.load(list_file)
    with open(GITHUB_EMPTY_WORKFLOW_LIST_RETURN) as list_file:
        expected = json.load(list_file)
    actual = get_workflows("example", "repository")
    assert expected == actual


def test_filter_workflows(mocker):
    """Return workflows that match filter."""
    with open(GITHUB_WORKFLOW_LIST_RETURN) as list_file:
        get_workflows_return = json.load(list_file)
    with open(GITHUB_FILTERED_LIST) as list_file:
        expected = json.load(list_file)

    mocker.patch(
        "gerrit_to_platform.github.get_workflows", return_value=get_workflows_return
    )

    actual = filter_workflows("example", "repository", "verify")
    assert expected == actual
