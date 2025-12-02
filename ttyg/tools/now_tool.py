from datetime import datetime, timezone

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException

from ttyg.utils import timeit


class NowTool(BaseTool):
    """
    Tool, which returns the current UTC date time in yyyy-mm-ddTHH:MM:SS format
    """

    name: str = "now"
    description: str = "Returns the current UTC date time in yyyy-mm-ddTHH:MM:SS format. Do not reuse responses."
    handle_tool_error: bool = True

    @timeit
    def _run(
            self,
            run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        try:
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            raise ToolException(str(e))
