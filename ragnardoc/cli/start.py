"""
The start command initializes ragnardoc to run as a service that continuously
maintains the state of your documents in all of your connected RAG apps.
"""
# Standard
from datetime import timedelta
import argparse
import re
import shlex
import subprocess
import sys
import time

# First Party
import alog

# Local
from .. import config
from .base import CommandBase

log = alog.use_channel("START")


class StartCommand(CommandBase):
    __doc__ = __doc__
    name = "start"

    def __init__(self):
        self._period = self._parse_time(config.service.period)
        self._cmd = f"{sys.executable} -m ragnardoc run"
        self._running = False

    def add_args(self, parser: argparse.ArgumentParser):
        """Add the args to configure the periodic scraping"""
        parser.add_argument(
            "--period",
            "-p",
            default=None,
            help="The period to run the ingestion service",
        )

    def stop(self):
        self._running = False

    def run(self, args: argparse.Namespace):
        """Start the infinite loop to run periodically"""
        period = self._period
        if args.period:
            period = self._parse_time(args.period)
        self._running = True
        while self._running:
            log.info("Running ingestion service")
            self._ingest()
            log.info("Sleeping for %s", period)
            time.sleep(period.total_seconds())

    def _ingest(self):
        """Run the ingestion as a subprocess. This is done so that config
        changes are re-parsed on very run.
        """
        with alog.ContextTimer(log.debug, "Ingestion done in: %s"):
            subprocess.run(shlex.split(self._cmd))

    @staticmethod
    def _parse_time(time_str: str) -> timedelta:
        """Parse a time string into a timedelta object"""
        pattern = r"(\d+\.?\d*)([dhms])\s*"
        seconds = 0
        for match in re.finditer(pattern, time_str):
            value = float(match.group(1))
            unit = match.group(2)
            if unit == "s":
                seconds += value
            elif unit == "m":
                seconds += value * 60
            elif unit == "h":
                seconds += value * 60 * 60
            elif unit == "d":
                seconds += value * 60 * 60 * 24
        if not seconds:
            raise ValueError(f"Invalid time string: {time_str}")
        return timedelta(seconds=seconds)
