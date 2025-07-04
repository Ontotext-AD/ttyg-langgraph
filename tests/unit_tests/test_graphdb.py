import pytest
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed
from rdflib import Graph

from ttyg.graphdb import GraphDB

GRAPHDB_BASE_URL = "http://localhost:7200/"
GRAPHDB_REPOSITORY_ID = "starwars"


@pytest.fixture
def graphdb():
    yield GraphDB(
        base_url=GRAPHDB_BASE_URL,
        repository_id=GRAPHDB_REPOSITORY_ID,
    )


def test_eval_sparql_query_invalid_sparql_query_raises_value_error(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError) as exc:
        graphdb.eval_sparql_query("SELECT {?s ?p ?o}")
    assert "Expected SelectQuery, found '{'  (at char 7), (line:1, col:8)" == str(exc.value)


def test_eval_sparql_query_valid_update_query_raises_value_error(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError) as exc:
        graphdb.eval_sparql_query(
            "DELETE DATA { <https://swapi.co/resource/human/1> <https://swapi.co/vocabulary/eyeColor> \"blue\" }"
        )
    assert ("Expected {SelectQuery | ConstructQuery | DescribeQuery | AskQuery}, "
            "found 'DELETE'  (at char 0), (line:1, col:1)") == str(exc.value)


def test_eval_sparql_query_select_query(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        "PREFIX voc: <https://swapi.co/vocabulary/> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(results["results"]["bindings"])
    assert "PREFIX voc: <https://swapi.co/vocabulary/> SELECT * { ?character voc:eyeColor \"red\"}" == query


def test_eval_sparql_query_ask_query(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        "PREFIX voc: <https://swapi.co/vocabulary/> ASK { ?character voc:eyeColor ?eyeColor}"
    )
    assert True == results["boolean"]
    assert "PREFIX voc: <https://swapi.co/vocabulary/> ASK { ?character voc:eyeColor ?eyeColor}" == query


def test_eval_sparql_query_describe_query(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        "PREFIX voc: <https://swapi.co/vocabulary/> DESCRIBE voc:eyeColor"
    )
    results = Graph().parse(
        data=results,
        format="turtle",
    )
    assert 5 == len(results)
    assert "PREFIX voc: <https://swapi.co/vocabulary/> DESCRIBE voc:eyeColor" == query


def test_eval_sparql_query_construct_query(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        "PREFIX voc: <https://swapi.co/vocabulary/> "
        "CONSTRUCT {?character voc:eyeColor ?eyeColor} "
        "{?character voc:eyeColor ?eyeColor}"
    )
    results = Graph().parse(
        data=results,
        format="turtle",
    )
    assert 86 == len(results)
    assert ("PREFIX voc: <https://swapi.co/vocabulary/> "
            "CONSTRUCT {?character voc:eyeColor ?eyeColor} "
            "{?character voc:eyeColor ?eyeColor}") == query


def test_eval_sparql_query_missing_known_prefix_is_added(graphdb: GraphDB) -> None:
    with pytest.raises(QueryBadFormed) as exc:
        graphdb.eval_sparql_query(
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT * { ?character voc:eyeColor \"red\"}",
            validation=False,
        )
    assert ("QueryBadFormed: A bad request has been sent to the endpoint: probably the SPARQL query is badly formed. \n"
            "\n"
            "Response:\n"
            "b\"MALFORMED QUERY: QName 'voc:eyeColor' uses an undefined prefix\"") == str(exc.value)

    results, query = graphdb.eval_sparql_query(
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(results["results"]["bindings"])
    assert ("PREFIX voc: <https://swapi.co/vocabulary/> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
            "SELECT * { ?character voc:eyeColor \"red\"}") == query


def test_eval_sparql_query_missing_unknown_prefix(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError) as exc:
        graphdb.eval_sparql_query(
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT * { ?character unknown:eyeColor \"red\"}"
        )
    assert "The following prefixes are undefined: unknown" == str(exc.value)


def test_eval_sparql_query_wrong_prefix_is_fixed(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        "PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:eyeColor \"red\"}",
        validation=False,
    )
    assert 0 == len(results["results"]["bindings"])
    assert "PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:eyeColor \"red\"}" == query

    results, query = graphdb.eval_sparql_query(
        "PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(results["results"]["bindings"])
    assert "PREFIX voc: <https://swapi.co/vocabulary/> SELECT * { ?character voc:eyeColor \"red\"}" == query


def test_eval_sparql_query_iri_which_is_not_stored(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError) as exc:
        graphdb.eval_sparql_query("PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:unknown \"red\"}")
    assert ("The following IRIs are not used in the data stored in GraphDB: "
            "<https://swapi.co/vocabulary/unknown>") == str(exc.value)
