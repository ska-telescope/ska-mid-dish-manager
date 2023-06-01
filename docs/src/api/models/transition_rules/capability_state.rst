=================================
Capability State Transition Rules
=================================


**CAPABILITY_STATE_RULES**

.. code-block:: python

   "UNAVAILABLE": rule_engine.Rule(
    "(DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
    "DS.operatingmode  == 'DSOperatingMode.ESTOP') "
    " and "
    "SPF.capabilitystate  == 'SPFCapabilityStates.UNAVAILABLE'"
    " and "
    "SPFRX.capabilitystate  == 'SPFRxCapabilityStates.UNAVAILABLE'"
   ),
   "STANDBY_1": rule_engine.Rule(
      "DM.dishmode in "
      "    ['DishMode.STANDBY_LP', "
      "     'DishMode.STANDBY_FP']"
      " and "
      "SPF.capabilitystate in "
      "    ['SPFCapabilityStates.STANDBY', "
      "     'SPFCapabilityStates.OPERATE_DEGRADED', "
      "     'SPFCapabilityStates.OPERATE_FULL']"
      " and "
      "SPFRX.capabilitystate in "
      "    ['SPFRxCapabilityStates.STANDBY', "
      "     'SPFRxCapabilityStates.OPERATE']"
   ),
   "STANDBY_2": rule_engine.Rule(
      "( "
      "  DM.dishmode == 'DishMode.STOW'"
      "  and "
      # Added line below otherwise matches OPERATE_DEGRADED
      "  DS.indexerposition  != 'IndexerPosition.MOVING' "
      ") "
      " and "
      "SPF.capabilitystate == 'SPFCapabilityStates.STANDBY'"
      " and "
      "SPFRX.capabilitystate in "
      "    ['SPFRxCapabilityStates.STANDBY', "
      "     'SPFRxCapabilityStates.OPERATE']"
   ),
   "STANDBY_3": rule_engine.Rule(
      "DM.dishmode == 'DishMode.MAINTENANCE'"
      " and "
      "SPF.capabilitystate in "
      "    ['SPFCapabilityStates.STANDBY', "
      "     'SPFCapabilityStates.OPERATE_DEGRADED', "
      "     'SPFCapabilityStates.OPERATE_FULL']"
      " and "
      "SPFRX.capabilitystate == 'SPFRxCapabilityStates.STANDBY' "
   ),
   "OPERATE_FULL": rule_engine.Rule(
      " DM.dishmode in ['DishMode.STOW', 'DishMode.OPERATE'] "
      " and "
      " SPF.capabilitystate == 'SPFCapabilityStates.OPERATE_FULL' "
      " and "
      " SPFRX.capabilitystate == 'SPFRxCapabilityStates.OPERATE'"
   ),
   "CONFIGURING": rule_engine.Rule(
      "( "
      "   DM.dishmode == 'DishMode.CONFIG' "
      ")  "
      " and "
      "SPF.capabilitystate in "
      "     ['SPFCapabilityStates.OPERATE_DEGRADED', "
      "     'SPFCapabilityStates.OPERATE_FULL']"
      " and "
      "SPFRX.capabilitystate in "
      "    ['SPFRxCapabilityStates.CONFIGURE', "
      "     'SPFRxCapabilityStates.OPERATE']"
   ),
   "OPERATE_DEGRADED": rule_engine.Rule(
      "( "
      "   DS.indexerposition  != 'IndexerPosition.MOVING' "
      "   and  "
      "   DS.operatingmode in "
      "       ['DSOperatingMode.STOW', "
      "        'DSOperatingMode.POINT']"
      ") "
      " and "
      " SPF.capabilitystate == 'SPFCapabilityStates.OPERATE_DEGRADED' "
      " and "
      " SPFRX.capabilitystate == 'SPFRxCapabilityStates.OPERATE'"
   )
