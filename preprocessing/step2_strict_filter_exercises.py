# step2_strict_filter_exercises.py

import pandas as pd
import re
import os

INPUT = "output/clean_kaggle.csv"  
OUTPUT = "output/exercises_strict.csv"

print(f"📥 Membaca data dari {INPUT} ...")
df = pd.read_csv(INPUT)

# Pastikan kolom yang dipakai ada
required_cols = ["ExerciseName", "Type", "BodyPart", "Equipment"]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"Kolom '{col}' tidak ditemukan di {INPUT}")

# Hitung jumlah kata pada nama latihan
df["word_count"] = df["ExerciseName"].astype(str).str.split().str.len()

# 1) Filter berdasarkan TYPE (fokus latihan beban)
valid_types = ["Strength", "Powerlifting", "Olympic Weightlifting", "Strongman"]
mask_type = df["Type"].isin(valid_types)

# 2) Filter berdasarkan panjang nama (maksimal 5 kata)
mask_words = df["word_count"] <= 5

# 3) Filter berdasarkan EQUIPMENT (alat yang umum di gym)
allowed_equipment = [
    "Dumbbell",
    "Barbell",
    "Cable",
    "Machine",
    "Smith Machine",
    "Kettlebells",
    "Body Only",      # bodyweight
    "Bands",
    "E-Z Curl Bar",
]
mask_equipment = df["Equipment"].isin(allowed_equipment)

# 4) Buang latihan yang mengandung kata kunci “aneh” / tidak relevan
bad_keywords = [
    "Holman",
    "Metaburn",
    "Gethin",
    "Routine",
    "Workout",
    "Program",
    "Circuit",
    "Test",
    "Assessment",
    "Challenge",
    "Tabata",
    "Metcon",
    "Crossfit",
    "Emom",
    "Amrap",
    "Combo",
]
regex_bad = re.compile("|".join(bad_keywords), re.IGNORECASE)
mask_bad = ~df["ExerciseName"].str.contains(regex_bad, na=False)

# 5) Buang nama yang diawali angka (biasanya dari template “30 Back …” dsb.)
mask_not_number = ~df["ExerciseName"].str.match(r"^\d", na=False)

# Gabungkan semua filter
strict = df[mask_type & mask_words & mask_equipment & mask_bad & mask_not_number].copy()

# Hapus kolom bantu
strict = strict.drop(columns=["word_count"])

# Hapus duplikat berdasarkan nama latihan + equipment + bodypart
strict = strict.drop_duplicates(subset=["ExerciseName", "Equipment", "BodyPart"])

os.makedirs("output", exist_ok=True)
strict.to_csv(OUTPUT, index=False)

print(f"✅ Strict filtering selesai.")
print(f"   Total latihan awal : {len(df)}")
print(f"   Total latihan final: {len(strict)}")
print(f"💾 Disimpan ke: {OUTPUT}")
print("\nContoh beberapa latihan hasil filter:")
print(strict[["ExerciseName", "BodyPart", "Equipment"]].head(10))
