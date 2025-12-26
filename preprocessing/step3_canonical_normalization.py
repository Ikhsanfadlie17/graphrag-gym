# step3_canonical_normalization.py
# Tahap 3: Canonical Normalization (Exercise, BodyPart, Equipment)

import pandas as pd
import re
import os

INPUT = "output/exercises_strict.csv"
OUTPUT_EX = "output/nodes_exercise.csv"
OUTPUT_BP = "output/nodes_bodypart.csv"
OUTPUT_EQ = "output/nodes_equipment.csv"
OUTPUT_REL_BP = "output/relationships_exercise_bodypart.csv"
OUTPUT_REL_EQ = "output/relationships_exercise_equipment.csv"

print("📥 Membaca strict exercise dataset...")
df = pd.read_csv(INPUT)

# ============================
# 1. CANONICAL CLEANING
# ============================

def clean_exercise_name(name):
    name = str(name)
    # Hapus kata tidak penting
    remove_words = [
        "variant", "version", "alternative", "type", "variation",
        "exercise", "movement", "test", "drill"
    ]
    for w in remove_words:
        name = re.sub(rf"\b{w}\b", "", name, flags=re.IGNORECASE)

    # Hapus angka
    name = re.sub(r"\b\d+\b", "", name)

    # Hapus simbol
    name = re.sub(r"[^a-zA-Z\s]", " ", name)

    name = re.sub(r"\s+", " ", name).strip()
    return name.title()


print("✨ Membersihkan nama exercise...")
df["ExerciseName"] = df["ExerciseName"].apply(clean_exercise_name)


# ============================
# 2. CANONICAL BODY PART
# ============================

print("🧠 Canonical bodypart mapping...")

bodypart_map = {
    "Chest": "Chest",
    "Pecs": "Chest",
    "Triceps": "Triceps",
    "Biceps": "Biceps",
    "Shoulders": "Shoulders",
    "Delts": "Shoulders",
    "Back": "Back",
    "Upper Back": "Back",
    "Middle Back": "Back",
    "Lower Back": "Back",
    "Lats": "Lats",
    "Lat": "Lats",
    "Quadriceps": "Quadriceps",
    "Quads": "Quadriceps",
    "Hamstrings": "Hamstrings",
    "Hams": "Hamstrings",
    "Glutes": "Glutes",
    "Legs": "Legs",
    "Calves": "Calves",
    "Abdominals": "Abs",
    "Abs": "Abs",
    "Core": "Abs",
    "Forearms": "Forearms",
    "Traps": "Traps",
    "Hip": "Hip",
}

def map_bodypart(bp):
    bp = str(bp)
    for key in bodypart_map:
        if key.lower() in bp.lower():
            return bodypart_map[key]
    return None  # dibuang nanti kalau tidak ditemukan


df["BodyPartCanonical"] = df["BodyPart"].apply(map_bodypart)
df = df.dropna(subset=["BodyPartCanonical"])


# ============================
# 3. CANONICAL EQUIPMENT
# ============================

print("🔧 Canonical equipment mapping...")

equipment_map = {
    "Dumbbell": "Dumbbell",
    "Dumbbells": "Dumbbell",
    "Barbell": "Barbell",
    "Smith Machine": "Smith Machine",
    "Cable": "Cable Machine",
    "Machine": "Machine",
    "Body Only": "Bodyweight",
    "Bodyweight": "Bodyweight",
    "Bands": "Resistance Bands",
    "Kettlebells": "Kettlebell",
}

def map_equipment(eq):
    eq = str(eq)
    for key in equipment_map:
        if key.lower() in eq.lower():
            return equipment_map[key]
    return None

df["EquipmentCanonical"] = df["Equipment"].apply(map_equipment)
df = df.dropna(subset=["EquipmentCanonical"])


# ============================
# 4. EXPORT NODES
# ============================

print("💾 Menghasilkan node exercise...")
nodes_exercise = df[["ExerciseName", "EquipmentCanonical"]].drop_duplicates()
nodes_exercise.to_csv(OUTPUT_EX, index=False)

print("💾 Menghasilkan node bodypart...")
nodes_body = df[["ExerciseName", "BodyPartCanonical"]].drop_duplicates()
nodes_body.to_csv(OUTPUT_BP, index=False)

print("💾 Menghasilkan equipment list...")
nodes_equipment = pd.DataFrame({"Equipment": df["EquipmentCanonical"].unique()})
nodes_equipment.to_csv(OUTPUT_EQ, index=False)


# ============================
# 5. EXPORT RELATIONSHIPS
# ============================

rel_bp = pd.DataFrame({
    "start": df["ExerciseName"],
    "type": "TARGETS",
    "end": df["BodyPartCanonical"]
}).drop_duplicates()

rel_bp.to_csv(OUTPUT_REL_BP, index=False)

rel_eq = pd.DataFrame({
    "start": df["ExerciseName"],
    "type": "USES_EQUIPMENT",
    "end": df["EquipmentCanonical"]
}).drop_duplicates()

rel_eq.to_csv(OUTPUT_REL_EQ, index=False)

print("🎉 Tahap 3 selesai! Semua canonical data berhasil dibuat.")
