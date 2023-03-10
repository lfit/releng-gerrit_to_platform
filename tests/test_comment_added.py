# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Unit tests for comment_added."""

import json
import os
from typing import Any, Callable, Dict, List, Union

from typer.testing import CliRunner

import gerrit_to_platform.comment_added  # type: ignore
from gerrit_to_platform.comment_added import app  # type: ignore
from gerrit_to_platform.config import Platform  # type: ignore

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


CHANGE1 = [
    "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
    "--change-url=https://gerrit.example.org/r/c/example/project/+/1",
    "--change-owner='Foo <foo@example.org>'",
    "--change-owner-username=foo",
    "--project=example/project",
    "--branch=master",
    "--topic=testing",
    "--author='Foo <foo@example.org>'",
    "--author-username=foo",
    "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
    """--comment=Patch Set 1:

recheck""",
    "--Code-Review=0",
]

CHANGE2 = [
    "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
    "--change-url=https://gerrit.example.org/r/c/example/project/+/512",
    "--change-owner='Foo <foo@example.org>'",
    "--change-owner-username=foo",
    "--project=example/project",
    "--branch=master",
    "--topic=testing",
    "--author='Foo <foo@example.org>'",
    "--author-username=foo",
    "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
    """--comment=Patch Set 6:

remerge""",
    "--Code-Review=0",
]

CHANGE1_VERIFY = (
    "Dispatching workflow 'Verify', id 18525370 on "
    + "github:example/example-project for change 1 patch 1"
)
CHANGE1_CHECK_MAIN = (
    "Dispatching workflow 'Check Main', id 17098575 on "
    + "github:example/example-project for change 1 patch 1"
)

CHANGE2_MERGE = (
    "Dispatching workflow 'Merge', id 18525370 on "
    + "github:example/example-project for change 512 patch 6"
)

runner = CliRunner()


def test_app(mocker):
    """Test app options exist."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0

    with open(REPLICATION_REMOTES_GITHUB) as remotes:
        replication_remotes = json.load(remotes)

    mocker.patch(
        "gerrit_to_platform.comment_added.get_replication_remotes",
        return_value=replication_remotes,
    )

    def mock_filter_workflows(
        owner: str, repo: str, search_filter: str
    ) -> List[Dict[str, str]]:
        """Mock of filter_workflows."""
        filter_file = VERIFY_FILTERED_WORKFLOWS
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
        gerrit_to_platform.comment_added,
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
        if platform is Platform.GITHUB:
            return mock_dispatch_workflow

        return None

    mocker.patch.object(
        gerrit_to_platform.comment_added,
        "choose_dispatch",
        mock_choose_dispatch,
    )

    mocker.patch(
        "gerrit_to_platform.comment_added.get_mapping",
        return_value={"recheck": "verify", "remerge": "merge"},
    )

    result = runner.invoke(app, CHANGE1)
    assert result.exit_code == 0
    assert CHANGE1_VERIFY in result.stdout
    assert CHANGE1_CHECK_MAIN in result.stdout
    assert CHANGE2_MERGE not in result.stdout

    result = runner.invoke(app, CHANGE2)
    assert result.exit_code == 0
    assert CHANGE1_VERIFY not in result.stdout
    assert CHANGE1_CHECK_MAIN not in result.stdout
    assert CHANGE2_MERGE in result.stdout

    mocker.patch("gerrit_to_platform.comment_added.get_mapping", return_value=None)
    result = runner.invoke(app, CHANGE1)
    assert result.exit_code == 0
    assert "" == result.stdout

    mocker.patch(
        "gerrit_to_platform.comment_added.get_mapping",
        return_value={"recheck": "verify", "remerge": "merge"},
    )

    with open(REPLICATION_REMOTES_GITLAB) as remotes:
        replication_remotes = json.load(remotes)
    mocker.patch(
        "gerrit_to_platform.comment_added.get_replication_remotes",
        return_value=replication_remotes,
    )
    result = runner.invoke(app, CHANGE1)
    assert result.exit_code == 0
    assert "" == result.stdout
