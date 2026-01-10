Quick Start Guide
=================

Launch a basic OpenScope experiment, then layer in optional metadata validation and post-acquisition tooling.

Prerequisites
-------------

* Windows 10 or 11 with Python 3.8 or newer
* Rig configuration ``.toml`` describing hardware defaults
* Experiment parameter ``.json`` (start with ``params/example_minimalist_params.json``)

Install
-------

.. code-block:: bash

   pip install -e .

Configuration Layers
--------------------

1. **Rig Config (TOML)** – shared hardware + default values.
2. **Parameter File (JSON)** – experiment-specific overrides.
3. **Runtime Prompts** – final confirmation during launch.

Precedence order is runtime prompt > parameter file > rig config. Rig values can be referenced inside ``script_parameters`` using ``{rig_param:KEY}``.

Prepare Parameters
------------------

Adjust the minimal example or copy a template:

.. code-block:: json
   :caption: params/example_minimalist_params.json

   {
     "subject_id": "mouse_001",
     "user_id": "operator",
     "script_path": "C:/local/scripts/task.py",
     "output_root_folder": "D:/OpenScopeData"
   }

Launch a Session
----------------

.. code-block:: bash

   python run_launcher.py --param_file params/example_minimalist_params.json

Follow the prompts; a session folder is created with ``launcher_metadata/processed_parameters.json`` and ``launcher_metadata/end_state.json``.

Add Modules (Optional)
----------------------

Extend the workflow by listing modules in your parameter file:

* **Metadata service checks** – see ``params/example_metadata_pipeline.json`` for subject, procedures, and project validation prior to acquisition. Modules default to the in-rig host ``http://aind-metadata-service``; override via ``metadata_service_base_url`` when your deployment uses a different metadata host.
* **Experiment notes workflow** – ``params/experiment_notes_pipeline.json`` previews notes before the run and requires confirmation after the run.
* **Session archiver** – add ``session_archiver`` to ``post_acquisition_pipeline`` to copy data to backup storage with checksum and throughput logging. Provide ``session_dir`` (usually ``{output_session_folder}``), plus ``network_dir`` and ``backup_dir``.

You can exercise a module independently via:

.. code-block:: bash

   python run_module.py --module_type post_acquisition --module_name session_archiver --param_file params/example_metadata_pipeline.json

The param file you pass must include ``session_dir`` (or override it via ``--overrides session_dir=<path>``) in addition to the archive destinations.

Outputs
-------

Every run produces:

* ``launcher_metadata/processed_parameters.json`` – merged config and prompts
* ``launcher_metadata/end_state.json`` – flattened end-state summary
* ``launcher_metadata/debug_state.json`` when a crash occurs

Post-acquisition modules may add artifacts such as ``session.json`` or archived data manifests.

Next Steps
----------

* :doc:`parameter_files` – full parameter schema and module references
* :doc:`rig_config` – rig TOML structure and placeholder usage
* :doc:`modules` – metadata integrations, notes workflow, session archiver, and more
* :doc:`matlab_launcher` – configure the shared-engine MATLAB workflow