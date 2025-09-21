import json
import logging
import pathlib
import shutil
import subprocess
import tempfile
import typing


class FileHandler:
    """Handles file system operations and git configuration."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def get_global_gitignore_path(self) -> pathlib.Path | None:
        """Get the path to the global gitignore file from git config."""
        try:
            self.logger.debug("Running: git config --global core.excludesfile")
            result = subprocess.run(
                ["git", "config", "--global", "core.excludesfile"],
                capture_output=True,
                text=True,
                check=True,
            )
            path_str = result.stdout.strip()

            if not path_str:
                self.logger.debug(
                    "Git config returned empty string for core.excludesfile"
                )
                return None

            # Expand user home directory if present
            expanded_path = pathlib.Path(path_str).expanduser()
            self.logger.debug("Expanded git config path: %s", expanded_path)

        except subprocess.CalledProcessError as e:
            self.logger.debug(
                "Git config command failed with exit code %d: %s",
                e.returncode,
                e.stderr.strip(),
            )
            return None
        except FileNotFoundError:
            self.logger.debug("Git command not found in PATH")
            return None
        else:
            return expanded_path

    @staticmethod
    def get_default_global_gitignore_path() -> pathlib.Path:
        """Get the default global gitignore path."""
        xdg_config_home = pathlib.Path.home() / ".config"

        if "XDG_CONFIG_HOME" in __import__("os").environ:
            xdg_config_home = pathlib.Path(__import__("os").environ["XDG_CONFIG_HOME"])

        return xdg_config_home / "git" / "ignore"

    def read_gitignore_patterns(self, gitignore_path: pathlib.Path) -> list[str]:
        """Read and parse gitignore patterns from file."""
        if not gitignore_path.exists():
            return []

        try:
            content = gitignore_path.read_text(encoding="utf-8")
            patterns = []

            for original_line in content.splitlines():
                line = original_line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    # Convert gitignore patterns to glob patterns for Zed
                    if not line.startswith("**/"):
                        line = f"**/{line}"
                    patterns.append(line)

        except (OSError, UnicodeDecodeError):
            self.logger.exception("Failed to read %s", gitignore_path)
            return []
        else:
            return patterns

    @staticmethod
    def ensure_zed_settings_directory(project_path: pathlib.Path) -> pathlib.Path:
        """Ensure .zed directory exists in project."""
        zed_dir = project_path / ".zed"
        zed_dir.mkdir(exist_ok=True)
        return zed_dir

    def read_zed_settings(self, settings_path: pathlib.Path) -> dict[str, typing.Any]:
        """Read existing Zed settings file with JSON5 support."""
        if not settings_path.exists():
            return {}

        try:
            content = settings_path.read_text(encoding="utf-8")
            return self._parse_json5(content)

        except (OSError, UnicodeDecodeError):
            self.logger.exception("Failed to read %s", settings_path)
            return {}

    def write_zed_settings(
        self, settings_path: pathlib.Path, settings: dict[str, typing.Any]
    ) -> bool:
        """Write Zed settings to file atomically using temporary file."""
        temp_path = None
        try:
            # Create temporary file in same directory to ensure atomic move
            temp_dir = settings_path.parent
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=temp_dir, suffix=".tmp", delete=False
            ) as temp_file:
                temp_path = pathlib.Path(temp_file.name)

                # Write to temporary file
                content = json.dumps(settings, indent=2, ensure_ascii=False)
                temp_file.write(content)
                temp_file.flush()

            # Validate the temporary file can be read back
            try:
                self._parse_json5(temp_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                if temp_path:
                    temp_path.unlink(missing_ok=True)
                self.logger.exception("Failed to validate temporary settings file")
                return False

            # Atomic move to final location
            shutil.move(str(temp_path), str(settings_path))

        except (OSError, UnicodeEncodeError, TypeError):
            self.logger.exception("Failed to write %s", settings_path)
            # Clean up temporary file if it exists
            if temp_path:
                temp_path.unlink(missing_ok=True)
            return False
        else:
            return True

    def _parse_json5(self, content: str) -> dict[str, typing.Any]:
        """Parse JSON5-like content (JSON with trailing commas and comments)."""
        if not content.strip():
            return {}

        # Remove single-line comments (// comments)
        lines = []
        for original_line in content.splitlines():
            # Find // not inside strings
            in_string = False
            escaped = False
            comment_pos = None

            for i, char in enumerate(original_line):
                if escaped:
                    escaped = False
                    continue

                if char == "\\":
                    escaped = True
                    continue

                if char == '"' and not escaped:
                    in_string = not in_string
                    continue

                if (
                    not in_string
                    and char == "/"
                    and i < len(original_line) - 1
                    and original_line[i + 1] == "/"
                ):
                    comment_pos = i
                    break

            processed_line = original_line
            if comment_pos is not None:
                processed_line = original_line[:comment_pos].rstrip()

            lines.append(processed_line)

        cleaned_content = "\n".join(lines)

        # Remove trailing commas before closing brackets/braces
        cleaned_content = self._remove_trailing_commas(cleaned_content)

        return json.loads(cleaned_content)

    @staticmethod
    def _remove_trailing_commas(content: str) -> str:
        """Remove trailing commas that would make JSON invalid."""
        result = []
        in_string = False
        escaped = False

        for i, char in enumerate(content):
            if escaped:
                escaped = False
                result.append(char)
                continue

            if char == "\\":
                escaped = True
                result.append(char)
                continue

            if char == '"' and not escaped:
                in_string = not in_string
                result.append(char)
                continue

            if not in_string and char == ",":
                # Look ahead for only whitespace before closing bracket/brace
                j = i + 1
                while j < len(content) and content[j].isspace():
                    j += 1

                if j < len(content) and content[j] in "}]":
                    # Skip the trailing comma
                    continue

            result.append(char)

        return "".join(result)
