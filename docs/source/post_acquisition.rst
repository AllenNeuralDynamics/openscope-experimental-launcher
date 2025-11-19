.. _post_acquisition:

Post-Acquisition Tools
======================

The OpenScope Experimental Launcher includes a modular post-acquisition system designed to handle data transformation and session creation after experiment completion.

Philosophy
----------

- All post-acquisition logic is handled by standalone modules, not the launcher core.
- Modules are inserted via the ``post_acquisition_pipeline`` list in your parameter file.
- Each module is focused, testable, and reusable.

How It Works
------------

- Add a ``post_acquisition_pipeline`` list to your parameter JSON file. Each entry is the name of a Python module in ``src/openscope_experimental_launcher/post_acquisition/``.
- Each module must define a function ``main(param_file)`` and return 0 for success, 1 for failure.
- The launcher will import and run each module in order after the experiment completes. If any step fails (returns 1 or raises), the pipeline stops and logs the error.

Available Post-Acquisition Modules
----------------------------------

- **session_archiver**: Copies session artifacts to a network location with checksum verification, duplicates originals into a backup folder, and records transfer status in a manifest for safe retries.
- **experiment_notes_finalize**: Prompts the operator to confirm the notes are saved, ensures the file exists inside the session directory, and records a completion message in the logs.
- **session_creator**: Creates standardized ``session.json`` files from experiment data using the AIND data schema.
- **stimulus_table_predictive_processing**: Converts Predictive Processing stimulus tables to a standardized format for downstream analysis.
- **session_enhancer_bonsai**: Adds Bonsai-specific metadata and enrichment to session files.
- **session_enhancer_predictive_processing**: Adds Predictive Processing-specific metadata and enrichment to session files.
- **session_enhancer_slap2**: Adds SLAP2-specific metadata and enrichment to session files.
- **mouse_weight_post_prompt**: Prompts for and records the mouse's weight after the experiment.
- **experiment_notes_post_prompt**: Prompts for and records experiment notes after the experiment.
- **example_post_acquisition_module**: Template for creating new post-acquisition modules.

Session Archiver
----------------

The ``session_archiver`` module automates reliable transfer of session output to centralized storage while preserving a local safety copy. When the module starts it:

- Prompts the operator to confirm the network destination path and the backup directory. Defaults come from the parameter file and accept ``y/1/true`` to proceed.
- Asks whether to copy data to the network share and whether to move originals into the backup directory. Both default to **Yes** so operators can quickly acknowledge the transfer.
- Copies each matching file (``include_patterns`` / ``exclude_patterns``) to the network path using a temporary file, verifies checksums, then copies the original file to the backup folder while leaving the source in place.
- Records the status for every file in ``session_archiver_manifest.json`` (stored in the backup directory by default) so interrupted runs can resume without re-copying successful entries.

Required parameters:

.. code-block:: json

    {
        "post_acquisition_pipeline": [
            "session_archiver"
        ],
        "session_dir": "C:/data/sessions/{session_uuid}",
        "network_dir": "//server/openscope/archive/{session_uuid}",
        "backup_dir": "D:/archive_backups/{session_uuid}"
    }

Optional parameters include ``include_patterns``, ``exclude_patterns``, ``dry_run``, ``skip_completed``, ``max_retries``, ``checksum_algo``, and ``remove_empty_dirs``. All parameters support launcher placeholder expansion (for example ``{session_uuid}``).

Non-interactive environments can pass a custom ``prompt_func`` override via the launcher so the module uses pre-approved values. This is useful for automated test runs where operator confirmation is not possible.

Experiment Notes Finalize
-------------------------

Use this alongside ``experiment_notes_editor`` to close the notebook loop after acquisition.

- Resolves the notes path using the same placeholder expansion as the launcher (default file name ``experiment_notes.txt``).
- Creates the notes file on the spot if it has been deleted so the archive remains complete.
- Displays a confirmation prompt (customizable via ``experiment_notes_confirm_prompt``) to remind the operator to save and close the editor before proceeding.

Parameters include:

.. code-block:: json

    {
        "experiment_notes_filename": "notes/experiment_notes.txt",
        "experiment_notes_confirm_prompt": "Confirm experiment notes are saved; press Enter to finish."
    }

The module returns success even in non-interactive environments by using defaults supplied through ``param_utils.get_user_input``.

Example Parameter File
----------------------

.. code-block:: json

    {
        "launcher": "base",
        "post_acquisition_pipeline": [
            "session_archiver",
            "session_creator",
            "mouse_weight_post_prompt",
            "experiment_notes_post_prompt"
        ],
        ...
    }

Best Practices
--------------

- Keep each module focused on a single task.
- Log all actions for traceability.
- Use exceptions or return 1 to signal failure and stop the pipeline.

See also: ``src/openscope_experimental_launcher/post_acquisition/`` for example modules.
