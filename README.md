# GraphRAG Gym

An Informatics Engineering thesis project that answers exercise questions using a Neo4j knowledge graph and a language model. The system retrieves exercise context such as target muscles, equipment, and body parts before generating a recommendation.

[Read the portfolio case study](https://ikhsannurfadlie.vercel.app/proyek/graphrag-fitness/)

## How it works

1. A user asks a workout question in the Next.js interface.
2. The Python backend identifies constraints such as the target body part, available equipment, or requested number of exercises.
3. Cypher queries retrieve matching exercises and relationships from Neo4j.
4. The language model uses the retrieved context to write the answer. The interface can display the associated graph and query.

**Example question** · “What are three back exercises I can do with dumbbells?”

## Implementation

| Part | Purpose |
| --- | --- |
| [`web/`](web/) | Next.js and TypeScript interface with conversation, graph visualization, and evaluation views |
| [`python-backend/`](python-backend/) | Flask API, Neo4j retrieval, and LLM integration through LangChain |
| [`preprocessing/`](preprocessing/) | Exercise data cleaning and graph construction |
| [`scripts/`](scripts/) | Neo4j import utilities, graph schema, and query utilities |

## Evaluation

The [evaluation module](python-backend/evaluation.py) includes checks for faithfulness to the retrieved Neo4j context and answer relevance to the question. The portfolio case study describes the retrieval approach and reports the evaluation results.

## Local setup notes

Run the Python backend with a Neo4j database populated using the graph import utilities and an OpenAI API key. The Next.js frontend forwards queries to the backend at `http://localhost:5000` by default. Use `NEXT_PUBLIC_PYTHON_BACKEND_URL` to configure a different address.
