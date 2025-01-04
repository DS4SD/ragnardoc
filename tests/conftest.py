"""
Shared test setup and fixtures
"""
# Standard
from pathlib import Path
import tempfile

# Third Party
import pytest


@pytest.fixture
def data_dir():
    return Path(__file__).parent / "data"


@pytest.fixture
def txt_data_file(data_dir):
    return data_dir / "sample.txt"


@pytest.fixture
def scratch_dir():
    with tempfile.TemporaryDirectory() as dirname:
        yield dirname
