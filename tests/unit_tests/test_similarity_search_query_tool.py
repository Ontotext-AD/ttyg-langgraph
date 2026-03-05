from rdflib import Graph

from ttyg.graphdb import GraphDB
from ttyg.tools import SimilaritySearchQueryTool
from .constants import GRAPHDB_REPOSITORY_ID


def test_run(graphdb: GraphDB) -> None:
    similarity_search_query_tool = SimilaritySearchQueryTool(
        graph=graphdb,
        graphdb_repository_id=GRAPHDB_REPOSITORY_ID,
        index_name="similarityIndex",
    )
    results, artifact = similarity_search_query_tool._run(
        query="Skywalker",
    )
    graph = Graph().parse(
        data=results,
        format="turtle",
    )
    assert len(graph) > 0
    assert """PREFIX sim: <http://www.ontotext.com/graphdb/similarity/>
PREFIX sim-index: <http://www.ontotext.com/graphdb/similarity/instance/>
DESCRIBE ?documentID {
    SELECT DISTINCT ?documentID {
        ?search a sim-index:similarityIndex ;
            sim:searchTerm "Skywalker";
            sim:documentResult ?result .
        ?result sim:value ?documentID ;
            sim:score ?score.
        FILTER(?score >= 0.6)
    }
    ORDER BY DESC(?score)
    LIMIT 10
}""" == artifact.query
