"""
Ingestor for AnythingLLM
https://anythingllm.com/

Config schema:
    - url: str
    - apikey: str

Currently, the AnythingLLM API is fairly hidden and does not support update
operations on documents, so instead we add a timestamp to the docs when uploaded
to indicate to the user their update time.
"""

# Standard
from datetime import datetime

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

    _time_format = "%Y-%m-%d-%H-%M-%S"

    def __init__(
        self,
        config: aconfig.Config,
        instance_name: str,
        *,
        storage: StorageBase,
    ):
        self.upload_url = f"{config.base_url}/api/v1/document/raw-text"
        self.apikey = config.apikey
        self._storage = storage.namespace(self.name + instance_name)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.apikey}",
        }

    def ingest(self, documents: list[Document]):
        """Ingest the document with a name matching the"""
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
                log.debug(
                    "Unable to parse document %s: %s", doc.path, err, exc_info=True
                )
                continue

            # TODO:
            #   - Ingestion logging
            #   - Error handling
            title = f"{doc.path}-{datetime.now().strftime(self._time_format)}"
            log.info("Ingesting document: %s", title)
            resp = requests.post(
                self.upload_url,
                json={
                    "textContent": doc_content,
                    "metadata": {
                        "title": title,
                    },
                },
                headers=self._headers(),
            )
            log.debug("Upload response code: %d", resp.status_code)
            log.debug2(resp.text)
            self._storage.set(doc.path, fingerprint)

    def delete(self, documents: list[Document]):
        """Currently, there is no good way to delete docs!"""
        log.warning("Unable to delete documents from AnythingLLM!")
        # TODO: It may be possible to physically delete them form the special
        #   cache dir used by the server
