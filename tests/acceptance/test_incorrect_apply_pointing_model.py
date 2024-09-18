"""Test Apply Pointing Model Command."""

from typing import Any

import numpy as np
import pytest
import tango
from ska_control_model import ResultCode


@pytest.mark.acceptance
@pytest.mark.forked
def test_incorrect_apply_pointing_model(
    dish_manager_proxy: tango.DeviceProxy,
    ds_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test ApplyPointingModel command with incorrect JSON inputs."""
    incorrect_antenna = """{
    "interface": "https://schema.skao.int/ska-mid-dish-gpm/1.2",
    "antenna": "SKA053",
    "band": "Band_2",
    "coefficients": {
        "IA": {
            "value": -491.05237180985154
        },
        "CA": {
            "value": -46.49438759990891
        },
        "NPAE": {
            "value": -0.20043883924247693
        },
        "AN": {
            "value": 6.303488540553789
        },
        "AN0": {
            "value": 0
        },
        "AW": {
            "value": 16.015694895168707
        },
        "AW0": {
            "value": 0
        },
        "ACEC": {
            "value": 11.97440290133107
        },
        "ACES": {
            "value": -3.7385420287177227
        },
        "ABA": {
            "value": 0
        },
        "ABphi": {
            "value": 0
        },
        "IE": {
            "value": 1655.986889730121
        },
        "ECEC": {
            "value": -145.2842284526637
        },
        "ECES": {
            "value": -26.760848137365375
        },
        "HECE4": {
            "value": 0
        },
        "HESE4": {
            "value": 0
        },
        "HECE8": {
            "value": 0
        },
        "HESE8": {
            "value": 0
        }
    }
    }"""

    incorrect_number = """{
    "interface": "https://schema.skao.int/ska-mid-dish-gpm/1.2",
    "antenna": "SKA001",
    "band": "Band_2",
    "coefficients": {
        "IA": {
            "value": -491.05237180985154
        },
        "CA": {
            "value": -46.49438759990891
        },
        "NPAE": {
            "value": -0.20043883924247693
        },
        "AN": {
            "value": 6.303488540553789
        },
        "AN0": {
            "value": 0
        },
        "AW": {
            "value": 16.015694895168707
        },
        "AW0": {
            "value": 0
        },
        "ACEC": {
            "value": 11.97440290133107
        },
        "ACES": {
            "value": -3.7385420287177227
        },
        "ABA": {
            "value": 0
        },
        "ABphi": {
            "value": 0
        },
        "IE": {
            "value": 1655.986889730121
        },
        "ECEC": {
            "value": -145.2842284526637
        },
        "ECES": {
            "value": -26.760848137365375
        },
        "HECE4": {
            "value": 0
        }
    }
    }"""

    incorrect_band = """{
    "interface": "https://schema.skao.int/ska-mid-dish-gpm/1.2",
    "antenna": "SKA001",
    "band": "Band_6",
    "coefficients": {
        "IA": {
            "value": -491.05237180985154
        },
        "CA": {
            "value": -46.49438759990891
        },
        "NPAE": {
            "value": -0.20043883924247693
        },
        "AN": {
            "value": 6.303488540553789
        },
        "AN0": {
            "value": 0
        },
        "AW": {
            "value": 16.015694895168707
        },
        "AW0": {
            "value": 0
        },
        "ACEC": {
            "value": 11.97440290133107
        },
        "ACES": {
            "value": -3.7385420287177227
        },
        "ABA": {
            "value": 0
        },
        "ABphi": {
            "value": 0
        },
        "IE": {
            "value": 1655.986889730121
        },
        "ECEC": {
            "value": -145.2842284526637
        },
        "ECES": {
            "value": -26.760848137365375
        },
        "HECE4": {
            "value": 0
        },
        "HESE4": {
            "value": 0
        },
        "HECE8": {
            "value": 0
        },
        "HESE8": {
            "value": 0
        }
    }
    }"""

    values = [
        -4.91052372e02,
        -4.64943876e01,
        -2.00438839e-01,
        6.30348854e00,
        0.00000000e00,
        1.60156949e01,
        0.00000000e00,
        1.19744029e01,
        -3.73854203e00,
        0.00000000e00,
        0.00000000e00,
        1.65598689e03,
        -1.45284228e02,
        -2.67608481e01,
        0.00000000e00,
        0.00000000e00,
        0.00000000e00,
        0.00000000e00,
    ]

    # Incorrect Antenna
    result_code, antenna_resp = dish_manager_proxy.ApplyPointingModel(incorrect_antenna)
    ds_band_pointing_model_params = ds_device_proxy.read_attribute(
        "band2PointingModelParams"
    ).value
    antenna_error_resp = (
        "Command rejected. The Dish id SKA001 and the Antenna's value SKA053 are not equal."
    )
    assert not np.array_equal(values, ds_band_pointing_model_params)
    assert antenna_error_resp == antenna_resp[0]
    assert result_code == ResultCode.REJECTED

    # Incorrect Band
    result_code, band_resp = dish_manager_proxy.ApplyPointingModel(incorrect_band)
    ds_band_pointing_model_params = ds_device_proxy.read_attribute(
        "band2PointingModelParams"
    ).value
    band_error_resp = "Unsupported Band: b6"
    assert not np.array_equal(values, ds_band_pointing_model_params)
    assert band_error_resp == band_resp[0]
    assert result_code == ResultCode.REJECTED

    # Incorrect Number of Coefficients
    result_code, coefficients_resp = dish_manager_proxy.ApplyPointingModel(incorrect_number)
    ds_band_pointing_model_params = ds_device_proxy.read_attribute(
        "band2PointingModelParams"
    ).value
    expected_coefficients = [
        "IA",
        "CA",
        "NPAE",
        "AN",
        "AN0",
        "AW",
        "AW0",
        "ACEC",
        "ACES",
        "ABA",
        "ABphi",
        "IE",
        "ECEC",
        "ECES",
        "HECE4",
    ]
    coeff_error_resp = (
        f"Coefficients are missing or not in the correct order. "
        f"The coefficients found in the JSON object were {expected_coefficients}"
    )
    assert not np.array_equal(values, ds_band_pointing_model_params)
    assert coeff_error_resp == coefficients_resp[0]
    assert result_code == ResultCode.REJECTED
