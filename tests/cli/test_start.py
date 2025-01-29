"""
Unit tests for the start command
"""
# Standard
from datetime import timedelta

# Third Party
import pytest

# Local
from ragnardoc.cli.start import StartCommand


@pytest.mark.parametrize(
    ["time_str", "expected_delta"],
    [
        ("35s", timedelta(seconds=35)),
        ("1d  2h  35s", timedelta(seconds=35 + 2 * 60 * 60 + 60 * 60 * 24)),
        ("16s 6h", timedelta(seconds=16 + 6 * 60 * 60)),
        ("2hours 1minute", timedelta(seconds=60 + 2 * 60 * 60)),
    ],
)
def test_parse_time(time_str, expected_delta):
    """Test that time parsing works for various combinations"""
    assert StartCommand._parse_time(time_str) == expected_delta


@pytest.mark.parametrize("time_str", ["", "  ", "1 d"])
def test_parse_time_invalid(time_str):
    """Test that ValueError is raised for invalid time strings"""
    with pytest.raises(ValueError):
        StartCommand._parse_time(time_str)
