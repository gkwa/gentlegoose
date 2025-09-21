import pathlib
import tempfile
import typing

import pytest

import gentlegoose.config_manager
import gentlegoose.file_handler


@pytest.fixture
def temp_dir() -> typing.Generator[pathlib.Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield pathlib.Path(tmp_dir)


@pytest.fixture
def mock_global_gitignore(temp_dir: pathlib.Path) -> pathlib.Path:
    """Create a mock global gitignore file."""
    global_ignore = temp_dir / "global_gitignore"
    global_ignore.write_text(
        """# Global gitignore patterns
.env
.fmt/
.terraform.lock.hcl
.DS_Store
scratch/
*.log
__pycache__/
.vscode/
""",
        encoding="utf-8",
    )
    return global_ignore


@pytest.fixture
def project_dir(temp_dir: pathlib.Path) -> pathlib.Path:
    """Create a project directory."""
    project = temp_dir / "project"
    project.mkdir()
    return project


@pytest.fixture
def zed_settings_dir(project_dir: pathlib.Path) -> pathlib.Path:
    """Create .zed directory in project."""
    zed_dir = project_dir / ".zed"
    zed_dir.mkdir()
    return zed_dir


@pytest.fixture
def file_handler() -> gentlegoose.file_handler.FileHandler:
    """Create a FileHandler instance."""
    return gentlegoose.file_handler.FileHandler()


@pytest.fixture
def config_manager(
    file_handler: gentlegoose.file_handler.FileHandler,
) -> gentlegoose.config_manager.ConfigManager:
    """Create a ConfigManager instance."""
    return gentlegoose.config_manager.ConfigManager(file_handler, dry_run=False)


@pytest.fixture
def dry_run_config_manager(
    file_handler: gentlegoose.file_handler.FileHandler,
) -> gentlegoose.config_manager.ConfigManager:
    """Create a ConfigManager instance in dry-run mode."""
    return gentlegoose.config_manager.ConfigManager(file_handler, dry_run=True)
