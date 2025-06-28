"""
OpenScope Experimental Launcher

A Python package for launching OpenScope experiments with modular architecture,
supporting Bonsai, MATLAB, and Python workflows.
"""

__version__ = "0.1.0"

# Import main launcher classes for easy access
from .launchers.base_launcher import BaseLauncher
from .launchers.bonsai_launcher import BonsaiLauncher
from .launchers.matlab_launcher import MatlabLauncher
from .launchers.python_launcher import PythonLauncher
# Import interface modules
from .interfaces import bonsai_interface, matlab_interface, python_interface
import sys
import os

# Add scripts directory to path
scripts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

__all__ = [
    "BaseLauncher",
    "BonsaiLauncher", 
    "MatlabLauncher",
    "PythonLauncher",
    "bonsai_interface",
    "matlab_interface", 
    "python_interface",
]
