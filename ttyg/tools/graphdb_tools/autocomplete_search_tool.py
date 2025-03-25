import json
import logging
from typing import (
    Optional,
    ClassVar,
    Type,
)

from langchain_core.callbacks import CallbackManagerForToolRun
from openai.types import FunctionDefinition
from openai.types.beta import FunctionTool, AssistantToolParam
from pydantic import Field, model_validator, BaseModel
from typing_extensions import Self

from .base import BaseGraphDBTool


class AutocompleteSearchTool(BaseGraphDBTool):
    """
    Tool, which uses GraphDB Autocomplete index to search for IRIs by name and class.
    The agent generates the autocomplete search query and the target class, which are expanded in the SPARQL template.
    """

    class SearchInput(BaseModel):
        query: str = Field(description="autocomplete search query")
        result_class: Optional[str] = Field(description="Filter the results by class. "
                                                        "A valid value is the full IRI of one class from the ontology. "
                                                        "Do not use prefixes to shorten the full IRI.")

    name: str = "autocomplete_search"
    description: str = "Discover IRIs by searching their names and getting results in order of relevance."
    args_schema: Type[BaseModel] = SearchInput
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
                        "description": "Autocomplete search query"
                    },
                    "result_class": {
                        "type": "string",
                        "description": "Filter the results by class. "
                                       "A valid value is the full IRI of one class from the ontology. "
                                       "Do not use prefixes to shorten the full IRI."
                    }
                },
                "required": [
                    "query"
                ],
                "additionalProperties": False,
            },
        )
    )
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
    limit: int = Field(default=10, ge=1)
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

    def _run(
            self,
            query: str,
            result_class: Optional[str],
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        query = self.sparql_query_template.format(
            query=query,
            property_path=self.property_path,
            filter_clause=f"a <{result_class}> ;" if result_class else "",
            limit=self.limit,
        )
        logging.debug(f"Searching with autocomplete query {query}")
        query_results = self.graph.eval_sparql_query(query, validation=False)
        return json.dumps(query_results, indent=2)
