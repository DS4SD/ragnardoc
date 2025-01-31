"""
Unit tests for testing the Open WebUI ingestor
"""
# Standard
from contextlib import contextmanager
from unittest import mock
import re
import uuid

# Third Party
import pytest
import requests

# First Party
import aconfig

# Local
from ragnardoc.ingestors.open_webui import OpenWebUIIngestor
from ragnardoc.storage import storage_factory
from ragnardoc.types import Document
from tests.conftest import ServerMockBase

## Helpers #####################################################################


class OpenWebUIMock(ServerMockBase):
    """Mock implementation of OpenWebUI that stores docs in memory"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.files = {}
        self.collections = {}

    def _handle_call(self, method: str, url: str, body: dict | None = None):
        """Handle an API call"""
        # NOTE: The trailing slash is there to replicate behavior of Open WebUI
        files_url = f"{self.base_url}/api/v1/files/"
        knowledge_url = f"{self.base_url}/api/v1/knowledge/"

        if method == "post":
            if url == files_url:
                return self._upload(body)
            if m := re.match(f"{files_url}(?P<file_id>[^/]+)/content/update", url):
                return self._update_content(m.group("file_id"), body)
            if url == f"{knowledge_url}create":
                return self._create_collection(body)
            if m := re.match(
                f"{knowledge_url}/(?P<collection_id>[^/]+)/file/update", url
            ):
                collection_id = m.group("collection_id")
                return self._update_collection_file(collection_id, body)
            if m := re.match(f"{knowledge_url}(?P<collection_id>[^/]+)/file/add", url):
                collection_id = m.group("collection_id")
                return self._add_collection_file(collection_id, body)
            if m := re.match(
                f"{knowledge_url}(?P<collection_id>[^/]+)/file/remove", url
            ):
                collection_id = m.group("collection_id")
                return self._remove_collection_file(collection_id, body)

        elif method == "get":
            if m := re.match(f"{files_url}(?P<file_id>[^/]+)", url):
                file_id = m.group("file_id")
                return self._get_file(file_id)
            if url == knowledge_url:
                return self._get_collections()
            if m := re.match(f"{knowledge_url}(?P<collection_id>[^/]+)", url):
                collection_id = m.group("collection_id")
                return self._get_collection(collection_id)

        elif method == "delete":
            if m := re.match(f"{files_url}(?P<file_id>[^/]+)", url):
                file_id = m.group("file_id")
                return self._delete_file(file_id)

        # Any endpoint that doesn't explicitly match redirects back to the web
        # entrypoint, which includes missing trailing slashes
        return self._make_response("<html>this is a web page</html>", 200)

    @classmethod
    def _make_error(cls, status_code: int, msg: str = "") -> requests.Response:
        return cls._make_response({"detail": msg}, status_code)

    ## Handlers ##

    def _upload(self, body: dict) -> requests.Response:
        """Upload always places the doc in custom-documents"""
        try:
            filename, content = body["file"]
        except (IndexError, TypeError):
            return self._make_error(422, "bad file upload")
        uid = str(uuid.uuid4())
        file_value = {"filename": filename, "data": {"content": content}, "id": uid}
        self.files[uid] = file_value
        return self._make_response(file_value)

    def _update_content(self, file_id: str, body: dict) -> requests.Response:
        """Update the content of a file"""
        if file_id not in self.files:
            return self._make_error(404, "file not found")
        try:
            new_content = body["content"]
        except IndexError:
            return self._make_error(422, "bad update")
        self.files[file_id]["data"]["content"] = new_content
        return self._make_response(self.files[file_id])

    def _create_collection(self, body: dict) -> requests.Response:
        """Create a new collection

        NOTE: Open WebUI will happily make a new collection with a duplicate
            name and description!
        """
        uid = str(uuid.uuid4())
        try:
            collection_value = {
                "id": uid,
                "description": body.get("description", ""),
                "name": body["name"],
                "data": {
                    "file_ids": [],
                    "files": [],
                },
            }
            self.collections[uid] = collection_value
            return self._make_response(collection_value)
        except KeyError:
            return self._make_error(422, "bad request")

    def _update_collection_file(
        self, collection_id: str, body: dict
    ) -> requests.Response:
        """Update a file in a collection (reindex)"""
        if collection_id not in self.collections:
            return self._make_error(404, "collection not found")
        try:
            file_id = body["file_id"]
        except KeyError:
            return self._make_error(422, "bad request")
        collection_files = self.collections[collection_id]["files"]
        if file_id not in collection_files:
            return self._make_error(404, "file not in collection")
        return self._make_response(self.collections[collection_id])

    def _add_collection_file(self, collection_id: str, body: dict) -> requests.Response:
        """Add a file to the collection"""
        try:
            file_id = body["file_id"]
        except KeyError:
            return self._make_error(422, "bad request")
        if (collection_value := self.collections.get(collection_id)) is None:
            return self._make_error(404, "collection not found")
        if (file_value := self.files.get(file_id)) is None:
            return self._make_error(404, "file not found")
        if file_id in collection_value["data"]["file_ids"]:
            # NOTE: This error is handled specifically
            return self._make_error(
                400,
                "400: Duplicate content detected. Please provide unique content to proceed.",
            )
        collection_value["data"]["file_ids"].append(file_id)
        collection_value["data"]["files"].append(file_value)
        return self._make_response(collection_value)

    def _remove_collection_file(
        self, collection_id: str, body: dict
    ) -> requests.Response:
        """Remove a file from the collection"""
        try:
            file_id = body["file_id"]
        except KeyError:
            return self._make_error(422, "bad request")
        if (collection_value := self.collections.get(collection_id)) is None:
            return self._make_error(404, "collection not found")
        if file_id not in collection_value["data"]["file_ids"]:
            return self._make_error(400, "file not in collection")
        collection_value["data"]["file_ids"].remove(file_id)
        collection_value["data"]["files"] = [
            f for f in collection_value["data"]["files"] if f["id"] != file_id
        ]
        return self._make_response(collection_value)

    def _get_file(self, file_id: str) -> requests.Response:
        """Get a file"""
        if (file_value := self.files.get(file_id)) is None:
            return self._make_error(404, "file not found")
        return self._make_response(file_value)

    def _get_collections(self) -> requests.Response:
        """Get all collections"""
        return self._make_response(self.collections)

    def _get_collection(self, collection_id: str) -> requests.Response:
        """Get a collection"""
        if (collection_value := self.collections.get(collection_id)) is None:
            return self._make_error(404, "collection not found")
        return self._make_response(collection_value)

    def _delete_file(self, file_id: str) -> requests.Response:
        """Delete a file

        NOTE: Open WebUI will happily delete a file that is still in a
            knowledge collection. It seems to remove the entry from "files" but
            not "file_ids"
        """
        if self.files.get(file_id) is None:
            return self._make_error(404, "file not found")
        return self._make_response(self.files.pop(file_id))


@contextmanager
def open_webui_mock_ctx():
    base_url = "http://localhost:5432187"
    mock_server = OpenWebUIMock(base_url)
    with (
        mock.patch("requests.get", mock_server.get),
        mock.patch("requests.post", mock_server.post),
        mock.patch("requests.delete", mock_server.delete),
    ):
        yield mock_server


@pytest.fixture
def open_webui_mock():
    with open_webui_mock_ctx() as mock_server:
        storage = storage_factory.construct({"type": "dict"})
        cfg = aconfig.Config(
            {
                "base_url": mock_server.base_url,
                "apikey": "my-key",
                "knowledge": "ragnardoc_tests",
            },
            override_env_vars=False,
        )
        inst = OpenWebUIIngestor(cfg, "test-inst", storage=storage)
        inst.mock = mock_server
        yield inst


## Tests #######################################################################


def test_anythingllm_init_knowledge(open_webui_mock):
    """Test that the knowledge collection is initialized if needed"""
    assert open_webui_mock._knowledge_id is not None
    assert open_webui_mock._knowledge_id in open_webui_mock.mock.collections


def test_open_webui_ingest_delete(open_webui_mock, mutable_data_dir):
    """Test basic ingestion and deletion"""
    docs = [
        Document.from_file(mutable_data_dir / "sample.txt", mutable_data_dir),
        Document.from_file(
            mutable_data_dir / "sample_docs" / "README.md", mutable_data_dir
        ),
    ]
    open_webui_mock.ingest(docs)

    # Make sure there are two docs uploaded and both were added to the
    # collection
    assert len(open_webui_mock.mock.files) == 2
    assert len(open_webui_mock.mock.collections) == 1
    collection = list(open_webui_mock.mock.collections.values())[0]
    assert all(
        fid in collection["data"]["file_ids"] for fid in open_webui_mock.mock.files
    )

    # Redo ingestion and make sure nothing changes
    open_webui_mock.ingest(docs)
    assert len(open_webui_mock.mock.files) == 2
    assert len(open_webui_mock.mock.collections) == 1
    collection = list(open_webui_mock.mock.collections.values())[0]
    assert all(
        fid in collection["data"]["file_ids"] for fid in open_webui_mock.mock.files
    )

    # Change the content of sample.txt and make sure it gets updated in place
    new_content = "I added some interesting different content!"
    doc_id = [
        doc_id
        for doc_id, doc in open_webui_mock.mock.files.items()
        if doc["filename"].startswith("sample")
    ][0]
    assert open_webui_mock.mock.files[doc_id]["data"]["content"] != new_content
    with open(docs[0].path, "w") as handle:
        handle.write("I added some interesting different content!")
    open_webui_mock.ingest(docs)
    assert open_webui_mock.mock.files[doc_id]["data"]["content"] == new_content

    # Delete the doc and make sure it gets removed from the collection and
    # deleted from files
    open_webui_mock.delete([docs[0]])
    assert len(open_webui_mock.mock.files) == 1
    assert len(open_webui_mock.mock.collections) == 1
    collection = list(open_webui_mock.mock.collections.values())[0]
    assert doc_id not in collection["data"]["file_ids"]
    assert len(collection["data"]["files"]) == 1
