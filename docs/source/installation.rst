Installation Guide
==================

System Requirements
-------------------

.. warning::
   This package is **Windows-only** and will not work on Linux or macOS due to its use of Windows-specific APIs and process management features.

**Required:**

- Windows 10 or Windows 11
- Python 3.8 or higher
- Git (for repository management)

**Optional Dependencies:**

- Bonsai (required for running experiments)

Pre-Installation Setup
----------------------

1. **Install Python**

   Download and install Python 3.8+ from `python.org <https://www.python.org/downloads/>`_
   
   .. note::
      Make sure to check "Add Python to PATH" during installation.

2. **Install Git**

   Download and install Git from `git-scm.com <https://git-scm.com/download/win>`_


Installation Methods
--------------------

Development Installation (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For users who want to modify the code or contribute to development:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/AllenNeuralDynamics/openscope-experimental-launcher.git
   cd openscope-experimental-launcher
   
   # Install in development mode with all dependencies
   pip install -e .[dev]

Standard Installation
~~~~~~~~~~~~~~~~~~~~~

For users who just want to use the package:

.. code-block:: bash

   pip install openscope-experimental-launcher

From Source
~~~~~~~~~~~

.. code-block:: bash

   # Download and install from source
   pip install git+https://github.com/AllenNeuralDynamics/openscope-experimental-launcher.git

Verifying Installation
----------------------

Test that the installation was successful:

.. code-block:: python

   import openscope_experimental_launcher
   print(openscope_experimental_launcher.__version__)

.. code-block:: python

   # Test basic functionality
   from openscope_experimental_launcher.launchers import BaseLauncher
   launcher = BaseLauncher()
   print("Installation successful!")