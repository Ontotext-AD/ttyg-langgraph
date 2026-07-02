import json

from ttyg.graphdb import GraphDB
from ttyg.tools import IRIDiscoveryTool
from .constants import GRAPHDB_REPOSITORY_ID


def test_run(graphdb: GraphDB) -> None:
    iri_discovery_tool = IRIDiscoveryTool(
        graph=graphdb,
        graphdb_repository_id=GRAPHDB_REPOSITORY_ID,
    )
    results, artifact = iri_discovery_tool._run(
        query="Skywalker",
    )
    assert len(json.loads(results)["results"]["bindings"]) > 0
    assert """PREFIX onto: <http://www.ontotext.com/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>
PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
SELECT ?iri ?label {
    ?label onto:fts ('''Skywalker''' "*").
    ?iri rdfs:label|skos:prefLabel|schema:name ?label.
    ?iri rank:hasRDFRank ?rank .
}
ORDER BY DESC(?rank)
LIMIT 10""" == artifact.query


def test_query_with_double_quotes(graphdb: GraphDB) -> None:
    iri_discovery_tool = IRIDiscoveryTool(
        graph=graphdb,
        graphdb_repository_id=GRAPHDB_REPOSITORY_ID,
    )
    results, artifact = iri_discovery_tool._run(
        query='"Skywalker"',
    )
    assert len(json.loads(results)["results"]["bindings"]) > 0
    assert r"""PREFIX onto: <http://www.ontotext.com/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>
PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
SELECT ?iri ?label {
    ?label onto:fts ('''\\"Skywalker\\"''' "*").
    ?iri rdfs:label|skos:prefLabel|schema:name ?label.
    ?iri rank:hasRDFRank ?rank .
}
ORDER BY DESC(?rank)
LIMIT 10""" == artifact.query
