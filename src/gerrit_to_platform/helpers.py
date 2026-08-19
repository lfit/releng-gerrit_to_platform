# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Common helper functions."""

import re
import time
from typing import Callable, Dict, Optional, Union

import gerrit_to_platform.github as github
from gerrit_to_platform._logging import get_logger
from gerrit_to_platform.config import (
    Platform,
    ReplicationRemotes,
    get_replication_remotes,
)
from gerrit_to_platform.gerrit import is_change_readable

log = get_logger(__name__)


def choose_dispatch(platform: Platform) -> Union[Callable, None]:
    """
    Choose platform job dispatcher.

    Args:
        platform (Platform): the platform that the dispatch is being looked up
            for

    Returns:
        Callable: The appropriate callable matching the dispatch_worfklow call
            signature for the platform
        None: If no dispatch_workflow is defined for the platform passed in a
            None is returned
    """
    if platform.value == "github":
        return github.dispatch_workflow

    return None


def choose_filter_workflows(platform: Platform) -> Union[Callable, None]:
    """
    Choose platform workflow filter.

    Args:
        platform (Platform): the platform that the filter_workflows is being
            looked up for


    Returns:
        Callable: The appropriate callable matching the filter_workflows call
            signature for the platform
        None: If no filter_workflows is defined for the platform passed in a
            None is returned
    """
    if platform.value == "github":
        return github.filter_workflows

    return None


def convert_repo_name(
    remotes: ReplicationRemotes, platform: Platform, remote: str, repository: str
) -> str:
    """
    Convert the repository name based on the remotenamestyle of the target
    platform/owner.

    Args:
        remotes (ReplicationRemotes): object containing the defined remotes
            styles
        platform (Platform): what platform is the conversion happening against
        remote (str): The specific remote that is being worked on
        repository (str): The repository name that needs conversion

    Returns:
        str: The repository name converted to the appropriate flattening for
            the target remote
    """

    remote_styles = {
        "dash": "-",
        "underscore": "_",
        "slash": "/",
    }

    target_style = remotes[platform.value][remote]["remotenamestyle"]
    converted_repository = repository.replace("/", remote_styles[target_style])

    return converted_repository


def find_and_dispatch(
    project: str, workflow_filter: str, inputs: Dict[str, str]
) -> int:
    """
    Find relevant workflows and dispatch them.

    Args:
        project (str): the project repository name
        workflow_filter (str): the filter for the workflow names
        inputs (Dict[str, str]): key / value pair dictionary for inputs to be
            passed to the target workflow dispatch

    Returns:
        int: The number of workflows dispatched
    """
    change_url = inputs.get("GERRIT_CHANGE_URL", "")
    change_number = inputs.get("GERRIT_CHANGE_NUMBER", "")
    event_type = inputs.get("GERRIT_EVENT_TYPE", "")

    # Merged changes are always public (Gerrit refuses to submit a
    # private change), so the probe only runs for pre-merge events.
    if event_type != "change-merged" and not is_change_readable(
        change_url, change_number
    ):
        # Operator-facing confirmation kept on stdout; the structured
        # log line below is the machine-readable counterpart.
        print(
            f"Skipping dispatch for change {change_number}: the change "
            "is not readable platform-side (private or restricted). "
            "A fresh event fires when the change is published."
        )
        log.info(
            "dispatch skipped (change not readable) project=%s "
            "filter=%s change_number=%s event_type=%s",
            project,
            workflow_filter,
            change_number,
            event_type,
        )
        return 0

    remotes = get_replication_remotes()
    dispatched_count = 0
    log.debug(
        "find_and_dispatch project=%s filter=%s remotes_platforms=%s",
        project,
        workflow_filter,
        sorted(remotes.keys()),
    )

    for platform in Platform:
        if platform.value not in remotes:
            continue

        dispatcher = choose_dispatch(platform)
        filter_workflows = choose_filter_workflows(platform)

        if dispatcher is None or filter_workflows is None:
            log.debug(
                "platform=%s has no dispatcher/filter; skipping",
                platform.value,
            )
            continue

        for remote in remotes[platform.value]:
            owner = remotes[platform.value][remote]["owner"]
            repo = convert_repo_name(remotes, platform, remote, project)
            log.info(
                "platform detected platform=%s remote=%s owner=%s repo=%s project=%s",
                platform.value,
                remote,
                owner,
                repo,
                project,
            )
            workflows = filter_workflows(owner, repo, workflow_filter)
            log.info(
                "workflow lookup platform=%s owner=%s repo=%s filter=%s candidates=%d",
                platform.value,
                owner,
                repo,
                workflow_filter,
                len(workflows),
            )
            if not workflows:
                log.info(
                    "no workflow matched filter=%s on %s/%s",
                    workflow_filter,
                    owner,
                    repo,
                )

            for workflow in workflows:
                # User-facing confirmation kept on stdout; the structured
                # log line below is the machine-readable counterpart.
                print(
                    f"Dispatching workflow '{workflow['name']}', "
                    + f"id {workflow['id']} on "
                    + f"{platform.value}:{owner}/{repo} for change "
                    + f"{inputs['GERRIT_CHANGE_NUMBER']} patch "
                    + inputs["GERRIT_PATCHSET_NUMBER"]
                )
                started = time.monotonic()
                log.info(
                    "dispatch attempt platform=%s owner=%s repo=%s "
                    "workflow=%s workflow_id=%s change_number=%s patchset=%s "
                    "input_keys=%d",
                    platform.value,
                    owner,
                    repo,
                    workflow["name"],
                    workflow["id"],
                    inputs["GERRIT_CHANGE_NUMBER"],
                    inputs["GERRIT_PATCHSET_NUMBER"],
                    len(inputs),
                )
                try:
                    dispatcher(
                        owner,
                        repo,
                        workflow["id"],
                        f"refs/heads/{inputs['GERRIT_BRANCH']}",
                        inputs,
                    )
                    dispatched_count += 1
                    log.info(
                        "dispatch success platform=%s owner=%s repo=%s "
                        "workflow=%s elapsed_ms=%d",
                        platform.value,
                        owner,
                        repo,
                        workflow["name"],
                        int((time.monotonic() - started) * 1000),
                    )
                except Exception as e:
                    log.exception(
                        "dispatch failure platform=%s owner=%s repo=%s "
                        "workflow=%s elapsed_ms=%d: %s",
                        platform.value,
                        owner,
                        repo,
                        workflow["name"],
                        int((time.monotonic() - started) * 1000),
                        e,
                    )

            magic_repo = get_magic_repo(platform)
            if magic_repo:
                required_workflows = filter_workflows(
                    owner, magic_repo, workflow_filter, True
                )
                log.debug(
                    "required workflows lookup platform=%s owner=%s "
                    "magic_repo=%s filter=%s candidates=%d",
                    platform.value,
                    owner,
                    magic_repo,
                    workflow_filter,
                    len(required_workflows),
                )

                inputs["TARGET_REPO"] = f"{owner}/{repo}"

                for workflow in required_workflows:
                    print(
                        f"Dispatching required workflow '{workflow['name']}', "
                        + f"id {workflow['id']} on "
                        + f"{platform.value}:{owner}/{magic_repo} for change "
                        + f"{inputs['GERRIT_CHANGE_NUMBER']} patch "
                        + f"{inputs['GERRIT_PATCHSET_NUMBER']} against "
                        + f"{platform.value}:{owner}/{repo}"
                    )
                    started = time.monotonic()
                    log.info(
                        "required dispatch attempt platform=%s owner=%s "
                        "magic_repo=%s target=%s/%s workflow=%s",
                        platform.value,
                        owner,
                        magic_repo,
                        owner,
                        repo,
                        workflow["name"],
                    )
                    try:
                        dispatcher(
                            owner,
                            magic_repo,
                            workflow["id"],
                            "refs/heads/main",
                            inputs,
                        )
                        dispatched_count += 1
                        log.info(
                            "required dispatch success platform=%s owner=%s "
                            "magic_repo=%s workflow=%s elapsed_ms=%d",
                            platform.value,
                            owner,
                            magic_repo,
                            workflow["name"],
                            int((time.monotonic() - started) * 1000),
                        )
                    except Exception as e:
                        log.exception(
                            "required dispatch failure platform=%s "
                            "owner=%s magic_repo=%s workflow=%s "
                            "elapsed_ms=%d: %s",
                            platform.value,
                            owner,
                            magic_repo,
                            workflow["name"],
                            int((time.monotonic() - started) * 1000),
                            e,
                        )

    log.info(
        "find_and_dispatch finished project=%s filter=%s dispatched=%d",
        project,
        workflow_filter,
        dispatched_count,
    )
    return dispatched_count


# Gerrit hook ``--change`` argument shapes.
#
# Legacy triplet ID, present in older Gerrit releases and still emitted
# by some configurations:
#     project~branch~Iabc123def...
# The third tilde-separated field is the commit-message Change-Id
# footer (always starts with ``I``).
_LEGACY_CHANGE_ID_RE = re.compile(r"^[^~]+~[^~]+~(I[A-Za-z0-9]+)$")

# Modern compact ID, introduced in Gerrit 3.x and now the default
# value passed to hook scripts:
#     <URL-encoded project>~<change_number>
# e.g. ``ccsdk%2Fapps~1``.  This shape does not carry the
# commit-message Change-Id footer, only the project + numeric id, but
# it is still a unique, stable identifier for the change.
_COMPACT_CHANGE_ID_RE = re.compile(r"^[^~]+~\d+$")


def get_change_id(change: str) -> str:
    """
    Return a Gerrit change identifier from the hook ``--change`` value.

    Gerrit hooks pass ``--change`` in one of two shapes depending on
    the server version and configuration:

    * **Legacy triplet** (e.g. ``project~branch~Iabc123def...``).  The
      third tilde-separated field is the commit-message ``Change-Id``
      footer.  When this shape is detected the function returns that
      ``I...`` value, preserving the previous behaviour.

    * **Modern compact** (Gerrit 3.x and later, e.g. ``ccsdk%2Fapps~1``
      — URL-encoded project followed by the change number).  Gerrit
      no longer ships the commit-message ``Change-Id`` footer in the
      hook argv for this shape, so the function returns the compact
      id as-is.  It is still a unique, stable identifier per change
      and works as a ``GERRIT_CHANGE_ID`` workflow input (e.g. for
      concurrency keys).

    Args:
        change (str): the ``--change`` value supplied by the Gerrit
            hook plugin.

    Returns:
        str: The legacy ``I...`` Change-Id when present, otherwise the
        modern compact ``project~number`` identifier verbatim.

    Raises:
        ValueError: if ``change`` matches neither shape.  The previous
            implementation raised ``IndexError`` here, which made
            triage harder for operators inspecting hook tracebacks.
    """
    legacy_match = _LEGACY_CHANGE_ID_RE.fullmatch(change)
    if legacy_match:
        return legacy_match.group(1)
    if _COMPACT_CHANGE_ID_RE.fullmatch(change):
        return change
    raise ValueError(
        f"Unrecognised Gerrit --change argument: {change!r}; expected "
        "either 'project~branch~Iabc123' (legacy triplet) or "
        "'project~changeNumber' (Gerrit 3.x compact form)."
    )


def get_change_number(change_url: str) -> str:
    """
    Get the Gerrit change_number

    Args:
        change_url (str): the url to the specific change passed by the Gerrit
            event

    Returns:
        str: The change number as string extracted from the url
    """
    change_number_regex = r"^.*/\+/(\d+)$"
    return re.findall(change_number_regex, change_url)[0]


def get_change_refspec(change_number: str, patchset: str) -> str:
    """
    Return the change refspec from the change number (str) and patch number

    Args:
        change_number (str): The change number to work with
        patchset (str): The patchset number to work with

    Returns:
        str: The git refspec pointing to the hidden ref for the specific change
            and patchset
    """
    if int(change_number) < 100:
        ref_shard = change_number.zfill(2)
    else:
        ref_shard = change_number[len(change_number) - 2 :]
    return f"refs/changes/{ref_shard}/{change_number}/{patchset}"


def get_magic_repo(platform: Platform) -> Optional[str]:
    """
    Get the "magic" repo for a given Platform used to store organization wide
    required workflows

    Args:
        platform (Platform): Platform to lookup magic repo for

    Returns:
        Optional[str]: The magic repo name or None if not defined for the
            platform
    """

    if platform == Platform.GITHUB:
        return ".github"

    return None
