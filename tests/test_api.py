"""
Automated Verification Suite for VLearn Adaptive Learning API
Matches 4 Core Flows from docs/sequence_diagram.jpg
"""

import sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["transcripts_indexed"] >= 700
    print("[PASS] 1. Health check & transcript indexing ok")

def test_slide_question():
    res = client.get("/api/slide-question?deck=d1&page=12")
    assert res.status_code == 200
    data = res.json()
    assert data["deck"] == "d1"
    assert data["page"] == 12
    assert data["prior_page"] == 6
    assert len(data["options"]) >= 2
    assert "T04-049" in data["citations"]
    print("[PASS] 2. Slide question retrieval & bridge concept ok")

def test_misconception_detection():
    # Khối 2: Chẩn đoán quan niệm sai từ câu trả lời tự do
    res = client.post("/api/chat/evaluate", json={
        "student_id": "S0102",
        "deck": "d1",
        "page": 12,
        "answer_text": "Tôi nghĩ 120 từ tiếng Việt bằng đúng 120 token như tiếng Anh",
        "current_level": 1,
        "current_streak": 0,
        "theta": 0.0,
        "item_a": 1.0,
        "item_b": 0.0,
        "item_c": 0.2
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is False
    assert data["diagnostic"] is not None
    assert data["diagnostic"]["is_misconception"] is True
    assert data["diagnostic"]["citation_id"] == "T04-049"
    assert data["should_scaffold"] is True
    print("[PASS] 3. Misconception diagnostic & citation [T04-049] ok")

def test_semantic_misconception_matching():
    # Kiểm tra so khớp ngữ nghĩa Semantic Vector Matching (không dùng từ khóa cứng)
    res = client.post("/api/chat/evaluate", json={
        "student_id": "S0102",
        "deck": "d1",
        "page": 18,
        "answer_text": "Transformer đọc từng từ từ trái qua phải theo thời gian nên các câu dài vẫn bị rơi rụng ngữ cảnh",
        "current_level": 1,
        "current_streak": 0,
        "theta": 0.0,
        "item_a": 1.4,
        "item_b": 0.3,
        "item_c": 0.15
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is False
    assert data["diagnostic"] is not None
    assert data["diagnostic"]["is_misconception"] is True
    assert "Transformer" in data["diagnostic"]["faulty_assumption"] or "tuần tự" in data["diagnostic"]["faulty_assumption"]
    assert data["diagnostic"]["citation_id"] == "T06-086"
    print("[PASS] 3b. Semantic Vector Misconception Matching [T06-086] ok")


def test_adaptive_difficulty():
    # Khối 3: Thăng cấp độ khó khi streak >= 2
    res = client.post("/api/chat/evaluate", json={
        "student_id": "S0102",
        "deck": "d1",
        "page": 12,
        "answer_text": "Phải nhân hệ số 1.35x vì tiếng Việt có dấu thanh tách sub-token",
        "current_level": 1,
        "current_streak": 1,
        "theta": 0.0,
        "item_a": 1.0,
        "item_b": 0.0,
        "item_c": 0.2
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is True
    assert data["new_level"] == 2
    assert data["should_level_up"] is True
    print("[PASS] 4. Adaptive difficulty level up (streak >= 2) ok")

def test_instructor_dashboard_and_override():
    # Khối 4: Dashboard & can thiệp
    res = client.get("/api/analytics/dashboard")
    assert res.status_code == 200
    dash = res.json()
    assert len(dash["kpis"]) >= 4
    assert len(dash["heatmap"]) >= 4
    assert len(dash["roster"]) >= 4
    print("[PASS] 5. Instructor dashboard aggregation ok")

    # Can thiệp
    res_override = client.post("/api/instructor/override", json={
        "student_id": "S0448",
        "original_error": "Cho rằng Attention đọc tuần tự",
        "action": "relabel",
        "notes": "Đã sửa kịch bản: hiểu đúng Self-Attention song song"
    })
    assert res_override.status_code == 200
    ov_data = res_override.json()
def test_static_files():
    res = client.get("/")
    assert res.status_code == 200
    assert "<title>" in res.text
    print("[PASS] 7. Static frontend mount ok")

def test_slide_image():
    res = client.get("/api/slide-image?deck=d1&page=12")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 100000
    print("[PASS] 8. Slide HD image rendering ok")

def test_auth():
    # Login student
    res_s = client.post("/api/auth/login", json={"username": "hocvien", "password": "123"})
    assert res_s.status_code == 200
    data_s = res_s.json()
    assert data_s["success"] is True
    assert data_s["user"]["role"] == "student"

    # Login teacher
    res_t = client.post("/api/auth/login", json={"username": "giangvien", "password": "123"})
    assert res_t.status_code == 200
    data_t = res_t.json()
    assert data_t["success"] is True
    assert data_t["user"]["role"] == "teacher"

    # Register
    res_reg = client.post("/api/auth/register", json={
        "username": "test_student",
        "password": "123",
        "name": "Test Học Viên",
        "role": "student"
    })
    assert res_reg.status_code == 200
    data_reg = res_reg.json()
    assert data_reg["success"] is True
    assert data_reg["user"]["role"] == "student"

    print("[PASS] 9. Role-based authentication & registration ok")

def test_theta_logging_options():
    # 1. Gọi lấy câu hỏi
    q_res = client.get("/api/slide-question?deck=d1&page=6&level=1&student_id=S0102&theta=0.0")
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert len(q_data["options"]) == 4

    # 2. Học viên chọn phương án A (đúng)
    opt_a = q_data["options"][0]
    res_a = client.post("/api/chat/evaluate", json={
        "student_id": "S0102",
        "deck": "d1",
        "page": 6,
        "question_text": q_data["ai_question"],
        "selected_option_id": opt_a["id"],
        "answer_text": opt_a["text"],
        "is_option_correct": opt_a["is_correct"],
        "current_level": 1,
        "current_streak": 0,
        "theta": 0.0
    })
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["is_correct"] is True
    assert data_a["new_theta"] > 0.0

    # 3. Kiểm tra API lấy log
    log_res = client.get("/api/ai-log/thea?limit=10")
    assert log_res.status_code == 200
    logs = log_res.json()["logs"]
    assert len(logs) >= 2
    # Bản ghi cuối cùng phải là answer_evaluated với selected_option_id = "A"
    last_log = logs[-1]
    assert last_log["event"] == "answer_evaluated"
    assert last_log["selected_option_id"] == "A"
    assert last_log["is_correct"] is True
    assert "theta_before" in last_log
    assert "theta_after" in last_log
    assert last_log["theta_after"] > last_log["theta_before"]

    print("[PASS] 10. Theta logging for user-selected options to logbythea.jsonl ok")

def test_student_memory_system():
    # 1. Gửi chat yêu cầu gợi ý/ví dụ
    res = client.post("/api/chat/ask", json={
        "student_id": "S_TEST_MEM",
        "deck": "d1",
        "page": 12,
        "message": "Cho tôi ví dụ thực tế về token tiếng Việt",
        "current_level": 1,
        "history": []
    })
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 10

    # 2. Kiểm tra bộ nhớ STM và LTM qua API endpoint
    mem_res = client.get("/api/student/S_TEST_MEM/memory")
    assert mem_res.status_code == 200
    mem_data = mem_res.json()
    assert mem_data["student_id"] == "S_TEST_MEM"
    assert "stm_conversation_history" in mem_data
    assert len(mem_data["stm_conversation_history"]) >= 2
    assert mem_data["stm_conversation_history"][-2]["role"] == "user"
    assert mem_data["stm_conversation_history"][-1]["role"] == "assistant"
    assert "ltm_profile" in mem_data
    print("[PASS] 11. Student STM Working Memory & LTM Profile System ok")

if __name__ == "__main__":
    test_health()
    test_slide_question()
    test_misconception_detection()
    test_semantic_misconception_matching()
    test_adaptive_difficulty()
    test_instructor_dashboard_and_override()
    test_static_files()
    test_slide_image()
    test_auth()
    test_theta_logging_options()
    test_student_memory_system()
    print("\nSUCCESS: All 11+ verification tests passed perfectly!")

