import logging
from functools import cached_property
from pathlib import Path
from typing import Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import model_validator, computed_field
from pyparsing import ParseException
from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery
from typing_extensions import Self

from ttyg.utils import timeit
from .base import BaseGraphDBTool


class OntologySchemaAndVocabularyTool(BaseGraphDBTool):
    """
    Tool, which returns the configured ontology schema and vocabulary for the SPARQL queries.
    The ontology schema can be provided either with a path to a file in turtle format containing the ontology schema statements,
    or with a SPARQL CONSTRUCT query, which returns all the ontology schema statements.
    """

    name: str = "ontology_schema_and_vocabulary_tool"
    description: str = "Tool, which returns the configured ontology schema and vocabulary for the SPARQL queries"
    ontology_schema_file_path: Optional[Path] = None
    ontology_schema_query: Optional[str] = None

    @model_validator(mode="after")
    def valid_ontology_query(self) -> Self:
        """
        Validate the query is a valid SPARQL CONSTRUCT query
        """

        if self.ontology_schema_query:
            try:
                parsed_query = prepareQuery(self.ontology_schema_query)
            except ParseException as e:
                raise ValueError("Ontology query is not a valid SPARQL query.", e)

            if parsed_query.algebra.name != "ConstructQuery":
                raise ValueError(
                    "Invalid query type. Only CONSTRUCT queries are supported."
                )

        return self

    @model_validator(mode="after")
    def validate(self) -> Self:
        if self.ontology_schema_file_path and self.ontology_schema_query:
            raise ValueError(
                "Expected only one of ontology schema file path or ontology schema query. Both are provided."
            )
        if (not self.ontology_schema_file_path) and (not self.ontology_schema_query):
            raise ValueError(
                "Neither ontology schema file path nor ontology schema query is provided."
            )
        return self

    @computed_field
    @cached_property
    def schema_graph(self) -> Graph:
        if self.ontology_schema_query:
            logging.debug("Configuring the ontology schema with query.")
            schema_graph = Graph().parse(
                data=self.graph.eval_sparql_query(self.ontology_schema_query, validation=False),
                format="turtle",
            )
            logging.debug(f"Collected {len(schema_graph)} ontology schema statements.")
            return schema_graph
        else:
            logging.debug("Configuring the ontology schema with file.")
            schema_graph = Graph().parse(
                data=self.ontology_schema_file_path.read_text(),
                format="turtle",
            )
            logging.debug(f"Collected {len(schema_graph)} ontology schema statements.")
            return schema_graph

    @timeit
    def _run(
            self,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return self.schema_graph.serialize(format="turtle")
