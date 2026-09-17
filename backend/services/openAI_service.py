"""
OpenRouter Service: Socratic Adaptive Question & Evaluation Engine
Powered by GPT-4o-mini via OpenRouter
Integrates: ReAct Reasoning, Bloom Taxonomy, Few-Shot Learning & Guardrails
"""

import json
import os
from typing import Optional, Dict, Any
import httpx
from backend.config import OPENAI_API_KEY, OPENAI_MODEL, ENV_FILE
from backend.prompts import (
    check_guardrails_input,
    SOCRATIC_GENERATOR_SYSTEM_PROMPT,
    build_question_generator_prompt,
    REACT_EVALUATOR_SYSTEM_PROMPT,
    build_evaluation_prompt
)

class OpenRouterService:
    def __init__(self):
        self.api_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        self.model = OPENAI_MODEL or "openai/gpt-4o-mini"
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def set_key(self, key: str):
        self.api_key = key.strip()
        os.environ["OPENROUTER_API_KEY"] = self.api_key
        # Also persist to .env
        try:
            lines = []
            found = False
            if ENV_FILE.exists():
                for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                    if line.startswith("OPENROUTER_API_KEY="):
                        lines.append(f"OPENROUTER_API_KEY={self.api_key}")
                        found = True
                    else:
                        lines.append(line)
            if not found:
                lines.append(f"OPENROUTER_API_KEY={self.api_key}")
            ENV_FILE.write_text("\n".join(lines), encoding="utf-8")
        except Exception as e:
            print(f"[OpenRouterService] Error writing to .env: {e}")

    def get_api_key(self) -> str:
        if not self.api_key:
            self.api_key = os.getenv("OPENROUTER_API_KEY", "")
            if not self.api_key and ENV_FILE.exists():
                try:
                    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                        if line.startswith("OPENROUTER_API_KEY="):
                            self.api_key = line.split("=", 1)[1].strip().strip("'\"")
                            os.environ["OPENROUTER_API_KEY"] = self.api_key
                            break
                except Exception:
                    pass
        return self.api_key

    def is_available(self) -> bool:
        key = self.get_api_key()
        return bool(key and len(key) > 10)

    async def generate_slide_question(
        self,
        deck: str,
        page: int,
        slide_text: str,
        prior_page: Optional[int] = None,
        prior_concept: Optional[str] = None,
        level: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Sinh câu hỏi Socratic thích ứng theo năng lực học viên bằng GPT-4o-mini"""
        if not self.is_available():
            return None

        prompt = build_question_generator_prompt(
            deck=deck,
            page=page,
            slide_text=slide_text,
            level=level,
            prior_page=prior_page,
            prior_concept=prior_concept
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "VLearn Adaptive Tutor",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SOCRATIC_GENERATOR_SYSTEM_PROMPT.strip()},
                {"role": "user", "content": prompt.strip()}
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(self.endpoint, headers=headers, json=payload)
                if res.status_code == 200:
                    raw_content = res.json()["choices"][0]["message"]["content"].strip()
                    # Clean json markdown tags if any
                    if raw_content.startswith("```"):
                        raw_content = raw_content.split("\n", 1)[1]
                        if raw_content.endswith("```"):
                            raw_content = raw_content.rsplit("```", 1)[0]
                    parsed = json.loads(raw_content.strip())
                    parsed["level"] = level
                    return parsed
        except Exception as e:
            print(f"[OpenRouterService] Generate question error: {e}")

        return None

    async def evaluate_answer(
        self,
        deck: str,
        page: int,
        slide_text: str,
        question_text: str,
        student_answer: str,
        current_level: int = 1,
        current_streak: int = 0,
        theta: float = 0.0,
        item_a: float = 1.0,
        item_b: float = 0.0,
        item_c: float = 0.2
    ) -> Optional[Dict[str, Any]]:
        """
        Đánh giá câu trả lời của học viên bằng ReAct Pattern và Few-Shot Prompting.
        Tích hợp Guardrail Pre-Check chống Prompt Injection và bảo vệ an toàn sư phạm.
        """
        # Bước 1: Guardrail Pre-Check (Quét vi phạm trước khi gọi LLM)
        guardrail_result = check_guardrails_input(student_answer)
        if guardrail_result:
            return guardrail_result

        if not self.is_available():
            return None

        # Bước 2: Tạo ReAct Prompt với Few-Shot Learning
        prompt = build_evaluation_prompt(
            deck=deck,
            page=page,
            slide_text=slide_text,
            question_text=question_text,
            student_answer=student_answer,
            current_level=current_level,
            current_streak=current_streak,
            theta=theta,
            item_a=item_a,
            item_b=item_b,
            item_c=item_c
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "VLearn Adaptive Tutor",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": REACT_EVALUATOR_SYSTEM_PROMPT.strip()},
                {"role": "user", "content": prompt.strip()}
            ],
            "temperature": 0.2,
            "max_tokens": 650
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(self.endpoint, headers=headers, json=payload)
                if res.status_code == 200:
                    raw_content = res.json()["choices"][0]["message"]["content"].strip()
                    if raw_content.startswith("```"):
                        raw_content = raw_content.split("\n", 1)[1]
                        if raw_content.endswith("```"):
                            raw_content = raw_content.rsplit("```", 1)[0]
                    parsed = json.loads(raw_content.strip())
                    parsed["guardrail_triggered"] = False
                    return parsed
        except Exception as e:
            print(f"[OpenRouterService] Evaluate answer error: {e}")

        return None

    async def chat_socratic(
        self,
        deck: str,
        page: int,
        slide_text: str,
        question_text: str,
        user_message: str,
        transcript_context: str = "",
        level: int = 1
    ) -> Optional[str]:
        """Tương tác đàm thoại Socratic kết hợp RAG từ Slide PDF và 700 đoạn transcript bài giảng"""
        if not self.is_available():
            return None

        sys_prompt = """
Bạn là AI Companion đồng hành trong nền tảng học tập thích ứng VLearn.
Nhiệm vụ của bạn là giải thích trực quan, cung cấp ví dụ thực tế và gợi ý tư duy cho người học dựa trên bối cảnh bài giảng RAG được cung cấp.
[NGUYÊN TẮC CỐT LÕI]:
1. Nếu người học xin VÍ DỤ THỰC TẾ: Hãy đưa ra 1-2 ví dụ thực tế đời sống hoặc bài toán công nghiệp cụ thể, gần gũi, dễ hình dung về khái niệm trong slide.
2. Nếu người học hỏi BẢN CHẤT LÀ GÌ: Hãy giải thích ngắn gọn, súc tích (dưới 4 câu) về nguyên lý cốt lõi, không dùng từ ngữ trừu tượng khó hiểu.
3. Nếu người học xin GỢI Ý (Hint): Đưa ra câu hỏi gợi mở tư duy hoặc chỉ dẫn học viên quan sát chi tiết nào trên slide, TUYỆT ĐỐI không đọc thẳng đáp án trắc nghiệm.
4. Luôn bám sát bối cảnh bài giảng và lời giảng của giảng viên (RAG Context). Nếu có trích dẫn từ transcript, có thể tự nhiên kèm mã [Txx-NNN] để người học tham khảo.
5. Luôn giữ phong cách thân thiện, súc tích, khuyến khích học viên tự tin suy luận.
"""
        rag_section = f"""
[BỐI CẢNH BÀI GIẢNG RAG]:
- Slide {page} ({deck.upper()}) trích xuất:
\"\"\"{slide_text[:1000]}\"\"\"
"""
        if transcript_context:
            rag_section += f"""
- Lời giảng chi tiết của giảng viên (Transcript):
\"\"\"{transcript_context[:1000]}\"\"\"
"""

        user_prompt = f"""
{rag_section}
- Câu hỏi kiểm tra hiện tại: {question_text}

[CÂU HỎI / YÊU CẦU CỦA HỌC VIÊN]:
"{user_message}"

Hãy trả lời ngắn gọn (khoảng 3-5 câu), trực quan, đúng trọng tâm và đúng nguyên tắc sư phạm.
"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "VLearn Adaptive Tutor",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()}
            ],
            "temperature": 0.5,
            "max_tokens": 500
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(self.endpoint, headers=headers, json=payload)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[OpenRouterService] Chat socratic error: {e}")

        return None

openrouter_service = OpenRouterService()
