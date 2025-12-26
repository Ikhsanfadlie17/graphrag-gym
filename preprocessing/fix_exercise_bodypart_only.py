import pandas as pd
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
OUT = os.path.join(ROOT, "output")
FINAL = os.path.join(OUT, "final")

EX_NODES = os.path.join(OUT, "nodes_exercise_final_FIXED.csv")
BP_NODES = os.path.join(OUT, "nodes_bodypart_final_FIXED.csv")
REL_EX_BP = os.path.join(OUT, "relationships_exercise_bodypart_final_FIXED2.csv")

OUT_REL = os.path.join(FINAL, "relationships_exercise_bodypart_FIXED_MAPPED.csv")


def normalize(x):
    return str(x).strip().lower()


print("📥 Loading nodes...")
ex_df = pd.read_csv(EX_NODES)
bp_df = pd.read_csv(BP_NODES)
rel_df = pd.read_csv(REL_EX_BP)

# Build lowercase name → id map
ex_map = {normalize(r["name"]): int(r["id"]) for _, r in ex_df.iterrows()}
bp_map = {normalize(r["name"]): int(r["id"]) for _, r in bp_df.iterrows()}

print("✔ Exercise names loaded:", len(ex_map))
print("✔ BodyPart names loaded:", len(bp_map))

fixed_rows = []

missing_ex = []
missing_bp = []

for _, row in rel_df.iterrows():
    ex_name = normalize(row["Exercise"])
    bp_name = normalize(row["BodyPart"])
    rtype = row["type"]

    ex_id = ex_map.get(ex_name)
    bp_id = bp_map.get(bp_name)

    if ex_id is None:
        missing_ex.append(row["Exercise"])
        continue

    if bp_id is None:
        missing_bp.append(row["BodyPart"])
        continue

    fixed_rows.append({
        "start_id": ex_id,
        "end_id": bp_id,
        "type": rtype,
        "source": "exercise_bodypart_fixed"
    })

fixed_df = pd.DataFrame(fixed_rows)
fixed_df.to_csv(OUT_REL, index=False)

print("💾 FIXED saved to:", OUT_REL)
print("👉 Total mapped:", len(fixed_df))
print("❌ Missing Exercise:", len(missing_ex))
print("❌ Missing Bodypart:", len(missing_bp))
