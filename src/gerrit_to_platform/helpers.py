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

import re
from typing import Callable, Dict, Union

import gerrit_to_platform.github as github
from gerrit_to_platform.config import (
    Platform,
    ReplicationRemotes,
    get_replication_remotes,
)


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


def find_and_dispatch(project: str, workflow_filter: str, inputs: Dict[str, str]):
    """Find relevant workflows and dispatch them."""
    remotes = get_replication_remotes()

    for platform in Platform:
        if platform.value not in remotes:
            continue

        dispatcher = choose_dispatch(platform)
        filter_workflows = choose_filter_workflows(platform)

        if dispatcher is None or filter_workflows is None:
            continue

        for remote in remotes[platform.value]:
            owner = remotes[platform.value][remote]["owner"]
            repo = convert_repo_name(remotes, platform, remote, project)
            workflows = filter_workflows(owner, repo, workflow_filter)

            for workflow in workflows:
                print(
                    f"Dispatching workflow '{workflow['name']}', "
                    + f"id {workflow['id']} on "
                    + f"{platform.value}:{owner}/{repo} for change "
                    + f"{inputs['GERRIT_CHANGE_NUMBER']} patch "
                    + inputs["GERRIT_PATCHSET_NUMBER"]
                )
                dispatcher(
                    owner,
                    repo,
                    workflow["id"],
                    f"refs/heads/{inputs['GERRIT_BRANCH']}",
                    inputs,
                )


def filter_path(search_filter: str, workflow: Dict[str, str]) -> bool:
    """
    Case insensitive path filter for use in lambda filters.

    Returns True if search_filter matches in workflow["path"]
    """
    path = workflow["path"].lower()
    if path.find(search_filter.lower()) >= 0:
        return True

    return False


def get_change_id(change: str) -> str:
    """Get the Gerrit change_id from an hook event."""
    change_id_regex = r".*~.*~(I.*)"
    return re.findall(change_id_regex, change)[0]


def get_change_number(change_url: str) -> str:
    """Get the Gerrit change_number"""
    change_number_regex = r"^.*/\+/(\d+)$"
    return re.findall(change_number_regex, change_url)[0]


def get_change_refspec(change_number: str, patchset: str) -> str:
    """Return the change refspec from the change number (str) and patch number"""
    if int(change_number) < 100:
        ref_shard = change_number.zfill(2)
    else:
        ref_shard = change_number[len(change_number) - 2 :]
    return f"refs/changes/{ref_shard}/{change_number}/{patchset}"
