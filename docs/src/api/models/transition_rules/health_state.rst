=============================
Health State Transition Rules
=============================

Rules when no devices are being ignored
---------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/health_state.py
   :language: python
   :lines: 5-63
   :emphasize-lines: 2,44,49,54

Rules when ignoring SPFC device
-------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/health_state.py
   :language: python
   :lines: 66-94
   :emphasize-lines: 2,20,23,26

Rules when ignoring SPFRx device
--------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/health_state.py
   :language: python
   :lines: 96-124
   :emphasize-lines: 2,20,23,26

Rules when ignoring both SPFC and SPFRx devices
-----------------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/health_state.py
   :language: python
   :lines: 126-131
   :emphasize-lines: 2,3,4,5
