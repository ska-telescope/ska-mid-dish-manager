====================
Abort on DishManager
====================

DishManager implemented *Abort* as part of its adaptation of the base classes long running command interface (LRC).
There is extensive `documentation`_ on the implementation details and usage LRC. For clients of DishLMC, aborting can
mean more than instructing the executor to cancel an LRC.

In TMC for example, it could mean:

* stop moving the dish

* and clear the scan id

In the MeerKAT dish proxy, it could mean:

* stop moving the dish

* and request the dish to go to STANDBY-FP mode.

In light of the above, Abort for DishManager consolidates cancelling tasks on DishLMC from the clients' (TMC, MeerKAT Dish Proxy) perspective.
The goal is to arrive at the same state regardless of which client is requesting the action.

DishManager therefore provides two commands:

* **Abort** only cancels LRCs. It is the standard base classes command.

* **AbortScan** cancels LRCs, then runs the abort sequence, so the dish arrives at the same state regardless of which client requested it.

What does Abort do?
^^^^^^^^^^^^^^^^^^^

Abort cancels the running long running command and empties the queue. It does not move the
dish or change the dish mode, and it completes as soon as the cancellation is done.

.. note:: Abort in the other sub-systems usually comes with a Reset command: no Reset functionality is accounted for.

What does AbortScan do?
^^^^^^^^^^^^^^^^^^^^^^^

AbortScan first cancels any running long running commands, similar to Abort. It then executes the abort sequence, ensuring that the dish is brought to a safe and consistent state, typically STANDBY-FP mode.
This guarantees that the dish reaches the same state regardless of which client initiated the abort. AbortScan runs the abort sequence in this order:

#. **TrackStop** if the dish is slewing or tracking, so the dish stops moving.
#. **SetStandbyFPMode**, so further commands can be requested from STANDBY-FP mode.
#. **EndScan**, to clear the scan id.
#. **ResetTrackTable**, to clear the program track table on the controller.

AbortScan is itself a long running command and completes once the whole sequence has finished. It reports FAILED if a step fails, and ABORTED if the sequence is cancelled by a later Abort.

Guarantees and Caveats
^^^^^^^^^^^^^^^^^^^^^^

* Only one AbortScan can run at a time: a second request is rejected until the first finishes.

* While the abort sequence is running, other long running commands are rejected. SetStowMode is still accepted, and cancels the abort sequence when it runs.

* In MAINTENANCE mode, or when controlMode is not MONITOR_AND_CONTROL, AbortScan only cancels LRCs; the abort sequence is not run.

* A dish in STOW mode is left in STOW: TrackStop and the transition to STANDBY-FP are skipped.

* The transition to STANDBY-FP is also skipped if the dish is already in STANDBY-FP.

* A plain Abort issued while AbortScan is running cancels the abort sequence too.

See `abort documentation`_ for discussion and flow diagram

.. warning::
    An ongoing STOW can be interrupted if Abort is triggered. SetStowMode can
    be requested again to resume STOW movement. STOW is primarily a SAFETY request
    is the user's responsibility to avoid unintended consequences.

.. _documentation: https://developer.skao.int/projects/ska-tango-base/en/latest/concepts/long-running-commands.html
.. _abort documentation: https://confluence.skatelescope.org/x/cMiJEQ
