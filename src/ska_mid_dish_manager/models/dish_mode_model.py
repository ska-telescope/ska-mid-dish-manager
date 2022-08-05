# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=C0301
# flake8: noqa: E501
import networkx as nx
import rule_engine

from ska_mid_dish_manager.models.dish_enums import DishMode, HealthState

CONFIG_COMMANDS = (
    "ConfigureBand1",
    "ConfigureBand2",
    "ConfigureBand3",
    "ConfigureBand4",
    "ConfigureBand5a",
    "ConfigureBand5b",
)

DISH_MODE_NODES = (
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

DISH_MODE_RULES = {
    "CONFIG": rule_engine.Rule(
        "DS.operatingmode  in ['DSOperatingMode.POINT', 'DSOperatingMode.STOW', 'DSOperatingMode.STANDBY_LP', 'DSOperatingMode.STANDBY_FP'] and "  # noqa: E501
        "SPF.operatingmode  == 'SPFOperatingMode.OPERATE' and SPFRX.operatingmode  == 'SPFRxOperatingMode.CONFIGURE'"  # noqa: E501
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
        "SPFRX.operatingmode  in ['SPFRxOperatingMode.STANDBY', 'SPFRxOperatingMode.DATA_CAPTURE']"
    ),
    "STANDBY_LP": rule_engine.Rule(
        "DS.operatingmode == 'DSOperatingMode.STANDBY_LP' and "
        "SPF.operatingmode  == 'SPFOperatingMode.STANDBY_LP' and "
        "SPFRX.operatingmode  == 'SPFRxOperatingMode.STANDBY'"
    ),
    "STOW": rule_engine.Rule(
        "DS.operatingmode  == 'DSOperatingMode.STOW' and "
        "SPF.operatingmode in ['SPFOperatingMode.STANDBY_LP', 'SPFOperatingMode.OPERATE'] and "
        "SPFRX.operatingmode in ['SPFRxOperatingMode.STANDBY', 'SPFRxOperatingMode.DATA_CAPTURE']"
    ),
}


HEALTH_STATE_RULES = {
    "DEGRADED": rule_engine.Rule(
        "("
        "    DS.healthstate == 'HealthState.DEGRADED' and "
        "    SPF.healthstate in ['HealthState.NORMAL', 'HealthState.DEGRADED', 'HealthState.UNKNOWN'] and "
        "    SPFRX.healthstate in ['HealthState.NORMAL', 'HealthState.DEGRADED', 'HealthState.UNKNOWN']"
        ") "
        "or "
        "("
        "    DS.healthstate in ['HealthState.NORMAL', 'HealthState.DEGRADED', 'HealthState.UNKNOWN'] and "
        "    SPF.healthstate == 'HealthState.DEGRADED' and "
        "    SPFRX.healthstate in ['HealthState.NORMAL', 'HealthState.DEGRADED', 'HealthState.UNKNOWN']"
        ") "
        "or "
        "("
        "    DS.healthstate in ['HealthState.NORMAL', 'HealthState.DEGRADED', 'HealthState.UNKNOWN'] and "
        "    SPF.healthstate in ['HealthState.NORMAL', 'HealthState.DEGRADED', 'HealthState.UNKNOWN'] and "
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


class CommandNotAllowed(Exception):
    pass


class DishModeModel:
    def __init__(self):
        self.dishmode_graph = self._build_model()

    @classmethod
    def _build_model(cls):
        dishmode_graph = nx.DiGraph()
        for node in DISH_MODE_NODES:
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

        # From any mode to Stow
        for node in DISH_MODE_NODES:
            if node == "STOW":
                continue
            dishmode_graph.add_edge(node, "STOW", commands=["SetStowMode"])

        # From any mode to Shutdown
        for node in DISH_MODE_NODES:
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

    def is_command_allowed(self, dish_mode=None, command_name=None):
        allowed_commands = []
        for from_node, to_node in self.dishmode_graph.edges(dish_mode):
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
                f"[{dish_mode}], only allowed to do {allowed_commands}"
            )
        )

    def compute_dish_mode(
        self,
        ds_component_state: dict,
        spf_component_state: dict,
        spfrx_component_state: dict,
    ) -> DishMode:
        """Compute the dishMode based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :return: the calculated dishMode
        :rtype: DishMode
        """
        dish_manager_states = self._collapse(
            ds_component_state, spf_component_state, spfrx_component_state
        )

        for mode, rule in DISH_MODE_RULES.items():
            if rule.matches(dish_manager_states):
                return DishMode[mode]
        return DishMode.UNKNOWN

    def compute_dish_health_state(
        self,
        ds_component_state: dict,
        spf_component_state: dict,
        spfrx_component_state: dict,
    ) -> HealthState:
        """Compute the HealthState based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :return: the calculated HealthState
        :rtype: HealthState
        """
        dish_manager_states = self._collapse(
            ds_component_state, spf_component_state, spfrx_component_state
        )

        for healthstate, rule in HEALTH_STATE_RULES.items():
            if rule.matches(dish_manager_states):
                return HealthState[healthstate]
        return HealthState.UNKNOWN

    @classmethod
    def _collapse(
        cls,
        ds_component_state: dict,
        spf_component_state: dict,
        spfrx_component_state: dict,
    ) -> dict:
        """Collapse multiple state dicts into one"""
        dish_manager_states = {"DS": dict(), "SPF": dict(), "SPFRX": dict()}

        for key, val in ds_component_state.items():
            dish_manager_states["DS"][key] = str(val)

        for key, val in spf_component_state.items():
            dish_manager_states["SPF"][key] = str(val)

        for key, val in spfrx_component_state.items():
            dish_manager_states["SPFRX"][key] = str(val)

        return dish_manager_states
