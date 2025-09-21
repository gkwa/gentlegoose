import json
import logging
import pathlib
import shutil
import tempfile
import typing

try:
    from dulwich.config import ConfigFile
except ImportError:
    # Fallback if dulwich is not available
    ConfigFile = None

# Constants
CONFIG_KEY_VALUE_PARTS = 2


class FileHandler:
    """Handles file system operations and git configuration."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def get_global_gitignore_path(self) -> pathlib.Path | None:
        """Get the path to the global gitignore file from git config."""
        if ConfigFile is None:
            self.logger.debug(
                "Dulwich not available, falling back to manual config parsing"
            )
            return self._get_global_gitignore_path_fallback()

        try:
            self.logger.debug("Reading git global config for core.excludesfile")

            # Try to read from global git config file
            global_config_path = pathlib.Path.home() / ".gitconfig"
            if global_config_path.exists():
                with global_config_path.open("rb") as f:
                    config = ConfigFile.from_file(f)

                excludes_file = config.get((b"core",), b"excludesfile")
                if excludes_file:
                    path_str = excludes_file.decode("utf-8")
                    self.logger.debug("Git config returned path: %s", path_str)

                    # Expand user home directory if present
                    expanded_path = pathlib.Path(path_str).expanduser()
                    self.logger.debug("Expanded git config path: %s", expanded_path)
                    return expanded_path
                self.logger.debug("No core.excludesfile found in git config")
            else:
                self.logger.debug(
                    "Global git config file does not exist: %s", global_config_path
                )

        except (OSError, UnicodeDecodeError, KeyError, AttributeError) as e:
            self.logger.debug("Failed to read git config with dulwich: %s", e)
            return self._get_global_gitignore_path_fallback()

        return None

    def _get_global_gitignore_path_fallback(self) -> pathlib.Path | None:
        """Fallback method to parse git config manually."""
        try:
            self.logger.debug("Using fallback git config parsing")
            global_config_path = pathlib.Path.home() / ".gitconfig"

            if not global_config_path.exists():
                self.logger.debug(
                    "Global git config file does not exist: %s", global_config_path
                )
                return None

            content = global_config_path.read_text(encoding="utf-8")

            # Simple parser for core.excludesfile
            for original_line in content.splitlines():
                stripped_line = original_line.strip()
                if stripped_line.startswith("excludesfile"):
                    # Handle both quoted and unquoted values
                    parts = stripped_line.split("=", 1)
                    if len(parts) == CONFIG_KEY_VALUE_PARTS:
                        path_str = parts[1].strip().strip('"').strip("'")
                        if path_str:
                            self.logger.debug("Git config returned path: %s", path_str)
                            expanded_path = pathlib.Path(path_str).expanduser()
                            self.logger.debug(
                                "Expanded git config path: %s", expanded_path
                            )
                            return expanded_path

            self.logger.debug("No core.excludesfile found in git config")

        except (OSError, UnicodeDecodeError) as e:
            self.logger.debug("Failed to read git config: %s", e)

        return None

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
