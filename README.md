# TTYG (Talk to your graph)

This repository includes a python module, which provides functionality for Natural Language Querying (NLQ) using [GraphDB](https://graphdb.ontotext.com/) and [OpenAI Assistants API](https://platform.openai.com/docs/api-reference/assistants) or [LangGraph Agents](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/).
Sample usage is provided in the [Jupyter Notebooks](jupyter_notebooks).
The LangGraph implementation can be used to plug in any open-source Large Language Model (LLM) including locally deployable ones.
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
poetry install
```

If you want to use LLMs from [Databricks](https://www.databricks.com/) or [Anthropic](https://www.anthropic.com/), run
```
poetry install --with llm-databricks
```

or

```
poetry install --with llm-anthropic
```

### Run Jupyter Notebooks

```bash
conda activate ttyg
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
