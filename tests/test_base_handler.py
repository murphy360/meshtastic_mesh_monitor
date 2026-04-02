"""Tests for BaseHandler helper methods."""

from unittest.mock import MagicMock, patch

import pytest

from core.constants import DEFAULT_NODE_NAME, LOCAL_NODE_ID
from handlers.base_handler import BaseHandler


@pytest.fixture
def handler():
    """Create a BaseHandler instance with mocked dependencies."""
    with patch("handlers.base_handler.MessageSender") as mock_ms, patch(
        "handlers.base_handler.SQLiteHelper"
    ) as mock_db:
        mock_ms.get_instance.return_value = MagicMock()
        mock_db.get_instance.return_value = MagicMock()
        return BaseHandler()


class TestGetNodeShortName:
    def test_valid_node(self, handler, sample_node):
        assert handler._get_node_short_name(sample_node) == "TST1"

    def test_none_node(self, handler):
        assert handler._get_node_short_name(None) == DEFAULT_NODE_NAME

    def test_missing_user_key(self, handler):
        node = {"num": 123}
        assert handler._get_node_short_name(node) == DEFAULT_NODE_NAME

    def test_missing_short_name(self, handler):
        node = {"user": {"longName": "Test"}}
        assert handler._get_node_short_name(node) == DEFAULT_NODE_NAME

    def test_empty_dict(self, handler):
        assert handler._get_node_short_name({}) == DEFAULT_NODE_NAME


class TestIsLocalNode:
    def test_local_node_returns_true(self, handler, mock_interface):
        assert handler._is_local_node(mock_interface, 999999999) is True

    def test_remote_node_returns_false(self, handler, mock_interface):
        assert handler._is_local_node(mock_interface, 123456789) is False

    def test_calls_getNode_with_local_id(self, handler, mock_interface):
        handler._is_local_node(mock_interface, 123)
        mock_interface.getNode.assert_called_with(LOCAL_NODE_ID)
