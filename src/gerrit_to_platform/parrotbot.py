# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2026 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Parrotbot: relay Gerrit committer commands to GitHub PRs.

Gerrit committers who lack GitHub admin access cannot directly issue
commands like ``@dependabot recreate`` on GitHub PRs. The parrotbot
watches for ``@parrot @dependabot <command>`` comments on Gerrit
changes and relays them to the linked GitHub PR using a token with
push access.

Flow:
1. Gerrit ``comment-added`` hook fires with a comment containing
   ``@parrot @dependabot <command>``.
2. Parrotbot extracts the target bot (``@dependabot``) and the command
   (e.g., ``recreate``, ``rebase``).
3. It verifies the commenter is a project committer (owner group member).
4. It finds the linked GitHub PR via the ``GitHub-PR:`` trailer in
   the Gerrit change's commit message.
5. It posts ``@dependabot <command>`` as a comment on the GitHub PR.
6. It posts a confirmation comment back on the Gerrit change.

Security:
- Only whitelisted commands are relayed.
- Only project committers (owner group members) can trigger the bot.
- The GitHub token used must have push access to the target org.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

from gerrit_to_platform.config import get_setting

log = logging.getLogger("gerrit_to_platform.parrotbot")

# ── Command whitelist ──────────────────────────────────────────────
# Only these commands may be relayed to GitHub bots.
ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {
        "recreate",
        "rebase",
        "merge",
        "squash",
        "close",
        "reopen",
    }
)

# ── Regex for parrotbot invocation ─────────────────────────────────
# Matches: @parrot @dependabot <command>
#      or: @parrotbot @dependabot <command>
# The target bot name and command are captured.
PARROT_RE = re.compile(
    r"@parrot(?:bot)?\s+@(\w[\w\-\[\]]*)\s+(\w+)",
    re.IGNORECASE,
)


def is_parrot_command(comment: str) -> bool:
    """Check whether a Gerrit comment contains a parrotbot invocation."""
    return bool(PARROT_RE.search(comment))


def parse_parrot_command(comment: str) -> Optional[Dict[str, str]]:
    """Extract target bot and command from a parrotbot invocation.

    Returns:
        Dict with keys ``target_bot`` and ``command``, or None if no
        valid parrotbot command is found.
    """
    match = PARROT_RE.search(comment)
    if not match:
        return None

    target_bot = match.group(1).strip()
    command = match.group(2).strip().lower()

    if command not in ALLOWED_COMMANDS:
        log.warning(
            "Parrotbot: command %r not in whitelist (allowed: %s)",
            command,
            ", ".join(sorted(ALLOWED_COMMANDS)),
        )
        return None

    return {"target_bot": target_bot, "command": command}


def extract_github_pr_from_commit(
    gerrit_host: str,
    change_number: str,
) -> Optional[Dict[str, str]]:
    """Extract the linked GitHub PR from a Gerrit change's commit message.

    Looks for ``GitHub-PR: https://github.com/<owner>/<repo>/pull/<num>``
    in the commit message trailers.

    Returns:
        Dict with ``owner``, ``repo``, ``pr_number``, ``url`` keys,
        or None if no GitHub-PR trailer is found.
    """
    try:
        from pygerrit2 import GerritRestAPI

        gerrit_url = f"https://{gerrit_host}"
        api = GerritRestAPI(url=gerrit_url)
        change = api.get(f"/changes/{change_number}/detail")

        # Get the commit message from the latest revision
        current_rev = change.get("current_revision", "")
        revisions = change.get("revisions", {})
        if current_rev and current_rev in revisions:
            commit_msg = revisions[current_rev].get("commit", {}).get("message", "")
        else:
            log.warning("Cannot find current revision for change %s", change_number)
            return None

        # Parse GitHub-PR trailer
        pr_re = re.compile(
            r"GitHub-PR:\s*https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        )
        match = pr_re.search(commit_msg)
        if not match:
            log.info("No GitHub-PR trailer found in change %s", change_number)
            return None

        return {
            "owner": match.group(1),
            "repo": match.group(2),
            "pr_number": match.group(3),
            "url": match.group(0).replace("GitHub-PR: ", "").strip(),
        }
    except ImportError:
        log.error("pygerrit2 not available — cannot query Gerrit REST API")
        return None
    except Exception as exc:
        log.error(
            "Failed to extract GitHub PR from change %s: %s",
            change_number,
            exc,
        )
        return None


def post_github_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    comment_body: str,
) -> bool:
    """Post a comment on a GitHub PR.

    Uses the token configured in the g2p config file.

    Returns:
        True on success, False on failure.
    """
    try:
        from ghapi.all import GhApi  # type: ignore

        github_token = get_setting("github.com", "token")
        api = GhApi(token=github_token)
        api.issues.create_comment(owner, repo, pr_number, body=comment_body)
        log.info(
            "Posted comment on %s/%s#%d: %s",
            owner,
            repo,
            pr_number,
            comment_body[:80],
        )
        return True
    except Exception as exc:
        log.error(
            "Failed to post comment on %s/%s#%d: %s",
            owner,
            repo,
            pr_number,
            exc,
        )
        return False


def post_gerrit_comment(
    gerrit_host: str,
    change_number: str,
    message: str,
) -> bool:
    """Post a review comment on a Gerrit change (for confirmation).

    Returns:
        True on success, False on failure.
    """
    try:
        from pygerrit2 import GerritRestAPI

        gerrit_url = f"https://{gerrit_host}"
        api = GerritRestAPI(url=gerrit_url)
        api.post(
            f"/changes/{change_number}/revisions/current/review",
            json={"message": message},
        )
        log.info("Posted Gerrit comment on change %s", change_number)
        return True
    except Exception as exc:
        log.debug(
            "Could not post Gerrit confirmation for change %s: %s",
            change_number,
            exc,
        )
        return False


def check_user_authorized(
    gerrit_host: str,
    project: str,
    username: str,
) -> bool:
    """Verify that a Gerrit user is a committer (owner) for the project.

    Queries the Gerrit REST API to retrieve the project access
    configuration.  The ``owner`` groups listed under ``refs/*`` are
    the project committer groups.  The function then checks whether
    *username* is a member of any of those groups.

    Args:
        gerrit_host: Gerrit server hostname.
        project: Gerrit project name (e.g., ``yangtools``).
        username: Gerrit username of the commenter.

    Returns:
        True if the user is a project committer, False otherwise.
    """
    try:
        from pygerrit2 import GerritRestAPI

        gerrit_url = f"https://{gerrit_host}"
        api = GerritRestAPI(url=gerrit_url)

        encoded_project = project.replace("/", "%2F")
        access_info = api.get(f"/projects/{encoded_project}/access")

        # Collect owner group UUIDs from all ref patterns
        owner_groups: list[str] = []
        local_perms = access_info.get("local", {})
        for _ref_pattern, ref_info in local_perms.items():
            permissions = ref_info.get("permissions", {})
            owner_perm = permissions.get("owner", {})
            for group_uuid in owner_perm.get("rules", {}):
                if group_uuid not in owner_groups:
                    owner_groups.append(group_uuid)

        if not owner_groups:
            log.warning(
                "Parrotbot: no owner groups found for project %s",
                project,
            )
            return False

        # Check if the user is a member of any owner (committer) group
        for group_uuid in owner_groups:
            try:
                members = api.get(f"/groups/{group_uuid}/members/")
                for member in members:
                    if member.get("username") == username:
                        log.info(
                            "Parrotbot: user %s is a committer for %s "
                            "(member of %s)",
                            username,
                            project,
                            group_uuid,
                        )
                        return True
            except Exception:
                # Group may not be queryable (e.g. LDAP/SAML groups
                # without list access).  Fall through to next group.
                log.debug(
                    "Parrotbot: cannot list members of group %s",
                    group_uuid,
                )
                continue

        log.warning(
            "Parrotbot: user %s is NOT a committer for %s",
            username,
            project,
        )
        return False
    except ImportError:
        log.error("pygerrit2 not available — cannot verify user authorization")
        return False
    except Exception as exc:
        log.error(
            "Failed to check committer status for user %s on %s: %s",
            username,
            project,
            exc,
        )
        return False


def handle_parrot_command(
    comment: str,
    change_number: str,
    change_url: str,
    author_username: str,
    project: str,
) -> bool:
    """Process a parrotbot command from a Gerrit comment.

    This is the main entry point called from ``comment_added.py``.

    Args:
        comment: The full Gerrit comment text.
        change_number: Gerrit change number.
        change_url: URL to the Gerrit change.
        author_username: Gerrit username of the commenter.
        project: Gerrit project name.

    Returns:
        True if the command was successfully relayed, False otherwise.
    """
    parsed = parse_parrot_command(comment)
    if not parsed:
        log.debug("No valid parrotbot command in comment")
        return False

    target_bot = parsed["target_bot"]
    command = parsed["command"]

    log.info(
        "Parrotbot: user=%s project=%s change=%s → @%s %s",
        author_username,
        project,
        change_number,
        target_bot,
        command,
    )

    # Check if parrotbot is enabled
    try:
        enabled = str(get_setting("parrotbot", "enabled")).lower() in (
            "true",
            "yes",
            "1",
        )
    except (KeyError, TypeError):
        enabled = False
    if not enabled:
        log.info("Parrotbot is disabled in configuration")
        return False

    # Extract the Gerrit host from the change URL
    gerrit_host_match = re.match(r"https?://([^/]+)", change_url)
    if not gerrit_host_match:
        log.error("Cannot extract Gerrit host from URL: %s", change_url)
        return False
    gerrit_host = gerrit_host_match.group(1)

    # Verify the commenter has submit permission on the project
    if not check_user_authorized(gerrit_host, project, author_username):
        log.warning(
            "Parrotbot: unauthorized user %s attempted command on %s",
            author_username,
            project,
        )
        post_gerrit_comment(
            gerrit_host,
            change_number,
            f"🦜 Parrotbot: User `{author_username}` is not a committer for "
            f"project `{project}`. Only project committers may use parrotbot.",
        )
        return False

    # Find the linked GitHub PR
    pr_info = extract_github_pr_from_commit(gerrit_host, change_number)
    if not pr_info:
        log.warning(
            "No linked GitHub PR found for change %s. "
            "The change may not have been created by GitHub2Gerrit.",
            change_number,
        )
        # Post a failure message back to Gerrit
        post_gerrit_comment(
            gerrit_host,
            change_number,
            "🦜 Parrotbot: Cannot find linked GitHub PR for this change. "
            "Only changes created by GitHub2Gerrit (with GitHub-PR trailer) "
            "are supported.",
        )
        return False

    # Relay the command to GitHub
    relay_comment = f"@{target_bot} {command}"
    success = post_github_pr_comment(
        pr_info["owner"],
        pr_info["repo"],
        int(pr_info["pr_number"]),
        relay_comment,
    )

    # Post confirmation back to Gerrit
    if success:
        post_gerrit_comment(
            gerrit_host,
            change_number,
            f"🦜 Parrotbot: Relayed `@{target_bot} {command}` to "
            f"{pr_info['url']} on behalf of {author_username}.",
        )
    else:
        post_gerrit_comment(
            gerrit_host,
            change_number,
            f"🦜 Parrotbot: Failed to relay `@{target_bot} {command}` to "
            f"GitHub PR. Check the g2p logs for details.",
        )

    return success
