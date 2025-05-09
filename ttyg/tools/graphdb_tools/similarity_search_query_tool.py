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


class SimilaritySearchQueryTool(BaseGraphDBTool):
    """
    Tool, which uses GraphDB Similarity Index.
    Similarity Index must exist in order to use this tool.
    The agent generates the similarity search term, which is expanded in the SPARQL template.
    """

    class SearchInput(BaseModel):
        query: str = Field(description="FTS search query")

    min_graphdb_version: ClassVar[str] = "8.7"
    name: str = "similarity_search"
    description: str = "Query GraphDB by full-text search and return a subgraph of RDF triples."
    args_schema: Type[BaseModel] = SearchInput
    sparql_query_template: str = """PREFIX sim: <http://www.ontotext.com/graphdb/similarity/>
    PREFIX sim-index: <http://www.ontotext.com/graphdb/similarity/instance/>
    DESCRIBE ?documentID {{
        SELECT DISTINCT ?documentID {{
            ?search a sim-index:{index_name} ;
                sim:searchTerm "{query}";
                sim:documentResult ?result .
            ?result sim:value ?documentID ;
                sim:score ?score.
            FILTER(?score >= {similarity_score_threshold})
        }}
        ORDER BY DESC(?score)
        LIMIT {limit}
    }}"""
    limit: int = Field(default=10, ge=1)
    similarity_score_threshold: float = Field(default=0.6, ge=0)
    index_name: str

    @model_validator(mode="after")
    def check_similarity_index_exists(self) -> Self:
        if not self.graph.similarity_index_exists(self.index_name):
            raise ValueError(
                f"Similarity index with name \"{self.index_name}\" doesn't exist."
            )
        return self

    @timeit
    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        query = self.sparql_query_template.format(
            index_name=self.index_name,
            query=query,
            limit=self.limit,
            similarity_score_threshold=self.similarity_score_threshold,
        )
        logging.debug(f"Searching with similarity query {query}")
        query_results = self.graph.eval_sparql_query(query, validation=False)
        return json.dumps(query_results, indent=2)
