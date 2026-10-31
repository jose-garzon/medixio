"""Local observability: error capture, metrics, heartbeats and health checks."""

from functools import lru_cache

from medixio.config import get_settings
from medixio.observability.store import Store


@lru_cache
def obs() -> Store:
    return Store(get_settings().observability_db)


__all__ = ["Store", "obs"]
