"""Checkpoint 4: Improvement Configurations & Error Analysis on Dev.
Tests:
1. Improvement 1: Dense Retrieval with Budget 1500 chars (overcoming Context Cutoff)
2. Improvement 2: Hybrid RRF with Budget 1500 chars + Metadata Filtering (Best Candidate)
"""
import json
import statistics
import sys
import time
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
starter_dir = root_dir / "starter"
for d in [root_dir, starter_dir]:
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from src.retrievers import DenseRetriever, LexicalRetriever, HybridRetriever, pack_context, hit

CHUNKS_FILE = root_dir / "data" / "chunks.json"
QUESTIONS_FILE = root_dir / "data" / "questions.json"
RESULTS_DIR = starter_dir / "results"


def evaluate_config(retriever, questions, budget=1500, use_filter=True, strategy_name=""):
    traces = []
    latencies = []
    for q in questions:
        start = time.perf_counter()
        filters = q.get("filter") if use_filter else None
        results = retriever.search(q["question"], filters=filters, top_k=3)
        context, ids = pack_context(results, budget=budget)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
        
        marked = [{**c, "hit": hit(c, q["gold"])} for c in results]
        h1 = bool(marked and marked[0]["hit"])
        h3 = any(c["hit"] for c in marked)
        c_hit = any(c["hit"] and c["id"] in ids for c in marked)
        
        traces.append({
            "query_id": q["id"],
            "split": q["split"],
            "question": q["question"],
            "strategy": strategy_name,
            "top_k": 3,
            "budget_chars": budget,
            "filter": filters,
            "gold": q["gold"],
            "results": marked,
            "context": context,
            "context_ids": ids,
            "context_chars": len(context),
            "elapsed_ms": elapsed_ms,
            "hit1": h1,
            "hit3": h3,
            "context_hit": c_hit
        })
        
    n = len(traces)
    h1_count = sum(t["hit1"] for t in traces)
    h3_count = sum(t["hit3"] for t in traces)
    c_hit_count = sum(t["context_hit"] for t in traces)
    
    summary = {
        "strategy": strategy_name,
        "split": "dev",
        "n": n,
        "hit1": h1_count,
        "hit1_ratio": f"{h1_count}/{n} ({h1_count/n*100:.1f}%)",
        "hit3": h3_count,
        "hit3_ratio": f"{h3_count}/{n} ({h3_count/n*100:.1f}%)",
        "context_hit": c_hit_count,
        "context_hit_ratio": f"{c_hit_count}/{n} ({c_hit_count/n*100:.1f}%)",
        "avg_context_chars": statistics.mean(t["context_chars"] for t in traces),
        "median_ms": statistics.median(latencies),
        "service_cost_usd": 0.0
    }
    return traces, summary


def main():
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    dev_q = [q for q in questions if q["split"] == "dev"]
    
    print(f"Loaded {len(chunks)} chunks and {len(dev_q)} dev questions.")
    
    dense_r = DenseRetriever(persist_dir="starter/chroma_data", collection_name="strategy_b")
    lex_r = LexicalRetriever(chunks)
    hybrid_r = HybridRetriever(dense_r, lex_r, rrf_k=60, pool_size=15)
    
    # Run Improvement 1: Dense with Budget 1500
    print("\n--- Running Improvement 1: Dense ChromaDB with Budget 1500 chars ---")
    traces_imp1, sum_imp1 = evaluate_config(dense_r, dev_q, budget=1500, use_filter=True, strategy_name="Dense (Budget 1500)")
    dir_imp1 = RESULTS_DIR / "improvement1-dense-b1500-dev"
    dir_imp1.mkdir(parents=True, exist_ok=True)
    (dir_imp1 / "traces.json").write_text(json.dumps(traces_imp1, ensure_ascii=False, indent=2), encoding="utf-8")
    (dir_imp1 / "summary.json").write_text(json.dumps(sum_imp1, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Improvement 1: Hit@1: {sum_imp1['hit1_ratio']} | Hit@3: {sum_imp1['hit3_ratio']} | Context Hit: {sum_imp1['context_hit_ratio']}")

    # Run Improvement 2: Hybrid RRF with Budget 1500 + Metadata Filter
    print("\n--- Running Improvement 2: Hybrid RRF (Budget 1500 + Metadata Filter) ---")
    traces_imp2, sum_imp2 = evaluate_config(hybrid_r, dev_q, budget=1500, use_filter=True, strategy_name="Hybrid RRF (Budget 1500 + Filter)")
    dir_imp2 = RESULTS_DIR / "improvement2-hybrid-b1500-dev"
    dir_imp2.mkdir(parents=True, exist_ok=True)
    (dir_imp2 / "traces.json").write_text(json.dumps(traces_imp2, ensure_ascii=False, indent=2), encoding="utf-8")
    (dir_imp2 / "summary.json").write_text(json.dumps(sum_imp2, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Improvement 2: Hit@1: {sum_imp2['hit1_ratio']} | Hit@3: {sum_imp2['hit3_ratio']} | Context Hit: {sum_imp2['context_hit_ratio']}")


if __name__ == "__main__":
    main()
