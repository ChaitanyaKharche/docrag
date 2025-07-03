DocScraper: A Graph RAG System for Technical Documentation
This project implements a sophisticated, multi-stage Retrieval-Augmented Generation (RAG) system designed to answer complex questions about technical documentation. It moves beyond simple vector search by building and querying an intelligent knowledge graph, resulting in more accurate and contextually aware answers.

This system was built to ingest the entire React Flow documentation, but its architecture is generic and can be adapted for any documentation website.

Architecture
The system is composed of two main pipelines: a Data Ingestion Pipeline that builds the knowledge graph, and a Query Engine that uses the graph to answer questions.

1. Data Ingestion Pipeline
This is a three-stage process that turns unstructured web pages into a structured, vectorized knowledge graph.

scraper.py (Crawl & Scrape): Starts with a seed URL and crawls the target domain, discovering all valid, on-site links. It downloads the raw HTML for each page and saves it, ensuring a complete and pristine copy of the source data.

parser.py (Parse & Structure): Reads the raw HTML files. Instead of naively stripping text, it intelligently parses the HTML structure, identifying headings, code blocks, and, most importantly, converting complex <table> structures into clean, well-formatted Markdown. This preserves the critical structure of the documentation.

graph_builder.py (Ingest & Vectorize): This is the core of the ingestion process.

It takes the clean Markdown from the parser.

It uses a powerful Large Language Model (gpt-4o) with Pydantic schemas to perform entity extraction, identifying Components, Props, Hooks, Utils, and Types.

It connects to a Neo4j graph database.

For each extracted entity, it creates a corresponding node (e.g., :Component, :Prop).

It creates relationships between entities (e.g., (:Component)-[:HAS_PROP]->(:Prop)).

It uses an embedding model (text-embedding-3-small) to create vector embeddings for the description of each entity and stores them directly on the nodes, creating a hybrid graph ready for both structured and semantic queries.

2. Query Engine
The query engine uses an advanced, multi-step retrieval strategy to ensure high-quality context is provided to the final generation model.

query_engine.py (Retrieve & Generate):

The user's question is converted into a vector embedding.

A vector search is performed across all relevant indexes (:Component, :Prop, :Hook, etc.) to find the most semantically similar entities in the graph.

Contextual Graph Traversal: The system then enriches this initial context. For example, if a Prop is retrieved, the engine traverses the graph to find which Component it belongs to. If a prop's type is a custom Type (e.g., NodeOrigin), it fetches the definition of that :Type node as well.

This rich, multi-faceted context is compiled and passed to the final LLM (gpt-4o).

The LLM synthesizes the detailed context into a comprehensive, accurate answer.

Setup and Installation (Windows)
Prerequisites
Python 3.10+: Ensure Python is installed and accessible from your terminal.

Docker Desktop: Install and run Docker Desktop. This is required to run the Neo4j database.

Download from docker.com.

Ensure Docker Desktop is running before proceeding.

Installation Steps
Create Project Directory:
Open PowerShell and create your project folder.

mkdir docscraper
cd docscraper

Set up Python Virtual Environment:

python -m venv venv
.\venv\Scripts\Activate.ps1

(Your terminal prompt should now be prefixed with (venv)).

Create Project Files:
Create the following files inside the docscraper directory.

requirements.txt:

requests
beautifulsoup4
lxml
pandas
tabulate
langchain
langchain-openai
neo4j
python-dotenv

.env:

OPENAI_API_KEY="sk-..."
NEO4J_PASSWORD="your_neo4j_password"

(Replace with your actual OpenAI key and the password you will use for Neo4j).

Install Dependencies:

pip install -r requirements.txt

Running the System: Full Workflow
Follow these steps in order to populate the database and run queries.

Step 1: Start the Neo4j Database
Run this command in a new PowerShell terminal (do not activate the venv here). This will download the Neo4j image and start the database container.

docker run `
    --name docscraper-neo4j `
    -p 7474:7474 -p 7687:7687 `
    -d `
    -v ${PWD}/neo4j/data:/data `
    -v ${PWD}/neo4j/logs:/logs `
    --env NEO4J_AUTH=neo4j/your_neo4j_password `
    --env NEO4J_PLUGINS='["graph-data-science"]' `
    neo4j:5.18.1

(Make sure to replace your_neo4j_password with the same password you put in your .env file).

Step 2: Create Vector Indexes
Navigate to the Neo4j Browser in your web browser: http://localhost:7474

Connect using the username neo4j and your password.

Run the following four commands one by one in the query bar:

CREATE VECTOR INDEX `component_descriptions` IF NOT EXISTS FOR (n:Component) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};

CREATE VECTOR INDEX `prop_descriptions` IF NOT EXISTS FOR (n:Prop) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};

CREATE VECTOR INDEX `hook_descriptions` IF NOT EXISTS FOR (n:Hook) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};

CREATE VECTOR INDEX `util_descriptions` IF NOT EXISTS FOR (n:Util) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};

CREATE VECTOR INDEX `type_descriptions` IF NOT EXISTS FOR (n:Type) ON (n.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }};

Step 3: Scrape the Website
In your terminal with the (venv) activated, run the scraper. This will fetch the raw HTML of all pages.

python src/main.py

Output: data/scraped_content_raw.json

Step 4: Parse the Raw HTML
Next, run the parser to convert the raw HTML into structured Markdown.

python src/parser.py

Output: data/parsed_structured_content.json

Step 5: Build the Knowledge Graph
Now, run the graph builder to populate your Neo4j database. This will take several minutes and will make calls to the OpenAI API.

python src/graph_builder.py

Output: A fully populated and vectorized Neo4j database.

Step 6: Ask Questions!
You are now ready to query your RAG system.

python src/query_engine.py

Output: The script will ask a pre-defined question and print the retrieved context and the final, generated answer. You can modify the question variable in query_engine.py to ask your own questions.
