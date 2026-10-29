"""Test AP Manager subcomponent manager method overrides."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model.future import ControlMode

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import TrackInterpolationMode


@pytest.mark.unit
@pytest.mark.forked
def test_ap_manager_cm_intercepts_unwritable_ds_attrs(
    dish_manager_resources_with_ap_manager,
    caplog,
):
    """Test that the AP subcomponent manager intercepts unwritable DS Manager attributes."""
    _, dish_manager_cm = dish_manager_resources_with_ap_manager
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    # Remove the mock the fixture configures on the attr write function of the
    # ap subcomponent manager
    del ds_cm.write_attribute_value

    unwritable_attr_name = "trackInterpolationMode"

    ds_cm.write_attribute_value(unwritable_attr_name, TrackInterpolationMode.SPLINE)

    assert (
        f"Attribute [{unwritable_attr_name}] cannot be written while monitoring and controlling "
        "an AP Manager instance."
    ) in caplog.text


@pytest.mark.unit
@pytest.mark.forked
def test_ap_manager_stop_communicating(
    dish_manager_resources_with_ap_manager,
):
    """AP stop communicating requests NO_MONITOR_NO_CONTROL before Tango dev cm stop_comms."""
    _, dish_manager_cm = dish_manager_resources_with_ap_manager
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    # Hold all commands called over the test duration
    operations = []

    ds_cm._write_attribute_value = Mock(
        side_effect=lambda attribute_name, value: operations.append(
            ("write", attribute_name, value)
        )
    )

    with patch.object(
        TangoDeviceComponentManager,
        "stop_communicating",
        autospec=True,
        side_effect=lambda component_manager: operations.append(("tango_dev_cm_stop",)),
    ) as tango_dev_cm_stop_communicating:
        ds_cm.stop_communicating()

    assert operations == [
        ("write", "controlMode", ControlMode.NO_MONITOR_NO_CONTROL),
        ("tango_dev_cm_stop",),
    ]
    tango_dev_cm_stop_communicating.assert_called_once_with(ds_cm)
