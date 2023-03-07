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

from typer.testing import CliRunner

from gerrit_to_platform.comment_added import app  # type: ignore

runner = CliRunner()


def test_app(mocker):
    """Test app options exist."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
