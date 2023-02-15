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

from ghapi.all import GhApi  # type: ignore

from gerrit_to_platform.config import get_setting

github_token = get_setting("github.com", "token")
api = GhApi(token=github_token)


def get_workflows(owner: str, repository: str) -> list[dict[str, str]]:
    """Get all active workflows for specific repository."""

    workflows = api.actions.list_repo_workflows(owner, repository)["workflows"]
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
