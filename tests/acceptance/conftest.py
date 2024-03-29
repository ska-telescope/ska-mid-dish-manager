"""Fixtures for running ska-mid-dish-manager acceptance tests"""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFOperatingMode,
)


@pytest.fixture
def undo_raise_exceptions(spf_device_proxy, spfrx_device_proxy):
    """Undo any updates to raiseCmdException in SPF and SPFRx"""
    yield
    spf_device_proxy.raiseCmdException = False
    spfrx_device_proxy.raiseCmdException = False


@pytest.fixture(autouse=True)
def setup_and_teardown(
    event_store,
    dish_manager_proxy,
    ds_device_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
):
    """Reset the tango devices to a fresh state before each test"""
    spfrx_device_proxy.ResetToDefault()
    spf_device_proxy.ResetToDefault()

    ds_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    ds_device_proxy.subscribe_event(
        "indexerPosition",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    if ds_device_proxy.operatingMode != DSOperatingMode.STOW:
        ds_device_proxy.Stow()
        assert event_store.wait_for_value(DSOperatingMode.STOW, timeout=9)

    ds_device_proxy.SetStandbyLPMode()
    assert event_store.wait_for_value(DSOperatingMode.STANDBY_LP, timeout=9)

    if ds_device_proxy.indexerPosition != IndexerPosition.B1:
        ds_device_proxy.SetIndexPosition(IndexerPosition.B1)
        assert event_store.wait_for_value(IndexerPosition.B1, timeout=9)

    spf_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    assert event_store.wait_for_value(SPFOperatingMode.STANDBY_LP, timeout=7)
    event_store.clear_queue()

    dish_manager_proxy.SyncComponentStates()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    try:
        event_store.wait_for_value(DishMode.STANDBY_LP, timeout=7)
    except RuntimeError as err:
        component_states = dish_manager_proxy.GetComponentStates()
        raise RuntimeError(f"DishManager not in STANDBY_LP:\n {component_states}\n") from err

    yield
