import json
import logging
from typing import (
    Optional,
    ClassVar,
    Type,
)

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import Field, model_validator, BaseModel
from typing_extensions import Self

from ttyg.utils import timeit
from .base import BaseGraphDBTool


class RetrievalQueryTool(BaseGraphDBTool):
    """
    Tool, which uses GraphDB ChatGPT Retrieval Plugin Connector.
    ChatGPT Retrieval Plugin Connector must exist in order to use this tool.
    The agent generates the search query, which is expanded in the SPARQL template.
    """

    class SearchInput(BaseModel):
        query: str = Field(description="text query")
        limit: Optional[int] = Field(description="limit the results", default=5, ge=1)
        score: Optional[float] = Field(description="filter the results by score", default=0, ge=0, le=1)

    min_graphdb_version: ClassVar[str] = "10.4"
    name: str = "retrieval_search"
    description: str = "Query the vector database to retrieve relevant pieces of documents."
    args_schema: Type[BaseModel] = SearchInput
    sparql_query_template: str = """PREFIX retr: <http://www.ontotext.com/connectors/retrieval#>
    PREFIX retr-inst: <http://www.ontotext.com/connectors/retrieval/instance#>
    SELECT * {{
        [] a retr-inst:{connector_name} ;
            retr:query "{query}" ;
            retr:limit {limit} ;
            retr:entities ?entity .
        ?entity retr:snippets _:s ;
            retr:score ?score;
        _:s retr:snippetField ?field ;
            retr:snippetText ?text .
        FILTER (?score > {score})
    }}"""
    connector_name: str

    @model_validator(mode="after")
    def check_retrieval_connector_exists(self) -> Self:
        if not self.graph.retrieval_connector_exists(self.connector_name):
            raise ValueError(
                f"ChatGPT Retrieval connector with name \"{self.connector_name}\" doesn't exist."
            )
        return self

    @timeit
    def _run(
            self,
            query: str,
            limit: Optional[int] = 5,
            score: Optional[float] = 0,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        query = self.sparql_query_template.format(
            connector_name=self.connector_name,
            query=query,
            limit=limit,
            score=score,
        )
        logging.debug(f"Searching with retrieval query {query}")
        query_results = self.graph.eval_sparql_query(query, validation=False)
        return json.dumps(query_results, indent=2)
