"""
Implementation of the storage abstraction using sqlite3
"""

# Standard
import builtins
import os
import sqlite3

# First Party
import aconfig
import alog

# Local
from .. import config as base_config
from .base import StorageBase

log = alog.use_channel("SQLLSTOR")


class SqliteStorage(StorageBase):
    __doc__ = __doc__

    name = "sqlite"
    config_schema = {
        "type": "object",
        "properties": {
            "db_path": {
                "type": "string",
                "description": "Path or filename for DB file. Non-absolute paths will be placed in RAGNARDOC_HOME",
            },
        },
        "required": ["db_path"],
    }
    config_defaults = {"db_path": "storage.db"}

    def __init__(self, config: aconfig.Config, *_, **__) -> None:
        db_path = config.db_path
        if not os.path.isabs(db_path):
            db_path = os.path.join(base_config.ragnardoc_home, db_path)
        self._db_path = os.path.abspath(db_path)
        log.debug("DB Path: %s", self._db_path)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)

    def __del__(self):
        self._conn.close()

    class StorageSqliteNamespace(StorageBase.StorageNamespaceBase):
        """Implementation of the storage namespace using sqlite3"""

        def __init__(self, name: str, conn: sqlite3.Connection):
            self.name = name
            self._conn = conn

        def set(self, key: str, value: "StorageBase.VALUE_TYPE"):
            type_name = type(value).__name__
            if type_name not in ["str", "int", "float"]:
                raise TypeError(f"Invalid value type: {type_name}")
            with self._conn as conn:
                cursor = conn.cursor()
                self._execute(
                    cursor,
                    f"INSERT OR REPLACE INTO '{self.name}' VALUES (?, ?, ?)",
                    (key, str(value), type_name),
                )
            self._conn.commit()

        def get(self, key: str) -> "StorageBase.VALUE_TYPE":
            with self._conn as conn:
                cursor = conn.cursor()
                self._execute(
                    cursor, f"SELECT * FROM '{self.name}' WHERE key = '{key}' LIMIT 1"
                )
                result = cursor.fetchone()
                if not result:
                    return None
                val = result[1]
                val_type = result[2]
                return self._get_type(val_type)(val)

        def pop(self, key: str) -> "StorageBase.VALUE_TYPE":
            """Delete the key from the namespace and return any value that was
            set
            """
            current_val = self.get(key)
            with self._conn as conn:
                cursor = conn.cursor()
                self._execute(cursor, f"DELETE FROM '{self.name}' WHERE key=?", (key,))
            self._conn.commit()
            return current_val

        @staticmethod
        def _execute(cursor: sqlite3.Cursor, statement: str, args: tuple | None = None):
            log.debug("Executing SQL: %s", statement)
            if args is not None:
                log.debug("Args: %s", args)
                cursor.execute(statement, args)
            else:
                cursor.execute(statement)

        @staticmethod
        def _get_type(type_name: str) -> type:
            return getattr(builtins, type_name)

    def namespace(self, name: str) -> StorageSqliteNamespace:
        ns = self.StorageSqliteNamespace(name, self._conn)
        with self._conn as conn:
            cursor = conn.cursor()
            ns._execute(
                cursor,
                f"""CREATE TABLE IF NOT EXISTS '{name}' (
                key TEXT PRIMARY KEY,
                value TEXT,
                value_type TEXT
            );""",
            )
        return ns
