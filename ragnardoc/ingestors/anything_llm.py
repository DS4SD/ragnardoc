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
        },
        "required": ["base_url", "apikey"],
    }
    config_defaults = {"root_folder": "ragnardoc"}

    _time_format = "%Y-%m-%d-%H-%M-%S"

    def __init__(
        self,
        config: aconfig.Config,
        instance_name: str,
        *,
        storage: StorageBase,
    ):
        self.base_url = config.base_url
        self.upload_url = f"{config.base_url}/api/v1/document/raw-text"
        self.move_url = f"{self.base_url}/api/v1/document/move-files"
        self.create_folder_url = f"{self.base_url}/api/v1/document/create-folder"
        self.apikey = config.apikey
        self.root_folder = config.root_folder
        self._storage = storage.namespace(self.name + instance_name)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.apikey}",
        }

    def _ensure_directory_path(self, dirpath: str):
        """Create the given document directory path exists"""
        resp = requests.post(
            self.create_folder_url,
            headers=self._headers(),
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

    def ingest(self, documents: list[Document]):
        """Ingest the document with a name matching the"""
        # Ensure the base ragnardoc folder exists
        self._ensure_directory_path(self.root_folder)

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

            # Create the title. Anything LLM does not support nested directories
            # so we need to flatten the path with '--' characters
            raw_title = os.path.relpath(
                doc.path, os.path.dirname(os.path.abspath(doc.root))
            )
            title = raw_title.replace(os.sep, "--")
            log.debug2("Title for %s: %s", doc.path, title)

            # Do the raw ingestion into custom-documents
            log.info("Ingesting document: %s", title)
            resp = requests.post(
                self.upload_url,
                headers=self._headers(),
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
            except IndexError:
                log.warning("No location found in first document!")
                continue
            target_location = os.path.join(self.root_folder, f"{title}.json")
            move_resp = requests.post(
                self.move_url,
                headers=self._headers(),
                json={"files": [{"from": upload_location, "to": target_location}]},
            )
            if move_resp.status_code != 200:
                log.warning("Failed to move document %s to correct location", doc.path)
                continue

            # If everything successful, tore the fingerprint for future
            # re-ingest checks
            self._storage.set(doc.path, fingerprint)

    def delete(self, documents: list[Document]):
        """Currently, there is no good way to delete docs!"""
        log.warning("Unable to delete documents from AnythingLLM!")
        # TODO: It may be possible to physically delete them form the special
        #   cache dir used by the server
