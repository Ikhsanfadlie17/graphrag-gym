# step4_refine_equipment_bodypart.py
# Refinement Level A: equipment spesifik + perbaikan bodypart

import pandas as pd
import re
import os

NODES_EX = "output/nodes_exercise.csv"
NODES_BP = "output/nodes_bodypart.csv"
NODES_EQ = "output/nodes_equipment.csv"

OUT_EX = "output/nodes_exercise_final.csv"
OUT_BP = "output/nodes_bodypart_final.csv"
OUT_EQ = "output/nodes_equipment_final.csv"
OUT_REL_BP = "output/relationships_exercise_bodypart_final.csv"
OUT_REL_EQ = "output/relationships_exercise_equipment_final.csv"

print("📥 Membaca nodes awal...")
ex = pd.read_csv(NODES_EX)          # ExerciseName, EquipmentCanonical
bp = pd.read_csv(NODES_BP)          # ExerciseName, BodyPartCanonical
eq = pd.read_csv(NODES_EQ)          # Equipment

# Merge exercise + bodypart dalam satu frame
df = ex.merge(bp, on="ExerciseName", how="left")
df.rename(columns={
    "EquipmentCanonical": "Equipment",
    "BodyPartCanonical": "BodyPart"
}, inplace=True)

# ============================
# 1. PERBAIKAN EQUIPMENT
# ============================

def refine_equipment(name, base_eq):
    name_low = str(name).lower()

    # Kettlebell family
    if "kettle" in name_low:
        return "Kettlebell"

    # Bands
    if "band" in name_low and "resistance" in base_eq.lower():
        return "Resistance Bands"

    # Smith
    if "smith" in name_low or base_eq == "Smith Machine":
        return "Smith Machine"

    # Lat pulldown / pulldown variants
    if "lat pulldown" in name_low or "lat pull down" in name_low or "pulldown" in name_low:
        return "Lat Pulldown Machine"

    # Seated row / row machine
    if "seated row" in name_low or "row machine" in name_low:
        return "Seated Row Machine"

    # Leg press / hack squat
    if "leg press" in name_low or "hack squat" in name_low:
        return "Leg Press Machine"

    # Leg extension
    if "leg extension" in name_low:
        return "Leg Extension Machine"

    # Leg curl / hamstring curl
    if "leg curl" in name_low or "hamstring curl" in name_low:
        return "Leg Curl Machine"

    # Calf raise
    if "calf" in name_low and ("press" in name_low or "raise" in name_low):
        return "Calf Raise Machine"

    # Pec deck / machine fly
    if "pec deck" in name_low or ("machine fly" in name_low and base_eq == "Machine"):
        return "Pec Deck Machine"

    # Chest press machine
    if "chest press" in name_low and base_eq in ["Machine", "Cable Machine"]:
        return "Chest Press Machine"

    # Hip thrust
    if "hip thrust" in name_low:
        if base_eq in ["Barbell", "Smith Machine"]:
            return base_eq  # Barbell Hip Thrust / Smith Hip Thrust
        return "Hip Thrust Machine"

    # Cable family
    if "cable" in name_low:
        return "Cable Machine"

    # Default berdasarkan base eq
    if base_eq in ["Barbell", "Dumbbell", "Machine", "Cable Machine",
                   "Bodyweight", "Resistance Bands", "Kettlebell"]:
        return base_eq

    # fallback
    return base_eq


print("🔧 Memperbaiki equipment menjadi spesifik...")
df["EquipmentFinal"] = df.apply(
    lambda row: refine_equipment(row["ExerciseName"], row["Equipment"]),
    axis=1
)

# ============================
# 2. PERBAIKAN BODYPART
# ============================

def refine_bodypart(name, base_bp):
    n = str(name).lower()
    bp = base_bp

    # khusus kaki
    if base_bp in ["Legs", "Quadriceps", "Hamstrings", "Glutes"]:
        if "calf" in n:
            return "Calves"
        if "hamstring" in n or "leg curl" in n or "romanian deadlift" in n or "russian deadlift" in n:
            return "Hamstrings"
        if "glute" in n or "hip thrust" in n:
            return "Glutes"
        if "squat" in n or "leg press" in n or "lunge" in n or "step up" in n:
            return "Quadriceps"

    # back vs lats
    if base_bp in ["Back", "Lats"]:
        if "lat pulldown" in n or "lat pull" in n or "pull up" in n or "chin up" in n:
            return "Lats"

    # shoulders / delts
    if base_bp in ["Shoulders"]:
        # bisa ditambah logika rear/front/side kalau dibutuhkan
        return "Shoulders"

    # core
    if base_bp in ["Abs", "Core"]:
        return "Abs"

    return bp


print("🧠 Memperbaiki bodypart menjadi lebih ilmiah...")
df["BodyPartFinal"] = df.apply(
    lambda row: refine_bodypart(row["ExerciseName"], row["BodyPart"]),
    axis=1
)

# Buang baris kalau bodypart gagal (None) — mestinya sedikit atau tidak ada
df = df.dropna(subset=["BodyPartFinal"])

# ============================
# 3. BANGUN NODE & RELASI FINAL
# ============================

print("💾 Menyusun nodes dan relationships final...")

# Node Exercise
nodes_ex_final = df[["ExerciseName", "EquipmentFinal"]].drop_duplicates()
nodes_ex_final.rename(columns={
    "ExerciseName": "name",
    "EquipmentFinal": "default_equipment"
}, inplace=True)

# Node BodyPart
nodes_bp_final = pd.DataFrame({"name": df["BodyPartFinal"].unique()})

# Node Equipment
nodes_eq_final = pd.DataFrame({"name": df["EquipmentFinal"].unique()})

# Relationships
rels_bp_final = df[["ExerciseName", "BodyPartFinal"]].drop_duplicates()
rels_bp_final.rename(columns={
    "ExerciseName": "start",
    "BodyPartFinal": "end"
}, inplace=True)
rels_bp_final["type"] = "TARGETS"

rels_eq_final = df[["ExerciseName", "EquipmentFinal"]].drop_duplicates()
rels_eq_final.rename(columns={
    "ExerciseName": "start",
    "EquipmentFinal": "end"
}, inplace=True)
rels_eq_final["type"] = "USES_EQUIPMENT"

os.makedirs("output", exist_ok=True)

nodes_ex_final.to_csv(OUT_EX, index=False)
nodes_bp_final.to_csv(OUT_BP, index=False)
nodes_eq_final.to_csv(OUT_EQ, index=False)
rels_bp_final.to_csv(OUT_REL_BP, index=False)
rels_eq_final.to_csv(OUT_REL_EQ, index=False)

print("✅ Selesai:")
print(f"  Exercise nodes : {len(nodes_ex_final)}")
print(f"  BodyPart nodes : {len(nodes_bp_final)}")
print(f"  Equipment nodes: {len(nodes_eq_final)}")
print(f"  TARGETS rel    : {len(rels_bp_final)}")
print(f"  USES_EQUIPMENT : {len(rels_eq_final)}")
print("💾 File disimpan ke folder output/")
