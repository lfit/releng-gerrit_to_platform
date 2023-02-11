# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
from typer.testing import CliRunner

from gerrit_to_platform.cli import app

runner = CliRunner()


def test_app():
    """Test all app options exist."""
    result = runner.invoke(app, ["patchset-created", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["comment-added", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["change-merged", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["change-abandoned", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["change-deleted", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["change-restored", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["ref-updated", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["project-created", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["reviewer-added", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["reviewer-deleted", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["topic-changed", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["hashtags-changed", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["cla-signed", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["main", "--help"])
    assert result.exit_code == 2
