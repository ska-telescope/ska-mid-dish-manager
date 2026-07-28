=============================
Health State Transition Rules
=============================

Rules when no devices are being ignored
---------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/health_state.py
   :language: python
   :lines: 12-70
   :emphasize-lines: 2,44,49,54

Rules when ignoring SPFC device
-------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/health_state.py
   :language: python
   :lines: 73-101
   :emphasize-lines: 2,20,23,26

Rules when ignoring SPFRx device
--------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/health_state.py
   :language: python
   :lines: 104-131
   :emphasize-lines: 2,20,23,26

Rules when ignoring both SPFC and SPFRx devices
-----------------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/health_state.py
   :language: python
   :lines: 133-138
   :emphasize-lines: 2,3,4,5
