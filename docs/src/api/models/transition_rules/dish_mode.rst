==========================
Dish Mode Transition Rules
==========================

Rules when no devices are being ignored
---------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/dish_mode.py
   :language: python
   :lines: 5-39
   :emphasize-lines: 2,7,12,17,24,29,30

Rules when ignoring SPFC device
-------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/dish_mode.py
   :language: python
   :lines: 41-70
   :emphasize-lines: 2,7,11,15,21,25,26

Rules when ignoring SPFRx device
--------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/dish_mode.py
   :language: python
   :lines: 72-95
   :emphasize-lines: 2,3,7,11,15,19,20

Rules when ignoring both SPFC and SPFRx devices
-----------------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/dish_mode.py
   :language: python
   :lines: 97-104
   :emphasize-lines: 2,3,4,5,6,7
