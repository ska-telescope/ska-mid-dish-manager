"""State transition computation"""

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    CapabilityStates,
    DishMode,
    HealthState,
    SPFBandInFocus,
)
from ska_mid_dish_manager.models.transition_rules import (
    CAPABILITY_STATE_RULES,
    CONFIGURED_BAND_RULES,
    DISH_MODE_RULES,
    HEALTH_STATE_RULES,
    SPF_BAND_IN_FOCUS_RULES,
)


class StateTransition:
    """Computes the next state from rules based on component updates"""

    def compute_dish_mode(
        self,
        ds_component_state: dict,
        spfrx_component_state: dict,
        spf_component_state: dict,
    ) -> DishMode:
        """Compute the dishMode based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :return: the calculated dishMode
        :rtype: DishMode
        """
        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state, spf_component_state
        )

        for mode, rule in DISH_MODE_RULES.items():
            if rule.matches(dish_manager_states):
                return DishMode[mode]
        return DishMode.UNKNOWN

    def compute_dish_health_state(
        self,
        ds_component_state: dict,
        spfrx_component_state: dict,
        spf_component_state: dict,
    ) -> HealthState:
        """Compute the HealthState based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :return: the calculated HealthState
        :rtype: HealthState
        """
        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state, spf_component_state
        )

        for healthstate, rule in HEALTH_STATE_RULES.items():
            if rule.matches(dish_manager_states):
                return HealthState[healthstate]
        return HealthState.UNKNOWN

    # pylint: disable=too-many-arguments
    def compute_capability_state(
        self,
        band,  # Literal["b1", "b2", "b3", "b4", "b5a", "b5b"],
        ds_component_state: dict,
        spfrx_component_state: dict,
        spf_component_state: dict,
        dish_manager_component_state: dict,
    ) -> CapabilityStates:
        """Compute the capabilityState based off component_states

        The same rules are used regardless of band.
        This method renames b5aCapabilityState to capabilitystate to
        apply the generic rules.

        :param band: The band to calculate for
        :type band: str
        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :param dish_manager_component_state: Dish Manager device component state
        :type dish_manager_component_state: dict
        :return: the calculated capabilityState
        :rtype: CapabilityStates
        """
        # Add the generic name so the rules can be applied
        # SPF
        cap_state = spf_component_state.get(f"{band}capabilitystate", None)
        spf_component_state["capabilitystate"] = cap_state
        # SPFRX
        cap_state = spfrx_component_state.get(f"{band}capabilitystate", None)
        spfrx_component_state["capabilitystate"] = cap_state

        dish_manager_states = self._collapse(
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )

        new_cap_state = CapabilityStates.UNKNOWN
        for capability_state, rule in CAPABILITY_STATE_RULES.items():
            if rule.matches(dish_manager_states):
                if capability_state.startswith("STANDBY"):
                    new_cap_state = CapabilityStates["STANDBY"]
                else:
                    new_cap_state = CapabilityStates[capability_state]
                break

        # Clean up state dicts
        for state_dict in [
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        ]:
            if "capabilitystate" in state_dict:
                del state_dict["capabilitystate"]

        return new_cap_state

    def compute_configured_band(
        self,
        ds_component_state: dict,
        spfrx_component_state: dict,
        spf_component_state: dict,
    ) -> Band:
        """Compute the configuredband based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :return: the calculated configuredband
        :rtype: Band
        """
        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state, spf_component_state
        )

        for band_number, rule in CONFIGURED_BAND_RULES.items():
            if rule.matches(dish_manager_states):
                return Band[band_number]
        return Band.UNKNOWN

    def compute_spf_band_in_focus(
        self,
        ds_component_state: dict,
        spfrx_component_state: dict,
    ) -> SPFBandInFocus:
        """Compute the bandinfocus based off component_states

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :return: the calculated bandinfocus
        :rtype: SPFBandInFocus
        """
        dish_manager_states = self._collapse(ds_component_state, spfrx_component_state)

        for band_number, rule in SPF_BAND_IN_FOCUS_RULES.items():
            if rule.matches(dish_manager_states):
                return SPFBandInFocus[band_number]
        return SPFBandInFocus.UNKNOWN

    @classmethod
    def _collapse(
        cls,
        ds_component_state: dict,
        spfrx_component_state,
        spf_component_state: dict = None,
        dish_manager_component_state: dict = None,
    ) -> dict:
        """Collapse multiple state dicts into one"""
        dish_manager_states = {"DS": {}, "SPF": {}, "SPFRX": {}, "DM": {}}

        for key, val in ds_component_state.items():
            dish_manager_states["DS"][key] = str(val)

        for key, val in spfrx_component_state.items():
            dish_manager_states["SPFRX"][key] = str(val)

        if spf_component_state:
            for key, val in spf_component_state.items():
                dish_manager_states["SPF"][key] = str(val)

        if dish_manager_component_state:
            for key, val in dish_manager_component_state.items():
                dish_manager_states["DM"][key] = str(val)

        return dish_manager_states
