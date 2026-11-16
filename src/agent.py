"""Agentic RAG implementation for Day 7.
Features:
- Real Gemini LLM Controller (gemini-3.5-flash / gemini-3.8-flash)
- Dynamic tool-calling ReAct loop: search(query), filter(meta), answer(content, citations)
- Context Engineering: configurable context budget (800 / 1500 chars), deduplication, citation preservation
- Strict Abstention & Grounding Guardrails: rejects unanswerable questions without hallucination
- Trace preservation for starter/agent_metrics.py
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from dotenv import dotenv_values
from google import genai
from google.genai import types

root_dir = Path(__file__).resolve().parent.parent
starter_dir = root_dir / "starter"
for d in [root_dir, starter_dir]:
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from starter.baseline import pack_context
from starter.agentic import run_agent, Controller, Retriever
from src.retrievers import DenseRetriever, LexicalRetriever, HybridRetriever


SYSTEM_PROMPT = """Bạn là một AI Agent điều phối truy xuất thông tin và trả lời câu hỏi dựa trên tài liệu (Agentic RAG).
Mục tiêu tối thượng: Trả lời CHÍNH XÁC, CÓ TRÍCH DẪN NGUỒN và TUYỆT ĐỐI KHÔNG BỊA ĐẶT (Không hallucination).

Các hành động bạn có thể đưa ra tại mỗi lượt (JSON format):

1. "search": Khi context hiện tại chưa có thông tin hoặc chưa đủ bằng chứng để trả lời toàn diện.
   Hãy đưa ra một search query cô đọng, giàu từ khóa thực thể (tên riêng, số liệu, thuật ngữ kỹ thuật).
   Format:
   {
       "action": "search",
       "query": "<từ khóa tìm kiếm trọng tâm>"
   }

2. "answer": Khi context hiện tại ĐÃ CÓ ĐỦ BẰNG CHỨNG để trả lời câu hỏi một cách thuyết phục.
   BẮT BUỘC:
   - Trả lời đúng trọng tâm câu hỏi.
   - Gắn mã trích dẫn [chunk_id] ngay sau thông tin được lấy từ chunk đó.
   - Điền danh sách các chunk_id đã dùng vào mảng "citations".
   Format:
   {
       "action": "answer",
       "answer": "<câu trả lời đầy đủ và súc tích> [chunk_id]",
       "citations": ["chunk_id"]
   }

3. "abstain": Nếu câu hỏi hỏi về thông tin KHÔNG CÓ trong tài liệu, hoặc sau khi tìm kiếm không thấy bằng chứng:
   Hãy dứt khoát từ chối, KHÔNG ĐƯỢC SUY ĐOÁN:
   Format:
   {
       "action": "answer",
       "answer": "Không đủ bằng chứng để trả lời.",
       "citations": []
   }

QUY TẮC BẮT BUỘC:
- Mọi chunk_id trong "citations" và [chunk_id] trong "answer" PHẢI LÀ ID THỰC TẾ có trong Context được cung cấp.
- Chỉ trả lời DUY NHẤT một khối JSON hợp lệ, không kèm văn bản mở đầu hay kết thúc nào khác.
"""


class GeminiController:
    """Real LLM Controller using Google GenAI SDK."""
    
    def __init__(self, model_name: str = "gemini-3.5-flash", api_key: str | None = None):
        env_vals = dotenv_values("starter/.env")
        self.api_key = api_key or env_vals.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in starter/.env")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        prompt_parts = [f"Câu hỏi của người dùng: {question}\n"]
        if not history:
            prompt_parts.append("Context hiện tại: [Trống. Chưa có lượt tìm kiếm nào.]")
            prompt_parts.append("Hãy đưa ra query tìm kiếm đầu tiên.")
        else:
            latest = history[-1]
            ctx = latest.get("context", "")
            q_list = latest.get("queries", [])
            prompt_parts.append(f"Các query đã tìm kiếm trước đó: {q_list}")
            prompt_parts.append(f"Context tích lũy hiện có:\n{ctx}\n")
            if len(q_list) >= 2:
                prompt_parts.append("Lưu ý: Đã tìm kiếm nhiều lượt. Nếu Context vẫn không có bằng chứng liên quan, hãy từ chối trả lời (action: answer, citations: []).")
            else:
                prompt_parts.append("Dựa vào Context, quyết định hành động tiếp theo: 'search' hoặc 'answer'.")

        prompt_str = "\n".join(prompt_parts)

        # Retry with backoff
        candidate_models = [self.model_name, "gemini-3.8-flash"]
        for attempt in range(4):
            for m in candidate_models:
                try:
                    response = self.client.models.generate_content(
                        model=m,
                        contents=prompt_str,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            temperature=0.0
                        )
                    )
                    text = response.text.strip()
                    action = json.loads(text)
                    if "action" in action:
                        return action
                except Exception as e:
                    err = str(e)
                    if "429" in err or "503" in err or "RESOURCE_EXHAUSTED" in err:
                        time.sleep(2.0 * (attempt + 1))
                    else:
                        print(f"[Warning] Model {m} error: {e}")
                        
        # Fallback if API fails completely
        return {"action": "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": []}


def run_benchmark_agent(
    cases: list[dict[str, Any]],
    controller: Controller,
    retriever: Retriever,
    *,
    split: str,
    max_searches: int = 3,
    top_k: int = 3,
    budget: int = 800,
    output_dir: Path | None = None
) -> list[dict[str, Any]]:
    """Execute agent loop across benchmark cases, logging full traces."""
    traces = []
    selected_cases = [c for c in cases if c.get("split") == split]
    
    print(f"\nRunning Agent on split: {split.upper()} ({len(selected_cases)} cases) | max_searches={max_searches}, top_k={top_k}, budget={budget}...")
    
    for idx, case in enumerate(selected_cases, 1):
        cid = case["id"]
        q_text = case["question"]
        filters = case.get("filter")
        
        start_t = time.perf_counter()
        try:
            result = run_agent(
                question=q_text,
                controller=controller,
                retriever=retriever,
                filters=filters,
                max_searches=max_searches,
                top_k=top_k,
                budget=budget
            )
            elapsed_ms = (time.perf_counter() - start_t) * 1000
            
            trace_entry = {
                "query_id": cid,
                "split": split,
                "question": q_text,
                "status": result["status"],
                "answer": result["answer"],
                "citations": result["citations"],
                "events": result["events"],
                "elapsed_ms": elapsed_ms,
                "tool_calls": sum(1 for e in result["events"] if e.get("event") == "search")
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_t) * 1000
            trace_entry = {
                "query_id": cid,
                "split": split,
                "question": q_text,
                "status": "error",
                "answer": f"Error: {e}",
                "citations": [],
                "events": [{"event": "error", "message": str(e)}],
                "elapsed_ms": elapsed_ms,
                "tool_calls": 0
            }
            
        traces.append(trace_entry)
        status_label = trace_entry["status"].upper()
        cites_count = len(trace_entry["citations"])
        print(f"  [{idx:02d}/{len(selected_cases):02d}] {cid}: {status_label} ({trace_entry['tool_calls']} searches, {cites_count} citations, {elapsed_ms:.1f}ms)")
        # Gentle sleep between API calls to avoid rate limits
        time.sleep(1.2)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved traces to {output_dir / 'traces.json'}")

    return traces


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Agentic RAG Benchmark")
    parser.add_argument("--cases", default="data/cases.json", type=Path)
    parser.add_argument("--chunks", default="data/chunks.json", type=Path)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--retriever", choices=("dense", "tfidf", "hybrid"), default="dense")
    parser.add_argument("--budget", type=int, default=800)
    parser.add_argument("--top_k", type=int, default=3)
    parser.add_argument("--max_searches", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("starter/results/agent-dev"))
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    chunks = json.loads(args.chunks.read_text(encoding="utf-8"))

    controller = GeminiController()
    
    if args.retriever == "dense":
        retriever = DenseRetriever()
    elif args.retriever == "tfidf":
        retriever = LexicalRetriever(chunks)
    else:
        dense_r = DenseRetriever()
        lex_r = LexicalRetriever(chunks)
        retriever = HybridRetriever(dense_r, lex_r)

    traces = run_benchmark_agent(
        cases=cases,
        controller=controller,
        retriever=retriever,
        split=args.split,
        max_searches=args.max_searches,
        top_k=args.top_k,
        budget=args.budget,
        output_dir=args.output
    )
