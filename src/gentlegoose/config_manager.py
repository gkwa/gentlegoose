import logging
import pathlib

import gentlegoose.file_handler

# Constants
MAX_PATTERNS_TO_SHOW = 5


class ConfigManager:
    """Manages the synchronization of gitignore patterns to Zed settings."""

    def __init__(
        self,
        file_handler: gentlegoose.file_handler.FileHandler,
        *,
        dry_run: bool = False,
    ) -> None:
        self.file_handler = file_handler
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

    def sync_global_gitignore_to_zed(
        self, settings_file_path: str, *, update_existing: bool = False
    ) -> bool:
        """Sync global gitignore patterns to Zed settings file."""
        settings_path = pathlib.Path(settings_file_path).resolve()

        if not self._validate_settings_path(settings_path):
            return False

        # If settings file exists and update_existing is False, skip update
        if settings_path.exists() and not update_existing:
            self.logger.info(
                "Settings file exists. Use --update-existing to add new global "
                "patterns: %s",
                settings_path,
            )
            return True

        global_patterns = self._get_global_gitignore_patterns()

        if not global_patterns:
            self.logger.info("No global gitignore patterns found")
            return True

        return self._update_zed_settings(settings_path, global_patterns)

    def _validate_settings_path(self, settings_path: pathlib.Path) -> bool:
        """Validate that the settings file path is valid."""
        # Check if parent directory exists or can be created
        parent_dir = settings_path.parent
        if not parent_dir.exists():
            # For nonexistent directories, we'll create them later
            # Just validate that the path structure is reasonable
            try:
                # Test if we can resolve the parent path
                parent_dir.resolve()
            except (OSError, ValueError):
                self.logger.exception("Invalid settings directory path: %s", parent_dir)
                return False
        elif not parent_dir.is_dir():
            self.logger.error("Settings parent path is not a directory: %s", parent_dir)
            return False

        # If settings file exists, check it's a file
        if settings_path.exists() and not settings_path.is_file():
            self.logger.error(
                "Settings path exists but is not a file: %s", settings_path
            )
            return False

        return True

    def _get_global_gitignore_patterns(self) -> list[str]:
        """Get global gitignore patterns from git config or default location."""
        # Try git config first
        self.logger.debug("Checking git config for global gitignore path")
        global_path = self.file_handler.get_global_gitignore_path()

        if global_path:
            self.logger.debug("Git config returned path: %s", global_path)
            if global_path.exists():
                self.logger.info(
                    "Using global gitignore from git config: %s", global_path
                )
                return self.file_handler.read_gitignore_patterns(global_path)
            self.logger.debug(
                "Global gitignore path from git config does not exist: %s",
                global_path,
            )
        else:
            self.logger.debug("No global gitignore path configured in git")

        # Fall back to default location
        default_path = self.file_handler.get_default_global_gitignore_path()
        self.logger.debug("Checking default global gitignore path: %s", default_path)

        if default_path.exists():
            self.logger.info("Using default global gitignore: %s", default_path)
            return self.file_handler.read_gitignore_patterns(default_path)
        self.logger.debug(
            "Default global gitignore file does not exist: %s", default_path
        )

        self.logger.info("No global gitignore file found. Checked paths:")
        if global_path:
            self.logger.info("  Git config path: %s (not found)", global_path)
        else:
            self.logger.info("  Git config: no path configured")
        self.logger.info("  Default path: %s (not found)", default_path)
        return []

    def _update_zed_settings(
        self, settings_path: pathlib.Path, global_patterns: list[str]
    ) -> bool:
        """Update Zed settings with gitignore patterns."""
        current_settings = self.file_handler.read_zed_settings(settings_path)
        current_exclusions = current_settings.get("file_scan_exclusions", [])

        # Determine what patterns need to be added
        patterns_to_add = self._get_patterns_to_add(current_exclusions, global_patterns)

        if not patterns_to_add:
            self.logger.info(
                "All global gitignore patterns already present in Zed settings"
            )
            return True

        if self.dry_run:
            self._log_dry_run_info(settings_path, patterns_to_add, current_exclusions)
            return True

        # Create new exclusions list (current + new patterns)
        new_exclusions = current_exclusions + patterns_to_add
        current_settings["file_scan_exclusions"] = new_exclusions

        # Ensure parent directory exists
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        success = self.file_handler.write_zed_settings(settings_path, current_settings)

        if success:
            self.logger.info("Updated Zed settings: %s", settings_path)
            self.logger.info(
                "Added %d new global gitignore patterns", len(patterns_to_add)
            )
            for pattern in patterns_to_add:
                self.logger.debug("Added pattern: %s", pattern)

        return success

    def _get_patterns_to_add(
        self, current_exclusions: list[str], global_patterns: list[str]
    ) -> list[str]:
        """Determine which global patterns need to be added to current exclusions."""
        current_set = set(current_exclusions)
        patterns_to_add = []

        for pattern in global_patterns:
            if pattern not in current_set:
                patterns_to_add.append(pattern)
                self.logger.debug("Pattern needs to be added: %s", pattern)
            else:
                self.logger.debug("Pattern already exists: %s", pattern)

        return patterns_to_add

    def _log_dry_run_info(
        self,
        settings_path: pathlib.Path,
        patterns_to_add: list[str],
        current_exclusions: list[str],
    ) -> None:
        """Log information about what would be done in dry run mode."""
        self.logger.info("Would update: %s", settings_path)
        self.logger.info("Current exclusions count: %d", len(current_exclusions))
        self.logger.info("Would add %d new patterns:", len(patterns_to_add))

        for pattern in patterns_to_add:
            self.logger.info("  + %s", pattern)

        if current_exclusions:
            self.logger.info("Existing patterns would be preserved:")
            for pattern in current_exclusions[:MAX_PATTERNS_TO_SHOW]:
                self.logger.info("  = %s", pattern)
            if len(current_exclusions) > MAX_PATTERNS_TO_SHOW:
                remaining = len(current_exclusions) - MAX_PATTERNS_TO_SHOW
                self.logger.info("  ... and %d more", remaining)
