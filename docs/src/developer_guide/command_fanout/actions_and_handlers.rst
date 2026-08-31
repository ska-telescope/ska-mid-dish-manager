====================
Actions and Handlers
====================

Most DishManager commands are not executed on DishManager itself, they are fanned out to the
subservient devices and DishManager waits for its own aggregated attributes to settle before the
command is reported as complete. Three classes make up that flow.

The ``FannedOutCommand`` class represents a single command on a single device. It knows how to
dispatch the command, which attributes it is waiting on, and what its own status is. It never
decides the outcome of the overall command.

The ``ActionHandler`` class owns a list of ``FannedOutCommand`` objects. It dispatches them, polls
them once a second, and will only succeed once every command has succeeded and the awaited
component state on DishManager matches. It fails if any of the commands fail or if the action times
out. ``SequentialActionHandler`` has the same design, however, it waits for each command to
finish before dispatching the next one.

The ``Action`` class is the main user facing class. It usually builds its fanned out commands and
its handler in ``__init__``, and is used by the ``DishManagerComponentManager`` as
``SomeAction(logger, self, timeout).execute``. Actions are chained using ``action_on_success`` and
``action_on_failure``, which is how ConfigureBand runs as a sequence of actions.

For example, the SetStandbyLPMode Action has one handler holding 3 fanned out commands, each
waiting on its own device, while the handler waits for ``dishmode`` to become STANDBY_LP.

An Action does not have to be built up front in the ``__init__``. ConfigureBandActionSequence`` has
no handler of its own and defines nothing in ``__init__``, it assembles the whole chain inside
``execute`` because the steps depend on the dish mode at the time the command runs. It applies the
pointing model, chains SetOperateMode on unless we are in STOW, and starts with SetStandbyFPMode if
we are in STANDBY_LP. Build the commands at run time whenever the steps of the action is only known
then.

FannedOutCommand implementations
--------------------------------

- ``FannedOutTangoCommand`` is used for a command on a subservient device which returns
  immediately. It completes once the awaited component state matches.
- ``FannedOutTangoLongRunningCommand`` is used for a long running command on a subservient device
  implemented following the ska-tango-base design. It tracks the command through the ``lrcQueue``,
  ``lrcExecuting`` and ``lrcFinished`` attributes, and also requires the awaited component state to
  match before it will complete.
- ``DishManagerCMMethod`` is used for a plain component manager method. It completes when the call
  returns and fails if it raises.
- ``DishManagerCMMethodResultCode`` is used for a method which returns a ResultCode immediately.
  Anything other than ``ResultCode.OK`` is treated as a failure. If the work gets queued then use a
  separate Action instead.

The ``DishManagerCMMethod`` implementations share one ``execute`` and differ only in
``_handle_result``, which interprets the return value. Add a new one by subclassing and overriding
that method. Both of them reach a final status as soon as the call returns, so they never wait on
an awaited component state.

Command status
--------------

Every fanned out command starts as PENDING, moves through QUEUED or IN_PROGRESS, and ends in
COMPLETED, IGNORED, FAILED, REJECTED, ABORTED or TIMED_OUT. COMPLETED and IGNORED are both counted
as successful.

Every transition goes through ``_set_status``, which logs it at debug level. Example:
``DS.SetStandbyMode IN_PROGRESS -> COMPLETED``.

Adding an Action
----------------

Subclass ``Action``, build the fanned out commands and the handler in ``__init__``, and assign the
handler to ``self._handler``. See ``SetStandbyLPModeAction`` in ``models/command_actions.py`` for
the simplest example. Override ``execute`` when something has to happen before the fan-out, as
SetStandbyLPMode does to move SPFRx out of ENGINEERING admin mode, or when the action has to be
assembled at run time, as ``ConfigureBandActionSequence`` does.

Things to watch out for
-----------------------

There are two unrelated ``execute`` methods in this design. ``Action.execute`` and
``ActionHandler.execute`` take ``task_callback`` and ``task_abort_event`` because they are
submitted to the ska-tango-base task executor. ``FannedOutCommand.execute`` is only ever called by
the handler and takes neither argument.

The commands are given the private ``_component_state`` dict rather than the ``component_state``
property, because the property deep copies and the commands need a live reference to see updates.

A ``timeout_s`` of 0 or less means do not wait. The handler will dispatch and report success
immediately, and if the handler itself is given no timeout it derives one from the longest command
timeout.

``skip_if_already_satisfied`` skips the fan-out when the awaited state already matches and marks
the command IGNORED, and ``completion_delay_s`` covers devices which keep reporting their
pre-command state for a moment after accepting a command, which would otherwise complete the
command instantly.

``is_device_ignored`` comes from the ADR-93 ignored device configuration. Those commands are never
dispatched and are counted as successful.

On timeout the handler re-reads the awaited attributes off each unfinished device before giving up,
as a fallback in case change events were missed.

Actions which build their commands in ``__init__`` do so when the command is submitted and not when
it executes, so values read from component state at construction time can be stale by the time the
worker thread picks the action up. Building at run time avoids that.
