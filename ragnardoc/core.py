"""
The core of RAGNARDoc's document crawling and ingestion
"""

# First Party
import aconfig
import alog

# Local
from . import config as default_config
from .ingestors import ingestor_factory
from .scraping import FileScraper
from .storage import storage_factory

log = alog.use_channel("RAGNARDOC")


class RagnardocCore:
    """This is the core class object that maintains the config, scrapers, and
    ingesteors
    """

    def __init__(self, config: aconfig.Config | None = None):
        self.config = config or default_config

        # Construct the scraper
        self.scraper = FileScraper(self.config.scraping)

        # Construct the storage
        self.storage = storage_factory.construct(self.config.storage)

        # Construct the ingestors
        self.ingestors = [
            ingestor_factory.construct(cfg, storage=self.storage)
            for cfg in self.config.ingestion.plugins
        ]
        log.info(
            "All configured ingestion plugins: %s",
            [entry.name for entry in self.ingestors],
        )

    def ingest(self):
        """Run a single ingestion cycle"""
        log.debug("Initializing scrape")
        with alog.ContextTimer(log.debug, "Done scraping in: "):
            docs = self.scraper.scrape()
        for ingestor in self.ingestors:
            log.debug("Ingesting into %s", ingestor.name)
            ingestor.ingest(docs)
