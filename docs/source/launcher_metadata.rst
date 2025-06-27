Launcher Metadata Folder
=======================

Overview
--------

Each experiment session run with the OpenScope Experimental Launcher creates a `launcher_metadata` folder inside the session output directory. This folder contains metadata and configuration files that document the full context of the experiment, supporting reproducibility, troubleshooting, and downstream analysis.

Purpose
-------

The `launcher_metadata` folder provides a complete record of:

- The parameters and configuration used for the experiment
- The runtime environment and software versions
- Any user prompts or overrides entered during the session
- Additional metadata needed for post-processing and data provenance

Contents
--------

Typical files found in the `launcher_metadata` folder include:

- **processed_parameters.json**
  - The unified parameter file used for the experiment, including all overrides and runtime prompts.
  - This is the canonical input for all post-processing tools.

- **launcher_metadata.json**
  - Metadata about the launcher, including:
    - Launcher type and version
    - Timestamps (start, stop)
    - User and subject IDs
    - Script and repository information
    - System/platform details

- **end_state.json**
  - Captures the final state of the experiment, including:
    - Outcome (success/failure)
    - User notes
    - Any runtime-collected data (e.g., animal weight)

- **debug_state.json** (optional)
  - If an error or crash occurs, this file contains exception details and stack traces for troubleshooting.

- **Other files**
  - Additional metadata or logs may be included by custom launchers or post-processing tools.

How It Is Created
-----------------

- The folder is created automatically by the launcher at the start of each experiment session.
- Files are written as the experiment progresses:

  - Parameters and launcher metadata are saved at initialization.
  - End state and debug files are saved at experiment completion or on error.

Best Practices
--------------

- **Do not edit files in `launcher_metadata` manually.**
  - These files are used by post-processing tools and for data provenance.
- **Always use `processed_parameters.json` as the input for post-processing.**
- **Retain the entire session folder, including `launcher_metadata`, for reproducibility and auditing.**

Example Structure
-----------------

.. code-block:: text

   output_session_folder/
   ├── experiment.log
   ├── session.json
   ├── launcher_metadata/
   │   ├── processed_parameters.json
   │   ├── launcher_metadata.json
   │   ├── end_state.json
   │   └── debug_state.json
   └── ... (other experiment files)

For more details, see the code in `src/openscope_experimental_launcher/launchers/base_launcher.py` and related modules.
