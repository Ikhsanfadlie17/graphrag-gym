import os
import json
import pandas as pd
from tqdm import tqdm
from openai import OpenAI
from sentence_transformers import SentenceTransformer, util

# =============================
#  CONFIG
# =============================

MODEL = SentenceTransformer("all-mpnet-base-v2")

OUTPUT_DIR = "output/final"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# input nodes
EXERCISE_NODE = "output/nodes_exercise_final.csv"
BODYPART_NODE = "output/nodes_bodypart_final.csv"
EQUIPMENT_NODE = "output/nodes_equipment_final.csv"
SCIENCE_NODE = "output/science/science_nodes_final_cleaned.csv"

# input relationships (SUDAH ADA)
REL_EX_SC = "output/final/relationships_exercise_science.csv"
REL_BP_SC = "output/final/relationships_bodypart_science.csv"

# output final merged graph
FINAL_NODES = f"{OUTPUT_DIR}/nodes_all.csv"
FINAL_RELS = f"{OUTPUT_DIR}/relationships_all.csv"


# =============================
#  LOAD DATA
# =============================

def load_nodes():
    print("📥 Loading node files...")

    ex_df = pd.read_csv(EXERCISE_NODE)
    bp_df = pd.read_csv(BODYPART_NODE)
    eq_df = pd.read_csv(EQUIPMENT_NODE)
    sc_df = pd.read_csv(SCIENCE_NODE)

    # Assign label kolom
    ex_df["label"] = "Exercise"
    bp_df["label"] = "BodyPart"
    eq_df["label"] = "Equipment"
    sc_df["label"] = "ScienceConcept"

    return ex_df, bp_df, eq_df, sc_df


def load_relationships():
    print("📥 Loading relationship files...")

    rel_ex_sc = pd.read_csv(REL_EX_SC)
    rel_bp_sc = pd.read_csv(REL_BP_SC)

    rel_ex_sc["type"] = "EXPLAINS"
    rel_bp_sc["type"] = "SUPPORTS"

    return rel_ex_sc, rel_bp_sc


# =============================
#  MERGE GRAPH
# =============================

def merge_graph():
    ex_df, bp_df, eq_df, sc_df = load_nodes()
    rel_ex_sc, rel_bp_sc = load_relationships()

    print("🧩 Merging Nodes...")

    all_nodes = pd.concat([
        ex_df[["name", "label"]],
        bp_df[["name", "label"]],
        eq_df[["name", "label"]],
        sc_df[["name", "label"]],
    ], ignore_index=True)

    # drop duplicate node names
    all_nodes = all_nodes.drop_duplicates(subset=["name"])

    all_nodes.to_csv(FINAL_NODES, index=False, encoding="utf-8")
    print(f"✅ Saved Nodes: {FINAL_NODES}")

    print("🔗 Merging Relationships...")

    all_relationships = pd.concat([
        rel_ex_sc,
        rel_bp_sc
    ], ignore_index=True)

    all_relationships.to_csv(FINAL_RELS, index=False, encoding="utf-8")
    print(f"✅ Saved Relationships: {FINAL_RELS}")

    print("\n🎉 Tahap 6 selesai — FINAL GRAPH READY FOR NEO4J!\n")


# =============================
#  MAIN
# =============================

if __name__ == "__main__":
    merge_graph()
