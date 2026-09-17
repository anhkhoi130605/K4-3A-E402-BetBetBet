"""
OpenRouter Service: Socratic Adaptive Question & Evaluation Engine
Powered by GPT-4o-mini via OpenRouter
Integrates: ReAct Reasoning, Bloom Taxonomy, Few-Shot Learning & Guardrails
"""

import json
import os
import sys
from typing import Optional, Dict, Any, List
import httpx
import random
from backend.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    ENV_FILE
)
from backend.prompts import (
    check_guardrails_input,
    SOCRATIC_GENERATOR_SYSTEM_PROMPT,
    build_question_generator_prompt,
    REACT_EVALUATOR_SYSTEM_PROMPT,
    build_evaluation_prompt
)

class OpenRouterService:
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY") or OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        self.model = OPENROUTER_MODEL or os.getenv("OPENROUTER_MODEL") or OPENAI_MODEL or "openai/gpt-4o-mini"
        if not self.model or "gpt-5" in self.model or "union" in self.model:
            self.model = "openai/gpt-4o-mini"
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
        if not self.api_key or self.api_key.startswith("sk-5Y"):
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
        # During automated tests, avoid calling external LLM backends.
        if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
            return False
        key = self.get_api_key()
        return bool(key and len(key) > 10)

    async def generate_slide_question(
        self,
        deck: str,
        page: int,
        slide_text: str,
        prior_page: Optional[int] = None,
        prior_concept: Optional[str] = None,
        level: int = 1,
        misconceptions: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """Sinh câu hỏi Socratic thích ứng theo năng lực học viên bằng GPT-4o-mini chống học vẹt"""
        # During automated tests, avoid calling external LLM backends even if key is present
        if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
            return None
        if not self.is_available():
            return None

        prompt = build_question_generator_prompt(
            deck=deck,
            page=page,
            slide_text=slide_text,
            level=level,
            prior_page=prior_page,
            prior_concept=prior_concept,
            misconceptions=misconceptions
        )

        # Yêu cầu LLM sinh câu hỏi với ĐỦ 4 PHƯƠNG ÁN (A, B, C, D)
        prompt += "\n\nQUY ĐỊNH BẮT BUỘC:\n1. Mỗi câu hỏi PHẢI CÓ ĐỦ 4 PHƯƠNG ÁN LỰA CHỌN (A, B, C, D) trong mảng 'options', trong đó có đúng 1 đáp án đúng (is_correct=true) và 3 đáp án bẫy ngộ nhận/nhiễu (is_correct=false) kèm lời giải thích feedback chi tiết.\n2. Trả về JSON thuần túy, không kèm markdown backticks hay giải thích bên ngoài."

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
            "max_tokens": 1200
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
                    # Nếu LLM trả về nhiều câu hỏi, chọn ngẫu nhiên 1 câu để trả về cho hệ thống
                    if isinstance(parsed, dict) and parsed.get("questions") and isinstance(parsed["questions"], list):
                        candidates = parsed["questions"]
                        selected = random.choice(candidates)
                        # giữ metadata và trả về định dạng giống như trước
                        selected["_generated_questions"] = candidates
                        selected["level"] = level
                        return selected

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
        item_c: float = 0.2,
        misconceptions: Optional[list] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Đánh giá câu trả lời của học viên bằng ReAct Pattern và Few-Shot Prompting.
        Tích hợp Guardrail Pre-Check chống Prompt Injection và bảo vệ an toàn sư phạm.
        """
        # Bước 1: Guardrail Pre-Check (Quét vi phạm trước khi gọi LLM)
        guardrail_result = check_guardrails_input(student_answer)
        if guardrail_result:
            return guardrail_result

        # During automated tests, skip external LLM even when a key exists
        if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
            return None

        if not self.is_available():
            return None

        # Bước 2: Tạo ReAct Prompt với Few-Shot Learning & Semantic Misconceptions
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
            item_c=item_c,
            misconceptions=misconceptions
        )

        from backend.services.analytics_service import evaluate_learner_by_theta, UPDATE_THETA_TOOL

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
            "tools": [UPDATE_THETA_TOOL],
            "temperature": 0.2,
            "max_tokens": 650
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(self.endpoint, headers=headers, json=payload)
                if res.status_code == 200:
                    choice = res.json()["choices"][0]["message"]
                    parsed = {}
                    
                    # Kiểm tra xem LLM có thực hiện Tool Calling (function calling) không
                    if choice.get("tool_calls"):
                        for tool_call in choice["tool_calls"]:
                            fn = tool_call.get("function", {})
                            if fn.get("name") == "update_theta_and_evaluate":
                                try:
                                    args = json.loads(fn.get("arguments", "{}"))
                                    is_cor = bool(args.get("is_correct", False))
                                    theta_eval = evaluate_learner_by_theta(
                                        theta=float(args.get("theta", theta)),
                                        is_correct=is_cor,
                                        a=float(args.get("a", item_a)),
                                        b=float(args.get("b", item_b)),
                                        c=float(args.get("c", item_c)),
                                        current_level=current_level,
                                        current_streak=current_streak
                                    )
                                    parsed = {
                                        "is_correct": is_cor,
                                        "feedback": "Phân tích lập luận hoàn tất và cập nhật năng lực theta.",
                                        "reasoning": {
                                            "thought": "LLM thực hiện function call hàm update_theta.",
                                            "action": f"call_function update_theta(theta={theta}, is_correct={is_cor}, a={item_a}, b={item_b}, c={item_c})",
                                            "observation": theta_eval["reasoning_observation"],
                                            "pedagogical_decision": theta_eval["pedagogical_decision"]
                                        }
                                    }
                                    parsed.update(theta_eval)
                                    parsed["guardrail_triggered"] = False
                                    return parsed
                                except Exception as err:
                                    print(f"[OpenRouterService] Tool call parse error: {err}")

                    raw_content = (choice.get("content") or "").strip()
                    if raw_content.startswith("```"):
                        raw_content = raw_content.split("\n", 1)[1]
                        if raw_content.endswith("```"):
                            raw_content = raw_content.rsplit("```", 1)[0]
                    if raw_content:
                        parsed = json.loads(raw_content.strip())

                    # Dù LLM trả về JSON gì, ĐÁNH GIÁ NĂNG LỰC NGƯỜI HỌC BẮT BUỘC THEO HÀM THETA
                    is_correct_val = bool(parsed.get("is_correct", False))
                    theta_eval = evaluate_learner_by_theta(
                        theta=theta,
                        is_correct=is_correct_val,
                        a=item_a,
                        b=item_b,
                        c=item_c,
                        current_level=current_level,
                        current_streak=current_streak
                    )

                    # Ghi đè các thông số đánh giá dựa hoàn toàn trên thông số theta
                    parsed["is_correct"] = is_correct_val
                    parsed["score"] = theta_eval["score"]
                    parsed["grade"] = theta_eval["grade"]
                    parsed["new_level"] = theta_eval["new_level"]
                    parsed["new_streak"] = theta_eval["new_streak"]
                    parsed["should_level_up"] = theta_eval["should_level_up"]
                    parsed["should_scaffold"] = theta_eval["should_scaffold"]
                    parsed["theta"] = theta_eval["theta"]
                    parsed["new_theta"] = theta_eval["new_theta"]
                    parsed["p3pl_prob"] = theta_eval["p3pl_prob"]

                    if "reasoning" not in parsed or not isinstance(parsed["reasoning"], dict):
                        parsed["reasoning"] = {}
                    parsed["reasoning"]["action"] = f"call_function update_theta(theta={theta}, is_correct={is_correct_val}, a={item_a}, b={item_b}, c={item_c})"
                    parsed["reasoning"]["observation"] = theta_eval["reasoning_observation"]
                    parsed["reasoning"]["pedagogical_decision"] = theta_eval["pedagogical_decision"]

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
Bạn là AI Bét Bét Bét Agent đồng hành trong nền tảng học tập thích ứng Adaptive Learning.
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
