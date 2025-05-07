"""
Automatic transition rules for power state

These rules are based on assumption that the DS power state is
the most important and the SPF power state is only supplementary
"""

import rule_engine

POWER_STATE_RULES_ALL_DEVICES = {
    "UPS": rule_engine.Rule("DS.powerstate in ['DSPowerState.UPS', 'DSPowerState.OFF']"),
    "LOW_1": rule_engine.Rule("DS.powerstate  == 'DSPowerState.LOW_POWER'"),
    "FULL_1": rule_engine.Rule("DS.powerstate  == 'DSPowerState.FULL_POWER'"),
    # consider case where DS is UNKNOWN and only SPF powerState is available
    "LOW_2": rule_engine.Rule(
        "DS.powerstate  == 'DSPowerState.UNKNOWN' and "
        "SPF.powerstate  == 'SPFPowerState.LOW_POWER'"
    ),
    "FULL_2": rule_engine.Rule(
        "DS.powerstate  == 'DSPowerState.UNKNOWN' and "
        "SPF.powerstate  == 'SPFPowerState.FULL_POWER'"
    ),
    # consider case where both components report UNKNOWN powerstate
    "LOW_3": rule_engine.Rule(
        "DS.powerstate  == 'DSPowerState.UNKNOWN' and "
        "SPF.powerstate  == 'SPFPowerState.UNKNOWN'"
    ),
}

POWER_STATE_RULES_SPF_IGNORED = {
    "UPS": rule_engine.Rule("DS.powerstate in ['DSPowerState.UPS', 'DSPowerState.OFF']"),
    "LOW": rule_engine.Rule("DS.powerstate in ['DSPowerState.LOW_POWER', 'DSPowerState.UNKNOWN']"),
    "FULL": rule_engine.Rule("DS.powerstate  == 'DSPowerState.FULL_POWER'"),
}
