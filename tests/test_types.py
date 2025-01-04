"""
Unit tests for core types
"""
# Standard
from pathlib import Path

# Local
from ragnardoc import types


def test_document_from_file(txt_data_file):
    """Test that a document can be loaded from a file directly"""
    doc = types.Document.from_file(txt_data_file, foo=1)
    assert isinstance(doc, types.Document)
    assert doc.path == str(txt_data_file)
    assert doc.converter is None
    assert doc.metadata == {"foo": 1}
    assert doc._content is None


def test_document_from_file_proactive(txt_data_file):
    """Test that a document can be loaded from a file directly and proactively
    loaded
    """
    doc = types.Document.from_file(txt_data_file, load=True)
    assert doc._content is not None


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
    expected = "converted!"

    def dummy_converter(ignored):
        return expected

    doc = types.Document.from_file(txt_data_file, converter=dummy_converter)
    assert doc._content is None
    assert doc.content == expected
    assert doc._content == expected


def test_set_content():
    """Test that the content property can be set directly"""
    doc = types.Document("some/bad/path")
    assert doc._content is None
    content = "Hello there!"
    doc.content = content
    assert doc.content == content
    assert doc._content == content


def test_fingerprint_content_change(scratch_dir):
    """Test that the doc's fingerprint is computed correctly and mirrors changes
    to the document itself
    """
    doc_path = Path(scratch_dir) / "doc.txt"
    content1 = "Hello World"
    content2 = "Hiya world!"
    with open(doc_path, "w") as handle:
        handle.write(content1)

    # Load from doc with initial content
    doc = types.Document.from_file(doc_path)
    fp1 = doc.fingerprint()
    read_content1 = doc.content

    # Make sure the fingerprint doesn't change if the doc hasn't changed
    assert doc.fingerprint() == fp1
    assert doc.content == read_content1 == content1

    # Update the doc content
    with open(doc_path, "w") as handle:
        handle.write(content2)

    # Make sure the fingerprint changes and the content is invalidated and
    # re-loaded
    fp2 = doc.fingerprint()
    read_content2 = doc.content
    assert fp2 != fp1
    assert read_content2 != read_content1
    assert doc.content == read_content2 == content2
