import json
import logging
from typing import (
    Optional,
    ClassVar,
)

from langchain_core.callbacks import CallbackManagerForToolRun
from openai.types import FunctionDefinition
from openai.types.beta import FunctionTool, AssistantToolParam
from pydantic import Field, model_validator
from typing_extensions import Self

from .base import BaseGraphDBTool


class RetrievalQueryTool(BaseGraphDBTool):
    """
    Tool, which uses GraphDB ChatGPT Retrieval Plugin Connector.
    ChatGPT Retrieval Plugin Connector must exist in order to use this tool.
    The agent generates the search query, which is expanded in the SPARQL template.
    """

    min_graphdb_version: ClassVar[str] = "10.4"
    name: str = "retrieval_search"
    description: str = "Query the vector database to retrieve relevant pieces of documents."
    function_tool: ClassVar[AssistantToolParam] = FunctionTool(
        type="function",
        function=FunctionDefinition(
            name=name,
            description=description,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "text query"
                    }
                },
                "required": [
                    "query"
                ],
                "additionalProperties": False,
            },
        )
    )
    sparql_query_template: str = """PREFIX retr: <http://www.ontotext.com/connectors/retrieval#>
    PREFIX retr-inst: <http://www.ontotext.com/connectors/retrieval/instance#>
    SELECT * {{
        [] a retr-inst:{connector_name} ;
            retr:query "{query}" ;
            retr:limit {limit} ;
            retr:entities ?entity .
        ?entity retr:snippets _:s .
        _:s retr:snippetField ?field ;
            retr:snippetText ?text .
    }}"""
    limit: int = Field(default=10, ge=1)
    connector_name: str

    @model_validator(mode="after")
    def check_retrieval_connector_exists(self) -> Self:
        if not self.graph.retrieval_connector_exists(self.connector_name):
            raise ValueError(
                f"ChatGPT Retrieval connector with name \"{self.connector_name}\" doesn't exist."
            )
        return self

    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        query = self.sparql_query_template.format(connector_name=self.connector_name, query=query, limit=self.limit)
        logging.debug(f"Searching with retrieval query {query}")
        query_results = self.graph.eval_sparql_query(query, validation=False)
        return json.dumps(query_results, indent=2)
