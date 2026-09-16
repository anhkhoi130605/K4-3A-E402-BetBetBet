# Transcript bài giảng — bản sạch

Sáu file transcript ASR thô trong `transcript_2/` đã được làm sạch: sửa lỗi nhận dạng theo ngữ cảnh khoá học, ngắt câu, bỏ từ đệm, ẩn danh tên học viên, rút gọn phần hoạt động lớp thành ghi chú — giữ nguyên giọng nói và trình tự ý của giảng viên, không thêm ý mới. Chỗ không khôi phục được đánh dấu `[không nghe rõ]`, không đoán.

## Bảng ánh xạ & định vị buổi

| Bản sạch | Nguồn thô | Định vị buổi (đánh giá từ nội dung) | Tin cậy | Đoạn | Ẩn danh (lượt) | [không nghe rõ] |
|---|---|---|---|---|---|---|
| transcript-01-clean.md | 01.md | Day 2 sáng — Xác định bài toán kinh doanh cho AI | Cao | 89 | 3 | 17 |
| transcript-02-clean.md | 02.md | Day 2 — Chỉ số thành công & mức tự động hoá | Vừa | 43 | 4 | 10 |
| transcript-03-clean.md | 03.md | Day 2 chiều — Soi bài toán các nhóm · tự động hoá & ràng buộc | Vừa | 154 | 2 | 13 |
| transcript-04-clean.md | 04.md | Day 1 — Foundation: cách LLM hoạt động | Cao | 98 | 6 | 21 |
| transcript-05-clean.md | 05.md | Buổi về bài toán · đánh giá · dữ liệu (không gắn số ngày) | — | 154 | 4 | 29 |
| transcript-06-clean.md | 06.md | Buổi Foundation: transformer & attention (không gắn số ngày) | — | 162 | 23 | 33 |

Tổng: ~700 đoạn có mã trích dẫn `[Txx-NNN]` · ~465k ký tự sạch (từ ~854k thô, giữ ~54% — phần giảng giữ 60-80%, phần hoạt động lớp rút thành ghi chú).

## Luật dùng & bảo mật

Theo quy định chung của data pack (xem `data/vlearn-pack/README.md` và README gốc mục "Bảo mật dữ liệu được cung cấp"): chỉ dùng trong phạm vi hackathon · không chia sẻ ra ngoài khoá · không commit nguyên file vào repo nộp bài (trích dẫn bằng mã đoạn `[Txx-NNN]`) · không cố suy ngược danh tính từ nhãn [học viên].
