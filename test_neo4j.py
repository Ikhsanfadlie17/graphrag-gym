from neo4j import GraphDatabase, basic_auth

driver = GraphDatabase.driver(
    "neo4j://127.0.0.1:7687",
    auth=basic_auth("neo4j", "12345678")
)

with driver.session() as session:
    print(session.run("RETURN 1 AS test").single())
