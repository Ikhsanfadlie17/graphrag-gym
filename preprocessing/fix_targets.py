import pandas as pd

print("📥 Loading nodes...")

nodes_ex = pd.read_csv("output/nodes_exercise_final.csv")  # kolom: name
nodes_bp = pd.read_csv("output/nodes_bodypart_final.csv")  # kolom: name

rels_raw = pd.read_csv("output/relationships_exercise_bodypart_final.csv")  # kolom: Exercise, BodyPart

# Validasi
if not {"Exercise", "BodyPart"}.issubset(rels_raw.columns):
    raise ValueError("File relasi MUST punya kolom Exercise & BodyPart")

# --- Generate ID ulang yang bersih ---
nodes_ex = nodes_ex.reset_index().rename(columns={"index": "exercise_id"})
nodes_ex["exercise_id"] += 1

nodes_bp = nodes_bp.reset_index().rename(columns={"index": "bodypart_id"})
nodes_bp["bodypart_id"] += nodes_ex["exercise_id"].max() + 1

# Mapping
map_ex = dict(zip(nodes_ex["name"].str.strip(), nodes_ex["exercise_id"]))
map_bp = dict(zip(nodes_bp["name"].str.strip(), nodes_bp["bodypart_id"]))

print(f"✔ Total Exercise: {len(nodes_ex)}")
print(f"✔ Total BodyPart: {len(nodes_bp)}")

# --- Build relasi baru ---
new_relations = []

for row in rels_raw.itertuples(index=False):
    ex = str(row.Exercise).strip()
    bp = str(row.BodyPart).strip()

    ex_id = map_ex.get(ex, None)
    bp_id = map_bp.get(bp, None)

    if ex_id and bp_id:
        new_relations.append({
            "start_id": ex_id,
            "end_id": bp_id,
            "type": "TARGETS",
            "Exercise": ex,
            "BodyPart": bp
        })
    else:
        print(f"⚠️ SKIPPED: {ex} → {bp} (invalid)")

df = pd.DataFrame(new_relations)
df.to_csv("output/relationships_exercise_bodypart_fixed.csv", index=False)

print("\n🎉 FIX COMPLETE!")
print(f"Total relasi valid: {len(df)}")
print(df.head())
