"""Test deactivating subservient devices."""
import pytest

from tests.utils import set_active_devices


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_deactivating_spf(
    dish_manager_proxy,
):
    """Test deactivating SPF device."""
    set_active_devices(dish_manager_proxy=dish_manager_proxy, ignore_spf=True, ignore_spfrx=False)

    # TODO: Uncomment below and complete in KAR-864 as without those changes dishMode is stuck
    # in UNKNOWN
    # result_event_store = event_store_class()
    # progress_event_store = event_store_class()

    # dish_manager_proxy.subscribe_event(
    #     "longrunningCommandResult",
    #     tango.EventType.CHANGE_EVENT,
    #     result_event_store,
    # )

    # dish_manager_proxy.subscribe_event(
    #     "longRunningCommandProgress",
    #     tango.EventType.CHANGE_EVENT,
    #     progress_event_store,
    # )

    # [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    # result_event_store.wait_for_command_id(unique_id, timeout=8)

    # expected_progress_updates = [
    #     "SetStandbyFPMode called on DS",
    #     "SPF device is disabled. SetOperateMode call ignored",
    #     "Awaiting dishMode change to STANDBY_FP",
    #     "SetStandbyFPMode completed",
    # ]

    # events = progress_event_store.wait_for_progress_update(
    #     expected_progress_updates[-1], timeout=6
    # )

    # events_string = "".join([str(event) for event in events])

    # # Check that all the expected progress messages appeared
    # # in the event store
    # for message in expected_progress_updates:
    #     assert message in events_string


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_deactivating_spfrx(
    dish_manager_proxy,
):
    """Test deactivating SPFRX device."""
    set_active_devices(dish_manager_proxy=dish_manager_proxy, ignore_spf=False, ignore_spfrx=True)

    # TODO: Uncomment below and complete in KAR-864 as without those changes dishMode is stuck
    # in UNKNOWN
    # result_event_store = event_store_class()
    # progress_event_store = event_store_class()

    # dish_manager_proxy.subscribe_event(
    #     "longrunningCommandResult",
    #     tango.EventType.CHANGE_EVENT,
    #     result_event_store,
    # )

    # dish_manager_proxy.subscribe_event(
    #     "longRunningCommandProgress",
    #     tango.EventType.CHANGE_EVENT,
    #     progress_event_store,
    # )

    # [[_], [unique_id]] = dish_manager_proxy.SetStowMode()
    # result_event_store.wait_for_command_id(unique_id, timeout=8)

    # [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    # result_event_store.wait_for_command_id(unique_id, timeout=8)

    # expected_progress_updates = [
    #     "SetStandbyLPMode called on DS",
    #     "SetStandbyLPMode called on SPF",
    #     "SPFRX device is disabled. SetStandbyMode call ignored",
    #     "Awaiting dishMode change to STANDBY_LP",
    #     "SetStandbyLPMode completed",
    # ]

    # events = progress_event_store.wait_for_progress_update(
    #     expected_progress_updates[-1], timeout=6
    # )

    # events_string = "".join([str(event) for event in events])

    # # Check that all the expected progress messages appeared
    # # in the event store
    # for message in expected_progress_updates:
    #     assert message in events_string


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_deactivating_all(
    dish_manager_proxy,
):
    """Test deactivating both SPF and SPFRx devices."""
    set_active_devices(dish_manager_proxy=dish_manager_proxy, ignore_spf=True, ignore_spfrx=True)

    # TODO: Uncomment below and complete in KAR-864 as without those changes dishMode is stuck
    # in UNKNOWN
    # result_event_store = event_store_class()
    # progress_event_store = event_store_class()

    # dish_manager_proxy.subscribe_event(
    #     "longrunningCommandResult",
    #     tango.EventType.CHANGE_EVENT,
    #     result_event_store,
    # )

    # dish_manager_proxy.subscribe_event(
    #     "longRunningCommandProgress",
    #     tango.EventType.CHANGE_EVENT,
    #     progress_event_store,
    # )

    # [[_], [unique_id]] = dish_manager_proxy.SetStowMode()
    # result_event_store.wait_for_command_id(unique_id, timeout=8)

    # [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    # result_event_store.wait_for_command_id(unique_id, timeout=8)

    # expected_progress_updates = [
    #     "SetStandbyLPMode called on DS",
    #     "SPF device is disabled. SetStandbyLPMode call ignored",
    #     "SPFRX device is disabled. SetStandbyMode call ignored",
    #     "Awaiting dishMode change to STANDBY_LP",
    #     "SetStandbyLPMode completed",
    # ]

    # events = progress_event_store.wait_for_progress_update(
    #     expected_progress_updates[-1], timeout=6
    # )

    # events_string = "".join([str(event) for event in events])

    # # Check that all the expected progress messages appeared
    # # in the event store
    # for message in expected_progress_updates:
    #     assert message in events_string
