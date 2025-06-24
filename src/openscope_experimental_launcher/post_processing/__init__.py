"""
Post-processing tools for OpenScope experiments.

This package contains tools that process experiment output folders after
experiments complete. These tools are designed to work by reading data
from the output folder, allowing them to regenerate outputs after the fact.

"""

from .session_creator import SessionCreator

__all__ = ['SessionCreator']