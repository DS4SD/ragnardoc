"""
Central module for all CLI commands
"""

# Local
from .common import add_common, use_common
from .run import RunCommand

all_commands = {
    cmd.name: cmd
    for cmd in [
        RunCommand,
    ]
}
