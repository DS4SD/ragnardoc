"""
Add a document or directory to RAGNARDoc
"""
# Standard
import argparse
import os

# Third Party
import yaml

# First Party
import alog

# Local
from .. import config
from .base import CommandBase

log = alog.use_channel("ADD")


class AddCommand(CommandBase):
    __doc__ = __doc__
    name = "add"

    def add_args(self, parser: argparse.ArgumentParser):
        """Add arbitrary documents"""
        parser.add_argument(
            "paths",
            nargs="+",
            help="Paths to files or directories to add to RAGNARDoc",
        )

    def run(self, args: argparse.Namespace):
        """Add the docs to the config"""
        # Read the existing user config
        user_config_path = os.path.join(config.ragnardoc_home, "config.yaml")
        user_config = {}
        if os.path.exists(user_config_path):
            with open(user_config_path, "r", encoding="utf-8") as handle:
                user_config = yaml.safe_load(handle)

        # Add each path to either the roots or to the includes
        scraping = user_config.setdefault("scraping", {})
        for path in args.paths:
            path = self._normalize_path(path)
            if os.path.isdir(path):
                if path not in (current_roots := scraping.setdefault("roots", [])):
                    current_roots.append(path)
            elif os.path.exists(path):
                if path not in (
                    current_paths := scraping.setdefault("include", {}).setdefault(
                        "paths", []
                    )
                ):
                    current_paths.append(path)
            else:
                print(f"WARNING: Ignoring non-existing path [{path}]")

        # Write the config back out
        user_config_str = yaml.safe_dump(user_config)
        log.debug("FULL CONFIG\n%s", user_config_str)
        with open(user_config_path, "w", encoding="utf-8") as handle:
            handle.write(user_config_str)

    def _normalize_path(self, path: str) -> str:
        return os.path.normpath(os.path.realpath(os.path.expanduser(path)))
