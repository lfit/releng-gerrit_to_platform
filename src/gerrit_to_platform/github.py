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

from typing import Any, Dict, List

from fastcore.net import HTTP404NotFoundError  # type: ignore
from ghapi.all import GhApi  # type: ignore

from gerrit_to_platform.config import get_setting


def dispatch_workflow(
    owner: str, repository: str, workflow_id: str, ref: str, inputs: Dict[str, str]
) -> Any:
    """Trigger target workflow."""
    github_token = get_setting("github.com", "token")
    api = GhApi(token=github_token)

    return api.actions.create_workflow_dispatch(
        owner, repository, workflow_id, ref, inputs
    )


def filter_workflows(
    owner: str, repository: str, search_filter: str, search_required: bool = False
) -> List[Dict[str, str]]:
    """Return a case insensitive filtered list of workflows."""
    search_filter = search_filter.lower()
    workflows = get_workflows(owner, repository)
    filtered_workflows: List[Dict[str, str]] = []

    for workflow in workflows:
        path = workflow["path"].lower()
        if path.find(search_filter) >= 0 and path.find("gerrit") >= 0:
            if search_required:
                if path.find("required") >= 0:
                    filtered_workflows.append(workflow)
            else:
                filtered_workflows.append(workflow)

    return filtered_workflows


def get_workflows(owner: str, repository: str) -> List[Dict[str, str]]:
    """Get all active workflows for specific repository."""
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
