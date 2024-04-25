"""
This model enforces the legal transitions when a command is triggered. It assesses the current
state of the device to decide if the requested state is a nearby node to allow or reject a command.
"""

from dataclasses import dataclass, field

# pylint: disable=too-few-public-methods
from typing import Any, Callable, Optional

import networkx as nx
import tango
from ska_control_model import ResultCode, TaskStatus

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


class CommandNotAllowed(Exception):
    """Exception for illegal transitions"""


class DishModeModel:
    """A representation of the mode transition diagram"""

    def __init__(self) -> None:
        self.dishmode_graph = self._build_model()

    @classmethod
    def _build_model(cls) -> Any:
        dishmode_graph = nx.DiGraph()
        for node in DISH_MODE_NODES:
            dishmode_graph.add_node(node)

        # From Shutdown mode
        dishmode_graph.add_edge("SHUTDOWN", "STARTUP")

        # From Startup to other modes
        dishmode_graph.add_edge("STARTUP", "STANDBY_LP")

        # From Standby_LP to other modes
        dishmode_graph.add_edge("STANDBY_LP", "STANDBY_FP", commands=["SetStandbyFPMode"])
        dishmode_graph.add_edge("STANDBY_LP", "MAINTENANCE", commands=["SetMaintenanceMode"])

        # From Standby_FP to other modes
        dishmode_graph.add_edge("STANDBY_FP", "STANDBY_LP", commands=["SetStandbyLPMode"])
        dishmode_graph.add_edge("STANDBY_FP", "CONFIG", commands=CONFIG_COMMANDS)
        dishmode_graph.add_edge("STANDBY_FP", "OPERATE", commands=["SetOperateMode"])
        dishmode_graph.add_edge("STANDBY_FP", "MAINTENANCE", commands=["SetMaintenanceMode"])

        # From Operate to other modes
        dishmode_graph.add_edge("OPERATE", "STANDBY_FP", commands=["SetStandbyFPMode"])
        dishmode_graph.add_edge("OPERATE", "CONFIG", commands=CONFIG_COMMANDS)

        # From Config to other modes
        dishmode_graph.add_edge("CONFIG", "STANDBY_FP")
        dishmode_graph.add_edge("CONFIG", "OPERATE")
        # config to stow is covered in "any mode to stow" but that
        # transition must be triggered by the SetStowMode cmd
        # However, CONFIG to STOW can also be an automatic transition
        dishmode_graph.add_edge("CONFIG", "STOW")

        # From Stow to other modes
        dishmode_graph.add_edge("STOW", "STANDBY_FP", commands=["SetStandbyFPMode"])
        dishmode_graph.add_edge("STOW", "STANDBY_LP", commands=["SetStandbyLPMode"])
        dishmode_graph.add_edge("STOW", "CONFIG", commands=CONFIG_COMMANDS)

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
        dishmode_graph.add_edge("MAINTENANCE", "STANDBY_FP", commands=["SetStandbyFPMode"])

        return dishmode_graph

    def is_command_allowed(
        self,
        dishmode: Optional[str] = None,
        command_name: Optional[str] = None,
        task_callback: Optional[Callable] = None,
    ) -> bool:
        """Determine if requested tango command is allowed based on current dish mode"""
        allowed_commands = []
        for from_node, to_node in self.dishmode_graph.edges(dishmode):
            commands = self.dishmode_graph.get_edge_data(from_node, to_node).get("commands", None)
            if commands:
                allowed_commands.extend(commands)

        if command_name in allowed_commands:
            return True

        ex = CommandNotAllowed(
            (
                f"Command [{command_name}] not allowed in dishMode "
                f"[{dishmode}], only allowed to do {allowed_commands}"
            )
        )
        if task_callback:
            task_callback(status=TaskStatus.REJECTED, exception=(ResultCode.REJECTED, ex))
        raise ex


@dataclass(order=True)
class PrioritizedEventData:
    """Tango event data with a priority attribute"""

    priority: int
    item: tango.EventData = field(compare=False)
