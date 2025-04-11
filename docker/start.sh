#! /bin/bash

set -ex

REPOSITORY_ID="starwars"
GRAPHDB_URI="http://localhost:7200"

function loadData {
  echo -e "\nImporting starwars-data.ttl"
  curl -X POST -H "Content-Type: application/x-turtle" -T starwars-data.ttl ${GRAPHDB_URI}/repositories/${REPOSITORY_ID}/statements

  echo -e "\nImporting SWAPI-ontology.ttl"
  curl -X POST -H "Content-Type:application/x-turtle" -T SWAPI-ontology.ttl  ${GRAPHDB_URI}/repositories/${REPOSITORY_ID}/statements
}

function computeRdfRank {
  echo -e "\nTriggering the computation of the RDF rank"
  curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d 'update=INSERT DATA { _:b1 <http://www.ontotext.com/owlim/RDFRank#compute> _:b2. }' "${GRAPHDB_URI}/repositories/${REPOSITORY_ID}/statements"
}

function createSimilarityIndex {
  echo -e "\nCreating similarity index"
  curl -X POST -H "Content-Type: application/json;charset=UTF-8" -X POST -H "X-GraphDB-Repository: ${REPOSITORY_ID}" --data "@similarity.json" "${GRAPHDB_URI}/rest/similarity"
}

function enableAutocompleteIndex {
  echo -e "\nEnable autocomplete index"
  curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d 'update=INSERT DATA { _:s  <http://www.ontotext.com/plugins/autocomplete#enabled> true . }' "${GRAPHDB_URI}/repositories/${REPOSITORY_ID}/statements"
}

docker build --tag graphdb .
docker compose up --wait -d graphdb
loadData
computeRdfRank
createSimilarityIndex
enableAutocompleteIndex
# sleep 60 seconds, so that the set-up is completed
sleep 60s
echo -e "\nFinished"
