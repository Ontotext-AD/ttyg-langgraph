from unittest.mock import MagicMock

from langchain_core.language_models import FakeMessagesListChatModel, BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from langsmith.schemas import UsageMetadata

from ttyg.agents import run_agent_for_evaluation


def test_run_agent_for_evaluation_status_success():
    answer = "The weather is sunny"
    chat_model = FakeMessagesListChatModel(responses=[
        AIMessage(content=answer,
                  usage_metadata=UsageMetadata(input_tokens=100, output_tokens=50, total_tokens=150))
    ])
    agent = create_react_agent(
        model=chat_model,
        tools=[],
        prompt="You are a helpful assistant"
    )
    question_id = "question-123"
    messages = {"messages": [("user", "What's the weather in Sofia today?")]}
    response = run_agent_for_evaluation(agent, question_id, messages)
    assert 7 == len(response)
    assert question_id == response["question_id"]
    assert 100 == response["input_tokens"]
    assert 50 == response["output_tokens"]
    assert 150 == response["total_tokens"]
    assert "elapsed_sec" in response
    assert [] == response["actual_steps"]
    assert answer == response["actual_answer"]


def test_run_agent_for_evaluation_status_error():
    chat_model = MagicMock(spec=BaseChatModel)
    error_message = "Some error"
    chat_model.invoke.side_effect = RuntimeError(error_message)

    agent = create_react_agent(
        model=chat_model,
        tools=[],
        prompt="You are Aragorn."
    )
    question_id = "question-42"
    messages = {"messages": [("user", "Where was Gondor when the Westfold fell?")]}
    response = run_agent_for_evaluation(agent, question_id, messages)
    assert 3 == len(response)
    assert question_id == response["question_id"]
    assert error_message == response["error"]
    assert "error" == response["status"]
