# NLQ Notebooks

This repository provides python modules and Jupyter Notebooks demonstrating a Natural Language Querying (NLQ) system using [GraphDB](https://graphdb.ontotext.com/) and 
[OpenAI Assistants API](https://platform.openai.com/docs/api-reference/assistants) or
[LangGraph Agents](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/).
The LangGraph implementation can be used to plug in any open-source Large Language Model (LLM) including locally deployable ones.
This project is licensed under the terms of the [Apache License Version 2.0](LICENSE).

## Usage

### Set up an environment with conda and poetry

#### Prerequisites

You should install [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). `miniconda` will suffice.

#### Create the environment

```bash
conda create --name nlq-notebooks --file conda-linux-64.lock
conda activate nlq-notebooks
poetry install --no-root
```

### Run

```bash
jupyter notebook
```
