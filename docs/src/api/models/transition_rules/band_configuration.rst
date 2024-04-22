=============================
Dish Band Configuration Rules
=============================

Rules when no devices are being ignored
---------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/band_configuration.py
   :language: python
   :lines: 5-37
   :emphasize-lines: 2,3,8,13,18,23,28

Rules when ignoring SPFC device
-------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/band_configuration.py
   :language: python
   :lines: 39-59
   :emphasize-lines: 2,3,6,9,12,15,18

Rules when ignoring SPFRx device
--------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/band_configuration.py
   :language: python
   :lines: 61-82
   :emphasize-lines: 2,5,8,11,14,18

Rules when ignoring both SPFC and SPFRx devices
-----------------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/band_configuration.py
   :language: python
   :lines: 84-91
   :emphasize-lines: 2,3,4,5,6,7
