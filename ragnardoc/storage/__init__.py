"""
Extensible set of storage implementations
"""

# Local
from ..factory import ImportableFactory
from .base import StorageBase
from .dict_storage import DictStorage
from .sqlite_storage import SqliteStorage

storage_factory = ImportableFactory("storage")
storage_factory.register(DictStorage)
storage_factory.register(SqliteStorage)
