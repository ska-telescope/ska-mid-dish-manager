"""State transition computation."""

from typing import Optional

from ska_control_model import CommunicationStatus, HealthState

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    CapabilityStates,
    DishMode,
    PowerState,
    SPFBandInFocus,
    SPFHealthState,
)
from ska_mid_dish_manager.models.transition_rules import (
    band_focus_rules_all_devices,
    band_focus_rules_spfrx_ignored,
    cap_state_rules_all_devices,
    cap_state_rules_ds_only,
    cap_state_rules_spf_ignored,
    cap_state_rules_spfrx_ignored,
    config_rules_all_devices,
    config_rules_ds_only,
    config_rules_spf_ignored,
    config_rules_spfrx_ignored,
    dish_mode_rules_all_devices,
    dish_mode_rules_ds_only,
    dish_mode_rules_spf_ignored,
    dish_mode_rules_spfrx_ignored,
    health_state_rules_all_devices,
    health_state_rules_ds_only,
    health_state_rules_spf_ignored,
    health_state_rules_spfrx_ignored,
    power_state_rules_all_devices,
    power_state_rules_spf_ignored,
)


class StateTransition:
    """Computes the next state from rules based on component updates."""

    def compute_dish_mode(
        self,
        ds_component_state: dict,  # type: ignore
        spfrx_component_state: Optional[dict] = None,  # type: ignore
        spf_component_state: Optional[dict] = None,  # type: ignore
    ) -> DishMode:
        """Compute the dishMode based off component_states.
        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :return: the calculated dishMode
        :rtype: DishMode.
        """
        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state, spf_component_state
        )

        rules_to_use = dish_mode_rules_ds_only
        if spfrx_component_state and spf_component_state:
            rules_to_use = dish_mode_rules_all_devices
        elif spf_component_state:
            rules_to_use = dish_mode_rules_spfrx_ignored
        elif spfrx_component_state:
            rules_to_use = dish_mode_rules_spf_ignored

        for mode, rule in rules_to_use.items():
            if rule.matches(dish_manager_states):
                return DishMode[mode]
        return DishMode.UNKNOWN

    def _monitored_subdevice_disconnected(
        self,
        ds_communication_state: CommunicationStatus,
        spfrx_communication_state: CommunicationStatus,
        spf_communication_state: CommunicationStatus,
        b5dc_communication_state: CommunicationStatus,
        ds_component_state: dict,
        spfrx_component_state: Optional[dict] = None,
        spf_component_state: Optional[dict] = None,
        b5dc_component_state: Optional[dict] = None,
    ) -> bool:
        """Return a flag indicating whether the expected subdevices are connected or not.

        :param ds_communication_state: DS device component communication state
        :type ds_communication_state: CommunicationStatus
        :param spfrx_communication_state: SPFRX device component communication state
        :type spfrx_communication_state: CommunicationStatus
        :param spf_communication_state: SPF device component communication state
        :type spf_communication_state: CommunicationStatus
        :param b5dc_communication_state: B5dc device component communication state
        :type b5dc_communication_state: CommunicationStatus
        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :param b5dc_component_state: B5dc device component state
        :type b5dc_component_state: dict
        :return: Flag indicating whether an expected device is disconnected
        :rtype: bool
        """
        # Tentatively assume all expected subdevices are connected
        device_disconnected = False

        if ds_communication_state in [
            CommunicationStatus.DISABLED,
            CommunicationStatus.NOT_ESTABLISHED,
        ]:
            device_disconnected = True
        # The following if statement tests the DS Manager - DS Controller connection state
        if CommunicationStatus(
            ds_component_state.get("connectionstate", CommunicationStatus.DISABLED)
        ) in [CommunicationStatus.DISABLED, CommunicationStatus.NOT_ESTABLISHED]:
            device_disconnected = True
        if spfrx_component_state:
            if spfrx_communication_state in [
                CommunicationStatus.DISABLED,
                CommunicationStatus.NOT_ESTABLISHED,
            ]:
                device_disconnected = True
        if spf_component_state:
            if spf_communication_state in [
                CommunicationStatus.DISABLED,
                CommunicationStatus.NOT_ESTABLISHED,
            ]:
                device_disconnected = True
        if b5dc_component_state:
            # The following if statement tests the Dish Manager - B5dc proxy connection state
            if b5dc_communication_state in [
                CommunicationStatus.DISABLED,
                CommunicationStatus.NOT_ESTABLISHED,
            ]:
                device_disconnected = True
            # The following if statement tests the B5dc proxy - B5dc server connection state
            if CommunicationStatus(
                b5dc_component_state.get("connectionstate", CommunicationStatus.DISABLED)
            ) in [CommunicationStatus.DISABLED, CommunicationStatus.NOT_ESTABLISHED]:
                device_disconnected = True

        return device_disconnected

    def compute_dish_health_state(
        self,
        ds_communication_state: CommunicationStatus,
        spfrx_communication_state: CommunicationStatus,
        spf_communication_state: CommunicationStatus,
        b5dc_communication_state: CommunicationStatus,
        ds_component_state: dict,  # type: ignore
        spfrx_component_state: Optional[dict] = None,  # type: ignore
        spf_component_state: Optional[dict] = None,  # type: ignore
        b5dc_component_state: Optional[dict] = None,  # type: ignore
    ) -> HealthState:
        """Compute the HealthState based off component_states.

        :param ds_communication_state: DS device component communication state
        :type ds_communication_state: CommunicationStatus
        :param spfrx_communication_state: SPFRX device component communication state
        :type spfrx_communication_state: CommunicationStatus
        :param spf_communication_state: SPF device component communication state
        :type spf_communication_state: CommunicationStatus
        :param b5dc_communication_state: B5dc device component communication state
        :type b5dc_communication_state: CommunicationStatus
        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :param b5dc_component_state: B5dc device component state
        :type b5dc_component_state: dict
        :return: the calculated HealthState
        :rtype: HealthState
        """
        if self._monitored_subdevice_disconnected(
            ds_communication_state,
            spfrx_communication_state,
            spf_communication_state,
            b5dc_communication_state,
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            b5dc_component_state,
        ):
            return HealthState.FAILED

        dish_manager_states = self._collapse(
            ds_component_state, spfrx_component_state, spf_component_state
        )

        # Get the current healthState enum
        if ds_component_state:
            dish_manager_states["DS"]["healthstate"] = ds_component_state.get(
                "healthstate", HealthState.UNKNOWN
            )
        if spfrx_component_state:
            dish_manager_states["SPFRX"]["healthstate"] = spfrx_component_state.get(
                "healthstate", HealthState.UNKNOWN
            )
        if spf_component_state:
            dish_manager_states["SPF"]["healthstate"] = spf_component_state.get(
                "healthstate", SPFHealthState.UNKNOWN
            )

        # Build the names used in the transition rules
        # --------------------------------------------
        ds_healthstate_name = HealthState(dish_manager_states["DS"]["healthstate"]).name
        dish_manager_states["DS"]["healthstate"] = f"HealthState.{ds_healthstate_name}"

        if "SPFRX" in dish_manager_states:
            spfrx_healthstate_name = HealthState(dish_manager_states["SPFRX"]["healthstate"]).name
            dish_manager_states["SPFRX"]["healthstate"] = f"HealthState.{spfrx_healthstate_name}"
        if "SPF" in dish_manager_states:
            spf_healthstate_name = SPFHealthState(dish_manager_states["SPF"]["healthstate"]).name
            dish_manager_states["SPF"]["healthstate"] = f"SPFHealthState.{spf_healthstate_name}"

        rules_to_use = health_state_rules_ds_only
        if spfrx_component_state and spf_component_state:
            rules_to_use = health_state_rules_all_devices
        elif spf_component_state:
            rules_to_use = health_state_rules_spfrx_ignored
        elif spfrx_component_state:
            rules_to_use = health_state_rules_spf_ignored

        for healthstate, rule in rules_to_use.items():
            if rule.matches(dish_manager_states):
                return HealthState[healthstate]

        return HealthState.UNKNOWN

    # pylint: disable=too-many-arguments
    def compute_capability_state(
        self,
        band: str,  # Literal["b1", "b2", "b3", "b4", "b5a", "b5b"],
        ds_component_state: dict,  # type: ignore
        dish_manager_component_state: dict,  # type: ignore
        spfrx_component_state: Optional[dict] = None,  # type: ignore
        spf_component_state: Optional[dict] = None,  # type: ignore
    ) -> CapabilityStates:
        """Compute the capabilityState based off component_states.

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
        if spf_component_state:
            cap_state = spf_component_state.get(f"{band}capabilitystate", None)
            spf_component_state["capabilitystate"] = cap_state
        # SPFRX
        if spfrx_component_state:
            cap_state = spfrx_component_state.get(f"{band}capabilitystate", None)
            spfrx_component_state["capabilitystate"] = cap_state

        dish_manager_states = self._collapse(
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        rules_to_use = cap_state_rules_ds_only
        if spfrx_component_state and spf_component_state:
            rules_to_use = cap_state_rules_all_devices
        elif spf_component_state:
            rules_to_use = cap_state_rules_spfrx_ignored
        elif spfrx_component_state:
            rules_to_use = cap_state_rules_spf_ignored

        new_cap_state = CapabilityStates.UNKNOWN
        for capability_state, rule in rules_to_use.items():
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
            if state_dict and "capabilitystate" in state_dict:
                del state_dict["capabilitystate"]

        return new_cap_state

    def compute_configured_band(
        self,
        ds_component_state: dict,  # type: ignore
        spfrx_component_state: Optional[dict] = None,  # type: ignore
        spf_component_state: Optional[dict] = None,  # type: ignore
    ) -> Band:
        """Compute the configuredband based off component_states.

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
        rules_to_use = config_rules_ds_only
        if spfrx_component_state and spf_component_state:
            rules_to_use = config_rules_all_devices
        elif spf_component_state:
            rules_to_use = config_rules_spfrx_ignored
        elif spfrx_component_state:
            rules_to_use = config_rules_spf_ignored

        for band_number, rule in rules_to_use.items():
            if rule.matches(dish_manager_states):
                return Band[band_number]
        return Band.UNKNOWN

    def compute_spf_band_in_focus(
        self,
        ds_component_state: dict,  # type: ignore
        spfrx_component_state: Optional[dict] = None,  # type: ignore
    ) -> SPFBandInFocus:
        """Compute the bandinfocus based off component_states.

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spfrx_component_state: SPFRX device component state
        :type spfrx_component_state: dict
        :return: the calculated bandinfocus
        :rtype: SPFBandInFocus
        """
        dish_manager_states = self._collapse(ds_component_state, spfrx_component_state)
        rules_to_use = band_focus_rules_all_devices
        if not spfrx_component_state:
            rules_to_use = band_focus_rules_spfrx_ignored

        for band_number, rule in rules_to_use.items():
            if rule.matches(dish_manager_states):
                return SPFBandInFocus[band_number]
        return SPFBandInFocus.UNKNOWN

    def compute_power_state(
        self,
        ds_component_state: dict,  # type: ignore
        spf_component_state: Optional[dict] = None,  # type: ignore
    ) -> PowerState:
        """Compute the powerstate based off component_states.

        :param ds_component_state: DS device component state
        :type ds_component_state: dict
        :param spf_component_state: SPF device component state
        :type spf_component_state: dict
        :return: the calculated powerstate
        :rtype: PowerState
        """
        dish_manager_states = self._collapse(
            ds_component_state, spf_component_state=spf_component_state
        )
        rules_to_use = power_state_rules_all_devices
        if not spf_component_state:
            rules_to_use = power_state_rules_spf_ignored

        for power_state, rule in rules_to_use.items():
            if rule.matches(dish_manager_states):
                if power_state.startswith("UPS"):
                    return PowerState[power_state]
                _power_state = power_state.split("_")[0]  # pylint: disable=use-maxsplit-arg
                return PowerState[_power_state]
        return PowerState.LOW

    @classmethod
    def _collapse(
        cls,
        ds_component_state: dict,  # type: ignore
        spfrx_component_state: Optional[dict] = None,
        spf_component_state: Optional[dict] = None,  # type: ignore
        dish_manager_component_state: Optional[dict] = None,  # type: ignore
    ) -> dict:  # type: ignore
        """Collapse multiple state dicts into one."""
        dish_manager_states = {"DS": {}}  # type: ignore

        for key, val in ds_component_state.items():
            dish_manager_states["DS"][key] = str(val)

        if spfrx_component_state:
            dish_manager_states["SPFRX"] = {}
            for key, val in spfrx_component_state.items():
                dish_manager_states["SPFRX"][key] = str(val)

        if spf_component_state:
            dish_manager_states["SPF"] = {}
            for key, val in spf_component_state.items():
                dish_manager_states["SPF"][key] = str(val)

        if dish_manager_component_state:
            dish_manager_states["DM"] = {}
            for key, val in dish_manager_component_state.items():
                dish_manager_states["DM"][key] = str(val)

        return dish_manager_states
