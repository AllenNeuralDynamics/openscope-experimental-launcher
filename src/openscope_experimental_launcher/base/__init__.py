"""
Base module for OpenScope experimental launchers.

Contains the core functionality for launching Bonsai workflows with
parameter management, process monitoring, and metadata generation.
"""

from .experiment import BaseExperiment
from . import bonsai_interface

__all__ = [
    "BaseExperiment",
    "bonsai_interface"
]