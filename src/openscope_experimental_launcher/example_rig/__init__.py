"""
Example rig module for OpenScope experimental launchers.

This module demonstrates how to create rig-specific implementations
that extend the base functionality.
"""

from .session_builder import ExampleRigSessionBuilder

__all__ = [
    "ExampleRigSessionBuilder",
]
