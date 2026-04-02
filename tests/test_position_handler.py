"""Tests for PositionHandler extracted methods."""

from unittest.mock import MagicMock, patch

import pytest

from core.constants import (
    AIRCRAFT_ALTITUDE_THRESHOLD,
    AIRCRAFT_GROUND_SPEED_THRESHOLD,
    DEFAULT_LOCATION,
)
from handlers.position_handler import PositionHandler


@pytest.fixture
def position_handler():
    """Create a PositionHandler with mocked dependencies."""
    with patch("handlers.base_handler.MessageSender") as mock_ms, patch(
        "handlers.base_handler.SQLiteHelper"
    ) as mock_db:
        mock_ms.get_instance.return_value = MagicMock()
        mock_db.get_instance.return_value = MagicMock()
        handler = PositionHandler()
        handler.location_utils = MagicMock()
        handler.location_utils.find_location_by_coordinates.return_value = "Akron, OH"
        return handler


class TestExtractPositionData:
    def test_full_position(self, position_handler):
        position = {
            "latitude": 41.5,
            "longitude": -81.5,
            "altitude": 250,
            "groundSpeed": 5,
            "satsInView": 8,
            "time": 1700000000,
        }
        data = position_handler._extract_position_data(position)
        assert data["altitude"] == 250
        assert data["ground_speed"] == 5
        assert data["location"] == "Akron, OH"
        assert data["is_fast_moving"] is False
        assert data["is_high_altitude"] is False
        assert data["satsInView"] == 8
        assert "time_str" in data

    def test_aircraft_detection_thresholds(self, position_handler):
        position = {
            "latitude": 41.5,
            "longitude": -81.5,
            "altitude": AIRCRAFT_ALTITUDE_THRESHOLD + 1,
            "groundSpeed": AIRCRAFT_GROUND_SPEED_THRESHOLD + 1,
        }
        data = position_handler._extract_position_data(position)
        assert data["is_fast_moving"] is True
        assert data["is_high_altitude"] is True

    def test_below_thresholds(self, position_handler):
        position = {
            "altitude": AIRCRAFT_ALTITUDE_THRESHOLD - 1,
            "groundSpeed": AIRCRAFT_GROUND_SPEED_THRESHOLD - 1,
        }
        data = position_handler._extract_position_data(position)
        assert data["is_fast_moving"] is False
        assert data["is_high_altitude"] is False

    def test_missing_lat_lon(self, position_handler):
        position = {"altitude": 100}
        data = position_handler._extract_position_data(position)
        assert data["location"] == DEFAULT_LOCATION

    def test_manual_location_source(self, position_handler):
        position = {"locationSource": "LOC_MANUAL"}
        data = position_handler._extract_position_data(position)
        assert data["location_source"] == "LOC_MANUAL"

    def test_empty_position(self, position_handler):
        data = position_handler._extract_position_data({})
        assert data["altitude"] == 0
        assert data["ground_speed"] == 0
        assert data["location"] == DEFAULT_LOCATION


class TestBuildLogMessage:
    def test_minimal(self, position_handler):
        data = {
            "location": DEFAULT_LOCATION,
            "ground_speed": 0,
            "altitude": 0,
            "is_fast_moving": False,
            "is_high_altitude": False,
        }
        msg = position_handler._build_log_message("TST1", 123, data)
        assert "TST1" in msg
        assert "123" in msg

    def test_with_location(self, position_handler):
        data = {
            "location": "Akron, OH",
            "ground_speed": 10,
            "altitude": 300,
            "is_fast_moving": False,
            "is_high_altitude": False,
            "satsInView": 8,
        }
        msg = position_handler._build_log_message("TST1", 123, data)
        assert "Akron, OH" in msg
        assert "Ground Speed: 10" in msg
        assert "Altitude: 300" in msg
        assert "Satellites in View: 8" in msg


class TestHandleAircraftDetection:
    def test_new_aircraft_detected(self, position_handler):
        node = {"num": 123}
        position_handler.db_helper.is_aircraft.return_value = False
        pos_data = {"is_fast_moving": True, "is_high_altitude": True, "altitude": 9000, "ground_speed": 200}
        mock_interface = MagicMock()

        position_handler._handle_aircraft_detection(
            node, "TST1", pos_data, mock_interface, "admin msg", 1
        )

        position_handler.db_helper.set_aircraft.assert_called_once_with(node, True)

    def test_already_aircraft(self, position_handler):
        node = {"num": 123}
        position_handler.db_helper.is_aircraft.return_value = True
        pos_data = {"is_fast_moving": True, "is_high_altitude": True, "altitude": 9000, "ground_speed": 200}

        position_handler._handle_aircraft_detection(
            node, "TST1", pos_data, MagicMock(), "admin msg", 1
        )

        position_handler.db_helper.set_aircraft.assert_not_called()

    def test_aircraft_unmarked_when_below_thresholds(self, position_handler):
        node = {"num": 123}
        position_handler.db_helper.is_aircraft.return_value = True
        pos_data = {"is_fast_moving": False, "is_high_altitude": False, "altitude": 100, "ground_speed": 5}

        position_handler._handle_aircraft_detection(
            node, "TST1", pos_data, MagicMock(), "admin msg", 1
        )

        position_handler.db_helper.set_aircraft.assert_called_once_with(node, False)

    def test_no_action_mixed_thresholds(self, position_handler):
        """Fast but low altitude — no action."""
        node = {"num": 123}
        pos_data = {"is_fast_moving": True, "is_high_altitude": False, "altitude": 100, "ground_speed": 200}

        position_handler._handle_aircraft_detection(
            node, "TST1", pos_data, MagicMock(), "admin msg", 1
        )

        position_handler.db_helper.set_aircraft.assert_not_called()
        position_handler.db_helper.is_aircraft.assert_not_called()
