import os
import re
import math
import pandas as pd
import numpy as np

# ============================================================
# KONFIG PATH
# ============================================================

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "output")
SCI_DIR = os.path.join(OUT_DIR, "science")
FINAL_DIR = os.path.join(OUT_DIR, "final")

os.makedirs(FINAL_DIR, exist_ok=True)

# Sumber utama (FIXED)
EX_FILE = os.path.join(OUT_DIR, "nodes_exercise_final_FIXED.csv")
BP_FILE = os.path.join(OUT_DIR, "nodes_bodypart_final_FIXED.csv")
EQ_FILE = os.path.join(OUT_DIR, "nodes_equipment_final_FIXED.csv")
REL_EX_BP_FILE = os.path.join(OUT_DIR, "relationships_exercise_bodypart_final_FIXED2.csv")

SCI_NODES_FILE = os.path.join(SCI_DIR, "science_nodes_final_cleaned.csv")
SCI_RELS_FILE = os.path.join(SCI_DIR, "science_rels_final_cleaned.csv")

# Output FINAL
NODES_OUT = os.path.join(FINAL_DIR, "nodes_all_rich.csv")
RELS_OUT = os.path.join(FINAL_DIR, "relationships_all_rich.csv")


# ============================================================
# HELPER
# ============================================================

def clean_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def norm_rel_type(t):
    """
    Normalisasi nama relasi -> UPPERCASE + underscore.
    """
    if not isinstance(t, str):
        t = str(t)
    t = t.strip()
    if not t:
        return ""
    t = t.upper().replace(" ", "_")
    t = re.sub(r"[^A-Z0-9_]", "_", t)
    return t


# ============================================================
# MAIN BUILD
# ============================================================

def main():
    print("🚀 Tahap 6 – Graph Assembler FINAL (RICH, pakai data FIXED)")

    # -----------------------------
    # 1) LOAD NODE DASAR
    # -----------------------------
    ex_df = pd.read_csv(EX_FILE)
    bp_df = pd.read_csv(BP_FILE)
    eq_df = pd.read_csv(EQ_FILE)
    sci_nodes_df = pd.read_csv(SCI_NODES_FILE)

    # Pastikan kolom penting ada
    assert {"name", "default_equipment"}.issubset(ex_df.columns), "nodes_exercise_final_FIXED.csv harus punya name & default_equipment"
    assert {"name", "label"}.issubset(bp_df.columns), "nodes_bodypart_final_FIXED.csv harus punya name & label"
    assert {"name", "label"}.issubset(eq_df.columns), "nodes_equipment_final_FIXED.csv harus punya name & label"
    assert {"name", "label"}.issubset(sci_nodes_df.columns), "science_nodes_final_cleaned.csv harus punya name & label"

    print(f"✔ Exercise rows      : {len(ex_df)}")
    print(f"✔ BodyPart rows      : {len(bp_df)}")
    print(f"✔ Equipment rows     : {len(eq_df)}")
    print(f"✔ ScienceConcept rows: {len(sci_nodes_df)}")

    # -----------------------------
    # 2) BUILD NODE MASTER (re-ID dari 1..N)
    # -----------------------------
    nodes = []
    name_to_id = {}
    id_counter = 1

    def add_node(name, label):
        nonlocal id_counter
        name = clean_str(name)
        label = clean_str(label)

        if not name:
            return None
        key = (name, label)
        if key in name_to_id:
            return name_to_id[key]

        nid = id_counter
        id_counter += 1
        nodes.append({"id": nid, "name": name, "label": label})
        name_to_id[key] = nid
        return nid

    # Tambah Exercise
    for _, row in ex_df.iterrows():
        add_node(row["name"], "Exercise")

    # Tambah BodyPart
    for _, row in bp_df.iterrows():
        add_node(row["name"], "BodyPart")

    # Tambah Equipment
    for _, row in eq_df.iterrows():
        add_node(row["name"], "Equipment")

    # Tambah ScienceConcept
    for _, row in sci_nodes_df.iterrows():
        nm = clean_str(row["name"])
        add_node(nm, "ScienceConcept")

    print(f"\n📦 Node dasar (Exercise+BodyPart+Equipment+Science): {len(nodes)}")

    # Map cepat nama -> id per label (supaya tidak salah sambung)
    def get_id(name, label):
        return name_to_id.get((clean_str(name), label))

    # -----------------------------
    # 3) BANGUN RELASI DASAR
    # -----------------------------
    rels = []

    # 3a) Exercise TARGETS BodyPart dari relationships_exercise_bodypart_final_FIXED2
    rel_ex_bp = pd.read_csv(REL_EX_BP_FILE)
    assert {"Exercise", "BodyPart", "type"}.issubset(rel_ex_bp.columns), \
        "relationships_exercise_bodypart_final_FIXED2.csv harus punya kolom Exercise, BodyPart, type"

    for _, row in rel_ex_bp.iterrows():
        ex_name = clean_str(row["Exercise"])
        bp_name = clean_str(row["BodyPart"])
        rtype = norm_rel_type(row["type"]) or "TARGETS"

        ex_id = get_id(ex_name, "Exercise")
        bp_id = get_id(bp_name, "BodyPart")

        if ex_id is None or bp_id is None:
            # kalau ada miss, log saja
            # (tapi dari penjelasan kamu, semua sudah lengkap)
            continue

        rels.append({
            "start_id": ex_id,
            "end_id": bp_id,
            "type": rtype,
            "source": "exercise_bodypart_final"
        })

    print(f"✔ Relasi TARGETS (base)     : {sum(1 for r in rels if r['type']=='TARGETS')}")

    # 3b) Exercise USES_EQUIPMENT dari default_equipment
    for _, row in ex_df.iterrows():
        ex_name = clean_str(row["name"])
        eq_name = clean_str(row["default_equipment"])

        ex_id = get_id(ex_name, "Exercise")
        eq_id = get_id(eq_name, "Equipment")

        if ex_id is None or eq_id is None:
            continue

        rels.append({
            "start_id": ex_id,
            "end_id": eq_id,
            "type": "USES_EQUIPMENT",
            "source": "exercise_default_equipment"
        })

    print(f"✔ Relasi USES_EQUIPMENT (base): {sum(1 for r in rels if r['type']=='USES_EQUIPMENT')}")

    # -----------------------------
    # 4) SCIENCE → SCIENCE RELASI DASAR
    # -----------------------------
    sci_rels_df = pd.read_csv(SCI_RELS_FILE)
    assert {"start", "type", "end"}.issubset(sci_rels_df.columns), "science_rels_final_cleaned.csv harus punya start,type,end"

    sci_added = 0
    for _, row in sci_rels_df.iterrows():
        h_name = clean_str(row["start"])
        t_name = clean_str(row["end"])
        rtype = norm_rel_type(row["type"])
        if not rtype:
            continue

        h_id = get_id(h_name, "ScienceConcept")
        if h_id is None:
            h_id = add_node(h_name, "ScienceConcept")

        t_id = get_id(t_name, "ScienceConcept")
        if t_id is None:
            t_id = add_node(t_name, "ScienceConcept")

        rels.append({
            "start_id": h_id,
            "end_id": t_id,
            "type": rtype,
            "source": "science_pdf_relation"
        })
        sci_added += 1

    print(f"✔ Relasi science<->science   : {sci_added}")

    # -----------------------------
    # 5) GENERATE NODE & RELASI RICH (variation, technique, cue, injury)
    # -----------------------------
    print("\n🧠 Generate node & relasi RICH (ExerciseVariation, Technique, Cue, InjuryRisk)...")

    # Precompute bodypart per exercise (dari rel_ex_bp)
    bp_map = {}
    for _, row in rel_ex_bp.iterrows():
        ex_name = clean_str(row["Exercise"])
        bp_name = clean_str(row["BodyPart"])
        bp_map[ex_name] = bp_name

    # Precompute science konsep yg relevan untuk hypertrophy/strength/power/endurance
    sci_names = [clean_str(x) for x in sci_nodes_df["name"].tolist()]

    def pick_sci_by_keywords(keywords, limit=30):
        kw_lower = [k.lower() for k in keywords]
        hits = []
        for nm in sci_names:
            low = nm.lower()
            if any(k in low for k in kw_lower):
                hits.append(nm)
        # unik dan batas
        uniq = []
        for x in hits:
            if x not in uniq:
                uniq.append(x)
        return uniq[:limit]

    sci_strength = pick_sci_by_keywords(["strength", "force"])
    sci_hyper = pick_sci_by_keywords(["hypertrophy", "muscle growth", "cross-sectional area"])
    sci_power = pick_sci_by_keywords(["power", "velocity", "rate of force"])
    sci_endurance = pick_sci_by_keywords(["endurance", "fatigue"])
    sci_general = pick_sci_by_keywords(["training", "exercise", "resistance"], limit=50)

    if not sci_general:
        sci_general = sci_names[:50]

    def pick_science_for_ex(ex_name, bp_name):
        """
        Pilih 5 ScienceConcept yg akan di-link ke satu exercise.
        Logika simple berdasar bodypart.
        """
        bp = (bp_name or "").lower()
        cands = []

        # semua exercise pasti dapat general
        cands.extend(sci_general)

        # tambahkan sesuai bodypart
        if any(k in bp for k in ["quad", "hamstring", "glute", "calf", "leg"]):
            cands.extend(sci_strength)
            cands.extend(sci_hyper)
        elif any(k in bp for k in ["chest", "shoulder", "tricep", "bicep", "lat", "back", "trap", "forearm"]):
            cands.extend(sci_strength)
            cands.extend(sci_power)
        else:
            cands.extend(sci_strength)

        # unique, ambil 5 pertama
        uniq = []
        for x in cands:
            if x not in uniq:
                uniq.append(x)

        if len(uniq) <= 5:
            return uniq
        return uniq[:5]

    # generator rich per exercise
    def create_rich_for_exercise(row):
        nonlocal id_counter
        ex_name = clean_str(row["name"])
        eq_name = clean_str(row["default_equipment"])
        ex_id = get_id(ex_name, "Exercise")
        if ex_id is None:
            return

        bp_name = bp_map.get(ex_name)
        bp_id = get_id(bp_name, "BodyPart") if bp_name else None
        eq_id = get_id(eq_name, "Equipment") if eq_name else None

        # --- Variations (2 per exercise)
        variation_suffixes = [" (Variation A)", " (Variation B)"]
        var_ids = []
        for suf in variation_suffixes:
            v_name = ex_name + suf
            vid = add_node(v_name, "ExerciseVariation")
            var_ids.append(vid)

            # rel VARIATION_OF
            rels.append({
                "start_id": vid,
                "end_id": ex_id,
                "type": "VARIATION_OF",
                "source": "auto_variation"
            })

            # variation TARGETS bodypart & USES_EQUIPMENT sama seperti base
            if bp_id is not None:
                rels.append({
                    "start_id": vid,
                    "end_id": bp_id,
                    "type": "TARGETS",
                    "source": "auto_variation"
                })
            if eq_id is not None:
                rels.append({
                    "start_id": vid,
                    "end_id": eq_id,
                    "type": "USES_EQUIPMENT",
                    "source": "auto_variation"
                })

        # --- Technique (2 per exercise)
        tech_names = [
            f"{ex_name} – Neutral spine & braced core",
            f"{ex_name} – Full range of motion"
        ]
        tech_ids = []
        for tn in tech_names:
            tid = add_node(tn, "Technique")
            tech_ids.append(tid)
            # Exercise REQUIRES_TECHNIQUE Technique
            rels.append({
                "start_id": ex_id,
                "end_id": tid,
                "type": "REQUIRES_TECHNIQUE",
                "source": "auto_technique"
            })

        # --- Coaching cues (2 per exercise)
        cue_names = [
            f"Cue: keep core tight on {ex_name}",
            f"Cue: control eccentric phase on {ex_name}"
        ]
        for cn in cue_names:
            cid = add_node(cn, "CoachingCue")
            rels.append({
                "start_id": ex_id,
                "end_id": cid,
                "type": "HAS_CUE",
                "source": "auto_cue"
            })

        # --- Injury risk (1 per exercise)
        risk_bp = bp_name or "general"
        risk_name = f"Injury risk: potential overuse of {risk_bp} on {ex_name}"
        rid = add_node(risk_name, "InjuryRisk")
        rels.append({
            "start_id": ex_id,
            "end_id": rid,
            "type": "INJURY_RISK_FOR",
            "source": "auto_injury"
        })

        # --- Science linking (5 concept per exercise: 3 SUPPORTED_BY, 2 EXPLAINED_BY)
        sci_list = pick_science_for_ex(ex_name, bp_name)
        for i, s_name in enumerate(sci_list):
            sid = get_id(s_name, "ScienceConcept")
            if sid is None:
                sid = add_node(s_name, "ScienceConcept")
            if i < 3:
                rtype = "SUPPORTED_BY"
            else:
                rtype = "EXPLAINED_BY"
            rels.append({
                "start_id": ex_id,
                "end_id": sid,
                "type": rtype,
                "source": "auto_exercise_science"
            })

    for _, row in ex_df.iterrows():
        create_rich_for_exercise(row)

    print(f"📦 Total node setelah rich: {len(nodes)}")
    print(f"📦 Total relasi (sementara): {len(rels)}")

    # -----------------------------
    # 6) DEDUP RELASI
    # -----------------------------
    rel_df = pd.DataFrame(rels)
    rel_df.drop_duplicates(subset=["start_id", "end_id", "type"], inplace=True)
    print(f"🔢 Total relasi unik FINAL: {len(rel_df)}")

    print("🔎 Distribusi type relasi:")
    print(rel_df["type"].value_counts())

    # -----------------------------
    # 7) SIMPAN CSV FINAL
    # -----------------------------
    nodes_df = pd.DataFrame(nodes)
    nodes_df.sort_values("id", inplace=True)
    nodes_df.to_csv(NODES_OUT, index=False, encoding="utf-8")

    rel_df.sort_values(["start_id", "end_id", "type"], inplace=True)
    rel_df.to_csv(RELS_OUT, index=False, encoding="utf-8")

    print(f"\n💾 Nodes disimpan ke: {NODES_OUT}")
    print(f"💾 Rels  disimpan ke: {RELS_OUT}")
    print("\n🎉 Tahap 6 RICH FINAL SELESAI. Graph siap di-import ke Neo4j.")


if __name__ == "__main__":
    main()
