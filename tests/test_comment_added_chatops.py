# SPDX-License-Identifier: Apache-2.0
##############################################################################
# Copyright (c) 2023 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Apache-2.0 license which accompanies this
# distribution, and is available at
# https://opensource.org/licenses/Apache-2.0
##############################################################################
"""Unit tests for comment_added ChatOps functionality."""

import os
import tempfile
import time
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import gerrit_to_platform.comment_added
from gerrit_to_platform.comment_added import app, check_cooldown

# Test fixtures for ChatOps commands
CHATOPS_CSIT = [
    "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
    "--change-url=https://gerrit.example.org/r/c/example/project/+/12345",
    "--change-owner='Foo <foo@example.org>'",
    "--change-owner-username=foo",
    "--project=example/project",
    "--branch=master",
    "--topic=testing",
    "--author='Foo <foo@example.org>'",
    "--author-username=foo",
    "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
    """--comment=Patch Set 1:

gha-run csit-2n-perftest nic=intel-e810cq drv=avf""",
    "--Code-Review=0",
]

CHATOPS_TERRAFORM = [
    "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
    "--change-url=https://gerrit.example.org/r/c/example/project/+/12345",
    "--change-owner='Foo <foo@example.org>'",
    "--change-owner-username=foo",
    "--project=example/project",
    "--branch=master",
    "--topic=testing",
    "--author='Foo <foo@example.org>'",
    "--author-username=foo",
    "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
    """--comment=Patch Set 1:

gha-run terraform-cdash-deploy env=production""",
    "--Code-Review=0",
]

CHATOPS_MULTILINE = [
    "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
    "--change-url=https://gerrit.example.org/r/c/example/project/+/12345",
    "--change-owner='Foo <foo@example.org>'",
    "--change-owner-username=foo",
    "--project=example/project",
    "--branch=master",
    "--topic=testing",
    "--author='Foo <foo@example.org>'",
    "--author-username=foo",
    "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
    """--comment=Patch Set 1:

Here is my comment about the change.

gha-run csit-2n-perftest nic=intel-e810cq

This should trigger the workflow.""",
    "--Code-Review=0",
]

CHATOPS_QUOTED = [
    "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
    "--change-url=https://gerrit.example.org/r/c/example/project/+/12345",
    "--change-owner='Foo <foo@example.org>'",
    "--change-owner-username=foo",
    "--project=example/project",
    "--branch=master",
    "--topic=testing",
    "--author='Foo <foo@example.org>'",
    "--author-username=foo",
    "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
    """--comment=Patch Set 1:

> gha-run should-be-ignored

gha-run csit-2n-perftest nic=intel-e810cq""",
    "--Code-Review=0",
]

CHATOPS_NO_COMMAND = [
    "--change=example/project~master~I308b4eda73ff90ee486f14e01db145684889eaae",
    "--change-url=https://gerrit.example.org/r/c/example/project/+/12345",
    "--change-owner='Foo <foo@example.org>'",
    "--change-owner-username=foo",
    "--project=example/project",
    "--branch=master",
    "--topic=testing",
    "--author='Foo <foo@example.org>'",
    "--author-username=foo",
    "--commit=7f0f8a2b05546d5956b0bb1431ba13c8cbe94631",
    """--comment=Patch Set 1:

Just a regular comment without any commands.""",
    "--Code-Review=0",
]

runner = CliRunner()


class TestCheckCooldown:
    """Tests for check_cooldown function."""

    def setup_method(self):
        """Clean up cooldown files before each test."""
        # Clean up any existing test cooldown files
        for f in Path("/tmp").glob("gha_cooldown_*"):
            try:
                f.unlink()
            except OSError:
                pass

    def teardown_method(self):
        """Clean up cooldown files after each test."""
        for f in Path("/tmp").glob("gha_cooldown_*"):
            try:
                f.unlink()
            except OSError:
                pass

    def test_cooldown_allows_first_trigger(self):
        """Test that cooldown allows first trigger."""
        result = check_cooldown("12345", "test-workflow")
        assert result is True

    def test_cooldown_blocks_second_trigger(self):
        """Test that cooldown blocks immediate second trigger."""
        # First trigger
        result1 = check_cooldown("12345", "test-workflow")
        assert result1 is True

        # Second trigger immediately after
        result2 = check_cooldown("12345", "test-workflow")
        assert result2 is False

    def test_cooldown_allows_different_workflows(self):
        """Test that cooldown is per-workflow."""
        # Trigger workflow1
        result1 = check_cooldown("12345", "workflow1")
        assert result1 is True

        # Trigger workflow2 on same change
        result2 = check_cooldown("12345", "workflow2")
        assert result2 is True

    def test_cooldown_allows_different_changes(self):
        """Test that cooldown is per-change."""
        # Trigger on change 1
        result1 = check_cooldown("12345", "test-workflow")
        assert result1 is True

        # Trigger same workflow on change 2
        result2 = check_cooldown("67890", "test-workflow")
        assert result2 is True

    def test_cooldown_expires_after_timeout(self):
        """Test that cooldown expires after COOLDOWN_SECONDS."""
        # First trigger
        result1 = check_cooldown("12345", "test-workflow")
        assert result1 is True

        # Mock time to be COOLDOWN_SECONDS + 1 in the future
        with patch("gerrit_to_platform.comment_added.time") as mock_time:
            cooldown_file = Path("/tmp/gha_cooldown_12345_test-workflow")
            original_mtime = cooldown_file.stat().st_mtime
            mock_time.time.return_value = original_mtime + 301  # COOLDOWN_SECONDS + 1

            result2 = check_cooldown("12345", "test-workflow")
            assert result2 is True


class TestChatOpsCommandParsing:
    """Tests for ChatOps command parsing."""

    def setup_method(self):
        """Set up mocks for each test."""
        self.mock_get_mapping_patcher = patch(
            "gerrit_to_platform.comment_added.get_mapping",
            return_value=None  # Disable legacy mapping
        )
        self.mock_find_and_dispatch_patcher = patch(
            "gerrit_to_platform.comment_added.find_and_dispatch",
            return_value=1  # Simulate successful dispatch
        )
        self.mock_check_cooldown_patcher = patch(
            "gerrit_to_platform.comment_added.check_cooldown",
            return_value=True  # Allow all triggers
        )

        self.mock_get_mapping = self.mock_get_mapping_patcher.start()
        self.mock_find_and_dispatch = self.mock_find_and_dispatch_patcher.start()
        self.mock_check_cooldown = self.mock_check_cooldown_patcher.start()

    def teardown_method(self):
        """Clean up mocks after each test."""
        self.mock_get_mapping_patcher.stop()
        self.mock_find_and_dispatch_patcher.stop()
        self.mock_check_cooldown_patcher.stop()

    def test_chatops_csit_command(self):
        """Test CSIT ChatOps command triggers workflow."""
        result = runner.invoke(app, CHATOPS_CSIT)
        assert result.exit_code == 0

        # Verify cooldown was checked
        self.mock_check_cooldown.assert_called_once_with("12345", "csit-2n-perftest")

        # Verify workflow was dispatched
        self.mock_find_and_dispatch.assert_called_once()
        args = self.mock_find_and_dispatch.call_args
        assert args[0][0] == "example/project"  # project
        assert args[0][1] == "comment-handler"  # workflow filter
        assert args[0][2]["GERRIT_COMMENT"] == "gha-run csit-2n-perftest nic=intel-e810cq drv=avf"

    def test_chatops_terraform_command(self):
        """Test Terraform ChatOps command triggers workflow."""
        result = runner.invoke(app, CHATOPS_TERRAFORM)
        assert result.exit_code == 0

        # Verify cooldown was checked
        self.mock_check_cooldown.assert_called_once_with("12345", "terraform-cdash-deploy")

        # Verify workflow was dispatched
        self.mock_find_and_dispatch.assert_called_once()
        args = self.mock_find_and_dispatch.call_args
        assert args[0][2]["GERRIT_COMMENT"] == "gha-run terraform-cdash-deploy env=production"

    def test_chatops_multiline_comment(self):
        """Test ChatOps command in multiline comment."""
        result = runner.invoke(app, CHATOPS_MULTILINE)
        assert result.exit_code == 0

        # Should find the command in the middle of the comment
        self.mock_check_cooldown.assert_called_once_with("12345", "csit-2n-perftest")
        self.mock_find_and_dispatch.assert_called_once()

    def test_chatops_ignores_quoted_commands(self):
        """Test that quoted commands are ignored."""
        result = runner.invoke(app, CHATOPS_QUOTED)
        assert result.exit_code == 0

        # Should use the non-quoted command
        self.mock_check_cooldown.assert_called_once_with("12345", "csit-2n-perftest")
        args = self.mock_find_and_dispatch.call_args
        assert "should-be-ignored" not in args[0][2]["GERRIT_COMMENT"]

    def test_no_chatops_command_falls_back_to_legacy(self):
        """Test that comments without ChatOps fall back to legacy mapping."""
        # Re-enable legacy mapping for this test
        self.mock_get_mapping.return_value = {"recheck": "verify"}

        result = runner.invoke(app, CHATOPS_NO_COMMAND)
        assert result.exit_code == 0

        # Cooldown should not be checked (no ChatOps command)
        self.mock_check_cooldown.assert_not_called()

        # Legacy mapping should be queried
        self.mock_get_mapping.assert_called_once()

    def test_cooldown_blocks_dispatch(self):
        """Test that cooldown prevents workflow dispatch."""
        # Make cooldown return False
        self.mock_check_cooldown.return_value = False

        result = runner.invoke(app, CHATOPS_CSIT)
        assert result.exit_code == 0

        # Cooldown should be checked
        self.mock_check_cooldown.assert_called_once()

        # Workflow should NOT be dispatched
        self.mock_find_and_dispatch.assert_not_called()

    def test_no_workflows_found(self):
        """Test handling when no workflows match."""
        # Make find_and_dispatch return 0 (no workflows found)
        self.mock_find_and_dispatch.return_value = 0

        result = runner.invoke(app, CHATOPS_CSIT)
        assert result.exit_code == 0
        assert "No workflows found matching 'comment-handler'" in result.stdout
        assert "gha-run csit-2n-perftest" in result.stdout

    def test_dispatch_exception_handling(self):
        """Test exception handling during dispatch."""
        # Make find_and_dispatch raise an exception
        self.mock_find_and_dispatch.side_effect = Exception("API Error")

        result = runner.invoke(app, CHATOPS_CSIT)
        assert result.exit_code != 0  # Should fail with exception
        assert "Error dispatching workflow" in result.stdout


class TestChatOpsSecurityAndEdgeCases:
    """Tests for security and edge cases."""

    def test_empty_comment(self):
        """Test handling of comment with only Patch Set header (no user text)."""
        # Gerrit always includes "Patch Set X:" header, even for empty comments
        empty_comment = CHATOPS_CSIT.copy()
        empty_comment[10] = "--comment=Patch Set 1:"

        with patch("gerrit_to_platform.comment_added.get_mapping", return_value=None):
            result = runner.invoke(app, empty_comment)
            # Should handle gracefully (no ChatOps command, falls back to legacy)
            assert result.exit_code == 0

    def test_malformed_command(self):
        """Test handling of malformed ChatOps command."""
        malformed = CHATOPS_CSIT.copy()
        malformed[10] = """--comment=Patch Set 1:

gha-run"""  # No workflow name

        with patch("gerrit_to_platform.comment_added.get_mapping", return_value=None):
            with patch("gerrit_to_platform.comment_added.check_cooldown", return_value=True):
                with patch("gerrit_to_platform.comment_added.find_and_dispatch", return_value=0):
                    result = runner.invoke(app, malformed)
                    # Should handle gracefully
                    assert result.exit_code == 0

    def test_multiple_commands_only_first_processed(self):
        """Test that only first command is processed."""
        multi_cmd = CHATOPS_CSIT.copy()
        multi_cmd[10] = """--comment=Patch Set 1:

gha-run workflow1
gha-run workflow2"""

        with patch("gerrit_to_platform.comment_added.get_mapping", return_value=None):
            with patch("gerrit_to_platform.comment_added.check_cooldown", return_value=True) as mock_cooldown:
                with patch("gerrit_to_platform.comment_added.find_and_dispatch", return_value=1):
                    result = runner.invoke(app, multi_cmd)
                    assert result.exit_code == 0

                    # Should only check cooldown for first command
                    mock_cooldown.assert_called_once_with("12345", "workflow1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
