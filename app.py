import streamlit as st
import asyncio
import os
import json
from groq import Groq  # Đã đổi từ google.genai sang thư viện groq
import edge_tts
from streamlit_mic_recorder import speech_to_text

# =====================================================================
# CẤU HÌNH KHÓA API KEY CỦA BẠN TẠI ĐÂY
# =====================================================================
# Khởi tạo khóa API bảo mật từ Streamlit Secrets bằng hàm get an toàn
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")

# Khởi tạo client sử dụng thư viện Groq
client = Groq(api_key=GROQ_API_KEY)

# Chỉ thị hệ thống định hình hành vi Gia sư kiến tạo (Constructivist Peer Tutor)
PEDAGOGICAL_PROMPT = """
You are a warm, collaborative, and highly effective English peer tutor.
Your core objective is to help the user learn and practice English dynamically.
Adhere strictly to the following interaction rules:
1. When the user makes a grammatical, spelling, or vocabulary mistake, DO NOT give the correct answer immediately.
2. Acknowledge their effort, point out the error, explain the rule briefly using simple language, and encourage them to try correcting it.
3. Keep responses highly focused, direct, and under 150 words. Avoid generic praise (e.g., "Good job!", "Excellent!").
4. Always end your turn with a level-appropriate, open-ended question based on the ongoing topic to keep the conversation going.
5. If the user fails to correct the mistake after 2-3 attempts, provide the direct correction and transition to a new topic.
"""

# Khởi tạo các trạng thái bộ nhớ đệm
if "chat_history" not in st.session_state:
    st.session_state.chat_history = list()
# Biến kiểm tra chống trùng lặp yêu cầu gọi API
if "last_processed_text" not in st.session_state:
    st.session_state.last_processed_text = ""

# Thiết lập cấu hình trang Streamlit
st.set_page_config(page_title="Gia Sư Tiếng Anh Nông Trại 🧑‍🌾🌸", page_icon="🌸", layout="centered")

# --- ĐOẠN CODE TRANG TRÍ GIAO DIỆN NÔNG TRẠI BẰNG CSS ---
st.markdown("""
<style>
    /* Toàn bộ nền ứng dụng: Hiệu ứng chuyển màu mượt mà từ trời xanh dịu sang cỏ xanh non */
    .stApp {
        background: linear-gradient(135deg, #E8F5E9 0%, #FFF8E1 100%)!important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #000000 !important; /* Ép màu chữ mặc định toàn trang là màu đen */
    }
    
    /* Đảm bảo các thẻ văn bản cơ bản không bị ảnh hưởng bởi chế độ Dark Mode của nền tảng */
    p, span, label, div[data-testid="stMarkdownContainer"] {
        color: #000000 !important;
    }
    
    /* Làm đẹp tiêu đề chính mang màu sắc của khu vườn */
    h1 {
        color: #2E7D32!important;
        font-family: 'Segoe UI', sans-serif!important;
        font-weight: 800!important;
        text-shadow: 2px 2px 4px rgba(46, 125, 50, 0.15)!important;
    }

    /* Thiết lập lại nút ghi âm và nút dọn dẹp */
    div.stButton > button {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)!important;
        color: white!important; /* Chữ trong nút vẫn giữ màu trắng */
        border-radius: 20px!important;
        border: none!important;
        padding: 12px 30px!important;
        font-weight: bold!important;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3)!important;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)!important;
    }
    div.stButton > button:hover {
        transform: scale(1.05) translateY(-3px)!important;
        box-shadow: 0 6px 20px rgba(46, 125, 50, 0.4)!important;
    }

    /* Chỉnh sửa kiểu dáng hộp Dịch Tiếng Việt */
    .stExpander {
        background-color: rgba(255, 255, 255, 0.6)!important;
        border: 1px solid #C8E6C9!important;
        border-radius: 12px!important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02)!important;
    }

    /* ==========================================================
       BỔ SUNG CSS: NEO CỐ ĐỊNH THANH ĐIỀU KHIỂN XUỐNG ĐÁY MÀN HÌNH
       ========================================================== */
    /* Tạo khoảng đệm ở đáy nội dung chính để không bị thanh công cụ che mất */
    .main-scroll-container {
        margin-bottom: 110px;
    }

    /* Khung cố định ở đáy màn hình */
    .fixed-footer-panel {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, rgba(232, 245, 233, 0.95) 0%, rgba(255, 248, 225, 0.95) 100%);
        padding: 15px 20px;
        box-shadow: 0 -5px 20px rgba(0,0,0,0.08);
        z-index: 999;
        border-top: 1px solid #C8E6C9;
    }
    .footer-content-wrapper {
        max-width: 700px;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

# Bao bọc toàn bộ nội dung hiển thị lịch sử trò chuyện vào một container div để căn khoảng cách đáy
st.markdown('<div class="main-scroll-container">', unsafe_allow_html=True)

st.title("Gia Sư Tiếng Anh Nông Trại 🧑‍🌾🌸")
st.write("Chăm sóc vườn tri thức Anh ngữ mỗi ngày cùng cành hoa đào thông thái.")

# --- KHU VỰC GIAO TIẾP VÀ LUYỆN NÓI THỜI GIAN THỰC ---
st.header("Luyện Nói Tiếng Anh Với Cành Hoa AI 🌸")
st.write("Hãy nhấn nút ghi âm bên dưới và nói một câu tiếng Anh. Cành hoa thông thái sẽ lắng nghe và trò chuyện cùng bạn.")

# Thiết lập nhận diện đầu vào từ micro
captured_text = None

# XỬ LÝ LOGIC API KHI CÓ ĐẦU VÀO MỚI (Đặt trước phần hiển thị để cập nhật danh sách mượt mà)
# Để nhận diện từ module ghi âm ở đáy, chúng ta cần khai báo một vị trí ẩn tạm thời để hứng dữ liệu
placeholder_stt = st.empty()

# HIỂN THỊ LẠI LỊCH SỬ TRÒ CHUYỆN
for item in st.session_state.chat_history:
    if isinstance(item, (tuple, list)) and len(item) >= 2:
        speaker = item[0]  # Vai trò "user" hoặc "ai"
        text = item[1]     # Câu thoại
        translation = item[2] if len(item) >= 3 else None
        
        if speaker == "user":
            st.chat_message("user", avatar="🧑‍🌾").write(text)
        else:
            st.chat_message("assistant", avatar="🌸").write(text)
            if translation:
                with st.expander("🌐 Xem cành hoa dịch nghĩa"):
                    st.write(translation)

st.markdown('</div>', unsafe_allow_html=True) # Đóng div nội dung chính

# --- THANH ĐIỀU KHIỂN ĐƯỢC ÉP CHẶT XUỐNG ĐÁY MÀN HÌNH ---
st.markdown('<div class="fixed-footer-panel"><div class="footer-content-wrapper">', unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    captured_text = speech_to_text(
        language='en',
        start_prompt="2026 ⏺️ Bắt đầu ghi âm nói",
        stop_prompt="⏹️ Dừng ghi âm",
        just_once=True,
        key='stt_module'
    )
with col2:
    if st.button("🧹 Xóa cuộc thoại", use_container_width=True):
        st.session_state.chat_history = list()
        st.session_state.last_processed_text = ""
        if os.path.exists("ai_speech.mp3"):
            try: os.remove("ai_speech.mp3")
            except: pass
        st.rerun()

st.markdown('</div></div>', unsafe_allow_html=True) # Đóng div thanh điều khiển đáy

# Chỉ xử lý khi có câu thoại mới hoàn toàn để chống lặp trang
if captured_text and captured_text != st.session_state.last_processed_text:
    st.session_state.last_processed_text = captured_text
    st.session_state.chat_history.append(("user", captured_text, None))
    
    with st.spinner("Cành hoa đang suy nghĩ câu trả lời..."):
        try:
            # Xây dựng mảng tin nhắn (messages) chứa toàn bộ lịch sử để gửi lên Groq
            groq_messages = [{"role": "system", "content": PEDAGOGICAL_PROMPT}]
            for speaker, text, _ in st.session_state.chat_history:
                role = "user" if speaker == "user" else "assistant"
                groq_messages.append({"role": role, "content": text})
                
            # Gọi API Groq tạo câu trả lời của Gia sư
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=groq_messages,
                temperature=0.7,
            )
            ai_response_text = completion.choices[0].message.content
            
            # Thực hiện dịch ngầm sang tiếng Việt bằng Groq
            vi_translation = ""
            try:
                translate_prompt = f"Translate the following English text into natural, native-sounding Vietnamese. Return ONLY the translated text, do not add any intros or explanations:\n\n{ai_response_text}"
                translation_response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": translate_prompt}],
                    temperature=0.3,
                )
                vi_translation = translation_response.choices[0].message.content
            except Exception as trans_err:
                vi_translation = f"(Không thể dịch tự động: {str(trans_err)})"
            
            st.session_state.chat_history.append(("ai", ai_response_text, vi_translation))
            
            # Chuyển đổi phản hồi văn bản của AI thành tệp âm thanh (TTS) bằng edge-tts
            async def generate_voice_file(text, output_path="ai_speech.mp3"):
                communicate = edge_tts.Communicate(text, voice="en-US-AvaNeural")
                await communicate.save(output_path)
                
            asyncio.run(generate_voice_file(ai_response_text))
            st.rerun() # Tải lại trang để cập nhật bong bóng thoại ngay lập tức
                
        except Exception as e:
            st.error(f"Lỗi kết nối hoặc xử lý API Groq: {str(e)}")
        
if os.path.exists("ai_speech.mp3") and st.session_state.last_processed_text:
    st.audio("ai_speech.mp3", format="audio/mp3", autoplay=True)
    try:
        os.remove("ai_speech.mp3")
    except PermissionError:
        pass
