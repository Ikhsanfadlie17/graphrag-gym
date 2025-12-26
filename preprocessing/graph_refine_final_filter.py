import os
import re
import pandas as pd
from tqdm import tqdm
from rapidfuzz import fuzz

# ============================================
# CONFIG INPUT / OUTPUT
# ============================================

RAW_NODES = "output/science/science_nodes_clean.csv"
RAW_RELS  = "output/science/science_relationships_clean.csv"

FINAL_NODES = "output/science/science_nodes_final.csv"
FINAL_RELS  = "output/science/science_rels_final.csv"


# ============================================
# STEP 1 — HELPER CLEAN FUNCTIONS
# ============================================

def clean_text(x):
    if pd.isna(x):
        return ""
    x = str(x).strip()

    # Remove excessive spaces
    x = re.sub(r"\s+", " ", x)

    # Remove weird unicode
    x = x.replace("\xad", "").replace("\u200b", "").replace("\n", " ")

    return x.strip()


def is_junk_node(x):
    """Membuang node aneh / noise / tidak relevan"""

    x_low = x.lower()

    # Buang kalimat panjang (> 70 karakter)
    if len(x) > 70:
        return True

    # Buang nomor variant
    if re.search(r"variant\s+\d+", x_low):
        return True

    # Buang node yang mengandung angka panjang
    if re.search(r"\d{3,}", x_low):
        return True

    # Buang istilah non-sport (ML, dataset, AI)
    BLOCK = [
        "model", "dataset", "algorithm", "framework",
        "kg4eer", "collaborative filtering", "deep learning",
        "recommender", "students", "education", "math",
        "feature extraction"
    ]

    if any(b in x_low for b in BLOCK):
        return True

    # Buang kata yang terlalu umum (bukan konsep ilmiah)
    if x_low in ["introduction", "conclusion", "table", "summary"]:
        return True

    # Jika hanya 1–2 kata yang tidak relevan
    if len(x.split()) == 1 and len(x) <= 4:
        return True

    return False


def normalize_relation(r):
    """Hanya biarkan relasi ilmiah yang valid"""
    r = r.lower().strip()

    mapping = {
        "causes": "CAUSES",
        "cause": "CAUSES",
        "induces": "CAUSES",
        "leads to": "LEADS_TO",
        "results in": "LEADS_TO",
        "improves": "IMPROVES",
        "increases": "INCREASES",
        "enhances": "INCREASES",
        "correlates with": "CORRELATES_WITH",
        "associated with": "CORRELATES_WITH",
        "affects": "AFFECTS",
        "regulates": "REGULATES",
        "involves": "INVOLVES",
        "drives": "CAUSES",
        "stimulates": "INCREASES",
        "reduces": "DECREASES"
    }

    # Cari mapping
    for k, v in mapping.items():
        if k in r:
            return v

    # Jika tidak relevan → drop
    return None


# ============================================
# STEP 2 — LOAD DATA
# ============================================

print("📥 Loading nodes & relationships...")

nodes = pd.read_csv(RAW_NODES)
rels  = pd.read_csv(RAW_RELS)

nodes["name"] = nodes["name"].astype(str)
rels["start"] = rels["start"].astype(str)
rels["end"]   = rels["end"].astype(str)
rels["type"]  = rels["type"].astype(str)


# ============================================
# STEP 3 — CLEAN NODES
# ============================================

print("🧹 Cleaning nodes...")

cleaned_nodes = []

for n in nodes["name"]:
    n2 = clean_text(n)
    if n2 == "":
        continue
    if is_junk_node(n2):
        continue
    cleaned_nodes.append(n2)

cleaned_nodes = pd.DataFrame({"name": cleaned_nodes}).drop_duplicates()


# ============================================
# STEP 4 — FUZZY MERGE (REMOVE SEMANTIC DUPLICATES)
# ============================================

print("🔍 Fuzzy merging similar concepts...")

merged_map = {}
node_list = cleaned_nodes["name"].tolist()

for i, a in enumerate(node_list):
    if a in merged_map:
        continue

    merged_map[a] = a  # root

    for j in range(i+1, len(node_list)):
        b = node_list[j]

        if b in merged_map:
            continue

        score = fuzz.ratio(a.lower(), b.lower())

        if score >= 90:
            merged_map[b] = a

# Apply merge
cleaned_nodes["canonical"] = cleaned_nodes["name"].map(lambda x: merged_map[x])


# ============================================
# STEP 5 — CLEAN RELATIONSHIPS
# ============================================

print("🔗 Cleaning relationships...")

rels["start"] = rels["start"].map(clean_text)
rels["end"]   = rels["end"].map(clean_text)

# Drop junk nodes
rels = rels[
    (~rels["start"].apply(is_junk_node)) &
    (~rels["end"].apply(is_junk_node))
]

# Normalize relations
rels["type_norm"] = rels["type"].apply(normalize_relation)

rels = rels[rels["type_norm"].notna()]

# Apply canonical form
rels["start"] = rels["start"].map(lambda x: merged_map.get(x, x))
rels["end"]   = rels["end"].map(lambda x: merged_map.get(x, x))


# ============================================
# STEP 6 — REMOVE SELF LOOPS & DUPLICATES
# ============================================

rels = rels[rels["start"] != rels["end"]]
rels = rels.drop_duplicates(subset=["start", "type_norm", "end"])

# Keep only necessary columns
rels_final = rels[["start", "type_norm", "end"]].rename(columns={
    "start": "start",
    "type_norm": "type",
    "end": "end"
})


# ============================================
# STEP 7 — SAVE OUTPUT
# ============================================

cleaned_nodes = cleaned_nodes[["canonical"]].drop_duplicates()
cleaned_nodes.rename(columns={"canonical": "name"}, inplace=True)
cleaned_nodes["label"] = "ScienceConcept"

cleaned_nodes.to_csv(FINAL_NODES, index=False, encoding="utf-8")
rels_final.to_csv(FINAL_RELS, index=False, encoding="utf-8")

print("\n🎉 SUCCESS — Science Graph CLEAN & FINALIZED!")
print(f"📄 Nodes saved to: {FINAL_NODES}")
print(f"📄 Rels  saved to: {FINAL_RELS}")
