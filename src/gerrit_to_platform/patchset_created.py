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
    get_change_refspec,
)

app = typer.Typer()
log = get_logger(__name__)


@app.command()
def patchset_created(
    change: Annotated[str, typer.Option(help="change id")],
    kind: Annotated[str, typer.Option(help="change kind")],
    change_url: Annotated[str, typer.Option(help="change url")],
    change_owner: Annotated[str, typer.Option(help="change owner")],
    change_owner_username: Annotated[str, typer.Option(help="username")],
    project: Annotated[str, typer.Option(help="project name")],
    branch: Annotated[str, typer.Option(help="branch")],
    topic: Annotated[str, typer.Option(help="topic")],
    uploader: Annotated[str, typer.Option(help="uploader")],
    uploader_username: Annotated[str, typer.Option(help="username")],
    commit: Annotated[str, typer.Option(help="sha1")],
    patchset: Annotated[str, typer.Option(help="patchset id")],
):
    """
    Handle patcheset-created hook.

    Args:
        change (str): change ID
        kind (str): type of change
        change_url (str): change URL
        change_owner (str): change owner eg: 'Foo <foo@example.com>'
        change_owner_username (str): change owner username eg: 'foo'
        project (str): Gerrit project name
        branch (str): branch change is against
        topic (str): topic change is part of
        uploader (str): uploader of change eg: 'Foo <foo@example.com>'
        uploader_username (str): uploader of change username eg: 'foo'
        commit (str): SHA1 of commit
        patchset (str): patchset number
    """

    _configure_logging()
    started = time.monotonic()
    log.info(
        "hook=patchset-created project=%s branch=%s patchset=%s argv_count=%d",
        project,
        branch,
        patchset,
        len(sys.argv),
    )

    change_id = get_change_id(change)
    change_number = get_change_number(change_url)
    refspec = get_change_refspec(change_number, patchset)
    log.debug(
        "event parsed change_number=%s change_id=%s refspec=%s commit=%s",
        change_number,
        change_id,
        refspec,
        commit,
    )

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

    try:
        dispatched = find_and_dispatch(project, "verify", inputs)
        log.info(
            "hook=patchset-created dispatched=%d project=%s " "change_number=%s",
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
            "hook=patchset-created exit project=%s change_number=%s " "elapsed_ms=%d",
            project,
            change_number,
            elapsed_ms,
        )


if __name__ == "__main__":
    app()
