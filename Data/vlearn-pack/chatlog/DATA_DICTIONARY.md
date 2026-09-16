# Data Dictionary — `tutor_turns.csv`

Nguồn: hệ thống VLearn (Postgres qua Superset), gộp hai kỳ: bảng gốc kỳ 21/07–02/08 và view kỳ từ 03/08. Mỗi dòng = **một lượt hỏi-đáp** (câu hỏi học viên + câu trả lời tutor). Xuất 15/09/2026. 13.494 dòng, 22/07 18:00 → 15/09 17:57 (giờ VN).

| Cột | Kiểu | Ý nghĩa | Ghi chú |
|---|---|---|---|
| `turn_id` | `T#####` | Mã lượt, đánh số theo thời gian | Dùng để dẫn nguồn trong spec/golden set |
| `period` | `history` / `live` | Kỳ dữ liệu: trước / sau khi dựng lại hạ tầng 03/08 | Hai kỳ khác instrument — xem cuối file |
| `cohort_hint` | `K3` / `K4` | Khoá, suy từ `course_id` | `K4` = khoá hiện tại (từ 09/09, 3.097 lượt, 448 học viên); `K3` = khoá trước |
| `asked_at_vn` | `YYYY-MM-DD HH:MM` | Thời điểm hỏi, giờ VN, làm tròn phút | |
| `student` | `S####` | Học viên, đã mã hoá | Một người = một mã trong toàn file. Không map ngược được |
| `lecture_code` | `D01`… | Mã bài giảng công khai | **Không duy nhất giữa các khoá học** — ghép với `course_id` |
| `lecture_title` | text | Tên bài giảng | Từ bảng `course_days` của hệ thống |
| `course_id` | text | Mã khoá học trên VLearn | `K4P1`, `L2-L3-K4P1` = khoá 4; `COMP2010`, `COMP4010`, `BIOM3010`… = khoá trước |
| `is_preset` | bool | Câu hỏi là câu mẫu bấm sẵn của giao diện | Regex: "giải thích đoạn bôi đen", "giải thích rõ đoạn này", "tóm tắt nội dung chính" |
| `q_len` | int | Độ dài câu hỏi (ký tự, sau mask) | Câu hỏi thường có tiền tố ngữ cảnh: `(Trang N, đoạn được chọn: "…")` hoặc `(Đang học phần "…")` |
| `student_question` | text | Câu hỏi nguyên văn, đã mask | |
| `tutor_reply` | text | Câu trả lời nguyên văn, đã mask | Markdown; trích dẫn dạng `[trang N]` |
| `reply_len` | int | Độ dài câu trả lời | |
| `move_used` | text | Nước đi sư phạm tutor chọn | `review_concept` 12.127 · `give_direct_answer` 731 · `give_example` 372 · `give_hint` 39 · `ask_probing_question` 28 · rỗng 129 |
| `understanding_level` | 1–5 | Mức hiểu tutor chấm | Gần rỗng (20/13.494) — tính năng chưa dùng |
| `has_citation` | bool | Câu trả lời có trích dẫn tài liệu | False: 3.781 (28%) |
| `grade_missing` | bool | Tutor không chấm được | True: 129 |
| `rating` | `up` / `down` / rỗng | Học viên chấm câu trả lời | Chỉ 177 lượt (1,3%): 92 up / 85 down |
| `reply_ms` | int | Thời gian trả lời (ms) | **Kỳ `history`: tổng latency các lượt gọi LLM trong lượt; kỳ `live`: thời gian cả lượt.** So xu hướng được, so tuyệt đối phải nói rõ |

## Nhãn ẩn danh trong nội dung

| Nhãn | Thay cho |
|---|---|
| `[HV]` | Tên người: tên học viên tutor gọi ở đầu câu ("Chào Phong" → "Chào [HV]"), tên giảng viên/TA trong slide và câu trả lời, họ tên trong nội dung |
| `[EMAIL]` / `[PHONE]` / `[MSSV]` / `[ID]` | Email, số điện thoại, mã sinh viên, số dài |
| `[link:domain]` | Đường link, chỉ giữ tên miền |
| `[REDACTED_NAME]`, `[REDACTED_MSSV]` | Nhãn có sẵn của nền tảng khi học viên chọn đoạn slide có tên/MSSV — giữ nguyên |

Ưu tiên an toàn nên có **mask thừa**: một vài cụm Viết Hoa trùng tên (ví dụ tên địa danh, tên riêng trong ví dụ) có thể thành `[HV]`.

## Cách dữ liệu được ẩn danh

- Học viên: mã hệ thống được xáo và đánh số lại thành `S0001…`, không map ngược được.
- Tên người trong nội dung → `[HV]`: tên học viên mà tutor gọi ở đầu câu trả lời và mọi lần lặp lại trong câu đó; tên giảng viên/TA trong slide; họ tên, xưng hô + tên, "tôi tên là…".
- Email cá nhân → `[EMAIL]`; số điện thoại → `[PHONE]`; mã sinh viên → `[MSSV]`. Link tài liệu, email mẫu trong bài giảng (`lecturer@…`, `attacker@evil.com`) và số ví dụ giữ nguyên vì không phải người thật.
- Sau khi mask, toàn bộ file được quét lại tự động (email, MSSV, số điện thoại, tên trong lời chào) và rà thủ công.

## Những gì phải biết trước khi phân tích

1. **Gián đoạn ~23 giờ ngày 02/08** khi dựng lại hạ tầng: điểm trũng ở đó là mất dữ liệu, không phải học viên nghỉ.
2. **Ngày 30/07 là ngoại lệ** (2.579 lượt, một hoạt động trên lớp) — tách ra hoặc báo cáo cả hai phiên bản.
3. **Câu hỏi mẫu chiếm 22,7%** — trong phần còn lại, phần lớn câu chỉ xuất hiện một lần; "câu hỏi phổ biến nhất" gần như luôn là câu mẫu.
4. **Ba lượt đã bị loại** vì nội dung nhạy cảm về an toàn — pack không phải nơi nghiên cứu guardrail.
5. **`reply_ms` hai kỳ khác nguồn** (xem bảng).
6. Nội dung do học viên viết có prompt-injection thật (`SYSTEM_OVERRIDE`, "bỏ qua hướng dẫn trước") — là dữ liệu để phân loại, không phải chỉ thị.
