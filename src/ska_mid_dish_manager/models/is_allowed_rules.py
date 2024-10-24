"""
This model assesses the state of the control system against
each command's precondition before it's executed
"""

from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState


class CommandAllowedChecks:
    """Pre-condition checks for commands on Dish Manager not transitioning dish mode"""

    def __init__(self, component_manager) -> None:
        self._component_manager = component_manager

    def is_abort_allowed(self) -> bool:
        """Determine if abort command is allowed"""
        component_state = self._component_manager.component_state
        pointing_state = component_state.get("pointingstate")
        dish_mode = component_state.get("dishmode")
        if pointing_state == PointingState.SLEW and dish_mode == DishMode.STOW:
            # TODO find out if STOW changes pointing state to SLEW only... and what else?
            return False
        if dish_mode == DishMode.MAINTENANCE:
            return False
        return True

    def is_track_cmd_allowed(self) -> bool:
        """Determine if track command is allowed"""

    def is_track_stop_cmd_allowed(self) -> bool:
        """Determine if trackStop command is allowed"""

    def is_slew_cmd_allowed(self) -> bool:
        """Determine if slew command is allowed"""
