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
        self.roots = [os.path.expanduser(root) for root in config.roots]

        # Save the configured set of raw text types that don't need conversion
        self.raw_text_extensions = config.raw_text_extensions

        # Store the include/exclude patterns
        self.include_paths = config.include.paths
        self.include_regexprs = [
            re.compile(expr) for expr in config.include.regexprs or [".*"]
        ]
        self.exclude_paths = config.exclude.paths
        self.exclude_regexprs = [re.compile(expr) for expr in config.exclude.regexprs]

    def scrape(self) -> list[Document]:
        """Scrape the given path"""
        files_to_ingest = {}
        for root in self.roots:
            log.debug("Scraping root: %s", root)
            for parent, _, files in os.walk(root):
                log.debug2("Scraping contents of %s", parent)
                for fname in files:
                    full_path = os.path.join(parent, fname)
                    if (
                        self._match_paths(full_path, self.include_paths)
                        or self._match_regexprs(full_path, self.include_regexprs)
                    ) and not (
                        self._match_paths(full_path, self.exclude_paths)
                        or self._match_regexprs(full_path, self.exclude_regexprs)
                    ):
                        files_to_ingest.setdefault(root, []).append(full_path)
        log.debug4("All docs to ingest: %s", files_to_ingest)

        # Construct the docs (with lazy loading)
        output_docs = []
        for root, root_files in files_to_ingest.items():
            for fname in root_files:
                is_raw_text = self._is_raw_text_type(fname)
                log.debug2(
                    "Doc %s %s raw text", fname, "IS" if is_raw_text else "IS NOT"
                )
                converter = None if is_raw_text else self._convert_doc
                output_docs.append(
                    Document.from_file(path=fname, root=root, converter=converter)
                )
        return output_docs

    ## Impl ##

    @staticmethod
    def _match_paths(candidate: str, paths: list[str]) -> bool:
        return any(path == candidate for path in paths)

    @staticmethod
    def _match_regexprs(candidate: str, exprs: list[re.Pattern]) -> bool:
        return any(expr.match(candidate) for expr in exprs)

    def _is_raw_text_type(self, candidate: str) -> bool:
        return (
            os.path.splitext(candidate)[1].lower().lstrip(".")
            in self.raw_text_extensions
        )

    def _convert_doc(self, fname: str) -> Document | None:
        converted = self.converter.convert(fname)
        return converted.document.export_to_markdown()
