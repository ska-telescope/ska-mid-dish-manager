"""
Assesses the state of the control system against
each command's pre-condition before it's executed
"""

from ska_mid_dish_manager.models.dish_enums import DishMode


class CommandAllowedChecks:
    """Pre-condition checks for commands on Dish Manager not transitioning dish mode"""

    def __init__(self, component_manager) -> None:
        self._component_manager = component_manager

    def is_abort_allowed(self) -> bool:
        """Determine if abort command is allowed"""
        component_state = self._component_manager.component_state
        dish_mode = component_state.get("dishmode")
        if dish_mode == DishMode.MAINTENANCE:
            return False
        return True

    def is_track_cmd_allowed(self) -> bool:
        """Determine if track command is allowed"""

    def is_track_stop_cmd_allowed(self) -> bool:
        """Determine if trackStop command is allowed"""

    def is_slew_cmd_allowed(self) -> bool:
        """Determine if slew command is allowed"""
