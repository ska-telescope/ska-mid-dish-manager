"""Automatic transition rules for health state."""

import rule_engine

HEALTH_STATE_RULES_ALL_DEVICES = {
    "FAILED": rule_engine.Rule(
        "DS.connectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "DS.dsconnectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "SPF.spfconnectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "SPFRX.spfrxconnectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "DS.healthstate == 'HealthState.FAILED' or "
        "SPF.healthstate == 'SPFHealthState.FAILED' or "
        "SPFRX.healthstate == 'HealthState.FAILED'"
    ),
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
    "FAILED": rule_engine.Rule(
        "DS.connectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "DS.dsconnectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "SPFRX.spfrxconnectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "DS.healthstate == 'HealthState.FAILED' or "
        "SPFRX.healthstate == 'HealthState.FAILED'"
    ),
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
    "OK": rule_engine.Rule(
        "DS.healthstate == 'HealthState.OK' and SPFRX.healthstate == 'HealthState.OK'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "DS.healthstate == 'HealthState.UNKNOWN' or SPFRX.healthstate == 'HealthState.UNKNOWN'"
    ),
}

HEALTH_STATE_RULES_SPFRX_IGNORED = {
    "FAILED": rule_engine.Rule(
        "DS.connectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "DS.dsconnectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "SPF.spfrxconnectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "DS.healthstate == 'HealthState.FAILED' or "
        "SPF.healthstate == 'SPFHealthState.FAILED'"
    ),
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
    "OK": rule_engine.Rule(
        "DS.healthstate == 'HealthState.OK' and SPF.healthstate == 'SPFHealthState.NORMAL'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "DS.healthstate == 'HealthState.UNKNOWN' or SPF.healthstate == 'SPFHealthState.UNKNOWN'"
    ),
}

HEALTH_STATE_RULES_DS_ONLY = {
    "FAILED": rule_engine.Rule(
        "DS.connectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "DS.dsconnectionstate in "
        "   ['CommunicationState.NOT_ESTABLISHED', 'CommunicationState.DISABLED'] or "
        "DS.healthstate == 'HealthState.FAILED'"
    ),
    "DEGRADED": rule_engine.Rule("DS.healthstate == 'HealthState.DEGRADED'"),
    "OK": rule_engine.Rule("DS.healthstate == 'HealthState.OK'"),
    "UNKNOWN": rule_engine.Rule("DS.healthstate == 'HealthState.UNKNOWN'"),
}
