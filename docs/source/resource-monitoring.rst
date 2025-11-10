Resource Monitoring
==================

This page describes the resource usage monitoring feature in the OpenScope Experimental Launcher.

Overview
--------
Resource monitoring allows you to track CPU and memory usage for both the launcher and the acquisition subprocess during an experiment. The data is logged to a file for later analysis and troubleshooting.

How It Works
------------
The launcher always logs resource usage statistics (CPU %, memory in MB) for both itself and (once started) the acquisition subprocess.
The log is written continuously to ``launcher_metadata/resource_usage.json`` inside the session output folder.
Logging occurs at a configurable interval (``resource_log_interval`` parameter; default 5 seconds if not provided).

Configuration
-------------
Optional parameter to adjust interval::

  {
    "resource_log_interval": 5
  }

If omitted, the default interval of 5 seconds is used. There is no on/off toggle.

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
* Monitoring continues for the launcher even after the acquisition subprocess exits.
* Data points are appended; previous samples are preserved for the entire session duration.

Troubleshooting
---------------
* 100% CPU usage means one full core; may be normal during computation.
* If the log file is missing, verify the session folder was created and the launcher was not terminated immediately after start.
