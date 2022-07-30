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
        "ds_op_mode  in ['POINT', 'STOW', 'STANDBY_LP', 'STANDBY_FP'] and "
        "spf_op_mode  == 'OPERATE' and spfrx_op_mode  == 'CONFIGURE'"
    ),
    "MAINTENANCE": rule_engine.Rule(
        "ds_op_mode  == 'STOW' and "
        "spf_op_mode  == 'MAINT' and "
        "spfrx_op_mode  == 'MAINT'"
    ),
    "OPERATE": rule_engine.Rule(
        "("
        "    ds_op_mode  == 'POINT' and "
        "    spf_op_mode  == 'OPERATE' and "
        "    spfrx_op_mode  == 'DATA_CAPTURE'"
        ") "
        "and "
        "("
        "    ds_pow_state == 'FULL_POWER' and "
        "    spf_pow_state == 'FULL_POWER' and "
        "    spfrx_pow_state == 'FULL_POWER'"
        ")"
    ),
    "STANDBY_FP": rule_engine.Rule(
        "("
        "    ds_op_mode  == 'STANDBY_FP' and "
        "    spf_op_mode  == 'OPERATE' and "
        "    spfrx_op_mode  in ['STANDBY', 'DATA_CAPTURE']"
        ") "
        "and "
        "("
        "    ds_pow_state == 'FULL_POWER' and "
        "    spf_pow_state == 'FULL_POWER' and "
        "    spfrx_pow_state == 'FULL_POWER'"
        ")"
    ),
    "STANDBY_LP": rule_engine.Rule(
        "("
        "    ds_op_mode == 'STANDBY_LP' and "
        "    spf_op_mode  == 'STANDBY_LP' and "
        "    spfrx_op_mode  == 'STANDBY'"
        ") "
        "and "
        "("
        "    ds_pow_state == 'LOW_POWER' and "
        "    spf_pow_state == 'LOW_POWER' and "
        "    spfrx_pow_state == 'LOW_POWER'"
        ")"
    ),
    "STOW": rule_engine.Rule(
        "("
        "    ds_op_mode  == 'STOW' and "
        "    spf_op_mode in ['STANDBY_LP', 'OPERATE'] and "
        "    spfrx_op_mode in ['STANDBY_LP', 'STANDBY_FP', 'DATA_CAPTURE']"
        ") "
        "and "
        "("
        "    ds_pow_state == 'LOW_POWER' and "
        "    spf_pow_state == 'LOW_POWER' and "
        "    spfrx_pow_state == 'LOW_POWER'"
        ")"
    ),
    # "SHUTDOWN": "",
    # "STARTUP": "",
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

    def compute_dish_mode(self, sub_devices_states):
        return ""
