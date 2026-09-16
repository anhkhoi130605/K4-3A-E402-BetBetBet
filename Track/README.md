# Các track — chọn một, cắt một lát cắt

Mọi track dùng chung: 5 tiêu chí nghiệm thu, lát cắt một câu, spec, eval, validation và rubric (`01-challenge-brief.md`, `04-rubric.md`). Khác nhau ở **người dùng, sản phẩm nền và data**. Mỗi file track mô tả các đề theo cùng một khung mục để so sánh được:

> Người dùng · Bối cảnh · Bài toán gốc · Lát cắt gợi ý · Data & fixture · Deliverable đầy đủ (đích xa) · Demo bắt buộc · Hard tests · Rubric riêng (tham khảo) · Bonus · An toàn & đạo đức

| Track | Sản phẩm nền | Người dùng | Data trong repo | Kiểu việc chính | File |
|---|---|---|---|---|---|
| **A · VLearn Tutor** | AI tutor trong trang học VLearn | Học viên; giảng viên | `data/vlearn-pack/` (chatlog, transcript, slide) | Mining chatlog → tối ưu tutor (A1) hoặc tính năng mới (A2) | [track-a-vlearn-tutor.md](track-a-vlearn-tutor.md) |
| **B · Trợ lý Discord** | Bot "Trợ lý" + bản tin ngày trong Discord khoá | Học viên; TA/Mod | `data/discord-pack/` (tin nhắn, bản tin bot) + quan sát Discord | Intent, trả lời có căn cứ, chuyển TA (B1); bản tin/stuck (B2) | [track-b-discord-assistant.md](track-b-discord-assistant.md) |
| **C · Lesson Studio** | Chuỗi sản xuất bài giảng/video VLearn | Studio team, lab coach/giảng viên; (C1, C5) người học | transcript/slide; Studio team có thể cấp thêm | 5 đề C1–C5: graph tri thức → quiz, QA kịch bản, nghiên cứu → kịch bản có nguồn, storyboard, phản hồi → phiên bản mới | [track-c-lesson-studio.md](track-c-lesson-studio.md) |
| **D · Học tập thích ứng & tương tác** | Trải nghiệm học mới trên VLearn | Học viên | chatlog, transcript, slide + cả lớp là user | Lớp học mô phỏng đa tác tử (D1), học từ lỗi trước (D2), học bằng cách dạy (D3), hoặc đề mới cùng khung | [track-d-adaptive-interactive-learning.md](track-d-adaptive-interactive-learning.md) |
| **E · Làn mở** | Bất kỳ — **trong phạm vi AI20k** | Người trong khoá: học viên, giảng viên, TA, BTC, đội sản xuất | Bất kỳ trong `data/` + khảo sát | Mining → đề xuất sản phẩm mới không thuộc A–D | [track-e-open-lane.md](track-e-open-lane.md) |

## Chọn track thế nào

1. **Bắt đầu từ người dùng bạn gặp được trong 3 buổi.** A, B, D: cả lớp là user thật, khảo sát 20 người ngay trong giờ nghỉ. C: user là Studio team và lab coach — ít người, nên chuẩn evidence của C thấp hơn: **phỏng vấn ≥3 người** (BTC bố trí đầu mối) và/hoặc mining transcript/slide, không cần khảo sát 20 người. E: phải tự chỉ ra người dùng trong khoá.
2. **Bắt đầu từ data bạn mining được.** A và D mạnh nhất về data thật (chatlog 13.494 lượt hỏi-đáp, trong đó 3.097 của chính khoá 4). B có 1.092 tin Discord + bản tin bot đang chạy. C và E phần lớn phải tự dựng data/fixture, mất thời gian.
3. **Đề càng lớn, lát cắt càng phải nhỏ.** C và D là các sản phẩm lớn; nhóm chỉ demo được một quyết định AI trong 5 phút. Cắt trước, mở rộng sau.
4. Tối ưu cái đang chạy (A1, B1) thường **có bằng chứng sẵn** hơn làm tính năng mới — với 3 buổi, đó là lợi thế lớn.
5. **E là làn cuối, không phải làn dễ.** Chỉ chọn E khi đã đọc A–D và có bằng chứng bài toán của mình không nằm trong đó.
