.. Doc Template documentation master file, created by
   sphinx-quickstart on Wed Aug 17 15:36:32 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


OpenScope Experimental Launcher Documentation
==============================================

.. image:: https://img.shields.io/badge/license-MIT-brightgreen
   :target: https://github.com/AllenNeuralDynamics/openscope-experimental-launcher/blob/main/LICENSE
   :alt: License

.. image:: https://img.shields.io/badge/platform-Windows-blue?logo=windows
   :alt: Platform

.. image:: https://img.shields.io/badge/python->=3.8-blue?logo=python
   :alt: Python Version

**Modular, pipeline-driven experimental launcher for OpenScope. All pre- and post-acquisition logic is handled by standalone modules, not the launcher core.**

Overview
--------

The OpenScope Experimental Launcher is a modular package designed to manage and execute neuroscience experiments across multiple platforms. It features a clean architectural separation between interface-specific process creation and common launcher functionality, supporting Bonsai, MATLAB, and Python workflows.

Key Features
------------

🏗️ **Modular Architecture**
   Clean separation between launchers (process management), interfaces (process creation), and pipeline modules (pre/post-acquisition logic)

🔧 **Multi-Interface Support**
   Dedicated launchers for Bonsai, MATLAB, and Python workflows

📊 **Session Tracking**
   Generate unique session IDs and comprehensive experiment metadata

🗂️ **Unified Parameter Management**
   Consistent parameter handling with ``script_path`` convention across all interfaces

🔌 **Pipeline Modules**
   All pre- and post-acquisition steps are handled by modular, reusable Python modules, specified in the parameter file

Quick Start
-----------

1. **Installation**:

   .. code-block:: bash
   
      pip install -e .

2. **Basic Usage**:

   .. code-block:: python
   
      from openscope_experimental_launcher.launchers import BonsaiLauncher
      
      # Create and run Bonsai experiment
      launcher = BonsaiLauncher()
      success = launcher.run("path/to/parameters.json")

3. **Using Project Scripts**:

   .. code-block:: bash
   
      # Use project-specific launcher scripts
      python scripts/minimalist_launcher.py scripts/example_minimalist_params.json
      python scripts/predictive_processing_launcher.py experiment_params.json

3. **Parameter File Example**:

   .. code-block:: json      {
          "subject_id": "test_mouse_001",
          "user_id": "researcher_name",
          "script_path": "path/to/workflow.bonsai",
          "repository_url": "https://github.com/user/repo.git",
          "output_root_folder": "C:/experiment_data",
          "collect_mouse_runtime_data": true,
          "protocol_id": ["protocol_001"],
          "pre_acquisition_pipeline": ["mouse_weight_pre_prompt", "zmq_ready_publisher"],
          "post_acquisition_pipeline": ["session_creator", "mouse_weight_post_prompt", "experiment_notes_post_prompt"]
      }

Architecture
------------

The package uses a modular architecture with clear separation of concerns:

**Core Components:**

- **Launchers** (``src/openscope_experimental_launcher/launchers/``): Interface-specific launcher classes that inherit from ``BaseLauncher``
- **Interfaces** (``src/openscope_experimental_launcher/interfaces/``): Stateless process creation utilities for each platform
- **Pre/Post-Acquisition Modules** (``src/openscope_experimental_launcher/pre_acquisition/``, ``post_acquisition/``): Modular pipeline steps for experiment setup and teardown
- **Utilities** (``src/openscope_experimental_launcher/utils/``): Shared utilities for configuration, Git management, and monitoring
- **Scripts** (``scripts/``): Project-specific launcher scripts for custom experiments

**Design Principles:**

- **Single Responsibility**: Each launcher handles one interface type, each interface handles only process creation, each module handles one pipeline step
- **Stateless Functions**: Interface modules provide pure functions with no global state
- **Common Base Logic**: All launchers share functionality through ``BaseLauncher`` (process management, monitoring, logging)
- **Project Flexibility**: Custom launchers and modules can be created without modifying core code

System Requirements
-------------------

.. note::
   Primary support is for **Windows** with untested cross-platform compatibility:
   
   - Windows 10 or Windows 11 (primary platform)
   - Python 3.8 or higher
   - Interface-specific requirements:
   
     - **Bonsai**: Bonsai installation for Bonsai workflows
     - **MATLAB**: MATLAB installation for MATLAB scripts  
     - **Python**: Python environment for Python scripts
   - Git for repository management (optional)

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   installation
   quickstart
   configuration
   rig_config
   parameter_files
   rig_launchers
   pre_acquisition
   post_acquisition
   logging
   launcher_metadata
   architecture
   contributing

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
