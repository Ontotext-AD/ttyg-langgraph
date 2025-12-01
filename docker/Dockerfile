FROM ontotext/graphdb:10.8.11
RUN mkdir -p /opt/graphdb/dist/data/repositories/starwars
COPY config.ttl /opt/graphdb/dist/data/repositories/starwars/
COPY run.sh /run.sh
ENTRYPOINT ["bash", "/run.sh"]