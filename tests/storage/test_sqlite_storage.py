"""
Unit tests for dict-based storage
"""

# Third Party
import pytest

# Local
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
