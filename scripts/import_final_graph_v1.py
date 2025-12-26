# scripts/import_final_graph.py
# FINAL FIX FOR NEO4J 5.x
# -----------------------------------------------

from neo4j import GraphDatabase
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

NODES_CSV = "output/final/nodes_all_rich_BIG.csv"
RELS_CSV  = "output/final/relationships_all_rich_BIG.csv"

URI      = os.getenv("NEO4J_URI")
USER     = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")


# ============================================================
# CONNECT
# ============================================================
def get_driver():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD), encrypted=False)
    return driver


# ============================================================
# CLEAR DATABASE
# ============================================================
def clear_db(driver):
    with driver.session(database="neo4j") as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("✔ Database cleared.")


# ============================================================
# CREATE CONSTRAINTS (Neo4j 5 syntax)
# ============================================================
def create_constraints(driver):

    constraints = [
        ("exercise_id_unique",     "Exercise"),
        ("bodypart_id_unique",     "BodyPart"),
        ("equipment_id_unique",    "Equipment"),
        ("science_id_unique",      "ScienceConcept")
    ]

    with driver.session(database="neo4j") as session:
        for name, label in constraints:
            query = f"""
            CREATE CONSTRAINT {name} IF NOT EXISTS
            FOR (n:{label})
            REQUIRE n.id IS UNIQUE
            """
            session.run(query)

    print("✔ Constraints created (Neo4j 5 syntax).")


# ============================================================
# IMPORT NODES
# ============================================================
def import_nodes(driver):
    df = pd.read_csv(NODES_CSV)

    print(f"📥 Importing {len(df)} nodes...")

    with driver.session(database="neo4j") as session:
        for _, row in df.iterrows():
            q = f"""
            MERGE (n:{row['label']} {{id: $id}})
            SET n.name = $name
            """
            session.run(q, id=int(row["id"]), name=row["name"])

    print("✔ Nodes imported.\n")


# ============================================================
# IMPORT RELATIONSHIPS
# ============================================================
def import_relationships(driver):
    df = pd.read_csv(RELS_CSV)

    s = "start_id" if "start_id" in df.columns else "start"
    t = "end_id"   if "end_id"   in df.columns else "end"

    print(f"📥 Importing {len(df)} relationships...")

    with driver.session(database="neo4j") as session:
        for _, row in df.iterrows():
            q = f"""
            MATCH (a {{id: $start_id}})
            MATCH (b {{id: $end_id}})
            MERGE (a)-[:`{row['type']}`]->(b)
            """
            session.run(q,
                start_id=int(row[s]),
                end_id=int(row[t])
            )

    print("✔ Relationships imported.\n")


# ============================================================
# MAIN
# ============================================================
def main():
    print("🚀 Importing FINAL FIXED GRAPH...\n")

    driver = get_driver()

    clear_db(driver)
    create_constraints(driver)
    import_nodes(driver)
    import_relationships(driver)

    driver.close()
    print("🎉 DONE! Graph berhasil di-import ke Neo4j.")


if __name__ == "__main__":
    main()
