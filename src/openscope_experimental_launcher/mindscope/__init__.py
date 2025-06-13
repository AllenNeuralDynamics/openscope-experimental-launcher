"""
Mindscope rig experiment launchers.

This package contains rig-specific experiment launchers for different Mindscope platforms:
- ClusterExperiment: For cluster rig experiments with pickle file output
- MesoscopeExperiment: For mesoscope rig experiments with multi-plane imaging
- NeuropixelExperiment: For neuropixel rig experiments with electrophysiology data
"""

from .cluster import ClusterExperiment
from .mesoscope import MesoscopeExperiment
from .neuropixel import NeuropixelExperiment

__all__ = [
    'ClusterExperiment',
    'MesoscopeExperiment', 
    'NeuropixelExperiment'
]