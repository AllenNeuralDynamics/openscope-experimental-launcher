Launcher Architecture
=====================

.. graphviz::

   digraph launcher_flow {
       rankdir=LR;
       node [shape=box, style=filled, fillcolor=lightgray];

       ParamFile [label="Parameter File (JSON)", shape=note, fillcolor=lightyellow];
       RigConfigFile [label="Rig Config (TOML)", shape=note, fillcolor=lightyellow];
       RuntimePrompt [label="Runtime Prompts", shape=note, fillcolor=lightyellow];
       ParamMerge [label="Merged Parameters\n(param > rig config > runtime)", shape=box, fillcolor=lightblue];
       PrePipeline [label="Pre-Acquisition Pipeline\n(modules)"];
       Acquisition [label="Acquisition Subprocess\n(Bonsai, MATLAB, Python, etc.)"];
       PostPipeline [label="Post-Acquisition Pipeline\n(modules)"];
       SessionFolder [label="Session Folder\n(all logs, metadata, data)", shape=folder, fillcolor=yellow];

       ParamFile -> ParamMerge;
       RigConfigFile -> ParamMerge;
       RuntimePrompt -> ParamMerge;
       ParamMerge -> PrePipeline;
       PrePipeline -> Acquisition;
       Acquisition -> PostPipeline;
       PrePipeline -> SessionFolder;
       Acquisition -> SessionFolder;
       PostPipeline -> SessionFolder;
       ParamMerge -> SessionFolder;
   }

.. note::
   The above diagram is compiled automatically by GitHub Actions and reflects the current modular pipeline architecture and data flow.

Launcher Flow Overview
----------------------

1. **Parameter File Input:**
   - The user provides a parameter file (JSON) to the launcher.
2. **Rig Config Merge:**
   - The launcher loads the rig config (TOML) and merges it with the parameter file (parameters override rig config).
3. **Runtime Prompts:**
   - The launcher interactively prompts for any missing required values, which override both param file and rig config.
4. **Pre-Acquisition Pipeline:**
   - The launcher runs each pre-acquisition module in order, passing the merged parameter file. Each module can read/write to the session folder.
5. **Acquisition Subprocess:**
   - The launcher starts the main experiment process (Bonsai, MATLAB, Python, etc.) with the merged parameters. The subprocess writes data and logs to the session folder.
6. **Post-Acquisition Pipeline:**
   - After acquisition, the launcher runs each post-acquisition module in order, again passing the merged parameter file. These modules can generate session files, enhance metadata, and write results to the session folder.

**All steps (launcher, pre-acquisition modules, acquisition subprocess, post-acquisition modules) write logs, metadata, and data to the session folder.**

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
