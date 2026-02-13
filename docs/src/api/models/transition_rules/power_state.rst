============================
Power State Transition Rules
============================

Rules when no devices are being ignored
---------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/power_state.py
   :language: python
   :lines: 10-28
   :emphasize-lines: 2,3,4,6,10,15

Rules when ignoring SPFC device
-------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/power_state.py
   :language: python
   :lines: 30-35
   :emphasize-lines: 2,3,4
