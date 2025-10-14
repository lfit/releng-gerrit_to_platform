# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Github connection module."""

from typing import Any, Dict, List, Optional

from fastcore.net import HTTP404NotFoundError  # type: ignore
from ghapi.all import GhApi  # type: ignore

from gerrit_to_platform.config import get_setting


def dispatch_workflow(
    owner: str, repository: str, workflow_id: str, ref: str, inputs: Dict[str, str]
) -> Any:
    """
    Trigger target workflow on GitHub.

    Args:
        owner (str): GitHub owner (user or organization)
        repository (str): target repository
        workflow_id (str): ID of the workflow to trigger
        ref (str): the commit ref to trigger with
        inputs (Dict[str, str]): dictionary of key / value pairs to pass as
            inputs to the workflow
    """
    github_token = get_setting("github.com", "token")
    api = GhApi(token=github_token)

    return api.actions.create_workflow_dispatch(
        owner, repository, workflow_id, ref, inputs
    )


def filter_path(search_filter: str, workflow: Dict[str, str]) -> bool:
    """
    Case insensitive path filter for use in lambda filters.

    Args:
        search_filter (str): string to search workflow file names for
        workflow (Dict[str, str]): dictionary containing all data related to
            the workflow being evaluated

    Returns:
        bool: True if search_filter matches in workflow["path"], False otherwise
    """
    path = workflow["path"].lower()
    if path.find(search_filter.lower()) >= 0:
        return True

    return False


def filter_workflows(
    owner: str,
    repository: str,
    search_filter: str,
    search_required: bool = False,
    exact_match: bool = False,
    job_filter: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Return a case insensitive filtered list of workflows.

    All workflows must meet the basic filtering of containing the search_filter
    in the name as well as "gerrit" in the name.

    If search_required is true, then the list will contiain all workflows that
    contain "required" in the name

    If search_required is false (the default), then the list will _exclude_ all
    workflows that contain "required" in the name.

    If exact_match is true, the workflow path must match exactly "gerrit-<search_filter>.yaml"
    or "gerrit-<search_filter>.yml", preventing multiple workflows from being triggered.

    If job_filter is provided, adds an additional filter level to match only workflows
    containing the job_filter string. This allows triggering specific workflows like
    "gerrit-packer-verify.yaml" when job_filter="packer". If job_filter is None,
    all matching workflows are returned (backward compatible).

    Args:
        owner (str): GitHub owner (entity or organization)
        repository (str): target repository
        search_filter (str): the substring to search for in workflow filenames
        search_required (bool): if workflows with "required" in the filename
            are to be returned. If false, then required workflows will be
            filtered out, if true only required workflows will be returned.
        exact_match (bool): if True, only match workflows with exact pattern
            "gerrit-<search_filter>.yaml" or "gerrit-<search_filter>.yml".
            This prevents multiple workflows from being triggered.
        job_filter (Optional[str]): additional filter string to narrow workflow selection.
            If provided, only workflows containing this string are returned.
            If None, all workflows matching other criteria are returned.

    Returns:
        List[Dict[str, str]]: list of dictionaries containing all workflows
            that meet the search criteria of having "gerrit" in the name, the
            search_filter substring, optional job_filter, and either required
            or not required according to the search_required argument.
    """
    workflows = get_workflows(owner, repository)
    filtered_workflows: List[Dict[str, str]] = []

    if exact_match:
        # Exact match mode: only match "gerrit-<search_filter>.yaml" or ".yml"
        exact_patterns = [
            f"gerrit-{search_filter}.yaml",
            f"gerrit-{search_filter}.yml",
        ]
        if search_required:
            exact_patterns.extend(
                [
                    f"gerrit-required-{search_filter}.yaml",
                    f"gerrit-required-{search_filter}.yml",
                    f"gerrit-{search_filter}-required.yaml",
                    f"gerrit-{search_filter}-required.yml",
                ]
            )

        for workflow in workflows:
            path_lower = workflow["path"].lower()
            filename = path_lower.split("/")[-1]  # Get just the filename
            if filename in exact_patterns:
                filtered_workflows.append(workflow)
    else:
        # Original substring matching behavior
        filtered_workflows = list(
            filter(lambda workflow: filter_path(search_filter, workflow), workflows)
        )
        filtered_workflows = list(
            filter(lambda workflow: filter_path("gerrit", workflow), filtered_workflows)
        )

        # Apply job_filter if provided (3rd level filter)
        if job_filter:
            filtered_workflows = list(
                filter(
                    lambda workflow: filter_path(job_filter, workflow),
                    filtered_workflows,
                )
            )

        if search_required:
            filtered_workflows = list(
                filter(
                    lambda workflow: filter_path("required", workflow),
                    filtered_workflows,
                )
            )
        else:
            filtered_workflows = list(
                filter(
                    lambda workflow: not filter_path("required", workflow),
                    filtered_workflows,
                )
            )

    return filtered_workflows


def get_workflows(owner: str, repository: str) -> List[Dict[str, str]]:
    """
    Get all active workflows for specific repository.

    Args:
        owner (str): GitHub owner (entity or organization)
        repository (str): target repository

    Returns:
        List[Dict[str, str]]: list of dictionaries containing data related to
            active workflows in the target repository.
    """
    github_token = get_setting("github.com", "token")
    api = GhApi(token=github_token)

    try:
        workflows = api.actions.list_repo_workflows(owner, repository)["workflows"]
    except HTTP404NotFoundError:
        return []

    workflows = [workflow for workflow in workflows if workflow["state"] == "active"]
    key_ids = [
        "node_id",
        "created_at",
        "updated_at",
        "url",
        "html_url",
        "badge_url",
        "state",
    ]
    for workflow in workflows:
        for del_key in key_ids:
            del workflow[del_key]
    return workflows
