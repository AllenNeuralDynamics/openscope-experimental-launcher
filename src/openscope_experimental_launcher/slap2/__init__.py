"""
SLAP2 module for OpenScope experimental launchers.

Contains specialized functionality for SLAP2 (Simultaneous Light Activation 
and Photometry) experiments with metadata generation and stimulus table creation.
"""

from .launcher import SLAP2Experiment

__all__ = [
    "SLAP2Experiment"
]