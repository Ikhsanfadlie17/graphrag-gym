import pandas as pd

# ============
# 1. PERBAIKI FILE BODY PART
# ============
df = pd.read_csv("output/relationships_exercise_bodypart_final.csv")

if set(df.columns) == {"start", "end", "type"}:
    df = df.rename(columns={
        "start": "Exercise",
        "end": "BodyPart"
    })
    df = df[["Exercise", "BodyPart", "type"]]
    df.to_csv("output/relationships_exercise_bodypart_final_FIXED2.csv", index=False)
    print("✔ BodyPart relations fixed → relationships_exercise_bodypart_final_FIXED2.csv")
else:
    print("⚠ Struktur BodyPart tidak dikenali:", df.columns.tolist())


# ============
# 2. PERBAIKI FILE EQUIPMENT
# ============
df2 = pd.read_csv("output/relationships_exercise_equipment_final.csv")

if set(df2.columns) == {"start", "end", "type"}:
    df2 = df2.rename(columns={
        "start": "Exercise",
        "end": "Equipment"
    })
    df2 = df2[["Exercise", "Equipment", "type"]]
    df2.to_csv("output/relationships_exercise_equipment_final_FIXED2.csv", index=False)
    print("✔ Equipment relations fixed → relationships_exercise_equipment_final_FIXED2.csv")
else:
    print("⚠ Struktur Equipment tidak dikenali:", df2.columns.tolist())


print("\n🎉 Semua relasi berhasil diformat ulang.")
