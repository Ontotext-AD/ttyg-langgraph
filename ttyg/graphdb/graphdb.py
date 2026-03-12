import logging
import re
import threading
from enum import Enum
from functools import cached_property
from typing import Tuple

import httpx
import pyparsing
from rdflib import Variable
from rdflib.contrib.graphdb.client import GraphDBClient
from rdflib.contrib.graphdb.exceptions import (
    RepositoryNotFoundError,
    RepositoryNotHealthyError,
)
from rdflib.plugins import sparql
from rdflib.query import Result


class GraphDBRdfRankStatus(Enum):
    CANCELED = "CANCELED"
    COMPUTED = "COMPUTED"
    COMPUTING = "COMPUTING"
    EMPTY = "EMPTY"
    ERROR = "ERROR"
    OUTDATED = "OUTDATED"
    CONFIG_CHANGED = "CONFIG_CHANGED"


class GraphDBAutocompleteStatus(Enum):
    READY = "READY"
    READY_CONFIG = "READY_CONFIG"
    ERROR = "ERROR"
    NONE = "NONE"
    BUILDING = "BUILDING"
    CANCELED = "CANCELED"


class GraphDB:
    """Wrapper of rdflib GraphDB Client https://rdflib.readthedocs.io/en/stable/graphdb/"""

    _lock = threading.Lock()

    def __init__(
        self,
        base_url: str,
        connect_timeout: float = 2,
        read_timeout: float = 10,
        auth_header: str | None = None,
    ):
        """
        Initializes a GraphDB Client.

        :param base_url : The base URL of the GraphDB server
        :type base_url: str
        :param connect_timeout: connect timeout in seconds, default = 2
        :type connect_timeout: float
        :param read_timeout: read timeout in seconds, default = 10
        :type read_timeout: float
        :param auth_header: optional, the value of the "Authorization" header to pass to GraphDB, if it's secured
        :type auth_header: str | None
        """

        self.__base_url = base_url
        self.__auth_header = auth_header
        self.__graphdb_client = GraphDBClient(
            base_url=base_url,
            auth=auth_header,
            timeout=httpx.Timeout((connect_timeout, read_timeout))
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__graphdb_client.close()

    def health(self, repository_id: str, timeout: int = 5) -> httpx.Response:
        """Repository health check.
        The implementation from rdflib returns a boolean value, so we need to override it
        to get the response.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :param timeout: A timeout parameter in seconds. If provided, the endpoint attempts
                to retrieve the repository within this timeout. If not, the passive
                check is performed.
        :type timeout: int
        :return: the http response
        :rtype: httpx.Response

        Raises:
            RepositoryNotFoundError: If the repository is not found or the passive check failed.
            RepositoryNotHealthyError: If the repository is not healthy.
        """
        try:
            params = {"passive": str(timeout)}
            response = self.__graphdb_client.http_client.get(
                f"/repositories/{repository_id}/health", params=params
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 404:
                raise RepositoryNotFoundError(
                    f"Repository {repository_id} not found."
                )
            raise RepositoryNotHealthyError(
                f"Repository {repository_id} is not healthy. {err.response.status_code} - {err.response.text}"
            )

    def eval_sparql_query(
        self,
        repository_id: str,
        query: str,
        validation: bool = True
    ) -> Tuple[Result, str]:
        """
        Executes the provided SPARQL query against GraphDB.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :param query: the SPARQL query, which should be evaluated
        :type query: str
        :param validation: should be True, if the SPARQL query is generated from a LLM, and should be validated.
        The validation includes parsing of the query, checks for missing prefixes,
         or usage of IRIs, which are not stored in GraphDB.
        :type validation: bool
        :return: the results of the query execution and the actual executed query
        :rtype: Tuple[Result, str]
        """
        if validation:
            query = self.__validate_query(repository_id, query)

        return self.__graphdb_client.repositories.get(repository_id).query(query), query

    def fts_is_enabled(self, repository_id: str) -> bool:
        """
        Checks if the full-text search (FTS) is enabled
        using the GraphDB REST API /rest/repositories/{repository_id} endpoint.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :return: True, if full-text search (FTS) is enabled; False, otherwise
        :rtype: bool
        """
        response = self.__get_request(
            f"{self.__base_url}/rest/repositories/{repository_id}",
            headers={
                "Accept": "application/json",
            },
        )
        return response.json()["params"]["enableFtsIndex"]["value"].lower() == "true"

    def get_autocomplete_status(self, repository_id: str) -> GraphDBAutocompleteStatus:
        """
        Returns the status of the autocomplete index for the repository.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :rtype: GraphDBAutocompleteStatus
        """
        sparql_result, _ = self.eval_sparql_query(
            repository_id,
            "PREFIX auto: <http://www.ontotext.com/plugins/autocomplete#> SELECT ?status { ?s auto:status ?status }",
            validation=False
        )
        try:
            raw_value = sparql_result.bindings[0][Variable("status")].value
            if raw_value in GraphDBAutocompleteStatus:
                return GraphDBAutocompleteStatus[raw_value]
        except IndexError:
            return GraphDBAutocompleteStatus.ERROR
        return GraphDBAutocompleteStatus.ERROR

    def similarity_index_exists(self, repository_id: str, index_name: str) -> bool:
        """
        Checks if a similarity index with the provided name exists
        using the GraphDB REST API /rest/similarity endpoint.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :param index_name: the similarity index name
        :type index_name: str
        :return: True, if the index exists; False, otherwise
        :rtype: bool
        """
        response = self.__get_request(
            f"{self.__base_url}/rest/similarity",
            headers={
                "Accept": "application/json",
                "X-GraphDB-Repository": repository_id,
            },
        )
        return index_name in {index["name"] for index in response.json()}

    def retrieval_connector_exists(self, repository_id: str, connector_name: str) -> bool:
        """
        Checks if a ChatGPT Retrieval Plugin Connector with the provided name exists.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :param connector_name: the connector name
        :type connector_name: str
        :return: True, if the connector exists; False, otherwise
        :rtype: bool
        """
        sparql_result, _ = self.eval_sparql_query(
            repository_id,
            "PREFIX retr: <http://www.ontotext.com/connectors/retrieval#> "
            "SELECT ?connector { [] retr:listConnectors ?connector . }",
            validation=False
        )
        existing_connectors = set()
        for bindings in sparql_result.bindings:
            if Variable("connector") in bindings:
                existing_connectors.add(bindings[Variable("connector")].value)
        return connector_name in existing_connectors

    def get_rdf_rank_status(self, repository_id: str) -> GraphDBRdfRankStatus:
        """
        Returns the status of GraphDB RDF rank for the repository.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :rtype: GraphDBRdfRankStatus
        """
        sparql_result, _ = self.eval_sparql_query(
            repository_id,
            "PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#> SELECT ?status { ?s rank:status ?status }",
            validation=False
        )
        try:
            raw_value = sparql_result.bindings[0][Variable("status")].value
            if raw_value in GraphDBRdfRankStatus:
                return GraphDBRdfRankStatus[raw_value]
        except IndexError:
            return GraphDBRdfRankStatus.ERROR
        return GraphDBRdfRankStatus.ERROR

    @cached_property
    def version(self) -> str:
        """
        :return: the GraphDB server version
        :rtype: str
        """
        response = self.__get_request(
            f"{self.__base_url}/rest/info/version",
            headers={
                "Accept": "application/json",
            },
        )
        return response.json()["productVersion"]

    def __get_request(self, url: str, headers: dict, params=None) -> httpx.Response:
        if self.__auth_header:
            headers["Authorization"] = self.__auth_header

        response = self.__graphdb_client.http_client.get(
            url,
            params=params,
            headers=headers,
        )

        response.raise_for_status()
        return response

    def __validate_query(self, repository_id: str, query: str) -> str:
        """
        Validates a given SPARQL query and corrects its prefixes, if possible.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :param query: SPARQL query
        :type query: str
        :return updated SPARQL query, where:
         - missing prefixes are added automatically, if they appear in the declaration info available in the repository
         - prefix definitions, which values differ from the declaration info available in the repository,
         are automatically corrected
        :rtype: str
        :raises ValueError, if:
        - the SPARQL query syntax is wrong
        - the query is an update SPARQL query
        - the query uses prefixes, which are not defined in the query and don't appear in
        the declaration info available in the repository
        - one or more IRIs used in the query are not stored in repository
        """
        parsed_query = self.__parse_query(query)
        prefix_part = str(parsed_query[0])
        query_part = str(parsed_query[1:])

        defined_prefixes = self.__get_defined_prefixes(prefix_part)
        known_prefixes = self.__get_known_prefixes(repository_id)

        query = self.__correct_wrong_prefixes(defined_prefixes, known_prefixes, query)

        prefixed_iris = self.__get_prefixed_iris(query_part)

        query = self.__add_missing_prefixes(defined_prefixes, known_prefixes, prefixed_iris, query)
        query = self.__add_new_lines_after_prefixes_if_missing(query)

        self.__validate_iris_are_stored(repository_id, defined_prefixes, prefixed_iris, query_part)

        return query

    @staticmethod
    def __parse_query(query: str) -> pyparsing.results.ParseResults:
        """
        Parses a given SPARQL query.
        If the query is an update SPARQL query, an exception is thrown, as we expect only read queries.

        :param query: SPARQL query
        :type query: str
        :return: the parsed SPARQL query
        :rtype: pyparsing.results.ParseResults
        :raises ValueError, if the SPARQL query syntax is wrong or the query is an update SPARQL query
        """
        with GraphDB._lock:  # use lock, because this method is not thread safe
            try:
                return sparql.parser.parseQuery(query)
            except pyparsing.exceptions.ParseException as e:
                raise ValueError(e)

    @staticmethod
    def __get_defined_prefixes(prefix_part: str) -> dict[str, str]:
        """
        Returns the defined prefixes in the SPARQL query
        :param prefix_part: the prefix part of the parsed query
        :type prefix_part: str
        :return: the defined prefix - namespace pairs as dictionary
        :rtype: dict[str, str]
        """
        return dict(
            re.findall(
                r"PrefixDecl_\{'prefix': '(.+?)', 'iri': rdflib\.term\.URIRef\('(.+?)'\)}",
                prefix_part
            )
        )

    def __get_known_prefixes(self, repository_id: str) -> dict[str, str]:
        """
        Fetch all namespace declaration info available in the repository.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :return: dictionary of prefix - namespace pairs
        :rtype: dict[str, str]
        """

        return {
            ns.prefix: ns.namespace
            for ns in self.__graphdb_client.repositories.get(repository_id).namespaces.list()
        }

    @staticmethod
    def __correct_wrong_prefixes(
        defined_prefixes: dict[str, str],
        known_prefixes: dict[str, str],
        query: str
    ) -> str:
        """
        Corrects the prefix definitions in the SPARQL query,
        which values differ from the declaration info available in the repository.
        :param defined_prefixes: prefixes defined in the SPARQL query
        :type defined_prefixes: dict[str, str]
        :param known_prefixes: prefixes from the declaration info available in the repository
        :type known_prefixes:  dict[str, str]
        :param query: SPARQL query
        :type query: str
        :return: updated SPARQL query, where the prefix definitions,
        which values differ from the declaration info available in the repository, are automatically corrected.
        The defined_prefixes are also updated.
        :rtype: str
        """
        for prefix, namespace in defined_prefixes.items():
            if prefix in known_prefixes and known_prefixes[prefix] != namespace:
                logging.debug(
                    f"Correcting wrong value of prefix {prefix} : {namespace} to {known_prefixes[prefix]}"
                )
                regex = re.compile("prefix\\s+%s:\\s*<%s>" % (prefix, namespace), flags=re.IGNORECASE)
                query = re.sub(regex, f"PREFIX {prefix}: <{known_prefixes[prefix]}>", query)
                defined_prefixes[prefix] = known_prefixes[prefix]
        return query

    @staticmethod
    def __get_prefixed_iris(query_part: str) -> set[tuple[str, str]]:
        """
        Returns the prefixed IRIs in the SPARQL query
        :param query_part: the query part of the parsed query
        :type query_part: str
        :return: prefixed IRIs in the SPARQL query as set of tuples (prefix, local name)
        :rtype: set[tuple[str, str]]
        """
        return set(map(
            lambda x: (x[0], x[1]),
            re.findall(r"pname_\{'prefix': '(.+?)', 'localname': '(.+?)'}", query_part)
        ))

    @staticmethod
    def __add_missing_prefixes(
        defined_prefixes: dict[str, str],
        known_prefixes: dict[str, str],
        prefixed_iris: set[tuple[str, str]],
        query: str
    ) -> str:
        """
        Adds prefixes used in the SPARQL query, which are not defined in it, but appear in
        the declaration info available in the repository
        :param defined_prefixes: prefixes defined in the SPARQL query
        :type defined_prefixes: dict[str, str]
        :param known_prefixes: prefixes from the declaration info available in the repository
        :type known_prefixes:  dict[str, str]
        :param prefixed_iris: the prefixed IRIs in the SPARQL query
        :type prefixed_iris: set[tuple[str, str]]
        :param query: SPARQL query
        :type query: str
        :return: updated SPARQL query, where missing prefixes are added automatically,
         if they appear in the declaration info available in the repository.
         The defined_prefixes are also updated.
        :rtype: str
        :raises ValueError, if the query uses prefixes, which are not defined in the query and don't appear in
        the declaration info available in the repository
        """
        references_prefixes = set(map(lambda x: x[0], prefixed_iris))
        if not references_prefixes.issubset(defined_prefixes.keys()):
            undefined_prefixes = references_prefixes - defined_prefixes.keys()
            for prefix in undefined_prefixes:
                if prefix in known_prefixes:
                    defined_prefixes[prefix] = known_prefixes[prefix]
                    query = f"PREFIX {prefix}: <{known_prefixes[prefix]}> " + query
            undefined_prefixes = undefined_prefixes - defined_prefixes.keys()
            if undefined_prefixes:
                raise ValueError(f"The following prefixes are undefined: {', '.join(undefined_prefixes)}")
        return query

    def __validate_iris_are_stored(
        self,
        repository_id: str,
        defined_prefixes: dict[str, str],
        prefixed_iris: set[tuple[str, str]],
        query_part: str
    ) -> None:
        """
        Executes a SPARQL query, which uses the special predicate <http://www.ontotext.com/owlim/entity#id>
        to check if the IRIs in the SPARQL query are stored in the repository.

        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :param defined_prefixes: prefixes defined in the SPARQL query
        :type defined_prefixes: dict[str, str]
        :param prefixed_iris: the prefixed IRIs in the SPARQL query
        :type prefixed_iris: set[tuple[str, str]]
        :param query_part: the query part of the parsed query
        :type query_part: str
        :rtype: None
        :raises ValueError, if one or more IRIs used in the query are not stored in repository
        """
        iris = self.__get_all_iris(defined_prefixes, prefixed_iris, query_part)
        iri_values = " ".join(map(lambda x: f"<{x}>", iris))
        iri_validation_query = """
        SELECT ?iri {
            VALUES ?iri {
                %s
            }
            ?iri <http://www.ontotext.com/owlim/entity#id> ?id .
            FILTER(?id < 0)
        }
        """
        result, _ = self.eval_sparql_query(repository_id, iri_validation_query % iri_values, validation=False)
        invalid_iris = list(
            map(lambda x: f"<{x[Variable("iri")]}>", result.bindings)
        )
        if invalid_iris:
            raise ValueError(
                f"The following IRIs are not used in the data stored in GraphDB: {', '.join(invalid_iris)}"
            )

    @staticmethod
    def __get_all_iris(
        defined_prefixes: dict[str, str],
        prefixed_iris: set[tuple[str, str]],
        query_part: str
    ) -> set[str]:
        """
        Returns all IRIs used in the SPARQL query
        :param defined_prefixes: prefixes defined in the SPARQL query
        :type defined_prefixes: dict[str, str]
        :param prefixed_iris: the prefixed IRIs in the SPARQL query
        :type prefixed_iris: set[tuple[str, str]]
        :param query_part: the query part of the parsed query
        :type query_part: str
        :return: all IRIs from the SPARQL query
        :rtype: set[str]
        """
        prefixed_iris_to_full_iris = {
            defined_prefixes[x[0]] + x[1]
            for x in prefixed_iris
        }
        full_iris = set(re.findall(r"rdflib\.term\.URIRef\('(.+?)'\)", query_part))
        iris = full_iris | prefixed_iris_to_full_iris
        iris = set(
            filter(
                lambda x: (
                              not x.startswith("http://www.w3.org/2001/XMLSchema#")
                          ) and (
                              not x.startswith("http://www.ontotext.com/owlim/RDFRank#")
                          ) and (
                              not x.startswith("http://www.ontotext.com/plugins/autocomplete#")
                          ) and (
                              not x.startswith("http://www.openrdf.org/schema/sesame#")
                          ) and (
                              not x.startswith("http://spinrdf.org/spif#")
                          ) and (
                              not x.startswith("http://www.ontotext.com/fts")
                          ) and (
                              not x.startswith("http://www.ontotext.com/describe/outgoing")
                          ),
                iris
            )
        )
        return iris

    @staticmethod
    def __add_new_lines_after_prefixes_if_missing(query: str) -> str:
        # 1. Handle PREFIX spacing:
        # Matches optional leading whitespace, the word PREFIX, the content,
        # and any optional trailing horizontal space.
        # Pattern: \s*(PREFIX\s+[^>]+>)[ \t]*
        prefix_pattern = r"\s*(PREFIX\s+[^>]+>)[ \t]*"
        # Replacement: Ensures the prefix starts on a new line (\n) with no leading spaces.
        query = re.sub(prefix_pattern, r"\n\1\n", query, flags=re.IGNORECASE)

        # 2. Clean up whitespace before the main query verb (SELECT|ASK|CONSTRUCT|DESCRIBE)
        query_verbs = r"(?:SELECT|ASK|CONSTRUCT|DESCRIBE)"
        verb_pattern = fr"\s+(?={query_verbs})"
        query = re.sub(verb_pattern, r"\n", query, flags=re.IGNORECASE)

        # 3. remove leading/trailing whitespace and collapse double newlines
        query = query.strip()
        return re.sub(r"\n+", "\n", query)
