# flake8: noqa: E501
import pytest
import tango


# Skampi deploys 4 sets of dish devices, testing 1 for now
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.parametrize("domain", ["0001"])
@pytest.mark.parametrize(
    "family_member",
    ["elt/master", "lmc/ds_simulator", "spf/simulator", "spfrx/simulator"],
)
def test_lmc_devices_available_in_skampi(domain, family_member):
    """Test that dish lmc devices are available in skampi and responsive"""
    tango_device_proxy = tango.DeviceProxy(f"mid_d{domain}/{family_member}")
    assert isinstance(tango_device_proxy.ping(), int)
    # Just make sure the device responds
    assert tango_device_proxy.State() in tango.DevState.values.values()


@pytest.mark.parametrize("domain", ["0001"])
@pytest.mark.parametrize(
    "family_member",
    ["elt/master", "lmc/ds_simulator", "spf/simulator", "spfrx/simulator"],
)
def test_lmc_devices_available_in_local_deployment(domain, family_member):
    """Test that dish lmc devices are available in local repo deployment and responsive"""
    tango_device_proxy = tango.DeviceProxy(f"mid_d{domain}/{family_member}")
    assert isinstance(tango_device_proxy.ping(), int)
    # Just make sure the device responds
    assert tango_device_proxy.State() in tango.DevState.values.values()
