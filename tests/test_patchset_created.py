# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Unit tests for patchset_created."""

from typing import Dict

from typer.testing import CliRunner

import gerrit_to_platform.helpers  # type: ignore
import gerrit_to_platform.patchset_created  # type: ignore
from gerrit_to_platform.patchset_created import app  # type: ignore

CHANGE1 = [
    "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
    "--kind=REWORK",
    "--change-url=https://gerrit.example.org/r/c/example/project/+/1",
    "--change-owner='Foo <foo@example.org>'",
    "--change-owner-username=foo",
    "--project=example/project",
    "--branch=master",
    "--topic=testing",
    "--uploader=Foo <foo@example.org>",
    "--uploader-username=foo",
    "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
    "--patchset=1",
]


runner = CliRunner()


def test_app(mocker):
    """Test app options exist."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0

    def mock_find_and_dispatch(
        project: str, workflow_filter: str, inputs: Dict[str, str]
    ):
        """Mock find_and_dispatch helper."""
        print("Dispatched")

    mocker.patch.object(
        gerrit_to_platform.patchset_created,
        "find_and_dispatch",
        mock_find_and_dispatch,
    )

    result = runner.invoke(app, CHANGE1)
    assert result.exit_code == 0
    assert "Dispatched" in result.stdout
