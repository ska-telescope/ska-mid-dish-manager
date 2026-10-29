"""Tests for selecting the dish structure implementation."""

from unittest.mock import MagicMock, patch

import pytest
import tango

from ska_mid_dish_manager.component_managers.ap_manager_cm import APComponentManager
from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.constants import DEFAULT_DS_MANAGER_TRL

DISH_MAN_CM_DS_FQDN_IDX = 5


def test_create_component_manager_uses_default_ds_when_fqdns_are_not_configured():
    """Test default DS TRL used when neither DS Manager nor AP TRLs are configured."""
    device = DishManager.__new__(DishManager)
    device.logger = MagicMock()

    # Force the creation of the properties dict
    device._tango_properties = {}
    device._command_tracker = MagicMock()
    device._update_version_of_subdevice_on_success = MagicMock()
    device._attr_quality_state_changed = MagicMock()
    device.get_name = MagicMock(return_value="test/dish-manager/1")

    # Init device properties with empty DS and AP instances to later ensure
    # that on DishManagerCM creation, the default DSDeviceFqdn is applied
    device.DSDeviceFqdn = ""
    device.APManagerDeviceFqdn = ""
    device.SPFDeviceFqdn = "test/spf/1"
    device.SPFRxDeviceFqdn = "test/spfrx/1"
    device.B5DCDeviceFqdn = ""
    device.DefaultActionTimeoutSeconds = 10.0
    device.WMSDeviceNames = []
    device.DefaultWatchdogTimeout = 0.0
    device.MeanWindSpeedThreshold = 0.0
    device.WindGustThreshold = 0.0

    device._communication_state_changed = MagicMock()
    device._component_state_changed = MagicMock()
    device._wind_stow_inform = MagicMock()

    with patch.object(DishManager, "_configure_additional_user_tags_for_logging"):
        with patch(
            "ska_mid_dish_manager.devices.DishManagerDS.DishManagerComponentManager",
            wraps=DishManagerComponentManager,
        ) as dish_manager_cm_init:
            dish_manager_cm = device.create_component_manager()

    dish_manager_cm_init.assert_called_once()
    assert dish_manager_cm_init.call_args.args[DISH_MAN_CM_DS_FQDN_IDX] == DEFAULT_DS_MANAGER_TRL

    # Verify that the correct dish structure CM type was selected
    assert isinstance(dish_manager_cm.sub_component_managers["DS"], DSComponentManager)


def test_create_component_manager_creates_ap_sub_component_manager_when_ap_fqdn_configured():
    """Test AP subcomponent manager is instatiated when APFqdn property is set."""
    device = DishManager.__new__(DishManager)
    device.logger = MagicMock()

    # Force the creation of the properties dict
    device._tango_properties = {}
    device._command_tracker = MagicMock()
    device._update_version_of_subdevice_on_success = MagicMock()
    device._attr_quality_state_changed = MagicMock()
    device.get_name = MagicMock(return_value="test/dish-manager/1")

    # Init device properties with empty DS and  configured AP instance to later ensure
    # that on DishManagerCM creation the instantiation of the AP subcomponent manager is done
    device.DSDeviceFqdn = ""
    device.APManagerDeviceFqdn = "test/ap-man/1"
    device.SPFDeviceFqdn = "test/spf/1"
    device.SPFRxDeviceFqdn = "test/spfrx/1"
    device.B5DCDeviceFqdn = ""
    device.DefaultActionTimeoutSeconds = 10.0
    device.WMSDeviceNames = []
    device.DefaultWatchdogTimeout = 0.0
    device.MeanWindSpeedThreshold = 0.0
    device.WindGustThreshold = 0.0

    device._communication_state_changed = MagicMock()
    device._component_state_changed = MagicMock()
    device._wind_stow_inform = MagicMock()

    with patch.object(DishManager, "_configure_additional_user_tags_for_logging"):
        with patch(
            "ska_mid_dish_manager.devices.DishManagerDS.DishManagerComponentManager",
            wraps=DishManagerComponentManager,
        ) as dish_manager_cm_init:
            dish_manager_cm = device.create_component_manager()

    dish_manager_cm_init.assert_called_once()

    # Verify that the correct dish structure CM type was selected
    assert isinstance(dish_manager_cm.sub_component_managers["DS"], APComponentManager)


def test_ds_fqdn_and_ap_fqdn_conflict_fails_dish_manager_cm_creation():
    """Test configuring both dish structure FQDNs raises a Tango error."""
    device = DishManager.__new__(DishManager)
    device.logger = MagicMock()

    # Force the creation of the properties dict
    device._tango_properties = {}
    device._command_tracker = MagicMock()
    device._update_version_of_subdevice_on_success = MagicMock()
    device._attr_quality_state_changed = MagicMock()
    device.get_name = MagicMock(return_value="test/dish-manager/1")

    # Init device properties with both DS and AP fqdns to later ensure
    # that on DishManagerCM creation raises a DevFailed due to the configuration
    # conflict
    ds_man_trl = "test/ds-man/1"
    ap_man_trl = "test/ap-man/1"
    device.DSDeviceFqdn = ds_man_trl
    device.APManagerDeviceFqdn = ap_man_trl
    device.SPFDeviceFqdn = "test/spf/1"
    device.SPFRxDeviceFqdn = "test/spfrx/1"
    device.B5DCDeviceFqdn = ""
    device.DefaultActionTimeoutSeconds = 10.0
    device.WMSDeviceNames = []
    device.DefaultWatchdogTimeout = 0.0
    device.MeanWindSpeedThreshold = 0.0
    device.WindGustThreshold = 0.0

    device._communication_state_changed = MagicMock()
    device._component_state_changed = MagicMock()
    device._wind_stow_inform = MagicMock()

    expected_message = (
        "Failed to instantiate dish manager while both the "
        f"DS Manager FQDN [{ds_man_trl}] and the AP Manager "
        f"FQDN [{ap_man_trl}] are configured. Please configure only one of "
        "the dish structure FQDN properties, disabling the other by setting it to an "
        "empty string."
    )

    with patch.object(DishManager, "_configure_additional_user_tags_for_logging"):
        with pytest.raises(tango.DevFailed) as except_msg:
            device.create_component_manager()

    assert expected_message in str(except_msg.value)
