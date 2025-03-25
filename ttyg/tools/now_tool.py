from datetime import datetime, timezone
from typing import Optional, ClassVar

from langchain_core.callbacks import CallbackManagerForToolRun
from openai.types import FunctionDefinition
from openai.types.beta import FunctionTool, AssistantToolParam

from .base import BaseTool


class NowTool(BaseTool):
    """
    Tool, which returns the current UTC date time in yyyy-mm-ddTHH:MM:SS format
    """

    name: str = "now"
    description: str = "Returns the current UTC date time in yyyy-mm-ddTHH:MM:SS format. Do not reuse responses."
    function_tool: ClassVar[AssistantToolParam] = FunctionTool(
        type="function",
        function=FunctionDefinition(
            name=name,
            description=description,
        )
    )

    def _run(
            self,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
