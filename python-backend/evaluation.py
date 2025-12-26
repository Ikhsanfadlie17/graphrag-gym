import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor
from main import graph, answer

load_dotenv()

# LLM for evaluation
eval_llm = ChatOpenAI(
    model="gpt-4.1",
    temperature=0,
    max_retries=2,
    timeout=30
)

# ============================================================
# 1. FAITHFULNESS
# ============================================================
def evaluate_faithfulness(question: str, answer_text: str, context_data: List[Dict]) -> float:
    """
    Mengukur apakah jawaban faithful terhadap data dari Neo4j
    """
    try:
        context_str = json.dumps(context_data, ensure_ascii=False, indent=2)[:2000]
        
        prompt = f"""
Evaluasi apakah ANSWER dibuat berdasarkan CONTEXT yang diberikan.

QUESTION: {question}

CONTEXT (Data dari Neo4j):
{context_str}

ANSWER:
{answer_text[:1000]}

TUGAS:
Berikan score 0-10 untuk faithfulness:
- 10: Semua klaim di answer ada di context
- 7-9: Sebagian besar klaim ada di context, sedikit inferensi wajar
- 4-6: Beberapa klaim tidak ada di context
- 0-3: Banyak klaim tidak ada di context atau hallucination

OUTPUT FORMAT (JSON):
{{
  "score": <0-10>,
  "reasoning": "<penjelasan singkat>"
}}
"""
        
        response = eval_llm.invoke(prompt).content.strip()
        start = response.find('{')
        end = response.rfind('}') + 1
        result = json.loads(response[start:end])
        
        score = result.get('score', 0) / 10.0
        print(f"   ✅ Faithfulness: {score:.3f}")
        return score
    except Exception as e:
        print(f"⚠️ Faithfulness evaluation error: {e}")
        return 0.5

# ============================================================
# 2. ANSWER RELEVANCY
# ============================================================
def evaluate_answer_relevancy(question: str, answer_text: str) -> float:
    """
    Mengukur relevansi jawaban terhadap pertanyaan
    """
    try:
        prompt = f"""
Evaluasi seberapa relevan ANSWER terhadap QUESTION.

QUESTION: {question}

ANSWER:
{answer_text[:1000]}

TUGAS:
Berikan score 0-10 untuk relevancy:
- 10: Jawaban sangat relevan, menjawab pertanyaan dengan lengkap
- 7-9: Jawaban relevan, menjawab sebagian besar pertanyaan
- 4-6: Jawaban agak relevan tapi tidak lengkap
- 0-3: Jawaban tidak relevan atau tidak menjawab pertanyaan

OUTPUT FORMAT (JSON):
{{
  "score": <0-10>,
  "reasoning": "<penjelasan>"
}}
"""
        
        response = eval_llm.invoke(prompt).content.strip()
        start = response.find('{')
        end = response.rfind('}') + 1
        result = json.loads(response[start:end])
        
        score = result.get('score', 0) / 10.0
        print(f"   ✅ Relevancy: {score:.3f}")
        return score
    except Exception as e:
        print(f"⚠️ Answer relevancy error: {e}")
        return 0.5

# ============================================================
# 3. CONTEXT PRECISION
# ============================================================
def evaluate_context_precision(question: str, context_data: List[Dict]) -> float:
    """
    Mengukur precision dari context yang di-retrieve
    """
    if not context_data:
        return 0.0
    
    try:
        context_str = json.dumps(context_data, ensure_ascii=False, indent=2)[:1500]
        
        prompt = f"""
Evaluasi apakah CONTEXT yang di-retrieve dari database relevan dengan QUESTION.

QUESTION: {question}

CONTEXT:
{context_str}

TUGAS:
Untuk setiap item di context, tentukan apakah relevan atau tidak.
Hitung: Precision = (jumlah item relevan) / (total item)

OUTPUT FORMAT (JSON):
{{
  "total_items": <number>,
  "relevant_items": <number>,
  "precision": <0.0-1.0>,
  "reasoning": "<penjelasan>"
}}
"""
        
        response = eval_llm.invoke(prompt).content.strip()
        start = response.find('{')
        end = response.rfind('}') + 1
        result = json.loads(response[start:end])
        
        precision = result.get('precision', 0.0)
        print(f"   ✅ Precision: {precision:.3f}")
        return precision
    except Exception as e:
        print(f"⚠️ Context precision error: {e}")
        return 0.5

# ============================================================
# 4. GRAPH COVERAGE
# ============================================================
def calculate_graph_coverage(context_data: List[Dict]) -> Dict[str, Any]:
    """
    Hitung coverage dari knowledge graph
    """
    try:
        total_nodes_query = "MATCH (n) RETURN count(n) as total"
        total_edges_query = "MATCH ()-[r]->() RETURN count(r) as total"
        
        total_nodes = graph.run(total_nodes_query)[0]['total']
        total_edges = graph.run(total_edges_query)[0]['total']
        
        used_nodes = set()
        used_edges = 0
        
        for item in context_data:
            if item.get('name'):
                used_nodes.add(item['name'])
            
            for key in ['bodyparts', 'techniques', 'injury_risks', 'equipment', 'science_concepts', 'exercises']:
                if key in item and item[key]:
                    if isinstance(item[key], list):
                        used_nodes.update(item[key])
                        used_edges += len(item[key])
                    else:
                        used_nodes.add(item[key])
                        used_edges += 1
        
        node_coverage = len(used_nodes) / total_nodes if total_nodes > 0 else 0
        edge_coverage = used_edges / total_edges if total_edges > 0 else 0
        
        return {
            'total_nodes': total_nodes,
            'used_nodes': len(used_nodes),
            'node_coverage': node_coverage,
            'total_edges': total_edges,
            'used_edges': used_edges,
            'edge_coverage': edge_coverage
        }
    except Exception as e:
        print(f"⚠️ Graph coverage error: {e}")
        return {
            'total_nodes': 0,
            'used_nodes': 0,
            'node_coverage': 0.0,
            'total_edges': 0,
            'used_edges': 0,
            'edge_coverage': 0.0
        }

# ============================================================
# 5. ✅ NEW: FAST EVALUATION WITH PRE-GENERATED ANSWER
# ============================================================
def evaluate_with_answer(
    question: str, 
    answer_text: str, 
    response_time_ms: float = 0.0
) -> Dict[str, Any]:
    """
    Evaluate with pre-generated answer (NO re-generation!)
    This is FAST because it skips answer generation step.
    
    Args:
        question: User's question
        answer_text: Pre-generated answer from frontend
        response_time_ms: Response time from original answer generation
    
    Returns:
        Evaluation results with metrics
    """
    print(f"\n{'='*70}")
    print(f"📊 Fast Evaluation (with pre-generated answer)")
    print(f"📝 Question: {question[:50]}...")
    print(f"📄 Answer length: {len(answer_text)} chars")
    print(f"{'='*70}")
    
    # Get context data by re-querying (this is fast, ~2-3s)
    print("🔍 Retrieving context data...")
    try:
        _, context_data = answer(question)
    except Exception as e:
        print(f"❌ Error getting context: {e}")
        context_data = []
    
    print(f"   Context items: {len(context_data)}")
    
    # Run all evaluations in PARALLEL (30-40s instead of 60-90s)
    print("🚀 Running parallel evaluations...")
    eval_start = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_faithfulness = executor.submit(
            evaluate_faithfulness, question, answer_text, context_data
        )
        future_relevancy = executor.submit(
            evaluate_answer_relevancy, question, answer_text
        )
        future_precision = executor.submit(
            evaluate_context_precision, question, context_data
        )
        
        faithfulness = future_faithfulness.result()
        relevancy = future_relevancy.result()
        precision = future_precision.result()
    
    eval_end = time.time()
    print(f"✅ Parallel evaluations complete in {eval_end - eval_start:.1f}s")
    
    # Calculate graph coverage
    print("🕸️  Calculating graph coverage...")
    coverage = calculate_graph_coverage(context_data)
    
    results = {
        'question': question,
        'answer': answer_text[:500] + '...' if len(answer_text) > 500 else answer_text,
        'context_items': len(context_data),
        'metrics': {
            'faithfulness': round(faithfulness, 3),
            'answer_relevancy': round(relevancy, 3),
            'context_precision': round(precision, 3),
            'response_time_ms': round(response_time_ms, 2),
            'graph_coverage': round(coverage['node_coverage'], 4)
        },
        'details': {
            'timing': {
                'latency_ms': response_time_ms,
                'success': True,
                'answer_length': len(answer_text)
            },
            'coverage': coverage
        },
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"\n✅ Evaluation Complete!")
    print(f"   Faithfulness: {results['metrics']['faithfulness']:.3f}")
    print(f"   Relevancy: {results['metrics']['answer_relevancy']:.3f}")
    print(f"   Precision: {results['metrics']['context_precision']:.3f}")
    print(f"   Graph Coverage: {results['metrics']['graph_coverage']:.4f}")
    
    return results

# ============================================================
# 6. ORIGINAL: EVALUATION WITH ANSWER GENERATION
# ============================================================
def evaluate_single_query_fast(question: str, expected_context: List[Dict] = None) -> Dict[str, Any]:
    """
    Fast evaluation WITH answer generation (for batch testing)
    """
    print(f"\n{'='*70}")
    print(f"📊 Fast Evaluation: {question}")
    print(f"{'='*70}")
    
    start_time = time.time()
    
    try:
        answer_text, context_data = answer(question)
        end_time = time.time()
        
        timing = {
            'latency_ms': (end_time - start_time) * 1000,
            'success': True,
            'answer_length': len(answer_text)
        }
    except Exception as e:
        end_time = time.time()
        print(f"❌ Error: {e}")
        return {
            'question': question,
            'error': str(e),
            'metrics': {
                'faithfulness': 0.0,
                'answer_relevancy': 0.0,
                'context_precision': 0.0,
                'response_time_ms': (end_time - start_time) * 1000,
                'graph_coverage': 0.0
            }
        }
    
    print(f"   Answer length: {len(answer_text)} chars")
    print(f"   Context items: {len(context_data)}")
    
    eval_start = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_faithfulness = executor.submit(
            evaluate_faithfulness, question, answer_text, context_data
        )
        future_relevancy = executor.submit(
            evaluate_answer_relevancy, question, answer_text
        )
        future_precision = executor.submit(
            evaluate_context_precision, question, context_data
        )
        
        faithfulness = future_faithfulness.result()
        relevancy = future_relevancy.result()
        precision = future_precision.result()
    
    eval_end = time.time()
    print(f"✅ Evaluations complete in {eval_end - eval_start:.1f}s")
    
    coverage = calculate_graph_coverage(context_data)
    
    results = {
        'question': question,
        'answer': answer_text[:500] + '...' if len(answer_text) > 500 else answer_text,
        'context_items': len(context_data),
        'metrics': {
            'faithfulness': round(faithfulness, 3),
            'answer_relevancy': round(relevancy, 3),
            'context_precision': round(precision, 3),
            'response_time_ms': round(timing['latency_ms'], 2),
            'graph_coverage': round(coverage['node_coverage'], 4)
        },
        'details': {
            'timing': timing,
            'coverage': coverage
        },
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"\n✅ Complete!")
    print(f"   Faithfulness: {results['metrics']['faithfulness']:.3f}")
    print(f"   Relevancy: {results['metrics']['answer_relevancy']:.3f}")
    print(f"   Precision: {results['metrics']['context_precision']:.3f}")
    print(f"   Response Time: {results['metrics']['response_time_ms']:.2f}ms")
    print(f"   Graph Coverage: {results['metrics']['graph_coverage']:.4f}")
    
    return results

# ============================================================
# 7. BATCH EVALUATION
# ============================================================
def evaluate_test_set(test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluasi batch untuk multiple test cases
    """
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'#'*70}")
        print(f"Test Case {i}/{len(test_cases)}")
        print(f"{'#'*70}")
        
        result = evaluate_single_query_fast(
            question=test_case['question']
        )
        
        result['category'] = test_case.get('category', 'general')
        results.append(result)
        
        time.sleep(1)
    
    avg_metrics = {
        'faithfulness': sum(r['metrics']['faithfulness'] for r in results) / len(results),
        'answer_relevancy': sum(r['metrics']['answer_relevancy'] for r in results) / len(results),
        'context_precision': sum(r['metrics']['context_precision'] for r in results) / len(results),
        'response_time_ms': sum(r['metrics']['response_time_ms'] for r in results) / len(results),
        'graph_coverage': sum(r['metrics']['graph_coverage'] for r in results) / len(results),
    }
    
    summary = {
        'total_queries': len(test_cases),
        'timestamp': datetime.now().isoformat(),
        'average_metrics': {k: round(v, 3) for k, v in avg_metrics.items()},
        'individual_results': results
    }
    
    print(f"\n{'='*70}")
    print(f"📊 EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total Queries: {summary['total_queries']}")
    print(f"\nAverage Metrics:")
    for metric, value in summary['average_metrics'].items():
        print(f"  {metric}: {value:.3f}")
    
    return summary

# ============================================================
# 8. SAVE RESULTS
# ============================================================
def save_evaluation_results(results: Dict[str, Any], filename: str = None):
    """
    Save evaluation results to JSON file
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.json"
    
    filepath = os.path.join('evaluation_results', filename)
    os.makedirs('evaluation_results', exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {filepath}")
    return filepath

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    test_cases = [
        {
            "question": "berikan saya latihan chest 3 variasi",
            "category": "exercise_recommendation"
        },
        {
            "question": "apa itu hypertrophy?",
            "category": "general_knowledge"
        },
        {
            "question": "apa risiko bench press dengan beban terlalu berat?",
            "category": "injury_risk"
        },
        {
            "question": "berikan latihan triceps menggunakan dumbbell",
            "category": "equipment_filtered"
        },
        {
            "question": "otot quadriceps itu otot apa?",
            "category": "bodypart_definition"
        }
    ]
    
    print("🚀 Starting Fast Graph RAG Evaluation...")
    
    results = evaluate_test_set(test_cases)
    save_evaluation_results(results)
    
    print("\n✅ Evaluation complete!")
