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

       subgraph cluster_interfaces {
           label="Interfaces";
           InterfaceBonsai [label="BonsaiInterface"];
           InterfaceMatlab [label="MatlabInterface"];
           InterfacePython [label="PythonInterface"];
       }

       subgraph cluster_post {
           label="Post-Processing";
           PostProcessing [label="Post-Processing\n(session_creator, etc.)"];
       }

       # Parameter tiers
       ParamFile [label="Parameter File (JSON)", shape=note, fillcolor=lightyellow];
       RigConfigFile [label="Rig Config (TOML)", shape=note, fillcolor=lightyellow];
       RuntimePrompt [label="Runtime Prompts", shape=note, fillcolor=lightyellow];

       # Relationships
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
       BaseLauncher -> PostProcessing;

       # Parameter tiers flow
       ParamFile -> ParamUtils;
       RigConfigFile -> RigConfig;
       RuntimePrompt -> ParamUtils;

       # Logging flow
       BaseLauncher -> Logging;
       BonsaiLauncher -> Logging;
       MatlabLauncher -> Logging;
       PythonLauncher -> Logging;
       MinimalistLauncher -> Logging;
   }


Architecture Details
--------------------

- **Parameter Tiers:**

  1. **Parameter File (JSON):** User-supplied experiment settings.
  2. **Rig Config (TOML):** Hardware and rig-specific configuration.
  3. **Runtime Prompts:** Interactive prompts for missing or runtime-only values.
  - **Priority:** Runtime Prompts > Parameter File > Rig Config

- **Logging:**

  - Each launcher and the core logic write to session-based log files.
  - Optionally, logs are mirrored to a centralized directory.
  - Logging covers all experiment phases: setup, execution, post-processing, and cleanup.

- **Post-Processing:**

  - Modular tools (e.g., session_creator) operate on the output session folder and metadata.

- **Interfaces:**

  - Stateless modules for process creation (Bonsai, MATLAB, Python).

- **Extensibility:**

  - New launchers, interfaces, or post-processing tools can be added with minimal changes to the core.

For more, see the code in `src/openscope_experimental_launcher/launchers/` and related modules.
