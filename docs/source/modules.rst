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
