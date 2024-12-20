"""
Base class abstraction for an ingestor. An Ingestor is responsible for taking a
document (or multiple documents) and uploading them to a given RAG service.
"""
# Standard
from abc import abstractmethod

# Local
from ..factory import FactoryConstructible
from ..types import Document


class Ingestor(FactoryConstructible):
    __doc__ = __doc__

    @abstractmethod
    def ingest(self, documents: list[Document]):
        """Ingest a document or a list of documents

        Args:
            documents: list of documents to ingest
        """

    @abstractmethod
    def delete(self, documents: list[Document]):
        """Delete the set of documents from the RAG instance"""
