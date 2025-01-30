"""
Unit tests for the start command
"""
# Standard
from datetime import timedelta
from unittest import mock
import argparse
import threading
import time

# Third Party
import pytest

# First Party
import aconfig

# Local
from ragnardoc.cli.start import StartCommand


@pytest.mark.parametrize(
    ["time_str", "expected_delta"],
    [
        ("35s", timedelta(seconds=35)),
        ("1d  2h  35s", timedelta(seconds=35 + 2 * 60 * 60 + 60 * 60 * 24)),
        ("16s 6h", timedelta(seconds=16 + 6 * 60 * 60)),
        ("2hours 1minute", timedelta(seconds=60 + 2 * 60 * 60)),
        ("0.5s", timedelta(seconds=0.5)),
    ],
)
def test_parse_time(time_str, expected_delta):
    """Test that time parsing works for various combinations"""
    assert StartCommand._parse_time(time_str) == expected_delta


@pytest.mark.parametrize("time_str", ["", "  ", "1 d", "1w"])
def test_parse_time_invalid(time_str):
    """Test that ValueError is raised for invalid time strings"""
    with pytest.raises(ValueError):
        StartCommand._parse_time(time_str)


@mock.patch("subprocess.run")
def test_run(run_mock):
    """Test that running the command launches the infinite loop correctly"""
    cmd = StartCommand()
    args = aconfig.Config({"period": "0.1s"}, override_env_vars=False)
    run_thread = threading.Thread(target=cmd.run, args=(args,))
    run_thread.start()
    time.sleep(0.05)
    cmd.stop()
    run_thread.join()
    run_mock.assert_called_once()


def test_add_args():
    """Test that the command adds the expected arguments"""
    parser = argparse.ArgumentParser()
    StartCommand().add_args(parser)
    args = parser.parse_args([])
    assert hasattr(args, "period")
