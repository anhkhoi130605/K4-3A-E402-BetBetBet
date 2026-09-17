"""
Pydantic Schemas for VLearn Adaptive Learning API
Matches Sequence Diagram Data Flow
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Authentication & Role Schemas
class UserLoginRequest(BaseModel):
    username: str = Field(..., example="hocvien")
    password: str = Field(..., example="123")

class UserRegisterRequest(BaseModel):
    username: str = Field(..., example="nguyenvana")
    password: str = Field(..., example="123")
    name: str = Field(..., example="Nguyễn Văn A")
    role: str = Field("student", example="student")  # 'student' | 'teacher'

class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    message: str

# Request: Học viên gửi câu trả lời / tương tác
class StudentAnswerRequest(BaseModel):
    student_id: str = Field("S0102", example="S0102")
    deck: str = Field("d1", example="d1")
    page: int = Field(12, example=12)
    answer_text: str = Field(..., example="Tôi nghĩ 120 từ tiếng Việt bằng 120 token giống tiếng Anh.")
    current_level: int = Field(1, example=1)
    current_streak: int = Field(0, example=0)
    question_text: Optional[str] = None
    selected_option_id: Optional[str] = None
    is_option_correct: Optional[bool] = None

# Request: Giảng viên ghi đè kịch bản / can thiệp (Tính năng 4)
class InstructorOverrideRequest(BaseModel):
    student_id: str = Field(..., example="S0448")
    original_error: str = Field(..., example="Cho rằng Attention đọc tuần tự từng từ")
    action: str = Field(..., example="relabel")
    notes: Optional[str] = Field(None, example="Học viên cần lưu ý lại mô hình Transformer")

# Response: Thẻ Chẩn đoán Lỗi Tư Duy (Tính năng 2 trong Sơ đồ)
class MisconceptionDiagnostic(BaseModel):
    is_misconception: bool = False
    faulty_assumption: Optional[str] = None
    citation_id: Optional[str] = None
    slide_reference: Optional[str] = None
    transcript_excerpt: Optional[str] = None
    socratic_guidance: str = ""

# Response: Đánh giá câu trả lời & Chấm điểm Socratic
class AnswerEvaluationResponse(BaseModel):
    is_correct: bool
    score: int = 100  # Điểm số 0 - 100
    grade: str = "Đạt yêu cầu"  # "Xuất sắc" | "Đạt yêu cầu" | "Cần củng cố"
    feedback: str
    diagnostic: Optional[MisconceptionDiagnostic] = None
    new_streak: int = 0
    new_level: int = 1
    should_level_up: bool = False
    should_scaffold: bool = False
    socratic_hint: str = ""
    review_recommendation: Optional[str] = None  # Cho biết người học cần ôn tập phần nào
    review_slide: Optional[int] = None  # Slide cần mở lại để ôn tập
    reasoning: Optional[Dict[str, Any]] = None  # Chuỗi tư duy ReAct (thought, action, observation)
    guardrail_triggered: bool = False  # Bật nếu phát hiện prompt injection hoặc vi phạm an toàn

# Response: Câu hỏi gợi nhớ theo Slide
class QuestionOption(BaseModel):
    id: str
    text: str
    is_correct: bool
    feedback: str

class SlideQuestionResponse(BaseModel):
    deck: str
    page: int
    level: int = 1
    level_label: Optional[str] = "Level 1 (Cơ bản)"
    is_checkpoint: bool = True
    checkpoint_title: Optional[str] = None
    title: str
    summary: str
    prior_page: Optional[int] = None
    bridge_concept: Optional[str] = None
    bridge_note: Optional[str] = None
    ai_question: str
    options: List[QuestionOption]
    citations: List[str]
    next_checkpoint: Optional[int] = None

# Response: Dashboard Giảng viên (Tính năng 4 trong Sơ đồ)
class KPIMetric(BaseModel):
    title: str
    value: str
    desc: str
    color_class: str

class MisconceptionHeatmapItem(BaseModel):
    topic: str
    affected_students: int
    pct: float
    severity: str

class StudentRosterItem(BaseModel):
    id: str
    level: int
    streak: int
    last_error: str
    status: str
    flagged: bool

class InstructorDashboardResponse(BaseModel):
    kpis: List[KPIMetric]
    heatmap: List[MisconceptionHeatmapItem]
    roster: List[StudentRosterItem]
    active_overrides_count: int

# Request & Response: Chat trao đổi Socratic với AI Companion
class StudentChatRequest(BaseModel):
    student_id: str = Field("S0102", example="S0102")
    deck: str = Field("d1", example="d1")
    page: int = Field(12, example=12)
    message: str = Field(..., example="Cho tôi một ví dụ thực tế trực quan")
    current_level: int = Field(1, example=1)
    question_context: Optional[str] = None

class StudentChatResponse(BaseModel):
    reply: str
    intent: str  # "example" | "hint" | "concept" | "general"
    citations: List[str] = []

