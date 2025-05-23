<p align="center">
  <img alt="Graphwise Logo" src=".github/Graphwise_Logo.jpg">
</p>

# Talk to Your Graph (TTYG)

TTYG is a Python module that enables Natural Language Querying (NLQ) using [GraphDB](https://graphdb.ontotext.com/) and [LangGraph Agents](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/).
It includes a lightweight GraphDB client and a collection of tools designed for integration with large language model (LLM) agents.

## License

Apache-2.0 License. See [LICENSE](LICENSE) file for details.

## Installation

```bash
pip install ttyg
```

## Maintainers

Developed and maintained by [Graphwise](https://graphwise.ai/).
For issues or feature requests, please open [a GitHub issue](https://github.com/Ontotext-AD/ttyg-evaluation/issues).

## Usage

A sample usage is provided in [the Jupyter Notebook](jupyter_notebooks/NLQ_with_LangGraph_ReAct_Agents.ipynb), which demonstrates natural language querying using the Star Wars dataset.

### Run Jupyter Notebook

#### Prerequisites

- Install [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). `miniconda` will suffice.
- Install [Docker](https://docs.docker.com/get-docker/). The documentation is created using Docker version `28.0.1` which bundles Docker Compose. For earlier Docker versions you may need to install Docker Compose separately.

#### Create and activate the Conda environment

```bash
conda create --name ttyg --file conda-linux-64.lock
conda activate ttyg
```

#### Install dependencies with Poetry

Depending on the LLM provider you want to use, run one of the following:

```
poetry install --with llm-openai --with jupyter
# or
poetry install --with llm-anthropic --with jupyter
# or
poetry install --with llm-databricks --with jupyter
```

#### Run the Notebook

```bash
jupyter notebook
```
