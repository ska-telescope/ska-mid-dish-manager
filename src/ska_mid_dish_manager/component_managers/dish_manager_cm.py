# pylint: disable=protected-access
"""Component manager for a DishManager tango device"""
import logging
from datetime import datetime
from typing import Callable, Optional, Tuple

from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.commands import SubmittedSlowCommand
from ska_tango_base.control_model import CommunicationStatus, HealthState
from ska_tango_base.executor import TaskStatus

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import (
    SPFRxComponentManager,
)
from ska_mid_dish_manager.models.command_map import CommandMap
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    CapabilityStates,
    DishMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
    SPFCapabilityStates,
    SPFPowerState,
    SPFRxCapabilityStates,
)
from ska_mid_dish_manager.models.dish_mode_model import (
    CommandNotAllowed,
    DishModeModel,
)


# pylint: disable=abstract-method
class DishManagerComponentManager(TaskExecutorComponentManager):
    """A component manager for DishManager

    It watches the component managers of the subservient devices
    (DS, SPF, SPFRX) to reflect the state of the Dish LMC.
    """

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker,
        sub_device_comm_state_cb,
        *args,
        ds_device_fqdn: str = "mid_d0001/lmc/ds_simulator",
        spf_device_fqdn: str = "mid_d0001/spf/simulator",
        spfrx_device_fqdn: str = "mid_d0001/spfrx/simulator",
        max_workers: int = 3,
        **kwargs,
    ):
        """"""
        # pylint: disable=useless-super-delegation
        super().__init__(
            logger,
            *args,
            max_workers=max_workers,
            dishmode=None,
            capturing=False,
            healthstate=None,
            pointingstate=None,
            b1capabilitystate=None,
            b2capabilitystate=None,
            b3capabilitystate=None,
            b4capabilitystate=None,
            b5acapabilitystate=None,
            b5bcapabilitystate=None,
            achievedtargetlock=None,
            achievedpointing=[0.0, 0.0, 30.0],
            configuredband=Band.NONE,
            spfconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            spfrxconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            dsconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            **kwargs,
        )
        self.sub_device_comm_state_cb = sub_device_comm_state_cb
        self._dish_mode_model = DishModeModel()
        self._command_tracker = command_tracker
        self.component_managers = {}
        self.component_managers["DS"] = DSComponentManager(
            ds_device_fqdn,
            logger,
            operatingmode=None,
            pointingstate=None,
            achievedtargetlock=None,
            indexerposition=IndexerPosition.UNKNOWN,
            powerstate=DSPowerState.UNKNOWN,
            achievedpointing=[0.0, 0.0, 30.0],
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPFRX"] = SPFRxComponentManager(
            spfrx_device_fqdn,
            logger,
            operatingmode=None,
            configuredband=Band.NONE,
            capturingdata=False,
            healthstate=HealthState.UNKNOWN,
            b1capabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b2capabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b3capabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b4capabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b5acapabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b5bcapabilitystate=SPFRxCapabilityStates.UNKNOWN,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPF"] = SPFComponentManager(
            spf_device_fqdn,
            logger,
            operatingmode=None,
            powerstate=SPFPowerState.UNKNOWN,
            healthstate=HealthState.UNKNOWN,
            bandinfocus=BandInFocus.UNKNOWN,
            b1capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b2capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b3capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b4capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b5acapabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b5bcapabilitystate=SPFCapabilityStates.UNAVAILABLE,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        initial_component_states = {
            "dishmode": DishMode.STARTUP,
            "healthstate": HealthState.UNKNOWN,
            "configuredband": Band.NONE,
            "capturing": False,
            "pointingstate": PointingState.UNKNOWN,
            "b1capabilitystate": CapabilityStates.UNKNOWN,
            "b2capabilitystate": CapabilityStates.UNKNOWN,
            "b3capabilitystate": CapabilityStates.UNKNOWN,
            "b4capabilitystate": CapabilityStates.UNKNOWN,
            "b5acapabilitystate": CapabilityStates.UNKNOWN,
            "b5bcapabilitystate": CapabilityStates.UNKNOWN,
            "spfconnectionstate": CommunicationStatus.NOT_ESTABLISHED,
            "spfrxconnectionstate": CommunicationStatus.NOT_ESTABLISHED,
            "dsconnectionstate": CommunicationStatus.NOT_ESTABLISHED,
        }
        self._update_component_state(**initial_component_states)

        self._command_map = CommandMap(
            self,
            self._dish_mode_model,
            self._command_tracker,
            logger,
            self._update_dishmode_component_states,
        )

    # pylint: disable=unused-argument
    def _communication_state_changed(self, *args, **kwargs):
        # communication state will come from args and kwargs

        # an empty dict will make all condition always pass. check
        # that the dict is not empty before continuing with trigger
        if self.component_managers:
            if all(
                cm.communication_state == CommunicationStatus.ESTABLISHED
                for cm in self.component_managers.values()
            ):
                self._update_communication_state(
                    CommunicationStatus.ESTABLISHED
                )

                # Automatic transition to LP mode on startup should come from
                # operating modes of subservient devices. Likewise, any
                # reconnection gained should be accompanied by fresh
                # attribute updates
                self._component_state_changed()
            else:
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                self._update_component_state(healthstate=HealthState.FAILED)

            # trigger push events for the connection state attributes
            self.sub_device_comm_state_cb()

    # pylint: disable=unused-argument, too-many-branches
    def _component_state_changed(self, *args, **kwargs):

        ds_comp_state = self.component_managers["DS"].component_state
        spf_comp_state = self.component_managers["SPF"].component_state
        spfrx_comp_state = self.component_managers["SPFRX"].component_state

        self.logger.debug(
            (
                "Component state has changed, kwargs [%s], DS [%s], SPF [%s]"
                ", SPFRx [%s], DM [%s]"
            ),
            kwargs,
            ds_comp_state,
            spf_comp_state,
            spfrx_comp_state,
            self.component_state,
        )

        if "achievedpointing" in kwargs:
            self.logger.info(
                ("Updating achievedPointing with DS achievedPointing [%s]"),
                str(ds_comp_state["achievedpointing"]),
            )
            new_position = ds_comp_state["achievedpointing"]
            self._update_component_state(achievedpointing=new_position)

        # Only update dishMode if there are operatingmode changes
        if "operatingmode" in kwargs:
            self.logger.info(
                (
                    "Updating dishMode with operatingModes DS"
                    " [%s], SPF [%s], SPFRX [%s]"
                ),
                str(ds_comp_state["operatingmode"]),
                str(spf_comp_state["operatingmode"]),
                str(spfrx_comp_state["operatingmode"]),
            )
            new_dish_mode = self._dish_mode_model.compute_dish_mode(
                ds_comp_state,
                spfrx_comp_state,
                spf_comp_state,
            )
            self._update_component_state(dishmode=new_dish_mode)

        if "healthstate" in kwargs:
            self.logger.info(
                (
                    "Updating healthState with healthstate DS"
                    " [%s], SPF [%s], SPFRX [%s]"
                ),
                str(ds_comp_state["healthstate"]),
                str(spf_comp_state["healthstate"]),
                str(spfrx_comp_state["healthstate"]),
            )
            new_health_state = self._dish_mode_model.compute_dish_health_state(
                ds_comp_state,
                spfrx_comp_state,
                spf_comp_state,
            )
            self._update_component_state(healthstate=new_health_state)

        if "pointingstate" in kwargs:
            self.logger.debug(
                ("Newly calculated component state [pointing_state] [%s]"),
                ds_comp_state["pointingstate"],
            )
            self._update_component_state(
                pointingstate=ds_comp_state["pointingstate"]
            )

            if ds_comp_state["pointingstate"] in [
                PointingState.SLEW,
                PointingState.READY,
            ]:
                self._update_component_state(achievedtargetlock=False)
            elif ds_comp_state["pointingstate"] == PointingState.TRACK:
                self._update_component_state(achievedtargetlock=True)

        # spf bandInFocus
        if (
            "indexerposition" in ds_comp_state
            and "configuredband" in spfrx_comp_state
        ):
            band_in_focus = self._dish_mode_model.compute_spf_band_in_focus(
                ds_comp_state, spfrx_comp_state
            )
            # pylint: disable=protected-access
            # update the bandInFocus of SPF before configuredBand
            spf_proxy = self.component_managers["SPF"]._device_proxy
            # component state changed for DS and SPFRx may be triggered while
            # SPF device proxy is not initialised. Write to the bandInFocus
            # only when you have the device proxy
            if spf_proxy:
                spf_proxy.write_attribute("bandInFocus", band_in_focus)

        # configuredBand
        if (
            "indexerposition" in kwargs
            or "bandinfocus" in kwargs
            or "configuredband" in kwargs
        ):
            self.logger.info(
                (
                    "Updating configuredBand with DS"
                    " [%s] SPF [%s] SPFRX [%s]"
                ),
                str(ds_comp_state),
                str(spf_comp_state),
                str(spfrx_comp_state),
            )

            configured_band = self._dish_mode_model.compute_configured_band(
                ds_comp_state,
                spfrx_comp_state,
                spf_comp_state,
            )
            self._update_component_state(configuredband=configured_band)

        # update capturing attribute when SPFRx captures data
        if "capturingdata" in spfrx_comp_state:
            self.logger.info(
                ("Updating capturing with SPFRx [%s]"),
                str(spfrx_comp_state),
            )
            self._update_component_state(
                capturing=spfrx_comp_state["capturingdata"]
            )

        # CapabilityStates
        # Update all CapabilityStates when indexerposition, dish_mode
        # or operatingmode changes
        if (
            "indexerposition" in kwargs
            or "dish_mode" in kwargs
            or "operatingmode" in kwargs
        ):
            for band in ["b1", "b2", "b3", "b4", "b5a", "b5b"]:
                cap_state_name = f"{band}capabilitystate"
                new_state = self._dish_mode_model.compute_capability_state(
                    band,
                    ds_comp_state,
                    spfrx_comp_state,
                    spf_comp_state,
                    self.component_state,
                )
                self._update_component_state(**{cap_state_name: new_state})

        # Update individual CapabilityStates if it changes
        # b5 for SPF
        for band in ["b1", "b2", "b3", "b4", "b5a", "b5b"]:
            cap_state_name = f"{band}capabilitystate"
            if cap_state_name in kwargs:
                new_state = self._dish_mode_model.compute_capability_state(
                    band,
                    ds_comp_state,
                    spfrx_comp_state,
                    spf_comp_state,
                    self.component_state,
                )
                self._update_component_state(**{cap_state_name: new_state})

    def _update_component_state(self, *args, **kwargs):
        """Log the new component state"""
        self.logger.debug(
            "Updating dish manager component state with [%s]", kwargs
        )
        super()._update_component_state(*args, **kwargs)

    def _update_dishmode_component_states(self):
        """Update the component state required for dishMode changes"""
        for comp_man in self.component_managers.values():
            op_mode = comp_man.read_attribute_value("operatingMode")
            comp_man._update_component_state(operatingmode=op_mode)

    def start_communicating(self):
        """Connect from monitored devices"""
        for com_man in self.component_managers.values():
            com_man.start_communicating()

    def set_standby_lp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_LP mode"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetStandbyLPMode",
        )
        status, response = self.submit_task(
            self._command_map.set_standby_lp_mode,
            args=[],
            task_callback=task_callback,
        )
        return status, response

    def set_standby_fp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_LP mode"""
        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetStandbyFPMode",
        )
        status, response = self.submit_task(
            self._command_map.set_standby_fp_mode,
            args=[],
            task_callback=task_callback,
        )
        return status, response

    def set_operate_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetOperateMode",
        )

        if self.component_state["configuredband"] in [
            Band.NONE,
            Band.UNKNOWN,
        ]:
            raise CommandNotAllowed(
                "configuredBand can not be in "
                f"{Band.NONE.name} or {Band.UNKNOWN.name}",
            )

        status, response = self.submit_task(
            self._command_map.set_operate_mode,
            args=[],
            task_callback=task_callback,
        )
        return status, response

    def track_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode"""
        dish_mode = self.component_state["dishmode"].name
        if dish_mode != "OPERATE":
            raise CommandNotAllowed(
                "Track command only allowed in `OPERATE`"
                f"mode. Current dishMode: {dish_mode}."
            )

        status, response = self.submit_task(
            self._command_map.track_cmd, args=[], task_callback=task_callback
        )
        return status, response

    def configure_band2_cmd(
        self,
        activation_timestamp,
        current_configured_band,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Configure frequency band to band 2"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="ConfigureBand2",
        )

        if current_configured_band == Band.B2:
            return TaskStatus.REJECTED, f"Already in band {Band.B2.name}"

        # TODO Check if ConfigureBand2 is already running

        # check timestamp is in the future
        try:
            if (
                datetime.fromisoformat(activation_timestamp)
                <= datetime.utcnow()
            ):
                return (
                    TaskStatus.REJECTED,
                    f"{activation_timestamp} is not in the future",
                )
        except ValueError as err:
            self.logger.exception(err)
            return TaskStatus.REJECTED, str(err)

        status, response = self.submit_task(
            self._command_map.configure_band2_cmd,
            args=[],
            task_callback=task_callback,
        )
        return status, response

    def set_stow_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STOW mode"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetStowMode",
        )
        status, response = self.submit_task(
            self._command_map.set_stow_mode,
            args=[],
            task_callback=task_callback,
        )
        return status, response

    # pylint: disable=missing-function-docstring
    def stop_communicating(self):
        """Disconnect from monitored devices"""
        for com_man in self.component_managers.values():
            com_man.stop_communicating()
