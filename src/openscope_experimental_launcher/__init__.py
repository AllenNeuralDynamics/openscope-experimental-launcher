"""
OpenScope Experimental Launcher

A Python package for launching OpenScope Bonsai workflows with advanced 
metadata generation and session tracking capabilities.
"""

__version__ = "0.1.0"

# Import main classes for easy access
from .base.experiment import BaseExperiment
from .base import bonsai_interface
from .slap2.launcher import SLAP2Experiment