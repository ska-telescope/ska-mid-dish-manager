"""CapabilityState checks"""
# pylint: disable=protected-access,use-dict-literal,too-many-arguments
# pylint: disable=attribute-defined-outside-init,missing-function-docstring
from unittest.mock import patch

import mock
import pytest
import tango
from ska_control_model import CommunicationStatus
from tango import AttrQuality
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


@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=None),
            dict(dishmode=None),
            dict(b5bcapabilitystate=SPFRxCapabilityStates.UNAVAILABLE),
            dict(b5bcapabilitystate=SPFCapabilityStates.UNAVAILABLE),
            CapabilityStates.UNAVAILABLE,
        ),
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=None),
            dict(dishmode=None),
            None,
            dict(b5bcapabilitystate=SPFCapabilityStates.UNAVAILABLE),
            CapabilityStates.UNAVAILABLE,
        ),
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=None),
            dict(dishmode=None),
            dict(b5bcapabilitystate=SPFRxCapabilityStates.UNAVAILABLE),
            None,
            CapabilityStates.UNAVAILABLE,
        ),
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=None),
            dict(dishmode=None),
            None,
            None,
            CapabilityStates.UNAVAILABLE,
        ),
    ],
)
def test_capability_state_rules_unavailable(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b5b",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.STANDBY_LP),
            dict(b5bcapabilitystate=SPFRxCapabilityStates.STANDBY),
            dict(b5bcapabilitystate=SPFCapabilityStates.STANDBY),
            CapabilityStates.STANDBY,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.STANDBY_LP),
            None,
            dict(b5bcapabilitystate=SPFCapabilityStates.STANDBY),
            CapabilityStates.STANDBY,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.STANDBY_LP),
            dict(b5bcapabilitystate=SPFRxCapabilityStates.STANDBY),
            None,
            CapabilityStates.STANDBY,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.STANDBY_LP),
            None,
            None,
            CapabilityStates.STANDBY,
        ),
    ],
)
def test_capability_state_rules_standby(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b5b",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.CONFIG),
            dict(b4capabilitystate=SPFRxCapabilityStates.CONFIGURE),
            dict(b4capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED),
            CapabilityStates.CONFIGURING,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.CONFIG),
            None,
            dict(b4capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED),
            CapabilityStates.CONFIGURING,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.CONFIG),
            dict(b4capabilitystate=SPFRxCapabilityStates.CONFIGURE),
            None,
            CapabilityStates.CONFIGURING,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.CONFIG),
            None,
            None,
            CapabilityStates.CONFIGURING,
        ),
    ],
)
def test_capability_state_rules_configuring(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b4",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.B1),
            dict(dishmode=None),
            dict(b3capabilitystate=SPFRxCapabilityStates.OPERATE),
            dict(b3capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED),
            CapabilityStates.OPERATE_DEGRADED,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.B1),
            dict(dishmode=None),
            None,
            dict(b3capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED),
            CapabilityStates.OPERATE_DEGRADED,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.B1),
            dict(dishmode=None),
            dict(b3capabilitystate=SPFRxCapabilityStates.OPERATE),
            None,
            CapabilityStates.OPERATE_DEGRADED,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.B1),
            dict(dishmode=None),
            None,
            None,
            CapabilityStates.OPERATE_DEGRADED,
        ),
    ],
)
def test_capability_state_rules_degraded(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b3",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=None, indexerposition=IndexerPosition.MOVING),
            dict(dishmode=DishMode.STOW),
            dict(b1capabilitystate=SPFRxCapabilityStates.OPERATE),
            dict(b1capabilitystate=SPFCapabilityStates.OPERATE_FULL),
            CapabilityStates.OPERATE_FULL,
        ),
        (
            dict(operatingmode=None, indexerposition=IndexerPosition.MOVING),
            dict(dishmode=DishMode.STOW),
            None,
            dict(b1capabilitystate=SPFCapabilityStates.OPERATE_FULL),
            CapabilityStates.OPERATE_FULL,
        ),
        (
            dict(operatingmode=None, indexerposition=IndexerPosition.MOVING),
            dict(dishmode=DishMode.STOW),
            dict(b1capabilitystate=SPFRxCapabilityStates.OPERATE),
            None,
            CapabilityStates.OPERATE_FULL,
        ),
        (
            dict(operatingmode=None, indexerposition=IndexerPosition.MOVING),
            dict(dishmode=DishMode.STOW),
            None,
            None,
            CapabilityStates.OPERATE_FULL,
        ),
    ],
)
def test_capability_state_rules_operate(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b1",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=None),
            dict(b1capabilitystate=None),
            dict(b1capabilitystate=None),
            CapabilityStates.UNKNOWN,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=None),
            None,
            dict(b1capabilitystate=None),
            CapabilityStates.UNKNOWN,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=None),
            dict(b1capabilitystate=None),
            None,
            CapabilityStates.UNKNOWN,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=None),
            None,
            None,
            CapabilityStates.UNKNOWN,
        ),
    ],
)
def test_capability_state_rules_unknown(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b1",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
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
        self.dish_manager_cm._update_component_state(
            dishmode=[DishMode.STANDBY_LP, AttrQuality.ATTR_VALID]
        )
        self.spfrx_cm._update_component_state(
            b1capabilitystate=[SPFRxCapabilityStates.STANDBY, AttrQuality.ATTR_VALID]
        )
        self.spf_cm._update_component_state(
            b1capabilitystate=[SPFCapabilityStates.STANDBY, AttrQuality.ATTR_VALID]
        )

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
        self.ds_cm._update_component_state(
            operatingmode=[DSOperatingMode.STARTUP, AttrQuality.ATTR_VALID]
        )
        self.spf_cm._update_component_state(
            b2capabilitystate=[SPFCapabilityStates.UNAVAILABLE, AttrQuality.ATTR_VALID]
        )
        self.spfrx_cm._update_component_state(
            b2capabilitystate=[SPFRxCapabilityStates.UNAVAILABLE, AttrQuality.ATTR_VALID]
        )

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
        self.dish_manager_cm._update_component_state(
            dishmode=[DishMode.STOW, AttrQuality.ATTR_VALID]
        )
        self.spf_cm._update_component_state(
            b3capabilitystate=[SPFCapabilityStates.OPERATE_FULL, AttrQuality.ATTR_VALID]
        )
        self.spfrx_cm._update_component_state(
            b3capabilitystate=[SPFRxCapabilityStates.OPERATE, AttrQuality.ATTR_VALID]
        )

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
        self.dish_manager_cm._update_component_state(
            dishmode=[DishMode.CONFIG, AttrQuality.ATTR_VALID]
        )
        self.ds_cm._update_component_state(
            indexerposition=[IndexerPosition.MOVING, AttrQuality.ATTR_VALID]
        )
        self.spf_cm._update_component_state(
            b4capabilitystate=[SPFCapabilityStates.OPERATE_DEGRADED, AttrQuality.ATTR_VALID]
        )
        self.spfrx_cm._update_component_state(
            b4capabilitystate=[SPFRxCapabilityStates.CONFIGURE, AttrQuality.ATTR_VALID]
        )

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
            indexerposition=[IndexerPosition.B1, AttrQuality.ATTR_VALID],
            operatingmode=[DSOperatingMode.STOW, AttrQuality.ATTR_VALID],
        )
        self.spf_cm._update_component_state(
            b5acapabilitystate=[SPFCapabilityStates.OPERATE_DEGRADED, AttrQuality.ATTR_VALID]
        )
        self.spfrx_cm._update_component_state(
            b5acapabilitystate=[SPFRxCapabilityStates.OPERATE, AttrQuality.ATTR_VALID]
        )

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
        self.dish_manager_cm._update_component_state(
            dishmode=[DishMode.CONFIG, AttrQuality.ATTR_VALID]
        )
        self.spf_cm._update_component_state(
            b2capabilitystate=[SPFCapabilityStates.OPERATE_FULL, AttrQuality.ATTR_VALID]
        )
        self.spfrx_cm._update_component_state(
            b2capabilitystate=[SPFRxCapabilityStates.CONFIGURE, AttrQuality.ATTR_VALID]
        )

        event_store.wait_for_value(CapabilityStates.CONFIGURING, timeout=7)
