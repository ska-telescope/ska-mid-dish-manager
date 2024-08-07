============================
DishManager Device Interface
============================

Implementing the commands as long running commands require some changes to the telescope model since
all long running commands return a status code and a unique id of the queued command. Tango return
type is `DevVarLongStringArray`. The api guide here captures this difference but will need to be brought
to the notice of TMC and any subsystem going to interface with DishManager.

The current implementation also has the complete API according to the ICD but not all the commands shown
here have been fleshed out fully.

.. note:: SetStowMode on DishManager ensures dish safety: it is time critical and takes precedence over all tasks.
   Though this command is implemented as a long running command, it is immediately executed and NOT parked off on the input queue.
   All other queued LRC tasks are cleared after SetStowMode is executed to ensure the dish does not continue executing tasks which will nullify the STOW.


.. literalinclude:: dish_manager_interface.yaml
   :language: yaml
