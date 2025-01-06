"""
Unit tests for dict-based storage
"""

# Local
from ragnardoc.storage import storage_factory
from ragnardoc.storage.dict_storage import DictStorage


def test_factory_construct():
    """Test that an instance can be constructed from the factory"""
    inst = storage_factory.construct({"type": "dict"})
    assert isinstance(inst, DictStorage)


def test_namespace_get_set_pop():
    """Test that the basic get/set/pop work on a single namespace"""
    inst = DictStorage()
    ns = inst.namespace("test")
    assert ns.get("key") is None
    ns.set("key1", 1)
    assert ns.get("key1") == 1
    assert ns.get("key2") is None
    assert ns.pop("key1") == 1
    assert ns.get("key1") is None


def test_multi_namespace():
    """Test that multiple namespaces can be managed independently"""
    inst = DictStorage()
    ns1 = inst.namespace("ns1")
    ns2 = inst.namespace("ns2")
    ns1.set("key", 42)
    assert ns1.get("key") == 42
    assert ns2.get("key") is None
