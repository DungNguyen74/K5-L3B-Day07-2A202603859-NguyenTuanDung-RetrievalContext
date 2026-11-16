"""Test GeminiController with Gemini 3.5 Flash."""
import json
import os
import re
import sys
from pathlib import Path

# Ensure root dir is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from dotenv import dotenv_values
from google import genai
from google.genai import types

from src.retrievers import DenseRetriever, pack_context


SYSTEM_PROMPT = """Bạn là một Agent điều phối truy xuất và trả lời câu hỏi dựa trên tài liệu (Agentic RAG).
Nhiệm vụ của bạn là đọc câu hỏi của người dùng và lịch sử context đã tìm kiếm để đưa ra quyết định tiếp theo:

Các hành động khả dĩ:
1. "search": Nếu context hiện tại chưa có thông tin hoặc chưa đủ để trả lời câu hỏi, hãy tìm kiếm tiếp.
   Query tìm kiếm phải ngắn gọn, tập trung vào các từ khóa thực thể quan trọng nhất.
   Format JSON:
   {
       "action": "search",
       "query": "<từ khóa tìm kiếm>"
   }

2. "answer": Nếu context hiện tại ĐÃ CÓ ĐẦY ĐỦ BẰNG CHỨNG để trả lời câu hỏi, hãy trả lời ngắn gọn, chính xác dựa trên bằng chứng đó.
   BẮT BUỘC phải trích dẫn ID của chunk chứa bằng chứng dưới dạng [chunk_id] trong câu trả lời VÀ trong mảng "citations".
   Format JSON:
   {
       "action": "answer",
       "answer": "<câu trả lời trực tiếp kèm trích dẫn [chunk_id]>",
       "citations": ["<chunk_id>"]
   }

3. Nếu câu hỏi KHÔNG THỂ trả lời dựa trên tài liệu hoặc thông tin hoàn toàn không có trong context sau khi đã tìm kiếm:
   Hãy trả lời từ chối:
   {
       "action": "answer",
       "answer": "Không đủ bằng chứng để trả lời.",
       "citations": []
   }

QUY TẮC CỐT LÕI (CHỐNG BỊA ĐẶT / HALLUCINATION):
- CHỈ trả lời dựa trên dữ liệu có trong Context được cung cấp. Tuyệt đối KHÔNG suy đoán hay dùng kiến thức bên ngoài nếu không có trong context.
- Chỉ trích dẫn các chunk_id thực sự xuất hiện trong Context và thực sự hỗ trợ thông tin bạn trả lời.
- Luôn trả về DUY NHẤT một khối JSON hợp lệ theo format trên, không thêm bất kỳ văn bản giải thích nào ngoài JSON.
"""


class GeminiController:
    def __init__(self, model_name: str = "gemini-3.5-flash", api_key: str | None = None):
        env_vals = dotenv_values("starter/.env")
        self.api_key = api_key or env_vals.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def decide(self, question: str, history: list[dict]) -> dict:
        # Build prompt
        messages = [
            f"User Question: {question}\n"
        ]
        if not history:
            messages.append("Context hiện tại: [Trống. Chưa có lượt tìm kiếm nào.]")
            messages.append("Hãy đưa ra query tìm kiếm phù hợp nhất để trả lời câu hỏi trên.")
        else:
            latest = history[-1]
            ctx = latest.get("context", "")
            q_list = latest.get("queries", [])
            messages.append(f"Các query đã tìm kiếm trước đó: {q_list}")
            messages.append(f"Context tích lũy hiện có:\n{ctx}\n")
            messages.append("Dựa vào Context trên, hãy quyết định: hoặc 'search' nếu cần tìm thêm từ khóa khác, hoặc 'answer' nếu đã đủ bằng chứng hoặc không có bằng chứng.")

        full_prompt = "\n".join(messages)

        # Call Gemini with JSON mode
        for model in [self.model_name, "gemini-3.8-flash"]:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.0
                    )
                )
                text = response.text.strip()
                data = json.loads(text)
                return data
            except Exception as e:
                # If 503 or transient, fallback or retry
                print(f"Model {model} error: {e}")
                continue
                
        # Fallback if both failed
        return {"action": "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": []}


if __name__ == "__main__":
    controller = GeminiController()
    
    # Test 1: Empty history
    q1 = "At which institution is the World Bank Group Guarantee Platform hosted?"
    d1 = controller.decide(q1, [])
    print("Decision 1 (empty history):", json.dumps(d1, ensure_ascii=False, indent=2))
    
    # Test 2: With context
    retriever = DenseRetriever()
    hits = retriever.search(d1.get("query", q1), top_k=3)
    context, ids = pack_context(hits, budget=800)
    history = [{"tool": "search", "queries": [d1.get("query", q1)], "context": context, "context_ids": ids}]
    
    d2 = controller.decide(q1, history)
    print("Decision 2 (with context):", json.dumps(d2, ensure_ascii=False, indent=2))
