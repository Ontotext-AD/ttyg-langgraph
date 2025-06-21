import json
import logging
from typing import (
    Optional,
    Type,
)

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import Field, model_validator, BaseModel
from typing_extensions import Self

from ttyg.utils import timeit
from .base import BaseGraphDBTool


class AutocompleteSearchTool(BaseGraphDBTool):
    """
    Tool, which uses GraphDB Autocomplete index to search for IRIs by name and class.
    The agent generates the autocomplete search query and the target class, which are expanded in the SPARQL template.
    """

    class SearchInput(BaseModel):
        query: str = Field(description="autocomplete search query")
        result_class: Optional[str] = Field(
            description="Optionally, filter the results by class. ",
            default=None,
        )
        limit: Optional[int] = Field(description="limit the results", default=10, ge=1)

    name: str = "autocomplete_search"
    description: str = "Discover IRIs by searching their names and getting results in order of relevance."
    args_schema: Type[BaseModel] = SearchInput
    sparql_query_template: str = """PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
    PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#>
    SELECT ?iri ?name ?rank {{
        ?iri auto:query "{query}" ;
            {property_path} ?name ;
            {filter_clause}
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
        if not self.graph.autocomplete_is_enabled():
            raise ValueError(
                "You must enable the autocomplete index for the repository "
                "to use the Autocomplete search tool."
            )

        if not self.graph.rdf_rank_is_computed():
            logging.warning(
                "The RDF Rank for the repository is not computed. It's recommended to compute it "
                "in order to use the Autocomplete search tool."
            )
        return self

    @timeit
    def _run(
            self,
            query: str,
            limit: Optional[int] = 10,
            result_class: Optional[str] = None,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        query = self.sparql_query_template.format(
            query=query,
            property_path=self.property_path,
            filter_clause=f"a {result_class} ;" if result_class else "",
            limit=limit,
        )
        logging.debug(f"Searching with autocomplete query {query}")
        query_results = self.graph.eval_sparql_query(query)
        return json.dumps(query_results, indent=2)
