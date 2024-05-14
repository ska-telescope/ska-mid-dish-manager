"""
This model enforces the legal transitions when a command is triggered. It assesses the current
state of the device to decide if the requested state is a nearby node to allow or reject a command.
"""

import typing
from dataclasses import dataclass, field

# pylint: disable=too-few-public-methods,protected-access
from typing import Any

import networkx as nx
import tango

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

    @typing.no_type_check
    def is_command_allowed(
        self, cmd_name: str, dish_mode: str | None = None, component_manager: Any | None = None
    ) -> bool:
        """
        Determine if requested tango command is allowed based on current dish mode

        This method is used by the executor to evaluate the command pre-condition after it's
        taken off the queue. To ensure the evaluation is always performed using an updated
        component state (and not the old state used when the command is queued), the component
        manager should be passed for the enqueue operation. In testing scenarios for example,
        function can be evoked directly with dishmode passed to evaluate the pre-condition.

        NOTE: Though the function signature has only one required argument, it still needs either
        the dish_mode or component_manager passed to it to perform the evaluation.

        :param cmd_name: the requested command
        :param dish_mode: the current dishMode reported by the component state
        :param component_manager: the component manager containing the component state

        :raises TypeError: when no dish_mode or component_manager is provided to function call

        :return: boolean indicating the function execution is allowed
        """
        try:
            current_dish_mode = (
                dish_mode or DishMode(component_manager.component_state["dishmode"]).name
            )
        except AttributeError as exc:
            raise TypeError(
                "is_command_allowed() is missing either the dish_mode or component_manager"
            ) from exc

        allowed_commands = []
        for from_node, to_node in self.dishmode_graph.edges(current_dish_mode):
            commands = self.dishmode_graph.get_edge_data(from_node, to_node).get("commands", None)
            if commands:
                allowed_commands.extend(commands)

        if cmd_name in allowed_commands:
            return True

        if component_manager:
            msg = (
                f"{cmd_name} not allowed in {current_dish_mode} dishMode."
                f" Commands allowed from {current_dish_mode} are: {allowed_commands}."
            )
            logger = component_manager.logger
            task_callback = component_manager._command_tracker

            # report the reason for the command rejection to logs and lrc attribute
            task_callback(progress=msg)  # status and result are handled in executor
            logger.debug(msg)

        return False


@dataclass(order=True)
class PrioritizedEventData:
    """Tango event data with a priority attribute"""

    priority: int
    item: tango.EventData = field(compare=False)
