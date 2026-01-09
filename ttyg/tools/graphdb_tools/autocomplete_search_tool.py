import json
import logging
from typing import (
    Type,
    Tuple,
)

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import ToolException
from pydantic import Field, model_validator, BaseModel
from typing_extensions import Self

from ttyg.graphdb import GraphDBAutocompleteStatus, GraphDBRdfRankStatus
from ttyg.utils import timeit
from .base import BaseGraphDBTool
from .sparql_query_artifact import SparqlQueryArtifact


class AutocompleteSearchTool(BaseGraphDBTool):
    """
    Tool, which uses GraphDB Autocomplete index to search for IRIs by name and class.
    The agent generates the autocomplete search query and the target class, which are expanded in the SPARQL template.
    """

    class SearchInput(BaseModel):
        query: str = Field(description="autocomplete search query")
        result_class: str | None = Field(
            description="Optionally, filter the results by class. ",
            default=None,
        )
        limit: int | None = Field(description="limit the results", default=10, ge=1)

    name: str = "autocomplete_search"
    description: str = "Discover IRIs by searching their names and getting results in order of relevance."
    args_schema: Type[BaseModel] = SearchInput
    response_format: str = "content_and_artifact"
    sparql_query_template: str = """PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#>
SELECT ?iri ?name ?rank {{
    ?iri auto:query "{query}" ;
        {property_path} ?name ;{filter_clause}
        rank:hasRDFRank5 ?rank.
}}
ORDER BY DESC(?rank)
LIMIT {limit}"""
    property_path: str = Field(
        default="<http://www.w3.org/2000/01/rdf-schema#label>",
        examples=[
            "<http://www.w3.org/2000/01/rdf-schema#label> | <http://schema.org/name>",
        ],
    )

    @model_validator(mode="after")
    def graphdb_config(self) -> Self:
        autocomplete_status = self.graph.get_autocomplete_status()
        if autocomplete_status != GraphDBAutocompleteStatus.READY:
            logging.warning(
                f"The Autocomplete index status of the repository is \"{autocomplete_status.name}\". "
                f"It's recommended the status to be READY in order to use the Autocomplete search tool."
            )

        rdf_rank_status = self.graph.get_rdf_rank_status()
        if rdf_rank_status != GraphDBRdfRankStatus.COMPUTED:
            logging.warning(
                f"The RDF Rank status of the repository is \"{rdf_rank_status.name}\". "
                f"It's recommended the status to be COMPUTED in order to use the Autocomplete search tool."
            )
        return self

    @timeit
    def _run(
        self,
        query: str,
        limit: int | None = 10,
        result_class: str | None = None,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> Tuple[str, SparqlQueryArtifact]:
        try:
            query = self.sparql_query_template.format(
                query=query,
                property_path=self.property_path,
                filter_clause=f" a {result_class} ;" if result_class else "",
                limit=limit,
            )
            logging.debug(f"Searching with autocomplete query {query}")
            query_results, actual_query = self.graph.eval_sparql_query(query)
            return json.dumps(query_results, indent=2), SparqlQueryArtifact(query=actual_query)
        except Exception as e:
            raise ToolException(str(e))
