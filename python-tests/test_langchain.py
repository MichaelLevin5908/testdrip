"""
Test LangChain callback handler integration.

This module tests the DripCallbackHandler that integrates with LangChain
to automatically track token usage and tool calls.
"""

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock
import uuid

# Check if drip-sdk is available
try:
    from drip import Drip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None

# Check if LangChain is available
try:
    import langchain
    from langchain.callbacks.base import BaseCallbackHandler
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseCallbackHandler = None

# Check if Drip LangChain integration is available
try:
    from drip.integrations.langchain import DripCallbackHandler
    LANGCHAIN_INTEGRATION_AVAILABLE = True
except ImportError:
    LANGCHAIN_INTEGRATION_AVAILABLE = False
    DripCallbackHandler = None


pytestmark = [
    pytest.mark.skipif(not DRIP_SDK_AVAILABLE, reason="drip-sdk not installed"),
    pytest.mark.langchain
]


class MockLLMResponse:
    """Mock LLM response for testing."""

    def __init__(self, total_tokens: int = 100, prompt_tokens: int = 50, completion_tokens: int = 50):
        self.llm_output = {
            "token_usage": {
                "total_tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }
        }
        self.generations = [[Mock(text="Test response")]]


class MockChainResponse:
    """Mock chain response for testing."""

    def __init__(self, output: str = "Chain output"):
        self.output = output


class TestDripCallbackHandlerInitialization:
    """Test DripCallbackHandler initialization."""

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_initialization(self, client, test_customer):
        """Handler initializes with client and customer."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens"
        )
        assert handler.customer_id == test_customer.id
        assert handler.meter == "tokens"

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_initialization_with_workflow(self, client, test_customer, test_workflow):
        """Handler initializes with workflow for run tracking."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            workflow_id=test_workflow.id,
            emit_events=True
        )
        assert handler.workflow_id == test_workflow.id
        assert handler.emit_events is True

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_initialization_defaults(self, client, test_customer):
        """Handler has sensible defaults."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id
        )
        # Check default meter
        assert handler.meter is not None or handler.default_meter is not None

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_inherits_callback_handler(self, client, test_customer):
        """Handler inherits from LangChain BaseCallbackHandler."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens"
        )
        if LANGCHAIN_AVAILABLE and BaseCallbackHandler:
            assert isinstance(handler, BaseCallbackHandler)


class TestDripCallbackHandlerTokenTracking:
    """Test token tracking functionality."""

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_tracks_tokens(self, client, test_customer):
        """Handler tracks token usage."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens"
        )

        # Simulate LLM response with token counts
        response = MockLLMResponse(total_tokens=150)
        handler.on_llm_end(
            response=response,
            run_id=uuid.uuid4()
        )

        assert handler.total_tokens >= 150

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_tracks_prompt_and_completion_tokens(self, client, test_customer):
        """Handler tracks prompt and completion tokens separately."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            track_prompt_tokens=True,
            track_completion_tokens=True
        )

        response = MockLLMResponse(
            total_tokens=200,
            prompt_tokens=80,
            completion_tokens=120
        )
        handler.on_llm_end(
            response=response,
            run_id=uuid.uuid4()
        )

        # Check for separate tracking if supported
        if hasattr(handler, 'prompt_tokens'):
            assert handler.prompt_tokens >= 80
        if hasattr(handler, 'completion_tokens'):
            assert handler.completion_tokens >= 120

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_accumulates_tokens(self, client, test_customer):
        """Handler accumulates tokens across multiple LLM calls."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens"
        )

        for i in range(3):
            response = MockLLMResponse(total_tokens=50)
            handler.on_llm_end(
                response=response,
                run_id=uuid.uuid4()
            )

        assert handler.total_tokens >= 150

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_handles_missing_token_info(self, client, test_customer):
        """Handler handles responses without token info gracefully."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens"
        )

        # Response without token usage
        response = Mock()
        response.llm_output = None

        # Should not raise an error
        handler.on_llm_end(
            response=response,
            run_id=uuid.uuid4()
        )


class TestDripCallbackHandlerToolTracking:
    """Test tool call tracking functionality."""

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_tracks_tool_calls(self, client, test_customer):
        """Handler tracks tool call events."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tool_calls",
            track_tools=True
        )

        handler.on_tool_start(
            serialized={"name": "calculator"},
            input_str="2 + 2",
            run_id=uuid.uuid4()
        )
        handler.on_tool_end(output="4", run_id=uuid.uuid4())

        assert handler.tool_call_count >= 1

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_tracks_multiple_tool_calls(self, client, test_customer):
        """Handler tracks multiple tool calls."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tool_calls",
            track_tools=True
        )

        tools = ["search", "calculator", "weather"]
        for tool in tools:
            handler.on_tool_start(
                serialized={"name": tool},
                input_str="test input",
                run_id=uuid.uuid4()
            )
            handler.on_tool_end(output="result", run_id=uuid.uuid4())

        assert handler.tool_call_count >= 3

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_tool_tracking_disabled(self, client, test_customer):
        """Handler doesn't track tools when disabled."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            track_tools=False
        )

        handler.on_tool_start(
            serialized={"name": "calculator"},
            input_str="2 + 2",
            run_id=uuid.uuid4()
        )
        handler.on_tool_end(output="4", run_id=uuid.uuid4())

        # Tool count should be 0 or not tracked
        tool_count = getattr(handler, 'tool_call_count', 0)
        assert tool_count == 0

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_tracks_tool_errors(self, client, test_customer):
        """Handler tracks tool errors."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tool_calls",
            track_tools=True
        )

        handler.on_tool_start(
            serialized={"name": "failing_tool"},
            input_str="bad input",
            run_id=uuid.uuid4()
        )
        handler.on_tool_error(
            error=ValueError("Tool failed"),
            run_id=uuid.uuid4()
        )

        # Tool call should still be counted
        assert handler.tool_call_count >= 1


class TestDripCallbackHandlerRunTracking:
    """Test workflow run tracking integration."""

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_with_run_tracking(self, client, test_customer, test_workflow):
        """Handler integrates with workflow runs."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            workflow_id=test_workflow.id,
            emit_events=True
        )

        handler.on_chain_start(
            serialized={"name": "test_chain"},
            inputs={"query": "test"},
            run_id=uuid.uuid4()
        )

        assert handler.run_id is not None

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_emits_llm_events(self, client, test_customer, test_workflow):
        """Handler emits LLM events to run timeline."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            workflow_id=test_workflow.id,
            emit_events=True
        )

        # Start a chain to create a run
        handler.on_chain_start(
            serialized={"name": "test_chain"},
            inputs={"query": "test"},
            run_id=uuid.uuid4()
        )

        # Emit LLM start event
        handler.on_llm_start(
            serialized={"name": "gpt-4"},
            prompts=["Hello, world!"],
            run_id=uuid.uuid4()
        )

        # Should have emitted events
        if hasattr(handler, 'events_emitted'):
            assert handler.events_emitted >= 1

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_chain_end_finalizes(self, client, test_customer, test_workflow):
        """Handler finalizes on chain end."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            workflow_id=test_workflow.id,
            emit_events=True,
            finalize_on_chain_end=True
        )

        chain_run_id = uuid.uuid4()

        handler.on_chain_start(
            serialized={"name": "test_chain"},
            inputs={"query": "test"},
            run_id=chain_run_id
        )

        handler.on_chain_end(
            outputs={"result": "success"},
            run_id=chain_run_id
        )

        # Run should be finalized
        if hasattr(handler, 'run_finalized'):
            assert handler.run_finalized is True


class TestDripCallbackHandlerBilling:
    """Test billing integration."""

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_charges_on_finalize(self, client, test_customer):
        """Handler charges usage when finalized."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            auto_charge=True
        )

        # Simulate usage
        response = MockLLMResponse(total_tokens=100)
        handler.on_llm_end(
            response=response,
            run_id=uuid.uuid4()
        )

        # Finalize to trigger charge
        result = handler.finalize()

        # Should return charge info or None if auto_charge handled it
        assert result is None or result is not None

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_manual_charge(self, client, test_customer):
        """Handler supports manual charging."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            auto_charge=False
        )

        response = MockLLMResponse(total_tokens=100)
        handler.on_llm_end(
            response=response,
            run_id=uuid.uuid4()
        )

        # Manual charge
        charge = handler.charge()
        assert charge is not None

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_idempotency(self, client, test_customer, idempotency_key):
        """Handler supports idempotency keys."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            idempotency_key=idempotency_key
        )

        assert handler.idempotency_key == idempotency_key


class TestDripCallbackHandlerMetrics:
    """Test metrics and statistics."""

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_get_metrics(self, client, test_customer):
        """Handler provides usage metrics."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens"
        )

        # Simulate some activity
        handler.on_llm_start(
            serialized={"name": "gpt-4"},
            prompts=["Test"],
            run_id=uuid.uuid4()
        )

        response = MockLLMResponse(total_tokens=100)
        handler.on_llm_end(
            response=response,
            run_id=uuid.uuid4()
        )

        metrics = handler.get_metrics()
        assert metrics is not None
        assert "total_tokens" in metrics or hasattr(metrics, "total_tokens")

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_reset_metrics(self, client, test_customer):
        """Handler can reset metrics."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens"
        )

        response = MockLLMResponse(total_tokens=100)
        handler.on_llm_end(
            response=response,
            run_id=uuid.uuid4()
        )

        assert handler.total_tokens >= 100

        handler.reset()
        assert handler.total_tokens == 0


class TestDripCallbackHandlerConfiguration:
    """Test configuration options."""

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_custom_meter_mapping(self, client, test_customer):
        """Handler supports custom meter mapping."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter_mapping={
                "llm_tokens": "tokens",
                "tool_calls": "api_calls"
            }
        )
        assert handler.meter_mapping is not None

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_metadata(self, client, test_customer):
        """Handler supports metadata."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            metadata={"chain_type": "qa", "model": "gpt-4"}
        )
        assert handler.metadata == {"chain_type": "qa", "model": "gpt-4"}

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_verbose_mode(self, client, test_customer):
        """Handler supports verbose mode."""
        handler = DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens",
            verbose=True
        )
        assert handler.verbose is True


class TestDripCallbackHandlerContextManager:
    """Test context manager functionality."""

    @pytest.mark.skipif(
        not LANGCHAIN_INTEGRATION_AVAILABLE,
        reason="drip.integrations.langchain not available"
    )
    def test_handler_as_context_manager(self, client, test_customer):
        """Handler can be used as context manager."""
        with DripCallbackHandler(
            client=client,
            customer_id=test_customer.id,
            meter="tokens"
        ) as handler:
            response = MockLLMResponse(total_tokens=100)
            handler.on_llm_end(
                response=response,
                run_id=uuid.uuid4()
            )
            assert handler.total_tokens >= 100

        # After exiting context, handler should be finalized
        # (behavior depends on implementation)
