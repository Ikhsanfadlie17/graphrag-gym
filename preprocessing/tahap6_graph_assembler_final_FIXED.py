import pandas as pd
import os

BASE = "output"
SCI_DIR = os.path.join(BASE, "science")
OUT_FINAL = os.path.join(BASE, "final")

os.makedirs(OUT_FINAL, exist_ok=True)

# ==============================
#  Helper loader
# ==============================
def load_csv(path, required=None):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ File tidak ditemukan: {path}")

    df = pd.read_csv(path)

    if required:
        for col in required:
            if col not in df.columns:
                raise ValueError(f"❌ File {path} HARUS punya kolom {required}, "
                                 f"tapi hanya ada: {df.columns.tolist()}")

    return df


# ==============================
#  Main Builder
# ==============================
def main():

    print("🚀 Tahap 6 – Graph Assembler FINAL (FIXED MAP)")

    # ==============================
    # 1. LOAD NODES
    # ==============================
    print("\n📥 Load semua node dasar...")

    nodes_ex = load_csv(
        os.path.join(BASE, "nodes_exercise_final_FIXED.csv"),
        ["id", "name", "label"]
    )

    nodes_bp = load_csv(
        os.path.join(BASE, "nodes_bodypart_final_FIXED.csv"),
        ["id", "name", "label"]
    )

    nodes_eq = load_csv(
        os.path.join(BASE, "nodes_equipment_final_FIXED.csv"),
        ["id", "name", "label"]
    )

    nodes_sci = load_csv(
        os.path.join(SCI_DIR, "science_nodes_final_cleaned.csv"),
        ["name", "label"]
    )

    # Tambahkan ID unik untuk science nodes jika belum ada
    if "id" not in nodes_sci.columns:
        nodes_sci["id"] = range(30000, 30000 + len(nodes_sci))

    # Gabungkan semua node
    nodes_all = pd.concat([nodes_ex, nodes_bp, nodes_eq, nodes_sci], ignore_index=True)

    print(f"✔ Total node unik: {len(nodes_all)}")
    print(nodes_all["label"].value_counts())

    # Simpan node final
    nodes_all.to_csv(os.path.join(OUT_FINAL, "nodes_all_rich.csv"), index=False)
    print(f"💾 Nodes final disimpan ke: {OUT_FINAL}/nodes_all_rich.csv")

    # ==============================
    # 2. LOAD RELATIONSHIPS
    # ==============================
    print("\n📥 Load relation files...")

    # 2.1 Exercise → BodyPart (FILE MAP FINAL)
    REL_EX_BP = os.path.join(BASE, "relationships_exercise_bodypart_FIXED_MAPPED.csv")

    rel_ex_bp = load_csv(REL_EX_BP, required=["start_id", "end_id", "type"])

    print(f"✔ Load EXERCISE → BODYPART (mapped): {len(rel_ex_bp)} rows")

    # Tambahkan source
    rel_ex_bp["source"] = "exercise_bodypart_fixed"

    # 2.2 Exercise → Equipment (gunakan default_equipment)
    rel_ex_eq_rows = []
    for _, row in nodes_ex.iterrows():
        eq_name = row["default_equipment"].strip()

        eq_match = nodes_eq[nodes_eq["name"] == eq_name]
        if not eq_match.empty:
            eq_id = int(eq_match.iloc[0]["id"])
            rel_ex_eq_rows.append([int(row["id"]), eq_id, "USES_EQUIPMENT", "default_equipment"])

    rel_ex_eq = pd.DataFrame(rel_ex_eq_rows, columns=["start_id", "end_id", "type", "source"])
    print(f"✔ Build USES_EQUIPMENT: {len(rel_ex_eq)} rows")

    # 2.3 Science relations
    sci_rels = load_csv(
        os.path.join(SCI_DIR, "science_rels_final_cleaned.csv"),
        required=["start", "type", "end"]
    )

    # Map science name → id
    sci_map = nodes_sci.set_index("name")["id"].to_dict()

    rel_sci_rows = []
    for _, row in sci_rels.iterrows():
        s = str(row["start"]).strip()
        e = str(row["end"]).strip()

        if s not in sci_map or e not in sci_map:
            continue

        rel_sci_rows.append([
            sci_map[s], sci_map[e], row["type"], "science_relation"
        ])

    rel_sci = pd.DataFrame(rel_sci_rows, columns=["start_id", "end_id", "type", "source"])
    print(f"✔ Build SCIENCE relations: {len(rel_sci)} rows")

    # ==============================
    # 3. GABUNGKAN SEMUA RELASI
    # ==============================
    rel_all = pd.concat([rel_ex_bp, rel_ex_eq, rel_sci], ignore_index=True)

    # Hapus duplikat relasi
    rel_all = rel_all.drop_duplicates()

    print("\n🔢 Statistik relasi FINAL:")
    print(rel_all["type"].value_counts())

    # Simpan relasi final
    rel_all.to_csv(os.path.join(OUT_FINAL, "relationships_all_rich.csv"), index=False)
    print(f"\n💾 Relationships final disimpan ke: {OUT_FINAL}/relationships_all_rich.csv")

    print("\n🎉 Tahap 6 FINAL FIXED SELESAI! Graph SIAP untuk Neo4j.\n")


if __name__ == "__main__":
    main()
