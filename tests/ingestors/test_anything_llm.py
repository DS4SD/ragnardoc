"""
Unit tests for testing the AnythingLLM ingestor
"""
# Standard
from contextlib import contextmanager
from unittest import mock
import io
import json
import os
import re
import uuid

# Third Party
import pytest
import requests

# First Party
import aconfig

# Local
from ragnardoc.ingestors import ingestor_factory
from ragnardoc.ingestors.anything_llm import AnythingLLMIngestor
from ragnardoc.storage import storage_factory
from ragnardoc.types import Document

## Helpers #####################################################################


class AnythingLLMMock:
    """Mock implementation of AnythingLLM that stores docs in memory"""

    def __init__(self, base_url: str, workspaces: list[str]):
        self.base_url = base_url
        self.docs = {"custom-documents": {}}
        self.workspaces = {
            self._workspace_slug(ws): {
                "name": ws,
                "slug": self._workspace_slug(ws),
                "documents": [],
            }
            for ws in workspaces
        }

    def get(self, url, *_, **__) -> requests.Response:
        return self._handle_call("get", url)

    def post(self, url, json, *_, **__) -> requests.Response:
        return self._handle_call("post", url, json)

    def delete(self, url, json, *_, **__) -> requests.Response:
        return self._handle_call("delete", url, json)

    def _handle_call(self, method: str, url: str, body: dict | None = None):
        """Handle an API call"""
        if method == "post":
            if url == f"{self.base_url}/api/v1/document/raw-text":
                return self._upload(body)
            if url == f"{self.base_url}/api/v1/document/move-files":
                return self._move(body)
            if url == f"{self.base_url}/api/v1/document/create-folder":
                return self._create_folder(body)
            if (workspace_slug := self._get_workspace_slug(url)) and url.endswith(
                f"{workspace_slug}/update-embeddings"
            ):
                return self._update_embeddings(workspace_slug, body)
        elif method == "get":
            if url == f"{self.base_url}/api/v1/workspaces":
                return self._get_workspaces()
            if (workspace_slug := self._get_workspace_slug(url)) and url.endswith(
                workspace_slug
            ):
                return self._workspace_details(workspace_slug)
        elif method == "delete":
            if url == f"{self.base_url}/api/v1/system/remove-documents":
                return self._delete_documents(body)
        return self._make_error(404, "Not found")

    @staticmethod
    def _make_response(
        resp_body: dict | str, status_code: int = 200
    ) -> requests.Response:
        resp = requests.Response()
        resp.status_code = status_code
        resp_str = resp_body if isinstance(resp_body, str) else json.dumps(resp_body)
        resp.raw = io.BytesIO(resp_str.encode("utf-8"))
        return resp

    @classmethod
    def _make_error(cls, status_code: int, msg: str = "") -> requests.Response:
        return cls._make_response({"success": False, "error": msg}, status_code)

    def _folder_exists(self, folder_name: str) -> bool:
        return folder_name in self.docs

    @staticmethod
    def _workspace_slug(name: str) -> str:
        return name.replace(".", "-dot-").replace(":", "")

    def _get_workspace_slug(self, url: str) -> str | None:
        if m := re.match(f"{self.base_url}/api/v1/workspace/([^/]+)", url):
            return m.group(1)

    def _split_folder_name(self, docpath: str) -> tuple[str | None, str | None]:
        parts = docpath.split(os.sep)
        if len(parts) != 2 or not self._folder_exists(parts[0]):
            return None, None
        return parts

    ## Handlers ##

    def _upload(self, body: dict) -> requests.Response:
        """Upload always places the doc in custom-documents"""
        try:
            title = body["metadata"]["title"]
        except IndexError:
            return self._make_error(422, "missing metadata.title")
        uid = str(uuid.uuid4())
        folder = "custom-documents"
        doc_path = f"raw-{title}-{uid}.json"
        self.docs[folder][doc_path] = body
        return self._make_response(
            {
                "success": True,
                "error": None,
                "documents": [
                    {
                        "id": uid,
                        "title": title,
                        "location": os.path.join(folder, doc_path),
                    }
                ],
            }
        )

    def _move(self, body: dict) -> requests.Response:
        """Move the location key"""
        for file_move in body.get("files", []):
            try:
                from_loc = file_move["from"]
                to_loc = file_move["to"]
                from_folder, from_name = self._split_folder_name(from_loc)
                to_folder, to_name = self._split_folder_name(to_loc)
                if None in [from_folder, from_name, to_folder, to_name]:
                    return self._make_error(500, "Failed to move some files")
                self.docs[to_folder][to_name] = self.docs[from_folder].pop(from_name)
            except KeyError:
                return self._make_error(500, "missing to/from")
        return self._make_response({"success": True})

    def _create_folder(self, body: dict) -> requests.Response:
        """Create or error if folder exists already to mirror the real server"""
        try:
            name = body["name"]
        except KeyError:
            return self._make_error(500, "Invalid path")
        if self._folder_exists(name):
            # NOTE: This specific error message is checked as OK
            return self._make_error(500, "Folder by that name already exists")
        self.docs[name] = {}
        return self._make_response({"success": True})

    def _get_workspaces(self) -> requests.Response:
        """Get details (without docs) for all workspaces"""
        return self._make_response(
            {
                "workspaces": [
                    {"name": details["name"], "slug": details["slug"]}
                    for details in self.workspaces.values()
                ]
            }
        )

    def _workspace_details_impl(self, workspace_slug: str) -> dict:
        """Get the detailed view of the workspace"""
        if workspace_slug not in self.workspaces:
            # 200 on bad workspace is what the real server does
            return self._make_response({"workspace": []})
        ws_details = self.workspaces[workspace_slug]
        return {"workspace": [ws_details]}

    def _workspace_details(self, workspace_slug: str) -> requests.Response:
        return self._make_response(self._workspace_details_impl(workspace_slug))

    def _update_embeddings(self, workspace_slug: str, body: dict) -> requests.Response:
        """Update the docs for the given workspace"""
        ws_details = self.workspaces.get(workspace_slug)
        if ws_details is None:
            return self._make_response("Bad Request", 400)
        ws_docs = ws_details.setdefault("documents", [])
        ws_doc_paths = [doc["docpath"] for doc in ws_docs]
        for add_path in body.get("adds", []):
            if add_path not in ws_doc_paths and None not in self._split_folder_name(
                add_path
            ):
                ws_docs.append({"docpath": add_path})
        for delete_path in body.get("deletes", []):
            if delete_path in ws_doc_paths:
                delete_idxs = [
                    idx
                    for idx, doc in enumerate(ws_docs)
                    if doc["docpath"] == delete_path
                ]
                assert len(delete_idxs) == 1, "Not sure what happens here!!!"
                ws_docs.pop(delete_idxs[0])
        ws_details = self._workspace_details_impl(workspace_slug)
        # It's a dict here and a list in the GET call
        return self._make_response({"workspace": ws_details["workspace"][0]})

    def _delete_documents(self, body: dict) -> requests.Response:
        """Delete docs if they've been unlinked from all workspaces"""
        for doc_path in body.get("names", []):
            folder, name = self._split_folder_name(doc_path)
            if None not in [folder, name]:
                self.docs[folder].pop(name, None)
        return self._make_response(
            {"success": True, "message": "Documents removed successfully"}
        )


@contextmanager
def anythingllm_mock_ctx(workspaces: list[str]):
    base_url = "http://localhost:5432187"
    mock_server = AnythingLLMMock(base_url, workspaces)
    with (
        mock.patch("requests.get", mock_server.get),
        mock.patch("requests.post", mock_server.post),
        mock.patch("requests.delete", mock_server.delete),
    ):
        yield mock_server


@pytest.fixture
def anythingllm():
    workspaces = ["workspace1", "workspace2"]
    with anythingllm_mock_ctx(workspaces) as mock_server:
        storage = storage_factory.construct({"type": "dict"})
        cfg = aconfig.Config(
            {
                "base_url": mock_server.base_url,
                "workspaces": workspaces,
                "apikey": "my-key",
                "root_folder": "ragnardoc_tests",
            },
            override_env_vars=False,
        )
        inst = AnythingLLMIngestor(cfg, "test-inst", storage=storage)
        inst.mock = mock_server
        yield inst


## Tests #######################################################################


def test_anythingllm_get_workspaces(anythingllm):
    """Test that the workspaces are fetched correctly"""
    assert set(anythingllm._workspace_slugs) == {"workspace1", "workspace2"}


def test_anythingllm_ingest_delete(anythingllm, data_dir):
    """Test basic ingestion and deletion"""
    docs = [
        Document.from_file(data_dir / "sample.txt", data_dir),
        Document.from_file(data_dir / "sample_docs" / "README.md", data_dir),
    ]
    anythingllm.ingest(docs)

    # Make sure root folder set up correctly
    assert anythingllm._root_folder in anythingllm.mock.docs

    # Make sure both docs found in correct folder
    assert len(anythingllm.mock.docs[anythingllm._root_folder]) == 2

    # Make sure docs are associated with both workspaces
    assert len(anythingllm.mock.workspaces["workspace1"]["documents"]) == 2
    assert len(anythingllm.mock.workspaces["workspace2"]["documents"]) == 2

    # Delete one of the docs
    delete_docs = [docs[0]]
    anythingllm.delete(delete_docs)

    # Make sure only one doc is left
    assert len(anythingllm.mock.docs[anythingllm._root_folder]) == 1

    # Make sure doc removed from both workspaces
    assert len(anythingllm.mock.workspaces["workspace1"]["documents"]) == 1
    assert len(anythingllm.mock.workspaces["workspace2"]["documents"]) == 1
