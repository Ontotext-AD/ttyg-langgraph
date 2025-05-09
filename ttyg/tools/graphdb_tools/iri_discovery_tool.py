import json
import logging
from typing import (
    Any,
    Optional,
    ClassVar,
    Type,
)

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import Field, model_validator, BaseModel
from typing_extensions import Self

from ttyg.graphdb import GraphDB
from ttyg.utils import timeit
from .base import BaseGraphDBTool


def _get_default_sparql_template(validated_data: dict[str, Any]) -> str:
    graph: GraphDB = validated_data["graph"]
    graphdb_version = graph.version
    major, minor, _ = graphdb_version.split(".")
    major, minor = int(major), int(minor)

    if major >= 10 and minor >= 8:
        return """PREFIX onto: <http://www.ontotext.com/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>
PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
SELECT ?iri ?label {{
    ?label onto:fts ("{query}" "*").
    ?iri rdfs:label|skos:prefLabel|schema:name ?label.
    ?iri rank:hasRDFRank ?rank .
}}
ORDER BY DESC(?rank)
LIMIT {limit}"""
    else:
        return """PREFIX onto: <http://www.ontotext.com/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>
PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
SELECT ?iri ?label {{
    ?label onto:fts ("{query}").
    ?iri rdfs:label|skos:prefLabel|schema:name ?label.
    ?iri rank:hasRDFRank ?rank .
}}
ORDER BY DESC(?rank)
LIMIT {limit}"""


class IRIDiscoveryTool(BaseGraphDBTool):
    """
    Tool, which uses GraphDB full-text search (FTS), to discover IRIs of concepts.
    The full-text search (FTS) must be enabled for the repository in order to use this tool.
    For details how to enable it check the documentation https://graphdb.ontotext.com/documentation/10.8/full-text-search.html#simple-full-text-search-index.
    It's also recommended to compute the RDF rank for the repository.
    For details how to compute it refer to the documentation https://graphdb.ontotext.com/documentation/10.8/ranking-results.html.
    The agent generates the fts search query, which is expanded in the SPARQL template.
    """

    class SearchInput(BaseModel):
        query: str = Field(description="FTS search query")

    min_graphdb_version: ClassVar[str] = "10.1"
    name: str = "iri_discovery"
    description: str = "Discovery IRIs by full-text search in labels."
    args_schema: Type[BaseModel] = SearchInput
    query_template: str = Field(default_factory=lambda validated_data: _get_default_sparql_template(validated_data))
    limit: int = Field(default=10, ge=1)

    @model_validator(mode="after")
    def graphdb_config(self) -> Self:
        if not self.graph.fts_is_enabled():
            raise ValueError(
                "You must enable the full-text search (FTS) index for the repository "
                "to use the IRI discovery tool."
            )

        if not self.graph.rdf_rank_is_computed():
            logging.warning(
                "The RDF Rank for the repository is not computed. It's recommended to compute it "
                "in order to use the IRI discovery tool."
            )

        return self

    @timeit
    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        query = self.query_template.format(query=query, limit=self.limit)
        logging.debug(f"Searching with iri discovery {query}")
        query_results = self.graph.eval_sparql_query(query, validation=False)
        return json.dumps(query_results, indent=2)
