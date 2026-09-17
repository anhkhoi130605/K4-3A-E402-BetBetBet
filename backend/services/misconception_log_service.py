"""
Persistent Student Misconception Service:
Lưu trữ và quản lý bền vững các ngộ nhận của học sinh cho Giáo viên và AI Agent.
Lưu vết vào file backend/ai-log/student_misconceptions.json
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from backend.config import STUDENT_MISCONCEPTIONS_FILE

INITIAL_SEED_RECORDS = [
    {
        "id": "misc_rec_seed_01",
        "timestamp": "2026-09-17T14:20:00",
        "student_id": "S0102",
        "student_name": "Học viên S0102",
        "deck": "d1",
        "page": 12,
        "faulty_assumption": "Đồng nhất 1 từ tiếng Việt với 1 token (như tiếng Anh)",
        "student_answer": "Tôi nghĩ 120 từ tiếng Việt bằng đúng 120 token như tiếng Anh",
        "citation_id": "T04-049",
        "slide_reference": "Slide Day 1 · Trang 12",
        "status": "unresolved",
        "teacher_note": None,
        "resolved_at": None
    },
    {
        "id": "misc_rec_seed_02",
        "timestamp": "2026-09-17T15:10:00",
        "student_id": "S0448",
        "student_name": "Học viên S0448",
        "deck": "d1",
        "page": 18,
        "faulty_assumption": "Nghĩ rằng Transformer duyệt tuần tự từng từ như con người hay RNN/LSTM cũ",
        "student_answer": "Transformer đọc từng từ từ trái sang phải tuần tự theo thời gian",
        "citation_id": "T06-086",
        "slide_reference": "Slide Day 1 · Trang 18",
        "status": "unresolved",
        "teacher_note": None,
        "resolved_at": None
    },
    {
        "id": "misc_rec_seed_03",
        "timestamp": "2026-09-17T16:05:00",
        "student_id": "S1205",
        "student_name": "Học viên S1205",
        "deck": "d1",
        "page": 22,
        "faulty_assumption": "Bỏ quên chi phí Input Token của System Prompt trong mỗi lượt gọi API",
        "student_answer": "System Prompt lưu trên server rồi nên không tính tiền mỗi lượt gọi",
        "citation_id": "T04-089",
        "slide_reference": "Slide Day 1 · Trang 22",
        "status": "unresolved",
        "teacher_note": None,
        "resolved_at": None
    }
]

class MisconceptionLogService:
    def __init__(self, file_path: Path = STUDENT_MISCONCEPTIONS_FILE):
        self.file_path = file_path
        self.records: List[Dict[str, Any]] = []
        self._load_records()

    def _load_records(self):
        """Nạp danh sách ngộ nhận từ file JSON bền vững"""
        if self.file_path.exists():
            try:
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.records = data
                    print(f"[MisconceptionLog] Đã nạp {len(self.records)} bản ghi ngộ nhận từ {self.file_path.name}")
                    return
            except Exception as e:
                print(f"[MisconceptionLog] Lỗi đọc file {self.file_path}: {e}")

        # Khởi tạo mặc định nếu chưa có
        self.records = list(INITIAL_SEED_RECORDS)
        self._save_records()

    def _save_records(self):
        """Lưu trữ danh sách ngộ nhận bền vững vào đĩa"""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[MisconceptionLog] Lỗi lưu file {self.file_path}: {e}")

    def record_misconception(
        self,
        student_id: str,
        student_name: str,
        deck: str,
        page: int,
        faulty_assumption: str,
        student_answer: str,
        citation_id: str = "T04-049",
        slide_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ghi nhận một ngộ nhận mới của học sinh"""
        rec_id = f"misc_rec_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now().isoformat()
        
        record = {
            "id": rec_id,
            "timestamp": now_str,
            "student_id": student_id,
            "student_name": student_name or f"Học viên {student_id}",
            "deck": deck,
            "page": page,
            "faulty_assumption": faulty_assumption,
            "student_answer": student_answer,
            "citation_id": citation_id,
            "slide_reference": slide_reference or f"Slide {page}",
            "status": "unresolved",
            "teacher_note": None,
            "resolved_at": None
        }
        
        self.records.append(record)
        self._save_records()
        print(f"[MisconceptionLog] Đã lưu ngộ nhận mới [{rec_id}] cho {student_id} tại Slide {page}: {faulty_assumption}")
        return record

    def get_unresolved_for_student(self, student_id: str) -> List[Dict[str, Any]]:
        """Lấy các ngộ nhận chưa được giải quyết của học sinh (để AI Agent đọc và cá nhân hóa Socratic hint)"""
        return [
            r for r in self.records
            if r["student_id"] == student_id and r["status"] == "unresolved"
        ]

    def mark_remediated(
        self,
        student_id: str,
        deck: str,
        page: Optional[int] = None,
        faulty_assumption: Optional[str] = None
    ) -> int:
        """Đánh giá học sinh đã hiểu đúng và tự động chuyển trạng thái ngộ nhận sang remediated"""
        updated_count = 0
        now_str = datetime.now().isoformat()
        for r in self.records:
            if r["student_id"] == student_id and r["status"] == "unresolved":
                match = True
                if deck and r.get("deck") != deck:
                    match = False
                if page and r.get("page") != page:
                    match = False
                if faulty_assumption and faulty_assumption.lower() not in r.get("faulty_assumption", "").lower():
                    match = False
                if match:
                    r["status"] = "remediated"
                    r["resolved_at"] = now_str
                    updated_count += 1

        if updated_count > 0:
            self._save_records()
            print(f"[MisconceptionLog] Đã tự động cập nhật remediated cho {updated_count} ngộ nhận của {student_id}")
        return updated_count

    def resolve_or_override(self, record_id: str, action: str, note: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Giáo viên can thiệp trực tiếp hoặc ghi chú cho ngộ nhận của học sinh"""
        for r in self.records:
            if r["id"] == record_id:
                r["status"] = "teacher_intervened" if action in ["override", "intervene", "resolve"] else r["status"]
                r["teacher_note"] = note or "Giáo viên đã can thiệp và hướng dẫn trực tiếp"
                r["resolved_at"] = datetime.now().isoformat()
                self._save_records()
                return r
        return None

    def get_all_records(
        self,
        student_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Truy xuất danh sách ngộ nhận cho Dashboard Giáo viên"""
        res = list(self.records)
        if student_id:
            res = [r for r in res if r["student_id"] == student_id]
        if status:
            res = [r for r in res if r["status"] == status]
        res.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return res[:limit]

    def get_misconception_stats(self) -> List[Dict[str, Any]]:
        """Tổng hợp thống kê ngộ nhận phục vụ Heatmap Giáo viên"""
        topic_map: Dict[str, Dict[str, Any]] = {}
        total_students_set = set()

        for r in self.records:
            topic = r["faulty_assumption"]
            sid = r["student_id"]
            total_students_set.add(sid)

            if topic not in topic_map:
                topic_map[topic] = {
                    "topic": topic,
                    "students": set(),
                    "total_occurrences": 0,
                    "unresolved_count": 0,
                    "remediated_count": 0,
                    "citation_id": r.get("citation_id", "T04-049"),
                    "slide": r.get("slide_reference", f"Slide {r.get('page')}")
                }

            topic_map[topic]["students"].add(sid)
            topic_map[topic]["total_occurrences"] += 1
            if r["status"] == "unresolved":
                topic_map[topic]["unresolved_count"] += 1
            else:
                topic_map[topic]["remediated_count"] += 1

        total_students = max(len(total_students_set), 4)
        stats = []
        for topic, data in topic_map.items():
            affected = len(data["students"])
            pct = round((affected / total_students) * 100, 1)
            severity = "Cao" if pct >= 50 else ("Trung bình" if pct >= 25 else "Thấp")
            stats.append({
                "topic": topic,
                "affected_students": affected,
                "pct": pct,
                "severity": severity,
                "total_occurrences": data["total_occurrences"],
                "unresolved_count": data["unresolved_count"],
                "citation_id": data["citation_id"],
                "slide": data["slide"]
            })

        stats.sort(key=lambda x: x["affected_students"], reverse=True)
        return stats

# Singleton instance
misconception_logger = MisconceptionLogService()
