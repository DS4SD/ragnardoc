"""
Module for scraping files to ingest
"""
# Standard
import os
import re

# Third Party
from docling.document_converter import DocumentConverter

# First Party
import aconfig
import alog

# Local
from .types import Document

log = alog.use_channel("SCRAPING")


class FileScraper:

    def __init__(self, config: aconfig.Config):
        # Load the docling converter
        with alog.ContextTimer(log.debug, "Loaded doc converter in: "):
            self.converter = DocumentConverter()

        # Figure out the paths to scrape from
        self.roots = [
            os.path.expanduser(root)
            for root in config.roots
        ]

        # Save the configured set of raw text types that don't need conversion
        self.raw_text_extensions = config.raw_text_extensions

        # Store the include/exclude patterns
        self.include_paths = config.include.paths
        self.include_regexprs = [
            re.compile(expr)
            for expr in config.include.regexprs or [".*"]
        ]
        self.exclude_paths = config.exclude.paths
        self.exclude_regexprs = [
            re.compile(expr)
            for expr in config.exclude.regexprs
        ]

    def scrape(self) -> list[Document]:
        """Scrape the given path"""
        files_to_ingest = []
        for root in self.roots:
            log.debug("Scraping root: %s", root)
            for parent, _, files in os.walk(root):
                log.debug2("Scraping contents of %s", parent)
                for fname in files:
                    full_path = os.path.join(parent, fname)
                    if (
                        (
                            self._match_paths(full_path, self.include_paths) or
                            self._match_regexprs(full_path, self.include_regexprs)
                        ) and not (
                            self._match_paths(full_path, self.exclude_paths) or
                            self._match_regexprs(full_path, self.exclude_regexprs)
                        )
                    ):
                        files_to_ingest.append(full_path)
        log.debug4("All docs to ingest: %s", files_to_ingest)

        # Construct the docs
        output_docs = []
        for fname in files_to_ingest:
            if self._is_raw_text_type(fname):
                output_docs.append(Document.from_file(fname))
            else:
                if (converted := self._convert_doc(fname)) is not None:
                    output_docs.append(converted)
        return output_docs

    ## Impl ##

    @staticmethod
    def _match_paths(candidate: str, paths: list[str]) -> bool:
        return any(path == candidate for path in paths)

    @staticmethod
    def _match_regexprs(candidate: str, exprs: list[re.Pattern]) -> bool:
        return any(expr.match(candidate) for expr in exprs)

    def _is_raw_text_type(self, candidate: str) -> bool:
        return os.path.splitext(candidate)[1].lower() in self.raw_text_extensions

    def _convert_doc(self, fname: str) -> Document | None:
        try:
            converted = self.converter.convert(fname)
            return Document(
                path=fname, content=converted.document.export_to_markdown()
            )
        except Exception as err:
            log.debug("Error converting document %s: %s", fname, err, exc_info=True)
            return None