=================================
Capability State Transition Rules
=================================

Rules when no devices are being ignored
---------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/capability_state.py
   :language: python
   :lines: 5-83
   :emphasize-lines: 2,10,24,38,48,55,66

Rules when ignoring SPFC device
-------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/capability_state.py
   :language: python
   :lines: 85-141
   :emphasize-lines: 2,8,17,29,34,39,46

Rules when ignoring SPFRX device
--------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/capability_state.py
   :language: python
   :lines: 143-201
   :emphasize-lines: 2,8,18,28,36,41,48

Rules when ignoring both SPFC and SPFRX devices
-----------------------------------------------
.. literalinclude:: ../../../../../src/ska_mid_dish_manager/models/transition_rules/capability_state.py
   :language: python
   :lines: 203-229
   :emphasize-lines: 2,6,7,15,16,17,18
