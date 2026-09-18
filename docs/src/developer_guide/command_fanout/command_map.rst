===========
Command Map
===========

DishManager Command Fan-out
---------------------------
The `command fanout page`_ details the Dish component level flow of commands, showing the command,
its pre-condition, triggers (command fan-out) and post condition. The reported value is an aggregation
of values from the sub component determined by a :doc:`list of transition rules <../../api/models/transition_rules/index>`.

.. note::

   **MAINTENANCE mode is not computed from aggregating operating modes it is commanded on dish manager.**

The fan-out itself is done by an Action, which holds one command per subservient device and an
ActionHandler which dispatches them and waits for the result. See
:doc:`actions_and_handlers` for the classes involved.

Command Execution
^^^^^^^^^^^^^^^^^
A command is only accepted if the DishModeModel allows it from the current state. The Action then
fans out its commands, and each one waits for the attribute update it expects from its own device,
whereas, the handler waits for the aggregated attribute on DishManager. The command is only
reported as complete once both have happened. The sequence diagram below shows a transition to
STANDBY-FP, where two commands are sent to DS and none to SPFRx.

.. uml:: command_map_sequence_diagram.uml

Command Execution (ADR-93 considered)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Since ADR-93, DishManager considers whether a sub-component has been ignored to determine which
device receives a command propoagation and is included in the transition rule aggregation. An
ignored device is never sent its command and is counted as successful, so it cannot hold the action
up. The sequence diagram below shows a transition to STANDBY-LP with SPF ignored.

.. uml:: command_map_sequence_diagram_adr93.uml

.. _command fanout page: https://confluence.skatelescope.org/pages/viewpage.action?pageId=188656205
