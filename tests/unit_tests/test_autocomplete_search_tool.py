import json

import pytest

from ttyg.graphdb import GraphDB
from ttyg.tools import AutocompleteSearchTool

GRAPHDB_BASE_URL = "http://localhost:7200/"
GRAPHDB_REPOSITORY_ID = "starwars"


@pytest.fixture
def graphdb():
    yield GraphDB(
        base_url=GRAPHDB_BASE_URL,
        repository_id=GRAPHDB_REPOSITORY_ID,
    )


def test_result_class_filter(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        limit=5,
    )
    results = autocomplete_search_tool._run(
        query="Skywalker"
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])

    results = autocomplete_search_tool._run(
        query="Skywalker",
        result_class="https://swapi.co/vocabulary/Human"
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])

    results = autocomplete_search_tool._run(
        query="Skywalker",
        result_class="https://swapi.co/vocabulary/Aleena"
    )
    assert 0 == len(json.loads(results)["results"]["bindings"])


def test_property_path_is_syntactically_wrong(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="http://schema.org/name",
        limit=5,
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
        )
    assert "Expected SelectQuery, found 'http'  (at char 199), (line:5, col:13)" == str(exc.value)


def test_property_path_is_prefixed(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="rdfs:label",
        limit=5,
    )
    results = autocomplete_search_tool._run(
        query="Skywalker"
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])


def test_property_path_with_two_properties_which_are_prefixed(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="rdfs:label | schema:name",
        limit=5,
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
        )
    assert "The following IRIs are not used in the data stored in GraphDB: <http://schema.org/name>" == str(exc.value)


def test_property_path_is_prefixed_with_unknown_prefix(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="unknown:label",
        limit=5,
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
        )
    assert "The following prefixes are undefined: unknown" == str(exc.value)


def test_result_class_uses_wrong_prefix(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        limit=5,
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
            result_class="https://swapi.co/voc/Human"
        )
    assert "The following IRIs are not used in the data stored in GraphDB: <https://swapi.co/voc/Human>" == str(
        exc.value)


def test_result_class_is_prefixed(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        limit=5,
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
            result_class="unknown:Human"
        )
    assert "The following IRIs are not used in the data stored in GraphDB: <unknown:Human>" == str(exc.value)
