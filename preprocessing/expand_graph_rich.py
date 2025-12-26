import os
import pandas as pd

# =====================================
# KONFIGURASI PATH
# =====================================
BASE_NODES_PATH = "output/nodes_all.csv"
BASE_RELS_PATH  = "output/relationships_all.csv"

OUT_DIR         = "output/final"
OUT_NODES_PATH  = os.path.join(OUT_DIR, "nodes_all_rich.csv")
OUT_RELS_PATH   = os.path.join(OUT_DIR, "relationships_all_rich.csv")

# Banyak variasi & teknik per exercise
VARIATION_SUFFIXES = [
    " (Beginner)",
    " (Hypertrophy Focus)",
    " (Strength Focus)",
    " (Power Focus)",
    " (Endurance Focus)",
]

TECHNIQUE_SUFFIXES = [
    " - Setup Technique",
    " - Execution Technique",
]

REL_TYPES_COPY_TO_VARIATION = {
    "TARGETS",
    "USES_EQUIPMENT",
    "SUPPORTED_BY",
    "EXPLAINED_BY",
}


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def main():
    print("🚀 Expand Graph Rich from existing nodes_all & relationships_all\n")

    # ---------------------------------
    # 1. Load base nodes & relationships
    # ---------------------------------
    if not os.path.exists(BASE_NODES_PATH):
        raise FileNotFoundError(f"Tidak ditemukan: {BASE_NODES_PATH}")
    if not os.path.exists(BASE_RELS_PATH):
        raise FileNotFoundError(f"Tidak ditemukan: {BASE_RELS_PATH}")

    nodes = pd.read_csv(BASE_NODES_PATH)
    rels  = pd.read_csv(BASE_RELS_PATH)

    required_node_cols = {"id", "name", "label"}
    if not required_node_cols.issubset(nodes.columns):
        raise ValueError(f"nodes_all.csv wajib punya kolom: {required_node_cols}, "
                         f"sekarang: {nodes.columns.tolist()}")

    required_rel_cols = {"start_id", "end_id", "type"}
    if not required_rel_cols.issubset(rels.columns):
        raise ValueError(f"relationships_all.csv wajib punya kolom minimal: {required_rel_cols}, "
                         f"sekarang: {rels.columns.tolist()}")

    has_source_col = "source" in rels.columns

    print(f"✔ Base nodes: {len(nodes)} rows")
    print(nodes["label"].value_counts())
    print()
    print(f"✔ Base rels : {len(rels)} rows")
    print(rels["type"].value_counts())
    print()

    # ---------------------------------
    # 2. Pilih Exercise sebagai base
    # ---------------------------------
    ex_nodes = nodes[nodes["label"] == "Exercise"].copy()
    if ex_nodes.empty:
        raise ValueError("Tidak ada node dengan label 'Exercise' di nodes_all.csv")

    print(f"🏋️ Total Exercise: {len(ex_nodes)}")

    # Siapkan struktur untuk node baru & relasi baru
    new_nodes = []
    new_rels  = []

    # Id baru mulai setelah id maksimum yang ada
    max_id = int(nodes["id"].max())
    next_id = max_id + 1

    # Mapping: base_exercise_id -> [variation_ids]
    ex_id_to_variations = {}
    # Mapping: base_exercise_id -> [technique_ids]
    ex_id_to_techniques = {}

    # ---------------------------------
    # 3. Buat ExerciseVariation & Technique nodes
    # ---------------------------------
    print("\n🧱 Generate ExerciseVariation & Technique nodes...")

    for _, row in ex_nodes.iterrows():
        base_id   = int(row["id"])
        base_name = str(row["name"])

        # 3.1 Variations
        variation_ids = []
        for suf in VARIATION_SUFFIXES:
            var_name = f"{base_name}{suf}"
            new_nodes.append({
                "id": next_id,
                "name": var_name,
                "label": "ExerciseVariation"
            })
            # Relasi VARIATION_OF (variation -> base exercise)
            new_rels.append({
                "start_id": next_id,
                "end_id": base_id,
                "type": "VARIATION_OF",
                "source": "auto_variation"
            })
            variation_ids.append(next_id)
            next_id += 1

        ex_id_to_variations[base_id] = variation_ids

        # 3.2 Techniques
        technique_ids = []
        for suf in TECHNIQUE_SUFFIXES:
            tech_name = f"{base_name}{suf}"
            new_nodes.append({
                "id": next_id,
                "name": tech_name,
                "label": "Technique"
            })
            # Base Exercise -> Technique
            new_rels.append({
                "start_id": base_id,
                "end_id": next_id,
                "type": "REQUIRES_TECHNIQUE",
                "source": "auto_technique"
            })
            technique_ids.append(next_id)
            next_id += 1

        ex_id_to_techniques[base_id] = technique_ids

    print(f"✔ Tambah ExerciseVariation: {sum(len(v) for v in ex_id_to_variations.values())}")
    print(f"✔ Tambah Technique       : {sum(len(v) for v in ex_id_to_techniques.values())}")

    # ---------------------------------
    # 4. Copy relasi dari base Exercise ke Variations
    # ---------------------------------
    print("\n🔗 Copy relasi penting dari Exercise ke Variations...")

    # Mulai dengan salin semua rel lama apa adanya
    for _, row in rels.iterrows():
        start_id = int(row["start_id"])
        end_id   = int(row["end_id"])
        rtype    = str(row["type"]).strip()
        source   = str(row["source"]) if has_source_col else "base_graph"

        # rel lama tetap
        new_rels.append({
            "start_id": start_id,
            "end_id": end_id,
            "type": rtype,
            "source": source
        })

        # Jika rel ini keluar dari Exercise, dan type-nya termasuk yang kita copy
        if start_id in ex_id_to_variations and rtype in REL_TYPES_COPY_TO_VARIATION:
            for vid in ex_id_to_variations[start_id]:
                new_rels.append({
                    "start_id": vid,
                    "end_id": end_id,
                    "type": rtype,
                    "source": f"auto_from_exercise_{rtype}"
                })

    # ---------------------------------
    # 5. Tambah REQUIRES_TECHNIQUE untuk semua variation
    # ---------------------------------
    print("\n🧠 Tambah REQUIRES_TECHNIQUE dari Variation → Technique...")

    for base_id, var_ids in ex_id_to_variations.items():
        tech_ids = ex_id_to_techniques.get(base_id, [])
        for vid in var_ids:
            for tid in tech_ids:
                new_rels.append({
                    "start_id": vid,
                    "end_id": tid,
                    "type": "REQUIRES_TECHNIQUE",
                    "source": "auto_technique"
                })

    # ---------------------------------
    # 6. Gabungkan & bersihkan duplikat
    # ---------------------------------
    print("\n🧩 Merge & clean nodes/relationships...")

    # Nodes
    new_nodes_df = pd.DataFrame(new_nodes)
    nodes_rich   = pd.concat([nodes, new_nodes_df], ignore_index=True)

    # Pastikan id unik
    if nodes_rich["id"].duplicated().any():
        raise ValueError("Terdapat id duplikat di nodes_rich — cek logika next_id.")

    # Relationships
    rels_rich = pd.DataFrame(new_rels)

    # Hilangkan duplikat (start_id, end_id, type)
    before = len(rels_rich)
    rels_rich = rels_rich.drop_duplicates(subset=["start_id", "end_id", "type"])
    after = len(rels_rich)

    print(f"🔢 Relasi sebelum drop dup : {before}")
    print(f"🔢 Relasi sesudah drop dup : {after}")

    # ---------------------------------
    # 7. Simpan ke output/final
    # ---------------------------------
    ensure_dir(OUT_DIR)

    nodes_rich.to_csv(OUT_NODES_PATH, index=False, encoding="utf-8")
    rels_rich.to_csv(OUT_RELS_PATH, index=False, encoding="utf-8")

    print("\n✅ DONE — RICH graph generated.")
    print(f"   Nodes rich : {len(nodes_rich)} → {OUT_NODES_PATH}")
    print(f"   Rels  rich : {len(rels_rich)} → {OUT_RELS_PATH}")


if __name__ == "__main__":
    main()
