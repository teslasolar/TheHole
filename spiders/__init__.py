"""
THE HOLE spider registry.

Import all spider classes and expose a registry dict for dynamic lookup.
"""

from .arxiv import ArxivSpider
from .base import HoleSpider, make_document
from .blogs import BlogSpider
from .fediverse import FediverseSpider
from .github import GithubSpider
from .hn import HackerNewsSpider
from .lobsters import LobstersSpider
from .pubmed import PubmedSpider
from .rfc import RfcSpider
from .stackoverflow import StackOverflowSpider

# name -> class mapping for dynamic instantiation
SPIDERS = {
    "arxiv": ArxivSpider,
    "github": GithubSpider,
    "hn": HackerNewsSpider,
    "stackoverflow": StackOverflowSpider,
    "blogs": BlogSpider,
    "pubmed": PubmedSpider,
    "rfc": RfcSpider,
    "lobsters": LobstersSpider,
    "fediverse": FediverseSpider,
}

__all__ = [
    "HoleSpider",
    "make_document",
    "ArxivSpider",
    "BlogSpider",
    "FediverseSpider",
    "GithubSpider",
    "HackerNewsSpider",
    "LobstersSpider",
    "PubmedSpider",
    "RfcSpider",
    "StackOverflowSpider",
    "SPIDERS",
]
