============================
AbortCommands on DishManager
============================

*AbortCommands* resulted from the implementation of long running commands.
There is extensive `documentation`_ on the implementation details and usage
of long running commands. From the docs, *AbortCommands*:

* Cancel currently running long running task.

* Clear out any commands in the queue.

* Once completed the client is notified via a change event on an attribute.

The steps above apply to the execution of long running commands on DishManager.
Since DishManager provides aggregate attribute monitoring and control to subservient
devices, it's also useful to detail the events which occur at the sub-level.

Scenario: DishManager issues ``AbortCommands()`` after issuing ``SetStandbyFPMode()``.

**DishManager.AbortCommands() ->**

* *abort_commands* is called on DishManagerComponentManager
  and the component managers of the subservient devices.

* *abort_commands* sets abort_event (threading.Event object) to ``True``.

* AbortEvent check:
  
  * if event check happens after event is set in the command handler:

    * lrc progress attributes will report aborted.
    * *SetStandbyFPMode()* will be canceled.
    * There will be no sub device command call i.e. *SetStandbyFPMpode*.
      on **DS**, *SetOperateMode* on **SPF** and *CaptureData* on
      **SPFRx** (if band is configured).

  * if event check happens before abort event is set DishManager:
  
    * DishManager lrc progress attributes will report **"in progress"**.
    * sub devices command call will trigger.
    * DishManager lrc progress attributes will report every 1s waiting
      for DishMode for update while checking for abort_event during the wait.
    * DishManager will abort (cancel the waiting) and report aborted on its
      lrc progress attributes (if abort_event is set while in the wait loop
      else it will report completed).
    * Subservient devices command call will be busy in a thread as points 3,4
      above are busy running. DishManager will report queued and then **"in progress"**
      on its progress attributes for the individual subservient command calls.
    * In subservient device component manager another abort check is done before
      executing the tango command on the device proxy. Again, if the event is set
      before the check, the command is never triggered. If not, the command will
      trigger and will finish; meaning the component state of the subservient device
      will change and abort will not happen in its true sense but only reported.

* While the above is ongoing, all commands to DishManager will be rejected until
  a `shutdown_and_relaunch`_ is completed on the DishManager component manager.

.. _documentation: https://developer.skao.int/projects/ska-tango-base/en/latest/guide/long_running_command.html
.. _shutdown_and_relaunch: https://gitlab.com/ska-telescope/ska-tango-base/-/blob/main/src/ska_tango_base/executor/executor.py#L94