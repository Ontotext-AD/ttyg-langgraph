import json
import logging
from typing import ClassVar

import openai
from openai import OpenAI
from openai.types.beta import (
    Assistant,
    AssistantDeleted,
    Thread,
    ThreadDeleted,
)
from openai.types.beta.threads import Run, Message
from openai.types.beta.threads.run_submit_tool_outputs_params import ToolOutput
from pydantic import BaseModel, Field, ConfigDict
from typing_extensions import Self

from ..tools import Toolkit


class ThreadNotFoundError(Exception):
    pass


class RunStatusError(Exception):
    pass


class OpenAIAssistant(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    # OpenAI API documentation doesn't describe the exact limitations.
    # The values are configured empirically.
    # Minimum single tool output to model. A single output will stop being truncated at this
    # value (in case when repetitive truncation is still necessary)
    MIN_TOOL_OUTPUT: ClassVar[int] = 10_000
    # Maximum tool output. This is a hardcoded value and can be set lower than the maximum
    # of 256,000 but setting so probably doesn't make much sense. Note that the OpenAI
    # will say "more than 512k chars" if you go over the limit, but they probably count
    # bytes and each character is 2 bytes (UTF-16).
    MAX_TOTAL_TOOL_OUTPUT: ClassVar[int] = 256_000

    model: str
    temperature: float = Field(default=0, ge=0, le=2)
    instructions: str = Field(max_length=256_000)
    openai_client: OpenAI
    toolkit: Toolkit
    name: str = "Natural Language Querying Assistant"
    assistant: Assistant = Field(exclude=True)

    @classmethod
    def create(
            cls,
            model: str,
            temperature: float,
            instructions: str,
            openai_client: OpenAI,
            toolkit: Toolkit,
            name: str = "Natural Language Querying Assistant",
    ) -> Self:
        assistant = openai_client.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=toolkit.as_assistant_tool_params(),
            model=model,
            temperature=temperature,
        )
        logging.debug(f"Created assistant with id {assistant.id}")
        return cls(
            model=model,
            temperature=temperature,
            instructions=instructions,
            openai_client=openai_client,
            toolkit=toolkit,
            name=name,
            assistant=assistant,
        )

    def delete_assistant(self) -> AssistantDeleted:
        """
        Deletes the OpenAI Assistant.
        :return: the assistant deleted object
        :rtype: AssistantDeleted
        """
        logging.debug(f"Deleting assistant with id {self.assistant.id}")
        return self.openai_client.beta.assistants.delete(self.assistant.id)

    def create_thread(self) -> Thread:
        """
        Creates a new thread / conversation
        :return: the thread created
        :rtype: Thread
        """
        logging.debug(f"Creating a new thread.")
        thread = self.openai_client.beta.threads.create()
        logging.debug(f"Created thread {thread.id}")
        return thread

    def delete_thread(self, thread_id: str) -> ThreadDeleted:
        """
        Deletes a thread
        :param thread_id: the thread id, which should be deleted
        :type thread_id: str
        :return: the thread deleted object
        :rtype: ThreadDeleted
        """
        try:
            logging.debug(f"Deleting thread {thread_id}")
            return self.openai_client.beta.threads.delete(thread_id)
        except openai.NotFoundError:
            logging.debug(f"Thread {thread_id} not found.")
            raise ThreadNotFoundError(f"Thread {thread_id} not found.")

    def create_message_and_run(
            self,
            thread_id: str,
            message: str,
    ) -> str:
        """
        Creates / adds a message to a thread and creates a new run.
        :param thread_id: the thread id to which the message is added
        :type thread_id: str
        :param message: the message to be added to the thread
        :type message: str
        :return: the last message in the thread, when the run status is in terminal state.
        :rtype: str
        """
        self.__create_message(message, thread_id)
        run = self.__create_run_and_poll(thread_id)
        self.__handle_run(run, thread_id)
        return self.__get_last_message(thread_id)

    def __create_message(self, message: str, thread_id: str) -> Message:
        logging.debug(f"Adding message \"{message}\" to thread {thread_id}")

        try:
            return self.openai_client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
        except openai.NotFoundError:
            logging.debug(f"Thread {thread_id} not found.")
            raise ThreadNotFoundError(f"Thread {thread_id} not found.")

    def __create_run_and_poll(self, thread_id: str) -> Run:
        try:
            return self.openai_client.beta.threads.runs.create_and_poll(
                thread_id=thread_id,
                assistant_id=self.assistant.id,
            )
        except openai.NotFoundError:
            logging.debug(f"Thread {thread_id} not found.")
            raise ThreadNotFoundError(f"Thread {thread_id} not found.")

    def __handle_run(
            self,
            run: Run,
            thread_id: str,
    ) -> Run:
        if run.usage:
            logging.debug(
                f"Run {run.id} usage in tokens - "
                f"total: {run.usage.total_tokens}, "
                f"completion: {run.usage.completion_tokens}, "
                f"prompt: {run.usage.prompt_tokens}"
            )

        if run.status == "requires_action":
            logging.debug(f"Run {run.id} status is requires_action.")
            run = self.__handle_requires_action(run, thread_id)
            return self.__handle_run(run, thread_id)
        elif run.status == "completed":
            logging.debug(f"Run {run.id} status is completed.")
            return run
        elif run.status == "expired":
            logging.error(f"Run {run.id} status is expired. Expired at {run.expires_at}.")
            raise RunStatusError(f"Run {run.id} status is expired. Expired at {run.expires_at}.")
        elif run.status == "failed":
            logging.error(f"Run {run.id} status is failed. Failed at {run.failed_at}."
                          f"Run last error: {run.last_error}")
            raise RunStatusError(f"Run {run.id} status is failed. Failed at {run.failed_at}.")
        elif run.status == "incomplete":
            logging.error(f"Run {run.id} status is incomplete. Incomplete details: {run.incomplete_details}.")
            raise RunStatusError(f"Run {run.id} status is incomplete.")
        elif run.status == "cancelled":
            logging.error(f"Run {run.id} status is cancelled. Cancelled at {run.cancelled_at}.")
            raise RunStatusError(f"Run {run.id} status is cancelled. Cancelled at {run.cancelled_at}.")

    def __handle_requires_action(
            self,
            run: Run,
            thread_id: str,
    ) -> Run:
        tool_outputs = []

        for tool_call in run.required_action.submit_tool_outputs.tool_calls:

            function_called = tool_call.function
            functions_args = json.loads(function_called.arguments)
            logging.debug(f"{tool_call.id} calling function {function_called.name} with arguments \"{functions_args}\"")

            try:
                output = self.toolkit.call(function_called)
            except Exception as e:
                output = "Error: " + str(e)
            logging.debug(f"{tool_call.id} function {function_called.name} output \"{output}\"")
            tool_outputs.append(ToolOutput(tool_call_id=tool_call.id, output=output))

        self.__shorten_tool_outputs(tool_outputs)
        try:
            return self.openai_client.beta.threads.runs.submit_tool_outputs_and_poll(
                tool_outputs=tool_outputs,
                run_id=run.id,
                thread_id=thread_id,
            )
        except openai.NotFoundError:
            logging.debug(f"Thread {thread_id} not found.")
            raise ThreadNotFoundError(f"Thread {thread_id} not found.")

    def __get_last_message(self, thread_id: str) -> str:
        try:
            messages = self.openai_client.beta.threads.messages.list(
                thread_id=thread_id
            )
            return messages.data[0].content[0].text.value
        except openai.NotFoundError:
            logging.debug(f"Thread {thread_id} not found.")
            raise ThreadNotFoundError(f"Thread {thread_id} not found.")

    def __shorten_tool_outputs(self, tool_outputs: list[ToolOutput]) -> None:
        """
        A somewhat naive truncation of the tool outputs taken as a whole.
        If the entire output (combined from all tool calls) is above the MAX_TOOL_OUTPUT (256,000 characters),
        then the outputs are sorted by length in descending order,
        and until the entire output is fitted into the maximum,
        we repetitively remove the last line from each tool output.
        Outputs with length, which is less than MIN_TOOL_OUTPUT (10,000 chars), will not be truncated.
        """
        total_length = sum([len(tool_output["output"]) for tool_output in tool_outputs])

        if total_length > self.MAX_TOTAL_TOOL_OUTPUT:
            logging.warning(
                f"The size of all tool outputs {total_length:,} characters exceeds the maximum defined "
                f"size of {self.MAX_TOTAL_TOOL_OUTPUT}"
            )

            indexed_outputs = list(enumerate(tool_outputs))
            indexed_outputs.sort(key=lambda x: len(x[1]["output"]), reverse=True)

            previous_total_length = None
            while total_length > self.MAX_TOTAL_TOOL_OUTPUT and total_length != previous_total_length:
                previous_total_length = total_length
                for idx, s in indexed_outputs:
                    current_length = len(tool_outputs[idx]["output"])
                    if current_length <= self.MIN_TOOL_OUTPUT:
                        continue
                    o_short = self.__remove_last_line(tool_outputs[idx]["output"])
                    new_length = len(o_short)
                    total_length = total_length - current_length + new_length
                    tool_outputs[idx]["output"] = o_short
                    if total_length <= self.MAX_TOTAL_TOOL_OUTPUT:
                        break
                if total_length == previous_total_length:
                    raise ValueError("Unable to shorten tool outputs to fit into limit")
            logging.info(f"Truncated tool outputs to: {total_length:,} characters")

    def __remove_last_line(self, string: str) -> str:
        """
        Truncates the output to MAX_TOTAL_TOOL_OUTPUT characters,
        splits by new line, removes the last line,
        and returns the join by new line of the remaining lines
        :param string: string, which should be truncated
        :type string: str
        :return: the truncated string
        :rtype: str
        """
        lines = string[:self.MAX_TOTAL_TOOL_OUTPUT].split("\n")
        if lines:
            lines = lines[:-1]
        return "\n".join(lines)
