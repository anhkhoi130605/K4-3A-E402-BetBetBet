// =========================================================
// VLearn Adaptive AI Tutor - Auto-Tracking Socratic Engine
// AI dynamically follows the slide the user is reading
// Powered by GPT-4o-mini (OpenRouter) & Adaptive RAG
// =========================================================

document.addEventListener('DOMContentLoaded', () => {
  const localData = window.VLEARN_DATA || {};
  const API_BASE = window.location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:8000';

  const state = {
    currentUser: null,
    currentDeck: 'd1',
    currentPage: 1,
    currentLevel: 1,
    currentStreak: 0,
    currentTheta: 0.0,
    activeCheckpointPage: null,
    currentQuestionData: null,
    studentId: 'S0102',
    chatHistory: []
  };

  let slideObserver = null;
  let scrollDebounceTimer = null;

  // Metadata các mốc kiến thức quan trọng (Checkpoints)
  const CHECKPOINTS_META = {
    d1: [
      { page: 6, title: "LLM là gì & Cơ chế Next-Token Prediction" },
      { page: 12, title: "Token hóa & Đặc thù Tiếng Việt (1.35x sub-token)" },
      { page: 18, title: "Kiến trúc Transformer & Self-Attention song song" },
      { page: 22, title: "Tham số Temperature & Tính Tất Định" },
      { page: 25, title: "Token Economy & Tối Ưu Chi Phí Gọi API" }
    ],
    d2: [
      { page: 5, title: "Phân loại bài toán AI & Machine Learning" },
      { page: 11, title: "Đánh giá mô hình & Metrics (Precision, Recall, F1)" },
      { page: 20, title: "Triển khai thực tế & Giám sát Data Drift" }
    ]
  };

  function getCheckpoints(deck) {
    return CHECKPOINTS_META[deck] || CHECKPOINTS_META['d1'];
  }

  function isKeyCheckpoint(deck, page) {
    return getCheckpoints(deck).some(c => c.page === page);
  }

  function getNextCheckpoint(deck, currentPage) {
    const chks = getCheckpoints(deck);
    return chks.find(c => c.page > currentPage) || chks[chks.length - 1];
  }

  // Thuật toán trộn ngẫu nhiên mảng Fisher-Yates (chống học vẹt vị trí đáp án)
  function shuffleArray(array) {
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  // DOM Elements - Auth & Header
  const authModal = document.getElementById('auth-modal');
  const authForm = document.getElementById('auth-form');
  const authUsername = document.getElementById('auth-username');
  const authPassword = document.getElementById('auth-password');
  const authFullname = document.getElementById('auth-fullname');
  const authRoleSelect = document.getElementById('auth-role-select');
  const registerFields = document.getElementById('register-fields');
  const linkToggleAuth = document.getElementById('link-toggle-auth');
  const authErrorMsg = document.getElementById('auth-error-msg');
  const btnAuthSubmit = document.getElementById('btn-auth-submit');
  const btnQuickStudent = document.getElementById('btn-quick-student');
  const btnQuickTeacher = document.getElementById('btn-quick-teacher');

  const headerRoleBadge = document.getElementById('header-role-badge');
  const currentUserName = document.getElementById('current-user-name');
  const btnLogout = document.getElementById('btn-logout');
  const deckSelect = document.getElementById('slide-deck-select');
  const btnRerollCheckpoints = document.getElementById('btn-reroll-checkpoints');

  // DOM Elements - Views
  const studentView = document.getElementById('student-view');
  const instructorView = document.getElementById('instructor-view');

  // DOM Elements - Student Pane (Scroll Feed & AI Tracking)
  const slideScrollContainer = document.getElementById('slide-scroll-container');
  const aiStatusDot = document.getElementById('ai-status-dot');
  const aiTrackingStatus = document.getElementById('ai-tracking-status');
  const checkpointCard = document.getElementById('checkpoint-card');
  const bridgeCard = document.getElementById('bridge-card');
  const bridgeFlow = document.getElementById('bridge-flow');
  const bridgeNote = document.getElementById('bridge-note');
  const questionTitle = document.getElementById('question-title');
  const optionsContainer = document.getElementById('options-container');
  const evaluationCard = document.getElementById('evaluation-card');
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
  // DOM Elements - Adaptive Level & Streak Badges
  const studentLevelBadge = document.getElementById('student-level-badge');
  const studentStreakBadge = document.getElementById('student-streak-badge');
  const questionLevelBadge = document.getElementById('question-level-badge');

  function updateAdaptiveBadges() {
    if (studentLevelBadge) {
      studentLevelBadge.className = `level-badge level-${state.currentLevel}`;
      const labels = {
        1: '🌱 Level 1 (Cơ bản)',
        2: '⚡ Level 2 (Vận dụng)',
        3: '👑 Level 3 (Chuyên sâu)'
      };
      studentLevelBadge.textContent = labels[state.currentLevel] || `Level ${state.currentLevel}`;
    }

    if (studentStreakBadge) {
      studentStreakBadge.textContent = `🔥 ${state.currentStreak}/2`;
      studentStreakBadge.classList.toggle('fire', state.currentStreak >= 1);
    }
  }

  // DOM Elements - Slide Zoom Controls
  const btnZoomOut = document.getElementById('btn-zoom-out');
  const btnZoomIn = document.getElementById('btn-zoom-in');
  const btnZoomFit = document.getElementById('btn-zoom-fit');
  const zoomLevelText = document.getElementById('zoom-level-text');

  let currentZoom = 80;

  function applySlideZoom(zoom) {
    currentZoom = Math.min(Math.max(zoom, 50), 120);
    if (zoomLevelText) zoomLevelText.textContent = `${currentZoom}%`;
    document.querySelectorAll('.slide-page-item').forEach(el => {
      el.style.width = `${currentZoom}%`;
      el.style.maxWidth = `${Math.round(820 * (currentZoom / 80))}px`;
    });
  }

  if (btnZoomOut) {
    btnZoomOut.addEventListener('click', () => applySlideZoom(currentZoom - 10));
  }
  if (btnZoomIn) {
    btnZoomIn.addEventListener('click', () => applySlideZoom(currentZoom + 10));
  }
  if (btnZoomFit) {
    btnZoomFit.addEventListener('click', () => applySlideZoom(80));
  }

  let isRegisterMode = false;

  // ================= 1. AUTHENTICATION & ROLE-BASED ROUTING =================
  function initAuth() {
    const savedUser = localStorage.getItem('vlearn_user');
    if (savedUser) {
      try {
        state.currentUser = JSON.parse(savedUser);
        state.studentId = state.currentUser.id || 'S0102';
        state.currentLevel = state.currentUser.level || 1;
        state.currentStreak = state.currentUser.streak || 0;
        updateAdaptiveBadges();
        applyUserRole(state.currentUser);
        return;
      } catch (e) {
        localStorage.removeItem('vlearn_user');
      }
    }
    updateAdaptiveBadges();
    showAuthModal();
  }

  function showAuthModal() {
    if (authModal) authModal.classList.remove('hidden');
  }

  function hideAuthModal() {
    if (authModal) authModal.classList.add('hidden');
  }

  if (btnQuickStudent) {
    btnQuickStudent.addEventListener('click', () => loginDirectly('hocvien', '123'));
  }

  if (btnQuickTeacher) {
    btnQuickTeacher.addEventListener('click', () => loginDirectly('giangvien', '123'));
  }

  if (linkToggleAuth) {
    linkToggleAuth.addEventListener('click', (e) => {
      e.preventDefault();
      isRegisterMode = !isRegisterMode;
      if (isRegisterMode) {
        if (registerFields) registerFields.style.display = 'block';
        if (btnAuthSubmit) btnAuthSubmit.textContent = 'Đăng ký';
        linkToggleAuth.textContent = 'Đã có tài khoản? Đăng nhập';
      } else {
        if (registerFields) registerFields.style.display = 'none';
        if (btnAuthSubmit) btnAuthSubmit.textContent = 'Đăng nhập';
        linkToggleAuth.textContent = 'Chưa có tài khoản? Đăng ký';
      }
      if (authErrorMsg) authErrorMsg.textContent = '';
    });
  }

  if (authForm) {
    authForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (authErrorMsg) authErrorMsg.textContent = '';
      const username = authUsername.value.trim();
      const password = authPassword.value.trim();

      if (isRegisterMode) {
        const fullname = (authFullname ? authFullname.value.trim() : '') || username;
        const role = authRoleSelect ? authRoleSelect.value : 'student';
        await registerUser(username, password, fullname, role);
      } else {
        await loginDirectly(username, password);
      }
    });
  }

  async function loginDirectly(username, password) {
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.user) {
          saveUserSession(data.user);
          return;
        } else {
          showAuthError(data.message || 'Sai thông tin đăng nhập');
          return;
        }
      }
    } catch (e) {
      console.warn('[Auth] Offline login fallback:', e.message);
    }

    if (username.toLowerCase().includes('giang') || username.toLowerCase() === 'gv') {
      saveUserSession({ id: 'GV001', username, name: 'ThS. Trần Nam (Giảng viên)', role: 'teacher' });
    } else {
      saveUserSession({ id: 'S0102', username, name: 'Học viên S0102', role: 'student' });
    }
  }

  async function registerUser(username, password, name, role) {
    try {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, name, role })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.user) {
          saveUserSession(data.user);
          return;
        }
      }
    } catch (e) {
      console.warn('[Auth] Offline register fallback:', e.message);
    }

    saveUserSession({ id: role === 'teacher' ? 'GV999' : 'S9999', username, name, role });
  }

  function saveUserSession(user) {
    state.currentUser = user;
    state.studentId = user.id || 'S0102';
    state.currentLevel = user.level || 1;
    state.currentStreak = user.streak || 0;
    updateAdaptiveBadges();
    localStorage.setItem('vlearn_user', JSON.stringify(user));
    hideAuthModal();
    applyUserRole(user);
  }

  function showAuthError(msg) {
    if (authErrorMsg) authErrorMsg.textContent = msg;
  }

  if (btnLogout) {
    btnLogout.addEventListener('click', () => {
      localStorage.removeItem('vlearn_user');
      state.currentUser = null;
      showAuthModal();
    });
  }

  function applyUserRole(user) {
    if (!user) return;
    if (currentUserName) currentUserName.textContent = user.name;

    if (user.role === 'teacher') {
      if (headerRoleBadge) {
        headerRoleBadge.className = 'badge-role-header teacher';
        headerRoleBadge.textContent = 'Giáo viên';
      }
      if (deckSelect) deckSelect.style.display = 'none';
      if (studentView) studentView.classList.remove('active');
      if (instructorView) instructorView.classList.add('active');
      fetchInstructorData();
    } else {
      if (headerRoleBadge) {
        headerRoleBadge.className = 'badge-role-header student';
        headerRoleBadge.textContent = 'Học sinh';
      }
      if (deckSelect) deckSelect.style.display = 'inline-block';
      if (instructorView) instructorView.classList.remove('active');
      if (studentView) studentView.classList.add('active');
      initSlideFeed();
      setTimeout(streamWelcomeMessage, 250);
    }
  }

  // ================= 1.5. CẤU HÌNH API KEY (OPENAI / OPENROUTER) =================
  const btnApiSettings = document.getElementById('btn-api-settings');
  const apiModal = document.getElementById('api-modal');
  const btnCloseApiModal = document.getElementById('btn-close-api-modal');
  const apiKeyForm = document.getElementById('api-key-form');
  const apiKeyInput = document.getElementById('api-key-input');
  const apiKeyFeedback = document.getElementById('api-key-feedback');
  const apiModalStatusText = document.getElementById('api-modal-status-text');
  const aiStatusLabel = document.getElementById('ai-status-label');

  async function checkAIStatus() {
    try {
      const res = await fetch(`${API_BASE}/api/settings/ai-status`);
      if (res.ok) {
        const data = await res.json();
        if (data.is_available) {
          if (aiStatusDot) aiStatusDot.className = 'ai-status-dot online';
          if (aiStatusLabel) aiStatusLabel.textContent = `🟢 ${data.provider === 'openai' ? 'OpenAI' : 'OpenRouter'}`;
          if (apiModalStatusText) {
            apiModalStatusText.innerHTML = `🟢 <b>Đang kết nối:</b> ${data.provider.toUpperCase()} (Model: <code>${data.model}</code>)<br/><span style="color:#94a3b8; font-size:0.75rem;">Key: ${data.masked_key}</span>`;
          }
        } else {
          if (aiStatusDot) aiStatusDot.className = 'ai-status-dot offline';
          if (aiStatusLabel) aiStatusLabel.textContent = '⚪ Chế độ dự phòng';
          if (apiModalStatusText) {
            apiModalStatusText.innerHTML = `⚪ <b>Chưa kết nối AI:</b> Đang dùng chế độ Fallback RAG & Ngân hàng tri thức`;
          }
        }
      }
    } catch (e) {
      console.warn('[AIStatus] Check error:', e.message);
    }
  }

  if (btnApiSettings) {
    btnApiSettings.addEventListener('click', () => {
      checkAIStatus();
      if (apiModal) apiModal.style.display = 'flex';
      if (apiKeyFeedback) apiKeyFeedback.style.display = 'none';
      if (apiKeyInput) apiKeyInput.focus();
    });
  }

  if (btnCloseApiModal) {
    btnCloseApiModal.addEventListener('click', () => {
      if (apiModal) apiModal.style.display = 'none';
    });
  }

  if (apiModal) {
    apiModal.addEventListener('click', (e) => {
      if (e.target === apiModal) apiModal.style.display = 'none';
    });
  }

  if (apiKeyForm) {
    apiKeyForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const key = apiKeyInput.value.trim();
      if (!key) return;

      const btnSave = document.getElementById('btn-save-api-key');
      if (btnSave) {
        btnSave.disabled = true;
        btnSave.textContent = '⏳ Đang lưu...';
      }

      try {
        const res = await fetch(`${API_BASE}/api/settings/openrouter-key`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          if (apiKeyFeedback) {
            apiKeyFeedback.style.display = 'block';
            apiKeyFeedback.style.color = '#34d399';
            apiKeyFeedback.textContent = `✅ ${data.message}`;
          }
          apiKeyInput.value = '';
          await checkAIStatus();
          setTimeout(() => {
            if (apiModal) apiModal.style.display = 'none';
          }, 1500);
        } else {
          if (apiKeyFeedback) {
            apiKeyFeedback.style.display = 'block';
            apiKeyFeedback.style.color = '#f87171';
            apiKeyFeedback.textContent = `❌ Lỗi: ${data.detail || 'Không thể lưu key'}`;
          }
        }
      } catch (err) {
        if (apiKeyFeedback) {
          apiKeyFeedback.style.display = 'block';
          apiKeyFeedback.style.color = '#f87171';
          apiKeyFeedback.textContent = `❌ Lỗi kết nối: ${err.message}`;
        }
      } finally {
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.textContent = 'Lưu & Kết nối';
        }
      }
    });
  }

  // ================= 2. BỘ SLIDE CUỘN TỰ DO & AI THEO DÕI TỰ ĐỘNG =================
  if (deckSelect) {
    deckSelect.addEventListener('change', (e) => {
      state.currentDeck = e.target.value;
      state.currentPage = 1;
      state.activeCheckpointPage = null;
      initSlideFeed();
    });
  }

  if (btnRerollCheckpoints) {
    btnRerollCheckpoints.addEventListener('click', async () => {
      btnRerollCheckpoints.disabled = true;
      btnRerollCheckpoints.textContent = '⏳ Đang đổi...';
      try {
        const res = await fetch(`${API_BASE}/api/checkpoints?deck=${state.currentDeck}&refresh=true`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.checkpoints) {
            CHECKPOINTS_META[state.currentDeck] = data.checkpoints;
          }
        }
      } catch (e) {
        console.warn('[VLearn] Reroll checkpoints error:', e.message);
      }
      state.activeCheckpointPage = null;
      await initSlideFeed();
      btnRerollCheckpoints.disabled = false;
      btnRerollCheckpoints.textContent = '🎲 Trạm ngẫu nhiên';
    });
  }

  async function initSlideFeed() {
    if (!slideScrollContainer) return;
    slideScrollContainer.innerHTML = '<div style="color:#94a3b8; padding:20px; text-align:center;">Đang tải toàn bộ bài giảng slide...</div>';

    // 1. Tải danh sách các trạm kiểm tra ngẫu nhiên từ Backend
    try {
      const cpRes = await fetch(`${API_BASE}/api/checkpoints?deck=${state.currentDeck}`);
      if (cpRes.ok) {
        const cpData = await cpRes.json();
        if (cpData && cpData.checkpoints && cpData.checkpoints.length > 0) {
          CHECKPOINTS_META[state.currentDeck] = cpData.checkpoints;
        }
      }
    } catch (e) {
      console.warn('[VLearn] Dùng checkpoints mặc định:', e.message);
    }

    let totalPages = 29;
    try {
      const res = await fetch(`${API_BASE}/api/deck-info?deck=${state.currentDeck}`);
      if (res.ok) {
        const info = await res.json();
        totalPages = info.total_pages || 29;
      }
    } catch (e) {
      console.warn('[DeckInfo] Using default 29 pages:', e.message);
    }

    // Render các trang slide liên tục, đánh dấu các trạm kiểm tra ngẫu nhiên
    slideScrollContainer.innerHTML = '';
    for (let p = 1; p <= totalPages; p++) {
      const isChkp = isKeyCheckpoint(state.currentDeck, p);
      const pageItem = document.createElement('div');
      pageItem.className = 'slide-page-item' + (isChkp ? ' has-checkpoint' : '');
      pageItem.id = `slide-item-${p}`;
      pageItem.dataset.page = p;
      pageItem.style.width = `${currentZoom}%`;
      pageItem.style.maxWidth = `${Math.round(820 * (currentZoom / 80))}px`;

      pageItem.innerHTML = `
        <span class="slide-page-tag${isChkp ? ' checkpoint-tag' : ''}">Slide ${p}${isChkp ? ' 🎯 Trạm kiểm tra' : ''}</span>
        <img class="slide-page-img" loading="lazy" src="${API_BASE}/api/slide-image?deck=${state.currentDeck}&page=${p}&dpi=150" alt="Slide ${p}" />
      `;
      slideScrollContainer.appendChild(pageItem);
    }

    setupSlideObserver();

    // Khởi động AI tại trang 1
    onSlideInView(1);
  }

  function setupSlideObserver() {
    if (slideObserver) slideObserver.disconnect();

    slideObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          const page = parseInt(entry.target.dataset.page, 10);
          clearTimeout(scrollDebounceTimer);
          scrollDebounceTimer = setTimeout(() => {
            if (page !== state.currentPage) {
              onSlideInView(page);
            }
          }, 200); // Debounce 200ms
        }
      });
    }, {
      root: slideScrollContainer,
      threshold: 0.5
    });

    document.querySelectorAll('.slide-page-item').forEach(el => slideObserver.observe(el));
  }

  // Khi người học lướt đến Slide nào -> Xử lý tối giản:
  // - Nếu là slide thường: Cập nhật vị trí trang, KHÔNG đổi/reload câu hỏi
  // - Nếu là slide mốc kiến thức mới (Checkpoint): AI tự động đề xuất câu hỏi phù hợp
  function onSlideInView(page) {
    state.currentPage = page;

    // Highlight viền slide đang xem
    document.querySelectorAll('.slide-page-item').forEach(el => {
      el.classList.toggle('active-viewing', parseInt(el.dataset.page, 10) === page);
    });

    const isCheckpoint = isKeyCheckpoint(state.currentDeck, page);

    if (isCheckpoint) {
      if (aiTrackingStatus) {
        aiTrackingStatus.textContent = `AI đang đồng hành: Slide ${page}`;
      }
      if (aiStatusDot) {
        aiStatusDot.style.background = '#8b5cf6';
        aiStatusDot.style.boxShadow = '0 0 10px #8b5cf6';
      }

      // Chỉ nạp câu hỏi mới nếu chuyển sang mốc khác, không reload khi cuộn nhẹ trong cùng mốc
      if (state.activeCheckpointPage !== page) {
        state.activeCheckpointPage = page;
        loadSlideQuestion(state.currentDeck, page);
      }
    } else {
      // Slide thường: Giữ nguyên câu hỏi hiện tại, không reload hay gián đoạn việc đọc
      if (aiTrackingStatus) {
        aiTrackingStatus.textContent = `AI đang đồng hành: Slide ${page}`;
      }
      if (aiStatusDot) {
        aiStatusDot.style.background = '#10b981';
        aiStatusDot.style.boxShadow = '0 0 8px #10b981';
      }
    }
  }

  // ================= 3. SINH CÂU HỎI THÍCH ỨNG (GPT-4o-mini) =================
  async function loadSlideQuestion(deck, page) {
    // 1. Ẩn khối câu hỏi cũ, không hiển thị bất kỳ dòng chữ "Đang tải câu hỏi..."
    if (checkpointCard) {
      checkpointCard.style.display = 'none';
    }
    if (questionTitle) questionTitle.innerHTML = '';
    if (optionsContainer) optionsContainer.innerHTML = '';
    if (evaluationCard) {
      evaluationCard.style.display = 'none';
      evaluationCard.innerHTML = '';
    }

    // 2. Hiển thị hiệu ứng 3 chấm "AI đang nhập..." tự nhiên trong khung chat
    const existingTyping = document.getElementById('ai-typing-indicator');
    if (existingTyping) existingTyping.remove();

    const typingEl = document.createElement('div');
    typingEl.className = 'chat-msg tutor typing-indicator-msg';
    typingEl.id = 'ai-typing-indicator';
    typingEl.innerHTML = `
      <div class="typing-bubble">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    `;
    if (chatMessages) {
      chatMessages.appendChild(typingEl);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    try {
      const res = await fetch(`${API_BASE}/api/slide-question?deck=${deck}&page=${page}&level=${state.currentLevel}&student_id=${state.studentId}&theta=${state.currentTheta ?? 0.0}`);
      if (res.ok) {
        const q = await res.json();
        const curTyping = document.getElementById('ai-typing-indicator');
        if (curTyping) curTyping.remove();
        renderQuestionUI(q);
        return;
      }
    } catch (e) {
      console.warn('[VLearn] API offline, using fallback:', e.message);
    }

    const curTyping = document.getElementById('ai-typing-indicator');
    if (curTyping) curTyping.remove();
    renderFallbackQuestion(page);
  }

  function renderQuestionUI(q) {
    state.currentQuestionData = q;

    if (checkpointCard) {
      checkpointCard.style.display = 'flex';
      if (chatMessages && checkpointCard.parentElement === chatMessages) {
        chatMessages.appendChild(checkpointCard);
      }
    }

    if (bridgeCard) {
      if (q.prior_page && (q.bridge_note || q.bridge_concept)) {
        bridgeCard.style.display = 'flex';
        if (bridgeNote) {
          bridgeNote.innerHTML = `<strong>Gợi nhớ từ Slide ${q.prior_page}:</strong> ${q.bridge_note || q.bridge_concept}`;
        }
      } else {
        bridgeCard.style.display = 'none';
      }
    }

    if (questionLevelBadge) {
      questionLevelBadge.textContent = q.level_label || `Level ${q.level || state.currentLevel}`;
    }

    if (questionTitle) {
      questionTitle.textContent = q.ai_question || 'Hãy suy ngẫm về kiến thức trên slide:';
    }

    if (optionsContainer) {
      optionsContainer.innerHTML = '';
      const displayOptions = shuffleArray(q.options || []);
      displayOptions.forEach((opt, i) => {
        const btn = document.createElement('button');
        btn.className = 'opt-btn';
        const keyChar = String.fromCharCode(65 + i);
        btn.innerHTML = `<span class="opt-key" style="font-family:var(--font-mono);font-weight:700;color:var(--accent-light);min-width:18px;">${keyChar}.</span><span class="opt-text">${opt.text}</span>`;
        btn.addEventListener('click', () => handleStudentAnswer(
          opt.text,
          opt.is_correct,
          opt.feedback,
          q.citations,
          false,
          q.ai_question,
          opt.id || keyChar
        ));
        optionsContainer.appendChild(btn);
      });
    }

    if (evaluationCard) {
      evaluationCard.style.display = 'none';
      evaluationCard.innerHTML = '';
    }

    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  function renderFallbackQuestion(page) {
    const flowList = localData.slideRecallFlow ? (localData.slideRecallFlow[state.currentDeck] || []) : [];
    let flow = flowList.find(f => f.page === page);
    if (!flow) {
      flow = [...flowList].reverse().find(f => f.page <= page) || flowList[0];
    }
    if (!flow) return;

    renderQuestionUI({
      deck: state.currentDeck,
      page: page,
      title: flow.title,
      summary: flow.summary,
      prior_page: flow.recallConnection?.priorPage,
      bridge_concept: flow.recallConnection?.concept,
      bridge_note: flow.recallConnection?.note,
      ai_question: flow.aiQuestion,
      options: flow.options.map(o => ({
        id: o.text.substring(0, 1),
        text: o.text,
        is_correct: o.isCorrect,
        feedback: o.feedback || ''
      })),
      citations: flow.citations || []
    });
  }

  // ================= 4. ĐÁNH GIÁ CÂU TRẢ LỜI, CHẤM ĐIỂM & HƯỚNG DẪN ÔN TẬP =================
  async function handleStudentAnswer(answerText, defaultCorrect = false, defaultFeedback = '', defaultCitations = [], skipUserMsg = false, questionText = '', optionId = null) {
    const allBtns = optionsContainer ? optionsContainer.querySelectorAll('.opt-btn') : [];
    allBtns.forEach(b => b.disabled = true);


    const currentQText = questionText || (state.currentQuestionData ? state.currentQuestionData.ai_question : '');

    try {
      const res = await fetch(`${API_BASE}/api/chat/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: state.studentId,
          deck: state.currentDeck,
          page: (state.currentQuestionData && state.currentQuestionData.page) ? state.currentQuestionData.page : state.currentPage,
          answer_text: answerText,
          current_level: state.currentLevel,
          current_streak: state.currentStreak,
          question_text: currentQText,
          selected_option_id: optionId,
          is_option_correct: defaultCorrect,
          theta: state.currentTheta ?? 0.0
        })
      });

      if (res.ok) {
        const evalResult = await res.json();
        applyEvaluationResult(evalResult, answerText, defaultFeedback);
        return;
      }
    } catch (e) {
      console.warn('[VLearn] API evaluate fallback:', e.message);
    }

    const evalResult = {
      is_correct: defaultCorrect,
      score: defaultCorrect ? 100 : 40,
      grade: defaultCorrect ? 'Xuất sắc (Nắm vững bản chất)' : 'Cần củng cố (Chưa chính xác)',
      feedback: defaultFeedback || (defaultCorrect ? 'Chính xác! Bạn đã kết nối đúng bản chất.' : 'Chưa đúng mối liên hệ.'),
      new_level: (defaultCorrect && state.currentStreak >= 1) ? Math.min(state.currentLevel + 1, 3) : state.currentLevel,
      new_streak: defaultCorrect ? state.currentStreak + 1 : 0,
      should_level_up: defaultCorrect && state.currentStreak >= 1 && state.currentLevel < 3,
      review_recommendation: defaultCorrect
        ? 'Bạn đã nắm rất vững kiến thức mốc này! Hãy tự tin tiếp tục học các slide tiếp theo.'
        : `Bạn cần mở lại slide trước để ôn tập lại cơ sở lý thuyết.`,
      review_slide: defaultCorrect ? null : (state.currentQuestionData?.prior_page || state.currentPage),
      socratic_hint: defaultCorrect ? 'Bạn đã nắm rất vững kiến thức!' : 'Quan sát kỹ slide bên trái để kiểm tra.'
    };
    applyEvaluationResult(evalResult, answerText, defaultFeedback);
  }

  function applyEvaluationResult(res, answerText, defaultFeedback = '') {
    // Đồng bộ cấp độ nhận thức thích ứng (Adaptive Learning Progression)
    const prevLevel = state.currentLevel;
    if (typeof res.new_level === 'number') {
      state.currentLevel = res.new_level;
    }
    if (typeof res.new_streak === 'number') {
      state.currentStreak = res.new_streak;
    } else {
      state.currentStreak = res.is_correct ? state.currentStreak + 1 : 0;
    }
    if (typeof res.new_theta === 'number') {
      state.currentTheta = res.new_theta;
    }
    updateAdaptiveBadges();

    // Thông báo Toast chúc mừng khi thăng cấp độ
    if (res.should_level_up || state.currentLevel > prevLevel) {
      const levelLabels = { 2: 'Vận dụng thực tế', 3: 'Phản biện & Tối ưu' };
      const toast = document.createElement('div');
      toast.className = 'level-up-toast';
      toast.innerHTML = `🎉 <strong>THĂNG CẤP ĐỘ!</strong> Bạn đã đạt <strong>Level ${state.currentLevel} (${levelLabels[state.currentLevel] || 'Nâng cao'})</strong>. Trạm tiếp theo sẽ có thử thách tư duy sâu hơn!`;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 5000);
    }


    // Hiển thị khung chấm điểm & hướng dẫn ôn tập
    // Ẩn hoàn toàn evaluationCard (bỏ toàn bộ thang điểm 40/100, 100/100 theo yêu cầu)
    if (evaluationCard) {
      evaluationCard.style.display = 'none';
      evaluationCard.innerHTML = '';
    }

    // Đánh dấu màu trên nút tùy chọn (xanh cho đúng, đỏ cho sai)
    if (optionsContainer) {
      const allBtns = optionsContainer.querySelectorAll('.opt-btn');
      allBtns.forEach(btn => {
        if (btn.textContent.includes(answerText) || answerText.includes(btn.textContent.replace(/^[A-Z]\.\s*/, ''))) {
          btn.classList.add(res.is_correct ? 'correct' : 'wrong');
        }
      });
    }

    // Đưa câu trả lời của học viên vào khung chat
    appendChatMessage('user', answerText);

    // Chuẩn hóa nội dung nhận xét: Đúng hay sai, Sai ở đâu, Cần củng cố gì
    const cleanFeedback = defaultFeedback || res.feedback || (res.is_correct ? 'Bạn đã nắm rất vững bản chất của khái niệm này.' : 'Phương án này phản ánh một ngộ nhận thường gặp.');
    const reviewSlide = res.review_slide || (state.currentQuestionData?.prior_page || state.currentPage);

    let tutorMsg = '';
    if (res.is_correct) {
      const explanation = cleanFeedback.replace(/^(🎉\s*)?(Chính xác!?|Rất chuẩn!?|Xuất sắc!?|Đúng!?)\s*/i, '').trim();
      tutorMsg = `
        <div style="font-size:0.88rem; font-weight:700; color:#10b981; margin-bottom:6px;">
          ✅ Chính xác!
        </div>
        <div style="font-size:0.82rem; line-height:1.55; color:#f1f5f9;">
          <strong>Nhận xét:</strong> ${explanation || 'Bạn đã nắm rất vững bản chất kiến thức của slide này.'}
        </div>
      `;
    } else {
      const explanation = cleanFeedback.replace(/^(⚠️\s*)?(Chưa đúng:?|Sai lầm:?|Chưa chính xác:?|Không đúng:?)\s*/i, '').trim();
      const reviewTopic = res.review_recommendation || `Đối chiếu lại kiến thức trên Slide ${reviewSlide} để làm rõ khái niệm.`;

      tutorMsg = `
        <div style="font-size:0.88rem; font-weight:700; color:#f43f5e; margin-bottom:6px;">
          ❌ Chưa chính xác!
        </div>
        <div style="display:flex; flex-direction:column; gap:6px; font-size:0.82rem; line-height:1.55; color:#f1f5f9;">
          <div>
            <span style="font-weight:700; color:#fb923c;">🔍 Sai ở đâu:</span> ${explanation}
          </div>
          <div>
            <span style="font-weight:700; color:#818cf8;">📚 Cần củng cố:</span> ${reviewTopic}
          </div>
          ${reviewSlide ? `
            <div style="margin-top:4px;">
              <button class="btn-jump-slide" onclick="window.jumpToSlide(${reviewSlide})" style="padding:5px 12px; font-size:0.75rem;">
                👉 Mở lại Slide ${reviewSlide} để xem lại bài giảng
              </button>
            </div>
          ` : ''}
        </div>
      `;
    }

    // Hiển thị phản hồi với hiệu ứng streaming typewriter mượt mà
    streamChatMessage('tutor', tutorMsg, null, 14);
  }

  // Hàm chuyển nhanh tới slide chỉ định với hiệu ứng highlight
  window.jumpToSlide = function (targetPage) {
    const targetEl = document.getElementById(`slide-item-${targetPage}`);
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      targetEl.classList.add('flash-review-target');
      setTimeout(() => {
        targetEl.classList.remove('flash-review-target');
      }, 2500);
    }
  };

  function appendChatMessage(sender, text) {
    if (!chatMessages) return null;
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;
    msg.innerHTML = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msg;
  }

  // Hiệu ứng streaming (typewriter) chân thực như ChatGPT/Claude
  function streamChatMessage(sender, htmlContent, onComplete, speed = 14, insertBeforeEl = null) {
    if (!chatMessages) return null;
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;
    if (insertBeforeEl && insertBeforeEl.parentElement === chatMessages) {
      chatMessages.insertBefore(msg, insertBeforeEl);
    } else {
      chatMessages.appendChild(msg);
    }

    // Tách thành token: thẻ HTML giữ nguyên cụm, chữ tách theo từng từ/khoảng trắng
    const tokens = htmlContent.match(/(<[^>]+>|[^<>\s]+|\s+)/g) || [htmlContent];
    let idx = 0;
    let currentHtml = '';

    const cursor = document.createElement('span');
    cursor.className = 'streaming-cursor';
    cursor.textContent = '●';
    msg.appendChild(cursor);

    function step() {
      if (idx < tokens.length) {
        currentHtml += tokens[idx];
        idx++;
        msg.innerHTML = currentHtml;
        msg.appendChild(cursor);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        setTimeout(step, speed);
      } else {
        if (cursor.parentElement) cursor.remove();
        msg.innerHTML = currentHtml;
        chatMessages.scrollTop = chatMessages.scrollHeight;
        if (typeof onComplete === 'function') onComplete();
      }
    }
    step();
    return msg;
  }

  // Tự động streaming lời chào thân thiện mở đầu khi học viên vào bài học
  function streamWelcomeMessage() {
    if (!chatMessages) return;
    const existing = chatMessages.querySelector('.welcome-msg');
    if (existing) return;

    const welcomeHtml = `👋 <strong>Chào bạn!</strong> Tôi là AI đồng hành học tập. Tôi sẽ theo dõi các slide bạn đang đọc và đặt câu hỏi gợi mở tại các slide trọng tâm, cũng như giải đáp mọi thắc mắc của bạn!`;
    const msg = streamChatMessage('tutor', welcomeHtml, null, 14, checkpointCard);
    if (msg) msg.classList.add('welcome-msg');
  }

  if (btnSendChat) btnSendChat.addEventListener('click', handleChatSubmit);
  if (chatInputText) {
    chatInputText.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleChatSubmit();
    });
  }

  // Quick suggestion chips: Luôn hỏi AI Tutor để được hướng dẫn/ví dụ, KHÔNG nộp bài chấm điểm
  document.querySelectorAll('.quick-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const promptText = chip.getAttribute('data-prompt');
      if (promptText) {
        appendChatMessage('user', promptText);
        askSocraticTutor(promptText);
      }
    });
  });

  async function askSocraticTutor(message) {
    const typingId = 'typing-' + Date.now();
    const typingMsg = document.createElement('div');
    typingMsg.className = 'chat-msg tutor typing-indicator-msg';
    typingMsg.id = typingId;
    typingMsg.innerHTML = `
      <div class="typing-bubble">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    `;
    if (chatMessages) {
      chatMessages.appendChild(typingMsg);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    try {
      const currentQText = state.currentQuestionData ? state.currentQuestionData.ai_question : '';
      if (!state.chatHistory) state.chatHistory = [];
      const payloadHistory = state.chatHistory.slice(-6);

      const res = await fetch(`${API_BASE}/api/chat/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: state.studentId,
          deck: state.currentDeck,
          page: state.currentPage,
          message: message,
          current_level: state.currentLevel,
          question_context: currentQText,
          history: payloadHistory
        })
      });

      if (res.ok) {
        const data = await res.json();
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();

        // Ghi nhận hội thoại vào STM (Short-term Working Memory)
        state.chatHistory.push({ role: 'user', content: message });
        state.chatHistory.push({ role: 'assistant', content: data.reply || '' });

        let formattedReply = (data.reply || '')
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          .replace(/\n/g, '<br/>');

        if (data.citations && data.citations.length > 0) {
          const citsHtml = data.citations.map(c => `<span class="citation-pill" style="display:inline-block; margin-top:6px; margin-right:4px; padding:2px 7px; background:rgba(99,102,241,0.2); border:1px solid rgba(99,102,241,0.4); border-radius:4px; font-size:0.7rem; color:#a5b4fc; font-family:var(--font-mono);">📎 Nguồn: ${c}</span>`).join(' ');
          formattedReply += `<br/>${citsHtml}`;
        }

        if (data.memory_note) {
          const memHtml = `<div class="memory-pill" style="display:inline-flex; align-items:center; gap:4px; margin-top:6px; margin-right:4px; padding:2px 8px; background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.35); border-radius:4px; font-size:0.7rem; color:#34d399; font-weight:500;">🧠 ${data.memory_note}</div>`;
          formattedReply += `<br/>${memHtml}`;
        }

        streamChatMessage('tutor', formattedReply, null, 12);
        return;
      }
    } catch (e) {
      console.warn('[VLearn] Chat ask fallback error:', e.message);
    }

    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();
    streamChatMessage('tutor', `💡 <em>Gợi ý từ bài giảng Slide ${state.currentPage}:</em> Bạn hãy quan sát kỹ sơ đồ minh họa trên slide bên trái để tự tìm ra mối liên hệ nhé!`, null, 14);
  }

  function handleChatSubmit() {
    if (!chatInputText) return;
    const text = chatInputText.value.trim();
    if (!text) return;
    chatInputText.value = '';

    appendChatMessage('user', text);

    const textLower = text.toLowerCase();

    // 1. Nếu người dùng hỏi xin đáp án trực tiếp
    const isAskingDirectAnswer = /(cho|tiết\s*lộ|nói|xem)\s*(tôi)?\s*(luôn|ngay)?\s*(đáp\s*án|kết\s*quả)|đáp\s*án\s*(là\s*gì|nào|sao|\?)|câu\s*nào\s*đúng|chọn\s*(câu\s*)?(a\s*hay\s*b)/i.test(textLower);
    if (isAskingDirectAnswer) {
      appendChatMessage('tutor', '💡 <em>Tôi là trợ lý AI đồng hành để bạn tự hiểu bản chất, không cung cấp đáp án trực tiếp.</em> Bạn hãy đối chiếu lại từ khóa cốt lõi trên slide bên trái để tự chọn phương án đúng nhé!');
      return;
    }

    // 2. Nếu người dùng chọn phương án trắc nghiệm cụ thể (A hoặc B)
    const isExplicitOptionPick = /^(\s*tôi\s*chọn\s*|\s*chọn\s*|\s*phương\s*án\s*|\s*đáp\s*án\s*)?[ab](\.|\s|$|\))/i.test(text.trim());
    if (isExplicitOptionPick) {
      handleStudentAnswer(text);
      return;
    }

    // 3. Toàn bộ các câu hỏi khác (hỏi han, xin ví dụ, xin giải thích bản chất, thắc mắc bài học) -> Gọi Socratic Tutor
    askSocraticTutor(text);
  }

  // ================= 5. INSTRUCTOR DASHBOARD =================
  async function fetchInstructorData() {
    fetchThetaLogs();
    loadTeacherMisconceptions();
    try {
      const res = await fetch(`${API_BASE}/api/analytics/dashboard`);
      if (res.ok) {
        const dashData = await res.json();
        renderInstructorUI(dashData);
        return;
      }
    } catch (e) {
      console.warn('[VLearn] API dashboard fallback:', e.message);
    }

    if (localData.instructorDashboardData) {
      const d = localData.instructorDashboardData;
      renderInstructorUI({
        heatmap: d.topMisconceptions.map(m => ({
          topic: m.topic,
          affected_students: m.affectedStudents,
          pct: m.pct,
          severity: m.severity
        })),
        roster: d.studentRoster.map(s => ({
          id: s.id,
          level: s.level,
          streak: s.streak,
          last_error: s.lastError,
          status: s.status,
          flagged: s.flagged
        }))
      });
    }
  }

  function renderInstructorUI(dash) {
    if (heatmapBody && dash.heatmap) {
      heatmapBody.innerHTML = dash.heatmap.map(m => `
        <tr>
          <td style="font-weight: 600; color: #f8fafc;">${m.topic}</td>
          <td>${m.affected_students} HV</td>
          <td><strong>${m.pct}%</strong></td>
          <td><span class="tag-severity ${m.severity}">${m.severity}</span></td>
        </tr>
      `).join('');
    }

    if (rosterBody && dash.roster) {
      rosterBody.innerHTML = dash.roster.map(s => `
        <tr>
          <td style="font-family: var(--font-mono); color: #60a5fa; font-weight: 700;">${s.id}</td>
          <td>Lv ${s.level}</td>
          <td>${s.streak} 🔥</td>
          <td style="color: #cbd5e1;">${s.last_error}</td>
          <td style="color: ${s.flagged ? '#fb7185' : '#34d399'}; font-weight: 600;">${s.status}</td>
          <td>
            <button class="btn-mini-override" onclick="window.handleSelectOverride('${s.id}', '${s.last_error}')">
              Can thiệp
            </button>
          </td>
        </tr>
      `).join('');
    }
  }

  // Quản lý và render Nhật ký ngộ nhận của học sinh cho Giáo viên
  const miscLogBody = document.getElementById('misconception-log-body');
  const miscRecordCount = document.getElementById('misc-record-count');
  const miscFilterStatus = document.getElementById('misc-filter-status');
  const btnRefreshMiscLog = document.getElementById('btn-refresh-misc-log');

  async function loadTeacherMisconceptions() {
    if (!miscLogBody) return;
    try {
      const statusParam = miscFilterStatus ? miscFilterStatus.value : '';
      const url = statusParam ? `${API_BASE}/api/teacher/misconceptions?status=${encodeURIComponent(statusParam)}` : `${API_BASE}/api/teacher/misconceptions`;
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      const records = data.records || [];

      if (miscRecordCount) {
        miscRecordCount.textContent = `${records.length} ngộ nhận`;
      }

      if (records.length === 0) {
        miscLogBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 16px;">Chưa có bản ghi ngộ nhận nào phù hợp.</td></tr>`;
        return;
      }

      miscLogBody.innerHTML = records.map(r => {
        const timeStr = r.timestamp ? new Date(r.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--';
        const statusBadge = r.status === 'remediated'
          ? '<span style="color: #34d399; font-weight: 600;">Đã tự sửa</span>'
          : (r.status === 'teacher_intervened'
            ? '<span style="color: #60a5fa; font-weight: 600;">GV đã can thiệp</span>'
            : '<span style="color: #fb7185; font-weight: 700;">Chưa giải quyết</span>');

        const safeAssumption = (r.faulty_assumption || '').replace(/'/g, "\\'");

        return `
          <tr>
            <td style="font-family: var(--font-mono); color: #94a3b8; font-size: 0.75rem;">${timeStr}</td>
            <td style="font-family: var(--font-mono); color: #60a5fa; font-weight: 700;">${r.student_id}</td>
            <td><span style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">${(r.deck || '').toUpperCase()} T${r.page}</span></td>
            <td style="color: #f8fafc; font-weight: 600;">${r.faulty_assumption}</td>
            <td style="color: #cbd5e1; font-style: italic; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${r.student_answer || ''}">${r.student_answer || '—'}</td>
            <td>${statusBadge}</td>
            <td style="color: #a78bfa; font-size: 0.78rem; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${r.teacher_note || ''}">${r.teacher_note || '—'}</td>
            <td>
              <button class="btn-mini-override" onclick="window.handleResolveMisconception('${r.id}', '${r.student_id}', '${safeAssumption}')">
                Ghi chú / Đã xử lý
              </button>
            </td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.warn('[VLearn] Lỗi tải danh sách ngộ nhận:', e);
    }
  }

  window.handleResolveMisconception = async function(recordId, studentId, errorText) {
    const note = prompt(`Nhập ghi chú sư phạm hoặc hướng dẫn cho ${studentId} về lỗi:\n"${errorText}"`, 'Đã giải thích và hướng dẫn học viên nắm đúng bản chất.');
    if (note === null) return;
    try {
      const res = await fetch(`${API_BASE}/api/teacher/misconceptions/${recordId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'resolve', note: note })
      });
      if (res.ok) {
        alert('Đã cập nhật trạng thái ngộ nhận thành công!');
        loadTeacherMisconceptions();
        fetchInstructorData();
      }
    } catch (e) {
      alert('Lỗi cập nhật ngộ nhận: ' + e);
    }
  };

  if (btnRefreshMiscLog) {
    btnRefreshMiscLog.addEventListener('click', loadTeacherMisconceptions);
  }
  if (miscFilterStatus) {
    miscFilterStatus.addEventListener('change', loadTeacherMisconceptions);
  }

  // Tab switching cho màn hình Giảng viên
  const instTabBtns = document.querySelectorAll('.inst-tab-btn');
  const instTabOverview = document.getElementById('inst-tab-overview');
  const instTabLogs = document.getElementById('inst-tab-logs');
  const thetaTabBadge = document.getElementById('theta-tab-badge');

  function switchInstructorTab(tabId) {
    instTabBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.instTab === tabId);
    });
    if (tabId === 'tab-overview') {
      if (instTabOverview) {
        instTabOverview.style.display = 'block';
        instTabOverview.classList.add('active');
      }
      if (instTabLogs) {
        instTabLogs.style.display = 'none';
        instTabLogs.classList.remove('active');
      }
    } else if (tabId === 'tab-logs') {
      if (instTabOverview) {
        instTabOverview.style.display = 'none';
        instTabOverview.classList.remove('active');
      }
      if (instTabLogs) {
        instTabLogs.style.display = 'block';
        instTabLogs.classList.add('active');
      }
      fetchThetaLogs();
    }
  }

  instTabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      switchInstructorTab(btn.dataset.instTab);
    });
  });

  window.handleSelectOverride = (id, err) => {
    switchInstructorTab('tab-overview');
    if (overrideStudentId) overrideStudentId.value = id;
    if (overrideStudentError) overrideStudentError.value = err;
    if (overrideNotes) {
      overrideNotes.focus();
      const panel = document.querySelector('.override-panel');
      if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  if (btnSubmitOverride) {
    btnSubmitOverride.addEventListener('click', async () => {
      const studentId = overrideStudentId ? overrideStudentId.value : 'S0448';
      const originalError = overrideStudentError ? overrideStudentError.value : 'Lỗi tư duy';
      const action = overrideActionSelect ? overrideActionSelect.value : 'relabel';
      const notes = overrideNotes ? overrideNotes.value : '';

      try {
        const res = await fetch(`${API_BASE}/api/instructor/override`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            student_id: studentId,
            original_error: originalError,
            action: action,
            notes: notes
          })
        });

        if (res.ok) {
          const result = await res.json();
          alert(`✅ ĐÃ LƯU CAN THIỆP CHO HỌC VIÊN ${studentId}`);
          fetchInstructorData();
          return;
        }
      } catch (e) {
        console.warn('[VLearn] Override fallback:', e.message);
      }

      alert(`✅ ĐÃ LƯU CAN THIỆP CHO HỌC VIÊN ${studentId}`);
    });
  }

  // ================= 6. THETA REAL-TIME AI LOG (logbythea.jsonl) =================
  const thetaLogBody = document.getElementById('theta-log-body');
  const thetaLogCount = document.getElementById('theta-log-count');
  const thetaFilterStudent = document.getElementById('theta-filter-student');
  const thetaFilterEvent = document.getElementById('theta-filter-event');
  const btnRefreshThetaLog = document.getElementById('btn-refresh-theta-log');

  let allThetaLogs = [];

  async function fetchThetaLogs() {
    if (!thetaLogBody) return;
    try {
      const res = await fetch(`${API_BASE}/api/ai-log/thea?limit=150`);
      if (res.ok) {
        const data = await res.json();
        allThetaLogs = (data.logs || []).reverse(); // Mới nhất lên đầu
        if (thetaTabBadge) {
          thetaTabBadge.textContent = allThetaLogs.length;
        }
        updateThetaStudentFilterOptions();
        renderThetaLogsUI();
        return;
      }
    } catch (e) {
      console.warn('[VLearn] Fetch theta logs error:', e.message);
    }
  }

  function updateThetaStudentFilterOptions() {
    if (!thetaFilterStudent) return;
    const currentVal = thetaFilterStudent.value;
    const students = [...new Set(allThetaLogs.map(l => l.student_id).filter(Boolean))];
    thetaFilterStudent.innerHTML = '<option value="">Tất cả học viên</option>' +
      students.map(s => `<option value="${s}" ${s === currentVal ? 'selected' : ''}>Học viên ${s}</option>`).join('');
  }

  function renderThetaLogsUI() {
    if (!thetaLogBody) return;
    const studentFilter = thetaFilterStudent ? thetaFilterStudent.value : '';
    const eventFilter = thetaFilterEvent ? thetaFilterEvent.value : '';

    let filtered = allThetaLogs;
    if (studentFilter) {
      filtered = filtered.filter(l => l.student_id === studentFilter);
    }
    if (eventFilter) {
      filtered = filtered.filter(l => l.event === eventFilter);
    }

    if (thetaLogCount) {
      thetaLogCount.textContent = `${filtered.length} sự kiện`;
    }

    if (filtered.length === 0) {
      thetaLogBody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#94a3b8; padding:24px;">Chưa có dữ liệu log phù hợp với bộ lọc.</td></tr>';
      return;
    }

    thetaLogBody.innerHTML = filtered.map(log => {
      // Format time
      let timeStr = '';
      try {
        const d = new Date(log.timestamp);
        timeStr = d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      } catch (e) {
        timeStr = (log.timestamp || '').slice(11, 19);
      }

      // Event Badge
      const isQuestion = log.event === 'question_asked';
      const eventBadge = isQuestion
        ? '<span style="background:rgba(139,92,246,0.2); color:#c4b5fd; border:1px solid rgba(139,92,246,0.3); padding:2px 7px; border-radius:4px; font-size:0.72rem; font-weight:600;">❓ Câu hỏi</span>'
        : '<span style="background:rgba(59,130,246,0.2); color:#93c5fd; border:1px solid rgba(59,130,246,0.3); padding:2px 7px; border-radius:4px; font-size:0.72rem; font-weight:600;">📝 Chấm IRT</span>';

      // Nội dung / Câu trả lời
      const contentText = isQuestion
        ? (log.question_text || 'Câu hỏi kiểm tra kiến thức')
        : (log.user_answer || (log.selected_option_id ? `Chọn phương án ${log.selected_option_id}` : 'Không rõ'));

      // Chẩn đoán lỗi nếu có
      let subDiagnosis = '';
      if (log.diagnostic && log.diagnostic.is_misconception) {
        subDiagnosis = `<div style="font-size:0.7rem; color:#fca5a5; margin-top:2px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="${(log.diagnostic.faulty_assumption || '').replace(/"/g, '&quot;')}">⚠️ ${log.diagnostic.faulty_assumption}</div>`;
      }

      // Kết quả
      let resultBadge = '<span style="color:#64748b;">-</span>';
      if (!isQuestion) {
        resultBadge = log.is_correct
          ? `<span style="background:rgba(16,185,129,0.2); color:#34d399; padding:2px 6px; border-radius:4px; font-size:0.72rem; font-weight:700;">✅ Đúng (${log.score || 85}đ)</span>`
          : `<span style="background:rgba(244,63,94,0.2); color:#fb7185; padding:2px 6px; border-radius:4px; font-size:0.72rem; font-weight:700;">❌ Sai (${log.score || 40}đ)</span>`;
      }

      // Biến thiên Theta θ & Cấp độ
      let thetaSnippet = '';
      if (!isQuestion && log.theta_before !== undefined && log.theta_after !== undefined) {
        const delta = typeof log.delta_theta === 'number' ? log.delta_theta : (log.theta_after - log.theta_before);
        const deltaFormatted = (delta >= 0 ? '+' : '') + delta.toFixed(3);
        const deltaColor = delta >= 0 ? '#34d399' : '#fb7185';
        thetaSnippet = `
          <div style="font-family:var(--font-mono); font-size:0.74rem;">
            <span>${log.theta_before.toFixed(2)} ➔ <strong>${log.theta_after.toFixed(2)}</strong></span>
            <span style="color:${deltaColor}; font-weight:700; margin-left:3px;">(${deltaFormatted})</span>
          </div>
        `;
      } else {
        const th = typeof log.theta === 'number' ? log.theta.toFixed(2) : '0.00';
        thetaSnippet = `<div style="font-family:var(--font-mono); font-size:0.74rem; color:#94a3b8;">θ = ${th}</div>`;
      }

      const lvlStr = log.level_after ? `Lv ${log.level_before ?? 1} ➔ Lv ${log.level_after}` : `Lv ${log.level || 1}`;
      const streakStr = log.streak_after !== undefined ? `(🔥${log.streak_after}/2)` : '';
      const levelSnippet = `<div style="font-size:0.7rem; color:#a5b4fc; margin-top:2px;">${lvlStr} <span style="color:#f59e0b;">${streakStr}</span></div>`;

      // Nút Thao tác
      const cleanErr = (log.diagnostic?.faulty_assumption || 'Lỗi ngộ nhận').replace(/'/g, "\\'");
      const actionBtn = `
        <button class="btn-mini-override" style="padding:3px 8px; font-size:0.7rem;" onclick="window.handleSelectOverride('${log.student_id}', '${cleanErr}')">
          Can thiệp
        </button>
      `;

      return `
        <tr>
          <td style="font-family:var(--font-mono); font-size:0.72rem; color:#94a3b8;">${timeStr}</td>
          <td>
            <span style="font-family:var(--font-mono); color:#60a5fa; font-weight:700; font-size:0.78rem;">${log.student_id}</span>
            <span style="font-size:0.72rem; color:#94a3b8; margin-left:4px;">· S${log.page}</span>
          </td>
          <td>${eventBadge}</td>
          <td style="max-width:280px; overflow:hidden;">
            <div style="font-size:0.76rem; color:#f1f5f9; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="${(contentText).replace(/"/g, '&quot;')}">${contentText}</div>
            ${subDiagnosis}
          </td>
          <td>${resultBadge}</td>
          <td>
            ${thetaSnippet}
            ${levelSnippet}
          </td>
          <td style="text-align:center;">${actionBtn}</td>
        </tr>
      `;
    }).join('');
  }

  if (thetaFilterStudent) thetaFilterStudent.addEventListener('change', renderThetaLogsUI);
  if (thetaFilterEvent) thetaFilterEvent.addEventListener('change', renderThetaLogsUI);
  if (btnRefreshThetaLog) btnRefreshThetaLog.addEventListener('click', fetchThetaLogs);

  // Khởi động
  initAuth();
  checkAIStatus();
});
