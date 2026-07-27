"""Test the UpdateTZData command on DishManager."""

import json

import pytest
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.constants import TZ_DATA_URL_ENV_VAR
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_update_tz_data_fails_when_url_not_configured(dish_manager_proxy, event_store_class):
    """UpdateTZData reports FAILED when the TZ data URL is not configured.

    The download URL is read server-side from the ``TZ_DATA_URL`` environment
    variable, which is not set in the deployment. Invoking the command over
    the Tango interface should therefore result in a FAILED long running command.
    """
    result_event_store = event_store_class()
    attr_cb_mapping = {
        "lrcFinished": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    [[_], [unique_id]] = dish_manager_proxy.UpdateTZData()

    expected_message = (
        f"UpdateTZData failed. Environment variable '{TZ_DATA_URL_ENV_VAR}' is not "
        "set or is empty; cannot determine where to download the TZ data from."
    )
    expected_result = json.dumps([int(ResultCode.FAILED), expected_message])

    result_event_store.wait_for_finished_command_result(unique_id, expected_result, timeout=10)

    remove_subscriptions(subscriptions)
