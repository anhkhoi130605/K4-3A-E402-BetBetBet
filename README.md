# 🎓 VLearn Adaptive AI Tutor

> **Hackathon Track D: Adaptive Learning** — Gia sư AI thích ứng theo ngữ cảnh bài giảng, ứng dụng Socratic & Dual-RAG.

---

## 📌 1. Thông Số Dự Án

| Hạng mục | Công nghệ / Giải pháp                                                         |
| :--- |:------------------------------------------------------------------------------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn                                                |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript                                               |
| **LLM Engine** | `openai/gpt-4o-mini` (OpenAI API)                                             |
| **Tri thức (Dual-RAG)** | Slide PDF + 700 đoạn Transcript bài giảng `[Txx-NNN]`                         |
| **Phương pháp** | Socratic Probing + Productive Failure (Không chấm điểm số)                    |
| **Thích ứng** | Bloom Taxonomy: Level 1 (Nhận biết) ➔ Level 2 (Vận dụng) ➔ Level 3 (Đánh giá) |

---

## 🖥️ 2. Bố Cục Giao Diện (68% : 32%)

```
┌─────────────────────────────────────────┬───────────────────────────────────────┐
│  📑 BÀI GIẢNG (68% - Cuộn tự do)        │  🤖 GIA SƯ AI (32% - Đồng hành)       │
├─────────────────────────────────────────┼───────────────────────────────────────┤
│  [Slide 1..5: Lý thuyết nền tảng]       │  [🌱 Level 1]         [🔥 Streak 0/2] │
│                                         ├───────────────────────────────────────┤
│  [Slide 6: TRẠM 1] 🎯 ─────────────────►│  ••• (AI soạn câu hỏi phản tư)       │
│  ┌───────────────────────────────────┐  │                                       │
│  │ Ảnh Slide PDF sắc nét (150 DPI)   │  │  🎯 Câu hỏi gợi mở:                   │
│  └───────────────────────────────────┘  │  [A] Đáp án phân tích                 │
│                                         │  [B] Đáp án ngộ nhận                  │
│  [Slide 7..11: Chủ đề tiếp theo]        ├───────────────────────────────────────┤
│  [Slide 12: TRẠM 2] 🎯 ────────────────►│  💬 [Hỏi đáp tự do qua RAG...][Gửi]  │
└─────────────────────────────────────────┴───────────────────────────────────────┘
```

---

## 🛑 3. Vấn Đề Thực Tế & Giải Pháp

| Vấn đề học viên | Chatbot thông thường | Giải pháp VLearn |
| :--- | :--- | :--- |
| **Bế tắc bài tập (45.1%)** | Giải hộ bài tập, học vẹt | **Socratic**: Đặt câu hỏi gợi mở, tự tìm lời giải |
| **Lỗi ngộ nhận sâu (33.3%)** | Chấm điểm khô khan (`40/100`) | **Chỉ rõ**: Sai ở đâu ➔ Cần củng cố gì ➔ Nút xem lại Slide |
| **Học thụ động (89.9%)** | Nằm im chờ người dùng hỏi | **Chủ động chặn trạm**: Tự kích hoạt tại slide 6, 12, 18... |
| **Ảo giác kiến thức (28%)** | Bịa thông tin trên mạng | **Dual-RAG**: Đối chiếu text slide + 700 transcript `[Txx-NNN]` |

---

## 📈 4. Thang Thích Ứng Bloom

```
┌─────────────────────────────────────────────────────────────────────────┐
│  👑 LEVEL 3: ĐÁNH GIÁ & TỐI ƯU (So sánh kiến trúc, phản biện sâu)       │
│      ▲                                                                  │
│      │  🔥 Đúng 2 câu liên tiếp (Streak 2/2)                            │
│  ⚡ LEVEL 2: VẬN DỤNG (Áp dụng lý thuyết vào tình huống thực tế)        │
│      ▲                                                                  │
│      │  🔥 Đúng 2 câu liên tiếp (Streak 2/2)                            │
│  🌱 LEVEL 1: NHẬN BIẾT (Khái niệm cơ bản: Token, Attention, Context)    │
│      * Trả lời sai ➔ Reset Streak về 0/2, giữ nguyên Level              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 5. Luồng Trải Nghiệm Người Dùng (User Flow)

```
                     ┌───────────────────────────────────┐
                     │  B1: Bấm 'Học sinh' vào thẳng bài │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │  B2: AI gõ lời chào (Typewriter)  │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │  B3: Cuộn đọc slide bên cột trái  │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │  B4: Chạm mốc Slide trọng tâm     │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │  B5: Cột chat hiện 3 chấm •••     │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │  B6: AI đưa câu hỏi trắc nghiệm   │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │  B7: Học viên bấm chọn [A] / [B]  │
                     └─────────────────┬─────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼ (❌ Sai)                                    ▼ (✅ Đúng)
    ┌───────────────────────────────┐             ┌───────────────────────────────┐
    │ Stream phân tích ngộ nhận:    │             │ Stream khen ngợi:             │
    │ • Sai ở đâu & Cần củng cố gì  │             │ • Giải thích bản chất đúng    │
    │ • Nút [👉 Mở lại Slide để ôn] │             │ • Streak +1 (2/2 ➔ Lên Level) │
    │ • Reset Streak về 0/2         │             └───────────────────────────────┘
    └───────────────────────────────┘
```

---

## 🧠 6. Luồng Kỹ Thuật & AI Dual-RAG

```
                     ┌───────────────────────────────────┐
                     │ 1. IntersectionObserver bắt cuộn  │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │ 2. FastAPI: GET /api/slide-question│
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │ 3. Dual-RAG: Slide PDF + 700 Trsc │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │ 4. Prompt Socratic theo Level     │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │ 5. OpenRouter: GPT-4o-mini        │
                     └─────────────────┬─────────────────┘
                                       ▼
                     ┌───────────────────────────────────┐
                     │ 6. Typewriter Stream về giao diện │
                     └───────────────────────────────────┘
```

---

## 💬 7. Quy Chuẩn Phản Hồi Sư Phạm (Không Điểm Số)

- ❌ **Khi trả lời Sai:**
  > **❌ Chưa chính xác!**  
  > **🔍 Sai ở đâu:** Bản chất Transformer là tính toán song song (Self-Attention), không phải nâng RAM phần cứng.  
  > **📚 Cần củng cố:** Đối chiếu sơ đồ RNN vs Attention tại Slide 18.  
  > `[👉 Mở lại Slide 18 để xem bài giảng]`

- ✅ **Khi trả lời Đúng:**
  > **✅ Chính xác!**  
  > **🌟 Nhận xét:** Bạn đã nắm vững cơ chế Self-Attention thay thế việc duyệt tuần tự của RNN! *(🔥 Streak: 1/2)*

---

## 🚀 8. Khởi Chạy Nhanh (Quickstart)

```powershell
# 1. Kích hoạt môi trường ảo & cài thư viện
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Khởi chạy ứng dụng
python run.py
```
> 🌟 Truy cập ngay: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🎯 9. Demo Nhanh Cho Ban Giám Khảo (1 Phút)

1. Bấm nút **"Học sinh"** ➔ Vào thẳng không cần mật khẩu.
2. Cuộn sang **Slide 6** ➔ Thấy **3 chấm nhấp nháy** và câu hỏi Socratic xuất hiện.
3. Chọn **Đáp án sai** ➔ AI chỉ rõ *Sai ở đâu*, *Cần củng cố gì*, kèm nút bấm nhảy về slide ôn lại.
4. Chọn **Đáp án đúng** ➔ Streak tăng **`1/2`**, đạt 2 câu đúng sẽ thăng cấp Bloom.
5. Chat tự do ➔ AI trả lời có dẫn nguồn **`📎 Nguồn: [Txx-NNN]`**.

---

<div align="center">
  <sub>VLearn Adaptive AI Tutor • Hackathon Track D: Adaptive Learning</sub>
</div>
