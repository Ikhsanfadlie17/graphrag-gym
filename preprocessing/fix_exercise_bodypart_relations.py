# preprocessing/fix_exercise_bodypart_relations.py

import os
import pandas as pd

# ==== PATH KONFIG SESUAI STRUKTUR FOLDER KAMU ====
BASE_FINAL = "output/final"
BASE_OUT   = "output"
BASE_SCI   = "output/science"

NODES_ALL_FILE   = os.path.join(BASE_FINAL, "nodes_all_rich.csv")
RELS_ALL_FILE    = os.path.join(BASE_FINAL, "relationships_all_rich.csv")

# Relasi Exercise–BodyPart yang SUDAH BENAR (pakai nama)
REL_EX_BP_FIXED2 = os.path.join(BASE_OUT, "relationships_exercise_bodypart_final_FIXED2.csv")

# Output relasi final yang sudah diperbaiki TARGETS
RELS_ALL_FIXED   = os.path.join(BASE_FINAL, "relationships_all_rich_FIXED.csv")


def main():
    print("🔧 Fix Exercise–BodyPart TARGETS ONLY (graph rich tetap utuh)\n")

    # =========================
    # 1. Load nodes_all_rich
    # =========================
    if not os.path.exists(NODES_ALL_FILE):
        raise FileNotFoundError(f"Tidak menemukan {NODES_ALL_FILE}")

    nodes = pd.read_csv(NODES_ALL_FILE)
    print(f"✔ Nodes loaded: {len(nodes)}")
    if "id" not in nodes.columns or "name" not in nodes.columns or "label" not in nodes.columns:
        raise ValueError(f"nodes_all_rich.csv wajib punya kolom: id, name, label. Kolom sekarang: {nodes.columns.tolist()}")

    # Buat mapping nama → id khusus label Exercise & BodyPart
    ex_map = (
        nodes[nodes["label"] == "Exercise"]
        .set_index("name")["id"]
        .to_dict()
    )
    bp_map = (
        nodes[nodes["label"] == "BodyPart"]
        .set_index("name")["id"]
        .to_dict()
    )

    print(f"   • Exercise nodes : {len(ex_map)}")
    print(f"   • BodyPart nodes : {len(bp_map)}")

    # =========================
    # 2. Load relationships_all_rich
    # =========================
    if not os.path.exists(RELS_ALL_FILE):
        raise FileNotFoundError(f"Tidak menemukan {RELS_ALL_FILE}")

    rels = pd.read_csv(RELS_ALL_FILE)
    print(f"\n✔ Relationships loaded: {len(rels)}")
    print("   Type distribution (BEFORE fix):")
    if "type" not in rels.columns:
        raise ValueError(f"relationships_all_rich.csv wajib punya kolom 'type'. Kolom sekarang: {rels.columns.tolist()}")

    print(rels["type"].value_counts())

    # Deteksi nama kolom untuk start/end ID di relasi existing
    if "start_id" in rels.columns and "end_id" in rels.columns:
        start_col, end_col = "start_id", "end_id"
    elif "start" in rels.columns and "end" in rels.columns:
        start_col, end_col = "start", "end"
    else:
        raise ValueError(
            f"relationships_all_rich.csv harus punya salah satu pasangan kolom: "
            f"('start_id','end_id') atau ('start','end'). Kolom sekarang: {rels.columns.tolist()}"
        )

    # =========================
    # 3. Load relasi Exercise–BodyPart FIXED2 (berbasis nama)
    # =========================
    if not os.path.exists(REL_EX_BP_FIXED2):
        raise FileNotFoundError(f"Tidak menemukan {REL_EX_BP_FIXED2}")

    rel_ex_bp = pd.read_csv(REL_EX_BP_FIXED2)
    required_cols = ["Exercise", "BodyPart", "type"]
    if not all(c in rel_ex_bp.columns for c in required_cols):
        raise ValueError(
            f"{REL_EX_BP_FIXED2} harus punya kolom: {required_cols}, "
            f"tapi sekarang: {rel_ex_bp.columns.tolist()}"
        )

    print(f"\n✔ Loaded Exercise–BodyPart FIXED2 rows: {len(rel_ex_bp)}")

    # =========================
    # 4. Bangun ulang TARGETS dari FIXED2
    # =========================
    new_targets_rows = []
    missing_ex = set()
    missing_bp = set()

    for _, row in rel_ex_bp.iterrows():
        ex_name = str(row["Exercise"]).strip()
        bp_name = str(row["BodyPart"]).strip()
        rel_type = str(row["type"]).strip() or "TARGETS"

        if ex_name not in ex_map:
            missing_ex.add(ex_name)
            continue
        if bp_name not in bp_map:
            missing_bp.add(bp_name)
            continue

        new_targets_rows.append({
            start_col: ex_map[ex_name],
            end_col: bp_map[bp_name],
            "type": "TARGETS",
            "source": "exercise_bodypart_final_FIXED2"
        })

    new_targets = pd.DataFrame(new_targets_rows)
    print(f"\n✔ New TARGETS built: {len(new_targets)}")

    if missing_ex:
        print(f"⚠️ Exercise TIDAK ditemukan di nodes_all_rich (cek ejaannya): {len(missing_ex)} contoh: {list(missing_ex)[:5]}")
    if missing_bp:
        print(f"⚠️ BodyPart TIDAK ditemukan di nodes_all_rich (cek ejaannya): {len(missing_bp)} contoh: {list(missing_bp)[:5]}")

    if new_targets.empty:
        raise RuntimeError("❌ Tidak ada TARGETS baru yang berhasil dibangun. Cek mapping nama exercise/bodypart.")

    # =========================
    # 5. Hapus semua TARGETS lama & ganti dengan yang baru
    # =========================
    rels_no_targets = rels[rels["type"] != "TARGETS"].copy()
    before = len(rels)
    removed = before - len(rels_no_targets)
    print(f"\n🧹 Menghapus TARGETS lama: {removed} baris")

    # Sesuaikan kolom new_targets dengan kolom di rels
    for col in [start_col, end_col, "type"]:
        if col not in new_targets.columns:
            raise ValueError(f"Kolom {col} tidak ada di new_targets, ini bug di script.")

    # Jika relasi existing punya kolom 'source', pastikan new_targets juga punya
    if "source" in rels.columns and "source" not in new_targets.columns:
        new_targets["source"] = "exercise_bodypart_final_FIXED2"

    # Combine
    rels_fixed = pd.concat([rels_no_targets, new_targets], ignore_index=True)

    # Drop duplikat
    rels_fixed = rels_fixed.drop_duplicates(subset=[start_col, end_col, "type"])

    after = len(rels_fixed)
    print(f"🔢 Total relationships AFTER fix: {after}")
    print("   Type distribution (AFTER fix):")
    print(rels_fixed["type"].value_counts())

    # =========================
    # 6. Simpan ke file baru
    # =========================
    rels_fixed.to_csv(RELS_ALL_FIXED, index=False, encoding="utf-8")
    print(f"\n💾 Saved FIXED relationships to: {RELS_ALL_FIXED}")
    print("✅ HANYA relasi TARGETS yang diubah. Relasi lain tetap sama.\n")


if __name__ == "__main__":
    main()
