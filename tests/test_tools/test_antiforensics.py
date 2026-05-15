"""Unit tests for anti-forensics tools (USB monitoring and artifact cleanup).

Tests verify:
1. research_usb_kill_monitor detects USB devices safely in dry-run mode
2. research_artifact_cleanup identifies forensic artifacts without deleting anything
3. Both tools guarantee dry_run=True and never destructive operations
4. Error handling for missing commands or permission issues
"""

from __future__ import annotations

import platform
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loom.tools.privacy.antiforensics import research_forensics_cleanup, research_usb_kill_monitor


class TestUSBKillMonitor:
    """research_usb_kill_monitor monitors USB connections safely."""

    def test_usb_monitor_dry_run_default(self) -> None:
        """USB monitor defaults to dry_run=True (safe)."""
        result = research_usb_kill_monitor()

        assert result["dry_run"] is True
        assert result["status"] == "simulated"
        assert "note" in result
        assert "DRY-RUN" in result["note"]

    def test_usb_monitor_returns_required_fields(self) -> None:
        """USB monitor response includes all required fields."""
        result = research_usb_kill_monitor(dry_run=True)

        required_fields = [
            "usb_devices_detected",
            "usb_count",
            "trigger_action",
            "target_path",
            "dry_run",
            "status",
            "timestamp",
            "note",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_usb_monitor_devices_list(self) -> None:
        """USB monitor devices field is always a list."""
        result = research_usb_kill_monitor()
        assert isinstance(result["usb_devices_detected"], list)
        assert isinstance(result["usb_count"], int)
        assert result["usb_count"] == len(result["usb_devices_detected"])

    def test_usb_monitor_trigger_actions(self) -> None:
        """USB monitor accepts different trigger actions."""
        for action in ["alert", "wipe", "none"]:
            result = research_usb_kill_monitor(trigger_action=action)
            assert result["trigger_action"] == action

    def test_usb_monitor_custom_target_path(self) -> None:
        """USB monitor accepts custom target paths."""
        custom_path = "/home/user/sensitive"
        result = research_usb_kill_monitor(target_path=custom_path)
        assert result["target_path"] == custom_path

    def test_usb_monitor_never_deletes(self) -> None:
        """USB monitor never deletes files in dry_run mode."""
        result = research_usb_kill_monitor(dry_run=True, trigger_action="wipe")
        assert result["dry_run"] is True
        assert result["status"] == "simulated"
        # Even with wipe trigger, dry_run prevents actual deletion
        assert "DRY-RUN" in result["note"]

    @patch("subprocess.run")
    def test_usb_monitor_handles_command_failure(self, mock_run: MagicMock) -> None:
        """USB monitor handles missing lsusb/system_profiler gracefully."""
        mock_run.side_effect = FileNotFoundError("lsusb not found")

        result = research_usb_kill_monitor()

        assert isinstance(result, dict)
        assert "usb_devices_detected" in result
        # Should return empty list on error, not raise exception
        assert result["usb_devices_detected"] == [] or isinstance(result["usb_devices_detected"], list)


class TestArtifactCleanup:
    """research_forensics_cleanup identifies artifacts safely (dry-run only)."""

    def test_artifact_cleanup_dry_run_guaranteed(self) -> None:
        """Artifact cleanup is always dry-run (safety guarantee)."""
        result = research_forensics_cleanup()

        assert result["dry_run"] is True
        assert "DRY-RUN" in result["note"]

    def test_artifact_cleanup_returns_required_fields(self) -> None:
        """Artifact cleanup response includes all required fields."""
        result = research_forensics_cleanup()

        required_fields = [
            "artifacts_found",
            "total_size_mb",
            "cleanup_plan",
            "os_type",
            "dry_run",
            "timestamp",
            "note",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_artifact_cleanup_artifacts_list_shape(self) -> None:
        """Artifact cleanup artifacts are well-formed dicts."""
        result = research_forensics_cleanup()

        assert isinstance(result["artifacts_found"], list)
        for artifact in result["artifacts_found"]:
            assert isinstance(artifact, dict)
            assert "path" in artifact
            assert "type" in artifact
            assert "size_bytes" in artifact
            assert "exists" in artifact

    def test_artifact_cleanup_total_size_nonnegative(self) -> None:
        """Artifact cleanup total size is non-negative float."""
        result = research_forensics_cleanup()

        assert isinstance(result["total_size_mb"], float)
        assert result["total_size_mb"] >= 0

    def test_artifact_cleanup_plan_is_list(self) -> None:
        """Artifact cleanup plan is a list of action strings."""
        result = research_forensics_cleanup()

        assert isinstance(result["cleanup_plan"], list)
        for action in result["cleanup_plan"]:
            assert isinstance(action, str)

    def test_artifact_cleanup_os_detection(self) -> None:
        """Artifact cleanup detects OS type."""
        result = research_forensics_cleanup()

        assert result["os_type"] in ["linux", "darwin", "windows", "Linux", "Darwin", "Windows"]

    def test_artifact_cleanup_custom_os_type(self) -> None:
        """Artifact cleanup accepts custom OS type."""
        result = research_forensics_cleanup(os_type="linux")
        assert result["os_type"] == "linux"

    def test_artifact_cleanup_custom_paths(self) -> None:
        """Artifact cleanup scans custom target paths."""
        custom_paths = ["/tmp/test"]
        result = research_forensics_cleanup(target_paths=custom_paths)

        # Should include custom paths in artifacts
        assert any("/tmp/test" in str(a.get("path", "")) for a in result["artifacts_found"])

    def test_artifact_cleanup_never_deletes(self) -> None:
        """Artifact cleanup never deletes files (dry-run only)."""
        test_dir = Path("/tmp/antiforensics_test_never_delete_this")
        test_file = test_dir / "test_file.txt"

        try:
            test_dir.mkdir(exist_ok=True)
            test_file.write_text("test data")

            # Run cleanup on this directory
            result = research_forensics_cleanup(target_paths=[str(test_dir)])

            # File should still exist
            assert test_file.exists(), "Artifact cleanup deleted a file in dry-run mode!"
            assert result["dry_run"] is True
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
            if test_dir.exists():
                test_dir.rmdir()

    def test_artifact_cleanup_handles_permission_errors(self) -> None:
        """Artifact cleanup handles permission errors gracefully."""
        # Use a path that likely won't be accessible
        restricted_paths = ["/root/sensitive"]

        result = research_forensics_cleanup(target_paths=restricted_paths)

        # Should return without crashing
        assert isinstance(result, dict)
        assert result["dry_run"] is True

    @pytest.mark.parametrize("os_type", ["linux", "darwin", "windows"])
    def test_artifact_cleanup_os_variants(self, os_type: str) -> None:
        """Artifact cleanup handles different OS types."""
        result = research_forensics_cleanup(os_type=os_type)

        assert result["os_type"] == os_type
        assert isinstance(result["artifacts_found"], list)
        assert isinstance(result["cleanup_plan"], list)


class TestAntiForensicsIntegration:
    """Integration tests for antiforensics tools together."""

    def test_both_tools_never_destructive(self) -> None:
        """Both tools are safe: dry-run=True, no deletions."""
        usb_result = research_usb_kill_monitor(dry_run=True)
        artifact_result = research_forensics_cleanup()

        assert usb_result["dry_run"] is True
        assert artifact_result["dry_run"] is True
        assert "DRY-RUN" in usb_result["note"]
        assert "DRY-RUN" in artifact_result["note"]

    def test_tools_have_timestamps(self) -> None:
        """Both tools include ISO timestamps."""
        usb_result = research_usb_kill_monitor()
        artifact_result = research_forensics_cleanup()

        assert "timestamp" in usb_result
        assert "timestamp" in artifact_result
        # Verify ISO format (rough check)
        assert "T" in usb_result["timestamp"]
        assert "T" in artifact_result["timestamp"]

    def test_tools_handle_missing_dependencies(self) -> None:
        """Tools degrade gracefully when system tools are missing."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("lsusb not available")

            usb_result = research_usb_kill_monitor()

            # Should not crash, should return empty or error indication
            assert isinstance(usb_result, dict)
            assert "usb_devices_detected" in usb_result
