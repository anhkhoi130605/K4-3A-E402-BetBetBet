"""
Theta Interaction Logger Service
Ghi nhận toàn bộ nhật ký câu hỏi Socratic (chỉ số theta lúc sinh câu hỏi)
và câu trả lời do người dùng lựa chọn (kèm cập nhật thông số theta sau đánh giá 3PL).
Dữ liệu được lưu dạng JSON Lines (.jsonl) tại backend/ai-log/logbythea.jsonl.
"""

import json
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.config import LOG_BY_THETA_FILE, AI_LOG_DIR

class ThetaLoggerService:
    def __init__(self):
        self._lock = threading.Lock()
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        try:
            AI_LOG_DIR.mkdir(parents=True, exist_ok=True)
            if not LOG_BY_THETA_FILE.exists():
                LOG_BY_THETA_FILE.touch()
        except Exception as e:
            print(f"[ThetaLogger] Warning ensuring log directory: {e}")

    def _append_line(self, record: Dict[str, Any]):
        """Ghi an toàn 1 dòng JSON UTF-8 vào file logbythea.jsonl"""
        try:
            line_str = json.dumps(record, ensure_ascii=False)
            with self._lock:
                self._ensure_log_dir()
                with open(LOG_BY_THETA_FILE, "a", encoding="utf-8") as f:
                    f.write(line_str + "\n")
        except Exception as e:
            print(f"[ThetaLogger] Error writing to {LOG_BY_THETA_FILE}: {e}")

    def log_question(
        self,
        deck: str,
        page: int,
        question_text: str,
        options: List[Any],
        level: int = 1,
        theta: float = 0.0,
        student_id: Optional[str] = "S0102",
        item_params: Optional[Dict[str, float]] = None,
        source: str = "preset",
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ghi log khi hệ thống/LLM đưa ra câu hỏi kiểm tra kèm chỉ số năng lực theta hiện tại.
        """
        if item_params is None:
            item_params = {"a": 1.0, "b": 0.0, "c": 0.2}

        # Chuẩn hóa danh sách options thành dict
        normalized_options = []
        for opt in options:
            if isinstance(opt, dict):
                normalized_options.append({
                    "id": opt.get("id", ""),
                    "text": opt.get("text", ""),
                    "is_correct": bool(opt.get("is_correct", False)),
                    "feedback": opt.get("feedback", "")
                })
            else:
                normalized_options.append({
                    "id": getattr(opt, "id", ""),
                    "text": getattr(opt, "text", ""),
                    "is_correct": bool(getattr(opt, "is_correct", False)),
                    "feedback": getattr(opt, "feedback", "")
                })

        record = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "event": "question_asked",
            "student_id": student_id or "anonymous",
            "deck": deck,
            "page": page,
            "level": level,
            "theta": round(float(theta), 4),
            "item_parameters": {
                "a": round(float(item_params.get("a", 1.0)), 4),
                "b": round(float(item_params.get("b", 0.0)), 4),
                "c": round(float(item_params.get("c", 0.2)), 4)
            },
            "question_text": question_text,
            "options": normalized_options,
            "source": source
        }
        if extra:
            record["extra"] = extra

        self._append_line(record)
        return record

    def log_answer(
        self,
        student_id: str,
        deck: str,
        page: int,
        question_text: str,
        answer_text: str,
        is_correct: bool,
        score: int,
        grade: str,
        theta_before: float,
        theta_after: float,
        selected_option_id: Optional[str] = None,
        p3pl_prob: Optional[float] = None,
        item_params: Optional[Dict[str, float]] = None,
        level_before: int = 1,
        level_after: int = 1,
        streak_before: int = 0,
        streak_after: int = 0,
        feedback: str = "",
        diagnostic: Optional[Any] = None,
        reasoning: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ghi log khi người học lựa chọn/trả lời câu hỏi kèm cập nhật chỉ số theta.
        """
        if item_params is None:
            item_params = {"a": 1.0, "b": 0.0, "c": 0.2}

        # Chuẩn hóa diagnostic
        diagnostic_dict = None
        if diagnostic:
            if isinstance(diagnostic, dict):
                diagnostic_dict = diagnostic
            elif hasattr(diagnostic, "model_dump"):
                diagnostic_dict = diagnostic.model_dump()
            elif hasattr(diagnostic, "dict"):
                diagnostic_dict = diagnostic.dict()

        record = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "event": "answer_evaluated",
            "student_id": student_id or "anonymous",
            "deck": deck,
            "page": page,
            "question_text": question_text,
            "selected_option_id": selected_option_id,
            "user_answer": answer_text,
            "is_correct": bool(is_correct),
            "score": score,
            "grade": grade,
            "item_parameters": {
                "a": round(float(item_params.get("a", 1.0)), 4),
                "b": round(float(item_params.get("b", 0.0)), 4),
                "c": round(float(item_params.get("c", 0.2)), 4)
            },
            "theta_before": round(float(theta_before), 4),
            "theta_after": round(float(theta_after), 4),
            "delta_theta": round(float(theta_after) - float(theta_before), 4),
            "p3pl_prob": round(float(p3pl_prob), 4) if p3pl_prob is not None else None,
            "level_before": level_before,
            "level_after": level_after,
            "streak_before": streak_before,
            "streak_after": streak_after,
            "feedback": feedback,
            "diagnostic": diagnostic_dict,
            "reasoning": reasoning
        }
        if extra:
            record["extra"] = extra

        self._append_line(record)
        return record

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Đọc danh sách các bản ghi log gần nhất từ logbythea.jsonl"""
        logs = []
        if not LOG_BY_THETA_FILE.exists():
            return logs
        try:
            with open(LOG_BY_THETA_FILE, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            for line in lines[-limit:]:
                try:
                    logs.append(json.loads(line))
                except Exception:
                    continue
        except Exception as e:
            print(f"[ThetaLogger] Read log error: {e}")
        return logs

theta_logger = ThetaLoggerService()
