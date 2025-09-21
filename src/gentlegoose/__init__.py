import importlib.metadata

import gentlegoose.cli

try:
    __version__ = importlib.metadata.version("gentlegoose")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.0"  # fallback version


def main() -> None:
    gentlegoose.cli.run_cli()
