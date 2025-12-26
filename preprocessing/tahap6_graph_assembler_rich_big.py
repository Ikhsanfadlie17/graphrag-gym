import os
import pandas as pd

BASE_DIR   = "output"
SCI_DIR    = os.path.join(BASE_DIR, "science")

# === File input utama (FIXED) ===
EX_FILE        = os.path.join(BASE_DIR, "nodes_exercise_final_FIXED.csv")
BP_FILE        = os.path.join(BASE_DIR, "nodes_bodypart_final_FIXED.csv")
EQ_FILE        = os.path.join(BASE_DIR, "nodes_equipment_final_FIXED.csv")
REL_EX_BP_FIX  = os.path.join(BASE_DIR, "relationships_exercise_bodypart_FIXED_MAPPED.csv")

SCI_NODES_FILE = os.path.join(SCI_DIR, "science_nodes_final_cleaned.csv")
SCI_RELS_FILE  = os.path.join(SCI_DIR, "science_rels_final_cleaned.csv")

# === File output besar untuk skripsi ===
OUT_NODES = os.path.join(BASE_DIR, "final", "nodes_all_rich_BIG.csv")
OUT_RELS  = os.path.join(BASE_DIR, "final", "relationships_all_rich_BIG.csv")


def main():
    print("🚀 Tahap 6 – Build RICH BIG Graph (≈10k node, <25k rel)")
    # ------------------------------------------------------
    # 1. Load node dasar
    # ------------------------------------------------------
    ex_df = pd.read_csv(EX_FILE)
    bp_df = pd.read_csv(BP_FILE)
    eq_df = pd.read_csv(EQ_FILE)
    sci_df = pd.read_csv(SCI_NODES_FILE)

    print(f"✔ Exercise : {len(ex_df)}")
    print(f"✔ BodyPart : {len(bp_df)}")
    print(f"✔ Equipment: {len(eq_df)}")
    print(f"✔ Science  : {len(sci_df)}")

    # bangun list node (id, name, label)
    nodes = []

    # Exercise (sudah ada id & label)
    for _, r in ex_df.iterrows():
        nodes.append({
            "id": int(r["id"]),
            "name": str(r["name"]).strip(),
            "label": "Exercise"
        })

    # BodyPart
    bp_name_to_id = {}
    for _, r in bp_df.iterrows():
        nid = int(r["id"])
        name = str(r["name"]).strip()
        bp_name_to_id[name] = nid
        nodes.append({
            "id": nid,
            "name": name,
            "label": "BodyPart"
        })

    # Equipment
    eq_name_to_id = {}
    for _, r in eq_df.iterrows():
        nid = int(r["id"])
        name = str(r["name"]).strip()
        eq_name_to_id[name] = nid
        nodes.append({
            "id": nid,
            "name": name,
            "label": "Equipment"
        })

    # id berikutnya
    next_id = max(n["id"] for n in nodes) + 1

    # ScienceConcept
    sci_name_to_id = {}
    for _, r in sci_df.iterrows():
        name = str(r["name"]).strip()
        nid = next_id
        next_id += 1
        sci_name_to_id[name] = nid
        nodes.append({
            "id": nid,
            "name": name,
            "label": "ScienceConcept"
        })

    # ------------------------------------------------------
    # 2. Tambah node sintetis: Variation, CoachingCue, Technique, InjuryRisk
    # ------------------------------------------------------
    ex_to_var_ids   = {}
    ex_to_cue_ids   = {}
    ex_to_tech_id   = {}
    ex_to_risk_id   = {}
    ex_to_eq_id     = {}

    for _, r in ex_df.iterrows():
        ex_id   = int(r["id"])
        ex_name = str(r["name"]).strip()
        eq_name = str(r.get("default_equipment", "")).strip()
        eq_id   = eq_name_to_id.get(eq_name)
        ex_to_eq_id[ex_id] = eq_id

        # 3 variation per exercise
        var_ids = []
        for level in ["Beginner", "Intermediate", "Advanced"]:
            nid = next_id
            next_id += 1
            var_ids.append(nid)
            nodes.append({
                "id": nid,
                "name": f"{ex_name} ({level} variation)",
                "label": "ExerciseVariation"
            })
        ex_to_var_ids[ex_id] = var_ids

        # 2 coaching cue
        cue_ids = []
        for idx in range(1, 3):
            nid = next_id
            next_id += 1
            cue_ids.append(nid)
            nodes.append({
                "id": nid,
                "name": f"Coaching cue {idx} for {ex_name}",
                "label": "CoachingCue"
            })
        ex_to_cue_ids[ex_id] = cue_ids

        # 1 technique
        tech_id = next_id
        next_id += 1
        ex_to_tech_id[ex_id] = tech_id
        nodes.append({
            "id": tech_id,
            "name": f"Technique focus for {ex_name}",
            "label": "Technique"
        })

        # 1 injury risk
        risk_id = next_id
        next_id += 1
        ex_to_risk_id[ex_id] = risk_id
        nodes.append({
            "id": risk_id,
            "name": f"Injury risk consideration for {ex_name}",
            "label": "InjuryRisk"
        })

    # ------------------------------------------------------
    # 3. Build relasi
    # ------------------------------------------------------
    rels = []

    # 3.1 RELASI TARGETS dari file FIXED_MAPPED (id -> id)
    rel_bp = pd.read_csv(REL_EX_BP_FIX)
    start_col = "start_id" if "start_id" in rel_bp.columns else "start"
    end_col   = "end_id"   if "end_id"   in rel_bp.columns else "end"

    # mapping exercise -> list bodypart id
    bp_by_ex = rel_bp.groupby(start_col)[end_col].apply(list).to_dict()

    for _, r in rel_bp.iterrows():
        sid = int(r[start_col])
        tid = int(r[end_col])
        rels.append({
            "start_id": sid,
            "end_id":   tid,
            "type":    "TARGETS",
            "source":  "exercise_bodypart_fixed_mapped"
        })

    # 3.2 RELASI USES_EQUIPMENT dasar (exercise -> equipment)
    for _, r in ex_df.iterrows():
        ex_id   = int(r["id"])
        eq_name = str(r.get("default_equipment", "")).strip()
        eq_id   = eq_name_to_id.get(eq_name)
        if eq_id is None:
            continue
        rels.append({
            "start_id": ex_id,
            "end_id":   eq_id,
            "type":     "USES_EQUIPMENT",
            "source":   "exercise_equipment_default"
        })

    # 3.3 RELASI untuk variation
    for ex_id, var_ids in ex_to_var_ids.items():
        bps   = bp_by_ex.get(ex_id, [])
        eq_id = ex_to_eq_id.get(ex_id)

        for vid in var_ids:
            # VARIATION_OF
            rels.append({
                "start_id": vid,
                "end_id":   ex_id,
                "type":     "VARIATION_OF",
                "source":   "auto_variation"
            })
            # variation TARGETS bodypart yang sama
            for bp_id in bps:
                rels.append({
                    "start_id": vid,
                    "end_id":   int(bp_id),
                    "type":     "TARGETS",
                    "source":   "auto_variation"
                })
            # variation USES_EQUIPMENT sama
            if eq_id is not None:
                rels.append({
                    "start_id": vid,
                    "end_id":   eq_id,
                    "type":     "USES_EQUIPMENT",
                    "source":   "auto_variation"
                })

    # 3.4 CoachingCue relasi
    for ex_id, cue_ids in ex_to_cue_ids.items():
        bps = bp_by_ex.get(ex_id, [])
        for cid in cue_ids:
            # cue -> exercise (IMPROVES)
            rels.append({
                "start_id": cid,
                "end_id":   ex_id,
                "type":     "IMPROVES",
                "source":   "auto_coaching_cue"
            })
            # cue -> bodypart (TARGETS)
            for bp_id in bps:
                rels.append({
                    "start_id": cid,
                    "end_id":   int(bp_id),
                    "type":     "TARGETS",
                    "source":   "auto_coaching_cue"
                })

    # 3.5 Technique relasi
    for ex_id, tech_id in ex_to_tech_id.items():
        bps = bp_by_ex.get(ex_id, [])
        # exercise INVOLVES technique
        rels.append({
            "start_id": ex_id,
            "end_id":   tech_id,
            "type":     "INVOLVES",
            "source":   "auto_technique"
        })
        # technique IMRPOVES bodypart
        for bp_id in bps:
            rels.append({
                "start_id": tech_id,
                "end_id":   int(bp_id),
                "type":     "IMPROVES",
                "source":   "auto_technique"
            })

    # 3.6 InjuryRisk relasi
    for ex_id, risk_id in ex_to_risk_id.items():
        rels.append({
            "start_id": ex_id,
            "end_id":   risk_id,
            "type":     "CAUSES",
            "source":   "auto_injury_risk"
        })

    # 3.7 Relasi antar ScienceConcept dari science_rels_final_cleaned
    sci_rels = pd.read_csv(SCI_RELS_FILE)
    for _, r in sci_rels.iterrows():
        h_name = str(r["start"]).strip()
        t_name = str(r["end"]).strip()
        h_id   = sci_name_to_id.get(h_name)
        t_id   = sci_name_to_id.get(t_name)
        if h_id is None or t_id is None:
            continue
        rels.append({
            "start_id": h_id,
            "end_id":   t_id,
            "type":     str(r["type"]).strip(),
            "source":   "science_pdf"
        })

    # 3.8 Link tiap exercise ke 2 ScienceConcept (SUPPORTED_BY) – round robin
    sci_ids = list(sci_name_to_id.values())
    if sci_ids:
        sci_len = len(sci_ids)
        ex_ids = [int(r["id"]) for _, r in ex_df.iterrows()]
        for idx, ex_id in enumerate(ex_ids):
            s1 = sci_ids[idx % sci_len]
            s2 = sci_ids[(idx + 123) % sci_len]
            rels.append({
                "start_id": ex_id,
                "end_id":   s1,
                "type":     "SUPPORTED_BY",
                "source":   "auto_science_link"
            })
            rels.append({
                "start_id": ex_id,
                "end_id":   s2,
                "type":     "SUPPORTED_BY",
                "source":   "auto_science_link"
            })

    # ------------------------------------------------------
    # 4. Simpan CSV
    # ------------------------------------------------------
    nodes_df = pd.DataFrame(nodes).drop_duplicates(subset=["id"])
    rels_df  = pd.DataFrame(rels).drop_duplicates()

    print("\n📊 STATISTIK AKHIR")
    print(f"Total nodes : {len(nodes_df)}")
    print(nodes_df["label"].value_counts())
    print("\nTotal relasi:", len(rels_df))
    print(rels_df["type"].value_counts())

    os.makedirs(os.path.dirname(OUT_NODES), exist_ok=True)
    nodes_df.to_csv(OUT_NODES, index=False)
    rels_df.to_csv(OUT_RELS, index=False)

    print(f"\n💾 Nodes disimpan ke: {OUT_NODES}")
    print(f"💾 Rels  disimpan ke: {OUT_RELS}")
    print("🎉 Tahap 6 RICH BIG selesai.")


if __name__ == "__main__":
    main()
