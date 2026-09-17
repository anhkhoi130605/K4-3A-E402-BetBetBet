Project này là một backend FastAPI + frontend mockup để mô phỏng AI tutor thích ứng theo slide, có các luồng chính:



Sinh câu hỏi Socratic theo slide đang đọc

Đánh giá câu trả lời học viên

Phát hiện ngộ nhận / misconception

Thăng cấp độ học theo streak

Dashboard giảng viên \& override

Chat hỏi đáp theo kiểu gợi mở, không cho đáp án thẳng

Tôi đã đọc các file cốt lõi và luồng chạy chính của project, theo thứ tự:



run.py

config.py

main.py

schemas.py

prompts.py

rag\_service.py

openAI\_service.py

pedagogy\_service.py

analytics\_service.py

auth\_service.py

index.html

app.js

data.js

test\_api.py

1\) Workflow tổng thể của project

Luồng chạy như sau:



run.py khởi động uvicorn

main.py tạo app FastAPI, đăng ký middleware CORS, mount static files, định nghĩa tất cả API routes

config.py load env, đường dẫn dữ liệu slide / transcript / CSV

schemas.py định nghĩa request/response schema cho login, quiz, dashboard, chat

rag\_service.py index transcript, đọc PDF slide, search citation

openAI\_service.py gọi OpenRouter GPT-4o-mini để sinh câu hỏi, chấm điểm, chat Socratic

pedagogy\_service.py là “bộ não” của app: tạo câu hỏi, đánh giá học sinh, fallback heuristic, chat tư vấn

analytics\_service.py tổng hợp dashboard giảng viên, thống kê lỗi và override

auth\_service.py xử lý đăng nhập / đăng ký / token

app.js là frontend mockup, tự động theo dõi slide đang đọc và gọi API

data.js chứa dữ liệu mẫu cho UI, transcript mẫu, misconception bank

test\_api.py test API và luồng chính

2\) File-by-file: file nào chứa hàm gì

run.py

Mục đích: launcher app.



Hàm chính:



if \_\_name\_\_ == "\_\_main\_\_":

khởi chạy uvicorn với app backend.main:app

Nói đơn giản: đây là điểm khởi đầu khi chạy app.



config.py

Mục đích: cấu hình môi trường và dữ liệu project.



Biến chính:



BASE\_DIR

ROOT\_DATA\_DIR

DATA\_DIR

SLIDES\_DIR

TRANSCRIPT\_DIR

CHATLOG\_DIR

SURVEY\_FILE

MOCKUP\_DIR

OPENAI\_API\_KEY

OPENAI\_MODEL

GEMINI\_API\_KEY

MODEL\_NAME

Tệp này định nghĩa đường dẫn file + biến config cho toàn bộ project.



schemas.py

Mục đích: định nghĩa contract dữ liệu cho API.



Các model chính:



UserLoginRequest

UserRegisterRequest

AuthResponse

StudentAnswerRequest

InstructorOverrideRequest

MisconceptionDiagnostic

AnswerEvaluationResponse

QuestionOption

QuestionVariant

SlideQuestionResponse

KPIMetric

MisconceptionHeatmapItem

StudentRosterItem

InstructorDashboardResponse

StudentChatRequest

StudentChatResponse

Nói ngắn gọn: đây là “bản hợp đồng” giữa frontend và backend.



prompts.py

Mục đích: prompt engineering + guardrails.



Hàm chính:



check\_guardrails\_input(user\_text: str) -> Optional\[Dict\[str, Any]]

phát hiện prompt injection

chặn câu hỏi “đáp án trực tiếp”

chặn input quá ngắn

build\_question\_generator\_prompt(...)

xây prompt để sinh câu hỏi Socratic theo Bloom level

build\_evaluation\_prompt(...)

xây prompt đánh giá câu trả lời với ReAct pattern

Constant chính:



INJECTION\_PATTERNS

SOCRATIC\_GENERATOR\_SYSTEM\_PROMPT

REACT\_EVALUATOR\_SYSTEM\_PROMPT

FEW\_SHOT\_EVALUATION\_EXAMPLES

Đây là file “hộp prompt”, rất quan trọng vì app dùng AI để chấm điểm và gợi ý.



rag\_service.py

Mục đích: đọc slide PDF + index transcript.



Class:



RAGService

Hàm chính:



\_\_init\_\_

\_load\_transcripts()

get\_citation(citation\_id)

extract\_slide\_page(deck, page)

render\_slide\_image(deck, page, dpi)

search\_transcripts(keyword, limit)

Công việc:



đọc toàn bộ transcript từ thư mục data transcript

tìm citation dạng \[Txx-NNN]

extract text từ slide pdf

render slide page thành PNG

tìm transcript liên quan theo keyword

Nói ngắn gọn: đây là “RAG layer” của app.



openAI\_service.py

Mục đích: giao tiếp với OpenRouter GPT-4o-mini.



Class:



OpenRouterService

Hàm chính:



\_\_init\_\_

set\_key(key)

get\_api\_key()

is\_available()

generate\_slide\_question(...)

evaluate\_answer(...)

chat\_socratic(...)

Công việc:



gọi API OpenRouter

dùng prompt đã xây ở prompts.py

trả về JSON cho câu hỏi và đánh giá

chat Socratic có RAG context

Nói gọn: đây là “layer AI call”.



pedagogy\_service.py

Mục đích: bộ xử lý sư phạm \& logic học tập.



Class:



PedagogyService

Hàm chính:



is\_key\_milestone(deck, page)

get\_next\_milestone(deck, page)

get\_slide\_question(deck, page, level)

evaluate\_answer(req)

answer\_student\_query(req)

Biến/constant:



KEY\_MILESTONES

MISCONCEPTION\_BANK

PRESET\_FLOWS

Đây là file quan trọng nhất sau main.py. Nó là trái tim của logic:



khi học sinh ở slide nào thì sinh câu hỏi nào

nếu trả lời đúng/sai thì cập nhật streak và level

nếu mắc ngộ nhận thì trigger misconception bank

nếu hỏi chat thì trả lời theo intent: example / concept / hint / general

Nếu bạn muốn “đi vào file nào” thì file này là file đọc tiếp quan trọng nhất.



analytics\_service.py

Mục đích: dashboard giảng viên và thống kê lớp.



Class:



AnalyticsService

Hàm chính:



\_\_init\_\_

\_load\_survey\_data()

\_load\_chatlog\_data()

get\_dashboard()

apply\_override(req)

Công việc:



đọc CSV survey

đọc chatlog

tạo KPI / heatmap / roster

xử lý override của giảng viên

Nói ngắn gọn: đây là phần “thống kê lớp học”.



auth\_service.py

Mục đích: authentication \& role-based access.



Class:



AuthService

Hàm chính:



login(username, password)

register(username, password, name, role)

get\_user\_by\_token(token)

Công việc:



lưu user seed demo

sinh token

phân biệt role student / teacher

main.py

Mục đích: API gateway tổng.



Nơi định nghĩa route quan trọng:



health\_check()

login()

register()

get\_current\_user()

configure\_openrouter()

get\_deck\_info()

get\_slide\_question()

evaluate\_answer()

ask\_tutor()

get\_citation\_detail()

get\_instructor\_dashboard()

instructor\_override()

get\_slide\_image()

Cũng có các hàm tính toán 3PL:



sigmoid(x)

p3pl(theta, a, b, c)

update\_theta(theta, is\_correct, a, b, c, lr)

Đây là file trung tâm phối ghép tất cả service.



index.html

Mục đích: layout giao diện người dùng.



Bao gồm:



header

view học sinh

view giảng viên

chat panel

slide pane

instructor dashboard panel

app.js

Mục đích: logic frontend mockup, gọi API và render UI.



Các phần chính:



auth / login / register

state quản lý học viên

theo dõi slide đang đọc

load câu hỏi AI theo checkpoint

render options A/B

xử lý phản hồi đúng/sai

chat với AI companion

dashboard giảng viên

Đây là frontend thực thụ cho demo product.



data.js

Mục đích: dữ liệu mẫu tĩnh cho mockup.



Chứa:



surveyStats

chatlogStats

transcripts

exercises

misconceptionBank

slideRecallFlow

Dùng như dữ liệu demo khi frontend chạy mà không cần backend.



test\_api.py

Mục đích: kiểm thử API.



Hàm test:



test\_health()

test\_slide\_question()

test\_misconception\_detection()

test\_adaptive\_difficulty()

test\_instructor\_dashboard\_and\_override()

test\_static\_files()

test\_slide\_image()

test\_auth()

Đây là file xác minh hệ thống hoạt động đúng.



3\) Luồng nghiệp vụ theo từng module

A. Người dùng mở app

app.js khởi tạo state

gọi auth flow

load giao diện học sinh / giảng viên

B. Khi scroll slide

frontend detect checkpoint page

gọi /api/slide-question

main.py -> pedagogy\_service.py

get\_slide\_question() sinh câu hỏi

dùng RAGService.extract\_slide\_page() + OpenRouter nếu có key

C. Khi học sinh chọn đáp án / trả lời tự do

frontend gửi tới /api/chat/evaluate

main.py -> evaluate\_answer()

pedagogy\_service.py

nếu có LLM thì gọi openAI\_service.py

nếu không thì dùng heuristic + misconception bank

cập nhật streak và level

trả về AnswerEvaluationResponse

D. Khi học sinh chat

frontend gọi /api/chat/ask

pedagogy\_service.py answer\_student\_query()

search transcript bằng RAGService.search\_transcripts()

gọi OpenRouter chat\_socratic()

trả kết quả theo intent

E. Giảng viên dashboard

frontend gọi /api/analytics/dashboard

analytics\_service.py tổng hợp KPI + heatmap + roster

main.py trả dữ liệu chuẩn theo schema

F. Override của giảng viên

POST /api/instructor/override

main.py -> instructor\_override()

analytics\_service.py apply\_override()

4\) File nào nên đọc tiếp theo nếu bạn muốn “đi sâu”

Đây là chuỗi đọc quan trọng nhất:



main.py

pedagogy\_service.py

openAI\_service.py

prompts.py

rag\_service.py

analytics\_service.py

auth\_service.py

