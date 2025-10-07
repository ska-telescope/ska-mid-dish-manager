"""Tests for configure band in CommandMap"."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.models.command_map import CommandMap
from ska_mid_dish_manager.models.dish_enums import Band, DishMode
from tests.unit.business_logic.data.test_data_configure_band import (
    configure_band_5b_no_subband,
    configure_band_5b_with_subband,
    configure_band_all,
    configure_band_invalid_receiver_band,
)


@pytest.mark.unit
class TestCommandMapConfigureBand:
    """Tests for configuring bands in CommandMap."""

    # pylint: disable=protected-access,attribute-defined-outside-init
    def setup_method(self):
        """Set up context."""
        self.dish_manager_cm_mock = Mock(component_state={"dishmode": DishMode.STANDBY_LP})
        self.command_map = CommandMap(self.dish_manager_cm_mock, Mock())

        self.result_calls = []
        self.status_calls = []
        self.progress_calls = []

    def teardown_method(self):
        """Tear down context."""
        return

    def my_task_callback(self, progress=None, status=None, result=None):
        if progress is not None:
            self.progress_calls.append(progress)
        if result is not None:
            self.result_calls.append(result)
        if status is not None:
            self.status_calls.append(status)

    @pytest.mark.unit
    def test_configure_band_all(self):
        """Test configure all json."""
        self.dish_manager_cm_mock.component_state["configuredband"] = Band["B2"]

        with patch.object(
            self.command_map, "_run_long_running_command", autospec=True
        ) as mock_run:
            self.command_map.configure_band(
                configure_band_all, task_callback=Mock(), task_abort_event=Mock()
            )
            assert mock_run.called

    @pytest.mark.unit
    def test_configure_band_already_configured(self):
        """Test configure when already on band json."""
        self.dish_manager_cm_mock.component_state["configuredband"] = Band["B1"]

        with patch.object(
            self.command_map, "_run_long_running_command", autospec=True
        ) as mock_run:
            self.command_map.configure_band(
                configure_band_all, task_callback=self.my_task_callback, task_abort_event=Mock()
            )
            assert self.result_calls[0] == (ResultCode.OK, "ConfigureBand completed.")
            assert self.status_calls[0] == TaskStatus.COMPLETED
            assert self.progress_calls[0] == "Already in band B1"
            assert mock_run.assert_not_called

    @pytest.mark.unit
    def test_band_5b_no_subband(self):
        """Test configure 5b without subband."""
        self.dish_manager_cm_mock.component_state["configuredband"] = Band["B1"]

        with patch.object(
            self.command_map, "_run_long_running_command", autospec=True
        ) as mock_run:
            self.command_map.configure_band(
                configure_band_5b_no_subband,
                task_callback=self.my_task_callback,
                task_abort_event=Mock(),
            )
            assert self.result_calls[0] == (ResultCode.FAILED, "Invalid sub-band in JSON.")
            assert self.status_calls[0] == TaskStatus.FAILED
            assert mock_run.assert_not_called

    @pytest.mark.unit
    def test_band_5b_with_subband(self):
        """Test configure 5b with subband."""
        self.dish_manager_cm_mock.component_state["configuredband"] = Band["B1"]

        with patch.object(
            self.command_map, "_run_long_running_command", autospec=True
        ) as mock_run:
            self.command_map.configure_band(
                configure_band_5b_with_subband,
                task_callback=self.my_task_callback,
                task_abort_event=Mock(),
            )
            assert mock_run.assert_called

    @pytest.mark.unit
    def test_invalid_receiver_band(self):
        """Test configure invalid receiver band."""
        self.dish_manager_cm_mock.component_state["configuredband"] = Band["B1"]

        with patch.object(
            self.command_map, "_run_long_running_command", autospec=True
        ) as mock_run:
            self.command_map.configure_band(
                configure_band_invalid_receiver_band,
                task_callback=self.my_task_callback,
                task_abort_event=Mock(),
            )
            assert self.result_calls[0] == (ResultCode.FAILED, "Invalid receiver band in JSON.")
            assert self.status_calls[0] == TaskStatus.FAILED
            assert mock_run.assert_not_called

    @pytest.mark.unit
    def test_with_wrong_root_key(self):
        """Test configure invalid root key."""
        cfg_band_json = """
        {
            "dish1": {
                "receiver_band": "5b",
                "sub_band": 1,
                "spfrx_processing_parameters": [
                    {
                        "dishes": ["SKA001"]
                    }
                ]
            }
        }
        """

        with patch.object(
            self.command_map, "_run_long_running_command", autospec=True
        ) as mock_run:
            self.command_map.configure_band(
                cfg_band_json, task_callback=self.my_task_callback, task_abort_event=Mock()
            )
            assert self.result_calls[0] == (
                ResultCode.FAILED,
                "Error parsing JSON.",
            )
            assert self.status_calls[0] == TaskStatus.FAILED
            assert mock_run.assert_not_called
