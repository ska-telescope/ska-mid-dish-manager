"""Automatic transition rules for health state"""

import rule_engine

HEALTH_STATE_RULES = {
    "DEGRADED": rule_engine.Rule(
        "("
        "    DS.healthstate == 'HealthState.DEGRADED' and "
        "    SPF.healthstate in "
        "       ['HealthState.OK', "
        "        'HealthState.DEGRADED', "
        "        'HealthState.UNKNOWN'] "
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
        "    SPF.healthstate == 'HealthState.DEGRADED' "
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
        "        ['HealthState.OK', "
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
    "OK": rule_engine.Rule(
        "DS.healthstate == 'HealthState.OK' and "
        "SPF.healthstate == 'HealthState.OK' and "
        "SPFRX.healthstate == 'HealthState.OK'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "DS.healthstate == 'HealthState.UNKNOWN' or "
        "SPF.healthstate == 'HealthState.UNKNOWN' or "
        "SPFRX.healthstate == 'HealthState.UNKNOWN'"
    ),
}
