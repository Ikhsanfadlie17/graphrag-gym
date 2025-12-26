import pandas as pd

INPUT = "output/relationships_exercise_bodypart_final.csv"
OUTPUT = "output/relationships_exercise_bodypart_final_FIXED2.csv"

df = pd.read_csv(INPUT)

# HARUS punya kolom start & end
if "start" not in df.columns or "end" not in df.columns:
    raise ValueError("File ini tidak punya kolom 'start' dan 'end'. Tidak bisa dikonversi.")

# rename ke format baru
df_fixed = df.rename(columns={
    "start": "Exercise",
    "end": "BodyPart"
})

# pastikan kolom type ada
if "type" not in df_fixed.columns:
    df_fixed["type"] = "TARGETS"

df_fixed = df_fixed[["Exercise", "BodyPart", "type"]]

df_fixed.to_csv(OUTPUT, index=False)

print("✔ File berhasil dikonversi:")
print(f"  → {OUTPUT}")
print(df_fixed.head())
