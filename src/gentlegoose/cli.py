import argparse
import importlib.metadata
import logging
import sys

import gentlegoose.config_manager
import gentlegoose.file_handler
import gentlegoose.logger

# Exit status codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_INTERRUPTED = 130  # Standard for SIGINT (Ctrl+C)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync global gitignore patterns into Zed editor project settings"
    )

    parser.add_argument(
        "--settings-file",
        type=str,
        help="Path to Zed settings.json file (default: ./.zed/settings.json)",
        metavar="FILE",
    )

    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing settings file with new global gitignore patterns",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {importlib.metadata.version('gentlegoose')}",
    )

    return parser


def run_cli() -> None:
    parser = create_parser()
    args = parser.parse_args()

    gentlegoose.logger.setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        file_handler = gentlegoose.file_handler.FileHandler()
        config_manager = gentlegoose.config_manager.ConfigManager(
            file_handler, dry_run=args.dry_run
        )

        settings_file = args.settings_file
        if settings_file is None:
            settings_file = "./.zed/settings.json"

        success = config_manager.sync_global_gitignore_to_zed(
            settings_file, update_existing=args.update_existing
        )

        if not success:
            sys.exit(EXIT_FAILURE)

        sys.exit(EXIT_SUCCESS)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(EXIT_INTERRUPTED)
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(EXIT_FAILURE)
