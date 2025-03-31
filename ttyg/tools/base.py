import json
from abc import ABC, abstractmethod
from typing import Iterable

from langchain_core.tools import BaseTool as LangChainBaseTool
from openai.types.beta import AssistantToolParam
from openai.types.beta.threads.required_action_function_tool_call import Function


class BaseTool(LangChainBaseTool, ABC):
    """Interface tools must implement."""

    @property
    @abstractmethod
    def function_tool(self) -> AssistantToolParam:
        """
        :return: the tool definition, which should be provided to the OpenAI API
        :rtype: AssistantToolParam
        """

    def call(self, *args, **kwargs) -> str:
        """
        :return: the output of the tool, which should be provided to the OpenAI API
        :rtype: str
        """
        return self._run(*args, **kwargs)


class Toolkit:
    """Representing a collection of tools."""

    def __init__(self, tools: list[BaseTool]):
        """
        Initializes the toolkit with all available tools.

        :param tools: list of the tools
        :type tools: list[BaseTool]
        """
        self.tools: dict[str, BaseTool] = {
            tool.name: tool
            for tool in tools
        }

    def as_assistant_tool_params(self) -> Iterable[AssistantToolParam]:
        """
        :return: the tools as expected from the OpenAI
        :rtype: Iterable[AssistantToolParam]
        """
        return [tool.function_tool for tool in self.tools.values()]

    def call(
            self,
            function_called: Function,
    ) -> str:
        """
        :param function_called: the function, which is called by the agent
        :type function_called: Function
        :return: the output of the called function as string
        :rtype: str
        """
        return self.tools.get(function_called.name).call(**json.loads(function_called.arguments))
