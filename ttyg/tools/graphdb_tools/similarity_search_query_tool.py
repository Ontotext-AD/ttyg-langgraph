import logging
from typing import (
    ClassVar,
    Type,
    Tuple,
)

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import Field, model_validator, BaseModel
from typing_extensions import Self

from ttyg.utils import timeit
from .sparql_query_artifact import SparqlQueryArtifact
from .sparql_query_tool import SparqlQueryTool
from .utils import to_sparql_literal


class SimilaritySearchQueryTool(SparqlQueryTool):
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
            sim:searchTerm {query};
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
        if not self.graph.similarity_index_exists(self.graphdb_repository_id, self.index_name):
            logging.warning(
                f"Similarity index with name \"{self.index_name}\" doesn't exist."
            )
        return self

    @timeit
    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> Tuple[str, SparqlQueryArtifact]:
        sparql_query = self.sparql_query_template.format(
            index_name=self.index_name,
            query=to_sparql_literal(query),
            limit=self.limit,
            similarity_score_threshold=self.similarity_score_threshold,
        )
        logging.debug(f"Searching with similarity query {sparql_query}")
        return super()._run(query=sparql_query, validation=False)
