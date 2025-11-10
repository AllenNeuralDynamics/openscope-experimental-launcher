Flattened End & Debug State System
==================================

The launcher writes a small set of JSON metadata files into each session folder using a flattened structure to simplify downstream tooling.

Files Generated
---------------

* ``processed_parameters.json`` – final merged parameters (rig config + JSON + runtime prompts).
* ``end_state.json`` – final experiment outcome and core identifiers.
* ``debug_state.json`` – only created when an unexpected exception/crash occurs.
* ``session.json`` – created by post-acquisition tools (e.g. ``session_creator``) from the above.

End State Schema (Flattened)
----------------------------

Example:

.. code-block:: json

     {
         "session_uuid": "4fe1c6a0-2f5d-4f7e-9c44-5c2e9f6a9e1a",
         "subject_id": "mouse_001",
         "user_id": "researcher",
         "start_time": "2025-06-21T10:30:00.123456",
         "stop_time": "2025-06-21T10:45:30.654321",
         "process_returncode": 0,
         "rig_config": {"rig_id": "behavior_rig", "COM_port": "COM5"},
         "experiment_data": {"experiment_notes": "Good behavioral engagement"},
         "custom_data": {"custom_field": "value"},
         "version": "<launcher_version>"
     }

Custom Data Injection
---------------------

Subclasses can expose extra fields by implementing ``get_custom_end_state()`` which returns a dict merged into ``custom_data``.

Debug State Schema
------------------

The debug file captures a crash snapshot with a dedicated ``crash_info`` block and a shallow serialization of the launcher state.

.. code-block:: json

     {
         "session_uuid": "4fe1c6a0-2f5d-4f7e-9c44-5c2e9f6a9e1a",
         "timestamp": "2025-06-21T10:40:05.001234",
         "exception": "ValueError('Invalid parameter value')",
         "traceback": "<stack trace>",
         "crash_info": {
             "exception_type": "ValueError",
             "message": "Invalid parameter value",
             "crash_time": "2025-06-21T10:40:05.001234"
         },
         "launcher_state": {
             "subject_id": "mouse_001",
             "user_id": "researcher",
             "session_uuid": "4fe1c6a0-2f5d-4f7e-9c44-5c2e9f6a9e1a"
             // ... additional shallow, JSON-safe fields ...
         }
     }

Crash handling automatically writes this file before termination.

Session Creation (Post-Acquisition)
-----------------------------------

The ``session_creator`` module reads ``end_state.json`` + ``processed_parameters.json`` to build a standards-compliant ``session.json``. If missing timestamps, it falls back gracefully and logs warnings.

Why Flatten?
------------

* Easier ingestion by lightweight tools
* Reduced nesting ambiguity
* Clear boundary for launcher vs. custom extension data

Extensibility Guidelines
------------------------

1. Add new optional keys ONLY under ``custom_data``.
2. Avoid altering existing top-level keys to keep downstream consumers stable.
3. Prefer ISO8601 timestamps (``datetime.isoformat()``) for all temporal fields.

Example Custom Launcher
-----------------------

.. code-block:: python

     class RewardTrackingLauncher(BaseLauncher):
             def __init__(self):
                     super().__init__()
                     self.total_reward_ul = 0.0

             def get_custom_end_state(self):
                     return {"total_reward_ul": self.total_reward_ul}

Use these additions for specialized downstream analytics without modifying the base schema.

Best Practices Summary
----------------------

* Treat ``end_state.json`` as append-only schema (extend via ``custom_data``)
* Never mutate or delete previous experiment metadata files mid-run
* Keep debug states for crash forensics; do not rely on them for normal analytics
