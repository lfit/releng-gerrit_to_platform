# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""CLI main for gerrit_to_platform."""

from typing import List, Optional

import typer

import gerrit_to_platform.comment_added as comment_added
import gerrit_to_platform.patchset_created as patchset_created
from gerrit_to_platform.change_merged import app as change_merged

app = typer.Typer()
app.add_typer(
    patchset_created.app, name="patchset-created", help="Handle patchset-created hook"
)
app.add_typer(comment_added.app, name="comment-added", help="Handle comment-added hook")
app.add_typer(change_merged, name="change-merged", help="Handle change-merged hook")


@app.command()
def change_abandoned(
    change: str = typer.Option(..., help="change id"),
    change_url: str = typer.Option(..., help="change url"),
    change_owner: str = typer.Option(..., help="change owner"),
    change_owner_username: str = typer.Option(..., help="username"),
    project: str = typer.Option(..., help="project name"),
    branch: str = typer.Option(..., help="branch"),
    topic: str = typer.Option(..., help="topic"),
    abandoner: str = typer.Option(..., help="abandoner"),
    abandoner_username: str = typer.Option(..., help="username"),
    commit: str = typer.Option(..., help="sha1"),
    reason: str = typer.Option(..., help="reason"),
):
    """Handle change-abandoned hook."""


@app.command()
def change_deleted(
    change: str = typer.Option(..., help="change id"),
    change_url: str = typer.Option(..., help="change url"),
    change_owner: str = typer.Option(..., help="change owner"),
    project: str = typer.Option(..., help="project name"),
    branch: str = typer.Option(..., help="branch"),
    topic: str = typer.Option(..., help="topic"),
    deleter: str = typer.Option(..., help="deleter"),
):
    """Handle change-deleted hook."""


@app.command()
def change_restored(
    change: str = typer.Option(..., help="change id"),
    change_url: str = typer.Option(..., help="change url"),
    change_owner: str = typer.Option(..., help="change owner"),
    change_owner_username: str = typer.Option(..., help="username"),
    project: str = typer.Option(..., help="project name"),
    branch: str = typer.Option(..., help="branch"),
    topic: str = typer.Option(..., help="topic"),
    restorer: str = typer.Option(..., help="restorer"),
    restorer_username: str = typer.Option(..., help="username"),
    commit: str = typer.Option(..., help="sha1"),
    reason: str = typer.Option(..., help="reason"),
):
    """Handle change-restored hook."""


@app.command()
def ref_updated(
    oldrev: str = typer.Option(..., help="old revision"),
    newrev: str = typer.Option(..., help="new revision"),
    refname: str = typer.Option(..., help="ref name"),
    project: str = typer.Option(..., help="project name"),
    submitter: str = typer.Option(..., help="submitter"),
    submitter_username: str = typer.Option(..., help="username"),
):
    """Handle ref-updated hook."""


@app.command()
def project_created(
    project: str = typer.Option(..., help="project name"),
    head: str = typer.Option(..., help="head name"),
):
    """Handle project-created hook."""


@app.command()
def reviewer_added(
    change: str = typer.Option(..., help="change id"),
    change_url: str = typer.Option(..., help="change url"),
    change_owner: str = typer.Option(..., help="change owner"),
    change_owner_username: str = typer.Option(..., help="username"),
    project: str = typer.Option(..., help="project name"),
    branch: str = typer.Option(..., help="branch"),
    reviewer: str = typer.Option(..., help="reviewer"),
    reviewer_username: str = typer.Option(..., help="username"),
):
    """Handle reviewer-added hook."""


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def reviewer_deleted(
    context: typer.Context,
    change: str = typer.Option(..., help="change id"),
    change_url: str = typer.Option(..., help="change url"),
    change_owner: str = typer.Option(..., help="change owner"),
    change_owner_username: str = typer.Option(..., help="username"),
    project: str = typer.Option(..., help="project name"),
    branch: str = typer.Option(..., help="branch"),
    reviewer: str = typer.Option(..., help="reviewer"),
):
    """
    Handle reviewer-deleted hook.

    Approval scores to remove should be done as --<aproval category id> <score>

    Multiple scores may be passed
    """


@app.command()
def topic_changed(
    change: str = typer.Option(..., help="change id"),
    change_owner: str = typer.Option(..., help="change owner"),
    change_owner_username: str = typer.Option(..., help="username"),
    project: str = typer.Option(..., help="project name"),
    branch: str = typer.Option(..., help="branch"),
    changer: str = typer.Option(..., help="changer"),
    changer_username: str = typer.Option(..., help="username"),
    old_topic: str = typer.Option(..., help="old topic"),
    new_topic: str = typer.Option(..., help="new topic"),
):
    """Handle topic-changed hook."""


@app.command()
def hashtags_changed(
    added: Optional[List[str]] = typer.Option(None, help="added hashtag"),
    removed: Optional[List[str]] = typer.Option(None, help="removed hashtag"),
    hashtag: Optional[List[str]] = typer.Option(None, help="remaining hashtag"),
    change: str = typer.Option(..., help="change id"),
    change_owner: str = typer.Option(..., help="change owner"),
    change_owner_username: str = typer.Option(..., help="username"),
    project: str = typer.Option(..., help="project name"),
    branch: str = typer.Option(..., help="branch"),
    editor: str = typer.Option(..., help="editor"),
    editor_username: str = typer.Option(..., help="username"),
):
    """
    Handle hashtags-changed hook.

    --added, --removed, and --hashtag may be provided multiple times
    """


@app.command()
def cla_signed(
    submitter: str = typer.Option(..., help="submitter"),
    user_id: str = typer.Option(..., help="user_id"),
    cla_id: str = typer.Option(..., help="cla_id"),
):
    """Handle cla-signed hook."""


if __name__ == "__main__":
    app()
