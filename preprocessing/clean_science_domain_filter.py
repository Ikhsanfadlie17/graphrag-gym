import pandas as pd
import re
from tqdm import tqdm

INPUT_NODES = "output/science/science_nodes_final.csv"
INPUT_RELS  = "output/science/science_rels_final.csv"

OUTPUT_NODES = "output/science/science_nodes_final_cleaned.csv"
OUTPUT_RELS  = "output/science/science_rels_final_cleaned.csv"


# ============================================================
# 1. DOMAIN WORDLIST — hanya konsep sport science yang boleh lolos
# ============================================================

SPORT_KEYWORDS = [
    "muscle", "fiber", "hypertrophy", "strength", "force", "power", "velocity",
    "fatigue", "neural", "protein", "synthesis", "adaptation", "load",
    "mechanical", "tension", "stress", "eccentric", "concentric",
    "metabolic", "recovery", "performance", "volume", "intensity",
    "resistance", "training", "exercise", "limb", "joint", "contraction",
    "torque", "activation", "mass", "endurance", "motor unit", "type i",
    "type ii", "myofibril", "sarcoplasmic", "myosin", "actin"
]

# ============================================================
# 2. BLACKLIST — buang semua NON-SPORT
# ============================================================

BLACKLIST = [
    "student", "knowledge", "recommend", "forgetting", "hyperparameter",
    "algorithm", "predict", "probability", "framework", "data", "dataset",
    "model", "learning", "feature", "graph", "embedding", "sequence",
    "item", "attention", "kc_t", "ct_i", "ml_", "p_k_", "m_lk", "lk_c",
    "i,j", "equation", "denotes", "represents"
]

# Terms that indicate noise
NOISE_PATTERNS = [
    r"[a-z]_[a-z]_",           # ex: ml_kc, p_k_, m_lk
    r"[A-Z]{2,}\d+",           # ex: KG4EER
    r"\(|\)",                  # remove parenthesis nodes
    r"\{|\}",                  # remove braces
    r"=",                      # mathematical
    r"\^",                     # superscript math
    r"\d{3,}",                 # variant numbers
]


def clean_text(x):
    if pd.isna(x):
        return ""
    x = str(x).strip()
    x = re.sub(r"\s+", " ", x)
    return x


def is_noise_node(name):
    """Buang node non-sport dengan rule ketat"""
    n = name.lower()

    # 1. Jika mengandung blacklist → buang
    if any(b in n for b in BLACKLIST):
        return True

    # 2. Jika cocok pattern simbol matematika
    for p in NOISE_PATTERNS:
        if re.search(p, n):
            return True

    # 3. Jika node berupa kalimat panjang
    if len(name) > 60:
        return True

    # 4. Node tidak ada hubungan dengan sport science
    if not any(k in n for k in SPORT_KEYWORDS):
        return True

    return False


# ============================================================
# 3. LOAD FILE
# ============================================================

print("📥 Loading data...")
nodes = pd.read_csv(INPUT_NODES)
rels = pd.read_csv(INPUT_RELS)

nodes["name"] = nodes["name"].astype(str).apply(clean_text)
rels["start"] = rels["start"].astype(str).apply(clean_text)
rels["end"]   = rels["end"].astype(str).apply(clean_text)


# ============================================================
# 4. FILTER NOISE NODES
# ============================================================

print("🧹 Filtering nodes (domain-based)...")

valid_nodes = []
for n in tqdm(nodes["name"]):
    if not is_noise_node(n):
        valid_nodes.append(n)

valid_nodes_df = pd.DataFrame({"name": sorted(set(valid_nodes))})
valid_nodes_set = set(valid_nodes_df["name"])

print(f"✔ Nodes before: {len(nodes)}")
print(f"✔ Nodes after:  {len(valid_nodes_df)}")


# ============================================================
# 5. FILTER RELATIONSHIPS BERDASARKAN NODE VALID
# ============================================================

print("\n🔗 Filtering relationships...")

rels_clean = rels[
    (rels["start"].isin(valid_nodes_set)) &
    (rels["end"].isin(valid_nodes_set))
]

print(f"✔ Relationships before: {len(rels)}")
print(f"✔ Relationships after:  {len(rels_clean)}")


# ============================================================
# 6. WRITE OUTPUT
# ============================================================

valid_nodes_df["label"] = "ScienceConcept"

valid_nodes_df.to_csv(OUTPUT_NODES, index=False, encoding="utf-8")
rels_clean.to_csv(OUTPUT_RELS, index=False, encoding="utf-8")

print("\n🎉 DONE — Science Domain Filtering Completed!")
print(f"📄 Clean nodes → {OUTPUT_NODES}")
print(f"📄 Clean rels  → {OUTPUT_RELS}")
