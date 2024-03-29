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

import typer
from typing_extensions import Annotated

from gerrit_to_platform.config import get_mapping
from gerrit_to_platform.helpers import (
    find_and_dispatch,
    get_change_id,
    get_change_number,
    get_change_refspec,
)

app = typer.Typer()


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def comment_added(
    context: typer.Context,
    change: Annotated[str, typer.Option(help="change id")],
    change_url: Annotated[str, typer.Option(help="change url")],
    change_owner: Annotated[str, typer.Option(help="change owner")],
    change_owner_username: Annotated[str, typer.Option(help="username")],
    project: Annotated[str, typer.Option(help="project name")],
    branch: Annotated[str, typer.Option(help="branch")],
    topic: Annotated[str, typer.Option(help="topic")],
    author: Annotated[str, typer.Option(help="comment author")],
    author_username: Annotated[str, typer.Option(help="username")],
    commit: Annotated[str, typer.Option(help="sha1")],
    comment: Annotated[str, typer.Option(help="comment")],
):
    """
    Handle comment-added hook.

    Approval scores should be added as --<approval category id> <score>

    When a score is removed it should be --<approval category id>-oldValue <score>

    Multiple scores and old scores may be passed

    ex: --Code-Review +1 --Code-Review-oldValue 0

    Args:
        context (typer.Context): handler for the typer context to allow for
            extra non-defined parameters (code scores, see above)
        change (str): change ID
        change_url (str): change URL
        change_owner (str): change owner eg: 'Foo <foo@example.com>'
        change_owner_username (str): change owner username eg: 'foo'
        project (str): Gerrit project name
        branch (str): branch change is against
        topic (str): topic change is part of
        submitter (str): submitter of change eg: 'Foo <foo@example.com>'
        submitter_username (str): submitter of change username eg: 'foo'
        commit (str): SHA1 of commit
        comment (str): the comment added to the change
    """
    change_id = get_change_id(change)
    change_number = get_change_number(change_url)

    patchset_regex = r"^Patch Set (\d+):"
    patchset = re.findall(patchset_regex, comment)[0]

    refspec = get_change_refspec(change_number, patchset)

    inputs = {
        "GERRIT_BRANCH": branch,
        "GERRIT_CHANGE_ID": change_id,
        "GERRIT_CHANGE_NUMBER": change_number,
        "GERRIT_CHANGE_URL": change_url,
        "GERRIT_EVENT_TYPE": "comment-added",
        "GERRIT_PATCHSET_NUMBER": patchset,
        "GERRIT_PATCHSET_REVISION": commit,
        "GERRIT_PROJECT": project,
        "GERRIT_REFSPEC": refspec,
    }

    mapping = get_mapping("comment-added")
    if mapping is None:
        return

    for mapper in mapping:
        if not re.findall(mapper, comment):
            continue

        find_and_dispatch(project, mapping[mapper], inputs)


if __name__ == "__main__":
    app()
