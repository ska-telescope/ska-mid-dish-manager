==========================
Dish Mode Transition Rules
==========================

Rules when no devices are being ignored
---------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/dish_mode.py
   :language: python
   :lines: 5-33
   :emphasize-lines: 4,9,10,15,20,25

Rules when ignoring SPFC device
-------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/dish_mode.py
   :language: python
   :lines: 35-58
   :emphasize-lines: 2,6,7,12,16,20

Rules when ignoring SPFRx device
--------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/dish_mode.py
   :language: python
   :lines: 60-80
   :emphasize-lines: 2,6,7,8,12,17

Rules when ignoring both SPFC and SPFRx devices
-----------------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/dish_mode.py
   :language: python
   :lines: 82-95
   :emphasize-lines: 2,3,4,5,6,10
