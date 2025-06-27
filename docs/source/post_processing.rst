Post-Processing Tools
====================

The OpenScope Experimental Launcher includes a modular post-processing system designed to handle data transformation and session creation after experiment completion.

Overview
--------

Post-processing tools are standalone, focused utilities that transform raw experiment data and create standardized session files. Each tool follows a consistent design pattern for maximum reusability and maintainability.

.. note::
   Post-processing tools are completely independent of the launcher system and can be run on any session folder, whether from a recent experiment or historical data.

Core Components
---------------

**Session Creator**
   Creates standardized session.json files using AIND data schema from experiment metadata

**Data Converters**
   Transform experiment-specific data formats into standardized structures

**Enhancement Tools**
   Add launcher-specific metadata and enrichment to session files

Design Philosophy
-----------------

**Single Responsibility**
   Each tool performs one specific transformation or analysis task

**Modular Session Creation**
   Session.json generation is handled in post-processing for better extensibility

**Session-Based Input**
   Tools operate on session folders containing experiment data

**Self-Contained**
   No dependencies on launcher classes or complex state management

**Unified Parameter File**
   All tools accept a param_file (JSON) as input, and prompt for missing fields interactively

**Python API and CLI**
   Tools expose a `run_postprocessing(param_file)` function for both CLI and Python use

Integration with Launchers
--------------------------

Post-processing tools are automatically called by specific launchers after experiment completion:

**Automatic Integration:**

.. code-block:: python

   from openscope_experimental_launcher.launchers import PredictiveProcessingLauncher
   launcher = PredictiveProcessingLauncher(param_file="experiment_params.json")
   success = launcher.run()
   # Post-processing automatically runs after successful experiment

**Manual Execution:**

.. code-block:: python

   from openscope_experimental_launcher.post_processing import session_creator
   result = session_creator.run_postprocessing(param_file="path/to/processed_parameters.json")

.. code-block:: bash

   python -m openscope_experimental_launcher.post_processing.session_creator path/to/processed_parameters.json

Adding New Tools
----------------

When creating new post-processing tools, follow this template structure:

**File Structure:**

.. code-block:: python

   def run_postprocessing(param_file: str = None, overrides: dict = None) -> int:
       """
       Main processing function.
       Loads parameters, prompts for missing fields, and runs processing.
       Returns 0 on success, nonzero on error.
       """
       # Implementation here
       pass

   if __name__ == "__main__":
       import argparse
       import sys
       parser = argparse.ArgumentParser(description="Tool description")
       parser.add_argument("param_file", help="Path to processed_parameters.json")
       args = parser.parse_args()
       sys.exit(run_postprocessing(param_file=args.param_file))

**Integration Steps:**

1. Create the tool in ``src/openscope_experimental_launcher/post_processing/``
2. Add the unified CLI and Python API entry point as above
3. Update launcher's ``run_post_processing()`` method if automatic integration is needed

Available Tools
---------------

Session Creator
~~~~~~~~~~~~~~~

**Purpose**: Creates standardized ``session.json`` files from experiment data

**Location**: ``post_processing/session_creator.py``

**Usage**:

.. code-block:: bash

   python -m openscope_experimental_launcher.post_processing.session_creator path/to/processed_parameters.json
   # Force overwrite existing session.json
   python -m openscope_experimental_launcher.post_processing.session_creator path/to/processed_parameters.json --force

**Input Files**:
- ``end_state.json``: Runtime information from experiment completion
- ``launcher_metadata.json``: Launcher configuration and parameters
- Output folder contents: Used to determine data streams and timing

**Output**: ``session.json`` file using AIND data schema format

**Key Features**:
- Reads experiment data from files (not runtime state)
- Can regenerate session files after the fact
- Handles custom end state data from launcher subclasses
- Provides detailed error reporting and logging

Predictive Processing Stimulus Converter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Converts Predictive Processing stimulus tables to standardized format

**Location**: ``post_processing/pp_stimulus_converter.py``

**Usage**:

.. code-block:: bash

   python -m openscope_experimental_launcher.post_processing.pp_stimulus_converter path/to/processed_parameters.json

**Input**: Raw stimulus table files from Predictive Processing experiments

**Output**: Standardized stimulus table format compatible with downstream analysis

Example Tool Template
~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Template for creating new post-processing tools

**Location**: ``post_processing/example_tool_template.py``

**Usage**: Copy and modify this template to create new tools

**Features**:
- Consistent command-line interface
- Error handling patterns
- Logging setup
- Input validation