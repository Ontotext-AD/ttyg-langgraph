#! /bin/bash
REPOSITORY_ID="starwars"
GRAPHDB_URI="http://localhost:7200/"

echo -e "\nUsing GraphDB: ${GRAPHDB_URI}"

function startGraphDB {
 echo -e "\nStarting GraphDB..."
 exec /opt/graphdb/dist/bin/graphdb
}

function waitGraphDBStart {
  echo -e "\nWaiting GraphDB to start..."
  for _ in $(seq 1 5); do
    CHECK_RES=$(curl --silent --write-out '%{http_code}' --output /dev/null ${GRAPHDB_URI}/rest/repositories)
    if [ "${CHECK_RES}" = '200' ]; then
        echo -e "\nUp and running"
        break
    fi
    sleep 30s
    echo "CHECK_RES: ${CHECK_RES}"
  done
}

function loadData {
  echo -e "\nImporting starwars-data.ttl"
  curl -X POST -H "Content-Type: application/x-turtle" -T /starwars-data.ttl ${GRAPHDB_URI}/repositories/${REPOSITORY_ID}/statements

  echo -e "\nImporting SWAPI-ontology.ttl"
  curl -X POST -H "Content-Type:application/x-turtle" -T /SWAPI-ontology.ttl  ${GRAPHDB_URI}/repositories/${REPOSITORY_ID}/statements
}

function computeRdfRank {
  echo -e "\nTriggering the computation of the RDF rank"
  curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d 'update=INSERT DATA { _:b1 <http://www.ontotext.com/owlim/RDFRank#compute> _:b2. }' "${GRAPHDB_URI}/repositories/${REPOSITORY_ID}/statements"
}

function createSimilarityIndex {
  echo -e "\nCreating similarity index"
  curl -X POST -H "Content-Type: application/json;charset=UTF-8" -X POST -H "X-GraphDB-Repository: ${REPOSITORY_ID}" --data "@/similarity.json" "${GRAPHDB_URI}/rest/similarity"
}

startGraphDB &
waitGraphDBStart
loadData
computeRdfRank
createSimilarityIndex
wait
