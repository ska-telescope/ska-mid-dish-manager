# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import logging

from ska_tango_base.base.component_manager import BaseComponentManager
from ska_tango_base.control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import (
    TangoDeviceComponentManager,
)
from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.models.dish_mode_model import DishModeModel


class DishManagerComponentManager(BaseComponentManager):
    def __init__(
        self,
        *args,
        logger: logging.Logger = None,
        **kwargs,
    ):
        """"""
        # pylint: disable=useless-super-delegation
        super().__init__(
            *args, logger=logger, dish_mode=DishMode.STARTUP, **kwargs
        )
        self._dish_mode_model = DishModeModel()
        self._ds_component_manager = TangoDeviceComponentManager(
            "mid_d0001/lmc/ds_simulator",
            logger=logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )
        self._spfrx_component_manager = TangoDeviceComponentManager(
            "mid_d0001/spfrx/simulator",
            logger=logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )
        self._spf_component_manager = TangoDeviceComponentManager(
            "mid_d0001/spf/simulator",
            logger=logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )

    # pylint: disable=unused-argument
    def _communication_state_changed(self, *args, **kwargs):
        # communication state will come from args and kwargs
        if not hasattr(self, "_ds_component_manager"):
            # init command hasnt run yet. this will cause init device to fail
            return
        if (
            self._ds_component_manager.communication_state
            == CommunicationStatus.ESTABLISHED
            and self._spfrx_component_manager.communication_state
            == CommunicationStatus.ESTABLISHED
            and self._spf_component_manager.communication_state
            == CommunicationStatus.ESTABLISHED
        ):
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            self._update_component_state(dish_mode=DishMode.STANDBY_LP)
        else:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )

    def set_standby_lp_mode(self):
        if self._dish_mode_model.is_command_allowed(
            dish_mode=self.component_state["dish_mode"].name,
            command_name="SetStandbyLPMode",
        ):
            pass
            # commands to call
            # DS -> setstanby-lp
            # SPF -> setstanby-lp
            # SPFRx -> setstandby
            # self._ds_component_manager._device_proxy.SetStandbyLPMode()
            # self._spf_component_manager._device_proxy.SetStandbyLPMode()
            # self._spfrx_component_manager._device_proxy.SetStandbyMode()
        else:
            raise Exception
