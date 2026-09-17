"""
Memory Service: Hybrid Short-Term & Long-Term Memory (STM & LTM) Engine
Empowers the AI Socratic Companion with multi-turn conversation memory
and longitudinal learner misconception tracking.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.config import LEARNER_MEMORY_FILE, AI_LOG_DIR

class MemoryService:
    def __init__(self, memory_file: Path = LEARNER_MEMORY_FILE):
        self.memory_file = memory_file
        # Short-term working memory: student_id -> list of recent message dicts {"role": ..., "content": ...}
        self.short_term_memory: Dict[str, List[Dict[str, str]]] = {}
        # Long-term learner profile memory: student_id -> profile dict
        self.long_term_memory: Dict[str, Dict[str, Any]] = {}
        self._ensure_dir()
        self._load_memory()

    def _ensure_dir(self):
        if not AI_LOG_DIR.exists():
            AI_LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _load_memory(self):
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text(encoding="utf-8"))
                self.long_term_memory = data.get("profiles", {})
            except Exception as e:
                print(f"[MemoryService] Warning loading memory file: {e}")
                self.long_term_memory = {}
        else:
            # Khởi tạo hồ sơ ban đầu cho học viên mẫu S0102
            self.long_term_memory = {
                "S0102": {
                    "student_id": "S0102",
                    "name": "Nguyễn Văn An (S0102)",
                    "misconceptions": [
                        {
                            "slide": 12,
                            "faulty_assumption": "Đồng nhất 1 từ tiếng Việt = 1 token như tiếng Anh",
                            "recorded_at": "2026-09-17T14:30:00",
                            "status": "in_progress"
                        }
                    ],
                    "masteries": [
                        {
                            "slide": 6,
                            "concept": "Lịch sử AI và Hệ chuyên gia luật IF-THEN",
                            "recorded_at": "2026-09-17T14:15:00"
                        }
                    ],
                    "learning_style": "Thích ví dụ thực tế và giải thích trực quan về chi phí token"
                }
            }
            self._save_memory()

    def _save_memory(self):
        try:
            payload = {
                "updated_at": datetime.now().isoformat(),
                "profiles": self.long_term_memory
            }
            self.memory_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[MemoryService] Error saving memory: {e}")

    # =========================================================================
    # 1. SHORT-TERM WORKING MEMORY (STM) - Lịch sử hội thoại trượt
    # =========================================================================
    def get_recent_history(self, student_id: str, limit: int = 6) -> List[Dict[str, str]]:
        """Lấy danh sách các lượt tin nhắn gần nhất trong phiên học"""
        history = self.short_term_memory.get(student_id, [])
        return history[-limit:]

    def append_turn(self, student_id: str, role: str, content: str, max_turns: int = 10):
        """Thêm một lượt hội thoại vào bộ nhớ làm việc ngắn hạn"""
        if student_id not in self.short_term_memory:
            self.short_term_memory[student_id] = []
        self.short_term_memory[student_id].append({
            "role": role,
            "content": content.strip(),
            "timestamp": datetime.now().isoformat()
        })
        if len(self.short_term_memory[student_id]) > max_turns:
            self.short_term_memory[student_id] = self.short_term_memory[student_id][-max_turns:]

    def clear_short_term(self, student_id: str):
        """Xóa bộ nhớ ngắn hạn khi học viên đổi bài giảng hoặc đăng xuất"""
        if student_id in self.short_term_memory:
            self.short_term_memory[student_id] = []

    # =========================================================================
    # 2. LONG-TERM EPISODIC & PROFILE MEMORY (LTM) - Hồ sơ nhận thức dài hạn
    # =========================================================================
    def get_profile(self, student_id: str) -> Dict[str, Any]:
        """Truy xuất hồ sơ bộ nhớ dài hạn của học viên"""
        if student_id not in self.long_term_memory:
            self.long_term_memory[student_id] = {
                "student_id": student_id,
                "misconceptions": [],
                "masteries": [],
                "learning_style": "Cần tiếp cận sư phạm Socratic từng bước"
            }
        return self.long_term_memory[student_id]

    def record_misconception(self, student_id: str, slide: int, faulty_assumption: str):
        """Ghi nhận một quan niệm sai lầm mới vào bộ nhớ dài hạn"""
        profile = self.get_profile(student_id)
        # Kiểm tra xem ngộ nhận này đã được ghi nhận chưa
        exists = any(
            m.get("slide") == slide and m.get("faulty_assumption") == faulty_assumption
            for m in profile.get("misconceptions", [])
        )
        if not exists:
            profile["misconceptions"].append({
                "slide": slide,
                "faulty_assumption": faulty_assumption,
                "recorded_at": datetime.now().isoformat(),
                "status": "active"
            })
            self._save_memory()

    def record_mastery(self, student_id: str, slide: int, concept: str):
        """Ghi nhận một khái niệm học viên đã nắm vững hoặc sửa sai thành công"""
        profile = self.get_profile(student_id)
        # Nếu khái niệm này từng là ngộ nhận ở slide này, đánh dấu là đã giải quyết (resolved)
        for m in profile.get("misconceptions", []):
            if m.get("slide") == slide:
                m["status"] = "resolved"

        exists = any(
            c.get("slide") == slide and c.get("concept") == concept
            for c in profile.get("masteries", [])
        )
        if not exists:
            profile["masteries"].append({
                "slide": slide,
                "concept": concept,
                "recorded_at": datetime.now().isoformat()
            })
            self._save_memory()

    def get_memory_prompt_context(self, student_id: str, current_page: int) -> str:
        """
        Tổng hợp ngữ cảnh bộ nhớ dài hạn & ngắn hạn thành đoạn chỉ thị sư phạm
        đưa vào Prompt của GPT-4o-mini, giúp AI giao tiếp liền mạch và cá nhân hóa.
        """
        profile = self.get_profile(student_id)
        active_misc = [m for m in profile.get("misconceptions", []) if m.get("status") == "active"]
        resolved_misc = [m for m in profile.get("misconceptions", []) if m.get("status") == "resolved"]
        recent_masteries = profile.get("masteries", [])[-3:]

        lines = ["[BỘ NHỚ HỌC TẬP DÀI HẠN & TIỂU SỬ HỌC VIÊN (LONG-TERM MEMORY)]:"]
        lines.append(f"- Mã học viên: {student_id}")

        if active_misc:
            misc_strs = [f"Slide {m['slide']}: '{m['faulty_assumption']}'" for m in active_misc[-3:]]
            lines.append(f"- Các ngộ nhận học viên đang gặp phải: {'; '.join(misc_strs)}.")
            lines.append("  (Chỉ thị: Nếu câu hỏi hiện tại có liên quan, hãy khéo léo nhắc lại bài học trước để giúp học viên đính chính triệt để)")

        if resolved_misc:
            res_strs = [f"Slide {m['slide']}: '{m['faulty_assumption']}'" for m in resolved_misc[-2:]]
            lines.append(f"- Đã sửa sai thành công các ngộ nhận: {'; '.join(res_strs)}.")

        if recent_masteries:
            mast_strs = [f"Slide {m['slide']} ({m['concept']})" for m in recent_masteries]
            lines.append(f"- Kiến thức đã nắm vững: {'; '.join(mast_strs)}.")

        return "\n".join(lines)


memory_service = MemoryService()
