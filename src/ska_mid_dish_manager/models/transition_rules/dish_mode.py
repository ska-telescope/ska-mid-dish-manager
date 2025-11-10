"""Automatic transition rules for dish mode."""

import rule_engine

DISH_MODE_RULES_ALL_DEVICES = {
    # MAINTENANCE mode is not aggregated from operating modes of subdevices. It
    # is a separate mode that can be commanded directly on the dish manager.
    "STARTUP": rule_engine.Rule(
        "DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
        "SPF.operatingmode  == 'SPFOperatingMode.STARTUP' or "
        "SPFRX.operatingmode  == 'SPFRxOperatingMode.STARTUP'"
    ),
    "STOW": rule_engine.Rule("DS.operatingmode  == 'DSOperatingMode.STOW'"),
    "CONFIG": rule_engine.Rule(
        "SPFRX.operatingmode  == 'SPFRxOperatingMode.CONFIGURE' "
        "or "
        "DS.indexerposition  == 'IndexerPosition.MOVING' "
    ),
    "OPERATE": rule_engine.Rule(
        "DS.operatingmode  == 'DSOperatingMode.POINT' and "
        "SPF.operatingmode  == 'SPFOperatingMode.OPERATE' and "
        "SPFRX.operatingmode  == 'SPFRxOperatingMode.OPERATE'"
    ),
    "STANDBY_LP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY' and "
        "DS.powerstate  == 'DSPowerState.LOW_POWER' and "
        "SPF.operatingmode  != 'SPFOperatingMode.OPERATE'"
    ),
    "STANDBY_FP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY' and "
        "DS.powerstate  == 'DSPowerState.FULL_POWER'"
    ),
}

DISH_MODE_RULES_SPF_IGNORED = {
    "STARTUP": rule_engine.Rule(
        "DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
        "SPFRX.operatingmode  == 'SPFRxOperatingMode.STARTUP'"
    ),
    "STOW": rule_engine.Rule("DS.operatingmode  == 'DSOperatingMode.STOW'"),
    "CONFIG": rule_engine.Rule(
        "SPFRX.operatingmode  == 'SPFRxOperatingMode.CONFIGURE' "
        "or "
        "DS.indexerposition  == 'IndexerPosition.MOVING' "
    ),
    "OPERATE": rule_engine.Rule(
        "DS.operatingmode  == 'DSOperatingMode.POINT' and "
        "SPFRX.operatingmode  == 'SPFRxOperatingMode.OPERATE'"
    ),
    "STANDBY_LP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY' and "
        "DS.powerstate  == 'DSPowerState.LOW_POWER'"
    ),
    "STANDBY_FP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY' and "
        "DS.powerstate  == 'DSPowerState.FULL_POWER'"
    ),
}

DISH_MODE_RULES_SPFRX_IGNORED = {
    "STARTUP": rule_engine.Rule(
        "DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
        "SPF.operatingmode  == 'SPFOperatingMode.STARTUP'"
    ),
    "STOW": rule_engine.Rule("DS.operatingmode  == 'DSOperatingMode.STOW'"),
    "CONFIG": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.MOVING' "),
    "OPERATE": rule_engine.Rule(
        "DS.operatingmode  == 'DSOperatingMode.POINT' and "
        "SPF.operatingmode  == 'SPFOperatingMode.OPERATE'"
    ),
    "STANDBY_LP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY' and "
        "DS.powerstate  == 'DSPowerState.LOW_POWER' and "
        "SPF.operatingmode  != 'SPFOperatingMode.OPERATE'"
    ),
    "STANDBY_FP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY' and "
        "DS.powerstate  == 'DSPowerState.FULL_POWER'"
    ),
}

DISH_MODE_RULES_DS_ONLY = {
    "STARTUP": rule_engine.Rule("DS.operatingmode  == 'DSOperatingMode.STARTUP'"),
    "STOW": rule_engine.Rule("DS.operatingmode  == 'DSOperatingMode.STOW'"),
    "CONFIG": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.MOVING' "),
    "OPERATE": rule_engine.Rule("DS.operatingmode  == 'DSOperatingMode.POINT'"),
    "STANDBY_LP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY' and "
        "DS.powerstate  == 'DSPowerState.LOW_POWER'"
    ),
    "STANDBY_FP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY' and "
        "DS.powerstate  == 'DSPowerState.FULL_POWER'"
    ),
}
