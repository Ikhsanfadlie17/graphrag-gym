import pandas as pd

# === Load nodes ===
nodes_ex = pd.read_csv("output/nodes_exercise_final.csv")   # kolom: name
nodes_bp = pd.read_csv("output/nodes_bodypart_final.csv")   # kolom: name

# === Load original relationship ===
rels = pd.read_csv("output/relationships_exercise_bodypart_final.csv")

# Validasi kolom
if not {"start", "end"}.issubset(rels.columns):
    raise ValueError("File relasi harus memiliki kolom 'start' dan 'end'.")

# Buat mapping nama → id
nodes_ex = nodes_ex.reset_index().rename(columns={"index": "id"})
nodes_ex["id"] += 1
map_ex = dict(zip(nodes_ex["name"].str.strip(), nodes_ex["id"]))

nodes_bp = nodes_bp.reset_index().rename(columns={"index": "id"})
nodes_bp["id"] += nodes_ex["id"].max() + 1
map_bp = dict(zip(nodes_bp["name"].str.strip(), nodes_bp["id"]))

output_rows = []

for row in rels.itertuples(index=False):
    ex_name = str(row.start).strip()
    bp_name = str(row.end).strip()

    ex_id = map_ex.get(ex_name, None)
    bp_id = map_bp.get(bp_name, None)

    if ex_id and bp_id:
        output_rows.append({
            "Exercise": ex_name,
            "BodyPart": bp_name,
            "exercise_id": ex_id,
            "bodypart_id": bp_id,
            "type": "TARGETS"
        })
    else:
        print(f"⚠️ Warning: Tidak ditemukan {ex_name} atau {bp_name}")

df = pd.DataFrame(output_rows)
df.to_csv("output/relationships_exercise_bodypart_final_FIXED.csv", index=False)

print("\n✔ Konversi selesai!")
print(df.head())
print(f"Total relasi valid: {len(df)}")
