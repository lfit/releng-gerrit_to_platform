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

from typing import Dict

from typer.testing import CliRunner

import gerrit_to_platform.comment_added  # type: ignore
from gerrit_to_platform.comment_added import app  # type: ignore

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

CHANGE1_VERIFY = "Dispatched verify for patchset 1"
CHANGE2_MERGE = "Dispatched merge for patchset 6"

runner = CliRunner()


def test_app(mocker):
    """Test app options exist."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0

    def mock_find_and_dispatch(
        project: str, workflow_filter: str, inputs: Dict[str, str]
    ):
        """Mock find_and_dispatch helper."""
        print(
            f"Dispatched {workflow_filter} for patchset {inputs['GERRIT_PATCHSET_NUMBER']}"
        )

    mocker.patch.object(
        gerrit_to_platform.comment_added,
        "find_and_dispatch",
        mock_find_and_dispatch,
    )

    result = runner.invoke(app, CHANGE1)
    assert result.exit_code == 0
    assert CHANGE1_VERIFY in result.stdout
    assert CHANGE2_MERGE not in result.stdout

    result = runner.invoke(app, CHANGE2)
    assert result.exit_code == 0
    assert CHANGE1_VERIFY not in result.stdout
    assert CHANGE2_MERGE in result.stdout

    mocker.patch("gerrit_to_platform.comment_added.get_mapping", return_value=None)
    result = runner.invoke(app, CHANGE1)
    assert result.exit_code == 0
    assert "" == result.stdout
