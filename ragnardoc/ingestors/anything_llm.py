"""
Ingestor for AnythingLLM
https://anythingllm.com/

Currently, the AnythingLLM API is fairly hidden and does not support update
operations on documents, so instead we add a timestamp to the docs when uploaded
to indicate to the user their update time.
"""

# Standard
from datetime import datetime
import os

# Third Party
import requests

# First Party
import aconfig
import alog

# Local
from ..storage import StorageBase
from ..types import Document
from .base import Ingestor

log = alog.use_channel("ANYTHINGLLM")


class AnythingLLMIngestor(Ingestor):
    __doc__ = __doc__

    name = "anything-llm"
    config_schema = {
        "type": "object",
        "properties": {
            "base_url": {
                "type": "string",
                "description": "The base URL for the AnythingLLM server",
            },
            "apikey": {
                "type": "string",
                "description": "The developer API Key for the AnythingLLM server",
            },
            "root_folder": {
                "type": "string",
                "description": "The root folder name in the AnythingLLM doc tree",
            },
            "workspaces": {
                "type": "array",
                "items": {
                    "type": "string",
                },
                "description": "List of workspaces to add documents to",
            },
        },
        "required": ["apikey"],
    }
    config_defaults = {
        "base_url": "http://localhost:3001",
        "root_folder": "ragnardoc",
        "workspaces": [],
    }

    def __init__(
        self,
        config: aconfig.Config,
        instance_name: str,
        *,
        storage: StorageBase,
    ):
        # All the API URLs we'll use for easy reference
        self._base_url = config.base_url
        api_base = f"{self._base_url}/api/v1"
        self._upload_url = f"{api_base}/document/raw-text"
        self._move_url = f"{api_base}/document/move-files"
        self._create_folder_url = f"{api_base}/document/create-folder"
        self._workspaces_url = f"{api_base}/workspaces"
        self._workspace_details_url = f"{api_base}/workspace"
        self._doc_delete_url = f"{api_base}/system/remove-documents"

        self._root_folder = config.root_folder

        self._headers = {
            "Authorization": f"Bearer {config.apikey}",
        }

        # Scoped storage for re-ingestion fingerprint cache
        self._storage = storage.namespace(self.name + instance_name)

        # Get the workspace slugs for all configured workspaces
        self._workspace_slugs = {
            ws["name"]: ws["slug"]
            for ws in self._get_workspaces()
            if ws["name"] in config.workspaces
        }
        log.debug("Workspace slugs: %s", self._workspace_slugs)
        missing_workspaces = [
            ws for ws in config.workspaces if ws not in self._workspace_slugs
        ]
        if missing_workspaces:
            log.warning("Workspace(s) not found: %s", missing_workspaces)

    #######################
    ## Interface Methods ##
    #######################

    def ingest(self, documents: list[Document]):
        """Ingest the documents, updating existing docs as necessary"""
        # Ensure the base ragnardoc folder exists
        self._ensure_directory_path(self._root_folder)

        uploaded_docs = []
        for doc in documents:

            # Check to see if this doc has changed since last ingesting
            fingerprint = doc.fingerprint()
            if self._storage.get(doc.path) == fingerprint:
                log.debug("Document [%s] has not changed. Not uploading", doc.path)
                continue

            # Ensure the latest content is current
            try:
                doc_content = doc.content
            except Exception as err:
                log.debug("Unable to parse document %s: %s", doc.path, err)
                log.debug4(err, exc_info=True)
                continue

            # Do the raw ingestion into custom-documents
            title = self._get_doc_title(doc)
            log.info("Ingesting document: %s", title)
            resp = requests.post(
                self._upload_url,
                headers=self._headers,
                json={
                    "textContent": doc_content,
                    "metadata": {
                        "title": title,
                    },
                },
            )
            log.debug("Upload response code: %d", resp.status_code)
            log.debug2(resp.text)

            # Parse the response json if possible
            try:
                resp_json = resp.json()
            except requests.exceptions.JSONDecodeError:
                resp_json = {}

            # Handle errors
            if resp.status_code != 200:
                log.warning(
                    "Failed to upload document %s: %s",
                    doc.path,
                    resp_json.get("message"),
                )
                log.debug(resp.text)
                continue

            # Move the document to the root folder. Here, we use a name that is
            # unique to the doc, but _not_ unique to the upload. This
            # approximates "update" semantics.
            try:
                upload_location = resp_json["documents"][0]["location"]
            except KeyError:
                log.warning("No location found in first document!")
                continue
            target_location = self._get_doc_location(doc)
            move_resp = requests.post(
                self._move_url,
                headers=self._headers,
                json={"files": [{"from": upload_location, "to": target_location}]},
            )
            if move_resp.status_code != 200:
                log.warning("Failed to move document %s to correct location", doc.path)
                continue

            # If everything successful so far, store the fingerprint for future
            # re-ingest checks
            self._storage.set(doc.path, fingerprint)
            uploaded_docs.append(target_location)

        # Update the workspaces with the uploaded docs
        for workspace_name, workspace_slug in self._workspace_slugs.items():
            log.debug2("Updating docs in workspace %s", workspace_name)
            self._update_docs_in_workspace(uploaded_docs, workspace_slug)

    def delete(self, documents: list[Document]):
        """Currently, there is no good way to delete docs!"""
        # Remove all documents from workspaces where they're indexed
        doc_locations = [self._get_doc_location(doc) for doc in documents]
        for workspace_name, workspace_slug in self._workspace_slugs.items():
            workspace_docs = self._workspace_doc_paths(workspace_slug)
            if docs_to_remove := [
                doc_loc for doc_loc in doc_locations if doc_loc in workspace_docs
            ]:
                log.debug(
                    "Removing docs from workspace %s: %s",
                    workspace_name,
                    docs_to_remove,
                )
                remove_resp = requests.post(
                    f"{self._workspace_details_url}/{workspace_slug}/update-embeddings",
                    headers=self._headers,
                    json={"deletes": docs_to_remove},
                )
                remove_resp.raise_for_status()

        # Fully delete the docs
        delete_resp = requests.delete(
            self._doc_delete_url,
            headers=self._headers,
            json={"names": doc_locations},
        )
        delete_resp.raise_for_status()

        # Clear out the fingerprints
        for doc in documents:
            self._storage.pop(doc.path)

    #####################
    ## Private Methods ##
    #####################

    @staticmethod
    def _get_doc_title(doc: Document) -> str:
        """Get the title to be used for this doc in Anything LLM's storage.

        NOTE: Anything LLM does not support nested directories so we need to
            flatten the path with '--' characters
        """
        raw_title = os.path.relpath(
            doc.path, os.path.dirname(os.path.abspath(doc.root))
        )
        title = raw_title.replace(os.sep, "--")
        log.debug2("Title for %s: %s", doc.path, title)
        return title

    def _get_doc_location(self, doc: Document) -> str:
        """Get the location where the doc will be stored in AnythingLLM's doc
        cache dir
        """
        return os.path.join(self._root_folder, self._get_doc_title(doc) + ".json")

    def _ensure_directory_path(self, dirpath: str):
        """Create the given document directory path exists"""
        resp = requests.post(
            self._create_folder_url,
            headers=self._headers,
            json={"name": dirpath},
        )
        # If it's a 500 because the dir already exists, that's ok! If any of the
        # logic to check this fails and raises, that's not ok and it _should_
        # raise.
        if resp.status_code == 500:
            try:
                resp_body = resp.json()
                if (
                    not resp_body["success"]
                    and "already exists" in resp_body["message"]
                ):
                    log.debug4("Directory %s already exists", dirpath)
                    return
            except Exception as err:
                log.error("Failed to set up directory %s: %s", dirpath, err)
                raise
        resp.raise_for_status()

    def _get_workspaces(self) -> list[dict]:
        """Get info about all workspaces"""
        resp = requests.get(self._workspaces_url, headers=self._headers)
        resp.raise_for_status()
        return resp.json()["workspaces"]

    def _workspace_doc_paths(self, workspace_slug: str) -> list[str]:
        """Get the list of doc paths in a given workspace"""
        resp = requests.get(
            f"{self._workspace_details_url}/{workspace_slug}",
            headers=self._headers,
        )
        resp.raise_for_status()
        return [doc["docpath"] for doc in resp.json()["workspace"][0]["documents"]]

    def _update_docs_in_workspace(self, uploaded_docs: list[str], workspace_slug: str):
        """Attempt to update the given workspace with the given uploaded docs"""
        try:
            existing_docs = self._workspace_doc_paths(workspace_slug)

            # Remove any existing docs that have been updated
            if updated_docs := [doc for doc in uploaded_docs if doc in existing_docs]:
                log.debug(
                    "Removing updated docs from %s: %s", workspace_slug, updated_docs
                )
                remove_resp = requests.post(
                    f"{self._workspace_details_url}/{workspace_slug}/update-embeddings",
                    headers=self._headers,
                    json={"deletes": updated_docs},
                )
                remove_resp.raise_for_status()

            # Add all the docs as new to trigger indexing
            add_resp = requests.post(
                f"{self._workspace_details_url}/{workspace_slug}/update-embeddings",
                headers=self._headers,
                json={"adds": uploaded_docs},
            )
            add_resp.raise_for_status()
        except Exception as err:
            log.warning("Failed to update docs for %s: %s", workspace_slug, err)
            log.debug(err, exc_info=True)
