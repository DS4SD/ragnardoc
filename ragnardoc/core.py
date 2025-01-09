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

        # Construct the storage
        self.storage = storage_factory.construct(self.config.storage)

        # Construct the scraper
        self.scraper = FileScraper(self.storage, self.config.scraping)

        # Construct the ingestors
        self.ingestors = []
        for plugin in self.config.ingestion.plugins:
            try:
                ingestor = ingestor_factory.construct(plugin, storage=self.storage)
                self.ingestors.append(ingestor)
            except Exception as err:
                log.warning(
                    "Failed to construct ingestor %s: %s", plugin.get("type"), err
                )
        log.info(
            "All configured ingestion plugins: %s",
            [entry.name for entry in self.ingestors],
        )

    def ingest(self):
        """Run a single ingestion cycle"""
        log.debug("Initializing scrape")
        with alog.ContextTimer(log.debug, "Done scraping in: "):
            scrape_result = self.scraper.scrape()
        for ingestor in self.ingestors:
            log.debug("Ingesting into %s", ingestor.name)
            if scrape_result.documents:
                with alog.ContextLog(
                    log.info, "Ingesting %d docs", len(scrape_result.documents)
                ):
                    try:
                        ingestor.ingest(scrape_result.documents)
                    except Exception as err:
                        log.warning(
                            "Ingestion failed for ingestor [%s]: err",
                            ingestor.name,
                            err,
                        )
                        log.debug4(err)
            if scrape_result.removed:
                with alog.ContextLog(
                    log.info, "Removing %d docs", len(scrape_result.removed)
                ):
                    try:
                        ingestor.delete(scrape_result.removed)
                    except Exception as err:
                        log.warning(
                            "Deletion failed for ingestor [%s]: err", ingestor.name, err
                        )
                        log.debug4(err)
