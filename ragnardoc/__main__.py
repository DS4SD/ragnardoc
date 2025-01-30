#!/usr/bin/env python
"""
RAGNARDoc is a tool that runs natively on a developer workstation to
automatically ingest local documents into a variety of RAG applications. It can
operate as a CLI for direct ingestion or as a service for background ingestion
and synchronization (Coming soon!)
"""

# Standard
import argparse

# First Party
import alog

# Local
from . import cli, config
from ._version import __version__

log = alog.use_channel("MAIN")


def main():
    # Initial parser to parse the command
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?", choices=sorted(cli.all_commands.keys()))
    parser.add_argument(
        "--version", "-v", action="store_true", help="Show the library version"
    )
    initial_args = parser.parse_known_args()[0]

    # Handle version
    if initial_args.version:
        print(__version__)
        return 0

    # Full parser to parse the command arguments
    command = initial_args.command
    cmd_cls = cli.all_commands.get(command)
    parser = argparse.ArgumentParser(description=parser.description)
    parser.add_argument("command", choices=sorted(cli.all_commands.keys()))
    cli.add_common(parser)

    # Add the args for the specific command
    if cmd_cls:
        cmd_inst = cmd_cls()
        cmd_inst.add_args(
            parser.add_argument_group(cmd_cls.name, description=cmd_cls.__doc__)
        )

    # Parse all args and handle common setup
    args = parser.parse_args()
    cli.use_common(args)

    # Run the command
    log.info("RAGNARDoc is running command %s", command)
    log.debug4("Full config: %s", config.config_instance)
    cmd_inst.run(args)


if __name__ == "__main__":
    main()
