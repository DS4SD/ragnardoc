"""
Shared test setup and fixtures
"""
# Standard
from pathlib import Path
import os
import tempfile

# Third Party
import pytest

# First Party
import alog

alog.configure(
    default_level=os.getenv("LOG_LEVEL", "error"),
    filters=os.getenv("LOG_FILTERS", ""),
    formatter="json" if os.getenv("LOG_JSON", "").lower() == "true" else "pretty",
    thread_id=os.getenv("LOG_THREAD_IDF", "").lower() == "true",
)


@pytest.fixture
def data_dir():
    return Path(__file__).parent / "data"


@pytest.fixture
def txt_data_file(data_dir):
    return data_dir / "sample.txt"


@pytest.fixture
def scratch_dir():
    with tempfile.TemporaryDirectory() as dirname:
        yield Path(dirname)


# Force RAGNARDOC_HOME to be a temporary directory that will be auto-cleaned up.
# This is done while importing conftest.py to avoid the import-time config
# parsing where user config is merged.
_tempdir = tempfile.TemporaryDirectory(suffix="ragnardoc")
os.environ["RAGNARDOC_HOME"] = _tempdir.name


@pytest.fixture(autouse=True)
def ignore_user_config():
    with tempfile.TemporaryDirectory() as temp_home:
        _tempdir.cleanup()
        os.environ["RAGNARDOC_HOME"] = temp_home
        yield
        _tempdir.cleanup()
