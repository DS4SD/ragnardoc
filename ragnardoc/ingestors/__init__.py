"""
Extensible set of ingestors that can link to multiple RAG consumers
"""

# Local
from ..factory import ImportableFactory
from .anything_llm import AnythingLLMIngestor
from .open_webui import OpenWebUIIngestor

ingestor_factory = ImportableFactory("ingestor")
ingestor_factory.register(AnythingLLMIngestor)
ingestor_factory.register(OpenWebUIIngestor)
