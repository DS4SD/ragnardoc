"""
Base class for the key/value storage abstraction. This abstraction is used to
store keys and values as needed by the various ingestors for state management.
Storage is isolated by namespace so that individual ingestors can operate
independently.
"""

# Standard
from typing import Type
import abc

# Local
from ..factory import FactoryConstructible


class StorageBase(FactoryConstructible):
    __doc__ = __doc__

    # Acceptable value types for storage
    VALUE_TYPE = str | int | float | None

    class StorageNamespaceBase(abc.ABC):
        """A single storage namespace"""

        @abc.abstractmethod
        def set(self, key: str, value: "StorageBase.VALUE_TYPE"):
            """Set the given key/value in this namespace"""

        @abc.abstractmethod
        def get(self, key: str) -> "StorageBase.VALUE_TYPE":
            """Get the value for the given key in this namespace"""

        @abc.abstractmethod
        def pop(self, key: str) -> "StorageBase.VALUE_TYPE":
            """Delete the key from the namespace and return any value that was
            set
            """

    @abc.abstractmethod
    def namespace(str, name: str) -> Type[StorageNamespaceBase]:
        """Get the namespace instance for this name"""
