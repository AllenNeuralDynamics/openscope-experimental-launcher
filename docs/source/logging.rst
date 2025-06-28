Logging in OpenScope Experimental Launcher
=========================================

Overview
--------

The OpenScope Experimental Launcher provides robust, session-based logging for all experiment runs. Logging is designed to capture experiment progress, errors, and metadata for both debugging and reproducibility.

Key Features
------------

- **Session-based logs:** Each experiment run creates a dedicated log file in the session output folder.
- **Continuous logging:** Logs are written throughout the experiment lifecycle, including setup, execution, post-acquisition, and cleanup.
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

- **Post-acquisition:**

  - Post-acquisition steps and results
  - Errors and warnings

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
3. **Post-Acquisition:**

   - Post-acquisition modules log their progress and any issues.
4. **Finalization:**

   - Log handlers are flushed and closed to ensure all messages are saved.

Customizing Logging
-------------------

- **Log level:**

  - Default is `INFO`. Can be changed in the code or by editing launcher scripts.
- **Centralized logging:**

  - Set `centralized_log_directory` in your parameter file to enable log mirroring.
- **Additional log messages:**

  - You can add custom log messages in your own launcher or post-acquisition modules using Python's `logging` module.

Example: Accessing Log Files
----------------------------

After running an experiment, you can find the log file in the session output folder:

.. code-block:: bash

   cat /path/to/output_session_folder/experiment.log

Or, if centralized logging is enabled:

.. code-block:: bash

   cat /path/to/centralized_log_directory/experiment.log