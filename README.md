Of course. Here is a complete, improved, and detailed README file for your GitHub repository. It incorporates all the features we've built, includes best practices, and provides a clear, step-by-step guide for anyone (including your future self) to set up and run the project.

-----

\<div align="center"\>

# DocRAG: A Graph-Powered RAG System for Technical Documentation

\<p\>
\<img alt="Python Version" src="[https://img.shields.io/badge/python-3.10%2B-blue](https://img.shields.io/badge/python-3.10%2B-blue)"\>
\<img alt="License" src="[https://img.shields.io/badge/license-MIT-green](https://www.google.com/search?q=https://img.shields.io/badge/license-MIT-green)"\>
\</p\>

\</div\>

An advanced Retrieval-Augmented Generation (RAG) system that transforms unstructured technical documentation into a structured, vectorized knowledge graph. This approach enables highly accurate, context-aware answers to complex questions by leveraging the relationships between different documentation entities.

## Architecture

This project uses a multi-stage pipeline to ingest data and a sophisticated query engine to retrieve it.

#### Data Flow Diagram

```
┌────────────────┐   ┌───────────────────────────┐
│   main.py      │──▶│ scraped_content_raw.json  │
│ (Web Crawler)  │   │      (Raw HTML)           │
└────────────────┘   └────────────┬──────────────┘
                                  │
                                  ▼
┌────────────────┐   ┌──────────────────────────────┐
│   parser.py    │──▶│ parsed_structured_content.json │
│ (HTML->MD)     │   │      (Cleaned Markdown)        │
└────────────────┘   └────────────┬──────────────────┘
                                  │
                                  ▼
┌──────────────────┐   ┌──────────────────────────┐
│ graph_builder.py │──▶│   Neo4j Graph Database   │
│ (Ingest/Vectorize) │   │ (Nodes with Embeddings)  │
└──────────────────┘   └────────────┬───────────────┘
                                  │
                                  ▼
┌────────────────┐   ┌──────────────────────────┐
│ query_engine.py│◀─▶│   Neo4j Graph Database   │
│   (RAG Logic)  │   │ (Vector + Graph Search)  │
└────────────────┘   └──────────────────────────┘
```

## Features

  - **Multi-Stage Processing:** Decouples scraping, parsing, and ingestion for a robust and debuggable pipeline.
  - **Graph-Based Knowledge:** Models documentation as a rich graph of interconnected Components, Props, Hooks, Utils, and Types, preserving vital relationships lost in simple vector stores.
  - **Hybrid Search:** Combines semantic vector search (for finding relevant concepts) with deterministic graph traversal (for gathering accurate context).
  - **Intelligent Contextual Retrieval:** The query engine automatically fetches definitions for related custom types mentioned in a prop or hook, providing the LLM with comprehensive context.
  - **Extensible Entity System:** Easily expandable to include new entity types (e.g., Changelogs, Examples) by adding new Pydantic schemas.

## Tech Stack

  - **Language:** Python 3.10+
  - **Orchestration & LLM Interaction:** LangChain
  - **LLM & Embeddings:** OpenAI (`gpt-4o`, `text-embedding-3-small`)
  - **Database:** Neo4j (Graph Database with native Vector Index)
  - **Web Scraping/Parsing:** `requests`, `BeautifulSoup4`
  - **Containerization:** Docker

## Project Structure

```
docrag/
├── .env                  # Stores API keys and secrets
├── .gitignore            # Specifies files for Git to ignore
├── requirements.txt      # Project dependencies
├── data/                 # (Git-ignored) Directory for scraped and parsed data
│   ├── scraped_content_raw.json
│   └── parsed_structured_content.json
├── neo4j/                # (Git-ignored) Directory for Neo4j database files
│   ├── data/
│   └── logs/
└── src/                  # Main source code
    ├── main.py           # The web crawler that fetches raw HTML
    ├── parser.py         # The script that converts raw HTML to clean Markdown
    ├── graph_builder.py  # The script that extracts entities and builds the graph
    └── query_engine.py   # The final RAG application to ask questions
```

## Setup and Installation

### 1\. Prerequisites

  - **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
  - **Docker Desktop**: [Download Docker](https://www.docker.com/products/docker-desktop/). Ensure the Docker application is running before you start.
  - **Git**: [Download Git](https://git-scm.com/download/win)

### 2\. Initial Setup

1.  **Clone the Repository:**

    ```powershell
    git clone https://github.com/ChaitanyaKharche/docrag.git
    cd docrag
    ```

2.  **Create and Activate Virtual Environment:**

    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

3.  **Create `.env` file:**
    Create a file named `.env` in the project root and add your secrets.

      * Get an API key from [platform.openai.com](https://platform.openai.com/).

    <!-- end list -->

    ```env
    OPENAI_API_KEY="sk-..."
    NEO4J_PASSWORD="your-strong-password-here"
    ```

4.  **Install Dependencies:**
    Install all required Python packages from `requirements.txt`.

    ```powershell
    pip install -r requirements.txt
    ```

## Execution Workflow

Follow these steps in order to run the entire pipeline.

### Step 1: Start the Neo4j Database

In a **new terminal** (do not activate the `venv`), run the following Docker command. This will download and start your Neo4j database container.

**Note:** Make sure to replace `your-strong-password-here` with the same password you set in your `.env` file.

```powershell
docker run `
    --name docrag-neo4j `
    -p 7474:7474 -p 7687:7687 `
    -d `
    -v "$($pwd)\neo4j\data:/data" `
    -v "$($pwd)\neo4j\logs:/logs" `
    --env NEO4J_AUTH="neo4j/your-strong-password-here" `
    --env NEO4J_PLUGINS='["graph-data-science"]' `
    neo4j:5.18.1
```

  * `-p 7474:7474`: Exposes the Neo4j web browser interface.
  * `-p 7687:7687`: Exposes the Bolt protocol for the Python driver.
  * `-v ...`: Mounts local directories for persistent database storage.

### Step 2: Create Database Vector Indexes

Before ingesting data, you must create the vector indexes.

1.  Navigate to the Neo4j Browser: `http://localhost:7474`

2.  Connect with username `neo4j` and your password.

3.  Run these five Cypher commands one by one in the query bar:

    ```cypher
    CREATE VECTOR INDEX `component_descriptions` IF NOT EXISTS FOR (n:Component) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};
    ```

    ```cypher
    CREATE VECTOR INDEX `prop_descriptions` IF NOT EXISTS FOR (n:Prop) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};
    ```

    ```cypher
    CREATE VECTOR INDEX `hook_descriptions` IF NOT EXISTS FOR (n:Hook) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};
    ```

    ```cypher
    CREATE VECTOR INDEX `util_descriptions` IF NOT EXISTS FOR (n:Util) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};
    ```

    ```cypher
    CREATE VECTOR INDEX `type_descriptions` IF NOT EXISTS FOR (n:Type) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};
    ```

### Step 3: Run the Data Pipeline

In your original terminal (with the `venv` activated), run the following scripts in order.

1.  **Scrape the Website:**

    ```powershell
    python src/main.py
    ```

2.  **Parse the Raw HTML:**

    ```powershell
    python src/parser.py
    ```

3.  **Build the Knowledge Graph:** (This will take several minutes)

    ```powershell
    python src/graph_builder.py
    ```

### Step 4: Query the System

Your knowledge graph is now complete and ready to be used. Run the query engine to ask a question.

```powershell
python src/query_engine.py
```

You can change the default question inside `query_engine.py` to explore the documentation.

## Future Improvements

  - **Changelog Integration:** Parse the changelog and create `:Version` nodes, linking them to entities to answer version-specific questions.
  - **Interactive API:** Wrap the `query_engine.py` logic in a FastAPI application to serve the RAG system as a web endpoint.
  - **Advanced Relationships:** Extract more nuanced relationships, such as which Hooks are used by which Components, by parsing code blocks.
  - **Support for More Documentation:** Adapt the `parser.py` script with custom logic for the unique HTML structure of other documentation sites.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.md) file for details.
