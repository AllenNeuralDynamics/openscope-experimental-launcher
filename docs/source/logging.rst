Logging in OpenScope Experimental Launcher
=========================================

Overview
--------

The OpenScope Experimental Launcher provides robust, session-based logging for all experiment runs. Logging is designed to capture experiment progress, errors, and metadata for both debugging and reproducibility.

Key Features
------------

- **Session-based logs:** Each experiment run creates a dedicated log file in the session output folder.
- **Continuous logging:** Logs are written throughout the experiment lifecycle, including setup, execution, pre-acquisition, post-acquisition, and cleanup.
- **Modular pipeline logging:** All pre- and post-acquisition modules log to the same session log, ensuring a complete record of the pipeline.
- **Centralized log directory (optional):** Logs can be mirrored to a centralized location for backup or monitoring.
- **Automatic log finalization:** All log handlers are flushed and closed at the end of each run.
- **Error and exception reporting:** All errors and exceptions are logged with stack traces for troubleshooting.

Log File Locations
------------------

- **Session log:**

  - Located in the `output_session_folder` for each experiment.
  - Filename: `experiment.log` (or similar, depending on launcher).

- **Centralized log (optional):**

  - If `centralized_log_directory` is specified in parameters, logs are also copied there.

Log Contents
------------

- **Experiment metadata:**

  - Start and stop times
  - Subject and user IDs
  - Script and repository information

- **Process events:**

  - Experiment start/stop
  - Process creation and termination
  - Resource usage (memory, CPU)

- **Pre- and Post-acquisition pipeline:**

  - Each module logs its actions, results, and any errors or warnings
  - The log provides a full trace of the pipeline steps

- **Custom notes:**

  - User-entered notes at the end of the experiment

How Logging Works
-----------------

1. **Setup:**

   - Logging is initialized at the start of each experiment run.
   - Log files are created in the session output folder.
2. **During Experiment:**

   - All major events, warnings, and errors are logged.
   - Log messages include timestamps and severity levels.
3. **Pre- and Post-Acquisition:**

   - All pipeline modules log their progress and any issues to the session log.
4. **Finalization:**

   - Log handlers are flushed and closed to ensure all messages are saved.

Customizing Logging
-------------------

- **Log level:**

  - Default is `INFO`. Can be changed in the code or by editing launcher scripts.
- **Centralized logging:**

  - Set `centralized_log_directory` in your parameter file to enable log mirroring.
- **Additional log messages:**

  - You can add custom log messages in your own launcher or pipeline modules using Python's `logging` module.

Best Practices for Module Authors
---------------------------------
- Use the standard Python `logging` module for all log messages.
- Log important actions, parameter values, and any errors or exceptions.
- Avoid printing directly to stdout/stderr; use logging for traceability.

Example: Accessing Log Files
----------------------------

After running an experiment, you can find the log file in the session output folder:

.. code-block:: bash

   cat /path/to/output_session_folder/experiment.log

Or, if centralized logging is enabled:

.. code-block:: bash

   cat /path/to/centralized_log_directory/experiment.log