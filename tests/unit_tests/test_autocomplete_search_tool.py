import json

import pytest
from langchain_core.tools import ToolException

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
    results, artifact = autocomplete_search_tool._run(
        query="Skywalker",
        limit=5,
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])
    assert """PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
    PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#>
    SELECT ?iri ?name ?rank {
        ?iri auto:query "Skywalker" ;
            <http://www.w3.org/2000/01/rdf-schema#label> ?name ;
            rank:hasRDFRank5 ?rank.
    }
    ORDER BY DESC(?rank)
    LIMIT 5""" == artifact.query

    results, artifact = autocomplete_search_tool._run(
        query="Skywalker",
        result_class="voc:Human",
        limit=5,
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])
    assert """PREFIX voc: <https://swapi.co/vocabulary/> PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
    PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#>
    SELECT ?iri ?name ?rank {
        ?iri auto:query "Skywalker" ;
            <http://www.w3.org/2000/01/rdf-schema#label> ?name ; a voc:Human ;
            rank:hasRDFRank5 ?rank.
    }
    ORDER BY DESC(?rank)
    LIMIT 5""" == artifact.query

    results, artifact = autocomplete_search_tool._run(
        query="Skywalker",
        result_class="voc:Aleena",
        limit=5,
    )
    assert 0 == len(json.loads(results)["results"]["bindings"])
    assert """PREFIX voc: <https://swapi.co/vocabulary/> PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
    PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#>
    SELECT ?iri ?name ?rank {
        ?iri auto:query "Skywalker" ;
            <http://www.w3.org/2000/01/rdf-schema#label> ?name ; a voc:Aleena ;
            rank:hasRDFRank5 ?rank.
    }
    ORDER BY DESC(?rank)
    LIMIT 5""" == artifact.query


def test_result_class_is_prefixed_with_unknown_prefix(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
    )
    with pytest.raises(ToolException) as exc:
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
    with pytest.raises(ToolException) as exc:
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
    results, artifact = autocomplete_search_tool._run(
        query="Skywalker",
        limit=5,
    )
    assert 5 == len(json.loads(results)["results"]["bindings"])
    assert """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
    PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#>
    SELECT ?iri ?name ?rank {
        ?iri auto:query "Skywalker" ;
            rdfs:label ?name ;
            rank:hasRDFRank5 ?rank.
    }
    ORDER BY DESC(?rank)
    LIMIT 5""" == artifact.query


def test_property_path_with_two_properties_which_are_prefixed(graphdb: GraphDB) -> None:
    autocomplete_search_tool = AutocompleteSearchTool(
        graph=graphdb,
        property_path="rdfs:label | schema:name",
    )
    with pytest.raises(ToolException) as exc:
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
    with pytest.raises(ToolException) as exc:
        autocomplete_search_tool._run(
            query="Skywalker",
            limit=5,
        )
    assert "The following prefixes are undefined: unknown" == str(exc.value)
