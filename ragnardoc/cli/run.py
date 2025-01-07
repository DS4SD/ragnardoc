"""
The run command runs a single ragnardoc ingestion based on the available config
"""
# Standard
import argparse

# First Party
import alog

# Local
from .. import config
from ..core import RagnardocCore
from .base import CommandBase

log = alog.use_channel("RUN")


class RunCommand(CommandBase):
    __doc__ = __doc__
    name = "run"

    def add_args(self, *_, **__):
        """There are no additional args to the run command"""

    def run(self, args: argparse.Namespace):
        """Perform the single run"""
        instance = RagnardocCore(config)
        with alog.ContextTimer(log.info, "Finished ingestion in: "):
            instance.ingest()
