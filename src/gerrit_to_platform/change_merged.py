# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Handler for change-merged events."""

import sys
import time
from typing import Annotated

import typer

from gerrit_to_platform._logging import configure as _configure_logging
from gerrit_to_platform._logging import get_logger
from gerrit_to_platform.helpers import (
    find_and_dispatch,
    get_change_id,
    get_change_number,
)

app = typer.Typer()
log = get_logger(__name__)


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
    """
    Handle change-merged hook.

    Args:
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
        newrev (str): SHA1 of commit
    """

    _configure_logging()
    started = time.monotonic()
    log.info(
        "hook=change-merged project=%s branch=%s argv_count=%d",
        project,
        branch,
        len(sys.argv),
    )

    change_id = get_change_id(change)
    change_number = get_change_number(change_url)

    # Merges are always against the branch and the patchset doesn't matter
    # Plus, the change-merged hook does not provide it and would require
    # looping back into the Gerrit API to retrieve
    patchset = "1"
    refspec = f"refs/heads/{branch}"
    log.debug(
        "event parsed change_number=%s change_id=%s refspec=%s commit=%s newrev=%s",
        change_number,
        change_id,
        refspec,
        commit,
        newrev,
    )

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

    try:
        dispatched = find_and_dispatch(project, "merge", inputs)
        log.info(
            "hook=change-merged dispatched=%d project=%s change_number=%s",
            dispatched,
            project,
            change_number,
        )
    except Exception:
        log.exception(
            "unhandled error during dispatch for change_number=%s",
            change_number,
        )
        raise
    finally:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        log.info(
            "hook=change-merged exit project=%s change_number=%s elapsed_ms=%d",
            project,
            change_number,
            elapsed_ms,
        )


if __name__ == "__main__":
    app()
