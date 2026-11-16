"""Script to benchmark and compare Retrieval Methods on Dev and Test splits.
Complies with Day 7 BENCHMARK.md and RUBRIC.md.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.retrievers import (
    LexicalRetriever,
    DenseRetriever,
    HybridRetriever,
    pack_context,
    hit
)


def evaluate_retriever(retriever, questions: list[dict[str, Any]], strategy_name: str, split: str, budget: int = 800) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    traces = []
    latencies = []
    
    for q in questions:
        start = time.perf_counter()
        # Respect metadata filter if question specifies one
        filters = q.get('filter')
        results = retriever.search(q['question'], filters=filters, top_k=3)
        context, ids = pack_context(results, budget=budget)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
        
        marked = [{**c, 'hit': hit(c, q['gold'])} for c in results]
        h1 = bool(marked and marked[0]['hit'])
        h3 = any(c['hit'] for c in marked)
        c_hit = any(c['hit'] and c['id'] in ids for c in marked)
        
        traces.append({
            'query_id': q['id'],
            'split': split,
            'question': q['question'],
            'strategy': strategy_name,
            'top_k': 3,
            'budget_chars': budget,
            'filter': filters,
            'gold': q['gold'],
            'results': marked,
            'context': context,
            'context_ids': ids,
            'context_chars': len(context),
            'elapsed_ms': elapsed_ms,
            'hit1': h1,
            'hit3': h3,
            'context_hit': c_hit
        })
        
    n = len(traces)
    h1_count = sum(t['hit1'] for t in traces)
    h3_count = sum(t['hit3'] for t in traces)
    c_hit_count = sum(t['context_hit'] for t in traces)
    
    summary = {
        'strategy': strategy_name,
        'split': split,
        'n': n,
        'hit1': h1_count,
        'hit1_ratio': f"{h1_count}/{n} ({h1_count/n*100:.1f}%)" if n else "0/0",
        'hit3': h3_count,
        'hit3_ratio': f"{h3_count}/{n} ({h3_count/n*100:.1f}%)" if n else "0/0",
        'context_hit': c_hit_count,
        'context_hit_ratio': f"{c_hit_count}/{n} ({c_hit_count/n*100:.1f}%)" if n else "0/0",
        'avg_context_chars': statistics.mean(t['context_chars'] for t in traces) if traces else 0,
        'median_ms': statistics.median(latencies) if latencies else 0,
        'service_cost_usd': 0.0
    }
    return traces, summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate Day 7 Retrieval Methods")
    parser.add_argument("--chunks", default="data/chunks.json", type=Path)
    parser.add_argument("--questions", default="data/questions.json", type=Path)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--method", choices=("tfidf", "dense", "hybrid_rrf", "all"), default="all")
    parser.add_argument("--budget", type=int, default=800)
    parser.add_argument("--output_base", default="starter/results", type=Path)
    args = parser.parse_args()

    chunks = json.loads(args.chunks.read_text(encoding="utf-8"))
    all_questions = json.loads(args.questions.read_text(encoding="utf-8"))

    splits = ["dev", "test"] if args.split == "all" else [args.split]

    print(f"Loaded {len(chunks)} chunks and {len(all_questions)} questions.")

    # Initialize Retrievers
    print("Initializing Retrievers...")
    lexical_retriever = LexicalRetriever(chunks)
    dense_retriever = DenseRetriever(persist_dir="starter/chroma_data", collection_name="strategy_b")
    hybrid_retriever = HybridRetriever(dense_retriever, lexical_retriever, rrf_k=60, pool_size=15)

    retrievers_map = {
        "tfidf": ("TF-IDF Lexical", lexical_retriever),
        "dense": ("Dense ChromaDB (MiniLM-384d)", dense_retriever),
        "hybrid_rrf": ("Hybrid RRF (Dense + TFIDF)", hybrid_retriever)
    }

    target_methods = list(retrievers_map.keys()) if args.method == "all" else [args.method]

    overall_results = []

    for sp in splits:
        selected_q = [q for q in all_questions if q.get("split") == sp]
        print(f"\n==================== SPLIT: {sp.upper()} ({len(selected_q)} questions) ====================")
        
        for m_key in target_methods:
            m_name, r_inst = retrievers_map[m_key]
            out_dir = args.output_base / f"{m_key}-{sp}"
            out_dir.mkdir(parents=True, exist_ok=True)
            
            traces, summary = evaluate_retriever(r_inst, selected_q, m_name, sp, budget=args.budget)
            
            # Save traces and summary
            (out_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
            (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            
            overall_results.append(summary)
            print(f"[{m_name}] Hit@1: {summary['hit1_ratio']} | Hit@3: {summary['hit3_ratio']} | Context Hit: {summary['context_hit_ratio']} | Latency: {summary['median_ms']:.2f}ms")

    print("\n" + "=" * 95)
    print(f"{'Strategy':<30} | {'Split':<6} | {'Hit@1':<15} | {'Evidence Hit@3':<15} | {'Context Hit':<15} | {'Latency':<8}")
    print("-" * 95)
    for r in overall_results:
        print(f"{r['strategy']:<30} | {r['split']:<6} | {r['hit1_ratio']:<15} | {r['hit3_ratio']:<15} | {r['context_hit_ratio']:<15} | {r['median_ms']:.2f}ms")
    print("=" * 95)


if __name__ == "__main__":
    main()
