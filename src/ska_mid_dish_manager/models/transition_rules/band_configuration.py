"""Automatic transition rules for configuredBand."""

import rule_engine

CONFIGURED_BAND_RULES_ALL_DEVICES = {
    # Must be before None, since for B6 the SPFRx is not configured.
    "B6": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B6'"),
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
        "DS.indexerposition  == 'IndexerPosition.B5a' and "
        "SPFRX.configuredband  == 'Band.B5a' and "
        "SPF.bandinfocus == 'SPFBandInFocus.B5a'"
    ),
    "B5b": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5b' and "
        "SPFRX.configuredband  == 'Band.B1' and "
        "SPF.bandinfocus == 'SPFBandInFocus.B5b'"
    ),
}

CONFIGURED_BAND_RULES_SPF_IGNORED = {
    "B6": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B6'"),
    "NONE": rule_engine.Rule("SPFRX.configuredband  == 'Band.NONE'"),
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
        "DS.indexerposition  == 'IndexerPosition.B5a' and SPFRX.configuredband  == 'Band.B5a'"
    ),
    "B5b": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5b' and SPFRX.configuredband  == 'Band.B1'"
    ),
}

CONFIGURED_BAND_RULES_SPFRX_IGNORED = {
    "B6": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B6'"),
    "B1": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B1' and SPF.bandinfocus == 'SPFBandInFocus.B1'"
    ),
    "B2": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B2' and SPF.bandinfocus == 'SPFBandInFocus.B2'"
    ),
    "B3": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B3' and SPF.bandinfocus == 'SPFBandInFocus.B3'"
    ),
    "B4": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B4' and SPF.bandinfocus == 'SPFBandInFocus.B4'"
    ),
    "B5a": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5a' and SPF.bandinfocus == 'SPFBandInFocus.B5a'"
    ),
    "B5b": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5b' and SPF.bandinfocus == 'SPFBandInFocus.B5b'"
    ),
}

CONFIGURED_BAND_RULES_DS_ONLY = {
    "B1": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B1'"),
    "B2": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B2'"),
    "B3": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B3'"),
    "B4": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B4'"),
    "B5a": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B5a'"),
    "B5b": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B5b'"),
    "B6": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B6'"),
}

SPF_BAND_IN_FOCUS_RULES_ALL_DEVICES = {
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
        "DS.indexerposition  == 'IndexerPosition.B5a' and SPFRX.configuredband == 'Band.B5a'"
    ),
    "B5b": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5b' and SPFRX.configuredband == 'Band.B1'"
    ),
    "B6": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B6'"),
}

SPF_BAND_IN_FOCUS_RULES_SPFRX_IGNORED = {
    "B1": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B1'"),
    "B2": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B2'"),
    "B3": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B3'"),
    "B4": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B4'"),
    "B5a": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B5a'"),
    "B5b": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B5b'"),
    "B6": rule_engine.Rule("DS.indexerposition  == 'IndexerPosition.B6'"),
}
