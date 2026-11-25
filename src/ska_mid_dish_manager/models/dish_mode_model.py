"""This model enforces the legal transitions when a command is triggered.

It assesses the current state of the dish to decide whether a requested command is allowed.
Mode transition commands are checked against the dish mode transition graph, while other
commands (such as Track and Slew) have their own checks on the component state.

A command whose target mode is the dish's current mode is also allowed, so repeating a
command (for example SetStowMode while already in STOW) succeeds instead of being rejected.
"""

from typing import Any, Callable, Dict

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


def _build_transitions() -> dict[tuple[str, str], tuple[str, ...]]:
    """Build the commanded dish mode transitions.

    :return: The commands that move the dish between two modes, keyed by
        (from mode, to mode). An empty tuple is a transition no command triggers yet.
    """
    transitions: dict[tuple[str, str], tuple[str, ...]] = {
        # From Standby_LP to other modes
        ("STANDBY_LP", "STANDBY_FP"): ("SetStandbyFPMode",),
        ("STANDBY_LP", "CONFIG"): CONFIG_COMMANDS,
        # From Standby_FP to other modes
        ("STANDBY_FP", "STANDBY_LP"): ("SetStandbyLPMode",),
        ("STANDBY_FP", "CONFIG"): CONFIG_COMMANDS,
        # From Operate to other modes
        ("OPERATE", "STANDBY_FP"): ("SetStandbyFPMode",),
        ("OPERATE", "STANDBY_LP"): ("SetStandbyLPMode",),
        ("OPERATE", "CONFIG"): CONFIG_COMMANDS,
        # From Stow to other modes
        ("STOW", "STANDBY_FP"): ("SetStandbyFPMode",),
        ("STOW", "STANDBY_LP"): ("SetStandbyLPMode",),
        ("STOW", "CONFIG"): CONFIG_COMMANDS,
        ("STOW", "MAINTENANCE"): ("SetMaintenanceMode",),
    }

    # From any mode to Stow
    for mode in DISH_MODE_NODES:
        if mode != "STOW":
            transitions[(mode, "STOW")] = ("SetStowMode",)

    # From any mode to Shutdown
    # TODO: The shutdown command is not currently defined. Add it here once implemented
    for mode in DISH_MODE_NODES:
        if mode != "SHUTDOWN":
            transitions[(mode, "SHUTDOWN")] = ()

    return transitions


DISH_MODE_TRANSITIONS = _build_transitions()


class DishModeModel:
    """Representation of the mode transition diagram, depicting commanded transitions."""

    def __init__(self) -> None:
        self.dish_modes = DISH_MODE_NODES
        self.transitions = DISH_MODE_TRANSITIONS
        self._allowed_commands_by_dish_mode = self._build_allowed_commands(self.transitions)
        self._command_other_state_check_mapping: dict[str, Callable[[Dict], None]] = {
            "SetOperateMode": self._is_set_operate_mode_allowed,
            "Slew": self._is_slew_allowed,
            "Track": self._is_track_allowed,
            "TrackStop": self._is_track_stop_allowed,
        }

    @staticmethod
    def _build_allowed_commands(
        transitions: dict[tuple[str, str], tuple[str, ...]],
    ) -> dict[str, frozenset[str]]:
        """Precompute the commands allowed from each dish mode.

        A command is allowed in a mode if it leads out of that mode, or if it leads into
        that mode (so the dish is already where the command would take it). CONFIG is a
        transient mode, so commands leading into it are not allowed while in it.

        :param transitions: The commanded transitions, keyed by (from mode, to mode).
        :return: The set of allowed commands, keyed by dish mode name.
        """
        allowed_commands_by_mode: dict[str, frozenset[str]] = {}
        for mode in DISH_MODE_NODES:
            commands: set[str] = set()
            for (from_mode, to_mode), transition_commands in transitions.items():
                if from_mode == mode or (to_mode == mode and mode != "CONFIG"):
                    commands.update(transition_commands)
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

        Mode transition commands are checked against the dish mode transition graph. A
        command is also allowed when the dish is already in the mode it would lead to.
        Commands with their own state checks (such as Track and Slew) depend on more than
        the dish mode.

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
        # Allowed from STANDBY_FP, or in OPERATE, where the dish is already in the target mode
        if component_state["dishmode"] not in (DishMode.STANDBY_FP, DishMode.OPERATE):
            raise CommandNotAllowedError(
                "Set operate mode command rejected for current dishMode. "
                "Set operate mode command is allowed for dishMode STANDBY_FP or OPERATE"
            )
