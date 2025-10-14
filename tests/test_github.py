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
from typing import Dict

from fastcore.net import HTTP404NotFoundError  # type: ignore

import gerrit_to_platform.config  # type: ignore
import gerrit_to_platform.github  # type: ignore
from gerrit_to_platform.config import CONFIG, REPLICATION
from gerrit_to_platform.github import (  # type: ignore
    dispatch_workflow,
    filter_path,
    filter_workflows,
    get_workflows,
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

GITHUB_REQUIRED_FILTERED_LIST = os.path.join(
    FIXTURE_DIR, "github_workflow_list_required_filter_workflows_return.json"
)


def test_dispatch_workflow(mocker):
    """Test workflow triggering."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "CONFIG_FILES",
        MOCK_CONFIG_FILES,
    )

    def mock_create_workflow_dispatch(
        owner: str, repository: str, workflow_id: str, ref: str, inputs: Dict[str, str]
    ):
        """Mock GhApi.actions.create_workflow_dispatch."""
        return {}

    mock_GhApi = mocker.MagicMock()
    mock_GhApi.actions.create_workflow_dispatch = mock_create_workflow_dispatch
    mocker.patch(
        "gerrit_to_platform.github.GhApi",
        return_value=mock_GhApi,
    )

    expected = {}
    actual = dispatch_workflow(
        "example_org", "example_repo", "48166297", "refs/heads/main", {}
    )
    assert expected == actual


def test_get_workflows(mocker):
    """Test workflow acquisition."""
    mocker.patch.object(
        gerrit_to_platform.config,
        "CONFIG_FILES",
        MOCK_CONFIG_FILES,
    )

    with open(GITHUB_WORKFLOW_LIST) as list_file:
        workflow_list_json = json.load(list_file)

    def mock_list_repo_workflows(owner: str, repository: str) -> dict:
        return workflow_list_json

    def mock_list_repo_workflows_exception(owner: str, repository: str) -> dict:
        raise HTTP404NotFoundError(
            mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()
        )

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

    mock_GhApi.actions.list_repo_workflows = mock_list_repo_workflows_exception
    actual = get_workflows("example", "repository")
    assert expected == actual


def test_filter_path(mocker):
    """Test filter_path"""
    # use upper case to validate that filter works case insensitive
    workflow = {"path": ".GITHUB/WORKFLOWS/GERRIT-VERIFY.yaml"}

    expected = True
    actual = filter_path("verify", workflow)
    assert actual == expected

    expected = False
    actual = filter_path("merge", workflow)
    assert actual == expected


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

    with open(GITHUB_REQUIRED_FILTERED_LIST) as list_file:
        expected = json.load(list_file)
    actual = filter_workflows("example", "repository", "verify", True)
    assert expected == actual


def test_filter_workflows_exact_match(mocker):
    """Test exact match filtering to trigger only one specific workflow."""
    # Mock workflow list with multiple verify workflows
    mock_workflows = [
        {
            "name": "Gerrit Verify",
            "path": ".github/workflows/gerrit-verify.yaml",
            "id": 1,
        },
        {
            "name": "Gerrit Packer Verify",
            "path": ".github/workflows/gerrit-packer-verify.yaml",
            "id": 2,
        },
        {
            "name": "Gerrit Shellcheck Verify",
            "path": ".github/workflows/gerrit-shellcheck-verify.yaml",
            "id": 3,
        },
        {
            "name": "Gerrit Merge",
            "path": ".github/workflows/gerrit-merge.yaml",
            "id": 4,
        },
    ]

    mocker.patch("gerrit_to_platform.github.get_workflows", return_value=mock_workflows)

    # Test exact match for verify - should only match "gerrit-verify.yaml"
    actual = filter_workflows("example", "repository", "verify", exact_match=True)
    assert len(actual) == 1
    assert actual[0]["name"] == "Gerrit Verify"
    assert actual[0]["path"] == ".github/workflows/gerrit-verify.yaml"

    # Test exact match for merge - should only match "gerrit-merge.yaml"
    actual = filter_workflows("example", "repository", "merge", exact_match=True)
    assert len(actual) == 1
    assert actual[0]["name"] == "Gerrit Merge"

    # Test substring match (exact_match=False) - should match all verify workflows
    actual = filter_workflows("example", "repository", "verify", exact_match=False)
    assert (
        len(actual) == 3
    )  # gerrit-verify, gerrit-packer-verify, gerrit-shellcheck-verify


def test_filter_workflows_with_job_filter(mocker):
    """Test job_filter parameter to narrow down workflow selection."""
    # Mock workflow list with multiple verify workflows
    mock_workflows = [
        {
            "name": "Gerrit Verify",
            "path": ".github/workflows/gerrit-verify.yaml",
            "id": 1,
        },
        {
            "name": "Gerrit Packer Verify",
            "path": ".github/workflows/gerrit-packer-verify.yaml",
            "id": 2,
        },
        {
            "name": "Gerrit Shellcheck Verify",
            "path": ".github/workflows/gerrit-shellcheck-verify.yaml",
            "id": 3,
        },
        {
            "name": "Gerrit JJB Verify",
            "path": ".github/workflows/gerrit-jjb-verify.yaml",
            "id": 4,
        },
        {
            "name": "Gerrit Merge",
            "path": ".github/workflows/gerrit-merge.yaml",
            "id": 5,
        },
    ]

    mocker.patch("gerrit_to_platform.github.get_workflows", return_value=mock_workflows)

    # Test with job_filter="packer" - should only match packer workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="packer")
    assert len(actual) == 1
    assert actual[0]["name"] == "Gerrit Packer Verify"
    assert actual[0]["path"] == ".github/workflows/gerrit-packer-verify.yaml"

    # Test with job_filter="jjb" - should only match jjb workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="jjb")
    assert len(actual) == 1
    assert actual[0]["name"] == "Gerrit JJB Verify"

    # Test without job_filter - should match all verify workflows (backward compatible)
    actual = filter_workflows("example", "repository", "verify", job_filter=None)
    assert len(actual) == 4  # All verify workflows

    # Test with job_filter that doesn't match anything
    actual = filter_workflows(
        "example", "repository", "verify", job_filter="nonexistent"
    )
    assert len(actual) == 0


def test_filter_workflows_maven_patterns(mocker):
    """Test job_filter with Maven-style workflow naming patterns."""
    # Mock workflows with various Maven-related naming patterns
    mock_workflows = [
        {
            "name": "Gerrit Verify",
            "path": ".github/workflows/gerrit-verify.yaml",
            "id": 1,
        },
        {
            "name": "Gerrit Verify Maven",
            "path": ".github/workflows/gerrit-verify-maven.yaml",
            "id": 2,
        },
        {
            "name": "Gerrit Verify Maven MRI",
            "path": ".github/workflows/gerrit-verify-maven-mri.yaml",
            "id": 3,
        },
        {
            "name": "Gerrit Maven Verify",
            "path": ".github/workflows/gerrit-maven-verify.yaml",
            "id": 4,
        },
        {
            "name": "Gerrit Maven Sonar Verify",
            "path": ".github/workflows/gerrit-maven-sonar-verify.yaml",
            "id": 5,
        },
        {
            "name": "Gerrit Merge",
            "path": ".github/workflows/gerrit-merge.yaml",
            "id": 6,
        },
    ]

    mocker.patch("gerrit_to_platform.github.get_workflows", return_value=mock_workflows)

    # Test 1: Filter for "maven" - should match ALL maven-related workflows
    actual = filter_workflows("example", "repository", "verify", job_filter="maven")
    assert len(actual) == 4
    paths = [w["path"] for w in actual]
    assert ".github/workflows/gerrit-verify-maven.yaml" in paths
    assert ".github/workflows/gerrit-verify-maven-mri.yaml" in paths
    assert ".github/workflows/gerrit-maven-verify.yaml" in paths
    assert ".github/workflows/gerrit-maven-sonar-verify.yaml" in paths
    # Should NOT include generic verify or merge
    assert ".github/workflows/gerrit-verify.yaml" not in paths
    assert ".github/workflows/gerrit-merge.yaml" not in paths

    # Test 2: Filter for "maven-mri" - should match only the specific MRI workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="maven-mri")
    assert len(actual) == 1
    assert actual[0]["path"] == ".github/workflows/gerrit-verify-maven-mri.yaml"

    # Test 3: Filter for "sonar" - should match maven-sonar workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="sonar")
    assert len(actual) == 1
    assert actual[0]["path"] == ".github/workflows/gerrit-maven-sonar-verify.yaml"

    # Test 4: No filter - should match all verify workflows
    actual = filter_workflows("example", "repository", "verify", job_filter=None)
    assert len(actual) == 5  # All verify workflows
    assert ".github/workflows/gerrit-merge.yaml" not in [w["path"] for w in actual]


def test_filter_workflows_complex_patterns(mocker):
    """Test job_filter with complex real-world workflow patterns."""
    mock_workflows = [
        # Generic workflows
        {
            "name": "Gerrit Verify",
            "path": ".github/workflows/gerrit-verify.yaml",
            "id": 1,
        },
        {
            "name": "Gerrit Merge",
            "path": ".github/workflows/gerrit-merge.yaml",
            "id": 2,
        },
        # Packer workflows
        {
            "name": "Gerrit Packer Verify",
            "path": ".github/workflows/gerrit-packer-verify.yaml",
            "id": 3,
        },
        {
            "name": "Gerrit Verify Packer",
            "path": ".github/workflows/gerrit-verify-packer.yaml",
            "id": 4,
        },
        # Maven workflows with various patterns
        {
            "name": "Gerrit Maven Verify",
            "path": ".github/workflows/gerrit-maven-verify.yaml",
            "id": 5,
        },
        {
            "name": "Gerrit Verify Maven CLM",
            "path": ".github/workflows/gerrit-verify-maven-clm.yaml",
            "id": 6,
        },
        {
            "name": "Gerrit Maven Sonar Verify",
            "path": ".github/workflows/gerrit-maven-sonar-verify.yaml",
            "id": 7,
        },
        # Python workflows
        {
            "name": "Gerrit Python Verify",
            "path": ".github/workflows/gerrit-python-verify.yaml",
            "id": 8,
        },
        {
            "name": "Gerrit Verify Python Tox",
            "path": ".github/workflows/gerrit-verify-python-tox.yaml",
            "id": 9,
        },
        # JJB workflows
        {
            "name": "Gerrit JJB Verify",
            "path": ".github/workflows/gerrit-jjb-verify.yaml",
            "id": 10,
        },
        {
            "name": "Gerrit Verify JJB Merge",
            "path": ".github/workflows/gerrit-verify-jjb-merge.yaml",
            "id": 11,
        },
    ]

    mocker.patch("gerrit_to_platform.github.get_workflows", return_value=mock_workflows)

    # Test 1: Packer filter matches both naming patterns
    actual = filter_workflows("example", "repository", "verify", job_filter="packer")
    assert len(actual) == 2
    paths = [w["path"] for w in actual]
    assert ".github/workflows/gerrit-packer-verify.yaml" in paths
    assert ".github/workflows/gerrit-verify-packer.yaml" in paths

    # Test 2: Maven filter matches all maven workflows
    actual = filter_workflows("example", "repository", "verify", job_filter="maven")
    assert len(actual) == 3
    paths = [w["path"] for w in actual]
    assert ".github/workflows/gerrit-maven-verify.yaml" in paths
    assert ".github/workflows/gerrit-verify-maven-clm.yaml" in paths
    assert ".github/workflows/gerrit-maven-sonar-verify.yaml" in paths

    # Test 3: Maven-CLM filter matches specific workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="maven-clm")
    assert len(actual) == 1
    assert actual[0]["path"] == ".github/workflows/gerrit-verify-maven-clm.yaml"

    # Test 4: Python filter matches all python workflows
    actual = filter_workflows("example", "repository", "verify", job_filter="python")
    assert len(actual) == 2
    paths = [w["path"] for w in actual]
    assert ".github/workflows/gerrit-python-verify.yaml" in paths
    assert ".github/workflows/gerrit-verify-python-tox.yaml" in paths

    # Test 5: Tox filter matches specific python-tox workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="tox")
    assert len(actual) == 1
    assert actual[0]["path"] == ".github/workflows/gerrit-verify-python-tox.yaml"

    # Test 6: JJB filter matches both jjb workflows
    actual = filter_workflows("example", "repository", "verify", job_filter="jjb")
    assert len(actual) == 2
    paths = [w["path"] for w in actual]
    assert ".github/workflows/gerrit-jjb-verify.yaml" in paths
    assert ".github/workflows/gerrit-verify-jjb-merge.yaml" in paths

    # Test 7: No filter matches ALL verify workflows (not merge)
    actual = filter_workflows("example", "repository", "verify", job_filter=None)
    assert len(actual) == 10  # All verify workflows
    paths = [w["path"] for w in actual]
    assert ".github/workflows/gerrit-merge.yaml" not in paths


def test_filter_workflows_case_insensitive(mocker):
    """Test that job_filter is case-insensitive."""
    mock_workflows = [
        {
            "name": "Gerrit Maven Verify",
            "path": ".github/workflows/gerrit-maven-verify.yaml",
            "id": 1,
        },
        {
            "name": "Gerrit PACKER Verify",
            "path": ".github/workflows/gerrit-PACKER-verify.yaml",
            "id": 2,
        },
        {
            "name": "Gerrit Python Verify",
            "path": ".github/workflows/gerrit-Python-verify.yaml",
            "id": 3,
        },
    ]

    mocker.patch("gerrit_to_platform.github.get_workflows", return_value=mock_workflows)

    # Test lowercase filter matches mixed case workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="maven")
    assert len(actual) == 1

    # Test uppercase filter matches uppercase workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="PACKER")
    assert len(actual) == 1

    # Test mixed case filter matches mixed case workflow
    actual = filter_workflows("example", "repository", "verify", job_filter="Python")
    assert len(actual) == 1

    # Test all case variations match
    for filter_val in ["maven", "MAVEN", "Maven", "MaVeN"]:
        actual = filter_workflows(
            "example", "repository", "verify", job_filter=filter_val
        )
        assert len(actual) == 1


def test_filter_workflows_required_with_job_filter(mocker):
    """Test that job_filter works with required workflows."""
    mock_workflows = [
        {
            "name": "Gerrit Required Verify",
            "path": ".github/workflows/gerrit-required-verify.yaml",
            "id": 1,
        },
        {
            "name": "Gerrit Required Maven Verify",
            "path": ".github/workflows/gerrit-required-maven-verify.yaml",
            "id": 2,
        },
        {
            "name": "Gerrit Maven Verify",
            "path": ".github/workflows/gerrit-maven-verify.yaml",
            "id": 3,
        },
        {
            "name": "Gerrit Required Packer Verify",
            "path": ".github/workflows/gerrit-required-packer-verify.yaml",
            "id": 4,
        },
    ]

    mocker.patch("gerrit_to_platform.github.get_workflows", return_value=mock_workflows)

    # Test 1: Get required workflows with maven filter
    actual = filter_workflows(
        "example", "repository", "verify", search_required=True, job_filter="maven"
    )
    assert len(actual) == 1
    assert actual[0]["path"] == ".github/workflows/gerrit-required-maven-verify.yaml"

    # Test 2: Get non-required workflows with maven filter
    actual = filter_workflows(
        "example", "repository", "verify", search_required=False, job_filter="maven"
    )
    assert len(actual) == 1
    assert actual[0]["path"] == ".github/workflows/gerrit-maven-verify.yaml"

    # Test 3: Get all required workflows (no job filter)
    actual = filter_workflows(
        "example", "repository", "verify", search_required=True, job_filter=None
    )
    assert len(actual) == 3
    paths = [w["path"] for w in actual]
    assert ".github/workflows/gerrit-required-verify.yaml" in paths
    assert ".github/workflows/gerrit-required-maven-verify.yaml" in paths
    assert ".github/workflows/gerrit-required-packer-verify.yaml" in paths
