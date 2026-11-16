"""Automatic transition rules for capability states."""

import rule_engine

CAPABILITY_STATE_RULES_ALL_DEVICES = {
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
        "  DS.feedindexermoving == 'False' "
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
        "DM.dishmode == 'DishMode.CONFIG' "
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
        "   DS.feedindexermoving == 'False' "
        "   and  "
        "   DS.operatingmode in "
        "       ['DSOperatingMode.STOW', "
        "        'DSOperatingMode.POINT']"
        ") "
        " and "
        " SPF.capabilitystate == 'SPFCapabilityStates.OPERATE_DEGRADED' "
        " and "
        " SPFRX.capabilitystate == 'SPFRxCapabilityStates.OPERATE'"
    ),
}

CAPABILITY_STATE_RULES_SPF_IGNORED = {
    "UNAVAILABLE": rule_engine.Rule(
        "(DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
        "DS.operatingmode  == 'DSOperatingMode.ESTOP') "
        " and "
        "SPFRX.capabilitystate  == 'SPFRxCapabilityStates.UNAVAILABLE'"
    ),
    "STANDBY_1": rule_engine.Rule(
        "DM.dishmode in "
        "    ['DishMode.STANDBY_LP', "
        "     'DishMode.STANDBY_FP']"
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
        "  DS.feedindexermoving == 'False' "
        ") "
        " and "
        "SPFRX.capabilitystate in "
        "    ['SPFRxCapabilityStates.STANDBY', "
        "     'SPFRxCapabilityStates.OPERATE']"
    ),
    "STANDBY_3": rule_engine.Rule(
        "DM.dishmode == 'DishMode.MAINTENANCE'"
        " and "
        "SPFRX.capabilitystate == 'SPFRxCapabilityStates.STANDBY' "
    ),
    "OPERATE_FULL": rule_engine.Rule(
        " DM.dishmode in ['DishMode.STOW', 'DishMode.OPERATE'] "
        " and "
        " SPFRX.capabilitystate == 'SPFRxCapabilityStates.OPERATE'"
    ),
    "CONFIGURING": rule_engine.Rule(
        "DM.dishmode == 'DishMode.CONFIG' "
        " and "
        "SPFRX.capabilitystate in "
        "    ['SPFRxCapabilityStates.CONFIGURE', "
        "     'SPFRxCapabilityStates.OPERATE']"
    ),
    "OPERATE_DEGRADED": rule_engine.Rule(
        "( "
        "   DS.feedindexermoving == 'False' "
        "   and  "
        "   DS.operatingmode in "
        "       ['DSOperatingMode.STOW', "
        "        'DSOperatingMode.POINT']"
        ") "
        " and "
        " SPFRX.capabilitystate == 'SPFRxCapabilityStates.OPERATE'"
    ),
}

CAPABILITY_STATE_RULES_SPFRX_IGNORED = {
    "UNAVAILABLE": rule_engine.Rule(
        "(DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
        "DS.operatingmode  == 'DSOperatingMode.ESTOP') "
        " and "
        "SPF.capabilitystate  == 'SPFCapabilityStates.UNAVAILABLE'"
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
    ),
    "STANDBY_2": rule_engine.Rule(
        "( "
        "  DM.dishmode == 'DishMode.STOW'"
        "  and "
        # Added line below otherwise matches OPERATE_DEGRADED
        "  DS.feedindexermoving == 'False' "
        ") "
        " and "
        "SPF.capabilitystate == 'SPFCapabilityStates.STANDBY'"
    ),
    "STANDBY_3": rule_engine.Rule(
        "DM.dishmode == 'DishMode.MAINTENANCE'"
        " and "
        "SPF.capabilitystate in "
        "    ['SPFCapabilityStates.STANDBY', "
        "     'SPFCapabilityStates.OPERATE_DEGRADED', "
        "     'SPFCapabilityStates.OPERATE_FULL']"
    ),
    "OPERATE_FULL": rule_engine.Rule(
        " DM.dishmode in ['DishMode.STOW', 'DishMode.OPERATE'] "
        " and "
        " SPF.capabilitystate == 'SPFCapabilityStates.OPERATE_FULL' "
    ),
    "CONFIGURING": rule_engine.Rule(
        "DM.dishmode == 'DishMode.CONFIG' "
        " and "
        "SPF.capabilitystate in "
        "     ['SPFCapabilityStates.OPERATE_DEGRADED', "
        "     'SPFCapabilityStates.OPERATE_FULL']"
    ),
    "OPERATE_DEGRADED": rule_engine.Rule(
        "( "
        "   DS.feedindexermoving == 'False' "
        "   and  "
        "   DS.operatingmode in "
        "       ['DSOperatingMode.STOW', "
        "        'DSOperatingMode.POINT']"
        ") "
        " and "
        " SPF.capabilitystate == 'SPFCapabilityStates.OPERATE_DEGRADED' "
    ),
}

CAPABILITY_STATE_RULES_DS_ONLY = {
    "UNAVAILABLE": rule_engine.Rule(
        "(DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
        "DS.operatingmode  == 'DSOperatingMode.ESTOP')"
    ),
    "STANDBY_1": rule_engine.Rule("DM.dishmode in ['DishMode.STANDBY_LP', 'DishMode.STANDBY_FP']"),
    "STANDBY_2": rule_engine.Rule(
        "( "
        "  DM.dishmode == 'DishMode.STOW'"
        "  and "
        # Added line below otherwise matches OPERATE_DEGRADED
        "  DS.feedindexermoving == 'False' "
        ")"
    ),
    "STANDBY_3": rule_engine.Rule("DM.dishmode == 'DishMode.MAINTENANCE'"),
    "OPERATE_FULL": rule_engine.Rule(" DM.dishmode in ['DishMode.STOW', 'DishMode.OPERATE'] "),
    "CONFIGURING": rule_engine.Rule("DM.dishmode == 'DishMode.CONFIG' "),
    "OPERATE_DEGRADED": rule_engine.Rule(
        "( "
        "   DS.feedindexermoving == 'False' "
        "   and  "
        "   DS.operatingmode in "
        "       ['DSOperatingMode.STOW', "
        "        'DSOperatingMode.POINT']"
        ") "
    ),
}
