import pandas as pd
import re

RAW = "datasets/megaGymDataset.csv"
OUT = "output/clean_kaggle.csv"

df = pd.read_csv(RAW)

# ----------------------------------
# NAMA EXERCISE — NORMALISASI
# ----------------------------------
def clean_name(x):
    if pd.isna(x): return ""
    x = re.sub(r"[^a-zA-Z0-9 ]", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x.title()

df["ExerciseName"] = df["Title"].apply(clean_name)

# remove weird non-gym items
valid = df[df["ExerciseName"].str.len() > 3]

# filtering by familiar gym words
keywords = ["Press", "Curl", "Row", "Squat", "Lateral",
            "Deadlift", "Raise", "Fly", "Bench",
            "Pulldown", "Extension", "Cable", "Machine",
            "Barbell", "Dumbbell", "Kettlebell", "Smith",
            "Chest", "Shoulder", "Back", "Tricep", "Bicep",
            "Quad", "Hamstring", "Glute", "Calf"]

valid = valid[valid["ExerciseName"].str.contains("|".join(keywords), case=False)]

valid = valid.drop_duplicates(subset=["ExerciseName"])

valid.to_csv(OUT, index=False)
print("DONE:", len(valid), "clean exercises.")
