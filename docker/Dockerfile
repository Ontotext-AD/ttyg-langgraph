FROM ontotext/graphdb:10.8.4
RUN mkdir -p /opt/graphdb/dist/data/repositories/starwars
COPY config.ttl /opt/graphdb/dist/data/repositories/starwars/
COPY starwars-data.ttl /
COPY SWAPI-ontology.ttl /
COPY similarity.json /
COPY graphdb_create.sh /run.sh
ENTRYPOINT ["bash", "/run.sh"]