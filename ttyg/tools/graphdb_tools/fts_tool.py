import logging
from typing import (
    Any,
    ClassVar,
    Type,
    Tuple,
)

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import Field, model_validator, BaseModel
from typing_extensions import Self

from ttyg.graphdb import GraphDB, GraphDBRdfRankStatus
from ttyg.utils import timeit
from .sparql_query_artifact import SparqlQueryArtifact
from .sparql_query_tool import SparqlQueryTool


def _get_default_sparql_template(validated_data: dict[str, Any]) -> str:
    graph: GraphDB = validated_data["graph"]
    graphdb_version = graph.version
    major, minor, _ = graphdb_version.split(".")
    major, minor = int(major), int(minor)

    if major >= 10 and minor >= 8:
        return """PREFIX onto: <http://www.ontotext.com/>
PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
DESCRIBE ?iri {{
SELECT DISTINCT ?iri {{
    ?x onto:fts ("{query}" "*") {{
        ?x ?p ?iri .
    }} UNION {{
        ?iri ?p ?x .
    }}
    ?iri rank:hasRDFRank ?rank.
}}
ORDER BY DESC(?rank)
LIMIT {limit}
}}"""
    else:
        return """PREFIX onto: <http://www.ontotext.com/>
PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
DESCRIBE ?iri {{
SELECT DISTINCT ?iri {{
    ?x onto:fts ("{query}") {{
        ?x ?p ?iri .
    }} UNION {{
        ?iri ?p ?x .
    }}
    ?iri rank:hasRDFRank ?rank.
}}
ORDER BY DESC(?rank)
LIMIT {limit}
}}"""


class FTSTool(SparqlQueryTool):
    """
    Tool, which uses GraphDB full-text search (FTS).
    The full-text search (FTS) must be enabled for the repository in order to use this tool.
    For details how to enable it check the documentation
    https://graphdb.ontotext.com/documentation/11.3/full-text-search.html#simple-full-text-search-index .
    It's also recommended to compute the RDF rank for the repository.
    For details how to compute it refer to the documentation
    https://graphdb.ontotext.com/documentation/11.3/ranking-results.html .
    The agent generates the fts search query, which is expanded in the SPARQL template.
    """

    class SearchInput(BaseModel):
        query: str = Field(description="FTS search query")

    min_graphdb_version: ClassVar[str] = "10.1"
    name: str = "fts_search"
    description: str = "Query GraphDB by full-text search and return a subgraph of RDF triples."
    args_schema: Type[BaseModel] = SearchInput

    query_template: str = Field(default_factory=lambda validated_data: _get_default_sparql_template(validated_data))
    limit: int = Field(default=10, ge=1)

    @model_validator(mode="after")
    def graphdb_config(self) -> Self:
        if not self.graph.fts_is_enabled(self.graphdb_repository_id):
            logging.warning(
                "You must enable the full-text search (FTS) index for the repository "
                "to use the full-text search (FTS) tool."
            )

        rdf_rank_status = self.graph.get_rdf_rank_status(self.graphdb_repository_id)
        if rdf_rank_status != GraphDBRdfRankStatus.COMPUTED:
            logging.warning(
                f"The RDF Rank status of the repository is \"{rdf_rank_status.name}\". "
                f"It's recommended the status to be COMPUTED in order to use the full-text search (FTS) tool."
            )

        return self

    @timeit
    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> Tuple[str, SparqlQueryArtifact]:
        query = self.query_template.format(query=query, limit=self.limit)
        logging.debug(f"Searching with FTS query {query}")
        return super()._run(query=query, validation=False)
