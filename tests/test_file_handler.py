import json
import pathlib

import gentlegoose.file_handler


class TestFileHandler:
    """Test FileHandler functionality."""

    def test_read_gitignore_patterns(
        self, file_handler: gentlegoose.file_handler.FileHandler, temp_dir: pathlib.Path
    ) -> None:
        """Test reading and parsing gitignore patterns."""
        gitignore_file = temp_dir / "test_gitignore"
        gitignore_content = """# Comments should be ignored
.env
.fmt/

# Another comment
.DS_Store
scratch/
*.log
__pycache__/
"""
        gitignore_file.write_text(gitignore_content, encoding="utf-8")

        patterns = file_handler.read_gitignore_patterns(gitignore_file)

        expected_patterns = [
            "**/.env",
            "**/.fmt/",
            "**/.DS_Store",
            "**/scratch/",
            "**/*.log",
            "**/__pycache__/",
        ]

        assert patterns == expected_patterns

    def test_read_gitignore_patterns_with_existing_glob_patterns(
        self, file_handler: gentlegoose.file_handler.FileHandler, temp_dir: pathlib.Path
    ) -> None:
        """Test that existing ** patterns are not double-prefixed."""
        gitignore_file = temp_dir / "test_gitignore"
        gitignore_content = """**/.env
**/node_modules/
.DS_Store
"""
        gitignore_file.write_text(gitignore_content, encoding="utf-8")

        patterns = file_handler.read_gitignore_patterns(gitignore_file)

        expected_patterns = [
            "**/.env",
            "**/node_modules/",
            "**/.DS_Store",
        ]

        assert patterns == expected_patterns

    def test_read_nonexistent_gitignore(
        self, file_handler: gentlegoose.file_handler.FileHandler, temp_dir: pathlib.Path
    ) -> None:
        """Test reading nonexistent gitignore file returns empty list."""
        nonexistent_file = temp_dir / "nonexistent"
        patterns = file_handler.read_gitignore_patterns(nonexistent_file)
        assert patterns == []

    def test_parse_json5_with_comments_and_trailing_commas(
        self, file_handler: gentlegoose.file_handler.FileHandler
    ) -> None:
        """Test JSON5 parsing with comments and trailing commas."""
        json5_content = """{
  // This is a comment
  "soft_wrap": "bounded",
  "file_scan_exclusions": [
    "**/.venv/",
    "**/.terragrunt-cache/", // Another comment
  ], // Trailing comma here
}"""

        result = file_handler._parse_json5(json5_content)

        expected = {
            "soft_wrap": "bounded",
            "file_scan_exclusions": [
                "**/.venv/",
                "**/.terragrunt-cache/",
            ],
        }

        assert result == expected

    def test_atomic_write_zed_settings(
        self, file_handler: gentlegoose.file_handler.FileHandler, temp_dir: pathlib.Path
    ) -> None:
        """Test atomic writing of settings file."""
        settings_file = temp_dir / "settings.json"
        settings_data = {"file_scan_exclusions": ["**/.env", "**/.DS_Store"]}

        result = file_handler.write_zed_settings(settings_file, settings_data)

        assert result is True
        assert settings_file.exists()

        # Verify content can be read back
        content = json.loads(settings_file.read_text(encoding="utf-8"))
        assert content == settings_data

    def test_write_settings_validates_json(
        self, file_handler: gentlegoose.file_handler.FileHandler, temp_dir: pathlib.Path
    ) -> None:
        """Test that write operation validates JSON before committing."""
        settings_file = temp_dir / "settings.json"

        # Create an object that can't be JSON serialized
        invalid_settings = {"key": {1, 2, 3}}  # sets aren't JSON serializable

        result = file_handler.write_zed_settings(settings_file, invalid_settings)

        assert result is False
        assert not settings_file.exists()
