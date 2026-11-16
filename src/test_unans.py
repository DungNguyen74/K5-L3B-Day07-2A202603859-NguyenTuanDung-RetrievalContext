"""Test unanswerable behavior with GeminiController."""
import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.test_controller import GeminiController
from src.retrievers import DenseRetriever, pack_context

controller = GeminiController()
retriever = DenseRetriever()

q_unans = "According to the 2024 report, what is the personal annual salary and bonus of President Ajay Banga? (Theo báo cáo năm 2024, mức lương và tiền thưởng hàng năm của Chủ tịch Ajay Banga là bao nhiêu?)"

d1 = controller.decide(q_unans, [])
print("Decision 1 (empty):", json.dumps(d1, ensure_ascii=False, indent=2))

hits = retriever.search(d1.get("query", q_unans), top_k=3)
context, ids = pack_context(hits, budget=800)
history = [{"tool": "search", "queries": [d1.get("query", q_unans)], "context": context, "context_ids": ids}]

d2 = controller.decide(q_unans, history)
print("Decision 2 (with unanswerable context):", json.dumps(d2, ensure_ascii=False, indent=2))
