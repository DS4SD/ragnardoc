"""
Config initializer for Open WebUI
"""
# Third Party
import requests

# Local
from ...ingestors import OpenWebUIIngestor
from ...ingestors.base import Ingestor
from .initializer_base import IngestorInitializerBase


class OpenWebUIInitializer(IngestorInitializerBase):
    __doc__ = __doc__

    def ingestor_class(self) -> type[Ingestor]:
        return OpenWebUIIngestor

    def is_installed(self):
        try:
            resp = requests.get("http://localhost:8080/api/version")
            if resp.status_code == 200:
                # Warn if version is old
                try:
                    # This can fail at json parsing, key indexing, split
                    # unpacking, or int conversion, all of which are caught and
                    # ignored since this is just to do a version check.
                    version = resp.json()["version"]
                    major, minor, patch = (int(elt) for elt in version.split("."))
                    if major != 0 or minor != 5 or patch < 4:
                        print(f"WARNING: Open WebUI version {version} not tested!")
                except (requests.exceptions.JSONDecodeError, KeyError, ValueError):
                    pass
                return True
        except Exception:
            pass
        return False
