"""
Shared test setup and fixtures
"""
# Standard
from pathlib import Path
import abc
import io
import json
import os
import shutil
import tempfile

# Third Party
import pytest
import requests

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
def mutable_data_dir(data_dir):
    """Get a version of the data dir that the test can mutate without side
    effects
    """
    with tempfile.TemporaryDirectory() as working_dir:
        mutable_dir = Path(working_dir) / "data"
        shutil.copytree(data_dir, mutable_dir)
        yield mutable_dir


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


## Server Mock Structure #######################################################


class ServerMockBase(abc.ABC):
    """Shared base class for mock server implementations"""

    ## Abstract ##

    @abc.abstractmethod
    def _handle_call(self, method: str, url: str, body: dict | None = None):
        """Server-specific router method"""

    ## Public ##

    def get(self, url, *_, **__) -> requests.Response:
        return self._handle_call("get", url)

    def post(self, url, json=None, files=None, *_, **__) -> requests.Response:
        if json and files:
            raise ValueError("Cannot specify both `json` and `files`.")
        body = json or files
        return self._handle_call("post", url, body)

    def delete(self, url, json=None, *_, **__) -> requests.Response:
        return self._handle_call("delete", url, json)

    ## Protected ##

    @staticmethod
    def _make_response(
        resp_body: dict | str, status_code: int = 200
    ) -> requests.Response:
        resp = requests.Response()
        resp.status_code = status_code
        resp_str = resp_body if isinstance(resp_body, str) else json.dumps(resp_body)
        resp.raw = io.BytesIO(resp_str.encode("utf-8"))
        return resp
