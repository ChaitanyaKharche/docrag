import os
import re
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# --- 1. Setup ---
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o", temperature=0)

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("Neo4j connection successful.")
except Exception as e:
    print(f"Neo4j connection failed: {e}")
    exit()

def retrieve_context(question: str):
    """
    Smarter retrieval:
    1. Vector search across all indexes to find starting nodes.
    2. For each starting node, get its full context (e.g., for a Prop, get its Component).
    3. From the context, find linked type definitions and fetch their descriptions too.
    """
    question_embedding = embeddings_model.embed_query(question)
    
    all_results = []
    indexes = ['component_descriptions', 'prop_descriptions', 'hook_descriptions', 'util_descriptions', 'type_descriptions']
    with driver.session(database="neo4j") as session:
        for index in indexes:
            query = "CALL db.index.vector.queryNodes($index_name, $k, $embedding) YIELD node, score RETURN node, score"
            results = session.run(query, index_name=index, k=3, embedding=question_embedding)
            all_results.extend([record for record in results])

    all_results.sort(key=lambda x: x['score'], reverse=True)
    top_results = all_results[:5]

    context = ""
    related_types = set()

    with driver.session(database="neo4j") as session:
        for record in top_results:
            node_data = record['node']
            label = list(node_data.labels)[0]
            name = node_data.get('name', 'N/A')

            context += f"Found Entity: {name} (Type: {label})\n"
            context += f"Description: {node_data.get('description', 'N/A')}\n"

            if 'type' in node_data:
                found_types = re.findall(r'\b([A-Z][a-zA-Z<>]+)\b', str(node_data['type']))
                related_types.update(found_types)
            
            if label == 'Prop':
                component_name = node_data.get('component', 'N/A')
                context += f"This is a prop for the '{component_name}' component.\n"
            
            context += "---\n"

        if related_types:
            context += "\nRelated Type Definitions:\n"
            # --- THE FIX: Add aliases 'AS name' and 'AS description' ---
            type_query = "MATCH (t:Type) WHERE t.name IN $type_names RETURN t.name AS name, t.description AS description"
            type_results = session.run(type_query, type_names=list(related_types))
            for record in type_results:
                context += f"- {record['name']}: {record['description']}\n"
    
    return context

# --- RAG Chain and Execution ---
rag_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert on the React Flow library. Use the provided, richly detailed context from the knowledge graph to answer the user's question. The context may include components, props, hooks, and related type definitions. Synthesize this information into a clear, helpful answer."),
    ("human", "CONTEXT FROM DATABASE:\n{context}\n\nQUESTION:\n{question}")
])
rag_chain = rag_prompt | llm

def ask_question(question: str):
    print("--- 1. Retrieving rich context from graph... ---")
    retrieved_context = retrieve_context(question)
    
    if not retrieved_context:
        print("--- No relevant context found. ---")
        print("\nI'm sorry, I couldn't find any relevant information in the documentation to answer your question.")
        return

    print("\n--- 2. Retrieved Context: ---\n")
    print(retrieved_context)
    
    print("--- 3. Generating answer with LLM... ---")
    response = rag_chain.invoke({"context": retrieved_context, "question": question})
    
    print("\n--- 4. Final Answer: ---")
    print(response.content)

# --- Main Execution ---
if __name__ == "__main__":
    question = "What is the nodeOrigin prop and what does its type mean?"
    ask_question(question)
    
    driver.close()