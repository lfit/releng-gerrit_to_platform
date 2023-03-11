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

from gerrit_to_platform.helpers import (
    find_and_dispatch,
    get_change_id,
    get_change_number,
    get_change_refspec,
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

    change_id = get_change_id(change)
    change_number = get_change_number(change_url)
    refspec = get_change_refspec(change_number, patchset)

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

    find_and_dispatch(project, "verify", inputs)


if __name__ == "__main__":
    app()
