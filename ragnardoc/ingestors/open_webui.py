"""
Ingestor for Open WebUI
https://openwebui.com/
"""

# Standard
import json
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

log = alog.use_channel("OPENWEBUI")


class OpenWebUIIngestor(Ingestor):
    __doc__ = __doc__

    name = "open-webui"
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
            "knowledge": {
                "type": "string",
                "description": "The knowledge collection to place the docs in",
            },
        },
        "required": ["apikey"],
    }
    config_defaults = {
        "base_url": "http://localhost:8080",
        "knowledge": "ragnardoc",
    }

    def __init__(
        self,
        config: aconfig.Config,
        instance_name: str,
        *,
        storage: StorageBase,
    ):
        # All the API URLs we'll use for easy reference
        # NOTE: Open WebUI is very sensitive to the trailing slash! Some
        #   endpoints require it, others require it to not be present.
        self._base_url = config.base_url
        self._version_url = f"{self._base_url}/api/version"
        self._files_url = f"{self._base_url}/api/v1/files/"
        self._knowledge_url = f"{self._base_url}/api/v1/knowledge/"

        # Common headers for all requests
        self._headers = {
            "Authorization": f"Bearer {config.apikey}",
        }

        # Central knowledge collection for ragnardoc
        self._knowledge_id = self._ensure_knowledge_collection(config.knowledge)
        self._knowledge_collection_url = f"{self._knowledge_url}{self._knowledge_id}"

        # Scoped storage for re-ingestion fingerprint cache
        self._storage = storage.namespace(self.name + instance_name)

    #######################
    ## Interface Methods ##
    #######################

    def ingest(self, documents: list[Document]):
        """Ingest the documents, updating existing docs as necessary"""
        uploaded_doc_ids = []
        for doc in documents:

            # Check to see if this doc has changed since last ingesting
            fingerprint = doc.fingerprint()
            stored_fingerprint, file_id = None, None
            if stored_content := self._get_file_storage(doc.path):
                stored_fingerprint = stored_content["fingerprint"]
                file_id = stored_content["id"]
            if stored_fingerprint == fingerprint:
                log.debug("Document [%s] has not changed. Not uploading", doc.path)
                continue

            # Ensure the latest content is current
            try:
                doc_content = doc.content
            except Exception as err:
                log.debug("Unable to parse document %s: %s", doc.path, err)
                log.debug4(err, exc_info=True)
                continue

            # Check to see if the file already exists in Open WebUI
            file_exists = False
            if file_id:
                resp = requests.get(f"{self._files_url}/{file_id}")
                file_exists = resp.status_code == 200

            # If the file already exists, update its content
            if file_exists:
                log.debug2("Updating existing file %s with id %s", doc.path, file_id)
                resp = requests.post(
                    f"{self._files_url}/{file_id}/content/update",
                    headers=self._headers,
                    json={"content": doc_content},
                )
                if resp.status_code != 200:
                    log.warning(
                        "Failed to update doc %s: [%d] %s",
                        doc.path,
                        resp.status_code,
                        resp.text,
                    )
                    continue

                # Update this doc to the knowledge collection
                resp = requests.post(
                    f"{self._knowledge_collection_url}/file/update",
                    headers=self._headers,
                    json={"file_id": file_id},
                )
                if resp.status_code != 200:
                    log.warning(
                        "Failed to update document %s with id %s in knowledge collection: %s",
                        doc.path,
                        file_id,
                        resp.text,
                    )
                    continue

            # Otherwise, upload it
            else:
                # Get the filename that will be used in Open WebUI
                filename = self._get_filename(doc)
                resp = requests.post(
                    f"{self._files_url}",
                    headers=self._headers,
                    files={"file": (filename, doc_content)},
                )
                if resp.status_code != 200:
                    log.warning("Failed to upload doc %s: %s", doc.path, resp.text)
                try:
                    resp_body = resp.json()
                    file_id = resp_body["id"]
                except (requests.exceptions.JSONDecodeError, KeyError) as err:
                    log.warning("Failed to get file_id from upload response: %s", err)
                    log.debug4(err, exc_info=True)
                    continue

                # Add this doc to the knowledge collection
                resp = requests.post(
                    f"{self._knowledge_collection_url}/file/add",
                    headers=self._headers,
                    json={"file_id": file_id},
                )
                if resp.status_code != 200:
                    log.warning(
                        "Failed to add document %s with id %s to knowledge collection: %s",
                        doc.path,
                        file_id,
                        resp.text,
                    )
                    continue

            # Mark this doc as successfully uploaded
            uploaded_doc_ids.append(file_id)

            # Update the storage to reflect this file
            self._set_file_storage(doc.path, fingerprint, file_id)

    def delete(self, documents: list[Document]):
        """Currently, there is no good way to delete docs!"""
        # Get the file_ids from storage for each doc
        doc_infos = [self._get_file_storage(doc.path) for doc in documents]
        doc_file_ids = {
            stored_content["id"] for stored_content in doc_infos if stored_content
        }
        for file_id in doc_file_ids:

            # Remove from knowledge collection
            resp = requests.post(
                f"{self._knowledge_collection_url}/file/remove",
                headers=self._headers,
                json={"file_id": file_id},
            )
            if resp.status_code != 200:
                log.warning(
                    "Failed to remove doc with id %s from knowledge collection", file_id
                )
                continue

            # Delete it
            resp = requests.delete(
                f"{self._files_url}/{file_id}", headers=self._headers
            )
            if resp.status_code != 200:
                log.warning("Failed to delete doc with id %s", file_id)

    #####################
    ## Private Methods ##
    #####################

    def _get_file_storage(self, path: str) -> dict | None:
        if stored_content := self._storage.get(path):
            return json.loads(stored_content)

    def _set_file_storage(self, path: str, fingerprint: str, file_id: str):
        self._storage.set(
            path,
            json.dumps(
                {
                    "fingerprint": fingerprint,
                    "id": file_id,
                }
            ),
        )

    def _ensure_knowledge_collection(self, knowledge_collection: str) -> str:
        """Create the given knowledge collection if needed and return the id"""
        # Get all knowledge collections and look for one matching this name
        resp = requests.get(self._knowledge_url, headers=self._headers)
        resp.raise_for_status()
        all_knowledge_collections = {col["name"]: col["id"] for col in resp.json()}
        if knowledge_id := all_knowledge_collections.get(knowledge_collection):
            log.debug2(
                "Knowledge collection [%s] already exists with id: %s",
                knowledge_collection,
                knowledge_id,
            )
            return knowledge_id

        # If not found above, create it and return the ID
        resp = requests.post(
            f"{self._knowledge_url}create",
            headers=self._headers,
            json={
                "name": knowledge_collection,
                "description": "Documents ingested with RAGNARDoc",
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]

    @staticmethod
    def _get_filename(doc: Document) -> str:
        """The file name will be formatted with the actual file name at the
        beginning, followed by a qualifying path relative to the root, followed
        by a file extension. This is to allow the user to easily reference the
        file by name, but still disambiguate by path and to avoid confusing Open
        WebUI with non-text file types.
        """
        abs_path = os.path.abspath(doc.path)
        file_name = os.path.basename(abs_path)
        if doc.converter:
            ext = ".md"
        else:
            file_name, ext = os.path.splitext(file_name)
        rel_path = os.path.relpath(
            os.path.dirname(abs_path), os.path.dirname(os.path.abspath(doc.root))
        ).replace(os.sep, "--")
        filename = f"{file_name} ({rel_path}){ext}"
        return filename
