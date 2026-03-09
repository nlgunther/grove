"""
Manifest Manager - Hierarchical XML Data Management CLI
Version 3.4.0
"""

from .manifest_core import (
    ManifestRepository,
    NodeSpec,
    ManifestView,
    Result,
    TaskStatus,
    Validator,
)
from .config import Config
from .id_sidecar import IDSidecar
from .storage import StorageManager, PasswordRequired

__version__ = "3.5.0"
__all__ = [
    "ManifestRepository",
    "NodeSpec",
    "ManifestView",
    "Result",
    "TaskStatus",
    "Validator",
    "Config",
    "IDSidecar",
    "StorageManager",
    "PasswordRequired",
]
