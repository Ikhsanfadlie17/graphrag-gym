import pandas as pd
import os

# =========================================================
# AUTO LOAD NODES (buat ID jika tidak ada)
# =========================================================
def load_nodes(path, default_label=None):
    df = pd.read_csv(path)

    # Jika tidak ada kolom id / node_id → buat ID otomatis
    if "id" not in df.columns and "node_id" not in df.columns:
        print(f"[INFO] File tanpa ID, generate otomatis → {path}")
        df["id"] = range(1, len(df) + 1)

    # Normalisasi nama kolom
    if "node_id" in df.columns:
        df = df.rename(columns={"node_id": "id"})

    # Kolom label wajib
    if "label" not in df.columns:
        if default_label is None:
            raise ValueError(f"File {path} tidak punya 'label' dan default_label tidak diberikan.")
        df["label"] = default_label

    return df[["id", "name", "label"]]


# =========================================================
# LOAD NODE DATA
# =========================================================

nodes_body = load_nodes("output/nodes_bodypart_final.csv", default_label="BodyPart")
nodes_ex   = load_nodes("output/nodes_exercise_final.csv", default_label="Exercise")
nodes_eq   = load_nodes("output/nodes_equipment_final.csv", default_label="Equipment")
nodes_sc   = load_nodes("output/science/science_nodes_final_cleaned.csv", default_label="ScienceConcept")

# Gabungkan semua
all_nodes = pd.concat([nodes_body, nodes_ex, nodes_eq, nodes_sc], ignore_index=True)
all_nodes.to_csv("output/final/nodes_all_fixed.csv", index=False)

print("✔ Total nodes:", len(all_nodes))


# =========================================================
# BUAT DICTIONARY MAPPING
# =========================================================
exercise_map = nodes_ex.set_index("name")["id"].to_dict()
bodypart_map = nodes_body.set_index("name")["id"].to_dict()
equipment_map = nodes_eq.set_index("name")["id"].to_dict()
science_map = nodes_sc.set_index("name")["id"].to_dict()


# =========================================================
# FIX RELATIONSHIPS
# =========================================================
def fix_relations(path, start_map, end_map):
    df = pd.read_csv(path)

    # auto-detect kolom start/end/type
    start_col = None
    end_col = None
    type_col = None

    for col in ["start", "head", "source"]:
        if col in df.columns:
            start_col = col
            break

    for col in ["end", "tail", "target"]:
        if col in df.columns:
            end_col = col
            break

    for col in ["type", "relation", "rel_type"]:
        if col in df.columns:
            type_col = col
            break

    if start_col is None or end_col is None or type_col is None:
        raise ValueError(f"Tidak dapat menemukan kolom relasi untuk file {path}")

    # Map name → ID
    df["start_id"] = df[start_col].map(start_map)
    df["end_id"]   = df[end_col].map(end_map)

    df = df.dropna(subset=["start_id", "end_id"])

    return df[["start_id", "end_id", type_col]].rename(columns={type_col: "type"})


# =========================================================
# PROCESS ALL RELATIONSHIP FILES
# =========================================================

rels_ex_bp = fix_relations(
    "output/relationships_exercise_bodypart_final.csv",
    exercise_map,
    bodypart_map
)

rels_ex_eq = fix_relations(
    "output/relationships_exercise_equipment_final.csv",
    exercise_map,
    equipment_map
)

rels_sc = fix_relations(
    "output/science/science_rels_final_cleaned.csv",
    science_map,
    science_map
)

all_rels = pd.concat([rels_ex_bp, rels_ex_eq, rels_sc], ignore_index=True)
all_rels.to_csv("output/final/relationships_all_fixed.csv", index=False)

print("✔ Total relationships:", len(all_rels))
print("✔ Saved to output/final/relationships_all_fixed.csv")
