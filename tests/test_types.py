"""
Unit tests for core types
"""

# Third Party
import pytest

# Local
from ragnardoc import types
from tests.conftest import txt_data_file


def test_document_from_file(txt_data_file):
    """Test that a document can be loaded from a file directly"""
    doc = types.Document.from_file(txt_data_file, foo=1)
    assert isinstance(doc, types.Document)
    assert doc.path == str(txt_data_file)
    assert doc.converter is None
    assert doc.metadata == {"foo": 1}
    assert doc._content is None


def test_document_lazy_loading_no_conversion(txt_data_file):
    """Test that the document's content is lazily loaded without conversion"""
    doc = types.Document.from_file(txt_data_file)
    with open(txt_data_file, "r", encoding="utf-8") as handle:
        expected = handle.read()
    assert doc._content is None
    assert doc.content == expected
    assert doc._content == expected


def test_document_lazy_loading_with_conversion(txt_data_file):
    """Test that the document's content is lazily loaded with conversion"""
    expected = "conveted!"
    def dummy_converter(ignored):
        return expected

    doc = types.Document.from_file(txt_data_file, converter=dummy_converter)
    assert doc._content is None
    assert doc.content == expected
    assert doc._content == expected


# def test_document_loading():
#     doc = types.Document(
#         path="some/path", converter=lambda _: "Converted!", title="title", metadata={"key": 1}
#     )

#     assert doc._content is None
#     doc.load()

#     with open("some/path") as f:
#         expected = f.read()
#     assert doc.content == expected