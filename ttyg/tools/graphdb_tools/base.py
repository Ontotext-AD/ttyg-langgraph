from abc import ABCMeta
from typing import Optional

from langchain_core.tools import BaseTool
from pydantic import model_validator
from typing_extensions import Self

from ttyg.graphdb import GraphDB


class BaseGraphDBTool(BaseTool, metaclass=ABCMeta):
    """Base tool for interacting with GraphDB"""

    graph: GraphDB
    """The GraphDB Client"""

    @property
    def min_graphdb_version(self) -> Optional[str]:
        """
        :return: the minimum GraphDB version required to use the tool
        :rtype: str
        """
        return None

    @model_validator(mode="after")
    def graphdb_version_compatibility(self) -> Self:
        if self.min_graphdb_version:
            graphdb_version = self.graph.version
            major, minor, _ = graphdb_version.split(".")
            major, minor = int(major), int(minor)

            min_major, min_minor = self.min_graphdb_version.split(".")
            min_major, min_minor = int(min_major), int(min_minor)

            if (major < min_major) or (major == min_major and minor < min_minor):
                raise ValueError(
                    f"GraphDB version {self.min_graphdb_version} or later required. Please, upgrade to a newer version."
                )

        return self
