from typing import Literal

from ..base_artifact import BaseArtifact


class SparqlQueryArtifact(BaseArtifact):
    type: Literal["query"] = "query"
    query_type: Literal["sparql"] = "sparql"
    query: str
