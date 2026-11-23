==================================================
Migrating clients to the new DishManager interface
==================================================

DishManager now uses the ska-tango-base *future* device interfaces
(``ControllerInterface``, ``ControlModeMixin``, ``ComponentManagerMixin`` and ``LRCMixin``).
This page lists what clients of DishManager (TMC, the MeerKAT dish proxy, engineering
scripts and operator tools) need to check or change.

1. Enable control with ``controlMode``
======================================

Monitoring and control are now switched on and off with the ``controlMode`` attribute,
not with ``adminMode``.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``controlMode``
     - Behaviour
   * - ``NO_MONITOR_NO_CONTROL`` (0)
     - DishManager does not connect to its sub-devices. ``healthState`` is ``UNKNOWN`` and
       all commands are rejected except ``Abort``, ``AbortScan`` and ``GetComponentStates``.
   * - ``MONITOR_NO_CONTROL`` (1)
     - DishManager monitors its sub-devices and reports their state. Commands that control
       the dish are rejected. ``SyncComponentStates``, ``GetComponentStates``, ``Abort``
       and ``AbortScan`` are still accepted.
   * - ``MONITOR_AND_CONTROL`` (2)
     - Full monitoring and control.

``controlMode`` starts as ``NO_MONITOR_NO_CONTROL`` on a new deployment. It is memorized,
so once it has been written the value survives a device restart.

.. code-block:: python

   from ska_control_model.future import ControlMode

   dish_manager.controlMode = ControlMode.MONITOR_AND_CONTROL

``adminMode`` is still there, but only records whether the device is used for science or
engineering. Writing ``OFFLINE`` or ``ONLINE`` no longer stops or starts monitoring.

A command rejected because of ``controlMode`` raises ``DevFailed`` with
``Control is disabled: controlMode is ...`` (or ``Monitoring is disabled`` for
``SyncComponentStates``), and is recorded on ``lastCommandFailure``.

Attribute writes follow the same rule: writing any DishManager attribute needs
``MONITOR_AND_CONTROL``, except ``ignoreSpf``, ``ignoreSpfrx`` and ``ignoreB5dc``, which only
need monitoring. A rejected write raises ``DevFailed`` with the same message. Reading
attributes is not affected.

``Abort`` and ``AbortScan`` are always accepted so that queued work can be cancelled.
Without ``MONITOR_AND_CONTROL``, ``AbortScan`` only cancels the long running commands and
does not run the abort sequence.

2. Abort and AbortScan
======================

``Abort`` now only cancels long running commands. It no longer moves the dish. Use
``AbortScan`` for what ``Abort`` did before: cancel the long running commands, then stop
tracking, go to ``STANDBY_FP``, clear the scan ID and reset the track table. The
``AbortCommands`` command has been removed. See :doc:`abort` for the full behaviour.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - If your client called
     - Call now
   * - ``Abort`` to stop the dish
     - ``AbortScan``
   * - ``Abort`` or ``AbortCommands`` to cancel queued commands only
     - ``Abort``

While ``AbortScan`` runs, all long running commands are rejected (``SetStowMode`` is a fast
command and is still accepted), and a second ``AbortScan`` returns ``REJECTED``. In ``MAINTENANCE`` dishMode, ``AbortScan`` only cancels
the long running commands, as it does when ``controlMode`` is not ``MONITOR_AND_CONTROL``.

3. Rejected commands
====================

Long running commands are checked against the current ``dishMode`` when they are called.
A command that is not allowed raises ``DevFailed`` straight away, with a message naming the
commands that are allowed:

.. code-block:: text

   ConfigureBand3 not allowed in UNKNOWN dishMode.
   Commands allowed from UNKNOWN are: ['SetStowMode'].

A command is also allowed when the dish is already in the mode the command leads to, so
repeating a mode command is not an error.

Long running commands are checked a second time just before they start. If the dish
mode changed while the command was queued, the command does not run and ``lrcFinished``
reports it as ``REJECTED``. Clients must therefore handle a rejection both from the
command call and in the command result.

``UpdateTZData``, ``TrackLoadStaticOff`` and ``InterlockAck`` are not checked against the
dish mode, so they are accepted in any dish mode. Like every long running command, they
still need ``MONITOR_AND_CONTROL`` and are rejected while ``AbortScan`` is running.

4. Long running commands
========================

Two points about waiting for a command:

* **Wait for the result in lrcFinished, not for an attribute or progress message.**
  ``ConfigureBand`` from ``OPERATE`` reports the new ``configuredBand`` and the
  ``ConfigureBand<N> complete`` progress message before its final ``SetOperateMode``
  step. A command sent at that point can be rejected, because ``dishMode`` can be
  ``UNKNOWN`` while the dish finishes changing band.
* **Do not match exact progress or result text.** Messages are for operators and can
  change between releases. Use the ``ResultCode``. Timeouts now read
  ``Action '<name>' timed out ...`` followed by details that vary.

5. SetStowMode
==============

``SetStowMode`` is a fast command. It sends Stow to the dish structure, cancels all queued
and running long running commands, and returns ``[ResultCode.STARTED]`` with the message
``Stow called on Dish Structure, monitor achievedPointing and dishmode``. Follow
``dishMode`` to see when the dish reaches ``STOW``. Its message is not published in
``lrcExecuting``. ``SetStowMode`` is accepted in any dish mode and while ``AbortScan``
is running. Called in ``MAINTENANCE``, it also takes the dish out of maintenance mode.

6. healthState and healthInfo
=============================

Both attributes now follow the ska-tango-base rules:

* ``healthState`` is ``UNKNOWN`` only while ``controlMode`` is ``NO_MONITOR_NO_CONTROL``.
  Otherwise an unknown aggregate health is reported as ``FAILED``.
* ``healthInfo`` is empty when ``healthState`` is ``OK``, and lists at least one reason for
  any other state.
* Each ``healthInfo`` entry names a sub-device and its state, for example
  ``tango://.../mid-dish/ds-manager/SKA001: HealthState.FAILED, ["DSC error status: General error"]``.
  A sub-device whose connection is lost is listed as
  ``<device>: CommunicationStatus.NOT_ESTABLISHED, ["Connection lost"]``.
* If every sub-device reports ``OK`` but the DS manager still gives reasons (for example a
  DSC safety status), DishManager reports ``DEGRADED`` with those reasons.

Clients that showed ``healthInfo`` only when ``healthState`` was ``FAILED`` should show it
for every state other than ``OK``.

7. Checklist
============

* Write ``controlMode = MONITOR_AND_CONTROL`` before commanding the dish or writing its
  attributes, and stop using ``adminMode`` to start or stop monitoring.
* Replace ``Abort`` with ``AbortScan`` where the dish should stop moving, and remove
  calls to ``AbortCommands``.
* Handle ``DevFailed`` from command calls and ``REJECTED`` results in ``lrcFinished``.
* Track long running commands through ``lrcQueue``, ``lrcExecuting`` and ``lrcFinished``,
  and wait for the result before sending the next command.
* Check ``ResultCode`` values, not message text.
* Treat ``healthInfo`` as present for every health state other than ``OK``.
