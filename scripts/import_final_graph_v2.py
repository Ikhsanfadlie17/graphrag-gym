import os
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

# =======================================================
# CONFIG
# =======================================================

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

# Sesuaikan dengan lokasi file kamu
NODES_CSV = "output/final/nodes_all_rich_v2.csv"
RELS_CSV  = "output/final/relationships_all_rich_v2.csv"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# =======================================================
# UTIL
# =======================================================

def clear_db():
    """Hapus semua node & relasi di database."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("✔ Database cleared.")


def create_constraints(labels):
    """
    Buat constraint id unik per label utama.
    Semua node juga diberi label umum :GraphNode.
    """
    with driver.session() as session:
        for lbl in labels:
            cypher = f"""
            CREATE CONSTRAINT IF NOT EXISTS
            FOR (n:{lbl})
            REQUIRE n.id IS UNIQUE
            """
            session.run(cypher)

        # constraint umum (boleh, tapi optional)
        session.run("""
            CREATE CONSTRAINT IF NOT EXISTS
            FOR (n:GraphNode)
            REQUIRE n.id IS UNIQUE
        """)
    print("🔧 Constraints created.")


# =======================================================
# IMPORT NODES
# =======================================================

def import_nodes():
    df = pd.read_csv(NODES_CSV)

    # Pastikan kolom yang diperlukan ada
    required = {"id", "name", "label"}
    if not required.issubset(df.columns):
        raise ValueError(f"Kolom nodes harus mengandung: {required}")

    # Daftar label unik (Exercise, BodyPart, Equipment, dll)
    labels = sorted(df["label"].dropna().unique().tolist())
    create_constraints(labels)

    with driver.session() as session:
        for _, row in df.iterrows():
            node_id = int(row["id"])
            name = str(row["name"])
            label = str(row["label"])

            # Hati-hati: label dimasukkan langsung ke query
            # Pastikan hanya berisi huruf/angka/underscore
            safe_label = "".join(ch for ch in label if ch.isalnum() or ch == "_")
            if not safe_label:
                safe_label = "GraphNode"

            cypher = f"""
            MERGE (n:GraphNode:{safe_label} {{id: $id}})
            SET n.name  = $name,
                n.label = $label
            """

            session.run(cypher, id=node_id, name=name, label=label)

    print(f"✔ Imported {len(df)} nodes.")


# =======================================================
# IMPORT RELATIONSHIPS
# =======================================================

def import_relationships():
    df = pd.read_csv(RELS_CSV)

    required = {"start_id", "end_id", "type", "source"}
    if not required.issubset(df.columns):
        raise ValueError(f"Kolom relationships harus mengandung: {required}")

    total = len(df)
    print(f"📥 Importing {total} relationships...")

    with driver.session() as session:
        for idx, row in df.iterrows():
            start_id = int(row["start_id"])
            end_id   = int(row["end_id"])
            rel_type = str(row["type"]).upper().strip()
            source   = str(row["source"])

            # Bersihkan nama relasi (hanya huruf/angka/underscore)
            rel_safe = "".join(ch for ch in rel_type if ch.isalnum() or ch == "_")
            if not rel_safe:
                continue  # skip kalau aneh

            cypher = f"""
            MATCH (s:GraphNode {{id: $start_id}})
            MATCH (t:GraphNode {{id: $end_id}})
            MERGE (s)-[r:{rel_safe} {{source: $source}}]->(t)
            """

            session.run(cypher, start_id=start_id, end_id=end_id, source=source)

            if (idx + 1) % 5000 == 0:
                print(f"   ... {idx+1}/{total} relationships imported")

    print(f"✔ Imported {total} relationships.")


# =======================================================
# MAIN
# =======================================================

def main():
    print("🚀 Importing FINAL Rich Graph...\n")

    print("🧹 Clearing old database...")
    clear_db()

    print("\n📥 Importing nodes...")
    import_nodes()

    print("\n📥 Importing relationships...")
    import_relationships()

    print("\n🎉 Done! Graph siap dipakai untuk Graph RAG.\n")


if __name__ == "__main__":
    main()
