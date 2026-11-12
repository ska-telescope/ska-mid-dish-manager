"""Test ignoring subservient devices."""

import pytest
from ska_control_model.future import ControlMode

from ska_mid_dish_manager.models.dish_enums import Band
from tests.utils import remove_subscriptions, set_ignored_devices, setup_subscriptions


@pytest.fixture
def toggle_spfrx_control_mode(dish_manager_proxy):
    """Ignore SPFRx."""
    set_ignored_devices(
        device_proxy=dish_manager_proxy,
        spf_control_mode=ControlMode.MONITOR_AND_CONTROL,
        spfrx_control_mode=ControlMode.NO_MONITOR_NO_CONTROL,
        b5dc_control_mode=ControlMode.NO_MONITOR_NO_CONTROL,
    )
    yield
    set_ignored_devices(
        device_proxy=dish_manager_proxy,
        spf_control_mode=ControlMode.MONITOR_AND_CONTROL,
        spfrx_control_mode=ControlMode.MONITOR_AND_CONTROL,
        b5dc_control_mode=ControlMode.MONITOR_AND_CONTROL,
    )


@pytest.fixture
def toggle_spf_control_mode(dish_manager_proxy):
    """Ignore SPF."""
    set_ignored_devices(
        device_proxy=dish_manager_proxy,
        spf_control_mode=ControlMode.NO_MONITOR_NO_CONTROL,
        spfrx_control_mode=ControlMode.MONITOR_AND_CONTROL,
        b5dc_control_mode=ControlMode.MONITOR_AND_CONTROL,
    )
    yield
    set_ignored_devices(
        device_proxy=dish_manager_proxy,
        spf_control_mode=ControlMode.MONITOR_AND_CONTROL,
        spfrx_control_mode=ControlMode.MONITOR_AND_CONTROL,
        b5dc_control_mode=ControlMode.MONITOR_AND_CONTROL,
    )


@pytest.fixture
def toggle_spf_control_mode_and_spfrx_b5dc(dish_manager_proxy):
    """Ignore SPF, SPFRx and B5DC."""
    set_ignored_devices(
        device_proxy=dish_manager_proxy,
        spf_control_mode=ControlMode.NO_MONITOR_NO_CONTROL,
        spfrx_control_mode=ControlMode.NO_MONITOR_NO_CONTROL,
        b5dc_control_mode=ControlMode.NO_MONITOR_NO_CONTROL,
    )
    yield
    set_ignored_devices(
        device_proxy=dish_manager_proxy,
        spf_control_mode=ControlMode.MONITOR_AND_CONTROL,
        spfrx_control_mode=ControlMode.MONITOR_AND_CONTROL,
        b5dc_control_mode=ControlMode.MONITOR_AND_CONTROL,
    )


@pytest.mark.acceptance
def test_ignoring_spf(
    monitor_tango_servers, toggle_spf_control_mode, event_store_class, dish_manager_proxy
):
    """Test ignoring SPF device."""
    result_event_store = event_store_class()
    status_event_store = event_store_class()
    main_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredband": main_event_store,
        "lrcFinished": result_event_store,
        "Status": status_event_store,
    }

    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ConfigureBand1(True)
    main_event_store.wait_for_value(Band.B1, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "Fanned out commands: DS.SetStandbyMode, DS.SetPowerMode",
        "Awaiting dishmode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_ignoring_spfrx(
    monitor_tango_servers, toggle_spfrx_control_mode, event_store_class, dish_manager_proxy
):
    """Test ignoring SPFRX device."""
    result_event_store = event_store_class()
    status_event_store = event_store_class()
    dish_mode_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": dish_mode_event_store,
        "lrcFinished": result_event_store,
        "Status": status_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(True)
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "Fanned out commands: DS.SetIndexPosition",
        "Awaiting configuredband change to B2",
        "DS.SetIndexPosition completed",
        "ConfigureBand2 complete. Triggering on success action.",
        "Fanned out commands: SPF.SetOperateMode, DS.SetPointMode",
        "Awaiting dishmode change to OPERATE",
        "SetOperateMode completed",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_ignoring_all(
    monitor_tango_servers,
    toggle_spf_control_mode_and_spfrx_b5dc,
    event_store_class,
    dish_manager_proxy,
):
    """Test ignoring both SPF and SPFRx devices."""
    result_event_store = event_store_class()
    status_event_store = event_store_class()
    dish_mode_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": dish_mode_event_store,
        "lrcFinished": result_event_store,
        "Status": status_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "Fanned out commands: DS.SetStandbyMode",
        "Awaiting dishmode change to STANDBY_LP",
        "SetStandbyLPMode completed",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)
