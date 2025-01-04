"""
Extensible set of storage implementations
"""

# Local
from ..factory import ImportableFactory
from .base import StorageBase
from .dict_storage import DictStorage

storage_factory = ImportableFactory("storage")
storage_factory.register(DictStorage)
