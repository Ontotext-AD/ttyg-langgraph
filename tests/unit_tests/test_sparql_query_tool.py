import json

import pytest

from ttyg.graphdb import GraphDB
from ttyg.tools import SparqlQueryTool

GRAPHDB_BASE_URL = "http://localhost:7200/"
GRAPHDB_REPOSITORY_ID = "starwars"


@pytest.fixture
def sparql_query_tool():
    graph = GraphDB(
        base_url=GRAPHDB_BASE_URL,
        repository_id=GRAPHDB_REPOSITORY_ID,
    )
    yield SparqlQueryTool(graph=graph)


def test_eval_sparql_query_invalid_sparql_query_raises_value_error(sparql_query_tool: SparqlQueryTool) -> None:
    with pytest.raises(ValueError) as exc:
        sparql_query_tool._run("SELECT {?s ?p ?o}")
    assert "Expected SelectQuery, found '{'  (at char 7), (line:1, col:8)" == str(exc.value)


def test_eval_sparql_query_valid_update_query_raises_value_error(sparql_query_tool: SparqlQueryTool) -> None:
    with pytest.raises(ValueError) as exc:
        sparql_query_tool._run(
            "DELETE DATA { <https://swapi.co/resource/human/1> <https://swapi.co/vocabulary/eyeColor> \"blue\" }"
        )
    assert ("Expected {SelectQuery | ConstructQuery | DescribeQuery | AskQuery}, "
            "found 'DELETE'  (at char 0), (line:1, col:1)") == str(exc.value)


def test_eval_sparql_query_select_query(sparql_query_tool: SparqlQueryTool) -> None:
    results, query = sparql_query_tool._run(
        "PREFIX voc: <https://swapi.co/vocabulary/> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(json.loads(results)["results"]["bindings"])
    assert "PREFIX voc: <https://swapi.co/vocabulary/> SELECT * { ?character voc:eyeColor \"red\"}" == query


def test_eval_sparql_query_ask_query(sparql_query_tool: SparqlQueryTool) -> None:
    results, query = sparql_query_tool._run(
        "PREFIX voc: <https://swapi.co/vocabulary/> ASK { ?character voc:eyeColor ?eyeColor}"
    )
    assert True == json.loads(results)["boolean"]
    assert "PREFIX voc: <https://swapi.co/vocabulary/> ASK { ?character voc:eyeColor ?eyeColor}" == query


def test_eval_sparql_query_missing_known_prefix_is_added(sparql_query_tool: SparqlQueryTool) -> None:
    results, query = sparql_query_tool._run(
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(json.loads(results)["results"]["bindings"])
    assert ("PREFIX voc: <https://swapi.co/vocabulary/> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
            "SELECT * { ?character voc:eyeColor \"red\"}") == query


def test_eval_sparql_query_missing_unknown_prefix(sparql_query_tool: SparqlQueryTool) -> None:
    with pytest.raises(ValueError) as exc:
        sparql_query_tool._run(
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT * { ?character unknown:eyeColor \"red\"}"
        )
    assert "The following prefixes are undefined: unknown" == str(exc.value)


def test_eval_sparql_query_wrong_prefix_is_fixed(sparql_query_tool: SparqlQueryTool) -> None:
    results, query = sparql_query_tool._run(
        "PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(json.loads(results)["results"]["bindings"])
    assert "PREFIX voc: <https://swapi.co/vocabulary/> SELECT * { ?character voc:eyeColor \"red\"}" == query


def test_eval_sparql_query_iri_which_is_not_stored(sparql_query_tool: SparqlQueryTool) -> None:
    with pytest.raises(ValueError) as exc:
        sparql_query_tool._run("PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:unknown \"red\"}")
    assert ("The following IRIs are not used in the data stored in GraphDB: "
            "<https://swapi.co/vocabulary/unknown>") == str(exc.value)
