"""Script to export and validate Day 6 chunks and benchmark for Day 7."""
import json
from pathlib import Path
import chromadb

DAY6_CHROMA = Path(r"C:\Users\reals\Vin\K5-L3-Day06-DataIngestionEngineering\starter\chroma_data")
DAY6_QUESTIONS = Path(r"C:\Users\reals\Vin\K5-L3-Day06-DataIngestionEngineering\benchmark\questions.json")
OUTPUT_DIR = Path("data")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    
    # 1. Connect to ChromaDB
    print(f"Connecting to Day 6 ChromaDB at: {DAY6_CHROMA}")
    client = chromadb.PersistentClient(path=str(DAY6_CHROMA))
    
    col_b = client.get_collection("strategy_b")
    count_b = col_b.count()
    print(f"Collection 'strategy_b' has {count_b} chunks.")
    
    # Fetch all items from strategy_b
    data_b = col_b.get(include=["documents", "metadatas"])
    chunks = []
    for cid, doc, meta in zip(data_b["ids"], data_b["documents"], data_b["metadatas"]):
        clean_meta = dict(meta) if meta else {}
        chunks.append({
            "id": cid,
            "text": doc,
            "source_id": clean_meta.get("document_id", "wb_annual_report"),
            "source": clean_meta.get("source", "data/world_bank_annual_report.pdf"),
            "page": int(clean_meta.get("page", clean_meta.get("physical_page", 1))),
            "metadata": clean_meta
        })
    
    chunks_file = OUTPUT_DIR / "chunks.json"
    chunks_file.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(chunks)} chunks to {chunks_file}")
    
    # Also fetch strategy_a for comparison
    col_a = client.get_collection("strategy_a")
    data_a = col_a.get(include=["documents", "metadatas"])
    chunks_a = []
    for cid, doc, meta in zip(data_a["ids"], data_a["documents"], data_a["metadatas"]):
        clean_meta = dict(meta) if meta else {}
        chunks_a.append({
            "id": cid,
            "text": doc,
            "source_id": clean_meta.get("document_id", "wb_annual_report"),
            "source": clean_meta.get("source", "data/world_bank_annual_report.pdf"),
            "page": int(clean_meta.get("page", clean_meta.get("physical_page", 1))),
            "metadata": clean_meta
        })
    (OUTPUT_DIR / "chunks_strategy_a.json").write_text(json.dumps(chunks_a, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(chunks_a)} strategy_a chunks to data/chunks_strategy_a.json")

    # 2. Convert questions
    raw_questions = json.loads(DAY6_QUESTIONS.read_text(encoding="utf-8"))
    converted_questions = []
    for q in raw_questions:
        ev = q["evidence_quote"]
        # Normalize whitespace mismatch in q20
        if q["id"] == "q20":
            ev = "Climate action remains a crucial global priority. The Executive Directors wel -\ncome the efforts the Bank Group"
            
        gold = [{
            "source_id": q["gold_source_id"],
            "page": q["gold_page"],
            "evidence": ev
        }]
        item = {
            "id": q["id"],
            "split": q["split"],
            "question": q["question"],
            "expected_answer": q["expected_answer"],
            "gold": gold
        }
        if "filter" in q and q["filter"]:
            item["filter"] = q["filter"]
        converted_questions.append(item)
    
    # Check hit for each question
    def hit(chunk, gold):
        return any(
            chunk["source_id"] == g["source_id"]
            and chunk["page"] == g["page"]
            and g["evidence"] in chunk["text"]
            for g in gold
        )
    
    print("\n--- Validating Gold Evidence in Chunks (Strategy B) ---")
    missed = []
    for q in converted_questions:
        found = any(hit(c, q["gold"]) for c in chunks)
        if not found:
            # Let's inspect why: maybe whitespace or exact string match
            candidate_chunks = [c for c in chunks if c["source_id"] == q["gold"][0]["source_id"] and c["page"] == q["gold"][0]["page"]]
            missed.append((q["id"], len(candidate_chunks), q["gold"][0]["evidence"][:60]))
        else:
            print(f"  [OK] {q['id']} ({q['split']}) found in chunk")
            
    if missed:
        print(f"\nWarning: {len(missed)} questions did not match exact substring:")
        for mid, n_cands, ev in missed:
            print(f"  - {mid} (candidates on page: {n_cands}): {repr(ev)}")
    else:
        print("\nAll 20 Day 6 questions successfully matched chunks in Strategy B!")
        
    questions_file = OUTPUT_DIR / "questions.json"
    questions_file.write_text(json.dumps(converted_questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(converted_questions)} questions to {questions_file}")


if __name__ == "__main__":
    main()
