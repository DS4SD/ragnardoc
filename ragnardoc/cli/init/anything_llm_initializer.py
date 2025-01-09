"""
Config initializer for AnythingLLM
"""
# Standard
import os
import platform

# Local
from ...ingestors import AnythingLLMIngestor
from ...ingestors.base import Ingestor
from .initializer_base import IngestorInitializerBase


class AnythingLLMInitializer(IngestorInitializerBase):
    __doc__ = __doc__

    def ingestor_class(self) -> type[Ingestor]:
        return AnythingLLMIngestor

    def is_installed(self):
        system = platform.system()
        if system == "Darwin":
            return os.path.exists("/Applications/AnythingLLM.app")
        print(f"Auto-detection not supported on {system} for AnythingLLM")
        return False
