import io
from unittest.mock import MagicMock, patch

import httpx
import pytest
from rdflib.contrib.graphdb.exceptions import (
    RepositoryNotFoundError,
    RepositoryNotHealthyError,
)
from rdflib.query import Result

from ttyg.graphdb import GraphDB
from ttyg.graphdb import GraphDBAutocompleteStatus, GraphDBRdfRankStatus
from .constants import GRAPHDB_REPOSITORY_ID


def test_health_existing_repository(graphdb: GraphDB) -> None:
    response = graphdb.health(GRAPHDB_REPOSITORY_ID)
    assert response.status_code == 200
    assert response.json() == {
        "name": f"{GRAPHDB_REPOSITORY_ID}",
        "status": "green",
        "components": [
            {
                "name": "repository-state",
                "status": "green",
                "message": "RUNNING"
            },
            {
                "name": "read-availability",
                "status": "green"
            },
            {
                "name": "storage-folder",
                "status": "green"
            },
            {
                "name": "long-running-queries",
                "status": "green"
            },
            {
                "name": "predicates-statistics",
                "status": "green"
            },
            {
                "name": "write-availability",
                "status": "green",
                "message": "Not in a cluster"
            },
            {
                "name": "plugins",
                "status": "green",
                "components": [
                    {
                        "name": "chatgpt-retrieval-connector",
                        "status": "green",
                        "components": []
                    },
                    {
                        "name": "elasticsearch-connector",
                        "status": "green",
                        "components": []
                    },
                    {
                        "name": "entity-change",
                        "status": "green",
                        "components": []
                    },
                    {
                        "name": "kafka-connector",
                        "status": "green",
                        "components": []
                    },
                    {
                        "name": "lucene-connector",
                        "status": "green",
                        "components": []
                    },
                    {
                        "name": "opensearch-connector",
                        "status": "green",
                        "components": []
                    },
                    {
                        "name": "solr-connector",
                        "status": "green",
                        "components": []
                    }
                ]
            }
        ]
    }


def test_health_missing_repository(graphdb: GraphDB) -> None:
    with pytest.raises(RepositoryNotFoundError) as exc:
        graphdb.health("missing_repository")
    assert "Repository missing_repository not found." == str(exc.value)


def test_health_unhealthy_repository() -> None:
    repository_id = "unhealthy_repository"

    mocked_health_response = MagicMock(spec=httpx.Response)
    mocked_health_response.status_code = 500
    mocked_health_response.text = "Internal Server Error"
    mocked_health_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="500 Server Error",
        request=MagicMock(),
        response=mocked_health_response
    )

    with patch("ttyg.graphdb.graphdb.GraphDBClient") as mocked_graphdb_client:
        graphdb_client = mocked_graphdb_client.return_value
        graphdb_client.http_client.get.return_value = mocked_health_response

        graphdb = GraphDB(base_url="http://fake-graphdb:7200")

        with pytest.raises(RepositoryNotHealthyError) as exc:
            graphdb.health(repository_id)
        assert "Repository unhealthy_repository is not healthy. 500 - Internal Server Error" == str(exc.value)

        graphdb_client.http_client.get.assert_called_once_with(
            f"/repositories/{repository_id}/health",
            params={"passive": "5"}
        )


def test_eval_sparql_query_invalid_sparql_query_raises_value_error(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError) as exc:
        graphdb.eval_sparql_query(GRAPHDB_REPOSITORY_ID, "SELECT {?s ?p ?o}")
    assert "Expected SelectQuery, found '{'  (at char 7), (line:1, col:8)" == str(exc.value)


def test_eval_sparql_query_valid_update_query_raises_value_error(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError) as exc:
        graphdb.eval_sparql_query(
            GRAPHDB_REPOSITORY_ID,
            "DELETE DATA { <https://swapi.co/resource/human/1> <https://swapi.co/vocabulary/eyeColor> \"blue\" }"
        )
    assert ("Expected {SelectQuery | ConstructQuery | DescribeQuery | AskQuery}, "
            "found 'DELETE'  (at char 0), (line:1, col:1)") == str(exc.value)


def test_eval_sparql_query_select_query(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX voc: <https://swapi.co/vocabulary/> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(results.bindings)
    assert ("PREFIX voc: <https://swapi.co/vocabulary/>\n"
            "SELECT * { ?character voc:eyeColor \"red\"}") == query


def test_eval_sparql_query_ask_query(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX voc: <https://swapi.co/vocabulary/> ASK { ?character voc:eyeColor ?eyeColor}"
    )
    assert True == results.askAnswer
    assert ("PREFIX voc: <https://swapi.co/vocabulary/>\n"
            "ASK { ?character voc:eyeColor ?eyeColor}") == query


def test_eval_sparql_query_describe_query(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX voc: <https://swapi.co/vocabulary/> DESCRIBE voc:eyeColor"
    )
    assert 5 == len(results.graph)
    assert ("PREFIX voc: <https://swapi.co/vocabulary/>\n"
            "DESCRIBE voc:eyeColor") == query


def test_eval_sparql_query_construct_query(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX voc: <https://swapi.co/vocabulary/> "
        "CONSTRUCT {?character voc:eyeColor ?eyeColor} "
        "{?character voc:eyeColor ?eyeColor}"
    )
    assert 86 == len(results.graph)
    assert ("PREFIX voc: <https://swapi.co/vocabulary/>\n"
            "CONSTRUCT {?character voc:eyeColor ?eyeColor} "
            "{?character voc:eyeColor ?eyeColor}") == query


def test_eval_sparql_query_missing_known_prefix_is_added(graphdb: GraphDB) -> None:
    with pytest.raises(Exception) as exc:
        graphdb.eval_sparql_query(
            GRAPHDB_REPOSITORY_ID,
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT * { ?character voc:eyeColor \"red\"}",
            validation=False,
        )
    assert "Unknown namespace prefix : voc" == str(exc.value)

    results, query = graphdb.eval_sparql_query(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(results.bindings)
    assert ("PREFIX voc: <https://swapi.co/vocabulary/>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "SELECT * { ?character voc:eyeColor \"red\"}") == query


def test_eval_sparql_query_missing_unknown_prefix(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError) as exc:
        graphdb.eval_sparql_query(
            GRAPHDB_REPOSITORY_ID,
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT * { ?character unknown:eyeColor \"red\"}"
        )
    assert "The following prefixes are undefined: unknown" == str(exc.value)


def test_eval_sparql_query_wrong_prefix_is_fixed(graphdb: GraphDB) -> None:
    results, query = graphdb.eval_sparql_query(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:eyeColor \"red\"}",
        validation=False,
    )
    assert 0 == len(results.bindings)
    assert "PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:eyeColor \"red\"}" == query

    results, query = graphdb.eval_sparql_query(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:eyeColor \"red\"}"
    )
    assert 6 == len(results.bindings)
    assert ("PREFIX voc: <https://swapi.co/vocabulary/>\n"
            "SELECT * { ?character voc:eyeColor \"red\"}") == query


def test_eval_sparql_query_iri_which_is_not_stored(graphdb: GraphDB) -> None:
    with pytest.raises(ValueError) as exc:
        graphdb.eval_sparql_query(
            GRAPHDB_REPOSITORY_ID,
            "PREFIX voc: <https://swapi.co/voc/> SELECT * { ?character voc:unknown \"red\"}"
        )
    assert ("The following IRIs are not used in the data stored in GraphDB: "
            "<https://swapi.co/vocabulary/unknown>") == str(exc.value)


@pytest.mark.parametrize(
    "raw_value, expected_status",
    [
        ("READY", GraphDBAutocompleteStatus.READY),
        ("READY_CONFIG", GraphDBAutocompleteStatus.READY_CONFIG),
        ("ERROR", GraphDBAutocompleteStatus.ERROR),
        ("ERROR: java.lang.NullPointerException: Cannot load from object array because 'pagesArray' is null",
         GraphDBAutocompleteStatus.ERROR),
        ("something_unexpected", GraphDBAutocompleteStatus.ERROR),
        ("NONE", GraphDBAutocompleteStatus.NONE),
        ("BUILDING", GraphDBAutocompleteStatus.BUILDING),
        ("CANCELED", GraphDBAutocompleteStatus.CANCELED),
    ],
)
def test_get_autocomplete_status(raw_value: str, expected_status: GraphDBAutocompleteStatus):
    client = MagicMock(spec=GraphDB)
    client.get_autocomplete_status = GraphDB.get_autocomplete_status.__get__(client)
    json_data = f"""{{
        "head": {{ "vars": [ "status" ] }},
        "results": {{
            "bindings": [
                {{ "status": {{ "type": "literal", "value": "{raw_value}" }} }}
            ]
        }}
    }}"""
    mock_result = Result.parse(io.BytesIO(json_data.encode("utf-8")), format="json")
    client.eval_sparql_query.return_value = (mock_result, None)
    status = client.get_autocomplete_status(GRAPHDB_REPOSITORY_ID)

    assert status == expected_status
    client.eval_sparql_query.assert_called_once_with(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#> SELECT ?status { ?s auto:status ?status }",
        validation=False
    )


def test_get_autocomplete_status_empty_binding():
    client = MagicMock(spec=GraphDB)
    client.get_autocomplete_status = GraphDB.get_autocomplete_status.__get__(client)
    json_data = f"""{{
        "head": {{ "vars": [ "status" ] }},
        "results": {{
            "bindings": [ ]
        }}
    }}"""
    mock_result = Result.parse(io.BytesIO(json_data.encode("utf-8")), format="json")
    client.eval_sparql_query.return_value = (mock_result, None)
    status = client.get_autocomplete_status(GRAPHDB_REPOSITORY_ID)

    assert status == GraphDBAutocompleteStatus.ERROR
    client.eval_sparql_query.assert_called_once_with(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#> SELECT ?status { ?s auto:status ?status }",
        validation=False
    )


@pytest.mark.parametrize(
    "raw_value, expected_status",
    [
        ("CANCELED", GraphDBRdfRankStatus.CANCELED),
        ("COMPUTED", GraphDBRdfRankStatus.COMPUTED),
        ("COMPUTING", GraphDBRdfRankStatus.COMPUTING),
        ("EMPTY", GraphDBRdfRankStatus.EMPTY),
        ("ERROR", GraphDBRdfRankStatus.ERROR),
        ("ERROR: some error message", GraphDBRdfRankStatus.ERROR),
        ("something_unexpected", GraphDBRdfRankStatus.ERROR),
        ("OUTDATED", GraphDBRdfRankStatus.OUTDATED),
        ("CONFIG_CHANGED", GraphDBRdfRankStatus.CONFIG_CHANGED),
    ],
)
def test_get_rdf_rank_status(raw_value: str, expected_status: GraphDBRdfRankStatus):
    client = MagicMock(spec=GraphDB)
    client.get_rdf_rank_status = GraphDB.get_rdf_rank_status.__get__(client)
    json_data = f"""{{
        "head": {{ "vars": [ "status" ] }},
        "results": {{
            "bindings": [
                {{ "status": {{ "type": "literal", "value": "{raw_value}" }} }}
            ]
        }}
    }}"""
    mock_result = Result.parse(io.BytesIO(json_data.encode("utf-8")), format="json")
    client.eval_sparql_query.return_value = (mock_result, None)
    status = client.get_rdf_rank_status(GRAPHDB_REPOSITORY_ID)

    assert status == expected_status
    client.eval_sparql_query.assert_called_once_with(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#> SELECT ?status { ?s rank:status ?status }",
        validation=False
    )


def test_get_rdf_rank_status_empty_binding():
    client = MagicMock(spec=GraphDB)
    client.get_rdf_rank_status = GraphDB.get_rdf_rank_status.__get__(client)
    json_data = f"""{{
        "head": {{ "vars": [ "status" ] }},
        "results": {{
            "bindings": [ ]
        }}
    }}"""
    mock_result = Result.parse(io.BytesIO(json_data.encode("utf-8")), format="json")
    client.eval_sparql_query.return_value = (mock_result, None)
    status = client.get_rdf_rank_status(GRAPHDB_REPOSITORY_ID)

    assert status == GraphDBRdfRankStatus.ERROR
    client.eval_sparql_query.assert_called_once_with(
        GRAPHDB_REPOSITORY_ID,
        "PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#> SELECT ?status { ?s rank:status ?status }",
        validation=False
    )
