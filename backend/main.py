"""
VLearn Adaptive AI Tutor - FastAPI Backend
Implements the 4 core sequences from docs/sequence_diagram.jpg:
1. Gợi nhớ lý thuyết kết nối thực hành (Bridge theory to practice)
2. Chẩn đoán quan niệm sai & Hướng dẫn Socratic (Misconception Diagnostic & Socratic Scaffolding)
3. Điều phối độ khó thích ứng (Adaptive Difficulty & Streak tracking)
4. Dashboard & Can thiệp giảng viên (Instructor Heatmap & Manual Override)
"""
import math
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import BASE_DIR, ROOT_DATA_DIR, DATA_DIR, SLIDES_DIR, MOCKUP_DIR
from backend.models.schemas import (
    UserLoginRequest,
    UserRegisterRequest,
    AuthResponse,
    StudentAnswerRequest,
    AnswerEvaluationResponse,
    SlideQuestionResponse,
    InstructorDashboardResponse,
    InstructorOverrideRequest,
    StudentChatRequest,
    StudentChatResponse
)
from backend.services.rag_service import rag_service
from backend.services.pedagogy_service import pedagogy_service
from backend.services.analytics_service import analytics_service
from backend.services.auth_service import auth_service
from backend.services.openAI_service import openrouter_service

app = FastAPI(
    title="VLearn Adaptive Learning API",
    description="Backend API for Hackathon Track D: VLearn Adaptive AI Tutor",
    version="1.0.0"
)

# Enable CORS for local testing & multi-port dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chống browser cache cho development để luôn nạp JS/CSS mới nhất
@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# API Endpoints
@app.get("/api/health")
async def health_check():
    """Kiểm tra tình trạng sẵn sàng của hệ thống"""
    return {
        "status": "healthy",
        "app": "VLearn Adaptive AI Tutor",
        "version": "1.0.0",
        "transcripts_indexed": len(rag_service.transcripts),
        "active_students": len(analytics_service.students)
    }

# ================= AUTHENTICATION & ROLE MANAGEMENT =================
@app.post("/api/auth/login", response_model=AuthResponse)
async def login(req: UserLoginRequest):
    """Đăng nhập phân quyền Học sinh hoặc Giáo viên"""
    res = auth_service.login(req.username, req.password)
    return AuthResponse(**res)

@app.post("/api/auth/register", response_model=AuthResponse)
async def register(req: UserRegisterRequest):
    """Đăng ký tài khoản mới theo vai trò (student / teacher)"""
    res = auth_service.register(req.username, req.password, req.name, req.role)
    return AuthResponse(**res)

@app.get("/api/auth/me")
async def get_current_user(token: str = Query(...)):
    """Lấy thông tin tài khoản hiện tại từ token"""
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
    return user

@app.post("/api/settings/openrouter-key")
async def configure_openrouter(payload: Dict[str, str]):
    """Cấu hình OpenRouter API key cho GPT-4o-mini"""
    key = payload.get("key", "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Key không được để trống.")
    openrouter_service.set_key(key)
    return {
        "success": True,
        "message": "Đã cấu hình OpenRouter API key thành công. Model GPT-4o-mini sẵn sàng hoạt động!",
        "model": openrouter_service.model
    }

@app.get("/api/deck-info")
async def get_deck_info(deck: str = Query("d1")):
    """Trả về số lượng trang và thông tin cơ bản của bộ slide"""
    pdf_name = "d1-slide-hackathon.pdf" if deck == "d1" else "d2-slide-hackathon.pdf"
    pdf_path = SLIDES_DIR / pdf_name
    total_pages = 29
    if pdf_path.exists():
        try:
            import pymupdf
            doc = pymupdf.open(str(pdf_path))
            total_pages = len(doc)
        except Exception:
            pass
    return {
        "deck": deck,
        "total_pages": total_pages,
        "pages": list(range(1, total_pages + 1))
    }



@app.get("/api/slide-question", response_model=SlideQuestionResponse)
async def get_slide_question(
    deck: str = Query("d1", description="Slide deck ID (d1 hoặc d2)"),
    page: int = Query(12, ge=1, le=100, description="Số trang slide hiện tại"),
    level: int = Query(1, ge=1, le=3, description="Cấp độ nhận thức học viên (1: Cơ bản, 2: Vận dụng, 3: Chuyên sâu)")
):
    """
    Khối 1: Gợi nhớ kiến thức slide cũ bắc cầu sang slide/bài tập hiện tại
    Tự động sinh câu hỏi thích ứng theo năng lực học viên bằng GPT-4o-mini hoặc RAG fallback
    """
    try:
        return await pedagogy_service.get_slide_question(deck=deck, page=page, level=level)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi truy xuất câu hỏi slide: {str(e)}")


QUESTION_PARAMS = {
    "d1:6": {"a": 1.1, "b": -0.2, "c": 0.18},
    "d1:12": {"a": 1.2, "b": 0.1, "c": 0.2},
    "d1:18": {"a": 1.4, "b": 0.3, "c": 0.15},
    "d1:22": {"a": 1.0, "b": 0.0, "c": 0.25},
    "d1:25": {"a": 1.3, "b": 0.4, "c": 0.18},
    "d2:5": {"a": 1.0, "b": -0.1, "c": 0.2},
    "d2:11": {"a": 1.2, "b": 0.2, "c": 0.15},
    "d2:20": {"a": 1.3, "b": 0.4, "c": 0.18},
}


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def p3pl(theta: float, a: float, b: float, c: float) -> float:
    z = a * (theta - b)
    g = sigmoid(z)
    return c + (1 - c) * g


def update_theta(theta: float, is_correct: bool, a: float, b: float, c: float, lr: float = 0.25) -> float:
    a = max(float(a), 0.1)
    c = min(max(float(c), 0.0), 0.8)
    p = p3pl(theta, a, b, c)
    y = 1.0 if is_correct else 0.0

    g = sigmoid(a * (theta - b))
    dP = (1 - c) * a * g * (1 - g)
    new_theta = theta + lr * (y - p) * dP
    return float(new_theta)


@app.post("/api/chat/evaluate", response_model=AnswerEvaluationResponse)
async def evaluate_answer(req: StudentAnswerRequest):
    """
    Khối 1 & 2 & 3: Đánh giá câu trả lời học viên bằng GPT-4o-mini / Misconception Bank
    """
    try:
        result = await pedagogy_service.evaluate_answer(req)

        # Cập nhật trạng thái học viên vào bộ nhớ
        student = analytics_service.students.get(req.student_id)
        if student:
            theta = float(req.theta) if req.theta is not None else float(student.get("theta", 0.0))
            q_key = f"{req.deck}:{req.page}"
            params = QUESTION_PARAMS.get(q_key, {"a": 1.0, "b": 0.0, "c": 0.2})
            item_a = float(req.item_a) if req.item_a is not None else float(params["a"])
            item_b = float(req.item_b) if req.item_b is not None else float(params["b"])
            item_c = float(req.item_c) if req.item_c is not None else float(params["c"])

            new_theta = update_theta(theta, result.is_correct, item_a, item_b, item_c, lr=0.25)
            student["theta"] = new_theta
            student["level"] = result.new_level
            student["streak"] = result.new_streak

            if new_theta < -1.0:
                student["level"] = 1
            elif new_theta < 1.0:
                student["level"] = 2
            else:
                student["level"] = 3

            if result.diagnostic and result.diagnostic.is_misconception:
                student["last_error"] = result.diagnostic.faulty_assumption
                student["flagged"] = True
                student["status"] = "Cần hỗ trợ"
            elif result.is_correct:
                student["status"] = "Tiến bộ tốt"
                student["flagged"] = False

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đánh giá câu trả lời: {str(e)}")

@app.post("/api/chat/ask", response_model=StudentChatResponse)
async def ask_tutor(req: StudentChatRequest):
    """
    Khối 1: Đàm thoại gợi mở Socratic & Giải đáp thắc mắc
    - Trả lời yêu cầu ví dụ thực tế trực quan
    - Giải thích bản chất khái niệm
    - Gợi ý tư duy sư phạm không lộ đáp án
    """
    try:
        return await pedagogy_service.answer_student_query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi phản hồi đàm thoại Socratic: {str(e)}")


@app.get("/api/citations/{citation_id}")
async def get_citation_detail(citation_id: str):
    """Truy xuất chi tiết trích dẫn transcript theo mã [Txx-NNN]"""
    citation = rag_service.get_citation(citation_id)
    if not citation:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy trích dẫn {citation_id}")
    return citation

@app.get("/api/analytics/dashboard", response_model=InstructorDashboardResponse)
async def get_instructor_dashboard():
    """
    Khối 4: Dashboard giảng viên
    - Heatmap ngộ nhận lớp học
    - Danh sách học viên & trạng thái
    - Thống kê khảo sát người học thực tế
    """
    try:
        return analytics_service.get_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo Dashboard: {str(e)}")

@app.post("/api/instructor/override")
async def instructor_override(req: InstructorOverrideRequest):
    """
    Khối 4: Can thiệp thủ công từ giảng viên
    - Điều chỉnh nhãn lỗi, gửi gợi ý tùy biến, thêm bước scaffolding
    """
    try:
        return analytics_service.apply_override(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi thực hiện can thiệp: {str(e)}")


@app.get("/api/slide-image")
async def get_slide_image(
    deck: str = Query("d1", description="Slide deck (d1 hoặc d2)"),
    page: int = Query(12, ge=1, le=100, description="Trang slide"),
    dpi: int = Query(150, ge=72, le=300, description="Độ phân giải DPI")
):
    """
    Render trực tiếp trang slide thành ảnh PNG sắc nét (2000x1125).
    Khắc phục triệt để lỗi không mở được PDF hoặc bị chặn iframe trên mọi trình duyệt.
    """
    img_bytes = rag_service.render_slide_image(deck=deck, page=page, dpi=dpi)
    if not img_bytes:
        raise HTTPException(status_code=404, detail=f"Không thể render trang {page} của deck {deck}")
    return Response(content=img_bytes, media_type="image/png")

# Mount static directories
# 1. Mount toàn bộ thư mục Data để khớp với cả link /Data/vlearn-pack/...
if ROOT_DATA_DIR.exists():
    app.mount("/Data", StaticFiles(directory=str(ROOT_DATA_DIR)), name="root_data")

# 2. Mount thư mục slides trực tiếp để truy cập nhanh /slides/...
if SLIDES_DIR.exists():
    app.mount("/slides", StaticFiles(directory=str(SLIDES_DIR)), name="slides")

# 3. Frontend Mockup UI in root /
if MOCKUP_DIR.exists():
    app.mount("/", StaticFiles(directory=str(MOCKUP_DIR), html=True), name="frontend")

