"""
SLAP2 module for OpenScope experimental launchers.

Contains specialized functionality for SLAP2 (Simultaneous Light Activation 
and Photometry) experiments with metadata generation and stimulus table creation.
"""

from .launcher import SLAP2Experiment
from .session_builder import SLAP2SessionBuilder
from .stimulus_table import SLAP2StimulusTableGenerator

__all__ = [
    "SLAP2Experiment",
    "SLAP2SessionBuilder",
    "SLAP2StimulusTableGenerator"
]