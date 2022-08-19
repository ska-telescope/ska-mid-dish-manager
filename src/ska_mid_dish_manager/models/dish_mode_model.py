# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=C0301
# flake8: noqa: E501
import networkx as nx
import rule_engine

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    CapabilityStates,
    DishMode,
    HealthState,
)

CONFIG_COMMANDS = (
    "ConfigureBand1",
    "ConfigureBand2",
    "ConfigureBand3",
    "ConfigureBand4",
    "ConfigureBand5a",
    "ConfigureBand5b",
)

dishmode_NODES = (
    "STARTUP",
    "SHUTDOWN",
    "STANDBY_LP",
    "STANDBY_FP",
    "MAINTENANCE",
    "STOW",
    "CONFIG",
    "OPERATE",
    "UNKNOWN",
)

dishmode_RULES = {
    "STOW": rule_engine.Rule("DS.operatingmode  == 'DSOperatingMode.STOW'"),
    "CONFIG": rule_engine.Rule(
        "DS.operatingmode in "
        "   ['DSOperatingMode.POINT', "
        "    'DSOperatingMode.STOW', "
        "    'DSOperatingMode.STANDBY_LP', "
        "    'DSOperatingMode.STANDBY_FP'] "
        " and "
        "SPF.operatingmode  == 'SPFOperatingMode.OPERATE' and "
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

CONFIGURED_BAND_RULES = {
    "NONE": rule_engine.Rule("SPFRX.configuredband  == 'Band.NONE'"),
    "B1": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B1' and "
        "SPFRX.configuredband  == 'Band.B1' and "
        "SPF.bandinfocus == 'BandInFocus.B1'"
    ),
    "B2": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B2' and "
        "SPFRX.configuredband  == 'Band.B2' and "
        "SPF.bandinfocus == 'BandInFocus.B2'"
    ),
    "B3": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B3' and "
        "SPFRX.configuredband  == 'Band.B3' and "
        "SPF.bandinfocus == 'BandInFocus.B3'"
    ),
    "B4": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B4' and "
        "SPFRX.configuredband  == 'Band.B4' and "
        "SPF.bandinfocus == 'BandInFocus.B4'"
    ),
    "B5a": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5' and "
        "SPFRX.configuredband  == 'Band.B5a' and "
        "SPF.bandinfocus == 'BandInFocus.B5'"
    ),
    "B5b": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5' and "
        "SPFRX.configuredband  == 'Band.B5b' and "
        "SPF.bandinfocus == 'BandInFocus.B5'"
    ),
}

SPF_BAND_IN_FOCUS_RULES = {
    "B1": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B1' and "
        "SPFRX.configuredband  == 'Band.B1'"
    ),
    "B2": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B2' and "
        "SPFRX.configuredband  == 'Band.B2'"
    ),
    "B3": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B3' and "
        "SPFRX.configuredband  == 'Band.B3'"
    ),
    "B4": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B4' and "
        "SPFRX.configuredband  == 'Band.B4'"
    ),
    "B5": rule_engine.Rule(
        "DS.indexerposition  == 'IndexerPosition.B5' and "
        "SPFRX.configuredband  in ['Band.B5a', 'Band.B5b']"
    ),
}

CAPABILITY_STATE_RULES = {
    "UNAVAILABLE": rule_engine.Rule(
        "(DS.operatingmode  == 'DSOperatingMode.STARTUP' or "
        "DS.operatingmode  == 'DSOperatingMode.ESTOP') "
        " or "
        "SPF.capabilitystate  == 'SPFCapabilityStates.UNAVAILABLE'"
        " or "
        "SPFRX.capabilitystate  == 'SPFRxCapabilityStates.UNAVAILABLE'"
    ),
    "STANDBY_1": rule_engine.Rule(
        "DM.dishmode in "
        "    ['DishMode.STANDBY_LP', "
        "      'DishMode.STANDBY_FP']"
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
        "DM.dishmode == 'DishMode.OPERATE'"
        " and "
        "SPF.capabilitystate in "
        "    ['SPFCapabilityStates.STANDBY', "
        "     'SPFCapabilityStates.OPERATE_DEGRADED', "
        "     'SPFCapabilityStates.OPERATE_FULL']"
        " and "
        "SPFRX.capabilitystate == 'SPFRxCapabilityStates.STANDBY' "
    ),
    "STANDBY_3": rule_engine.Rule(
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
    "STANDBY_4": rule_engine.Rule(
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
        "( "
        "   DS.indexerposition  == 'IndexerPosition.MOVING' "
        "   and  "
        "   DM.dishmode == 'DishMode.STOW'"
        ") "
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
        "   DS.indexerposition  == 'IndexerPosition.MOVING' "
        "   and  "
        "   DM.dishmode in "
        "       ['DishMode.STOW', "
        "        'DishMode.STANDBY_FP']"
        ") "
        " and "
        " SPF.capabilitystate == 'SPFCapabilityStates.STANDBY' "
        " and "
        " SPFRX.capabilitystate in "
        "     ['SPFRxCapabilityStates.STANDBY', "
        "      'SPFRxCapabilityStates.OPERATE']"
    ),
}


class CommandNotAllowed(Exception):
    pass


class DishModeModel:
    def __init__(self):
        self.dishmode_graph = self._build_model()

    @classmethod
    def _build_model(cls):
        dishmode_graph = nx.DiGraph()
        for node in dishmode_NODES:
            dishmode_graph.add_node(node)

        # From Shutdown mode
        dishmode_graph.add_edge("SHUTDOWN", "STARTUP")

        # From Startup to other modes
        dishmode_graph.add_edge("STARTUP", "STANDBY_LP")

        # From Standby_LP to other modes
        dishmode_graph.add_edge(
            "STANDBY_LP", "STANDBY_FP", commands=["SetStandbyFPMode"]
        )
        dishmode_graph.add_edge(
            "STANDBY_LP", "MAINTENANCE", commands=["SetMaintenanceMode"]
        )

        # From Standby_FP to other modes
        dishmode_graph.add_edge(
            "STANDBY_FP", "STANDBY_LP", commands=["SetStandbyLPMode"]
        )
        dishmode_graph.add_edge(
            "STANDBY_FP", "CONFIG", commands=CONFIG_COMMANDS
        )
        dishmode_graph.add_edge(
            "STANDBY_FP", "OPERATE", commands=["SetOperateMode"]
        )
        dishmode_graph.add_edge(
            "STANDBY_FP", "MAINTENANCE", commands=["SetMaintenanceMode"]
        )

        # From Operate to other modes
        dishmode_graph.add_edge(
            "OPERATE", "STANDBY_FP", commands=["SetStandbyFPMode"]
        )
        dishmode_graph.add_edge("OPERATE", "CONFIG", commands=CONFIG_COMMANDS)

        # From Config to other modes
        dishmode_graph.add_edge("CONFIG", "STANDBY_FP")
        dishmode_graph.add_edge("CONFIG", "OPERATE")

        # From Stow to other modes
        dishmode_graph.add_edge(
            "STOW", "STANDBY_FP", commands=["SetStandbyFPMode"]
        )
        dishmode_graph.add_edge(
            "STOW", "STANDBY_LP", commands=["SetStandbyLPMode"]
        )
        dishmode_graph.add_edge("STOW", "CONFIG")

        # From any mode to Stow
        for node in dishmode_NODES:
            if node == "STOW":
                continue
            dishmode_graph.add_edge(node, "STOW", commands=["SetStowMode"])

        # From any mode to Shutdown
        for node in dishmode_NODES:
            if node == "SHUTDOWN":
                continue
            dishmode_graph.add_edge(node, "SHUTDOWN")

        # From Maintenance to other modes
        dishmode_graph.add_edge(
            "MAINTENANCE",
            "STANDBY_LP",
            commands=["SetStandbyLPMode"],
        )
        dishmode_graph.add_edge(
            "MAINTENANCE", "STANDBY_FP", commands=["SetStandbyFPMode"]
        )

        return dishmode_graph

    def is_command_allowed(self, dishmode=None, command_name=None):
        allowed_commands = []
        for from_node, to_node in self.dishmode_graph.edges(dishmode):
            commands = self.dishmode_graph.get_edge_data(
                from_node, to_node
            ).get("commands", None)
            if commands:
                allowed_commands.extend(commands)

        if command_name in allowed_commands:
            return True

        raise CommandNotAllowed(
            (
                f"Command [{command_name}] not allowed in dishMode "
                f"[{dishmode}], only allowed to do {allowed_commands}"
            )
        )

    def compute_dish_mode(
        self,
        ds_component_state: dict,
        spfrx_component_state: dict,
        spf_component_state: dict,
    ) -> DishMode:
        """Compute the dishMode based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :return: the calculated dishMode
        :rtype: DishMode
        """
        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state, spf_component_state
        )

        for mode, rule in dishmode_RULES.items():
            if rule.matches(dish_manager_states):
                return DishMode[mode]
        return DishMode.UNKNOWN

    def compute_dish_health_state(
        self,
        ds_component_state: dict,
        spfrx_component_state: dict,
        spf_component_state: dict,
    ) -> HealthState:
        """Compute the HealthState based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :return: the calculated HealthState
        :rtype: HealthState
        """
        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state, spf_component_state
        )

        for healthstate, rule in HEALTH_STATE_RULES.items():
            if rule.matches(dish_manager_states):
                return HealthState[healthstate]
        return HealthState.UNKNOWN

    def compute_configured_band(
        self,
        ds_component_state: dict,
        spfrx_component_state: dict,
        spf_component_state: dict,
    ) -> Band:
        """Compute the configuredband based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :return: the calculated configuredband
        :rtype: Band
        """
        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state, spf_component_state
        )

        for band_number, rule in CONFIGURED_BAND_RULES.items():
            if rule.matches(dish_manager_states):
                return Band[band_number]
        return Band.UNKNOWN

    def compute_spf_band_in_focus(
        self,
        ds_component_state: dict,
        spfrx_component_state: dict,
    ) -> BandInFocus:
        """Compute the bandinfocus based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :return: the calculated bandinfocus
        :rtype: BandInFocus
        """
        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state
        )

        for band_number, rule in SPF_BAND_IN_FOCUS_RULES.items():
            if rule.matches(dish_manager_states):
                return BandInFocus[band_number]
        return BandInFocus.UNKNOWN

    # pylint: disable=too-many-arguments
    def compute_capability_state(
        self,
        band,  # Literal["b1", "b2", "b3", "b4", "b5a", "b5b"],
        ds_component_state: dict,
        spfrx_component_state: dict,
        spf_component_state: dict,
        dish_manager_component_state: dict,
    ) -> CapabilityStates:
        """Compute the capabilityState based off component_states

        The same rules are used regardless of band.
        This method renames b5aCapabilityState to capabilitystate to
        apply the generic rules.

        :param band: The band to calculate for
        :type band: str
        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :param dish_manager_component_state: Dish Manager device component state
        :type dish_manager_component_state: dict
        :return: the calculated capabilityState
        :rtype: CapabilityStates
        """
        # Add the generic name so the rules can be applied
        # SPF
        cap_state = spf_component_state.get(f"{band}capabilitystate", None)
        if band in ["b5a", "b5b"]:
            cap_state = spf_component_state.get(
                f"{band[:-1]}capabilitystate", None
            )
        spf_component_state["capabilitystate"] = cap_state
        # SPFRX
        cap_state = spfrx_component_state.get(f"{band}capabilitystate", None)
        spfrx_component_state["capabilitystate"] = cap_state

        dish_manager_states = self._collapse(
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )

        new_cap_state = CapabilityStates.UNKNOWN
        for capability_state, rule in CAPABILITY_STATE_RULES.items():
            if rule.matches(dish_manager_states):
                if capability_state.startswith("STANDBY"):
                    new_cap_state = CapabilityStates["STANDBY"]
                else:
                    new_cap_state = CapabilityStates[capability_state]
                break

        # Clean up state dicts
        for state_dict in [
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        ]:
            if "capabilitystate" in state_dict:
                del state_dict["capabilitystate"]

        return new_cap_state

    @classmethod
    def _collapse(
        cls,
        ds_component_state: dict,
        spfrx_component_state,
        spf_component_state: dict = None,
        dish_manager_component_state: dict = None,
    ) -> dict:
        """Collapse multiple state dicts into one"""
        dish_manager_states = {"DS": {}, "SPF": {}, "SPFRX": {}, "DM": {}}

        for key, val in ds_component_state.items():
            dish_manager_states["DS"][key] = str(val)

        for key, val in spfrx_component_state.items():
            dish_manager_states["SPFRX"][key] = str(val)

        if spf_component_state:
            for key, val in spf_component_state.items():
                dish_manager_states["SPF"][key] = str(val)

        if dish_manager_component_state:
            for key, val in dish_manager_component_state.items():
                dish_manager_states["DM"][key] = str(val)

        return dish_manager_states
