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

**Command-Line Interface**
   Simple, scriptable interfaces for automation and batch processing


Integration with Launchers
---------------------------

Post-processing tools are automatically called by specific launchers after experiment completion:

**Automatic Integration:**

.. code-block:: python

   from openscope_experimental_launcher.launchers import PredictiveProcessingLauncher
   
   launcher = PredictiveProcessingLauncher()
   success = launcher.run("experiment_params.json")
   # Post-processing automatically runs after successful experiment

**Manual Execution:**

.. code-block:: python

   # Run post-processing independently
   from openscope_experimental_launcher.post_processing.pp_stimulus_converter import process_session
   
   success = process_session("/path/to/session/folder")


Adding New Tools
----------------

When creating new post-processing tools, follow this template structure:

**File Structure:**

.. code-block:: python

   def process_session(session_folder: str, output_folder: str = None) -> bool:
       """
       Main processing function.
       
       Args:
           session_folder: Path to session data folder
           output_folder: Optional output folder (defaults to session folder)
           
       Returns:
           True if successful, False otherwise
       """
       # Implementation here
       pass

   def main():
       """Command-line interface."""
       parser = argparse.ArgumentParser(description="Tool description")
       parser.add_argument("session_folder", help="Path to session folder")
       parser.add_argument("output_folder", nargs='?', help="Output folder (optional)")
       
       args = parser.parse_args()
       success = process_session(args.session_folder, args.output_folder)
       sys.exit(0 if success else 1)

   if __name__ == "__main__":
       main()


**Integration Steps:**

1. Create the tool in ``src/openscope_experimental_launcher/post_processing/``
2. Add command-line interface following the template
3. Update launcher's ``run_post_processing()`` method if automatic integration is needed


Available Tools
---------------

Session Creator
~~~~~~~~~~~~~~~

**Purpose**: Creates standardized ``session.json`` files from experiment data

**Location**: ``post_processing/session_creator.py``

**Usage**:

.. code-block:: bash

   # Create session file from experiment output
   python -m openscope_experimental_launcher.post_processing.session_creator /path/to/output
   
   # Force overwrite existing session.json
   python -m openscope_experimental_launcher.post_processing.session_creator /path/to/output --force

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

   # Convert stimulus table
   python -m openscope_experimental_launcher.post_processing.pp_stimulus_converter /path/to/session

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