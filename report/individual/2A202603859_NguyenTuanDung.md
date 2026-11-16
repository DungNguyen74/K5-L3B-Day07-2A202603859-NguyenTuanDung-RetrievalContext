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
| **Baseline (P1)** | TF-IDF Lexical, top-k=3, budget=800 | Khớp từ khóa chuẩn hóa NFC | dev | 10/15 (66.7%) | 14/15 (93.3%) | 10/15 (66.7%) | 4.64ms / $0 |
| **Phương pháp 2 (P2)** | Dense ChromaDB (MiniLM-384d), top-k=3, budget=800 | Truy xuất ngữ nghĩa cosine space | dev | 8/15 (53.3%) | 13/15 (86.7%) | 8/15 (53.3%) | 275.71ms / $0 |
| **Phương pháp 3 (P3)** | Hybrid RRF (Dense + TF-IDF), k=60, top-k=3, budget=800 | Hợp nhất thứ hạng Reciprocal Rank Fusion | dev | 9/15 (60.0%) | 14/15 (93.3%) | 9/15 (60.0%) | 288.44ms / $0 |
| Cải thiện 1 | [Triển khai CP4: Budget 1500 chars] | Mở rộng budget tránh cắt mất rank 2-3 | dev | | | | |
| Cải thiện 2 | [Triển khai CP4: Hybrid + Metadata Filter] | Lọc metadata chỉ định năm + RRF | dev | | | | |
| Cấu hình đã chọn | | | test | | | | |
| **Baseline (P1)** | TF-IDF Lexical, top-k=3, budget=800 | Đánh giá độc lập trên tập test | test | 4/5 (80.0%) | 4/5 (80.0%) | 4/5 (80.0%) | 4.36ms / $0 |
| **Phương pháp 2 (P2)** | Dense ChromaDB (MiniLM-384d), top-k=3, budget=800 | Đánh giá độc lập trên tập test | test | 2/5 (40.0%) | 2/5 (40.0%) | 2/5 (40.0%) | 206.83ms / $0 |
| **Phương pháp 3 (P3)** | Hybrid RRF (Dense + TF-IDF), k=60, top-k=3, budget=800 | Đánh giá độc lập trên tập test | test | 3/5 (60.0%) | 4/5 (80.0%) | 3/5 (60.0%) | 266.91ms / $0 |

### Mô tả 3 Phương pháp Retrieval đã triển khai (Checkpoint 2)
1. **Phương pháp 1 — TF-IDF Lexical Retrieval (Baseline):** Xây dựng bảng tần suất từ và nghịch đảo tần suất văn bản (TF-IDF) trên 1.047 chunks theo chuẩn hóa Unicode NFC. Truy vấn dựa trên độ tương đồng Cosine của vector thưa (sparse vector). Tốc độ cực nhanh (~4.64ms), nhận diện chính xác các từ khóa số liệu kỹ thuật, nhưng hạn chế khi câu hỏi sử dụng từ đồng nghĩa.
2. **Phương pháp 2 — Dense Retrieval (ChromaDB + all-MiniLM-L6-v2):** Kết nối trực tiếp cơ sở dữ liệu vector từ Day 6 với 1.047 chunks đã nhúng vector 384 chiều. Sử dụng hàm nhúng `all-MiniLM-L6-v2` để sinh vector cho query câu hỏi và truy vấn Cosine similarity trong không gian HNSW. Bắt trúng ngữ nghĩa tổng quát và các cách diễn đạt lại (paraphrasing).
3. **Phương pháp 3 — Hybrid Retrieval (Dense + Lexical kết hợp RRF):** Khởi chạy song song cả Dense Retriever và Lexical Retriever để lấy ra danh sách ứng viên (candidate pool $N=15$). Hợp nhất thứ hạng bằng thuật toán Reciprocal Rank Fusion:
   $$RRF(d) = \frac{1}{60 + rank_{dense}(d)} + \frac{1}{60 + rank_{lexical}(d)}$$
   Phương pháp này bù đắp điểm yếu của cả hai phía: vừa giữ được từ khóa độc nhất (tên riêng, số liệu) nhờ Lexical, vừa nắm bắt được ngữ nghĩa tổng quan nhờ Dense. Kết quả: Evidence Hit@3 đạt **14/15 (93.3%)** trên tập Dev và **4/5 (80.0%)** trên tập Test.

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
