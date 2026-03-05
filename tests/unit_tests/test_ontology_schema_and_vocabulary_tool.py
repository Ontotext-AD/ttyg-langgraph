from pathlib import Path

import pytest
from rdflib import Graph

from ttyg.graphdb import GraphDB
from ttyg.tools import OntologySchemaAndVocabularyTool
from .constants import GRAPHDB_REPOSITORY_ID


def test_both_file_and_query_are_provided(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError):
        OntologySchemaAndVocabularyTool(
            graph=graphdb,
            ontology_schema_file_path=Path("/some/path/to/file.ttl"),
            ontology_schema_query="CONSTRUCT {?s ?p ?o} {?s ?p ?o}"
        )


def test_neither_file_nor_query_is_provided(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError):
        OntologySchemaAndVocabularyTool(
            graph=graphdb,
        )


def test_wrong_query_type(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError):
        OntologySchemaAndVocabularyTool(
            graph=graphdb,
            ontology_schema_query="SELECT * { ?s ?p ?o }"
        )


def test_wrong_query_syntax(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError):
        OntologySchemaAndVocabularyTool(
            graph=graphdb,
            ontology_schema_query="SELECT * { ?s ?p ?o "
        )


def test_missing_graphdb_repository_id(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError):
        OntologySchemaAndVocabularyTool(
            graph=graphdb,
            ontology_schema_query="""
CONSTRUCT {
    ?s ?p ?o
} WHERE {
    VALUES ?s {<https://swapi.co/vocabulary/>}
    ?s ?p ?o
}""",
        )


def test_run(graphdb: GraphDB) -> None:
    ontology_schema_and_vocabulary_tool = OntologySchemaAndVocabularyTool(
        graph=graphdb,
        ontology_schema_query="""
CONSTRUCT {
    ?s ?p ?o
} WHERE {
    VALUES ?s {<https://swapi.co/vocabulary/>}
    ?s ?p ?o
}""",
        graphdb_repository_id=GRAPHDB_REPOSITORY_ID,
    )
    results = ontology_schema_and_vocabulary_tool._run()
    graph = Graph().parse(
        data=results,
        format="turtle",
    )
    assert len(graph) > 0
