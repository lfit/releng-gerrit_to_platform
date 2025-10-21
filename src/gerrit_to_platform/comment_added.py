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

import os
import re
import time
from pathlib import Path

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

# Cooldown period in seconds (5 minutes)
COOLDOWN_SECONDS = 300

# Compiled regex pattern (avoids recompilation on each use)
GHA_PATTERN = re.compile(r"^gha-(\w+)\s+([\w-]+)", re.IGNORECASE)

# Generic workflow handler name for ChatOps commands
GHA_GENERIC_HANDLER = "comment-handler"


def check_cooldown(change_number: str, workflow_name: str) -> bool:
    """
    Check if workflow trigger is within cooldown period.

    Args:
        change_number: Gerrit change number
        workflow_name: Name of the workflow to trigger

    Returns:
        bool: True if trigger is allowed, False if still in cooldown
    """
    # Issue 1 Fix: Input validation to prevent path injection (CWE-22)
    if not change_number.isdigit():
        print(f"Invalid change number: {change_number}")
        return False

    # Workflow name must be alphanumeric with hyphens only
    if not re.match(r"^[\w-]+$", workflow_name):
        print(f"Invalid workflow name: {workflow_name}")
        return False

    # /tmp/ is intentional for ephemeral cooldown files with path validation below
    cooldown_file = Path(
        f"/tmp/gha_cooldown_{change_number}_{workflow_name}"
    )  # nosec B108

    # Verify the resolved path is still within /tmp (path traversal protection)
    try:
        # Path traversal protection - validate resolved path stays in /tmp
        if not str(cooldown_file.resolve()).startswith("/tmp/"):  # nosec B108
            print(f"Path traversal attempt detected: {cooldown_file}")
            return False
    except OSError as e:
        # Issue 13 Fix: Filesystem error handling - fail open
        print(f"Warning: Cooldown path validation failed: {e}")
        return True

    try:
        # Issue 2 Fix: Atomic file creation to prevent race condition (TOCTOU)
        # Try to create the file atomically with O_CREAT | O_EXCL
        try:
            fd = os.open(
                str(cooldown_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
            )
            os.close(fd)
            # File created successfully - cooldown starts now
            return True
        except FileExistsError:
            # File exists - check if still in cooldown
            last_trigger = cooldown_file.stat().st_mtime
            time_since_trigger = time.time() - last_trigger

            if time_since_trigger < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - time_since_trigger)
                print(
                    f"Cooldown active for workflow '{workflow_name}' on change {change_number}. "
                    f"Retry in {remaining} seconds."
                )
                return False
            else:
                # Issue 9 Fix: Opportunistic cleanup - delete expired file
                try:
                    cooldown_file.unlink()
                except OSError:
                    pass  # Ignore deletion errors

                # Create new cooldown file
                try:
                    fd = os.open(
                        str(cooldown_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
                    )
                    os.close(fd)
                except FileExistsError:
                    # Race condition - another process created it, treat as in cooldown
                    return False

                return True

    except OSError as e:
        # Issue 13 Fix: Filesystem error handling - fail open for non-critical feature
        print(f"Warning: Cooldown check failed due to filesystem error: {e}")
        print(f"Allowing workflow to proceed for change {change_number}")
        return True


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

    Supports two trigger mechanisms:
    1. gha-<action> <workflow_name> pattern for direct workflow triggering
       Example: "gha-run csit-2n-perftest nic=intel-e810cq drv=avf"
       The full command line is passed to the workflow via GERRIT_COMMENT input
       for parameter parsing by the GitHub Actions workflow.
    2. Keyword mapping from config file (legacy behavior)

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

    # Check for gha-<action> pattern first
    # Process line-by-line, require command at start of line,
    # ignore quoted text, process only first valid command
    workflow_name = None
    gha_command_line = None

    for line in comment.split("\n"):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip quoted text (Gerrit quote marker)
        if line.startswith(">"):
            continue

        # Match command at start of line
        gha_match = GHA_PATTERN.match(line)
        if gha_match:
            workflow_name = gha_match.group(2)
            gha_command_line = line
            # Process only first valid command
            break

    if workflow_name:
        # Issue 5 Fix: Check cooldown but don't update yet (update after successful dispatch)
        if not check_cooldown(change_number, workflow_name):
            return

        # Add command line to inputs so GHA workflow can parse parameters
        inputs["GERRIT_COMMENT"] = gha_command_line

        try:
            # Issue 3 Fix: Use constant instead of magic string
            dispatched = find_and_dispatch(project, GHA_GENERIC_HANDLER, inputs)

            # Issue 6 Fix: Validate dispatch was successful
            if dispatched == 0:
                print(
                    f"No workflows found matching '{GHA_GENERIC_HANDLER}' for project {project}"
                )
                print(f"Command attempted: {gha_command_line}")
                return  # Don't update cooldown if no workflows found

            # Issue 6 Fix: Log success with count
            print(
                f"Successfully dispatched {dispatched} workflow(s) for '{workflow_name}'"
            )

        except Exception as e:
            # Issue 11 Fix: Add context to exception
            print(f"Error dispatching workflow '{GHA_GENERIC_HANDLER}': {e}")
            print(f"Command attempted: {gha_command_line}")
            print(f"Change: {change_number}, Patchset: {patchset}, Project: {project}")
            raise  # Don't update cooldown on error

        return

    mapping = get_mapping("comment-added")
    if mapping is None:
        return

    for mapper in mapping:
        if not re.findall(mapper, comment):
            continue

        find_and_dispatch(project, mapping[mapper], inputs)


if __name__ == "__main__":
    app()
