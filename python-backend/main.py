import os
import json
import re
from neo4j import GraphDatabase
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import Tuple, List, Dict

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

# ============================================================
# NEO4J DRIVER
# ============================================================
class SimpleGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def run(self, cypher: str):
        with self.driver.session(database="neo4j") as session:
            return list(session.run(cypher))

graph = SimpleGraph(URI, USER, PASSWORD)

# ============================================================
# LLM CONFIG
# ============================================================
llm = ChatOpenAI(
    model="gpt-5.1",
    temperature=0,
    max_retries=2,
    request_timeout=60
)

# ============================================================
# HELPER
# ============================================================
def extract_requested_count(question: str, default: int = 3) -> int:
    m = re.search(r"\d+", question)
    if m:
        n = int(m.group(0))
        return max(1, min(n, 10))
    return default

# ============================================================
# ✅ NEW: EQUIPMENT DETECTION
# ============================================================
EQUIPMENT_SYNONYMS = {
    "Barbell": ["barbell", "barbel", "bar bell"],
    "Dumbbell": ["dumbbell", "dumbell", "dumbel"],
    "Machine": ["machine", "mesin", "smith machine"],
    "Cable": ["cable", "kabel"],
    "Resistance Bands": ["resistance band", "band", "elastic band"],
    "Kettlebell": ["kettlebell", "kettle bell"],
    "Bodyweight": ["bodyweight", "body weight", "tanpa alat"],
}

def detect_equipment(question: str):
    """
    Detect equipment mentioned in question
    """
    q = question.lower()
    detected = []
    
    # Sort by length to match longer terms first
    sorted_equipment = sorted(EQUIPMENT_SYNONYMS.items(), 
                             key=lambda x: max(len(s) for s in x[1]), 
                             reverse=True)
    
    for eq, synonyms in sorted_equipment:
        for synonym in synonyms:
            pattern = r'\b' + re.escape(synonym) + r'\b'
            if re.search(pattern, q):
                if eq not in detected:
                    detected.append(eq)
                    print(f"  ✅ Equipment: '{synonym}' → {eq}")
                break
    
    return detected

# ============================================================
# BODY PART DETECTION (UNCHANGED)
# ============================================================
BODY_PART_SYNONYMS = {
    "Chest": ["chest", "dada", "pecs", "pectoralis"],
    "Shoulders": ["shoulders", "shoulder", "bahu", "deltoid", "delts"],
    "Triceps": ["triceps", "tricep", "tris"],
    "Biceps": ["biceps", "bicep", "bisep"],
    "Back": ["back", "punggung"],
    "Lats": ["lats", "latissimus"],
    "Quadriceps": ["quadriceps", "quads", "quad"],
    "Hamstrings": ["hamstrings", "hamstring"],
    "Glutes": ["glutes", "glute", "bokong"],
    "Calves": ["calves", "calf", "betis"],
    "Core": ["core", "inti"],
    "Abs": ["abs", "abdominal", "perut"]
}

def detect_body_parts(question: str):
    q = question.lower()
    detected = []
    
    sorted_bodyparts = sorted(BODY_PART_SYNONYMS.items(), 
                             key=lambda x: max(len(s) for s in x[1]), 
                             reverse=True)
    
    for bp, synonyms in sorted_bodyparts:
        for synonym in synonyms:
            pattern = r'\b' + re.escape(synonym) + r'\b'
            if re.search(pattern, q):
                if bp not in detected:
                    detected.append(bp)
                    print(f"  ✅ BodyPart: '{synonym}' → {bp}")
                break
    
    return detected

# ============================================================
# ✅ UPDATED: BUILD CYPHER WITH EQUIPMENT FILTER
# ============================================================
def build_bodyparts_cypher(bodypart_list, equipment_list=None, limit: int = 3):
    """
    Build cypher with optional equipment filtering - FIXED SYNTAX
    """
    bp_filter = "', '".join(bodypart_list)
    
    if equipment_list:
        # WITH equipment filter - FIX: Properly carry bp and tgt variables
        eq_filter = "', '".join(equipment_list)
        cypher = f"""
MATCH (e:Exercise)-[tgt:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['{bp_filter}']
WITH DISTINCT e

MATCH (e)-[:USES_EQUIPMENT]->(eq:Equipment)
WHERE eq.name IN ['{eq_filter}']
WITH DISTINCT e LIMIT {limit}

OPTIONAL MATCH (e)-[r1:TARGETS]->(b:BodyPart)
OPTIONAL MATCH (e)-[r2:INVOLVES]->(t:Technique)
OPTIONAL MATCH (e)-[r3:CAUSES]->(ir:InjuryRisk)
OPTIONAL MATCH (e)-[r4:USES_EQUIPMENT]->(eq_all:Equipment)
OPTIONAL MATCH (e)-[r5:SUPPORTED_BY]->(sc:ScienceConcept)
RETURN e, b, r1, t, r2, ir, r3, eq_all, r4, sc, r5
"""
    else:
        # WITHOUT equipment filter (original)
        cypher = f"""
MATCH (e:Exercise)-[tgt:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['{bp_filter}']
WITH DISTINCT e LIMIT {limit}

OPTIONAL MATCH (e)-[r1:TARGETS]->(b:BodyPart)
OPTIONAL MATCH (e)-[r2:INVOLVES]->(t:Technique)
OPTIONAL MATCH (e)-[r3:CAUSES]->(ir:InjuryRisk)
OPTIONAL MATCH (e)-[r4:USES_EQUIPMENT]->(eq:Equipment)
OPTIONAL MATCH (e)-[r5:SUPPORTED_BY]->(sc:ScienceConcept)
RETURN e, b, r1, t, r2, ir, r3, eq, r4, sc, r5
"""
    
    return cypher


# ============================================================
# GENERAL KNOWLEDGE QUERY (UNCHANGED)
# ============================================================
def query_general_knowledge(question: str):
    q = question.lower()
    
    words = re.findall(r'\b[a-z]{4,}\b', q)
    stop_words = {'adalah', 'yang', 'untuk', 'dengan', 'pada', 'dalam', 'dari', 
                  'kepada', 'oleh', 'tentang', 'apakah', 'bagaimana', 'dimaksud',
                  'jelaskan', 'berapa', 'sebutkan', 'latihan', 'berikan'}
    keywords = [w for w in words if w not in stop_words]
    
    print(f"🔍 Extracted keywords: {keywords}")
    
    if not keywords:
        return None
    
    results = {}
    
    for keyword in keywords[:5]:
        try:
            cypher = f"""
            MATCH (bp:BodyPart)
            WHERE toLower(bp.name) CONTAINS '{keyword}'
            OPTIONAL MATCH (e:Exercise)-[r:TARGETS]->(bp)
            RETURN bp, collect(DISTINCT {{exercise: e.name, rel: type(r)}})[0..3] as exercises
            LIMIT 3
            """
            rows = graph.run(cypher)
            for row in rows:
                d = dict(row)
                if d['bp']:
                    if 'bodyparts' not in results:
                        results['bodyparts'] = []
                    results['bodyparts'].append({
                        'name': d['bp']['name'],
                        'exercises': [ex['exercise'] for ex in d.get('exercises', []) if ex.get('exercise')]
                    })
        except Exception as e:
            print(f"⚠️ BodyPart query error: {e}")
        
        try:
            cypher = f"""
            MATCH (sc:ScienceConcept)
            WHERE toLower(sc.name) CONTAINS '{keyword}'
            OPTIONAL MATCH (e:Exercise)-[r:SUPPORTED_BY]->(sc)
            RETURN sc, collect(DISTINCT e.name)[0..3] as exercises
            LIMIT 3
            """
            rows = graph.run(cypher)
            for row in rows:
                d = dict(row)
                if d['sc']:
                    if 'science_concepts' not in results:
                        results['science_concepts'] = []
                    results['science_concepts'].append({
                        'name': d['sc']['name'],
                        'exercises': d.get('exercises', [])
                    })
        except Exception as e:
            print(f"⚠️ ScienceConcept query error: {e}")
        
        try:
            cypher = f"""
            MATCH (ir:InjuryRisk)
            WHERE toLower(ir.name) CONTAINS '{keyword}'
            OPTIONAL MATCH (e:Exercise)-[r:CAUSES]->(ir)
            RETURN ir, collect(DISTINCT e.name)[0..3] as exercises
            LIMIT 3
            """
            rows = graph.run(cypher)
            for row in rows:
                d = dict(row)
                if d['ir']:
                    if 'injury_risks' not in results:
                        results['injury_risks'] = []
                    results['injury_risks'].append({
                        'name': d['ir']['name'],
                        'exercises': d.get('exercises', [])
                    })
        except Exception as e:
            print(f"⚠️ InjuryRisk query error: {e}")
        
        try:
            cypher = f"""
            MATCH (t:Technique)
            WHERE toLower(t.name) CONTAINS '{keyword}'
            OPTIONAL MATCH (e:Exercise)-[r:INVOLVES]->(t)
            RETURN t, collect(DISTINCT e.name)[0..3] as exercises
            LIMIT 3
            """
            rows = graph.run(cypher)
            for row in rows:
                d = dict(row)
                if d['t']:
                    if 'techniques' not in results:
                        results['techniques'] = []
                    results['techniques'].append({
                        'name': d['t']['name'],
                        'exercises': d.get('exercises', [])
                    })
        except Exception as e:
            print(f"⚠️ Technique query error: {e}")
        
        try:
            cypher = f"""
            MATCH (cc:CoachingCue)
            WHERE toLower(cc.name) CONTAINS '{keyword}'
            RETURN cc
            LIMIT 3
            """
            rows = graph.run(cypher)
            for row in rows:
                d = dict(row)
                if d['cc']:
                    if 'coaching_cues' not in results:
                        results['coaching_cues'] = []
                    results['coaching_cues'].append({
                        'name': d['cc']['name']
                    })
        except Exception as e:
            print(f"⚠️ CoachingCue query error: {e}")
    
    for key in results:
        if key != 'exercises':
            unique_names = set()
            unique_items = []
            for item in results[key]:
                if item['name'] not in unique_names:
                    unique_names.add(item['name'])
                    unique_items.append(item)
            results[key] = unique_items
    
    print(f"✅ Found data: {list(results.keys())}")
    
    return results if results else None

# ============================================================
# FORMAT GENERAL ANSWER (UNCHANGED)
# ============================================================
def format_general_answer(question: str, data):
    if not data:
        return """
⚠️ **Informasi Tidak Tersedia**

Maaf, informasi yang Anda cari tidak ditemukan dalam knowledge graph.

Sistem ini dapat menjawab pertanyaan tentang:
- 💪 **Bodyparts** (otot tubuh)
- 🔬 **Science Concepts** (konsep training)
- ⚠️ **Injury Risks** (risiko cedera)
- 📋 **Techniques** (teknik latihan)
- 🎯 **Coaching Cues** (panduan)

Silakan coba pertanyaan lain yang lebih spesifik.
"""
    
    try:
        prompt = f"""
Pertanyaan user: "{question}"

Data dari Neo4j:
{json.dumps(data, ensure_ascii=False, indent=2)}

Jawab pertanyaan HANYA menggunakan data di atas.

ATURAN:
1. HANYA gunakan info dari JSON
2. Format 2-4 paragraf formal akademik
3. Gunakan **bold** untuk istilah teknis
4. Jika ada exercises, sebutkan sebagai contoh

Tulis maksimal 4 paragraf ringkas.
"""
        
        answer = llm.invoke(prompt).content.strip()
        answer = re.sub(r'\n{3,}', '\n\n', answer)
        return answer
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return "⚠️ Terjadi kesalahan dalam memformat jawaban."

# ============================================================
# FORMAT EXERCISE ANSWER (UNCHANGED)
# ============================================================
def format_exercise_answer(rows):
    if not rows:
        return "⚠️ Tidak ada data latihan yang ditemukan dalam knowledge graph."

    try:
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

            bp = d.get("bp") or d.get("targetBP")
            if bp:
                exs[eid]["bodyparts"].add(bp.get("name"))

            if d.get("b"): exs[eid]["bodyparts"].add(d["b"]["name"])
            if d.get("t"): exs[eid]["techniques"].add(d["t"]["name"])
            if d.get("ir"): exs[eid]["injury_risks"].add(d["ir"]["name"])
            if d.get("eq"): exs[eid]["equipment"].add(d["eq"]["name"])
            if d.get("eq_all"): exs[eid]["equipment"].add(d["eq_all"]["name"])
            if d.get("sc"): exs[eid]["science"].add(d["sc"]["name"])

        formatted = []
        for v in exs.values():
            formatted.append({
                "name": v["name"],
                "bodyparts": sorted(v["bodyparts"]),
                "techniques": sorted(v["techniques"]),
                "injury_risks": sorted(v["injury_risks"]),
                "equipment": sorted(v["equipment"]),
                "science_concepts": sorted(v["science"]),
            })

        prompt = f"""
Data latihan dari Neo4j:
{json.dumps(formatted, ensure_ascii=False, indent=2)}

Tulis penjelasan untuk setiap latihan dengan format akademik profesional.

FORMAT:
### 💪 **[Nomor]. [Nama Latihan]**

**🎯 Target Otot**
[2 paragraf tentang bodyparts]

**📋 Teknik Pelaksanaan**
[3 paragraf dengan referensi techniques]

**🔧 Equipment yang Digunakan**
[1-2 paragraf tentang equipment]

**⚠️ Pertimbangan Keamanan**
[2 paragraf tentang injury_risks]

**🔬 Landasan Ilmiah**
[2 paragraf tentang science_concepts]

---

ATURAN:
- HANYA gunakan data dari JSON
- Setiap paragraf dipisah baris kosong
- Format istilah dengan **bold**
- Skip section jika field kosong
- Bahasa Indonesia formal akademik
"""

        text = llm.invoke(prompt).content.strip()
        
        text = re.sub(r"(\*\*🎯 Target Otot\*\*)", r"\1\n", text)
        text = re.sub(r"(\*\*📋 Teknik Pelaksanaan\*\*)", r"\1\n", text)
        text = re.sub(r"(\*\*🔧 Equipment yang Digunakan\*\*)", r"\1\n", text)
        text = re.sub(r"(\*\*⚠️ Pertimbangan Keamanan\*\*)", r"\1\n", text)
        text = re.sub(r"(\*\*🔬 Landasan Ilmiah\*\*)", r"\1\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return f"⚠️ Terjadi kesalahan: {str(e)}"

# ============================================================
# ✅ UPDATED: MAIN ROUTER WITH EQUIPMENT DETECTION
# ============================================================
def answer(question: str) -> Tuple[str, List[Dict]]:
    """
    Returns: (answer_text, context_data)
    """
    try:
        q = question.lower()
        limit = extract_requested_count(question, default=3)

        print(f"\n{'='*70}")
        print(f"🔍 Processing: {question}")
        print(f"{'='*70}")

        # Track context data
        context_data = []

        # PRIORITY 1: Exercise recommendation
        exercise_keywords = ["berikan", "rekomendasi", "kasih", "variasi", "contoh latihan"]
        is_explicit_exercise = any(k in q for k in exercise_keywords)
        
        if is_explicit_exercise:
            print("✅ Type: EXERCISE REQUEST")
            
            detected_equipment = detect_equipment(q)
            
            # PUSH/PULL/LEG
            if any(x in q for x in ["push day", "push", "latihan push"]):
                cy = build_bodyparts_cypher(['Chest', 'Shoulders', 'Triceps'], detected_equipment, limit=limit)
                rows = graph.run(cy)
                
                # ✅ Extract context data
                context_data = extract_context_from_rows(rows)
                
                answer_text = format_exercise_answer(rows) if rows else "⚠️ Tidak ada data latihan push."
                return answer_text, context_data

            if any(x in q for x in ["pull day", "pull", "latihan pull"]):
                cy = build_bodyparts_cypher(['Back', 'Lats', 'Biceps'], detected_equipment, limit=limit)
                rows = graph.run(cy)
                context_data = extract_context_from_rows(rows)
                answer_text = format_exercise_answer(rows) if rows else "⚠️ Tidak ada data latihan pull."
                return answer_text, context_data

            if any(x in q for x in ["leg day", "legs", "kaki", "latihan kaki"]):
                cy = build_bodyparts_cypher(['Quadriceps', 'Hamstrings', 'Glutes', 'Calves'], detected_equipment, limit=limit)
                rows = graph.run(cy)
                context_data = extract_context_from_rows(rows)
                answer_text = format_exercise_answer(rows) if rows else "⚠️ Tidak ada data latihan kaki."
                return answer_text, context_data

            # Specific bodyparts
            detected_bodyparts = detect_body_parts(q)
            if detected_bodyparts:
                cy = build_bodyparts_cypher(detected_bodyparts, detected_equipment, limit=limit)
                rows = graph.run(cy)
                context_data = extract_context_from_rows(rows)
                
                if rows:
                    answer_text = format_exercise_answer(rows)
                    return answer_text, context_data
                else:
                    if detected_equipment:
                        answer_text = f"⚠️ Tidak ada latihan {', '.join(detected_bodyparts)} menggunakan {', '.join(detected_equipment)}."
                    else:
                        answer_text = f"⚠️ Tidak ada latihan {', '.join(detected_bodyparts)}."
                    return answer_text, context_data

        # PRIORITY 2: General knowledge
        print("✅ Type: GENERAL KNOWLEDGE")
        data = query_general_knowledge(question)
        
        # ✅ Convert data to context format
        if data:
            context_data = []
            for key, items in data.items():
                for item in items:
                    context_data.append({
                        'type': key,
                        'name': item.get('name'),
                        'exercises': item.get('exercises', [])
                    })
        
        answer_text = format_general_answer(question, data)
        return answer_text, context_data

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return f"⚠️ Terjadi kesalahan sistem: {str(e)}", []


# ✅ NEW: Extract context data from Neo4j rows
def extract_context_from_rows(rows) -> List[Dict]:
    """
    Extract structured context data from Neo4j query results
    """
    context = []
    
    if not rows:
        return context
    
    try:
        for row in rows:
            d = dict(row)
            e = d.get("e")
            
            if e:
                exercise_data = {
                    'type': 'exercise',
                    'name': e.get("name"),
                    'bodyparts': [],
                    'techniques': [],
                    'injury_risks': [],
                    'equipment': [],
                    'science_concepts': []
                }
                
                # Extract bodyparts
                if d.get("b"):
                    exercise_data['bodyparts'].append(d["b"].get("name"))
                
                # Extract techniques
                if d.get("t"):
                    exercise_data['techniques'].append(d["t"].get("name"))
                
                # Extract injury risks
                if d.get("ir"):
                    exercise_data['injury_risks'].append(d["ir"].get("name"))
                
                # Extract equipment
                if d.get("eq"):
                    exercise_data['equipment'].append(d["eq"].get("name"))
                if d.get("eq_all"):
                    exercise_data['equipment'].append(d["eq_all"].get("name"))
                
                # Extract science concepts
                if d.get("sc"):
                    exercise_data['science_concepts'].append(d["sc"].get("name"))
                
                context.append(exercise_data)
    
    except Exception as e:
        print(f"⚠️ Error extracting context: {e}")
    
    return context
# ============================================================
# CLI
# ============================================================
def main():
    print("\n" + "="*70)
    print("🎓 Graph RAG Exercise Recommendation System")
    print("📚 Supports Equipment-Filtered Recommendations!")
    print("="*70 + "\n")
    print(">> ", end="")
    q = input()
    print("\n" + answer(q) + "\n")

if __name__ == "__main__":
    main()