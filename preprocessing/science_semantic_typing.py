import os
import json
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering

# ============================================
# CONFIG
# ============================================

OUTPUT_DIR = "output/science"

NODES_IN  = f"{OUTPUT_DIR}/science_nodes_clean.csv"
RELS_IN   = f"{OUTPUT_DIR}/science_relationships_clean.csv"

NODES_OUT = f"{OUTPUT_DIR}/science_nodes_typed.csv"
RELS_OUT  = f"{OUTPUT_DIR}/science_relationships_typed.csv"


# ============================================
# HELPER: ENSURE DIR
# ============================================

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


# ============================================
# 1. KLASIFIKASI TIPE KONSEP ILMIAH
# ============================================

MECHANISM_KW = [
    "mechanical tension", "metabolic stress", "muscle damage",
    "neural drive", "neural adaptation", "motor unit recruitment",
    "eccentric", "concentric", "stretch-shortening", "stretch shortening",
    "strain", "torque", "force", "moment arm", "lever arm",
]

OUTCOME_KW = [
    "hypertrophy", "muscle growth", "strength", "power", "endurance",
    "performance", "functional capacity", "fitness", "maximal strength",
    "muscular strength", "muscle size", "lean mass", "fat loss",
]

VARIABLE_KW = [
    "intensity", "volume", "frequency", "rest interval", "rest period",
    "load", "sets", "repetitions", "repetition", "tempo",
    "time under tension", "rm ", "-rm", "1rm", "2rm", "3rm", "5rm",
]

PHYSIO_KW = [
    "protein synthesis", "protein breakdown", "satellite cell", "myonuclei",
    "myonuclear", "mTOR", "igf-1", "igf1", "hormone", "testosterone",
    "cortisol", "growth hormone", "insulin", "signaling", "signalling",
    "mitochondria", "mitochondrial", "fiber type", "type i", "type ii",
    "capillary", "capillarization", "oxidative", "glycolytic",
]

PROGRAM_KW = [
    "periodization", "periodised", "periodized",
    "linear", "undulating", "block", "conjugate",
    "training model", "training program", "training programme",
    "split routine", "full body", "upper lower", "push pull",
]

RECOVERY_KW = [
    "recovery", "overtraining", "overreaching", "delayed onset muscle soreness",
    "doms", "fatigue", "supercompensation", "sleep", "nutrition",
]

EXERCISE_HINT_KW = [
    "squat", "press", "bench press", "deadlift", "curl", "row", "pulldown",
    "pull-up", "push-up", "lunge", "raise", "extension", "flexion",
    "fly", "dip", "hip thrust", "leg press",
]


def contains_any(text: str, keywords):
    t = text.lower()
    return any(kw in t for kw in keywords)


def classify_subtype(name: str) -> str:
    """
    Beri label subtipe ilmiah untuk setiap node.
    """
    n = name.strip()
    if n == "":
        return "Unknown"

    low = n.lower()

    # 1. Latihan (jika ada kata squat, bench press, dll)
    if contains_any(low, EXERCISE_HINT_KW):
        return "ExerciseConcept"

    # 2. Mekanisme latihan (mechanical tension, metabolic stress, dll)
    if contains_any(low, MECHANISM_KW):
        return "Mechanism"

    # 3. Outcome / Adaptasi (hypertrophy, strength, power, dll)
    if contains_any(low, OUTCOME_KW):
        return "Outcome"

    # 4. Variabel beban latihan (volume, intensity, rest interval, dll)
    if contains_any(low, VARIABLE_KW):
        return "TrainingVariable"

    # 5. Fisiologi (protein synthesis, satellite cell, hormone, dll)
    if contains_any(low, PHYSIO_KW):
        return "Physiology"

    # 6. Model program latihan (periodization, block, split, dll)
    if contains_any(low, PROGRAM_KW):
        return "ProgrammingPrinciple"

    # 7. Recovery / fatigue
    if contains_any(low, RECOVERY_KW):
        return "RecoveryConcept"

    # 8. Default
    return "ScienceConceptOther"


# ============================================
# 2. EMBEDDING + CLUSTERING
# ============================================

def build_embeddings(names, model_name="all-MiniLM-L6-v2"):
    print("🧠 Memuat model embedding:", model_name)
    model = SentenceTransformer(model_name)
    embeddings = model.encode(names, show_progress_bar=True)
    return embeddings


def cluster_embeddings(embeddings, n_clusters=50):
    """
    Clustering sederhana dengan Agglomerative Clustering (cosine).
    """
    if len(embeddings) == 0:
        return np.array([])

    print(f"🧩 Melakukan clustering ke {n_clusters} cluster...")
    # AgglomerativeClustering di sklearn 1.4+ pakai metric="cosine"
    clusterer = AgglomerativeClustering(
        n_clusters=n_clusters,
        affinity="cosine",
        linkage="average"
    )
    labels = clusterer.fit_predict(embeddings)
    return labels


# ============================================
# 3. PIPELINE UTAMA
# ============================================

def main():
    print("🚀 Science Semantic Typing Running...\n")

    # -------------------------
    # Cek file input
    # -------------------------
    if not os.path.exists(NODES_IN):
        print(f"❌ File nodes tidak ditemukan: {NODES_IN}")
        return

    if not os.path.exists(RELS_IN):
        print(f"❌ File relationships tidak ditemukan: {RELS_IN}")
        return

    ensure_dir(OUTPUT_DIR)

    # -------------------------
    # Load data
    # -------------------------
    print("📥 Membaca nodes & relationships...")
    nodes_df = pd.read_csv(NODES_IN)
    rels_df = pd.read_csv(RELS_IN)

    if "name" not in nodes_df.columns:
        print("❌ Kolom 'name' tidak ditemukan di nodes.")
        return

    print(f"   Jumlah node: {len(nodes_df)}")
    print(f"   Jumlah relasi: {len(rels_df)}")

    # -------------------------
    # Step 1: Type inference
    # -------------------------
    print("\n🔎 Memberi label subtipe ilmiah untuk tiap node...")

    nodes_df["subtype"] = nodes_df["name"].astype(str).apply(classify_subtype)

    # Flag panjang (kalimat panjang) untuk kamu cek manual kalau perlu
    nodes_df["is_long_span"] = nodes_df["name"].astype(str).apply(
        lambda x: len(x) > 120
    )

    # Label utama tetap ScienceConcept (sesuai tahap sebelumnya)
    if "label" not in nodes_df.columns:
        nodes_df["label"] = "ScienceConcept"

    # -------------------------
    # Step 2: Embedding + Clustering (opsional)
    # -------------------------
    print("\n🧠 Membuat embedding & cluster (untuk analisis skripsi)...")

    names = nodes_df["name"].astype(str).tolist()

    try:
        embeddings = build_embeddings(names)
        cluster_labels = cluster_embeddings(embeddings, n_clusters=50)
        nodes_df["cluster_id"] = cluster_labels
    except Exception as e:
        print("⚠️ Gagal melakukan embedding/clustering:", e)
        print("   → Kolom 'cluster_id' akan diisi -1 (tidak terkluster).")
        nodes_df["cluster_id"] = -1

    # -------------------------
    # Step 3: Simpan hasil
    # -------------------------
    print("\n💾 Menyimpan hasil...")

    nodes_df.to_csv(NODES_OUT, index=False, encoding="utf-8")
    print(f"✅ Nodes dengan tipe & cluster disimpan ke: {NODES_OUT}")

    # Relasi tidak diubah strukturnya, hanya kita copy ke file baru
    rels_df.to_csv(RELS_OUT, index=False, encoding="utf-8")
    print(f"✅ Relationships disalin ke: {RELS_OUT}")

    print("\n🎉 Tahap 6 (Semantic Typing & Clustering) SELESAI.\n")


if __name__ == "__main__":
    main()
