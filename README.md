# gentlegoose

Sync global gitignore patterns into Zed editor project settings.

## Overview

`gentlegoose` helps you keep your Zed editor file exclusion patterns in sync with your global git ignore settings. By default, it will only create new settings files and will not modify existing ones unless explicitly requested with the `--update-existing` flag. This allows you to customize your local settings without them being repeatedly overwritten.

## Installation

```bash
pip install gentlegoose
```

## Usage

### Basic Usage

Create initial settings file from global gitignore (only if file doesn't exist):

```bash
uv init
gentlegoose
```

Update existing settings file with new global patterns:

```bash
uv init
gentlegoose --update-existing
```

### Specify Custom Settings File

Update global Zed settings:

```bash
uv init
gentlegoose --settings-file ~/.config/zed/settings.json --update-existing
```

Update project-specific settings:

```bash
uv init
gentlegoose --settings-file /path/to/project/.zed/settings.json --update-existing
```

### Dry Run

See what would be changed without making modifications:

```bash
uv init
gentlegoose --dry-run --update-existing
```

### Verbose Output

Get detailed information about what the tool is doing:

```bash
uv init
gentlegoose --verbose --update-existing
```

## Behavior

- **Default**: Creates new settings files only. Existing files are left unchanged.
- **With `--update-existing`**: Adds new global gitignore patterns to existing settings while preserving all current patterns and other settings.
- **Pattern Merging**: Global patterns are appended to existing exclusions, avoiding duplicates.
- **Settings Preservation**: All non-exclusion settings (themes, formatting, etc.) are preserved exactly.

## Global Gitignore Sources

The tool looks for global gitignore patterns in this order:

1. Git config setting: `git config --global core.excludesfile`
2. Default XDG location: `~/.config/git/ignore`
3. Falls back to `~/.gitignore_global` if XDG config home is not set

## Examples

### Initial Setup

```bash
# Create settings for current project (if .zed/settings.json doesn't exist)
gentlegoose

# Create global Zed settings (if ~/.config/zed/settings.json doesn't exist)
gentlegoose --settings-file ~/.config/zed/settings.json
```

### Updating Existing Settings

```bash
# Add new global patterns to existing project settings
uv init
gentlegoose --update-existing

# Update global Zed settings with new patterns
uv init
gentlegoose --settings-file ~/.config/zed/settings.json --update-existing

# Preview changes without applying them
uv init
gentlegoose --dry-run --update-existing -v
```

## Configuration

The tool converts gitignore patterns to Zed's glob format by prefixing patterns with `**/` if they don't already start with it. For example:

- `.env` becomes `**/.env`
- `node_modules/` becomes `**/node_modules/`
- `**/.DS_Store` remains `**/.DS_Store`

## Development

### Setup

```bash
git clone https://github.com/taylormonacelli/gentlegoose.git
cd gentlegoose
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing

```bash
pytest
```