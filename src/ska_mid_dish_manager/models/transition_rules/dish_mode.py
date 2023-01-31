"""Automatic transition rules for dish mode"""

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
