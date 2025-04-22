from pathlib import Path

import pytest
from ttyg.graphdb import GraphDB
from ttyg.tools import OntologySchemaAndVocabularyTool

GRAPHDB_BASE_URL = "http://localhost:7200/"
GRAPHDB_REPOSITORY_ID = "starwars"


@pytest.fixture
def graphdb():
    yield GraphDB(
        base_url=GRAPHDB_BASE_URL,
        repository_id=GRAPHDB_REPOSITORY_ID,
    )


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
