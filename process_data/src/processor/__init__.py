import logging

from .client_handler import ClientHandler
from .config import Config
from .index_factory import IndexFactory
from .permission_handler import PermissionHandler

logger = logging.getLogger(__name__)

logger.addHandler(logging.StreamHandler())

__all__ = ["IndexFactory", "PermissionHandler", "ClientHandler", "Config"]
