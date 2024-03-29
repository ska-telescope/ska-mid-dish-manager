"""CapabilityState checks"""
# pylint: disable=protected-access
# pylint: disable=attribute-defined-outside-init
from unittest.mock import patch

import mock
import pytest
import tango
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    CapabilityStates,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFCapabilityStates,
    SPFRxCapabilityStates,
)
from ska_mid_dish_manager.models.dish_state_transition import StateTransition
from tests.utils import EventStore


# pylint: disable=redefined-outer-name
@pytest.fixture(scope="module")
def state_transition():
    """Instance of StateTransition"""
    return StateTransition()


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_unavailable(state_transition):
    """Test the capabilityState rules"""

    ds_component_state = {
        "operatingmode": DSOperatingMode.STARTUP,
        "indexerposition": None,
    }
    spf_component_state = {"b5bcapabilitystate": SPFCapabilityStates.UNAVAILABLE}
    spfrx_component_state = {"b5bcapabilitystate": SPFRxCapabilityStates.UNAVAILABLE}
    dish_manager_component_state = {"dishmode": None}

    assert (
        state_transition.compute_capability_state(
            "b5b",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.UNAVAILABLE
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_standby(state_transition):
    """Test the capabilityState rules"""

    ds_component_state = {"operatingmode": None, "indexerposition": None}
    spf_component_state = {"b5acapabilitystate": SPFCapabilityStates.STANDBY}
    spfrx_component_state = {"b5acapabilitystate": SPFRxCapabilityStates.STANDBY}
    dish_manager_component_state = {"dishmode": DishMode.STANDBY_LP}

    assert (
        state_transition.compute_capability_state(
            "b5a",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.STANDBY
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_configuring(state_transition):
    """Test the capabilityState rules"""

    ds_component_state = {"operatingmode": None, "indexerposition": None}
    spf_component_state = {"b4capabilitystate": SPFCapabilityStates.OPERATE_DEGRADED}
    spfrx_component_state = {"b4capabilitystate": SPFRxCapabilityStates.CONFIGURE}
    dish_manager_component_state = {"dishmode": DishMode.CONFIG}

    assert (
        state_transition.compute_capability_state(
            "b4",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.CONFIGURING
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_degraded(state_transition):
    """Test the capabilityState rules"""

    ds_component_state = {
        "indexerposition": IndexerPosition.B1,
        "operatingmode": DSOperatingMode.STOW,
    }
    spf_component_state = {"b3capabilitystate": SPFCapabilityStates.OPERATE_DEGRADED}
    spfrx_component_state = {"b3capabilitystate": SPFRxCapabilityStates.OPERATE}
    dish_manager_component_state = {"dishmode": None}

    assert (
        state_transition.compute_capability_state(
            "b3",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.OPERATE_DEGRADED
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_operate(state_transition):
    """Test the capabilityState rules"""

    ds_component_state = {
        "indexerposition": IndexerPosition.MOVING,
        "operatingmode": None,
    }
    spf_component_state = {"b1capabilitystate": SPFCapabilityStates.OPERATE_FULL}
    spfrx_component_state = {"b1capabilitystate": SPFRxCapabilityStates.OPERATE}
    dish_manager_component_state = {"dishmode": DishMode.STOW}

    assert (
        state_transition.compute_capability_state(
            "b1",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.OPERATE_FULL
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_unknown(state_transition):
    """Test the capabilityState rules"""

    ds_component_state = {"operatingmode": None, "indexerposition": None}
    spf_component_state = {"b2capabilitystate": None}
    spfrx_component_state = {"b2capabilitystate": None}
    dish_manager_component_state = {"dishmode": None}

    assert (
        state_transition.compute_capability_state(
            "b2",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.UNKNOWN
    )


@pytest.mark.unit
@pytest.mark.forked
class TestCapabilityStates:
    """Tests for CapabilityStates"""

    def setup_method(self):
        """Set up context"""
        with patch(
            (
                "ska_mid_dish_manager.component_managers.tango_device_cm."
                "TangoDeviceComponentManager.start_communicating"
            )
        ):
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()

            self.device_proxy = self.tango_context.device
            class_instance = DishManager.instances.get(self.device_proxy.name())
            self.ds_cm = class_instance.component_manager.sub_component_managers["DS"]
            self.spf_cm = class_instance.component_manager.sub_component_managers["SPF"]
            self.spfrx_cm = class_instance.component_manager.sub_component_managers["SPFRX"]

            for com_man in [self.ds_cm, self.spf_cm, self.spfrx_cm]:
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

            self.spf_cm.write_attribute_value = mock.MagicMock()

            self.dish_manager_cm = class_instance.component_manager

            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

            event_store = EventStore()
            for conn_attr in ["spfConnectionState", "spfrxConnectionState", "dsConnectionState"]:
                self.device_proxy.subscribe_event(
                    conn_attr,
                    tango.EventType.CHANGE_EVENT,
                    event_store,
                )
                event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=7)

    def teardown_method(self):
        """Tear down context"""
        return

    def test_capabilitystate_available(self):
        """Test cap state present"""
        attributes = self.device_proxy.get_attribute_list()
        for capability in ("b1", "b2", "b3", "b4", "b5a", "b5b"):
            state_name = f"{capability}CapabilityState"
            assert state_name in attributes
            assert getattr(self.device_proxy, state_name, None) == CapabilityStates.UNKNOWN

    def test_b1capabilitystate_change(
        self,
        event_store,
    ):
        """Test b1CapabilityState"""
        self.device_proxy.subscribe_event(
            "b1CapabilityState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Mimic capabilitystatechanges on sub devices
        self.dish_manager_cm._update_component_state(dishmode=DishMode.STANDBY_LP)
        self.spfrx_cm._update_component_state(b1capabilitystate=SPFRxCapabilityStates.STANDBY)
        self.spf_cm._update_component_state(b1capabilitystate=SPFCapabilityStates.STANDBY)

        event_store.wait_for_value(CapabilityStates.STANDBY, timeout=7)

    def test_b2capabilitystate_change(
        self,
        event_store,
    ):
        """Test b2CapabilityState"""
        self.device_proxy.subscribe_event(
            "b2CapabilityState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Mimic capabilitystatechanges on sub devices
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STARTUP)
        self.spf_cm._update_component_state(b2capabilitystate=SPFCapabilityStates.UNAVAILABLE)
        self.spfrx_cm._update_component_state(b2capabilitystate=SPFRxCapabilityStates.UNAVAILABLE)

        event_store.wait_for_value(CapabilityStates.UNAVAILABLE, timeout=7)

    def test_b3capabilitystate_change(
        self,
        event_store,
    ):
        """Test b3CapabilityState"""
        self.device_proxy.subscribe_event(
            "b3CapabilityState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Mimic capabilitystatechanges on sub devices
        self.dish_manager_cm._update_component_state(dishmode=DishMode.STOW)
        self.spf_cm._update_component_state(b3capabilitystate=SPFCapabilityStates.OPERATE_FULL)
        self.spfrx_cm._update_component_state(b3capabilitystate=SPFRxCapabilityStates.OPERATE)

        event_store.wait_for_value(CapabilityStates.OPERATE_FULL, timeout=7)

    def test_b4capabilitystate_change(
        self,
        event_store,
    ):
        """Test b4CapabilityState"""
        self.device_proxy.subscribe_event(
            "b4CapabilityState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Mimic capabilitystatechanges on sub devices
        self.dish_manager_cm._update_component_state(dishmode=DishMode.CONFIG)
        self.ds_cm._update_component_state(indexerposition=IndexerPosition.MOVING)
        self.spf_cm._update_component_state(b4capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED)
        self.spfrx_cm._update_component_state(b4capabilitystate=SPFRxCapabilityStates.CONFIGURE)

        event_store.wait_for_value(CapabilityStates.CONFIGURING, timeout=7)

    def test_b5acapabilitystate_change(
        self,
        event_store,
    ):
        """Test b5aCapabilityState"""
        self.device_proxy.subscribe_event(
            "b5aCapabilityState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Mimic capabilitystatechanges on sub devices
        self.ds_cm._update_component_state(
            indexerposition=IndexerPosition.B1,
            operatingmode=DSOperatingMode.STOW,
        )
        self.spf_cm._update_component_state(
            b5acapabilitystate=SPFCapabilityStates.OPERATE_DEGRADED
        )
        self.spfrx_cm._update_component_state(b5acapabilitystate=SPFRxCapabilityStates.OPERATE)

        event_store.wait_for_value(CapabilityStates.OPERATE_DEGRADED, timeout=7)

    def test_b2capabilitystate_configuring_change(
        self,
        event_store,
    ):
        """Test Configuring"""
        self.device_proxy.subscribe_event(
            "b2CapabilityState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Mimic capabilitystatechanges on sub devices
        self.dish_manager_cm._update_component_state(dishmode=DishMode.CONFIG)
        self.spf_cm._update_component_state(b2capabilitystate=SPFCapabilityStates.OPERATE_FULL)
        self.spfrx_cm._update_component_state(b2capabilitystate=SPFRxCapabilityStates.CONFIGURE)

        event_store.wait_for_value(CapabilityStates.CONFIGURING, timeout=7)
