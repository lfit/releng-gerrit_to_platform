# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Handler for patchset-created events."""

import re
from typing import Dict, List

import typer

from gerrit_to_platform.config import Platform, get_replication_remotes
from gerrit_to_platform.helpers import (
    choose_dispatch,
    choose_filter_workflows,
    convert_repo_name,
)

app = typer.Typer()


@app.command()
def patchset_created(
    change: str = typer.Option(..., help="change id"),
    kind: str = typer.Option(..., help="change kind"),
    change_url: str = typer.Option(..., help="change url"),
    change_owner: str = typer.Option(..., help="change owner"),
    change_owner_username: str = typer.Option(..., help="username"),
    project: str = typer.Option(..., help="project name"),
    branch: str = typer.Option(..., help="branch"),
    topic: str = typer.Option(..., help="topic"),
    uploader: str = typer.Option(..., help="uploader"),
    uploader_username: str = typer.Option(..., help="username"),
    commit: str = typer.Option(..., help="sha1"),
    patchset: str = typer.Option(..., help="patchset id"),
):
    """Handle patcheset-created hook."""

    change_id_regex = r".*~.*~(I.*)"
    change_id = re.findall(change_id_regex, change)[0]

    change_number_regex = r"^.*/\+/(\d+)$"
    change_number = re.findall(change_number_regex, change_url)[0]

    if int(change_number) < 100:
        ref_shard = change_number.zfill(2)
    else:
        ref_shard = change_number[len(change_number) - 2 :]
    refspec = f"refs/changes/{ref_shard}/{change_number}/{patchset}"

    inputs = {
        "GERRIT_BRANCH": branch,
        "GERRIT_CHANGE_ID": change_id,
        "GERRIT_CHANGE_NUMBER": change_number,
        "GERRIT_CHANGE_URL": change_url,
        "GERRIT_EVENT_TYPE": "patchset-created",
        "GERRIT_PATCHSET_NUMBER": patchset,
        "GERRIT_PATCHSET_REVISION": commit,
        "GERRIT_PROJECT": project,
        "GERRIT_REFSPEC": refspec,
    }

    remotes = get_replication_remotes()
    for platform in Platform:
        if platform.value in remotes.keys():
            dispatcher = choose_dispatch(Platform(platform.value))
            filter_workflows = choose_filter_workflows(Platform(platform.value))

            if not (dispatcher is None or filter_workflows is None):
                for remote in remotes[platform.value].keys():
                    verify_workflows: List[Dict[str, str]] = []
                    owner = remotes[platform.value][remote]["owner"]
                    repo = convert_repo_name(
                        remotes, Platform(platform.value), remote, project
                    )

                    verify_workflows = filter_workflows(owner, repo, "verify")  # type: ignore
                    for workflow in verify_workflows:
                        print(
                            f"Dispatching workflow '{workflow['name']}', "
                            + f"id {workflow['id']} on "
                            + f"{platform.value}:{owner}/{repo} for change "
                            + f"{change_number} patch {patchset}"
                        )
                        dispatcher(
                            owner, repo, workflow["id"], f"refs/heads/{branch}", inputs
                        )


if __name__ == "__main__":
    app()
