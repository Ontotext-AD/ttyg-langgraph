from rdflib import Graph

from ttyg.graphdb import GraphDB
from ttyg.tools import FTSTool
from .constants import GRAPHDB_REPOSITORY_ID


def test_run(graphdb: GraphDB) -> None:
    fts_tool = FTSTool(
        graph=graphdb,
        graphdb_repository_id=GRAPHDB_REPOSITORY_ID,
    )
    results, artifact = fts_tool._run(
        query="Skywalker",
    )
    graph = Graph().parse(
        data=results,
        format="turtle",
    )
    assert len(graph) > 0
    assert """PREFIX onto: <http://www.ontotext.com/>
PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
DESCRIBE ?iri {
SELECT DISTINCT ?iri {
    ?x onto:fts ('''Skywalker''' "*") {
        ?x ?p ?iri .
    } UNION {
        ?iri ?p ?x .
    }
    ?iri rank:hasRDFRank ?rank.
}
ORDER BY DESC(?rank)
LIMIT 10
}""" == artifact.query


def test_query_with_double_quotes(graphdb: GraphDB) -> None:
    fts_tool = FTSTool(
        graph=graphdb,
        graphdb_repository_id=GRAPHDB_REPOSITORY_ID,
    )
    results, artifact = fts_tool._run(
        query='"Skywalker"',
    )
    graph = Graph().parse(
        data=results,
        format="turtle",
    )
    assert len(graph) > 0
    assert r"""PREFIX onto: <http://www.ontotext.com/>
PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#>
DESCRIBE ?iri {
SELECT DISTINCT ?iri {
    ?x onto:fts ('''\\"Skywalker\\"''' "*") {
        ?x ?p ?iri .
    } UNION {
        ?iri ?p ?x .
    }
    ?iri rank:hasRDFRank ?rank.
}
ORDER BY DESC(?rank)
LIMIT 10
}""" == artifact.query
