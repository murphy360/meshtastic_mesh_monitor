"""Tests for core constants module."""

import pytest

from core.constants import (
    AIRCRAFT_ALTITUDE_THRESHOLD,
    AIRCRAFT_GROUND_SPEED_THRESHOLD,
    BATTERY_CRITICAL_THRESHOLD,
    BATTERY_LOW_THRESHOLD,
    BROADCAST_DESTINATION,
    DATABASE_PATH,
    DATETIME_FORMAT,
    DEFAULT_LOCATION,
    DEFAULT_NODE_NAME,
    LOCAL_NODE_ID,
    MAIN_LOOP_INTERVAL_SECONDS,
    MESSAGE_CHUNK_SIZE,
    MESSAGE_MAX_LENGTH,
    SECONDS_PER_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
)


class TestConstants:
    """Verify constants have sensible values and relationships."""

    def test_time_constants_consistent(self):
        assert SECONDS_PER_MINUTE == 60
        assert SECONDS_PER_HOUR == 3600
        assert SECONDS_PER_DAY == 86400
        assert SECONDS_PER_DAY == SECONDS_PER_HOUR * 24
        assert SECONDS_PER_HOUR == SECONDS_PER_MINUTE * 60

    def test_message_sizes(self):
        assert MESSAGE_CHUNK_SIZE < MESSAGE_MAX_LENGTH
        assert MESSAGE_MAX_LENGTH > 0
        assert MESSAGE_CHUNK_SIZE > 0

    def test_battery_thresholds_ordered(self):
        assert BATTERY_CRITICAL_THRESHOLD < BATTERY_LOW_THRESHOLD
        assert BATTERY_CRITICAL_THRESHOLD > 0
        assert BATTERY_LOW_THRESHOLD <= 100

    def test_aircraft_thresholds_positive(self):
        assert AIRCRAFT_GROUND_SPEED_THRESHOLD > 0
        assert AIRCRAFT_ALTITUDE_THRESHOLD > 0

    def test_default_values_not_empty(self):
        assert DEFAULT_NODE_NAME
        assert DEFAULT_LOCATION
        assert LOCAL_NODE_ID
        assert BROADCAST_DESTINATION
        assert DATABASE_PATH
        assert DATETIME_FORMAT

    def test_main_loop_interval_reasonable(self):
        assert MAIN_LOOP_INTERVAL_SECONDS >= 10
        assert MAIN_LOOP_INTERVAL_SECONDS <= 300
