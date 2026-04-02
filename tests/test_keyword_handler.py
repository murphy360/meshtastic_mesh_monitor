"""Tests for KeywordHandler helper methods."""

from unittest.mock import MagicMock, patch

import pytest

from core.constants import BROADCAST_DESTINATION
from keywords.keyword_handler import KeywordHandler


@pytest.fixture
def keyword_handler():
    """Create a KeywordHandler instance with mocked dependencies."""
    with patch("keywords.keyword_handler.MessageSender") as mock_ms:
        mock_ms.get_instance.return_value = MagicMock()
        return KeywordHandler()


class TestExtractMessageArgs:
    def test_normal_message(self, keyword_handler):
        packet = {"decoded": {"payload": b"ping test"}}
        assert keyword_handler._extract_message_args(packet) == ["ping", "test"]

    def test_single_word(self, keyword_handler):
        packet = {"decoded": {"payload": b"commands"}}
        assert keyword_handler._extract_message_args(packet) == ["commands"]

    def test_whitespace_stripped(self, keyword_handler):
        packet = {"decoded": {"payload": b"  trace  node1  "}}
        assert keyword_handler._extract_message_args(packet) == ["trace", "node1"]

    def test_no_decoded(self, keyword_handler):
        packet = {"encrypted": True}
        assert keyword_handler._extract_message_args(packet) == []

    def test_no_payload(self, keyword_handler):
        packet = {"decoded": {"portnum": "TEXT_MESSAGE_APP"}}
        assert keyword_handler._extract_message_args(packet) == []

    def test_empty_payload(self, keyword_handler):
        packet = {"decoded": {"payload": b""}}
        assert keyword_handler._extract_message_args(packet) == []


class TestGetReplyTarget:
    def test_direct_message(self, keyword_handler, mock_interface):
        """When packet 'to' matches local node, reply goes to sender."""
        packet = {"from": 123456789, "to": 999999999, "channel": 2}
        channel, to_id = keyword_handler._get_reply_target(packet, mock_interface)
        assert channel == 2
        assert to_id == 123456789

    def test_channel_message(self, keyword_handler, mock_interface):
        """When packet 'to' doesn't match local node, reply goes to broadcast."""
        packet = {"from": 123456789, "to": 4294967295, "channel": 0}
        channel, to_id = keyword_handler._get_reply_target(packet, mock_interface)
        assert channel == 0
        assert to_id == BROADCAST_DESTINATION

    def test_missing_channel_defaults_to_zero(self, keyword_handler, mock_interface):
        packet = {"from": 123456789, "to": 4294967295}
        channel, to_id = keyword_handler._get_reply_target(packet, mock_interface)
        assert channel == 0

    def test_missing_to_field(self, keyword_handler, mock_interface):
        """When 'to' is missing, should reply to broadcast."""
        packet = {"from": 123456789, "channel": 0}
        channel, to_id = keyword_handler._get_reply_target(packet, mock_interface)
        assert to_id == BROADCAST_DESTINATION
