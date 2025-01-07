"""
Common CLI argument setup
"""

# Standard
import argparse

# First Party
import alog

# Local
from .. import config


def add_common(parser: argparse.ArgumentParser):
    """Add common arguments"""
    # Logging
    log_section = parser.add_argument_group(
        "log", description="Output logging configuration"
    )
    log_section.add_argument(
        "--log-level", "-l", default=config.log_level, help="Default log channel level"
    )
    log_section.add_argument(
        "--log-filters",
        "-lf",
        default=config.log_filters,
        help="Per-channel log filters",
    )
    log_section.add_argument(
        "--log-json",
        "-lj",
        action="store_true",
        default=config.log_json,
        help="Log output as JSON",
    )
    log_section.add_argument(
        "--log-thread-id",
        "-lt",
        action="store_true",
        default=config.log_thread_id,
        help="Include the thread ID in log header",
    )


def use_common(args: argparse.Namespace):
    """Use the common arguments"""
    # Configure logging
    alog.configure(
        default_level=args.log_level,
        filters=args.log_filters,
        formatter="json" if args.log_json else "pretty",
        thread_id=args.log_thread_id,
    )
