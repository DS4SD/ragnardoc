"""
Implementation of the storage abstraction using an in-memory dict
"""

# Local
from .base import StorageBase


class DictStorage(StorageBase):
    __doc__ = __doc__

    name = "dict"
    config_schema = {"type": "object"}

    def __init__(self, *_, **__):
        self._data = {}

    class DictStorageNamespace(StorageBase.StorageNamespaceBase):
        """Single dict namespace"""

        def __init__(self, name: str, parent: "DictStorage"):
            self._data = parent._data.setdefault(name, {})

        def set(self, key: str, value: StorageBase.VALUE_TYPE):
            """Set the given key/value in the given namespace"""
            self._data[key] = value

        def get(self, key: str) -> StorageBase.VALUE_TYPE:
            """Get the value for the given key in the given namespace"""
            return self._data.get(key)

        def pop(self, key: str) -> StorageBase.VALUE_TYPE:
            """Delete the key from the namespace and return any value that was
            set
            """
            return self._data.pop(key, None)

    def namespace(self, name: str) -> DictStorageNamespace:
        return self.DictStorageNamespace(name, self)
