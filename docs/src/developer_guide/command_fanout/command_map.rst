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

Command Execution (ADR-93 not considered)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In a naive example, the fan-out only considers the sub-components which have the mapped commands from
DishManager. Thus, the propogated respective commands and transition rule aggregation consider all the
participating devices. The sequence diagram below shows a transition to STANDBY-FP.

.. uml:: command_map_sequence_diagram.uml

Command Execution (ADR-93 considered)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Since ADR-93, DishManager now considers whether a sub-component has been ignored to determine which
device receives a command propoagation and is included in the transition rule aggregation. The sequence
diagram below shows a transition to STANDBY-LP (using the ignored attributes).

.. uml:: command_map_sequence_diagram_adr93.uml

.. _command fanout page: https://confluence.skatelescope.org/pages/viewpage.action?pageId=188656205
