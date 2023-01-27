"""DishManager transition rules for changes in component state of DS, SPF and SPFRx"""

import rule_engine

DISH_MODE_RULES = {
    "CONFIG": rule_engine.Rule(
        "DS.operatingmode in "
        "   ['DSOperatingMode.POINT', "
        "    'DSOperatingMode.STOW', "
        "    'DSOperatingMode.STANDBY_LP', "
        "    'DSOperatingMode.STANDBY_FP'] "
        " and "
        "SPF.operatingmode  in "
        " ['SPFOperatingMode.OPERATE', "
        "  'SPFOperatingMode.STANDBY_LP'] "
        "and "
        "SPFRX.operatingmode  == 'SPFRxOperatingMode.CONFIGURE'"
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
}


HEALTH_STATE_RULES = {
    "DEGRADED": rule_engine.Rule(
        "("
        "    DS.healthstate == 'HealthState.DEGRADED' and "
        "    SPF.healthstate in "
        "       ['HealthState.NORMAL', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN'] "
        "    and "
        "    SPFRX.healthstate in "
        "      ['HealthState.NORMAL', "
        "       'HealthState.DEGRADED', "
        "       'HealthState.UNKNOWN']"
        ") "
        " or "
        "("
        "    DS.healthstate in "
        "       ['HealthState.NORMAL', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN'] "
        "    and "
        "    SPF.healthstate == 'HealthState.DEGRADED' "
        "    and "
        "    SPFRX.healthstate in "
        "       ['HealthState.NORMAL', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN']"
        ") "
        "or "
        "("
        "    DS.healthstate in "
        "       ['HealthState.NORMAL', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN'] "
        "    and "
        "    SPF.healthstate in "
        "        ['HealthState.NORMAL', "
        "         'HealthState.DEGRADED', "
        "         'HealthState.UNKNOWN'] "
        "    and "
        "    SPFRX.healthstate == 'HealthState.DEGRADED'"
        ")"
    ),
    "FAILED": rule_engine.Rule(
        "DS.healthstate == 'HealthState.FAILED' or "
        "SPF.healthstate == 'HealthState.FAILED' or "
        "SPFRX.healthstate == 'HealthState.FAILED'"
    ),
    "NORMAL": rule_engine.Rule(
        "DS.healthstate == 'HealthState.NORMAL' and "
        "SPF.healthstate == 'HealthState.NORMAL' and "
        "SPFRX.healthstate == 'HealthState.NORMAL'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "("
        "    DS.healthstate == 'HealthState.UNKNOWN' and "
        "    SPF.healthstate in ['HealthState.NORMAL', 'HealthState.UNKNOWN'] and "
        "    SPFRX.healthstate in ['HealthState.NORMAL', 'HealthState.UNKNOWN']"
        ") "
        "or "
        "("
        "    DS.healthstate in ['HealthState.NORMAL', 'HealthState.UNKNOWN'] and "
        "    SPF.healthstate == 'HealthState.UNKNOWN' and "
        "    SPFRX.healthstate in ['HealthState.NORMAL', 'HealthState.UNKNOWN']"
        ") "
        "or "
        "("
        "    DS.healthstate in ['HealthState.NORMAL', 'HealthState.UNKNOWN'] and "
        "    SPF.healthstate in ['HealthState.NORMAL', 'HealthState.UNKNOWN'] and "
        "    SPFRX.healthstate == 'HealthState.UNKNOWN'"
        ")"
    ),
}


CAPABILITY_STATE_RULES = {
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
        "   or "
        "   DS.indexerposition == 'IndexerPosition.MOVING' "
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
    ),
}


CONFIGURED_BAND_RULES = {
    "NONE": rule_engine.Rule("SPFRX.configuredband  == 'Band.NONE'"),
    "B1": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B1' and "
        "SPFRX.configuredband  == 'Band.B1' and "
        "SPF.bandinfocus == 'SPFBandInFocus.B1'"
    ),
    "B2": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B2' and "
        "SPFRX.configuredband  == 'Band.B2' and "
        "SPF.bandinfocus == 'SPFBandInFocus.B2'"
    ),
    "B3": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B3' and "
        "SPFRX.configuredband  == 'Band.B3' and "
        "SPF.bandinfocus == 'SPFBandInFocus.B3'"
    ),
    "B4": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B4' and "
        "SPFRX.configuredband  == 'Band.B4' and "
        "SPF.bandinfocus == 'SPFBandInFocus.B4'"
    ),
    "B5a": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5' and "
        "SPFRX.configuredband  == 'Band.B5a' and "
        "SPF.bandinfocus == 'SPFBandInFocus.B5a'"
    ),
    "B5b": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5' and "
        "SPFRX.configuredband  == 'Band.B5b' and "
        "SPF.bandinfocus == 'SPFBandInFocus.B5b'"
    ),
}

SPF_BAND_IN_FOCUS_RULES = {
    "B1": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B1' and SPFRX.configuredband  == 'Band.B1'"
    ),
    "B2": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B2' and SPFRX.configuredband  == 'Band.B2'"
    ),
    "B3": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B3' and SPFRX.configuredband  == 'Band.B3'"
    ),
    "B4": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B4' and SPFRX.configuredband  == 'Band.B4'"
    ),
    "B5a": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5' and SPFRX.configuredband == 'Band.B5a'"
    ),
    "B5b": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5' and SPFRX.configuredband == 'Band.B5b'"
    ),
}
