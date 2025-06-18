.. Doc Template documentation master file, created by
   sphinx-quickstart on Wed Aug 17 15:36:32 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


OpenScope Experimental Launcher Documentation
============================================

.. image:: https://img.shields.io/badge/license-MIT-brightgreen
   :target: https://github.com/AllenNeuralDynamics/openscope-experimental-launcher/blob/main/LICENSE
   :alt: License

.. image:: https://img.shields.io/badge/platform-Windows-blue?logo=windows
   :alt: Platform

.. image:: https://img.shields.io/badge/python->=3.8-blue?logo=python
   :alt: Python Version

**Windows-only experimental launcher for OpenScope Bonsai workflows with metadata generation and session tracking.**

Overview
--------

The OpenScope Experimental Launcher is a Windows-specific package designed to manage and execute Bonsai-based neuroscience experiments in the OpenScope project. It provides robust process management, parameter handling, session tracking, and metadata generation capabilities.

Key Features
------------

🔧 **Bonsai Process Management**
   Start, monitor, and manage Bonsai workflow execution with Windows-specific process control

📊 **Session Tracking**
   Generate unique session IDs and comprehensive experiment metadata

🗂️ **Parameter Management**
   Load and validate experiment parameters from JSON configuration files

🔄 **Git Repository Management**
   Automatic cloning and version control of workflow repositories

📈 **Process Monitoring**
   Memory usage monitoring and automatic handling of runaway processes

🎯 **Multi-Rig Support**
   Specialized launchers for different experimental rigs (SLAP2, etc.)

Quick Start
-----------

1. **Installation**:

   .. code-block:: bash
   
      pip install -e .

2. **Basic Usage**:

   .. code-block:: python
   
      from openscope_experimental_launcher.base.experiment import BaseExperiment
      
      # Create and run experiment
      experiment = BaseExperiment()
      success = experiment.run("path/to/parameters.json")

3. **Parameter File Example**:

   .. code-block:: json
   
      {
          "subject_id": "test_mouse_001",
          "user_id": "researcher_name",
          "bonsai_path": "path/to/workflow.bonsai",
          "repository_url": "https://github.com/user/repo.git",
          "output_directory": "C:/experiment_data"
      }

Architecture
------------

The package consists of several key components:

- **BaseExperiment**: Core experiment launcher with Bonsai process management
- **SLAP2Experiment**: Specialized launcher for SLAP2 imaging experiments  
- **Utility Classes**: Configuration loading, Git management, process monitoring

System Requirements
-------------------

.. warning::
   This package is **Windows-only** and requires:
   
   - Windows 10 or Windows 11
   - Python 3.8 or higher
   - Bonsai (installed separately)
   - Git for repository management

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   installation
   quickstart
   parameter_files
   rig_launchers
   examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference
     api/base
   api/slap2
   api/utils

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide
   
   contributing
   testing
   deployment

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources
   
   troubleshooting
   changelog
   license

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
