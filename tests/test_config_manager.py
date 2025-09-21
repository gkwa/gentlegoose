import json
import pathlib
import unittest.mock

import pytest

import gentlegoose.config_manager
import gentlegoose.file_handler


class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_sync_global_gitignore_adds_missing_patterns_with_update_flag(
        self,
        config_manager: gentlegoose.config_manager.ConfigManager,
        zed_settings_dir: pathlib.Path,
        mock_global_gitignore: pathlib.Path,
    ) -> None:
        """Test missing patterns are added when update_existing=True."""
        # Create existing Zed settings with some patterns
        settings_file = zed_settings_dir / "settings.json"
        existing_settings = {
            "file_scan_exclusions": [
                "**/.git",
                "**/node_modules/",
                "**/.env",  # This one overlaps with global
            ]
        }
        settings_file.write_text(
            json.dumps(existing_settings, indent=2), encoding="utf-8"
        )

        # Mock the file handler methods to return our test data
        expected_global_patterns = [
            "**/.env",
            "**/.fmt/",
            "**/.terraform.lock.hcl",
            "**/.DS_Store",
            "**/scratch/",
            "**/*.log",
            "**/__pycache__/",
            "**/.vscode/",
        ]

        with (
            unittest.mock.patch.object(
                config_manager.file_handler,
                "get_global_gitignore_path",
                return_value=mock_global_gitignore,
            ),
            unittest.mock.patch.object(
                config_manager.file_handler,
                "read_gitignore_patterns",
                return_value=expected_global_patterns,
            ),
        ):
            # Run the sync operation with update_existing=True
            result = config_manager.sync_global_gitignore_to_zed(
                str(settings_file), update_existing=True
            )

        # Verify success
        assert result is True

        # Read the updated settings
        updated_content = settings_file.read_text(encoding="utf-8")
        updated_settings = json.loads(updated_content)

        # Verify the structure
        assert "file_scan_exclusions" in updated_settings
        exclusions = updated_settings["file_scan_exclusions"]

        # Original patterns should be preserved
        assert "**/.git" in exclusions
        assert "**/node_modules/" in exclusions
        assert "**/.env" in exclusions

        # New patterns from global should be added
        expected_new_patterns = [
            "**/.fmt/",
            "**/.terraform.lock.hcl",
            "**/.DS_Store",
            "**/scratch/",
            "**/*.log",
            "**/__pycache__/",
            "**/.vscode/",
        ]

        for pattern in expected_new_patterns:
            assert pattern in exclusions

        # Verify no duplicates
        assert exclusions.count("**/.env") == 1

        # Verify order (existing first, then new)
        assert exclusions[:3] == [
            "**/.git",
            "**/node_modules/",
            "**/.env",
        ]

    def test_sync_skips_update_when_file_exists_and_no_update_flag(
        self,
        config_manager: gentlegoose.config_manager.ConfigManager,
        zed_settings_dir: pathlib.Path,
        mock_global_gitignore: pathlib.Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that existing settings are not updated without update_existing=True."""
        caplog.set_level("INFO")

        # Create existing Zed settings
        settings_file = zed_settings_dir / "settings.json"
        existing_settings = {
            "file_scan_exclusions": [
                "**/.git",
                "**/node_modules/",
            ]
        }
        original_content = json.dumps(existing_settings, indent=2)
        settings_file.write_text(original_content, encoding="utf-8")

        expected_global_patterns = [
            "**/.env",
            "**/.DS_Store",
        ]

        with (
            unittest.mock.patch.object(
                config_manager.file_handler,
                "get_global_gitignore_path",
                return_value=mock_global_gitignore,
            ),
            unittest.mock.patch.object(
                config_manager.file_handler,
                "read_gitignore_patterns",
                return_value=expected_global_patterns,
            ),
        ):
            # Run without update_existing flag
            result = config_manager.sync_global_gitignore_to_zed(str(settings_file))

        # Should return success but not modify file
        assert result is True

        # File should be unchanged
        updated_content = settings_file.read_text(encoding="utf-8")
        assert updated_content == original_content

        # Should have logged that update was skipped
        assert "Settings file exists. Use --update-existing" in caplog.text

    def test_sync_with_empty_project_settings(
        self,
        config_manager: gentlegoose.config_manager.ConfigManager,
        temp_dir: pathlib.Path,
        mock_global_gitignore: pathlib.Path,
    ) -> None:
        """Test syncing when project has no existing settings (file doesn't exist)."""
        # Create a settings file path in the temp directory
        settings_file = temp_dir / "settings.json"

        expected_global_patterns = [
            "**/.env",
            "**/.fmt/",
            "**/.DS_Store",
        ]

        with (
            unittest.mock.patch.object(
                config_manager.file_handler,
                "get_global_gitignore_path",
                return_value=mock_global_gitignore,
            ),
            unittest.mock.patch.object(
                config_manager.file_handler,
                "read_gitignore_patterns",
                return_value=expected_global_patterns,
            ),
        ):
            # Should create new file even without update_existing flag
            result = config_manager.sync_global_gitignore_to_zed(str(settings_file))

        assert result is True

        # Verify settings file was created
        assert settings_file.exists()

        # Verify content
        content = json.loads(settings_file.read_text(encoding="utf-8"))
        assert content["file_scan_exclusions"] == expected_global_patterns

    def test_sync_with_all_patterns_already_present(
        self,
        config_manager: gentlegoose.config_manager.ConfigManager,
        zed_settings_dir: pathlib.Path,
        mock_global_gitignore: pathlib.Path,
    ) -> None:
        """Test that no changes are made when all patterns already exist."""
        global_patterns = ["**/.env", "**/.DS_Store"]

        # Create settings with all global patterns already present
        settings_file = zed_settings_dir / "settings.json"
        existing_settings = {
            "file_scan_exclusions": [
                "**/.git",
                "**/.env",
                "**/.DS_Store",
                "**/node_modules/",
            ]
        }
        original_content = json.dumps(existing_settings, indent=2)
        settings_file.write_text(original_content, encoding="utf-8")

        with (
            unittest.mock.patch.object(
                config_manager.file_handler,
                "get_global_gitignore_path",
                return_value=mock_global_gitignore,
            ),
            unittest.mock.patch.object(
                config_manager.file_handler,
                "read_gitignore_patterns",
                return_value=global_patterns,
            ),
        ):
            result = config_manager.sync_global_gitignore_to_zed(
                str(settings_file), update_existing=True
            )

        assert result is True

        # File should be unchanged
        updated_content = settings_file.read_text(encoding="utf-8")
        updated_settings = json.loads(updated_content)

        assert updated_settings == existing_settings

    def test_dry_run_mode(
        self,
        dry_run_config_manager: gentlegoose.config_manager.ConfigManager,
        zed_settings_dir: pathlib.Path,
        mock_global_gitignore: pathlib.Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that dry run mode doesn't modify files."""
        # Set the log level to INFO so we can capture the dry run messages
        caplog.set_level("INFO")

        settings_file = zed_settings_dir / "settings.json"
        original_settings = {"file_scan_exclusions": ["**/.git"]}
        original_content = json.dumps(original_settings, indent=2)
        settings_file.write_text(original_content, encoding="utf-8")

        global_patterns = ["**/.env", "**/.DS_Store"]

        with (
            unittest.mock.patch.object(
                dry_run_config_manager.file_handler,
                "get_global_gitignore_path",
                return_value=mock_global_gitignore,
            ),
            unittest.mock.patch.object(
                dry_run_config_manager.file_handler,
                "read_gitignore_patterns",
                return_value=global_patterns,
            ),
        ):
            result = dry_run_config_manager.sync_global_gitignore_to_zed(
                str(settings_file), update_existing=True
            )

        assert result is True

        # File should be unchanged
        updated_content = settings_file.read_text(encoding="utf-8")
        assert updated_content == original_content

        # Should have logged what would be done
        assert "Would update:" in caplog.text
        assert "Would add 2 new patterns:" in caplog.text

    def test_preserves_project_specific_exclusions(
        self,
        config_manager: gentlegoose.config_manager.ConfigManager,
        zed_settings_dir: pathlib.Path,
        mock_global_gitignore: pathlib.Path,
    ) -> None:
        """Test that project-specific exclusions not in global are preserved."""
        settings_file = zed_settings_dir / "settings.json"
        existing_settings = {
            "file_scan_exclusions": [
                "**/.git",
                "**/custom-build/",  # Project-specific, not in global
                "**/temp-cache/",  # Another project-specific pattern
                "**/.env",  # This one is in global
            ]
        }
        settings_file.write_text(
            json.dumps(existing_settings, indent=2), encoding="utf-8"
        )

        global_patterns = [
            "**/.env",
            "**/.DS_Store",  # This should be added
            "**/*.log",  # This should be added
        ]

        with (
            unittest.mock.patch.object(
                config_manager.file_handler,
                "get_global_gitignore_path",
                return_value=mock_global_gitignore,
            ),
            unittest.mock.patch.object(
                config_manager.file_handler,
                "read_gitignore_patterns",
                return_value=global_patterns,
            ),
        ):
            result = config_manager.sync_global_gitignore_to_zed(
                str(settings_file), update_existing=True
            )

        assert result is True

        # Read the updated settings
        updated_content = settings_file.read_text(encoding="utf-8")
        updated_settings = json.loads(updated_content)
        exclusions = updated_settings["file_scan_exclusions"]

        # All original project-specific patterns should be preserved
        assert "**/.git" in exclusions
        assert "**/custom-build/" in exclusions
        assert "**/temp-cache/" in exclusions
        assert "**/.env" in exclusions

        # New global patterns should be added
        assert "**/.DS_Store" in exclusions
        assert "**/*.log" in exclusions

        # Verify no duplicates of .env
        assert exclusions.count("**/.env") == 1

        # Verify project patterns come first (preserve original order)
        assert exclusions[:4] == [
            "**/.git",
            "**/custom-build/",
            "**/temp-cache/",
            "**/.env",
        ]

    def test_preserves_non_exclusion_settings(
        self,
        config_manager: gentlegoose.config_manager.ConfigManager,
        zed_settings_dir: pathlib.Path,
        mock_global_gitignore: pathlib.Path,
    ) -> None:
        """Test that non-exclusion settings like soft_wrap are preserved."""
        # Test constants
        expected_tab_size = 4

        settings_file = zed_settings_dir / "settings.json"
        existing_settings = {
            "soft_wrap": "bounded",
            "theme": "dark",
            "tab_size": expected_tab_size,
            "file_scan_exclusions": [
                "**/.git",
                "**/node_modules/",
            ],
            "formatter": {"language_server": {"name": "prettier"}},
        }
        settings_file.write_text(
            json.dumps(existing_settings, indent=2), encoding="utf-8"
        )

        global_patterns = [
            "**/.env",
            "**/.DS_Store",
        ]

        with (
            unittest.mock.patch.object(
                config_manager.file_handler,
                "get_global_gitignore_path",
                return_value=mock_global_gitignore,
            ),
            unittest.mock.patch.object(
                config_manager.file_handler,
                "read_gitignore_patterns",
                return_value=global_patterns,
            ),
        ):
            result = config_manager.sync_global_gitignore_to_zed(
                str(settings_file), update_existing=True
            )

        assert result is True

        # Read the updated settings
        updated_content = settings_file.read_text(encoding="utf-8")
        updated_settings = json.loads(updated_content)

        # All non-exclusion settings should be preserved exactly
        assert updated_settings["soft_wrap"] == "bounded"
        assert updated_settings["theme"] == "dark"
        assert updated_settings["tab_size"] == expected_tab_size
        assert updated_settings["formatter"] == {
            "language_server": {"name": "prettier"}
        }

        # Original exclusions should be preserved
        exclusions = updated_settings["file_scan_exclusions"]
        assert "**/.git" in exclusions
        assert "**/node_modules/" in exclusions

        # New global patterns should be added
        assert "**/.env" in exclusions
        assert "**/.DS_Store" in exclusions

        # Verify structure: original exclusions first, then new ones
        assert exclusions[:2] == ["**/.git", "**/node_modules/"]
        assert "**/.env" in exclusions[2:]
        assert "**/.DS_Store" in exclusions[2:]

    def test_sync_with_nonexistent_settings_directory(
        self,
        config_manager: gentlegoose.config_manager.ConfigManager,
        temp_dir: pathlib.Path,
        mock_global_gitignore: pathlib.Path,
    ) -> None:
        """Test syncing when the settings directory doesn't exist."""
        # Create a settings file path in a nonexistent directory
        nonexistent_dir = temp_dir / "nonexistent" / "nested"
        settings_file = nonexistent_dir / "settings.json"

        expected_global_patterns = [
            "**/.env",
            "**/.DS_Store",
        ]

        with (
            unittest.mock.patch.object(
                config_manager.file_handler,
                "get_global_gitignore_path",
                return_value=mock_global_gitignore,
            ),
            unittest.mock.patch.object(
                config_manager.file_handler,
                "read_gitignore_patterns",
                return_value=expected_global_patterns,
            ),
        ):
            result = config_manager.sync_global_gitignore_to_zed(str(settings_file))

        assert result is True

        # Verify directory and settings file were created
        assert nonexistent_dir.exists()
        assert settings_file.exists()

        # Verify content
        content = json.loads(settings_file.read_text(encoding="utf-8"))
        assert content["file_scan_exclusions"] == expected_global_patterns
