====================
Abort on DishManager
====================

DishManager implemented *AbortCommands* as part of its adaptation of the base classes long running command interface (LRC).
There is extensive `documentation`_ on the implementation details and usage LRC. For clients of DishLMC, cancelling a task
(Stop for MeerKAT dish proxy and Abort for TMC) means more than just instructing the executor to cancel a LRC.

In TMC for example, it could mean:

* stop moving the dish

* and clear the scan id

In the MeerKAT dish proxy, it could mean:

* stop moving the dish

* and request the dish to go to STANDBY-FP mode.

In light of the above, Abort for DishManager consolidates cancelling tasks on DishLMC from the clients' (TMC, MeerKAT Dish Proxy) perspective.
The goal is to arrive at the same state regardless of which client is requesting the action.

What does Abort do?
^^^^^^^^^^^^^^^^^^^

Abort transitions the device to a state from which further commands can be requested, i.e STANDBY-FP mode.

.. note:: Abort in the other sub-systems usually comes with a Reset command: no Reset functionality is accounted for.

Guarantees and Caveats
^^^^^^^^^^^^^^^^^^^^^^

* Only slew/track tasks will be interrupted when Abort is triggered; tasks like receiver indexing, will not be affected.

* Abort will **stop an ongoing slew to STOW position**.

* Dish will always be restored to STANDBY-FP mode regardless of the previous state before Abort was triggered

See `abort documentation`_ for discussion and flow diagram

.. warning::
    An ongoing STOW can be interrupted if Abort is triggered. SetStowMode can
    be requested again to resume STOW movement. STOW is primarily a SAFETY request
    is the user's responsibility to avoid unintended consequences.

.. _documentation: https://developer.skao.int/projects/ska-tango-base/en/latest/concepts/long-running-commands.html
.. _abort documentation: https://confluence.skatelescope.org/x/cMiJEQ
