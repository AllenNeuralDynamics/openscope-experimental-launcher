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

**Modular, pipeline-driven experimental launcher for OpenScope. Pre- and post-acquisition work runs via pipeline modules, while the launcher core also provides built-in session synchronization and orchestration.**

Overview
--------

The launcher merges rig config + JSON parameter file + runtime prompts, starts a subprocess (generic or interface-specific), monitors resources, and writes flattened metadata (``processed_parameters.json``, ``end_state.json``, ``debug_state.json``) for post-acquisition tools.

Key Features
------------

* **Modular Pipelines** – Ordered pre/post module lists drive setup and teardown.
* **End/Debug State** – Each run writes ``end_state.json`` and (on crash) ``debug_state.json``.
* **Rig Placeholders** – Use ``{rig_param:<key>}`` in ``script_parameters`` for dynamic injection.
* **Unified Parameters** – Rig config + param file + prompts are merged into ``processed_parameters.json``.
* **Post-Acquisition Generation** – Optional modules (for example ``session_creator``) can generate artifacts like ``session.json``.

Quick Start
-----------

1. **Installation**:

   .. code-block:: bash
   
      pip install -e .

2. **Run via the repo entry point**:

   .. code-block:: bash

      python run_launcher.py --param_file params/example_minimalist_params.json

   Your parameter file must include a ``launcher`` key (one of: ``base``, ``bonsai``, ``matlab``, ``python``).

3. **Basic usage from Python**:

   .. code-block:: python

      from openscope_experimental_launcher.launchers.base_launcher import BaseLauncher

      launcher = BaseLauncher(param_file="path/to/parameters.json")
      success = launcher.run()

4. **Parameter File Example**:

   .. code-block:: json

      {
        "launcher": "bonsai",
        "subject_id": "test_mouse_001",
        "user_id": "researcher_name",
        "script_path": "path/to/workflow.bonsai",
        "output_root_folder": "C:/experiment_data",
        "pre_acquisition_pipeline": ["mouse_weight_pre_prompt"],
        "post_acquisition_pipeline": ["session_creator"]
      }

Architecture
------------

The package uses a modular architecture with clear separation of concerns:

**Core Components:**

* **Launchers** (``launchers/``): Core orchestration via ``BaseLauncher``
* **Interfaces** (``interfaces/``): Stateless subprocess creation adapters
* **Pipeline Modules** (``pre_acquisition/`` / ``post_acquisition/``): Ordered tasks (:doc:`modules`)
* **Utilities** (``utils/``): Configuration, Git, prompting, logging helpers
* **Entrypoints** (repo root): ``run_launcher.py`` and ``run_module.py`` helpers

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
   
   quickstart
   installation

   configuration
   rig_config
   parameter_files

   rig_launchers
   launcher-configuration
   matlab_launcher
   end_state_system

   modules

   resource-monitoring
   logging
   launcher_metadata

   architecture
   contributing

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
