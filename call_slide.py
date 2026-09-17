from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
res = client.post('/api/chat/evaluate', json={
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
print('STATUS', res.status_code)
print('CONTENT BYTES LEN', len(res.content))
print('RAW BYTES REPR:', repr(res.content))
