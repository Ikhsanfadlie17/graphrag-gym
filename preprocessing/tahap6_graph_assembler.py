import os
import random
import pandas as pd
from collections import defaultdict

# =========================
# KONFIG
# =========================

BASE_NODE_FILE = "output/final/nodes_all.csv"
BASE_REL_FILE  = "output/final/relationships_all.csv"

OUT_NODE_FILE = "output/final/nodes_all_rich.csv"
OUT_REL_FILE  = "output/final/relationships_all_rich.csv"

# NOTE:
# Di Neo4j kamu label science sekarang "Theory".
# Kalau mau konsisten dengan NODE_USE kamu bisa pakai "ScienceConcept".
SCIENCE_LABEL = "Theory"   # ubah ke "ScienceConcept" kalau mau

random.seed(42)

# =========================
# UTIL
# =========================

def add_node(nodes_list, name_to_id, name, label, current_max_id):
    """
    Tambah node baru kalau belum ada (berdasarkan (name.lower(), label)).
    Return: (node_id, new_max_id)
    """
    key = (name.strip().lower(), label)
    if key in name_to_id:
        return name_to_id[key], current_max_id

    new_id = current_max_id + 1
    nodes_list.append({"id": new_id, "name": name, "label": label})
    name_to_id[key] = new_id
    return new_id, new_id


def add_rel(rel_list, start_id, end_id, rel_type, source):
    rel_list.append({
        "start_id": int(start_id),
        "end_id": int(end_id),
        "type": rel_type,
        "source": source
    })


# =========================
# DATA TEMPLATE
# =========================

VARIATION_PATTERNS = [
    "Pause", "Tempo 3-1-1", "Deficit", "Partial ROM",
    "Single-Leg", "Banded", "Slow Eccentric"
]

TECHNIQUES = [
    "Neutral Spine", "Brace the Core", "Scapular Retraction",
    "Packed Shoulder", "Full Range of Motion", "Controlled Lockout",
    "Even Foot Pressure", "Knees Out", "Tripod Foot",
    "Bar Path Over Mid-Foot", "Vertical Shin Position",
    "Elbows Under Bar", "Tuck the Elbows", "Squeeze the Glutes",
    "Drive Through Heels", "Push the Floor Away",
    "Keep Ribcage Down", "Maintain Neck Neutral",
    "Brace Before Descent", "Create Upper Back Tension",
    "Lat Engagement", "Grip the Bar Hard", "Breath Hold (Valsalva)",
    "Proper Spotter Communication", "Use Safety Pins/Racks"
]

COACHING_CUES = [
    "Chest up", "Knees out", "Pull the bar to your shins",
    "Push the floor away", "Crush the bar",
    "Screw your feet into the floor", "Spread the floor",
    "Touch-and-go with control", "Move smooth, not fast",
    "Control the way down", "Explode on the way up",
    "Reach tall at the top", "Keep the bar close",
    "Think about pushing the ground", "Imagine breaking the bar",
    "Zip the bar up your body", "Stay tight at the bottom",
    "Drive your elbows under the bar", "Show your chest to the wall",
    "Long neck at the top", "Pull shoulders down and back",
    "Keep ribs stacked over hips"
]

INJURY_RISKS = [
    ("Lower Back Strain Risk", "Back"),
    ("Lumbar Shear Stress", "Back"),
    ("Knee Valgus Stress", "Quadriceps"),
    ("Patellar Tendon Irritation", "Quadriceps"),
    ("Shoulder Impingement Risk", "Shoulders"),
    ("Rotator Cuff Overload", "Shoulders"),
    ("Elbow Tendon Overuse", "Triceps"),
    ("Wrist Hyperextension Risk", "Forearms"),
    ("Neck Hyperextension Risk", "Back"),
    ("Ankle Instability Risk", "Calves"),
    ("Hip Internal Rotation Stress", "Glutes"),
    ("Hamstring Strain Risk", "Hamstrings")
]

SCIENCE_CORE = [
    "Mechanical Tension",
    "Metabolic Stress",
    "Muscle Damage",
    "Progressive Overload",
    "Volume Load",
    "Intensity of Effort",
    "Proximity to Failure",
    "Rest Interval Duration",
    "Repetition Tempo",
    "Range of Motion",
    "Exercise Order",
    "Training Frequency",
    "Mind-Muscle Connection",
    "Stability vs Free Movement",
    "Lengthened Position Loading",
    "Eccentric Emphasis",
    "Concentric Velocity",
    "Set Endpoint (RPE/RIR)",
    "Fatigue Management",
    "Deloading Strategy"
]

# =========================
# MAIN ENRICH FUNCTION
# =========================

def main():
    # ---------- load base ----------
    if not os.path.exists(BASE_NODE_FILE) or not os.path.exists(BASE_REL_FILE):
        raise FileNotFoundError("Pastikan nodes_all.csv & relationships_all.csv ada di output/final/")

    base_nodes = pd.read_csv(BASE_NODE_FILE)
    base_rels  = pd.read_csv(BASE_REL_FILE)

    # Normalisasi kolom
    base_nodes = base_nodes[["id", "name", "label"]]
    base_rels  = base_rels[["start_id", "end_id", "type", "source"]]

    nodes_list = base_nodes.to_dict(orient="records")
    rel_list   = base_rels.to_dict(orient="records")

    max_id = int(base_nodes["id"].max())

    # Map: (name.lower(), label) -> id
    name_to_id = {
        (str(row["name"]).strip().lower(), row["label"]): int(row["id"])
        for _, row in base_nodes.iterrows()
    }

    # Index node id by label
    label_to_ids = defaultdict(list)
    for _, row in base_nodes.iterrows():
        label_to_ids[row["label"]].append(int(row["id"]))

    exercise_ids   = label_to_ids.get("Exercise", [])
    bodypart_ids   = label_to_ids.get("BodyPart", [])
    equipment_ids  = label_to_ids.get("Equipment", [])

    # ---------- index relasi lama (untuk diwariskan ke variation) ----------
    rels_by_type_and_start = defaultdict(list)
    for r in rel_list:
        key = (r["type"], int(r["start_id"]))
        rels_by_type_and_start[key].append(int(r["end_id"]))

    # ========== 1) ExerciseVariation ==========
    variation_ids = []

    for ex_id in exercise_ids:
        # ambil nama exercise
        ex_name = base_nodes.loc[base_nodes["id"] == ex_id, "name"].values[0]

        for pattern in VARIATION_PATTERNS:   # 7 variasi per exercise
            var_name = f"{ex_name} — {pattern}"
            var_id, max_id = add_node(
                nodes_list, name_to_id,
                var_name, "ExerciseVariation", max_id
            )
            variation_ids.append(var_id)

            # rel VARIATION_OF
            add_rel(rel_list, var_id, ex_id, "VARIATION_OF", "variation_from_exercise")

            # wariskan TARGETS / USES_EQUIPMENT / EXPLAINED_BY
            for t in ["TARGETS", "USES_EQUIPMENT", "EXPLAINED_BY"]:
                for end_id in rels_by_type_and_start.get((t, ex_id), []):
                    add_rel(rel_list, var_id, end_id, t, "inherit_from_parent")

    # ========== 2) Technique ==========
    technique_ids = []
    for tech in TECHNIQUES:
        tid, max_id = add_node(nodes_list, name_to_id, tech, "Technique", max_id)
        technique_ids.append(tid)

    # ========== 3) CoachingCue ==========
    cue_ids = []
    for cue in COACHING_CUES:
        cid, max_id = add_node(nodes_list, name_to_id, cue, "CoachingCue", max_id)
        cue_ids.append(cid)

    # Hubungkan Exercise & Variation → Technique & Cue
    all_ex_like = exercise_ids + variation_ids

    for ex_id in all_ex_like:
        # 2 teknik random
        chosen_techs = random.sample(technique_ids, k=min(2, len(technique_ids)))
        for tid in chosen_techs:
            add_rel(rel_list, ex_id, tid, "REQUIRES_TECHNIQUE", "exercise_requires_technique")

        # 1 cue random
        cid = random.choice(cue_ids)
        add_rel(rel_list, ex_id, cid, "REQUIRES_TECHNIQUE", "exercise_coaching_cue")

    # ========== 4) InjuryRisk ==========
    # Map nama bodypart -> id
    bodypart_name_to_id = {}
    for bid in bodypart_ids:
        name = base_nodes.loc[base_nodes["id"] == bid, "name"].values[0]
        bodypart_name_to_id[str(name).strip().lower()] = bid

    risk_ids = []
    for risk_name, bp_name in INJURY_RISKS:
        rid, max_id = add_node(nodes_list, name_to_id, risk_name, "InjuryRisk", max_id)
        risk_ids.append(rid)

        bp_id = bodypart_name_to_id.get(bp_name.strip().lower())
        if bp_id is not None:
            add_rel(rel_list, rid, bp_id, "PART_OF", "risk_bodypart_mapping")

    # Teknik yang memperbaiki risiko (IMPROVES atau INCREASES)
    for tid in technique_ids:
        if not risk_ids:
            break
        rid = random.choice(risk_ids)
        add_rel(rel_list, tid, rid, "IMPROVES", "technique_reduces_risk")

    # ========== 5) ScienceConcept (Theory) tambahan ==========
    science_core_ids = []
    for sc_name in SCIENCE_CORE:
        sid, max_id = add_node(nodes_list, name_to_id, sc_name, SCIENCE_LABEL, max_id)
        science_core_ids.append(sid)

    # Hubungkan Exercise & Variation ke beberapa konsep teori
    for ex_id in all_ex_like:
        chosen = random.sample(science_core_ids, k=min(3, len(science_core_ids)))
        for sid in chosen:
            add_rel(rel_list, ex_id, sid, "EXPLAINED_BY", "exercise_science_core")

    # (Opsional) beberapa relasi antar teori
    for sid in science_core_ids:
        other = random.choice(science_core_ids)
        if other != sid:
            add_rel(rel_list, sid, other, "SUPPORTED_BY", "science_links")

    # ========== Finalisasi: DataFrame + bersihin duplikat ==========
    final_nodes = pd.DataFrame(nodes_list).drop_duplicates(subset=["id"])
    final_rels  = pd.DataFrame(rel_list)

    # Hapus relasi duplikat persis sama (start,end,type)
    final_rels = final_rels.drop_duplicates(subset=["start_id", "end_id", "type"])

    # Simpan
    os.makedirs(os.path.dirname(OUT_NODE_FILE), exist_ok=True)
    final_nodes.to_csv(OUT_NODE_FILE, index=False, encoding="utf-8")
    final_rels.to_csv(OUT_REL_FILE,  index=False, encoding="utf-8")

    print("✅ Done enrich graph.")
    print(f"   Nodes: {len(final_nodes)}")
    print(final_nodes["label"].value_counts())
    print(f"\n   Relationships: {len(final_rels)}")
    print(final_rels["type"].value_counts())

if __name__ == "__main__":
    main()
