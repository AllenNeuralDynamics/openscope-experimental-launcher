Launcher Architecture
=====================

.. graphviz::

   digraph launcher_architecture {
       rankdir=LR;
       node [shape=box, style=filled, fillcolor=lightgray];

       subgraph cluster_core {
           label="Core Logic";
           BaseLauncher [label="BaseLauncher\n(core logic)"];
           ParamUtils [label="param_utils.py\n(parameter loading, prompts)"];
           RigConfig [label="rig_config.py\n(rig hardware config)"];
           GitManager [label="git_manager.py\n(repo management)"];
           Logging [label="Logging\n(session + centralized)"];
       }

       subgraph cluster_launchers {
           label="Launchers";
           BonsaiLauncher [label="BonsaiLauncher"];
           MatlabLauncher [label="MatlabLauncher"];
           PythonLauncher [label="PythonLauncher"];
           MinimalistLauncher [label="MinimalistLauncher"];
       }

       subgraph cluster_pre {
           label="Pre-Acquisition Pipeline";
           PreModules [label="Pre-Acquisition Modules\n(mouse weight, ZMQ, etc.)"];
       }

       subgraph cluster_post {
           label="Post-Acquisition Pipeline";
           PostModules [label="Post-Acquisition Modules\n(session_creator, notes, etc.)"];
       }

       subgraph cluster_interfaces {
           label="Interfaces";
           InterfaceBonsai [label="BonsaiInterface"];
           InterfaceMatlab [label="MatlabInterface"];
           InterfacePython [label="PythonInterface"];
       }

       ParamFile [label="Parameter File (JSON)", shape=note, fillcolor=lightyellow];
       RigConfigFile [label="Rig Config (TOML)", shape=note, fillcolor=lightyellow];
       RuntimePrompt [label="Runtime Prompts", shape=note, fillcolor=lightyellow];

       # Relationships
       ParamFile -> PreModules;
       PreModules -> BaseLauncher;
       BaseLauncher -> BonsaiLauncher;
       BaseLauncher -> MatlabLauncher;
       BaseLauncher -> PythonLauncher;
       BaseLauncher -> MinimalistLauncher;
       BonsaiLauncher -> InterfaceBonsai;
       MatlabLauncher -> InterfaceMatlab;
       PythonLauncher -> InterfacePython;
       BaseLauncher -> ParamUtils;
       BaseLauncher -> RigConfig;
       BaseLauncher -> GitManager;
       BaseLauncher -> Logging;
       BonsaiLauncher -> Logging;
       MatlabLauncher -> Logging;
       PythonLauncher -> Logging;
       MinimalistLauncher -> Logging;
       BaseLauncher -> PostModules;
       PostModules -> ParamFile;
       RigConfigFile -> RigConfig;
       RuntimePrompt -> ParamUtils;
   }

.. note::
   The above diagram is compiled automatically by GitHub Actions and reflects the current modular pipeline architecture.

Repository Folder Structure
--------------------------

- ``src/openscope_experimental_launcher/``: Main package source code
  - ``launchers/``: Generic and interface-specific launcher classes (Bonsai, MATLAB, Python, etc.)
  - ``interfaces/``: Stateless process creation utilities for each platform
  - ``pre_acquisition/``: Modular pre-acquisition pipeline modules (mouse weight, ZMQ, etc.)
  - ``post_acquisition/``: Modular post-acquisition pipeline modules (session creation, notes, enhancement, etc.)
  - ``utils/``: Shared utilities (configuration, git, logging, etc.)
- ``params/``: Example and project-specific parameter files (JSON)
- ``tests/``: Unit and integration tests for all core logic and modules
- ``docs/``: Documentation sources (reStructuredText, Sphinx, and build scripts)
- ``run_launcher.py``: CLI entry point for running experiments with a parameter file
- ``run_module.py``: CLI entry point for running any pipeline module directly
- ``setup.py``, ``pyproject.toml``: Packaging and build configuration
- ``README.md``, ``LICENSE``, etc.: Project metadata and top-level documentation

Philosophy: Modular Pre- and Post-Acquisition
---------------------------------------------

The OpenScope launcher is designed for maximum flexibility and reproducibility. All experiment-specific logic (e.g., mouse weight prompts, ZMQ signaling, experiment notes, data enhancement) is handled by modular pipeline modules, not the launcher core. This ensures:

- **Generic launchers** for each language/software (Bonsai, MATLAB, Python)
- **All pre- and post-acquisition steps** are modular and easily extended
- **Parameter files** define which modules run for each experiment
- **Symmetry**: Pre- and post-acquisition are handled identically, via ordered module lists

How Modules Are Inserted
------------------------

To add a pre- or post-acquisition step, simply add the module name to the appropriate list in your parameter file:

.. code-block:: json

    {
      "pre_acquisition_pipeline": ["mouse_weight_pre_prompt", "zmq_ready_publisher"],
      "post_acquisition_pipeline": ["mouse_weight_post_prompt", "experiment_notes_post_prompt"],
      ...
    }

Each module is a Python file in `src/openscope_experimental_launcher/pre_acquisition/` or `post_acquisition/`, and must accept a `param_file` argument and return 0 for success, 1 for failure.

For more, see the [Pre-Acquisition](pre_acquisition.html) and [Post-Acquisition](post_acquisition.html) pages, and the [Contributing](contributing.html) guide.
