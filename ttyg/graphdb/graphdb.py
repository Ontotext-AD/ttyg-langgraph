import re
from functools import cached_property
from typing import Optional

import pyparsing
import requests
from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE
from rdflib.plugins import sparql
from requests import Response


class GraphDB:
    """Ontotext GraphDB https://graphdb.ontotext.com/ Client"""

    def __init__(
            self,
            base_url: str,
            repository_id: str,
            connect_timeout: int = 2,
            read_timeout: int = 10,
            auth_header: Optional[str] = None,
    ):
        """
        Initializes a GraphDB Client.

        :param base_url : GraphDB Base URL
        :type base_url: str
        :param repository_id: GraphDB Repository ID
        :type repository_id: str
        :param connect_timeout: connect timeout in seconds for calls to GraphDB REST API, default = 2
        :type connect_timeout: int
        :param read_timeout: read timeout in seconds for calls to GraphDB REST API, default = 10
        :type read_timeout: int
        :param auth_header: optional, the value of the "Authorization" header to pass to GraphDB, if it's secured
        :type auth_header: Optional[str]
        """
        self.__base_url = base_url
        self.__repository_id = repository_id
        self.__connect_timeout = connect_timeout
        self.__read_timeout = read_timeout
        self.__sparql_wrapper = SPARQLWrapper(f"{base_url}/repositories/{repository_id}")
        self.__auth_header = auth_header
        if self.__auth_header:
            self.__sparql_wrapper.addCustomHttpHeader(
                "Authorization", self.__auth_header
            )

        self.__check_connectivity()

    def __check_connectivity(self):
        self.eval_sparql_query(query="ASK {?s ?p ?o}", validation=False)

    def __get_request(self, url: str, headers: dict, params=None) -> Response:
        if self.__auth_header:
            headers["Authorization"] = self.__auth_header

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=(self.__connect_timeout, self.__read_timeout),
        )
        response.raise_for_status()
        return response

    def fts_is_enabled(self) -> bool:
        """
        Checks if the full-text search (FTS) is enabled
        using the GraphDB REST API /rest/repositories/{repository_id} endpoint.

        :return: True, if full-text search (FTS) is enabled; False, otherwise
        :rtype: bool
        """
        response = self.__get_request(
            f"{self.__base_url}/rest/repositories/{self.__repository_id}",
            headers={
                "Accept": "application/json",
            },
        )
        return response.json()["params"]["enableFtsIndex"]["value"].lower() == "true"

    def autocomplete_is_enabled(self) -> bool:
        """
        Checks if the autocomplete is enabled.

        :return: True, if autocomplete is enabled; False, otherwise
        :rtype: bool
        """
        sparql_result = self.eval_sparql_query(
            "ASK {_:s <http://www.ontotext.com/plugins/autocomplete#enabled> ?o}",
            validation=False
        )
        return sparql_result["boolean"]

    def similarity_index_exists(self, index_name: str) -> bool:
        """
        Checks if a similarity index with the provided name exists
        using the GraphDB REST API /rest/similarity endpoint.

        :param index_name: the similarity index name
        :type index_name: str
        :return: True, if the index exists; False, otherwise
        :rtype: bool
        """
        response = self.__get_request(
            f"{self.__base_url}/rest/similarity",
            headers={
                "Accept": "application/json",
                "X-GraphDB-Repository": self.__repository_id,
            },
        )
        return index_name in {index["name"] for index in response.json()}

    def retrieval_connector_exists(self, connector_name: str) -> bool:
        """
        Checks if a ChatGPT Retrieval Plugin Connector with the provided name exists
        using the GraphDB REST API /rest/connectors/existing endpoint.

        :param connector_name: the connector name
        :type connector_name: str
        :return: True, if the connector exists; False, otherwise
        :rtype: bool
        """
        response = self.__get_request(
            f"{self.__base_url}/rest/connectors/existing",
            params={"prefix": "http://www.ontotext.com/connectors/retrieval#"},
            headers={
                "Accept": "application/json",
                "X-GraphDB-Repository": self.__repository_id,
            },
        )
        return connector_name in {connector["name"] for connector in response.json()}

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

    def rdf_rank_is_computed(self) -> bool:
        """
        Checks if the RDF rank for the repository is computed.

        :return: True, if the RDF rank status is "COMPUTED".
        False, if the RDF rank status is "CANCELED", "COMPUTING", "EMPTY", "ERROR", "OUTDATED" or "CONFIG_CHANGED".
        :rtype: bool
        """
        sparql_result = self.eval_sparql_query(
            "PREFIX rank: <http://www.ontotext.com/owlim/RDFRank#> SELECT ?status { ?s rank:status ?status }",
            validation=False
        )
        return "COMPUTED" == sparql_result["results"]["bindings"][0]["status"]["value"]

    @staticmethod
    def __extract_iris_from_sparql_query(query: str) -> set[str]:
        parsed = sparql.parser.parseQuery(query)
        prefix_part = str(parsed[0])
        query_part = str(parsed[1:])

        defined_prefixes = dict(
            re.findall(
                r"PrefixDecl_\{'prefix': '(.+?)', 'iri': rdflib\.term\.URIRef\('(.+?)'\)}",
                prefix_part
            )
        )

        prefixed_iris = set(map(
            lambda x: (x[0], x[1]),
            re.findall(r"pname_\{'prefix': '(.+?)', 'localname': '(.+?)'}", query_part)
        ))

        references_prefixes = set(map(lambda x: x[0], prefixed_iris))
        if not references_prefixes.issubset(defined_prefixes.keys()):
            undefined_prefixes = references_prefixes - defined_prefixes.keys()
            raise ValueError(f"The following prefixes are undefined: {', '.join(undefined_prefixes)}")

        prefixed_iris_to_full_iris = {
            defined_prefixes[x[0]] + x[1]
            for x in prefixed_iris
        }

        full_iris = set(re.findall(r"rdflib\.term\.URIRef\('(.+?)'\)", query_part))
        iris = full_iris | prefixed_iris_to_full_iris

        return set(
            filter(
                lambda x: not x.startswith("http://www.w3.org/2001/XMLSchema#"),
                iris
            )
        )

    def __validate_sparql_query(self, query: str) -> None:
        try:
            iris = self.__extract_iris_from_sparql_query(query)
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
            result = self.eval_sparql_query(iri_validation_query % iri_values, validation=False)
            invalid_iris = list(
                map(lambda x: f"<{x['iri']['value']}>", result["results"]["bindings"])
            )
            if invalid_iris:
                raise ValueError(
                    f"The following IRIs are not used in the data stored in GraphDB: {', '.join(invalid_iris)}"
                )
        except pyparsing.exceptions.ParseException as e:
            raise ValueError(e)

    def eval_sparql_query(
            self,
            query: str,
            result_format: str = None,
            validation: bool = True
    ):
        """
        Executes the provided SPARQL query against GraphDB.

        :param query: the SPARQL query, which should be evaluated
        :type query: str
        :param result_format: Format of the results.
        Possible values are "json", "xml", "turtle", "n3", "rdf", "rdf+xml", "csv", "tsv", "json-ld"
        (defined as constants in SPARQLWrapper). All other cases are ignored.
        :type result_format: str
        :param validation: should be True, if the SPARQL query is generated from a LLM, and should be validated.
        The validation includes parsing of the query, checks for missing prefixes,
         or usage of IRIs, which are not stored in GraphDB.
        :type validation: bool
        :return: the results in the expected result_format
        :rtype:
        """
        if validation:
            self.__validate_sparql_query(query)

        self.__sparql_wrapper.setQuery(query)

        if result_format is None:
            if self.__sparql_wrapper.queryType in {"CONSTRUCT", "DESCRIBE"}:
                result_format = TURTLE
            else:
                result_format = JSON

        self.__sparql_wrapper.setReturnFormat(result_format)
        results = self.__sparql_wrapper.query().convert()
        if result_format != JSON:
            return results.decode("utf-8")
        else:
            return results
