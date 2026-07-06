import streamlit as st
import asyncio
import os
import json
from groq import Groq
import edge_tts
from streamlit_mic_recorder import speech_to_text

# ==========================================
# CẤU HÌNH TRANG & GIAO DIỆN CHATBOX CỐ ĐỊNH
# ==========================================
st.set_page_config(
    page_title="Gia sư luyện tập tiếng anh", 
    page_icon="🌸", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Thêm CSS cao cấp cố định giao diện để không cần cuộn trang trên Điện thoại/PC
st.markdown("""
<style>
    /* Ẩn bớt các khoảng trắng thừa của Streamlit */
    [data-testid="stHeader"] {background: transparent;}
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 5rem !important;
        max-width: 800px !important;
    }
    
    /* Thiết kế Header tên Bot */
    .bot-header {
        text-align: center;
        background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%);
        padding: 15px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .bot-header h1 {
        color: #2C3E50;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
    }
    
    /* Thiết kế Avatar Bot hoạt họa trung tâm */
    .avatar-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 15px;
    }
    .bot-avatar {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        border: 4px solid #fff;
        box-shadow: 0 4px 20px rgba(255, 105, 180, 0.3);
        animation: pulse 3s infinite alternate;
    }
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 4px 15px rgba(255, 105, 180, 0.3); }
        100% { transform: scale(1.05); box-shadow: 0 4px 25px rgba(255, 105, 180, 0.6); }
    }

    /* Khung hộp thoại bong bóng chat */
    .chat-bubble {
        padding: 12px 16px;
        border-radius: 20px;
        margin-bottom: 10px;
        max-width: 85%;
        font-size: 1rem;
        line-height: 1.4;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .chat-user {
        background-color: #DCF8C6;
        color: #333;
        margin-left: auto;
        border-bottom-right-radius: 5px;
    }
    .chat-bot {
        background-color: #FFFFFF;
        color: #333;
        margin-right: auto;
        border-bottom-left-radius: 5px;
        border: 1px solid #EAEAEA;
    }
    
    /* Gắn chặt thanh điều khiển nhập liệu/ghi âm xuống ĐÁY màn hình */
    .footer-controls {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(255, 255, 255, 0.95);
        padding: 10px 20px;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.08);
        z-index: 999;
        display: flex;
        justify-content: center;
    }
    .footer-content {
        max-width: 800px;
        width: 100%;
    }
    
    /* Cấu hình chữ thân thiện với điện thoại di động */
    @media (max-width: 640px) {
        .bot-header h1 { font-size: 1.4rem !important; }
        .bot-avatar { width: 90px; height: 90px; }
        .chat-bubble { font-size: 0.95rem; max-width: 90%; }
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo API Groq từ Secrets
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Chỉ thị hệ thống định hình hành vi Gia sư kiến tạo
PEDAGOGICAL_PROMPT = """
You are a friendly, encouraging, and supportive English speaking tutor. 
Your goal is to help the user practice English conversational skills.
Rules:
1. Keep your responses short, natural, and engaging (1-3 sentences max).
2. Use simple, clear language suitable for learners.
3. Always end with an interesting follow-up question to keep the conversation flowing.
4. Gently comment or rephrase if the user makes a noticeable grammatical error, but keep the tone positive.
"""

# Khởi tạo các biến Session State lưu trữ lịch sử cuộc trò chuyện
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your AI Speaking Tutor. Let's practice talking in English together! What is your name?"}]
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None

async def generate_voice_file(text, filename="response.mp3"):
    """Hàm chuyển văn bản thành giọng nói tiếng Anh"""
    communicate = edge_tts.Communicate(text, "en-US-EmmaNeural")
    await communicate.save(filename)

def get_groq_response(chat_history):
    """Hàm gọi AI Groq xử lý hội thoại"""
    messages = [{"role": "system", "content": PEDAGOGICAL_PROMPT}] + chat_history
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
# GIAO DIỆN HIỂN THỊ TRÊN MÀN HÌNH
# ==========================================

# 1. TIÊU ĐỀ TRÊN CÙNG
st.markdown("""
<div class="bot-header">
    <h1>🌸 Gia sư luyện tập tiếng anh 🌸</h1>
</div>
""", unsafe_allow_html=True)

# 2. CON BOT AI MINH HỌA TRUNG TÂM (Sử dụng ảnh minh họa hoạt hình cute)
st.markdown("""
<div class="avatar-container">
    <img class="bot-avatar" src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f469_200d_1f3eb/512.webp" alt="AI Tutor">
</div>
""", unsafe_allow_html=True)

# 3. KHU VỰC NỘI DUNG CHAT (Nằm ở giữa)
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-bubble chat-user"><b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bubble chat-bot"><b>AI Tutor:</b> {msg["content"]}</div>', unsafe_allow_html=True)

# Phát âm thanh phản hồi của AI nếu có
if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
    st.audio(st.session_state.audio_path, format="audio/mp3", autoplay=True)
    st.session_state.audio_path = None # Reset sau khi phát xong

# 4. THANH ĐIỀU KHIỂN LUÔN CỐ ĐỊNH Ở ĐÁY MÀN HÌNH (Ghi âm + Nhập chữ)
st.markdown('<div class="footer-controls"><div class="footer-content">', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 5, 1.5])

# Công cụ 1: Nhấn để GHI ÂM giọng nói
with col1:
    user_speech = speech_to_text(
        start_prompt="🎙️ Bấm để nói",
        stop_prompt="🛑 Dừng nói",
        language='en',
        use_container_width=True,
        key="speech_input"
    )

# Công cụ 2: Ô ĐÁNH CHỮ (Dành cho lúc không tiện nói)
with col2:
    user_text = st.text_input("", placeholder="Hoặc gõ chữ tiếng Anh vào đây...", label_visibility="collapsed", key="text_input")

# Công cụ 3: Nút Xóa cuộc thoại
with col3:
    if st.button("🗑️ Xóa", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! Let's start a new practice session. What would you like to talk about today?"}]
        if os.path.exists("response.mp3"):
            os.remove("response.mp3")
        st.rerun()

st.markdown('</div></div>', unsafe_allow_html=True)

# ==========================================
# XỬ LÝ DỮ LIỆU ĐẦU VÀO TỪ NGƯỜI DÙNG
# ==========================================
final_input = None

if user_speech:
    final_input = user_speech
elif user_text and user_text != st.session_state.get("last_text_input", ""):
    final_input = user_text
    st.session_state["last_text_input"] = user_text

if final_input:
    # Lưu tin nhắn của Người dùng
    st.session_state.messages.append({"role": "user", "content": final_input})
    
    # Gọi AI sinh câu trả lời
    with st.spinner("AI Tutor đang lắng nghe và suy nghĩ..."):
        bot_reply = get_groq_response(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        
        # Sinh file âm thanh đọc câu trả lời
        asyncio.run(generate_voice_file(bot_reply, "response.mp3"))
        st.session_state.audio_path = "response.mp3"
        
    st.rerun()
