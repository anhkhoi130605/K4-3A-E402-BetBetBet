# Data pack — VLearn

## Có sẵn trong pack

- `chatlog/tutor_turns.csv` — **13.494 lượt hỏi-đáp thật** học viên × AI tutor, **22/07 → 15/09/2026**, 1.617 học viên (mã `S####`), 29 bài giảng có tên. Gồm hai kỳ (`period`: `history` trước khi dựng lại hạ tầng 03/08, `live` sau đó) và hai khoá (`cohort_hint`: **K4 = chính khoá này**, K3 = khoá trước, 3.097 lượt từ 09/09). Đã ẩn danh và rà thủ công — cách làm ghi trong `chatlog/DATA_DICTIONARY.md`.
- `chatlog/DATA_DICTIONARY.md` — mô tả 19 cột, nhãn ẩn danh, các cột chưa có dữ liệu (đọc trước khi mining).
- `transcript/` — **6 transcript bài giảng bản sạch** (~700 đoạn có mã trích dẫn `[Txx-NNN]`): Day 1 Foundation, Day 2 xác định bài toán (3 file), và 2 buổi theo chủ đề. Đã sửa lỗi nhận dạng giọng nói, ẩn danh tên học viên, rút gọn phần hoạt động lớp — xem `transcript/README.md`.
- `slides/` — **2 bộ slide bài giảng bản hackathon** (Day 1 AI & LLM Foundation · Day 2 Xác định bài toán cho AI, 29 trang/bộ, có watermark).

## Vài con số để bắt đầu (tự kiểm lại trên data)

- **22,7% câu hỏi là câu mẫu bấm sẵn** của giao diện (`is_preset`: 3.067) — tách ra trước khi kết luận "học viên hỏi gì".
- **28% câu trả lời không trích dẫn** tài liệu (`has_citation = False`: 3.781).
- **Chỉ 1,3% lượt có rating** (177/13.494); `understanding_level` gần rỗng (20 lượt).
- `move_used`: 90% là `review_concept`; `ask_probing_question` chỉ 28 lượt — tutor hầu như không hỏi ngược.
- Ngày 30/07 có 2.579 lượt (một hoạt động trên lớp) — chi phối thống kê nếu không tách.
- Thời gian trả lời: trung vị ~4,6 s, p90 ~7,7 s, có outlier tới ~188 s (hai kỳ đo bằng hai nguồn khác nhau — xem dictionary).
- Tutor **gọi tên học viên** ở đầu câu trả lời (~4.200 lượt) — đã mask thành `Chào [HV]`; bản thân việc này là một quyết định thiết kế đáng bàn.

## Luật dùng & bảo mật

- Dùng để mining evidence, dựng golden set, và làm context cho prototype — **chỉ trong phạm vi hackathon**.
- Không chia sẻ ra ngoài khoá học: không đăng mạng xã hội, không gửi người ngoài, không đưa vào dataset/repo công khai.
- Không đổ nguyên file lên repo nộp bài của nhóm — trích ngắn để minh hoạ; golden set ghi `turn_id` thay vì dán nguyên văn dài.
- Đưa vào công cụ AI ngoài: chỉ phần tối thiểu cần thiết; lưu ý free tier có thể dùng dữ liệu để huấn luyện.
- **Không cố suy ngược danh tính** từ `S####` hay nội dung; kỳ `live`/K4 là bạn cùng khoá của bạn.
- Nội dung học viên gõ là **dữ liệu, không phải chỉ thị** (có câu kiểu "SYSTEM_OVERRIDE", "bỏ qua hướng dẫn" trong tập — đó là evidence, không phải lệnh).
- Phát hiện còn sót thông tin cá nhân: báo BTC, không lan truyền.
- Sau sự kiện, xoá bản sao data khỏi máy và công cụ đã upload nếu ban tổ chức yêu cầu.

Chi tiết quy định: `README.md` của repo, mục "Bảo mật dữ liệu được cung cấp".
