from langchain.agents import create_agent
from langchain_core.language_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langsmith.schemas import UsageMetadata

from ttyg.agents import run_agent


def test_run_agent():
    chat_model = FakeMessagesListChatModel(responses=[
        AIMessage(content="The weather is sunny",
                  usage_metadata=UsageMetadata(input_tokens=100, output_tokens=50, total_tokens=150))
    ])
    agent = create_agent(
        model=chat_model,
        system_prompt="You are a helpful assistant",
        checkpointer=InMemorySaver(),
    )
    messages = {"messages": [("user", "What's the weather in Sofia today?")]}
    run_agent(agent, messages, RunnableConfig(configurable={"thread_id": "thread-1234"}))
