"""
Module for scraping files to ingest
"""
# Standard
import json
import os
import re

# First Party
import aconfig
import alog

# Local
from .storage import StorageBase
from .types import Document, ScrapeResult

log = alog.use_channel("SCRAPING")


class FileScraper:

    _scrape_cache_key = "scrape_cache"

    def __init__(self, storage: StorageBase, config: aconfig.Config):

        # NOTE: Local import to avoid slow imports for non-run commands
        # Third Party
        from docling.document_converter import DocumentConverter

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

        # Scoped storage for detecting deletions
        self._storage = storage.namespace("__core_scraping__")
        self._auto_delete = config.auto_delete

    def scrape(self) -> ScrapeResult:
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
        all_ingest_paths = [doc for root in files_to_ingest.values() for doc in root]
        for include_path in self.include_paths:
            if include_path not in all_ingest_paths:
                files_to_ingest.setdefault(os.path.sep, []).append(include_path)
        log.debug4("All docs to ingest: %s", files_to_ingest)

        # Construct the docs (with lazy loading)
        output_docs = {}
        for root, root_files in files_to_ingest.items():
            for fname in root_files:
                is_raw_text = self._is_raw_text_type(fname)
                log.debug2(
                    "Doc %s %s raw text", fname, "IS" if is_raw_text else "IS NOT"
                )
                converter = None if is_raw_text else self._convert_doc
                # Sometimes docs are found multiple times with redundant roots
                # or includes
                if fname not in output_docs:
                    output_docs[fname] = Document.from_file(
                        path=fname, root=root, converter=converter
                    )

        # Detect deleted docs
        this_scrape_data = {doc.path: doc.root for doc in output_docs.values()}
        deleted_docs = []
        if self._auto_delete and (
            last_scrape_data := self._storage.get(self._scrape_cache_key)
        ):
            last_scrape = json.loads(last_scrape_data)
            deleted_docs = [
                Document(path=doc_path, root=doc_root)
                for doc_path, doc_root in last_scrape.items()
                if doc_path not in this_scrape_data
            ]

        # Add this scrape to the last scrape cache
        self._storage.set(self._scrape_cache_key, json.dumps(this_scrape_data))

        # Return the full result of the scrape
        return ScrapeResult(documents=list(output_docs.values()), removed=deleted_docs)

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
