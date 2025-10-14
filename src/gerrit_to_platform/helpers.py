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
from typing import Callable, Dict, Optional, Union

import gerrit_to_platform.github as github
from gerrit_to_platform.config import (
    Platform,
    ReplicationRemotes,
    get_boolean_setting,
    get_project_workflow_filter,
    get_replication_remotes,
)


def choose_dispatch(platform: Platform) -> Union[Callable, None]:
    """
    Choose platform job dispatcher.

    Args:
        platform (Platform): the platform that the dispatch is being looked up
            for

    Returns:
        Callable: The appropriate callable matching the dispatch_worfklow call
            signature for the platform
        None: If no dispatch_workflow is defined for the platform passed in a
            None is returned
    """
    if platform.value == "github":
        return github.dispatch_workflow

    return None


def choose_filter_workflows(platform: Platform) -> Union[Callable, None]:
    """
    Choose platform workflow filter.

    Args:
        platform (Platform): the platform that the filter_workflows is being
            looked up for


    Returns:
        Callable: The appropriate callable matching the filter_workflows call
            signature for the platform
        None: If no filter_workflows is defined for the platform passed in a
            None is returned
    """
    if platform.value == "github":
        return github.filter_workflows

    return None


def convert_repo_name(
    remotes: ReplicationRemotes, platform: Platform, remote: str, repository: str
) -> str:
    """
    Convert the repository name based on the remotenamestyle of the target
    platform/owner.

    Args:
        remotes (ReplicationRemotes): object containing the defined remotes
            styles
        platform (Platform): what platform is the conversion happening against
        remote (str): The specific remote that is being worked on
        repository (str): The repository name that needs conversion

    Returns:
        str: The repository name converted to the appropriate flattening for
            the target remote
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
    """
    Find relevant workflows and dispatch them.

    Args:
        project (str): the project repository name
        workflow_filter (str): the filter for the workflow names
        inputs (Dict[str, str]): key / value pair dictionary for inputs to be
            passed to the target workflow dispatch
    """
    remotes = get_replication_remotes()

    # Check if exact workflow matching is enabled
    exact_match = get_boolean_setting("workflow", "exact_match", fallback=False)
    
    # Get project-specific workflow filter (if configured)
    job_filter = get_project_workflow_filter(project, workflow_filter)

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
            workflows = filter_workflows(
                owner, repo, workflow_filter, False, exact_match, job_filter
            )

            for workflow in workflows:
                print(
                    f"Dispatching workflow '{workflow['name']}', "
                    + f"id {workflow['id']} on "
                    + f"{platform.value}:{owner}/{repo} for change "
                    + f"{inputs['GERRIT_CHANGE_NUMBER']} patch "
                    + inputs["GERRIT_PATCHSET_NUMBER"]
                )
                try:
                    dispatcher(
                        owner,
                        repo,
                        workflow["id"],
                        f"refs/heads/{inputs['GERRIT_BRANCH']}",
                        inputs,
                    )
                except Exception as e:
                    print(f"Failed to dispatch workflow: {e}")

            magic_repo = get_magic_repo(platform)
            if magic_repo:
                required_workflows = filter_workflows(
                    owner, magic_repo, workflow_filter, True, exact_match, job_filter
                )

                inputs["TARGET_REPO"] = f"{owner}/{repo}"

                for workflow in required_workflows:
                    print(
                        f"Dispatching required workflow '{workflow['name']}', "
                        + f"id {workflow['id']} on "
                        + f"{platform.value}:{owner}/{magic_repo} for change "
                        + f"{inputs['GERRIT_CHANGE_NUMBER']} patch "
                        + f"{inputs['GERRIT_PATCHSET_NUMBER']} against "
                        + f"{platform.value}:{owner}/{repo}"
                    )
                    try:
                        dispatcher(
                            owner,
                            magic_repo,
                            workflow["id"],
                            "refs/heads/main",
                            inputs,
                        )
                    except Exception as e:
                        print(f"Failed to dispatch workflow: {e}")


def get_change_id(change: str) -> str:
    """
    Get the Gerrit change_id from an hook event.

    Args:
        change (str): the change string passed to event handlers

    Returns:
        str: The extracted Gerrit change_id from the event hook
    """
    change_id_regex = r".*~.*~(I.*)"
    return re.findall(change_id_regex, change)[0]


def get_change_number(change_url: str) -> str:
    """
    Get the Gerrit change_number

    Args:
        change_url (str): the url to the specific change passed by the Gerrit
            event

    Returns:
        str: The change number as string extracted from the url
    """
    change_number_regex = r"^.*/\+/(\d+)$"
    return re.findall(change_number_regex, change_url)[0]


def get_change_refspec(change_number: str, patchset: str) -> str:
    """
    Return the change refspec from the change number (str) and patch number

    Args:
        change_number (str): The change number to work with
        patchset (str): The patchset number to work with

    Returns:
        str: The git refspec pointing to the hidden ref for the specific change
            and patchset
    """
    if int(change_number) < 100:
        ref_shard = change_number.zfill(2)
    else:
        ref_shard = change_number[len(change_number) - 2 :]
    return f"refs/changes/{ref_shard}/{change_number}/{patchset}"


def get_magic_repo(platform: Platform) -> Optional[str]:
    """
    Get the "magic" repo for a given Platform used to store organization wide
    required workflows

    Args:
        platform (Platform): Platform to lookup magic repo for

    Returns:
        Optional[str]: The magic repo name or None if not defined for the
            platform
    """

    if platform == Platform.GITHUB:
        return ".github"

    return None
