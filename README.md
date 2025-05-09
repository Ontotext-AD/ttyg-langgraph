# TTYG (Talk to your graph)

This repository includes a python module, which provides functionality for Natural Language Querying (NLQ) using [GraphDB](https://graphdb.ontotext.com/) and [LangGraph Agents](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/).
This project is licensed under the terms of the [Apache License Version 2.0](LICENSE).

## Usage

### Prerequisites

- Install [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). `miniconda` will suffice.
- Install [Docker](https://docs.docker.com/get-docker/). The documentation is created using Docker version `28.0.1` which bundles Docker Compose. For earlier Docker versions you may need to install Docker Compose separately.

### Set up an environment with conda and poetry

#### Create the environment

```bash
conda create --name ttyg --file conda-linux-64.lock
conda activate ttyg
```

Depending on which LLM you want to use run
```
poetry install --with llm-<databricks|anthropic|openai>
```

### Run Jupyter Notebooks

```bash
jupyter notebook
```

## Development

### Run tests

```bash
conda activate ttyg
poetry install --with test
cd docker
./start.sh
cd ..
poetry run pytest tests/unit_tests/
cd docker
docker compose down -v --remove-orphans
```
