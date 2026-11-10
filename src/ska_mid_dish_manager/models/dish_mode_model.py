"""This model enforces the legal transitions when a command is triggered.

It assesses the current state of the dish to decide whether a requested command is allowed.
Mode transition commands are checked against the dish mode transition graph, while other
commands (such as Track and Slew) have their own checks on the component state.
"""

from collections.abc import Callable
from typing import Any, Dict

import networkx as nx

from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState

CONFIG_COMMANDS = (
    "ConfigureBand1",
    "ConfigureBand2",
    "ConfigureBand3",
    "ConfigureBand4",
    "ConfigureBand5a",
    "ConfigureBand5b",
    "ConfigureBand6",
    "ConfigureBand",
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


class CommandNotAllowedError(Exception):
    """Raised when a command is not allowed in the current state of the dish."""


class DishModeModel:
    """Representation of the mode transition diagram, depicting commanded transitions."""

    def __init__(self) -> None:
        self.dishmode_graph = self._build_model()
        self._allowed_commands_by_dish_mode = self._build_allowed_commands(self.dishmode_graph)
        self._command_other_state_check_mapping: dict[str, Callable[[Dict], None]] = {
            "SetOperateMode": self._is_set_operate_mode_allowed,
            "Slew": self._is_slew_allowed,
            "Track": self._is_track_allowed,
            "TrackStop": self._is_track_stop_allowed,
        }

    @classmethod
    def _build_model(cls) -> nx.DiGraph:
        dishmode_graph = nx.DiGraph()
        for node in DISH_MODE_NODES:
            dishmode_graph.add_node(node)

        # From Standby_LP to other modes
        dishmode_graph.add_edge("STANDBY_LP", "STANDBY_FP", commands=["SetStandbyFPMode"])
        dishmode_graph.add_edge("STANDBY_LP", "CONFIG", commands=CONFIG_COMMANDS)

        # From Standby_FP to other modes
        dishmode_graph.add_edge("STANDBY_FP", "STANDBY_LP", commands=["SetStandbyLPMode"])
        dishmode_graph.add_edge("STANDBY_FP", "CONFIG", commands=CONFIG_COMMANDS)

        # From Operate to other modes
        dishmode_graph.add_edge("OPERATE", "STANDBY_FP", commands=["SetStandbyFPMode"])
        dishmode_graph.add_edge("OPERATE", "STANDBY_LP", commands=["SetStandbyLPMode"])
        dishmode_graph.add_edge("OPERATE", "CONFIG", commands=CONFIG_COMMANDS)

        # From Stow to other modes
        dishmode_graph.add_edge("STOW", "STANDBY_FP", commands=["SetStandbyFPMode"])
        dishmode_graph.add_edge("STOW", "STANDBY_LP", commands=["SetStandbyLPMode"])
        dishmode_graph.add_edge("STOW", "CONFIG", commands=CONFIG_COMMANDS)
        dishmode_graph.add_edge("STOW", "MAINTENANCE", commands=["SetMaintenanceMode"])

        # From any mode to Stow
        for node in DISH_MODE_NODES:
            if node == "STOW":
                continue
            dishmode_graph.add_edge(node, "STOW", commands=["SetStowMode"])

        # From any mode to Shutdown
        # TODO: The shutdown command is not currently defined. Add it here
        # once implemented
        for node in DISH_MODE_NODES:
            if node == "SHUTDOWN":
                continue
            dishmode_graph.add_edge(node, "SHUTDOWN")

        return dishmode_graph

    @staticmethod
    def _build_allowed_commands(dishmode_graph: nx.DiGraph) -> dict[str, frozenset[str]]:
        """Precompute the commands allowed from each dish mode.

        :param dishmode_graph: The dish mode transition graph.
        :return: The set of allowed commands, keyed by dish mode name.
        """
        allowed_commands_by_mode: dict[str, frozenset[str]] = {}
        for mode in dishmode_graph.nodes:
            commands: set[str] = set()
            for _, _, edge_data in dishmode_graph.out_edges(mode, data=True):
                commands.update(edge_data.get("commands", ()))
            allowed_commands_by_mode[mode] = frozenset(commands)
        return allowed_commands_by_mode

    @staticmethod
    def _get_current_dish_mode(component_state: Dict[str, Any]) -> str:
        """Return the current dish mode name from the component state."""
        dish_mode = component_state["dishmode"]
        if isinstance(dish_mode, str):
            return DishMode[dish_mode].name

        return DishMode(dish_mode).name

    @staticmethod
    def _require_operate_and_ready(command: str, component_state: Dict[str, Any]) -> None:
        """Require dishMode OPERATE and pointingState READY for a command."""
        if component_state["dishmode"] != DishMode.OPERATE:
            raise CommandNotAllowedError(
                f"{command} command rejected for current dishMode. "
                f"{command} command is allowed for dishMode OPERATE"
            )
        if component_state["pointingstate"] != PointingState.READY:
            raise CommandNotAllowedError(
                f"{command} command rejected for current pointingState. "
                f"{command} command is allowed for pointingState READY"
            )

    def is_command_allowed(
        self,
        cmd_name: str,
        component_state: Dict,
    ) -> bool:
        """Check whether a Tango command is allowed in the current state of the dish.

        Mode transition commands are checked against the dish mode transition graph. Commands
        with their own state checks (such as Track and Slew) need the component manager, since
        they depend on more than the dish mode.

        :param cmd_name: The requested command.
        :param component_state: The current component state dictionary.

        :raises ValueError: If the command has no rule, or the dish mode is unknown to the model.
        :raises CommandNotAllowedError: If the command is not allowed in the current state.

        :return: True if the command is allowed.
        """
        current_dish_mode = self._get_current_dish_mode(component_state)
        allowed_dish_mode_commands = self._allowed_commands_by_dish_mode.get(current_dish_mode)
        check_other_command_allowed = self._command_other_state_check_mapping.get(cmd_name)

        # SetMaintenanceMode is allowed from any dish mode except MAINTENANCE itself
        if cmd_name == "SetMaintenanceMode":
            if current_dish_mode == "MAINTENANCE":
                raise CommandNotAllowedError(
                    "SetMaintenanceMode not allowed: the dish is already in MAINTENANCE dishMode."
                )
            return True
        elif check_other_command_allowed is not None:
            check_other_command_allowed(component_state)
            return True
        elif allowed_dish_mode_commands is not None:
            if cmd_name not in allowed_dish_mode_commands:
                raise CommandNotAllowedError(
                    f"{cmd_name} not allowed in {current_dish_mode} dishMode."
                    f" Commands allowed from {current_dish_mode} are: "
                    f"{sorted(allowed_dish_mode_commands)}."
                )
            return True
        else:
            raise ValueError(f"No rule is defined for command '{cmd_name}'.")

    # ------------------------------------
    # checks for commands NOT in the model
    # ------------------------------------

    def _is_track_allowed(self, component_state: Dict) -> None:
        self._require_operate_and_ready("Track", component_state)

    def _is_slew_allowed(self, component_state: Dict) -> None:
        self._require_operate_and_ready("Slew", component_state)

    def _is_track_stop_allowed(self, component_state: Dict) -> None:
        dish_mode = component_state["dishmode"]
        pointing_state = component_state["pointingstate"]
        if dish_mode != DishMode.OPERATE and pointing_state not in (
            PointingState.TRACK,
            PointingState.SLEW,
        ):
            raise CommandNotAllowedError(
                "TrackStop command rejected for current dishMode and pointingState. "
                "TrackStop command is allowed for dishMode OPERATE or "
                "pointingState SLEW/TRACK"
            )

    def _is_set_operate_mode_allowed(self, component_state: Dict) -> None:
        if component_state["dishmode"] != DishMode.STANDBY_FP:
            raise CommandNotAllowedError(
                "Set operate mode command rejected for current dishMode. "
                "Set operate mode command is allowed for dishMode STANDBY_FP"
            )
