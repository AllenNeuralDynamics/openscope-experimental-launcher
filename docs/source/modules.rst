Pre- and Post-Acquisition Modules
=================================

This page provides a detailed reference for pipeline modules executed before and after the acquisition subprocess.

Concept
-------
Modules are lightweight Python scripts that implement a single function performing setup (pre) or teardown / enrichment (post) tasks. They run inside the launcher process, receive the path to the resolved parameter JSON file, and can read or write files directly into the session folder.

Lifecycle
---------
1. Parameters merged -> `processed_parameters.json` written.
2. Pre-acquisition pipeline executes each module in order (`run_pre_acquisition`).
3. Acquisition subprocess runs (external tool or script).
4. Post-acquisition pipeline executes each module in order (`run_post_acquisition`).
5. End / debug state metadata written; optional session file generation occurs.

Module Contract
---------------
A module is a Python file located in `src/openscope_experimental_launcher/pre_acquisition/` or `post_acquisition/` defining exactly one entry function:

* Pre module: `run_pre_acquisition(param_file: str) -> int`
* Post module: `run_post_acquisition(param_file: str) -> int`

Return Codes:
* 0 = success (launcher continues)
* 1 = failure (launcher logs error; may continue unless critical logic enforced externally)

Input:
`param_file` is the path to the same JSON parameter file used to start the launcher. It reflects merged parameters (rig config placeholders expanded and runtime prompts applied) under `processed_parameters.json`.

Recommended Pattern:

.. code-block:: python

   import logging
   import os
   from openscope_experimental_launcher.utils import param_utils

   def run_pre_acquisition(param_file):
       params = param_utils.load_parameters(param_file=param_file)
       session_folder = params.get('output_session_folder')
       if not session_folder:
           logging.error('Missing output_session_folder')
           return 1
       # Perform setup, write artifacts
       return 0

Session Folder Injection
------------------------
The launcher injects `output_session_folder` into the merged parameters before any module runs. Modules should prefer this key over constructing paths manually. If `output_session_folder` is absent, treat it as an error.

Writing Files:
Use `os.path.join(session_folder, '<filename>')` to create new artifacts (e.g., `mouse_weight.csv`, `ready.flag`). Avoid changing existing launcher metadata files; write separate module-specific outputs.

Accessing Other Parameters:
All original parameter keys plus rig placeholders are available in the loaded dict after expansion. Example: camera settings, protocol identifiers, repository commit hash.

Launching Repository Python Scripts
-----------------------------------
A module may invoke Python scripts stored in a cloned repository (if `repository_url` was specified) by constructing a subprocess call:

.. code-block:: python

   import subprocess
   import sys
   def run_post_acquisition(param_file):
       params = param_utils.load_parameters(param_file=param_file)
       repo_path = params.get('local_repository_path')
       session_folder = params.get('output_session_folder')
       script_rel = params.get('analysis_script', 'scripts/analyze_session.py')
       script_path = os.path.join(repo_path, script_rel)
       cmd = [sys.executable, script_path, '--session', session_folder]
       proc = subprocess.run(cmd, capture_output=True, text=True)
       if proc.returncode != 0:
           logging.error(f'Analysis script failed: {proc.stderr}')
           return 1
       return 0

Add `analysis_script` to your parameter file to configure which script to run.

Best Practices
--------------
* Keep modules idempotent (safe to re-run).
* Fail fast and return 1; include clear log messages.
* Never mutate `processed_parameters.json`; derive additional files instead.
* Use timestamped outputs where appropriate.
* Avoid long blocking operations; offload heavy analysis to asynchronous processes if needed.

Common Examples
---------------
* Mouse weight prompts (pre/post) writing `mouse_weight.csv`.
* Notes collection module writing `experiment_notes.txt`.
* Session creation module generating `session.json`.
* Post-run analysis launching repository scripts.

Extending the Pipeline
----------------------
Add your module filename (without `.py`) to the appropriate list:

.. code-block:: json

     {
         "pre_acquisition_pipeline": ["mouse_weight_pre_prompt"],
         "post_acquisition_pipeline": ["session_creator", "analysis_post_step"]
     }

Testing Modules
---------------
Design modules with pure side effects (file creation) and simple returns; write unit tests that:

1. Create a temporary param file with `output_session_folder` set.
2. Call the module function directly.
3. Assert expected files exist and contents are valid.

Troubleshooting
---------------
* Missing session folder -> ensure launcher ran initialization or `output_session_folder` provided.
* Subprocess invocation failures -> inspect `proc.stderr` and verify script path.
* Parameter key missing -> verify placeholder expanded in `processed_parameters.json`.

Reference Utilities
-------------------
* `param_utils.load_parameters` – load merged parameters.
* `param_utils.get_user_input` – safe interactive prompt (returns cast value or raises).

Cross-Cutting Concerns
----------------------
* Logging: use `logging.info` / `logging.error`; launcher handles formatting & centralization.
* Resource Use: heavy CPU tasks can distort acquisition timing; prefer post-acquisition pipeline for analysis.
* Ordering: modules execute strictly in array order; maintain dependencies via sequence.

Future Extensions
-----------------
Potential enhancements (not implemented yet):
* Module retry semantics
* Parallel post-acquisition execution
* Declarative dependency graph

This document reflects the current implementation of the pipeline module system.

Detailed JSON Configuration Reference
------------------------------------
The parameter JSON file drives how modules are executed. Below is a breakdown using the example file `params/predictive_processing_params_example.json`.

Top-Level Keys (subset shown):

* ``launcher`` – interface type (e.g., ``bonsai``). Chooses the concrete launcher subclass.
* ``repository_url`` / ``repository_commit_hash`` / ``local_repository_path`` – optional repository cloning + commit checkout.
* ``script_path`` – acquisition script path (Bonsai workflow, Python script, etc.).
* ``output_root_folder`` – where the launcher creates a timestamped session folder (e.g., ``C:/BonsaiDataPredictiveProcessing``).
* ``script_parameters`` – key/value map passed to the acquisition interface. Supports placeholders described below.
* ``pre_acquisition_pipeline`` / ``post_acquisition_pipeline`` – ordered arrays describing module execution.

Placeholders Supported in ``script_parameters`` and Module Args:

* ``{rig_param:<key>}`` – replaced with the merged parameter value (includes rig config). Example: ``"PortName": "{rig_param:COM_port}"``.
* ``{subject_id}`` – replaced with subject ID after initialization.
* ``{session_folder}`` – replaced with the resolved session output directory (in function_args or script_parameters values).

Pipeline Entry Schema
~~~~~~~~~~~~~~~~~~~~~
Each element of ``pre_acquisition_pipeline`` or ``post_acquisition_pipeline`` can be either a simple string or a structured object.

1. String form (launcher module shortcut):

.. code-block:: json

     "pre_acquisition_pipeline": ["mouse_weight_pre_prompt"]

     Interpreted as:

.. code-block:: json

     {
         "module_type": "launcher_module",
         "module_path": "mouse_weight_pre_prompt",
         "module_parameters": {}
     }

2. Object form (explicit):

.. code-block:: json

     {
         "module_type": "script_module",
         "module_path": "code/stimulus-control/src/Mindscope/generate_experiment_csv.py",
         "module_parameters": {
             "function": "generate_single_session_csv",
             "function_args": {
                 "session_type": "short_test",
                 "seed": 42,
                 "output_path": "{session_folder}\\predictive_processing_session.csv"
             }
         }
     }

Field Semantics:

* ``module_type`` – ``launcher_module`` (Python file inside launcher package) or ``script_module`` (arbitrary Python file inside cloned repository tree).
* ``module_path`` – For ``launcher_module``: name without ``.py`` located in ``pre_acquisition/`` or ``post_acquisition/``. For ``script_module``: repository-relative path to the Python script.
* ``module_parameters`` – Arbitrary dict merged with processed parameters. Special keys:
    * ``function`` – Name of the function inside the script to call (falls back to ``run_pre_acquisition``/``run_post_acquisition`` or ``run`` if omitted).
    * ``function_args`` – Dict of keyword arguments passed directly to the target function. Only names matching the function signature are provided. If an ``output_filename`` key is given (legacy pattern) the launcher may derive ``output_path``.

Invocation Rules (Summary):

* When ``function_args`` present: only those keys (after placeholder expansion and path resolution) are passed as kwargs.
* ``{session_folder}`` inside any arg is expanded before the call.
* Relative paths ending with ``_path`` or ``_file`` inside ``function_args`` are resolved against the session folder.
* Return value success criteria: ``None``, ``0`` or ``True`` are treated as success; anything else logs failure.

Example Complete Snippet:

.. code-block:: json

     {
         "launcher": "bonsai",
         "script_parameters": {
             "stimulus_table_path": "{session_folder}\\predictive_processing_session.csv",
             "PortName": "{rig_param:COM_port}",
             "RecordCameras": "{rig_param:RecordCameras}",
             "Subject": "{subject_id}"
         },
         "pre_acquisition_pipeline": [
             {
                 "module_type": "script_module",
                 "module_path": "code/stimulus-control/src/Mindscope/generate_experiment_csv.py",
                 "module_parameters": {
                     "function": "generate_single_session_csv",
                     "function_args": {
                         "session_type": "short_test",
                         "seed": 42,
                         "output_path": "{session_folder}\\predictive_processing_session.csv"
                     }
                 }
             }
         ],
         "post_acquisition_pipeline": []
     }

Validation & Failure Behavior
-----------------------------
* Unknown ``{rig_param:<key>}`` placeholders raise a ``RuntimeError`` before execution.
* Missing ``output_session_folder`` during expansion leads to unexpanded ``{session_folder}``. Ensure you run through the launcher lifecycle.
* Any module failure is logged; pipeline continues unless critical semantics are enforced externally.

Design Tips
-----------
* Favor explicit object entries when you need function selection or arguments.
* Use ``function_args`` for stable, testable contracts; avoid relying on implicit positional parameter passing.
* Keep paths relative and let the launcher resolve them against the session folder.
* Prefer placeholder substitution over hard-coded subject identifiers.

See also the example file under ``params/`` for a live reference.
