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

Module Types
------------
Pipeline entries support two implementations, allowing teams to keep shared utilities inside the launcher package while
storing project-specific logic alongside the main experiment repository.

``launcher_module``
    *Location:* ``src/openscope_experimental_launcher/pre_acquisition`` or ``post_acquisition`` inside this repository.
    *Usage:* Reference by module name (without ``.py``). Ideal for reusable prompts, archivers, or shared infrastructure.
    *Deployment:* Ships with the launcher; updated via normal launcher releases. Best for functionality needed across rigs or
    projects.

``script_module``
    *Location:* Any Python file that lives in the cloned workflow repository referenced by ``repository_url`` /
    ``local_repository_path``. ``module_path`` is written relative to that repo root (see
    ``params/predictive_processing_params_example.json`` for a full example).
    *Usage:* Keeps bespoke preprocessing/post-processing code versioned alongside the acquisition script (for example, a
    stimulus table generator that belongs in the workflow repo). The launcher loads the file at runtime and calls the
    function requested in ``module_parameters``.
    *Deployment:* Update the workflow repository to change behavior; the launcher simply imports whatever commit was
    checked out.

Both types receive the same merged parameter dictionary, including ``output_session_folder`` and placeholder-expanded values.
Choose ``script_module`` when the code naturally belongs with the experiment repository so it evolves in lock step with the
workflow, and keep broadly useful utilities as ``launcher_module`` so they are available to every project.

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

Built-In Modules
----------------
The launcher ships with several reusable modules. These lists double as a quick feature catalog and an index into the
source tree under ``src/openscope_experimental_launcher``.

.. _pre-modules:

Pre-Acquisition Modules
~~~~~~~~~~~~~~~~~~~~~~~

- **experiment_notes_editor**: Creates an experiment-notes file inside the active session folder and can launch an editor
    (``notepad.exe`` by default) so operators can start typing immediately. Supply options via ``module_parameters`` inside the
    pipeline entry to keep settings scoped to this module. Key parameters:

    - ``experiment_notes_filename`` (default ``"experiment_notes.txt"``) — accepts placeholders such as ``{session_folder}``;
        relative paths are resolved beneath the session directory.
    - ``experiment_notes_launch_editor`` (default ``true``) — disable to skip opening an external editor.
    - ``experiment_notes_editor_command`` / ``experiment_notes_editor_args`` — override the executable and arguments.
    - ``experiment_notes_encoding`` (default ``"utf-8"``) — encoding used when the file is first created.

- **mouse_weight_pre_prompt**: Prompts the operator for the animal's weight before acquisition and appends the entry to
    ``mouse_weight.csv`` in the session directory.
- **metadata_subject_fetch**: Validates the active ``subject_id`` (or ``metadata_subject_id`` override) via
    ``GET /api/v2/subject/{subject_id}``. Writes the response to ``subject.json`` inside the session directory. Returns a warning
    (but continues) when the service responds with HTTP 400 so teams can review validation errors while proceeding with the run.
- **metadata_procedures_fetch**: Requests ``GET /api/v2/procedures/{subject_id}`` and stores the resulting JSON as
    ``procedures.json``. Waits up to 45 seconds by default (override with ``metadata_procedures_timeout``) before treating the call
    as failed. Empty responses are considered errors.
- **metadata_project_validator**: Fetches the available project list from ``GET /api/v2/project_names``. If the configured project
    name is missing, the module logs the options and interactively prompts the operator to choose one (up to five attempts) before
    persisting the selection to ``project.json``. HTTP 400 responses are recorded as warnings so payload details can be reviewed later.
- **example_pre_acquisition_module**: Minimal template illustrating logging, parameter loading, and return codes.

.. note::
    Metadata modules fall back to the in-network service URL ``http://aind-metadata-service``. Override by setting
    ``metadata_service_base_url`` / ``metadata_api_base_url`` in your parameter file when you need a different host. The
    optional ``metadata_service_timeout`` parameter still adjusts request timeouts.

.. _post-modules:

Post-Acquisition Modules
~~~~~~~~~~~~~~~~~~~~~~~~

- **experiment_notes_finalize**: Completes the notes workflow by ensuring the notes file exists (creating it if needed) and
        prompting the operator to confirm everything is saved. Provide overrides through ``module_parameters`` so they stay coupled
        with this post step. Key parameters:

    - ``experiment_notes_filename`` (default ``"experiment_notes.txt"``) — same placeholder behavior as the editor module.
    - ``experiment_notes_confirm_prompt`` — custom confirmation message for interactive runs.
        - ``experiment_notes_preview`` (default ``true``) — controls whether the module reads the notes file and displays the contents
            in the log before prompting for confirmation.
        - ``experiment_notes_preview_limit`` — optional integer cap on the number of characters shown during preview; omit or set to a
            non-positive value to display the full file.

- **session_archiver**: Transfers session artifacts to a network path, maintains a local backup, and records results in a
    manifest for resumable copies. Logs aggregate transfer throughput (MB/s) to help benchmark archive performance.
    Requires ``session_dir`` (point it at ``{output_session_folder}``), plus ``network_dir`` and ``backup_dir``. Other
    knobs include ``include_patterns``, ``exclude_patterns``, ``skip_completed``, ``checksum_algo``, and ``max_retries``;
    all support placeholder expansion.
- **session_creator**: Builds standards-compliant ``session.json`` metadata, typically using AIND schema helpers.
- **stimulus_table_predictive_processing**: Normalizes Predictive Processing stimulus tables for downstream analysis.
- **session_enhancer_bonsai**, **session_enhancer_predictive_processing**, **session_enhancer_slap2**: Enrich session metadata
    with workflow-specific fields after acquisition.
- **mouse_weight_post_prompt**: Mirrors the pre prompt to capture the animal's weight after the run.
- **experiment_notes_post_prompt**: Legacy notes prompt retained for compatibility; the ``experiment_notes_editor`` /
    ``experiment_notes_finalize`` pair is now the recommended workflow.
- **example_post_acquisition_module**: Template for building new post-acquisition steps.

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

1. Create a temporary param file with `output_session_folder` set (or `session_dir` when the module requires it, e.g., `session_archiver`).
2. Call the module function directly.
3. Assert expected files exist and contents are valid.

Troubleshooting
---------------
* Missing session folder -> ensure launcher ran initialization or the required key (`output_session_folder` or `session_dir`) is provided.
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

.. _pipeline-entry-schema:

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

Field semantics and placeholder expansion rules are summarized in :doc:`parameter_files`; refer there for a comprehensive
reference and additional examples.

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
