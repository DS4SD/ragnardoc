"""
Unit tests for dict-based storage
"""
# Standard
from unittest import mock

# Third Party
import pytest

# Local
from ragnardoc import config
from ragnardoc.storage import storage_factory
from ragnardoc.storage.sqlite_storage import SqliteStorage


def test_factory_construct(scratch_dir):
    """Test that an instance can be constructed from the factory"""
    inst = storage_factory.construct(
        {"type": "sqlite", "config": {"db_path": str(scratch_dir / "storage.db")}}
    )
    assert isinstance(inst, SqliteStorage)


def test_namespace_get_set_pop(scratch_dir):
    """Test that the basic get/set/pop work on a single namespace"""
    inst = storage_factory.construct(
        {"type": "sqlite", "config": {"db_path": str(scratch_dir / "storage.db")}}
    )
    ns = inst.namespace("test")
    assert ns.get("key") is None
    ns.set("key1", 1)
    assert ns.get("key1") == 1
    assert ns.get("key2") is None
    assert ns.pop("key1") == 1
    assert ns.get("key1") is None


def test_multi_namespace(scratch_dir):
    """Test that multiple namespaces can be managed independently"""
    inst = storage_factory.construct(
        {"type": "sqlite", "config": {"db_path": str(scratch_dir / "storage.db")}}
    )
    ns1 = inst.namespace("ns1")
    ns2 = inst.namespace("ns2")
    ns1.set("key", 42)
    assert ns1.get("key") == 42
    assert ns2.get("key") is None


def test_all_types(scratch_dir):
    """Test that the the value types are handled correctly"""
    inst = storage_factory.construct(
        {"type": "sqlite", "config": {"db_path": str(scratch_dir / "storage.db")}}
    )
    ns = inst.namespace("test")
    data = {
        "k1": 1,
        "k2": "two",
        "k3": 3.14,
    }
    for k, v in data.items():
        ns.set(k, v)
    for k, v in data.items():
        assert v == ns.get(k)


def test_invalid_type(scratch_dir):
    """Test that an invalid type is rejected at insertion time"""
    inst = storage_factory.construct(
        {"type": "sqlite", "config": {"db_path": str(scratch_dir / "storage.db")}}
    )
    ns = inst.namespace("test")
    with pytest.raises(TypeError):
        ns.set("key", b"bytes")


def test_ragnardoc_home_db(scratch_dir):
    """Test that non-absolute paths will be prepended by ragnardoc_home"""
    with mock.patch.object(config, "ragnardoc_home", scratch_dir):
        inst = storage_factory.construct(
            {"type": "sqlite", "config": {"db_path": "some_storage.db"}}
        )
        assert inst._db_path == str(scratch_dir / "some_storage.db")


def test_config_defaults(scratch_dir):
    """Test that if db path given, the default is used"""
    with mock.patch.object(config, "ragnardoc_home", scratch_dir):
        inst = storage_factory.construct({"type": "sqlite"})
        assert inst._db_path == str(scratch_dir / "storage.db")
