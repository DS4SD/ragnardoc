"""
Common structures for reusable data types
"""

# Standard
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# Type definition of a conversion function that takes the path to a file and
# provides the converted raw text
Converter = Callable[[str], str]


@dataclass
class Document:
    # The path on disk to the document
    path: str
    # The title of the document. If unset, the document's basename will be used
    title: str | None = None
    # Additional document metadata
    metadata: dict[str, str | int | float] = field(default_factory=dict)
    # The function that will be used to convert the document to plain text
    converter: Converter | None = None

    # The parsed content of the document. Accessed via content property.
    _content: str | None = None

    @property
    def content(self) -> str:
        self.load()
        return self._content

    @content.setter
    def content(self, value: str):
        self._content = value

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        converter: Converter | None = None,
        load: bool = False,
        **metadata,
    ):
        """Read the Document from the file. By default, it is lazy loaded unless
        load is True.
        """
        inst = cls(path=str(path), converter=converter, metadata=metadata)
        if load:
            inst.load()
        return inst

    def load(self):
        """If content is not yet set, load and convert it"""
        if self._content is None:
            # NOTE: This is _not_ thread safe! If ingestion supports threading
            #   (even with the GIL), this will need a lock
            if self.converter:
                self._content = self.converter(self.path)
            else:
                with open(self.path, encoding="utf-8") as handle:
                    self._content = handle.read()
