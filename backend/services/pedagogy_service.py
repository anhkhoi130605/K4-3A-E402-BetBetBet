"""
Socratic Pedagogy & Misconception Diagnostic Service
Implements Block 1 & Block 2 of Sequence Diagram
"""

from typing import Dict, Any, Optional
from backend.models.schemas import (
    SlideQuestionResponse,
    QuestionOption,
    QuestionVariant,
    StudentAnswerRequest,
    AnswerEvaluationResponse,
    MisconceptionDiagnostic,
    StudentChatRequest,
    StudentChatResponse
)
from backend.services.rag_service import rag_service
from backend.services.openAI_service import openrouter_service
from backend.config import STREAK_FOR_LEVEL_UP, MAX_ADAPTIVE_LEVEL

# Danh sách các Slide Mốc kiến thức quan trọng cần kích hoạt câu hỏi (Spaced Retrieval Checkpoints)
KEY_MILESTONES = {
    "d1": [6, 12, 18, 22, 25],
    "d2": [5, 11, 20]
}

# Ngân hàng lỗi tư duy chuẩn hóa (Mined từ tutor_turns.csv và transcript bài giảng)
MISCONCEPTION_BANK = [
    {
        "id": "misc-01",
        "keywords": ["120 token", "1 từ = 1 token", "1 từ tiếng việt = 1 token", "bằng đúng", "giống tiếng anh"],
        "faulty_assumption": "Đồng nhất 1 từ tiếng Việt với 1 token (như tiếng Anh)",
        "citation": "T04-049",
        "slide": "Slide Day 1 · Trang 12",
        "review_slide": 12,
        "explanation": "Tiếng Việt có dấu thanh và cấu trúc âm tiết ghép, bộ tokenizer tách từ tiếng Việt thành 1.3 - 1.4 token trung bình mỗi từ.",
        "sub_question": "Nếu từ 'Học tập' bị tách thành các sub-token, thì 120 từ tiếng Việt sẽ tốn khoảng bao nhiêu token so với 120 từ tiếng Anh?"
    },
    {
        "id": "misc-02",
        "keywords": ["tuần tự", "trái sang phải", "từng từ một", "đọc tuần tự"],
        "faulty_assumption": "Nghĩ rằng Transformer duyệt tuần tự từng từ như con người hay RNN/LSTM cũ",
        "citation": "T06-086",
        "slide": "Slide Day 1 · Trang 18",
        "review_slide": 18,
        "explanation": "Cơ chế Self-Attention trong Transformer cho phép TẤT CẢ các token nhìn nhau SONG SONG cùng lúc trong không gian toán học.",
        "sub_question": "Nếu cơ chế là song song, ma trận Attention giữa các từ được tính toán đồng thời hay theo thứ tự thời gian?"
    },
    {
        "id": "misc-03",
        "keywords": ["không mất phí", "chỉ tính 120 từ", "cài sẵn trong server", "bỏ qua system prompt"],
        "faulty_assumption": "Bỏ quên chi phí Input Token của System Prompt trong mỗi lượt gọi API",
        "citation": "T04-089",
        "slide": "Slide Day 1 · Trang 22",
        "review_slide": 22,
        "explanation": "Mỗi request gửi lên API đều phải gửi kèm toàn bộ System Prompt (chỉ thị nền tảng), do đó System Prompt được tính phí input cho MỌI câu chat.",
        "sub_question": "Nếu có 10.000 request/ngày, thì phần System Prompt dài 250 từ sẽ bị nhân lên bao nhiêu lần trong tổng hóa đơn API?"
    }
]

# Chuỗi câu hỏi gợi nhớ kết nối slide cũ
PRESET_FLOWS = {
    "d1": {
        6: {
            "title": "Trang 6: LLM là gì & Cơ chế hoạt động cốt lõi",
            "summary": "Mô hình ngôn ngữ lớn dự đoán token tiếp theo theo phân phối xác suất.",
            "prior_page": None,
            "bridge_concept": "Slide mở đầu nền tảng",
            "bridge_note": "Bản chất LLM là sinh token theo xác suất, không phải hiểu ngữ nghĩa tĩnh như con người.",
            "citations": ["T06-022", "T04-047"],
            "ai_question": "Bản chất của LLM là gì khi người dùng nhập câu hỏi vào?",
            "options": [
                {"id": "A", "text": "Mô hình ghi nhớ toàn bộ từ vựng và tra cứu như cuốn từ điển tĩnh.", "is_correct": False, "feedback": "Chưa chính xác: LLM không phải là cuốn từ điển tra từ vựng tĩnh."},
                {"id": "B", "text": "Mô hình tính toán xác suất thống kê để dự đoán và sinh ra từng token kế tiếp.", "is_correct": True, "feedback": "Chính xác! Ghi nhớ nguyên lý này để chuẩn bị bước sang Slide 12 về đơn vị tính Token."}
            ]
        },
        12: {
            "title": "Trang 12: Định nghĩa Token & Đặc thù Tiếng Việt",
            "summary": "Đơn vị tính cơ bản của LLM là Token, không phải từ. Tiếng Việt có dấu thanh tốn 1.3 - 1.4 lần token.",
            "prior_page": 6,
            "bridge_concept": "Dự đoán next-token (Slide 6) ➔ Đơn vị tính Token tiếng Việt (Slide 12)",
            "bridge_note": "Ở Slide 6, mô hình dự đoán theo 'token'. Sang Slide 12, giảng viên giải thích vì sao tiếng Việt tốn nhiều token hơn tiếng Anh.",
            "citations": ["T04-049"],
            "ai_question": "🔗 GỢI NHỚ TỪ SLIDE 6: Tại sao mô hình không đoán trực tiếp 'từ ngữ nguyên vẹn' mà phải chẻ nhỏ thành Token?",
            "options": [
                {"id": "A", "text": "Vì mô hình xử lý trên không gian toán học (embedding vector), và tiếng Việt có dấu cần chẻ thành sub-tokens.", "is_correct": True, "feedback": "Xuất sắc! Bạn đã kết nối đúng từ nguyên lý dự đoán xác suất (Slide 6) sang cơ chế mã hóa toán học của Token (Slide 12)."},
                {"id": "B", "text": "Vì tiếng Việt viết từ phải sang trái nên máy tính bắt buộc phải đổi sang token.", "is_correct": False, "feedback": "Chưa đúng: Tiếng Việt viết từ trái sang phải, việc chẻ token là do cấu trúc dấu thanh và âm tiết ghép."}
            ]
        },
        14: {
            "title": "Trang 14: Context Window & Giới Hạn Ngữ Cảnh",
            "summary": "Context Window là cửa sổ bối cảnh tối đa mà mô hình tiêu thụ trong một lần xử lý.",
            "prior_page": 12,
            "bridge_concept": "Hệ số Token tiếng Việt (Slide 12) ➔ Sức chứa Context Window (Slide 14)",
            "bridge_note": "Nếu quên tính hệ số 1.35x ở Slide 12, bạn sẽ ước lượng sai sức chứa Context Window ở Slide 14.",
            "citations": ["T04-051"],
            "ai_question": "🔗 KẾT NỐI VỚI SLIDE 12: Một tài liệu tiếng Việt dài 80.000 từ đưa vào mô hình có Context Window 100.000 token, liệu có bị tràn context không?",
            "options": [
                {"id": "A", "text": "Có nguy cơ tràn! Vì theo Slide 12, 80.000 từ tiếng Việt nhân hệ số ~1.35x tương đương ~108.000 token, vượt ngưỡng 100.000 token.", "is_correct": True, "feedback": "Chính xác tuyệt đối! Đây là lỗi rất phổ biến khi không liên kết giữa đơn vị từ tiếng Việt và token."},
                {"id": "B", "text": "Không tràn, vì 80.000 từ luôn luôn nhỏ hơn 100.000 token.", "is_correct": False, "feedback": "Sai lầm: 1 từ tiếng Việt không bằng 1 token! Cần nhân hệ số quy đổi ~1.35x."}
            ]
        },
        18: {
            "title": "Trang 18: Kiến Trúc Transformer & Self-Attention",
            "summary": "Xử lý song song, các token nhìn lẫn nhau trong ngữ cảnh, không bị quên như RNN/LSTM cũ.",
            "prior_page": 14,
            "bridge_concept": "Giới hạn đọc (Slide 14) ➔ Cơ chế 'nhìn song song' không bị quên (Slide 18)",
            "bridge_note": "Mô hình cũ đọc tuần tự nên càng về sau càng quên; Transformer cho các token nhìn nhau song song.",
            "citations": ["T06-086", "T06-127"],
            "ai_question": "🔗 GỢI NHỚ TỪ SLIDE 6 & 14: Trước Transformer, các mô hình cũ đọc từng từ từ trái sang phải và hay quên context dài (Slide 14). Transformer giải quyết điểm nghẽn này thế nào?",
            "options": [
                {"id": "A", "text": "Cơ chế Self-Attention cho phép TẤT CẢ các token nhìn nhau SONG SONG cùng lúc trong không gian toán học, không duyệt tuần tự.", "is_correct": True, "feedback": "Rất chuẩn! Bạn đã nắm được bước đột phá của Self-Attention so với cơ chế tuần tự cũ."},
                {"id": "B", "text": "Mô hình nâng cấp thêm thanh RAM trên GPU để nhớ tuần tự lâu hơn.", "is_correct": False, "feedback": "Chưa đúng: Bản chất là thay đổi kiến trúc thuật toán sang song song (Self-Attention), không phải chỉ tăng RAM."}
            ]
        },
        20: {
            "title": "Trang 20: Cơ Chế Toán Học: Q, K, V & Softmax",
            "summary": "Query, Key, Value biểu diễn vector; Softmax tính điểm tương đồng similarity score.",
            "prior_page": 18,
            "bridge_concept": "Các token nhìn nhau (Slide 18) ➔ Công thức toán học Q, K, V (Slide 20)",
            "bridge_note": "Khái niệm trực quan 'nhìn nhau' ở Slide 18 được hiện thực hóa bằng ma trận Q nhân K qua hàm Softmax ở Slide 20.",
            "citations": ["T06-130"],
            "ai_question": "🔗 KẾT NỐI VỚI SLIDE 18: Trong câu 'Con mèo bắt chuột vì nó đói', máy tính làm sao biết 'nó' đang chú ý vào 'mèo' hay 'chuột'?",
            "options": [
                {"id": "A", "text": "Query ('nó') nhân với Key ('mèo') qua Softmax tạo ra Similarity Score cao nhất, gán Value tương ứng.", "is_correct": True, "feedback": "Tuyệt đỉnh! Bạn đã bắc cầu hoàn hảo từ khái niệm trực quan ở Slide 18 sang công thức Q-K-V ở Slide 20."},
                {"id": "B", "text": "Mô hình tự động bốc thăm ngẫu nhiên từ nào đứng gần hơn.", "is_correct": False, "feedback": "Chưa đúng: Thuật toán tính ma trận tương đồng toán học có trọng số, không hề ngẫu nhiên."}
            ]
        },
        22: {
            "title": "Trang 22: Tham Số Temperature & Tính Tất Định",
            "summary": "Temperature = 0: chọn token xác suất cao nhất (deterministic). Temperature = 1: sáng tạo hơn.",
            "prior_page": 6,
            "bridge_concept": "Dự đoán xác suất (Slide 6) ➔ Điều khiển nhiệt độ Temperature (Slide 22)",
            "bridge_note": "Softmax ở Slide 20 tạo phân phối xác suất; Temperature ở Slide 22 sẽ làm dốc hoặc làm phẳng phân phối này.",
            "citations": ["T04-089"],
            "ai_question": "🔗 GỢI NHỚ TỪ SLIDE 6 & 20: Khi làm bài toán trích xuất hợp đồng tài chính chính xác tuyệt đối, bạn nên đặt Temperature bằng mấy?",
            "options": [
                {"id": "A", "text": "Đặt Temperature = 0 để mô hình luôn chọn token có xác suất cao nhất, đảm bảo tính tất định (deterministic).", "is_correct": True, "feedback": "Chính xác! Giảng viên đã nhấn mạnh điều này ở Slide 22 cho bài toán tài chính/y tế."},
                {"id": "B", "text": "Đặt Temperature = 1 để mô hình tự do sáng tạo thêm điều khoản mới.", "is_correct": False, "feedback": "Sai lầm: Trong tài chính, temperature = 1 sẽ gây rủi ro hallucination rất lớn."}
            ]
        },
        25: {
            "title": "Trang 25: Token Economy & Chi Phí Gọi API",
            "summary": "Tổng chi phí = Input Token + Output Token. Output token lại được feed-forward làm input tiếp theo.",
            "prior_page": 12,
            "bridge_concept": "Hệ số Token tiếng Việt (Slide 12) + Feed-forward (Slide 18) ➔ Bài toán Chi phí (Slide 25)",
            "bridge_note": "Bài toán thực tế: dự toán chi phí API cho doanh nghiệp dựa trên toàn bộ các slide trước.",
            "citations": ["T06-154"],
            "ai_question": "🔗 TỔNG HỢP TOÀN BỘ (SLIDE 12 ➔ 18 ➔ 25): Khi tính chi phí API cho chatbot tiếng Việt, điều gì xảy ra nếu bạn chỉ tính tiền số từ khách gõ?",
            "options": [
                {"id": "A", "text": "Sẽ bị hụt ngân sách nặng nề vì thiếu hệ số 1.35x tiếng Việt (Slide 12), token của System Prompt (Slide 22), và Output token feed-forward (Slide 25).", "is_correct": True, "feedback": "Chúc mừng bạn! Bạn đã hoàn thành trọn vẹn chuỗi bắc cầu lý thuyết xuyên suốt từ Slide 6 đến Slide 25!"},
                {"id": "B", "text": "Không sao, nhà cung cấp API sẽ tự động miễn phí phần System Prompt.", "is_correct": False, "feedback": "Sai lầm: Nhà cung cấp tính phí input token cho TOÀN BỘ request, bao gồm cả System Prompt."}
            ]
        }
    }
}

class PedagogyService:
    def is_key_milestone(self, deck: str, page: int) -> bool:
        return page in KEY_MILESTONES.get(deck, [6, 12, 18, 22, 25])

    def get_next_milestone(self, deck: str, page: int) -> Optional[int]:
        milestones = KEY_MILESTONES.get(deck, [6, 12, 18, 22, 25])
        next_pages = [p for p in milestones if p > page]
        return next_pages[0] if next_pages else None

    async def get_slide_question(self, deck: str, page: int, level: int = 1) -> SlideQuestionResponse:
        """Sinh câu hỏi Socratic kết nối slide theo năng lực học viên bằng GPT-4o-mini hoặc RAG fallback"""
        slide_text = rag_service.extract_slide_page(deck, page)
        is_checkpoint = self.is_key_milestone(deck, page)
        next_checkpoint = self.get_next_milestone(deck, page)
        level_label_map = {
            1: "Level 1 (Cơ bản)",
            2: "Level 2 (Vận dụng)",
            3: "Level 3 (Chuyên sâu)"
        }
        active_level_label = level_label_map.get(level, "Level 1 (Cơ bản)")

        variants = []

        # 1. Ưu tiên gọi GPT-4o-mini qua OpenRouter
        if openrouter_service.is_available():
            llm_res = await openrouter_service.generate_slide_question(
                deck=deck,
                page=page,
                slide_text=slide_text,
                prior_page=max(page - 1, 1) if page > 1 else None,
                level=level
            )
            if llm_res and "ai_question" in llm_res and "options" in llm_res:
                options = [
                    QuestionOption(
                        id=opt.get("id", "A"),
                        text=opt.get("text", ""),
                        is_correct=opt.get("is_correct", False),
                        feedback=opt.get("feedback", "")
                    )
                    for opt in llm_res["options"]
                ]
                preset_flow = PRESET_FLOWS.get(deck, {}).get(page, {})
                preset_prior = preset_flow.get("prior_page")
                primary = SlideQuestionResponse(
                    deck=deck,
                    page=page,
                    level=level,
                    level_label=llm_res.get("level_label", active_level_label),
                    is_checkpoint=is_checkpoint,
                    checkpoint_title=f"Trạm kiểm tra kiến thức (Slide {page})" if is_checkpoint else None,
                    title=llm_res.get("title", f"Trang {page}"),
                    summary=llm_res.get("summary", ""),
                    prior_page=preset_prior if preset_prior is not None else (page - 1 if page > 1 else None),
                    bridge_concept=llm_res.get("bridge_flow") or preset_flow.get("bridge_concept"),
                    bridge_note=llm_res.get("bridge_note") or preset_flow.get("bridge_note"),
                    ai_question=llm_res["ai_question"],
                    options=options,
                    citations=llm_res.get("citations") or preset_flow.get("citations", ["T04-049"]),
                    next_checkpoint=next_checkpoint,
                    questions=[]
                )
                variants = [
                    QuestionVariant(
                        id="v1",
                        question=primary.ai_question,
                        options=primary.options,
                        citations=primary.citations
                    )
                ]
                return primary

        # 2. Fallback sang kho câu hỏi mẫu chuẩn hóa
        deck_flow = PRESET_FLOWS.get(deck, PRESET_FLOWS["d1"])
        flow = deck_flow.get(page)
        if not flow:
            closest_page = max([p for p in deck_flow.keys() if p <= page], default=12)
            flow = deck_flow[closest_page]

        options = [
            QuestionOption(
                id=opt["id"],
                text=opt["text"],
                is_correct=opt["is_correct"],
                feedback=opt["feedback"]
            )
            for opt in flow["options"]
        ]

        primary = SlideQuestionResponse(
            deck=deck,
            page=page,
            level=level,
            level_label=active_level_label,
            is_checkpoint=is_checkpoint,
            checkpoint_title=f"Trạm kiểm tra kiến thức (Slide {page})" if is_checkpoint else None,
            title=flow["title"],
            summary=flow["summary"],
            prior_page=flow.get("prior_page"),
            bridge_concept=flow.get("bridge_concept"),
            bridge_note=flow.get("bridge_note"),
            ai_question=flow["ai_question"],
            options=options,
            citations=flow["citations"],
            next_checkpoint=next_checkpoint,
            questions=[
                QuestionVariant(
                    id="v1",
                    question=flow["ai_question"],
                    options=options,
                    citations=flow["citations"]
                )
            ]
        )

        # 3. Sinh 4 biến thể câu hỏi dựa trên cùng slide để UI có thể render nhiều dạng câu hỏi
        for idx in range(1, 5):
            if idx == 1:
                continue
            q_text = f"{flow['ai_question']} (Biến thể {idx})"
            q_options = [
                QuestionOption(
                    id=opt["id"],
                    text=opt["text"],
                    is_correct=opt["is_correct"],
                    feedback=opt["feedback"]
                )
                for opt in flow["options"]
            ]
            primary.questions.append(QuestionVariant(
                id=f"v{idx}",
                question=q_text,
                options=q_options,
                citations=flow["citations"]
            ))

        return primary

    async def evaluate_answer(self, req: StudentAnswerRequest) -> AnswerEvaluationResponse:
        """Đánh giá câu trả lời học viên bằng GPT-4o-mini hoặc Misconception Bank kèm chấm điểm và hướng dẫn ôn tập"""
        # 0. Nếu học viên click chọn phương án trắc nghiệm A/B đã có nhãn đúng/sai rõ ràng
        if req.is_option_correct is not None:
            is_correct = bool(req.is_option_correct)
            score = 100 if is_correct else 40
            grade = "Xuất sắc (Nắm vững bản chất)" if is_correct else "Cần củng cố (Lỗi ngộ nhận)"
            new_streak = req.current_streak + 1 if is_correct else 0
            new_level = min(req.current_level + 1, 3) if (is_correct and req.current_streak >= 1) else (
                req.current_level if is_correct else max(req.current_level - 1, 1)
            )
            should_level_up = is_correct and (new_level > req.current_level)

            thought = (
                f"Học viên đã phân tích chính xác câu hỏi '{req.question_text or f'Slide {req.page}'}' và chọn phương án đúng bản chất."
                if is_correct
                else f"Học viên chọn phương án chứa bẫy ngộ nhận (Misconception) của Slide {req.page}."
            )
            action = "validate_mastery_and_promote" if is_correct else "diagnose_misconception_and_scaffold"
            observation = "Khớp hoàn toàn với cơ sở lý thuyết bài giảng." if is_correct else "Lựa chọn này đi ngược lại nguyên lý vận hành được trình bày trên slide."
            decision = (
                f"Chấm 100/100 tuyệt đối, tăng streak lên {new_streak}" + (f", thăng cấp độ lên Level {new_level}." if should_level_up else ".")
                if is_correct
                else "Chấm 40/100, kích hoạt phản hồi Socratic gợi mở để học viên tự xem lại slide và sửa sai."
            )

            reasoning = {
                "thought": thought,
                "action": action,
                "observation": observation,
                "pedagogical_decision": decision
            }

            diagnostic = None
            if not is_correct:
                diagnostic = MisconceptionDiagnostic(
                    is_misconception=True,
                    faulty_assumption="Ngộ nhận khái niệm cốt lõi trong slide",
                    citation_id="T04-049",
                    slide_reference=f"Slide {req.page}",
                    transcript_excerpt="Vui lòng đối chiếu với slide bài giảng để làm rõ khái niệm.",
                    socratic_guidance=f"Hãy quan sát lại Slide {req.page} bên trái để phân biệt rõ bản chất nhé!"
                )

            feedback = (
                "🎉 Chính xác tuyệt đối! Bạn đã nắm rất vững bản chất kiến thức của slide này."
                if is_correct
                else "⚠️ Chưa chính xác. Phương án này phản ánh một ngộ nhận thường gặp trong thực tế."
            )

            return AnswerEvaluationResponse(
                is_correct=is_correct,
                score=score,
                grade=grade,
                feedback=feedback,
                diagnostic=diagnostic,
                new_streak=new_streak,
                new_level=new_level,
                should_level_up=should_level_up,
                should_scaffold=not is_correct,
                socratic_hint="Bạn đã nắm vững kiến thức! Hãy tiếp tục duy trì lập luận tốt ở các slide tiếp theo." if is_correct else f"Hãy nhìn lại Slide {req.page} để xem lý thuyết giải thích điều này thế nào.",
                review_recommendation="Bạn đã sẵn sàng học tiếp các slide tiếp theo!" if is_correct else f"Mở lại Slide {req.page} để xem lại khái niệm.",
                review_slide=None if is_correct else req.page,
                reasoning=reasoning,
                guardrail_triggered=False
            )

        # 1. Thử gọi GPT-4o-mini qua OpenRouter cho câu trả lời tự do
        deck_flow = PRESET_FLOWS.get(req.deck, PRESET_FLOWS.get("d1", {}))
        current_flow = deck_flow.get(req.page, {})

        if openrouter_service.is_available():
            slide_text = rag_service.extract_slide_page(req.deck, req.page)
            # Kết hợp thêm tóm tắt mốc kiến thức nếu có
            if current_flow.get("summary"):
                slide_text = f"{current_flow.get('summary')}\n{slide_text}"
            q_text = req.question_text or current_flow.get("ai_question") or f"Câu hỏi kiểm tra kiến thức Slide {req.page}"
            llm_eval = await openrouter_service.evaluate_answer(
                deck=req.deck,
                page=req.page,
                slide_text=slide_text,
                question_text=q_text,
                student_answer=req.answer_text,
                current_level=req.current_level,
                current_streak=req.current_streak,
                theta=float(req.theta) if req.theta is not None else 0.0,
                item_a=float(req.item_a) if req.item_a is not None else 1.0,
                item_b=float(req.item_b) if req.item_b is not None else 0.0,
                item_c=float(req.item_c) if req.item_c is not None else 0.2
            )
            if llm_eval:
                # Xử lý khi kích hoạt Guardrail an toàn sư phạm / chống injection
                if llm_eval.get("guardrail_triggered"):
                    return AnswerEvaluationResponse(
                        is_correct=False,
                        score=llm_eval.get("score", 0),
                        grade=llm_eval.get("grade", "Cảnh báo An toàn Sư phạm"),
                        feedback=llm_eval.get("feedback", "Yêu cầu bị chặn bởi Guardrail an toàn sư phạm."),
                        diagnostic=None,
                        new_streak=0,
                        new_level=req.current_level,
                        should_level_up=False,
                        should_scaffold=True,
                        socratic_hint=llm_eval.get("socratic_hint", "Hãy quan sát trực tiếp nội dung bài giảng để tự tìm ra câu trả lời!"),
                        review_recommendation=llm_eval.get("review_recommendation"),
                        review_slide=None,
                        reasoning=llm_eval.get("reasoning"),
                        guardrail_triggered=True
                    )

                is_correct = llm_eval.get("is_correct", False)
                is_misc = llm_eval.get("is_misconception", False)
                faulty = llm_eval.get("faulty_assumption")
                feedback = llm_eval.get("feedback", "")
                hint = llm_eval.get("socratic_hint", "")
                reasoning = llm_eval.get("reasoning")

                diagnostic = None
                if is_misc or faulty:
                    diagnostic = MisconceptionDiagnostic(
                        is_misconception=True,
                        faulty_assumption=faulty or "Giả định chưa chính xác",
                        citation_id="T04-049",
                        slide_reference=f"Slide {req.page}",
                        transcript_excerpt=slide_text[:200] if slide_text else "Tài liệu slide",
                        socratic_guidance=hint
                    )

                score = llm_eval.get("score", 100 if is_correct else (40 if is_misc else 60))
                grade = llm_eval.get("grade", "Xuất sắc (Hiểu sâu)" if is_correct else ("Cần củng cố (Lỗi ngộ nhận)" if is_misc else "Chưa đầy đủ"))
                review_rec = llm_eval.get("review_recommendation") or (
                    "Lập luận rất sắc bén! Bạn đã hiểu đúng bản chất và sẵn sàng học tiếp." if is_correct else (
                        f"Bạn cần xem lại Slide {req.page} để đính chính giả định: {faulty}" if faulty else f"Hãy đọc lại Slide {req.page}."
                    )
                )

                new_streak = llm_eval.get("new_streak", req.current_streak + 1 if is_correct else 0)
                new_level = llm_eval.get("new_level", min(req.current_level + 1, 3) if (is_correct and req.current_streak >= 1) else req.current_level)
                should_level_up = llm_eval.get("should_level_up", is_correct and req.current_streak >= 1 and req.current_level < 3)

                return AnswerEvaluationResponse(
                    is_correct=is_correct,
                    score=score,
                    grade=grade,
                    feedback=feedback,
                    diagnostic=diagnostic,
                    new_streak=new_streak,
                    new_level=new_level,
                    should_level_up=should_level_up,
                    should_scaffold=not is_correct,
                    socratic_hint=hint or f"Đối chiếu lại nội dung Slide {req.page} để tìm ra câu trả lời nhé!",
                    review_recommendation=review_rec,
                    review_slide=None if is_correct else req.page,
                    reasoning=reasoning,
                    guardrail_triggered=False
                )

        # 2. Fallback heuristic Misconception Bank
        text_lower = req.answer_text.lower()
        diagnostic = None
        matched_misc = None
        for item in MISCONCEPTION_BANK:
            if any(kw in text_lower for kw in item["keywords"]):
                citation_data = rag_service.get_citation(item["citation"])
                diagnostic = MisconceptionDiagnostic(
                    is_misconception=True,
                    faulty_assumption=item["faulty_assumption"],
                    citation_id=item["citation"],
                    slide_reference=item["slide"],
                    transcript_excerpt=citation_data["text"] if citation_data else item["explanation"],
                    socratic_guidance=f"{item['explanation']} {item['sub_question']}"
                )
                matched_misc = item
                break

        if diagnostic and matched_misc:
            rev_slide = matched_misc.get("review_slide", req.page)
            return AnswerEvaluationResponse(
                is_correct=False,
                score=40,
                grade="Cần củng cố (Mắc lỗi ngộ nhận)",
                feedback=f"⚠️ Phát hiện giả định sai: {diagnostic.faulty_assumption}",
                diagnostic=diagnostic,
                new_streak=0,
                new_level=max(req.current_level - 1, 1),
                should_level_up=False,
                should_scaffold=True,
                socratic_hint=f"Đối chiếu đoạn [{diagnostic.citation_id}]: {diagnostic.socratic_guidance}",
                review_recommendation=f"Bạn cần mở lại {matched_misc['slide']} để hiểu rõ: {matched_misc['explanation']}",
                review_slide=rev_slide
            )

        # 3. Kiểm tra xem người dùng có chọn trực tiếp một trong các phương án A/B của slide mốc này không
        deck_flow = PRESET_FLOWS.get(req.deck, PRESET_FLOWS.get("d1", {}))
        current_flow = deck_flow.get(req.page)
        if current_flow:
            for opt in current_flow.get("options", []):
                # Khớp phương án theo ID (A/B) hoặc nội dung văn bản
                if req.answer_text.strip() == opt["id"] or opt["text"].lower() in text_lower or text_lower in opt["text"].lower():
                    if opt["is_correct"]:
                        new_streak = req.current_streak + 1
                        new_level = req.current_level + 1 if new_streak >= STREAK_FOR_LEVEL_UP and req.current_level < MAX_ADAPTIVE_LEVEL else req.current_level
                        return AnswerEvaluationResponse(
                            is_correct=True,
                            score=100,
                            grade="Xuất sắc (Nắm vững bản chất)",
                            feedback=f"🎉 {opt['feedback']}",
                            diagnostic=None,
                            new_streak=new_streak,
                            new_level=new_level,
                            should_level_up=new_streak >= STREAK_FOR_LEVEL_UP,
                            should_scaffold=False,
                            socratic_hint="Hãy tiếp tục duy trì lập luận chặt chẽ khi đọc các slide tiếp theo!",
                            review_recommendation="Bạn đã nắm rất vững kiến thức mốc này! Hãy tự tin tiếp tục học các slide tiếp theo.",
                            review_slide=None
                        )
                    else:
                        rev_target = current_flow.get("prior_page") or req.page
                        return AnswerEvaluationResponse(
                            is_correct=False,
                            score=40,
                            grade="Cần củng cố (Chưa chính xác)",
                            feedback=f"⚠️ {opt['feedback']}",
                            diagnostic=None,
                            new_streak=0,
                            new_level=req.current_level,
                            should_level_up=False,
                            should_scaffold=True,
                            socratic_hint=f"Quan sát lại Slide {rev_target} để tìm ra mối liên hệ chính xác.",
                            review_recommendation=f"Bạn cần mở lại Slide {rev_target} để ôn tập: {current_flow.get('bridge_note') or current_flow.get('summary')}",
                            review_slide=rev_target
                        )

        # 4. Kiểm tra câu trả lời tự do có lý luận tốt (từ khóa cốt lõi)
        is_correct = any(kw in text_lower for kw in ["1.3", "1.4", "hệ số", "sub-token", "vector", "song song", "softmax", "deterministic", "system prompt"])

        if is_correct:
            new_streak = req.current_streak + 1
            new_level = req.current_level
            should_level_up = False
            if new_streak >= STREAK_FOR_LEVEL_UP and new_level < MAX_ADAPTIVE_LEVEL:
                new_level += 1
                new_streak = 0
                should_level_up = True

            return AnswerEvaluationResponse(
                is_correct=True,
                score=100,
                grade="Xuất sắc (Hiểu sâu bản chất)",
                feedback="🎉 Chính xác tuyệt đối! Bạn đã bắc cầu lý thuyết thành công vào bài toán thực tế.",
                diagnostic=None,
                new_streak=new_streak,
                new_level=new_level,
                should_level_up=should_level_up,
                should_scaffold=False,
                socratic_hint="Hãy tiếp tục duy trì lập luận chặt chẽ khi học tiếp!",
                review_recommendation="Bạn đã nắm rất vững kiến thức này. Hãy cuộn xuống các slide tiếp theo để học kiến thức mới!",
                review_slide=None
            )

        # 4. Câu trả lời chưa rõ ràng
        return AnswerEvaluationResponse(
            is_correct=False,
            score=60,
            grade="Chưa chính xác",
            feedback="Câu trả lời của bạn có hướng suy nghĩ tốt nhưng chưa đủ cơ sở dữ liệu.",
            diagnostic=None,
            new_streak=0,
            new_level=req.current_level,
            should_level_up=False,
            should_scaffold=True,
            socratic_hint=f"Tại Slide {req.page}, hãy đọc lại sơ đồ trên slide và đối chiếu với slide trước xem sự khác biệt nằm ở đâu?",
            review_recommendation=f"Bạn cần quan sát kỹ lại sơ đồ minh họa tại Slide {req.page}.",
            review_slide=req.page
        )

    async def answer_student_query(self, req: StudentChatRequest) -> StudentChatResponse:
        """Đồng hành đàm thoại: giải thích bản chất, đưa ví dụ thực tế hoặc gợi mở tư duy tích hợp RAG"""
        msg_lower = req.message.lower().strip()
        deck_flow = PRESET_FLOWS.get(req.deck, PRESET_FLOWS.get("d1", {}))
        current_flow = deck_flow.get(req.page, {})

        # RAG Layer 1: Trích xuất nội dung bài giảng trực tiếp từ trang Slide PDF
        slide_text = rag_service.extract_slide_page(req.deck, req.page)

        # RAG Layer 2: Truy xuất thông tin (RAG Search) từ kho 700 đoạn transcript bài giảng của giảng viên
        relevant_transcripts = rag_service.search_transcripts(req.message, limit=3)
        transcript_context = "\n".join([f"[{t['id']}] {t['text']}" for t in relevant_transcripts])
        rag_citations = [t["id"] for t in relevant_transcripts] or current_flow.get("citations", [])

        q_text = req.question_context or current_flow.get("ai_question") or f"Câu hỏi Slide {req.page}"

        # 1. Phát hiện Intent của học viên
        intent = "general"
        if any(kw in msg_lower for kw in ["ví dụ", "thực tế", "minh họa", "ứng dụng", "tình huống"]):
            intent = "example"
        elif any(kw in msg_lower for kw in ["bản chất", "nghĩa là gì", "tại sao", "là gì", "giải thích", "cơ chế"]):
            intent = "concept"
        elif any(kw in msg_lower for kw in ["gợi ý", "hint", "manh mối", "chỉ dẫn", "bắt đầu từ đâu"]):
            intent = "hint"

        # 2. Nếu người dùng hỏi xin đáp án trực tiếp: Từ chối khéo sư phạm
        if any(kw in msg_lower for kw in ["đáp án", "chọn câu nào", "chọn gì", "a hay b", "giải hộ", "kết quả"]):
            return StudentChatResponse(
                reply="💡 Tôi đóng vai trò là trợ giảng đồng hành giúp bạn tự nắm vững bản chất, không thể đưa ra đáp án trực tiếp. Bạn hãy quan sát kỹ từ khóa cốt lõi trên slide bên trái để tự tin đưa ra phán đoán nhé!",
                intent="hint",
                citations=rag_citations
            )

        # 3. Ưu tiên gọi GPT-4o-mini qua OpenRouter kết hợp bối cảnh RAG
        if openrouter_service.is_available():
            llm_reply = await openrouter_service.chat_socratic(
                deck=req.deck,
                page=req.page,
                slide_text=slide_text,
                question_text=q_text,
                user_message=req.message,
                transcript_context=transcript_context,
                level=req.current_level
            )
            if llm_reply:
                return StudentChatResponse(
                    reply=llm_reply,
                    intent=intent,
                    citations=rag_citations
                )

        # 4. Fallback thông minh dựa trên ngữ cảnh Slide & Intent
        citations = rag_citations
        if intent == "example":
            if req.page == 6:
                reply = "📌 **Ví dụ thực tế**: Hệ chuyên gia kinh điển như hệ thống MYCIN trong y tế (dùng hàng nghìn luật IF-THEN do bác sĩ nạp thủ công để chẩn đoán nhiễm trùng máu). Khác với LLM ngày nay tự học phân phối xác suất từ hàng nghìn tỷ từ trên Internet, Hệ chuyên gia bắt buộc phải có chuyên gia con người 'cầm tay chỉ việc' nạp từng luật trong miền tri thức hẹp."
            elif req.page == 12:
                reply = "📌 **Ví dụ thực tế**: Từ tiếng Anh 'apple' chỉ tính 1 token. Nhưng từ tiếng Việt 'quả táo' có dấu thanh, bộ BPE tokenizer chẻ thành 3 sub-token ('qu', 'ả', 'táo'). Vì vậy, một tài liệu 10.000 từ tiếng Việt khi gọi API OpenAI sẽ bị tính thành ~13.500 - 14.000 token, khiến chi phí hóa đơn API tăng ~35% so với tiếng Anh!"
            elif req.page == 14:
                reply = "📌 **Ví dụ thực tế**: Context Window giống như chiếc bàn làm việc. Nếu bạn muốn mô hình tóm tắt một cuốn sách dày 500 trang (~150.000 token) nhưng model chỉ có bàn chứa 32.000 token, những trang sách đầu tiên sẽ bị 'rơi khỏi bàn' và model hoàn toàn không đọc được chúng khi trả lời câu hỏi ở trang cuối."
            elif req.page == 18:
                reply = "📌 **Ví dụ thực tế**: Trong câu 'Con báo rượt theo con thỏ vì nó đói', cơ chế Self-Attention giúp mô hình tính toán trọng số tương quan song song giữa từ 'nó' với 'con báo' (đói) cao hơn hẳn so với 'con thỏ', giúp dịch chuẩn xác mà không bị nhầm lẫn như các mô hình duyệt tuần tự cũ."
            else:
                reply = f"📌 **Ví dụ thực tế cho Slide {req.page}**: {current_flow.get('summary') or 'Trong thực tế phát triển sản phẩm AI, việc nắm rõ cơ chế này giúp bạn tối ưu hóa cả về mặt chi phí và chất lượng phản hồi cho người dùng cuối.'}"
        elif intent == "concept":
            summary = current_flow.get("summary") or "Khái niệm này là nền tảng cốt lõi trong kiến trúc AI hiện đại."
            note = current_flow.get("bridge_note") or "Quan sát kỹ sự dịch chuyển giữa các slide bài giảng để thấy rõ bản chất."
            reply = f"🔍 **Bản chất cốt lõi**: {summary}\n\n💡 *Góc nhìn chuyên sâu*: {note}"
        elif intent == "hint":
            note = current_flow.get("bridge_note") or "Hãy đối chiếu giữa dữ liệu slide trước và slide hiện tại."
            reply = f"💡 **Gợi ý tư duy**: {note}\nBạn hãy xem kỹ câu hỏi trắc nghiệm bên trên: phương án nào đi ngược lại nguyên lý vận hành này chính là bẫy ngộ nhận!"
        else:
            reply = f"🤖 Tôi đang đồng hành cùng bạn tại Slide {req.page}. Bạn có thể bấm các nút gợi ý nhanh bên dưới để nhận ví dụ thực tế hoặc giải thích bản chất khái niệm nhé!"

        return StudentChatResponse(
            reply=reply,
            intent=intent,
            citations=citations
        )

pedagogy_service = PedagogyService()


