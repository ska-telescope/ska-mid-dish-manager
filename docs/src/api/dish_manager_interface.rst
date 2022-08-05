============================
DishManager Device Interface
============================

Implementing the commands as long running commands require some changes to the telescope model since
all long running commands return a status code and a unique id of the queued command. Tango return
type is `DevVarLongStringArray`. The api guide here captures this difference but will need to be brought
to the notice of TMC and any subsystem going to interface with DishManager.

The current implementation also has the complete API according to the ICD but not all the commands shown
here have been fleshed out fully. Only the following commands have been fleshed out:

* `SetStandbyLPMode`
* `SetStandbyFPMode`
* `SetOperateMode`
* `ConfigureBand2`
* `Track`

.. literalinclude:: dish_manager_interface.yaml
   :language: yaml
