"""
Socratic Pedagogy & Misconception Diagnostic Service
Implements Block 1 & Block 2 of Sequence Diagram
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
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
from backend.services.rag_service import rag_service, VectorSpaceRAG, VIETNAMESE_STOP_WORDS
from backend.services.openAI_service import openrouter_service
from backend.services.analytics_service import evaluate_learner_by_theta
from backend.services.memory_service import memory_service
from backend.config import (
    STREAK_FOR_LEVEL_UP,
    MAX_ADAPTIVE_LEVEL,
    MISCONCEPTIONS_FILE,
    PRESET_FLOWS_FILE,
    SLIDES_DIR
)
import random

def get_total_slides(deck: str = "d1") -> int:
    """Đọc động số lượng trang thực tế từ file PDF bằng PyMuPDF hoặc PyPDF, không hardcode số trang."""
    candidates = list(SLIDES_DIR.glob(f"{deck}*.pdf"))
    pdf_path = candidates[0] if candidates else (SLIDES_DIR / ("d1-slide-hackathon.pdf" if deck == "d1" else "d2-slide-hackathon.pdf"))
    if pdf_path.exists():
        try:
            import pymupdf
            doc = pymupdf.open(str(pdf_path))
            return len(doc)
        except Exception:
            try:
                import pypdf
                reader = pypdf.PdfReader(str(pdf_path))
                return len(reader.pages)
            except Exception:
                pass
    return 29

def generate_milestones(total_slides: Optional[int] = None, min_slides: int = 5, max_slides: int = 8, deck: str = "d1") -> List[int]:
    """Sinh danh sách các mốc slide ngẫu nhiên (dynamic milestones) cho phiên học theo số trang thực tế của PDF."""
    if total_slides is None:
        total_slides = get_total_slides(deck)
    # Đảm bảo các mốc chuẩn cốt lõi (như slide 6, 12 cho d1) luôn có mặt nếu file PDF có đủ trang
    core_anchors = [p for p in ([6, 12] if deck == "d1" else [5, 11]) if p <= total_slides]
    pool = [p for p in range(1, total_slides + 1) if p not in core_anchors]
    target_count = random.randint(min(min_slides, total_slides), min(max_slides, total_slides))
    needed_extra = max(0, target_count - len(core_anchors))
    extra = random.sample(pool, min(needed_extra, len(pool)))
    return sorted(core_anchors + extra)

# Checkpoint mốc ngẫu nhiên sinh động cho từng bộ slide, tính động theo số trang thực tế của PDF
KEY_MILESTONES = {
    "d1": generate_milestones(deck="d1"),
    "d2": generate_milestones(deck="d2")
}

# ==============================================================================
# SEMANTIC MISCONCEPTION ENGINE (Tách dữ liệu ra ngoài & Semantic Vector Matching)
# ==============================================================================
class SemanticMisconceptionMatcher:
    """
    Bộ máy quản lý và so khớp ngộ nhận thông minh:
    1. Tách dữ liệu ra file riêng: Đọc động từ Data/vlearn-pack/misconceptions.json.
    2. Semantic Vector Matching: Dùng Vector Space Model (TF-IDF Cosine Similarity) index toàn bộ
       ngữ nghĩa (faulty_assumption, explanation, semantic_examples).
    3. LLM Integration: Truyền danh sách misconceptions vào prompt để LLM phân loại ngữ nghĩa.
    4. Fallback an toàn: Hỗ trợ keywords nếu từ khóa khớp tuyệt đối.
    """
    def __init__(self, file_path: Path = MISCONCEPTIONS_FILE):
        self.file_path = file_path
        self.bank: List[Dict[str, Any]] = []
        self.vector_engine: Optional[VectorSpaceRAG] = None
        self.load_bank()

    def load_bank(self):
        """Nạp dữ liệu từ file misconceptions.json hoặc database"""
        try:
            if self.file_path.exists():
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    self.bank = data
                    self._build_vector_index()
                    return
        except Exception as e:
            print(f"[MisconceptionMatcher] Error loading from {self.file_path}: {e}")
            self.bank = []


    def _build_vector_index(self):
        """Xây dựng Vector Space Model trên tập dữ liệu ngộ nhận (chỉ index giả định sai & ví dụ ngộ nhận)"""
        docs = {}
        for item in self.bank:
            doc_id = item["id"]
            examples = " ".join(item.get("semantic_examples", []))
            keywords = " ".join(item.get("keywords", []))
            # Chỉ index giả định sai, ví dụ ngộ nhận và từ khóa ngộ nhận (không index lời giải thích đính chính)
            text = f"{item.get('faulty_assumption', '')} {examples} {keywords}"
            docs[doc_id] = {
                "id": doc_id,
                "text": text,
                "item": item
            }
        self.vector_engine = VectorSpaceRAG(docs)

    def reload(self):
        """Hỗ trợ reload động khi cập nhật file hoặc DB tại runtime"""
        self.load_bank()

    def get_all(self) -> List[Dict[str, Any]]:
        if not self.bank:
            self.load_bank()
        return self.bank

    def find_by_assumption(self, faulty_assumption: str) -> Optional[Dict[str, Any]]:
        """Tìm ngộ nhận dựa trên tên giả định sai do LLM trả về"""
        if not faulty_assumption:
            return None
        target = faulty_assumption.lower().strip()
        for item in self.bank:
            if item.get("faulty_assumption", "").lower() in target or target in item.get("faulty_assumption", "").lower():
                return item
        # Thử semantic match
        res = self.match(faulty_assumption, threshold=0.20)
        return res[0] if res else None

    def match(self, student_answer: str, threshold: float = 0.20) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Khớp ngộ nhận bằng Semantic Vector Matching kết hợp dự phòng từ khóa:
        1. Kiểm tra nếu học viên đưa ra lập luận đúng (sub-token, 1.35x, song song...) thì không đánh đồng ngộ nhận
        2. Tính Cosine Similarity trên Vector Space Model với các semantic examples & faulty assumptions
        3. Kiểm tra keywords nếu có
        """
        if not student_answer or not self.bank:
            return None

        text_lower = student_answer.lower()
        # Nếu học viên đang giải thích đúng với các từ khóa bản chất thì không coi là ngộ nhận
        correct_indicators = ["1.35", "hệ số", "sub-token", "song song", "softmax"]
        bank_keywords = [
            kw.lower()
            for item in self.bank
            for kw in item.get("keywords", [])
        ]
        if any(ci in text_lower for ci in correct_indicators) and not any(kw in text_lower for kw in bank_keywords):
            return None

        # 1. Semantic Similarity Search qua Vector Space
        if self.vector_engine:
            results = self.vector_engine.search(student_answer, limit=1)
            if results:
                score, doc = results[0]
                if score >= threshold:
                    return doc["item"], float(score)

        # 2. Keywords Fallback
        for item in self.bank:
            if any(kw.lower() in text_lower for kw in item.get("keywords", [])):
                return item, 1.0

        return None

    def get_misconceptions_for_slide(self, page: int, deck: str = "d1", slide_text: str = "") -> List[Dict[str, Any]]:
        """Lấy danh sách ngộ nhận mục tiêu của giáo viên tương ứng với slide hoặc chủ đề."""
        matched = [
            item for item in self.bank
            if item.get("review_slide") == page or (isinstance(item.get("slide"), str) and f"Trang {page}" in item.get("slide", ""))
        ]
        if matched:
            return matched

        # Nếu chưa tìm thấy theo số trang, dùng Vector Engine để tìm ngộ nhận có ngữ nghĩa sát với slide_text
        if slide_text and self.vector_engine:
            results = self.vector_engine.search(slide_text, limit=2)
            res_items = []
            for score, doc in results:
                if score > 0.05:
                    item = doc.get("item")
                    if item and item not in res_items:
                        res_items.append(item)
            if res_items:
                return res_items

        return self.bank[:2] if self.bank else []


# Khởi tạo singleton matcher & export MISCONCEPTION_BANK
misconception_matcher = SemanticMisconceptionMatcher()
MISCONCEPTION_BANK = misconception_matcher.bank


# Tải chuỗi câu hỏi gợi nhớ kết nối slide từ tệp cấu hình bên ngoài (Data/vlearn-pack/preset_flows.json)
def load_preset_flows(file_path: Path = PRESET_FLOWS_FILE) -> Dict[str, Dict[int, Any]]:
    """Đọc dữ liệu preset flows từ file json và chuẩn hóa số trang thành integer."""
    if file_path.exists():
        try:
            raw_data = json.loads(file_path.read_text(encoding="utf-8"))
            flows = {}
            for deck, pages in raw_data.items():
                flows[deck] = {int(p): flow for p, flow in pages.items()}
            return flows
        except Exception as e:
            print(f"[PedagogyService] Lỗi khi tải preset flows từ {file_path}: {e}")
    return {}

PRESET_FLOWS = load_preset_flows()

class PedagogyService:
    def get_milestones(self, deck: str = "d1", refresh: bool = False) -> List[int]:
        """Lấy hoặc làm mới danh sách mốc checkpoints ngẫu nhiên cho session bài giảng theo số trang thực tế của PDF."""
        if refresh or deck not in KEY_MILESTONES:
            total_slides = get_total_slides(deck)
            KEY_MILESTONES[deck] = generate_milestones(total_slides=total_slides, min_slides=5, max_slides=8, deck=deck)
        return KEY_MILESTONES.get(deck, [6, 12])

    def is_key_milestone(self, deck: str, page: int) -> bool:
        return page in self.get_milestones(deck)

    def get_next_milestone(self, deck: str, page: int) -> Optional[int]:
        milestones = self.get_milestones(deck)
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

        # Lấy danh sách ngộ nhận mục tiêu của giáo viên cho slide này
        target_misconceptions = misconception_matcher.get_misconceptions_for_slide(page=page, deck=deck, slide_text=slide_text)

        # 1. Ưu tiên gọi GPT-4o-mini qua OpenRouter để tự động sinh câu hỏi tình huống chống học vẹt
        if openrouter_service.is_available():
            llm_res = await openrouter_service.generate_slide_question(
                deck=deck,
                page=page,
                slide_text=slide_text,
                prior_page=max(page - 1, 1) if page > 1 else None,
                level=level,
                misconceptions=target_misconceptions
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
                    questions=[],
                    source="LLM (GPT-4o-mini)"
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

        # 2. Lấy câu hỏi mẫu hoặc sinh động từ slide_text & ngân hàng ngộ nhận nếu slide này chưa có mẫu
        deck_flow = PRESET_FLOWS.get(deck, PRESET_FLOWS.get("d1", {}))
        flow = deck_flow.get(page)
        if not flow:
            prior_candidates = [p for p in deck_flow.keys() if p < page]
            prior_p = max(prior_candidates) if prior_candidates else (max(page - 1, 1) if page > 1 else None)

            clean_lines = [line.strip() for line in (slide_text or "").split("\n") if line.strip()]
            first_line = clean_lines[0] if clean_lines else f"Chủ đề trọng tâm Slide {page}"
            summary_snippet = " ".join(clean_lines[1:4]) if len(clean_lines) > 1 else f"Nội dung và nguyên lý tại Slide {page}."

            rel_misc = target_misconceptions[0] if target_misconceptions else None
            misc_fault = rel_misc.get("faulty_assumption", "Hiểu nhầm nguyên lý hoặc áp dụng công thức sai lệch") if rel_misc else "Suy diễn cảm tính không dựa trên bài giảng"
            misc_exp = rel_misc.get("explanation", "Nguyên lý kỹ thuật được xác thực trên bài giảng chính thống.") if rel_misc else "Nắm vững nguyên lý và điều kiện áp dụng."
            misc_cit = rel_misc.get("citation", "T04-049") if rel_misc else "T04-049"

            if level == 1:
                q_stem = f"Tại Slide {page} ({first_line[:50]}): Đâu là nhận định phản ánh chính xác nhất bản chất nội dung này?"
            elif level == 2:
                q_stem = f"Vận dụng kiến thức Slide {page} ({first_line[:45]}): Khi giải quyết bài toán thực tế, nhận định nào sau đây là chuẩn xác?"
            else:
                q_stem = f"Phân tích chuyên sâu Slide {page} ({first_line[:45]}): Điểm cốt lõi nào cần tối ưu để khắc phục hạn chế hoặc rủi ro?"

            flow = {
                "title": f"Trang {page}: {first_line[:60]}",
                "summary": summary_snippet[:200] or f"Khái niệm tại Slide {page}.",
                "prior_page": prior_p,
                "bridge_concept": f"Liên kết từ Slide {prior_p or 1} sang Slide {page}",
                "bridge_note": f"Đối chiếu các nguyên lý trước đó để làm chủ nội dung Slide {page}.",
                "citations": [misc_cit],
                "ai_question": q_stem,
                "options": [
                    {
                        "id": "A",
                        "text": f"Đúng theo nguyên lý: {misc_exp[:140]}",
                        "is_correct": True,
                        "feedback": f"Chính xác! Bạn đã hiểu đúng bản chất nội dung Slide {page}."
                    },
                    {
                        "id": "B",
                        "text": f"Bẫy ngộ nhận: {misc_fault[:140]}",
                        "is_correct": False,
                        "feedback": f"Chưa chính xác: Đây là ngộ nhận phổ biến. Hãy xem lại nội dung tại Slide {page}."
                    },
                    {
                        "id": "C",
                        "text": f"Hiểu sai rằng toàn bộ cơ chế tại Slide {page} chỉ hoạt động tuần tự độc lập ngữ cảnh.",
                        "is_correct": False,
                        "feedback": f"Sai lầm kỹ thuật: Mô hình yêu cầu sự tương quan và xử lý dữ liệu chặt chẽ."
                    },
                    {
                        "id": "D",
                        "text": f"Bỏ qua các tham số và điều kiện biên được mô tả tại Slide {page}.",
                        "is_correct": False,
                        "feedback": f"Chưa đúng: Cần quan sát kỹ các tham số kỹ thuật tại Slide {page}."
                    }
                ]
            }

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
            source="preset",
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

    def _record_evaluation_memory(self, student_id: str, page: int, result: AnswerEvaluationResponse):
        """Tự động ghi nhận lỗi ngộ nhận hoặc kiến thức đã làm chủ vào bộ nhớ dài hạn LTM của học viên"""
        try:
            if result.diagnostic and result.diagnostic.is_misconception:
                memory_service.record_misconception(student_id, page, result.diagnostic.faulty_assumption)
            elif result.is_correct:
                memory_service.record_mastery(student_id, page, f"Slide {page}")
        except Exception as e:
            print(f"[PedagogyService] Error updating memory: {e}")

    async def evaluate_answer(self, req: StudentAnswerRequest) -> AnswerEvaluationResponse:
        """Đánh giá câu trả lời học viên bằng ReAct Pattern và cập nhật bộ nhớ nhận thức dài hạn LTM"""
        result = await self._evaluate_answer_impl(req)
        self._record_evaluation_memory(req.student_id, req.page, result)
        return result

    async def _evaluate_answer_impl(self, req: StudentAnswerRequest) -> AnswerEvaluationResponse:
        theta = float(req.theta) if req.theta is not None else 0.0
        item_a = float(req.item_a) if req.item_a is not None else 1.0
        item_b = float(req.item_b) if req.item_b is not None else 0.0
        item_c = float(req.item_c) if req.item_c is not None else 0.2

        # 0. Nếu học viên click chọn phương án trắc nghiệm A/B đã có nhãn đúng/sai rõ ràng
        if req.is_option_correct is not None:
            is_correct = bool(req.is_option_correct)
            theta_eval = evaluate_learner_by_theta(
                theta=theta,
                is_correct=is_correct,
                a=item_a,
                b=item_b,
                c=item_c,
                current_level=req.current_level,
                current_streak=req.current_streak
            )

            thought = (
                f"Học viên đã phân tích chính xác câu hỏi '{req.question_text or f'Slide {req.page}'}' và chọn phương án đúng bản chất. Đánh giá is_correct = true."
                if is_correct
                else f"Học viên chọn phương án chứa bẫy ngộ nhận (Misconception) của Slide {req.page}. Đánh giá is_correct = false."
            )
            action = f"call_function update_theta(theta={theta}, is_correct={is_correct}, a={item_a}, b={item_b}, c={item_c})"
            observation = theta_eval["reasoning_observation"]
            decision = theta_eval["pedagogical_decision"]

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
                score=theta_eval["score"],
                grade=theta_eval["grade"],
                feedback=feedback,
                diagnostic=diagnostic,
                new_streak=theta_eval["new_streak"],
                new_level=theta_eval["new_level"],
                should_level_up=theta_eval["should_level_up"],
                should_scaffold=theta_eval["should_scaffold"],
                socratic_hint="Bạn đã nắm vững kiến thức! Hãy tiếp tục duy trì lập luận tốt ở các slide tiếp theo." if is_correct else f"Hãy nhìn lại Slide {req.page} để xem lý thuyết giải thích điều này thế nào.",
                review_recommendation="Bạn đã sẵn sàng học tiếp các slide tiếp theo!" if is_correct else f"Mở lại Slide {req.page} để xem lại khái niệm.",
                review_slide=None if is_correct else req.page,
                reasoning=reasoning,
                guardrail_triggered=False,
                theta=theta_eval["theta"],
                new_theta=theta_eval["new_theta"],
                p3pl_prob=theta_eval["p3pl_prob"]
            )

        # 1. Thử gọi GPT-4o-mini qua OpenRouter cho câu trả lời tự do
        deck_flow = PRESET_FLOWS.get(req.deck, PRESET_FLOWS.get("d1", {}))
        current_flow = deck_flow.get(req.page, {})

        if openrouter_service.is_available():
            slide_text = rag_service.extract_slide_page(req.deck, req.page)
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
                theta=theta,
                item_a=item_a,
                item_b=item_b,
                item_c=item_c,
                misconceptions=misconception_matcher.get_all()
            )
            if llm_eval:
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
                matched_item = None
                if is_misc and faulty:
                    matched_item = misconception_matcher.find_by_assumption(faulty)
                elif not is_correct:
                    # Semantic vector match trực tiếp từ câu trả lời
                    match_res = misconception_matcher.match(req.answer_text)
                    if match_res:
                        matched_item, _ = match_res
                        is_misc = True
                        faulty = matched_item["faulty_assumption"]

                if matched_item:
                    citation_data = rag_service.get_citation(matched_item.get("citation", "T04-049"))
                    diagnostic = MisconceptionDiagnostic(
                        is_misconception=True,
                        faulty_assumption=matched_item["faulty_assumption"],
                        citation_id=matched_item.get("citation", "T04-049"),
                        slide_reference=matched_item.get("slide", f"Slide {req.page}"),
                        transcript_excerpt=citation_data["text"] if citation_data else matched_item.get("explanation", ""),
                        socratic_guidance=matched_item.get("sub_question", hint)
                    )
                elif is_misc or faulty:
                    diagnostic = MisconceptionDiagnostic(
                        is_misconception=True,
                        faulty_assumption=faulty or "Giả định chưa chính xác",
                        citation_id="T04-049",
                        slide_reference=f"Slide {req.page}",
                        transcript_excerpt=slide_text[:200] if slide_text else "Tài liệu slide",
                        socratic_guidance=hint
                    )

                review_rec = llm_eval.get("review_recommendation") or (
                    "Lập luận rất sắc bén! Bạn đã hiểu đúng bản chất và sẵn sàng học tiếp." if is_correct else (
                        f"Bạn cần xem lại Slide {req.page} để đính chính giả định: {faulty}" if faulty else f"Hãy đọc lại Slide {req.page}."
                    )
                )

                return AnswerEvaluationResponse(
                    is_correct=is_correct,
                    score=llm_eval.get("score", 100 if is_correct else 40),
                    grade=llm_eval.get("grade", "Đạt yêu cầu"),
                    feedback=feedback,
                    diagnostic=diagnostic,
                    new_streak=llm_eval.get("new_streak", req.current_streak + 1 if is_correct else 0),
                    new_level=llm_eval.get("new_level", req.current_level),
                    should_level_up=llm_eval.get("should_level_up", False),
                    should_scaffold=llm_eval.get("should_scaffold", not is_correct),
                    socratic_hint=hint or f"Đối chiếu lại nội dung Slide {req.page} để tìm ra câu trả lời nhé!",
                    review_recommendation=review_rec,
                    review_slide=None if is_correct else req.page,
                    reasoning=reasoning,
                    guardrail_triggered=False,
                    theta=llm_eval.get("theta", theta),
                    new_theta=llm_eval.get("new_theta", theta),
                    p3pl_prob=llm_eval.get("p3pl_prob")
                )

        # 2. Fallback heuristic Misconception Bank (Semantic Vector Matching + Keywords)
        text_lower = req.answer_text.lower()
        diagnostic = None
        matched_misc = None
        match_result = misconception_matcher.match(req.answer_text)
        if match_result:
            matched_misc, match_score = match_result
            citation_data = rag_service.get_citation(matched_misc.get("citation", "T04-049"))
            diagnostic = MisconceptionDiagnostic(
                is_misconception=True,
                faulty_assumption=matched_misc["faulty_assumption"],
                citation_id=matched_misc.get("citation", "T04-049"),
                slide_reference=matched_misc.get("slide", f"Slide {req.page}"),
                transcript_excerpt=citation_data["text"] if citation_data else matched_misc.get("explanation", ""),
                socratic_guidance=f"{matched_misc.get('explanation', '')} {matched_misc.get('sub_question', '')}"
            )

        if diagnostic and matched_misc:
            rev_slide = matched_misc.get("review_slide", req.page)
            theta_eval = evaluate_learner_by_theta(
                theta=theta,
                is_correct=False,
                a=item_a,
                b=item_b,
                c=item_c,
                current_level=req.current_level,
                current_streak=req.current_streak
            )
            reasoning = {
                "thought": f"Phát hiện ngộ nhận qua Misconception Bank: {diagnostic.faulty_assumption}. Đánh giá is_correct = false.",
                "action": f"call_function update_theta(theta={theta}, is_correct=False, a={item_a}, b={item_b}, c={item_c})",
                "observation": theta_eval["reasoning_observation"],
                "pedagogical_decision": theta_eval["pedagogical_decision"]
            }
            return AnswerEvaluationResponse(
                is_correct=False,
                score=theta_eval["score"],
                grade=theta_eval["grade"],
                feedback=f"⚠️ Phát hiện giả định sai: {diagnostic.faulty_assumption}",
                diagnostic=diagnostic,
                new_streak=theta_eval["new_streak"],
                new_level=theta_eval["new_level"],
                should_level_up=theta_eval["should_level_up"],
                should_scaffold=theta_eval["should_scaffold"],
                socratic_hint=f"Đối chiếu đoạn [{diagnostic.citation_id}]: {diagnostic.socratic_guidance}",
                review_recommendation=f"Bạn cần mở lại {matched_misc['slide']} để hiểu rõ: {matched_misc['explanation']}",
                review_slide=rev_slide,
                reasoning=reasoning,
                theta=theta_eval["theta"],
                new_theta=theta_eval["new_theta"],
                p3pl_prob=theta_eval["p3pl_prob"]
            )

        # 3. Kiểm tra xem người dùng có chọn trực tiếp một trong các phương án A/B của slide mốc này không
        deck_flow = PRESET_FLOWS.get(req.deck, PRESET_FLOWS.get("d1", {}))
        current_flow = deck_flow.get(req.page)
        if current_flow:
            for opt in current_flow.get("options", []):
                if req.answer_text.strip() == opt["id"] or opt["text"].lower() in text_lower or text_lower in opt["text"].lower():
                    is_correct = bool(opt["is_correct"])
                    theta_eval = evaluate_learner_by_theta(
                        theta=theta,
                        is_correct=is_correct,
                        a=item_a,
                        b=item_b,
                        c=item_c,
                        current_level=req.current_level,
                        current_streak=req.current_streak
                    )
                    reasoning = {
                        "thought": f"Học viên chọn phương án '{opt['text'][:50]}...'. Đánh giá is_correct = {is_correct}.",
                        "action": f"call_function update_theta(theta={theta}, is_correct={is_correct}, a={item_a}, b={item_b}, c={item_c})",
                        "observation": theta_eval["reasoning_observation"],
                        "pedagogical_decision": theta_eval["pedagogical_decision"]
                    }
                    if is_correct:
                        return AnswerEvaluationResponse(
                            is_correct=True,
                            score=theta_eval["score"],
                            grade=theta_eval["grade"],
                            feedback=f"🎉 {opt['feedback']}",
                            diagnostic=None,
                            new_streak=theta_eval["new_streak"],
                            new_level=theta_eval["new_level"],
                            should_level_up=theta_eval["should_level_up"],
                            should_scaffold=theta_eval["should_scaffold"],
                            socratic_hint="Hãy tiếp tục duy trì lập luận chặt chẽ khi đọc các slide tiếp theo!",
                            review_recommendation="Bạn đã nắm rất vững kiến thức mốc này! Hãy tự tin tiếp tục học các slide tiếp theo.",
                            review_slide=None,
                            reasoning=reasoning,
                            theta=theta_eval["theta"],
                            new_theta=theta_eval["new_theta"],
                            p3pl_prob=theta_eval["p3pl_prob"]
                        )
                    else:
                        rev_target = current_flow.get("prior_page") or req.page
                        return AnswerEvaluationResponse(
                            is_correct=False,
                            score=theta_eval["score"],
                            grade=theta_eval["grade"],
                            feedback=f"⚠️ {opt['feedback']}",
                            diagnostic=None,
                            new_streak=theta_eval["new_streak"],
                            new_level=theta_eval["new_level"],
                            should_level_up=theta_eval["should_level_up"],
                            should_scaffold=theta_eval["should_scaffold"],
                            socratic_hint=f"Quan sát lại Slide {rev_target} để tìm ra mối liên hệ chính xác.",
                            review_recommendation=f"Bạn cần mở lại Slide {rev_target} để ôn tập: {current_flow.get('bridge_note') or current_flow.get('summary')}",
                            review_slide=rev_target,
                            reasoning=reasoning,
                            theta=theta_eval["theta"],
                            new_theta=theta_eval["new_theta"],
                            p3pl_prob=theta_eval["p3pl_prob"]
                        )

        # 4. Kiểm tra câu trả lời tự do có lý luận tốt (từ khóa cốt lõi kết hợp ngữ nghĩa đáp án đúng)
        core_terms = ["1.3", "1.4", "hệ số", "sub-token", "vector", "song song", "softmax", "deterministic", "system prompt"]
        if current_flow:
            for opt in current_flow.get("options", []):
                if opt.get("is_correct"):
                    for w in re.findall(r"\w+", opt.get("text", "").lower()):
                        if len(w) > 4 and w not in VIETNAMESE_STOP_WORDS and w not in core_terms:
                            core_terms.append(w)
        is_correct = any(kw in text_lower for kw in core_terms)
        theta_eval = evaluate_learner_by_theta(
            theta=theta,
            is_correct=is_correct,
            a=item_a,
            b=item_b,
            c=item_c,
            current_level=req.current_level,
            current_streak=req.current_streak
        )
        reasoning = {
            "thought": f"Phân tích từ khóa câu trả lời. Xác định is_correct = {is_correct}.",
            "action": f"call_function update_theta(theta={theta}, is_correct={is_correct}, a={item_a}, b={item_b}, c={item_c})",
            "observation": theta_eval["reasoning_observation"],
            "pedagogical_decision": theta_eval["pedagogical_decision"]
        }

        if is_correct:
            return AnswerEvaluationResponse(
                is_correct=True,
                score=theta_eval["score"],
                grade=theta_eval["grade"],
                feedback="🎉 Chính xác tuyệt đối! Bạn đã bắc cầu lý thuyết thành công vào bài toán thực tế.",
                diagnostic=None,
                new_streak=theta_eval["new_streak"],
                new_level=theta_eval["new_level"],
                should_level_up=theta_eval["should_level_up"],
                should_scaffold=theta_eval["should_scaffold"],
                socratic_hint="Hãy tiếp tục duy trì lập luận chặt chẽ khi học tiếp!",
                review_recommendation="Bạn đã nắm rất vững kiến thức này. Hãy cuộn xuống các slide tiếp theo để học kiến thức mới!",
                review_slide=None,
                reasoning=reasoning,
                theta=theta_eval["theta"],
                new_theta=theta_eval["new_theta"],
                p3pl_prob=theta_eval["p3pl_prob"]
            )

        # 5. Câu trả lời chưa rõ ràng
        return AnswerEvaluationResponse(
            is_correct=False,
            score=theta_eval["score"],
            grade=theta_eval["grade"],
            feedback="Câu trả lời của bạn có hướng suy nghĩ tốt nhưng chưa đủ cơ sở dữ liệu.",
            diagnostic=None,
            new_streak=theta_eval["new_streak"],
            new_level=theta_eval["new_level"],
            should_level_up=theta_eval["should_level_up"],
            should_scaffold=theta_eval["should_scaffold"],
            socratic_hint=f"Tại Slide {req.page}, hãy đọc lại sơ đồ trên slide và đối chiếu với slide trước xem sự khác biệt nằm ở đâu?",
            review_recommendation=f"Bạn cần quan sát kỹ lại sơ đồ minh họa tại Slide {req.page}.",
            review_slide=req.page,
            reasoning=reasoning,
            theta=theta_eval["theta"],
            new_theta=theta_eval["new_theta"],
            p3pl_prob=theta_eval["p3pl_prob"]
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

        # 2.5. Ghi nhận lượt hỏi vào bộ nhớ ngắn hạn STM và trích xuất hồ sơ dài hạn LTM
        memory_service.append_turn(req.student_id, "user", req.message)
        memory_context = memory_service.get_memory_prompt_context(req.student_id, req.page)
        conv_history = req.history if req.history else memory_service.get_recent_history(req.student_id)

        # 3. Ưu tiên gọi GPT-4o-mini qua OpenRouter/OpenAI kết hợp bối cảnh RAG và Bộ nhớ ngữ cảnh STM / LTM
        if openrouter_service.is_available():
            llm_reply = await openrouter_service.chat_socratic(
                deck=req.deck,
                page=req.page,
                slide_text=slide_text,
                question_text=q_text,
                user_message=req.message,
                transcript_context=transcript_context,
                level=req.current_level,
                conversation_history=conv_history,
                memory_context=memory_context
            )
            if llm_reply:
                memory_service.append_turn(req.student_id, "assistant", llm_reply)
                return StudentChatResponse(
                    reply=llm_reply,
                    intent=intent,
                    citations=rag_citations,
                    memory_note=f"Đã liên kết bộ nhớ học tập (STM: {len(conv_history)} lượt | LTM: {req.student_id})"
                )

        # 4. Fallback thông minh dựa trên ngữ cảnh Slide & Intent
        citations = rag_citations
        if intent == "example":
            example_from_flow = current_flow.get("example")
            if example_from_flow:
                reply = f"📌 **Ví dụ thực tế**: {example_from_flow}"
            else:
                slide_lines = [l.strip() for l in (slide_text or "").splitlines() if l.strip()]
                concept_snippet = slide_lines[0] if slide_lines else f"Slide {req.page}"
                summary_text = current_flow.get('summary') or (" ".join(slide_lines[1:3]) if len(slide_lines) > 1 else "nguyên lý kỹ thuật của bài giảng")
                reply = f"📌 **Ví dụ thực tế cho Slide {req.page} ({concept_snippet[:40]}):** Vận dụng trực tiếp nguyên tắc này vào bài toán thực tế: {summary_text}."
        elif intent == "concept":
            summary = current_flow.get("summary") or "Khái niệm này là nền tảng cốt lõi trong kiến trúc AI hiện đại."
            note = current_flow.get("bridge_note") or "Quan sát kỹ sự dịch chuyển giữa các slide bài giảng để thấy rõ bản chất."
            reply = f"🔍 **Bản chất cốt lõi**: {summary}\n\n💡 *Góc nhìn chuyên sâu*: {note}"
        elif intent == "hint":
            note = current_flow.get("bridge_note") or "Hãy đối chiếu giữa dữ liệu slide trước và slide hiện tại."
            reply = f"💡 **Gợi ý tư duy**: {note}\nBạn hãy xem kỹ câu hỏi trắc nghiệm bên trên: phương án nào đi ngược lại nguyên lý vận hành này chính là bẫy ngộ nhận!"
        else:
            reply = f"🤖 Tôi đang đồng hành cùng bạn tại Slide {req.page}. Bạn có thể bấm các nút gợi ý nhanh bên dưới để nhận ví dụ thực tế hoặc giải thích bản chất khái niệm nhé!"

        memory_service.append_turn(req.student_id, "assistant", reply)
        return StudentChatResponse(
            reply=reply,
            intent=intent,
            citations=citations,
            memory_note=f"Bộ nhớ học viên: {req.student_id}"
        )

pedagogy_service = PedagogyService()


