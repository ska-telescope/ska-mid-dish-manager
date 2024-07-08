============================
AbortCommands on DishManager
============================

*AbortCommands* resulted from the implementation of long running commands.
There is extensive `documentation`_ on the implementation details and usage
of long running commands. From the docs, *AbortCommands*:

* Cancels currently running long running task.

* Clears out any commands in the queue.

* Once completed the client is notified via a change event on the lrc attributes.

The steps above also apply to the execution of long running commands on DishManager.
Since DishManager provides aggregate attribute monitoring and control to subservient
devices, it's also useful to detail the events which occur at the sub-level.

**Scenario: DishManager issues AbortCommands after issuing SetStandbyFPMode**

* *abort_commands* is triggered on the component managers for
  DishManager and the subservient devices.

* *abort_commands* sets abort_event (threading.Event object).

* AbortEvent check:
  
  * if event check happens after event is set in the command handler:

    * lrc progress attributes will report aborted.
    * *SetStandbyFPMode()* will be canceled.
    * There will be no command fanout to the
      subservient devices i.e. **DS**, **SPF** and **SPFRx**.

  * if event check happens before abort event is set:
  
    * lrc progress attributes will report **"in progress"**.
    * sub commands will be fanned out to **DS**, **SPF** and **SPFRx**.
    * lrc progress attributes will report every second waiting
      for DishMode update while checking for abort_event.
    * DishManager will abort (cancel the waiting) and report aborted on its
      lrc progress attributes.
    * Subservient devices will be busy executing the sub-commands in a thread
    * The component state of the subservient device might change.
      Abort might leave the device in an inconsistent state and may need recovering.

      .. note:: While the above is ongoing, all commands to DishManager will be rejected until
         `shutdown_and_relaunch`_ is completed on the DishManager component manager.

.. _documentation: https://developer.skao.int/projects/ska-tango-base/en/latest/concepts/long-running-commands.html
.. _shutdown_and_relaunch: https://gitlab.com/ska-telescope/ska-tango-base/-/blob/186236607dc724432fc5ab713766ff8315aafbf2/src/ska_tango_base/executor/executor.py#L128
