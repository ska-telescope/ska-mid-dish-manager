"""Unit tests checking DishManager behaviour."""
# pylint: disable=protected-access
# pylint: disable=attribute-defined-outside-init


import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import tango
from ska_control_model import CommunicationStatus, TaskStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango.DeviceProxy")
@patch("ska_mid_dish_manager.component_managers.device_monitor.tango.DeviceProxy")
def test_dish_manager_behaviour(patched_dp, patched_monitor_dp, event_store):
    """Test that SetStandbyFPMode does 3 result updates. DishManager, DS, SPF"""

    patched_monitor_dp.return_value = MagicMock()

    patched_dp.return_value = MagicMock()
    patched_dp.command_inout = MagicMock()
    patched_dp.command_inout.return_value = (
        TaskStatus.COMPLETED,
        "Task Done",
    )
    tango_context = DeviceTestContext(DishManager)
    tango_context.start()

    device_proxy = tango_context.device
    class_instance = DishManager.instances.get(device_proxy.name())
    ds_cm = class_instance.component_manager.sub_component_managers["DS"]
    spf_cm = class_instance.component_manager.sub_component_managers["SPF"]
    spfrx_cm = class_instance.component_manager.sub_component_managers["SPFRX"]
    dish_manager_cm = class_instance.component_manager

    spf_cm.write_attribute_value = MagicMock()

    ds_cm.update_state_from_monitored_attributes = MagicMock()
    spf_cm.update_state_from_monitored_attributes = MagicMock()
    spfrx_cm.update_state_from_monitored_attributes = MagicMock()

    # trigger transition to StandbyLP mode to
    # mimic automatic transition after startup
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

    ds_cm._update_communication_state(CommunicationStatus.ESTABLISHED)
    spf_cm._update_communication_state(CommunicationStatus.ESTABLISHED)
    spfrx_cm._update_communication_state(CommunicationStatus.ESTABLISHED)

    sub_id = device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    assert event_store.wait_for_value(DishMode.STANDBY_LP, timeout=8)
    # unsubscribe to stop listening for dishMode events
    device_proxy.unsubscribe_event(sub_id)
    # Clear out the queue to make sure we dont keep previous events
    event_store.clear_queue()

    # band should be configured to call command on SPFRx device
    # and have it propagated to the long running command result
    dish_manager_cm._update_component_state(configuredband=Band.B2)
    dish_manager_cm._update_component_state(configuredband=Band.B3)

    device_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    device_proxy.SetStandbyFPMode()

    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)

    # Sample events:
    # ('longRunningCommandResult', ('', ''))

    # ('longrunningcommandresult',
    # ('1659015778.0797186_172264627776495_DS_SetStandbyFPMode',
    #  '"result"'))

    # ('longrunningcommandresult',
    # ('1659015778.0823436_222123736715640_SPF_SetOperateMode',
    # '"result"'))

    # ('longrunningcommandresult',
    # ('1659015778.0741146_217952885485963_SetStandbyFPMode',
    # '"{\\"DS\\": \\"16598.0786_1795_DS_SetStandbyFPMode\\",
    # \\"SPF\\": \\"1659778.0826_2215640_SPF_SetOperateMode\\",
    # \\"SPFRX\\": \\"16578.0925_1954609_SPFRX_CaptureData\\"}"'))

    # ('longrunningcommandresult',
    # ('16590178.0985_1954609_SPFRX_CaptureData', '"result"'))

    events = event_store.wait_for_n_events(4)
    event_values = event_store.get_data_from_events(events)
    event_ids = [
        event_value[1][0] for event_value in event_values if event_value[1] and event_value[1][0]
    ]
    # Sort via command creation timestamp
    event_ids.sort(key=lambda x: datetime.fromtimestamp((float(x.split("_")[0]))))
    assert sorted([event_id.split("_")[-1] for event_id in event_ids]) == [
        "SetOperateMode",
        "SetStandbyFPMode",
        "SetStandbyFPMode",
    ]


def test_component_states():
    """Test that GetComponentStates for 3 devices are returned"""
    tango_context = DeviceTestContext(DishManager)
    tango_context.start()
    assert len(json.loads(tango_context.device.GetComponentStates())) == 3
    tango_context.stop()
