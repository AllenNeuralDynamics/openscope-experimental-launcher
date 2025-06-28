"""
Stimulus Table Utilities

This module will contain standardized functions for creating and manipulating 
stimulus tables across different OpenScope experiment types.

Future implementations will include:
- Standardized stimulus table schema validation
- Cross-experiment format conversion utilities
- Common stimulus table analysis functions
- Integration with AIND data standards

Currently, experiment-specific stimulus table generation is handled by
dedicated post-acquisition tools in the post_acquisition module.

For example:
- Predictive Processing: Uses stimulus_table_predictive_processing.py
- Other experiments: Will have dedicated converter tools

This approach provides better modularity and maintainability compared to
a single monolithic stimulus table generator.
"""

# Placeholder for future standardized stimulus table utilities
def create_standardized_stimulus_table():
    """
    Future function to create standardized stimulus tables.
    
    This will implement a common schema for stimulus tables across
    all OpenScope experiment types, ensuring consistency in:
    - Column naming conventions
    - Data types and formats
    - Timing synchronization
    - Metadata inclusion
    """
    raise NotImplementedError("Standardized stimulus table creation not yet implemented")


def validate_stimulus_table_schema():
    """
    Future function to validate stimulus table format.
    
    This will ensure stimulus tables conform to OpenScope standards
    and are compatible with downstream analysis tools.
    """
    raise NotImplementedError("Stimulus table validation not yet implemented")


def convert_to_aind_format():
    """
    Future function to convert stimulus tables to AIND data format.
    
    This will provide integration with the Allen Institute for Neural
    Dynamics data standards and pipeline tools.
    """
    raise NotImplementedError("AIND format conversion not yet implemented")
