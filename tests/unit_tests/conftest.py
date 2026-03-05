import pytest

from ttyg.graphdb import GraphDB
from .constants import GRAPHDB_BASE_URL


@pytest.fixture(scope="module")
def graphdb():
    with GraphDB(base_url=GRAPHDB_BASE_URL) as graphdb:
        yield graphdb
