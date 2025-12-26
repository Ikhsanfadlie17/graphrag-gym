import os
import math
import random
import pandas as pd
from collections import defaultdict

# ============================================================
# KONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SCIENCE_DIR = os.path.join(OUTPUT_DIR, "science")
FINAL_DIR = os.path.join(OUTPUT_DIR, "final")

# Input core (sudah kamu punya)
EXERCISE_NODES_CSV = os.path.join(OUTPUT_DIR, "nodes_exercise_final.csv")
BODYPART_NODES_CSV = os.path.join(OUTPUT_DIR, "nodes_bodypart_final.csv")
EQUIP_NODES_CSV = os.path.join(OUTPUT_DIR, "nodes_equipment_final.csv")

EX_BP_REL_CSV = os.path.join(OUTPUT_DIR, "relationships_exercise_bodypart_final.csv")
EX_EQ_REL_CSV = os.path.join(OUTPUT_DIR, "relationships_exercise_equipment_final.csv")

SCIENCE_NODES_CSV = os.path.join(SCIENCE_DIR, "science_nodes_final_cleaned.csv")
SCIENCE_RELS_CSV = os.path.join(SCIENCE_DIR, "science_rels_final_cleaned.csv")

# Output rich graph
NODES_OUT = os.path.join(FINAL_DIR, "nodes_all_rich.csv")
RELS_OUT = os.path.join(FINAL_DIR, "relationships_all_rich.csv")


# ============================================================
# HELPER
# ============================================================

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def norm_name(s: str) -> str:
    """Normalisasi nama untuk penyamaan (strip + lower)."""
    if not isinstance(s, str):
        return ""
    return " ".join(s.strip().split()).lower()


def pick_col(df: pd.DataFrame, candidates):
    """Ambil kolom pertama yang ada dari daftar candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"Tidak menemukan kolom dari kandidat: {candidates} di df.columns={df.columns.tolist()}")


# ============================================================
# LOAD NODES DASAR
# ============================================================

def load_nodes_generic(path, default_label):
    """
    Normalisasi nodes:
    - cari kolom 'name' atau ['Exercise', 'BodyPart', 'Equipment']
    - pastikan ada kolom 'name' & 'label'
    """
    if not os.path.exists(path):
        print(f"⚠️ Node file tidak ditemukan: {path}")
        return pd.DataFrame(columns=["name", "label"])

    df = pd.read_csv(path)

    # Cari kolom nama
    if "name" in df.columns:
        name_col = "name"
    else:
        name_col = pick_col(df, ["Exercise", "BodyPart", "Equipment"])

    out = df[[name_col]].copy()
    out.rename(columns={name_col: "name"}, inplace=True)

    if "label" in df.columns:
        out["label"] = df["label"].fillna(default_label)
    else:
        out["label"] = default_label

    out["name"] = out["name"].astype(str).str.strip()
    out = out.dropna(subset=["name"]).drop_duplicates(subset=["name"])

    return out[["name", "label"]]


def load_base_nodes():
    print("📥 Load base nodes...")

    ex_df = load_nodes_generic(EXERCISE_NODES_CSV, "Exercise")
    bp_df = load_nodes_generic(BODYPART_NODES_CSV, "BodyPart")
    eq_df = load_nodes_generic(EQUIP_NODES_CSV, "Equipment")

    if os.path.exists(SCIENCE_NODES_CSV):
        sc_df = pd.read_csv(SCIENCE_NODES_CSV)
        # normalisasi science nodes
        name_col = pick_col(sc_df, ["name"])
        sc = sc_df[[name_col]].copy()
        sc.rename(columns={name_col: "name"}, inplace=True)
        sc["label"] = "ScienceConcept"
        sc["name"] = sc["name"].astype(str).str.strip()
        sc = sc.dropna(subset=["name"]).drop_duplicates(subset=["name"])
    else:
        print(f"⚠️ Science node file tidak ditemukan: {SCIENCE_NODES_CSV}")
        sc = pd.DataFrame(columns=["name", "label"])

    print(f"  Exercise      : {len(ex_df)}")
    print(f"  BodyPart      : {len(bp_df)}")
    print(f"  Equipment     : {len(eq_df)}")
    print(f"  ScienceConcept: {len(sc)}")

    return ex_df, bp_df, eq_df, sc


# ============================================================
# LOAD RELASI DASAR
# ============================================================

def load_exercise_bodypart_rels():
    if not os.path.exists(EX_BP_REL_CSV):
        print(f"⚠️ File relasi Exercise-BodyPart tidak ditemukan: {EX_BP_REL_CSV}")
        return pd.DataFrame(columns=["exercise", "bodypart"])

    df = pd.read_csv(EX_BP_REL_CSV)

    # Coba deteksi mode:
    if {"Exercise", "BodyPart"}.issubset(df.columns):
        ex_col = "Exercise"
        bp_col = "BodyPart"
    elif {"start", "end"}.issubset(df.columns):
        ex_col = "start"
        bp_col = "end"
    else:
        # fallback: ambil 2 kolom pertama
        cols = df.columns.tolist()
        ex_col, bp_col = cols[0], cols[1]

    out = df[[ex_col, bp_col]].copy()
    out.columns = ["exercise", "bodypart"]
    out["exercise"] = out["exercise"].astype(str).str.strip()
    out["bodypart"] = out["bodypart"].astype(str).str.strip()
    out = out.dropna().drop_duplicates()

    print(f"🔗 Exercise-BodyPart relations: {len(out)}")
    return out


def load_exercise_equipment_rels():
    if not os.path.exists(EX_EQ_REL_CSV):
        print(f"⚠️ File relasi Exercise-Equipment tidak ditemukan: {EX_EQ_REL_CSV}")
        return pd.DataFrame(columns=["exercise", "equipment"])

    df = pd.read_csv(EX_EQ_REL_CSV)

    if {"Exercise", "Equipment"}.issubset(df.columns):
        ex_col = "Exercise"
        eq_col = "Equipment"
    elif {"start", "end"}.issubset(df.columns):
        ex_col = "start"
        eq_col = "end"
    else:
        cols = df.columns.tolist()
        ex_col, eq_col = cols[0], cols[1]

    out = df[[ex_col, eq_col]].copy()
    out.columns = ["exercise", "equipment"]
    out["exercise"] = out["exercise"].astype(str).str.strip()
    out["equipment"] = out["equipment"].astype(str).str.strip()
    out = out.dropna().drop_duplicates()

    print(f"🔗 Exercise-Equipment relations: {len(out)}")
    return out


def load_science_rels():
    if not os.path.exists(SCIENCE_RELS_CSV):
        print(f"⚠️ Science rels file tidak ditemukan: {SCIENCE_RELS_CSV}")
        return pd.DataFrame(columns=["start", "type", "end"])

    df = pd.read_csv(SCIENCE_RELS_CSV)

    # dukung dua format: (head, relation, tail) atau (start, type, end)
    if {"head", "relation", "tail"}.issubset(df.columns):
        df = df[["head", "relation", "tail"]].copy()
        df.columns = ["start", "type", "end"]
    else:
        # asumsikan sudah dalam format start, type, end
        df = df[["start", "type", "end"]].copy()

    df["start"] = df["start"].astype(str).str.strip()
    df["end"] = df["end"].astype(str).str.strip()
    df["type"] = df["type"].astype(str).str.strip().str.upper()

    # pakai sebagian type yang ilmiah (bisa dikurangi kalau mau)
    keep_types = {
        "SUPPORTED_BY", "CAUSES", "LEADS_TO", "INCREASES", "DECREASES",
        "AFFECTS", "IMPROVES", "CORRELATES_WITH", "INVOLVES"
    }
    df = df[df["type"].isin(keep_types)]

    df = df.dropna().drop_duplicates()
    print(f"🔗 Science-Science relations: {len(df)}")

    return df


# ============================================================
# GENERATE VARIATIONS, TECHNIQUE, COACHING CUE, INJURY RISK
# ============================================================

def generate_exercise_variations(ex_df: pd.DataFrame, bp_rel: pd.DataFrame, eq_rel: pd.DataFrame):
    """
    Untuk setiap Exercise, buat ~3-4 variasi.
    """
    variations = []
    var_rel = []  # (variation_name, base_exercise_name)
    random.seed(42)

    # equipment map: exercise → set(equipment)
    eq_map = defaultdict(set)
    for _, row in eq_rel.iterrows():
        eq_map[norm_name(row["exercise"])].add(row["equipment"])

    templates = [
        "{base} (Tempo Controlled)",
        "{base} (Paused)",
        "{base} (Partial ROM)",
        "{base} (Unilateral)"
    ]

    for _, row in ex_df.iterrows():
        ex_name = row["name"]
        key = norm_name(ex_name)

        # jumlah variasi per exercise (3 atau 4)
        n_var = 4

        for i in range(n_var):
            tmpl = templates[i % len(templates)]
            var_name = tmpl.format(base=ex_name)

            variations.append({
                "name": var_name,
                "label": "ExerciseVariation"
            })
            var_rel.append((var_name, ex_name))

    var_df = pd.DataFrame(variations).drop_duplicates(subset=["name"])

    print(f"🆕 Generated ExerciseVariation nodes: {len(var_df)}")
    return var_df, var_rel


def generate_techniques(ex_df: pd.DataFrame):
    """
    2 teknik per exercise, nama dibuat gabungan exercise + kata teknik.
    """
    base_tech_terms = [
        "Bracing Technique",
        "Hip Hinge Pattern",
        "Scapular Retraction",
        "Bar Path Control",
        "Depth Control",
        "Tempo Control",
        "Breathing Pattern",
        "Foot Placement",
        "Grip Position",
        "Core Engagement"
    ]
    techniques = []
    rel_requires = []  # (exercise, technique_name)
    rel_improves = []  # (exercise, technique_name) -- opsional

    random.seed(123)

    for _, row in ex_df.iterrows():
        ex_name = row["name"]
        chosen = random.sample(base_tech_terms, 2)

        for term in chosen:
            tech_name = f"{ex_name} — {term}"
            techniques.append({"name": tech_name, "label": "Technique"})
            rel_requires.append((ex_name, tech_name))

        # satu teknik yang dianggap paling penting sebagai IMPROVES
        tech_name = f"{ex_name} — {chosen[0]}"
        rel_improves.append((ex_name, tech_name))

    tech_df = pd.DataFrame(techniques).drop_duplicates(subset=["name"])
    print(f"🆕 Generated Technique nodes: {len(tech_df)}")

    return tech_df, rel_requires, rel_improves


def generate_coaching_cues(ex_df: pd.DataFrame):
    """
    2 coaching cue per exercise.
    """
    cue_templates = [
        "Keep chest up and core tight",
        "Drive through the heels",
        "Maintain neutral spine",
        "Squeeze shoulder blades together",
        "Control the eccentric phase",
        "Avoid locking out the joints",
        "Keep elbows under the bar",
        "Do not arch excessively",
        "Breathe out on exertion",
        "Focus on smooth bar path"
    ]

    cues = []
    rel_explained = []  # nanti bisa dihubungkan ke Exercise sebagai EXPLAINED_BY? (atau SIMPLY as CoachingCue)

    random.seed(777)

    for _, row in ex_df.iterrows():
        ex_name = row["name"]
        chosen = random.sample(cue_templates, 2)
        for c in chosen:
            cue_name = f"{ex_name} — Cue: {c}"
            cues.append({"name": cue_name, "label": "CoachingCue"})
            # Bisa dihubungkan sebagai EXPLAINED_BY di tahap RAG, tapi di graph cukup node saja

    cues_df = pd.DataFrame(cues).drop_duplicates(subset=["name"])
    print(f"🆕 Generated CoachingCue nodes: {len(cues_df)}")

    return cues_df


def generate_injury_risk(bp_df: pd.DataFrame):
    """
    Buat beberapa node InjuryRisk generic per bodypart.
    """
    base_risks = {
        "knee": ["Knee Stress", "Patellar Tendon Irritation"],
        "lower back": ["Lumbar Spine Stress", "Disc Compression"],
        "shoulder": ["Shoulder Impingement", "Rotator Cuff Overload"],
        "elbow": ["Elbow Tendonitis"],
        "wrist": ["Wrist Strain"],
        "hip": ["Hip Joint Stress"],
    }

    risk_nodes = []
    for _, row in bp_df.iterrows():
        bp_name = row["name"]
        bp_low = norm_name(bp_name)
        risks_for_bp = []

        if "quad" in bp_low or "leg" in bp_low or "hamstring" in bp_low or "glute" in bp_low:
            risks_for_bp.extend(base_risks["knee"])
            risks_for_bp.extend(base_risks["hip"])
        if "back" in bp_low:
            risks_for_bp.extend(base_risks["lower back"])
        if "shoulder" in bp_low or "trap" in bp_low:
            risks_for_bp.extend(base_risks["shoulder"])
        if "bicep" in bp_low or "tricep" in bp_low or "forearm" in bp_low:
            risks_for_bp.extend(base_risks["elbow"])
        if "forearm" in bp_low:
            risks_for_bp.extend(base_risks["wrist"])

        for r in set(risks_for_bp):
            risk_nodes.append({"name": r, "label": "InjuryRisk"})

    risk_df = pd.DataFrame(risk_nodes).drop_duplicates(subset=["name"])
    print(f"🆕 Generated InjuryRisk nodes: {len(risk_df)}")

    return risk_df


# ============================================================
# LINKING: EXPLAINED_BY (Exercise → ScienceConcept)
# ============================================================

def simple_token_overlap(a: str, b: str) -> float:
    """Skor overlap token sederhana untuk ranking relevance."""
    sa = set(norm_name(a).split())
    sb = set(norm_name(b).split())
    if not sa or not sb:
        return 0.0
    inter = sa.intersection(sb)
    union = sa.union(sb)
    return len(inter) / len(union)


def link_exercise_to_science(ex_df: pd.DataFrame, sc_df: pd.DataFrame, max_per_ex=4):
    """
    Untuk tiap exercise, pilih max_per_ex ScienceConcept paling relevan
    berdasarkan token overlap sederhana.
    """
    rels = []
    sc_names = sc_df["name"].tolist()

    # beberapa kata boost khusus
    boost_keywords = {
        "squat": ["strength", "hypertrophy", "power", "lower body"],
        "deadlift": ["strength", "hip", "back", "posterior"],
        "bench": ["chest", "hypertrophy", "upper body"],
        "curl": ["biceps", "elbow flexors"],
        "press": ["shoulder", "pressing"],
    }

    for _, row in ex_df.iterrows():
        ex_name = row["name"]
        ex_tokens = norm_name(ex_name)

        scores = []
        for sc_name in sc_names:
            base_score = simple_token_overlap(ex_name, sc_name)

            # tambahan sedikit boost jika ada kata kunci
            bonus = 0.0
            for kw, kws in boost_keywords.items():
                if kw in ex_tokens:
                    for k2 in kws:
                        if k2 in norm_name(sc_name):
                            bonus += 0.1
            total = base_score + bonus
            if total > 0:
                scores.append((sc_name, total))

        # urutkan dan ambil top-N
        scores.sort(key=lambda x: x[1], reverse=True)
        top = scores[:max_per_ex]

        for sc_name, s in top:
            rels.append((ex_name, "EXPLAINED_BY", sc_name))

    print(f"🔗 Generated EXPLAINED_BY relations: {len(rels)}")
    return rels


# ============================================================
# BUILD RICH GRAPH
# ============================================================

def main():
    ensure_dir(FINAL_DIR)

    # 1) Load nodes dasar
    ex_df, bp_df, eq_df, sc_df = load_base_nodes()

    # 2) Load relasi dasar
    ex_bp_rel = load_exercise_bodypart_rels()
    ex_eq_rel = load_exercise_equipment_rels()
    sc_rel = load_science_rels()

    # 3) Generate nodes turunan
    var_df, var_rel = generate_exercise_variations(ex_df, ex_bp_rel, ex_eq_rel)
    tech_df, rel_requires, rel_improves = generate_techniques(ex_df)
    cues_df = generate_coaching_cues(ex_df)
    risk_df = generate_injury_risk(bp_df)

    # 4) Link exercise → science
    ex_sc_rels = link_exercise_to_science(ex_df, sc_df, max_per_ex=4)

    # ========================================================
    # GABUNG NODE
    # ========================================================

    node_frames = [
        ex_df[["name", "label"]],
        bp_df[["name", "label"]],
        eq_df[["name", "label"]],
        sc_df[["name", "label"]],
        var_df[["name", "label"]],
        tech_df[["name", "label"]],
        cues_df[["name", "label"]],
        risk_df[["name", "label"]],
    ]

    all_nodes = pd.concat(node_frames, ignore_index=True)
    all_nodes = all_nodes.dropna(subset=["name"]).drop_duplicates(subset=["name", "label"]).reset_index(drop=True)

    # Assign ID
    all_nodes.insert(0, "id", range(1, len(all_nodes) + 1))

    # Map name+label → id
    name_label_to_id = {(row["name"], row["label"]): int(row["id"]) for _, row in all_nodes.iterrows()}
    name_to_ids = defaultdict(list)
    for _, row in all_nodes.iterrows():
        name_to_ids[row["name"]].append(int(row["id"]))

    print(f"\n📊 TOTAL NODE: {len(all_nodes)}")
    print(all_nodes["label"].value_counts())

    # ========================================================
    # BANGUN RELASI
    # ========================================================

    rel_rows = []

    # helper
    def add_rel(start_name, start_label, rel_type, end_name, end_label, source):
        sid = name_label_to_id.get((start_name, start_label))
        eid = name_label_to_id.get((end_name, end_label))
        if sid is None or eid is None:
            return
        rel_rows.append({
            "start_id": sid,
            "end_id": eid,
            "type": rel_type,
            "source": source
        })

    # a) TARGETS (Exercise → BodyPart)
    for _, row in ex_bp_rel.iterrows():
        ex_name = row["exercise"]
        bp_name = row["bodypart"]
        add_rel(ex_name, "Exercise", "TARGETS", bp_name, "BodyPart", "relationships_exercise_bodypart_final.csv")

    # b) USES_EQUIPMENT (Exercise → Equipment)
    for _, row in ex_eq_rel.iterrows():
        ex_name = row["exercise"]
        eq_name = row["equipment"]
        add_rel(ex_name, "Exercise", "USES_EQUIPMENT", eq_name, "Equipment", "relationships_exercise_equipment_final.csv")

    # c) VARIATION_OF (ExerciseVariation → Exercise)
    for var_name, ex_name in var_rel:
        add_rel(var_name, "ExerciseVariation", "VARIATION_OF", ex_name, "Exercise", "auto_variation")

    # d) REQUIRES_TECHNIQUE (Exercise → Technique)
    for ex_name, tech_name in rel_requires:
        add_rel(ex_name, "Exercise", "REQUIRES_TECHNIQUE", tech_name, "Technique", "auto_technique")

    # e) IMPROVES (Exercise → Technique) [opsional, misal interpretasi 'improves movement quality']
    for ex_name, tech_name in rel_improves:
        add_rel(ex_name, "Exercise", "IMPROVES", tech_name, "Technique", "auto_technique")

    # f) EXPLAINED_BY (Exercise → ScienceConcept)
    for ex_name, rel_type, sc_name in ex_sc_rels:
        add_rel(ex_name, "Exercise", rel_type, sc_name, "ScienceConcept", "auto_explained_by")

    # g) Science-Science: pakai langsung science_rels_final_cleaned
    for _, row in sc_rel.iterrows():
        start_name = row["start"]
        end_name = row["end"]
        rtype = row["type"]
        add_rel(start_name, "ScienceConcept", rtype, end_name, "ScienceConcept", "science_rels_final_cleaned.csv")

    # h) InjuryRisk: hubungkan Exercise -> InjuryRisk berdasarkan BodyPart
    # map bodypart norm_name -> risk list
    bp_risks = defaultdict(set)
    for _, r in risk_df.iterrows():
        risk_name = r["name"]
        low = norm_name(risk_name)
        if "knee" in low:
            bp_risks["quadriceps"].add(risk_name)
            bp_risks["hamstrings"].add(risk_name)
            bp_risks["glutes"].add(risk_name)
        if "lumbar" in low or "disc" in low or "spine" in low:
            bp_risks["back"].add(risk_name)
        if "shoulder" in low or "rotator" in low:
            bp_risks["shoulders"].add(risk_name)
        if "elbow" in low:
            bp_risks["biceps"].add(risk_name)
            bp_risks["triceps"].add(risk_name)
        if "wrist" in low:
            bp_risks["forearms"].add(risk_name)
        if "hip" in low:
            bp_risks["quadriceps"].add(risk_name)
            bp_risks["glutes"].add(risk_name)

    # map exercise -> set(bodypart)
    ex2bp = defaultdict(set)
    for _, row in ex_bp_rel.iterrows():
        ex2bp[row["exercise"]].add(row["bodypart"])

    for ex_name, bps in ex2bp.items():
        risks_for_ex = set()
        for bp in bps:
            bp_key = norm_name(bp)
            for k, v in bp_risks.items():
                if k in bp_key:
                    risks_for_ex.update(v)
        # ambil max 2 risk untuk tiap exercise
        for rname in list(risks_for_ex)[:2]:
            add_rel(ex_name, "Exercise", "INJURY_RISK", rname, "InjuryRisk", "auto_injury_risk")

    # ========================================================
    # FINAL CLEANUP RELASI
    # ========================================================

    rel_df = pd.DataFrame(rel_rows)
    rel_df = rel_df.drop_duplicates(subset=["start_id", "end_id", "type"])

    print(f"\n📊 TOTAL RELATIONSHIPS: {len(rel_df)}")
    print(rel_df["type"].value_counts())

    # ========================================================
    # SIMPAN
    # ========================================================

    all_nodes.to_csv(NODES_OUT, index=False, encoding="utf-8")
    rel_df.to_csv(RELS_OUT, index=False, encoding="utf-8")

    print(f"\n💾 Nodes saved to: {NODES_OUT}")
    print(f"💾 Relationships saved to: {RELS_OUT}")
    print("\n🎉 Rich Graph build COMPLETE.\n")


if __name__ == "__main__":
    main()
