import os
import json
import pandas as pd
from tqdm import tqdm
from PyPDF2 import PdfReader
from openai import OpenAI

# ============================================
# CONFIG
# ============================================

PDF_DIR = "pdfs"
OUTPUT_DIR = "output/science"

RAW_CHUNKS = f"{OUTPUT_DIR}/science_chunks_raw.jsonl"
FILTERED_CHUNKS = f"{OUTPUT_DIR}/science_chunks_filtered.jsonl"
TRIPLETS_FILE = f"{OUTPUT_DIR}/science_triplets_raw.jsonl"

NODES_CSV = f"{OUTPUT_DIR}/nodes_science_final.csv"
RELS_CSV = f"{OUTPUT_DIR}/relationships_science_final.csv"

client = OpenAI()


# ============================================
# HELPERS — ALWAYS UTF-8 on WINDOWS
# ============================================

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def read_jsonl_utf8(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def write_jsonl_utf8(path, list_of_dicts):
    with open(path, "w", encoding="utf-8") as f:
        for obj in list_of_dicts:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ============================================
# STAGE 1 — PDF → TEXT CHUNKS
# ============================================

def pdf_to_text_chunks(pdf_path, chunk_size=4000):
    """Membaca PDF dan membaginya menjadi chunk kecil 4000 karakter."""
    reader = PdfReader(pdf_path)
    full_text = ""

    for page in reader.pages:
        try:
            full_text += page.extract_text() + "\n"
        except Exception:
            pass

    chunks = []
    for i in range(0, len(full_text), chunk_size):
        piece = full_text[i:i + chunk_size].strip()
        if len(piece) > 50:
            chunks.append(piece)

    return chunks


def stage1_extract_chunks():
    print("📘 Stage 1 — Extract text chunks from PDF")

    ensure_dir(OUTPUT_DIR)

    all_chunks = []
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]

    total = 0

    for pdf_name in pdf_files:
        pdf_path = f"{PDF_DIR}/{pdf_name}"

        print(f"\n📖 Membaca PDF: {pdf_name}")
        chunks = pdf_to_text_chunks(pdf_path)

        print(f"   Panjang teks: {sum(len(c) for c in chunks)} karakter")
        print(f"   → Dibagi menjadi {len(chunks)} chunks")

        for c in chunks:
            all_chunks.append({
                "pdf": pdf_name,
                "text": c
            })

        total += len(chunks)

    write_jsonl_utf8(RAW_CHUNKS, all_chunks)
    print(f"\n✅ Stage 1 selesai — total chunks: {total}")
    print(f"📄 Disimpan ke: {RAW_CHUNKS}")


# ============================================
# STAGE 2 — FILTER SCIENCE CHUNKS
# ============================================

SCIENCE_KEYWORDS = [
    "hypertrophy", "muscle", "strength", "adapt", "volume",
    "intensity", "mechanical", "tension", "load", "fatigue",
    "activation", "physiology", "protein", "fiber", "growth",
]


def stage2_filter():
    print("\n🔬 Stage 2 — Filtering science chunks")

    if not os.path.exists(RAW_CHUNKS):
        print("❌ RAW_CHUNKS belum ada. Jalankan Stage 1 dulu.")
        return

    results = []

    for line in read_jsonl_utf8(RAW_CHUNKS):
        obj = json.loads(line)
        txt = obj["text"].lower()

        if any(k in txt for k in SCIENCE_KEYWORDS):
            results.append(obj)

    write_jsonl_utf8(FILTERED_CHUNKS, results)

    print(f"✅ Stage 2 selesai — hasil: {len(results)} chunks")
    print(f"📄 Disimpan ke: {FILTERED_CHUNKS}")


# ============================================
# STAGE 3 — LLM TRIPLET EXTRACTION
# ============================================

def extract_triplets(text, pdf_name):
    """Memanggil model untuk mengekstrak triplet."""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert exercise science assistant. "
                        "Extract **scientific knowledge** as structured triplets.\n"
                        "Format JSON ONLY:\n"
                        "{\"triplets\": [{\"head\":..., \"relation\":..., \"tail\":...}]}"
                    ),
                },
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )

        data = json.loads(resp.choices[0].message.content)
        triplets = data.get("triplets", [])
        for t in triplets:
            t["source"] = pdf_name

        return triplets

    except Exception as e:
        print("⚠️ LLM Error:", e)
        return []


def stage3_extract_triplets(max_chunks=200):
    print("\n🧠 Stage 3 — Extracting triplets with LLM")

    if not os.path.exists(FILTERED_CHUNKS):
        print("❌ FILTERED_CHUNKS belum ada. Jalankan Stage 2 dulu.")
        return

    filtered = list(read_jsonl_utf8(FILTERED_CHUNKS))
    filtered = [json.loads(x) for x in filtered]

    # batasi
    filtered = filtered[:max_chunks]

    all_triplets = []

    for item in tqdm(filtered):
        pdf_name = item["pdf"]
        text = item["text"]
        trips = extract_triplets(text, pdf_name)
        all_triplets.extend(trips)

    write_jsonl_utf8(TRIPLETS_FILE, all_triplets)
    print(f"\n✅ Stage 3 selesai — total triplets: {len(all_triplets)}")
    print(f"📄 Disimpan ke: {TRIPLETS_FILE}")


# ============================================
# STAGE 4 — FINALIZE TRIPLETS → CSV
# ============================================

def normalize_field(x):
    """
    Normalisasi isi head / tail:
    - Jika list → gabungkan menjadi string
    - Jika dict → flatten sebagai string
    - Jika None → ""
    - Jika string → trim
    """

    if x is None:
        return ""

    # Jika list (contoh: ["mechanical", "tension"])
    if isinstance(x, list):
        try:
            return "; ".join([str(i).strip() for i in x])
        except Exception:
            return ""

    # Jika dict
    if isinstance(x, dict):
        try:
            return "; ".join([f"{k}:{v}" for k, v in x.items()])
        except Exception:
            return ""

    # Jika string / number
    try:
        return str(x).strip()
    except Exception:
        return ""


def stage4_finalize():
    print("\n📦 Stage 4 — Finalizing science triplet graph")

    # Pastikan file triplets ada
    if not os.path.exists(TRIPLETS_FILE):
        print("❌ ERROR: Triplets file tidak ditemukan!")
        print(f"   Cek: {TRIPLETS_FILE}")
        return

    rows = []
    print("🔍 Membaca triplets...")

    # Baca file dengan UTF-8
    with open(TRIPLETS_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                t = json.loads(line.strip())

                head = normalize_field(t.get("head"))
                rel = normalize_field(t.get("relation"))
                tail = normalize_field(t.get("tail"))
                src = normalize_field(t.get("source"))

                # Lewati triplet dengan field kosong
                if head == "" or tail == "" or rel == "":
                    continue

                rows.append(
                    {
                        "head": head,
                        "relation": rel,
                        "tail": tail,
                        "source": src,
                    }
                )

            except Exception as e:
                print("⚠️ Error membaca baris triplets:", e)
                continue

    print(f"📌 Triplets valid ditemukan: {len(rows)}")

    if not rows:
        print("❌ Tidak ada triplet valid setelah dibersihkan.")
        return

    # Convert ke DataFrame
    df = pd.DataFrame(rows)

    # Hilangkan duplikat triplets
    df = df.drop_duplicates()
    print(f"📉 Setelah drop duplicate: {len(df)} triplets")

    # ============================
    #  NODES
    # ============================

    print("🧬 Membuat node list...")

    node_list = pd.concat([df["head"], df["tail"]]).unique()
    node_df = pd.DataFrame({"name": node_list})

    # Semua konsep → ScienceConcept
    node_df["label"] = "ScienceConcept"

    ensure_dir(OUTPUT_DIR)
    node_df.to_csv(
        "output/science/science_nodes_clean.csv", index=False, encoding="utf-8"
    )
    print("✅ Nodes disimpan ke: output/science/science_nodes_clean.csv")

    # ============================
    #  RELATIONSHIPS
    # ============================

    print("🔗 Membuat relationship list...")

    rel_df = df.copy()
    rel_df.rename(
        columns={"head": "start", "relation": "type", "tail": "end"}, inplace=True
    )

    rel_df.to_csv(
        "output/science/science_relationships_clean.csv",
        index=False,
        encoding="utf-8",
    )
    print(
        "✅ Relationships disimpan ke: output/science/science_relationships_clean.csv"
    )

    print("\n🎉 Stage 4 COMPLETE — Science Graph berhasil difinalisasi!\n")


# ============================================
# MAIN PIPELINE (DENGAN SKIP OTOMATIS)
# ============================================

def main():
    print("🚀 Science Extract Pipeline Running...\n")

    # ---------- Stage 1 ----------
    if os.path.exists(RAW_CHUNKS) and os.path.getsize(RAW_CHUNKS) > 0:
        print("⚠️ Stage 1 skipped (RAW_CHUNKS sudah ada)")
    else:
        stage1_extract_chunks()

    # ---------- Stage 2 ----------
    if os.path.exists(FILTERED_CHUNKS) and os.path.getsize(FILTERED_CHUNKS) > 0:
        print("⚠️ Stage 2 skipped (FILTERED_CHUNKS sudah ada)")
    else:
        stage2_filter()

    # ---------- Stage 3 ----------
    if os.path.exists(TRIPLETS_FILE) and os.path.getsize(TRIPLETS_FILE) > 0:
        print("⚠️ Stage 3 skipped (TRIPLETS_FILE sudah ada)")
    else:
        stage3_extract_triplets(max_chunks=200)

    # ---------- Stage 4 SELALU JALAN ----------
    stage4_finalize()

    print("\n🎉 PIPELINE SELESAI.\n")


if __name__ == "__main__":
    main()
