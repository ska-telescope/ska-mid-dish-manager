# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
import networkx as nx
import rule_engine
from ska_tango_base.control_model import HealthState

from ska_mid_dish_manager.models.dish_enums import DishMode

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
        "ds_operating_mode  in ['POINT', 'STOW', 'STANDBY_LP', 'STANDBY_FP'] and "  # noqa: E501
        "spf_operating_mode  == 'OPERATE' and spfrx_operating_mode  == 'CONFIGURE'"  # noqa: E501
    ),
    "MAINTENANCE": rule_engine.Rule(
        "ds_operating_mode  == 'STOW' and "
        "spf_operating_mode  == 'MAINT' and "
        "spfrx_operating_mode  == 'MAINT'"
    ),
    "OPERATE": rule_engine.Rule(
        "ds_operating_mode  == 'POINT' and "
        "spf_operating_mode  == 'OPERATE' and "
        "spfrx_operating_mode  == 'DATA_CAPTURE'"
    ),
    "STANDBY_FP": rule_engine.Rule(
        "ds_operating_mode  == 'STANDBY_FP' and "
        "spf_operating_mode  == 'OPERATE' and "
        "spfrx_operating_mode  in ['STANDBY', 'DATA_CAPTURE']"
    ),
    "STANDBY_LP": rule_engine.Rule(
        "ds_operating_mode == 'STANDBY_LP' and "
        "spf_operating_mode  == 'STANDBY_LP' and "
        "spfrx_operating_mode  == 'STANDBY'"
    ),
    "STOW": rule_engine.Rule(
        "ds_operating_mode  == 'STOW' and "
        "spf_operating_mode in ['STANDBY_LP', 'OPERATE'] and "
        "spfrx_operating_mode in ['STANDBY_LP', 'STANDBY_FP', 'DATA_CAPTURE']"
    ),
    # "SHUTDOWN": "",
    # "STARTUP": "",
}


HEALTH_STATE_RULES = {
    "DEGRADED": rule_engine.Rule(
        "("
        "    ds_health_state == 'DEGRADED' and "
        "    spf_health_state in ['OK', 'DEGRADED', 'UNKNOWN'] and "
        "    spfrx_health_state in ['OK', 'DEGRADED', 'UNKNOWN']"
        ") "
        "or "
        "("
        "    ds_health_state in ['OK', 'DEGRADED', 'UNKNOWN'] and "
        "    spf_health_state == 'DEGRADED' and "
        "    spfrx_health_state in ['OK', 'DEGRADED', 'UNKNOWN']"
        ") "
        "or "
        "("
        "    ds_health_state in ['OK', 'DEGRADED', 'UNKNOWN'] and "
        "    spf_health_state in ['OK', 'DEGRADED', 'UNKNOWN'] and "
        "    spfrx_health_state == 'DEGRADED'"
        ")"
    ),
    "FAILED": rule_engine.Rule(
        "ds_health_state == 'FAILED' or "
        "spf_health_state == 'FAILED' or "
        "spfrx_health_state == 'FAILED'"
    ),
    "OK": rule_engine.Rule(
        "ds_health_state == 'OK' and "
        "spf_health_state == 'OK' and "
        "spfrx_health_state == 'OK'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "ds_health_state == 'UNKNOWN' or "
        "spf_health_state == 'UNKNOWN' or "
        "spfrx_health_state == 'UNKNOWN'"
    ),
}


def compute_dish_mode(sub_devices_states):
    """Computes the dish mode based the state of the sub-devices. That is
        their operatingMode and powerState.

        E.g. sub-devices_states
            {
                'sub_device_operating_mode': DeviceOperatingMode(value).name
                ...
            }

    :param: sub_devices_states: State of the sub-devices
    :type: sub_devices_states: dict
    :return: The DishMode value computed
    :rtype: DishMode
    """
    for mode, rule in DISH_MODE_RULES.items():
        if rule.matches(sub_devices_states):
            return DishMode[mode]
    return DishMode.UNKNOWN


def compute_dish_health_state(sub_devices_health_states):
    """Computes the overall dish health state based on the
        given health states of the sub-devices

        E.g. sub_devices_health_states
            {
                'sub_device_1' : HealthState(value).name,
                ...
            }

    :param: sub_devices_health_states: Health states from the sub-devices
    :type: sub_devices_health_states: dict
    :return: The HealthState value computed
    :rtype: HealthState
    """
    for health_state, rule in HEALTH_STATE_RULES.items():
        if rule.matches(sub_devices_health_states):
            return HealthState[health_state]
    return HealthState.UNKNOWN


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
