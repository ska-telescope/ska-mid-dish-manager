"""Test AbortCommands"""
import pytest
import tango


@pytest.fixture(autouse=True, scope="module")
def turn_on_spf_attribute_update(request):
    """Ensure that attribute updates on spf is restored"""

    def toggle_attribute_update():
        spf_device = tango.DeviceProxy("mid_d0001/spf/simulator")
        spf_device.skipAttributeUpdates = False

    request.addfinalizer(toggle_attribute_update)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
@pytest.mark.skip("ABORT COMMANDS STOP MONITORING")
def test_abort_commands(event_store):
    """Test AbortCommands aborts the executing long running command"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")

    # Set a flag on SPF to skip attribute updates
    spf_device = tango.DeviceProxy("mid_d0001/spf/simulator")
    spf_device.skipAttributeUpdates = True

    for attr in [
        "longRunningCommandStatus",
        "longRunningCommandResult",
        "longRunningCommandProgress",
    ]:
        dish_manager.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

    # Transition to FP mode
    [[_], [unique_id]] = dish_manager.SetStandbyFPMode()
    event_store.wait_for_value((f"{unique_id}", "Awaiting dishMode change to STANDBY_FP"))
    dish_manager.AbortCommands()

    # TODO record in the progress attribute
    # that Abort was called on DS and SPF

    # confirm dishmanager aborted the request on lrcResult
    event_store.wait_for_value((f"{unique_id}", "SetStandbyFPMode Aborted"))
