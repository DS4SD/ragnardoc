"""
Common structures for reusable data types
"""

# Standard
from dataclasses import dataclass, field


@dataclass
class Document:
    # The path on disk to the document
    path: str
    # The parsed content of the document. If unset, document will be read as raw
    content: str | None = None
    # The title of the document. If unset, the document's basename will be used
    title: str | None = None
    # Additional document metadata
    metadata: dict[str, str | int | float] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str, load: bool = False):
        content = None
        if load:
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        return cls(path=path, content=content)
