// =========================================================
// VLearn Adaptive AI Tutor - Complete Interactive Engine
// Hoàn thiện 100% UI theo đúng 4 khối trong Sequence Diagram
// =========================================================

document.addEventListener('DOMContentLoaded', () => {
  const data = window.VLEARN_DATA;
  if (!data) return;

  const validPages = [6, 12, 14, 18, 20, 22, 25];

  const state = {
    activeView: 'student', // 'student' | 'instructor'
    currentDeck: 'd1',
    currentPage: 12,
    streak: 0,
    level: 1,
    overrides: []
  };

  // DOM Elements - Views
  const studentView = document.getElementById('student-view');
  const instructorView = document.getElementById('instructor-view');
  const tabStudentBtn = document.getElementById('tab-student-btn');
  const tabInstructorBtn = document.getElementById('tab-instructor-btn');
  const deckSelect = document.getElementById('slide-deck-select');

  // DOM Elements - Student Pane
  const slideFrame = document.getElementById('slide-pdf-frame');
  const levelBadge = document.getElementById('level-badge');
  const streakBadge = document.getElementById('streak-badge');
  const btnPrevQ = document.getElementById('btn-prev-q');
  const btnNextQ = document.getElementById('btn-next-q');
  const questionSelect = document.getElementById('question-select');

  const bridgeFlow = document.getElementById('bridge-flow');
  const bridgeNote = document.getElementById('bridge-note');
  const questionTitle = document.getElementById('question-title');
  const optionsContainer = document.getElementById('options-container');
  const diagnosticFeedback = document.getElementById('diagnostic-feedback');
  const chatMessages = document.getElementById('chat-messages');
  const chatInputText = document.getElementById('chat-input-text');
  const btnSendChat = document.getElementById('btn-send-chat');

  // DOM Elements - Instructor Pane
  const heatmapBody = document.getElementById('heatmap-body');
  const rosterBody = document.getElementById('roster-body');
  const overrideStudentId = document.getElementById('override-student-id');
  const overrideStudentError = document.getElementById('override-student-error');
  const overrideActionSelect = document.getElementById('override-action-select');
  const overrideNotes = document.getElementById('override-notes');
  const btnSubmitOverride = document.getElementById('btn-submit-override');

  // ================= 1. VIEW SWITCHING (Tính năng 4) =================
  if (tabStudentBtn && tabInstructorBtn) {
    tabStudentBtn.addEventListener('click', () => switchTab('student'));
    tabInstructorBtn.addEventListener('click', () => switchTab('instructor'));
  }

  function switchTab(view) {
    state.activeView = view;
    if (view === 'student') {
      tabStudentBtn.classList.add('active');
      tabInstructorBtn.classList.remove('active');
      studentView.classList.add('active');
      instructorView.classList.remove('active');
    } else {
      tabStudentBtn.classList.remove('active');
      tabInstructorBtn.classList.add('active');
      studentView.classList.remove('active');
      instructorView.classList.add('active');
      renderInstructorData();
    }
  }

  // ================= 2. DECK & QUESTION NAVIGATION =================
  if (deckSelect) {
    deckSelect.addEventListener('change', (e) => {
      state.currentDeck = e.target.value;
      state.currentPage = state.currentDeck === 'd1' ? 12 : 1;
      updateStudentView();
    });
  }

  if (questionSelect) {
    questionSelect.addEventListener('change', (e) => {
      state.currentPage = parseInt(e.target.value, 10);
      updateStudentView();
    });
  }

  if (btnPrevQ) {
    btnPrevQ.addEventListener('click', () => {
      const idx = validPages.indexOf(state.currentPage);
      if (idx > 0) {
        state.currentPage = validPages[idx - 1];
        updateStudentView();
      }
    });
  }

  if (btnNextQ) {
    btnNextQ.addEventListener('click', () => {
      const idx = validPages.indexOf(state.currentPage);
      if (idx < validPages.length - 1 && idx !== -1) {
        state.currentPage = validPages[idx + 1];
        updateStudentView();
      }
    });
  }

  function updateStudentView() {
    const page = state.currentPage;
    const deckFile = state.currentDeck === 'd1' 
      ? 'd1-slide-hackathon.pdf' 
      : 'd2-slide-hackathon.pdf';
    
    // 1. Cập nhật Slide bên trái
    if (slideFrame) {
      slideFrame.src = `../Data/vlearn-pack/slides/${deckFile}?t=${Date.now()}#page=${page}`;
    }

    if (questionSelect) {
      questionSelect.value = page.toString();
    }

    // 2. Cập nhật câu hỏi và trạng thái AI
    renderAIQuestion(page);
  }

  // ================= 3. AI SOCRATIC QUESTION & ADAPTIVE DIFFICULTY =================
  function renderAIQuestion(page) {
    const flowList = data.slideRecallFlow[state.currentDeck] || [];
    let flow = flowList.find(f => f.page === page);
    if (!flow) {
      flow = [...flowList].reverse().find(f => f.page <= page) || flowList[0];
    }
    if (!flow) return;

    // A. Cầu nối lý thuyết (Tính năng 1 trong sơ đồ)
    if (bridgeFlow && bridgeNote) {
      if (flow.recallConnection) {
        bridgeFlow.textContent = `Slide ${flow.recallConnection.priorPage} ➔ Slide ${page}:`;
        bridgeNote.textContent = flow.recallConnection.note;
      } else {
        bridgeFlow.textContent = `Slide ${page}:`;
        bridgeNote.textContent = flow.summary;
      }
    }

    // B. Câu hỏi
    if (questionTitle) {
      questionTitle.textContent = flow.aiQuestion;
    }

    // Reset feedback
    if (diagnosticFeedback) {
      diagnosticFeedback.className = 'diagnostic-feedback';
      diagnosticFeedback.innerHTML = '';
    }

    // C. Render các phương án tương tác A / B
    if (optionsContainer) {
      optionsContainer.innerHTML = '';
      flow.options.forEach((opt, i) => {
        const btn = document.createElement('button');
        btn.className = 'opt-btn';
        btn.innerHTML = `<strong>${String.fromCharCode(65 + i)}.</strong> ${opt.text}`;

        btn.addEventListener('click', () => handleOptionClick(opt, btn, flow));
        optionsContainer.appendChild(btn);
      });
    }
  }

  // Xử lý khi học viên bấm trả lời câu hỏi
  function handleOptionClick(opt, btn, flow) {
    const allBtns = optionsContainer.querySelectorAll('.opt-btn');
    allBtns.forEach(b => b.disabled = true);

    if (opt.isCorrect) {
      btn.classList.add('correct');
      // Thích ứng độ khó: tăng streak (Tính năng 3 trong sơ đồ)
      state.streak += 1;
      updateAdaptiveBadges();

      if (diagnosticFeedback) {
        diagnosticFeedback.className = 'diagnostic-feedback active correct';
        diagnosticFeedback.innerHTML = `<strong>✓ Đúng:</strong> ${opt.feedback || 'Bạn đã kết nối rất tốt với kiến thức ở slide trước.'}`;
      }

      appendChatMessage('tutor', `✓ <strong>Chính xác!</strong> Bạn đã liên kết đúng giữa Slide ${flow.recallConnection?.priorPage || 'trước'} và Slide ${state.currentPage}.`);

      // Kiểm tra điều kiện Level Up (>= 2 câu đúng liên tiếp)
      if (state.streak >= 2) {
        setTimeout(() => {
          if (state.level < 3) {
            state.level += 1;
            state.streak = 0;
            updateAdaptiveBadges();
            alert(`🎉 CHÚC MỪNG: Bạn đã trả lời đúng liên tiếp 2 câu! Hệ thống tự động THĂNG CẤP ĐỘ KHÓ lên Level ${state.level} (Edge-Cases)!`);
          }
        }, 500);
      }
    } else {
      btn.classList.add('wrong');
      // Thích ứng độ khó: reset streak, hạ cấp / scaffolding
      state.streak = 0;
      updateAdaptiveBadges();

      // Chẩn đoán lỗi tư duy (Tính năng 2 trong sơ đồ)
      if (diagnosticFeedback) {
        diagnosticFeedback.className = 'diagnostic-feedback active wrong';
        diagnosticFeedback.innerHTML = `
          <strong>⚠️ Chẩn đoán lỗi tư duy (Misconception):</strong><br/>
          Bạn đang hiểu nhầm hoặc chưa đối chiếu kỹ. Hãy xem lại mã trích dẫn gốc <code>[${flow.citations.join(', ')}]</code> trên slide bên trái để thấy sự khác biệt.
        `;
      }

      appendChatMessage('tutor', `⚠️ Bạn chưa chọn đúng mối liên hệ. Học từ lỗi sai giúp hiểu sâu hơn: Hãy đối chiếu lại sơ đồ trên slide bên trái nhé.`);
    }
  }

  function updateAdaptiveBadges() {
    if (levelBadge) levelBadge.textContent = `Level ${state.level}`;
    if (streakBadge) streakBadge.textContent = `🔥 Chuỗi đúng: ${state.streak}/2`;
  }

  function appendChatMessage(sender, text) {
    if (!chatMessages) return;
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;
    msg.innerHTML = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Gửi tin nhắn tự do
  if (btnSendChat) btnSendChat.addEventListener('click', handleChatSubmit);
  if (chatInputText) {
    chatInputText.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleChatSubmit();
    });
  }

  function handleChatSubmit() {
    if (!chatInputText) return;
    const text = chatInputText.value.trim();
    if (!text) return;

    appendChatMessage('user', text);
    chatInputText.value = '';

    setTimeout(() => {
      const lower = text.toLowerCase();
      if (lower.includes('token')) {
        appendChatMessage('tutor', 'Ở Slide 12, token tiếng Việt có dấu nên tốn gấp 1.3 - 1.4 lần tiếng Anh. Điều này dẫn đến chi phí API ở Slide 25 cao hơn nếu không tính kỹ.');
      } else if (lower.includes('attention')) {
        appendChatMessage('tutor', 'Attention ở Slide 18 là xử lý song song các token nhìn nhau, giải quyết việc bị quên context của các mô hình cũ ở Slide 6 và 14.');
      } else {
        appendChatMessage('tutor', `Ghi nhận ý kiến của bạn về Slide ${state.currentPage}. Hãy tiếp tục bấm nút '▶' hoặc chọn menu câu hỏi để thử sức tiếp nhé!`);
      }
    }, 300);
  }

  // ================= 4. INSTRUCTOR DASHBOARD DATA (Tính năng 4) =================
  function renderInstructorData() {
    const dash = data.instructorDashboardData;
    if (!dash) return;

    // Render Misconception Heatmap
    if (heatmapBody) {
      heatmapBody.innerHTML = dash.topMisconceptions.map(m => `
        <tr>
          <td style="font-weight: 600; color: #f8fafc;">${m.topic}</td>
          <td>${m.affectedStudents} học viên</td>
          <td><strong>${m.pct}%</strong></td>
          <td><span class="tag-severity ${m.severity}">${m.severity}</span></td>
        </tr>
      `).join('');
    }

    // Render Student Roster
    if (rosterBody) {
      rosterBody.innerHTML = dash.studentRoster.map(s => `
        <tr>
          <td style="font-family: var(--font-mono); color: #60a5fa; font-weight: 700;">${s.id}</td>
          <td>Level ${s.level}</td>
          <td>${s.streak} 🔥</td>
          <td style="color: #cbd5e1;">${s.lastError}</td>
          <td style="color: ${s.flagged ? '#fb7185' : '#34d399'}; font-weight: 600;">${s.status}</td>
          <td>
            <button class="btn-mini-override" onclick="window.handleSelectOverride('${s.id}', '${s.lastError}')">
              Can thiệp
            </button>
          </td>
        </tr>
      `).join('');
    }
  }

  // Chọn học viên để can thiệp
  window.handleSelectOverride = (id, err) => {
    if (overrideStudentId) overrideStudentId.value = id;
    if (overrideStudentError) overrideStudentError.value = err;
    if (overrideNotes) overrideNotes.focus();
  };

  // Submit Override
  if (btnSubmitOverride) {
    btnSubmitOverride.addEventListener('click', () => {
      const studentId = overrideStudentId ? overrideStudentId.value : 'S0448';
      const action = overrideActionSelect ? overrideActionSelect.value : '';
      const notes = overrideNotes ? overrideNotes.value : '';

      state.overrides.push({ studentId, action, notes, time: new Date().toLocaleTimeString() });
      alert(`✅ THÀNH CÔNG (TÍNH NĂNG 4):\nGiảng viên đã can thiệp ghi đè chẩn đoán cho học viên ${studentId}!\nKịch bản sư phạm của Bot đã được cập nhật thành công.`);
    });
  }

  // Khởi động tại Slide 12
  updateStudentView();
});
