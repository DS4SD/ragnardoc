"""
Base class for a self-contained command
"""

# Standard
import abc
import argparse


class CommandBase(abc.ABC):
    __doc__ = __doc__

    @property
    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        """The name of the command that will be used to select it"""

    @abc.abstractmethod
    def add_args(self, parser: argparse.ArgumentParser):
        """Add the arguments for this command"""

    @abc.abstractmethod
    def run(self, args: argparse.Namespace):
        """Run the command with the given parsed"""
