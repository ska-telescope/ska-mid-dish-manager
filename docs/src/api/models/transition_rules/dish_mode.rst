==========================
Dish Mode Transition Rules
==========================


**DISH_MODE_RULES**

.. code-block:: python

   "CONFIG": rule_engine.Rule(
      "SPFRX.operatingmode  == 'SPFRxOperatingMode.CONFIGURE' or"
      "DS.indexerposition  == 'IndexerPosition.MOVING' "
   ),
   "MAINTENANCE": rule_engine.Rule(
      "DS.operatingmode  == 'DSOperatingMode.STOW' and "
      "SPF.operatingmode  == 'SPFOperatingMode.MAINTENANCE' and "
      "SPFRX.operatingmode  == 'SPFRxOperatingMode.MAINTENANCE'"
   ),
   "OPERATE": rule_engine.Rule(
      "DS.operatingmode  == 'DSOperatingMode.POINT' and "
      "SPF.operatingmode  == 'SPFOperatingMode.OPERATE' and "
      "SPFRX.operatingmode  == 'SPFRxOperatingMode.DATA_CAPTURE'"
   ),
   "STANDBY_FP": rule_engine.Rule(
      "DS.operatingmode  == 'DSOperatingMode.STANDBY_FP' and "
      "SPF.operatingmode  == 'SPFOperatingMode.OPERATE' and "
      "SPFRX.operatingmode  in "
      " ['SPFRxOperatingMode.STANDBY', "
      "  'SPFRxOperatingMode.DATA_CAPTURE']"
   ),
   "STANDBY_LP": rule_engine.Rule(
      "DS.operatingmode == 'DSOperatingMode.STANDBY_LP' and "
      "SPF.operatingmode  == 'SPFOperatingMode.STANDBY_LP' and "
      "SPFRX.operatingmode  == 'SPFRxOperatingMode.STANDBY'"
   ),
   "STOW": rule_engine.Rule("DS.operatingmode  == 'DSOperatingMode.STOW'"),
   "STARTUP": rule_engine.Rule(
      "DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
      "SPF.operatingmode  == 'SPFOperatingMode.STARTUP' or "
      "SPFRX.operatingmode  == 'SPFRxOperatingMode.STARTUP'"
   ),
