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

from gerrit_to_platform.config import Platform  # type: ignore
from gerrit_to_platform.helpers import convert_repo_name  # type: ignore

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "fixtures",
)


def test_convert_repo_name(mocker):
    """Convert repository name to platform style."""

    REPLICATION_REMOTES = os.path.join(
        FIXTURE_DIR,
        "replication_remotes_return.json",
    )

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
