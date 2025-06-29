Resource Monitoring
==================

This page describes the resource usage monitoring feature in the OpenScope Experimental Launcher.

Overview
--------
Resource monitoring allows you to track CPU and memory usage for both the launcher and the acquisition subprocess during an experiment. The data is logged to a file for later analysis and troubleshooting.

How It Works
------------
- When enabled, the launcher logs resource usage statistics (CPU %, memory in MB) for both itself and the acquisition subprocess.
- The log is written to ``launcher_metadata/resource_usage.json`` inside the session output folder.
- Logging occurs at a configurable interval (see below).

Enabling Resource Monitoring
---------------------------
Resource monitoring is **off by default**. To enable it, add the following to your parameter file::

  {
    "resource_log_enabled": true,
    "resource_log_interval": 5
  }

- ``resource_log_enabled``: Set to ``true`` to enable resource monitoring.
- ``resource_log_interval``: (Optional) Interval in seconds between log entries (default: 5 seconds if not specified).

Disabling Resource Monitoring
----------------------------
To disable resource monitoring, either omit the ``resource_log_enabled`` key or set it to ``false``::

  {
    "resource_log_enabled": false
  }

Log File Location
-----------------
The resource usage log is saved as::

  <session_output_folder>/launcher_metadata/resource_usage.json

Log File Format
---------------
The log file is a JSON array. Each entry contains:

- ``timestamp``: ISO format timestamp
- ``launcher``: CPU and memory usage for the launcher process
- ``acquisition``: CPU and memory usage for the acquisition subprocess (if running)

Example entry::

  {
    "timestamp": "2025-06-28T12:34:56.789",
    "launcher": {"cpu_percent": 2.5, "memory_mb": 120.3},
    "acquisition": {"cpu_percent": 15.2, "memory_mb": 300.1}
  }

Notes
-----
- Resource monitoring is robust to subprocess exit and will continue logging launcher usage if the acquisition process ends.
- The log file is overwritten at each interval, so only the latest run's data is preserved.

Troubleshooting
---------------
- If you see 100% CPU usage, it means the process is using one full CPU core. This may be normal during heavy computation.
- If the log file is missing, ensure ``resource_log_enabled`` is set to ``true`` in your parameters.
