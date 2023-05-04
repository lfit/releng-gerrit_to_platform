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

import typer
from typing_extensions import Annotated

from gerrit_to_platform.helpers import (
    find_and_dispatch,
    get_change_id,
    get_change_number,
)

app = typer.Typer()


@app.command()
def change_merged(
    change: Annotated[str, typer.Option(help="change id")],
    change_url: Annotated[str, typer.Option(help="change url")],
    change_owner: Annotated[str, typer.Option(help="change owner")],
    change_owner_username: Annotated[str, typer.Option(help="username")],
    project: Annotated[str, typer.Option(help="project name")],
    branch: Annotated[str, typer.Option(help="branch")],
    topic: Annotated[str, typer.Option(help="topic")],
    submitter: Annotated[str, typer.Option(help="submitter")],
    submitter_username: Annotated[str, typer.Option(help="username")],
    commit: Annotated[str, typer.Option(help="sha1")],
    newrev: Annotated[str, typer.Option(help="sha1")],
):
    """Handle change-merged hook."""

    change_id = get_change_id(change)
    change_number = get_change_number(change_url)

    # Merges are always against the branch and the patchset doesn't matter
    # Plus, the change-merged hook does not provide it and would require
    # looping back into the Gerrit API to retrieve
    patchset = "1"
    refspec = f"refs/heads/{branch}"

    inputs = {
        "GERRIT_BRANCH": branch,
        "GERRIT_CHANGE_ID": change_id,
        "GERRIT_CHANGE_NUMBER": change_number,
        "GERRIT_CHANGE_URL": change_url,
        "GERRIT_EVENT_TYPE": "change-merged",
        "GERRIT_PATCHSET_NUMBER": patchset,
        "GERRIT_PATCHSET_REVISION": commit,
        "GERRIT_PROJECT": project,
        "GERRIT_REFSPEC": refspec,
    }

    find_and_dispatch(project, "merge", inputs)


if __name__ == "__main__":
    app()
