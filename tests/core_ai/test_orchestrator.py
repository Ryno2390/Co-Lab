import pytest
from pytest_mock import MockerFixture # For type hinting mocker
from typing import List
import asyncio # Need asyncio for mocking gather

# Modules to test (using imports relative to project root 'Co-Lab')
from core_ai.orchestrator import process_user_prompt
from core_ai.models import UserInput, SubTask, SubAIResponse, FinalResponse, RoutingDecision

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# --- Test Fixtures (Optional but good practice) ---
@pytest.fixture
def sample_user_input() -> UserInput:
    """Provides a sample UserInput object."""
    return UserInput(prompt="Test prompt about topic X", user_id="test_user_123")

@pytest.fixture
def mock_sub_tasks() -> List[SubTask]:
    """Provides a sample list of SubTask objects."""
    return [
        SubTask(sub_task_id="st1", instruction="Instruction for task 1"),
        SubTask(sub_task_id="st2", instruction="Instruction for task 2"),
    ]

@pytest.fixture
def mock_routing_decisions(mock_sub_tasks) -> List[RoutingDecision]:
    """Provides a sample list of RoutingDecision objects."""
    return [
        RoutingDecision(sub_task=mock_sub_tasks[0], route_type='fixed_specialist', target_id='SummarizationAI', confidence_score=0.9),
        RoutingDecision(sub_task=mock_sub_tasks[1], route_type='dynamic_instance', confidence_score=0.6), # Score below threshold
    ]

@pytest.fixture
def mock_sub_ai_responses(mock_sub_tasks) -> List[SubAIResponse]:
    """Provides a sample list of successful SubAIResponse objects."""
    return [
        SubAIResponse(sub_task_id="st1", source_sub_ai_id="SummarizationAI", content="Summary response.", status="success"),
        SubAIResponse(sub_task_id="st2", source_sub_ai_id="dynamic_instance_st2", content={"dynamic": "data"}, status="success"),
    ]

# --- Test Cases ---

async def test_process_user_prompt_success(
    mocker: MockerFixture,
    sample_user_input: UserInput,
    mock_sub_tasks: List[SubTask],
    mock_routing_decisions: List[RoutingDecision],
    mock_sub_ai_responses: List[SubAIResponse]
):
    """
    Tests the happy path where all steps succeed.
    """
    # Arrange: Mock all dependencies called by the orchestrator
    # Patch targets remain the same as they refer to where the name is looked up
    # within the orchestrator module's namespace.
    mock_decompose = mocker.patch('Co-Lab.core_ai.orchestrator.decompose_prompt', return_value=mock_sub_tasks)
    mock_route = mocker.patch('Co-Lab.core_ai.orchestrator.route_sub_tasks', return_value=mock_routing_decisions)
    mock_calc_cost = mocker.patch('Co-Lab.core_ai.orchestrator.calculate_query_cost', return_value=25.5) # Example cost
    mock_charge_user = mocker.patch('Co-Lab.core_ai.orchestrator.charge_user_for_query', return_value=True) # Simulate successful charge
    mock_invoke = mocker.patch('Co-Lab.core_ai.orchestrator.invoke_sub_ai')
    # Mock asyncio.gather used within the orchestrator
    mock_gather = mocker.patch('asyncio.gather', return_value=mock_sub_ai_responses)
    mock_synthesize = mocker.patch('Co-Lab.core_ai.orchestrator.synthesize_responses', return_value="Final synthesized answer.")

    # Act: Call the orchestrator function
    final_response = await process_user_prompt(sample_user_input)

    # Assert: Check if the flow was correct and the response is as expected
    mock_decompose.assert_awaited_once_with(sample_user_input.prompt)
    mock_route.assert_awaited_once_with(mock_sub_tasks)
    mock_calc_cost.assert_called_once_with(mock_routing_decisions)
    mock_charge_user.assert_awaited_once_with(sample_user_input.user_id, 25.5)
    # Check that invoke_sub_ai was called for each decision before gather
    assert mock_invoke.call_count == len(mock_routing_decisions)
    # Check the arguments passed to gather (it should be a list of awaitables from invoke_sub_ai)
    mock_gather.assert_awaited_once()
    assert len(mock_gather.call_args[0][0]) == len(mock_routing_decisions) # Check number of tasks passed to gather

    mock_synthesize.assert_awaited_once_with(
        original_prompt=sample_user_input.prompt,
        sub_tasks=mock_sub_tasks,
        sub_ai_responses=mock_sub_ai_responses # Assuming all were successful in this test
    )

    assert isinstance(final_response, FinalResponse)
    assert final_response.status == "success"
    assert final_response.synthesized_answer == "Final synthesized answer."
    assert final_response.session_id == sample_user_input.session_id
    assert final_response.error_message is None

async def test_process_user_prompt_charge_failed(
    mocker: MockerFixture,
    sample_user_input: UserInput,
    mock_sub_tasks: List[SubTask],
    mock_routing_decisions: List[RoutingDecision]
):
    """
    Tests the case where charging the user fails.
    """
    # Arrange: Mock dependencies up to the charging step
    mocker.patch('Co-Lab.core_ai.orchestrator.decompose_prompt', return_value=mock_sub_tasks)
    mocker.patch('Co-Lab.core_ai.orchestrator.route_sub_tasks', return_value=mock_routing_decisions)
    mocker.patch('Co-Lab.core_ai.orchestrator.calculate_query_cost', return_value=30.0)
    # Mock charge_user_for_query to return False (failure)
    mock_charge_user = mocker.patch('Co-Lab.core_ai.orchestrator.charge_user_for_query', return_value=False)
    # Mock subsequent functions to ensure they are NOT called
    mock_invoke = mocker.patch('Co-Lab.core_ai.orchestrator.invoke_sub_ai')
    mock_synthesize = mocker.patch('Co-Lab.core_ai.orchestrator.synthesize_responses')
    mock_gather = mocker.patch('asyncio.gather') # Also mock gather

    # Act: Call the orchestrator function
    final_response = await process_user_prompt(sample_user_input)

    # Assert: Check that charging failed and subsequent steps were skipped
    mock_charge_user.assert_awaited_once_with(sample_user_input.user_id, 30.0)
    mock_invoke.assert_not_called()
    mock_gather.assert_not_called()
    mock_synthesize.assert_not_called()

    assert isinstance(final_response, FinalResponse)
    assert final_response.status == "error_charge_failed"
    assert final_response.synthesized_answer == ""
    assert "Failed to charge for query" in final_response.error_message

# TODO: Add more test cases:
# - No user_id provided
# - Decomposition returns empty list
# - Routing fails
# - Some or all Sub-AI invocations fail
# - Synthesis fails