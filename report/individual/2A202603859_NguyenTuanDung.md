# Báo cáo Day 7 — Retrieval & Context Engineering

> **Học viên:** Nguyễn Tuấn Dũng | **MSSV:** 2A202603859 | **Lớp:** K5-L3B  
> **Chủ đề & Corpus:** Báo cáo Thường niên Ngân hàng Thế giới (World Bank Group Annual Reports 2023 & 2024)  
> **Kho dữ liệu kế thừa:** Day 6 Data Ingestion Engineering (`K5-L3-Day06-DataIngestionEngineering`)  

---

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:**
  - *Nguồn tài liệu:* Tải từ kho lưu trữ mở chính thức World Bank Open Knowledge Repository (OKR):
    - *World Bank Annual Report 2024:* Handle `10986/42057` (`data/world_bank_annual_report_2024.pdf`, 46 trang vật lý, 42 trang nội dung).
    - *World Bank Annual Report 2023:* Handle `10986/40219` (`data/world_bank_annual_report_2023.pdf`, 114 trang vật lý, 92 trang nội dung).
  - *Quyền sử dụng:* Giấy phép bản quyền mở Creative Commons Attribution 3.0 IGO (CC-BY 3.0 IGO), cho phép tự do khai thác và xử lý học thuật.
  - *Số trang nội dung:* Tổng cộng **156 trang nội dung hợp lệ** (sau khi loại bỏ trang bìa trắng và mục lục theo quy tắc Day 6).
  - *Số chunk đã index:* **1.047 chunks** (Chiến lược B: *Paragraph-aware chunking* $\le 600$ ký tự, bảo toàn ranh giới đoạn văn và câu) được lưu tại `data/chunks.json`. Ngoài ra có 1.202 chunks của Chiến lược A (Fixed-size 500/50) tại `data/chunks_strategy_a.json` để đối chiếu.
- **Vector store, embedding model, phiên bản và số chiều:**
  - *Vector Store:* `ChromaDB` (phiên bản `1.5.9`), client persistent lưu tại thư mục `C:\Users\reals\Vin\K5-L3-Day06-DataIngestionEngineering\starter\chroma_data`. Khoảng cách vector sử dụng Cosine Similarity (`hnsw:space: cosine`).
  - *Embedding Model:* `all-MiniLM-L6-v2` (Sentence-Transformers / Hugging Face via fastembed / onnxruntime), **384 chiều**. Toàn bộ 1.047 chunks đã được nhúng vector thật (không dùng mock vector).
- **Agent model, cách chạy và phân chia dev/test:**
  - *Agent Model:* Sử dụng mô hình hỗ trợ function/tool calling (Gemini / OpenAI compatible API).
  - *Cách chạy:* Điều phối qua ReAct loop (`run_agent` trong `starter/agentic.py`), có thể gọi tool retrieval nhiều lượt, kiểm soát ngân sách context và tự động định dạng trích dẫn `[chunk-id]`.
  - *Phân chia Dev / Test:* Tổng cộng **24 câu hỏi** (lưu tại `data/cases.json` và `data/questions_all.json`):
    - **Tập Dev (17 câu):** 15 câu có đáp án (`q01` đến `q15`) + 2 câu thiếu bằng chứng (`q_unans_dev_01`, `q_unans_dev_02`).
    - **Tập Test (7 câu):** 5 câu có đáp án (`q16` đến `q20`) + 2 câu thiếu bằng chứng (`q_unans_test_01`, `q_unans_test_02`).
    - 20 câu có đáp án được lưu trong `data/questions.json` để chạy benchmark retrieval độc lập.
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:**
  - *Câu có đáp án:* Có `gold` chứa chính xác `{source_id, page, evidence}` trích xuất nguyên văn từ tài liệu nguồn và nằm trọn vẹn trong chunk. Đánh giá tính chuẩn xác của retrieval qua `Hit@1`, `Evidence Hit@3`, và `Context Evidence Rate`.
  - *Câu thiếu bằng chứng (Unanswerable):* Được thiết kế bám sát chủ đề kinh tế/phát triển của World Bank nhưng thông tin không tồn tại trong hai báo cáo (ví dụ mức đóng góp của ADB vào quỹ năng lượng, GDP Việt Nam dự báo năm 2027, lương thưởng của Chủ tịch, hoạt động tại Nam Cực). Tiêu chí đạt: Agent phải dứt khoát từ chối (`search_and_abstain`), không sinh thông tin giả mạo.

---

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | TF-IDF (Lexical), top-k=3, budget=800 | Phản xạ từ khóa cơ bản không qua embedding | dev | 10/15 (66.7%) | 14/15 (93.3%) | 10/15 (66.7%) | 5.32ms / $0 |
| Phương pháp 2 | [Đang triển khai CP2: Dense ChromaDB MiniLM] | Vector similarity search trên 384d | dev | | | | |
| Phương pháp 3 | [Đang triển khai CP2: Hybrid RRF / Reranker] | Kết hợp Lexical + Dense hoặc Reranker | dev | | | | |
| Cải thiện 1 | | | dev | | | | |
| Cải thiện 2 | | | dev | | | | |
| Cấu hình đã chọn | | | test | | | | |
| Baseline | TF-IDF (Lexical), top-k=3, budget=800 | Đánh giá độc lập trên tập test | test | 4/5 (80.0%) | 4/5 (80.0%) | 4/5 (80.0%) | 6.92ms / $0 |

Một cấu hình có thể đồng thời là phương pháp mới và cải thiện; giải thích rõ. Báo `n/N` và tỷ lệ, ghi đơn vị thời gian/chi phí, so sánh test sau khi chốt. Nêu hai lỗi dev, nguyên nhân, cách thử và lý do chọn cấu hình:

---

## Agent và đánh giá

- Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi:

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:
- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:

---

## Thử thách nâng cao (nếu thực hiện)

- Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản:
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý:
- Cách chia benchmark, schema evidence, model và cấu hình đã chốt trên dev:

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | | | |
| Ảnh, sơ đồ | | | |
| Biểu đồ | | | |
| Multi-hop | | | |
| Text | | | |
| Thiếu bằng chứng | | | |
| **Toàn bộ** | | | |

- Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống:
- Giới hạn, cách tái lập và đường dẫn benchmark:
