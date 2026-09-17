// Dữ liệu thực tế từ c:\Users\gistr\Downloads\hackathon\Data và Untitled form.csv
window.VLEARN_DATA = {
  surveyStats: {
    totalResponses: 52,
    painPoints: [
      { label: "Hiểu lý thuyết nhưng không biết áp dụng vào bài tập", percentage: 45.1, count: 23, color: "#f43f5e" },
      { label: "Thường hiểu lơ mơ nhưng không biết mình sai ở đâu", percentage: 33.3, count: 17, color: "#fb923c" },
      { label: "Buồn ngủ, mất tập trung vì thụ động một chiều", percentage: 21.6, count: 11, color: "#a855f7" }
    ],
    failurePreference: {
      productiveFailureInterest: 76.9, // Thích thú thử thách trước khi học
      socraticProbingInterest: 84.6    // Hứng thú học trò ảo hỏi ngược
    }
  },

  chatlogStats: {
    totalTurns: 13494,
    historicalAnalysis: {
      reviewConcept: { count: 12127, pct: 89.9, desc: "Giảng giải lý thuyết thụ động (1 chiều)" },
      giveDirectAnswer: { count: 731, pct: 5.4, desc: "Cho đáp án trực tiếp" },
      giveExample: { count: 372, pct: 2.8, desc: "Đưa ví dụ" },
      giveHint: { count: 39, pct: 0.3, desc: "Gợi ý tối thiểu" },
      askProbingQuestion: { count: 28, pct: 0.2, desc: "Hỏi định hướng Socratic (Cực kỳ hiếm!)" }
    },
    noCitationRate: 28.0 // 3.781 lượt không trích dẫn nguồn
  },

  transcripts: {
    "T04-049": {
      id: "T04-049",
      source: "Day 1 — Foundation: Cách LLM hoạt động",
      slide: "Slide Day 1 · Trang 12",
      title: "Định nghĩa Token & Đặc thù Tiếng Việt",
      content: "Trong các mô hình ngôn ngữ lớn thì có một thuật ngữ quan trọng chúng ta cần nắm được, đấy là token. Nó sẽ là một đơn vị tính — không phải là từ, không phải là chữ cái, mà nó là token... Mô hình không nhìn văn bản nguyên vẹn mà chẻ nhỏ thành token. Tiếng Việt có dấu nên sẽ tốn hơn tiếng Anh khoảng 1.3 đến 1.4 lần."
    },
    "T04-051": {
      id: "T04-051",
      source: "Day 1 — Foundation: Cách LLM hoạt động",
      slide: "Slide Day 1 · Trang 14",
      title: "Context Window là gì?",
      content: "Context nghĩa là bối cảnh, ngữ cảnh — toàn bộ thông tin mà một mô hình có thể tiêu thụ trong một lần. Context window là cửa sổ ngữ cảnh. Mình có thể hình dung context là cái bàn làm việc của mô hình: trong một thời điểm nó có thể bày ra được tối đa bao nhiêu thì nó xử lý được chừng đấy thông tin."
    },
    "T04-089": {
      id: "T04-089",
      source: "Day 1 — Foundation: Cách LLM hoạt động",
      slide: "Slide Day 1 · Trang 22",
      title: "Temperature & Tính tất định (Determinism)",
      content: "Khi gọi API: System prompt mang tính quy luật tổng quát. Khi temperature = 0: model ưu tiên token có xác suất cao nhất, nên đầu ra gần như deterministic (nhất quán giữa các lần). Khi temperature = 1: mức độ sáng tạo ngẫu nhiên cao hơn."
    },
    "T06-086": {
      id: "T06-086",
      source: "Buổi Foundation: Transformer & Attention",
      slide: "Slide Day 1 · Trang 18",
      title: "Self-Attention & Xử lý Song song",
      content: "Cái self-attention bản chất là mỗi một token sẽ nhìn các token khác trong ngữ cảnh đang đặt ra. Multi-head attention: có nhiều góc nhìn song song. Khác với RNN hay LSTM xử lý tuần tự từng từ, Transformer cho phép các token nhìn nhau song song."
    },
    "T06-130": {
      id: "T06-130",
      source: "Buổi Foundation: Transformer & Attention",
      slide: "Slide Day 1 · Trang 20",
      title: "Cơ chế Toán học: Q, K, V & Softmax",
      content: "Cơ chế self-attention: làm sao mỗi từ được biểu diễn trong không gian toán học (embedding vector) để tự cái từ đấy nhìn được những từ khác. Sau khi đánh giá similarity score thì mới đoán được 'nó' là con mèo hay cái bàn. Công thức Q (Query), K (Key), V (Value) với hàm Softmax."
    },
    "T06-154": {
      id: "T06-154",
      source: "Buổi Foundation: Transformer & Attention",
      slide: "Slide Day 1 · Trang 25",
      title: "Token Economy & Chi phí gọi API",
      content: "Cách tính giá của nó: chúng ta tính cả input token cộng với output token thì ra total cost. Chú ý output token lại được feed forward trở lại làm input cho token tiếp theo! Không phải một từ là một token."
    }
  },

  // Bài tập mẫu thực tế ứng dụng
  exercises: [
    {
      id: "ex-token-calc",
      title: "Bài tập 1: Dự toán Chi phí Token cho Chatbot CSKH Tiếng Việt",
      topic: "Tokenization & Token Economy",
      description: "Doanh nghiệp xây dựng bot CSKH xử lý 10.000 yêu cầu/ngày bằng tiếng Việt. Mỗi yêu cầu khách hàng dài trung bình 120 từ tiếng Việt, system prompt dài 250 từ tiếng Anh, câu trả lời bot dài trung bình 150 từ tiếng Việt. Giả định giá API: Input $2.5/1M token, Output $10.00/1M token.",
      question: "Bước 1: Hãy ước tính tổng số INPUT TOKEN cho một phiên hội thoại và nêu cơ sở quy đổi bạn sử dụng.",
      targetConcepts: ["Token quy đổi tiếng Việt", "System prompt token", "Input vs Output cost"],
      relatedCitations: ["T04-049", "T06-154"]
    },
    {
      id: "ex-attention-calc",
      title: "Bài tập 2: Cơ chế Self-Attention trong câu chứa Đại từ quan hệ",
      topic: "Self-Attention & Contextual Embedding",
      description: "Cho câu đầu vào: 'Con mèo bắt con chuột vì nó đói'. Mô hình cần xác định đại từ 'nó' liên kết mật thiết nhất với token nào.",
      question: "Tại sao thuật toán Self-Attention xác định được 'nó' là 'mèo' thay vì 'chuột' trong không gian toán học?",
      targetConcepts: ["Query, Key, Value", "Similarity Score", "Softmax weighting"],
      relatedCitations: ["T06-086", "T06-130"]
    }
  ],

  // Ngân hàng chẩn đoán lỗi tư duy (Misconception Bank)
  misconceptionBank: [
    {
      id: "misc-01",
      trigger: "1 từ tiếng việt = 1 token",
      faultyAssumption: "Đồng nhất 1 từ tiếng Việt với 1 token (như tiếng Anh)",
      explanation: "Tiếng Việt có dấu thanh và cấu trúc âm tiết ghép, bộ tokenizer tách từ tiếng Việt thành 1.3 - 1.4 token trung bình mỗi từ.",
      citationId: "T04-049",
      subQuestion: "Nếu từ 'Học tập' bị tách thành các sub-token, thì 120 từ tiếng Việt sẽ tốn khoảng bao nhiêu token so với 120 từ tiếng Anh?"
    },
    {
      id: "misc-02",
      trigger: "attention đọc từ trái sang phải",
      faultyAssumption: "Nghĩ rằng Transformer đọc tuần tự từng từ như con người",
      explanation: "Transformer xử lý toàn bộ các token đồng thời (song song) thông qua ma trận tương quan Q và K, không duyệt tuần tự như RNN.",
      citationId: "T06-086",
      subQuestion: "Nếu cơ chế là song song, thì ma trận Attention Score giữa các từ được tính toán cùng một lúc hay theo thứ tự thời gian?"
    },
    {
      id: "misc-03",
      trigger: "chỉ tính tiền input khách hàng gõ",
      faultyAssumption: "Bỏ qua token của System Prompt trong chi phí Input",
      explanation: "Mỗi request gửi lên API đều phải gửi kèm toàn bộ System Prompt (lớp chỉ thị nền tảng), do đó System Prompt được tính phí input cho MỌI câu chat.",
      citationId: "T04-089",
      subQuestion: "Nếu bạn có 10.000 request/ngày, thì phần System Prompt dài 250 từ sẽ bị nhân lên bao nhiêu lần trong tổng bill?"
    }
  ],

  // Luồng gợi nhớ kiến thức cũ liên kết giữa các Slide (Spaced Retrieval & Cumulative Learning)
  slideRecallFlow: {
    "d1": [
      {
        page: 6,
        title: "Trang 6: LLM là gì & Cách thức hoạt động cốt lõi",
        summary: "Mô hình ngôn ngữ lớn huấn luyện trên dữ liệu khổng lồ, dự đoán token tiếp theo theo xác suất.",
        citations: ["T06-022", "T04-047"],
        recallConnection: null, // Slide mở đầu
        aiQuestion: "Bắt đầu từ Slide 6: Bản chất của LLM là dự đoán xác suất token tiếp theo, chứ không phải hiểu ngôn ngữ như con người. Bạn hãy ghi nhớ nguyên lý này để lát nữa đối chiếu với các slide sau nhé!",
        options: [
          { text: "Mô hình tính toán xác suất thống kê để sinh ra từng token kế tiếp trong không gian vector.", isCorrect: true, feedback: "Chính xác! Ghi nhớ điều này để chuẩn bị bước sang Slide 12 về đơn vị tính Token." },
          { text: "Mô hình ghi nhớ toàn bộ từ vựng dưới dạng chữ viết tĩnh và tra cứu như từ điển.", isCorrect: false, feedback: "Chưa chính xác: LLM không phải là cuốn từ điển tra từ vựng tĩnh mà tính toán phân phối xác suất sinh token." },
          { text: "Mô hình suy luận logic tư duy có ý thức độc lập giống hệt như bộ não con người.", isCorrect: false, feedback: "Sai lầm: LLM là mô hình toán học dự đoán chuỗi token tiếp theo dựa trên trọng số xác suất." },
          { text: "Mô hình dịch toàn bộ câu hỏi sang mã nhị phân 0-1 rồi tự động tìm kiếm câu trả lời trên Google.", isCorrect: false, feedback: "Sai lầm: LLM hoạt động độc lập bằng mạng nơ-ron sinh token, không tự động tìm Google." }
        ]
      },
      {
        page: 12,
        title: "Trang 12: Định nghĩa Token & Đặc thù Tiếng Việt",
        summary: "Đơn vị tính cơ bản của LLM là Token, không phải từ hay chữ cái. Tiếng Việt có dấu thanh tốn 1.3 - 1.4 lần token.",
        citations: ["T04-049"],
        recallConnection: {
          priorPage: 6,
          concept: "Nguyên lý dự đoán next-token (Slide 6) ➔ Đơn vị tính Token (Slide 12)",
          note: "Ở Slide 6, bạn đã biết mô hình sinh chuỗi theo 'token'. Sang Slide 12, giảng viên chỉ rõ Token là gì và tại sao tiếng Việt lại đặc biệt."
        },
        aiQuestion: "🔗 GỢI NHỚ TỪ SLIDE 6: Ở Slide 6, mô hình dự đoán xác suất token tiếp theo. Vậy sang Slide 12 này, tại sao mô hình không dự đoán trực tiếp 'từ ngữ nguyên vẹn' của con người mà phải chẻ nhỏ thành Token?",
        options: [
          { text: "Vì máy tính chỉ tính toán được trên không gian số học toán học (vector embedding), và các ngôn ngữ như tiếng Việt cần chẻ thành sub-tokens.", isCorrect: true, feedback: "Xuất sắc! Bạn đã kết nối đúng từ việc dự đoán xác suất (Slide 6) sang cơ chế mã hóa toán học của Token (Slide 12)." },
          { text: "Vì tiếng Việt viết từ phải sang trái nên cần đổi sang token.", isCorrect: false, feedback: "Chưa đúng: Tiếng Việt viết từ trái sang phải, việc chẻ token là do cấu trúc dấu thanh và âm tiết ghép." },
          { text: "Vì mỗi từ tiếng Việt luôn tương ứng đúng 1 token duy nhất giống hệt tiếng Anh nên không cần chẻ nhỏ.", isCorrect: false, feedback: "Ngộ nhận kinh điển: Tiếng Việt có dấu thanh khiến bộ tokenizer BPE tách thành 1.3 - 1.4 sub-token/từ!" },
          { text: "Vì máy chủ AI chỉ lưu trữ bảng mã ASCII tiếng Anh, không thể đọc được ký tự Unicode tiếng Việt.", isCorrect: false, feedback: "Sai lầm: Các bộ tokenizer hiện đại như BPE xử lý UTF-8 đa ngôn ngữ thông qua sub-token." }
        ]
      },
      {
        page: 14,
        title: "Trang 14: Context Window (Cửa Sổ Ngữ Cảnh)",
        summary: "Context Window là giới hạn bối cảnh tối đa mà mô hình có thể tiêu thụ trong một lần xử lý.",
        citations: ["T04-051"],
        recallConnection: {
          priorPage: 12,
          concept: "Đơn vị Token tiếng Việt (Slide 12) ➔ Sức chứa Context Window (Slide 14)",
          note: "Nếu quên tính hệ số 1.35x của tiếng Việt ở Slide 12, bạn sẽ ước lượng sai sức chứa của Context Window ở Slide 14."
        },
        aiQuestion: "🔗 KẾT NỐI VỚI SLIDE 12: Một tài liệu tiếng Việt dài 80.000 từ. Nếu bạn đưa vào mô hình có Context Window là 100.000 token, liệu có bị tràn context không?",
        options: [
          { text: "Có nguy cơ tràn! Vì theo Slide 12, 80.000 từ tiếng Việt nhân hệ số ~1.35x sẽ tương đương ~108.000 token, vượt ngưỡng 100.000 token của Slide 14.", isCorrect: true, feedback: "Chính xác tuyệt đối! Đây là lỗi cực kỳ phổ biến mà 34.8% học viên hay mắc phải khi không kết nối 2 slide này." },
          { text: "Không tràn, vì 80.000 từ nhỏ hơn 100.000 token.", isCorrect: false, feedback: "Sai lầm: 1 từ tiếng Việt không bằng 1 token! Cần nhân hệ số quy đổi ~1.35x." },
          { text: "Không tràn, vì mô hình sẽ tự động nén văn bản tiếng Việt lại còn 50.000 token.", isCorrect: false, feedback: "Chưa chính xác: LLM không tự nén token đầu vào nếu không có thuật toán nén chuyên dụng." },
          { text: "Có tràn, nhưng chỉ do kích thước file tính bằng Megabyte (MB) quá lớn chứ không liên quan đến token.", isCorrect: false, feedback: "Sai lầm: Giới hạn Context Window được đo bằng Token, không đo bằng dung lượng MB." }
        ]
      },
      {
        page: 18,
        title: "Trang 18: Kiến Trúc Transformer & Self-Attention",
        summary: "Xử lý song song, các token nhìn lẫn nhau trong ngữ cảnh, khắc phục việc quên thông tin của RNN/LSTM.",
        citations: ["T06-086", "T06-127"],
        recallConnection: {
          priorPage: 14,
          concept: "Giới hạn đọc (Slide 14) ➔ Cơ chế 'nhìn song song' không bị quên (Slide 18)",
          note: "Con người đọc từ trang 1 đến 500 thì quên trang đầu; Transformer cho cả 5.000 token nhìn nhau song song."
        },
        aiQuestion: "🔗 GỢI NHỚ TỪ SLIDE 6 & 14: Trước Transformer, các mô hình cũ đọc từng từ từ trái sang phải và hay bị 'quên' phần đầu khi context dài (Slide 14). Slide 18 giải quyết điểm nghẽn này bằng cơ chế nào?",
        options: [
          { text: "Cơ chế Self-Attention cho phép TẤT CẢ token nhìn nhau SONG SONG cùng lúc trong không gian toán học, không duyệt tuần tự.", isCorrect: true, feedback: "Rất chuẩn! Bạn đã hiểu được bước đột phá của Self-Attention so với cơ chế tuần tự cũ." },
          { text: "Mô hình tăng thêm ổ cứng SSD để đọc nhanh hơn.", isCorrect: false, feedback: "Chưa đúng: Bản chất là thay đổi kiến trúc thuật toán sang song song (Self-Attention), không phải chỉ tăng RAM." },
          { text: "Mô hình đảo ngược chiều đọc từ phải sang trái để đọc lại phần ngữ cảnh bị quên.", isCorrect: false, feedback: "Sai lầm: Transformer không duyệt tuần tự xuôi hay ngược mà tính toán ma trận song song toàn bộ." },
          { text: "Mô hình loại bỏ hoàn toàn các từ đứng ở đầu câu và chỉ giữ lại 50 từ cuối cùng.", isCorrect: false, feedback: "Chưa chính xác: Transformer tính toán trọng số tương đồng cho toàn bộ cửa sổ ngữ cảnh." }
        ]
      },
      {
        page: 20,
        title: "Trang 20: Cơ Chế Toán Học: Q, K, V & Softmax",
        summary: "Query, Key, Value biểu diễn vector; Softmax tính điểm tương đồng (similarity score).",
        citations: ["T06-130"],
        recallConnection: {
          priorPage: 18,
          concept: "Các token nhìn nhau (Slide 18) ➔ Công thức toán học Q, K, V (Slide 20)",
          note: "Nói 'nhìn nhau' là cách giải thích trực quan; về bản chất toán học là nhân ma trận Q với K rồi qua Softmax."
        },
        aiQuestion: "🔗 KẾT NỐI VỚI SLIDE 18: Ở Slide 18 bạn biết các token 'nhìn nhau'. Nhưng trong toán học, máy tính làm sao biết từ 'nó' trong câu 'Con mèo bắt chuột vì nó đói' đang chú ý vào 'mèo' hay 'chuột'?",
        options: [
          { text: "Query (nó) nhân với Key (mèo) qua hàm Softmax tạo ra Similarity Score cao nhất, gán Value tương ứng.", isCorrect: true, feedback: "Tuyệt đỉnh! Bạn đã bắc cầu hoàn hảo từ khái niệm trực quan ở Slide 18 sang bản chất toán học Q-K-V ở Slide 20." },
          { text: "Mô hình tự đoán ngẫu nhiên xem từ nào gần hơn.", isCorrect: false, feedback: "Chưa đúng: Thuật toán tính ma trận tương đồng toán học có trọng số, không hề ngẫu nhiên." },
          { text: "Mô hình tra từ điển ngữ pháp tiếng Việt để tìm chủ ngữ gần nhất.", isCorrect: false, feedback: "Sai lầm: Transformer không phân tích bằng luật ngữ pháp tĩnh mà tính toán không gian vector của Q và K." },
          { text: "Mô hình mặc định gán từ 'nó' cho danh từ đứng ngay liền kề trước đó là 'chuột'.", isCorrect: false, feedback: "Chưa chính xác: Dựa trên ngữ cảnh 'đói', liên kết ngữ nghĩa Q và K cho trọng số cao với 'mèo' hơn." }
        ]
      },
      {
        page: 22,
        title: "Trang 22: Tham Số Temperature & Tính Tất Định",
        summary: "Temperature = 0: chọn token xác suất cao nhất (nhất quán). Temperature = 1: sáng tạo ngẫu nhiên hơn.",
        citations: ["T04-089"],
        recallConnection: {
          priorPage: 6,
          concept: "Dự đoán xác suất token (Slide 6) ➔ Điều khiển nhiệt độ Temperature (Slide 22)",
          note: "Softmax ở Slide 20 tạo ra phân phối xác suất; Temperature ở Slide 22 sẽ làm phẳng hoặc làm dốc phân phối này."
        },
        aiQuestion: "🔗 GỢI NHỚ TỪ SLIDE 6 & 20: Khi Softmax (Slide 20) tính ra điểm số các token kế tiếp (Slide 6), nếu bạn cần trích xuất thông tin hợp đồng tài chính chính xác tuyệt đối, bạn nên đặt Temperature bằng mấy và vì sao?",
        options: [
          { text: "Đặt Temperature = 0 để mô hình luôn luôn chọn token có xác suất cao nhất, đảm bảo tính tất định (deterministic).", isCorrect: true, feedback: "Chính xác! Giảng viên đã nhấn mạnh điều này ở Slide 22 cho các bài toán tài chính/y tế." },
          { text: "Đặt Temperature = 1 để mô hình tự sáng tạo thêm điều khoản mới.", isCorrect: false, feedback: "Sai lầm: Trong tài chính, temperature = 1 sẽ gây rủi ro hallucination rất lớn." },
          { text: "Đặt Temperature = 2 để mô hình suy luận đa chiều và phát hiện gian lận tốt hơn.", isCorrect: false, feedback: "Sai lầm: Temperature quá cao sẽ làm phẳng phân phối xác suất, khiến kết quả lộn xộn, vô nghĩa." },
          { text: "Đặt Temperature bất kỳ vì tham số này chỉ ảnh hưởng đến tốc độ phản hồi chứ không ảnh hưởng nội dung.", isCorrect: false, feedback: "Chưa chính xác: Temperature điều khiển trực tiếp phân phối xác suất Softmax chọn token tiếp theo." }
        ]
      },
      {
        page: 25,
        title: "Trang 25: Token Economy & Chi Phí Gọi API",
        summary: "Tổng chi phí = Input Token + Output Token. Output token lại được feed-forward làm input kế tiếp.",
        citations: ["T06-154"],
        recallConnection: {
          priorPage: 12,
          concept: "Hệ số Token tiếng Việt (Slide 12) + Feed forward (Slide 18) ➔ Bài toán Chi phí (Slide 25)",
          note: "Bài toán thực tế: dự toán chi phí API cho doanh nghiệp dựa trên toàn bộ các slide trước."
        },
        aiQuestion: "🔗 TỔNG HỢP KIẾN THỨC TOÀN BỘ (SLIDE 12 ➔ 18 ➔ 25): Khi tính tổng chi phí API cho một phiên chat CSKH tiếng Việt, điều gì xảy ra nếu bạn chỉ tính tiền số từ khách hàng gõ?",
        options: [
          { text: "Sẽ bị hụt ngân sách nặng nề! Vì phải tính thêm hệ số 1.35x tiếng Việt (Slide 12), token của System Prompt (Slide 22), và Output token được feed-forward (Slide 18, 25).", isCorrect: true, feedback: "Chúc mừng bạn! Bạn đã hoàn thành trọn vẹn chuỗi bắc cầu lý thuyết xuyên suốt từ Slide 6 đến Slide 25!" },
          { text: "Không sao, nhà cung cấp API sẽ tự động miễn phí phần System Prompt.", isCorrect: false, feedback: "Sai lầm: Nhà cung cấp tính phí input token cho TOÀN BỘ request, bao gồm cả System Prompt." },
          { text: "Chi phí sẽ giảm một nửa vì nhà cung cấp chỉ tính phí các token đầu ra (output token).", isCorrect: false, feedback: "Sai lầm: API tính phí cho CẢ input token và output token, trong đó input token gửi kèm lịch sử chat lặp lại liên tục." },
          { text: "Ngân sách vẫn đúng vì 1 từ tiếng Việt luôn được tính đúng bằng 1 token khi quy đổi tài chính.", isCorrect: false, feedback: "Sai lầm kinh điển: Tiếng Việt có dấu thanh tốn ~1.35x token/từ, không nhân hệ số sẽ làm sai lệch dự toán ngân sách." }
        ]
      }
    ]
  },

    {
      level: 1,
      name: "Level 1: Nhận biết & Tái hiện (Recall & Understand)",
      difficultyBadge: "Cơ bản",
      streakRequired: 2,
      question: "Trong kiến trúc Transformer, tại sao tiếng Việt thường tiêu tốn nhiều token hơn tiếng Anh khi gọi API?",
      options: [
        { id: "A", text: "Do tiếng Việt có dấu thanh và ký tự có dấu khiến bộ mã hóa (BPE/WordPiece) phải chẻ thành nhiều sub-tokens hơn.", isCorrect: true },
        { id: "B", text: "Do các công ty AI cố tình tính phí cao hơn cho các ngôn ngữ châu Á.", isCorrect: false },
        { id: "C", text: "Do tiếng Việt viết từ phải sang trái nên cần thêm token định hướng.", isCorrect: false },
        { id: "D", text: "Do mỗi ký tự trong bảng chữ cái tiếng Việt luôn luôn tương ứng với 2 token độc lập.", isCorrect: false }
      ],
      citation: "T04-049"
    },
    {
      level: 2,
      name: "Level 2: Vận dụng & Phân tích (Apply & Analyze)",
      difficultyBadge: "Vận dụng",
      streakRequired: 2,
      question: "Một bạn lập trình viên đặt Temperature = 0 để làm một hệ thống trích xuất thông tin JSON tự động từ hợp đồng. Bạn ấy quan sát thấy: cùng một input hợp đồng nhưng kết quả JSON giữa 2 lần chạy hơi khác nhau một trường ngày tháng. Khả năng cao nhất nguyên nhân là gì?",
      options: [
        { id: "A", text: "Do bản thân mô hình LLM trên GPU có tính chất không tất định nhẹ (floating-point non-determinism khi batching song song), dù temperature = 0.", isCorrect: true },
        { id: "B", text: "Do temperature = 0 làm cho mô hình ngẫu nhiên tối đa.", isCorrect: false },
        { id: "C", text: "Do mô hình tự động đổi ngôn ngữ sang tiếng Việt.", isCorrect: false },
        { id: "D", text: "Do context window bị thu nhỏ lại còn 100 token.", isCorrect: false }
      ],
      citation: "T04-089"
    },
    {
      level: 3,
      name: "Level 3: Chuyên sâu & Trường hợp Ngoại lệ (Edge Cases)",
      difficultyBadge: "Thử thách Cao cấp 🔥",
      streakRequired: 1,
      question: "[EDGE CASE] Hệ thống Chatbot của bạn có Context Window là 128.000 token. Một khách hàng tải lên file tài liệu 100.000 token, sau đó tiếp tục chat 15 lượt (mỗi lượt hỏi-đáp tốn 2.000 token). Đến lượt thứ 15, tổng token hội thoại vượt ngưỡng 130.000 token. Nếu hệ thống không dùng kỹ thuật RAG hay Compaction, chuyện gì sẽ xảy ra ở tầng API?",
      options: [
        { id: "A", text: "API sẽ throw lỗi 400 'ContextWindowExceededError' (hoặc tự cắt cụt token đầu), gây mất mát ngữ cảnh quan trọng ban đầu.", isCorrect: true },
        { id: "B", text: "Mô hình sẽ tự động mua thêm RAM trên server để nén context mà không cần cấu hình.", isCorrect: false },
        { id: "C", text: "Chi phí token tự động giảm về 0 cho những token vượt quá.", isCorrect: false },
        { id: "D", text: "Mô hình chuyển sang chế độ offline và tiếp tục trả lời bình thường.", isCorrect: false }
      ],
      citation: "T04-051"
    }
  ],

  // Dữ liệu mẫu lớp học cho Bảng điều khiển Giảng viên
  instructorDashboardData: {
    classOverview: {
      totalStudents: 448,
      activeSessions: 312,
      avgMasteryScore: 74.2,
      misconceptionDetectionRate: "34.8% học viên có ít nhất 1 lần ngộ nhận"
    },
    topMisconceptions: [
      { topic: "Tokenization tiếng Việt vs Tiếng Anh", affectedStudents: 156, pct: 34.8, severity: "Cao" },
      { topic: "Bản chất Self-Attention vs Duyệt tuần tự", affectedStudents: 132, pct: 29.5, severity: "Cao" },
      { topic: "Chi phí Feed-forward Output Token trong API", affectedStudents: 98, pct: 21.9, severity: "Trung bình" },
      { topic: "Phân biệt Temperature và Context Window", affectedStudents: 62, pct: 13.8, severity: "Thấp" }
    ],
    studentRoster: [
      { id: "S0102", name: "Học viên S0102", level: 2, streak: 2, lastError: "Nhầm 1 từ tiếng Việt = 1 token", status: "Đang tiến bộ", flagged: false },
      { id: "S0448", name: "Học viên S0448", level: 1, streak: 0, lastError: "Cho rằng Attention đọc tuần tự", status: "Cần can thiệp", flagged: true },
      { id: "S0912", name: "Học viên S0912", level: 3, streak: 3, lastError: "Không", status: "Xuất sắc", flagged: false },
      { id: "S1205", name: "Học viên S1205", level: 1, streak: 1, lastError: "Bỏ quên System Prompt khi tính bill", status: "Đang học lại bước 2", flagged: false }
    ]
  }
};
