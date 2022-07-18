# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
import networkx as nx

CONFIG_COMMANDS = (
    "ConfigureBand1",
    "ConfigureBand2",
    "ConfigureBand3",
    "ConfigureBand4",
    "ConfigureBand5a",
    "ConfigureBand5b",
)

DISH_MODE_NODES = (
    "OFF",
    "STARTUP",
    "SHUTDOWN",
    "STANDBY_LP",
    "STANDBY_FP",
    "MAINTENANCE",
    "STOW",
    "CONFIG",
    "OPERATE",
)


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

        # For Shutdown mode
        dishmode_graph.add_edge("SHUTDOWN", "STARTUP")
        dishmode_graph.add_edge("SHUTDOWN", "OFF")

        # For Off mode
        dishmode_graph.add_edge("OFF", "STARTUP")

        # For Startup to other modes
        dishmode_graph.add_edge("STARTUP", "STANDBY_LP")

        # For Standby_LP to other modes
        dishmode_graph.add_edge(
            "STANDBY_LP", "STANDBY_FP", commands=["SetStandbyFPMode"]
        )
        dishmode_graph.add_edge(
            "STANDBY_LP", "MAINTENANCE", commands=["SetMaintenanceMode"]
        )

        # For Standby_FP to other modes
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

        # For Operate to other modes
        dishmode_graph.add_edge(
            "OPERATE", "STANDBY_FP", commands=["SetStandbyFPMode"]
        )
        dishmode_graph.add_edge("OPERATE", "CONFIG", commands=CONFIG_COMMANDS)

        # For Config to other modes
        dishmode_graph.add_edge("CONFIG", "STOW", commands=["SetStowMode"])
        dishmode_graph.add_edge(
            "CONFIG", "STANDBY_FP", commands=["SetStandbyFPMode"]
        )
        dishmode_graph.add_edge(
            "CONFIG", "OPERATE", commands=["SetOperateMode"]
        )

        # For Stow to other modes
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
