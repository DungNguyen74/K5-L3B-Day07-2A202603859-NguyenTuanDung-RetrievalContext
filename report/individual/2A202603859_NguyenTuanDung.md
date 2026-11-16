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
| **Cải thiện 1** | Dense ChromaDB, top-k=3, budget=1500 | Nâng context budget 800 $\rightarrow$ 1500 chars tránh cắt cụt | dev | 8/15 (53.3%) | 13/15 (86.7%) | 11/15 (73.3%) | 265.12ms / $0 |
| **Cải thiện 2 (Được chọn)** | Hybrid RRF + Filter + Budget 1500 | RRF hợp nhất + Lọc metadata năm + Budget 1500 | dev | 9/15 (60.0%) | **14/15 (93.3%)** | **14/15 (93.3%)** | 282.40ms / $0 |
| Cấu hình đã chọn | Hybrid RRF + Filter + Budget 1500 | Đánh giá độc lập trên tập test | test | [CP5] | [CP5] | [CP5] | [CP5] |
| **Baseline (P1)** | TF-IDF Lexical, top-k=3, budget=800 | Đánh giá độc lập trên tập test | test | 4/5 (80.0%) | 4/5 (80.0%) | 4/5 (80.0%) | 4.36ms / $0 |
| **Phương pháp 2 (P2)** | Dense ChromaDB (MiniLM-384d), top-k=3, budget=800 | Đánh giá độc lập trên tập test | test | 2/5 (40.0%) | 2/5 (40.0%) | 2/5 (40.0%) | 206.83ms / $0 |
| **Phương pháp 3 (P3)** | Hybrid RRF (Dense + TF-IDF), k=60, top-k=3, budget=800 | Đánh giá độc lập trên tập test | test | 3/5 (60.0%) | 4/5 (80.0%) | 3/5 (60.0%) | 266.91ms / $0 |

### Mô tả 3 Phương pháp Retrieval đã triển khai (Checkpoint 2)
1. **Phương pháp 1 — TF-IDF Lexical Retrieval (Baseline):** Xây dựng bảng tần suất từ và nghịch đảo tần suất văn bản (TF-IDF) trên 1.047 chunks theo chuẩn hóa Unicode NFC. Truy vấn dựa trên độ tương đồng Cosine của vector thưa (sparse vector). Tốc độ cực nhanh (~4.64ms), nhận diện chính xác các từ khóa số liệu kỹ thuật, nhưng hạn chế khi câu hỏi sử dụng từ đồng nghĩa.
2. **Phương pháp 2 — Dense Retrieval (ChromaDB + all-MiniLM-L6-v2):** Kết nối trực tiếp cơ sở dữ liệu vector từ Day 6 với 1.047 chunks đã nhúng vector 384 chiều. Sử dụng hàm nhúng `all-MiniLM-L6-v2` để sinh vector cho query câu hỏi và truy vấn Cosine similarity trong không gian HNSW. Bắt trúng ngữ nghĩa tổng quát và các cách diễn đạt lại (paraphrasing).
3. **Phương pháp 3 — Hybrid Retrieval (Dense + Lexical kết hợp RRF):** Khởi chạy song song cả Dense Retriever và Lexical Retriever để lấy ra danh sách ứng viên (candidate pool $N=15$). Hợp nhất thứ hạng bằng thuật toán Reciprocal Rank Fusion:
   $$RRF(d) = \frac{1}{60 + rank_{dense}(d)} + \frac{1}{60 + rank_{lexical}(d)}$$
   Phương pháp này bù đắp điểm yếu của cả hai phía: vừa giữ được từ khóa độc nhất (tên riêng, số liệu) nhờ Lexical, vừa nắm bắt được ngữ nghĩa tổng quan nhờ Dense. Kết quả: Evidence Hit@3 đạt **14/15 (93.3%)** trên tập Dev và **4/5 (80.0%)** trên tập Test.

### Phân tích 2 lỗi trên Dev, Thử nghiệm cải thiện và Lý do chọn cấu hình (Checkpoint 4)

#### 1. Phân tích 2 ca lỗi tiêu biểu trên tập Dev:
- **Lỗi 1 — Câu `q09` (Dev, Báo cáo 2023):**
  - *Câu hỏi:* *"By what percentage can low-carbon development strategies reduce emissions without harming growth?"*
  - *Bằng chứng chuẩn (Gold Target):* Trang 14: *"Collectively, the low-carbon development strategies from these reports can reduce emissions by 70 percent, without harming growth."*
  - *Nguyên nhân thất bại ở Dense Retrieval:* Mô hình embedding 384 chiều bị hiện tượng trôi ngữ nghĩa (*semantic drift*), gán độ tương đồng cao cho các đoạn thảo luận chung về biến đổi khí hậu, làm chìm mất con số định lượng *"70 percent"*.
  - *Biện pháp cải thiện:* Cấu hình Hybrid RRF kết hợp tín hiệu Lexical TF-IDF đã nhận diện ngay từ khóa hiếm `"70 percent"` và đưa chunk trang 14 lên Top-1.
- **Lỗi 2 — Câu `q07` (Dev, Báo cáo 2024):**
  - *Câu hỏi:* *"What health crisis causes high rates of premature death and disability in Pacific Island countries?"*
  - *Bằng chứng chuẩn (Gold Target):* Trang 12: *"Pacific Island countries face some of the world’s highest rates of premature death and disability from non-communicable disease, including diabetes..."*
  - *Nguyên nhân thất bại ở Baseline Budget 800 (Context Cutoff):* Chunk Rank 1 (nói về y tế chung) dài 540 ký tự. Chunk Rank 2 chứa đúng bằng chứng dài 480 ký tự. Tổng ký tự $540 + 480 = 1.020 > 800$ ký tự $\rightarrow$ Chunk Rank 2 bị hàm `pack_context` cắt bỏ hoàn toàn! Dẫn tới `Evidence Hit@3 = True` nhưng `Context Hit = False` (Agent buộc phải từ chối do thiếu bằng chứng trong context).
  - *Biện pháp cải thiện:* Nâng context budget lên 1.500 ký tự (Cải thiện 1 & 2) giúp cả 2 chunk cùng nằm trọn vẹn trong context, đưa Context Hit chuyển từ False sang True!

#### 2. Tiêu chí chọn Cấu hình Tối ưu (Đóng băng trước khi chạy Test):
- **Cấu hình được lựa chọn:** **Cải thiện 2 — Hybrid RRF (Dense + TF-IDF) kết hợp Metadata Filtering và Ngân sách Context 1.500 ký tự**.
- **Lý do lựa chọn:**
  1. Đạt **Context Evidence Rate cao nhất trên Dev: 14/15 (93.3%)**, xóa bỏ triệt để hiện tượng cắt cụt context.
  2. Đạt **Evidence Hit@3 cao nhất trên Dev: 14/15 (93.3%)**, cân bằng giữa bắt từ khóa chính xác và nắm bắt ngữ nghĩa.
  3. Độ trễ truy vấn trung bình chấp nhận được (282.40ms), chi phí 0.00 USD.

---

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi:**
  - *Tool sử dụng:* Tool truy xuất `search(query, top_k, filters)` kết nối trực tiếp kho vector ChromaDB và bộ TF-IDF/Hybrid.
  - *Số lượt gọi:* Giới hạn tối đa `max_searches = 3` lượt/câu hỏi.
  - *Điều kiện dừng:* Vòng lặp ReAct dừng khi Controller phát hiện context đã đủ bằng chứng và kích hoạt action `answer`, hoặc dừng khi chạm ngưỡng `max_searches` mà chưa đủ bằng chứng $\rightarrow$ tự động kích hoạt cơ chế an toàn `abstain`.
  - *Cách chọn context:* Cơ chế đóng gói `pack_context` với cơ chế khử trùng lặp (`deduplication`), gán nhãn nguồn rõ ràng `[chunk_id | source | page]` và kiểm soát theo ngân sách ký tự (`budget = 800` ký tự ở Baseline, mở rộng `1.500` ký tự ở cấu hình cải thiện).
  - *Xử lý lỗi & Hallucination:* Tự động retry với exponential backoff khi gặp lỗi mạng/quota. Kiểm tra hậu kỳ nghiêm ngặt (`post-validation`): nếu câu trả lời trích dẫn chunk không có trong context hoặc không có citation $\rightarrow$ chuẩn hóa về `abstain` thay vì để model bịa đặt.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| **Agent Dense Baseline (Dev)** | 16/17 (94.1%) | 1.12 lượt/câu | 0: 7 \| 1: 0 \| 2: 8 (TB: 1.07/2.0) | 8/8 (100%) | 8/8 (100%) | 2/2 (100%) | 7/15 (46.7%) |

#### Đánh giá chi tiết các câu hỏi trọng yếu (Audited Key Cases):

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| **q01** | Có đáp án (Trực tiếp) | Search: `"World Bank Group Guarantee Platform hosted"` $\rightarrow$ Top-1: `wb_annual_report_2024_p4_para0` (Trang 4) | *"The World Bank Group Guarantee Platform is hosted at MIGA [wb_annual_report_2024_p4_para0]."* | **Điểm 2**: Trả lời chính xác, đủ ý, citation ID chuẩn và thực sự chứng minh câu trả lời. |
| **q12** | Có đáp án (Đa điều kiện) | Search: `"World Bank Group strategy 3 Pillars 2024"` $\rightarrow$ Top-1: `wb_annual_report_2024_p7_para0` (Trang 7) | *"The 3 Pillars are: Invest in foundational infrastructure, Support business-enabling environment, and Mobilize private capital [wb_annual_report_2024_p7_para0]."* | **Điểm 2**: Nêu đúng cả 3 trụ cột chiến lược năm 2024, đúng metadata năm. |
| **q_unans_dev_01** | Thiếu bằng chứng (Unanswerable) | Search: `"ADB Asian Development Bank contribution Clean Energy Fund 2024"` $\rightarrow$ Không có thông tin liên quan | *"Không đủ bằng chứng để trả lời."* (Citations: `[]`) | **Abstention đúng**: Agent nhận thức được thông tin không tồn tại và dứt khoát từ chối, không suy đoán. |

- **Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:**
  - File traces: [`starter/results/agent-dense-dev/traces.json`](file:///c:/Users/reals/Vin/K5-L3B-Day07-2A202603859-NguyenTuanDung-RetrievalContext/starter/results/agent-dense-dev/traces.json)
  - File reviews audit: [`starter/results/agent-dense-dev/reviews.json`](file:///c:/Users/reals/Vin/K5-L3B-Day07-2A202603859-NguyenTuanDung-RetrievalContext/starter/results/agent-dense-dev/reviews.json)
  - File metrics summary: [`starter/results/agent-dense-dev/summary.json`](file:///c:/Users/reals/Vin/K5-L3B-Day07-2A202603859-NguyenTuanDung-RetrievalContext/starter/results/agent-dense-dev/summary.json)
  - Lệnh chạy: `python src/run_checkpoint3.py`
  - Thời gian trung bình: ~1.2s/câu hỏi | Chi phí: 0.00 USD (Gemini Free Tier API + Local Vector Index).

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
