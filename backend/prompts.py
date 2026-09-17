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
2. BẮT BUỘC mỗi câu hỏi phải có ĐỦ 4 PHƯƠNG ÁN LỰA CHỌN (A, B, C, D): Gồm 1 phương án ĐÚNG CHẶT CHẼ và 3 phương án BẪY NGỘ NHẬN / NHIỄU (Misconceptions) có kèm phản hồi feedback giải thích chi tiết.
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
    """Xây dựng prompt sinh câu hỏi thích ứng theo thang Bloom Taxonomy với đủ 4 đáp án"""
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

[YÊU CẦU ĐẦU RA - JSON DUY NHẤT VỚI ĐỦ 4 PHƯƠNG ÁN A, B, C, D]:
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
    {{"id": "B", "text": "Phương án bẫy ngộ nhận 1 (Misconception)", "is_correct": false, "feedback": "Chỉ ra vì sao cách nghĩ này là ngộ nhận"}},
    {{"id": "C", "text": "Phương án bẫy ngộ nhận 2 / nhiễu kỹ thuật", "is_correct": false, "feedback": "Chỉ ra điểm sai sót về mặt kỹ thuật"}},
    {{"id": "D", "text": "Phương án bẫy ngộ nhận 3 / hiểu nhầm kiến trúc", "is_correct": false, "feedback": "Giải thích vì sao cách tiếp cận này chưa đúng"}}
  ],
  "citations": ["T04-049"]
}}
"""

# ==============================================================================
# 3. SYSTEM PROMPT: REACT EVALUATOR & SOCRATIC DIAGNOSTIC ENGINE (Khối 2 & 3)
# ==============================================================================

REACT_EVALUATOR_SYSTEM_PROMPT = """
Bạn là AI Adaptive Socratic Evaluator & Diagnostic Engine trong hệ thống VLearn.
Nhiệm vụ của bạn là: Đánh giá câu trả lời của học viên bằng phương pháp suy luận ReAct (Reasoning + Acting) đa bước.
[QUY TẮC BẮT BUỘC]: KHÔNG tự ý phán đoán cấp độ (Level) hay điểm số cảm tính! Mọi đánh giá năng lực người học PHẢI dựa trên Function Calling hàm cập nhật năng lực theta (update_theta) và mô hình xác suất IRT 3PL (p3pl).

[QUY TRÌNH SUY LUẬN REACT BẮT BUỘC]:
Trong mỗi lần đánh giá, bạn PHẢI thực hiện 4 bước tư duy tường minh:
1. "thought": Phân tích chuỗi lập luận của học viên. Họ đang hiểu đúng chỗ nào? Điểm ngộ nhận (Misconception) cốt lõi là gì? Xác định học viên đúng (is_correct=true) hay sai (is_correct=false).
2. "action": Thực hiện function calling hàm update_theta(theta, is_correct, a, b, c) và tính xác suất p3pl(theta, a, b, c) dựa trên các tham số câu hỏi (độ phân biệt a, độ khó b, đoán mò c).
3. "observation": Quan sát kết quả tính toán trả về từ hàm: giá trị new_theta, xác suất P(theta), độ chênh lệch năng lực so với độ khó b của câu hỏi.
4. "pedagogical_decision": Đưa ra phán quyết sư phạm DỰA TRÊN THÔNG SỐ THETA VỪA TÍNH ĐƯỢC (không tự suy đoán):
   - Đánh giá cấp độ (Level) và xếp loại năng lực theo thang chuẩn của theta.
   - Nếu new_theta tăng trưởng tốt: kích hoạt thách thức nâng cao hoặc thăng cấp Level.
   - Nếu new_theta giảm hoặc học viên ngộ nhận: kích hoạt giàn giáo Socratic, gợi mở học viên quay lại slide bài giảng để tự sửa sai.

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
    "thought": "Học viên mắc lỗi ngộ nhận kinh điển: đồng nhất 1 từ với 1 token. Thực tế tiếng Việt có dấu thanh và âm tiết ghép, bộ BPE tokenizer chẻ thành 1.3 - 1.4 sub-token/từ. Đánh giá is_correct = false.",
    "action": "call_function update_theta(theta=0.0, is_correct=false, a=1.2, b=0.1, c=0.2)",
    "observation": "Hàm p3pl tính P=0.584. Hàm update_theta trả về new_theta = -0.069. Năng lực theta giảm do gặp lỗi ngộ nhận.",
    "pedagogical_decision": "Dựa trên thông số theta=-0.069: Xếp loại Cần củng cố, duy trì Level 1, kích hoạt giàn giáo gợi mở Socratic đối chiếu Slide 12."
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
    "thought": "Học viên nắm rất vững bản chất: đối chiếu chính xác giữa duyệt tuần tự của RNN và duyệt song song qua ma trận toán học của Transformer. Đánh giá is_correct = true.",
    "action": "call_function update_theta(theta=0.0, is_correct=true, a=1.4, b=0.3, c=0.15)",
    "observation": "Hàm p3pl tính P=0.489. Hàm update_theta trả về new_theta = +0.076. Năng lực theta tăng vượt ngưỡng câu hỏi khó.",
    "pedagogical_decision": "Dựa trên thông số theta=+0.076 tăng trưởng kết hợp chuỗi đúng: Đánh giá Xuất sắc, thăng cấp lên Level 2."
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
    "thought": "Học viên hiểu chính xác bản chất: nhận biết tiếng Việt có dấu thanh làm tăng số sub-token và nhớ chính xác hệ số 1.35x được giảng viên dạy trên slide. Đánh giá is_correct = true.",
    "action": "call_function update_theta(theta=0.1, is_correct=true, a=1.3, b=0.2, c=0.18)",
    "observation": "Hàm p3pl tính P=0.564. Hàm update_theta trả về new_theta = +0.178. Năng lực theta củng cố vững chắc.",
    "pedagogical_decision": "Dựa trên thông số theta=+0.178: Đạt yêu cầu xuất sắc, duy trì phong độ và chuẩn bị cho mốc Slide 14."
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
        current_streak: int = 0,
        theta: float = 0.0,
        item_a: float = 1.0,
        item_b: float = 0.0,
        item_c: float = 0.2
) -> str:
    """Xây dựng prompt đánh giá câu trả lời tích hợp ReAct, Function Calling và thông số Theta 3PL"""
    return f"""
{FEW_SHOT_EVALUATION_EXAMPLES}

[TÌNH HUỐNG CẦN ĐÁNH GIÁ HIỆN TẠI]:
- Slide {page} ({deck.upper()})
- Nội dung slide hiện tại: \"\"\"{slide_text[:1000]}\"\"\"
- Câu hỏi đặt ra: {question_text}
- Câu trả lời của học viên: \"\"\"{student_answer}\"\"\"
- Trạng thái học viên: Cấp độ hiện tại = Level {current_level}, Chuỗi đúng Streak = {current_streak}
- Mô hình 3PL hiện tại: theta = {theta}, a = {item_a}, b = {item_b}, c = {item_c}
 
[YÊU CẦU ĐÁNH GIÁ THEO CHUỖI REACT]:
Hãy phân tích chuỗi tư duy (thought) ➔ hành động function calling (action) ➔ quan sát kết quả hàm (observation) ➔ phán quyết sư phạm theo thông số theta (pedagogical_decision).
QUY TẮC CỐT LÕI: Tuyệt đối KHÔNG tự ý phán đoán điểm số/cấp độ cảm tính. Hãy để thông số theta từ hàm update_theta(theta={theta}, is_correct, a={item_a}, b={item_b}, c={item_c}) và hàm p3pl đánh giá năng lực người học!

Trả về JSON DUY NHẤT:
{{
  "reasoning": {{
    "thought": "Chuỗi phân tích logic tư duy của học viên, xác định đúng/sai và ngộ nhận nếu có",
    "action": "call_function update_theta(theta={theta}, is_correct=..., a={item_a}, b={item_b}, c={item_c})",
    "observation": "Giá trị P(theta) từ hàm p3pl và new_theta thu được sau khi gọi hàm",
    "pedagogical_decision": "Phán quyết sư phạm dựa trực tiếp trên thông số theta vừa cập nhật"
  }},
  "is_correct": true hoặc false,
  "is_misconception": true hoặc false,
  "faulty_assumption": "Giả định sai nếu có (hoặc null)",
  "feedback": "Nhận xét khách quan, cụ thể vào lập luận của học viên",
  "socratic_hint": "Gợi ý Socratic kích thích tự kiểm tra lại",
  "review_recommendation": "Đề xuất ôn tập phần nào",
  "review_slide": {page}
}}
"""
