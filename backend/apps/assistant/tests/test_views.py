"""
Integration tests for POST /api/v1/assistant/chat/.

The Anthropic client is mocked throughout — no API key or network needed.
"""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.commands import record_movement
from apps.inventory.models import MovementReason, Product, Stock

CHAT_URL = '/api/v1/assistant/chat/'


# ---------------------------------------------------------------------------
# Helpers to build mock Anthropic responses
# ---------------------------------------------------------------------------

def _end_turn_response(text: str) -> MagicMock:
    """Simulate a final Claude response with a text block and stop_reason=end_turn."""
    block = MagicMock()
    block.type = 'text'
    block.text = text

    response = MagicMock()
    response.stop_reason = 'end_turn'
    response.content = [block]
    return response


def _tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str = 'tu_abc123') -> MagicMock:
    """Simulate Claude requesting a tool call."""
    block = MagicMock()
    block.type = 'tool_use'
    block.id = tool_use_id
    block.name = tool_name
    block.input = tool_input

    response = MagicMock()
    response.stop_reason = 'tool_use'
    response.content = [block]
    return response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='chat_user', email='chat@example.com', password='ChatPass123!'
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username='chat_other', email='other@example.com', password='OtherPass123!'
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def product(user):
    return Product.objects.create(
        user=user, name='Test Product', sku='TP-01', unit_of_measure='KG',
    )


@pytest.fixture
def stock_batch(user, product):
    batch = Stock.objects.create(
        user=user,
        product=product,
        initial_quantity=Decimal('50'),
        current_quantity=Decimal('50'),
        unit_cost=Decimal('3.00'),
        lot_code='LOT-TEST',
    )
    record_movement(
        user=user,
        stock_batch=batch,
        delta=Decimal('50'),
        reason=MovementReason.RECEIPT,
    )
    return batch


@pytest.fixture
def other_product(other_user):
    return Product.objects.create(
        user=other_user, name='Other Product', sku='OTH-01', unit_of_measure='L',
    )


@pytest.fixture
def other_stock(other_user, other_product):
    batch = Stock.objects.create(
        user=other_user,
        product=other_product,
        initial_quantity=Decimal('10'),
        current_quantity=Decimal('10'),
        unit_cost=Decimal('1.00'),
    )
    record_movement(
        user=other_user,
        stock_batch=batch,
        delta=Decimal('10'),
        reason=MovementReason.RECEIPT,
    )
    return batch


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestChatAuthentication:
    def test_unauthenticated_returns_401(self, anon_client):
        response = anon_client.post(CHAT_URL, {'messages': []}, format='json')
        assert response.status_code == 401

    def test_authenticated_with_key_configured_returns_200(self, auth_client):
        end_turn = _end_turn_response('Hello!')
        with patch('apps.assistant.views._get_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = end_turn
            mock_client_fn.return_value = mock_client

            response = auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'Hi'}]},
                format='json',
            )
        assert response.status_code == 200
        assert 'reply' in response.data


# ---------------------------------------------------------------------------
# No API key configured
# ---------------------------------------------------------------------------

class TestNoApiKey:
    def test_returns_503_when_key_absent(self, auth_client):
        with patch('apps.assistant.views._get_client', return_value=None):
            response = auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'Hi'}]},
                format='json',
            )
        assert response.status_code == 503
        assert 'error' in response.data


# ---------------------------------------------------------------------------
# Happy path: end_turn (no tool calls)
# ---------------------------------------------------------------------------

class TestEndTurnResponse:
    def test_returns_reply_text(self, auth_client):
        end_turn = _end_turn_response('Your inventory looks great.')
        with patch('apps.assistant.views._get_client') as mock_client_fn:
            mock = MagicMock()
            mock.messages.create.return_value = end_turn
            mock_client_fn.return_value = mock

            response = auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'How is my inventory?'}]},
                format='json',
            )
        assert response.status_code == 200
        assert response.data['reply'] == 'Your inventory looks great.'

    def test_claude_called_once(self, auth_client):
        end_turn = _end_turn_response('Done.')
        with patch('apps.assistant.views._get_client') as mock_client_fn:
            mock = MagicMock()
            mock.messages.create.return_value = end_turn
            mock_client_fn.return_value = mock

            auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'Hello'}]},
                format='json',
            )
            assert mock.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# Tool call round-trip
# ---------------------------------------------------------------------------

class TestToolCallRoundTrip:
    def test_single_tool_call_followed_by_end_turn(self, auth_client, stock_batch):
        """Claude requests get_stock_levels, gets results, then replies."""
        tool_response = _tool_use_response('get_stock_levels', {})
        end_turn = _end_turn_response('You have 50 KG in stock.')

        with patch('apps.assistant.views._get_client') as mock_client_fn:
            mock = MagicMock()
            mock.messages.create.side_effect = [tool_response, end_turn]
            mock_client_fn.return_value = mock

            response = auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'What stock do I have?'}]},
                format='json',
            )

        assert response.status_code == 200
        assert '] == 'You have 50 KG in stock.'
        assert mock.messages.create.call_count == 2

    def test_tool_result_appended_to_messages(self, auth_client, stock_batch):
        """The second Claude call receives the tool_result in message history."""
        tool_response = _tool_use_response('get_stock_levels', {}, tool_use_id='tu_xyz')
        end_turn = _end_turn_response.data['replyresponse('Done.')

        captured_calls = []

        def capture(*args, **kwargs):
            captured_calls.append(kwargs.get('messages', []))
            if len(captured_calls) == 1:
                return tool_response
            return end_turn

        with patch('apps.assistant.views._get_client') as mock_client_fn:
            mock = MagicMock()
            mock.messages.create.side_effect = capture
            mock_client_fn.return_value = mock

            auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'Check stock'}]},
                format='json',
            )

        # Second call should have assistant turn + tool_result in messages
        second_call_messages = captured_calls[1]
        roles = [m['role'] for m in second_call_messages]
        assert 'assistant' in roles
        assert roles[-1] == 'user'  # tool_result is user role

        # Tool result content should be JSON
        tool_result_msg = second_call_messages[-1]
        assert tool_result_msg['role'] == 'user'
        result_blocks = tool_result_msg['content']
        assert len(result_blocks) == 1
        assert result_blocks[0]['type'] == 'tool_result'
        assert result_blocks[0]['tool_use_id'] == 'tu_xyz'
        payload = json.loads(result_blocks[0]['content'])
        assert isinstance(payload, list)


# ---------------------------------------------------------------------------
# Tool executor error surfaced as is_error tool_result
# ---------------------------------------------------------------------------

class TestToolExecutorError:
    def test_executor_exception_becomes_is_error_tool_result(self, auth_client):
        """An exception in execute_tool must produce is_error=True, not a 500."""
        bad_tool_response = _tool_use_response('get_stock_levels', {'product_id': 'not-a-uuid'})
        end_turn = _end_turn_response('Sorry, there was an error fetching that.')

        captured_second = []

        def side_effect(*args, **kwargs):
            msgs = kwargs.get('messages', [])
            if len(msgs) == 1:
                return bad_tool_response
            captured_second.append(msgs)
            return end_turn

        with patch('apps.assistant.views._get_client') as mock_client_fn:
            mock = MagicMock()
            mock.messages.create.side_effect = side_effect
            mock_client_fn.return_value = mock

            response = auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'Check a specific product'}]},
                format='json',
            )

        assert response.status_code == 200
        # The tool result should have is_error=True
        second_messages = captured_second[0]
        tool_result_block = second_messages[-1]['content'][0]
        assert tool_result_block.get('is_error') is True


# ---------------------------------------------------------------------------
# Iteration cap
# ---------------------------------------------------------------------------

class TestIterationCap:
    def test_always_tool_use_returns_500(self, auth_client):
        """If the model keeps requesting tools and never ends, the view returns 500."""
        infinite_tool = _tool_use_response('get_stock_levels', {})

        with patch('apps.assistant.views._get_client') as mock_client_fn:
            mock = MagicMock()
            mock.messages.create.return_value = infinite_tool
            mock_client_fn.return_value = mock

            response = auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'Loop forever'}]},
                format='json',
            )

        assert response.status_code == 500
        assert 'error' in response.data


# ---------------------------------------------------------------------------
# Cross-tenant isolation
# ---------------------------------------------------------------------------

class TestCrossTenantIsolation:
    def test_tool_results_for_user_a_exclude_user_b_data(
        self, auth_client, stock_batch, other_stock
    ):
        """get_stock_levels called as user_a must not return user_b's batches."""
        tool_response = _tool_use_response('get_stock_levels', {})
        end_turn = _end_turn_response('Done.')

        captured = []

        def side_effect(*args, **kwargs):
            msgs = kwargs.get('messages', [])
            if len(msgs) == 1:
                return tool_response
            captured.append(msgs)
            return end_turn

        with patch('apps.assistant.views._get_client') as mock_client_fn:
            mock = MagicMock()
            mock.messages.create.side_effect = side_effect
            mock_client_fn.return_value = mock

            auth_client.post(
                CHAT_URL,
                {'messages': [{'role': 'user', 'content': 'List my stock'}]},
                format='json',
            )

        second_messages = captured[0]
        tool_result_block = second_messages[-1]['content'][0]
        payload = json.loads(tool_result_block['content'])
        skus = [row['product_sku'] for row in payload]
        assert 'OTH-01' not in skus
        assert 'TP-01' in skus
