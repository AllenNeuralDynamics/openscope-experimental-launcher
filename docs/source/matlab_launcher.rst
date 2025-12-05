MATLAB Launcher
===============

The MATLAB launcher integrates with a shared MATLAB Engine session instead of
spawning ``matlab.exe`` directly. This allows the Python launcher to reconnect
if MATLAB restarts and gives the experimenter control through a small UI.

Prerequisites
-------------

* MATLAB R2020b or newer with the **MATLAB Engine for Python** installed into
  the same Python environment that runs ``run_launcher.py``. From a MATLAB
  command prompt:

  .. code-block:: matlab

     cd(fullfile(matlabroot, 'extern', 'engines', 'python'))
     system('python setup.py install')

* The launcher package on the MATLAB path so helper utilities (for example
  ``aind_launcher``) are available. A simple approach during development is:

  .. code-block:: matlab

     addpath('C:/BonsaiDataPredictiveProcessing/openscope-experimental-launcher/src/openscope_experimental_launcher/launchers')

Preparing MATLAB
----------------

Before starting the Python launcher, share the MATLAB engine and open the
OpenScope control UI:

.. code-block:: matlab

   aind_launcher('openscope_launcher')

The engine name is configurable through the ``matlab_engine_name`` parameter.
When the shared session is ready, the MATLAB UI shows ``Waiting for Python
launcher``.

Parameter Summary
-----------------

The MATLAB launcher parameters mirror the options used by
``MatlabLaunchRequest`` in ``interfaces/matlab_interface.py``:

``matlab_engine_name`` (string)
   Name of the shared engine. Defaults to ``"openscope_launcher"``.

``matlab_entrypoint`` / ``matlab_function`` (string)
   MATLAB function to call. ``matlab_function`` is accepted for legacy
   parameter files; ``matlab_entrypoint`` is preferred.

``matlab_entrypoint_args`` (list)
   Positional arguments forwarded to the MATLAB function. The launcher can
   automatically insert the session folder (see
   ``matlab_pass_session_folder``).

``matlab_entrypoint_kwargs`` (object)
   Key/value pairs appended to the argument list. Keys are passed exactly as
   provided.

``matlab_entrypoint_nargout`` (int)
   Number of outputs expected from the MATLAB function (default ``0``).

``matlab_pass_session_folder`` (bool)
   If ``true`` (default), the session folder is injected into the argument
   list. Use ``matlab_session_folder_position`` to control the insertion
   position or to disable the behaviour per run.

``matlab_session_folder_position`` (string or int)
   ``"prepend"`` (default), ``"append"``, ``"ignore"``, or an integer
   specifying the index at which to insert the session folder argument.

``matlab_enable_resume`` (bool)
   Enables automatic resume attempts when the engine connection drops.
   A ``matlab_resume_keyword`` argument and boolean flag are appended on
   subsequent attempts so MATLAB can differentiate resume from first launch.

``matlab_engine_connect_timeout_sec`` (float)
   How long to wait for the shared engine to appear (default ``120``).

``matlab_engine_connect_poll_interval_sec`` (float)
   Polling interval while waiting for the engine (default ``1`` second).

``matlab_cancel_timeout_sec`` (float)
   Maximum time to wait for MATLAB to acknowledge a cancellation request.

``matlab_keep_engine_alive`` (bool)
   Whether to leave the engine running after the launcher exits. Defaults to
   ``true`` so MATLAB stays available between runs.

Local Smoke Test
----------------

A ready-to-run parameter file is provided at
``params/matlab_local_test_params.json``. It exercises the shared engine flow
using ``sample_matlab_entrypoint.m`` which writes a heartbeat file inside the
session folder.

#. In MATLAB:

   .. code-block:: matlab

      addpath('C:/BonsaiDataPredictiveProcessing/openscope-experimental-launcher/src/openscope_experimental_launcher/launchers')
      aind_launcher('openscope_launcher')

#. In Python:

   .. code-block:: powershell

      python run_launcher.py --param_file params/matlab_local_test_params.json

The MATLAB UI exposes **Resume Acquisition** and **Signal Acquisition
Complete** buttons. Resume mode is triggered automatically when the Python
launcher reconnects to a shared engine after a failure and ensures operators
explicitly confirm that MATLAB should continue.

Troubleshooting
---------------

* **No module named ``matlab.engine``** – install the MATLAB Engine for Python
  into the active Python environment.
* **Engine connection times out** – verify the MATLAB session called
  ``aind_launcher('engine_name')`` and that the name matches
  ``matlab_engine_name`` in the parameter file.
* **Logs appear only after completion** – MATLAB buffers stdout while the UI
  ``uiwait`` is active. Use the heartbeat file or MATLAB ``diary`` to monitor
  progress during long acquisitions.
