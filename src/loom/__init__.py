"""Loom — Smart Internet Research MCP Server.

Weaves scraping, search, LLMs, and persistent browser sessions into a
single research thread. Exposes 23 MCP tools over streamable-HTTP and a
Typer CLI (`loom`) for terminal use.

See README.md for usage and `docs/` for reference.
"""

__version__ = "0.1.0a1"
__author__ = "Ahmed Adel Bakr Alderai"
__license__ = "Apache-2.0"

from loom.cache import CacheStore
from loom.validators import UrlSafetyError, cap_chars, validate_url

__all__ = [
    "CacheStore",
    "UrlSafetyError",
    "__author__",
    "__license__",
    "__version__",
    "cap_chars",
    "validate_url",
]
