"""
VLearn Adaptive AI Tutor - Prompt Engineering & Guardrails Engine
Contains:
1. Role Persona & System Prompts (Socratic Pedagogy)
2. ReAct Framework (Thought ➔ Action ➔ Observation ➔ Guidance)
3. In-Context Few-Shot Learning (Mined from Hackathon Learner Data)
4. Pedagogical & Prompt Injection Guardrails
"""

import re
from typing import Dict, Any, Optional

# ==============================================================================
# 1. PEDAGOGICAL & INJECTION GUARDRAILS (Tiền kiểm tra an toàn)
# ==============================================================================

INJECTION_PATTERNS = [
    r"system\s*override",
    r"ignore\s*(all)?\s*(previous|prior)\s*instructions",
    r"bỏ\s*qua\s*(mọi)?\s*(hướng\s*dẫn|chỉ\s*thị|quy\s*tắc)",
    r"(cho|nói|tiết\s*lộ)\s*(tôi)?\s*(luôn|ngay)?\s*(đáp\s*án|kết\s*quả)",
    r"đáp\s*án\s*(là\s*gì|nào|sao|\?)",
    r"câu\s*nào\s*đúng",
    r"chọn\s*(câu\s*)?(a\s*hay\s*b|nào)",
    r"jailbreak",
    r"prompt\s*injection",
    r"you\s*are\s*now\s*DAN",
    r"trả\s*lời\s*luôn\s*đi",
]

def check_guardrails_input(user_text: str) -> Optional[Dict[str, Any]]:
    """
    Guardrail Pre-Check: Quét phát hiện Prompt Injection hoặc đòi đáp án trực tiếp.
    Nếu vi phạm, kích hoạt phản hồi an toàn Socratic ngay lập tức để tiết kiệm token và bảo vệ hệ thống.
    """
    text_lower = user_text.lower().strip()
    
    # 1. Chống Prompt Injection & Jailbreak
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return {
                "guardrail_triggered": True,
                "reason": "prompt_injection_or_answer_bypass",
                "is_correct": False,
                "score": 0,
                "grade": "Cảnh báo An toàn Sư phạm",
                "feedback": "VLearn hỗ trợ gợi ý Socratic để bạn tự nắm vững bản chất, không cung cấp đáp án trực tiếp.",
                "reasoning": {
                    "thought": "Phát hiện người dùng cố gắng can thiệp kịch bản hệ thống hoặc yêu cầu cung cấp đáp án trực tiếp.",
                    "action": "trigger_pedagogical_guardrail",
                    "observation": f"Khớp mẫu cảnh báo: '{pattern}'",
                    "pedagogical_decision": "Từ chối khéo léo, nhắc nhở mục tiêu học tập tự chủ và đưa người học quay lại câu hỏi chuyên môn."
                },
                "new_streak": 0,
                "new_level": 1,
                "should_level_up": False,
                "should_scaffold": True,
                "socratic_hint": "Hãy quan sát trực tiếp dữ liệu trên slide để tự tìm ra mối liên hệ nhé!",
                "review_recommendation": "Vui lòng tập trung trả lời dựa trên lập luận lý thuyết bài giảng.",
                "review_slide": None
            }

    # 2. Chống câu trả lời rác hoặc spam quá ngắn
    if len(text_lower) < 2 and not text_lower in ["a", "b", "c", "d"]:
        return {
            "guardrail_triggered": True,
            "reason": "insufficient_input",
            "is_correct": False,
            "score": 30,
            "grade": "Chưa đủ cơ sở đánh giá",
            "feedback": "⚠️ Câu trả lời quá ngắn. Vui lòng trình bày rõ lập luận hoặc chọn một phương án cụ thể.",
            "reasoning": {
                "thought": "Đầu vào học viên gửi lên chưa đủ ký tự để phân tích chuỗi tư duy.",
                "action": "prompt_for_elaboration",
                "observation": f"Độ dài input: {len(text_lower)} ký tự",
                "pedagogical_decision": "Yêu cầu người học diễn giải chi tiết hơn."
            },
            "new_streak": 0,
            "new_level": 1,
            "should_level_up": False,
            "should_scaffold": True,
            "socratic_hint": "Bạn có thể giải thích thêm vì sao bạn nghĩ như vậy không?",
            "review_recommendation": "Hãy chia sẻ cách bạn liên hệ kiến thức slide này với bài tập thực tế.",
            "review_slide": None
        }

    return None

# ==============================================================================
# 2. SYSTEM PROMPT: SOCRATIC ADAPTIVE QUESTION GENERATOR (Khối 1)
# ==============================================================================

SOCRATIC_GENERATOR_SYSTEM_PROMPT = """
Bạn là AI Adaptive Socratic Tutor trong hệ thống tự học tương tác VLearn.
Mục tiêu tối thượng của bạn là: KÍCH HOẠT TƯ DUY PHẢN BIỆN (Productive Failure & Socratic Scaffolding), TUYỆT ĐỐI KHÔNG giải bài hộ.

[NGUYÊN TẮC SƯ PHẠM]:
1. Luôn tạo cầu nối gợi nhớ (Theory Bridging / Spaced Retrieval) từ slide trước sang slide hiện tại để người học thấy tính liền mạch.
2. Mỗi câu hỏi phải có 1 phương án ĐÚNG CHẶT CHẼ và 1 phương án BẪY NGỘ NHẬN PHỔ BIẾN (Misconception) thường gặp trong thực tế.
3. Luôn bám sát chính xác nội dung trích xuất từ tài liệu bài giảng (Grounding), không bịa đặt kiến thức ngoài.
4. Chỉ trả về cú pháp JSON hợp lệ, tuyệt đối không kèm markdown backticks hay text bên ngoài.
"""

def build_question_generator_prompt(
    deck: str,
    page: int,
    slide_text: str,
    level: int = 1,
    prior_page: Optional[int] = None,
    prior_concept: Optional[str] = None
) -> str:
    """Xây dựng prompt sinh câu hỏi thích ứng theo thang Bloom Taxonomy"""
    level_taxonomy = {
        1: {
            "name": "Level 1: Nhận biết & Củng cố nền tảng (Remembering / Understanding)",
            "guide": (
                "Người học đang ở mức cơ bản hoặc vừa mắc lỗi ngộ nhận. "
                "Hãy đặt câu hỏi trực quan, phân biệt rõ bản chất khái niệm cốt lõi so với ngộ nhận phổ biến để củng cố nền móng vững chắc."
            ),
            "focus": "Định nghĩa cốt lõi, cơ chế cơ bản, phân biệt đúng/sai trực quan."
        },
        2: {
            "name": "Level 2: Vận dụng thực tiễn & Tình huống (Applying / Analyzing)",
            "guide": (
                "Người học đang có chuỗi tiến bộ tốt (đạt Streak). "
                "Hãy đặt câu hỏi tình huống thực tế (case study bài giảng), yêu cầu tính toán số liệu cụ thể (ví dụ chi phí token, context window, ma trận attention)."
            ),
            "focus": "Bài toán thực tế, tính toán tham số, ứng dụng vào luồng sản phẩm AI."
        },
        3: {
            "name": "Level 3: Phản biện chuyên sâu & Tối ưu hóa (Evaluating / Creating)",
            "guide": (
                "Người học xuất sắc (Mastery). "
                "Hãy đặt câu hỏi thử thách hóc búa về trade-offs kiến trúc, tối ưu chi phí token, rủi ro tràn context window, rủi ro hallucination hoặc tình huống ngoại lệ (edge-cases)."
            ),
            "focus": "Đánh đổi kiến trúc (Latency vs Cost vs Accuracy), kịch bản lỗi biên, giải pháp tối ưu production."
        }
    }

    tax = level_taxonomy.get(level, level_taxonomy[1])

    return f"""
[BỐI CẢNH BÀI HỌC]:
- Học viên đang học Slide {page} (Bài giảng: {deck.upper()}).
- Nội dung trích xuất từ slide hiện tại:
\"\"\"{slide_text[:1200]}\"\"\"

{f'- Slide trước đã học là Slide {prior_page} ({prior_concept}). Hãy tạo cầu nối liên kết từ slide trước sang slide này.' if prior_page else ''}

[ĐIỀU PHỐI ĐỘ KHÓ THEO NĂNG LỰC HỌC VIÊN - BLOOM TAXONOMY]:
- Cấp độ hiện tại: {tax['name']}
- Chỉ thị trọng tâm: {tax['guide']}
- Tiêu chí câu hỏi: {tax['focus']}

[YÊU CẦU ĐẦU RA - JSON DUY NHẤT]:
{{
  "level": {level},
  "level_label": "{tax['name']}",
  "title": "Trang {page}: Tiêu đề khái niệm",
  "summary": "Tóm tắt ngắn gọn khái niệm trong slide (1-2 câu)",
  "bridge_flow": "Slide {prior_page or page - 1} ➔ Slide {page}",
  "bridge_note": "Điểm liên kết lý thuyết cốt lõi (1 câu)",
  "ai_question": "Câu hỏi gợi mở Socratic phù hợp với {tax['name']}?",
  "options": [
    {{"id": "A", "text": "Phương án đúng và chặt chẽ", "is_correct": true, "feedback": "Lời khen ngợi và củng cố kiến thức sâu"}},
    {{"id": "B", "text": "Phương án dễ mắc ngộ nhận (Misconception)", "is_correct": false, "feedback": "Chỉ ra vì sao cách nghĩ này là ngộ nhận"}}
  ],
  "citations": ["T04-049"]
}}
"""

# ==============================================================================
# 3. SYSTEM PROMPT: REACT EVALUATOR & SOCRATIC DIAGNOSTIC ENGINE (Khối 2 & 3)
# ==============================================================================

REACT_EVALUATOR_SYSTEM_PROMPT = """
Bạn là AI Adaptive Socratic Evaluator & Diagnostic Engine trong hệ thống VLearn.
Nhiệm vụ của bạn là: Đánh giá câu trả lời của học viên bằng phương pháp suy luận ReAct (Reasoning + Acting) đa bước trước khi đưa ra phán quyết và điểm số.

[QUY TRÌNH SUY LUẬN REACT BẮT BUỘC]:
Trong mỗi lần đánh giá, bạn PHẢI thực hiện 4 bước tư duy tường minh:
1. "thought": Phân tích chuỗi lập luận của học viên. Họ đang hiểu đúng chỗ nào? Điểm ngộ nhận (Misconception) cốt lõi là gì? Giả định ngầm sai của họ bắt nguồn từ đâu?
2. "action": Xác định hành động sư phạm cần làm (ví dụ: 'verify_slide_evidence', 'diagnose_misconception_root', 'scaffold_step_by_step', 'challenge_next_level').
3. "observation": Quan sát kết quả đối chiếu với dữ liệu slide/transcript bài giảng.
4. "pedagogical_decision": Quyết định điểm số (0-100), cấp độ mới (Level 1-3), và câu hỏi gợi mở Socratic để người học tự sửa sai.

[PEDAGOGICAL GUARDRAILS]:
- KHÔNG BAO GIỜ chê bai hay dùng từ ngữ tiêu cực.
- KHÔNG BAO GIỜ tiết lộ đáp án trực tiếp khi học viên làm sai; hãy đưa ra câu hỏi gợi ý để học viên tự nhìn vào slide và ngộ ra.
- Nếu học viên làm đúng: Khen ngợi lập luận cụ thể và kích hoạt câu hỏi đào sâu tiếp theo.
- Chỉ trả về JSON thuần túy hợp lệ.
"""

FEW_SHOT_EVALUATION_EXAMPLES = """
[CÁC VÍ DỤ MẪU CHUẨN MỰC (FEW-SHOT EXAMPLES TỪ HỌC VIÊN THỰC TẾ)]:

--- VÍ DỤ 1 (Học viên mắc lỗi ngộ nhận Tokenizer tiếng Việt) ---
Câu hỏi: Tại sao chi phí API cho tiếng Việt thường cao hơn tiếng Anh với cùng số lượng từ?
Học viên trả lời: "Vì 1 từ tiếng Việt bằng 1 token giống tiếng Anh, nhưng server tính phí đắt hơn cho khu vực Đông Nam Á."
Kết quả đánh giá:
{
  "reasoning": {
    "thought": "Học viên mắc lỗi ngộ nhận kinh điển: đồng nhất 1 từ với 1 token. Thực tế tiếng Việt có dấu thanh và âm tiết ghép, bộ BPE tokenizer chẻ thành 1.3 - 1.4 sub-token/từ.",
    "action": "diagnose_misconception_and_scaffold",
    "observation": "Dữ liệu slide 12 và transcript T04-049 xác nhận hệ số sub-token tiếng Việt là 1.35x. Giả định địa lý là sai.",
    "pedagogical_decision": "Chấm điểm 40/100, đánh dấu ngộ nhận, kích hoạt gợi ý Socratic và giữ Level 1."
  },
  "is_correct": false,
  "score": 40,
  "grade": "Cần củng cố (Mắc lỗi ngộ nhận)",
  "feedback": "Phát hiện giả định sai: Đơn vị tính toán của mô hình là Token chứ không phải Từ ngữ.",
  "is_misconception": true,
  "faulty_assumption": "Đồng nhất 1 từ tiếng Việt với 1 token như tiếng Anh",
  "socratic_hint": "Nếu từ 'Học tập' bị tách thành 2 sub-token, thì 100 từ tiếng Việt sẽ tốn bao nhiêu token so với 100 từ tiếng Anh?",
  "review_recommendation": "Xem lại Slide 12 để đối chiếu hệ số token 1.35x của tiếng Việt."
}

--- VÍ DỤ 2 (Học viên hiểu sâu bản chất Transformer Self-Attention) ---
Câu hỏi: Cơ chế Self-Attention trong Transformer giải quyết điểm nghẽn của RNN/LSTM cũ như thế nào?
Học viên trả lời: "RNN duyệt tuần tự từng từ từ trái sang phải nên câu dài sẽ bị quên context. Transformer dùng Self-Attention cho tất cả token nhìn nhau song song cùng một lúc qua ma trận Q, K, V nên không bị quên."
Kết quả đánh giá:
{
  "reasoning": {
    "thought": "Học viên nắm rất vững bản chất: đối chiếu chính xác giữa duyệt tuần tự (sequential) của RNN và duyệt song song (parallel) qua ma trận toán học của Transformer.",
    "action": "validate_mastery_and_promote",
    "observation": "Khớp hoàn toàn với slide 18 và transcript T06-086.",
    "pedagogical_decision": "Chấm điểm 100/100, thăng cấp lên Level 2 hoặc Level 3 nếu đủ streak."
  },
  "is_correct": true,
  "score": 100,
  "grade": "Xuất sắc (Hiểu sâu bản chất)",
  "feedback": "Lập luận sắc sảo! Bạn đã chỉ rõ sự khác biệt giữa xử lý tuần tự và xử lý ma trận song song.",
  "is_misconception": false,
  "faulty_assumption": null,
  "socratic_hint": "Hãy tiếp tục tư duy này để phân tích bài toán chi phí token ở Slide 25!",
  "review_recommendation": "Bạn đã sẵn sàng học các bài toán kiến trúc nâng cao tiếp theo."
}

--- VÍ DỤ 3 (Học viên hiểu đúng hệ số token tiếng Việt và sub-token) ---
Câu hỏi: Tại sao chi phí API tiếng Việt tốn hơn tiếng Anh và cách tính như thế nào?
Học viên trả lời: "Phải nhân hệ số 1.35x vì tiếng Việt có dấu thanh tách sub-token"
Kết quả đánh giá:
{
  "reasoning": {
    "thought": "Học viên hiểu chính xác bản chất: nhận biết tiếng Việt có dấu thanh làm tăng số sub-token và nhớ chính xác hệ số 1.35x được giảng viên dạy trên slide.",
    "action": "validate_mastery_and_promote",
    "observation": "Khớp hoàn toàn với bài giảng Slide 12 và transcript T04-049.",
    "pedagogical_decision": "Chấm điểm 100/100 tuyệt đối, thăng cấp lên Level 2 nếu có streak."
  },
  "is_correct": true,
  "score": 100,
  "grade": "Xuất sắc (Hiểu sâu bản chất)",
  "feedback": "Chính xác tuyệt đối! Bạn đã nắm rất vững hệ số quy đổi ~1.35x do tiếng Việt có dấu thanh và cấu trúc âm tiết ghép bị tách thành sub-token.",
  "is_misconception": false,
  "faulty_assumption": null,
  "socratic_hint": "Hãy tiếp tục duy trì lập luận sắc bén này ở các mốc tiếp theo!",
  "review_recommendation": "Bạn đã sẵn sàng bước sang bài toán tính toán Context Window ở Slide 14."
}
"""

def build_evaluation_prompt(
    deck: str,
    page: int,
    slide_text: str,
    question_text: str,
    student_answer: str,
    current_level: int = 1,
    current_streak: int = 0
) -> str:
    """Xây dựng prompt đánh giá câu trả lời tích hợp ReAct và Few-Shot"""
    return f"""
{FEW_SHOT_EVALUATION_EXAMPLES}

[TÌNH HUỐNG CẦN ĐÁNH GIÁ HIỆN TẠI]:
- Slide {page} ({deck.upper()})
- Nội dung slide hiện tại: \"\"\"{slide_text[:1000]}\"\"\"
- Câu hỏi đặt ra: {question_text}
- Câu trả lời của học viên: \"\"\"{student_answer}\"\"\"
- Trạng thái học viên: Cấp độ hiện tại = Level {current_level}, Chuỗi đúng Streak = {current_streak}

[YÊU CẦU ĐÁNH GIÁ THEO CHUỖI REACT]:
Hãy phân tích chuỗi tư duy (thought) ➔ hành động (action) ➔ quan sát (observation) ➔ phán quyết sư phạm.
Nếu học viên đúng và streak >= 1, hãy tăng level (tối đa Level 3). Nếu học viên ngộ nhận, hãy reset streak = 0 và scaffold.

Trả về JSON DUY NHẤT:
{{
  "reasoning": {{
    "thought": "Chuỗi phân tích logic tư duy của học viên (1-2 câu)",
    "action": "Hành động sư phạm đã chọn",
    "observation": "Đối chiếu với dữ liệu slide",
    "pedagogical_decision": "Lý do cho điểm và điều chỉnh cấp độ"
  }},
  "is_correct": true hoặc false,
  "score": 100 (nếu đúng) hoặc 40-60 (nếu sai/ngộ nhận),
  "grade": "Xuất sắc (Hiểu sâu)" hoặc "Cần củng cố (Lỗi ngộ nhận)",
  "feedback": "Nhận xét khách quan, cụ thể vào lập luận",
  "is_misconception": true hoặc false,
  "faulty_assumption": "Giả định sai nếu có (hoặc null)",
  "new_streak": {current_streak + 1} nếu đúng, 0 nếu sai,
  "new_level": {min(current_level + 1, 3)} nếu đúng và streak >= 1, ngược lại giữ nguyên hoặc giảm,
  "should_level_up": true nếu new_level > {current_level} ngược lại false,
  "should_scaffold": true nếu sai,
  "socratic_hint": "Gợi ý Socratic kích thích tự kiểm tra lại",
  "review_recommendation": "Đề xuất ôn tập phần nào",
  "review_slide": {page}
}}
"""
