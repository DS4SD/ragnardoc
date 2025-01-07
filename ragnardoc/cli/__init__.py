"""
Central module for all CLI commands
"""

# Local
from .add import AddCommand
from .common import add_common, use_common
from .init import InitCommand
from .run import RunCommand

all_commands = {
    cmd.name: cmd
    for cmd in [
        AddCommand,
        InitCommand,
        RunCommand,
    ]
}
