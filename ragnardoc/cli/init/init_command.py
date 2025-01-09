"""
Initialize Ragnardoc config for your system
"""
# Standard
import abc
import argparse
import json
import os
import sys

# Third Party
import yaml

# First Party
import alog

# Local
from ... import config
from ...ingestors import ingestor_factory
from ..base import CommandBase
from .anything_llm_initializer import AnythingLLMInitializer
from .open_webui_initializer import OpenWebUIInitializer

log = alog.use_channel("INIT")


class InitCommand(CommandBase):
    __doc__ = __doc__
    name = "init"

    def __init__(self):
        self.auto = False

    def add_args(self, parser: argparse.ArgumentParser):
        """Add all the arguments needed to initialize"""
        parser.add_argument(
            "--home",
            "-H",
            help="Path to where the ragnardoc home should be",
        )
        parser.add_argument(
            "--auto",
            "-a",
            action="store_true",
            help="Run configuration with no interaction",
        )
        parser.add_argument(
            "--overrides",
            "-o",
            help="Path to a file, or a serialized string holding yaml or json config overrides",
        )
        parser.add_argument(
            "--ingestors",
            "-i",
            nargs="*",
            choices=ingestor_factory.registered_types(),
            help="Ingestors to initialize explicitly. If not set, they will be auto-detected.",
        )

    def run(self, args: argparse.Namespace):
        """Run the initialization"""

        # Set the auto bit
        self.auto = args.auto

        # Make sure home exists
        home_dir = args.home or config.ragnardoc_home
        if home_dir != config.ragnardoc_home:
            print(
                "WARNING: Using a custom RAGNARDOC_HOME. Make sure to set RAGNARDOC_HOME in your environment!"
            )
        log.info("Using home: %s", home_dir)
        os.makedirs(home_dir, exist_ok=True)
        user_config_path = os.path.join(home_dir, "config.yaml")

        # Write out the config overrides if given
        user_config = {}
        if args.overrides:
            if os.path.exists(args.overrides):
                with open(args.overrides, "r", encoding="utf-8") as handle:
                    config_override_content = handle.read()
            else:
                config_override_content = args.overrides
            try:
                user_config = json.loads(config_override_content)
            except json.decoder.JSONDecodeError:
                try:
                    with open(args.overrides, "r", encoding="utf-8") as handle:
                        user_config = yaml.safe_load(handle.read())
                except yaml.parser.ParseError as err:
                    log.error("Unable to parse config overrides: %s", err)
                    raise ValueError("Unable to parse config overrides") from err
            if not isinstance(user_config, dict):
                raise ValueError("Config overrides must be a dict")
            if os.path.exists(user_config_path):
                if not self._ask_yes_no("Overwrite current user config", True):
                    sys.exit(1)
                user_config_path_bak = user_config_path + ".bak"
                log.warning(
                    "Backing up previous user config to %s", user_config_path_bak
                )
                os.rename(user_config, user_config_path_bak)

        # Look for ingestors to configure
        ingestors = args.ingestors or []
        if not ingestors:
            print("Detecting available ingestors")
            for ingestor_init in [
                AnythingLLMInitializer,
                OpenWebUIInitializer,
            ]:
                initializer = ingestor_init()
                if initializer.is_installed():
                    if self._ask_yes_no(f"Initialize {initializer.name}", True):
                        ingestor_config = (
                            initializer.initialize_config()
                            if not self.auto
                            else {"type": initializer.name}
                        )
                        user_config.setdefault("ingestion", {}).setdefault(
                            "plugins", []
                        ).append(ingestor_config)

        # Write out all user config if any set up
        if user_config:
            user_config_str = yaml.safe_dump(user_config)
            print("FULL USER CONFIG")
            print()
            print(user_config_str)
            with open(user_config_path, "w", encoding="utf-8") as handle:
                handle.write(user_config_str)

    ## Private Methods ##

    def _ask_yes_no(self, prompt: str, default: bool) -> bool:
        if self.auto:
            return default
        prompt_suffix = "Yn" if default else "yN"
        resp = input(f"{prompt} [{prompt_suffix}]? ")
        if default:
            return resp.lower() != "n"
        return resp.lower() == "y"
