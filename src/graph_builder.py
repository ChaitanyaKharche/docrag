import json
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List, Optional
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

# --- 1. Database & Model Setup ---
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
llm = ChatOpenAI(model="gpt-4o", temperature=0)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("Neo4j connection successful.")
except Exception as e:
    print(f"Neo4j connection failed: {e}")
    exit()

def run_cypher_query(query, params={}):
    with driver.session(database="neo4j") as session:
        session.run(query, params)

run_cypher_query("MATCH (n) DETACH DELETE n")
print("Database cleared for a fresh start.")

# --- 2. Expanded Pydantic Schemas ---
class Prop(BaseModel):
    name: str = Field(description="The name of the prop.")
    type: str = Field(description="The typescript type of the prop.")
    default: Optional[str] = Field(description="The default value of the prop.")
    description: str = Field(description="A concise description of what the prop does.")

class Param(BaseModel):
    name: str = Field(description="The name of the parameter.")
    type: str = Field(description="The typescript type of the parameter.")
    description: str = Field(description="A concise description of what the parameter does.")

class Component(BaseModel):
    name: str = Field(description="The name of the React component, e.g., <Background />.")
    description: str = Field(description="A concise description of what the component does.")
    props: Optional[List[Prop]] = Field(description="A list of all props the component accepts.")

class Hook(BaseModel):
    name: str = Field(description="The name of the React hook, e.g., useNodes().")
    description: str = Field(description="A concise description of what the hook does.")
    params: Optional[List[Param]] = Field(description="A list of parameters the hook accepts.")
    return_value: Optional[str] = Field(description="A description of what the hook returns.")

class Util(BaseModel):
    name: str = Field(description="The name of the utility function, e.g., addEdge.")
    description: str = Field(description="A concise description of what the function does.")
    params: Optional[List[Param]] = Field(description="A list of parameters the function accepts.")
    return_value: Optional[str] = Field(description="A description of what the function returns.")
    
class Type(BaseModel):
    name: str = Field(description="The name of the TypeScript type, e.g., Node.")
    description: str = Field(description="A description of the type definition or what it represents.")

class ExtractedData(BaseModel):
    """A container for all entities extracted from a documentation page."""
    components: Optional[List[Component]] = None
    hooks: Optional[List[Hook]] = None
    utils: Optional[List[Util]] = None
    types: Optional[List[Type]] = None

# --- 3. Updated LLM Parser ---
parser_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an expert entity extraction system. Your task is to parse technical documentation in Markdown format.
            Identify all Components, Hooks, Utility Functions, and Type Definitions on the page.
            - A Component is a JSX element like `<Background />`. It has props, which are usually in a Markdown table.
            - A Hook is a function starting with "use", like `useNodes()`. It can have parameters and a return value.
            - A Utility is a regular function like `addEdge()`. It can have parameters and a return value.
            - A Type is a TypeScript definition, like `type Node = ...`.
            Extract all entities you find and structure the output as a JSON object that strictly follows the provided `ExtractedData` schema.
            If a page describes multiple entities (e.g., a component and its related types), extract all of them.
            """,
        ),
        ("human", "Documentation content:\n\n{content}"),
    ]
)
structured_llm = parser_prompt | llm.with_structured_output(ExtractedData)

# --- 4. Expanded Ingestion Logic ---
PARSED_FILE = 'data/parsed_structured_content.json'
with open(PARSED_FILE, 'r', encoding='utf-8') as f:
    parsed_data = json.load(f)

print(f"Found {len(parsed_data)} documents to process.")

for i, doc in enumerate(parsed_data):
    print(f"\n--- Processing doc {i+1}/{len(parsed_data)}: {doc['url']} ---")
    try:
        extracted_data = structured_llm.invoke({"content": doc['content']})

        # Ingest Components and Props
        if extracted_data.components:
            for component in extracted_data.components:
                comp_embedding = embeddings_model.embed_query(component.description)
                run_cypher_query(
                    "MERGE (c:Component {name: $name}) SET c.description = $description, c.url = $url, c.embedding = $embedding",
                    {"name": component.name, "description": component.description, "url": doc['url'], "embedding": comp_embedding}
                )
                if component.props:
                    for prop in component.props:
                        prop_text = f"Prop: {prop.name}, Type: {prop.type}, Description: {prop.description}"
                        prop_embedding = embeddings_model.embed_query(prop_text)
                        run_cypher_query(
                            """
                            MATCH (c:Component {name: $comp_name})
                            MERGE (p:Prop {name: $prop_name, component: $comp_name})
                            SET p.type = $type, p.default = $default, p.description = $description, p.embedding = $embedding
                            MERGE (c)-[:HAS_PROP]->(p)
                            """,
                            {"comp_name": component.name, "prop_name": prop.name, "type": prop.type, "default": prop.default, "description": prop.description, "embedding": prop_embedding}
                        )
                print(f"  -> Ingested Component: {component.name}")

        # Ingest Hooks
        if extracted_data.hooks:
            for hook in extracted_data.hooks:
                hook_embedding = embeddings_model.embed_query(hook.description)
                run_cypher_query(
                    "MERGE (h:Hook {name: $name}) SET h.description = $description, h.url = $url, h.embedding = $embedding, h.returns = $returns",
                    {"name": hook.name, "description": hook.description, "url": doc['url'], "embedding": hook_embedding, "returns": hook.return_value or ""}
                )
                print(f"  -> Ingested Hook: {hook.name}")

        # Ingest Utils
        if extracted_data.utils:
            for util in extracted_data.utils:
                util_embedding = embeddings_model.embed_query(util.description)
                run_cypher_query(
                    "MERGE (u:Util {name: $name}) SET u.description = $description, u.url = $url, u.embedding = $embedding, u.returns = $returns",
                    {"name": util.name, "description": util.description, "url": doc['url'], "embedding": util_embedding, "returns": util.return_value or ""}
                )
                print(f"  -> Ingested Util: {util.name}")
                
        # Ingest Types
        if extracted_data.types:
            for type_def in extracted_data.types:
                type_embedding = embeddings_model.embed_query(type_def.description)
                run_cypher_query(
                    "MERGE (t:Type {name: $name}) SET t.description = $description, t.url = $url, t.embedding = $embedding",
                    {"name": type_def.name, "description": type_def.description, "url": doc['url'], "embedding": type_embedding}
                )
                print(f"  -> Ingested Type: {type_def.name}")

    except Exception as e:
        print(f"  -> An error occurred: {e}")

print("\n--- Full graph population and vectorization complete. ---")
driver.close()