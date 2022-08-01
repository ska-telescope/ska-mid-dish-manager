# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
import networkx as nx
import rule_engine

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
)

DISH_MODE_RULES = {
    "CONFIG": rule_engine.Rule(
        "ds_operating_mode  in ['POINT', 'STOW', 'STANDBY_LP', 'STANDBY_FP'] and "
        "spf_operating_mode  == 'OPERATE' and spfrx_operating_mode  == 'CONFIGURE'"
    ),
    "MAINTENANCE": rule_engine.Rule(
        "ds_operating_mode  == 'STOW' and "
        "spf_operating_mode  == 'MAINT' and "
        "spfrx_operating_mode  == 'MAINT'"
    ),
    "OPERATE": rule_engine.Rule(
        "("
        "    ds_operating_mode  == 'POINT' and "
        "    spf_operating_mode  == 'OPERATE' and "
        "    spfrx_operating_mode  == 'DATA_CAPTURE'"
        ") "
        "and "
        "("
        "    ds_power_state == 'FULL_POWER' and "
        "    spf_power_state == 'FULL_POWER' and "
        "    spfrx_power_state == 'FULL_POWER'"
        ")"
    ),
    "STANDBY_FP": rule_engine.Rule(
        "("
        "    ds_operating_mode  == 'STANDBY_FP' and "
        "    spf_operating_mode  == 'OPERATE' and "
        "    spfrx_operating_mode  in ['STANDBY', 'DATA_CAPTURE']"
        ") "
        "and "
        "("
        "    ds_power_state == 'FULL_POWER' and "
        "    spf_power_state == 'FULL_POWER' and "
        "    spfrx_power_state == 'FULL_POWER'"
        ")"
    ),
    "STANDBY_LP": rule_engine.Rule(
        "("
        "    ds_operating_mode == 'STANDBY_LP' and "
        "    spf_operating_mode  == 'STANDBY_LP' and "
        "    spfrx_operating_mode  == 'STANDBY'"
        ") "
        "and "
        "("
        "    ds_power_state == 'LOW_POWER' and "
        "    spf_power_state == 'LOW_POWER' and "
        "    spfrx_power_state == 'LOW_POWER'"
        ")"
    ),
    "STOW": rule_engine.Rule(
        "("
        "    ds_operating_mode  == 'STOW' and "
        "    spf_operating_mode in ['STANDBY_LP', 'OPERATE'] and "
        "    spfrx_operating_mode in ['STANDBY_LP', 'STANDBY_FP', 'DATA_CAPTURE']"
        ") "
        "and "
        "("
        "    ds_power_state == 'LOW_POWER' and "
        "    spf_power_state == 'LOW_POWER' and "
        "    spfrx_power_state == 'LOW_POWER'"
        ")"
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
        "("
        "    ds_health_state == 'FAILED' and "
        "    spf_health_state in ['OK', 'DEGRADED', 'FAILED', 'UNKNOWN'] and "
        "    spfrx_health_state in ['OK', 'DEGRADED', 'FAILED', 'UNKNOWN']"
        ") "
        "or "
        "("
        "    ds_health_state in ['OK', 'DEGRADED', 'FAILED', 'UNKNOWN'] and "
        "    spf_health_state == 'FAILED' and "
        "    spfrx_health_state in ['OK', 'DEGRADED', 'FAILED', 'UNKNOWN']"
        ") "
        "or "
        "("
        "    ds_health_state in ['OK', 'DEGRADED', 'FAILED', 'UNKNOWN'] and "
        "    spf_health_state in ['OK', 'DEGRADED', 'FAILED', 'UNKNOWN'] and "
        "    spfrx_health_state == 'FAILED'"
        ")"
    ),
    "OK": rule_engine.Rule(
        "ds_health_state == 'OK' and "
        "spf_health_state == 'OK' and "
        "spfrx_health_state == 'OK'"
    ),
    "UNKNOWN": rule_engine.Rule(
        "("
        "    ds_health_state == 'UNKNOWN' and "
        "    spf_health_state in ['OK', 'UNKNOWN'] and "
        "    spfrx_health_state in ['OK', 'UNKNOWN']"
        ") "
        "or "
        "("
        "    ds_health_state in ['OK', 'UNKNOWN'] and "
        "    spf_health_state == 'UNKNOWN' and "
        "    spfrx_health_state in ['OK', 'UNKNOWN']"
        ") "
        "or "
        "("
        "    ds_health_state in ['OK', 'UNKNOWN'] and "
        "    spf_health_state in ['OK', 'UNKNOWN'] and "
        "    spfrx_health_state == 'UNKNOWN'"
        ")"
    ),
}


def compute_dish_mode(sub_devices_states):
    for mode, rule in DISH_MODE_RULES.items():
        if rule.matches(sub_devices_states):
            return mode
    return ""


def compute_dish_health_state(sub_devices_health_states):
    for mode, rule in HEALTH_STATE_RULES.items():
        if rule.matches(sub_devices_health_states):
            return mode
    return ""


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
