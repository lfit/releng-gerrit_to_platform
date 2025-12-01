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
from typing import Any, Callable, Dict, List, Union

import gerrit_to_platform.github as github  # type: ignore
import gerrit_to_platform.helpers  # type: ignore
from gerrit_to_platform.config import Platform  # type: ignore
from gerrit_to_platform.helpers import (  # type: ignore
    build_gerrit_json,
    choose_dispatch,
    choose_filter_workflows,
    convert_repo_name,
    find_and_dispatch,
    get_change_id,
    get_change_number,
    get_change_refspec,
    get_magic_repo,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "fixtures",
)

VERIFY_FILTERED_WORKFLOWS = os.path.join(
    FIXTURE_DIR, "github_workflow_list_filter_workflows_return.json"
)

MERGE_FILTERED_WORKFLOWS = os.path.join(
    FIXTURE_DIR, "github_workflow_list_filter_workflows_return_merge.json"
)

REPLICATION_REMOTES = os.path.join(FIXTURE_DIR, "replication_remotes_return.json")

REPLICATION_REMOTES_GITHUB = os.path.join(
    FIXTURE_DIR, "limited_replication_remotes_return_github.json"
)

REPLICATION_REMOTES_GITLAB = os.path.join(
    FIXTURE_DIR, "limited_replication_remotes_return_gitlab.json"
)

REQUIRED_VERIFY_FILTERED_WORKFLOWS = os.path.join(
    FIXTURE_DIR, "github_workflow_list_required_filter_workflows_return.json"
)

PATCH1_GERRIT_VERIFY = (
    "Dispatching workflow 'Gerrit Verify', id 20937807 on "
    + "github:example/example-project for change 1 patch 1"
)
PATCH1_VERIFY = (
    "Dispatching workflow 'Verify', id 18525370 on "
    + "github:example/example-project for change 1 patch 1"
)
PATCH1_REQUIRED_VERIFY = (
    "Dispatching required workflow 'Required Gerrit Verify', id 20937808 on "
    + "github:example/.github for change 1 patch 1 against "
    + "github:example/example-project"
)
PATCH1_CHECK_MAIN = (
    "Dispatching workflow 'Check Main', id 17098575 on "
    + "github:example/example-project for change 1 patch 1"
)
CHANGE2_MERGE = (
    "Dispatching workflow 'Gerrit Merge', id 18525370 on "
    + "github:example/example-project for change 1 patch 1"
)


def test_choose_dispatch(mocker):
    """Test choose_dispatch."""
    expected = github.dispatch_workflow
    actual = choose_dispatch(Platform.GITHUB)
    assert expected == actual

    expected = None
    actual = choose_dispatch(Platform.GITLAB)
    assert expected == actual


def test_choose_filter_workflows(mocker):
    """Test choose_filter_workflows."""
    expected = github.filter_workflows
    actual = choose_filter_workflows(Platform.GITHUB)
    assert expected == actual

    expected = None
    actual = choose_filter_workflows(Platform.GITLAB)
    assert expected == actual


def test_convert_repo_name(mocker):
    """Convert repository name to platform style."""

    with open(REPLICATION_REMOTES) as remotes:
        replication_remotes = json.load(remotes)

    expected = "foo-bar"
    actual = convert_repo_name(
        replication_remotes, Platform.GITHUB, "github", "foo/bar"
    )
    assert expected == actual
    expected = "foo_bar"
    actual = convert_repo_name(
        replication_remotes, Platform.GITHUB, "github-other", "foo/bar"
    )
    assert expected == actual
    expected = "foo/bar"
    actual = convert_repo_name(
        replication_remotes, Platform.GITLAB, "gitlab", "foo/bar"
    )
    assert expected == actual


def test_find_and_dispatch(mocker, capfd):
    """Test the find_and_dispatch helper."""
    inputs = {
        "GERRIT_BRANCH": "main",
        "GERRIT_CHANGE_ID": "Ichange_id",
        "GERRIT_CHANGE_NUMBER": "1",
        "GERRIT_CHANGE_URL": "https://foo.bar/r/c/example/+/1",
        "GERRIT_EVENT_TYPE": "test",
        "GERRIT_PATCHSET_NUMBER": "1",
        "GERRIT_PATCHSET_REVISION": "foo",
        "GERRIT_PROJECT": "example/project",
        "GERRIT_REFSPEC": "refs/heads/main",
    }

    with open(REPLICATION_REMOTES_GITHUB) as remotes:
        replication_remotes = json.load(remotes)

    mocker.patch(
        "gerrit_to_platform.helpers.get_replication_remotes",
        return_value=replication_remotes,
    )

    def mock_filter_workflows(
        owner: str, repo: str, search_filter: str, search_required: bool = False
    ) -> List[Dict[str, str]]:
        """Mock of filter_workflows."""
        filter_file = VERIFY_FILTERED_WORKFLOWS

        if search_required:
            filter_file = REQUIRED_VERIFY_FILTERED_WORKFLOWS

        if search_filter == "merge":
            filter_file = MERGE_FILTERED_WORKFLOWS

        with open(filter_file) as workflows:
            return json.load(workflows)

    def mock_choose_filter_workflows(platform: Platform) -> Union[Callable, None]:
        """Mock of choose_filter_workflows."""
        if platform == Platform.GITHUB:
            return mock_filter_workflows

        return None

    mocker.patch.object(
        gerrit_to_platform.helpers,
        "choose_filter_workflows",
        mock_choose_filter_workflows,
    )

    def mock_dispatch_workflow(
        owner: str, repository: str, workflow_id: str, ref: str, inputs: Dict[str, str]
    ) -> Any:
        """Mock of dispach_workflow"""
        return {}

    def mock_choose_dispatch(platform: Platform) -> Union[Callable, None]:
        """Mock of choose_dispacth."""
        if platform == Platform.GITHUB:
            return mock_dispatch_workflow

        return None

    mocker.patch.object(
        gerrit_to_platform.helpers,
        "choose_dispatch",
        mock_choose_dispatch,
    )

    result = find_and_dispatch("example-project", "verify", inputs)
    actual = capfd.readouterr().out
    
    # Verify gerrit_json was added to inputs
    assert "gerrit_json" in inputs
    gerrit_json = json.loads(inputs["gerrit_json"])
    assert gerrit_json["branch"] == "main"
    assert gerrit_json["change_number"] == "1"
    assert gerrit_json["event_type"] == "test"
    assert PATCH1_GERRIT_VERIFY in actual
    assert PATCH1_VERIFY not in actual
    assert PATCH1_REQUIRED_VERIFY in actual
    assert PATCH1_CHECK_MAIN not in actual

    find_and_dispatch("example-project", "merge", inputs)
    actual = capfd.readouterr().out
    assert CHANGE2_MERGE in actual

    with open(REPLICATION_REMOTES_GITLAB) as remotes:
        replication_remotes = json.load(remotes)
    mocker.patch(
        "gerrit_to_platform.helpers.get_replication_remotes",
        return_value=replication_remotes,
    )
    find_and_dispatch("example-project", "verify", inputs)
    actual = capfd.readouterr().out
    assert PATCH1_GERRIT_VERIFY not in actual
    assert PATCH1_VERIFY not in actual
    assert PATCH1_REQUIRED_VERIFY not in actual
    assert PATCH1_CHECK_MAIN not in actual
    assert actual == ""


def test_get_change_id(mocker):
    """Test get_change_id"""
    expected = "Ibaz"
    actual = get_change_id("foo~bar~Ibaz")
    assert expected == actual


def test_get_change_number(mocker):
    """Test get_change_number"""
    expected = "71001"
    actual = get_change_number("https://example.org.org/r/c/example/+/71001")
    assert expected == actual


def test_get_change_refspec(mocker):
    """Test get_change_refspec"""
    expected = "refs/changes/01/1/1"
    actual = get_change_refspec("1", "1")
    assert expected == actual

    expected = "refs/changes/01/1/2"
    actual = get_change_refspec("1", "2")
    assert expected == actual

    expected = "refs/changes/02/202/1"
    actual = get_change_refspec("202", "1")
    assert expected == actual


def test_get_magic_repo(mocker):
    """Test get_magic_repo"""
    expected = ".github"
    actual = get_magic_repo(Platform.GITHUB)
    assert expected == actual

    expected = None
    actual = get_magic_repo(Platform.GITLAB)
    assert expected == actual


def test_build_gerrit_json(mocker):
    """Test build_gerrit_json"""
    inputs = {
        "GERRIT_BRANCH": "master",
        "GERRIT_CHANGE_ID": "I1234567890abcdef1234567890abcdef12345678",
        "GERRIT_CHANGE_NUMBER": "12345",
        "GERRIT_CHANGE_URL": "https://gerrit.example.com/r/c/test-project/+/12345",
        "GERRIT_EVENT_TYPE": "patchset-created",
        "GERRIT_PATCHSET_NUMBER": "3",
        "GERRIT_PATCHSET_REVISION": "abcdef1234567890abcdef1234567890abcdef12",
        "GERRIT_PROJECT": "test-project",
        "GERRIT_REFSPEC": "refs/changes/45/12345/3",
    }

    actual_json = build_gerrit_json(inputs)
    actual = json.loads(actual_json)

    # Verify all required fields are present
    assert actual["branch"] == "master"
    assert actual["change_id"] == "I1234567890abcdef1234567890abcdef12345678"
    assert actual["change_number"] == "12345"
    assert actual["change_url"] == "https://gerrit.example.com/r/c/test-project/+/12345"
    assert actual["event_type"] == "patchset-created"
    assert actual["patchset_number"] == "3"
    assert actual["patchset_revision"] == "abcdef1234567890abcdef1234567890abcdef12"
    assert actual["project"] == "test-project"
    assert actual["refspec"] == "refs/changes/45/12345/3"
    
    # Verify comment is not present when not in inputs
    assert "comment" not in actual


def test_build_gerrit_json_with_comment(mocker):
    """Test build_gerrit_json with optional comment field"""
    inputs = {
        "GERRIT_BRANCH": "main",
        "GERRIT_CHANGE_ID": "Iabcdef",
        "GERRIT_CHANGE_NUMBER": "67890",
        "GERRIT_CHANGE_URL": "https://gerrit.example.com/r/c/test/+/67890",
        "GERRIT_EVENT_TYPE": "comment-added",
        "GERRIT_PATCHSET_NUMBER": "1",
        "GERRIT_PATCHSET_REVISION": "fedcba0987654321fedcba0987654321fedcba09",
        "GERRIT_PROJECT": "test",
        "GERRIT_REFSPEC": "refs/changes/90/67890/1",
        "GERRIT_COMMENT": "gha-run test-workflow param1=value1",
    }

    actual_json = build_gerrit_json(inputs)
    actual = json.loads(actual_json)

    # Verify comment field is present
    assert actual["comment"] == "gha-run test-workflow param1=value1"
    assert actual["event_type"] == "comment-added"


def test_build_gerrit_json_is_compact(mocker):
    """Test that build_gerrit_json produces compact JSON without spaces"""
    inputs = {
        "GERRIT_BRANCH": "main",
        "GERRIT_CHANGE_ID": "I123",
        "GERRIT_CHANGE_NUMBER": "1",
        "GERRIT_CHANGE_URL": "https://example.com/1",
        "GERRIT_EVENT_TYPE": "patchset-created",
        "GERRIT_PATCHSET_NUMBER": "1",
        "GERRIT_PATCHSET_REVISION": "abc123",
        "GERRIT_PROJECT": "proj",
        "GERRIT_REFSPEC": "refs/changes/01/1/1",
    }

    actual_json = build_gerrit_json(inputs)
    
    # Verify no spaces after colons or commas (compact JSON)
    assert ": " not in actual_json
    assert ", " not in actual_json
    
    # Verify it's still valid JSON
    parsed = json.loads(actual_json)
    assert parsed["branch"] == "main"
