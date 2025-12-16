MATLAB Launcher
===============

The MATLAB launcher integrates with a shared MATLAB Engine session instead of
spawning ``matlab.exe`` directly. This allows the Python launcher to reconnect
if MATLAB restarts and gives the experimenter control through a small UI.

Prerequisites
-------------

* MATLAB R2020b or newer with the ``matlabengine`` Python package installed in
  the environment that runs ``run_launcher.py``. Install via ``pip``:

   .. code-block:: bash

     pip install openscope-experimental-launcher[matlab]

  or, if you only need the engine package:

  .. code-block:: bash

     pip install matlabengine

* The launcher package on the MATLAB path so helper utilities (for example
   ``slap2_launcher``) are available. A simple approach during development is:

  .. code-block:: matlab

     addpath('C:/BonsaiDataPredictiveProcessing/openscope-experimental-launcher/src/openscope_experimental_launcher/launchers')

Preparing MATLAB
----------------

Before starting the Python launcher, share the MATLAB engine and open the
SLAP2 control UI:

.. code-block:: matlab

   slap2_launcher('slap2_launcher')

The engine name is configurable through the ``matlab_engine_name`` parameter.
When the shared session is ready, the MATLAB UI shows ``Waiting for Python
launcher``.

Parameter Summary
-----------------

Most workflows only need a handful of parameters:

``matlab_engine_name`` (string)
   Name of the shared engine. Defaults to ``"slap2_launcher"``.

``matlab_entrypoint`` / ``matlab_function`` (string)
   MATLAB function to call. ``matlab_function`` is accepted for legacy
   parameter files; ``matlab_entrypoint`` is preferred. Defaults to
   ``"slap2_launcher"`` when omitted.

``matlab_entrypoint_args`` (list)
   Positional arguments forwarded to the MATLAB function. When the entry point
   is ``slap2_launcher``, the Python launcher automatically prepends
   ``"execute"`` (which tells MATLAB to start the acquisition flow) and then
   injects the session folder, so most SLAP2 workflows can omit this field.
   The ``"execute"`` branch inside ``slap2_launcher`` always runs the bundled
   ``slap2`` acquisition function; there is no configuration knob for swapping
   to a different MATLAB function.

``script_parameters`` (object)
   Arbitrary name/value pairs appended after ``matlab_entrypoint_args``. Use
   this block to pass rig paths or other configuration (for example,
   ``{"rig_description_path": "{rig_param:rig_description_path}"}``).

``matlab_entrypoint_kwargs`` (object)
   Additional name/value pairs appended after ``script_parameters``. These are
   rarely needed now that ``script_parameters`` handles rig-specific values.

``matlab_entrypoint_nargout`` (int)
   Number of outputs expected from the MATLAB function (default ``0``).

``matlab_engine_connect_timeout_sec`` (float)
   How long to wait for the shared engine to appear (default ``120``).

``matlab_engine_connect_poll_interval_sec`` (float)
   Polling interval while waiting for the engine (default ``1`` second).

``matlab_cancel_timeout_sec`` (float)
   Maximum time to wait for MATLAB to acknowledge a cancellation request.

``matlab_keep_engine_alive`` (bool)
   Whether to leave the engine running after the launcher exits. Defaults to
   ``true`` so MATLAB stays available between runs.

.. note::
   Session folder injection and resume signalling are automatic. Legacy keys
   such as ``matlab_pass_session_folder``, ``matlab_session_folder_position``,
   ``matlab_enable_resume``, and ``matlab_resume_keyword`` are still accepted
   for backward compatibility but should be omitted from new parameter files.
   If MATLAB crashes or the SLAP2 UI is closed, the Python launcher now stays
   alive, logs the failure, and keeps trying to reconnect so you can relaunch
   MATLAB and re-share the engine without restarting Python.

Local Smoke Test
----------------

A ready-to-run parameter file is provided at
``params/matlab_local_test_params.json``. It exercises the shared engine flow
using ``sample_matlab_entrypoint.m`` which writes a heartbeat file inside the
session folder. The same file demonstrates ``script_parameters`` to forward
``rig_description_path`` so SLAP2 immediately knows which rig to load.

#. In MATLAB:

   .. code-block:: matlab

      addpath('C:/BonsaiDataPredictiveProcessing/openscope-experimental-launcher/src/openscope_experimental_launcher/launchers')
      slap2_launcher('slap2_launcher')

#. In Python:

   .. code-block:: powershell

      python run_launcher.py --param_file params/matlab_local_test_params.json

The MATLAB UI exposes **Resume Acquisition** and **Signal Acquisition
Complete** buttons. Resume mode is triggered automatically when the Python
launcher reconnects to a shared engine after a failure and ensures operators
explicitly confirm that MATLAB should continue.

Troubleshooting
---------------

* **No module named ``matlab.engine``** – ensure ``pip install matlabengine``
   was run inside the same Python environment used for the launcher.
* **Engine connection times out** – verify the MATLAB session called
   ``slap2_launcher('engine_name')`` and that the name matches
  ``matlab_engine_name`` in the parameter file.
* **Logs appear only after completion** – MATLAB buffers stdout while the UI
  ``uiwait`` is active. Use the heartbeat file or MATLAB ``diary`` to monitor
  progress during long acquisitions.
