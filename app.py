import streamlit as st
import asyncio
import os
from groq import Groq
import edge_tts
from streamlit_mic_recorder import speech_to_text

# Cấu hình hiển thị trang
st.set_page_config(
    page_title="Gia sư luyện tập tiếng anh", 
    page_icon="🌸", 
    layout="centered"
)

# Thêm CSS cố định tiêu đề ở trên, nút điều khiển ở dưới đáy và tối ưu cỡ chữ di động
st.markdown("""
<style>
    /* Ẩn các thành phần thừa của Streamlit để tăng không gian hiển thị */
    [data-testid="stHeader"] {background: transparent;}
    
    /* 1. CỐ ĐỊNH TIÊU ĐỀ TRÊN CÙNG */
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: #F8F9FA;
        text-align: center;
        padding: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        z-index: 999;
        border-bottom: 1px solid #EAEAEA;
    }
    .fixed-header h1 {
        color: #2C3E50;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
    }

    /* Tạo khoảng trống phía trên để nội dung không bị tiêu đề che khuất */
    .main-content {
        margin-top: 75px;
        margin-bottom: 90px;
        padding: 10px;
    }
    
    /* 2. KHUNG HÌNH BOT MINH HỌA TRỰC QUAN */
    .bot-avatar-container {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }
    .bot-avatar-img {
        width: 110px;
        height: 110px;
        border-radius: 50%;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border: 3px solid #FFF;
    }

    /* 3. CỐ ĐỊNH THANH ĐIỀU KHIỂN Ở ĐÁY MÀN HÌNH */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #FFFFFF;
        padding: 10px 15px;
        box-shadow: 0 -4px 15px rgba(0,0,0,0.06);
        z-index: 999;
        border-top: 1px solid #EAEAEA;
    }
    .footer-container {
        max-width: 700px;
        margin: 0 auto;
    }

    /* Tối ưu hóa cỡ chữ hiển thị cân đối trên Điện thoại & Máy tính */
    .text-response {
        font-size: 1.1rem;
        line-height: 1.5;
        color: #333333;
    }
    
    @media (max-width: 640px) {
        .fixed-header h1 { font-size: 1.3rem !important; }
        .bot-avatar-img { width: 85px; height: 85px; }
        .text-response { font-size: 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo API Groq từ Secrets
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Chỉ thị hệ thống thiết lập tính cách cho Bot
PEDAGOGICAL_PROMPT = """
You are a friendly, encouraging, and supportive English speaking tutor. 
Your goal is to help the user practice English conversational skills.
Rules:
1. Keep your responses short, natural, and engaging (1-3 sentences max).
2. Use simple, clear language suitable for learners.
3. Always end with an interesting follow-up question to keep the conversation flowing.
4. Gently comment or rephrase if the user makes a noticeable grammatical error, but keep the tone positive.
"""

# Khởi tạo các biến lưu trữ hội thoại liên tục (Session State)
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "current_ai_text" not in st.session_state:
    st.session_state.current_ai_text = "Hello! I am your AI Speaking Tutor. Let's practice talking in English together! What is your name?"
if "current_user_text" not in st.session_state:
    st.session_state.current_user_text = ""
if "play_audio" not in st.session_state:
    st.session_state.play_audio = False

async def generate_voice(text, filename="response.mp3"):
    """Chuyển văn bản thành file nói mp3"""
    communicate = edge_tts.Communicate(text, "en-US-EmmaNeural")
    await communicate.save(filename)

def ask_groq(user_input):
    """Gửi toàn bộ lịch sử trò chuyện lên Groq để nhận câu trả lời phát triển tiếp nối"""
    messages = [{"role": "system", "content": PEDAGOGICAL_PROMPT}]
    # Nạp toàn bộ tiến trình lịch sử cuộc trò chuyện từ trước đến nay vào để bot nhớ ngữ cảnh
    for msg in st.session_state.conversation_history:
        messages.append(msg)
    # Thêm câu nói mới nhất của người dùng
    messages.append({"role": "user", "content": user_input})
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================
# GIAO DIỆN HIỂN THỊ
# ==========================================

# 1. Tiêu đề cố định trên cùng
st.markdown("""
<div class="fixed-header">
    <h1>🌸 Gia sư luyện tập tiếng anh </h1>
</div>
""", unsafe_allow_html=True)

# Mở khung chứa nội dung chính (Được đẩy dịch xuống để không bị che khuất)
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# 2. Con Bot AI minh họa trực quan ở giữa
st.markdown("""
<div class="bot-avatar-container">
    <img class="bot-avatar-img" src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f469_200d_1f3eb/512.webp" alt="AI Teacher">
</div>
""", unsafe_allow_html=True)

# 3. Khu vực hiển thị nội dung câu thoại hiện tại (Luôn xuất hiện ở giữa)
st.write("---")
if st.session_state.current_user_text:
    st.markdown(f"**🧑 Bạn vừa nói/gõ:**")
    st.info(st.session_state.current_user_text)

st.markdown(f"**👩 Gia sư AI phản hồi:**")
st.success(st.session_state.current_ai_text)

# Phát âm thanh tự động nếu có phản hồi mới
if st.session_state.play_audio and os.path.exists("response.mp3"):
    st.audio("response.mp3", format="audio/mp3", autoplay=True)
    st.session_state.play_audio = False

# Đóng khung chứa nội dung chính
st.markdown('</div>', unsafe_allow_html=True)

# 4. Thanh công cụ (Ghi âm + Gõ chữ) CỐ ĐỊNH HOÀN TOÀN Ở ĐÁY MÀN HÌNH
st.markdown('<div class="fixed-footer"><div class="footer-container">', unsafe_allow_html=True)

col1, col2, col3 = st.columns([3, 5, 2])

with col1:
    # Nút bấm ghi âm nói giọng nói
    spoken_text = speech_to_text(
        start_prompt="🎙️ Bấm để nói",
        stop_prompt="🛑 Dừng nói",
        language='en',
        use_container_width=True,
        key="voice_input"
    )

with col2:
    # Ô nhập văn bản khi không tiện nói
    typed_text = st.text_input("", placeholder="Hoặc gõ chữ tiếng Anh...", label_visibility="collapsed", key="text_field")

with col3:
    # Nút bấm xóa lịch sử làm lại từ đầu
    if st.button("🗑️ Xóa", use_container_width=True):
        st.session_state.conversation_history = []
        st.session_state.current_user_text = ""
        st.session_state.current_ai_text = "Hello! Let's start a new practice session. What is your name?"
        if os.path.exists("response.mp3"):
            os.remove("response.mp3")
        st.rerun()

st.markdown('</div></div>', unsafe_allow_html=True)

# ==========================================
# LOGIC XỬ LÝ DỮ LIỆU ĐẦU VÀO
# ==========================================
resolved_input = None

if spoken_text:
    resolved_input = spoken_text
elif typed_text and typed_text != st.session_state.get("previous_typed_text", ""):
    resolved_input = typed_text
    st.session_state["previous_typed_text"] = typed_text

# Nếu phát hiện có câu thoại mới được đưa vào
if resolved_input:
    # Cập nhật hiển thị text của người dùng lên màn hình chính
    st.session_state.current_user_text = resolved_input
    
    with st.spinner("Gia sư đang nghe và chuẩn bị câu trả lời..."):
        # 1. Gọi Groq lấy câu trả lời (Có truyền theo cả chuỗi lịch sử trước đó)
        new_ai_reply = ask_groq(resolved_input)
        
        # 2. Lưu cặp câu thoại này vào lịch sử bộ nhớ để lần sau nói tiếp câu chuyện liên mạch
        st.session_state.conversation_history.append({"role": "user", "content": resolved_input})
        st.session_state.conversation_history.append({"role": "assistant", "content": new_ai_reply})
        
        # 3. Cập nhật câu thoại của bot lên màn hình
        st.session_state.current_ai_text = new_ai_reply
        
        # 4. Tạo file âm thanh đọc nối tiếp câu thoại mới
        asyncio.run(generate_voice(new_ai_reply, "response.mp3"))
        st.session_state.play_audio = True
        
    st.rerun()
