"""
Base module for OpenScope experimental launchers.

Contains the core functionality for launching Bonsai workflows with
parameter management, process monitoring, and metadata generation.
"""

from .experiment import BaseExperiment
from .bonsai_interface import BonsaiInterface
from .session_builder import BaseSessionBuilder

__all__ = [
    "BaseExperiment",
    "BonsaiInterface", 
    "BaseSessionBuilder"
]