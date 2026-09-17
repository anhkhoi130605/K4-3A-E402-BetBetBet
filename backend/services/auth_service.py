"""
Authentication & Role-Based Authorization Service for VLearn
Supports:
- Role 'student' (Học sinh): Directs to 70/30 Slide + AI Companion
- Role 'teacher' (Giáo viên): Directs to Instructor Analytics & Override Dashboard
"""

from typing import Dict, Any, Optional
import uuid

class AuthService:
    def __init__(self):
        # Pre-seeded users for demo convenience
        self.users: Dict[str, Dict[str, Any]] = {
            "hocvien": {
                "id": "S0102",
                "username": "hocvien",
                "password": "123",
                "name": "Nguyễn Văn An (S0102)",
                "role": "student"  # 'student' | 'teacher'
            },
            "giangvien": {
                "id": "GV001",
                "username": "giangvien",
                "password": "123",
                "name": "ThS. Trần Nam (Giảng viên)",
                "role": "teacher"
            }
        }
        self.tokens: Dict[str, str] = {}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        username = username.strip().lower()
        user = self.users.get(username)
        if not user or user["password"] != password:
            return {
                "success": False,
                "message": "Tên đăng nhập hoặc mật khẩu không chính xác."
            }

        token = f"token_{uuid.uuid4().hex[:12]}"
        self.tokens[token] = username

        return {
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "name": user["name"],
                "role": user["role"]
            },
            "message": f"Đăng nhập thành công với vai trò {'Giáo viên' if user['role'] == 'teacher' else 'Học sinh'}!"
        }

    def register(self, username: str, password: str, name: str, role: str = "student") -> Dict[str, Any]:
        username = username.strip().lower()
        if username in self.users:
            return {
                "success": False,
                "message": f"Tài khoản '{username}' đã tồn tại trong hệ thống."
            }

        if len(password) < 3:
            return {
                "success": False,
                "message": "Mật khẩu phải có ít nhất 3 ký tự."
            }

        new_id = f"S{len(self.users) + 100:04d}" if role == "student" else f"GV{len(self.users):03d}"
        user_record = {
            "id": new_id,
            "username": username,
            "password": password,
            "name": name.strip() or f"Người dùng {username}",
            "role": "teacher" if role == "teacher" else "student"
        }
        self.users[username] = user_record

        token = f"token_{uuid.uuid4().hex[:12]}"
        self.tokens[token] = username

        return {
            "success": True,
            "token": token,
            "user": {
                "id": user_record["id"],
                "username": user_record["username"],
                "name": user_record["name"],
                "role": user_record["role"]
            },
            "message": f"Đăng ký thành công tài khoản {'Giáo viên' if user_record['role'] == 'teacher' else 'Học sinh'}!"
        }

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        username = self.tokens.get(token)
        if not username:
            return None
        user = self.users.get(username)
        if not user:
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "name": user["name"],
            "role": user["role"]
        }

auth_service = AuthService()
