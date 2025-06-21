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
    )
    results = autocomplete_search_tool._run(
        query="Skywalker",
        limit=5,
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])

    results = autocomplete_search_tool._run(
        query="Skywalker",
        result_class="voc:Human",
        limit=5,
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])

    results = autocomplete_search_tool._run(
        query="Skywalker",
        result_class="voc:Aleena",
        limit=5,
    )
    assert 0 == len(json.loads(results)["results"]["bindings"])


def test_result_class_is_prefixed_with_unknown_prefix(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
            result_class="unknown:Human",
            limit=5,
        )
    assert "The following prefixes are undefined: unknown" == str(exc.value)


def test_property_path_is_syntactically_wrong(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="http://schema.org/name",
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
            limit=5,
        )
    assert "Expected SelectQuery, found 'http'  (at char 199), (line:5, col:13)" == str(exc.value)


def test_property_path_is_prefixed(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="rdfs:label",
    )
    results = autocomplete_search_tool._run(
        query="Skywalker",
        limit=5,
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])


def test_property_path_with_two_properties_which_are_prefixed(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="rdfs:label | schema:name",
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
            limit=5,
        )
    assert "The following IRIs are not used in the data stored in GraphDB: <http://schema.org/name>" == str(exc.value)


def test_property_path_is_prefixed_with_unknown_prefix(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="unknown:label",
    )
    with pytest.raises(ValueError) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
            limit=5,
        )
    assert "The following prefixes are undefined: unknown" == str(exc.value)
