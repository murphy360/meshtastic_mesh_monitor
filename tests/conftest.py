"""Shared fixtures for mesh_monitor tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add app/ to sys.path so imports work like they do at runtime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))


@pytest.fixture
def mock_interface():
    """Create a mock meshtastic interface."""
    iface = MagicMock()
    local_node = MagicMock()
    local_node.nodeNum = 999999999
    iface.getNode.return_value = local_node
    iface.getMyNodeInfo.return_value = {
        "num": 999999999,
        "user": {
            "shortName": "LCAL",
            "longName": "Local Node",
            "id": "!deadbeef",
            "publicKey": "abc123",
            "hwModel": "HELTEC_V3",
        },
        "position": {"latitude": 41.0, "longitude": -81.0, "altitude": 300},
    }
    iface.nodesByNum = {}
    return iface


@pytest.fixture
def sample_packet():
    """Create a sample decoded packet."""
    return {
        "from": 123456789,
        "to": 4294967295,
        "channel": 0,
        "id": 12345,
        "decoded": {
            "portnum": "TEXT_MESSAGE_APP",
            "payload": b"hello world",
            "bitfield": 0,
        },
    }


@pytest.fixture
def sample_node():
    """Create a sample node dict."""
    return {
        "num": 123456789,
        "user": {
            "shortName": "TST1",
            "longName": "Test Node One",
            "id": "!12345678",
        },
        "position": {
            "latitude": 41.5,
            "longitude": -81.5,
            "altitude": 250,
        },
    }


@pytest.fixture
def sample_position_packet():
    """Create a sample position packet."""
    return {
        "from": 123456789,
        "to": 4294967295,
        "decoded": {
            "portnum": "POSITION_APP",
            "position": {
                "latitude": 41.5,
                "longitude": -81.5,
                "altitude": 250,
                "groundSpeed": 5,
                "satsInView": 8,
                "time": 1700000000,
            },
        },
    }
