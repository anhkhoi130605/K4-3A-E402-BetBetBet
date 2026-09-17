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
from backend.services.analytics_service import (
    analytics_service,
    sigmoid,
    p3pl,
    update_theta,
    evaluate_learner_by_theta
)
from backend.services.auth_service import auth_service
from backend.services.openAI_service import openrouter_service
from backend.services.logger_service import theta_logger
from backend.services.misconception_log_service import misconception_logger

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
    """Trả về số lượng trang và thông tin cơ bản của bộ slide (ưu tiên nạp từ slides_data.json)"""
    total_pages = rag_service.get_total_pages(deck)
    return {
        "deck": deck,
        "total_pages": total_pages,
        "pages": list(range(1, total_pages + 1))
    }



@app.get("/api/slide-question", response_model=SlideQuestionResponse)
async def get_slide_question(
    deck: str = Query("d1", description="Slide deck ID (d1 hoặc d2)"),
    page: int = Query(12, ge=1, le=100, description="Số trang slide hiện tại"),
    level: int = Query(1, ge=1, le=3, description="Cấp độ nhận thức học viên (1: Cơ bản, 2: Vận dụng, 3: Chuyên sâu)"),
    student_id: Optional[str] = Query("S0102", description="Mã học viên"),
    theta: Optional[float] = Query(None, description="Chỉ số năng lực theta hiện tại")
):
    """
    Khối 1: Gợi nhớ kiến thức slide cũ bắc cầu sang slide/bài tập hiện tại
    Tự động sinh câu hỏi thích ứng theo năng lực học viên bằng GPT-4o-mini hoặc RAG fallback
    Đồng thời ghi log câu hỏi và chỉ số theta vào file backend/ai-log/logbythea.jsonl
    """
    try:
        res = await pedagogy_service.get_slide_question(deck=deck, page=page, level=level)

        # Lấy chỉ số theta hiện tại của người học
        current_theta = theta
        if current_theta is None:
            student = analytics_service.students.get(student_id or "S0102")
            if student and "theta" in student:
                current_theta = float(student["theta"])
            else:
                current_theta = 0.0

        q_key = f"{deck}:{page}"
        item_params = QUESTION_PARAMS.get(q_key, {"a": 1.0, "b": 0.0, "c": 0.2})
        source_name = getattr(res, "source", None) or ("LLM (GPT-4o-mini)" if openrouter_service.is_available() else "preset")

        # Ghi log câu hỏi kèm chỉ số theta hiện tại
        theta_logger.log_question(
            student_id=student_id or "S0102",
            deck=deck,
            page=page,
            level=level,
            theta=current_theta,
            question_text=res.ai_question,
            options=res.options,
            item_params=item_params,
            source=source_name
        )

        return res
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


@app.post("/api/chat/evaluate", response_model=AnswerEvaluationResponse)
async def evaluate_answer(req: StudentAnswerRequest):
    """
    Khối 1 & 2 & 3: Đánh giá câu trả lời học viên bằng ReAct Pattern và thông số IRT 3PL Theta
    Đồng thời ghi log câu trả lời của người dùng và cập nhật chỉ số theta vào file backend/ai-log/logbythea.jsonl
    """
    try:
        # Tự động gán tham số 3PL của câu hỏi nếu chưa truyền lên
        q_key = f"{req.deck}:{req.page}"
        params = QUESTION_PARAMS.get(q_key, {"a": 1.0, "b": 0.0, "c": 0.2})
        if req.item_a is None:
            req.item_a = float(params["a"])
        if req.item_b is None:
            req.item_b = float(params["b"])
        if req.item_c is None:
            req.item_c = float(params["c"])

        student = analytics_service.students.get(req.student_id)
        if student and req.theta is None:
            req.theta = float(student.get("theta", 0.0))

        theta_before = float(req.theta if req.theta is not None else 0.0)
        result = await pedagogy_service.evaluate_answer(req)

        # Cập nhật trạng thái học viên vào bộ nhớ dựa trên kết quả tính toán thông số theta
        new_theta = result.new_theta if result.new_theta is not None else theta_before
        if student:
            student["theta"] = new_theta
            student["level"] = result.new_level
            student["streak"] = result.new_streak

            if result.diagnostic and result.diagnostic.is_misconception:
                student["last_error"] = result.diagnostic.faulty_assumption
                student["flagged"] = True
                student["status"] = "Cần can thiệp"
            elif result.is_correct:
                student["status"] = "Xuất sắc" if new_theta >= 1.0 else "Tiến bộ tốt"
                student["flagged"] = False
            else:
                student["status"] = "Cần can thiệp" if new_theta < -0.5 else "Đang củng cố"
                student["flagged"] = new_theta < -0.5

        # Lưu vết ngộ nhận bền vững vào MisconceptionLogService cho Giáo viên và AI Agent
        if result.diagnostic and result.diagnostic.is_misconception:
            misconception_logger.record_misconception(
                student_id=req.student_id or "S0102",
                student_name=student.get("name") if student else f"Học viên {req.student_id or 'S0102'}",
                deck=req.deck,
                page=req.page,
                faulty_assumption=result.diagnostic.faulty_assumption,
                student_answer=req.answer_text,
                citation_id=result.diagnostic.citation_id or "T04-049",
                slide_reference=result.diagnostic.slide_reference or f"Slide {req.page}"
            )
        elif result.is_correct:
            # Tự động chuyển trạng thái ngộ nhận sang remediated khi học sinh hiểu và làm đúng
            misconception_logger.mark_remediated(
                student_id=req.student_id or "S0102",
                deck=req.deck,
                page=req.page
            )

        # Ghi log câu trả lời người dùng đã chọn kèm chỉ số theta cập nhật theo JSON vào file logbythea.jsonl
        theta_logger.log_answer(
            student_id=req.student_id,
            deck=req.deck,
            page=req.page,
            question_text=req.question_text or f"Câu hỏi kiểm tra Slide {req.page}",
            selected_option_id=req.selected_option_id,
            answer_text=req.answer_text,
            is_correct=result.is_correct,
            score=result.score,
            grade=result.grade,
            theta_before=theta_before,
            theta_after=new_theta,
            p3pl_prob=result.p3pl_prob,
            item_params=params,
            level_before=req.current_level,
            level_after=result.new_level,
            streak_before=req.current_streak,
            streak_after=result.new_streak,
            feedback=result.feedback,
            diagnostic=result.diagnostic,
            reasoning=result.reasoning
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đánh giá câu trả lời: {str(e)}")


@app.get("/api/ai-log/thea")
async def get_theta_logs(limit: int = Query(50, ge=1, le=500)):
    """Lấy danh sách log câu hỏi và chỉ số theta từ backend/ai-log/logbythea.jsonl"""
    recent = theta_logger.get_recent_logs(limit)
    return {
        "count": len(recent),
        "logs": recent
    }

# ================= TEACHER MISCONCEPTION MANAGEMENT =================
@app.get("/api/teacher/misconceptions")
async def get_teacher_misconceptions(
    student_id: Optional[str] = Query(None, description="Lọc theo mã học sinh"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (unresolved / remediated / teacher_intervened)"),
    limit: int = Query(100, ge=1, le=500, description="Số lượng bản ghi tối đa")
):
    """
    Dành cho Giáo viên: Lấy danh sách toàn bộ các ngộ nhận học sinh đã mắc phải từ file lưu trữ bền vững.
    Hỗ trợ lọc theo từng học sinh hoặc trạng thái đã khắc phục/chưa khắc phục.
    """
    records = misconception_logger.get_all_records(student_id=student_id, status=status, limit=limit)
    stats = misconception_logger.get_misconception_stats()
    return {
        "count": len(records),
        "records": records,
        "summary": stats
    }

@app.post("/api/teacher/misconceptions/{record_id}/action")
async def update_misconception_record(record_id: str, payload: Dict[str, Any]):
    """
    Dành cho Giáo viên: Can thiệp, ghi chú sư phạm hoặc đánh dấu đã hướng dẫn cho một ngộ nhận của học sinh.
    """
    action = payload.get("action", "resolve")
    note = payload.get("note", "")
    updated = misconception_logger.resolve_or_override(record_id=record_id, action=action, note=note)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bản ghi ngộ nhận {record_id}")
    return {
        "success": True,
        "message": f"Đã cập nhật ngộ nhận {record_id} thành công",
        "record": updated
    }

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

