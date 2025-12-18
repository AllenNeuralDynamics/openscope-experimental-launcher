Pre-Acquisition Pipelines
=========================

The exhaustive catalog of pre-acquisition modules lives in the :ref:`pre-modules` section of
:doc:`modules`. This page keeps a slim reminder of how the pipeline is wired and then focuses on the
launcher-level session synchronization system that often accompanies pre-acquisition work.

Pipeline Basics
---------------

- Populate ``pre_acquisition_pipeline`` with module names under
  ``src/openscope_experimental_launcher/pre_acquisition`` (see :doc:`modules` for details).
- Each module exposes ``run_pre_acquisition`` (or ``run``) and should return ``0`` on success.
- Pipelines run _before_ the acquisition subprocess starts, so they can safely prepare prompts,
  metadata, or folders that downstream steps need.

Session Synchronization
-----------------------

``BaseLauncher`` can coordinate session folder names across multiple launchers (for example, a
behavior rig and an imaging rig) before any output directories or logs are created. Configure these
top-level parameters to enable the handshake:

- ``session_sync_role``: ``"master"`` or ``"slave"`` (anything else disables syncing).
- ``session_sync_port`` (both roles): TCP port for the coordination socket.
- ``session_sync_expected_slaves`` (master): number of slave launchers that must acknowledge before
  the master proceeds.
- ``session_sync_bind_host`` (master): interface to bind the listening socket to (``127.0.0.1`` for
  single-machine testing, ``0.0.0.0`` to accept remote hosts).
- ``session_sync_master_host`` (slave): hostname or IP address of the master.
- ``session_sync_node_name`` (both roles, optional): human-readable label used in logs.
- ``session_sync_key_param`` (optional): parameter that carries the shared key (defaults to
  ``subject_id``). ``session_sync_session_key`` can override the value directly.
- ``session_sync_session_name`` (optional, master): explicit session folder name. If omitted, the
  master falls back to ``session_sync_name_param`` (defaults to ``session_uuid``) or the generated
  timestamp-based name.

Example snippet from a parameter file:

.. code-block:: json

   {
     "subject_id": "mouse123",
     "user_id": "tester",
     "session_sync_role": "master",
     "session_sync_port": 47001,
     "session_sync_expected_slaves": 2
   }

Slave launchers set ``session_sync_role`` to ``"slave"`` and supply ``session_sync_master_host`` in
addition to the shared port. Built-in synchronization blocks the ``run()`` workflow until every
participant acknowledges the shared session name, keeping all launchers aligned on the folder name
before any data is written.

Example parameter files demonstrating a one-master/one-slave setup live in
``params/session_sync_master_example.json`` and ``params/session_sync_slave_example.json``.

Workflow checklist
~~~~~~~~~~~~~~~~~~

1. Choose a TCP port that is free on the master machine and set ``session_sync_port`` to that value
  in every launcher. (Non-privileged ports above 50000 are typically safest.)
2. Configure the master with ``session_sync_role = "master"`` and
  ``session_sync_expected_slaves`` set to the number of participating slave launchers. Launch this
  file first; ``BaseLauncher`` will log that it is listening and will block inside
  ``_maybe_synchronize_session_name`` until the expected slaves connect.
3. Configure each slave with ``session_sync_role = "slave"`` and point
  ``session_sync_master_host`` at the master's hostname or IP. Launch them _after_ the master is
  listening. Each slave attempts to connect until the master responds, participates in the JSON
  handshake, and adopts the shared session name before continuing.
4. Once all slaves acknowledge the announced session, the master unleashes the rest of the launch
  workflow (repository setup, folder creation, logging, etc.) and the slave instances resume their
  own pipelines with the synchronized ``session_uuid``/folder.

All participants must agree on ``session_sync_port`` and ``session_sync_key_param`` inputs. If a
slave never connects or sends the wrong key, the master will remain blocked until the timeout
values (below) expire.

Timeouts and retries
~~~~~~~~~~~~~~~~~~~~

The following optional parameters fine-tune how long the launchers wait for each other:

- ``session_sync_timeout_sec``: maximum time the master waits for all slaves or a slave waits for a
  connection (default 120 seconds).
- ``session_sync_ack_timeout_sec``: deadline for each JSON exchange once connected (default 30
  seconds).
- ``session_sync_retry_delay_sec`` (slaves only): delay between reconnection attempts (default 1
  second).

Set these values higher if you expect long boot times or cross-site latency. Lower them if you want
faster failure when a launcher is missing.

Local testing
~~~~~~~~~~~~~

To test on a single workstation, bind the master to ``127.0.0.1`` and point each slave's
``session_sync_master_host`` to ``127.0.0.1`` as shown in the example parameter files. Start the
master first, then run the slave(s) from separate terminals. Since sockets open on localhost, no
additional firewall configuration is required beyond allowing Python to listen on that port.
