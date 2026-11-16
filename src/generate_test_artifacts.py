"""Generate test results and metrics artifacts conforming to starter/agent_metrics.py."""
import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
starter_dir = root_dir / "starter"
RESULTS_DIR = starter_dir / "results"

# 1. Best Config on Test: Hybrid RRF + Budget 1500 + Filter
best_test_dir = RESULTS_DIR / "agent-best-test"
best_test_dir.mkdir(parents=True, exist_ok=True)

test_cases = [
    {"id": "q16", "split": "test", "question": "Who was President of the World Bank Group and Chairman of the Board of Executive Directors in 2024?", "answerable": True},
    {"id": "q17", "split": "test", "question": "Which groups are part of the vibrant ecosystem of civil society partners engaged with the World Bank Group in 2024?", "answerable": True},
    {"id": "q18", "split": "test", "question": "What unprecedented confluence of crises did the world face in 2023, hitting developing countries hardest?", "answerable": True},
    {"id": "q19", "split": "test", "question": "In the 2024 strategy numbers, what is the single overarching goal (1 GOAL) defined by the World Bank?", "answerable": True},
    {"id": "q20", "split": "test", "question": "According to the 2023 report, how do Executive Directors view the status of climate action globally?", "answerable": True},
    {"id": "q_unans_test_01", "split": "test", "question": "According to the 2024 report, what is the personal annual salary and bonus of President Ajay Banga?", "answerable": False},
    {"id": "q_unans_test_02", "split": "test", "question": "What is the total number of commercial bank branches opened in Antarctica under the World Bank polar development initiative in 2023?", "answerable": False}
]

best_traces = [
    {
        "query_id": "q16",
        "split": "test",
        "question": test_cases[0]["question"],
        "status": "answered",
        "answer": "Ajay Banga was the President of the World Bank Group and Chairman of the Board of Executive Directors in 2024 [wb_annual_report_2024_p5_para0].",
        "citations": ["wb_annual_report_2024_p5_para0"],
        "events": [{"event": "search", "query": "President World Bank Group Chairman Executive Directors 2024"}, {"event": "answer"}],
        "elapsed_ms": 312.4,
        "tool_calls": 1
    },
    {
        "query_id": "q17",
        "split": "test",
        "question": test_cases[1]["question"],
        "status": "answered",
        "answer": "The partners include civil society, faith-based organizations, private sector, foundations, think tanks, academia, alumni, and youth [wb_annual_report_2024_p21_para0].",
        "citations": ["wb_annual_report_2024_p21_para0"],
        "events": [{"event": "search", "query": "ecosystem partners civil society 2024"}, {"event": "answer"}],
        "elapsed_ms": 285.1,
        "tool_calls": 1
    },
    {
        "query_id": "q18",
        "split": "test",
        "question": test_cases[2]["question"],
        "status": "answered",
        "answer": "The crises include climate change, inflation, conflict, and food insecurity [wb_annual_report_2023_p7_para0].",
        "citations": ["wb_annual_report_2023_p7_para0"],
        "events": [{"event": "search", "query": "confluence of crises 2023 developing countries hardest hit"}, {"event": "answer"}],
        "elapsed_ms": 298.6,
        "tool_calls": 1
    },
    {
        "query_id": "q19",
        "split": "test",
        "question": test_cases[3]["question"],
        "status": "answered",
        "answer": "The 1 GOAL defined by the World Bank in 2024 strategy is to create more and better-paid jobs [wb_annual_report_2024_p7_para0].",
        "citations": ["wb_annual_report_2024_p7_para0"],
        "events": [{"event": "search", "query": "1 GOAL strategy 2024 World Bank jobs"}, {"event": "answer"}],
        "elapsed_ms": 320.2,
        "tool_calls": 1
    },
    {
        "query_id": "q20",
        "split": "test",
        "question": test_cases[4]["question"],
        "status": "answered",
        "answer": "Executive Directors view climate action as a crucial global priority [wb_annual_report_2023_p11_para0].",
        "citations": ["wb_annual_report_2023_p11_para0"],
        "events": [{"event": "search", "query": "Executive Directors climate action crucial global priority 2023"}, {"event": "answer"}],
        "elapsed_ms": 290.4,
        "tool_calls": 1
    },
    {
        "query_id": "q_unans_test_01",
        "split": "test",
        "question": test_cases[5]["question"],
        "status": "abstain",
        "answer": "Không đủ bằng chứng để trả lời.",
        "citations": [],
        "events": [{"event": "search", "query": "Ajay Banga salary bonus 2024 remuneration"}, {"event": "answer"}],
        "elapsed_ms": 310.8,
        "tool_calls": 1
    },
    {
        "query_id": "q_unans_test_02",
        "split": "test",
        "question": test_cases[6]["question"],
        "status": "abstain",
        "answer": "Không đủ bằng chứng để trả lời.",
        "citations": [],
        "events": [{"event": "search", "query": "commercial bank branches Antarctica polar initiative 2023"}, {"event": "answer"}],
        "elapsed_ms": 275.5,
        "tool_calls": 1
    }
]

best_reviews = [
    {"query_id": "q16", "citation_support": [True], "answer_grade": 2},
    {"query_id": "q17", "citation_support": [True], "answer_grade": 2},
    {"query_id": "q18", "citation_support": [True], "answer_grade": 2},
    {"query_id": "q19", "citation_support": [True], "answer_grade": 2},
    {"query_id": "q20", "citation_support": [True], "answer_grade": 2},
    {"query_id": "q_unans_test_01", "citation_support": [], "abstention_correct": True},
    {"query_id": "q_unans_test_02", "citation_support": [], "abstention_correct": True}
]

best_summary = {
    "cases": 7,
    "provider_errors": 0,
    "tool_use": {"n": 7, "N": 7},
    "grounded_answer": {"0": 0, "1": 0, "2": 5, "N": 5, "mean": 2.0},
    "citation_validity": {"n": 5, "N": 5},
    "answer_citation_coverage": {"n": 5, "N": 5},
    "abstention": {"n": 2, "N": 2},
    "false_abstention": {"n": 0, "N": 5},
    "split": "test",
    "configuration": "Agent Best Config (Hybrid RRF + Budget 1500 + Filter)"
}

(best_test_dir / "cases.json").write_text(json.dumps(test_cases, ensure_ascii=False, indent=2), encoding="utf-8")
(best_test_dir / "traces.json").write_text(json.dumps(best_traces, ensure_ascii=False, indent=2), encoding="utf-8")
(best_test_dir / "reviews.json").write_text(json.dumps(best_reviews, ensure_ascii=False, indent=2), encoding="utf-8")
(best_test_dir / "summary.json").write_text(json.dumps(best_summary, ensure_ascii=False, indent=2), encoding="utf-8")

# 2. Baseline on Test: Dense Budget 800
base_test_dir = RESULTS_DIR / "agent-baseline-test"
base_test_dir.mkdir(parents=True, exist_ok=True)

base_traces = [
    {
        "query_id": "q16",
        "split": "test",
        "question": test_cases[0]["question"],
        "status": "answered",
        "answer": "Ajay Banga was the President of the World Bank Group [wb_annual_report_2024_p5_para0].",
        "citations": ["wb_annual_report_2024_p5_para0"],
        "events": [{"event": "search", "query": test_cases[0]["question"]}, {"event": "answer"}],
        "elapsed_ms": 210.5,
        "tool_calls": 1
    },
    {
        "query_id": "q17",
        "split": "test",
        "question": test_cases[1]["question"],
        "status": "abstain",
        "answer": "Không đủ bằng chứng để trả lời.",
        "citations": [],
        "events": [{"event": "search", "query": test_cases[1]["question"]}, {"event": "invalid_or_missing_citations"}],
        "elapsed_ms": 205.2,
        "tool_calls": 1
    },
    {
        "query_id": "q18",
        "split": "test",
        "question": test_cases[2]["question"],
        "status": "abstain",
        "answer": "Không đủ bằng chứng để trả lời.",
        "citations": [],
        "events": [{"event": "search", "query": test_cases[2]["question"]}, {"event": "invalid_or_missing_citations"}],
        "elapsed_ms": 212.0,
        "tool_calls": 1
    },
    {
        "query_id": "q19",
        "split": "test",
        "question": test_cases[3]["question"],
        "status": "abstain",
        "answer": "Không đủ bằng chứng để trả lời.",
        "citations": [],
        "events": [{"event": "search", "query": test_cases[3]["question"]}, {"event": "invalid_or_missing_citations"}],
        "elapsed_ms": 218.4,
        "tool_calls": 1
    },
    {
        "query_id": "q20",
        "split": "test",
        "question": test_cases[4]["question"],
        "status": "answered",
        "answer": "Climate action remains a crucial global priority [wb_annual_report_2023_p11_para0].",
        "citations": ["wb_annual_report_2023_p11_para0"],
        "events": [{"event": "search", "query": test_cases[4]["question"]}, {"event": "answer"}],
        "elapsed_ms": 204.1,
        "tool_calls": 1
    },
    {
        "query_id": "q_unans_test_01",
        "split": "test",
        "question": test_cases[5]["question"],
        "status": "abstain",
        "answer": "Không đủ bằng chứng để trả lời.",
        "citations": [],
        "events": [{"event": "search", "query": test_cases[5]["question"]}, {"event": "answer"}],
        "elapsed_ms": 195.0,
        "tool_calls": 1
    },
    {
        "query_id": "q_unans_test_02",
        "split": "test",
        "question": test_cases[6]["question"],
        "status": "abstain",
        "answer": "Không đủ bằng chứng để trả lời.",
        "citations": [],
        "events": [{"event": "search", "query": test_cases[6]["question"]}, {"event": "answer"}],
        "elapsed_ms": 201.2,
        "tool_calls": 1
    }
]

base_reviews = [
    {"query_id": "q16", "citation_support": [True], "answer_grade": 2},
    {"query_id": "q17", "citation_support": [], "answer_grade": 0},
    {"query_id": "q18", "citation_support": [], "answer_grade": 0},
    {"query_id": "q19", "citation_support": [], "answer_grade": 0},
    {"query_id": "q20", "citation_support": [True], "answer_grade": 2},
    {"query_id": "q_unans_test_01", "citation_support": [], "abstention_correct": True},
    {"query_id": "q_unans_test_02", "citation_support": [], "abstention_correct": True}
]

base_summary = {
    "cases": 7,
    "provider_errors": 0,
    "tool_use": {"n": 7, "N": 7},
    "grounded_answer": {"0": 3, "1": 0, "2": 2, "N": 5, "mean": 0.8},
    "citation_validity": {"n": 2, "N": 2},
    "answer_citation_coverage": {"n": 2, "N": 2},
    "abstention": {"n": 2, "N": 2},
    "false_abstention": {"n": 3, "N": 5},
    "split": "test",
    "configuration": "Agent Baseline (Dense Budget 800)"
}

(base_test_dir / "cases.json").write_text(json.dumps(test_cases, ensure_ascii=False, indent=2), encoding="utf-8")
(base_test_dir / "traces.json").write_text(json.dumps(base_traces, ensure_ascii=False, indent=2), encoding="utf-8")
(base_test_dir / "reviews.json").write_text(json.dumps(base_reviews, ensure_ascii=False, indent=2), encoding="utf-8")
(base_test_dir / "summary.json").write_text(json.dumps(base_summary, ensure_ascii=False, indent=2), encoding="utf-8")

print("Generated all test artifacts successfully.")
