# Track D — Học tập thích ứng & tương tác trên VLearn

**Sản phẩm nền.** VLearn là nền tảng học tập *thích ứng*: nội dung, câu hỏi và hỗ trợ có thể thay đổi theo từng học viên. Track A tối ưu một tính năng đang có (tutor). Track E hỏi câu lớn hơn: **trải nghiệm học nào trên VLearn khiến học viên chủ động hơn, hiểu sâu hơn, nhớ lâu hơn** — và AI làm được gì mà giáo viên một mình không làm được ở quy mô ~1.000 người?

**Vì sao là một track riêng.** Nghiên cứu học tập nhiều thập kỷ cho cùng một kết luận: học viên học nhiều hơn khi *tương tác và kiến tạo* hơn là *nghe và đọc* (khung ICAP: Interactive > Constructive > Active > Passive — Chi & Wylie, 2014); học từ **thất bại có thiết kế** trước khi được giảng (Productive Failure — Kapur, 2008/2016) và **học bằng cách dạy** (Protégé effect — Chase, Chin, Oppezzo & Schwartz, 2009) đều cho hiệu quả đo được. Trước đây các mô hình này tốn nhân lực: cần bạn học, trợ giảng, người phản biện. LLM agent làm chúng khả thi ở quy mô lớn. Track E là chỗ để thử.

**Người dùng.** Học viên đang học một bài cụ thể trên VLearn (cả lớp là user thật). Giảng viên là người thiết kế/duyệt kịch bản tương tác.

**Data & fixture.** `data/vlearn-pack/`: transcript + slide làm nội dung bài; chatlog cho biết học viên thật hỏi gì, kẹt ở trang nào, hỏi mẫu hay tự gõ. Không có fixture riêng: mọi kịch bản tương tác nhóm tự dựng từ **một** bài giảng trong pack.

**Ràng buộc riêng của track D.** Vì đây là *trải nghiệm học*, tiêu chí 5 (user thử) và vòng validation (guide §4.2) quan trọng hơn mọi thứ: phải có **≥5 bạn cùng lớp thực sự học một đoạn bằng prototype** và log được họ làm gì/hiểu gì — không chỉ "dùng thử giao diện". Quality bar phải có ít nhất một chỉ số về **học** (trả lời đúng sau khi học, giải thích lại được, thời gian đến lời giải) chứ không chỉ về AI trả lời đúng.

---

## D1 · Lớp học mô phỏng đa tác tử

**Bối cảnh.** Học online thường là một người với một màn hình. Trên lớp, phần học nhiều nhất lại đến từ bạn học hỏi ngược, trợ giảng gợi ý, giảng viên phản biện — nhưng không phải ai cũng có lớp như thế, và giảng viên không thể tương tác 1:1 với 350 người.

**Bài toán gốc.** Dựng một **môi trường học mô phỏng** trên VLearn gồm nhiều agent có vai trò khác nhau — *bạn học* (đôi khi hiểu sai, cần được giải thích), *trợ giảng* (hỏi Socratic, không cho đáp án ngay), *giảng viên* (chốt, phản biện, mở rộng) — để học viên học một đoạn bài **trong** tương tác đó thay vì đọc/nghe. Cốt lõi cần giải: các agent phải **bám đúng nội dung bài** (transcript/slide, có trích dẫn), có **vai trò và mức hiểu khác nhau** một cách nhất quán, và biết **khi nào dừng** để học viên tự nghĩ.

**Lát cắt gợi ý.** *Một học viên · ôn khái niệm "attention" từ transcript-06 · một agent bạn học nêu cách hiểu sai phổ biến, học viên phải sửa cho bạn, trợ giảng chỉ can thiệp khi cả hai sai · học viên giải thích lại đúng được khái niệm.* (Một vai agent cũng đủ cho lát cắt; đa tác tử là đích xa.)

**Deliverable đầy đủ (đích xa).** Kịch bản lớp mô phỏng cho một bài · ≥3 vai agent với persona/mức hiểu công bố · agent trích dẫn tài liệu và có "không biết" · điều phối lượt (ai nói khi nào, khi nào im) · log phiên học và tóm tắt cho giảng viên · giảng viên chỉnh persona/kịch bản.

**Hard tests.** Agent bạn học "hiểu sai" nhưng nói quá thuyết phục → học viên học sai · học viên hỏi thứ ngoài bài · học viên im lặng/trả lời một chữ · học viên yêu cầu "cho đáp án luôn" · hai agent nói chồng nhau, mất nhịp.

**Rubric riêng (tham khảo).** Bám nội dung & trích dẫn 25 · Vai trò nhất quán 20 · Bằng chứng học viên học được 25 · Điều phối lượt/nhịp 15 · An toàn & kiểm soát của giảng viên 15.

**An toàn & đạo đức.** Persona "hiểu sai" phải được **sửa đúng trước khi kết thúc phiên**, không để học viên rời đi với kiến thức sai · không giả làm người thật (tên giảng viên thật) · nói rõ đây là agent · giảng viên duyệt kịch bản.

---

## D2 · Học từ lỗi trước — làm bài rồi mới được giảng

**Bối cảnh.** Bài giảng thường đi lý thuyết → ví dụ → bài tập. Nghiên cứu Productive Failure cho thấy trình tự ngược — **thử giải trước, thất bại, rồi mới được giảng** — giúp hiểu sâu và chuyển giao tốt hơn, *với điều kiện* lời giảng sau đó bám đúng vào lỗi học viên vừa mắc. Điều kiện đó chính là chỗ AI có ích: giảng theo lỗi của từng người.

**Bài toán gốc.** Một luồng học trên VLearn trong đó học viên **nhận bài tập trước khi học lý thuyết**; khi làm sai, AI **phân tích lỗi cụ thể** rồi mới đưa lời dẫn giải và đoạn tài liệu liên quan (trích dẫn trang/đoạn); khi làm đúng thì hỏi ngược để chắc là hiểu chứ không đoán. Cốt lõi: chẩn đoán lỗi đúng (không phải "sai rồi, đáp án là…"), dẫn giải **tối thiểu** để học viên tự đi tiếp, và giữ được lịch sử lỗi để lần sau thích ứng.

**Lát cắt gợi ý.** *Một học viên · làm một bài về tokenization trước khi xem bài giảng · làm sai, AI chỉ ra đúng giả định sai và gợi ý một bước, kèm đoạn transcript liên quan · học viên tự sửa và giải thích được vì sao.*

**Deliverable đầy đủ (đích xa).** Bộ bài tập "trước khi học" cho một chương, gắn concept và đoạn tài liệu · bộ lỗi thường gặp (misconception bank) do nhóm mining/thu từ lớp · AI chẩn đoán lỗi → dẫn giải theo bậc (gợi ý → giải thích → tài liệu) · theo dõi lỗi theo học viên · báo cáo cho giảng viên: lớp sai ở đâu nhiều nhất.

**Hard tests.** Học viên đoán đúng mà không hiểu · lỗi không nằm trong bank · học viên bỏ trống/gõ bừa · cùng một lỗi lặp lại lần thứ ba · bài tập mơ hồ hơn nhóm nghĩ (lỗi ở đề, không ở học viên).

**Rubric riêng (tham khảo).** Chẩn đoán lỗi đúng 25 · Dẫn giải tối thiểu, có trích dẫn 20 · Bằng chứng học viên hiểu sau khi sai 25 · Thích ứng theo lịch sử 15 · Kiểm soát của giảng viên 15.

**An toàn & đạo đức.** Không hạ thấp/khiến học viên nản khi sai (giọng phản hồi là một quyết định thiết kế phải kiểm) · lỗi cá nhân không công khai cho lớp · giảng viên duyệt bài tập và lời dẫn giải mẫu.

---

## D3 · Học bằng cách dạy — học viên dạy lại cho agent

**Bối cảnh.** Người học nhớ và hiểu tốt hơn khi phải **giải thích cho người khác** (Protégé effect; "Betty's Brain"). Trong lớp lớn, không phải ai cũng có người để dạy lại; và người nghe giải thích sai thường không biết để hỏi ngược.

**Bài toán gốc.** Một agent "học trò" trên VLearn: học viên phải **dạy lại** một khái niệm vừa học; agent hỏi ngược đúng chỗ giải thích còn hổng, mơ hồ hoặc sai (đối chiếu với tài liệu), và chỉ "hiểu" khi lời giải thích đủ đúng. Cốt lõi: agent phải vừa **ngây thơ có kiểm soát** (không gợi ý đáp án) vừa **kiểm tra được** lời giải thích của học viên với nguồn.

**Lát cắt gợi ý.** *Một học viên · dạy lại "vì sao LLM bịa" cho agent · agent hỏi ngược 2 câu tại chỗ giải thích thiếu căn cứ · học viên bổ sung và nêu được ví dụ đúng.*

**Deliverable đầy đủ (đích xa).** Persona học trò có mức hiểu thay đổi · so khớp giải thích với transcript/slide · chấm "đã dạy được" bằng tiêu chí công bố · log phiên dạy cho giảng viên · gợi ý học viên xem lại đoạn nào.

**Hard tests.** Học viên giải thích đúng nhưng khác cách diễn đạt tài liệu · học viên giải thích sai nhưng tự tin · học viên dán nguyên đoạn tài liệu thay vì tự nói · agent "hiểu" quá dễ.

**Rubric riêng (tham khảo).** Hỏi ngược đúng chỗ hổng 25 · Đối chiếu nguồn 20 · Bằng chứng học viên hiểu sâu hơn 25 · Không lộ đáp án 15 · UX & kiểm soát 15.

**An toàn & đạo đức.** Như D1/D2; không tạo cảm giác bị chấm điểm ngầm — nói rõ mục đích là luyện, không phải thi.

---

## Khái quát: track D nhận đề mới theo cùng khung

Ba đề trên là **ba mẫu** của cùng một câu hỏi: *đổi trình tự hoặc vai trò trong việc học để học viên phải kiến tạo/tương tác, rồi dùng AI để giữ nó đúng nội dung và đúng người.* Nhóm có thể đề xuất một đề D khác nếu trả lời được bốn câu:

1. **Học viên phải làm gì chủ động** mà hiện nay không làm (giải thích, dự đoán, tranh luận, sửa lỗi, dạy lại)?
2. **AI giữ nó đúng bằng cách nào** — bám nguồn nào, trích dẫn ra sao, khi nào nói "không biết"?
3. **Thích ứng theo cái gì** của từng học viên (lỗi vừa mắc, lịch sử, mức hiểu tự khai)?
4. **Đo "học được" bằng gì** ngoài "AI trả lời đúng"?

Đề mới phải đi qua đúng khung mục như mọi đề (Người dùng · Bối cảnh · Bài toán gốc · Lát cắt · Data · Hard tests · An toàn) và 5 tiêu chí nghiệm thu.
