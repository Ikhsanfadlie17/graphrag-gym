from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import re
import json
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
from main import answer, graph, detect_body_parts, detect_equipment

# ✅ Import evaluation functions
try:
    from evaluation import evaluate_with_answer, evaluate_single_query_fast, evaluate_test_set
    EVALUATION_AVAILABLE = True
except ImportError:
    EVALUATION_AVAILABLE = False
    print("⚠️ Warning: evaluation.py not found. Evaluation endpoints disabled.")

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

def get_cypher_from_question(question: str):
    """
    Generate cypher query from question
    """
    q = question.lower()
    
    print(f"\n🔍 Cypher Generation for: {q}")
    
    # ============================================================
    # 1) CEK PERMINTAAN LATIHAN (EXERCISE REQUEST)
    # ============================================================
    exercise_request_keywords = ["berikan", "rekomendasi", "kasih", "variasi", "contoh latihan"]
    is_exercise_request = any(k in q for k in exercise_request_keywords)
    
    if is_exercise_request:
        print("✅ Type: EXERCISE REQUEST")
        
        detected_equipment = detect_equipment(q)
        print(f"  Equipment detected for graph: {detected_equipment}")
        
        # PUSH DAY
        if any(x in q for x in ["push day", "push", "latihan push"]):
            if detected_equipment:
                eq_filter = "', '".join(detected_equipment)
                return f"""
MATCH (e:Exercise)-[:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['Chest', 'Shoulders', 'Triceps']
WITH DISTINCT e
MATCH (e)-[:USES_EQUIPMENT]->(eq:Equipment)
WHERE eq.name IN ['{eq_filter}']
WITH DISTINCT e LIMIT 3
MATCH (e)-[r]->(other)
RETURN e, other, r
"""
            else:
                return """
MATCH (e:Exercise)-[:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['Chest', 'Shoulders', 'Triceps']
WITH DISTINCT e LIMIT 3
MATCH (e)-[r]->(other)
RETURN e, other, r
"""

        # PULL DAY
        if any(x in q for x in ["pull day", "pull", "latihan pull"]):
            if detected_equipment:
                eq_filter = "', '".join(detected_equipment)
                return f"""
MATCH (e:Exercise)-[:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['Back', 'Lats', 'Biceps']
WITH DISTINCT e
MATCH (e)-[:USES_EQUIPMENT]->(eq:Equipment)
WHERE eq.name IN ['{eq_filter}']
WITH DISTINCT e LIMIT 3
MATCH (e)-[r]->(other)
RETURN e, other, r
"""
            else:
                return """
MATCH (e:Exercise)-[:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['Back', 'Lats', 'Biceps']
WITH DISTINCT e LIMIT 3
MATCH (e)-[r]->(other)
RETURN e, other, r
"""

        # LEG DAY
        if any(x in q for x in ["leg day", "legs", "kaki", "latihan kaki"]):
            if detected_equipment:
                eq_filter = "', '".join(detected_equipment)
                return f"""
MATCH (e:Exercise)-[:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['Quadriceps', 'Hamstrings', 'Glutes', 'Calves']
WITH DISTINCT e
MATCH (e)-[:USES_EQUIPMENT]->(eq:Equipment)
WHERE eq.name IN ['{eq_filter}']
WITH DISTINCT e LIMIT 3
MATCH (e)-[r]->(other)
RETURN e, other, r
"""
            else:
                return """
MATCH (e:Exercise)-[:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['Quadriceps', 'Hamstrings', 'Glutes', 'Calves']
WITH DISTINCT e LIMIT 3
MATCH (e)-[r]->(other)
RETURN e, other, r
"""

        # SPECIFIC BODY PARTS
        bodyparts = detect_body_parts(q)
        if bodyparts:
            bp_filter = "', '".join(bodyparts)
            
            if detected_equipment:
                eq_filter = "', '".join(detected_equipment)
                return f"""
MATCH (e:Exercise)-[:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['{bp_filter}']
WITH DISTINCT e
MATCH (e)-[:USES_EQUIPMENT]->(eq:Equipment)
WHERE eq.name IN ['{eq_filter}']
WITH DISTINCT e LIMIT 3
MATCH (e)-[r]->(other)
RETURN e, other, r
"""
            else:
                return f"""
MATCH (e:Exercise)-[:TARGETS]->(bp:BodyPart)
WHERE bp.name IN ['{bp_filter}']
WITH DISTINCT e LIMIT 3
MATCH (e)-[r]->(other)
RETURN e, other, r
"""

    # ============================================================
    # 2) KHUSUS: RISIKO CEDERA BERDASARKAN LATIHAN
    # ============================================================
    injury_terms = ['risiko', 'resiko', 'cidera', 'cedera', 'injury', 'bahaya']
    has_injury = any(t in q for t in injury_terms)

    # daftar kata latihan yang mau kamu mapping ke Exercise.name
    exercise_terms = [
        'deadlift', 'bench press', 'bench', 'squat', 'hip thrust',
        'row', 'pullover', 'curl', 'press', 'extension', 'pushdown'
    ]
    exercise_found = [w for w in exercise_terms if w in q]

    if has_injury and exercise_found:
        print("✅ Type: INJURY BY EXERCISE")
        print(f"  Exercise keywords for graph: {exercise_found}")

        # Bangun filter dinamis sesuai kata latihan yang ketemu di pertanyaan
        where_clauses = [f"toLower(e.name) CONTAINS '{kw}'" for kw in exercise_found]
        where_filter = " OR ".join(where_clauses)

        return f"""
MATCH (e:Exercise)
WHERE {where_filter}
WITH DISTINCT e LIMIT 5

// Fokus: hubungan latihan ↔ risiko cedera (+ konteks pendukung)
OPTIONAL MATCH (e)-[r1:CAUSES]->(ir:InjuryRisk)
OPTIONAL MATCH (e)-[r2:INVOLVES]->(t:Technique)
OPTIONAL MATCH (e)-[r3:SUPPORTED_BY]->(sc:ScienceConcept)
OPTIONAL MATCH (e)-[r4:TARGETS]->(bp:BodyPart)

RETURN
  e,
  ir, r1,
  t,  r2,
  sc, r3,
  bp, r4
"""

    # ============================================================
    # 3) FALLBACK: GENERAL KNOWLEDGE (QUERY UMUM)
    # ============================================================
    print("✅ Type: GENERAL KNOWLEDGE")
    
    words = re.findall(r'\b[a-z]{3,}\b', q)
    stop_words = {
        'adalah', 'yang', 'untuk', 'dengan', 'pada', 'dalam', 'dari',
        'kepada', 'oleh', 'tentang', 'apakah', 'bagaimana', 'dimaksud',
        'jelaskan', 'berapa', 'sebutkan', 'latihan', 'berikan',
        'otot', 'apa', 'itu', 'jika', 'saat', 'ketika', 'beban', 'berat',
        'terlalu', 'sangat', 'dapat', 'akan', 'hanya', 'yang'
    }
    
    keywords = [w for w in words if w not in stop_words]
    
    if any(x in q for x in ['risiko', 'resiko', 'cidera', 'cedera', 'injury', 'bahaya']):
        injury_terms_for_kw = ['risiko', 'resiko', 'cidera', 'cedera', 'injury']
        injury_keywords = [w for w in injury_terms_for_kw if w in q]
        
        exercise_terms_kw = [
            'bench', 'press', 'squat', 'deadlift', 'pullover', 'curl',
            'raise', 'extension', 'pushdown', 'dumbbell', 'barbell', 'row'
        ]
        exercise_found_kw = [w for w in exercise_terms_kw if w in q]
        
        keywords = injury_keywords + exercise_found_kw + keywords
    
    elif any(x in q for x in ['hypertrophy', 'rom', 'progressive', 'overload', 'detraining']):
        science_terms = ['hypertrophy', 'rom', 'progressive', 'overload', 'detraining']
        keywords = [w for w in science_terms if w in q] + keywords
    
    print(f"  Keywords: {keywords[:5]}")
    
    if not keywords:
        return "MATCH (n) WHERE n:ScienceConcept OR n:BodyPart OR n:InjuryRisk RETURN n LIMIT 10"
    
    keyword1 = keywords[0] if len(keywords) > 0 else ''
    keyword2 = keywords[1] if len(keywords) > 1 else keyword1
    
    cypher = f"""
    MATCH (n)
    WHERE (n:BodyPart OR n:ScienceConcept OR n:InjuryRisk OR n:Technique OR n:CoachingCue)
      AND (toLower(n.name) CONTAINS '{keyword1}' OR toLower(n.name) CONTAINS '{keyword2}')
    WITH n LIMIT 8

    OPTIONAL MATCH (n)-[r1]-(related1)
    WHERE related1:Exercise OR related1:BodyPart OR related1:ScienceConcept OR 
          related1:Technique OR related1:InjuryRisk OR related1:Equipment
    WITH n, collect(DISTINCT {{node: related1, rel: r1}})[0..6] as rels

    UNWIND CASE WHEN size(rels) > 0 THEN rels ELSE [{{node: null, rel: null}}] END as rel_data

    RETURN n, rel_data.node as related, rel_data.rel as r
    """
    
    print(f"  Cypher keywords: {keyword1}, {keyword2}")
    return cypher



@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/answer', methods=['POST', 'OPTIONS'])
def get_answer():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        print(f"\n{'='*70}")
        print(f"📩 Request: {question}")
        print(f"{'='*70}")
        
        result, context = answer(question)
        cypher = get_cypher_from_question(question)
        
        return jsonify({
            'answer': result,
            'cypher': cypher
        })
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/graph', methods=['POST', 'OPTIONS'])
def get_graph():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        cypher = data.get('cypher', '')
        
        if not cypher:
            return jsonify({'error': 'Cypher required'}), 400
        
        print(f"\n🔍 Executing:\n{cypher}")
        
        results = list(graph.driver.session(database="neo4j").run(cypher))
        
        nodes_dict = {}
        edges_list = []
        edge_id = 0
        
        colors = {
            'Exercise': '#3b82f6',
            'BodyPart': '#ef4444',
            'Technique': '#14b8a6',
            'InjuryRisk': '#eab308',
            'Equipment': '#22c55e',
            'ScienceConcept': '#a855f7',
            'CoachingCue': '#f97316',
        }
        
        for record in results:
            for key in record.keys():
                value = record[key]
                
                if hasattr(value, 'labels'):
                    node_id = value.id
                    if node_id not in nodes_dict:
                        labels = list(value.labels) if value.labels else []
                        label = labels[0] if labels else 'Unknown'
                        nodes_dict[node_id] = {
                            'id': node_id,
                            'label': value.get('name', str(node_id)),
                            'color': colors.get(label, '#64748b'),
                            'group': label,
                        }
                
                elif hasattr(value, 'type'):
                    if value.start_node and value.end_node:
                        edge_id += 1
                        edges_list.append({
                            'id': edge_id,
                            'from': value.start_node.id,
                            'to': value.end_node.id,
                            'label': value.type,
                        })
        
        nodes_list = list(nodes_dict.values())
        
        print(f"✅ Graph: {len(nodes_list)} nodes, {len(edges_list)} edges\n")
        
        return jsonify({
            'nodes': nodes_list,
            'edges': edges_list,
        })
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================================
# ✅ EVALUATION ENDPOINTS
# ============================================================

@app.route('/evaluate', methods=['POST', 'OPTIONS'])
def evaluate_query():
    """
    ✅ FIXED: Evaluate with PRE-GENERATED answer (NO re-generation!)
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    if not EVALUATION_AVAILABLE:
        return jsonify({'error': 'Evaluation module not available'}), 503
    
    try:
        data = request.json
        question = data.get('question', '')
        answer_text = data.get('answer', '')  # ✅ Get answer from frontend
        response_time_ms = data.get('response_time_ms', 0.0)  # ✅ Get original response time
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if not answer_text:
            return jsonify({'error': 'Answer is required'}), 400
        
        print(f"\n{'='*70}")
        print(f"📊 Evaluating (with pre-generated answer)")
        print(f"📝 Question: {question[:50]}...")
        print(f"📄 Answer length: {len(answer_text)} chars")
        print(f"{'='*70}")
        
        # ✅ Use evaluate_with_answer (NO answer re-generation!)
        results = evaluate_with_answer(question, answer_text, response_time_ms)
        
        return jsonify(results)
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/evaluate/batch', methods=['POST', 'OPTIONS'])
def evaluate_batch():
    """
    Evaluate multiple test cases
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    if not EVALUATION_AVAILABLE:
        return jsonify({'error': 'Evaluation module not available'}), 503
    
    try:
        data = request.json
        test_cases = data.get('test_cases', [])
        
        if not test_cases:
            return jsonify({'error': 'Test cases required'}), 400
        
        print(f"\n{'='*70}")
        print(f"📊 Batch Evaluation: {len(test_cases)} queries")
        print(f"{'='*70}")
        
        results = evaluate_test_set(test_cases)
        
        return jsonify(results)
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/metrics/latest', methods=['GET', 'OPTIONS'])
def get_latest_metrics():
    """
    Get latest evaluation results
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        results_dir = 'evaluation_results'
        if not os.path.exists(results_dir):
            return jsonify({'error': 'No evaluation results found'}), 404
        
        files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
        if not files:
            return jsonify({'error': 'No evaluation results found'}), 404
        
        latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(results_dir, f)))
        filepath = os.path.join(results_dir, latest_file)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        return jsonify(results)
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/metrics/all', methods=['GET', 'OPTIONS'])
def get_all_metrics():
    """
    Get all evaluation result files
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        results_dir = 'evaluation_results'
        if not os.path.exists(results_dir):
            return jsonify({'error': 'No evaluation results found'}), 404
        
        files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
        if not files:
            return jsonify({'error': 'No evaluation results found'}), 404
        
        all_results = []
        for filename in sorted(files, key=lambda f: os.path.getctime(os.path.join(results_dir, f)), reverse=True):
            filepath = os.path.join(results_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_results.append({
                    'filename': filename,
                    'timestamp': data.get('timestamp'),
                    'total_queries': data.get('total_queries'),
                    'average_metrics': data.get('average_metrics')
                })
        
        return jsonify({
            'count': len(all_results),
            'results': all_results
        })
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Flask Backend on http://0.0.0.0:5000")
    print("📊 Endpoints:")
    print("   /answer          - Get answer from RAG")
    print("   /graph           - Get graph visualization")
    print("   /health          - Health check")
    print("   /evaluate        - Fast evaluation (pre-generated answer)")
    print("   /evaluate/batch  - Batch evaluation")
    print("   /metrics/latest  - Get latest metrics")
    print("   /metrics/all     - Get all metrics history")
    print("="*70 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
