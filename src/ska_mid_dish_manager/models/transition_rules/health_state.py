"""Automatic transition rules for health state."""

import rule_engine

# NOTE! The following healthState computations apply under the assumption
# that all components/subdevices that DishLMC is expected to monitor & control are
# available and that connection with those components is ESTABLISHED

# If a component is expected and its communicationState is DISABLED or
# NOT_ESTABLISHED the computed dish healthState will be overwritten to report FAILED

HEALTH_STATE_RULES_ALL_DEVICES = {
    "DEGRADED": rule_engine.Rule(
        "("
        "    DS.healthstate == 'HealthState.DEGRADED' and "
        "    SPF.healthstate in "
        "       ['SPFHealthState.NORMAL', "
        "        'SPFHealthState.DEGRADED', "
        "        'SPFHealthState.UNKNOWN'] "
        "    and "
        "    SPFRX.healthstate in "
        "      ['HealthState.OK', "
        "       'HealthState.DEGRADED', "
        "       'HealthState.UNKNOWN']"
        ") "
        " or "
        "("
        "    DS.healthstate in "
        "       ['HealthState.OK', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN'] "
        "    and "
        "    SPF.healthstate == 'SPFHealthState.DEGRADED' "
        "    and "
        "    SPFRX.healthstate in "
        "       ['HealthState.OK', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN']"
        ") "
        "or "
        "("
        "    DS.healthstate in "
        "       ['HealthState.OK', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN'] "
        "    and "
        "    SPF.healthstate in "
        "        ['SPFHealthState.NORMAL', "
        "         'SPFHealthState.DEGRADED', "
        "         'SPFHealthState.UNKNOWN'] "
        "    and "
        "    SPFRX.healthstate == 'HealthState.DEGRADED'"
        ")"
    ),
    "FAILED": rule_engine.Rule(
        "DS.healthstate == 'HealthState.FAILED' or "
        "SPF.healthstate == 'SPFHealthState.FAILED' or "
        "SPFRX.healthstate == 'HealthState.FAILED'"
    ),
    "OK": rule_engine.Rule(
        "DS.healthstate == 'HealthState.OK' and "
        "SPF.healthstate == 'SPFHealthState.NORMAL' and "
        "SPFRX.healthstate == 'HealthState.OK'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "DS.healthstate == 'HealthState.UNKNOWN' or "
        "SPF.healthstate == 'SPFHealthState.UNKNOWN' or "
        "SPFRX.healthstate == 'HealthState.UNKNOWN'"
    ),
}


HEALTH_STATE_RULES_SPF_IGNORED = {
    "DEGRADED": rule_engine.Rule(
        "("
        "    DS.healthstate == 'HealthState.DEGRADED' and "
        "    SPFRX.healthstate in "
        "      ['HealthState.OK', "
        "       'HealthState.DEGRADED', "
        "       'HealthState.UNKNOWN']"
        ") "
        "or "
        "("
        "    DS.healthstate in "
        "       ['HealthState.OK', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN'] "
        "    and "
        "    SPFRX.healthstate == 'HealthState.DEGRADED'"
        ")"
    ),
    "FAILED": rule_engine.Rule(
        "DS.healthstate == 'HealthState.FAILED' or SPFRX.healthstate == 'HealthState.FAILED'"
    ),
    "OK": rule_engine.Rule(
        "DS.healthstate == 'HealthState.OK' and SPFRX.healthstate == 'HealthState.OK'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "DS.healthstate == 'HealthState.UNKNOWN' or SPFRX.healthstate == 'HealthState.UNKNOWN'"
    ),
}

HEALTH_STATE_RULES_SPFRX_IGNORED = {
    "DEGRADED": rule_engine.Rule(
        "("
        "    DS.healthstate == 'HealthState.DEGRADED' and "
        "    SPF.healthstate in "
        "       ['SPFHealthState.NORMAL', "
        "        'SPFHealthState.DEGRADED', "
        "        'SPFHealthState.UNKNOWN'] "
        ")"
        " or "
        "("
        "    DS.healthstate in "
        "       ['HealthState.OK', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN'] "
        "    and "
        "    SPF.healthstate == 'SPFHealthState.DEGRADED' "
        ")"
    ),
    "FAILED": rule_engine.Rule(
        "DS.healthstate == 'HealthState.FAILED' or SPF.healthstate == 'SPFHealthState.FAILED'"
    ),
    "OK": rule_engine.Rule(
        "DS.healthstate == 'HealthState.OK' and SPF.healthstate == 'SPFHealthState.NORMAL'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "DS.healthstate == 'HealthState.UNKNOWN' or SPF.healthstate == 'SPFHealthState.UNKNOWN'"
    ),
}

HEALTH_STATE_RULES_DS_ONLY = {
    "DEGRADED": rule_engine.Rule("DS.healthstate == 'HealthState.DEGRADED'"),
    "FAILED": rule_engine.Rule("DS.healthstate == 'HealthState.FAILED'"),
    "OK": rule_engine.Rule("DS.healthstate == 'HealthState.OK'"),
    "UNKNOWN": rule_engine.Rule("DS.healthstate == 'HealthState.UNKNOWN'"),
}
