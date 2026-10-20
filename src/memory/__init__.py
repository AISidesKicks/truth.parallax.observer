"""Memory module for OpenViking integration."""

from .openviking_config import get_openviking_config, init_openviking_config
from .viking_client import VikingClient, setup_logging

__all__ = ["VikingClient", "get_openviking_config", "init_openviking_config", "setup_logging"]
