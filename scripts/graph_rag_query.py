import os
import json
import re
from difflib import get_close_matches
from neo4j import GraphDatabase
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")


# ============================================================
# SIMPLE NEO4J DRIVER
# ============================================================
class SimpleGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def run(self, cypher: str):
        with self.driver.session(database="neo4j") as session:
            return list(session.run(cypher))


graph = SimpleGraph(URI, USER, PASSWORD)


# ============================================================
# LLM CONFIG (GPT-5.1)
# ============================================================
llm = ChatOpenAI(model="gpt-5.1", temperature=0)


# ============================================================
# HELPER: EXTRACT REQUESTED VARIATION COUNT
# ============================================================
def extract_requested_count(question: str, default: int = 5) -> int:
    """
    Ambil angka pertama dari pertanyaan user.
    Contoh: "back 3 variasi saja" -> 3.
    Jika tidak ada angka -> default.
    """
    m = re.search(r"\d+", question)
    if m:
        n = int(m.group(0))
        return max(1, min(n, 10))  # clamp 1..10
    return default


# ============================================================
# 1) BODY PART DETECTION — UNTUK EXERCISE MODE
# ============================================================
BODY_PART_SYNONYMS = {
    "Chest": ["dada", "chest", "upper chest", "pecs", "pectoralis"],
    "Shoulders": ["bahu", "shoulder", "deltoid", "delts"],
    "Triceps": ["tricep", "tris", "lengan belakang"],
    "Biceps": ["bicep", "bisep", "lengan depan"],
    "Back": ["punggung", "upper back", "mid back", "back"],
    "Lats": ["lat", "lats", "sayap", "latissimus"],
    "Quadriceps": ["quadriceps", "quads", "quad", "paha depan", "kaki depan", "otot quadriceps", "rectus femoris"],
    "Hamstrings": ["hamstring", "hamstrings", "ham", "paha belakang"],
    "Glutes": ["glute", "glutes", "bokong", "pantat"],
    "Calves": ["betis", "calf", "calves"],
    "Core": ["core", "inti", "pinggang"],
    "Abs": ["abs", "perut", "sixpack"]
}


def detect_body_part(question: str):
    q = question.lower()

    # (1) cek sinonim manual
    for bp, synonyms in BODY_PART_SYNONYMS.items():
        if any(s in q for s in synonyms):
            return bp

    # (2) fallback: fuzzy match ke BodyPart di Neo4j
    rows = graph.run("MATCH (b:BodyPart) RETURN b.name AS name")
    available_bps = [row["name"] for row in rows]

    matches = get_close_matches(
        q, [bp.lower() for bp in available_bps],
        n=1, cutoff=0.45
    )

    if matches:
        for bp in available_bps:
            if bp.lower() == matches[0]:
                return bp

    return None


# ============================================================
# 2) ANATOMY MODE (MUSCLE DICTIONARY) — DENGAN RELASI LENGKAP
# ============================================================
ANATOMY_TERMS = {
    "Quadriceps": ["quadriceps", "quads", "quad", "paha depan"],
    "Hamstrings": ["hamstring", "hamstrings", "paha belakang"],
    "Gluteus maximus": ["glutes", "bokong", "pantat"],
    "Pectoralis major": ["chest", "dada", "pecs", "pectoralis"],
    "Latissimus dorsi": ["lats", "lat", "sayap"],
    "Deltoid": ["bahu", "shoulder", "deltoid", "delts"],
    "Biceps brachii": ["biceps", "bisep"],
    "Triceps brachii": ["triceps", "tris"],
    "Gastrocnemius & Soleus": ["betis", "calf", "calves"],
    "Rectus abdominis": ["abs", "sixpack", "perut"],
}


def detect_anatomy_term(question: str):
    q = question.lower()
    for canon, syns in ANATOMY_TERMS.items():
        if any(s in q for s in syns):
            return canon
    return None


def is_anatomy_question(question: str) -> bool:
    q = question.lower()
    anatomy_keywords = ["otot apa", "apa itu", "fungsi", "letaknya", "dimana letaknya", "bagian tubuh apa"]
    if any(k in q for k in anatomy_keywords):
        if detect_anatomy_term(q):
            return True
    return False


def build_anatomy_cypher(canon_term: str):
    """
    Query anatomy: BodyPart + semua relasi penting.
    Mengembalikan node + relationship agar visual graph menampilkan panah.
    """
    safe = canon_term.replace("'", "''")
    return f"""
MATCH (bp:BodyPart)
WHERE toLower(bp.name) CONTAINS toLower('{safe}')
WITH bp LIMIT 1
OPTIONAL MATCH (e:Exercise)-[tgt:TARGETS]->(bp)
OPTIONAL MATCH (e)-[inv:INVOLVES]->(t:Technique)
OPTIONAL MATCH (e)-[c:CAUSES]->(ir:InjuryRisk)
OPTIONAL MATCH (e)-[ue:USES_EQUIPMENT]->(eq:Equipment)
OPTIONAL MATCH (e)-[sup:SUPPORTED_BY]->(sc:ScienceConcept)
OPTIONAL MATCH (bp)-[r]->(related)
RETURN bp, e, t, ir, eq, sc, related,
       tgt, inv, c, ue, sup, r
"""


def format_anatomy_answer(rows, question: str, canon_term: str):
    """
    Format jawaban anatomy dari node-node yang dikembalikan.
    Relationship (tgt, inv, dll) dipakai untuk visual graph saja,
    text answer hanya pakai nama-nama node.
    """
    if not rows:
        return "⚠️ Data anatomy tidak ditemukan di graph."

    data = {
        "bodypart": None,
        "exercises": set(),
        "techniques": set(),
        "injury_risks": set(),
        "equipment": set(),
        "science_concepts": set(),
        "related_nodes": set()
    }

    for row in rows:
        d = dict(row)
        bp = d.get("bp")
        if bp and not data["bodypart"]:
            data["bodypart"] = {
                "name": bp.get("name"),
                "properties": dict(bp)
            }

        e = d.get("e")
        t = d.get("t")
        ir = d.get("ir")
        eq = d.get("eq")
        sc = d.get("sc")
        related = d.get("related")

        if e:
            data["exercises"].add(e.get("name"))
        if t:
            data["techniques"].add(t.get("name"))
        if ir:
            data["injury_risks"].add(ir.get("name"))
        if eq:
            data["equipment"].add(eq.get("name"))
        if sc:
            data["science_concepts"].add(sc.get("name"))
        if related:
            data["related_nodes"].add(related.get("name", "N/A"))

    formatted = {
        "bodypart": data["bodypart"],
        "exercises": sorted(data["exercises"]),
        "techniques": sorted(data["techniques"]),
        "injury_risks": sorted(data["injury_risks"]),
        "equipment": sorted(data["equipment"]),
        "science_concepts": sorted(data["science_concepts"]),
        "related_nodes": sorted(data["related_nodes"]),
    }

    prompt = f"""
Pertanyaan user: "{question}"
Otot yang dimaksud: "{canon_term}"

Data dari Neo4j Graph:
{json.dumps(formatted, ensure_ascii=False, indent=2)}

Tugas:
Berikan jawaban 3–5 paragraf berbahasa Indonesia yang:
1. Menjelaskan definisi dan lokasi anatomi otot {canon_term}.
2. Menjelaskan fungsi utama otot ini dalam gerakan sehari-hari dan latihan.
3. Menjelaskan contoh latihan yang banyak menargetkan otot ini (dari 'exercises').
4. Menyebutkan teknik penting (dari 'techniques') dan risiko cedera (dari 'injury_risks') secara singkat.
5. Mengaitkan dengan konsep ilmiah (dari 'science_concepts') jika ada.

Aturan:
- Semua istilah teknis HARUS berasal dari JSON di atas.
- Tulis natural, seperti penjelasan bab pembahasan skripsi.
- Jika ada field kosong, cukup abaikan, jangan disebutkan.
"""
    return llm.invoke(prompt).content.strip()


def answer_anatomy(question: str, canon_term: str) -> str:
    cy = build_anatomy_cypher(canon_term)
    rows = graph.run(cy)
    if not rows:
        # fallback pengetahuan umum
        prompt = f"""
User bertanya tentang anatomi otot:

Pertanyaan: "{question}"
Otot yang dimaksud: "{canon_term}"

Tugas:
Berikan jawaban singkat 2–3 paragraf berbahasa Indonesia yang:
- Menjelaskan definisi dan lokasi anatomi otot {canon_term}
- Menjelaskan fungsi utama otot tersebut
- Menyebutkan beberapa contoh gerakan umum yang melibatkan otot ini
"""
        return llm.invoke(prompt).content.strip()
    return format_anatomy_answer(rows, question, canon_term)


# ============================================================
# 3) SCIENCE QUESTION DETECTION (GRAPH-BASED) — DENGAN RELASI
# ============================================================
def is_science_question(q: str):
    q = q.lower()
    science_words = ["apa itu", "jelaskan", "pengertian", "definisi", "maksud", "mekanisme", "prinsip"]
    return any(w in q for w in science_words)


def extract_concept_term(q: str):
    q = q.lower()
    keys = ["apa itu", "jelaskan", "pengertian", "definisi", "maksud", "mekanisme", "prinsip"]
    for k in keys:
        if k in q:
            return q.split(k, 1)[1].strip(" ?:!.")
    return q.strip(" ?:!.")


def get_science_terms():
    rows = graph.run("MATCH (sc:ScienceConcept) RETURN sc.name AS name")
    return [row["name"] for row in rows]


def autocorrect_concept(term: str):
    terms = get_science_terms()
    matches = get_close_matches(term.lower(), [t.lower() for t in terms], n=1, cutoff=0.55)
    return matches[0] if matches else term


def build_science_cypher(q: str):
    """
    Science concept + semua relasi penting.
    Mengembalikan node + relationship agar visual graph menampilkan panah.
    """
    term = extract_concept_term(q)
    corrected = autocorrect_concept(term)
    safe = corrected.replace("'", "''")

    return f"""
MATCH (sc:ScienceConcept)
WHERE toLower(sc.name) CONTAINS toLower('{safe}')
WITH sc LIMIT 3
OPTIONAL MATCH (sc)-[r1]->(related:ScienceConcept)
OPTIONAL MATCH (e:Exercise)-[sup:SUPPORTED_BY]->(sc)
OPTIONAL MATCH (e)-[tgt:TARGETS]->(bp:BodyPart)
OPTIONAL MATCH (e)-[inv:INVOLVES]->(t:Technique)
OPTIONAL MATCH (e)-[c:CAUSES]->(ir:InjuryRisk)
OPTIONAL MATCH (e)-[ue:USES_EQUIPMENT]->(eq:Equipment)
RETURN sc, related, r1,
       e, sup,
       bp, tgt,
       t, inv,
       ir, c,
       eq, ue
"""


def format_science_answer(rows, question: str):
    """
    Format jawaban science dari node-node graph.
    Relationship dipakai untuk visual; text hanya pakai nama-nama.
    """
    if not rows:
        return "⚠️ Konsep ilmiah tidak ditemukan di graph."

    concepts = {}

    for row in rows:
        d = dict(row)
        sc = d.get("sc")
        if not sc:
            continue
        name = sc.get("name")
        if name not in concepts:
            concepts[name] = {
                "definition": sc.get("definition"),
                "related_concepts": set(),
                "exercises": set(),
                "bodyparts": set(),
                "techniques": set(),
                "injury_risks": set(),
                "equipment": set(),
            }

        info = concepts[name]

        related = d.get("related")
        if related:
            info["related_concepts"].add(related.get("name"))

        e = d.get("e")
        bp = d.get("bp")
        t = d.get("t")
        ir = d.get("ir")
        eq = d.get("eq")

        if e:
            info["exercises"].add(e.get("name"))
        if bp:
            info["bodyparts"].add(bp.get("name"))
        if t:
            info["techniques"].add(t.get("name"))
        if ir:
            info["injury_risks"].add(ir.get("name"))
        if eq:
            info["equipment"].add(eq.get("name"))

    formatted = []
    for name, v in concepts.items():
        formatted.append({
            "name": name,
            "definition": v["definition"],
            "related_concepts": sorted(v["related_concepts"]),
            "exercises": sorted(v["exercises"]),
            "bodyparts": sorted(v["bodyparts"]),
            "techniques": sorted(v["techniques"]),
            "injury_risks": sorted(v["injury_risks"]),
            "equipment": sorted(v["equipment"]),
        })

    prompt = f"""
Pertanyaan user: "{question}"

Data konsep ilmiah dari Neo4j Graph:
{json.dumps(formatted, ensure_ascii=False, indent=2)}

Tugas:
Berikan penjelasan ilmiah 3–5 paragraf berbahasa Indonesia yang:
1. Menjelaskan definisi dan makna konsep utama.
2. Menguraikan mekanisme / teori utama yang relevan.
3. Mengaitkan dengan latihan-latihan yang ada (dari 'exercises') dan otot / bodypart yang terlibat.
4. Menyebutkan teknik latihan, potensi risiko cedera, dan peran equipment jika ada.
5. Menjelaskan hubungan dengan konsep-konsep ilmiah lain (dari 'related_concepts').

Aturan:
- Semua istilah teknis HARUS berasal dari JSON di atas.
- Tulis natural, seperti penjelasan review literatur skripsi.
- Jika ada field kosong, cukup abaikan.
"""
    return llm.invoke(prompt).content.strip()


# ============================================================
# 4) CYPHER EXERCISE MODE (PUSH / PULL / LEGS / BODYPART)
# ============================================================
def build_bodypart_exercise_cypher(bp: str, limit: int = 5):
    """
    Query exercise berdasarkan bodypart dengan semua relasi lengkap.
    Mengembalikan node + relationship untuk visual panah.
    """
    safe_bp = bp.replace("'", "''")
    return f"""
MATCH (e:Exercise)-[tgt:TARGETS]->(targetBP:BodyPart {{name:'{safe_bp}'}})
WITH DISTINCT e, targetBP, tgt LIMIT {limit}
OPTIONAL MATCH (e)-[r1:TARGETS]->(b:BodyPart)
OPTIONAL MATCH (e)-[r2:INVOLVES]->(t:Technique)
OPTIONAL MATCH (e)-[r3:CAUSES]->(ir:InjuryRisk)
OPTIONAL MATCH (e)-[r4:USES_EQUIPMENT]->(eq:Equipment)
OPTIONAL MATCH (e)-[r5:SUPPORTED_BY]->(sc:ScienceConcept)
RETURN e, targetBP, tgt,
       b, r1,
       t, r2,
       ir, r3,
       eq, r4,
       sc, r5
"""


def build_push_pull_legs_cypher(bodypart_list, limit: int = 5):
    """
    Query untuk push/pull/legs dengan relasi lengkap.
    bodypart_list: misal ['Chest','Shoulders','Triceps']
    """
    bp_filter = "', '".join(bodypart_list)
    return f"""
MATCH (e:Exercise)-[tgt:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['{bp_filter}']
WITH DISTINCT e, bp, tgt LIMIT {limit}
OPTIONAL MATCH (e)-[r1:TARGETS]->(b:BodyPart)
OPTIONAL MATCH (e)-[r2:INVOLVES]->(t:Technique)
OPTIONAL MATCH (e)-[r3:CAUSES]->(ir:InjuryRisk)
OPTIONAL MATCH (e)-[r4:USES_EQUIPMENT]->(eq:Equipment)
OPTIONAL MATCH (e)-[r5:SUPPORTED_BY]->(sc:ScienceConcept)
RETURN e, bp, tgt,
       b, r1,
       t, r2,
       ir, r3,
       eq, r4,
       sc, r5
"""


# ============================================================
# 5) FORMAT EXERCISE ANSWER (PARAGRAF NATURAL)
# ============================================================
def format_exercise_answer(rows):
    """
    Mengambil rows berisi e, b, t, ir, eq, sc (+ relasi),
    lalu membangun JSON ringkas untuk LLM.
    Relationship dipakai untuk visual graph, tapi tidak wajib di teks.
    """
    if not rows:
        return "⚠️ Tidak ada data latihan yang ditemukan."

    exs = {}

    for row in rows:
        d = dict(row)
        e = d["e"]
        eid = e["id"]

        if eid not in exs:
            exs[eid] = {
                "name": e["name"],
                "bodyparts": set(),
                "techniques": set(),
                "injury_risks": set(),
                "equipment": set(),
                "science": set(),
            }

        # target utama
        bp = d.get("bp") or d.get("targetBP")
        if bp:
            exs[eid]["bodyparts"].add(bp.get("name"))

        b = d.get("b")
        t = d.get("t")
        ir = d.get("ir")
        eq = d.get("eq")
        sc = d.get("sc")

        if b:
            exs[eid]["bodyparts"].add(b.get("name"))
        if t:
            exs[eid]["techniques"].add(t.get("name"))
        if ir:
            exs[eid]["injury_risks"].add(ir.get("name"))
        if eq:
            exs[eid]["equipment"].add(eq.get("name"))
        if sc:
            exs[eid]["science"].add(sc.get("name"))

    formatted = [{
        "name": v["name"],
        "bodyparts": sorted(v["bodyparts"]),
        "techniques": sorted(v["techniques"]),
        "injury_risks": sorted(v["injury_risks"]),
        "equipment": sorted(v["equipment"]),
        "science_concepts": sorted(v["science"])
    } for v in exs.values()]

    prompt = f"""
Berikut daftar latihan dari Neo4j dalam bentuk JSON:

{json.dumps(formatted, ensure_ascii=False, indent=2)}

Tugas:
Untuk SETIAP latihan, tuliskan 1–3 paragraf berbahasa Indonesia yang:
- Menjelaskan otot utama yang bekerja berdasarkan 'bodyparts'.
- Menjelaskan poin teknik penting berdasarkan 'techniques' (jika ada).
- Menjelaskan risiko cedera dan pencegahan berdasarkan 'injury_risks' (jika ada).
- Menjelaskan landasan ilmiah singkat berdasarkan 'science_concepts' (jika ada).
- Menyebutkan equipment yang digunakan (jika ada).

Aturan:
- Semua istilah teknis HARUS berasal dari JSON di atas.
- Boleh membuat kalimat penghubung natural.
- Tulis seperti penjelasan di bab pembahasan skripsi: ilmiah, rapi, mudah dibaca.
"""
    return llm.invoke(prompt).content.strip()


# ============================================================
# 6) GENERIC KNOWLEDGE FALLBACK
# ============================================================
def answer_generic(question: str) -> str:
    prompt = f"""
User bertanya:

\"{question}\"

Jawab sebagai pakar strength training, biomekanik, dan ilmu latihan.
Berikan jawaban ringkas 2–4 kalimat, ilmiah tapi mudah dipahami.
Jika pertanyaan tidak terkait data graph, jawab berdasarkan pengetahuan umum yang mapan di bidang latihan fisik.
Jangan menyebut Neo4j, graph, atau dataset.
"""
    return llm.invoke(prompt).content.strip()


# ============================================================
# 7) MAIN ROUTER — EXERCISE / SCIENCE / ANATOMY / GENERIC
# ============================================================
def answer(question: str):
    q = question.lower()

    # jumlah variasi latihan yang diminta (kalau ada angka di pertanyaan)
    limit = extract_requested_count(question, default=5)

    # ---------------- EXERCISE MODE ----------------
    exercise_keywords = ["latihan", "exercise", "gerakan", "workout", "variasi", "rekomendasi", "program"]
    is_exercise = any(k in q for k in exercise_keywords)

    if is_exercise:
        # PUSH / PULL / LEGS TEMPLATE (pakai relasi lengkap)
        if any(x in q for x in ["push day", "latihan push", "push workout"]):
            cy = build_push_pull_legs_cypher(['Chest', 'Shoulders', 'Triceps'], limit=limit)
            rows = graph.run(cy)
            if not rows:
                return "⚠️ Tidak ada latihan push yang ditemukan di graph."
            return format_exercise_answer(rows)

        if any(x in q for x in ["pull day", "latihan pull", "pull workout"]):
            cy = build_push_pull_legs_cypher(['Back', 'Lats', 'Biceps'], limit=limit)
            rows = graph.run(cy)
            if not rows:
                return "⚠️ Tidak ada latihan pull yang ditemukan di graph."
            return format_exercise_answer(rows)

        if any(x in q for x in ["leg day", "latihan kaki", "legs"]):
            cy = build_push_pull_legs_cypher(['Quadriceps', 'Hamstrings', 'Glutes', 'Calves'], limit=limit)
            rows = graph.run(cy)
            if not rows:
                return "⚠️ Tidak ada latihan kaki yang ditemukan di graph."
            return format_exercise_answer(rows)

        # EXERCISE BY BODY PART
        bp = detect_body_part(q)
        if bp:
            cy = build_bodypart_exercise_cypher(bp, limit=limit)
            rows = graph.run(cy)
            if not rows:
                return f"⚠️ Tidak ada latihan yang menargetkan bodypart '{bp}'."
            return format_exercise_answer(rows)

        # Jika kata "latihan" tapi bodypart tidak jelas → jawab generik
        return answer_generic(question)

    # ---------------- ANATOMY MODE ----------------
    if is_anatomy_question(question):
        canon = detect_anatomy_term(question)
        if canon:
            return answer_anatomy(question, canon)

    # ---------------- SCIENCE MODE ----------------
    if is_science_question(q):
        cy = build_science_cypher(q)
        rows = graph.run(cy)
        if not rows:
            return answer_generic(question)
        return format_science_answer(rows, question)

    # ---------------- GENERIC KNOWLEDGE ----------------
    return answer_generic(question)


# ============================================================
# CLI
# ============================================================
def main():
    print(">> ", end="")
    q = input()
    print("\n" + answer(q) + "\n")


if __name__ == "__main__":
    main()
