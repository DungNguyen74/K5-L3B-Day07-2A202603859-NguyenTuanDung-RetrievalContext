"""Generate cases.json and questions_all.json for Day 7 Benchmark.
Complies with Day 7 BENCHMARK.md and RUBRIC.md:
- Dev: 15 answerable + 2 unanswerable = 17 cases
- Test: 5 answerable + 2 unanswerable = 7 cases
- Total: 24 cases minimum
"""
import json
from pathlib import Path

DATA_DIR = Path("data")


def main():
    questions_file = DATA_DIR / "questions.json"
    answerable_questions = json.loads(questions_file.read_text(encoding="utf-8"))
    
    # 4 Unanswerable questions near the topic (World Bank Annual Reports)
    unanswerable_cases = [
        {
            "id": "q_unans_dev_01",
            "split": "dev",
            "question": "What was the exact financial contribution of the Asian Development Bank (ADB) to the World Bank's 2024 Clean Energy Fund? (Đóng góp tài chính chính xác của Ngân hàng Phát triển Châu Á (ADB) vào Quỹ Năng lượng Sạch 2024 của Ngân hàng Thế giới là bao nhiêu?)",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "Báo cáo Thường niên WB 2024 và 2023 không ghi nhận bất kỳ quỹ nào có tên '2024 Clean Energy Fund' có phần đóng góp tài chính riêng lẻ của ADB (chỉ có báo cáo hoạt động chung của các cơ quan WBG)."
        },
        {
            "id": "q_unans_dev_02",
            "split": "dev",
            "question": "What is the projected GDP growth rate of Vietnam for the fiscal year 2027 reported in the 2023 Annual Report? (Dự báo tốc độ tăng trưởng GDP của Việt Nam cho năm tài chính 2027 được báo cáo trong Báo cáo Thường niên 2023 là bao nhiêu?)",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "Báo cáo Thường niên 2023 chỉ công bố số liệu tổng kết đến năm tài khóa 2023 và một số dự báo ngắn hạn đến 2024-2025 cho các khu vực kinh tế lớn, hoàn toàn không có dự báo số liệu GDP cụ thể cho Việt Nam đến năm 2027."
        },
        {
            "id": "q_unans_test_01",
            "split": "test",
            "question": "According to the 2024 report, what is the personal annual salary and bonus of President Ajay Banga? (Theo báo cáo năm 2024, mức lương và tiền thưởng hàng năm của Chủ tịch Ajay Banga là bao nhiêu?)",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "Báo cáo Thường niên World Bank 2024 chỉ trình bày các cam kết tài trợ, chương trình phát triển và thư ngỏ của Chủ tịch, không công bố thông tin thu nhập cá nhân hay gói lương thưởng của Ban Giám đốc."
        },
        {
            "id": "q_unans_test_02",
            "split": "test",
            "question": "What is the total number of commercial bank branches opened in Antarctica under the World Bank polar development initiative in 2023? (Tổng số chi nhánh ngân hàng thương mại được mở tại Nam Cực theo sáng kiến phát triển vùng cực của World Bank năm 2023 là bao nhiêu?)",
            "answerable": False,
            "expected_behavior": "search_and_abstain",
            "absence_reason": "World Bank Group không có bất kỳ sáng kiến hay dự án phát triển nào tại Nam Cực (Antarctica); hai báo cáo tài chính 2023 & 2024 hoàn toàn không có dữ liệu về vùng cực này."
        }
    ]
    
    # Build cases.json for agent_metrics.py
    cases = []
    for q in answerable_questions:
        cases.append({
            "id": q["id"],
            "split": q["split"],
            "question": q["question"],
            "answerable": True,
            "expected_behavior": "search_and_answer",
            "expected_answer": q["expected_answer"]
        })
    cases.extend(unanswerable_cases)
    
    cases_file = DATA_DIR / "cases.json"
    cases_file.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(cases)} benchmark cases in {cases_file}:")
    dev_cases = [c for c in cases if c["split"] == "dev"]
    test_cases = [c for c in cases if c["split"] == "test"]
    print(f"  - Dev: {len(dev_cases)} cases ({sum(1 for c in dev_cases if c['answerable'])} answerable, {sum(1 for c in dev_cases if not c['answerable'])} unanswerable)")
    print(f"  - Test: {len(test_cases)} cases ({sum(1 for c in test_cases if c['answerable'])} answerable, {sum(1 for c in test_cases if not c['answerable'])} unanswerable)")
    
    # Build questions_all.json containing full details for agent execution
    questions_all = []
    for q in answerable_questions:
        item = dict(q)
        item["answerable"] = True
        item["expected_behavior"] = "search_and_answer"
        questions_all.append(item)
    for u in unanswerable_cases:
        item = dict(u)
        item["gold"] = []
        item["expected_answer"] = "Không đủ bằng chứng để trả lời."
        questions_all.append(item)
        
    (DATA_DIR / "questions_all.json").write_text(json.dumps(questions_all, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved complete questions dataset to data/questions_all.json")


if __name__ == "__main__":
    main()
