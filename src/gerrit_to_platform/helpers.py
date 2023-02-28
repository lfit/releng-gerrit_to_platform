# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Common helper functions."""

from typing import Callable, Union

import gerrit_to_platform.github as github
from gerrit_to_platform.config import Platform, ReplicationRemotes


def choose_dispatch(platform: Platform) -> Union[Callable, None]:
    """Choose platform job dispatcher."""
    if platform.value == "github":
        return github.dispatch_workflow

    return None


def choose_filter_workflows(platform: Platform) -> Union[Callable, None]:
    """Choose platform workflow filter."""
    if platform.value == "github":
        return github.filter_workflows

    return None


def convert_repo_name(
    remotes: ReplicationRemotes, platform: Platform, remote: str, repository: str
) -> str:
    """
    Convert the repository name based on the remotenamestyle of the target
    platform/owner.
    """

    remote_styles = {
        "dash": "-",
        "underscore": "_",
        "slash": "/",
    }

    target_style = remotes[platform.value][remote]["remotenamestyle"]
    converted_repository = repository.replace("/", remote_styles[target_style])

    return converted_repository
