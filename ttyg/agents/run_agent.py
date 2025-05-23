import logging
import time
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph.graph import CompiledGraph


def run_agent(
        agent: CompiledGraph,
        input_: dict[str, Any] | Any,
        config: RunnableConfig | None = None,
        last_message_id: str = None,
) -> str:
    sum_input_tokens, sum_output_tokens, sum_total_tokens = 0, 0, 0

    start = time.time()
    for s in agent.stream(input_, config, stream_mode="values"):
        messages = s["messages"]
        for message in reversed(messages):
            if message.id == last_message_id:
                break

            message.pretty_print()
            if hasattr(message, "usage_metadata"):
                usage_metadata = message.usage_metadata
                input_tokens, output_tokens, total_tokens = usage_metadata["input_tokens"], usage_metadata[
                    "output_tokens"], usage_metadata["total_tokens"]
                sum_input_tokens += input_tokens
                sum_output_tokens += output_tokens
                sum_total_tokens += total_tokens
                logging.debug(
                    f"Usage: input tokens: {input_tokens}, "
                    f"output tokens: {output_tokens}, "
                    f"total tokens: {total_tokens}")

        last_message_id = messages[-1].id

    logging.debug(
        f"Total usage: input tokens: {sum_input_tokens}, "
        f"output tokens: {sum_output_tokens}, "
        f"total tokens: {sum_total_tokens}"
    )
    logging.debug(
        f"Elapsed time: {time.time() - start:.2f} seconds"
    )
    return last_message_id
