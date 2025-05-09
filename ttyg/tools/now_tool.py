from datetime import datetime, timezone
from typing import Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool

from ttyg.utils import timeit


class NowTool(BaseTool):
    """
    Tool, which returns the current UTC date time in yyyy-mm-ddTHH:MM:SS format
    """

    name: str = "now"
    description: str = "Returns the current UTC date time in yyyy-mm-ddTHH:MM:SS format. Do not reuse responses."

    @timeit
    def _run(
            self,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
