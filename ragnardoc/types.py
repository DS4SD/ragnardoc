"""
Common structures for reusable data types
"""

# Standard
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
import hashlib
import os

# Type definition of a conversion function that takes the path to a file and
# provides the converted raw text
Converter = Callable[[str], str]


@dataclass
class Document:

    ## Public Attributes ##

    # The path on disk to the document
    path: str
    # The root used to scrape this document
    root: str
    # The title of the document. If unset, the document's basename will be used
    title: str | None = None
    # Additional document metadata
    metadata: dict[str, str | int | float] = field(default_factory=dict)
    # The function that will be used to convert the document to plain text
    converter: Converter | None = None

    ## Private Attributes ##

    # The parsed content of the document. Accessed via content property.
    _content: str | None = None

    # The last computed fingerprint for the document. Used to uniquely identify
    # the content and invalidate the currently read content if needed.
    _last_fingerprint: str | None = None

    ## Properties ##

    @property
    def content(self) -> str:
        """The content of the document will be lazily loaded with conversion
        when first accessed
        """
        self.load()
        return self._content

    @content.setter
    def content(self, value: str):
        self._content = value

    ## Public Methods ##

    def fingerprint(self) -> str | None:
        """The unique fingerprint for this document.

        This is used to determine if/when the document has changed content in
        order to update it where necessary. The current implementation relies on
        a single consistent filesystem as the source of documents, so it uses
        the file metadata rather than a content hash. If the assumption of
        single filesystem changes in the future, this will need to be updated!

        NOTE: Even with the efficient metadata implementation, this is a disk
            operation, so should be used only when needed.

        returns:
            fingerprint (str | None): The unique fingerprint if the file is
            valid, otherwise None (forcing re-read in the future).
        """
        try:
            st = os.stat(self.path)
        except FileNotFoundError:
            return None
        metadata = (
            # File size in bytes
            str(st.st_size),
            # Creation and modification time
            str(st.st_mtime),
            # File permissions
            str(st.st_mode),
        )
        return hashlib.sha256(":".join(metadata).encode()).hexdigest()

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        root: str | Path,
        converter: Converter | None = None,
        load: bool = False,
        **metadata,
    ):
        """Read the Document from the file. By default, it is lazy loaded unless
        load is True.
        """
        inst = cls(
            path=str(path), root=str(root), converter=converter, metadata=metadata
        )
        if load:
            inst.load()
        return inst

    def load(self):
        """If content is not yet set or is invalid, load and convert it"""
        fingerprint = self.fingerprint()
        if self._content is None or fingerprint != self._last_fingerprint:
            # NOTE: This is _not_ thread safe! If ingestion supports threading
            #   (even with the GIL), this will need a lock
            self._last_fingerprint = fingerprint
            if self.converter:
                self._content = self.converter(self.path)
            else:
                with open(self.path, encoding="utf-8") as handle:
                    self._content = handle.read()


@dataclass
class ScrapeResult:
    """The result of a single scrape is a set of documents that exist and a set
    that have been removed
    """

    documents: list[Document]
    removed: list[Document]
