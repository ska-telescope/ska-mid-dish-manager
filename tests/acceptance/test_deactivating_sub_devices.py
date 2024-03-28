"""Test deactivating subservient devices."""
import pytest
import tango

from tests.utils import set_active_devices_and_sync_component_states


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_deactivating_spf(
    event_store_class,
    dish_manager_proxy,
):
    """Test deactivating SPF device."""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    set_active_devices_and_sync_component_states(
        dish_manager_proxy=dish_manager_proxy, ignore_spf=True, ignore_spfrx=False
    )

    dish_manager_proxy.SetStandbyFPMode()

    # TODO: Command calls will only complete once transition rules have been updated in KAR-864
    # result_event_store.wait_for_command_id(unique_id, timeout=8)

    # TODO: "Completed" progress update will only come through after KAR-864
    expected_progress_updates = [
        "SetStandbyFPMode called on DS",
        "SPF device is disabled. SetOperateMode call ignored",
        "Awaiting dishMode change to STANDBY_FP",
        # "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    print(events)

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_deactivating_spfrx(
    event_store_class,
    dish_manager_proxy,
):
    """Test deactivating SPFRX device."""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    set_active_devices_and_sync_component_states(
        dish_manager_proxy=dish_manager_proxy, ignore_spf=False, ignore_spfrx=True
    )

    [[_], [unique_id]] = dish_manager_proxy.SetStowMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    # TODO: Command calls will only complete once transition rules have been updated in KAR-864
    # result_event_store.wait_for_command_id(unique_id, timeout=8)

    # TODO: "Completed" progress update will only come through after KAR-864
    expected_progress_updates = [
        "SetStandbyLPMode called on DS",
        "SetStandbyLPMode called on SPF",
        "SPFRX device is disabled. SetStandbyMode call ignored",
        "Awaiting dishMode change to STANDBY_LP",
        # "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    print(events)

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_deactivating_all(
    event_store_class,
    dish_manager_proxy,
):
    """Test deactivating both SPF and SPFRx devices."""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    set_active_devices_and_sync_component_states(
        dish_manager_proxy=dish_manager_proxy, ignore_spf=True, ignore_spfrx=True
    )

    [[_], [unique_id]] = dish_manager_proxy.SetStowMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    # TODO: Command calls will only complete once transition rules have been updated in KAR-864
    # result_event_store.wait_for_command_id(unique_id, timeout=8)

    # TODO: "Completed" progress update will only come through after KAR-864
    expected_progress_updates = [
        "SetStandbyLPMode called on DS",
        "SPF device is disabled. SetStandbyLPMode call ignored",
        "SPFRX device is disabled. SetStandbyMode call ignored",
        "Awaiting dishMode change to STANDBY_LP",
        # "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    print(events)

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
