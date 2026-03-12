# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2026 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Unit tests for parrotbot module.

Tests command parsing, whitelist validation, GitHub PR extraction,
comment relay, and the main handle_parrot_command entry point.
"""

from unittest.mock import MagicMock, patch

import pytest

from gerrit_to_platform.parrotbot import (
    ALLOWED_COMMANDS,
    handle_parrot_command,
    is_parrot_command,
    parse_parrot_command,
)

# ── is_parrot_command ──────────────────────────────────────────────


class TestIsParrotCommand:
    """Test quick boolean check for parrotbot invocations."""

    @pytest.mark.parametrize(
        "comment",
        [
            "@parrot @dependabot recreate",
            "@parrotbot @dependabot recreate",
            "@Parrot @dependabot rebase",
            "@PARROTBOT @renovate[bot] merge",
            "Patch Set 1:\n\n@parrot @dependabot recreate",
            "Some prefix text @parrot @dependabot close",
        ],
    )
    def test_valid_commands_detected(self, comment):
        assert is_parrot_command(comment) is True

    @pytest.mark.parametrize(
        "comment",
        [
            "recheck",
            "remerge",
            "@dependabot recreate",
            "parrot @dependabot recreate",
            "@parrot recreate",
            "@parrot",
            "",
        ],
    )
    def test_non_parrot_comments_rejected(self, comment):
        assert is_parrot_command(comment) is False


# ── parse_parrot_command ───────────────────────────────────────────


class TestParseParrotCommand:
    """Test command extraction and whitelist validation."""

    def test_basic_dependabot_recreate(self):
        result = parse_parrot_command("@parrot @dependabot recreate")
        assert result == {"target_bot": "dependabot", "command": "recreate"}

    def test_parrotbot_alias(self):
        result = parse_parrot_command("@parrotbot @dependabot rebase")
        assert result == {"target_bot": "dependabot", "command": "rebase"}

    def test_case_insensitive(self):
        result = parse_parrot_command("@PARROT @Dependabot RECREATE")
        assert result is not None
        assert result["command"] == "recreate"

    @pytest.mark.parametrize("cmd", sorted(ALLOWED_COMMANDS))
    def test_all_allowed_commands(self, cmd):
        result = parse_parrot_command(f"@parrot @dependabot {cmd}")
        assert result is not None
        assert result["command"] == cmd

    def test_disallowed_command_returns_none(self):
        result = parse_parrot_command("@parrot @dependabot hack")
        assert result is None

    def test_no_match_returns_none(self):
        result = parse_parrot_command("just a regular comment")
        assert result is None

    def test_embedded_in_patchset_comment(self):
        comment = "Patch Set 3:\n\n@parrot @dependabot recreate"
        result = parse_parrot_command(comment)
        assert result == {"target_bot": "dependabot", "command": "recreate"}

    def test_renovate_bot_target(self):
        result = parse_parrot_command("@parrot @renovate[bot] rebase")
        assert result is not None
        assert result["target_bot"] == "renovate[bot]"

    def test_target_bot_with_hyphens(self):
        result = parse_parrot_command("@parrot @my-custom-bot recreate")
        assert result is not None
        assert result["target_bot"] == "my-custom-bot"


# ── extract_github_pr_from_commit ──────────────────────────────────


class TestExtractGithubPrFromCommit:
    """Test Gerrit REST API → GitHub-PR trailer extraction."""

    @patch("gerrit_to_platform.parrotbot.GerritRestAPI")
    def test_extracts_pr_info(self, mock_gerrit_cls):
        """Successfully extract owner/repo/pr_number from trailer."""
        mock_api = MagicMock()
        mock_gerrit_cls.return_value = mock_api

        rev_sha = "abc123"
        mock_api.get.return_value = {
            "current_revision": rev_sha,
            "revisions": {
                rev_sha: {
                    "commit": {
                        "message": (
                            "feat: update deps\n\n"
                            "GitHub-PR: https://github.com/opendaylight/mdsal/pull/3\n"
                            "Change-Id: I1234\n"
                        )
                    }
                }
            },
        }

        from gerrit_to_platform.parrotbot import extract_github_pr_from_commit

        result = extract_github_pr_from_commit("gerrit.example.org", "12345")

        assert result is not None
        assert result["owner"] == "opendaylight"
        assert result["repo"] == "mdsal"
        assert result["pr_number"] == "3"

    def test_no_github_pr_trailer(self):
        """Change without GitHub-PR trailer returns None."""
        result = _call_extract_with_mock_gerrit(
            "gerrit.example.org",
            "99999",
            commit_message="fix: something\n\nChange-Id: I5678\n",
        )

        assert result is None

    def test_missing_current_revision(self):
        """Missing current_revision field returns None."""
        result = _call_extract_with_mock_gerrit(
            "gerrit.example.org",
            "11111",
            commit_message=None,
            current_revision="",
        )

        assert result is None


def _call_extract_with_mock_gerrit(
    gerrit_host,
    change_number,
    commit_message,
    current_revision="abc123",
):
    """Helper to call extract_github_pr_from_commit with mocked GerritRestAPI."""
    mock_api = MagicMock()

    if current_revision and commit_message:
        mock_api.get.return_value = {
            "current_revision": current_revision,
            "revisions": {current_revision: {"commit": {"message": commit_message}}},
        }
    elif not current_revision:
        mock_api.get.return_value = {
            "current_revision": "",
            "revisions": {},
        }
    else:
        mock_api.get.return_value = {
            "current_revision": current_revision,
            "revisions": {
                current_revision: {"commit": {"message": commit_message or ""}}
            },
        }

    with patch("gerrit_to_platform.parrotbot.GerritRestAPI", return_value=mock_api):
        from gerrit_to_platform.parrotbot import extract_github_pr_from_commit

        return extract_github_pr_from_commit(gerrit_host, change_number)


# ── post_github_pr_comment ─────────────────────────────────────────


class TestPostGithubPrComment:
    """Test GitHub PR comment posting."""

    def test_posts_comment_success(self):
        """Successfully post a comment to GitHub PR."""
        mock_ghapi_module = MagicMock()
        mock_api_instance = MagicMock()
        mock_ghapi_module.GhApi.return_value = mock_api_instance

        with patch.dict(
            "sys.modules", {"ghapi.all": mock_ghapi_module, "ghapi": MagicMock()}
        ):
            import importlib

            import gerrit_to_platform.parrotbot as pb

            importlib.reload(pb)
            # Patch get_setting AFTER reload so it isn't overwritten
            with patch.object(pb, "get_setting", return_value="ghp_fake"):
                result = pb.post_github_pr_comment(
                    "opendaylight", "mdsal", 3, "@dependabot recreate"
                )

        assert result is True

    def test_returns_false_on_error(self):
        """API error returns False."""
        mock_ghapi_module = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.issues.create_comment.side_effect = Exception("403")
        mock_ghapi_module.GhApi.return_value = mock_api_instance

        with patch.dict(
            "sys.modules", {"ghapi.all": mock_ghapi_module, "ghapi": MagicMock()}
        ):
            import importlib

            import gerrit_to_platform.parrotbot as pb

            importlib.reload(pb)
            # Patch get_setting AFTER reload so it isn't overwritten
            with patch.object(pb, "get_setting", return_value="ghp_fake"):
                result = pb.post_github_pr_comment(
                    "opendaylight", "mdsal", 3, "@dependabot recreate"
                )

        assert result is False


# ── post_gerrit_comment ────────────────────────────────────────────


class TestPostGerritComment:
    """Test Gerrit comment posting."""

    @patch("gerrit_to_platform.parrotbot.GerritRestAPI")
    def test_posts_comment_success(self, mock_gerrit_cls):
        mock_api = MagicMock()
        mock_gerrit_cls.return_value = mock_api

        from gerrit_to_platform.parrotbot import post_gerrit_comment

        result = post_gerrit_comment("gerrit.example.org", "12345", "test message")

        assert result is True

    @patch("gerrit_to_platform.parrotbot.GerritRestAPI")
    def test_returns_false_on_error(self, mock_gerrit_cls):
        mock_api = MagicMock()
        mock_api.post.side_effect = Exception("network error")
        mock_gerrit_cls.return_value = mock_api

        from gerrit_to_platform.parrotbot import post_gerrit_comment

        result = post_gerrit_comment("gerrit.example.org", "12345", "test message")

        assert result is False


# ── handle_parrot_command ──────────────────────────────────────────


class TestHandleParrotCommand:
    """Test the main entry point orchestrating the full flow."""

    @patch("gerrit_to_platform.parrotbot.post_gerrit_comment")
    @patch("gerrit_to_platform.parrotbot.post_github_pr_comment", return_value=True)
    @patch(
        "gerrit_to_platform.parrotbot.extract_github_pr_from_commit",
        return_value={
            "owner": "opendaylight",
            "repo": "mdsal",
            "pr_number": "3",
            "url": "https://github.com/opendaylight/mdsal/pull/3",
        },
    )
    @patch("gerrit_to_platform.parrotbot.check_user_authorized", return_value=True)
    @patch("gerrit_to_platform.parrotbot.get_setting", return_value="true")
    def test_successful_relay(
        self,
        mock_enabled,
        mock_auth,
        mock_extract,
        mock_post_gh,
        mock_post_gerrit,
    ):
        """Full successful flow: parse → auth → extract PR → relay → confirm."""
        result = handle_parrot_command(
            comment="@parrot @dependabot recreate",
            change_number="12345",
            change_url="https://gerrit.example.org/r/c/project/+/12345",
            author_username="rvarga",
            project="opendaylight/mdsal",
        )

        assert result is True
        mock_auth.assert_called_once_with(
            "gerrit.example.org", "opendaylight/mdsal", "rvarga"
        )
        mock_post_gh.assert_called_once_with(
            "opendaylight", "mdsal", 3, "@dependabot recreate"
        )
        # Confirmation posted back to Gerrit
        assert mock_post_gerrit.call_count >= 1
        confirm_msg = mock_post_gerrit.call_args[0][2]
        assert "Relayed" in confirm_msg

    @patch("gerrit_to_platform.parrotbot.get_setting", return_value="false")
    def test_disabled_returns_false(self, mock_enabled):
        """Parrotbot disabled in config → returns False."""
        result = handle_parrot_command(
            comment="@parrot @dependabot recreate",
            change_number="12345",
            change_url="https://gerrit.example.org/r/c/project/+/12345",
            author_username="rvarga",
            project="opendaylight/mdsal",
        )

        assert result is False

    @patch("gerrit_to_platform.parrotbot.post_gerrit_comment")
    @patch("gerrit_to_platform.parrotbot.check_user_authorized", return_value=False)
    @patch("gerrit_to_platform.parrotbot.get_setting", return_value="true")
    def test_unauthorized_user_rejected(
        self, mock_enabled, mock_auth, mock_post_gerrit
    ):
        """Unauthorized user → rejection comment posted to Gerrit."""
        result = handle_parrot_command(
            comment="@parrot @dependabot recreate",
            change_number="12345",
            change_url="https://gerrit.example.org/r/c/project/+/12345",
            author_username="random-user",
            project="opendaylight/mdsal",
        )

        assert result is False
        mock_auth.assert_called_once_with(
            "gerrit.example.org", "opendaylight/mdsal", "random-user"
        )
        mock_post_gerrit.assert_called_once()
        msg = mock_post_gerrit.call_args[0][2]
        assert "not a committer" in msg

    def test_invalid_command_returns_false(self):
        """Non-parrotbot comment → False."""
        result = handle_parrot_command(
            comment="recheck",
            change_number="12345",
            change_url="https://gerrit.example.org/r/c/project/+/12345",
            author_username="rvarga",
            project="opendaylight/mdsal",
        )

        assert result is False

    @patch("gerrit_to_platform.parrotbot.post_gerrit_comment")
    @patch(
        "gerrit_to_platform.parrotbot.extract_github_pr_from_commit",
        return_value=None,
    )
    @patch("gerrit_to_platform.parrotbot.check_user_authorized", return_value=True)
    @patch("gerrit_to_platform.parrotbot.get_setting", return_value="true")
    def test_no_linked_pr_posts_failure(
        self, mock_enabled, mock_auth, mock_extract, mock_post_gerrit
    ):
        """No linked GitHub PR → failure comment on Gerrit."""
        result = handle_parrot_command(
            comment="@parrot @dependabot recreate",
            change_number="12345",
            change_url="https://gerrit.example.org/r/c/project/+/12345",
            author_username="rvarga",
            project="opendaylight/mdsal",
        )

        assert result is False
        mock_post_gerrit.assert_called_once()
        msg = mock_post_gerrit.call_args[0][2]
        assert "Cannot find linked GitHub PR" in msg

    @patch("gerrit_to_platform.parrotbot.post_gerrit_comment")
    @patch("gerrit_to_platform.parrotbot.post_github_pr_comment", return_value=False)
    @patch(
        "gerrit_to_platform.parrotbot.extract_github_pr_from_commit",
        return_value={
            "owner": "opendaylight",
            "repo": "mdsal",
            "pr_number": "3",
            "url": "https://github.com/opendaylight/mdsal/pull/3",
        },
    )
    @patch("gerrit_to_platform.parrotbot.check_user_authorized", return_value=True)
    @patch("gerrit_to_platform.parrotbot.get_setting", return_value="true")
    def test_github_post_failure(
        self,
        mock_enabled,
        mock_auth,
        mock_extract,
        mock_post_gh,
        mock_post_gerrit,
    ):
        """GitHub comment fails → failure message on Gerrit."""
        result = handle_parrot_command(
            comment="@parrot @dependabot recreate",
            change_number="12345",
            change_url="https://gerrit.example.org/r/c/project/+/12345",
            author_username="rvarga",
            project="opendaylight/mdsal",
        )

        assert result is False
        msg = mock_post_gerrit.call_args[0][2]
        assert "Failed to relay" in msg

    def test_bad_change_url_returns_false(self):
        """Malformed change URL → cannot extract host → False."""
        with patch(
            "gerrit_to_platform.parrotbot.get_setting",
            return_value=True,
        ):
            result = handle_parrot_command(
                comment="@parrot @dependabot recreate",
                change_number="12345",
                change_url="not-a-url",
                author_username="rvarga",
                project="opendaylight/mdsal",
            )

        assert result is False


# ── comment_added integration ──────────────────────────────────────


class TestCommentAddedParrotIntegration:
    """Test that comment_added correctly routes parrot commands."""

    def test_parrot_comment_routes_to_handler(self, mocker):
        """Parrotbot comment triggers handler, not workflow dispatch."""
        from typer.testing import CliRunner

        from gerrit_to_platform.comment_added import app

        mock_handle = mocker.patch(
            "gerrit_to_platform.comment_added.handle_parrot_command",
            return_value=True,
        )
        mock_mapping = mocker.patch(
            "gerrit_to_platform.comment_added.get_mapping",
            return_value={"recheck": "verify"},
        )

        args = [
            "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
            "--change-url=https://gerrit.example.org/r/c/example/project/+/1",
            "--change-owner=Foo <foo@example.org>",
            "--change-owner-username=foo",
            "--project=example/project",
            "--branch=master",
            "--topic=testing",
            "--author=Foo <foo@example.org>",
            "--author-username=foo",
            "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
            "--comment=Patch Set 1:\n\n@parrot @dependabot recreate",
            "--Code-Review=0",
        ]

        runner = CliRunner()
        result = runner.invoke(app, args)

        assert result.exit_code == 0
        mock_handle.assert_called_once()
        # Should NOT hit regular workflow dispatch
        mock_mapping.assert_not_called()

    def test_non_parrot_comment_hits_dispatch(self, mocker):
        """Regular recheck still goes through normal dispatch flow."""
        from typer.testing import CliRunner

        from gerrit_to_platform.comment_added import app

        mock_handle = mocker.patch(
            "gerrit_to_platform.comment_added.handle_parrot_command",
        )
        mocker.patch(
            "gerrit_to_platform.comment_added.get_mapping",
            return_value={"recheck": "verify"},
        )
        mocker.patch(
            "gerrit_to_platform.comment_added.find_and_dispatch",
            side_effect=lambda p, w, i: print(f"Dispatched {w}"),
        )

        args = [
            "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
            "--change-url=https://gerrit.example.org/r/c/example/project/+/1",
            "--change-owner=Foo <foo@example.org>",
            "--change-owner-username=foo",
            "--project=example/project",
            "--branch=master",
            "--topic=testing",
            "--author=Foo <foo@example.org>",
            "--author-username=foo",
            "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
            """--comment=Patch Set 1:\n\nrecheck""",
            "--Code-Review=0",
        ]

        runner = CliRunner()
        result = runner.invoke(app, args)

        assert result.exit_code == 0
        # Parrotbot handler should NOT be called for regular comments
        mock_handle.assert_not_called()
