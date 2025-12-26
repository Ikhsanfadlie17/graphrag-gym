import pandas as pd

# =============================
# 1. FIX Exercise Nodes
# =============================
ex = pd.read_csv("output/nodes_exercise_final.csv")
ex = ex.rename(columns={"name": "name"})
ex["label"] = "Exercise"
ex.insert(0, "id", range(1, len(ex) + 1))

ex.to_csv("output/nodes_exercise_final_FIXED.csv", index=False)
print("✔ Saved: nodes_exercise_final_FIXED.csv")

# =============================
# 2. FIX BodyPart Nodes
# =============================
bp = pd.read_csv("output/nodes_bodypart_final.csv")
bp["label"] = "BodyPart"
bp.insert(0, "id", range(10000, 10000 + len(bp)))  # kasih ID jauh biar tidak bentrok

bp.to_csv("output/nodes_bodypart_final_FIXED.csv", index=False)
print("✔ Saved: nodes_bodypart_final_FIXED.csv")

# =============================
# 3. FIX Equipment Nodes
# =============================
eq = pd.read_csv("output/nodes_equipment_final.csv")
eq["label"] = "Equipment"
eq.insert(0, "id", range(20000, 20000 + len(eq)))

eq.to_csv("output/nodes_equipment_final_FIXED.csv", index=False)
print("✔ Saved: nodes_equipment_final_FIXED.csv")
