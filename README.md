# gentlegoose

Sync global gitignore patterns into Zed editor project settings.

## Overview

`gentlegoose` helps you keep your Zed editor file exclusion patterns in sync with your global git ignore settings. By default, it will only create new settings files and will not modify existing ones unless explicitly requested with the `--update-existing` flag. This allows you to customize your local settings without them being repeatedly overwritten.

## Installation

```bash
pip install gentlegoose
```
